import copy
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_state import FixtureMixin
from common import Error, digest, fingerprint, lock, read_json, write_json
from philharmonie import main
from runner import Runner
from spec_review import review_spec
from state import SPEC_POINTS, Store, contract_hash, current_cli, spec_review_score


class SpecReviewCase(FixtureMixin, unittest.TestCase):
    def submitted(self):
        return self.store.set_spec("# Spec\n\nZiel: zwei\n", self.contract, 1)

    def test_approve_requires_an_independent_review(self):
        state = self.submitted()
        with self.assertRaisesRegex(Error, "Gegenreview fehlt"):
            self.store.approve("Setze die Spec um.", state["revision"])
        self.assertIsNone(self.store.load()["authorization"])

    def test_score_is_computed_without_a_minimum_gate(self):
        state = self.submitted()
        result, adapter, source = self.spec_review_data(state)
        for item in result["scores"].values():
            item["points"] = 0
        result["scores"]["coverage"]["points"] = 3
        result["scores"]["risks"]["points"] = 2
        state = self.store.record_spec_review(result, adapter, source, state["revision"])
        self.assertEqual(state["spec_review"]["score"], 5)
        report = read_json(self.root / state["spec_review"]["report"])
        self.assertEqual(report["score"], 5)
        state = self.store.approve("Setze die Spec mit diesen bekannten Einschränkungen um.", state["revision"])
        self.assertEqual(state["phase"], "implementing")

    def test_blockers_prevent_approval_even_with_maximum_score(self):
        state = self.submitted()
        result, adapter, source = self.spec_review_data(state)
        result["blockers"] = [{"id": "decision-01", "reason": "Bindende Zielplattform fehlt",
                               "evidence": "Spec nennt keine Zielplattform"}]
        result["questions"] = ["Soll die Anwendung auf Linux oder auf macOS laufen?"]
        state = self.store.record_spec_review(result, adapter, source, state["revision"])
        self.assertEqual(state["spec_review"]["score"], 100)
        self.assertEqual(state["spec_review"]["questions"], result["questions"])
        with self.assertRaisesRegex(Error, "offene Blocker"):
            self.store.approve("Setze die Spec um.", state["revision"])

    def test_invalid_points_categories_and_missing_evidence_are_rejected(self):
        state = self.submitted()
        result, adapter, source = self.spec_review_data(state)
        mutations = [lambda value: value.update(score=100),
                     lambda value: value["scores"].pop("risks"),
                     lambda value: value["scores"]["evidence"].update(evidence=" "),
                     lambda value: value["scores"]["scope"].update(points=1.5),
                     lambda value: value["scores"]["scope"].update(points=True)]
        for key, maximum in SPEC_POINTS.items():
            for invalid in (-1, maximum + 1):
                changed = copy.deepcopy(result)
                changed["scores"][key]["points"] = invalid
                with self.subTest(category=key, points=invalid), self.assertRaises(Error):
                    spec_review_score(changed, source, adapter)
        for mutate in mutations:
            changed = copy.deepcopy(result)
            mutate(changed)
            with self.assertRaises(Error):
                spec_review_score(changed, source, adapter)

    def test_same_cli_and_mismatched_result_source_are_rejected(self):
        state = self.submitted()
        result, adapter, source = self.spec_review_data(state)
        with self.assertRaisesRegex(Error, "anderen CLI"):
            spec_review_score(result, source, {**adapter, "target": source["planner_cli"]})
        for key in ("run_id", "spec_hash", "contract_hash", "fingerprint"):
            changed = copy.deepcopy(result)
            changed[key] = "0" * 64
            with self.subTest(key=key), self.assertRaisesRegex(Error, "anderen Prüfstand"):
                spec_review_score(changed, source, adapter)

    def test_project_change_invalidates_review_before_approval(self):
        state = self.reviewed(self.submitted())
        (self.root / "new-source.md").write_text("Neue Projektquelle\n")
        with self.assertRaisesRegex(Error, "veraltet"):
            self.store.approve("Setze die Spec um.", state["revision"])

    def test_project_change_during_review_prevents_registration(self):
        state = self.submitted()
        result, adapter, source = self.spec_review_data(state)
        (self.root / "app.txt").write_text("Fremde Änderung\n")
        with self.assertRaisesRegex(Error, "Projekt.*verändert"):
            self.store.record_spec_review(result, adapter, source, state["revision"])
        self.assertIsNone(self.store.load()["spec_review"])

    def test_spec_and_contract_changes_invalidate_review(self):
        state = self.reviewed(self.submitted())
        original = (self.store.doc / "Spec.md").read_bytes()
        (self.store.doc / "Spec.md").write_text("Andere Spec\n")
        with self.assertRaisesRegex(Error, "Spec.*verändert"):
            self.store.approve("Setze die Spec um.", state["revision"])
        (self.store.doc / "Spec.md").write_bytes(original)
        changed = copy.deepcopy(state["spec"]["contract"])
        changed["allowed_paths"] = ["other.txt"]
        write_json(self.store.doc / "specs/1.json", changed)
        with self.assertRaisesRegex(Error, "Vertrag.*verändert"):
            self.store.approve("Setze die Spec um.", state["revision"])
        forged = copy.deepcopy(state)
        forged["spec"]["contract"] = changed
        with self.assertRaisesRegex(Error, "veraltet"):
            self.store.check_spec_review(forged)
        self.assertNotEqual(contract_hash(changed), state["spec_review"]["source"]["contract_hash"])

    def test_new_spec_revision_and_replan_clear_the_score(self):
        state = self.reviewed(self.submitted())
        state = self.store.set_spec("# Neue Spec\n", self.contract, state["revision"])
        self.assertIsNone(state["spec_review"])
        with self.assertRaisesRegex(Error, "Gegenreview fehlt"):
            self.store.approve("Setze die Spec um.", state["revision"])
        state = self.reviewed(state)
        state = self.store.replan("Scope nochmals abgleichen.", state["revision"])
        self.assertIsNone(state["spec_review"])

    def test_tampered_report_and_tampered_registered_score_are_rejected(self):
        state = self.reviewed(self.submitted())
        report = self.root / state["spec_review"]["report"]
        original = report.read_bytes()
        report.write_bytes(original + b"\n")
        with self.assertRaisesRegex(Error, "Bericht.*verändert"):
            self.store.approve("Setze die Spec um.", state["revision"])
        report.write_bytes(original)
        forged = copy.deepcopy(state)
        forged["spec_review"]["score"] = 0
        with self.assertRaisesRegex(Error, "Score.*widerspricht"):
            self.store.check_spec_review(forged)

    def test_persistent_planner_and_legacy_mission_fallback(self):
        with patch.dict("os.environ", {"CLAUDECODE": "1"}):
            other = Store(self.root, "claude-planned")
            self.assertEqual(other.create("Planen")["planner_cli"], "claude")
        other = Store(self.root, "explicit-planner")
        self.assertEqual(other.create("Planen", planner="codex")["planner_cli"], "codex")
        state = self.submitted()
        state.pop("planner_cli")
        state.pop("spec_review")
        write_json(self.store.path, state)
        state = self.store.load()
        self.assertNotIn("planner_cli", state)
        state = self.reviewed(state)
        self.assertEqual(state["planner_cli"], current_cli())
        self.assertTrue(state["planner_cli_inferred"])
        self.assertEqual(self.store.approve("Setze um.", state["revision"])["phase"], "implementing")

    def test_actual_review_flow_uses_other_cli_and_readonly_profile(self):
        state = self.submitted()
        received = []
        expected_target = "codex" if state["planner_cli"] == "claude" else "claude"

        def resolve(target, model, effort):
            self.assertEqual(target, expected_target)
            return {"target": target, "executable": f"fixture-{target}", "version": "fixture",
                    "model": "fixture", "effort": effort}

        def execute(runner, run, argv, handover, output_dir, config, env=None):
            context = json.loads(handover.split("## Maschinenvertrag\n", 1)[1])
            received.append(context)
            self.assertEqual(context["profile"], "inspect")
            self.assertEqual(context["planner_cli"], state["planner_cli"])
            self.assertEqual((Path(context["workspace"]) / "app.txt").read_text(), "eins\n")
            result, adapter, source = self.spec_review_data(runner.store.load())
            for key in ("run_id", "spec_revision", "spec_hash", "contract_hash", "fingerprint"):
                result[key] = context[key]
            if expected_target == "codex":
                self.assertIn("read-only", argv)
                write_json(output_dir / "scratch/result.json", result)
                stdout = ""
            else:
                self.assertNotIn("Edit", argv[argv.index("--tools") + 1])
                stdout = json.dumps({"structured_output": result})
            return {"exit_code": 0, "stdout": stdout, "stderr": "", "seconds": 0.01}

        with patch("transport.resolve", side_effect=resolve), patch("transport.check_sandbox"), \
             patch("transport.sandbox", side_effect=lambda work, scratch, argv, profile: argv), \
             patch.object(Runner, "execute_child", new=execute):
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(["-C", str(self.root), "review-spec", "test",
                                       "--revision", str(state["revision"])]), 0)
        status = json.loads(output.getvalue())
        self.assertEqual(status["spec_review"]["score"], 100)
        rows = status["invocation_models"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["role"], "spec_reviewer")
        self.assertIn("100/100", rows[0]["outcome"])
        saved = read_json(self.root / status["spec_review"]["report"])
        self.assertEqual(saved["model_activity"], rows)
        self.assertEqual(status["spec_review"]["reviewer_cli"], expected_target)
        self.assertEqual(status["phase"], "awaiting_spec")
        state = self.store.load()
        self.assertEqual(len(received), 1)
        self.assertEqual(state["runs"][-1]["role"], "spec_reviewer")
        self.assertEqual(state["runs"][-1]["status"], "succeeded")
        self.assertEqual((self.root / "app.txt").read_text(), "eins\n")
        self.assertEqual(self.store.approve("Setze die Spec um.", state["revision"])["phase"], "implementing")

    def test_stale_revision_and_active_run_lock_prevent_cli_start(self):
        state = self.submitted()
        with patch("transport.resolve") as resolve:
            with self.assertRaisesRegex(Error, "Veraltete Revision"):
                review_spec(self.store, state["revision"] - 1)
            with lock(self.store.run_lock), self.assertRaisesRegex(Error, "Sperre"):
                review_spec(self.store, state["revision"])
            resolve.assert_not_called()

    def test_protocol_failure_blocks_review_without_authorization(self):
        state = self.submitted()
        target = "codex" if state["planner_cli"] == "claude" else "claude"
        adapter = {"target": target, "executable": target, "model": "fixture", "effort": "high"}
        with patch("transport.resolve", return_value=adapter), patch("transport.check_sandbox"), \
             patch("transport.sandbox", side_effect=lambda work, scratch, argv, profile: argv), \
             patch.object(Runner, "execute_child", return_value={
                 "exit_code": 0, "stdout": "kein JSON", "stderr": "", "seconds": 0.01}):
            with self.assertRaises(Error):
                review_spec(self.store, state["revision"])
        state = self.store.load()
        self.assertEqual(state["phase"], "awaiting_spec")
        self.assertEqual(state["activity"], "blocked")
        self.assertEqual(state["runs"][-1]["status"], "failed")
        self.assertIsNone(state["spec_review"])
        self.assertIsNone(state["authorization"])


