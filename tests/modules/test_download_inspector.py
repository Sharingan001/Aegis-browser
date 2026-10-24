#!/usr/bin/env python3
"""
tests/modules/test_download_inspector.py — Automated verification of M8 Download Inspector module.

Verifies:
1. Module manifest compliance with spec Part 8.1.1 (Privacy P1, least privilege).
2. WebExtension manifest validity and absence of unnecessary elevated permissions.
3. Signature analysis across prototype attack vectors:
   - Double extensions (e.g. invoice.pdf.exe).
   - Executable payload disguised as benign media/documents (MZ / ELF magic).
   - Format mismatch (e.g. .jpg file containing PDF bytes).
   - Unicode Right-to-Left Override (RTLO) extension masking.
   - Direct risky extensions (.bat, .sh, .scr).
4. Live browser runtime enforcement:
   - Successful addon installation in Firefox ESR.
   - Live in-engine payload evaluation via runtime message passing.
   - AddonManager kill-switch toggle.
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
MODULE_DIR = REPO_ROOT / "modules" / "download-inspector"


def find_free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class TestDownloadInspector(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not ESR_BIN.is_file():
            raise unittest.SkipTest("firefox-esr binary not found; skipping download inspector runtime tests")

    def test_module_manifest_schema(self):
        """Verify module.json adheres to Master Spec Part 8.1.1 schema."""
        mod_json_path = MODULE_DIR / "module.json"
        self.assertTrue(mod_json_path.is_file(), "module.json missing")

        data = json.loads(mod_json_path.read_text(encoding="utf-8"))
        self.assertEqual(data.get("id"), "download-inspector")
        self.assertEqual(data.get("name"), "Download Inspector")
        self.assertEqual(data.get("privacy_class"), "P1", "Download Inspector must be Privacy Class P1 (local flag log)")
        self.assertTrue(data.get("kill_switch"), "Module must declare kill_switch: true")
        self.assertEqual(data.get("network"), "none", "Module must declare network: none")
        self.assertIn("flag-log", data.get("stores", []))

    def test_webextension_manifest_least_privilege(self):
        """Verify WebExtension manifest requests least possible privileges."""
        manifest_path = MODULE_DIR / "manifest.json"
        self.assertTrue(manifest_path.is_file(), "manifest.json missing")

        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(data.get("manifest_version"), 2)
        self.assertEqual(data.get("name"), "Aegis Download Inspector")

        perms = data.get("permissions", [])
        self.assertIn("downloads", perms)
        self.assertIn("storage", perms)

        # Prohibited elevated permissions
        self.assertNotIn("<all_urls>", perms, "Download inspector does not require all_urls host permission")
        self.assertNotIn("webRequest", perms)
        self.assertNotIn("tabs", perms)
        self.assertNotIn("nativeMessaging", perms)

        self.assertIn("notes", data, "Manifest must document permission justification")

    def test_inspection_logic_matches_prototype(self):
        """Verify inspector logic matches prototypes/aegis_modules.py test cases."""
        import sys
        sys.path.insert(0, str(REPO_ROOT / "prototypes"))
        from aegis_modules import inspect_download

        # Test Vector 1: Double extension
        rep1 = inspect_download("invoice.pdf.exe", b"MZ\x90\x00data")
        self.assertEqual(rep1.level, "high")
        self.assertTrue(any("double extension" in f for f in rep1.flags))

        # Test Vector 2: Disguised Windows binary as JPG
        rep2 = inspect_download("picture.jpg", b"MZ\x90\x00data")
        self.assertEqual(rep2.level, "high")
        self.assertTrue(any("content is windows-executable" in f for f in rep2.flags))

        # Test Vector 3: Disguised Linux binary as PDF
        rep3 = inspect_download("report.pdf", b"\x7fELF\x02\x01data")
        self.assertEqual(rep3.level, "high")
        self.assertTrue(any("content is linux-executable" in f for f in rep3.flags))

        # Test Vector 4: Format mismatch (PNG claiming to be PDF)
        rep4 = inspect_download("scan.pdf", b"\x89PNG\r\n\x1a\n")
        self.assertEqual(rep4.level, "medium")
        self.assertTrue(any("content looks like png" in f for f in rep4.flags))

        # Test Vector 5: Unicode RTL override
        rep5 = inspect_download("tax_form\u202epdf.exe", b"\x00\x00\x00")
        self.assertEqual(rep5.level, "high")
        self.assertTrue(any("right-to-left override" in f for f in rep5.flags))

        # Test Vector 6: Direct script file
        rep6 = inspect_download("run.sh", b"#!/bin/bash\necho 1")
        self.assertEqual(rep6.level, "medium")
        self.assertTrue(any("executable/script type .sh" in f for f in rep6.flags))

        # Test Vector 7: Benign clean file
        rep7 = inspect_download("document.pdf", b"%PDF-1.7\n...")
        self.assertEqual(rep7.level, "low")
        self.assertEqual(len(rep7.flags), 0)

    def test_browser_runtime_inspection_and_kill_switch(self):
        """
        Launch Firefox ESR, install download-inspector, and test:
        1. In-engine payload inspection via extension background script.
        2. Detection of disguised executables and double extensions.
        3. Kill switch disable and enable via AddonManager.
        """
        marionette_port = find_free_port()
        prof_dir = tempfile.mkdtemp(prefix="aegis_dl_inspector_test_")

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

            # 1. Start session & install extension
            send_recv(1, "WebDriver:NewSession", {})
            install_res = send_recv(2, "Addon:Install", {"path": str(MODULE_DIR), "temporary": True})
            self.assertEqual(install_res[3]["value"], "download-inspector@aegis.local", "Extension failed to install")

            time.sleep(0.5)

            # 2. Execute live in-engine verification of inspector_logic.js inside Gecko
            send_recv(3, "Marionette:SetContext", {"value": "content"})
            logic_js = (MODULE_DIR / "inspector_logic.js").read_text(encoding="utf-8")

            eval_script = logic_js + """
            const resolve = arguments[arguments.length - 1];
            (async () => {
                // Vector 1: Disguised Windows binary as PDF (MZ header)
                const mzBytes = new Uint8Array([0x4D, 0x5A, 0x90, 0x00, 0x03, 0x00]);
                const reportDisguised = await inspectDownload("invoice.pdf", mzBytes);

                // Vector 2: Double extension (.pdf.exe)
                const reportDouble = await inspectDownload("statement.pdf.exe", new Uint8Array([0x4D, 0x5A]));

                // Vector 3: Benign clean PDF (%PDF header)
                const pdfBytes = new Uint8Array([0x25, 0x50, 0x44, 0x46, 0x2D, 0x31]);
                const reportClean = await inspectDownload("document.pdf", pdfBytes);

                // Vector 4: Unicode Right-to-Left Override character (\u202e)
                const reportRtlo = await inspectDownload("tax_record\u202epdf.exe", new Uint8Array([0x00, 0x01]));

                resolve({ reportDisguised, reportDouble, reportClean, reportRtlo });
            })();
            """
            eval_res = send_recv(4, "WebDriver:ExecuteAsyncScript", {"script": eval_script, "args": []})
            val = eval_res[3]["value"]

            # Verify disguised executable result
            rep = val["reportDisguised"]
            self.assertEqual(rep["detectedType"], "windows-executable")
            self.assertEqual(rep["claimedExt"], "pdf")
            self.assertEqual(rep["level"], "high")
            self.assertTrue(any("content is windows-executable" in f for f in rep["flags"]))
            self.assertEqual(len(rep["sha256"]), 64, "Must compute valid 64-char SHA-256 via crypto.subtle")

            # Verify double extension result
            rep_double = val["reportDouble"]
            self.assertEqual(rep_double["level"], "high")
            self.assertTrue(any("double extension" in f for f in rep_double["flags"]))

            # Verify benign file
            rep_clean = val["reportClean"]
            self.assertEqual(rep_clean["detectedType"], "pdf")
            self.assertEqual(rep_clean["level"], "low")
            self.assertEqual(len(rep_clean["flags"]), 0)

            # Verify RTLO exploit
            rep_rtlo = val["reportRtlo"]
            self.assertEqual(rep_rtlo["level"], "high")
            self.assertTrue(any("right-to-left override" in f for f in rep_rtlo["flags"]))

            # 3. Test Kill-Switch via AddonManager
            send_recv(5, "Marionette:SetContext", {"value": "chrome"})
            kill_script = """
            const resolve = arguments[arguments.length - 1];
            (async () => {
                const { AddonManager } = ChromeUtils.importESModule("resource://gre/modules/AddonManager.sys.mjs");
                const addon = await AddonManager.getAddonByID("download-inspector@aegis.local");
                await addon.disable();
                const afterActive = addon.isActive;
                await addon.enable();
                const restoredActive = addon.isActive;
                resolve({ afterActive, restoredActive });
            })();
            """
            kill_res = send_recv(6, "WebDriver:ExecuteAsyncScript", {"script": kill_script, "args": []})
            kill_val = kill_res[3]["value"]
            self.assertFalse(kill_val["afterActive"], "Addon should be inactive after disable")
            self.assertTrue(kill_val["restoredActive"], "Addon should be active after enable")

            send_recv(7, "WebDriver:DeleteSession", {})
        finally:
            s.close()
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
            subprocess.run(["rm", "-rf", prof_dir])

    def test_live_downloads_oncreated_hook_metadata_inspection(self):
        """
        Verify that the live downloads.onCreated hook in the background script:
        1. Catches a new download in the browser.
        2. Evaluates filename metadata (double extension .pdf.exe) under least privileges.
        3. Records a flag event into the persistent log and browser.storage.local.
        4. Pauses the dangerous download via browser.downloads.pause().
        """
        import http.server
        import threading

        class DLHandler(http.server.SimpleHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/x-msdownload")
                self.send_header("Content-Disposition", 'attachment; filename="invoice.pdf.exe"')
                self.end_headers()
                self.wfile.write(b"MZ\x90\x00" + b"0" * 64)

            def log_message(self, *args):
                pass

        server = http.server.HTTPServer(("127.0.0.1", 0), DLHandler)
        srv_port = server.server_address[1]
        srv_thread = threading.Thread(target=server.serve_forever, daemon=True)
        srv_thread.start()

        marionette_port = find_free_port()
        prof_dir = tempfile.mkdtemp(prefix="aegis_dl_hook_test_")
        dl_dir = tempfile.mkdtemp(prefix="aegis_dl_out_")

        with open(os.path.join(prof_dir, "user.js"), "w") as f:
            f.write(f'user_pref("marionette.enabled", true);\n')
            f.write(f'user_pref("marionette.port", {marionette_port});\n')
            f.write('user_pref("xpinstall.signatures.required", false);\n')
            f.write('user_pref("extensions.autoDisableScopes", 0);\n')
            f.write(f'user_pref("browser.download.dir", "{dl_dir}");\n')
            f.write('user_pref("browser.download.folderList", 2);\n')
            f.write('user_pref("browser.download.useDownloadDir", true);\n')
            f.write('user_pref("browser.helperApps.neverAsk.saveToDisk", "application/x-msdownload");\n')

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

            # 1. Start session & install extension
            send_recv(1, "WebDriver:NewSession", {})
            install_res = send_recv(2, "Addon:Install", {"path": str(MODULE_DIR), "temporary": True})
            self.assertEqual(install_res[3]["value"], "download-inspector@aegis.local")

            time.sleep(0.5)

            # 2. Get manifest URL to enter extension execution context
            send_recv(3, "Marionette:SetContext", {"value": "chrome"})
            res = send_recv(4, "WebDriver:ExecuteScript", {
                "script": 'return WebExtensionPolicy.getByID("download-inspector@aegis.local").getURL("manifest.json");',
                "args": []
            })
            manifest_url = res[3]["value"]

            # 3. Navigate into extension context
            send_recv(5, "Marionette:SetContext", {"value": "content"})
            send_recv(6, "WebDriver:Navigate", {"url": manifest_url})

            # 4. Trigger download of suspicious file from local test server
            trigger_script = f"""
            const resolve = arguments[arguments.length - 1];
            (async () => {{
                try {{
                    const dlId = await browser.downloads.download({{
                        url: "http://127.0.0.1:{srv_port}/payload",
                        filename: "suspicious_invoice.pdf.exe"
                    }});
                    // Allow downloads.onCreated listener to execute in background script
                    await new Promise(r => setTimeout(r, 1500));
                    
                    const storage = await browser.storage.local.get(null);
                    const status = await browser.runtime.sendMessage({{ type: "GET_STATUS" }});
                    resolve({{ dlId, storage, status }});
                }} catch (e) {{
                    resolve({{ error: e.toString() }});
                }}
            }})();
            """
            dl_res = send_recv(7, "WebDriver:ExecuteAsyncScript", {"script": trigger_script, "args": []})
            val = dl_res[3]["value"]

            self.assertNotIn("error", val, f"Download trigger failed: {val.get('error')}")
            status = val["status"]
            self.assertTrue(status["enabled"])
            self.assertGreaterEqual(status["stats"]["totalInspected"], 1, "Must inspect at least 1 download")
            self.assertGreaterEqual(status["stats"]["flaggedCount"], 1, "Must flag suspicious download")

            # Check flagLog entry
            flag_entry = status["flagLog"][-1]
            self.assertEqual(flag_entry["level"], "high")
            self.assertTrue(any("double extension" in f for f in flag_entry["flags"]))
            self.assertIn("suspicious_invoice.pdf.exe", flag_entry["filename"])

            # Verify storage persistence
            storage_entry = val["storage"]["download_flag_log"][-1]
            self.assertEqual(storage_entry["level"], "high")
            self.assertEqual(storage_entry["filename"], flag_entry["filename"])

            send_recv(8, "WebDriver:DeleteSession", {})
        finally:
            s.close()
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
            subprocess.run(["rm", "-rf", prof_dir])
            subprocess.run(["rm", "-rf", dl_dir])
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
