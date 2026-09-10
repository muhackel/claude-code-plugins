import copy
import json
import os
from pathlib import Path
import uuid

import jsonschema

from common import (Error, alive, atomic, digest, fingerprint, identifier, inside, lock,
                    now, project, read_json, relative, write_json)

PHASES = {"planning", "awaiting_spec", "implementing", "evaluating", "awaiting_acceptance",
          "completed", "cancelled"}
TERMINAL = {"completed", "cancelled"}
DEFAULTS = {"schema_version": 1, "max_rounds": 3, "max_discussions": 3,
            "timeout_seconds": 1800, "generator": "auto", "evaluator": "auto",
            "second_opinion": False, "model": None, "effort": None, "check_nix_daemon": False}
SCHEMAS = Path(__file__).resolve().parents[1] / "schemas"
STATE_VALIDATOR = jsonschema.Draft7Validator(read_json(SCHEMAS / "state.json"))
CONTRACT_VALIDATOR = jsonschema.Draft7Validator(read_json(SCHEMAS / "contract.json"))
SPEC_REVIEW_VALIDATOR = jsonschema.Draft7Validator(read_json(SCHEMAS / "spec_reviewer.json"))
SPEC_POINTS = {"coverage": 25, "verification": 25, "scope": 20, "evidence": 15, "risks": 15}


def current_cli():
    return "claude" if os.environ.get("CLAUDECODE") else "codex"


def contract_hash(contract):
    return digest(json.dumps(contract, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":")).encode())


def spec_review_source(state, run_id, project_hash, planner=None):
    owner = state.get("planner_cli") or planner or current_cli()
    if owner not in ("claude", "codex"):
        raise Error("Planer-CLI muss claude oder codex sein.")
    if planner and planner != owner:
        raise Error("Planer-CLI widerspricht der gespeicherten Missionszuordnung.")
    return {"mission_id": state["mission_id"], "run_id": run_id,
            "planner_cli": owner, "reviewer_cli": "codex" if owner == "claude" else "claude",
            "spec_revision": state["spec"]["revision"], "spec_hash": state["spec"]["hash"],
            "contract_hash": contract_hash(state["spec"]["contract"]), "fingerprint": project_hash}


def spec_review_score(result, source, adapter):
    try:
        SPEC_REVIEW_VALIDATOR.validate(result)
    except jsonschema.ValidationError as exc:
        raise Error("Spec-Gegenreview verletzt das Schema: " + exc.message) from exc
    for key in ("run_id", "spec_revision", "spec_hash", "contract_hash", "fingerprint"):
        if result[key] != source[key]:
            raise Error(f"Spec-Gegenreview gehört zu einem anderen Prüfstand: {key}.")
    if adapter.get("target") != source["reviewer_cli"] or adapter.get("target") == source["planner_cli"]:
        raise Error("Spec-Gegenreview muss von der anderen CLI stammen.")
    texts = [result["summary"], *result["questions"]]
    for item in result["scores"].values():
        texts.extend((item["reason"], item["evidence"]))
    ids = set()
    for blocker in result["blockers"]:
        if blocker["id"] in ids:
            raise Error("Doppelte Blocker-ID im Spec-Gegenreview.")
        ids.add(blocker["id"])
        texts.extend(blocker.values())
    if any(not text.strip() for text in texts):
        raise Error("Spec-Gegenreview benötigt konkrete Begründungen und Belege.")
    return sum(result["scores"][key]["points"] for key in SPEC_POINTS)


