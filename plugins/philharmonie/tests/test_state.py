import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from common import Error, digest, fingerprint, identity, alive, write_preflight
from state import SPEC_POINTS, Store, spec_review_source, validate_result


class FixtureMixin:
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git("init", "-b", "feature/test")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Test")
        (self.root / "app.txt").write_text("eins\n")
        self.git("add", "app.txt")
        self.git("commit", "-m", "Testbasis")
        self.store = Store(self.root, "test")
        self.store.create("Ändere app.txt")
        self.contract = {"criteria": [{"id": "ac-01", "description": "Text stimmt",
                                       "verification": "Datei vollständig lesen"}],
                         "allowed_paths": ["app.txt"], "checks": []}

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args], check=True,
                              capture_output=True).stdout

    def approved(self):
        state = self.store.set_spec("# Spec\n\nZiel: zwei\n", self.contract, 1)
        state = self.reviewed(state)
        return self.store.approve("Implementiere diese Spec.", state["revision"])

    def spec_review_data(self, state):
        source = spec_review_source(state, uuid.uuid4().hex, fingerprint(self.root)["hash"])
        result = {key: source[key] for key in
                  ("run_id", "spec_revision", "spec_hash", "contract_hash", "fingerprint")}
        result.update(role="spec_reviewer", summary="Spec anhand der Testquellen geprüft",
                      scores={key: {"points": maximum, "reason": "Auftrag vollständig abgegrenzt",
                                    "evidence": "Spec.md und app.txt vollständig gelesen"}
                              for key, maximum in SPEC_POINTS.items()}, blockers=[], questions=[])
        adapter = {"target": source["reviewer_cli"], "version": "fixture", "model": "fixture", "effort": "high"}
        return result, adapter, source

    def reviewed(self, state):
        result, adapter, source = self.spec_review_data(state)
        return self.store.record_spec_review(result, adapter, source, state["revision"])

    def result(self):
        return {"role": "evaluator", "summary": "Geprüft", "verdict": "PASS",
                "criteria": [{"id": "ac-01", "status": "pass", "reason": "Text stimmt",
                              "evidence": "app.txt:1 enthält zwei"}], "findings": []}


class MissionCase(FixtureMixin, unittest.TestCase):
    def test_spec_revision_authorization(self):
        state = self.approved()
        self.assertEqual(state["phase"], "implementing")
        self.assertEqual(state["authorization"]["spec_hash"], state["spec"]["hash"])
        state = self.store.replan("Anderer Text", state["revision"])
        state = self.store.set_spec("# Neue Spec\n", self.contract, state["revision"])
        self.assertEqual(state["spec"]["revision"], 2)
        self.assertIsNone(state["authorization"])
        self.assertTrue((self.store.doc / "specs/1.md").exists())

    def test_stale_revision_does_not_mutate(self):
        before = self.store.path.read_bytes()
        with self.assertRaises(Error):
            self.store.set_spec("Spec", self.contract, 0)
        self.assertEqual(before, self.store.path.read_bytes())

    def test_external_spec_edit_rejected(self):
        state = self.approved()
        (self.store.doc / "Spec.md").write_text("Andere Kriterien")
        with self.assertRaises(Error):
            self.store.check_spec(state)

    def test_missing_duplicate_and_false_pass(self):
        state = self.approved()
        for mutation in (lambda r: r.update(criteria=[]),
                         lambda r: r["criteria"].append(copy.deepcopy(r["criteria"][0])),
                         lambda r: r["criteria"][0].update(status="unverified"),
                         lambda r: r["criteria"][0].update(evidence="")):
            result = self.result()
            mutation(result)
            with self.assertRaises(Error):
                validate_result(result, "evaluator", state)

    def test_accept_requires_current_verified_state(self):
        state = self.approved()
        with self.assertRaises(Error):
            self.store.accept("Passt", state["revision"])
        result = self.result()
        result["fingerprint"] = fingerprint(self.root)["hash"]
        report = self.store.doc / "evaluation.json"
        report.write_text(json.dumps(result))
        state = self.store.change(state["revision"], "fixture", lambda s: s.update(
            phase="awaiting_acceptance", evaluation=result, runs=[{
                "id": "fixture", "status": "succeeded", "owner": None, "child": None,
                "report": str(report.relative_to(self.root)),
                "report_hash": digest(report.read_bytes())}]))
        (self.root / "untracked.txt").write_text("Neue Anforderung")
        with self.assertRaises(Error):
            self.store.accept("Passt", state["revision"])
        (self.root / "untracked.txt").unlink()
        state = self.store.accept("Passt", state["revision"])
        self.assertEqual(state["phase"], "completed")
        self.assertTrue((self.store.doc / "Summary.md").exists())
        with self.assertRaises(Error):
            self.store.replan("Weiter", state["revision"])

    def test_dirty_paths_and_main(self):
        (self.root / "app.txt").write_text("fremd")
        with self.assertRaises(Error):
            write_preflight(self.root, ["app.txt"])
        write_preflight(self.root, ["app.txt"], ["app.txt"])
        self.git("branch", "-m", "main")
        with self.assertRaises(Error):
            write_preflight(self.root, ["app.txt"], ["app.txt"])

    def test_path_escape_and_symlink(self):
        for path in ("../escape", "/tmp/escape", ".git", ".philharmonie", "."):
            contract = copy.deepcopy(self.contract)
            contract["allowed_paths"] = [path]
            with self.assertRaises(Error):
                self.store.set_spec("Spec", contract, 1)
        (self.root / "link").symlink_to("/tmp", target_is_directory=True)
        with self.assertRaises(Error):
            write_preflight(self.root, ["link/file"])

    def test_identity_detects_reused_pid(self):
        record = identity(os.getpid())
        self.assertTrue(alive(record))
        record["start"] = "-1"
        self.assertFalse(alive(record))


if __name__ == "__main__":
    unittest.main()
