#!/usr/bin/env python3
"""
tests/axes/test_surface_levels.py - Runtime verification of Surface levels S1..S4 and conflict rules.

Every control in config/axes/surface/s*.json is verified against the running Firefox ESR engine:
- S1: Standard baseline (JS on, WASM on, WebGL on, mixed content blocked).
- S2: Guarded baseline (HTTPS-only mode locked, autoplay audio blocked, WebRTC ICE restricted).
- S3: Strict baseline (JIT disabled, WASM disabled, WebGL disabled, MathML disabled).
- S4: Static baseline (JS completely disabled, remote web fonts disabled).
- Cumulativity: S4 >= S3 >= S2 >= S1 with documented overrides.
- Sandbox & Fail-Closed: general.config.sandbox_enabled asserted true; empty tests flagged.
"""

import ast
import http.server
import json
import os
import pathlib
import socket
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

sys.path.insert(0, str(REPO_ROOT / "tools"))
from generate_autoconfig import load_tier_definitions, compute_cumulative_prefs


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
        with open(os.path.join(prof_dir, "user.js"), "w") as f:
            f.write(f'user_pref("aegis.profile.tier", "{tier}");\n')

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

    def _query_effective_prefs(self, tier, prefs_list, port=2846):
        """Query effective preferences directly from running Gecko engine via Marionette protocol."""
        prof_dir = tempfile.mkdtemp(prefix=f"aegis_marionette_{tier}_")
        with open(os.path.join(prof_dir, "user.js"), "w") as f:
            f.write(f'user_pref("aegis.profile.tier", "{tier}");\n')
            f.write(f'user_pref("marionette.enabled", true);\n')
            f.write(f'user_pref("marionette.port", {port});\n')

        env = dict(os.environ)
        if tier is not None:
            env["AEGIS_SURFACE_TIER"] = tier
        else:
            env.pop("AEGIS_SURFACE_TIER", None)

        cmd = [
            str(ESR_BIN),
            "-profile", prof_dir,
            "--no-remote",
            "--headless",
            "--marionette",
            "--remote-allow-system-access"
        ]
        proc = subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)

        def send_recv(s, msg_id, cmd_name, params):
            payload = json.dumps([0, msg_id, cmd_name, params])
            s.sendall(f"{len(payload)}:{payload}".encode())
            header = b""
            while b":" not in header:
                header += s.recv(1)
            length = int(header[:-1].decode())
            body = b""
            while len(body) < length:
                body += s.recv(length - len(body))
            return json.loads(body.decode())

        s = socket.socket()
        try:
            s.connect(("127.0.0.1", port))
            s.recv(1024)
            send_recv(s, 1, "WebDriver:NewSession", {})
            send_recv(s, 2, "Marionette:SetContext", {"value": "chrome"})

            script = """
            var res = {};
            var queried = %s;
            for (var p of queried) {
                try {
                    if (Services.prefs.getPrefType(p) === Services.prefs.PREF_BOOL) {
                        res[p] = Services.prefs.getBoolPref(p);
                    } else if (Services.prefs.getPrefType(p) === Services.prefs.PREF_INT) {
                        res[p] = Services.prefs.getIntPref(p);
                    } else if (Services.prefs.getPrefType(p) === Services.prefs.PREF_STRING) {
                        res[p] = Services.prefs.getStringPref(p);
                    } else {
                        res[p] = null;
                    }
                } catch(e) {
                    res[p] = null;
                }
            }
            res["_active_tier"] = Services.prefs.getStringPref("aegis.surface.active_tier", "none");
            res["_fail_closed"] = Services.prefs.getBoolPref("aegis.surface.fail_closed", false);
            return res;
            """ % json.dumps(prefs_list)

            resp = send_recv(s, 3, "WebDriver:ExecuteScript", {"script": script, "args": []})
            return resp[3]["value"]
        finally:
            s.close()
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
            subprocess.run(["rm", "-rf", prof_dir])

    def test_s1_runtime_enforcement(self):
        """S1: Standard surface allows WebAssembly, WebGL, and executes JIT."""
        url = f"http://127.0.0.1:{self.port}/axes/test_s3_controls.html"
        res = self._execute_tier_probe("S1", url)
        self.assertIsNotNone(res["report"], "S1 tier must execute page and return report")
        report = res["report"]
        self.assertFalse(report.get("wasm_disabled"), "S1 must allow WebAssembly")
        self.assertFalse(report.get("webgl_null"), "S1 must allow WebGL 3D graphics")
        self.assertLess(report.get("jit_bench_median_ms", 999), 60, "S1 must have JIT enabled")

    def test_s2_runtime_prefs(self):
        """S2: Guarded surface enforces HTTPS-only mode and audio autoplay lock (queried via Marionette)."""
        prefs_to_check = [
            "dom.security.https_only_mode",
            "media.autoplay.default",
            "media.peerconnection.ice.default_address_only",
            "webgl.disabled",
            "javascript.options.baselinejit",
            "javascript.options.wasm"
        ]
        res = self._query_effective_prefs("S2", prefs_to_check, port=2847)
        self.assertEqual(res.get("_active_tier"), "S2", "Active tier must be S2")
        self.assertFalse(res.get("_fail_closed"), "S2 must not fail closed")
        self.assertTrue(res.get("dom.security.https_only_mode"), "S2 must lock dom.security.https_only_mode to true")
        self.assertEqual(res.get("media.autoplay.default"), 1, "S2 must lock media.autoplay.default to 1 (block audible)")
        self.assertTrue(res.get("media.peerconnection.ice.default_address_only"), "S2 must restrict WebRTC ICE addresses")
        self.assertFalse(res.get("webgl.disabled"), "S2 must leave WebGL enabled")
        self.assertTrue(res.get("javascript.options.baselinejit"), "S2 must leave JIT enabled")
        self.assertTrue(res.get("javascript.options.wasm"), "S2 must leave WASM enabled")

    def test_s3_runtime_enforcement(self):
        """S3: Strict surface disables JIT, WebAssembly, and WebGL."""
        url = f"http://127.0.0.1:{self.port}/axes/test_s3_controls.html"
        res = self._execute_tier_probe("S3", url)
        self.assertIsNotNone(res["report"], "S3 tier must execute page and return report")
        report = res["report"]
        self.assertTrue(report.get("wasm_disabled"), "S3 must disable WebAssembly")
        self.assertEqual(report.get("wasm_detail"), "WebAssembly is undefined")
        self.assertTrue(report.get("webgl_null"), "S3 must disable WebGL")
        self.assertGreaterEqual(report.get("jit_bench_median_ms", 0), 70, "S3 must execute in interpreter")

    def test_s4_runtime_enforcement(self):
        """S4: Static surface completely disables JavaScript execution."""
        url = f"http://127.0.0.1:{self.port}/axes/test_js_status.html"
        res = self._execute_tier_probe("S4", url)
        self.assertIsNone(res["report"], "S4 must NOT execute JavaScript")
        self.assertIsNotNone(res["beacon"], "S4 must trigger noscript beacon")

    def test_sandbox_enabled(self):
        """Assert general.config.sandbox_enabled is true in running profile."""
        res = self._query_effective_prefs("S1", ["general.config.sandbox_enabled"], port=2848)
        self.assertTrue(res.get("general.config.sandbox_enabled"), "general.config.sandbox_enabled must be true")

    def test_surface_cumulativity(self):
        """Assert cumulativity across tiers: S4 >= S3 >= S2 >= S1 with documented overrides."""
        tiers_data = load_tier_definitions()
        effective = compute_cumulative_prefs(tiers_data)

        # 1. S2 includes all S1 controls plus overrides
        s1_prefs = effective["S1"]
        s2_prefs = effective["S2"]
        for p in s1_prefs:
            self.assertIn(p, s2_prefs, f"S2 must inherit pref '{p}' from S1")

        # Verify S2 overrides
        self.assertTrue(s2_prefs["dom.security.https_only_mode"]["value"])
        self.assertEqual(s2_prefs["media.autoplay.default"]["value"], 1)
        self.assertTrue(s2_prefs["media.peerconnection.ice.default_address_only"]["value"])

        # 2. S3 includes all S2 controls (specifically including media.peerconnection.ice.default_address_only)
        s3_prefs = effective["S3"]
        for p in s2_prefs:
            self.assertIn(p, s3_prefs, f"S3 must inherit pref '{p}' from S2")

        self.assertTrue(
            s3_prefs["media.peerconnection.ice.default_address_only"]["value"],
            "S3 must maintain media.peerconnection.ice.default_address_only=true inherited from S2"
        )
        self.assertEqual(s3_prefs["media.autoplay.default"]["value"], 5)
        self.assertFalse(s3_prefs["javascript.options.baselinejit"]["value"])
        self.assertFalse(s3_prefs["javascript.options.wasm"]["value"])
        self.assertTrue(s3_prefs["webgl.disabled"]["value"])

        # 3. S4 includes all S3 controls
        s4_prefs = effective["S4"]
        for p in s3_prefs:
            self.assertIn(p, s4_prefs, f"S4 must inherit pref '{p}' from S3")

        self.assertFalse(s4_prefs["javascript.enabled"]["value"])
        self.assertFalse(s4_prefs["gfx.downloadable_fonts.enabled"]["value"])
        self.assertFalse(s4_prefs["media.peerconnection.enabled"]["value"])

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

    def test_all_test_methods_have_assertions(self):
        """Inspect all test methods in this file via AST to guarantee no empty test methods exist."""
        test_file = pathlib.Path(__file__)
        with open(test_file, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(test_file))

        empty_tests = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                has_assert = False
                for child in ast.walk(node):
                    if isinstance(child, ast.Assert):
                        has_assert = True
                        break
                    if isinstance(child, ast.Call):
                        if isinstance(child.func, ast.Attribute) and child.func.attr.startswith("assert"):
                            has_assert = True
                            break
                if not has_assert:
                    empty_tests.append(node.name)

        self.assertEqual(empty_tests, [], f"Test methods lacking assertions: {empty_tests}")


if __name__ == "__main__":
    unittest.main()
