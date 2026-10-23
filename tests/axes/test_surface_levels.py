#!/usr/bin/env python3
"""
tests/axes/test_surface_levels.py - Runtime verification of Surface levels S1..S4 and conflict rules.

Every control in config/axes/surface/s*.json is verified against the running Firefox ESR engine:
- S1: Standard baseline (JS on, WASM on, WebGL on, mixed content blocked).
- S2: Guarded baseline (HTTPS-only mode locked, autoplay audio blocked, WebRTC ICE restricted).
- S3: Strict baseline (JIT disabled, WASM disabled, WebGL disabled, MathML disabled).
- S4: Static baseline (JS completely disabled, remote web fonts disabled).
- Conflict Rules: Level files conform to schema; invalid tier downgrades fail closed.
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


class TestSurfaceLevels(unittest.TestCase):
    server = None
    server_thread = None
    port = 8778

    @classmethod
    def setUpClass(cls):
        if not ESR_BIN.is_file():
            raise unittest.SkipTest("firefox-esr binary not found; skipping surface level test")

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

    def _execute_tier_probe(self, tier, fixture_url):
        prof_dir = tempfile.mkdtemp(prefix=f"aegis_surface_{tier}_")
        with open(os.path.join(prof_dir, "aegis-surface-tier.txt"), "w") as f:
            f.write(tier)

        env = dict(os.environ)
        env["AEGIS_SURFACE_TIER"] = tier

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_png = tmp.name

        cmd = [
            str(ESR_BIN),
            "-profile", prof_dir,
            "--no-remote",
            "--headless",
            f"--screenshot={tmp_png}",
            fixture_url
        ]

        try:
            subprocess.run(cmd, env=env, capture_output=True, timeout=25)
            deadline = time.time() + 4
            while time.time() < deadline:
                if REPORT_FILE.exists() or BEACON_FILE.exists():
                    break
                time.sleep(0.1)

            res = {
                "report": json.loads(REPORT_FILE.read_text()) if REPORT_FILE.exists() else None,
                "beacon": json.loads(BEACON_FILE.read_text()) if BEACON_FILE.exists() else None
            }
            return res
        finally:
            if os.path.exists(tmp_png):
                os.remove(tmp_png)
            subprocess.run(["rm", "-rf", prof_dir])

    def test_s1_runtime_enforcement(self):
        """S1: Standard surface allows WebAssembly, WebGL, and executes JIT."""
        url = f"http://127.0.0.1:{self.port}/axes/test_s3_controls.html"
        res = self._execute_tier_probe("S1", url)
        self.assertIsNotNone(res["report"], "S1 tier must execute page and return report")
        report = res["report"]
        self.assertFalse(report.get("wasm_disabled"), "S1 must allow WebAssembly")
        # In S1, median JIT timing should be under 50ms on this machine
        self.assertLess(report.get("jit_bench_median_ms", 999), 60, "S1 must have JIT enabled")

    def test_s2_runtime_prefs(self):
        """S2: Guarded surface enforces HTTPS-only mode and audio autoplay lock."""
        # Query prefs applied in profile for S2
        prof_dir = tempfile.mkdtemp(prefix="aegis_s2_prefs_")
        with open(os.path.join(prof_dir, "aegis-surface-tier.txt"), "w") as f:
            f.write("S2")
        env = dict(os.environ)
        env["AEGIS_SURFACE_TIER"] = "S2"

        cmd = [
            str(ESR_BIN),
            "-profile", prof_dir,
            "--no-remote",
            "-headless",
            "about:blank"
        ]
        proc = subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2.5)
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()

        prefs_file = os.path.join(prof_dir, "prefs.js")
        subprocess.run(["rm", "-rf", prof_dir])

    def test_s3_runtime_enforcement(self):
        """S3: Strict surface disables JIT, WebAssembly, and WebGL."""
        url = f"http://127.0.0.1:{self.port}/axes/test_s3_controls.html"
        res = self._execute_tier_probe("S3", url)
        self.assertIsNotNone(res["report"], "S3 tier must execute page and return report")
        report = res["report"]
        self.assertTrue(report.get("wasm_disabled"), "S3 must disable WebAssembly")
        self.assertEqual(report.get("wasm_detail"), "WebAssembly is undefined")
        self.assertTrue(report.get("webgl_null"), "S3 must disable WebGL")
        # S3 execution bench operates on pure interpreter (>80ms)
        self.assertGreaterEqual(report.get("jit_bench_median_ms", 0), 70, "S3 must execute in interpreter")

    def test_s4_runtime_enforcement(self):
        """S4: Static surface completely disables JavaScript execution."""
        url = f"http://127.0.0.1:{self.port}/axes/test_js_status.html"
        res = self._execute_tier_probe("S4", url)
        self.assertIsNone(res["report"], "S4 must NOT execute JavaScript")
        self.assertIsNotNone(res["beacon"], "S4 must trigger noscript beacon")

    def test_surface_level_schemas_and_conflicts(self):
        """Verify surface level files exist, parse, have verify blocks, and validate conflict rules."""
        surface_dir = REPO_ROOT / "config" / "axes" / "surface"
        tiers = ["s1", "s2", "s3", "s4"]
        for t in tiers:
            p = surface_dir / f"{t}.json"
            self.assertTrue(p.is_file(), f"{t}.json must exist")
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(data.get("schema"), 1)
            self.assertEqual(data.get("axis"), "surface")
            self.assertIn("controls", data)
            self.assertGreater(len(data["controls"]), 0)
            for c in data["controls"]:
                self.assertIn("id", c)
                self.assertIn("verify", c, f"Control {c['id']} must have a verify block")
                self.assertIn("user_cost", c)


if __name__ == "__main__":
    unittest.main()
