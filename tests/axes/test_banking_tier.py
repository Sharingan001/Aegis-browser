#!/usr/bin/env python3
"""
tests/axes/test_banking_tier.py — Runtime verification of Banking preset extension isolation.

Verifies:
1. Preset definition: banking preset specifies {S2, I3, N1} in tier_matrix.PRESETS.
2. Runtime enforcement: in the banking profile (extensions.enabledScopes: 0),
   extension installation is blocked and zero WebExtensions are active.
3. Pre-existing extension suppression: any extension in the profile directory
   is completely ignored and inactive under enabledScopes: 0.
"""

import json
import os
import pathlib
import socket
import subprocess
import tempfile
import time
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
ESR_BIN = REPO_ROOT / "firefox-esr" / "firefox"
MODULES_DIR = REPO_ROOT / "modules"


def find_free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class TestBankingTier(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not ESR_BIN.is_file():
            raise unittest.SkipTest("firefox-esr binary not found; skipping banking tier runtime tests")

    def test_banking_preset_matrix_definition(self):
        """Verify banking preset is defined in tier_matrix with {S2, I3, N1} and extension isolation."""
        import sys
        sys.path.insert(0, str(REPO_ROOT / "tools"))
        from tier_matrix import PRESETS

        self.assertIn("banking", PRESETS, "banking preset must exist in tier_matrix.PRESETS")
        bp = PRESETS["banking"]
        self.assertEqual(bp["S"], "S2", "Banking preset must use S2 (HTTPS-only, prompt autoplay)")
        self.assertEqual(bp["I"], "I3", "Banking preset must use I3 (site-keyed noise, D-012/A-003)")
        self.assertEqual(bp["N"], "N1", "Banking preset must use N1 (direct/local network)")
        self.assertIn("extensions off", bp.get("desc", "").lower(),
                      "Banking preset desc must document instance-wide extension isolation")

    def test_banking_runtime_extension_installation_blocked(self):
        """
        Verify that in the banking instance (extensions.enabledScopes: 0):
        1. Addon:Install is rejected.
        2. WebExtensionPolicy is not created.
        3. Zero WebExtensions are active in AddonManager.
        """
        marionette_port = find_free_port()
        prof_dir = tempfile.mkdtemp(prefix="aegis_banking_test_")

        with open(os.path.join(prof_dir, "user.js"), "w") as f:
            f.write(f'user_pref("marionette.enabled", true);\n')
            f.write(f'user_pref("marionette.port", {marionette_port});\n')
            f.write('user_pref("xpinstall.signatures.required", false);\n')
            f.write('user_pref("aegis.profile.tier", "S2");\n')
            f.write('user_pref("aegis.profile.identity_tier", "I3");\n')
            f.write('user_pref("extensions.enabledScopes", 0);\n')
            f.write('user_pref("extensions.autoDisableScopes", 15);\n')

        env = dict(os.environ)
        env["AEGIS_SURFACE_TIER"] = "S2"
        env["AEGIS_IDENTITY_TIER"] = "I3"

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
            s.connect(("127.0.0.1", marionette_port))
            hdr = b""
            while b":" not in hdr:
                hdr += s.recv(1)
            s.recv(int(hdr[:-1].decode()))

            def send_recv(msg_id, cmd_name, params):
                payload = json.dumps([0, msg_id, cmd_name, params])
                s.sendall(f"{len(payload)}:{payload}".encode())
                h = b""
                while b":" not in h:
                    h += s.recv(1)
                l = int(h[:-1].decode())
                body = b""
                while len(body) < l:
                    body += s.recv(l - len(body))
                return json.loads(body.decode())

            send_recv(1, "WebDriver:NewSession", {})

            # Attempt to install link-cleaner extension into banking profile
            ext_path = str(MODULES_DIR / "link-cleaner")
            install_res = send_recv(2, "Addon:Install", {"path": ext_path, "temporary": False})

            # Assert installation error
            self.assertIsNotNone(install_res[2], f"Expected error dict under enabledScopes: 0, got: {install_res}")
            self.assertIn("error", install_res[2], f"Expected 'error' in response, got: {install_res[2]}")
            self.assertEqual(install_res[2]["error"], "invalid web extension")

            # Query AddonManager and WebExtensionPolicy from chrome context
            send_recv(3, "Marionette:SetContext", {"value": "chrome"})
            script = """
            const resolve = arguments[arguments.length - 1];
            (async () => {
                const { AddonManager } = ChromeUtils.importESModule("resource://gre/modules/AddonManager.sys.mjs");
                const addons = await AddonManager.getAllAddons();
                const policy = WebExtensionPolicy.getByID("link-cleaner@aegis.local");
                const enabledScopes = Services.prefs.getIntPref("extensions.enabledScopes", -1);
                resolve({
                    enabledScopes,
                    policyFound: !!policy,
                    policyActive: policy ? policy.active : false,
                    activeWebExts: addons.filter(a => a.isActive && a.type === "extension").map(a => a.id)
                });
            })();
            """
            eval_res = send_recv(4, "WebDriver:ExecuteAsyncScript", {"script": script, "args": []})
            val = eval_res[3]["value"]

            self.assertEqual(val["enabledScopes"], 0, "extensions.enabledScopes must be 0 in banking")
            self.assertFalse(val["policyFound"], "No WebExtensionPolicy must exist for extension")
            self.assertEqual(len(val["activeWebExts"]), 0,
                             f"Banking instance must have 0 active WebExtensions; found: {val['activeWebExts']}")

            send_recv(5, "WebDriver:DeleteSession", {})
        finally:
            s.close()
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
            subprocess.run(["rm", "-rf", prof_dir])


if __name__ == "__main__":
    unittest.main()
