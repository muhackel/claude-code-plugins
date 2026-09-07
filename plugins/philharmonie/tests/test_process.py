import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import unittest

from test_state import FixtureMixin
from common import Error, identity
from runner import Runner, stop_process


class ProcessCase(FixtureMixin, unittest.TestCase):
    def test_pause_terminates_process_subtree(self):
        state = self.approved()
        run = {"id": "process", "status": "prepared", "owner": identity(os.getpid()), "child": None}
        self.store.change(state["revision"], "fixture", lambda s: s.update(activity="running", runs=[run]))
        marker = self.store.local / "late-write"
        ready = self.store.local / "ready"
        child = f"import time; from pathlib import Path; time.sleep(1); Path({str(marker)!r}).touch()"
        parent = (f"import subprocess, sys, time; from pathlib import Path; "
                  f"subprocess.Popen([sys.executable, '-c', {child!r}]); "
                  f"Path({str(ready)!r}).touch(); time.sleep(10)")
        runner = Runner(self.store)
        errors = []
        def pause():
            try:
                deadline = time.monotonic() + 5
                while not ready.exists() and time.monotonic() < deadline:
                    time.sleep(0.02)
                if not ready.exists():
                    raise AssertionError("Testprozess nicht gestartet")
                runner.stop("pause", self.store.load()["revision"])
            except Exception as exc:
                errors.append(exc)
        watcher = threading.Thread(target=pause)
        watcher.start()
        with self.assertRaisesRegex(Error, "angehalten"):
            runner.execute_child(run, [sys.executable, "-c", parent], "", self.store.local / "process",
                                 {"timeout_seconds": 10})
        watcher.join(timeout=5)
        self.assertFalse(watcher.is_alive())
        self.assertFalse(errors, errors)
        time.sleep(1.1)
        self.assertFalse(marker.exists())

    def test_another_process_owns_checkout_lock(self):
        state = self.approved()
        ready = self.store.local / "locked"
        script = (f"import sys, time; from pathlib import Path; sys.path.insert(0, {str(Path(__file__).resolve().parents[1] / 'scripts')!r}); "
                  f"from common import lock; guard=lock(Path({str(self.store.edit_lock)!r})); "
                  f"guard.__enter__(); Path({str(ready)!r}).touch(); time.sleep(10)")
        process = subprocess.Popen([sys.executable, "-c", script], start_new_session=True)
        try:
            deadline = time.monotonic() + 5
            while not ready.exists() and process.poll() is None and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue(ready.exists())
            with self.assertRaises(Error):
                Runner(self.store).one(state["revision"])
            self.assertFalse(self.store.load()["runs"])
        finally:
            stop_process(process)
