import copy
from contextlib import contextmanager
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from test_state import FixtureMixin
from common import Error, read_json, write_json
from runner import Runner


class AuditCase(FixtureMixin, unittest.TestCase):
    def configure(self, second_opinion=False, max_discussions=3):
        config = self.store.config()
        config.update(generator="claude", evaluator="claude",
                      second_opinion=second_opinion, max_discussions=max_discussions)
        write_json(self.store.base / "config.json", config)

    def finding(self, name, target, severity="high"):
        return {"id": name, "criterion": "ac-01", "severity": severity,
                "description": f"Befund {name} von {target}",
                "evidence": f"app.txt:1, geprüft von {target}"}

    @contextmanager
    def cli_fixture(self, evaluator=None):
        runner = Runner(self.store)
        calls = []

        def resolve(target, model=None, effort=None, tier="standard"):
            return {"target": target, "executable": f"fixture-{target}",
                    "version": "fixture-1", "model": model or f"fixture-{target}",
                    "effort": effort or "high", "tier": tier}

        def execute(run, argv, handover, output_dir, config, env=None):
            context, _ = json.JSONDecoder().raw_decode(
                handover.split("## Maschinenvertrag\n", 1)[1])
            target = argv[0].removeprefix("fixture-")
            calls.append({"target": target, "context": copy.deepcopy(context),
                          "directory": output_dir})
            common = {"role": context["role"], "run_id": context["run_id"],
                      "spec_hash": context["spec_hash"], "summary": "Datei geprüft"}
            if context["role"] == "generator":
                (Path(context["workspace"]) / "app.txt").write_text("zwei\n")
                result = {**common, "changed_files": ["app.txt"],
                          "unconfirmed": ["Browserdarstellung außerhalb des Auftrags ungeprüft."]}
            else:
                verdict, findings = evaluator(context, target) if evaluator else ("PASS", [])
                status = {"PASS": "pass", "FAIL": "fail", "BLOCKED": "unverified"}[verdict]
                result = {**common, "verdict": verdict, "findings": findings,
                          "criteria": [{"id": "ac-01", "status": status,
                                        "reason": "Datei vollständig gelesen",
                                        "evidence": "app.txt:1 enthält zwei"}]}
            if target == "codex":
                write_json(output_dir / "scratch/result.json", result)
                stdout = ""
            else:
                stdout = json.dumps({"structured_output": result})
            return {"exit_code": 0, "stdout": stdout, "stderr": "", "seconds": 0.01}

        with patch("transport.check_sandbox"), \
             patch("transport.resolve", side_effect=resolve), \
             patch("transport.sandbox", side_effect=lambda work, scratch, argv, profile, **kwargs: argv), \
             patch.object(runner, "execute_child", side_effect=execute):
            yield runner, calls

    def test_independent_review_precedes_generator_and_previous_findings(self):
        state = self.approved()
        self.configure()
        with self.cli_fixture() as (runner, calls):
            state = runner.one(state["revision"])
            previous = {"summary": "Früherer Befund", "findings": [
                self.finding("prior-01", "frühere Prüfung")]}
            state = self.store.change(state["revision"], "previous_review_fixture",
                                      lambda current: current.update(last_evaluation=previous))
            state = runner.one(state["revision"])

        reviews = [call["context"] for call in calls if call["context"]["role"] == "evaluator"]
        self.assertEqual(len(reviews), 2)
        self.assertIsNone(reviews[0]["discussion"])
        self.assertNotIn("findings", reviews[0])
        self.assertNotIn("Browserdarstellung", json.dumps(reviews[0]))
        self.assertNotIn("prior-01", json.dumps(reviews[0]))
        discussion = reviews[1]["discussion"]
        self.assertEqual(discussion["previous_evaluation"], previous)
        self.assertIn("Browserdarstellung", discussion["generator_report"]["unconfirmed"][0])
        self.assertEqual(discussion["independent_reviews"][0]["verdict"], "PASS")
        for context in reviews:
            self.assertEqual(context["spec_revision"], state["spec"]["revision"])
            self.assertEqual(context["profile"], "verify")
            self.assertEqual(len(context["fingerprint"]), 64)
            self.assertTrue(Path(context["workspace"]).is_dir())
            self.assertIn("criteria", context["result_schema"]["properties"])
        self.assertEqual(state["phase"], "awaiting_acceptance")

    def test_both_first_opinions_are_independent_and_then_reconcile(self):
        state = self.approved()
        self.configure(second_opinion=True)
        with self.cli_fixture() as (runner, calls):
            state = runner.run(state["revision"])

        reviews = [call for call in calls if call["context"]["role"] == "evaluator"]
        self.assertEqual([call["target"] for call in reviews], ["claude", "codex", "claude", "codex"])
        self.assertEqual([call["context"]["discussion"] for call in reviews[:2]], [None, None])
        for call in reviews[2:]:
            self.assertEqual(len(call["context"]["discussion"]["independent_reviews"]), 2)
            self.assertIsNotNone(call["context"]["discussion"]["generator_report"])
        report = read_json(self.root / state["runs"][-1]["report"])
        self.assertEqual([adapter["target"] for adapter in report["adapters"]], ["claude", "codex"])
        for call in reviews:
            recorded = read_json(call["directory"] / "adapter.json")
            self.assertEqual(recorded["target"], call["target"])
        self.assertEqual(state["phase"], "awaiting_acceptance")

    def test_findings_from_both_reviewers_reach_the_next_generator(self):
        state = self.approved()
        self.configure(second_opinion=True)

        def evaluator(context, target):
            names = ["f-a", "f-b"] if context["discussion"] else ["f-a" if target == "claude" else "f-b"]
            findings = [self.finding(name, target) for name in names]
            findings.append(self.finding(f"low-{target}", target, "low"))
            return "FAIL", findings

        with self.cli_fixture(evaluator) as (runner, calls):
            state = runner.one(state["revision"])
            state = runner.one(state["revision"])
            self.assertEqual(state["phase"], "implementing")
            findings = state["last_evaluation"]["findings"]
            self.assertEqual({finding["id"] for finding in findings},
                             {"f-a", "f-b", "low-claude", "low-codex"})
            for finding in findings:
                if finding["severity"] == "high":
                    self.assertIn("claude", finding["evidence"])
                    self.assertIn("codex", finding["evidence"])
            state = runner.one(state["revision"])
        self.assertEqual(calls[-1]["context"]["role"], "generator")
        self.assertEqual(calls[-1]["context"]["findings"]["findings"], findings)

    def test_same_failed_criterion_with_persistent_distinct_findings_is_blocked(self):
        state = self.approved()
        self.configure(second_opinion=True, max_discussions=2)

        def evaluator(context, target):
            return "FAIL", [self.finding(f"unresolved-{target}", target)]

        with self.cli_fixture(evaluator) as (runner, calls):
            state = runner.one(state["revision"])
            with self.assertRaisesRegex(Error, "uneinig"):
                runner.one(state["revision"])
        state = self.store.load()
        reviews = [call for call in calls if call["context"]["role"] == "evaluator"]
        self.assertEqual(len(reviews), 6)
        self.assertEqual(state["phase"], "evaluating")
        self.assertEqual(state["activity"], "blocked")
        self.assertEqual(state["runs"][-1]["status"], "failed")
        self.assertIsNone(state["evaluation"])
        for call in reviews:
            self.assertTrue((call["directory"] / "result.json").is_file())

    def test_modified_generator_or_evaluator_report_prevents_acceptance(self):
        state = self.approved()
        self.configure()
        with self.cli_fixture() as (runner, calls):
            state = runner.run(state["revision"])
        for run in state["runs"]:
            with self.subTest(role=run["role"]):
                report = self.root / run["report"]
                original = report.read_bytes()
                modified = read_json(report)
                modified["result"]["summary"] = "Nachträglich veränderter Bericht"
                write_json(report, modified)
                try:
                    with self.assertRaisesRegex(Error, "Rundenbericht.*verändert"):
                        self.store.accept("Passt", state["revision"])
                    self.assertEqual(self.store.load()["phase"], "awaiting_acceptance")
                    self.assertEqual(self.store.load()["revision"], state["revision"])
                    self.assertFalse((self.store.doc / "Summary.md").exists())
                finally:
                    report.write_bytes(original)
        accepted = self.store.accept("Passt", state["revision"])
        self.assertEqual(accepted["phase"], "completed")

    def test_foreign_change_after_report_write_cannot_receive_pass(self):
        state = self.approved()
        self.configure()
        mutated = []

        def write_and_change(path, value):
            write_json(path, value)
            if value.get("result", {}).get("role") == "evaluator":
                (self.root / "app.txt").write_text("Fremde Änderung nach der Prüfung\n")
                mutated.append(path)

        with self.cli_fixture() as (runner, calls):
            state = runner.one(state["revision"])
            with patch("runner.write_json", side_effect=write_and_change):
                with self.assertRaisesRegex(Error, "Prüfstand.*verändert"):
                    runner.one(state["revision"])
        state = self.store.load()
        self.assertEqual(len(mutated), 1)
        self.assertEqual((self.root / "app.txt").read_text(), "Fremde Änderung nach der Prüfung\n")
        self.assertEqual(state["phase"], "evaluating")
        self.assertEqual(state["activity"], "blocked")
        self.assertEqual(state["runs"][-1]["status"], "failed")
        self.assertIsNone(state["evaluation"])
        with self.assertRaises(Error):
            self.store.accept("Passt", state["revision"])


if __name__ == "__main__":
    unittest.main()
