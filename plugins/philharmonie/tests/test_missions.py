import os
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch

from test_state import FixtureMixin
from common import read_json, write_json
from runner import Runner


class DocumentMissionCase(FixtureMixin, unittest.TestCase):
    def mission(self, blocked=False):
        self.contract["allowed_paths"] = ["README.md"]
        self.contract["criteria"] = [{"id": "ac-01", "description": "README nennt den Startbefehl aus build.md",
                                     "verification": "Beide Dateien vollständig vergleichen"}]
        if not blocked:
            (self.root / "build.md").write_text("# Start\n\nnix run .\n")
        state = self.store.set_spec("# Spec\nREADME muss den Startbefehl der Quelle build.md nennen.",
                                    self.contract, 1)
        state = self.reviewed(state)
        state = self.store.approve("Dokumentiere den Startbefehl.", state["revision"])
        runner = Runner(self.store)
        verdicts = []
        def agent(role, state, run, directory, workspace, adapter, config, checks, discussion=None):
            base = {"role": role, "run_id": run["id"], "spec_hash": state["spec"]["hash"], "summary": "Dateivergleich"}
            if role == "generator":
                (workspace / "README.md").write_text("# Start\n" + ("nix run .\n" if state["round"] > 1 else "nix build .\n"))
                return {**base, "changed_files": ["README.md"], "unconfirmed": []}
            source = workspace / "build.md"
            verdict = "BLOCKED" if not source.exists() else (
                "PASS" if "nix run ." in (workspace / "README.md").read_text() else "FAIL")
            verdicts.append(verdict)
            return {**base, "verdict": verdict, "findings": [], "criteria": [{
                "id": "ac-01", "status": {"PASS": "pass", "FAIL": "fail", "BLOCKED": "unverified"}[verdict],
                "reason": "Startbefehl mit Originalquelle verglichen" if source.exists() else "Quelle fehlt",
                "evidence": source.read_text() if source.exists() else "build.md ist nicht vorhanden"}]}
        with patch("transport.check_sandbox"), patch("transport.resolve", return_value={"target": "fixture"}), \
             patch.object(runner, "agent", side_effect=agent):
            state = runner.run(state["revision"])
        return state, verdicts

    def test_document_fail_then_pass_with_source(self):
        state, verdicts = self.mission()
        self.assertIn("FAIL", verdicts)
        self.assertEqual(verdicts[-1], "PASS")
        self.assertEqual(state["round"], 2)
        self.assertEqual(self.store.accept("Das passt.", state["revision"])["phase"], "completed")

    def test_document_missing_source_is_blocked(self):
        state, verdicts = self.mission(blocked=True)
        self.assertEqual(set(verdicts), {"BLOCKED"})
        self.assertEqual((state["phase"], state["activity"]), ("evaluating", "blocked"))


@unittest.skipUnless(os.environ.get("PHILHARMONIE_INTEGRATION") == "1",
                     "Explizite Sandbox-Prüfung mit Nix und Shellcheck erforderlich")
class BashMissionCase(FixtureMixin, unittest.TestCase):
    def mission(self, blocked=False):
        executable = shutil.which("shellcheck")
        self.assertIsNotNone(executable, "Shellcheck muss in der Nix-Entwicklungsumgebung vorhanden sein")
        package = str(Path(executable).resolve().parents[1])
        self.contract["allowed_paths"] = ["hello.sh"]
        self.contract["criteria"] = [{"id": "ac-01", "description": "Skript gibt Hallo aus und besteht Shellcheck",
                                     "verification": "Shellcheck und Laufzeittest"}]
        self.contract["checks"] = [{"id": "shellcheck", "argv": ["nix", "--offline", "shell", package, "-c", "bash", "-c",
            "set -euo pipefail\nshellcheck --version\nshellcheck hello.sh\ntest \"$(bash hello.sh)\" = Hallo"]}]
        state = self.store.set_spec("# Spec\nShellcheck und Ausgabe Hallo nachweisen.", self.contract, 1)
        state = self.reviewed(state)
        state = self.store.approve("Skript bauen und in Nix prüfen.", state["revision"])
        config = self.store.config()
        config["check_nix_daemon"] = True
        write_json(self.store.base / "config.json", config)
        runner = Runner(self.store)
        def agent(role, state, run, directory, workspace, adapter, config, checks, discussion=None):
            base = {"role": role, "run_id": run["id"], "spec_hash": state["spec"]["hash"], "summary": "Shellcheck und Ausgabe geprüft"}
            if role == "generator":
                text = "#!/usr/bin/env bash\nset -euo pipefail\n"
                text += "printf '%s\\n' Hallo\n" if blocked or state["round"] > 1 else "printf '%s\\n' $missing\n"
                (workspace / "hello.sh").write_text(text)
                return {**base, "changed_files": ["hello.sh"], "unconfirmed": []}
            self.assertEqual(len(checks), 1)
            self.assertEqual(checks[0]["tool_version"]["exit_code"], 0)
            verdict = "BLOCKED" if blocked else "FAIL" if checks[0]["exit_code"] else "PASS"
            return {**base, "verdict": verdict, "findings": [], "criteria": [{
                "id": "ac-01", "status": {"PASS": "pass", "FAIL": "fail", "BLOCKED": "unverified"}[verdict],
                "reason": "Zusätzliche fachliche Quelle fehlt" if blocked else "Shellcheck und Laufzeittest",
                "evidence": "Fachliche Quelle nicht verfügbar" if blocked else checks[0]["stdout"] + checks[0]["stderr"]}]}
        with patch("transport.resolve", return_value={"target": "fixture"}), patch.object(runner, "agent", side_effect=agent):
            state = runner.run(state["revision"])
        return state

    def test_bash_fail_then_pass_with_real_shellcheck(self):
        state = self.mission()
        self.assertEqual(state["phase"], "awaiting_acceptance")
        self.assertEqual(state["round"], 2)
        reports = [read_json(self.root / r["report"]) for r in state["runs"] if r["role"] == "evaluator"]
        self.assertEqual([r["result"]["verdict"] for r in reports], ["FAIL", "PASS"])
        self.assertEqual(self.store.accept("Skript geprüft.", state["revision"])["phase"], "completed")

    def test_bash_missing_evidence_stays_blocked_after_green_check(self):
        state = self.mission(blocked=True)
        self.assertEqual((state["phase"], state["activity"]), ("evaluating", "blocked"))
        report = read_json(self.root / state["runs"][-1]["report"])
        self.assertEqual(report["checks"][0]["exit_code"], 0)
