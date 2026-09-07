import json
import os
from pathlib import Path
import subprocess
import uuid

from common import Error, fingerprint, identity, lock, now, read_json, write_json
from runner import Runner
from state import spec_review_source
import snapshot
import transport
import activity

PACKAGE = Path(__file__).resolve().parents[1]


def review_spec(store, expected, planner=None):
    runner = Runner(store)
    with lock(store.run_lock), lock(store.edit_lock):
        state = store.load()
        if state["revision"] != expected:
            raise Error("Veraltete Revision; status neu lesen.")
        if state["phase"] != "awaiting_spec" or state["activity"] != "idle" or state["stop_requested"]:
            raise Error("Spec-Gegenprüfung benötigt eine vorgelegte, nicht angehaltene Spec; status/resume prüfen.")
        store.idle(state)
        store.check_spec(state)
        run_id = uuid.uuid4().hex
        source = spec_review_source(state, run_id, fingerprint(store.root)["hash"], planner)
        run = {"id": run_id, "role": "spec_reviewer", "status": "prepared",
               "owner": identity(os.getpid()), "child": None, "created_at": now(),
               "spec_hash": source["spec_hash"], "retry_of": None}
        if state["runs"] and state["runs"][-1].get("role") == "spec_reviewer" and state["runs"][-1]["status"] in ("failed", "interrupted"):
            run["retry_of"] = state["runs"][-1]["id"]

        def prepare(current):
            if not current.get("planner_cli"):
                current["planner_cli_inferred"] = planner is None
            current["planner_cli"] = source["planner_cli"]
            current["runs"].append(run)
            current.update(activity="running", blocker=None, spec_review=None)

        state = store.change(expected, "spec_review_prepared", prepare)
        directory = store.local / "runs" / run_id
        try:
            directory.mkdir(parents=True, mode=0o700)
            config = store.config()
            transport.check_sandbox()
            adapter = transport.resolve(source["reviewer_cli"], None, config["effort"])
            if adapter["target"] != source["reviewer_cli"]:
                raise Error("Spec-Gegenprüfung muss die andere CLI verwenden.")
            write_json(directory / "adapter.json", adapter)
            baseline = fingerprint(store.root)
            if baseline["hash"] != source["fingerprint"]:
                raise Error("Projekt vor Beginn der Spec-Gegenprüfung verändert.")
            write_json(directory / "baseline.json", baseline)
            workspace = snapshot.capture(store.root, directory / "workspace", baseline)
            scratch = directory / "scratch"
            scratch.mkdir()
            schema = read_json(PACKAGE / "schemas/spec_reviewer.json")
            schema_path = directory / "schema.json"
            write_json(schema_path, schema)
            context = {**source, "role": "spec_reviewer", "profile": "inspect",
                       "workspace": str(workspace), "result_schema": schema,
                       "goal": state["goal"], "contract": state["spec"]["contract"]}
            instructions = (PACKAGE / "skills/spec_reviewer/SKILL.md").read_text()
            rules = []
            for name in ("AGENTS.md", "CLAUDE.md"):
                path = store.root / name
                if path.is_file():
                    rules.append(f"## {name}\n{path.read_text()}")
            handover = (instructions + "\n\n# Projektregeln\n\n" + "\n\n".join(rules)
                        + "\n\n# Spec\n\n" + (store.doc / "Spec.md").read_text()
                        + "\n\n## Maschinenvertrag\n" + json.dumps(context, ensure_ascii=False))
            output = scratch / "result.json"
            argv = transport.command(adapter, workspace, schema_path, output, "inspect")
            command = transport.sandbox(workspace, scratch, argv, "inspect")
            with activity.Call(adapter, directory, state["goal"], "spec_reviewer",
                               "Spec-Gegenprüfung", store, run_id) as trace:
                execution = runner.execute_child(run, command, handover, directory, config)
                trace.stdout = execution["stdout"]
                write_json(directory / "execution.json", {key: value for key, value in execution.items() if key != "stdout"})
                if execution["exit_code"]:
                    raise Error(f'Spec-Gegenprüfung endete mit Exit {execution["exit_code"]}; Protokoll: {directory / "stderr.log"}')
                result = transport.decode(adapter, execution["stdout"], output)
                write_json(directory / "result.json", result)
                runner.check_stop()
                from state import spec_review_score
                spec_review_score(result, source, adapter)
                trace.result = result
            return store.record_spec_review(result, adapter, source, None, run_id=run_id)
        except (Error, OSError, ValueError, subprocess.SubprocessError) as exc:
            def failed(current):
                active = current["runs"][-1]
                if active["id"] != run_id:
                    raise Error("Spec-Gegenprüfung gehört nicht mehr zum aktiven Run.")
                stop = current["stop_requested"]
                active.update(status="cancelled" if stop == "cancel" else "interrupted" if stop else "failed",
                              ended_at=now(), error=str(exc))
                current.update(activity="paused" if stop == "pause" else "blocked", blocker=str(exc))
                if stop == "cancel":
                    current.update(phase="cancelled", activity="idle")
            store.change(None, "spec_review_stopped", failed)
            raise Error(str(exc)) from exc
