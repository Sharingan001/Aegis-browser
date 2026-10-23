#!/usr/bin/env python3
"""
tests/axes/probe_rfp_vs_fpp.py — Empirical comparison probe for Phase 2b

Tests Firefox ESR 153.5.1 across 7 dimensions:
1. Canvas 2D extraction & randomization
2. Web Audio readback & sample rate
3. Timer precision (performance.now & Date.now)
4. Window & screen dimensions (with and without letterboxing)
5. Timezone (Intl and Date offset)
6. Language and HTTP Accept-Language headers
7. Hardware concurrency and WebGL unmasked vendor/renderer

Configurations tested:
- Baseline: default ESR 153.5.1 (RFP=false, FPP=false)
- RFP: privacy.resistFingerprinting=true (letterboxing=false)
- RFP_Letterboxing: privacy.resistFingerprinting=true (letterboxing=true)
- FPP: privacy.fingerprintingProtection=true (remoteOverrides=false)
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
FP_REPORT_FILE = FIXTURES_DIR / "output" / "fp_report.json"
LAST_HEADERS_FILE = FIXTURES_DIR / "output" / "last_headers.json"

sys.path.insert(0, str(REPO_ROOT / "tests" / "tools"))
from local_test_server import FixtureHandler


def find_free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class EmpiricalProber:
    def __init__(self):
        self.port = find_free_port()
        self.server = None
        self.server_thread = None

    def start_server(self):
        self.server = http.server.HTTPServer(("127.0.0.1", self.port), FixtureHandler)
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()

    def stop_server(self):
        if self.server:
            self.server.shutdown()

    def run_configuration(self, name, prefs, clear_output=True):
        if clear_output:
            for f in [FP_REPORT_FILE, LAST_HEADERS_FILE]:
                if f.is_file():
                    f.unlink()

        prof_dir = tempfile.mkdtemp(prefix=f"aegis_fp_{name}_")
        user_js = os.path.join(prof_dir, "user.js")
        with open(user_js, "w") as f:
            # Baseline preferences to make headless run predictable
            f.write('user_pref("browser.shell.checkDefaultBrowser", false);\n')
            f.write('user_pref("browser.startup.homepage_override.mstone", "ignore");\n')
            f.write('user_pref("datareporting.policy.dataSubmissionEnabled", false);\n')
            f.write('user_pref("toolkit.telemetry.enabled", false);\n')
            f.write('user_pref("app.normandy.enabled", false);\n')
            for pref_name, val in prefs.items():
                if isinstance(val, bool):
                    f.write(f'user_pref("{pref_name}", {"true" if val else "false"});\n')
                elif isinstance(val, int):
                    f.write(f'user_pref("{pref_name}", {val});\n')
                elif isinstance(val, str):
                    f.write(f'user_pref("{pref_name}", "{val}");\n')

        env = dict(os.environ)
        # Unset surface tier to prevent custom aegis.cfg overrides from interfering with pure test prefs
        env["AEGIS_SURFACE_TIER"] = "S1"

        url = f"http://127.0.0.1:{self.port}/axes/test_fp_surface.html"
        cmd = [
            str(ESR_BIN),
            "-profile", prof_dir,
            "--no-remote",
            "--headless",
            url
        ]

        proc = subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        report = None
        headers = None

        t0 = time.time()
        while time.time() - t0 < 8.0:
            if FP_REPORT_FILE.is_file() and LAST_HEADERS_FILE.is_file():
                try:
                    report = json.loads(FP_REPORT_FILE.read_text())
                    headers = json.loads(LAST_HEADERS_FILE.read_text())
                    break
                except Exception:
                    pass
            time.sleep(0.15)

        proc.terminate()
        try:
            proc.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            proc.kill()

        shutil.rmtree(prof_dir, ignore_errors=True)
        return {
            "name": name,
            "prefs": prefs,
            "report": report,
            "headers": headers
        }


def main():
    prober = EmpiricalProber()
    prober.start_server()
    print(f"[*] Test server listening on 127.0.0.1:{prober.port}")

    configs = [
        (
            "Baseline",
            {
                "privacy.resistFingerprinting": False,
                "privacy.fingerprintingProtection": False,
            }
        ),
        (
            "RFP_Default",
            {
                "privacy.resistFingerprinting": True,
                "privacy.resistFingerprinting.letterboxing": False,
            }
        ),
        (
            "RFP_Letterboxed",
            {
                "privacy.resistFingerprinting": True,
                "privacy.resistFingerprinting.letterboxing": True,
            }
        ),
        (
            "FPP_Default",
            {
                "privacy.fingerprintingProtection": True,
                "privacy.fingerprintingProtection.remoteOverrides.enabled": False,
            }
        ),
    ]

    all_results = {}
    for name, prefs in configs:
        print(f"[*] Running probe: {name} (Run 1)...")
        r1 = prober.run_configuration(name, prefs)
        print(f"[*] Running probe: {name} (Run 2 for canvas stability check)...")
        r2 = prober.run_configuration(name, prefs)
        all_results[name] = {
            "run1": r1,
            "run2": r2,
            "canvas_run1_hash": r1["report"]["canvas"]["dataUrlHash"] if r1["report"] else None,
            "canvas_run2_hash": r2["report"]["canvas"]["dataUrlHash"] if r2["report"] else None,
            "canvas_cross_run_stable": (
                r1["report"]["canvas"]["dataUrlHash"] == r2["report"]["canvas"]["dataUrlHash"]
                if (r1["report"] and r2["report"]) else None
            ),
            "audio_run1_hash": r1["report"]["audio"]["pcmHash"] if (r1["report"] and r1["report"]["audio"]["supported"]) else None,
            "audio_run2_hash": r2["report"]["audio"]["pcmHash"] if (r2["report"] and r2["report"]["audio"]["supported"]) else None,
            "audio_cross_run_stable": (
                r1["report"]["audio"]["pcmHash"] == r2["report"]["audio"]["pcmHash"]
                if (r1["report"] and r2["report"] and r1["report"]["audio"]["supported"]) else None
            ),
        }

    prober.stop_server()

    out_file = FIXTURES_DIR / "output" / "probe_results_summary.json"
    out_file.write_text(json.dumps(all_results, indent=2))
    print(f"[+] Empirical probing completed. Results written to {out_file}")


if __name__ == "__main__":
    main()
