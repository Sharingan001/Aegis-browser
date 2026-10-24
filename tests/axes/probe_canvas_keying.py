#!/usr/bin/env python3
"""
Empirical probe: FPP canvas-noise keying on NON-LOOPBACK origins (Phase 2d follow-up).

Why this probe exists:
  Prior Phase 2b/2c canvas evidence was collected on loopback origins
  (http://127.0.0.1:<port>/). Two problems with that evidence:
    1. canvas.toDataURL() PNG strings in ESR 153 headless embed a session-unique
       debug chunk, so PNG-string hashes differ across launches for reasons
       unrelated to fingerprinting protection.
    2. Loopback origins are a degenerate case for site-keyed protections
       (measured here directly against non-loopback hostnames).

Method:
  - Hostnames a.test and b.test are mapped to 127.0.0.1 via the
    network.dns.localDomains preference (no external DNS, no external network).
  - The fixture page draws a deterministic canvas and hashes RAW PIXELS:
    SHA-256 of ctx.getImageData(0,0,w,h).data via crypto.subtle (never PNG
    strings). Two successive readbacks are hashed to observe per-readback noise.
  - Every page self-reports its hashes to the local server with a tag.

Comparisons (all on the same machine, offline, ESR 153.5.1):
  A. One I3 (FPP) launch: a.test vs b.test (two origins); container 1 vs
     container 2 on a.test; 127.0.0.1 and localhost in the same launch.
  B. I3 same persistent profile launched twice (cross-launch stability).
  C. I3 fresh profile vs run A (fresh-profile cross-launch).
  D. I1 (FPP off) reference: a.test and 127.0.0.1.
  E. I3 + overrides="-CanvasRandomization": a.test and 127.0.0.1.

Output: JSON summary printed to stdout; verdicts derived by the caller.
"""

import hashlib
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

# Shared result store: tag_group -> {tag -> report dict}
results = {}

