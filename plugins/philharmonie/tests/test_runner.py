import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from common import Error, fingerprint, identity, write_json
from runner import Runner
from test_state import FixtureMixin


class RunnerCase(FixtureMixin, unittest.TestCase):
    def run_fixture(self, verdict="PASS", mutate=None):
        runner = Runner(self.store)
        def agent(role, state, run, directory, workspace, adapter, config, checks, discussion=None):
            common = {"role": role, "run_id": run["id"], "spec_hash": state["spec"]["hash"],
                      "summary": "Geprüft"}
            if role == "generator":
                (workspace / "app.txt").write_text("zwei\n")
                if mutate:
                    mutate(workspace)
                return {**common, "changed_files": ["app.txt"], "unconfirmed": []}
            status = {"PASS": "pass", "FAIL": "fail", "BLOCKED": "unverified"}[verdict]
            return {**common, "verdict": verdict, "findings": [], "criteria": [
                {"id": "ac-01", "status": status, "reason": "Datei gelesen",
                 "evidence": (workspace / "app.txt").read_text()}]}
        return runner, patch.object(runner, "agent", side_effect=agent)

    def test_complete_round_and_accept(self):
        state = self.approved()
        runner, mock_agent = self.run_fixture()
        with patch("transport.check_sandbox"), patch("transport.resolve", return_value={"target": "fixture"}), mock_agent:
            state = runner.run(state["revision"])
        self.assertEqual(state["phase"], "awaiting_acceptance")
        self.assertEqual((self.root / "app.txt").read_text(), "zwei\n")
        self.assertEqual(len(state["runs"]), 2)
        state = self.store.accept("Passt", state["revision"])
        self.assertEqual(state["phase"], "completed")

    def test_out_of_scope_write_not_applied(self):
        state = self.approved()
        runner, mock_agent = self.run_fixture(mutate=lambda p: (p / "other.txt").write_text("falsch"))
        with patch("transport.check_sandbox"), patch("transport.resolve", return_value={"target": "fixture"}), mock_agent:
            with self.assertRaises(Error):
                runner.run(state["revision"])
        self.assertFalse((self.root / "other.txt").exists())
        self.assertEqual((self.root / "app.txt").read_text(), "eins\n")
        self.assertEqual(self.store.load()["activity"], "blocked")

    def test_blocked_evaluation_retains_phase(self):
        state = self.approved()
        runner, mock_agent = self.run_fixture("BLOCKED")
        with patch("transport.check_sandbox"), patch("transport.resolve", return_value={"target": "fixture"}), mock_agent:
            state = runner.run(state["revision"])
        self.assertEqual(state["phase"], "evaluating")
        self.assertEqual(state["activity"], "blocked")
        with self.assertRaises(Error):
            runner.resume(state["revision"])

    def test_resume_rejects_live_owner(self):
        state = self.approved()
        def active(s):
            s.update(activity="running", runs=[{"id": "fixture", "status": "running",
                      "owner": identity(__import__("os").getpid()), "child": None}])
        state = self.store.change(state["revision"], "fixture", active)
        with self.assertRaises(Error):
            Runner(self.store).resume(state["revision"], "Erneut versuchen")

    def test_pause_and_cancel_idle(self):
        state = self.approved()
        runner = Runner(self.store)
        state = runner.stop("pause", state["revision"])
        self.assertEqual(state["activity"], "paused")
        state = runner.resume(state["revision"])
        self.assertEqual(state["activity"], "idle")
        state = runner.stop("cancel", state["revision"])
        self.assertEqual(state["phase"], "cancelled")

    def test_recheck_after_external_change(self):
        state = self.approved()
        runner, mock_agent = self.run_fixture()
        with patch("transport.check_sandbox"), patch("transport.resolve", return_value={"target": "fixture"}), mock_agent:
            state = runner.run(state["revision"])
        (self.root / "app.txt").write_text("anders\n")
        state = runner.reevaluate(state["revision"])
        self.assertEqual(state["phase"], "evaluating")
        self.assertIsNone(state["evaluation"])
