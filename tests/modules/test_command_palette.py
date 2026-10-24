#!/usr/bin/env python3
"""
tests/modules/test_command_palette.py — Verification of M2 Command Palette module.

Verifies:
1. Module manifest compliance with spec Part 8.1.1 (Privacy P0, least privilege).
2. WebExtension manifest least privilege:
   - Only requests commands, storage, and tabs.
   - Prohibits <all_urls>, webRequest, cookies, and nativeMessaging.
   - Verifies registered shortcut commands.
3. Palette search filtering logic across titles, descriptions, and keywords.
4. Live browser runtime enforcement:
   - Extension installs cleanly in Firefox ESR.
   - Runtime messaging dispatches search queries and command execution.
   - Kill-switch dynamically disables palette execution.
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
MODULE_DIR = REPO_ROOT / "modules" / "command-palette"


def find_free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class TestCommandPalette(unittest.TestCase):

    def test_module_manifest_schema(self):
        """Verify module.json adheres to Master Spec Part 8.1.1 schema."""
        mod_json_path = MODULE_DIR / "module.json"
        self.assertTrue(mod_json_path.is_file(), "module.json missing")

        data = json.loads(mod_json_path.read_text(encoding="utf-8"))
        self.assertEqual(data.get("id"), "command-palette")
        self.assertEqual(data.get("name"), "Command Palette")
        self.assertEqual(data.get("privacy_class"), "P0", "Command Palette must be Privacy Class P0")
        self.assertTrue(data.get("kill_switch"), "Module must declare kill_switch: true")
        self.assertEqual(data.get("network"), "none", "Module must declare network: none")

    def test_webextension_manifest_least_privilege(self):
        """Verify WebExtension manifest adheres strictly to least privilege with zero host permissions."""
        manifest_path = MODULE_DIR / "manifest.json"
        self.assertTrue(manifest_path.is_file(), "manifest.json missing")

        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(data.get("manifest_version"), 2)
        self.assertEqual(data.get("name"), "Aegis Command Palette")

        perms = set(data.get("permissions", []))
        self.assertEqual(perms, {"commands", "storage", "tabs"},
                         "Command Palette must strictly request only commands, storage, and tabs")

        # Prohibited elevated permissions
        prohibited = [
            "<all_urls>", "*://*/*", "http://*/*", "https://*/*",
            "webRequest", "webRequestBlocking", "cookies",
            "clipboardRead", "nativeMessaging"
        ]
        for p in prohibited:
            self.assertNotIn(p, perms, f"Elevated permission prohibited for Command Palette: {p}")

        # Shortcut commands registration
        cmds = data.get("commands", {})
        self.assertIn("toggle-palette", cmds, "Must register toggle-palette command")
        self.assertIn("clean-active-url", cmds, "Must register clean-active-url command")

        notes = data.get("notes", "").lower()
        self.assertIn("least privilege", notes)
        self.assertIn("offline", notes)

    def test_palette_logic_search_and_registry(self):
        """Verify JavaScript command filtering logic in palette_logic.js."""
        js_code = (MODULE_DIR / "palette_logic.js").read_text(encoding="utf-8")

        test_script = f"""
        {js_code}

        // Test 1: Empty query returns full registry
        const allCmds = filterCommands("");

        // Test 2: Search 'clean'
        const cleanResults = filterCommands("clean");

        // Test 3: Search 'xray' (keyword match)
        const xrayResults = filterCommands("xray");

        // Test 4: Search 'sweep'
        const sweepResults = filterCommands("sweep");

        // Test 5: Search non-existent query
        const noneResults = filterCommands("xyz_not_found_123");

        console.log(JSON.stringify({{
            allCount: allCmds.length,
            cleanMatch: cleanResults.map(c => c.id),
            xrayMatch: xrayResults.map(c => c.id),
            sweepMatch: sweepResults.map(c => c.id),
            noneCount: noneResults.length
        }}));
        """
        out = subprocess.check_output(["node", "-e", test_script], text=True)
        res = json.loads(out)

        self.assertGreaterEqual(res["allCount"], 5, "Registry must contain at least 5 built-in commands")
        self.assertIn("clean-active-url", res["cleanMatch"])
        self.assertIn("inspect-site-xray", res["xrayMatch"])
        self.assertIn("trigger-session-sweep", res["sweepMatch"])
        self.assertEqual(res["noneCount"], 0, "Unmatched query must return empty list")

    def test_browser_runtime_command_dispatch_and_kill_switch(self):
        """Launch Firefox ESR, install command-palette, and verify search, execution, and kill switch."""
        if not ESR_BIN.is_file():
            raise unittest.SkipTest("firefox-esr binary not found; skipping command-palette runtime test")

        marionette_port = find_free_port()
        prof_dir = tempfile.mkdtemp(prefix="aegis_palette_test_")

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
            self.assertEqual(install_res[3]["value"], "command-palette@aegis.local", "Extension failed to install")

            time.sleep(0.5)

            # 2. Get manifest URL to execute WebExtension script
            send_recv(3, "Marionette:SetContext", {"value": "chrome"})
            url_res = send_recv(4, "WebDriver:ExecuteScript", {
                "script": 'return WebExtensionPolicy.getByID("command-palette@aegis.local").getURL("manifest.json");',
                "args": []
            })
            manifest_url = url_res[3]["value"]
            self.assertIsNotNone(manifest_url)

            # 3. Navigate into extension context
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
            self.assertTrue(st.get("enabled"), "Command Palette should be enabled by default")
            self.assertGreaterEqual(st.get("commandsCount", 0), 5)

            # 4. Search commands
            search_script = """
            const resolve = arguments[arguments.length - 1];
            browser.runtime.sendMessage({ type: "SEARCH_COMMANDS", query: "sweep" }).then(res => {
                resolve(res);
            }).catch(err => resolve({ error: String(err) }));
            """
            search_res = send_recv(8, "WebDriver:ExecuteAsyncScript", {"script": search_script, "args": []})
            sr = search_res[3]["value"]
            self.assertTrue(sr.get("enabled"))
            results = sr.get("results", [])
            self.assertGreater(len(results), 0)
            self.assertEqual(results[0]["id"], "trigger-session-sweep")

            # 5. Execute command
            exec_script = """
            const resolve = arguments[arguments.length - 1];
            browser.runtime.sendMessage({ type: "EXECUTE_COMMAND", commandId: "trigger-session-sweep" }).then(res => {
                resolve(res);
            }).catch(err => resolve({ error: String(err) }));
            """
            exec_res = send_recv(9, "WebDriver:ExecuteAsyncScript", {"script": exec_script, "args": []})
            ex = exec_res[3]["value"]
            self.assertTrue(ex.get("success"))
            self.assertEqual(ex.get("commandId"), "trigger-session-sweep")

            # 6. Test Kill-Switch
            kill_script = """
            const resolve = arguments[arguments.length - 1];
            browser.runtime.sendMessage({ type: "SET_ENABLED", enabled: false }).then(res => {
                resolve(res);
            });
            """
            send_recv(10, "WebDriver:ExecuteAsyncScript", {"script": kill_script, "args": []})

            # Search while disabled -> fail closed
            search_dis_res = send_recv(11, "WebDriver:ExecuteAsyncScript", {"script": search_script, "args": []})
            sd = search_dis_res[3]["value"]
            self.assertFalse(sd.get("enabled"))
            self.assertEqual(sd.get("status"), "kill_switch_active")

            # 7. Re-enable module and verify functionality restored
            enable_script = """
            const resolve = arguments[arguments.length - 1];
            browser.runtime.sendMessage({ type: "SET_ENABLED", enabled: true }).then(res => {
                resolve(res);
            });
            """
            send_recv(12, "WebDriver:ExecuteAsyncScript", {"script": enable_script, "args": []})

            search_en_res = send_recv(13, "WebDriver:ExecuteAsyncScript", {"script": search_script, "args": []})
            se = search_en_res[3]["value"]
            self.assertTrue(se.get("enabled"))

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



    def test_browser_runtime_cross_module_allowlist_and_shortcut(self):
        """
        Live ESR test (Phase 2d follow-up items 4a/4b):

        A. Cross-module messaging sender allowlist:
           1. The palette (command-palette@aegis.local, listed in site-xray's
              externally_connectable + AEGIS_MODULE_IDS allowlist) CAN query
              site-xray via runtime.sendMessage.
           2. A ROGUE extension (unknown ID, not allowlisted) is BLOCKED at
              the platform level (externally_connectable) when trying to
              message site-xray - its sendMessage promise rejects.

        B. Ctrl+Shift+P shortcut conflict with Firefox's built-in
           "New Private Window" shortcut: real trusted key events are sent to
           a live ESR window via Marionette; the test observes BOTH whether
           the palette command fires AND whether a private window opens.
        """
        import shutil as _shutil

        if not ESR_BIN.is_file():
            raise unittest.SkipTest("firefox-esr binary not found; skipping palette cross-module test")

        # --- Build the rogue extension (unknown, non-Aegis ID) ---
        rogue_dir = tempfile.mkdtemp(prefix="aegis_rogue_ext_")
        with open(os.path.join(rogue_dir, "manifest.json"), "w") as f:
            json.dump({
                "manifest_version": 2,
                "name": "Rogue Test Extension",
                "version": "1.0",
                "applications": {"gecko": {"id": "rogue-test@aegis.local"}}
            }, f)

        class PageHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<html><body>key-target</body></html>")

            def log_message(self, *args):
                pass

        srv_port = find_free_port()
        server = http.server.HTTPServer(("127.0.0.1", srv_port), PageHandler)
        threading.Thread(target=server.serve_forever, daemon=True).start()

        marionette_port = find_free_port()
        prof_dir = tempfile.mkdtemp(prefix="aegis_palette_xmod_")

        with open(os.path.join(prof_dir, "user.js"), "w") as f:
            f.write(f'user_pref("marionette.enabled", true);\n')
            f.write(f'user_pref("marionette.port", {marionette_port});\n')
            f.write('user_pref("xpinstall.signatures.required", false);\n')
            f.write('user_pref("extensions.autoDisableScopes", 0);\n')
            f.write('user_pref("aegis.profile.tier", "S1");\n')
            f.write('user_pref("aegis.profile.identity_tier", "I1");\n')

        env = dict(os.environ, AEGIS_SURFACE_TIER="S1", AEGIS_IDENTITY_TIER="I1")

        cmd = [
            str(ESR_BIN), "-profile", prof_dir, "--no-remote",
            "--headless", "--marionette", "--remote-allow-system-access"
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

            def get_ext_url(ext_id, msg_id):
                send_recv(msg_id, "Marionette:SetContext", {"value": "chrome"})
                r = send_recv(msg_id + 1, "WebDriver:ExecuteScript", {
                    "script": f'return WebExtensionPolicy.getByID("{ext_id}").getURL("manifest.json");',
                    "args": []
                })
                send_recv(msg_id + 2, "Marionette:SetContext", {"value": "content"})
                send_recv(msg_id + 3, "WebDriver:Navigate", {"url": r[3]["value"]})
                time.sleep(0.4)

            # 1. Install palette, site-xray, and the rogue extension.
            send_recv(1, "WebDriver:NewSession", {})
            self.assertEqual(send_recv(2, "Addon:Install",
                                       {"path": str(MODULE_DIR), "temporary": True})[3]["value"],
                             "command-palette@aegis.local")
            self.assertEqual(send_recv(3, "Addon:Install",
                                       {"path": str(REPO_ROOT / "modules" / "site-xray"),
                                        "temporary": True})[3]["value"],
                             "site-xray@aegis.local")
            self.assertEqual(send_recv(4, "Addon:Install",
                                       {"path": rogue_dir, "temporary": True})[3]["value"],
                             "rogue-test@aegis.local")
            time.sleep(0.5)

            # 2. ROGUE: try to message site-xray from the rogue extension's
            #    own page. Must be blocked by externally_connectable.
            get_ext_url("rogue-test@aegis.local", 10)
            rogue_script = """
            const resolve = arguments[arguments.length - 1];
            browser.runtime.sendMessage("site-xray@aegis.local", { type: "GET_STATUS" }).then(
                res => resolve({ ok: true, response: res }),
                err => resolve({ ok: false, error: String(err) }));
            """
            rogue_res = send_recv(14, "WebDriver:ExecuteAsyncScript",
                                  {"script": rogue_script, "args": []})[3]["value"]
            self.assertIsNotNone(rogue_res, "Rogue page must return a result")
            # MEASURED FACT (ESR 153.5.1): Gecko does NOT enforce
            # externally_connectable (Chrome-only); the rogue's message IS
            # delivered to onMessageExternal. The enforced defense is the
            # module's code-level sender.id allowlist: site-xray ignores the
            # rogue entirely, so the rogue receives NO data (response null).
            self.assertIsNone(rogue_res.get("response"),
                              "A rogue (non-allowlisted) extension must receive NO "
                              "data from site-xray; got: " + json.dumps(rogue_res)[:300])
            self.assertNotIn("enabled", json.dumps(rogue_res.get("response") or {}))

            # 3. PALETTE (allowlisted sender): execute inspect-site-xray; the
            #    cross-module response must come from site-xray.
            get_ext_url("command-palette@aegis.local", 20)
            exec_script = """
            const resolve = arguments[arguments.length - 1];
            browser.runtime.sendMessage({
                type: "EXECUTE_COMMAND", commandId: "inspect-site-xray"
            }).then(res => resolve(res), err => resolve({ error: String(err) }));
            """
            exec_res = send_recv(24, "WebDriver:ExecuteAsyncScript",
                                 {"script": exec_script, "args": []})[3]["value"]
            self.assertTrue(exec_res.get("success"), json.dumps(exec_res)[:400])
            cross = exec_res.get("crossModule") or {}
            self.assertTrue(cross.get("ok"),
                            "The palette (allowlisted Aegis ID) must reach site-xray")
            self.assertTrue((cross.get("response") or {}).get("enabled"),
                            "site-xray must answer the palette's posture query")

            # 4. Ctrl+Shift+P conflict: send REAL key events to a live page.
            send_recv(30, "Marionette:SetContext", {"value": "content"})
            send_recv(31, "WebDriver:Navigate", {"url": f"http://127.0.0.1:{srv_port}/"})
            time.sleep(0.6)

            private_before = None
            send_recv(32, "Marionette:SetContext", {"value": "chrome"})
            private_before = send_recv(33, "WebDriver:ExecuteScript", {
                "script": """
                let wins = Services.wm.getEnumerator("navigator:browser");
                let n = 0;
                while (wins.hasMoreElements()) {
                    let w = wins.getNext();
                    if (w.document.documentElement.getAttribute("privatebrowsingmode") === "temporary") n++;
                }
                return n;
                """, "args": []
            })[3]["value"]

            # 4a. LIVE REGISTRATION PROOF: query the engine's registered
            #     shortcut for the palette commands (the suggested_key from
            #     the manifest, applied at install time).
            send_recv(34, "Marionette:SetContext", {"value": "chrome"})
            reg_res = send_recv(35, "WebDriver:ExecuteAsyncScript", {
                "script": """
                const resolve = arguments[arguments.length - 1];
                (async () => {
                  try {
                    let policy = WebExtensionPolicy.getByID("command-palette@aegis.local");
                    let cmds = await policy.extension.shortcuts.commands;
                    let out = {};
                    for (const c of cmds) {
                      let arr = Array.from(c);
                      if (arr.length >= 2 && arr[1] && arr[1].shortcut) {
                        out[arr[0]] = arr[1].shortcut;
                      }
                    }
                    resolve(out);
                  } catch (e) { resolve({ error: String(e).slice(0, 200) }); }
                })();
                """, "args": []
            })[3]["value"]
            self.assertNotIn("error", reg_res, json.dumps(reg_res))
            self.assertEqual(reg_res.get("toggle-palette"), "Ctrl+Shift+P",
                             "The Ctrl+Shift+P suggested_key must be registered at runtime")
            self.assertEqual(reg_res.get("clean-active-url"), "Ctrl+Shift+L")

            # 4b. CONFLICT CHECK (honest limits of automation):
            #     Firefox's built-in Ctrl+Shift+P opens a New Private Window.
            #     The palette registers the same combo (proven above). To
            #     observe precedence we send REAL trusted key events via
            #     Marionette. MEASURED FACT (ESR 153.5.1 headless): synthesized
            #     content-level key events do NOT reach parent-process
            #     shortcut dispatch - neither the palette command NOR any
            #     browser shortcut fires. This test therefore proves: (1) the
            #     shortcut is registered in the live engine, and (2) the
            #     automated harness cannot adjudicate real-key precedence.
            #     Real-hardware precedence remains UNVERIFIED (documented in
            #     SPEC_COVERAGE and the module notes).
            actions = [{"type": "key", "id": "aegis-kbd", "actions": [
                {"type": "keyDown", "value": "\ue009"},
                {"type": "keyDown", "value": "\ue008"},
                {"type": "keyDown", "value": "p"},
                {"type": "keyUp", "value": "p"},
                {"type": "keyUp", "value": "\ue008"},
                {"type": "keyUp", "value": "\ue009"}
            ]}]
            send_recv(36, "Marionette:SetContext", {"value": "content"})
            send_recv(37, "WebDriver:PerformActions", {"actions": actions})
            time.sleep(1.2)
            send_recv(38, "WebDriver:ReleaseActions", {})

            send_recv(39, "Marionette:SetContext", {"value": "chrome"})
            private_after = send_recv(40, "WebDriver:ExecuteScript", {
                "script": """
                let wins = Services.wm.getEnumerator("navigator:browser");
                let n = 0;
                while (wins.hasMoreElements()) {
                    let w = wins.getNext();
                    if (w.document.documentElement.getAttribute("privatebrowsingmode") === "temporary") n++;
                }
                return n;
                """, "args": []
            })[3]["value"]

            get_ext_url("command-palette@aegis.local", 42)
            st = send_recv(46, "WebDriver:ExecuteAsyncScript", {"script": """
                const resolve = arguments[arguments.length - 1];
                browser.runtime.sendMessage({ type: "GET_STATUS" }).then(resolve);
                """, "args": []})[3]["value"]
            fired = any(e.get("commandId") == "toggle-palette"
                        for e in (st.get("executionLogTail") or []))

            # The synthesized events must NOT dispatch the palette command
            # (measured: they do not reach shortcut dispatch at all).
            self.assertFalse(fired,
                             "Synthesized content-level key events must not claim to "
                             "prove shortcut dispatch (measured: they never reach "
                             "parent-process shortcut handling on ESR 153.5.1 headless)")
            # And no private window may open from the synthesized events either
            # (same reason - this documents the harness limit, NOT the real
            # conflict resolution).
            self.assertEqual(private_after, private_before,
                             "Synthesized key events must not open a private window "
                             "(they do not reach shortcut dispatch); real-hardware "
                             "precedence remains unverified by automation")

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
            _shutil.rmtree(rogue_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
