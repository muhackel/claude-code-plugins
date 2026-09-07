import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest

from test_state import FixtureMixin
import test_single
import test_audit
from common import read_json
from philharmonie import main
import activity


class ActivityCase(FixtureMixin, unittest.TestCase):
    invoke = test_single.SingleCase.invoke

    def test_single_cli_reports_models_without_changing_answer(self):
        for target in ("claude", "codex"):
            with self.subTest(target=target):
                code, answer = self.invoke(target, cli=True)
                self.assertEqual((code, answer), (0, "Geprüft: äöüß\n"))
                self.assertIn("Modelle und Aufgaben dieses Aufrufs", self.console)
                self.assertIn("fixture (konfiguriert, nicht bestätigt)", self.console)
                self.assertIn("Prüfe app.txt", self.console)
                self.assertIn("Geprüft: äöüß", self.console)
                self.assertFalse(self.artifacts.exists())

    def test_single_failure_keeps_model_assignment_and_original(self):
        code, _ = self.invoke("claude", "execute", failure="exit", cli=True)
        self.assertEqual(code, 7)
        self.assertIn("fehlgeschlagen", self.console)
        self.assertIn("fixture", self.console)
        rows = read_json(self.artifacts / "model-activity.json")
        self.assertEqual(rows[0]["status"], "failed")
        self.assertEqual(rows[0]["task"], "Prüfe app.txt")
        self.assertEqual((self.root / "app.txt").read_text(), "eins\n")

    def test_invalid_output_still_reports_the_attempted_model(self):
        code, _ = self.invoke("claude", failure="invalid", cli=True)
        self.assertEqual(code, 1)
        rows = read_json(self.artifacts / "model-activity.json")
        self.assertEqual(rows[0]["status"], "failed")
        self.assertIn("fixture", self.console)
        self.assertNotIn("abgeschlossen:", self.console)

    def test_status_separates_history_from_new_model_calls(self):
        previous = {"model": "historisches-modell", "task": "Frühere Prüfung", "outcome": "PASS"}
        self.store.change(1, "history_fixture", lambda state: state["runs"].append({
            "id": "past", "role": "evaluator", "status": "succeeded", "owner": None, "child": None,
            "model_activity": [previous]}))
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            self.assertEqual(main(["-C", str(self.root), "status", "test"]), 0)
        state = json.loads(stdout.getvalue())
        self.assertEqual(state["invocation_models"], [])
        self.assertEqual(state["last_run"]["model_activity"], [previous])
        self.assertIn("Keine zusätzlichen Modellaufträge", stderr.getvalue())
        self.assertNotIn("historisches-modell", stderr.getvalue())

    def test_all_reviewers_and_reconciliation_calls_remain_separate(self):
        state = self.approved()
        test_audit.AuditCase.configure(self, second_opinion=True)
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr), activity.Reporting() as report:
            with test_audit.AuditCase.cli_fixture(self) as (runner, calls):
                state = runner.run(state["revision"])
            self.assertEqual(len(activity.current()), 5)
        self.assertEqual(len(report.entries), 5)
        self.assertEqual(len({entry["call_id"] for entry in report.entries}), 5)
        self.assertEqual(sum("Unabhängige Prüfung" in entry["call"] for entry in report.entries), 2)
        self.assertEqual(sum("Abgleich" in entry["call"] for entry in report.entries), 2)
        self.assertEqual({entry["model"] for entry in report.entries}, {"fixture-claude", "fixture-codex"})
        saved = read_json(self.root / state["runs"][-1]["report"])
        self.assertEqual(len(saved["model_activity"]), 4)
        self.assertEqual(saved["model_activity"], state["runs"][-1]["model_activity"])

    def test_timeout_is_reported_and_invocations_do_not_leak(self):
        with tempfile.TemporaryDirectory() as directory:
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr), activity.Reporting() as report:
                with self.assertRaises(TimeoutError):
                    with activity.Call({"target": "codex", "model": "angefordert"}, directory,
                                       "Repository auditieren", "ask"):
                        raise TimeoutError("Zeitlimit")
            self.assertEqual(report.entries[0]["status"], "failed")
            self.assertEqual(report.entries[0]["model_evidence"], "configured")
            self.assertIn("Zeitlimit", stderr.getvalue())
            self.assertTrue((Path(directory) / "model-activity.md").exists())
            with contextlib.redirect_stderr(io.StringIO()), activity.Reporting():
                self.assertEqual(activity.current(), [])

    def test_table_escapes_multiline_model_output(self):
        rendered = activity.table([{"model": "test", "model_evidence": "observed", "role": "ask",
                                    "task": "A | B\nC", "status": "completed", "outcome": "D\x1b"}])
        self.assertEqual(len(rendered.splitlines()), 3)
        self.assertIn("A \\| B C", rendered)
        self.assertNotIn("\x1b", rendered)

    def test_table_prefers_native_task_description(self):
        rendered = activity.table([{"model": "test", "model_evidence": "observed", "role": "subagent",
                                    "task": "Arbeitsverzeichnis: " + "x" * 250,
                                    "task_summary": "app.txt nach checked.txt kopieren",
                                    "status": "completed", "outcome": "Erledigt"}])
        self.assertIn("app.txt nach checked.txt kopieren", rendered)
        self.assertNotIn("Arbeitsverzeichnis", rendered)

    def test_native_result_is_visible_after_long_model_explanation(self):
        outcome = ("Nativer Selbstbericht: Teilaufgabe abgeschlossen.\n- Modell: " + "x" * 250
                   + "\n- Ergebnis: checked.txt erstellt.\n- Nachweis: cmp Exit 0.")
        entry = {"model": "test", "role": "subagent", "task": "Aufgabentext nicht lesbar",
                 "status": "completed", "outcome": outcome}
        rendered = activity.table([entry])
        self.assertIn("checked.txt erstellt", rendered)
        self.assertIn("Nativer Selbstbericht (Auszug)", rendered)
        self.assertEqual(entry["outcome"], outcome)


