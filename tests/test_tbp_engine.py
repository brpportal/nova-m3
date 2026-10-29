import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from nova.engines.tbp import TbpEngine
from nova.session import LOGGED_IN, check_session

FAKE = os.path.join(os.path.dirname(__file__), "fake_tbp.py")


class TestTbpEngineEnvelope(unittest.TestCase):
    """Regression tests for the real TBP daemon envelope (v1.0.2 fix):
    status/eval results live under {"success": true, "data": {...}}."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.state = os.path.join(self.tmp, "state.json")
        os.environ["FAKE_TBP_STATE"] = self.state
        self.engine = TbpEngine(binary=f"{sys.executable} {FAKE}".split()[0],
                                timeout=15)
        # TbpEngine runs [binary, *args]; point it at the stub via a wrapper:
        self.wrapper = os.path.join(self.tmp, "tbp")
        with open(self.wrapper, "w") as fh:
            fh.write(f"#!/bin/sh\nexec {sys.executable} {FAKE} \"$@\"\n")
        os.chmod(self.wrapper, 0o755)
        self.engine = TbpEngine(binary=self.wrapper, timeout=15)

    def test_is_running_true_when_daemon_up(self):
        self.assertTrue(self.engine.is_running())

    def test_is_running_false_when_daemon_down(self):
        self.engine.stop()
        self.assertFalse(self.engine.is_running())

    def test_current_url_from_eval_result(self):
        self.assertEqual(self.engine.current_url(), "https://www.facebook.com/")

    def test_navigate_then_url(self):
        self.engine.navigate("https://www.facebook.com/SomePage")
        self.assertEqual(self.engine.current_url(),
                         "https://www.facebook.com/SomePage")

    def test_page_html(self):
        self.assertIn("/posts/123456789", self.engine.page_html())

    def test_session_logged_in(self):
        state, _ = check_session(self.engine)
        self.assertEqual(state, LOGGED_IN)

    def test_navigate_tolerates_goto_timeout_when_page_loaded(self):
        os.environ["FAKE_TBP_GOTO_TIMEOUT"] = "1"
        try:
            warning = self.engine.navigate("https://www.facebook.com/SomePage")
        finally:
            del os.environ["FAKE_TBP_GOTO_TIMEOUT"]
        self.assertIsNotNone(warning)
        self.assertIn("timed out", warning)
        self.assertEqual(self.engine.current_url(),
                         "https://www.facebook.com/SomePage")


if __name__ == "__main__":
    unittest.main()
