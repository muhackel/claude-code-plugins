import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from common import Error
from transport import command, decode


class TransportCase(unittest.TestCase):
    def test_exact_structured_output_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            schema = Path(directory) / "schema.json"
            schema.write_text('{"type":"object"}')
            for target in ("claude", "codex"):
                adapter = {"target": target, "executable": target,
                           "model": "explicit-model", "effort": "high"}
                argv = command(adapter, Path(directory), schema, Path(directory) / "out", "inspect")
                self.assertIn("explicit-model", argv)
                if target == "codex":
                    self.assertEqual(argv[-1], "-")
                    self.assertIn("read-only", argv)
                    self.assertIn(str(schema), argv)
                else:
                    self.assertIn(schema.read_text(), argv)
                    self.assertIn("--safe-mode", argv)
                    self.assertNotIn("--bare", argv)
                    allowed = argv[argv.index("--allowedTools") + 1]
                    self.assertIn("Bash(git diff:*)", allowed)
                    self.assertNotIn("Bash", allowed.split(","))

    def test_no_text_fallback_for_claude(self):
        for payload in ({"result": "PASS"}, {"is_error": True, "structured_output": {}}, {}, [], None):
            with self.assertRaises(Error):
                decode({"target": "claude"}, json.dumps(payload), None)
        expected = {"verdict": "BLOCKED"}
        self.assertEqual(decode({"target": "claude"}, json.dumps(
            {"structured_output": expected}), None), expected)

    def test_empty_or_missing_success_response_is_protocol_error(self):
        for stdout in ("", "{", "PASS"):
            with self.assertRaises(Error):
                decode({"target": "claude"}, stdout, None)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "missing.json"
            with self.assertRaises(Error):
                decode({"target": "codex"}, "", output)
            output.write_text("")
            with self.assertRaises(Error):
                decode({"target": "codex"}, "", output)

    def test_start_barrier_closes_without_execution(self):
        import os
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "started"
            read_fd, write_fd = os.pipe()
            child = subprocess.Popen([sys.executable,
                str(Path(__file__).resolve().parents[1] / "scripts/launch.py"), str(read_fd),
                sys.executable, "-c", "from pathlib import Path; Path(__import__('sys').argv[1]).touch()",
                str(marker)], pass_fds=(read_fd,))
            os.close(read_fd)
            os.close(write_fd)
            self.assertEqual(child.wait(timeout=10), 125)
            self.assertFalse(marker.exists())


if __name__ == "__main__":
    unittest.main()
