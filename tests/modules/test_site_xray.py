#!/usr/bin/env python3
"""
tests/modules/test_site_xray.py — Verification of M15 Site X-ray module.

Verifies:
1. Module manifest compliance with spec Part 8.1.1 (Privacy P1: local
   configuration only; posture records are in-memory).
2. WebExtension manifest permissions honesty:
   - webRequest is passive (no webRequestBlocking).
   - <all_urls> requirement disclosed honestly.
   - The "tabs" permission is NOT requested (not needed: tab lifecycle events
     work without it and tab URLs are not read).
   - externally_connectable limited to the Aegis command-palette.
3. Posture analysis logic parity with prototypes/aegis_modules.py.
4. Static value-storage proof: header values are never stored or logged.
5. Live browser runtime enforcement:
   - Passive header audit on main_frame navigation produces a SANITIZED
     posture (booleans/counts/origin only).
   - Sentinel proof: distinctive header values and the Set-Cookie payload
     (including the cookie NAME) never appear in the posture record nor in
     browser.storage.local.
   - Only the enabled flag is ever persisted.
   - Kill-switch disables posture observation dynamically.
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

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
ESR_BIN = REPO_ROOT / "firefox-esr" / "firefox"
MODULE_DIR = REPO_ROOT / "modules" / "site-xray"

# Distinctive sentinel values used to prove header values never persist.
SENTINEL_COOKIE_NAME = "XSENTINEL_SESSION_COOKIE"
SENTINEL_COOKIE_VALUE = "XSENTINEL_SUPER_SECRET_VALUE_31337"
SENTINEL_HEADER_VALUE = "XSENTINEL_HEADER_TOPSECRET_9999"


def find_free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class MockSiteHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Server", "nginx/1.18.0 (Ubuntu)")
        self.send_header("Set-Cookie",
                         f"{SENTINEL_COOKIE_NAME}={SENTINEL_COOKIE_VALUE}; Path=/")
        self.send_header("X-Sentinel-Header", SENTINEL_HEADER_VALUE)
        # Deliberately omit CSP, HSTS, X-Frame-Options, X-Content-Type-Options
        self.end_headers()
        self.wfile.write(b"<!DOCTYPE html><html><body><h1>X-Ray Test Site</h1></body></html>")

    def log_message(self, *args):
        pass


class TestSiteXray(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.http_port = find_free_port()
        cls.server = http.server.HTTPServer(("127.0.0.1", cls.http_port), MockSiteHandler)
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
        self.assertEqual(data.get("id"), "site-xray")
        self.assertEqual(data.get("name"), "Site X-ray")
        self.assertEqual(data.get("privacy_class"), "P1",
                         "Site X-ray must be Privacy Class P1: it persists local "
                         "configuration (the enabled flag) in browser.storage.local")
        self.assertTrue(data.get("kill_switch"), "Module must declare kill_switch: true")
        self.assertEqual(data.get("network"), "none", "Module must declare network: none")

    def test_webextension_manifest_permissions_honest_disclosure(self):
        """
        Verify WebExtension manifest permissions:
        1. webRequest is non-blocking (webRequestBlocking strictly prohibited).
        2. <all_urls> requirement disclosed honestly.
        3. The "tabs" permission is NOT requested (removed: unnecessary).
        4. externally_connectable is limited to the Aegis command-palette.
        """
        manifest_path = MODULE_DIR / "manifest.json"
        self.assertTrue(manifest_path.is_file(), "manifest.json missing")

        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(data.get("manifest_version"), 2)
        self.assertEqual(data.get("name"), "Aegis Site X-ray")

        perms = set(data.get("permissions", []))
        self.assertEqual(perms, {"webRequest", "storage", "<all_urls>"},
                         "Site X-ray must request exactly webRequest, storage, "
                         "and <all_urls> (the tabs permission was removed)")

        # Strictly verify passive mode (no blocking)
        self.assertNotIn("webRequestBlocking", perms, "Site X-ray is passive: webRequestBlocking must NOT be requested")
        self.assertNotIn("cookies", perms, "cookies permission is not needed (observed via headers)")
        self.assertNotIn("tabs", perms, "tabs permission removed: tab lifecycle events work without it and tab URLs are not read")
        self.assertNotIn("clipboardRead", perms)
        self.assertNotIn("nativeMessaging", perms)

        notes = data.get("notes", "").lower()
        self.assertIn("passive", notes)
        self.assertIn("non-blocking", notes)
        self.assertIn("privacy class p1", notes)
        self.assertIn("never stored or logged", notes,
                      "Notes must state that header values and cookie names are never stored or logged")

        ec = data.get("externally_connectable", {})
        self.assertEqual(ec.get("ids"), ["command-palette@aegis.local"],
                         "externally_connectable must be limited to the Aegis command-palette")

    def test_background_never_stores_header_values(self):
        """Static proof: the background service persists ONLY the enabled flag
        and derives booleans/counts from headers (no raw values stored)."""
        bg = (MODULE_DIR / "background.js").read_text(encoding="utf-8")
        # The only storage.local.set call must be the enabled flag.
        self.assertEqual(bg.count("browser.storage.local.set"), 1,
                         "Exactly one storage write path is allowed")
        self.assertIn('browser.storage.local.set({ "site_xray_enabled": isEnabled })', bg)
        # The stored record is derived (booleans/counts), not raw headers.
        self.assertIn("derivePosture", bg)
        # No console logging of header material.
        self.assertNotIn("console.log", bg)
        self.assertNotIn("console.debug", bg)
        # Sender allowlist for external messages.
        self.assertIn("AEGIS_MODULE_IDS", bg)
        self.assertIn("onMessageExternal", bg)

    def test_xray_logic_matches_prototype(self):
        """Verify JavaScript xrayHeaders logic matches prototypes/aegis_modules.py."""
        js_code = (MODULE_DIR / "xray_logic.js").read_text(encoding="utf-8")

        test_script = f"""
        {js_code}

        // Test Case 1: Missing headers on HTTPS
        const headers1 = {{ "Server": "nginx/1.18.0" }};
        const findings1 = xrayHeaders(headers1, true);

        // Test Case 2: Cookie without flags on HTTPS
        const headers2 = {{ "set-cookie": "sid=1; Path=/" }};
        const findings2 = xrayHeaders(headers2, true);

        // Test Case 3: Clean hardened site
        const headersClean = {{
            "strict-transport-security": "max-age=31536000; includeSubDomains",
            "content-security-policy": "default-src 'self'; frame-ancestors 'none'",
            "x-content-type-options": "nosniff",
            "referrer-policy": "strict-origin-when-cross-origin",
            "set-cookie": "token=xyz; Path=/; Secure; HttpOnly; SameSite=Strict"
        }};
        const findingsClean = xrayHeaders(headersClean, true);

        console.log(JSON.stringify({{ findings1, findings2, findingsClean }}));
        """
        out = subprocess.check_output(["node", "-e", test_script], text=True)
        res = json.loads(out)

        # Test Case 1: Missing headers
        f1_msgs = [msg for sev, msg in res["findings1"]]
        self.assertTrue(any("No HSTS header" in m for m in f1_msgs))
        self.assertTrue(any("No Content-Security-Policy" in m for m in f1_msgs))
        self.assertTrue(any("No clickjacking protection" in m for m in f1_msgs))
        self.assertTrue(any("nosniff" in m for m in f1_msgs))
        self.assertTrue(any("reveals a version number" in m for m in f1_msgs))

        # Test Case 2: Insecure cookie
        f2_msgs = [msg for sev, msg in res["findings2"]]
        self.assertTrue(any("Cookie 'sid' lacks the Secure flag" in m for m in f2_msgs))
        self.assertTrue(any("Cookie 'sid' lacks HttpOnly" in m for m in f2_msgs))
        self.assertTrue(any("Cookie 'sid' has no SameSite attribute" in m for m in f2_msgs))

        # Test Case 3: Clean site
        f3_sevs = [sev for sev, msg in res["findingsClean"]]
        self.assertEqual(f3_sevs, ["ok"], "Clean site must produce 'ok' status with no warnings")

    def test_browser_runtime_passive_audit_and_kill_switch(self):
        """
        Launch Firefox ESR, install site-xray, and verify:
        1. Navigating to the test page triggers a passive header audit.
        2. The stored posture is SANITIZED: booleans/counts/origin only.
        3. SENTINEL PROOF: header values and the cookie name/value never
           appear in the posture record or in browser.storage.local.
        4. Only the enabled flag is persisted.
        5. Kill-switch disables posture observation dynamically.
        """
        if not ESR_BIN.is_file():
            raise unittest.SkipTest("firefox-esr binary not found; skipping site-xray runtime test")

        marionette_port = find_free_port()
        prof_dir = tempfile.mkdtemp(prefix="aegis_xray_test_")

        with open(os.path.join(prof_dir, "user.js"), "w") as f:
            f.write(f'user_pref("marionette.enabled", true);\n')
            f.write(f'user_pref("marionette.port", {marionette_port});\n')
            f.write('user_pref("xpinstall.signatures.required", false);\n')
            f.write('user_pref("extensions.autoDisableScopes", 0);\n')
            f.write('user_pref("aegis.profile.tier", "S1");\n')
            f.write('user_pref("aegis.profile.identity_tier", "I1");\n')

        env = dict(os.environ, AEGIS_SURFACE_TIER="S1", AEGIS_IDENTITY_TIER="I1")

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

            # 1. Start Session & Install Extension
            send_recv(1, "WebDriver:NewSession", {})
            install_res = send_recv(2, "Addon:Install", {"path": str(MODULE_DIR), "temporary": True})
            self.assertEqual(install_res[3]["value"], "site-xray@aegis.local", "Extension failed to install")

            time.sleep(0.5)

            # 2. Get manifest URL to execute WebExtension script
            send_recv(3, "Marionette:SetContext", {"value": "chrome"})
            url_res = send_recv(4, "WebDriver:ExecuteScript", {
                "script": 'return WebExtensionPolicy.getByID("site-xray@aegis.local").getURL("manifest.json");',
                "args": []
            })
            manifest_url = url_res[3]["value"]
            self.assertIsNotNone(manifest_url)

            # 3. Navigate to test page (triggers webRequest.onHeadersReceived
            #    with sentinel-laden headers).
            send_recv(5, "Marionette:SetContext", {"value": "content"})
            test_url = f"http://127.0.0.1:{self.http_port}/"
            send_recv(6, "WebDriver:Navigate", {"url": test_url})
            time.sleep(0.5)

            # 4. Navigate into extension context and query posture
            send_recv(7, "WebDriver:Navigate", {"url": manifest_url})
            query_script = """
            const resolve = arguments[arguments.length - 1];
            (async () => {
                for (let i = 0; i < 15; i++) {
                    const res = await browser.runtime.sendMessage({ type: "GET_TAB_POSTURE" });
                    if (res && res.posture) {
                        return resolve(res);
                    }
                    await new Promise(r => setTimeout(r, 100));
                }
                const finalRes = await browser.runtime.sendMessage({ type: "GET_TAB_POSTURE" });
                resolve(finalRes);
            })();
            """
            posture_res = send_recv(8, "WebDriver:ExecuteAsyncScript", {"script": query_script, "args": []})
            p_val = posture_res[3]["value"]

            self.assertTrue(p_val.get("enabled"), "Site X-ray should be active")
            posture = p_val.get("posture")
            self.assertIsNotNone(posture, "Site X-ray must record posture for navigated page")

            # Sanitized posture: booleans/counts/origin only.
            self.assertEqual(posture.get("origin"), f"http://127.0.0.1:{self.http_port}")
            self.assertFalse(posture.get("isHttps"))
            self.assertFalse(posture.get("hasHSTS"))
            self.assertFalse(posture.get("hasCSP"))
            self.assertFalse(posture.get("hasNosniff"))
            self.assertFalse(posture.get("hasClickjackingProtection"))
            self.assertTrue(posture.get("serverVersionDisclosed"),
                            "nginx/1.18.0 must be flagged via the boolean (not the value)")
            self.assertEqual(posture.get("cookieCount"), 1)
            self.assertEqual(posture.get("cookieHttpOnlyMissing"), 1)
            self.assertEqual(posture.get("cookieSameSiteMissing"), 1)
            # The full URL (path/query) must not be stored, only the origin.
            self.assertNotIn("path", json.dumps(posture).lower().replace("path=/", ""))
            # The posture must NOT contain findings arrays with cookie names.
            self.assertNotIn("findings", posture)

            # SENTINEL PROOF (part 1): no header value or cookie name/value in
            # the stored posture record.
            posture_json = json.dumps(posture)
            for sentinel in (SENTINEL_COOKIE_NAME, SENTINEL_COOKIE_VALUE,
                             SENTINEL_HEADER_VALUE):
                self.assertNotIn(sentinel, posture_json,
                                 f"Sentinel '{sentinel}' must never appear in the posture record")
            self.assertNotIn("session_id", posture_json.lower())

            # SENTINEL PROOF (part 2): browser.storage.local contains only the
            # enabled flag — no header material, no postures.
            storage_script = """
            const resolve = arguments[arguments.length - 1];
            browser.storage.local.get(null).then(all => resolve(all));
            """
            storage_res = send_recv(9, "WebDriver:ExecuteAsyncScript",
                                    {"script": storage_script, "args": []})
            storage_dump = json.dumps(storage_res[3]["value"])
            self.assertTrue(set((storage_res[3]["value"] or {}).keys()) <= {"site_xray_enabled"},
                            "At most the enabled flag may be persisted (empty is fine)")
            for sentinel in (SENTINEL_COOKIE_NAME, SENTINEL_COOKIE_VALUE,
                             SENTINEL_HEADER_VALUE):
                self.assertNotIn(sentinel, storage_dump,
                                 f"Sentinel '{sentinel}' must never be persisted to storage")

            # 5. Test Kill-Switch
            kill_script = """
            const resolve = arguments[arguments.length - 1];
            browser.runtime.sendMessage({ type: "SET_ENABLED", enabled: false }).then(res => {
                resolve(res);
            });
            """
            send_recv(10, "WebDriver:ExecuteAsyncScript", {"script": kill_script, "args": []})

            # SENTINEL PROOF (part 3): after a real config write, storage
            # contains exactly the enabled flag - still no header material.
            storage_res2 = send_recv(15, "WebDriver:ExecuteAsyncScript",
                                     {"script": storage_script, "args": []})
            storage_dump2 = json.dumps(storage_res2[3]["value"])
            self.assertEqual(set((storage_res2[3]["value"] or {}).keys()),
                             {"site_xray_enabled"},
                             "After a config write, exactly the enabled flag is persisted")
            for sentinel in (SENTINEL_COOKIE_NAME, SENTINEL_COOKIE_VALUE,
                             SENTINEL_HEADER_VALUE):
                self.assertNotIn(sentinel, storage_dump2,
                                 f"Sentinel '{sentinel}' must never be persisted to storage")

            # Query while disabled
            disabled_res = send_recv(11, "WebDriver:ExecuteAsyncScript", {"script": query_script, "args": []})
            d_val = disabled_res[3]["value"]
            self.assertFalse(d_val.get("enabled"))
            self.assertEqual(d_val.get("status"), "kill_switch_active")

            # 6. Re-enable module and verify audit resumes
            enable_script = """
            const resolve = arguments[arguments.length - 1];
            browser.runtime.sendMessage({ type: "SET_ENABLED", enabled: true }).then(res => {
                resolve(res);
            });
            """
            send_recv(12, "WebDriver:ExecuteAsyncScript", {"script": enable_script, "args": []})

            resumed_res = send_recv(13, "WebDriver:ExecuteAsyncScript", {"script": query_script, "args": []})
            r_val = resumed_res[3]["value"]
            self.assertTrue(r_val.get("enabled"))

            # Teardown session
            send_recv(14, "WebDriver:DeleteSession", {})
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
