#!/usr/bin/env python3
"""
tests/axes/probe_container_canvas.py — Empirical test of canvas noise across containers

Tests whether the same origin gets the same canvas noise or different canvas noise
across two containers (userContextId: 1 vs userContextId: 2) in a single Firefox instance.
Evaluates both FPP and RFP.
"""

import http.server
import json
import os
import pathlib
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
ESR_BIN = REPO_ROOT / "firefox-esr" / "firefox"
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures"
OUTPUT_DIR = FIXTURES_DIR / "output"

sys.path.insert(0, str(REPO_ROOT / "tests" / "tools"))
from local_test_server import FixtureHandler


def find_free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


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


def test_containers_for_config(config_name, user_prefs):
    server_port = find_free_port()
    marionette_port = find_free_port()

    # Clear prior test reports
    for cid in ["c1_tab1", "c2_tab1", "c1_tab2"]:
        rf = OUTPUT_DIR / f"fp_report_{cid}.json"
        if rf.is_file():
            rf.unlink()

    server = http.server.HTTPServer(("127.0.0.1", server_port), FixtureHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    prof_dir = tempfile.mkdtemp(prefix=f"probe_c_{config_name}_")
    with open(os.path.join(prof_dir, "user.js"), "w") as f:
        f.write('user_pref("marionette.enabled", true);\n')
        f.write(f'user_pref("marionette.port", {marionette_port});\n')
        f.write('user_pref("privacy.userContext.enabled", true);\n')
        for k, v in user_prefs.items():
            if isinstance(v, bool):
                val = "true" if v else "false"
            elif isinstance(v, int):
                val = str(v)
            elif isinstance(v, str):
                val = f'"{v}"'
            f.write(f'user_pref("{k}", {val});\n')

    cmd = [
        str(ESR_BIN),
        "-profile", prof_dir,
        "--no-remote",
        "--headless",
        "--marionette",
        "--remote-allow-system-access"
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2.5)

    s = socket.socket()
    try:
        s.connect(("127.0.0.1", marionette_port))
        s.recv(1024)
        send_recv(s, 1, "WebDriver:NewSession", {})
        send_recv(s, 2, "Marionette:SetContext", {"value": "chrome"})

        base_url = f"http://127.0.0.1:{server_port}/axes/test_canvas_container.html"

        # Sequential loading of tabs with selection so each tab active executes its script
        script_step = f"""
        let win = Services.wm.getMostRecentWindow("navigator:browser");
        let gb = win.gBrowser;
        let secMan = Services.scriptSecurityManager;
        let sysPrin = secMan.getSystemPrincipal();

        // Open and select Tab 1 (container 1)
        let t1 = gb.addTab("{base_url}?cid=c1_tab1", {{ userContextId: 1, triggeringPrincipal: sysPrin }});
        gb.selectedTab = t1;
        """
        send_recv(s, 3, "WebDriver:ExecuteScript", {"script": script_step, "args": []})
        time.sleep(2.0)

        script_step2 = f"""
        let win = Services.wm.getMostRecentWindow("navigator:browser");
        let gb = win.gBrowser;
        let secMan = Services.scriptSecurityManager;
        let sysPrin = secMan.getSystemPrincipal();

        // Open and select Tab 2 (container 2)
        let t2 = gb.addTab("{base_url}?cid=c2_tab1", {{ userContextId: 2, triggeringPrincipal: sysPrin }});
        gb.selectedTab = t2;
        """
        send_recv(s, 4, "WebDriver:ExecuteScript", {"script": script_step2, "args": []})
        time.sleep(2.0)

        script_step3 = f"""
        let win = Services.wm.getMostRecentWindow("navigator:browser");
        let gb = win.gBrowser;
        let secMan = Services.scriptSecurityManager;
        let sysPrin = secMan.getSystemPrincipal();

        // Open and select Tab 3 (container 1 again)
        let t3 = gb.addTab("{base_url}?cid=c1_tab2", {{ userContextId: 1, triggeringPrincipal: sysPrin }});
        gb.selectedTab = t3;
        """
        send_recv(s, 5, "WebDriver:ExecuteScript", {"script": script_step3, "args": []})
        time.sleep(2.0)

        # Collect results
        results = {}
        for cid in ["c1_tab1", "c2_tab1", "c1_tab2"]:
            rf = OUTPUT_DIR / f"fp_report_{cid}.json"
            if rf.is_file():
                try:
                    data = json.loads(rf.read_text())
                    results[cid] = {
                        "dataUrlHash": data["canvas"]["dataUrlHash"],
                        "imgDataHash": data["canvas"]["imgDataHash"],
                    }
                except Exception as e:
                    results[cid] = f"read_error: {e}"
            else:
                results[cid] = "missing_report_file"

        return results
    finally:
        s.close()
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
        server.shutdown()
        shutil.rmtree(prof_dir, ignore_errors=True)


def main():
    print("=== Testing Container Canvas Noise in FPP ===")
    res_fpp = test_containers_for_config("FPP", {
        "privacy.fingerprintingProtection": True,
        "privacy.fingerprintingProtection.remoteOverrides.enabled": False,
    })
    print("FPP Results:\n", json.dumps(res_fpp, indent=2))

    # Evaluate FPP container isolation
    if isinstance(res_fpp.get("c1_tab1"), dict) and isinstance(res_fpp.get("c2_tab1"), dict):
        c1_1 = res_fpp["c1_tab1"]["dataUrlHash"]
        c2_1 = res_fpp["c2_tab1"]["dataUrlHash"]
        c1_2 = res_fpp.get("c1_tab2", {}).get("dataUrlHash")
        print(f"  Container 1 (Tab 1) == Container 1 (Tab 2): {c1_1 == c1_2}")
        print(f"  Container 1 (Tab 1) == Container 2 (Tab 1): {c1_1 == c2_1}")

    print("\n=== Testing Container Canvas Noise in RFP ===")
    res_rfp = test_containers_for_config("RFP", {
        "privacy.resistFingerprinting": True,
    })
    print("RFP Results:\n", json.dumps(res_rfp, indent=2))
    if isinstance(res_rfp.get("c1_tab1"), dict) and isinstance(res_rfp.get("c2_tab1"), dict):
        r_c1_1 = res_rfp["c1_tab1"]["dataUrlHash"]
        r_c2_1 = res_rfp["c2_tab1"]["dataUrlHash"]
        r_c1_2 = res_rfp.get("c1_tab2", {}).get("dataUrlHash")
        print(f"  RFP C1_1 == C1_2: {r_c1_1 == r_c1_2}")
        print(f"  RFP C1_1 == C2_1: {r_c1_1 == r_c2_1}")


if __name__ == "__main__":
    main()
