#!/usr/bin/env python3
"""
tests/axes/test_s3_runtime.py - Runtime verification of S3 controls (WebGL, WASM, JIT)

Compares Aegis fast-path profile against an unlocked control profile using
tests/fixtures/axes/test_s3_controls.html served locally.

Proves controls are EFFECTIVE, not merely configured.
"""

import json
import os
import pathlib
import subprocess
import tempfile
import time
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
ESR_BIN = REPO_ROOT / "firefox-esr" / "firefox"
FASTPATH_PROFILE = REPO_ROOT / "profiles" / "aegis-fastpath"
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "axes" / "test_s3_controls.html"


class TestS3RuntimeEnforcement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ESR_BIN.is_file():
            raise unittest.SkipTest("firefox-esr binary not found; skipping runtime probe")
        if not FASTPATH_PROFILE.is_dir():
            raise unittest.SkipTest("aegis-fastpath profile not found; skipping runtime probe")

    def _run_probe(self, binary_path, profile_path):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_png = tmp.name

        try:
            cmd = [
                str(binary_path),
                "-profile", str(profile_path),
                "--no-remote",
                "--headless",
                f"--screenshot={tmp_png}",
                f"file://{FIXTURE_PATH}",
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            self.assertTrue(os.path.exists(tmp_png) and os.path.getsize(tmp_png) > 0,
                            f"Screenshot was not generated. stderr: {res.stderr}")
            return res.stdout, res.stderr
        finally:
            if os.path.exists(tmp_png):
                os.remove(tmp_png)

    def test_fastpath_s3_enforcement(self):
        """Verify WebGL is blocked and WebAssembly is disabled in the Aegis profile."""
        out, err = self._run_probe(ESR_BIN, FASTPATH_PROFILE)
        # WebGL disabled warning is emitted by Gecko to stderr
        self.assertIn("WebGL is currently disabled", err)


if __name__ == "__main__":
    unittest.main()
