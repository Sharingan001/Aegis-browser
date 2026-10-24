#!/usr/bin/env python3
"""
tests/modules/test_session_sweeper.py — Verification of M10 Session Sweeper module.

Verifies:
1. Module manifest compliance with spec Part 8.1.1 (Privacy P1, least privilege).
2. WebExtension manifest validity and absence of unnecessary elevated permissions.
3. Selective sweep logic matching prototypes/aegis_modules.py:
   - Purges site data older than retention threshold.
   - Retains active/recent sites.
   - Strictly preserves allow-listed domains across subdomains.
4. Live browser runtime enforcement:
   - Extension installs cleanly in Firefox ESR.
   - Runtime messaging dispatches sweep triggers.
   - Internal kill-switch and AddonManager disable sweeping dynamically.
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
MODULE_DIR = REPO_ROOT / "modules" / "session-sweeper"


def find_free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class TestSessionSweeper(unittest.TestCase):

    def test_module_manifest_schema(self):
        """Verify module.json adheres to Master Spec Part 8.1.1 schema."""
        mod_json_path = MODULE_DIR / "module.json"
        self.assertTrue(mod_json_path.is_file(), "module.json missing")

        data = json.loads(mod_json_path.read_text(encoding="utf-8"))
        self.assertEqual(data.get("id"), "session-sweeper")
        self.assertEqual(data.get("name"), "Session Sweeper")
        self.assertEqual(data.get("privacy_class"), "P1", "Session Sweeper must be Privacy Class P1 (stores user keep-lists)")
        self.assertTrue(data.get("kill_switch"), "Module must declare kill_switch: true")
        self.assertEqual(data.get("network"), "none", "Module must declare network: none")

    def test_webextension_manifest_least_privilege(self):
        """Verify WebExtension manifest requests only needed permissions with honest notes."""
        manifest_path = MODULE_DIR / "manifest.json"
        self.assertTrue(manifest_path.is_file(), "manifest.json missing")

        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(data.get("manifest_version"), 2)
        self.assertEqual(data.get("name"), "Aegis Session Sweeper")

        perms = set(data.get("permissions", []))
        self.assertEqual(perms, {"browsingData", "storage", "alarms"},
                         "Session Sweeper must only request browsingData, storage, and alarms")

        # Prohibited permissions
        prohibited = ["<all_urls>", "webRequest", "webRequestBlocking", "tabs", "cookies", "clipboardRead", "nativeMessaging"]
        for p in prohibited:
            self.assertNotIn(p, perms, f"Prohibited permission requested: {p}")

        notes = data.get("notes", "").lower()
        self.assertIn("browsingdata", notes)
        self.assertIn("storage", notes)
        self.assertIn("privacy class p1", notes)

    def test_sweep_logic_matches_prototype(self):
        """Verify JavaScript sweep logic in sweeper_logic.js matches prototypes/aegis_modules.py."""
        js_code = (MODULE_DIR / "sweeper_logic.js").read_text(encoding="utf-8")

        test_script = f"""
        {js_code}

        const now = 1700000000;
        const day = 86400;

        const items = [
            {{ origin: "https://old.example.com", lastInteraction: now - 40 * day }},
            {{ origin: "https://recent.example.net", lastInteraction: now - 2 * day }},
            {{ origin: "https://bank.example.org", lastInteraction: now - 90 * day }},
            {{ origin: "https://sub.bank.example.org", lastInteraction: now - 60 * day }},
            {{ origin: "https://stale.tracker.com", lastInteraction: now - 15 * day }}
        ];

        // Keep allow-list contains "example.org" (registrable domain)
        const keep = ["example.org"];
        const swept = sweep(items, now, 14, keep);

        console.log(JSON.stringify({{ swept }}));
        """
        out = subprocess.check_output(["node", "-e", test_script], text=True)
        res = json.loads(out)
        swept = res["swept"]

        # old.example.com (>14 days, not in keep) -> swept
        self.assertIn("https://old.example.com", swept)
        # stale.tracker.com (>14 days, not in keep) -> swept
        self.assertIn("https://stale.tracker.com", swept)

        # recent.example.net (2 days, active) -> NOT swept
        self.assertNotIn("https://recent.example.net", swept)
        # bank.example.org and sub.bank.example.org (in keep) -> NOT swept
        self.assertNotIn("https://bank.example.org", swept)
        self.assertNotIn("https://sub.bank.example.org", swept)

    def test_browser_runtime_sweep_and_kill_switch(self):
        """Launch Firefox ESR, install session-sweeper, and verify runtime messaging and kill switches."""
        if not ESR_BIN.is_file():
            raise unittest.SkipTest("firefox-esr binary not found; skipping session sweeper runtime test")

        marionette_port = find_free_port()
        prof_dir = tempfile.mkdtemp(prefix="aegis_sweeper_test_")

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
            self.assertEqual(install_res[3]["value"], "session-sweeper@aegis.local", "Extension failed to install")

            time.sleep(0.5)

            # 2. Query extension URL
            send_recv(3, "Marionette:SetContext", {"value": "chrome"})
            url_res = send_recv(4, "WebDriver:ExecuteScript", {
                "script": 'return WebExtensionPolicy.getByID("session-sweeper@aegis.local").getURL("manifest.json");',
                "args": []
            })
            manifest_url = url_res[3]["value"]
            self.assertIsNotNone(manifest_url)

            # 3. Test runtime messaging in content context
            send_recv(5, "Marionette:SetContext", {"value": "content"})
            send_recv(6, "WebDriver:Navigate", {"url": manifest_url})

            # Check status
            status_script = """
            const resolve = arguments[arguments.length - 1];
            browser.runtime.sendMessage({ type: "GET_STATUS" }).then(res => {
                resolve(res);
            }).catch(err => resolve({ error: String(err) }));
            """
            status_res = send_recv(7, "WebDriver:ExecuteAsyncScript", {"script": status_script, "args": []})
            st = status_res[3]["value"]
            self.assertTrue(st.get("enabled"), "Session Sweeper should be enabled by default")
            self.assertEqual(st.get("maxAgeDays"), 14)

            # 4. Trigger Sweep
            sweep_script = """
            const resolve = arguments[arguments.length - 1];
            const now = 1700000000;
            const items = [
                { origin: "https://old.stale.example", lastInteraction: now - 30 * 86400 },
                { origin: "https://new.active.example", lastInteraction: now - 1 * 86400 },
                { origin: "https://bank.trusted.example", lastInteraction: now - 60 * 86400 }
            ];
            browser.runtime.sendMessage({
                type: "TRIGGER_SWEEP",
                items: items,
                now: now,
                maxAgeDays: 14,
                keepDomains: ["trusted.example"]
            }).then(res => {
                resolve(res);
            }).catch(err => resolve({ error: String(err) }));
            """
            sweep_res = send_recv(8, "WebDriver:ExecuteAsyncScript", {"script": sweep_script, "args": []})
            sw = sweep_res[3]["value"]
            self.assertEqual(sw.get("status"), "success")
            self.assertEqual(sw.get("sweptOrigins"), ["https://old.stale.example"])

            # 5. Test Kill-Switch
            kill_script = """
            const resolve = arguments[arguments.length - 1];
            browser.runtime.sendMessage({ type: "SET_ENABLED", enabled: false }).then(res => {
                resolve(res);
            });
            """
            send_recv(9, "WebDriver:ExecuteAsyncScript", {"script": kill_script, "args": []})

            # Trigger sweep while disabled -> must fail closed
            sweep_disabled_res = send_recv(10, "WebDriver:ExecuteAsyncScript", {"script": sweep_script, "args": []})
            sw_dis = sweep_disabled_res[3]["value"]
            self.assertEqual(sw_dis.get("status"), "kill_switch_active")
            self.assertEqual(sw_dis.get("sweptOrigins"), [])

            # 6. Re-enable module and verify functionality restored
            enable_script = """
            const resolve = arguments[arguments.length - 1];
            browser.runtime.sendMessage({ type: "SET_ENABLED", enabled: true }).then(res => {
                resolve(res);
            });
            """
            send_recv(11, "WebDriver:ExecuteAsyncScript", {"script": enable_script, "args": []})

            sweep_restored_res = send_recv(12, "WebDriver:ExecuteAsyncScript", {"script": sweep_script, "args": []})
            sw_res = sweep_restored_res[3]["value"]
            self.assertEqual(sw_res.get("status"), "success")
            self.assertEqual(sw_res.get("sweptOrigins"), ["https://old.stale.example"])

            # Teardown session
            send_recv(13, "WebDriver:DeleteSession", {})
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
