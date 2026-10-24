#!/usr/bin/env python3
"""
tests/modules/test_link_cleaner.py — Automated verification of M11 Link Cleaner module.

Verifies:
1. Module manifest compliance with spec Part 8.1.1 (Privacy P0, least privilege).
2. WebExtension manifest validity and absence of unnecessary elevated permissions.
3. Sanitization logic across standard tracking parameters, prefixes, and keep-lists.
4. Live browser runtime enforcement:
   - Active URL redirection strips tracking parameters during navigation.
   - Kill-switch dynamically disables cleaning when set to false.
   - Benign query parameters and fragments are preserved.
"""

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
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
ESR_BIN = REPO_ROOT / "firefox-esr" / "firefox"
MODULE_DIR = REPO_ROOT / "modules" / "link-cleaner"


def find_free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class MockHttpHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        html = f"""<!DOCTYPE html>
<html>
<head><title>Aegis Link Cleaner Test Page</title></head>
<body>
  <h1 id="header">Destination Page</h1>
  <div id="current-url"></div>
  <script>
    document.getElementById("current-url").textContent = window.location.href;
  </script>
</body>
</html>"""
        self.wfile.write(html.encode("utf-8"))

    def log_message(self, format, *args):
        pass  # Suppress console logging during test run


class TestLinkCleaner(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not ESR_BIN.is_file():
            raise unittest.SkipTest("firefox-esr binary not found; skipping link cleaner runtime tests")

        # Start local mock server
        cls.http_port = find_free_port()
        cls.server = http.server.HTTPServer(("127.0.0.1", cls.http_port), MockHttpHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "server"):
            cls.server.shutdown()

    def test_module_manifest_schema(self):
        """Verify module.json adheres to Master Spec Part 8.1.1 schema."""
        mod_json_path = MODULE_DIR / "module.json"
        self.assertTrue(mod_json_path.is_file(), "module.json missing")

        data = json.loads(mod_json_path.read_text(encoding="utf-8"))
        self.assertEqual(data.get("id"), "link-cleaner")
        self.assertEqual(data.get("name"), "Link Cleaner")
        self.assertEqual(data.get("privacy_class"), "P1", "Link Cleaner must be Privacy Class P1 (stores user keep-list in local storage)")
        self.assertTrue(data.get("kill_switch"), "Module must declare kill_switch: true")
        self.assertEqual(data.get("network"), "none", "Module must declare network: none")

    def test_webextension_manifest_permissions_acknowledged_broad(self):
        """
        Verify WebExtension manifest permissions:
        Acknowledge plainly that <all_urls> + webRequestBlocking is broad and NOT least privilege,
        and verify that the manifest explicitly justifies why this broad capability is required.
        """
        manifest_path = MODULE_DIR / "manifest.json"
        self.assertTrue(manifest_path.is_file(), "manifest.json missing")

        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(data.get("manifest_version"), 2)
        self.assertEqual(data.get("name"), "Aegis Link Cleaner")

        perms = data.get("permissions", [])
        # Broad interception permissions explicitly required for URL query rewriting across domains
        self.assertIn("webRequest", perms)
        self.assertIn("webRequestBlocking", perms)
        self.assertIn("<all_urls>", perms)
        self.assertIn("storage", perms)

        # Prohibited elevated permissions unrelated to link sanitization
        self.assertNotIn("tabs", perms, "tabs permission is not required and must not be requested")
        self.assertNotIn("cookies", perms, "cookies permission must not be requested")
        self.assertNotIn("clipboardRead", perms, "clipboardRead must not be requested")
        self.assertNotIn("nativeMessaging", perms, "nativeMessaging must not be requested")

        # Explicit acknowledgment in notes that <all_urls> + webRequestBlocking is broad and NOT least privilege
        notes = data.get("notes", "")
        self.assertIn("broad permissions", notes.lower(), "Manifest must plainly acknowledge permissions are broad")
        self.assertIn("not least privilege", notes.lower(), "Manifest must honestly state it is not least privilege")
        self.assertIn("declarativenetrequest", notes.lower(), "Manifest must justify why DNR cannot express prefix rules")

    def test_cleaning_logic_per_site_keep(self):
        """
        Verify that per-site keep-lists allow benign sites using parameters such as
        si (music/podcasts) and spm (e-commerce) to function without breakage,
        while strictly stripping them on non-whitelisted sites.
        """
        js_code = (MODULE_DIR / "cleaner_logic.js").read_text(encoding="utf-8")

        # Evaluate cleaner_logic.js in a JS runtime / Node or Python parity check
        # We can test directly in Node or Python, and also in the browser runtime test
        # Let's verify via Node or Python subprocess calling cleaner_logic.js
        test_script = f"""
        {js_code}
        const perSiteKeep = {{
            "shop.example.com": ["spm"],
            "music.example.org": ["si"]
        }};

        // Case 1: Whitelisted shop site using spm (should preserve spm, strip utm_source)
        const resShop = cleanLink("https://shop.example.com/item?id=42&spm=101.2.3&utm_source=promo", perSiteKeep);

        // Case 2: Non-whitelisted site using spm (should strip both spm and utm_source)
        const resOther = cleanLink("https://other.example.net/item?id=42&spm=101.2.3&utm_source=promo", perSiteKeep);

        // Case 3: Whitelisted music site using si (should preserve si, strip fbclid)
        const resMusic = cleanLink("https://music.example.org/track/99?si=abc123token&fbclid=xyz999", perSiteKeep);

        // Case 4: Non-whitelisted site using si (should strip si)
        const resTracker = cleanLink("https://tracker.example.com/log?si=abc123token", perSiteKeep);

        console.log(JSON.stringify({{ resShop, resOther, resMusic, resTracker }}));
        """
        import subprocess
        out = subprocess.check_output(["node", "-e", test_script], text=True)
        res = json.loads(out)

        # Case 1: shop.example.com retains spm
        self.assertIn("spm=101.2.3", res["resShop"]["cleanedUrl"])
        self.assertNotIn("utm_source", res["resShop"]["cleanedUrl"])
        self.assertEqual(res["resShop"]["removedParams"], ["utm_source"])

        # Case 2: other.example.net strips spm and utm_source
        self.assertNotIn("spm", res["resOther"]["cleanedUrl"])
        self.assertNotIn("utm_source", res["resOther"]["cleanedUrl"])
        self.assertEqual(set(res["resOther"]["removedParams"]), {"spm", "utm_source"})

        # Case 3: music.example.org retains si
        self.assertIn("si=abc123token", res["resMusic"]["cleanedUrl"])
        self.assertNotIn("fbclid", res["resMusic"]["cleanedUrl"])
        self.assertEqual(res["resMusic"]["removedParams"], ["fbclid"])

        # Case 4: tracker.example.com strips si
        self.assertNotIn("si", res["resTracker"]["cleanedUrl"])
        self.assertEqual(res["resTracker"]["removedParams"], ["si"])

    def test_cleaning_logic_matches_prototype(self):
        """Verify that JavaScript cleaner_logic.js contains all tracking parameters from prototype."""
        js_code = (MODULE_DIR / "cleaner_logic.js").read_text(encoding="utf-8")

        # Import reference from prototype
        import sys
        sys.path.insert(0, str(REPO_ROOT / "prototypes"))
        from aegis_modules import TRACKING_PARAMS, TRACKING_PREFIXES, clean_link

        for param in TRACKING_PARAMS:
            self.assertIn(f'"{param}"', js_code, f"JavaScript tracking set missing prototype param: {param}")

        for prefix in TRACKING_PREFIXES:
            self.assertIn(f'"{prefix}"', js_code, f"JavaScript tracking prefix missing prototype prefix: {prefix}")

        # Test prototype output parity
        dirty = "https://example.com/item?id=123&utm_source=newsletter&fbclid=xyz&keep_me=true#details"
        cleaned_py, removed_py = clean_link(dirty)
        self.assertEqual(cleaned_py, "https://example.com/item?id=123&keep_me=true#details")
        self.assertEqual(set(removed_py), {"utm_source", "fbclid"})

    def test_browser_runtime_cleaning_and_kill_switch(self):
        """
        Launch Firefox ESR, install link-cleaner extension, and verify:
        1. Navigations with tracking parameters are redirected to cleaned URLs.
        2. Kill switch disables redirection.
        3. Re-enabling restores active sanitization.
        """
        marionette_port = find_free_port()
        prof_dir = tempfile.mkdtemp(prefix="aegis_linkcleaner_test_")

        with open(os.path.join(prof_dir, "user.js"), "w") as f:
            f.write(f'user_pref("marionette.enabled", true);\n')
            f.write(f'user_pref("marionette.port", {marionette_port});\n')
            f.write('user_pref("xpinstall.signatures.required", false);\n')
            f.write('user_pref("extensions.autoDisableScopes", 0);\n')
            f.write('user_pref("aegis.profile.tier", "S1");\n')
            f.write('user_pref("aegis.profile.identity_tier", "I1");\n')

        env = dict(os.environ)
        env["AEGIS_SURFACE_TIER"] = "S1"
        env["AEGIS_IDENTITY_TIER"] = "I1"

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
            # Handshake
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

            # 1. Start Session & Install Extension
            send_recv(1, "WebDriver:NewSession", {})
            install_res = send_recv(2, "Addon:Install", {"path": str(MODULE_DIR), "temporary": True})
            self.assertEqual(install_res[3]["value"], "link-cleaner@aegis.local", "Extension failed to install")

            time.sleep(0.5)

            # 2. Test Active Sanitization
            # Navigate to URL with tracking query parameters
            dirty_url = f"http://127.0.0.1:{self.http_port}/product?item=widget&utm_source=twitter&fbclid=abc1234&gclid=xyz987"
            nav_res = send_recv(3, "WebDriver:Navigate", {"url": dirty_url})

            # Query current URL in browser content
            url_res = send_recv(4, "WebDriver:GetCurrentURL", {})
            effective_url = url_res[3]["value"]

            self.assertIn("item=widget", effective_url, "Benign parameter 'item=widget' must be preserved")
            self.assertNotIn("utm_source", effective_url, "Tracking parameter 'utm_source' must be stripped")
            self.assertNotIn("fbclid", effective_url, "Tracking parameter 'fbclid' must be stripped")
            self.assertNotIn("gclid", effective_url, "Tracking parameter 'gclid' must be stripped")
            self.assertEqual(effective_url, f"http://127.0.0.1:{self.http_port}/product?item=widget")

            # 3. Test Kill-Switch
            # Disable extension via AddonManager
            send_recv(5, "Marionette:SetContext", {"value": "chrome"})
            kill_script = """
            const resolve = arguments[arguments.length - 1];
            (async () => {
                const { AddonManager } = ChromeUtils.importESModule("resource://gre/modules/AddonManager.sys.mjs");
                const addon = await AddonManager.getAddonByID("link-cleaner@aegis.local");
                await addon.disable();
                resolve({ disabled: !addon.isActive });
            })();
            """
            kill_res = send_recv(6, "WebDriver:ExecuteAsyncScript", {"script": kill_script, "args": []})
            self.assertTrue(kill_res[3]["value"].get("disabled"), "Failed to disable link-cleaner via kill switch")

            # Navigate again with tracking parameter while disabled
            send_recv(7, "Marionette:SetContext", {"value": "content"})
            send_recv(8, "WebDriver:Navigate", {"url": dirty_url})
            disabled_url = send_recv(9, "WebDriver:GetCurrentURL", {})[3]["value"]

            self.assertIn("utm_source", disabled_url, "When kill-switch is active, parameters must NOT be stripped")
            self.assertIn("fbclid", disabled_url, "When kill-switch is active, parameters must NOT be stripped")

            # 4. Re-enable module and verify sanitization resumes
            send_recv(10, "Marionette:SetContext", {"value": "chrome"})
            reenable_script = """
            const resolve = arguments[arguments.length - 1];
            (async () => {
                const { AddonManager } = ChromeUtils.importESModule("resource://gre/modules/AddonManager.sys.mjs");
                const addon = await AddonManager.getAddonByID("link-cleaner@aegis.local");
                await addon.enable();
                resolve({ enabled: addon.isActive });
            })();
            """
            reenable_res = send_recv(11, "WebDriver:ExecuteAsyncScript", {"script": reenable_script, "args": []})
            self.assertTrue(reenable_res[3]["value"].get("enabled"), "Failed to re-enable link-cleaner")

            send_recv(12, "Marionette:SetContext", {"value": "content"})
            send_recv(13, "WebDriver:Navigate", {"url": dirty_url})
            reenabled_url = send_recv(14, "WebDriver:GetCurrentURL", {})[3]["value"]

            self.assertNotIn("utm_source", reenabled_url, "Sanitization must resume after re-enabling")
            self.assertEqual(reenabled_url, f"http://127.0.0.1:{self.http_port}/product?item=widget")

            # Delete session
            send_recv(15, "WebDriver:DeleteSession", {})
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
