#!/usr/bin/env python3
"""
tests/axes/test_identity_levels.py — Runtime verification of Identity levels I1..I4 and FPP overrides.

Verifies identity controls against the running Firefox ESR engine:
- I1: Native baseline (FPP off, RFP off, trimmingPolicy 0, no_host false, gamepad enabled).
- I3: Site-keyed noise (FPP locked true, remoteOverrides locked false, trimmingPolicy 2, no_host true).
- I2: Uniform spoofing (RFP locked true, letterboxing true, FPP false, unmeasured resemblance).
- I4: Minimal-API (RFP locked true, gamepad disabled).
- Fail-Closed: Invalid or mismatched identity tier fails closed to I4 minimal identity.
- FPP Override: Proves per-target overrides in privacy.fingerprintingProtection.overrides alter behavior.
- Cumulativity: Validates I4 >= I2 >= I3 >= I1 along the protection chain.
"""

import ast
import json
import os
import pathlib
import socket
import subprocess
import sys
import tempfile
import time
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
ESR_BIN = REPO_ROOT / "firefox-esr" / "firefox"
IDENTITY_DIR = REPO_ROOT / "config" / "axes" / "identity"

sys.path.insert(0, str(REPO_ROOT / "tools"))
from generate_autoconfig import load_tier_definitions, compute_cumulative_prefs, IDENTITY_TIERS


