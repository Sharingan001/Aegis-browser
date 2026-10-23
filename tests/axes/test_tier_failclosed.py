#!/usr/bin/env python3
"""
tests/axes/test_tier_failclosed.py - Runtime verification of fail-closed tier enforcement.

Verifies:
1. Unset AEGIS_SURFACE_TIER fails closed to S4 (JavaScript disabled, noscript beacon received).
2. Invalid/unrecognized AEGIS_SURFACE_TIER fails closed to S4.
3. Mismatched AEGIS_SURFACE_TIER (env != profile token) fails closed to S4.
4. Authorized valid tier (S1) runs with JavaScript enabled.
"""

import http.server
import json
import os
import pathlib
import subprocess
import tempfile
import threading
import time
import unittest
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
ESR_BIN = REPO_ROOT / "firefox-esr" / "firefox"
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures"
REPORT_FILE = FIXTURES_DIR / "output" / "s3_report.json"
BEACON_FILE = FIXTURES_DIR / "output" / "noscript_beacon.json"

sys.path.insert(0, str(REPO_ROOT / "tests" / "tools"))
from local_test_server import FixtureHandler


class TestTierFailClosed(unittest.TestCase):
    server = None
    server_thread = None
    port = 8775

    @classmethod
    def setUpClass(cls):
        if not ESR_BIN.is_file():
            raise unittest.SkipTest("firefox-esr binary not found; skipping fail-closed test")

        cls.server = http.server.HTTPServer(("127.0.0.1", cls.port), FixtureHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        if cls.server:
            cls.server.shutdown()

    def setUp(self):
        for f in [REPORT_FILE, BEACON_FILE]:
            if f.exists():
                f.unlink()

    def _run_browser_probe(self, env_tier=None, profile_tier=None):
        for f in [REPORT_FILE, BEACON_FILE]:
            if f.exists():
                f.unlink()
        prof_dir = tempfile.mkdtemp(prefix="aegis_failclosed_")
        if profile_tier:
            with open(os.path.join(prof_dir, "aegis-surface-tier.txt"), "w") as f:
                f.write(profile_tier)
            with open(os.path.join(prof_dir, "user.js"), "w") as f:
                f.write(f'user_pref("aegis.profile.tier", "{profile_tier}");\n')

        env = dict(os.environ)
        if env_tier is not None:
            env["AEGIS_SURFACE_TIER"] = env_tier
        else:
            env.pop("AEGIS_SURFACE_TIER", None)

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_png = tmp.name

        url = f"http://127.0.0.1:{self.port}/axes/test_js_status.html"
        cmd = [
            str(ESR_BIN),
            "-profile", prof_dir,
            "--no-remote",
            "--headless",
            f"--screenshot={tmp_png}",
            url
        ]

        try:
            subprocess.run(cmd, env=env, capture_output=True, timeout=20)
            deadline = time.time() + 4
            while time.time() < deadline:
                if REPORT_FILE.exists() or BEACON_FILE.exists():
                    break
                time.sleep(0.1)

            res = {
                "script_report": json.loads(REPORT_FILE.read_text()) if REPORT_FILE.exists() else None,
                "noscript_beacon": json.loads(BEACON_FILE.read_text()) if BEACON_FILE.exists() else None
            }
            return res
        finally:
            if os.path.exists(tmp_png):
                os.remove(tmp_png)
            subprocess.run(["rm", "-rf", prof_dir])

    def test_unset_tier_fails_closed_to_s4(self):
        """Unset tier must fail closed to S4 (JavaScript disabled, noscript beacon triggered)."""
        res = self._run_browser_probe(env_tier=None, profile_tier=None)
        self.assertIsNone(res["script_report"], "JavaScript must NOT execute when tier is unset")
        self.assertIsNotNone(res["noscript_beacon"], "Noscript beacon must trigger when tier is unset")

    def test_invalid_tier_fails_closed_to_s4(self):
        """Invalid tier value must fail closed to S4."""
        res = self._run_browser_probe(env_tier="UNKNOWN_HACK", profile_tier=None)
        self.assertIsNone(res["script_report"], "JavaScript must NOT execute on invalid tier")
        self.assertIsNotNone(res["noscript_beacon"], "Noscript beacon must trigger on invalid tier")

    def test_mismatched_tier_fails_closed_to_s4(self):
        """Mismatched tier (env != profile token) must fail closed to S4."""
        res = self._run_browser_probe(env_tier="S1", profile_tier="S3")
        self.assertIsNone(res["script_report"], "JavaScript must NOT execute on tier mismatch")
        self.assertIsNotNone(res["noscript_beacon"], "Noscript beacon must trigger on tier mismatch")

    def test_valid_tier_s1_executes_javascript(self):
        """Authorized S1 tier must execute JavaScript and post report."""
        res = self._run_browser_probe(env_tier="S1", profile_tier="S1")
        self.assertIsNotNone(res["script_report"], "JavaScript must execute on authorized S1 tier")
        self.assertTrue(res["script_report"].get("js_enabled"))
        self.assertIsNone(res["noscript_beacon"], "Noscript beacon must not trigger on S1")

    def test_profile_only_tier_without_env_var(self):
        """Profile tier setting (user.js) must be read via getPref in aegis.cfg when env var is unset."""
        # 1. Profile specifies S1 with NO environment variable
        res_s1 = self._run_browser_probe(env_tier=None, profile_tier="S1")
        self.assertIsNotNone(res_s1["script_report"], "S1 profile without env var must execute JavaScript")
        self.assertTrue(res_s1["script_report"].get("js_enabled"))
        self.assertTrue(res_s1["script_report"].get("wasm_present"))
        self.assertTrue(res_s1["script_report"].get("webgl_present"))
        self.assertIsNone(res_s1["noscript_beacon"])

        # 2. Profile specifies S4 with NO environment variable
        res_s4 = self._run_browser_probe(env_tier=None, profile_tier="S4")
        self.assertIsNone(res_s4["script_report"], "S4 profile without env var must NOT execute JavaScript")
        self.assertIsNotNone(res_s4["noscript_beacon"], "S4 profile without env var must trigger noscript beacon")


if __name__ == "__main__":
    unittest.main()