def contract_valid(value):
    try:
        CONTRACT_VALIDATOR.validate(value)
    except jsonschema.ValidationError as exc:
        raise Error("Vertrag verletzt das Schema: " + exc.message) from exc
    if not isinstance(value, dict) or set(value) != {"criteria", "allowed_paths", "checks"}:
        raise Error("Vertrag benötigt genau criteria, allowed_paths und checks.")
    ids = set()
    if not isinstance(value["criteria"], list) or not value["criteria"]:
        raise Error("Mindestens ein Abnahmekriterium ist erforderlich.")
    for criterion in value["criteria"]:
        if not isinstance(criterion, dict) or set(criterion) != {"id", "description", "verification"}:
            raise Error("Kriterium benötigt id, description und verification.")
        if any(not isinstance(v, str) or not v.strip() for v in criterion.values()):
            raise Error("Kriterienfelder dürfen nicht leer sein.")
        identifier(criterion["id"])
        if criterion["id"] in ids:
            raise Error("Doppelte Kriterien-ID.")
        ids.add(criterion["id"])
    if not isinstance(value["allowed_paths"], list) or not value["allowed_paths"]:
        raise Error("Konkrete Schreibpfade erforderlich.")
    for path in value["allowed_paths"]:
        relative(path)
    check_ids = set()
    if not isinstance(value["checks"], list):
        raise Error("checks muss eine Liste sein.")
    for check in value["checks"]:
        if not isinstance(check, dict) or set(check) != {"id", "argv"}:
            raise Error("Prüfung benötigt id und argv.")
        identifier(check["id"])
        if check["id"] in check_ids:
            raise Error("Doppelte Prüfungs-ID.")
        check_ids.add(check["id"])
        if not isinstance(check["argv"], list) or not check["argv"] or any(
                not isinstance(x, str) or not x for x in check["argv"]):
            raise Error("Prüfbefehl muss eine nicht leere argv-Liste sein.")
        if check["argv"][0] not in ("nix", "nix-shell"):
            raise Error("Prüfungen müssen mit nix oder nix-shell beginnen.")
    return value


