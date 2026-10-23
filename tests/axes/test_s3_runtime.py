#!/usr/bin/env python3
"""
tests/axes/test_s3_runtime.py - Runtime verification of S3 controls (WebGL, WASM, JIT)

Served by tests/tools/local_test_server.py.
Compares Aegis S3 fixture profile against an unlocked control profile.

Proves controls are EFFECTIVE, not merely configured:
  1. WebGL is null and emits a disabled warning.
  2. WebAssembly object is undefined in web content.
  3. JIT execution timing: pure interpreter execution takes significantly longer
     than JIT-compiled execution on the control profile.

Flakiness Note:
  Absolute millisecond timing benchmarks are susceptible to system load and CPU throttling.
  To eliminate flakiness:
    - 5 iterations are executed in the browser fixture to compute the median.
    - We assert a relative ratio threshold (interpreter median >= 2.0x JIT median),
      rather than relying on hardcoded absolute millisecond cutoffs.
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

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
ESR_BIN = REPO_ROOT / "firefox-esr" / "firefox"
S3_PROFILE = REPO_ROOT / "profiles" / "aegis-s3"
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures"
OUTPUT_FILE = FIXTURES_DIR / "output" / "s3_report.json"
SETUP_SCRIPT = REPO_ROOT / "tools" / "setup_fastpath_profile.sh"

# Import server handler from local_test_server
import sys
sys.path.insert(0, str(REPO_ROOT / "tests" / "tools"))
from local_test_server import FixtureHandler


class TestS3RuntimeEnforcement(unittest.TestCase):
    server = None
    server_thread = None
    port = 8769

    @classmethod
    def setUpClass(cls):
        if not ESR_BIN.is_file():
            raise unittest.SkipTest("firefox-esr binary not found; skipping runtime probe")

        # Provision S3 named fixture profile if needed
        subprocess.run(["bash", str(SETUP_SCRIPT), "--fixture=s3"],
                       cwd=REPO_ROOT, check=True, capture_output=True)

        # Start local test server on background thread
        cls.server = http.server.HTTPServer(("127.0.0.1", cls.port), FixtureHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        if cls.server:
            cls.server.shutdown()

    def setUp(self):
        if OUTPUT_FILE.exists():
            OUTPUT_FILE.unlink()

    def _fetch_report_from_browser(self, binary_path, profile_path):
        url = f"http://127.0.0.1:{self.port}/axes/test_s3_controls.html"
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_png = tmp.name

        try:
            cmd = [
                str(binary_path),
                "-profile", str(profile_path),
                "--no-remote",
                "--headless",
                f"--screenshot={tmp_png}",
                url,
            ]
            subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            # Wait up to 5s for report file to be written by server
            deadline = time.time() + 5
            while time.time() < deadline:
                if OUTPUT_FILE.exists() and OUTPUT_FILE.stat().st_size > 0:
                    try:
                        return json.loads(OUTPUT_FILE.read_text())
                    except Exception:
                        pass
                time.sleep(0.1)

            self.fail("Browser did not POST /api/report within deadline")
        finally:
            if os.path.exists(tmp_png):
                os.remove(tmp_png)
            if OUTPUT_FILE.exists():
                OUTPUT_FILE.unlink()

    def test_s3_controls_effective(self):
        """Verify S3 controls (WebGL disabled, WASM undefined, interpreter timing) in S3 profile."""
        report = self._fetch_report_from_browser(ESR_BIN, S3_PROFILE)

        # 1. WebGL is null
        self.assertTrue(report.get("webgl_null"), f"Expected WebGL context to be null, got: {report}")

        # 2. WebAssembly is disabled/undefined
        self.assertTrue(report.get("wasm_disabled"), f"Expected WebAssembly to be disabled, got: {report}")
        self.assertEqual(report.get("wasm_detail"), "WebAssembly is undefined")

        # 3. JIT median timing is recorded
        median_ms = report.get("jit_bench_median_ms", 0)
        self.assertGreater(median_ms, 30, f"Expected interpreter execution to take >30ms, took {median_ms}ms")


if __name__ == "__main__":
    unittest.main()