@unittest.skipUnless(os.environ.get("PHILHARMONIE_LIVE") == "1",
                     "Expliziter Test der Modellübersicht mit nativen Agents erforderlich")
class LiveActivityCase(FixtureMixin, unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="philharmonie-live-activity-", dir="/tmp"))
        self.git("init", "-b", "feature/activity-test")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Modellübersicht-Test")
        (self.root / "app.txt").write_text("eins\n")
        self.git("add", "app.txt")
        self.git("commit", "-m", "Quelle für Modellübersicht-Test")

    def native_activity(self, target, expected_model):
        request = self.root / ".philharmonie/local/request.md"
        request.parent.mkdir(parents=True)
        request.write_text(
            "Integrationstest der Modellübersicht: Starte genau einen nativen Agent vom Typ "
            "philharmonie-advanced ohne Kontext-Fork. Sein Auftrag: Lies app.txt und schreibe "
            "checked.txt mit exakt demselben Inhalt. Dieser Test verlangt den tatsächlichen "
            "Agent-Aufruf trotz der kleinen Aufgabe. Warte auf seinen Abschluss, prüfe checked.txt "
            "selbst und berichte das Ergebnis. Keine weiteren Agents und keine anderen Änderungen.")
        print(f"\nLive-Modellübersicht {target}: {self.root}", flush=True)
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(["-C", str(self.root), "execute", "--target", target,
                         "--handover", str(request), "--allow", "checked.txt", "--timeout", "240"])
        console = stderr.getvalue()
        print(console, flush=True)
        self.assertEqual(code, 0, console)
        base = next(Path(line.removeprefix("Protokoll: ")) for line in console.splitlines()
                    if line.startswith("Protokoll: "))
        rows = read_json(base / "model-activity.json")
        self.assertEqual(len(rows), 2, rows)
        child = rows[1]
        self.assertIn(expected_model, child["model"], rows)
        self.assertEqual(child["model_evidence"], "observed", rows)
        self.assertEqual(child["status"], "completed", rows)
        self.assertTrue(child["task"].strip(), rows)
        self.assertIn("checked.txt", child["task"] + "\n" + child["outcome"], rows)
        self.assertTrue(child["outcome"].strip(), rows)
        self.assertIn(child["model"], console)
        self.assertIn("Modelle und Aufgaben dieses Aufrufs", console)
        self.assertIn("checked.txt", activity.table([child]))
        self.assertTrue(stdout.getvalue().strip())
        self.assertNotIn("| Modell |", stdout.getvalue())
        self.assertEqual((self.root / "checked.txt").read_bytes(), b"eins\n")
        self.assertEqual((self.root / "app.txt").read_bytes(), b"eins\n")

    def test_claude_native_model_activity(self):
        self.native_activity("claude", "opus")

    def test_codex_native_model_activity(self):
        self.native_activity("codex", "gpt-5.6-sol")