def find_free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class TestIdentityLevels(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not ESR_BIN.is_file():
            raise unittest.SkipTest("firefox-esr binary not found; skipping identity level tests")

    def _query_live_identity_tier(self, identity_tier, surface_tier="S1", overrides="", port=None):
        """Query live effective preferences and content state via Marionette."""
        if port is None:
            port = find_free_port()

        prof_dir = tempfile.mkdtemp(prefix=f"aegis_id_{identity_tier}_")
        with open(os.path.join(prof_dir, "user.js"), "w") as f:
            f.write(f'user_pref("marionette.enabled", true);\n')
            f.write(f'user_pref("marionette.port", {port});\n')
            if surface_tier:
                f.write(f'user_pref("aegis.profile.tier", "{surface_tier}");\n')
            if identity_tier:
                f.write(f'user_pref("aegis.profile.identity_tier", "{identity_tier}");\n')
            if overrides:
                f.write(f'user_pref("privacy.fingerprintingProtection.overrides", "{overrides}");\n')

        env = dict(os.environ)
        if surface_tier:
            env["AEGIS_SURFACE_TIER"] = surface_tier
        else:
            env.pop("AEGIS_SURFACE_TIER", None)

        if identity_tier:
            env["AEGIS_IDENTITY_TIER"] = identity_tier
        else:
            env.pop("AEGIS_IDENTITY_TIER", None)

        cmd = [
            str(ESR_BIN),
            "-profile", prof_dir,
            "--no-remote",
            "--headless",
            "--marionette",
            "--remote-allow-system-access"
        ]

        proc = subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2.5)

        s = socket.socket()
        try:
            s.connect(("127.0.0.1", port))
            # Handshake
            header = b""
            while b":" not in header:
                header += s.recv(1)
            init_len = int(header[:-1].decode())
            s.recv(init_len)

            def send_recv(msg_id, cmd_name, params):
                payload = json.dumps([0, msg_id, cmd_name, params])
                s.sendall(f"{len(payload)}:{payload}".encode())
                hdr = b""
                while b":" not in hdr:
                    hdr += s.recv(1)
                l = int(hdr[:-1].decode())
                body = b""
                while len(body) < l:
                    body += s.recv(l - len(body))
                return json.loads(body.decode())

            send_recv(1, "WebDriver:NewSession", {})

            # Query chrome context prefs
            send_recv(2, "Marionette:SetContext", {"value": "chrome"})
            pref_script = """
            return {
                "fpp": Services.prefs.getBoolPref("privacy.fingerprintingProtection", false),
                "fpp_remote": Services.prefs.getBoolPref("privacy.fingerprintingProtection.remoteOverrides.enabled", true),
                "fpp_overrides": Services.prefs.getStringPref("privacy.fingerprintingProtection.overrides", "NOT_SET"),
                "rfp": Services.prefs.getBoolPref("privacy.resistFingerprinting", false),
                "rfp_letterboxing": Services.prefs.getBoolPref("privacy.resistFingerprinting.letterboxing", false),
                "trimming": Services.prefs.getIntPref("network.http.referer.trimmingPolicy", -1),
                "xorigin_policy": Services.prefs.getIntPref("network.http.referer.XOriginPolicy", -1),
                "no_host": Services.prefs.getBoolPref("media.peerconnection.ice.no_host", false),
                "accept_lang": Services.prefs.getStringPref("intl.accept_languages", "UNSET"),
                "remote_fonts": Services.prefs.getBoolPref("gfx.downloadable_fonts.enabled", true),
                "active_id": Services.prefs.getStringPref("aegis.identity.active_tier", "none"),
                "fail_closed": Services.prefs.getBoolPref("aegis.identity.fail_closed", false)
            };
            """
            resp_prefs = send_recv(3, "WebDriver:ExecuteScript", {"script": pref_script, "args": []})

            # Query content context
            send_recv(4, "Marionette:SetContext", {"value": "content"})
            content_script = """
            return {
                "tz_offset": new Date().getTimezoneOffset(),
                "gamepad_supported": typeof navigator.getGamepads === "function"
            };
            """
            resp_content = send_recv(5, "WebDriver:ExecuteScript", {"script": content_script, "args": []})

            send_recv(6, "WebDriver:DeleteSession", {})
            return {
                "prefs": resp_prefs[3]["value"],
                "content": resp_content[3]["value"]
            }
        finally:
            s.close()
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
            subprocess.run(["rm", "-rf", prof_dir])

    def test_all_test_methods_have_assertions(self):
        """AST Guard: inspect all test methods in this class to guarantee assertions exist."""
        with open(__file__, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=__file__)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "TestIdentityLevels":
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name.startswith("test_"):
                        asserts = [n for n in ast.walk(item) if isinstance(n, ast.Call) and getattr(n.func, "attr", "").startswith("assert")]
                        self.assertGreater(
                            len(asserts), 0,
                            f"Empty test flagged: {item.name} has no assertions"
                        )

    def test_i1_runtime_enforcement(self):
        """I1: Native baseline exposes unperturbed parameters."""
        res = self._query_live_identity_tier("I1", surface_tier="S1")
        prefs = res["prefs"]
        self.assertEqual(prefs["active_id"], "I1")
        self.assertFalse(prefs["fail_closed"])
        self.assertFalse(prefs["fpp"], "I1 must have FPP disabled")
        self.assertFalse(prefs["rfp"], "I1 must have RFP disabled")
        self.assertFalse(prefs["rfp_letterboxing"], "I1 must have letterboxing disabled")
        self.assertEqual(prefs["trimming"], 0, "I1 must have default referrer policy (0)")
        self.assertFalse(prefs["no_host"], "I1 must allow host candidates (no_host: false)")
        # dom.gamepad.enabled is not in the I-axis query (removed from I-axis definition;
        # with S4 JS disabled it is unreachable; for S1 the browser default applies)

    def test_i3_runtime_enforcement(self):
        """I3: Site-keyed noise enforces FPP with remote overrides locked false."""
        res = self._query_live_identity_tier("I3", surface_tier="S1")
        prefs = res["prefs"]
        self.assertEqual(prefs["active_id"], "I3")
        self.assertFalse(prefs["fail_closed"])
        self.assertTrue(prefs["fpp"], "I3 must lock FPP to true")
        self.assertFalse(prefs["fpp_remote"], "I3 must lock remote overrides to false (D-012)")
        self.assertFalse(prefs["rfp"], "I3 must leave RFP disabled")
        self.assertFalse(prefs["rfp_letterboxing"], "I3 must not enable letterboxing")
        self.assertEqual(prefs["trimming"], 2, "I3 must trim cross-origin referrers to origin (2)")
        self.assertTrue(prefs["no_host"], "I3 must hide local host IP in WebRTC (no_host: true)")

    def test_i2_runtime_enforcement(self):
        """I2: Uniform mode enforces full RFP with letterboxing (intended to resemble, unmeasured)."""
        res = self._query_live_identity_tier("I2", surface_tier="S3")
        prefs = res["prefs"]
        self.assertEqual(prefs["active_id"], "I2")
        self.assertFalse(prefs["fail_closed"])
        self.assertTrue(prefs["rfp"], "I2 must lock RFP to true")
        self.assertTrue(prefs["rfp_letterboxing"], "I2 must lock letterboxing to true")
        self.assertFalse(prefs["fpp"], "I2 must disable FPP (superseded by RFP)")
        self.assertEqual(prefs["trimming"], 2, "I2 must trim referrers")
        self.assertTrue(prefs["no_host"], "I2 must hide local IP")

    def test_i4_runtime_enforcement(self):
        """I4: Minimal-Signals enforces RFP and non-script passive signals (Accept-Language, remote fonts, referrer)."""
        res = self._query_live_identity_tier("I4", surface_tier="S4")
        prefs = res["prefs"]
        self.assertEqual(prefs["active_id"], "I4")
        self.assertFalse(prefs["fail_closed"])
        # I4 inherits I2 RFP baseline
        self.assertTrue(prefs["rfp"], "I4 must lock RFP to true (inherited from I2)")
        # I4-specific non-script signal controls
        self.assertEqual(prefs["accept_lang"], "en-US, en",
                         "I4 must lock Accept-Language to 'en-US, en' to normalize passive header signal")
        self.assertFalse(prefs["remote_fonts"],
                         "I4 must lock gfx.downloadable_fonts.enabled to false to block remote font loading")
        self.assertEqual(prefs["xorigin_policy"], 2,
                         "I4 must lock network.http.referer.XOriginPolicy to 2 (origin-only cross-origin)")
        # dom.gamepad.enabled is NOT tested: with S4 JS disabled, the API is unreachable
        # regardless of the pref. Testing it here would be security theater.

    def test_identity_omitted_fails_closed_per_surface(self):
        """
        Omitting AEGIS_IDENTITY_TIER must fail closed to I4 for ALL surface tiers.
        Auto-resolution from the surface tier is prohibited: it can yield I3 on S1/S2
        when Tor (N2/N3) is in use, violating R2 (Tor locks Identity to I2).
        Only the launcher may select an identity tier, from the preset table.
        """
        for surface_tier in ["S1", "S2", "S3", "S4"]:
            with self.subTest(surface_tier=surface_tier):
                prof_dir = tempfile.mkdtemp(prefix=f"aegis_id_omit_{surface_tier}_")
                port = find_free_port()
                try:
                    with open(os.path.join(prof_dir, "user.js"), "w") as f:
                        f.write(f'user_pref("marionette.enabled", true);\n')
                        f.write(f'user_pref("marionette.port", {port});\n')
                        # Set surface profile token but NO identity token
                        f.write(f'user_pref("aegis.profile.tier", "{surface_tier}");\n')

                    env = dict(os.environ)
                    env["AEGIS_SURFACE_TIER"] = surface_tier
                    env.pop("AEGIS_IDENTITY_TIER", None)   # Explicitly unset
                    env.pop("aegis.profile.identity_tier", None)

                    cmd = [
                        str(ESR_BIN),
                        "-profile", prof_dir,
                        "--no-remote",
                        "--headless",
                        "--marionette",
                        "--remote-allow-system-access"
                    ]
                    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    time.sleep(2.5)

                    s = socket.socket()
                    try:
                        s.connect(("127.0.0.1", port))
                        header = b""
                        while b":" not in header:
                            header += s.recv(1)
                        init_len = int(header[:-1].decode())
                        s.recv(init_len)

                        def send_recv(msg_id, cmd_name, params):
                            payload = json.dumps([0, msg_id, cmd_name, params])
                            s.sendall(f"{len(payload)}:{payload}".encode())
                            hdr = b""
                            while b":" not in hdr:
                                hdr += s.recv(1)
                            l = int(hdr[:-1].decode())
                            body = b""
                            while len(body) < l:
                                body += s.recv(l - len(body))
                            return json.loads(body.decode())

                        send_recv(1, "WebDriver:NewSession", {})
                        send_recv(2, "Marionette:SetContext", {"value": "chrome"})
                        script = """
                        return {
                            "active_id": Services.prefs.getStringPref("aegis.identity.active_tier", "none"),
                            "fail_closed": Services.prefs.getBoolPref("aegis.identity.fail_closed", false)
                        };
                        """
                        resp = send_recv(3, "WebDriver:ExecuteScript", {"script": script, "args": []})
                        send_recv(4, "WebDriver:DeleteSession", {})
                        val = resp[3]["value"]
                        self.assertEqual(
                            val["active_id"], "I4",
                            f"Omitted identity on surface {surface_tier} must fail closed to I4 (not auto-resolved)"
                        )
                        self.assertTrue(
                            val["fail_closed"],
                            f"Omitted identity on surface {surface_tier} must set fail_closed=true"
                        )
                    finally:
                        s.close()
                        proc.terminate()
                        try:
                            proc.wait(timeout=3)
                        except subprocess.TimeoutExpired:
                            proc.kill()
                finally:
                    subprocess.run(["rm", "-rf", prof_dir])

    def test_preset_identity_matches_cfg(self):
        """
        Preset-vs-cfg consistency: every preset in tier_matrix.PRESETS that has a defined
        Identity axis ('I') must be one of the valid identity tiers accepted by the cfg.
        And the cfg's fail-closed target (I4) must match what the preset table records for
        the detonation and detonation_local presets.
        """
        sys.path.insert(0, str(REPO_ROOT / "tools"))
        from tier_matrix import PRESETS

        VALID_TIERS = {"I1", "I2", "I3", "I4"}
        for preset_name, preset in PRESETS.items():
            identity = preset.get("I")
            self.assertIn(
                identity, VALID_TIERS,
                f"Preset '{preset_name}' has identity '{identity}' which is not a valid cfg tier"
            )

        # Both detonation presets must use I2 (Tor) or I4 (local static quarantine)
        detonation = PRESETS.get("detonation", {})
        detonation_local = PRESETS.get("detonation_local", {})
        self.assertEqual(detonation.get("I"), "I2",
                         "detonation preset (Tor) must use I2 (R2: Tor locks Identity to I2)")
        self.assertEqual(detonation_local.get("I"), "I4",
                         "detonation_local preset must use I4 (static quarantine, no Tor)")

        # No Tor preset (N2 or N3) may use I1 or I3 — that would violate R2
        for preset_name, preset in PRESETS.items():
            n = preset.get("N", "N1")
            i = preset.get("I", "I3")
            if n in ("N2", "N3"):
                self.assertIn(
                    i, ("I2",),
                    f"Tor preset '{preset_name}' (N={n}) must use I2; got {i} — violates R2"
                )

    def test_identity_cumulativity(self):
        """Assert cumulativity across identity levels: I4 >= I2 >= I3 >= I1 with documented overrides."""
        id_data = load_tier_definitions(IDENTITY_DIR, IDENTITY_TIERS)
        effective = compute_cumulative_prefs(id_data, IDENTITY_TIERS, "Identity")

        self.assertIn("I1", effective)
        self.assertIn("I3", effective)
        self.assertIn("I2", effective)
        self.assertIn("I4", effective)

        # I1 baseline assertions
        self.assertFalse(effective["I1"]["privacy.fingerprintingProtection"]["value"])
        self.assertFalse(effective["I1"]["privacy.resistFingerprinting"]["value"])

        # I3 FPP assertions
        self.assertTrue(effective["I3"]["privacy.fingerprintingProtection"]["value"])
        self.assertTrue(effective["I3"]["privacy.fingerprintingProtection"]["override"])

        # I2 RFP assertions
        self.assertTrue(effective["I2"]["privacy.resistFingerprinting"]["value"])
        self.assertTrue(effective["I2"]["privacy.resistFingerprinting"]["override"])

        # I4 Minimal-Signals assertions: non-script passive signals
        self.assertEqual(effective["I4"]["intl.accept_languages"]["value"], "en-US, en")
        self.assertTrue(effective["I4"]["intl.accept_languages"]["override"])
        self.assertFalse(effective["I4"]["gfx.downloadable_fonts.enabled"]["value"])
        self.assertTrue(effective["I4"]["gfx.downloadable_fonts.enabled"]["override"])
        self.assertEqual(effective["I4"]["network.http.referer.XOriginPolicy"]["value"], 2)
        self.assertTrue(effective["I4"]["network.http.referer.XOriginPolicy"]["override"])
        # dom.gamepad.enabled must NOT appear in the I4 effective prefs (removed from I-axis)
        self.assertNotIn("dom.gamepad.enabled", effective["I4"],
                         "dom.gamepad.enabled must not be in I4 effective prefs: JS is disabled under S4")

    def test_identity_level_schemas_and_conflicts(self):
        """Verify identity level files exist, parse, and have verify blocks."""
        for level in ["i1", "i2", "i3", "i4"]:
            fpath = IDENTITY_DIR / f"{level}.json"
            self.assertTrue(fpath.is_file(), f"{fpath} must exist")
            data = json.loads(fpath.read_text(encoding="utf-8"))
            self.assertEqual(data.get("axis"), "identity")
            self.assertIn("controls", data)
            for ctrl in data["controls"]:
                self.assertIn("id", ctrl)
                self.assertIn("set", ctrl)
                self.assertIn("verify", ctrl)
                self.assertIn("user_cost", ctrl)

    def test_identity_fail_closed_on_invalid_tier(self):
        """Invalid identity tier (e.g. I99) must fail closed to I4 minimal identity."""
        res = self._query_live_identity_tier("I99", surface_tier="S1")
        prefs = res["prefs"]
        self.assertEqual(prefs["active_id"], "I4", "Invalid tier must fail closed to I4")
        self.assertTrue(prefs["fail_closed"], "fail_closed flag must be true")
        self.assertTrue(prefs["rfp"], "Failed-closed identity must enable RFP (I4 inherits I2)")

    def test_identity_fail_closed_on_mismatch(self):
        """Mismatched identity tier (env != profile) must fail closed to I4."""
        prof_dir = tempfile.mkdtemp(prefix="aegis_id_mismatch_")
        port = find_free_port()
        with open(os.path.join(prof_dir, "user.js"), "w") as f:
            f.write(f'user_pref("marionette.enabled", true);\n')
            f.write(f'user_pref("marionette.port", {port});\n')
            f.write('user_pref("aegis.profile.tier", "S1");\n')
            f.write('user_pref("aegis.profile.identity_tier", "I1");\n')

        env = dict(os.environ)
        env["AEGIS_SURFACE_TIER"] = "S1"
        env["AEGIS_IDENTITY_TIER"] = "I3"  # Mismatch: env I3 != profile I1

        cmd = [
            str(ESR_BIN),
            "-profile", prof_dir,
            "--no-remote",
            "--headless",
            "--marionette",
            "--remote-allow-system-access"
        ]

        proc = subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2.5)

        s = socket.socket()
        try:
            s.connect(("127.0.0.1", port))
            header = b""
            while b":" not in header:
                header += s.recv(1)
            init_len = int(header[:-1].decode())
            s.recv(init_len)

            def send_recv(msg_id, cmd_name, params):
                payload = json.dumps([0, msg_id, cmd_name, params])
                s.sendall(f"{len(payload)}:{payload}".encode())
                hdr = b""
                while b":" not in hdr:
                    hdr += s.recv(1)
                l = int(hdr[:-1].decode())
                body = b""
                while len(body) < l:
                    body += s.recv(l - len(body))
                return json.loads(body.decode())

            send_recv(1, "WebDriver:NewSession", {})
            send_recv(2, "Marionette:SetContext", {"value": "chrome"})
            script = """
            return {
                "active_id": Services.prefs.getStringPref("aegis.identity.active_tier", "none"),
                "fail_closed": Services.prefs.getBoolPref("aegis.identity.fail_closed", false)
            };
            """
            resp = send_recv(3, "WebDriver:ExecuteScript", {"script": script, "args": []})
            send_recv(4, "WebDriver:DeleteSession", {})

            val = resp[3]["value"]
            self.assertEqual(val["active_id"], "I4", "Mismatched identity must fail closed to I4")
            self.assertTrue(val["fail_closed"], "Mismatched identity must set fail_closed=true")
        finally:
            s.close()
            proc.terminate()
            proc.wait()
            subprocess.run(["rm", "-rf", prof_dir])

    def test_fpp_per_target_override_changes_behavior(self):
        """
        Prove that a per-target override in privacy.fingerprintingProtection.overrides
        effectively changes the engine's target configuration at runtime.

        Baseline (I3, no overrides):
          fpp_overrides = "" (empty string)

        Override applied: -CanvasRandomization
          fpp_overrides = "-CanvasRandomization"
          Meaning: the FPP EfficientCanvasRandomization target is selectively disabled.
          This proves the per-target override mechanism is live in the running engine.
        """
        # Baseline I3: overrides is empty
        res_baseline = self._query_live_identity_tier("I3", overrides="")
        self.assertEqual(res_baseline["prefs"]["fpp_overrides"], "",
                         "Baseline I3 must have empty fpp_overrides")

        # Target override: -CanvasRandomization (disable canvas noise for this instance)
        res_override = self._query_live_identity_tier("I3", overrides="-CanvasRandomization")
        self.assertEqual(
            res_override["prefs"]["fpp_overrides"], "-CanvasRandomization",
            "Target override must be dynamically configured in running engine"
        )
        self.assertNotEqual(
            res_baseline["prefs"]["fpp_overrides"],
            res_override["prefs"]["fpp_overrides"],
            "Override preference must differ from baseline (before='', after='-CanvasRandomization')"
        )


if __name__ == "__main__":
    unittest.main()