@unittest.skipUnless(os.environ.get("PHILHARMONIE_LIVE") == "1",
                     "Explizite Spec-Gegenprüfung mit authentifizierten CLIs erforderlich")
class LiveSpecReviewCase(FixtureMixin, unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="philharmonie-live-spec-", dir="/tmp"))
        self.git("init", "-b", "feature/spec-review")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Spec-Gegenreview-Test")
        (self.root / "app.txt").write_bytes(b"eins\n")
        self.git("add", "app.txt")
        self.git("commit", "-m", "Textquelle für Gegenreview")

    def review_direction(self, planner):
        self.store = Store(self.root, "text-spec")
        goal = "Ändere app.txt zu genau einer Zeile „zwei“ mit einem abschließenden LF-Zeilenumbruch."
        state = self.store.create(goal, planner=planner)
        original = (self.root / "app.txt").read_bytes()
        markdown = f"""# Spezifikation

## Missionstyp

Abgegrenzte Textänderung. Dieser Prüflauf bewertet ausschließlich die Spec vor der Umsetzung.

## Nutzerauftrag

{state['goal']}

## Ziel

app.txt enthält nach der späteren Umsetzung exakt die fünf Bytes 7a 77 65 69 0a (UTF-8, Text zwei und abschließendes LF).

## Befunde und Quellen

Die vorhandene app.txt wurde vollständig gelesen. Sie enthält aktuell die fünf Bytes 65 69 6e 73 0a (Text eins und abschließendes LF).
SHA-256 der gelesenen Quelle: {digest(original)}. Die Quelle ist im Snapshot unter app.txt verfügbar.

## Abnahmekriterien

ac-01: app.txt enthält exakt zwei mit einem abschließenden LF, keine BOM, Leerzeichen oder weiteren Zeilen.
Prüfung: gesamten Dateiinhalt gegen die erwarteten UTF-8-Bytes 7a 77 65 69 0a vergleichen.

ac-02: Andere Projektdateien und der Dateimodus von app.txt bleiben unverändert.
Prüfung: Dateistand und Modi mit dem vor der Umsetzung erfassten Snapshot vergleichen.

## Randfälle und Risiken

CRLF, fehlender Schlussumbruch, zusätzliche Leerzeichen, BOM und zusätzliche Zeilen verletzen ac-01.
Eine konkurrierende Änderung an app.txt vor der Übernahme muss erhalten und als Konflikt gemeldet werden.
Es gibt keine Programme, Dienste, externen Quellen oder Architekturentscheidungen für diese Textänderung.

## Entscheidungen

Inhalt und LF-Zeilenende stammen aus dem Nutzerauftrag. Ein vollständiger Text-/Bytevergleich reicht zur Abnahme.
Es sind keine Entscheidungen offen. Automatische Buildkommandos sind für die reine Textdatei nicht erforderlich.

## Außerhalb des Auftrags

Kein Programmstart, kein neuer Code, keine zusätzlichen Dateien, keine Modusänderung, kein Commit oder Push.
Die Gegenprüfung selbst darf app.txt nicht ändern und erteilt keine Umsetzungsautorisierung.

## Mögliche Lösungswege

Nach einer späteren ausdrücklichen Umsetzungsfreigabe den Dateiinhalt durch die festgelegten fünf Bytes ersetzen.
"""
        contract = {"criteria": [
            {"id": "ac-01", "description": "app.txt enthält exakt die UTF-8-Bytes 7a 77 65 69 0a.",
             "verification": "Datei vollständig gegen zwei mit genau einem abschließenden LF vergleichen; BOM und zusätzliche Zeichen ausschließen."},
            {"id": "ac-02", "description": "Andere Projektdateien und der Modus von app.txt bleiben unverändert.",
             "verification": "Dateistand und Modi mit dem vor der Umsetzung erfassten Snapshot vergleichen."}],
            "allowed_paths": ["app.txt"], "checks": []}
        state = self.store.set_spec(markdown, contract, state["revision"])
        config = self.store.config()
        config["timeout_seconds"] = 240
        write_json(self.store.base / "config.json", config)
        before = fingerprint(self.root)["hash"]
        print(f"\nLive-Spec-Gegenreview: Planer {planner}; Artefakte {self.root}", flush=True)
        try:
            state = review_spec(self.store, state["revision"])
        except Error as exc:
            raise AssertionError(f"Live-Gegenprüfung fehlgeschlagen: {exc}; Artefakte {self.root}") from exc
        review = state["spec_review"]
        report_path = self.root / review["report"]
        report = read_json(report_path)
        print(json.dumps({"planner": planner, "reviewer": review["reviewer_cli"],
                          "score": review["score"], "blockers": review["blockers"],
                          "questions": review["questions"], "report": str(report_path)},
                         ensure_ascii=False), flush=True)
        self.assertEqual(review["reviewer_cli"], "codex" if planner == "claude" else "claude")
        self.assertEqual(report["source"]["planner_cli"], planner)
        self.assertEqual(set(report["result"]["scores"]), set(SPEC_POINTS))
        for name, entry in report["result"]["scores"].items():
            self.assertGreaterEqual(entry["points"], 0)
            self.assertLessEqual(entry["points"], SPEC_POINTS[name])
            self.assertTrue(entry["reason"].strip())
            self.assertTrue(entry["evidence"].strip())
        self.assertEqual(review["score"], sum(entry["points"] for entry in report["result"]["scores"].values()))
        self.assertEqual(review["report_hash"], digest(report_path.read_bytes()))
        self.assertEqual(fingerprint(self.root)["hash"], before)
        self.assertEqual((self.root / "app.txt").read_bytes(), original)
        self.assertIsNone(state["authorization"])
        self.assertEqual(state["phase"], "awaiting_spec")
        self.assertEqual(state["activity"], "idle")
        self.assertEqual(state["runs"][-1]["status"], "succeeded")
        self.assertFalse(review["blockers"], f"Fachliche Kritik der Gegenprüfung: {report_path}: {review['blockers']}")

    def test_claude_plan_is_reviewed_by_codex(self):
        self.review_direction("claude")

    def test_codex_plan_is_reviewed_by_claude(self):
        self.review_direction("codex")


if __name__ == "__main__":
    unittest.main()
