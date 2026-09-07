import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_state import FixtureMixin
from common import Error, fingerprint
import snapshot
import transport


@unittest.skipUnless(os.environ.get("PHILHARMONIE_INTEGRATION") == "1",
                     "Explizite lokale Sandbox-Integration erforderlich")
class SandboxCase(FixtureMixin, unittest.TestCase):
    def invoke(self, profile, script, extra=()):
        baseline = fingerprint(self.root)
        directory = self.store.local / ("probe-" + str(len(list(self.store.local.iterdir()))))
        work = snapshot.capture(self.root, directory / "workspace", baseline)
        schema = directory / "primary/schema.json"
        schema.parent.mkdir()
        schema.write_text("{}")
        args = transport.sandbox(work, directory / "primary/scratch",
            [sys.executable, "-c", script, str(schema), *map(str, extra)], profile, auth=False)
        return subprocess.run(args, env=transport.environment(), capture_output=True, text=True)

    def test_readonly_workspace_schema_and_git(self):
        result = self.invoke("verify", """
import pathlib, subprocess, sys
assert pathlib.Path(sys.argv[1]).read_text() == '{}'
assert subprocess.run(['git','log','-1','--format=%s'], capture_output=True).returncode == 0
try:
    pathlib.Path('app.txt').write_text('falsch')
except OSError:
    pass
else:
    raise AssertionError('Quellen sind schreibbar')
""")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_real_credentials_not_visible_without_auth(self):
        paths = [Path.home() / ".codex/auth.json", Path.home() / ".claude/.credentials.json"]
        result = self.invoke("verify", """
from pathlib import Path
import sys
for name in sys.argv[2:]:
    assert not Path(name).exists(), 'Host-Anmeldung sichtbar'
""", paths)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_edit_cannot_write_original_or_git(self):
        result = self.invoke("edit", """
from pathlib import Path
import sys
Path('app.txt').write_text('Snapshot')
assert not Path(sys.argv[2]).exists(), 'Originalprojekt ist sichtbar'
for target in [Path('.git/config')]:
    try:
        target.write_text('falsch')
    except OSError:
        pass
    else:
        raise AssertionError('Original oder Git ist schreibbar')
""", [self.root / "app.txt"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.root / "app.txt").read_text(), "eins\n")


@unittest.skipUnless(os.environ.get("PHILHARMONIE_LIVE") == "1",
                     "Expliziter Test mit beiden authentifizierten CLIs erforderlich")
class LiveCase(FixtureMixin, unittest.TestCase):
    def test_claude_generator_codex_evaluator(self):
        self.live_round("claude", "codex")

    def test_codex_generator_claude_evaluator(self):
        self.live_round("codex", "claude")

    def live_round(self, generator, evaluator):
        from runner import Runner
        from common import write_json
        state = self.approved()
        config = self.store.config()
        config.update(generator=generator, evaluator=evaluator, timeout_seconds=240)
        write_json(self.store.base / "config.json", config)
        try:
            state = Runner(self.store).run(state["revision"])
        except Error as exc:
            details = []
            for log in (self.store.local / "runs").glob("*/primary/*"):
                if log.name in ("stderr.log", "stdout.log"):
                    details.append(f"{log.name}: {log.read_text(errors='replace')[:4000]}")
            raise AssertionError(str(exc) + "\n" + "\n".join(details)) from exc
        self.assertEqual(state["phase"], "awaiting_acceptance")
        self.assertEqual((self.root / "app.txt").read_text().strip(), "zwei")
        state = self.store.accept("Das Testziel ist erreicht.", state["revision"])
        self.assertEqual(state["phase"], "completed")


if __name__ == "__main__":
    unittest.main()