class Store:
    def __init__(self, root, mission):
        self.root = project(root)
        self.id = identifier(mission)
        self.base = self.root / ".philharmonie"
        self.doc = self.base / "missions" / self.id
        self.local = self.base / "local" / self.id
        self.path = self.local / "state.json"
        self.state_lock = self.base / "local/locks" / f"{self.id}.state"
        self.run_lock = self.base / "local/locks" / f"{self.id}.run"
        self.edit_lock = self.base / "local/locks/checkout.edit"
        for folder in (self.doc, self.local, self.state_lock.parent):
            for item in (folder, *folder.parents):
                if item == self.root:
                    break
                if item.is_symlink():
                    raise Error(f"Symlink im Zustandspfad: {item}")

    def load(self):
        state = read_json(self.path)
        try:
            STATE_VALIDATOR.validate(state)
        except jsonschema.ValidationError as exc:
            raise Error("Zustand verletzt das Schema: " + exc.message) from exc
        if state.get("schema_version") != 1 or state.get("mission_id") != self.id:
            raise Error("Unbekanntes oder unpassendes Zustandsschema.")
        if state.get("project") != str(self.root) or state.get("phase") not in PHASES:
            raise Error("Zustand gehört nicht zu diesem Checkout.")
        return state

    def config(self):
        config = read_json(self.base / "config.json")
        if set(config) != set(DEFAULTS) or config["schema_version"] != 1:
            raise Error("Unbekanntes Konfigurationsschema.")
        for key in ("max_rounds", "max_discussions", "timeout_seconds"):
            if type(config[key]) is not int or config[key] < 1:
                raise Error(f"Ungültige Grenze: {key}")
        for role in ("generator", "evaluator"):
            if config[role] not in ("auto", "claude", "codex"):
                raise Error(f"Ungültiges CLI-Ziel für {role}")
        for option in ("second_opinion", "check_nix_daemon"):
            if type(config[option]) is not bool:
                raise Error(f"{option} muss boolean sein.")
        if config["model"] is not None and (not isinstance(config["model"], str) or not config["model"].strip()):
            raise Error("model muss ein nicht leerer Name oder null sein.")
        if config["effort"] is not None and (not isinstance(config["effort"], str) or not config["effort"].strip()):
            raise Error("effort muss ein nicht leerer Name oder null sein.")
        return config

    def create(self, goal, previous=None, planner=None):
        if not goal.strip():
            raise Error("Ein Ziel ist erforderlich.")
        planner = planner or current_cli()
        if planner not in ("claude", "codex"):
            raise Error("Planer-CLI muss claude oder codex sein.")
        with lock(self.state_lock):
            if self.path.exists() or self.doc.exists():
                raise Error("Mission existiert bereits; neuen Namen oder resume verwenden.")
            self.doc.mkdir(parents=True)
            self.local.mkdir(parents=True, mode=0o700)
            if not (self.base / "config.json").exists():
                write_json(self.base / "config.json", DEFAULTS)
            atomic(self.base / "local/.gitignore", "*\n!.gitignore\n")
            atomic(self.doc / "Spec.md", f"# Spezifikation\n\n## Nutzerauftrag\n\n{goal}\n")
            atomic(self.doc / "Decisions.md", "# Entscheidungen\n")
            state = {"schema_version": 1, "mission_id": self.id, "project": str(self.root),
                     "phase": "planning", "activity": "idle", "revision": 0, "goal": goal,
                     "previous_mission": previous, "planner_cli": planner,
                     "spec": None, "spec_review": None, "authorization": None,
                     "round": 0, "runs": [], "evaluation": None, "blocker": None,
                     "stop_requested": None, "events": [], "created_at": now()}
            self.save(state, "created")
            return state

    def save(self, state, event, detail=None):
        state["revision"] += 1
        state["events"].append({"revision": state["revision"], "event": event,
                                "at": now(), "detail": detail})
        try:
            STATE_VALIDATOR.validate(state)
        except jsonschema.ValidationError as exc:
            raise Error("Neuer Zustand verletzt das Schema: " + exc.message) from exc
        if state["phase"] in TERMINAL and (state["activity"] != "idle" or any(
                r["status"] in ("prepared", "running") for r in state["runs"])):
            raise Error("Abgeschlossene Mission darf keinen aktiven Run besitzen.")
        write_json(self.path, state)

    def change(self, expected, event, action):
        with lock(self.state_lock):
            state = self.load()
            if expected is not None and state["revision"] != expected:
                raise Error("Veraltete Revision; status neu lesen.")
            if state["phase"] in TERMINAL:
                raise Error("Mission ist abgeschlossen; Folgemission anlegen.")
            action(state)
            self.save(state, event)
            return state

    def idle(self, state):
        if state["activity"] == "running" or any(
                r["status"] in ("prepared", "running") for r in state["runs"]):
            raise Error("Ein Auftrag läuft; zuerst pause und resume verwenden.")

    def check_spec(self, state):
        spec = state["spec"]
        if not spec or digest((self.doc / "Spec.md").read_bytes()) != spec["hash"]:
            raise Error("Spec fehlt oder wurde außerhalb des Zustandskerns verändert.")
        archived = self.doc / "specs" / f'{spec["revision"]}.md'
        if digest(archived.read_bytes()) != spec["hash"]:
            raise Error("Archivierte Spec wurde verändert.")
        if read_json(archived.with_suffix(".json")) != spec["contract"]:
            raise Error("Archivierter Vertrag wurde verändert.")
        return spec

    def set_spec(self, markdown, contract, expected):
        contract_valid(contract)
        if not markdown.strip():
            raise Error("Spec ist leer.")
        def action(state):
            self.idle(state)
            if state["phase"] not in ("planning", "awaiting_spec"):
                raise Error("Für Scope-Änderungen zuerst replan verwenden.")
            version = (state["spec"] or {}).get("revision", 0) + 1
            atomic(self.doc / "Spec.md", markdown)
            atomic(self.doc / "specs" / f"{version}.md", markdown)
            write_json(self.doc / "specs" / f"{version}.json", contract)
            state["spec"] = {"revision": version, "hash": digest(markdown.encode()),
                             "contract": copy.deepcopy(contract)}
            state.update(phase="awaiting_spec", activity="idle", evaluation=None,
                         authorization=None, blocker=None, spec_review=None)
        return self.change(expected, "spec_submitted", action)

    def record_spec_review(self, result, adapter, source, expected, run_id=None):
        score = spec_review_score(result, source, adapter)
        def action(state):
            if state["phase"] != "awaiting_spec":
                raise Error("Keine Spec zur Gegenprüfung vorhanden.")
            if state["stop_requested"]:
                raise Error("Spec-Gegenprüfung wurde angehalten.")
            if run_id:
                active = state["runs"][-1] if state["runs"] else None
                if not active or active["id"] != run_id or active.get("role") != "spec_reviewer" or active["status"] not in ("prepared", "running"):
                    raise Error("Spec-Gegenreview gehört nicht zum aktiven Prüfauftrag.")
                if source["run_id"] != run_id:
                    raise Error("Spec-Gegenreview trägt eine andere Run-ID.")
            else:
                self.idle(state)
            self.check_spec(state)
            current = spec_review_source(state, source["run_id"], fingerprint(self.root)["hash"],
                                         source["planner_cli"])
            if current != source:
                raise Error("Spec, Vertrag oder Projekt seit Beginn der Gegenprüfung verändert.")
            report = self.doc / "specs" / f'{source["spec_revision"]}-review-{identifier(source["run_id"])}.json'
            payload = {"result": result, "score": score, "maximum": sum(SPEC_POINTS.values()),
                       "source": source, "adapter": adapter,
                       "model_activity": active.get("model_activity", []) if run_id else []}
            write_json(report, payload)
            lines = ["# Spec-Gegenprüfung", "", result["summary"], "",
                     f'Score: {score}/100. Planer: {source["planner_cli"]}; Gegenprüfung: {adapter["target"]}.', ""]
            for key, maximum in SPEC_POINTS.items():
                entry = result["scores"][key]
                lines.append(f'- {key}: {entry["points"]}/{maximum}. {entry["reason"]} Beleg: {entry["evidence"]}')
            lines += ["", "## Blocker", ""]
            lines += [f'- {item["id"]}: {item["reason"]} Beleg: {item["evidence"]}' for item in result["blockers"]] or ["Keine."]
            lines += ["", "## Offene Fragen und Entscheidungen", ""]
            lines += [f"- {question}" for question in result["questions"]] or ["Keine."]
            from activity import table
            lines += ["", "## Modelle und Aufgaben", "", table(payload["model_activity"])]
            atomic(report.with_suffix(".md"), "\n".join(lines) + "\n")
            registered = {"score": score, "maximum": 100, "source": copy.deepcopy(source),
                          "reviewer_cli": adapter["target"], "blockers": copy.deepcopy(result["blockers"]),
                          "questions": list(result["questions"]), "at": now(),
                          "report": str(report.relative_to(self.root)), "report_hash": digest(report.read_bytes())}
            if not state.get("planner_cli"):
                state["planner_cli_inferred"] = True
            state.update(planner_cli=source["planner_cli"], spec_review=registered,
                         activity="idle", blocker=None)
            if run_id:
                active.update(status="succeeded", ended_at=now(), report=registered["report"],
                              report_hash=registered["report_hash"], adapter=adapter)
        return self.change(expected, "spec_reviewed", action)

    def check_spec_review(self, state):
        self.check_spec(state)
        review = state.get("spec_review")
        if not review:
            raise Error("Aktueller Spec-Gegenreview fehlt; zuerst review-spec ausführen.")
        source = review.get("source", {})
        current = spec_review_source(state, source.get("run_id"), fingerprint(self.root)["hash"])
        if current != source:
            raise Error("Spec-Gegenreview ist für diese Spec, diesen Vertrag oder Projektstand veraltet.")
        stored_path = Path(review["report"])
        if stored_path.is_absolute() or ".." in stored_path.parts:
            raise Error("Ungültiger Berichtspfad der Spec-Gegenprüfung.")
        report = self.root / stored_path
        if not report.resolve().is_relative_to(self.doc.resolve()) or report.is_symlink() or not report.is_file():
            raise Error("Registrierter Spec-Gegenreview fehlt oder liegt außerhalb der Mission.")
        if digest(report.read_bytes()) != review.get("report_hash"):
            raise Error("Bericht der Spec-Gegenprüfung wurde verändert.")
        payload = read_json(report)
        if payload.get("source") != source:
            raise Error("Quelle der Spec-Gegenprüfung widerspricht dem registrierten Prüfstand.")
        score = spec_review_score(payload["result"], source, payload["adapter"])
        if score != review.get("score") or score != payload.get("score") or review.get("reviewer_cli") != source["reviewer_cli"]:
            raise Error("Registrierter Spec-Score oder Reviewer widerspricht dem Gegenreview.")
        if payload["result"]["blockers"] != review.get("blockers") or payload["result"]["questions"] != review.get("questions"):
            raise Error("Registrierte Blocker oder Fragen widersprechen dem Gegenreview.")
        if review["blockers"]:
            raise Error("Spec-Gegenprüfung enthält offene Blocker: " + "; ".join(item["reason"] for item in review["blockers"]))
        return review

    def approve(self, authorization, expected, include_dirty=()):
        if not authorization.strip():
            raise Error("Wortlaut der vorhandenen Nutzerautorisierung erforderlich.")
        def action(state):
            self.idle(state)
            if state["phase"] != "awaiting_spec":
                raise Error("Keine Spec zur Freigabe vorhanden.")
            spec = self.check_spec(state)
            self.check_spec_review(state)
            state["authorization"] = {"text": authorization, "spec_hash": spec["hash"],
                                      "at": now(), "include_dirty": list(include_dirty)}
            atomic(self.doc / "Decisions.md", (self.doc / "Decisions.md").read_text()
                   + f'\n## Spec {spec["revision"]}\n\n{authorization}\n')
            state.update(phase="implementing", activity="idle", blocker=None)
        with lock(self.edit_lock):
            return self.change(expected, "authorized", action)

    def replan(self, reason, expected):
        if not reason.strip():
            raise Error("Änderungsauftrag erforderlich.")
        def action(state):
            self.idle(state)
            state.update(phase="planning", activity="idle", authorization=None,
                         evaluation=None, blocker=None, stop_requested=None, spec_review=None)
            state.pop("configuration", None)
            state.pop("adapters", None)
            atomic(self.doc / "Decisions.md", (self.doc / "Decisions.md").read_text()
                   + f"\n## Neue Planung\n\n{reason}\n")
        return self.change(expected, "replan", action)

    def feedback(self, text, expected):
        if not text.strip():
            raise Error("Korrekturauftrag erforderlich.")
        def action(state):
            self.idle(state)
            if state["phase"] != "awaiting_acceptance":
                raise Error("Kein Ergebnis zur Abnahme vorhanden.")
            state.update(phase="implementing", evaluation=None, feedback=text)
            atomic(self.doc / "Decisions.md", (self.doc / "Decisions.md").read_text()
                   + f"\n## Korrekturauftrag\n\n{text}\n")
        return self.change(expected, "feedback", action)

    def accept(self, authorization, expected):
        if not authorization.strip():
            raise Error("Nutzerabnahme im Wortlaut erforderlich.")
        def action(state):
            self.idle(state)
            self.check_spec(state)
            if state["phase"] != "awaiting_acceptance" or not state["evaluation"]:
                raise Error("Kein geprüftes Ergebnis zur Abnahme vorhanden.")
            evaluation = state["evaluation"]
            if evaluation["fingerprint"] != fingerprint(self.root)["hash"]:
                raise Error("Projekt seit der Prüfung verändert; erneut evaluieren.")
            reports = [r for r in state["runs"] if r["status"] == "succeeded"]
            if not reports:
                raise Error("Dauerhafter Prüfbericht fehlt.")
            for run in reports:
                report = self.root / run["report"]
                if not report.is_relative_to(self.doc) or report.is_symlink() or not report.is_file():
                    raise Error("Registrierter Rundenbericht fehlt oder liegt außerhalb der Mission.")
                if digest(report.read_bytes()) != run.get("report_hash"):
                    raise Error("Rundenbericht seit der Registrierung verändert.")
            lines = ["# Abschluss", "", state["goal"], "", "## Bestätigt", ""]
            for result in evaluation["criteria"]:
                lines.append(f'- {result["id"]}: {result["reason"]} Beleg: {result["evidence"]}')
            lines += ["", "## Nicht bestätigt", "", "Keine offenen Pflichtkriterien.", "",
                      "## Weitere Hinweise", ""]
            for finding in evaluation["findings"]:
                lines.append(f'- {finding["id"]}: {finding["description"]} Beleg: {finding["evidence"]}')
            for run in reversed(reports):
                if run.get("role") == "generator":
                    generator = read_json(self.root / run["report"])["result"]
                    for item in generator.get("unconfirmed", []):
                        lines.append(f'- Vom Generator nicht bestätigt: {item}. Einordnung im Evaluationsbericht.')
                    break
            lines += ["", "## Prüfberichte", ""]
            lines.extend(f'- [{run["id"]}]({Path(run["report"]).relative_to(self.doc.relative_to(self.root))})'
                         for run in reports)
            lines += ["", "## Abnahme", "", authorization, "",
                      f'Prüfstand: `{evaluation["fingerprint"]}`; Spec: `{state["spec"]["hash"]}`.']
            atomic(self.doc / "Summary.md", "\n".join(lines) + "\n")
            state.update(phase="completed", activity="idle", accepted_at=now(),
                         acceptance=authorization)
        with lock(self.edit_lock):
            return self.change(expected, "accepted", action)