FIXTURE_HTML = b"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head><body>
<canvas id="canvas_probe" width="120" height="60"></canvas>
<script>
(function () {
  // Pure-JS SHA-256 (public-domain style implementation). crypto.subtle is
  // NOT used because http://a.test is not a secure context (loopback is).
  function sha256Bytes(bytes) {
    const K = [
      0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,
      0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,
      0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,
      0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
      0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,
      0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,
      0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,
      0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
      0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,
      0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,
      0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2];
    const H = [0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,
               0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19];
    const l = bytes.length;
    const withOne = l + 1;
    const blocks = Math.ceil((withOne + 8) / 64);
    const padded = new Uint8Array(blocks * 64);
    padded.set(bytes);
    padded[l] = 0x80;
    const bitLenHi = Math.floor(l / 0x20000000);
    const bitLenLo = (l << 3) >>> 0;
    const dv = padded.length - 8;
    padded[dv] = (bitLenHi >>> 24) & 0xff; padded[dv+1] = (bitLenHi >>> 16) & 0xff;
    padded[dv+2] = (bitLenHi >>> 8) & 0xff;  padded[dv+3] = bitLenHi & 0xff;
    padded[dv+4] = (bitLenLo >>> 24) & 0xff; padded[dv+5] = (bitLenLo >>> 16) & 0xff;
    padded[dv+6] = (bitLenLo >>> 8) & 0xff;  padded[dv+7] = bitLenLo & 0xff;

    const w = new Uint32Array(64);
    let a, b, c, d, e, f, g, h;
    for (let blk = 0; blk < blocks; blk++) {
      const off = blk * 64;
      for (let i = 0; i < 16; i++) {
        w[i] = (padded[off + i*4] << 24) | (padded[off + i*4 + 1] << 16) |
               (padded[off + i*4 + 2] << 8) | padded[off + i*4 + 3];
      }
      for (let i = 16; i < 64; i++) {
        const s0 = ((w[i-15] >>> 7) | (w[i-15] << 25)) ^
                   ((w[i-15] >>> 18) | (w[i-15] << 14)) ^ (w[i-15] >>> 3);
        const s1 = ((w[i-2] >>> 17) | (w[i-2] << 15)) ^
                   ((w[i-2] >>> 19) | (w[i-2] << 13)) ^ (w[i-2] >>> 10);
        w[i] = (w[i-16] + s0 + w[i-7] + s1) >>> 0;
      }
      a = H[0]; b = H[1]; c = H[2]; d = H[3];
      e = H[4]; f = H[5]; g = H[6]; h = H[7];
      for (let i = 0; i < 64; i++) {
        const S1 = ((e >>> 6) | (e << 26)) ^ ((e >>> 11) | (e << 21)) ^
                   ((e >>> 25) | (e << 7));
        const ch = (e & f) ^ (~e & g);
        const t1 = (h + S1 + ch + K[i] + w[i]) >>> 0;
        const S0 = ((a >>> 2) | (a << 30)) ^ ((a >>> 13) | (a << 19)) ^
                   ((a >>> 22) | (a << 10));
        const mj = (a & b) ^ (a & c) ^ (b & c);
        const t2 = (S0 + mj) >>> 0;
        h = g; g = f; f = e; e = (d + t1) >>> 0;
        d = c; c = b; b = a; a = (t1 + t2) >>> 0;
      }
      H[0] = (H[0] + a) >>> 0; H[1] = (H[1] + b) >>> 0;
      H[2] = (H[2] + c) >>> 0; H[3] = (H[3] + d) >>> 0;
      H[4] = (H[4] + e) >>> 0; H[5] = (H[5] + f) >>> 0;
      H[6] = (H[6] + g) >>> 0; H[7] = (H[7] + h) >>> 0;
    }
    let out = "";
    for (let i = 0; i < 8; i++) {
      out += H[i].toString(16).padStart(8, "0");
    }
    return out;
  }

  // Self-test vector: sha256("abc") must equal the known digest.
  const enc = new TextEncoder();
  const selfTestOk = sha256Bytes(enc.encode("abc")) ===
    "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad";

  function run() {
    const c = document.getElementById("canvas_probe");
    const ctx = c.getContext("2d");
    ctx.fillStyle = "#ff6600";
    ctx.fillRect(10, 10, 80, 40);
    ctx.fillStyle = "#006699";
    ctx.font = "16px sans-serif";
    ctx.fillText("Aegis Canvas Probe", 15, 35);
    ctx.strokeStyle = "rgba(120, 20, 200, 0.7)";
    ctx.lineWidth = 2;
    ctx.strokeRect(5, 5, 110, 50);

    // Raw pixel bytes of the full canvas: NOT a PNG string.
    const d1 = ctx.getImageData(0, 0, c.width, c.height).data;
    const h1 = sha256Bytes(new Uint8Array(d1));
    const h2 = sha256Bytes(new Uint8Array(
      ctx.getImageData(0, 0, c.width, c.height).data));
    const pngHash = sha256Bytes(enc.encode(c.toDataURL()));

    const params = new URLSearchParams(location.search);
    const tag = params.get("tag") || "untagged";
    fetch("/api/report_canvas", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tag: tag,
        origin: location.origin,
        readback1: h1,
        readback2: h2,
        dataUrlHash: pngHash,
        sha256SelfTestOk: selfTestOk
      })
    });
    window.__probeDone = true;
  }
  run();
})();
</script>
</body></html>
"""


class ProbeHandler(http.server.BaseHTTPRequestHandler):
    reports = {}

    def do_GET(self):
        if self.path.startswith("/canvas"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(FIXTURE_HTML)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path.startswith("/api/report_canvas"):
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length) or b"{}")
            ProbeHandler.reports[body.get("tag", "untagged")] = body
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):
        pass


def find_free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def send_recv(s, msg_id, cmd_name, params):
    payload = json.dumps([0, msg_id, cmd_name, params])
    s.sendall(f"{len(payload)}:{payload}".encode())
    hdr = b""
    while b":" not in hdr:
        hdr += s.recv(1)
    length = int(hdr[:-1].decode())
    body = b""
    while len(body) < length:
        body += s.recv(length - len(body))
    return json.loads(body.decode())


def launch(profile_dir, prefs, surface_tier, identity_tier):
    """Launch ESR headless with Marionette and the given user.js prefs."""
    port = find_free_port()
    with open(os.path.join(profile_dir, "user.js"), "w") as f:
        f.write('user_pref("marionette.enabled", true);\n')
        f.write(f'user_pref("marionette.port", {port});\n')
        f.write('user_pref("network.dns.localDomains", "a.test,b.test");\n')
        # Probe-only: the fixture server is plain HTTP. HTTPS-First upgrades
        # non-loopback http:// hosts (loopback is exempt), which would break
        # a.test/b.test loading. This does not affect FPP canvas keying.
        f.write('user_pref("dom.security.https_first", false);\n')
        f.write('user_pref("dom.security.https_only_mode", false);\n')
        for k, v in prefs.items():
            f.write(f"user_pref(\"{k}\", {json.dumps(v)});\n")
        if surface_tier:
            f.write(f'user_pref("aegis.profile.tier", "{surface_tier}");\n')
        if identity_tier:
            f.write(f'user_pref("aegis.profile.identity_tier", "{identity_tier}");\n')

    env = dict(os.environ)
    env["AEGIS_SURFACE_TIER"] = surface_tier or "S1"
    env["AEGIS_IDENTITY_TIER"] = identity_tier or "I1"

    cmd = [
        str(ESR_BIN), "-profile", profile_dir, "--no-remote",
        "--headless", "--marionette", "--remote-allow-system-access"
    ]
    proc = subprocess.Popen(cmd, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2.5)
    s = socket.socket()
    s.connect(("127.0.0.1", port))
    header = b""
    while b":" not in header:
        header += s.recv(1)
    init_len = int(header[:-1].decode())
    s.recv(init_len)
    send_recv(s, 1, "WebDriver:NewSession", {})
    return proc, s


def open_page(s, msg_id, url, user_context_id=None):
    """Navigate the current tab (content context) or open a container tab."""
    send_recv(s, msg_id, "Marionette:SetContext", {"value": "chrome"})
    if user_context_id is None:
        script = f"""
        let win = Services.wm.getMostRecentWindow("navigator:browser");
        win.gBrowser.loadURI(Services.io.newURI("{url}"),
            {{ triggeringPrincipal: Services.scriptSecurityManager.getSystemPrincipal() }});
        """
    else:
        script = f"""
        let win = Services.wm.getMostRecentWindow("navigator:browser");
        let gb = win.gBrowser;
        let sysPrin = Services.scriptSecurityManager.getSystemPrincipal();
        let t = gb.addTab("{url}", {{ userContextId: {user_context_id}, triggeringPrincipal: sysPrin }});
        gb.selectedTab = t;
        """
    send_recv(s, msg_id + 1, "WebDriver:ExecuteScript", {"script": script, "args": []})
    time.sleep(1.8)


def run_pb(tag_group, prefs, surface, identity, pages, base):
    """Open the fixture in a PRIVATE browser window for each (tag, host)."""
    prof = tempfile.mkdtemp(prefix=f"aegis_canvas_{tag_group}_")
    try:
        proc, s = launch(prof, prefs, surface, identity)
        try:
            mid = 10
            for tag, host in pages:
                page_url = base.replace("HOSTNAME", host) + f"?tag={tag}"
                send_recv(s, mid, "Marionette:SetContext", {"value": "chrome"})
                script = """
                let win = Services.ww.openWindow(null,
                    "chrome://browser/content/browser.xhtml", "_blank",
                    "chrome,dialog=no,all,private", null);
                """
                send_recv(s, mid + 1, "WebDriver:ExecuteScript",
                          {"script": script, "args": []})
                time.sleep(1.5)
                send_recv(s, mid + 2, "Marionette:SetContext", {"value": "chrome"})
                script2 = f"""
                let wins = Services.wm.getEnumerator("navigator:browser");
                let pw = null;
                while (wins.hasMoreElements()) {{
                    let w = wins.getNext();
                    if (w.document.documentElement.getAttribute("privatebrowsingmode") === "temporary") {{ pw = w; }}
                }}
                if (pw) {{
                    pw.gBrowser.loadURI(Services.io.newURI("{page_url}"),
                        {{ triggeringPrincipal: Services.scriptSecurityManager.getSystemPrincipal() }});
                }}
                """
                send_recv(s, mid + 3, "WebDriver:ExecuteScript",
                          {"script": script2, "args": []})
                time.sleep(2.0)
                mid += 10
            got = collect([p[0] for p in pages])
            results[tag_group] = got
        finally:
            s.close()
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
    finally:
        shutil.rmtree(prof, ignore_errors=True)


def collect(tags, timeout=12):
    """Wait until every tag has reported or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if all(t in ProbeHandler.reports for t in tags):
            break
        time.sleep(0.5)
    return {t: ProbeHandler.reports.get(t) for t in tags}


