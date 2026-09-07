from contextvars import ContextVar
from pathlib import Path
import sys
import uuid

from common import atomic, write_json
import participants

_report = ContextVar("philharmonie_model_activity", default=None)


def brief(value, limit=180):
    text = " ".join(str(value or "").split())
    text = "".join(character for character in text if character.isprintable())
    return text if len(text) <= limit else text[:limit - 1] + "…"


def outcome_excerpt(entry):
    outcome = entry.get("outcome", "Kein Abschlussbeleg")
    if isinstance(outcome, str) and outcome.startswith("Nativer Selbstbericht: "):
        lines = outcome.splitlines()
        for index, line in enumerate(lines):
            label = line.lstrip(" -*#").replace("**", "")
            if label.startswith("Ergebnis:"):
                return "Nativer Selbstbericht (Auszug): " + "\n".join(lines[index:])
    return outcome


def table(entries):
    if not entries:
        return "Keine zusätzlichen Modellaufträge durch die Laufzeit."
    lines = ["| Modell | Aufgabe | Ergebnis |", "|---|---|---|"]
    evidence = {"observed": "belegt", "configured": "konfiguriert, nicht bestätigt", "unknown": "unbekannt"}
    statuses = {"completed": "abgeschlossen", "failed": "fehlgeschlagen", "running": "läuft",
                "unknown": "Abschluss unbekannt", "cancelled": "abgebrochen", "interrupted": "unterbrochen"}
    for entry in entries:
        model = f'{entry.get("model") or "Unbekannt"} ({evidence.get(entry.get("model_evidence"), "unbekannt")})'
        task = f'{entry.get("call", entry.get("role", ""))}: {entry.get("task_summary") or entry.get("task", "")}'
        status = entry.get("status", "unknown")
        outcome = f'{statuses.get(status, status)}: {outcome_excerpt(entry)}'
        lines.append("| " + " | ".join(brief(value).replace("|", "\\|") for value in (model, task, outcome)) + " |")
    return "\n".join(lines)


def current():
    report = _report.get()
    return list(report.entries) if report else []


class Reporting:
    def __init__(self):
        self.entries = []
        self.exit_code = 0

    def __enter__(self):
        self.token = _report.set(self)
        return self

    def __exit__(self, kind, error, traceback):
        _report.reset(self.token)
        print("\nModelle und Aufgaben dieses Aufrufs\n", file=sys.stderr)
        print(table(self.entries), file=sys.stderr)
        if error or self.exit_code:
            print("Der Befehl ist fehlgeschlagen; gemeldete Modellarbeit ist keine bestätigte Übernahme.", file=sys.stderr)


class Call:
    def __init__(self, adapter, directory, task, role, label=None, store=None, run_id=None):
        self.adapter, self.directory, self.task, self.role = adapter, Path(directory), task, role
        self.label = label or role
        self.store, self.run_id = store, run_id
        self.stdout = None
        self.result = None
        self.error = None
        self.entries = []
        self.id = uuid.uuid4().hex

    def __enter__(self):
        return self

    def __exit__(self, kind, error, traceback):
        failure = error or self.error
        stdout = self.stdout
        if stdout is None:
            path = self.directory / "stdout.log"
            stdout = path.read_text(errors="replace") if path.is_file() else ""
        self.entries = participants.collect(self.adapter, self.directory / "scratch", stdout,
            self.task, self.role, result={"summary": f"Fehler: {failure}"} if failure else self.result,
            status="failed" if failure else "completed")
        for entry in self.entries:
            entry.update(call_id=self.id, call=self.label)
        report = _report.get()
        if report:
            report.entries.extend(self.entries)
        write_json(self.directory / "model-activity.json", self.entries)
        atomic(self.directory / "model-activity.md", "# Modelle und Aufgaben\n\n" + table(self.entries) + "\n")
        if self.store:
            def register(state):
                active = state["runs"][-1]
                if active["id"] == self.run_id:
                    active.setdefault("model_activity", []).extend(self.entries)
            self.store.change(None, "model_activity_recorded", register)
