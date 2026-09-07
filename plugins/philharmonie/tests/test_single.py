import contextlib
import io
import json
from pathlib import Path
import shutil
import sys
import unittest
from unittest.mock import patch

from test_state import FixtureMixin
from common import Error
from philharmonie import main, parser
from single import DEFAULT_REVIEW, single


class SingleCase(FixtureMixin, unittest.TestCase):
    def invoke(self, target, mode="ask", handover="Prüfe app.txt", failure=None, cli=False):
        request = self.root / ".philharmonie/local/request.md"
        request.write_text(handover)
        argv = ["-C", str(self.root), mode, "--target", target,
                "--handover", str(request), "--allow", "app.txt"]
        args = parser().parse_args(argv)
        adapter = {"target": target, "model": "fixture", "effort": "high"}
        def command(actual, workspace, schema, output, profile, **kwargs):
            self.assertEqual(actual["target"], target)
            script = "import json, pathlib, sys; request=sys.stdin.read(); "
            if mode == "execute":
                script += f"pathlib.Path({str(workspace / 'app.txt')!r}).write_text('zwei\\n'); "
            if failure == "exit":
                script += "print('API abgelehnt', file=sys.stderr); sys.exit(7)"
            elif failure == "invalid":
                script += "print('kein JSON')"
            else:
                response = {"answer": "Geprüft: äöüß"}
                if target == "codex":
                    script += f"pathlib.Path({str(output)!r}).write_text({json.dumps(response)!r})"
                else:
                    script += f"print({json.dumps({'structured_output': response})!r})"
            return [sys.executable, "-c", script]
        stdout, stderr = io.StringIO(), io.StringIO()
        try:
            with patch("transport.resolve", return_value=adapter), patch("transport.check_sandbox"), \
                 patch("delegation.prepare", return_value={"roles": {"philharmonie-light": {"model": "fixture"}}}), \
                 patch("transport.command", side_effect=command), \
                 patch("transport.sandbox", side_effect=lambda work, scratch, argv, profile, **kwargs: argv), \
                 contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = main(argv) if cli else single(args)
        finally:
            self.console = stderr.getvalue()
            for line in stderr.getvalue().splitlines():
                if line.startswith("Protokoll: "):
                    self.artifacts = Path(line.removeprefix("Protokoll: "))
                    self.addCleanup(shutil.rmtree, self.artifacts, True)
        return code, stdout.getvalue()

    def test_both_targets_preserve_answer_and_execute_scope(self):
        for target in ("claude", "codex"):
            with self.subTest(target=target):
                code, answer = self.invoke(target)
                self.assertEqual((code, answer), (0, "Geprüft: äöüß\n"))
                code, answer = self.invoke(target, "execute")
                self.assertEqual(code, 0)
                self.assertEqual((self.root / "app.txt").read_text(), "zwei\n")
                self.assertTrue((self.artifacts / "apply.json").is_file())
                self.assertTrue((self.artifacts / "delegation-events.json").is_file())
                self.assertIn("philharmonie-light", (self.artifacts / "Handover.md").read_text())
                (self.root / "app.txt").write_text("eins\n")

    def test_cli_exit_code_and_partial_snapshot_are_preserved(self):
        code, _ = self.invoke("claude", "execute", failure="exit")
        self.assertEqual(code, 7)
        self.assertIn("API abgelehnt", (self.artifacts / "stderr.log").read_text())
        self.assertEqual((self.artifacts / "workspace/app.txt").read_text(), "zwei\n")
        self.assertEqual((self.root / "app.txt").read_text(), "eins\n")

    def test_invalid_json_retains_raw_response(self):
        with self.assertRaises(Error):
            self.invoke("claude", failure="invalid")
        self.assertEqual((self.artifacts / "stdout.log").read_text(), "kein JSON\n")

    def test_standard_review_and_mandatory_execute_handover(self):
        adapter = {"target": "codex", "model": "fixture", "effort": "high"}
        args = parser().parse_args(["-C", str(self.root), "ask", "--dry-run", "--target", "codex"])
        output = io.StringIO()
        with patch("sys.stdin", io.StringIO("")), patch("transport.resolve", return_value=adapter) as resolve, \
             contextlib.redirect_stdout(output):
            self.assertEqual(single(args), 0)
        resolve.assert_called_once_with("codex", None, "high")
        self.assertEqual(json.loads(output.getvalue())["handover"], DEFAULT_REVIEW)
        args.command = "execute"
        with patch("sys.stdin", io.StringIO("")), self.assertRaisesRegex(Error, "Handover"):
            single(args)
