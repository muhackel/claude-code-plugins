import contextlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid

import jsonschema

from common import (Error, alive, atomic, digest, fingerprint, identity, lock, now, read_json,
                    write_json, write_preflight)
from state import TERMINAL, validate_result
import snapshot
import transport
import delegation
import activity

PACKAGE = Path(__file__).resolve().parents[1]


def result_schema(role):
    return read_json(PACKAGE / "schemas" / f"{role}.json")


def stop_process(process):
    if process.poll() is None:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)


class Runner:
    def __init__(self, store):
        self.store = store

    def check_stop(self):
        if self.store.load()["stop_requested"]:
            raise Error("Auftrag durch Nutzer angehalten; keine weitere Übernahme.")

    def adapter(self, role, target, config):
        binding = self.store.load().get("adapters", {}).get(role)
        adapter = transport.resolve(binding["target"] if binding else target,
                                    binding.get("model") if binding else config["model"],
                                    binding.get("effort", config["effort"]) if binding else config["effort"])
        if binding and adapter != binding:
            raise Error("CLI-Vertrag seit der Rollenbindung verändert; neue Planung mit geprüftem Adapter erforderlich.")
        def bind(state):
            state.setdefault("adapters", {})[role] = adapter
        self.store.change(None, "adapter_bound", bind)
        return adapter

    def stop(self, kind, expected):
        def action(state):
            state["stop_requested"] = kind
            active = [r for r in state["runs"] if r["status"] in ("prepared", "running")]
            if active and not any(alive(r.get("owner")) or alive(r.get("child")) for r in active):
                for run in active:
                    run.update(status="cancelled" if kind == "cancel" else "interrupted", ended_at=now())
                state.update(activity="idle", blocker="Unterbrochenen Auftrag und Teiländerungen prüfen.")
            if state["activity"] != "running":
                state.update(activity="idle" if kind == "cancel" else "paused")
                if kind == "cancel":
                    state["phase"] = "cancelled"
        return self.store.change(expected, kind + "_requested", action)

    def resume(self, expected, resolution=None, extra_rounds=0):
        with lock(self.store.run_lock):
            def action(state):
                for run in state["runs"]:
                    if run["status"] in ("prepared", "running"):
                        if alive(run.get("child")) or alive(run.get("owner")):
                            raise Error("Vorheriger Prozess läuft noch; kein zweiter Start.")
                        run["status"] = "cancelled" if state["stop_requested"] == "cancel" else "interrupted"
                        run["ended_at"] = now()
                        state["blocker"] = "Unterbrochenen Auftrag und Teiländerungen prüfen."
                if state["stop_requested"] == "cancel":
                    state.update(phase="cancelled", activity="idle")
                    return
                if state["spec"]:
                    self.store.check_spec(state)
                if state.get("blocker") and not resolution:
                    raise Error("Fortsetzungsbeleg erforderlich: " + str(state["blocker"]))
                if extra_rounds < 0 or (extra_rounds and not resolution):
                    raise Error("Zusätzliche Runden benötigen einen begründeten Nutzerauftrag.")
                state["extra_rounds"] = state.get("extra_rounds", 0) + extra_rounds
                state["resume_resolution"] = resolution
                state.update(activity="idle", blocker=None, stop_requested=None)
            return self.store.change(expected, "resumed", action)

    def reevaluate(self, expected):
        def action(state):
            self.store.idle(state)
            self.store.check_spec(state)
            if state["phase"] not in ("evaluating", "awaiting_acceptance"):
                raise Error("Kein Prüfstand zur erneuten Evaluation vorhanden.")
            state.update(phase="evaluating", activity="idle", evaluation=None,
                         blocker=None, stop_requested=None)
        return self.store.change(expected, "reevaluate", action)

    def execute_child(self, run, argv, handover, output_dir, config, env=None):
        output_dir.mkdir(parents=True, exist_ok=True)
        atomic(output_dir / "handover.txt", handover)
        read_fd, write_fd = os.pipe()
        process = None
        started = time.monotonic()
        try:
            with (output_dir / "handover.txt").open("rb") as stdin, \
                 (output_dir / "stdout.log").open("wb") as stdout, \
                 (output_dir / "stderr.log").open("wb") as stderr:
                process = subprocess.Popen([sys.executable, str(PACKAGE / "scripts/launch.py"),
                    str(read_fd), *argv], stdin=stdin, stdout=stdout, stderr=stderr,
                    env=env or transport.environment(), pass_fds=(read_fd,), start_new_session=True)
                os.close(read_fd)
                read_fd = -1
                child = identity(process.pid)
                def register(state):
                    active = state["runs"][-1]
                    if active["id"] != run["id"] or state["stop_requested"]:
                        raise Error("Start wurde zwischenzeitlich zurückgezogen.")
                    active.update(child=child, status="running", argv=argv, started_at=now())
                self.store.change(None, "process_registered", register)
                os.write(write_fd, b"1")
                os.close(write_fd)
                write_fd = -1
                while process.poll() is None:
                    state = self.store.load()
                    if state["stop_requested"]:
                        raise Error("Auftrag durch Nutzer angehalten.")
                    if time.monotonic() - started > config["timeout_seconds"]:
                        raise Error("Zeitlimit erreicht; Prozess wird beendet.")
                    time.sleep(0.2)
                return {"exit_code": process.returncode,
                        "stdout": (output_dir / "stdout.log").read_text(errors="replace"),
                        "stderr": (output_dir / "stderr.log").read_text(errors="replace"),
                        "seconds": round(time.monotonic() - started, 3)}
        finally:
            if read_fd >= 0:
                os.close(read_fd)
            if write_fd >= 0:
                os.close(write_fd)
            if process:
                stop_process(process)

    def prompt(self, role, state, run, checks, discussion=None):
        instructions = (PACKAGE / "skills" / role / "SKILL.md").read_text()
        if role == "generator":
            instructions += "\n\n" + (PACKAGE / "references/delegation.md").read_text()
        rules = []
        for name in ("AGENTS.md", "CLAUDE.md"):
            path = self.store.root / name
            if path.is_file():
                rules.append(f"## {name}\n{path.read_text()}")
        context = {"mission_id": self.store.id, "run_id": run["id"],
                   "role": role, "spec_revision": state["spec"]["revision"],
                   "workspace": run.get("workspace"), "fingerprint": run.get("fingerprint"),
                   "profile": "edit" if role == "generator" else "verify",
                   "result_schema": result_schema(role),
                   "spec_hash": state["spec"]["hash"], "goal": state["goal"],
                   "contract": state["spec"]["contract"], "checks": checks,
                   "feedback": state.get("feedback"), "discussion": discussion}
        if role == "generator" and run.get("delegation"):
            context["delegation"] = run["delegation"]
        if role == "generator" and state.get("last_evaluation"):
            context["findings"] = state["last_evaluation"]
        return (instructions + "\n\n# Handover\n\n" + "\n\n".join(rules)
                + "\n\n## Spec\n" + (self.store.doc / "Spec.md").read_text()
                + "\n\n## Maschinenvertrag\n" + json.dumps(context, ensure_ascii=False)
                + "\n\nLiefere ausschließlich das Ergebnis nach dem JSON-Schema. "
                  "run_id und spec_hash exakt übernehmen. Kein Commit, Push, Merge oder Deployment. "
                  "Das Arbeitsverzeichnis ist ein Snapshot. Erhalte fremde Änderungen.\n")

    def agent(self, role, state, run, directory, workspace, adapter, config, checks, discussion=None):
        scratch = directory / "scratch"
        scratch.mkdir(parents=True)
        schema_path = directory / "schema.json"
        schema = result_schema(role)
        write_json(directory / "adapter.json", adapter)
        write_json(schema_path, schema)
        output = scratch / "result.json"
        team = delegation.prepare(adapter, directory / "agents", "edit") if role == "generator" else None
        if team:
            run["delegation"] = team
        argv = transport.command(adapter, workspace, schema_path, output,
                                 "edit" if role == "generator" else "verify", **({"delegation": team} if team else {}))
        full = transport.sandbox(workspace, scratch, argv,
                                 "edit" if role == "generator" else "verify", **({"runtime_home": True} if team else {}))
        label = "Umsetzung" if role == "generator" else "Abgleich" if discussion else "Unabhängige Prüfung"
        label = f'Runde {state["round"]}: {label}'
        with activity.Call(adapter, directory, state["goal"], role, label, self.store, run["id"]) as trace:
            execution = self.execute_child(run, full, self.prompt(role, state, run, checks, discussion),
                                           directory, config)
            trace.stdout = execution["stdout"]
            write_json(directory / "execution.json", {k: v for k, v in execution.items() if k != "stdout"})
            if team:
                observed = {"events": delegation.events(execution["stdout"]),
                            "models": delegation.observed_models(scratch, execution["stdout"])}
                write_json(directory / "delegation-events.json", observed)
                run["delegation_observed"] = observed
            if execution["exit_code"]:
                raise Error(f'{adapter["target"]} endete mit Exit {execution["exit_code"]}; '
                            f'Protokoll: {directory / "stderr.log"}')
            result = transport.decode(adapter, execution["stdout"], output)
            try:
                jsonschema.validate(result, schema)
            except jsonschema.ValidationError as exc:
                raise Error("Ergebnis verletzt das Schema: " + exc.message) from exc
            validate_result(result, role, state, run)
            write_json(directory / "result.json", result)
            trace.result = result
        run.setdefault("model_activity", []).extend(trace.entries)
        return result

    def checks(self, state, run, directory, baseline, config):
        results = []
        for check in state["spec"]["contract"]["checks"]:
            target = directory / "checks" / check["id"]
            work = snapshot.capture(self.store.root, target / "workspace", baseline)
            argv = transport.sandbox(work, target / "scratch", check["argv"], "edit", auth=False,
                                     nix_daemon=config.get("check_nix_daemon", False))
            env = {k: v for k, v in transport.environment().items() if not k.endswith("API_KEY")}
            version_argv = transport.sandbox(work, target / "version/scratch",
                [check["argv"][0], "--version"], "verify", auth=False)
            version = self.execute_child(run, version_argv, "", target / "version", config, env)
            outcome = self.execute_child(run, argv, "", target, config, env)
            results.append({"id": check["id"], "argv": check["argv"],
                            "tool_version": version, **outcome})
        return results

    def one(self, expected):
        with lock(self.store.run_lock):
            state = self.store.load()
            if state["revision"] != expected:
                raise Error("Veraltete Revision; status neu lesen.")
            if state["activity"] != "idle" or state["stop_requested"]:
                raise Error("Mission ist nicht startbereit; status/resume verwenden.")
            if state["phase"] not in ("implementing", "evaluating"):
                return state
            self.store.check_spec(state)
            if not state["authorization"] or state["authorization"]["spec_hash"] != state["spec"]["hash"]:
                raise Error("Umsetzungsautorisierung passt nicht zur Spec.")
            config = state.get("configuration") or self.store.config()
            role = "generator" if state["phase"] == "implementing" else "evaluator"
            if role == "generator" and state["round"] >= config["max_rounds"] + state.get("extra_rounds", 0):
                def exhausted(current):
                    current.update(activity="blocked", blocker="Rundenbudget erreicht; Erweiterung benötigt Nutzerauftrag.")
                return self.store.change(expected, "budget_exhausted", exhausted)
            with lock(self.store.edit_lock):
                run = {"id": uuid.uuid4().hex, "role": role, "status": "prepared",
                       "owner": identity(os.getpid()), "child": None, "created_at": now(),
                       "spec_hash": state["spec"]["hash"], "retry_of": None}
                if state["runs"] and state["runs"][-1]["status"] in ("failed", "interrupted"):
                    run["retry_of"] = state["runs"][-1]["id"]
                def claim(current):
                    current.setdefault("configuration", config)
                    if role == "generator":
                        limit = config["max_rounds"] + current.get("extra_rounds", 0)
                        if current["round"] >= limit:
                            raise Error("Rundenbudget erreicht; begründete Erweiterung über resume erforderlich.")
                        current["round"] += 1
                    current["runs"].append(run)
                    current.update(activity="running", blocker=None)
                state = self.store.change(expected, "run_prepared", claim)
                directory = self.store.local / "runs" / run["id"]
                directory.mkdir(parents=True, mode=0o700)
                try:
                    if role == "generator":
                        owned = set(state["authorization"]["include_dirty"])
                        for old in state["runs"]:
                            owned.update(old.get("changed_files", []))
                        write_preflight(self.store.root, state["spec"]["contract"]["allowed_paths"], owned)
                    transport.check_sandbox()
                    adapter = self.adapter(role, config[role], config)
                    write_json(directory / "adapter.json", adapter)
                    baseline = fingerprint(self.store.root)
                    run.update(fingerprint=baseline["hash"], workspace=str(directory / "workspace"))
                    write_json(directory / "baseline.json", baseline)
                    workspace = snapshot.capture(self.store.root, directory / "workspace", baseline)
                    checks = self.checks(state, run, directory, baseline, config) if role == "evaluator" else []
                    generator_report = None
                    if role == "evaluator":
                        for previous in reversed(state["runs"]):
                            if previous.get("role") == "generator" and previous["status"] == "succeeded":
                                generator_report = read_json(self.store.root / previous["report"])["result"]
                                break
                    results = []
                    adapters = [adapter]
                    if role == "evaluator" and config["second_opinion"]:
                        second = self.adapter("second_evaluator",
                            "claude" if adapter["target"] == "codex" else "codex", {**config, "model": None})
                        adapters.append(second)
                        discussion = None
                        for number in range(config["max_discussions"] + 1):
                            results = [self.agent(role, state, run, directory / f"opinion-{number}-a",
                                                 workspace, adapter, config, checks, discussion),
                                       self.agent(role, state, run, directory / f"opinion-{number}-b",
                                                  workspace, second, config, checks, discussion)]
                            signatures = [(sorted((c["id"], c["status"]) for c in r["criteria"]),
                                           sorted((f["id"], f["criterion"], f["severity"]) for f in r["findings"]
                                                  if f["severity"] in ("high", "medium"))) for r in results]
                            if number > 0 and signatures[0] == signatures[1]:
                                break
                            discussion = {"independent_reviews": results, "generator_report": generator_report,
                                          "previous_evaluation": state.get("last_evaluation")}
                        else:
                            raise Error("Prüfer bleiben uneinig; Meinungen und Belege liegen im Run-Verzeichnis.")
                        result = dict(results[0])
                        findings = {}
                        for opinion in results:
                            for finding in opinion["findings"]:
                                key = (finding["id"], finding["criterion"], finding["severity"])
                                if key not in findings:
                                    findings[key] = dict(finding)
                                elif finding != findings[key]:
                                    findings[key]["description"] += "\nZweite Bewertung: " + finding["description"]
                                    findings[key]["evidence"] += "\nZweiter Beleg: " + finding["evidence"]
                        result["findings"] = list(findings.values())
                        used = set()
                        for finding in result["findings"]:
                            while finding["id"] in used:
                                finding["id"] = "b-" + finding["id"]
                            used.add(finding["id"])
                    else:
                        result = self.agent(role, state, run, directory / "primary", workspace,
                                            adapter, config, checks)
                        results = [result]
                        if role == "evaluator":
                            result = self.agent(role, state, run, directory / "reconciliation", workspace,
                                adapter, config, checks, {"independent_reviews": results,
                                "generator_report": generator_report,
                                "previous_evaluation": state.get("last_evaluation")})
                            results.append(result)
                    self.check_stop()
                    if fingerprint(self.store.root)["hash"] != baseline["hash"]:
                        raise Error("Arbeitsstand während des Auftrags verändert; Ergebnis ist veraltet.")
                    changed = []
                    if role == "generator":
                        changed = snapshot.apply(self.store.root, workspace, baseline,
                            state["spec"]["contract"]["allowed_paths"], directory / "apply.json", self.check_stop)
                        if set(result["changed_files"]) != set(changed):
                            result["reported_changed_files"] = result["changed_files"]
                        result["changed_files"] = changed
                    elif result["verdict"] == "PASS" and any(c["exit_code"] for c in checks):
                        raise Error("PASS trotz fehlgeschlagener Pflichtprüfung zurückgewiesen.")
                    result["fingerprint"] = (fingerprint(self.store.root)["hash"] if role == "generator"
                                             else baseline["hash"])
                    report = {"result": result, "opinions": results, "checks": checks,
                              "adapter": adapter, "run_id": run["id"], "spec_hash": state["spec"]["hash"],
                              "adapters": adapters, "generator_report": generator_report,
                              "delegation_observed": run.get("delegation_observed"),
                              "model_activity": run.get("model_activity", []),
                              "handover": self.prompt(role, state, run, checks)}
                    document = self.store.doc / "rounds" / str(state["round"]) / f'{role}-{run["id"]}.json'
                    write_json(document, report)
                    atomic(document.with_suffix(".md"), "# Arbeitsrunde\n\n" + result["summary"]
                           + "\n\n## Modelle und Aufgaben\n\n" + activity.table(report["model_activity"])
                           + "\n\n```json\n" + json.dumps(report, ensure_ascii=False, indent=2) + "\n```\n")
                    def finish(current):
                        if current["stop_requested"]:
                            raise Error("Auftrag vor Zustandsübergabe angehalten.")
                        self.store.check_spec(current)
                        if role == "evaluator" and fingerprint(self.store.root)["hash"] != baseline["hash"]:
                            raise Error("Prüfstand vor Zustandsübergabe verändert.")
                        active = current["runs"][-1]
                        if active["id"] != run["id"]:
                            raise Error("Ergebnis gehört nicht zum aktiven Run.")
                        active.update(status="succeeded", ended_at=now(), changed_files=changed,
                                      report=str(document.relative_to(self.store.root)),
                                      report_hash=digest(document.read_bytes()), adapter=adapter)
                        current.update(activity="idle", blocker=None)
                        if role == "generator":
                            current.update(phase="evaluating", evaluation=None)
                        else:
                            current["last_evaluation"] = result
                            if result["verdict"] == "PASS":
                                current.update(phase="awaiting_acceptance", evaluation=result)
                            elif result["verdict"] == "FAIL":
                                current.update(phase="implementing", evaluation=None)
                            else:
                                current.update(activity="blocked", blocker=result["summary"], evaluation=None)
                    return self.store.change(None, "run_completed", finish)
                except (Error, OSError, ValueError, subprocess.SubprocessError) as exc:
                    def fail(current):
                        active = current["runs"][-1]
                        stop = current["stop_requested"]
                        status = "cancelled" if stop == "cancel" else "interrupted" if stop else "failed"
                        active.update(status=status, ended_at=now(), error=str(exc))
                        current.update(activity="paused" if stop == "pause" else "blocked", blocker=str(exc))
                        if stop == "cancel":
                            current.update(phase="cancelled", activity="idle")
                    self.store.change(None, "run_stopped", fail)
                    raise Error(str(exc)) from exc

    def run(self, expected, once=False):
        while True:
            state = self.one(expected)
            if once or state["activity"] != "idle" or state["phase"] not in ("implementing", "evaluating"):
                return state
            expected = state["revision"]
