import unittest
from unittest.mock import patch

from test_state import FixtureMixin
from common import Error, fingerprint, write_json
from runner import Runner
from state import Store
import snapshot


class RegressionCase(FixtureMixin, unittest.TestCase):
    def test_mission_keeps_configuration_and_rejects_changed_adapter(self):
        state = self.approved()
        runner = Runner(self.store)
        adapter = {"target": "claude", "model": "pinned", "effort": "high", "version": "1"}
        result = {"role": "generator", "summary": "Kein Änderungsbedarf", "changed_files": [], "unconfirmed": []}
        with patch("transport.check_sandbox"), patch("transport.resolve", return_value=adapter), \
             patch.object(runner, "agent", return_value=result):
            state = runner.one(state["revision"])
        original = state["configuration"]
        write_json(self.store.base / "config.json", {**original, "evaluator": "codex", "model": "anderes-modell"})
        self.assertEqual(self.store.load()["configuration"], original)
        with patch("transport.resolve", return_value={**adapter, "version": "2"}), \
             self.assertRaisesRegex(Error, "CLI-Vertrag"):
            runner.adapter("generator", "auto", original)
        state = self.store.replan("Neue CLI-Version ausdrücklich prüfen.", self.store.load()["revision"])
        self.assertNotIn("adapters", state)
        self.assertNotIn("configuration", state)

    def test_worktrees_keep_separate_runtime_and_snapshots(self):
        worktree = self.root / ".philharmonie/local/other-worktree"
        self.git("worktree", "add", "-b", "feature/parallel", str(worktree))
        store = Store(worktree, "test")
        store.create("Separater Auftrag")
        self.assertNotEqual(store.run_lock, self.store.run_lock)
        (worktree / "app.txt").write_text("Paralleländerung\n")
        self.git("-C", str(worktree), "add", "app.txt")
        baseline = fingerprint(worktree)
        captured = snapshot.capture(worktree, store.local / "snapshot", baseline)
        self.assertEqual((captured / "app.txt").read_text(), "Paralleländerung\n")
        self.assertEqual(fingerprint(captured)["index"], baseline["index"])
        self.assertEqual((self.root / "app.txt").read_text(), "eins\n")

    def test_cancel_after_supervisor_death_is_terminal(self):
        state = self.approved()
        state = self.store.change(state["revision"], "fixture", lambda s: s.update(
            activity="running", runs=[{"id": "dead", "status": "running", "owner": None, "child": None}]))
        state = Runner(self.store).stop("cancel", state["revision"])
        self.assertEqual(state["phase"], "cancelled")
        self.assertEqual(state["runs"][-1]["status"], "cancelled")

    def test_resume_finishes_pending_cancel(self):
        state = self.approved()
        state = self.store.change(state["revision"], "fixture", lambda s: s.update(
            activity="running", stop_requested="cancel", runs=[{
                "id": "dead", "status": "running", "owner": None, "child": None}]))
        state = Runner(self.store).resume(state["revision"])
        self.assertEqual(state["phase"], "cancelled")
        self.assertEqual(state["runs"][-1]["status"], "cancelled")

    def test_late_stop_never_applies(self):
        state = self.approved()
        runner = Runner(self.store)
        def agent(role, state, run, directory, workspace, adapter, config, checks, discussion=None):
            (workspace / "app.txt").write_text("nach Pause")
            runner.stop("pause", self.store.load()["revision"])
            return {"role": role, "summary": "Geändert", "changed_files": ["app.txt"], "unconfirmed": []}
        with patch("transport.check_sandbox"), patch("transport.resolve", return_value={"target": "fixture"}), \
             patch.object(runner, "agent", side_effect=agent):
            with self.assertRaises(Error):
                runner.one(state["revision"])
        self.assertEqual((self.root / "app.txt").read_text(), "eins\n")
        self.assertEqual(self.store.load()["activity"], "paused")

    def test_ignore_change_preserves_untracked_file(self):
        (self.root / "draft.txt").write_text("Nutzerentwurf")
        baseline = fingerprint(self.root)
        work = snapshot.capture(self.root, self.store.local / "snapshot", baseline)
        (work / ".gitignore").write_text("draft.txt\n")
        changed = snapshot.apply(self.root, work, baseline, [".gitignore", "draft.txt"],
                                 self.store.local / "apply.json")
        self.assertEqual(changed, [".gitignore"])
        self.assertEqual((self.root / "draft.txt").read_text(), "Nutzerentwurf")

    def test_foreign_mode_change_is_not_overwritten(self):
        baseline = fingerprint(self.root)
        work = snapshot.capture(self.root, self.store.local / "snapshot", baseline)
        (work / "app.txt").write_text("neu")
        def mode_race():
            (self.root / "app.txt").chmod(0o700)
        with self.assertRaises(Error):
            snapshot.apply(self.root, work, baseline, ["app.txt"], self.store.local / "apply.json", mode_race)
        self.assertEqual((self.root / "app.txt").read_text(), "eins\n")

    def test_budget_is_a_blocker(self):
        state = self.approved()
        state = self.store.change(state["revision"], "fixture", lambda s: s.update(round=3))
        state = Runner(self.store).one(state["revision"])
        self.assertEqual(state["activity"], "blocked")
        self.assertFalse(state["runs"])

    def test_pause_during_planning_can_resume(self):
        runner = Runner(self.store)
        state = runner.stop("pause", 1)
        state = runner.resume(state["revision"])
        self.assertEqual(state["phase"], "planning")
        self.assertEqual(state["activity"], "idle")