def short(h):
    return (h or "None")[:16]


def main():
    if not ESR_BIN.is_file():
        sys.exit("firefox-esr binary not found")

    server_port = find_free_port()
    server = http.server.HTTPServer(("127.0.0.1", server_port), ProbeHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://HOSTNAME:{server_port}/canvas"

    def url_for(host, tag):
        return base.replace("HOSTNAME", host) + f"?tag={tag}"

    # (results is a module-level shared store)

    FPP_PREFS = {
        "privacy.fingerprintingProtection": True,
        "privacy.fingerprintingProtection.remoteOverrides.enabled": False,
        "privacy.fingerprintingProtection.overrides": "",
    }
    FPP_OFF_PREFS = {
        "privacy.fingerprintingProtection": False,
    }
    FPP_OVERRIDE_PREFS = {
        "privacy.fingerprintingProtection": True,
        "privacy.fingerprintingProtection.remoteOverrides.enabled": False,
        "privacy.fingerprintingProtection.overrides": "-CanvasRandomization",
    }

    def run(tag_group, prefs, surface, identity, pages, keep_profile=False):
        """pages: list of (tag, host, user_context_id_or_None)"""
        prof = tempfile.mkdtemp(prefix=f"aegis_canvas_{tag_group}_")
        try:
            proc, s = launch(prof, prefs, surface, identity)
            try:
                mid = 10
                for tag, host, ucid in pages:
                    open_page(s, mid, url_for(host, tag), ucid)
                    mid += 10
                got = collect([p[0] for p in pages])
                for tag, entry in got.items():
                    if entry and not entry.get("sha256SelfTestOk"):
                        raise RuntimeError(
                            f"in-page SHA-256 self-test failed for {tag}")
                results[tag_group] = got
            finally:
                s.close()
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
        finally:
            if not keep_profile:
                shutil.rmtree(prof, ignore_errors=True)
        return prof if keep_profile else None

    # A. One I3 launch: origins, containers, loopback comparison (same launch)
    run("A_i3_mixed", FPP_PREFS, "S1", "I3", [
        ("a_run_A", "a.test", None),
        ("b_run_A", "b.test", None),
        ("a_c1", "a.test", 1),
        ("a_c2", "a.test", 2),
        ("loop_ip", "127.0.0.1", None),
        ("loop_name", "localhost", None),
    ])

    # B. Same persistent profile, two launches (cross-launch stability)
    prof_b = run("B_launch1", FPP_PREFS, "S1", "I3",
                 [("a_launch1", "a.test", None)], keep_profile=True)
    if prof_b:
        try:
            proc, s = launch(prof_b, FPP_PREFS, "S1", "I3")
            try:
                open_page(s, 10, url_for("a.test", "a_launch2"))
                results["B_launch2"] = collect(["a_launch2"])
            finally:
                s.close()
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
        finally:
            shutil.rmtree(prof_b, ignore_errors=True)

    # C. Fresh profile I3 (fresh-profile cross-launch vs A)
    run("C_i3_fresh", FPP_PREFS, "S1", "I3", [("a_run_C", "a.test", None)])

    # D. I1 native (FPP off) reference
    run("D_i1_native", FPP_OFF_PREFS, "S1", "I1", [
        ("a_native", "a.test", None),
        ("loop_native", "127.0.0.1", None),
    ])

    # E. I3 with -CanvasRandomization override
    run("E_i3_override", FPP_OVERRIDE_PREFS, "S1", "I3", [
        ("a_override", "a.test", None),
        ("loop_override", "127.0.0.1", None),
    ])

    # F. Positive control: I2 (RFP) - RFP canvas randomization must be visible
    RFP_PREFS = {
        "privacy.resistFingerprinting": True,
        "privacy.fingerprintingProtection": False,
    }
    run("F_i2_rfp", RFP_PREFS, "S1", "I2", [
        ("a_rfp", "a.test", None),
        ("b_rfp", "b.test", None),
    ])

    # G. I3 with explicit +CanvasRandomization (is the target in the default set?)
    FPP_ADD_CANVAS_PREFS = {
        "privacy.fingerprintingProtection": True,
        "privacy.fingerprintingProtection.remoteOverrides.enabled": False,
        "privacy.fingerprintingProtection.overrides": "+CanvasRandomization",
    }
    run("G_i3_addcanvas", FPP_ADD_CANVAS_PREFS, "S1", "I3", [
        ("a_addcanvas", "a.test", None),
        ("b_addcanvas", "b.test", None),
        ("loop_addcanvas", "127.0.0.1", None),
    ])

    # H. I3 with +AllTargets (canvas noise IS in AllTargets; containers too)
    FPP_ALLTARGETS_PREFS = {
        "privacy.fingerprintingProtection": True,
        "privacy.fingerprintingProtection.remoteOverrides.enabled": False,
        "privacy.fingerprintingProtection.overrides": "+AllTargets",
    }
    run("H_i3_alltargets", FPP_ALLTARGETS_PREFS, "S1", "I3", [
        ("a_alltargets", "a.test", None),
        ("b_alltargets", "b.test", None),
        ("a_all_c1", "a.test", 1),
        ("a_all_c2", "a.test", 2),
    ])

    # K. +AllTargets: same persistent profile, two launches (key stability)
    prof_k = run("K_all_launch1", FPP_ALLTARGETS_PREFS, "S1", "I3",
                 [("a_all_launch1", "a.test", None)], keep_profile=True)
    if prof_k:
        try:
            proc, s = launch(prof_k, FPP_ALLTARGETS_PREFS, "S1", "I3")
            try:
                open_page(s, 10, url_for("a.test", "a_all_launch2"))
                results["K_all_launch2"] = collect(["a_all_launch2"])
            finally:
                s.close()
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
        finally:
            shutil.rmtree(prof_k, ignore_errors=True)

    # L. +AllTargets with -CanvasRandomization removed (override proof)
    FPP_ALL_MINUS_CANVAS_PREFS = {
        "privacy.fingerprintingProtection": True,
        "privacy.fingerprintingProtection.remoteOverrides.enabled": False,
        "privacy.fingerprintingProtection.overrides": "+AllTargets,-CanvasRandomization",
    }
    run("L_all_minus_canvas", FPP_ALL_MINUS_CANVAS_PREFS, "S1", "I3", [
        ("a_all_minus_canvas", "a.test", None),
    ])

    # M. +EfficientCanvasRandomization alone (target 76: stable site-keyed noise?)
    FPP_EFF_CANVAS_PREFS = {
        "privacy.fingerprintingProtection": True,
        "privacy.fingerprintingProtection.remoteOverrides.enabled": False,
        "privacy.fingerprintingProtection.overrides": "+EfficientCanvasRandomization",
    }
    run("M_eff_canvas", FPP_EFF_CANVAS_PREFS, "S1", "I3", [
        ("a_eff", "a.test", None),
        ("b_eff", "b.test", None),
        ("a_eff_c1", "a.test", 1),
        ("a_eff_c2", "a.test", 2),
    ])

    # I. I3 default in a PRIVATE window (FPP originally shipped PB-gated)
    FPP_PB_PREFS = {
        "privacy.fingerprintingProtection": True,
        "privacy.fingerprintingProtection.remoteOverrides.enabled": False,
        "privacy.fingerprintingProtection.overrides": "",
    }
    run_pb("I_i3_private", FPP_PB_PREFS, "S1", "I3",
           [("a_private", "a.test"), ("b_private", "b.test")], base)

    server.shutdown()
    server.server_close()

    # ---- Analysis ----
    def r1(group, tag):
        entry = results.get(group, {}).get(tag)
        return entry["readback1"] if entry else None

    def stable_within_page(group, tag):
        e = results.get(group, {}).get(tag)
        return bool(e) and e["readback1"] == e["readback2"]

    a = r1("A_i3_mixed", "a_run_A")
    b = r1("A_i3_mixed", "b_run_A")
    c1 = r1("A_i3_mixed", "a_c1")
    c2 = r1("A_i3_mixed", "a_c2")
    loop_ip = r1("A_i3_mixed", "loop_ip")
    loop_name = r1("A_i3_mixed", "loop_name")
    a_l1 = r1("B_launch1", "a_launch1")
    a_l2 = r1("B_launch2", "a_launch2")
    a_c = r1("C_i3_fresh", "a_run_C")
    a_nat = r1("D_i1_native", "a_native")
    loop_nat = r1("D_i1_native", "loop_native")
    a_ovr = r1("E_i3_override", "a_override")
    loop_ovr = r1("E_i3_override", "loop_override")
    a_rfp = r1("F_i2_rfp", "a_rfp")
    b_rfp = r1("F_i2_rfp", "b_rfp")
    a_rfp_r2 = None
    if results.get("F_i2_rfp", {}).get("a_rfp"):
        a_rfp_r2 = results["F_i2_rfp"]["a_rfp"]["readback2"]
    a_add = r1("G_i3_addcanvas", "a_addcanvas")
    b_add = r1("G_i3_addcanvas", "b_addcanvas")
    loop_add = r1("G_i3_addcanvas", "loop_addcanvas")

    def eq(x, y):
        return "SAME" if x and y and x == y else "DIFF"

    summary = {
        "environment": "Firefox ESR 153.5.1esr, Linux x86_64, --headless, offline",
        "hashes_16char_prefix": {
            "I3_a.test": short(a), "I3_b.test": short(b),
            "I3_a.test_container1": short(c1), "I3_a.test_container2": short(c2),
            "I3_127.0.0.1": short(loop_ip), "I3_localhost": short(loop_name),
            "I3_a.test_launch1": short(a_l1), "I3_a.test_launch2_same_profile": short(a_l2),
            "I3_a.test_fresh_profile": short(a_c),
            "I1_a.test_native": short(a_nat), "I1_127.0.0.1_native": short(loop_nat),
            "I3_override_a.test": short(a_ovr), "I3_override_127.0.0.1": short(loop_ovr),
            "I2_rfp_a.test_readback1": short(a_rfp),
            "I2_rfp_a.test_readback2": short(a_rfp_r2),
            "I2_rfp_b.test": short(b_rfp),
            "I3_plusCanvas_a.test": short(a_add), "I3_plusCanvas_b.test": short(b_add),
            "I3_plusCanvas_127.0.0.1": short(loop_add),
            "I3_allTargets_a.test": short(r1("H_i3_alltargets", "a_alltargets")),
            "I3_allTargets_b.test": short(r1("H_i3_alltargets", "b_alltargets")),
            "I3_privateWindow_a.test": short(r1("I_i3_private", "a_private")),
            "I3_privateWindow_b.test": short(r1("I_i3_private", "b_private")),
        },
        "within_page_readback_stability": {
            "a.test": stable_within_page("A_i3_mixed", "a_run_A"),
            "127.0.0.1": stable_within_page("A_i3_mixed", "loop_ip"),
        },
        "comparisons": {
            "two_origins_a_vs_b (I3)": eq(a, b),
            "two_containers_same_origin (I3)": eq(c1, c2),
            "container_vs_top_a.test (I3)": eq(c1, a),
            "two_launches_same_profile (I3)": eq(a_l1, a_l2),
            "two_launches_fresh_profiles (I3, A vs C)": eq(a, a_c),
            "fpp_on_vs_off_a.test (I3 vs I1)": eq(a, a_nat),
            "override_vs_i1_a.test (expect SAME)": eq(a_ovr, a_nat),
            "override_vs_i3_baseline_a.test (expect DIFF)": eq(a_ovr, a),
            "loopback_ip_vs_a.test (I3)": eq(loop_ip, a),
            "loopback_ip_vs_native (I3 loopback vs I1 loopback)": eq(loop_ip, loop_nat),
            "loopback_name_vs_native": eq(loop_name, loop_nat),
            "loopback_override_vs_native (expect SAME if noise off)": eq(loop_ovr, loop_nat),
            "loopback_ip_native_vs_a.test_native": eq(loop_nat, a_nat),
            "rfp_positive_control_within_page (expect DIFF)": eq(a_rfp, a_rfp_r2),
            "rfp_positive_control_vs_native_a.test (expect DIFF)": eq(a_rfp, a_nat),
            "rfp_two_origins_a_vs_b (I2)": eq(a_rfp, b_rfp),
            "fpp_plusCanvas_vs_native_a.test": eq(a_add, a_nat),
            "fpp_plusCanvas_two_origins_a_vs_b": eq(a_add, b_add),
            "fpp_plusCanvas_vs_default_fpp_a.test": eq(a_add, a),
            "fpp_allTargets_vs_native_a.test": eq(r1("H_i3_alltargets", "a_alltargets"), a_nat),
            "fpp_allTargets_two_origins": eq(r1("H_i3_alltargets", "a_alltargets"), r1("H_i3_alltargets", "b_alltargets")),
            "fpp_allTargets_containers_c1_vs_c2": eq(r1("H_i3_alltargets", "a_all_c1"), r1("H_i3_alltargets", "a_all_c2")),
            "fpp_allTargets_container_vs_top": eq(r1("H_i3_alltargets", "a_all_c1"), r1("H_i3_alltargets", "a_alltargets")),
            "fpp_allTargets_within_page_stability": eq(
                results.get("H_i3_alltargets", {}).get("a_alltargets", {}).get("readback1"),
                results.get("H_i3_alltargets", {}).get("a_alltargets", {}).get("readback2")),
            "fpp_allTargets_two_launches_same_profile": eq(r1("K_all_launch1", "a_all_launch1"), r1("K_all_launch2", "a_all_launch2")),
            "fpp_allTargets_minusCanvas_vs_native (expect SAME if removed)": eq(r1("L_all_minus_canvas", "a_all_minus_canvas"), a_nat),
            "fpp_allTargets_minusCanvas_vs_allTargets (expect DIFF)": eq(r1("L_all_minus_canvas", "a_all_minus_canvas"), r1("H_i3_alltargets", "a_alltargets")),
            "fpp_privateWindow_vs_native_a.test": eq(r1("I_i3_private", "a_private"), a_nat),
            "fpp_privateWindow_two_origins": eq(r1("I_i3_private", "a_private"), r1("I_i3_private", "b_private")),
        },
    }
    print(json.dumps(summary, indent=2))
    out = pathlib.Path("/tmp/aegis_canvas_keying_results.json")
    out.write_text(json.dumps({"summary": summary, "raw": results}, indent=2))
    print(f"\nFull raw results: {out}")


if __name__ == "__main__":
    main()