def validate_result(result, role, state=None, run=None):
    if not isinstance(result, dict) or result.get("role") != role:
        raise Error("Fehlende oder falsche Ergebnisrolle.")
    if not isinstance(result.get("summary"), str) or not result["summary"].strip():
        raise Error("Ergebnis braucht eine Zusammenfassung.")
    if run and (result.get("run_id") != run["id"] or
                result.get("spec_hash") != state["spec"]["hash"]):
        raise Error("Ergebnis gehört zu einem anderen Auftrag oder einer anderen Spec.")
    if role == "generator":
        if not isinstance(result.get("changed_files"), list) or not isinstance(result.get("unconfirmed"), list):
            raise Error("Generator-Ergebnis benötigt changed_files und unconfirmed.")
        if len(set(result["changed_files"])) != len(result["changed_files"]):
            raise Error("Generator meldet doppelte Dateinamen.")
        return result
    if role != "evaluator":
        return result
    expected = {c["id"] for c in state["spec"]["contract"]["criteria"]}
    results = result.get("criteria")
    if not isinstance(results, list) or len(results) != len(expected):
        raise Error("Evaluation deckt nicht alle Kriterien genau einmal ab.")
    if {r.get("id") for r in results} != expected:
        raise Error("Unbekannte oder fehlende Kriterien-ID.")
    for item in results:
        if item.get("status") not in ("pass", "fail", "unverified"):
            raise Error("Unbekannter Kriterienstatus.")
        if not item.get("reason") or not item.get("evidence"):
            raise Error("Jedes Kriterium braucht Beleg oder konkretes Prüfungshindernis.")
    statuses = {r["status"] for r in results}
    verdict = "FAIL" if "fail" in statuses else "BLOCKED" if "unverified" in statuses else "PASS"
    if result.get("verdict") != verdict:
        raise Error(f"Gesamturteil widerspricht Kriterien; erwartet: {verdict}.")
    if not isinstance(result.get("findings"), list):
        raise Error("Findings müssen eine Liste sein.")
    seen = set()
    for finding in result["findings"]:
        if not isinstance(finding, dict) or not all(finding.get(x) for x in
                ("id", "severity", "criterion", "evidence", "description")):
            raise Error("Finding ohne ID, Schweregrad, Kriterium oder Beleg.")
        if finding["id"] in seen or finding["criterion"] not in expected:
            raise Error("Doppeltes Finding oder unbekanntes Kriterium.")
        seen.add(finding["id"])
        if finding["severity"] not in ("high", "medium", "low"):
            raise Error("Unbekannter Schweregrad.")
        if finding["severity"] in ("high", "medium") and verdict == "PASS":
            raise Error("PASS mit blockierenden Findings ist unzulässig.")
    return result
