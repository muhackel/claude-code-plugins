import contextlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import jsonschema

from common import Error, atomic, fingerprint, lock, project, write_json, write_preflight
from runner import stop_process
import delegation
import activity
import snapshot
import transport

DEFAULT_REVIEW = """Lies README, CLAUDE.md/AGENTS.md, Projektstruktur und Git-Änderungen.
Prüfe Bugs/Risiken, Doku-Drift, Struktur/Konventionen und uncommitted Changes.
Nenne höchstens zehn Befunde nach Schwere, jeweils Datei:Zeile, Problem und Empfehlung.
Antworte auf Deutsch. Nur lesen. Keine Dateien ändern."""


def single(args):
    root = project(args.directory)
    handover = Path(args.handover).read_text() if args.handover else (
        "" if sys.stdin.isatty() else sys.stdin.read())
    edit = args.command == "execute"
    if not handover.strip():
        if edit:
            raise Error("execute benötigt ein Handover.")
        handover = DEFAULT_REVIEW
    if args.timeout < 1:
        raise Error("Timeout muss positiv sein.")
    if edit:
        write_preflight(root, args.allow, args.include_dirty)
    adapter = transport.resolve(args.target, args.model, args.effort)
    if args.dry_run:
        print(json.dumps({"adapter": adapter, "profile": "edit" if edit else "inspect",
                          "workspace": str(root), "allowed_paths": args.allow,
                          "handover": handover}, ensure_ascii=False, indent=2))
        return 0
    transport.check_sandbox()
    print(f'Philharmonie: {adapter["target"]}, Modell {adapter["model"]}, '
          f'Effort {adapter["effort"]}', file=sys.stderr)
    guard = lock(root / ".philharmonie/local/locks/checkout.edit") if edit else contextlib.nullcontext()
    if edit:
        atomic(root / ".philharmonie/local/.gitignore", "*\n!.gitignore\n")
    with guard:
        if edit:
            write_preflight(root, args.allow, args.include_dirty)
        parent = root / ".philharmonie/local/singles" if edit else None
        if parent:
            parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        base = Path(tempfile.mkdtemp(prefix="philharmonie-single-", dir=parent))
        print(f"Protokoll: {base}", file=sys.stderr)
        write_json(base / "adapter.json", adapter)
        baseline = fingerprint(root)
        write_json(base / "baseline.json", baseline)
        work = snapshot.capture(root, base / "workspace", baseline)
        scratch = base / "scratch"
        scratch.mkdir()
        schema = {"type": "object", "additionalProperties": False, "required": ["answer"],
                  "properties": {"answer": {"type": "string", "minLength": 1}}}
        write_json(base / "schema.json", schema)
        output = scratch / "result.json"
        team = delegation.prepare(adapter, base / "agents", "edit") if edit else None
        label = "Philharmonie Einzelumsetzung" if edit else "Philharmonie Einzelprüfung"
        argv = transport.command(adapter, work, base / "schema.json", output,
                                 "edit" if edit else "inspect", label=label,
                                 **({"delegation": team} if team else {}))
        argv = transport.sandbox(work, scratch, argv, "edit" if edit else "inspect",
                                 **({"runtime_home": True} if team else {}))
        instructions = (handover + "\n\nAntworte im JSON-Feld answer auf Deutsch. "
                        "Kein Commit, Push, Merge oder Deployment. "
                        + ("Änderungen nur an: " + json.dumps(args.allow) if edit else "Nur lesen."))
        if team:
            instructions += ("\n\n" + (delegation.PACKAGE / "references/delegation.md").read_text()
                             + "\n\nVerfügbare Agents:\n" + json.dumps(team, ensure_ascii=False)
                             + "\nNenne Teilaufgaben, Modellwahl, Gründe und Ergebnisse im Feld answer.")
        instructions = transport.label_prompt(label, instructions)
        atomic(base / "Handover.md", instructions)
        with activity.Call(adapter, base, handover, args.command,
                           "Einzelumsetzung" if edit else "Einzelprüfung") as trace:
            started = time.time()
            process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, text=True, env=transport.environment(),
                                       start_new_session=True)
            try:
                expired = False
                try:
                    stdout, stderr = process.communicate(instructions, timeout=args.timeout)
                except subprocess.TimeoutExpired:
                    expired = True
                    stop_process(process)
                    stdout, stderr = process.communicate()
                trace.stdout = stdout
                atomic(base / "stdout.log", stdout)
                atomic(base / "stderr.log", stderr)
                if team:
                    write_json(base / "delegation-events.json", {
                        "events": delegation.events(stdout), "models": delegation.observed_models(scratch, stdout, work, started)})
                if expired:
                    raise Error(f"Zeitlimit erreicht; Einzelauftrag beendet. Protokoll: {base}")
                if stderr:
                    print(stderr, file=sys.stderr, end="")
                if process.returncode:
                    trace.error = f"CLI-Exit {process.returncode}"
                    return process.returncode if process.returncode > 0 else 128 - process.returncode
                result = transport.decode(adapter, stdout, output)
                try:
                    jsonschema.validate(result, schema)
                except jsonschema.ValidationError as exc:
                    raise Error(f"Ungültiges Ergebnis: {exc.message}. Protokoll: {base}") from exc
                trace.result = result
                if edit:
                    changed = snapshot.apply(root, work, baseline, args.allow, base / "apply.json")
                    print("Geänderte Dateien: " + ", ".join(changed), file=sys.stderr)
                elif fingerprint(root)["hash"] != baseline["hash"]:
                    raise Error("Projekt während der Frage verändert; Antwort neu prüfen.")
                print(result["answer"])
            finally:
                stop_process(process)
        if not edit:
            shutil.rmtree(base)
        return 0
