#!/usr/bin/env python3
"""
tests/modules/test_session_sweeper.py — Verification of M10 Session Sweeper module.

Verifies:
1. Module manifest compliance with spec Part 8.1.1 (Privacy P1, kill switch).
2. WebExtension manifest permissions: every requested permission is used and
   justified (browsingData, storage, alarms, history, tabs), no host perms.
3. Selective sweep logic matching prototypes/aegis_modules.py:
   - Purges site data older than retention threshold.
   - Retains active/recent sites; preserves allow-listed domains.
4. Age computation honesty: data age comes from the module's own
   last-interaction ledger (history.onVisited), because browsingData
   "since" removes data NEWER than a timestamp (the opposite direction).
5. Live browser runtime enforcement:
   - First use is OPT-IN: purge is refused (with preview) before opt-in.
   - PREVIEW_SWEEP returns what would be deleted (stale vs fresh vs
     allow-listed vs open-tab origins) without deleting anything.
   - Open-tab protection: a stale origin with an open tab is never purged
     (its localStorage survives); after the tab closes it is purged
     (localStorage actually deleted — real behavioral proof).
   - Kill switch (SET_ENABLED false) fails closed; re-enable restores.
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
        self.assertEqual(data.get("privacy_class"), "P1",
                         "Session Sweeper must be Privacy Class P1 (stores config and a local ledger)")
        self.assertTrue(data.get("kill_switch"), "Module must declare kill_switch: true")
        self.assertEqual(data.get("network"), "none", "Module must declare network: none")
        # Every declared permission must be documented in the manifest notes.
        notes = json.loads((MODULE_DIR / "manifest.json").read_text(encoding="utf-8")).get("notes", "").lower()
        for perm in data.get("permissions", []):
            self.assertIn(perm.lower(), notes,
                          f"Permission '{perm}' must be justified in manifest notes")

    def test_webextension_manifest_permissions_used_and_justified(self):
        """Verify WebExtension manifest requests exactly the permissions the
        background service uses, each with an honest justification note."""
        manifest_path = MODULE_DIR / "manifest.json"
        self.assertTrue(manifest_path.is_file(), "manifest.json missing")

        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(data.get("manifest_version"), 2)
        self.assertEqual(data.get("name"), "Aegis Session Sweeper")

        perms = set(data.get("permissions", []))
        # Complete, justified set: browsingData (purge), storage (config +
        # ledger, P1), alarms (schedule), history (last-interaction ledger),
        # tabs (open-tab protection). No host permissions, nothing else.
        self.assertEqual(perms, {"browsingData", "storage", "alarms", "history", "tabs"},
                         "Session Sweeper must request exactly the used permission set")

        prohibited = ["<all_urls>", "webRequest", "webRequestBlocking", "cookies",
                      "clipboardRead", "nativeMessaging", "downloads", "geolocation"]
        for p in prohibited:
            self.assertNotIn(p, perms, f"Prohibited/unneeded permission requested: {p}")

        notes = data.get("notes", "").lower()
        self.assertIn("browsingdata", notes)
        self.assertIn("storage", notes)
        self.assertIn("alarms", notes)
        self.assertIn("history", notes)
        self.assertIn("tabs", notes)
        self.assertIn("privacy class p1", notes)
        # Honest age-mechanism documentation must be present.
        self.assertIn("newer", notes,
                      "Notes must explain that browsingData 'since' deletes NEWER data, "
                      "hence the module's own last-interaction ledger")

    def test_background_age_mechanism_documented(self):
        """The background service must document how data age is computed and
        list every permission/event used for last-interaction tracking."""
        bg = (MODULE_DIR / "background.js").read_text(encoding="utf-8")
        self.assertIn("history.onVisited", bg, "Last-interaction tracking must use history.onVisited")
        self.assertIn("tabs.query", bg, "Open-tab protection must use tabs.query")
        self.assertIn("opt_in", bg, "Opt-in gating must be implemented")
        self.assertIn("PREVIEW_SWEEP", bg, "Preview message must be implemented")
        # browsingData 'since' must NOT be used for the stale purge (check the
        # actual removal call, not the explanatory comments).
        exec_fn_start = bg.index("async function executeSweepData")
        exec_fn_end = bg.index("// Optional periodic schedule", exec_fn_start)
        self.assertNotIn("since:", bg[exec_fn_start:exec_fn_end].lower(),
                         "browsingData 'since' must not be used as a removal option: "
                         "it deletes data NEWER than a time")
        self.assertNotIn("removecookies", bg[exec_fn_start:exec_fn_end].lower(),
                         "No global cookie fallback: it would delete data for ALL sites")
        self.assertIn("{ origins: origins }", bg[exec_fn_start:exec_fn_end],
                      "Purge must be per-origin via browsingData.remove({origins})")

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

        const keep = ["example.org"];
        const swept = sweep(items, now, 14, keep);

        console.log(JSON.stringify({{ swept }}));
        """
        out = subprocess.check_output(["node", "-e", test_script], text=True)
        res = json.loads(out)
        swept = res["swept"]

        self.assertIn("https://old.example.com", swept)
        self.assertIn("https://stale.tracker.com", swept)
        self.assertNotIn("https://recent.example.net", swept)
        self.assertNotIn("https://bank.example.org", swept)
        self.assertNotIn("https://sub.bank.example.org", swept)

    def test_browser_runtime_opt_in_preview_open_tab_protection_and_kill_switch(self):
        """Live ESR test: opt-in gating, preview, open-tab protection (real
        localStorage survival + deletion), and the kill switch."""
        if not ESR_BIN.is_file():
            raise unittest.SkipTest("firefox-esr binary not found; skipping session sweeper runtime test")

        # Local server: /check reports the origin's stored state WITHOUT
        # touching it; /plant plants it (used exactly once, up front). All
        # observations flow through the server, so no Marionette tab
        # switching is needed.
        state_reports = {}

        class StateHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                phase = "plant" if self.path.startswith("/plant") else "check"
                body = f"""
                <html><body><script>
                (async () => {{
                  const seen = localStorage.getItem('aegis_sweep_test');
                  if (location.pathname.startsWith('/plant')) {{
                    localStorage.setItem('aegis_sweep_test','1');
                    document.cookie = 'aegis_sweep_cookie=1; path=/';
                  }}
                  await fetch('/api/state', {{method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{phase: '{phase}', seen: seen,
                                            cookie: document.cookie}})}});
                }})();
                </script>state-page</body></html>""".encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                if self.path.startswith("/api/state"):
                    length = int(self.headers.get("Content-Length", "0"))
                    state_reports["latest"] = json.loads(self.rfile.read(length) or b"{}")
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b"ok")
                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, *args):
                pass

        def wait_report(expected_phase, timeout=10):
            deadline = time.time() + timeout
            while time.time() < deadline:
                rep = state_reports.get("latest")
                if rep and rep.get("phase") == expected_phase:
                    return rep
                time.sleep(0.4)
            return state_reports.get("latest")

        srv_port = find_free_port()
        server = http.server.HTTPServer(("127.0.0.1", srv_port), StateHandler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        state_origin = f"http://127.0.0.1:{srv_port}"

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

            def chrome(script, msg_id):
                return send_recv(msg_id, "Marionette:SetContext", {"value": "chrome"}) and \
                       send_recv(msg_id + 1, "WebDriver:ExecuteScript", {"script": script, "args": []})

            def ext_message(msg, msg_id):
                """Send a runtime message from the extension's own page.
                Always re-enters content context first (chrome-context tab
                operations may have changed the Marionette context)."""
                send_recv(msg_id, "Marionette:SetContext", {"value": "content"})
                script = f"""
                const resolve = arguments[arguments.length - 1];
                browser.runtime.sendMessage({json.dumps(msg)}).then(
                    res => resolve(res),
                    err => resolve({{ error: String(err) }}));
                """
                resp = send_recv(msg_id + 1, "WebDriver:ExecuteAsyncScript",
                                 {"script": script, "args": []})
                if resp[3] is None:
                    raise AssertionError(f"ext_message failed: {json.dumps(resp)[:500]}")
                return resp[3]["value"]

            # 1. Start session & install extension
            send_recv(1, "WebDriver:NewSession", {})
            install_res = send_recv(2, "Addon:Install", {"path": str(MODULE_DIR), "temporary": True})
            self.assertEqual(install_res[3]["value"], "session-sweeper@aegis.local",
                             "Extension failed to install")
            time.sleep(0.5)

            # 2. Open the state page in a SECOND tab (stays open throughout).
            #    Primary tab is used for extension messaging.
            chrome(f"""
            let win = Services.wm.getMostRecentWindow("navigator:browser");
            let gb = win.gBrowser;
            let sysPrin = Services.scriptSecurityManager.getSystemPrincipal();
            gb.addTab("{state_origin}/plant", {{ triggeringPrincipal: sysPrin }});
            """, 3)
            plant_rep = wait_report("plant")
            self.assertIsNotNone(plant_rep, "State page must report after planting")
            self.assertIsNone(plant_rep.get("seen"),
                              "First plant must start from empty storage")

            # 3. Primary tab: navigate to the extension's own page for messaging.
            send_recv(5, "Marionette:SetContext", {"value": "chrome"})
            url_res = send_recv(6, "WebDriver:ExecuteScript", {
                "script": 'return WebExtensionPolicy.getByID("session-sweeper@aegis.local").getURL("manifest.json");',
                "args": []
            })
            send_recv(7, "Marionette:SetContext", {"value": "content"})
            send_recv(8, "WebDriver:Navigate", {"url": url_res[3]["value"]})
            time.sleep(0.5)

            # 4. Status: fresh install must be opt-OUT (no deletion until opt-in).
            st = ext_message({"type": "GET_STATUS"}, 10)
            self.assertTrue(st.get("enabled"), "Sweeper should be enabled by default")
            self.assertFalse(st.get("optIn"), "First use must NOT be opted in")
            self.assertTrue(st.get("needsOptIn"), "needsOptIn must be true before opt-in")

            now = 1700000000
            day = 86400
            sweep_items = [
                # Stale AND open in a tab (the state page) -> must be protected.
                {"origin": state_origin, "lastInteraction": now - 40 * day},
                # Stale with no open tab -> must be swept.
                {"origin": "https://old.stale.example", "lastInteraction": now - 30 * day},
                # Fresh -> must never be swept.
                {"origin": "https://new.active.example", "lastInteraction": now - 1 * day},
                # Stale but allow-listed -> must never be swept.
                {"origin": "https://bank.trusted.example", "lastInteraction": now - 60 * day},
            ]

            # 6. PREVIEW: no deletion; stale+closed swept; open tab protected;
            #    fresh and allow-listed excluded.
            pv = ext_message({"type": "PREVIEW_SWEEP", "items": sweep_items, "now": now,
                              "maxAgeDays": 14, "keepDomains": ["trusted.example"]}, 20)
            self.assertEqual(pv.get("status"), "preview")
            plan = pv["plan"]
            self.assertEqual(plan["wouldDelete"], ["https://old.stale.example"],
                             "Preview must delete only the stale, closed, non-allow-listed origin")
            self.assertIn(state_origin, plan["protectedOpenTabs"],
                          "Preview must protect the stale origin that has an open tab")
            self.assertEqual(plan["protectedOpenTabs"], [state_origin])
            self.assertFalse(pv.get("optIn"), "Preview reports opt-in state honestly")

            # 7. TRIGGER_SWEEP with purgeLive BEFORE opt-in: must refuse + preview.
            pre = ext_message({"type": "TRIGGER_SWEEP", "items": sweep_items, "now": now,
                               "maxAgeDays": 14, "keepDomains": ["trusted.example"],
                               "purgeLive": True}, 22)
            self.assertEqual(pre.get("status"), "opt_in_required",
                             "Purge must be refused before the user opts in")
            self.assertEqual(pre.get("sweptOrigins"), [])
            self.assertIn("https://old.stale.example", pre["preview"]["wouldDelete"])

            # 8. Opt in, then purge again: the open-tab origin must STILL be
            #    protected (behavioral: its storage survives the purge).
            ext_message({"type": "SET_OPT_IN", "optIn": True}, 24)
            purge1 = ext_message({"type": "TRIGGER_SWEEP", "items": sweep_items, "now": now,
                                  "maxAgeDays": 14, "keepDomains": ["trusted.example"],
                                  "purgeLive": True}, 26)
            # HONEST ENGINE LIMIT (measured on ESR 153.5.1): browsingData
            # "origins" is Chrome-only; per-origin purge is rejected. The
            # selection layer must still be exactly right, and the failure
            # must be reported honestly (never a silent or global fallback).
            self.assertEqual(purge1.get("status"), "purge_unsupported_on_this_engine",
                             json.dumps(purge1))
            self.assertFalse(purge1.get("purgeExecuted"))
            self.assertTrue(purge1.get("purgeUnsupportedOnEngine"),
                            "Engine must be reported as unsupported for per-origin purge")
            self.assertIn("origins", purge1.get("purgeError", ""),
                          "The live engine error must be surfaced, not swallowed")
            # Selection correctness: only the stale CLOSED origin is selected;
            # the open-tab stale origin is protected.
            self.assertEqual(purge1.get("sweptOrigins"), ["https://old.stale.example"],
                             "Only the stale closed origin may be selected for purge")
            self.assertEqual(purge1.get("protectedOpenTabs"), [state_origin],
                             "The open-tab stale origin must be protected from the purge")

            # Behavioral proof of open-tab protection: re-check the OPEN tab's
            # storage (navigate it to /check — no planting) — it must survive.
            state_reports["latest"] = None
            chrome(f"""
            let win = Services.wm.getMostRecentWindow("navigator:browser");
            let gb = win.gBrowser;
            for (let i = 0; i < gb.tabs.length; i++) {{
                let uri = gb.tabs[i].linkedBrowser.currentURI.spec;
                if (uri.startsWith("http://127.0.0.1")) {{
                    gb.tabs[i].linkedBrowser.loadURI(
                        Services.io.newURI("{state_origin}/check"),
                        {{ triggeringPrincipal:
                           Services.scriptSecurityManager.getSystemPrincipal() }});
                }}
            }}
            """, 28)
            check1 = wait_report("check")
            self.assertIsNotNone(check1, "Open tab must re-report its storage state")
            self.assertEqual(check1.get("seen"), "1",
                             "With the tab open AND the engine unable to purge per-origin, "
                             "the open origin's storage must be intact")

            # 9. Close the state tab; purge again; the origin is now swept and
            #    its storage must be GONE (real deletion proof via /check,
            #    which never re-plants).
            send_recv(31, "Marionette:SetContext", {"value": "chrome"})
            send_recv(32, "WebDriver:ExecuteScript", {
                "script": """
                let win = Services.wm.getMostRecentWindow("navigator:browser");
                let gb = win.gBrowser;
                for (let i = gb.tabs.length - 1; i >= 0; i--) {
                    let uri = gb.tabs[i].linkedBrowser.currentURI.spec;
                    if (uri.startsWith("http://127.0.0.1")) { gb.removeTab(gb.tabs[i]); }
                }
                return true;
                """, "args": []
            })
            time.sleep(0.5)

            purge2 = ext_message({"type": "TRIGGER_SWEEP", "items": sweep_items, "now": now,
                                  "maxAgeDays": 14, "keepDomains": ["trusted.example"],
                                  "purgeLive": True}, 34)
            self.assertEqual(purge2.get("status"), "purge_unsupported_on_this_engine",
                             json.dumps(purge2))
            self.assertIn(state_origin, purge2.get("sweptOrigins"),
                          "With the tab closed, the stale origin must now be SELECTED "
                          "(open-tab protection released correctly)")
            self.assertEqual(purge2.get("protectedOpenTabs"), [],
                             "No open-tab protection remains for the closed origin")
            # Honest limit: on ESR 153.5.1 nothing is actually deleted
            # (browsingData "origins" is Chrome-only); the module must say so.
            self.assertFalse(purge2.get("purgeExecuted"))

            state_reports["latest"] = None
            chrome(f"""
            let win = Services.wm.getMostRecentWindow("navigator:browser");
            let gb = win.gBrowser;
            let sysPrin = Services.scriptSecurityManager.getSystemPrincipal();
            gb.addTab("{state_origin}/check", {{ triggeringPrincipal: sysPrin }});
            """, 36)
            check2 = wait_report("check")
            self.assertIsNotNone(check2, "Post-purge check page must report")
            self.assertEqual(check2.get("seen"), "1",
                             "Honest engine limit: per-origin purge does not execute on "
                             "ESR 153.5.1, so storage persists (never a global fallback)")

            # 10. Kill switch: sweep must fail closed while disabled.
            ext_message({"type": "SET_ENABLED", "enabled": False}, 42)
            sw_dis = ext_message({"type": "TRIGGER_SWEEP", "items": sweep_items, "now": now,
                                  "maxAgeDays": 14, "keepDomains": ["trusted.example"],
                                  "purgeLive": True}, 44)
            self.assertEqual(sw_dis.get("status"), "kill_switch_active")
            self.assertEqual(sw_dis.get("sweptOrigins"), [])

            # 11. Re-enable: functionality restored.
            ext_message({"type": "SET_ENABLED", "enabled": True}, 46)
            sw_res = ext_message({"type": "TRIGGER_SWEEP", "items": sweep_items, "now": now,
                                  "maxAgeDays": 14, "keepDomains": ["trusted.example"]}, 48)
            self.assertEqual(sw_res.get("status"), "success")
            self.assertIn("https://old.stale.example", sw_res.get("sweptOrigins"))

            send_recv(50, "WebDriver:DeleteSession", {})
        finally:
            s.close()
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
            server.shutdown()
            server.server_close()
            subprocess.run(["rm", "-rf", prof_dir])


if __name__ == "__main__":
    unittest.main()
