#!/usr/bin/env python3
"""
tests/tools/local_test_server.py — Aegis local mock-page server (Phase 0 scaffold)

Serves labeled local mock pages from tests/fixtures/ for use in enforcement tests.
Uses ONLY the Python standard library (no external packages).

Usage:
    python3 tests/tools/local_test_server.py [--port 8765] [--host 127.0.0.1]

This server is for offline testing ONLY. It must never be exposed to the internet.
All test pages are benign, defanged fixtures — never real phishing or malware content.
"""

import argparse
import http.server
import json
import os
import pathlib
import signal
import sys
import urllib.parse

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures"

# ── Inline fixture pages ──────────────────────────────────────────────────────
# These are served if real fixture files are not found on disk.
# All are clearly labeled as test pages. None are real phishing content.

INLINE_FIXTURES = {
    "/": b"""<!DOCTYPE html>
<html><head><title>Aegis Test Server</title></head>
<body>
<h1>Aegis Local Test Server</h1>
<p>For offline enforcement testing only. Not connected to the internet.</p>
<ul>
  <li><a href="/benign/index.html">Benign page (HTTPS-equivalent local)</a></li>
  <li><a href="/http-only/index.html">HTTP-only test page (no TLS)</a></li>
  <li><a href="/phishing-mock/index.html">Phishing mock (labeled, defanged)</a></li>
  <li><a href="/download/test.txt">Download test (plain text)</a></li>
  <li><a href="/download/mislabeled.jpg">Download test (text labeled as .jpg)</a></li>
</ul>
</body></html>
""",
    "/benign/index.html": b"""<!DOCTYPE html>
<!-- AEGIS TEST FIXTURE: benign/index.html - a clean, ordinary web page -->
<html><head><title>Example benign page</title></head>
<body>
<h1>Benign test page</h1>
<p>This is a clean, ordinary test page. It contains no tracking, no forms, no scripts.</p>
<p>Aegis Link Guard should produce: Verdict = None (no signals).</p>
</body></html>
""",
    "/http-only/index.html": b"""<!DOCTYPE html>
<!-- AEGIS TEST FIXTURE: http-only/index.html - served over plain HTTP (no TLS) -->
<html><head><title>HTTP-only test page</title></head>
<body>
<h1>HTTP-only test page</h1>
<p>This page is served over plain HTTP. In S2+, Aegis should prompt before allowing.</p>
<p>Aegis Link Guard should produce: Verdict = Notice (plain HTTP flagged).</p>
</body></html>
""",
    "/phishing-mock/index.html": b"""<!DOCTYPE html>
<!-- AEGIS TEST FIXTURE: phishing-mock/index.html
     LABELED MOCK - not real phishing content.
     Simulates: urgency wording + login form + cross-domain post action.
     This file is used ONLY for offline Link Guard rule testing.
     It must never be used to impersonate a real site. -->
<html><head><title>AEGIS MOCK: Phishing pattern test</title></head>
<body>
<h1>[MOCK TEST PAGE] Phishing pattern simulation</h1>
<p style="color:red">WARNING: Your account has been suspended! Verify within 24 hours.</p>
<form method="POST" action="http://different-registrable-domain.test/collect">
  <label>Email: <input type="email" name="email"></label><br>
  <label>Password: <input type="password" name="pw"></label><br>
  <button type="submit">Verify now</button>
</form>
<p><small>This is a labeled Aegis test fixture. Not a real page.</small></p>
</body></html>
""",
    "/download/test.txt": b"AEGIS TEST FIXTURE: plain text download. Content-Type: text/plain.\n",
    "/download/mislabeled.jpg": b"AEGIS TEST FIXTURE: this is plain text served as .jpg to test type-vs-content mismatch.\n",
}


class FixtureHandler(http.server.BaseHTTPRequestHandler):
    """Serve fixture files from disk or from INLINE_FIXTURES."""

    def log_message(self, fmt, *args):  # quiet the default access log
        print(f"  [test-server] {self.address_string()} {fmt % args}", file=sys.stderr)

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path

        # Record incoming headers for test inspection
        try:
            headers_dict = {k: v for k, v in self.headers.items()}
            headers_file = FIXTURES_DIR / "output" / "last_headers.json"
            headers_file.parent.mkdir(parents=True, exist_ok=True)
            headers_file.write_text(json.dumps(headers_dict, indent=2))
        except Exception:
            pass

        # Try disk first
        disk_path = FIXTURES_DIR / path.lstrip("/")
        if disk_path.is_file():
            content = disk_path.read_bytes()
            ctype = self._guess_type(disk_path.suffix)
            self._send(200, ctype, content)
            return

        # Special beacon for noscript detection
        if path == "/api/noscript_beacon":
            beacon_file = FIXTURES_DIR / "output" / "noscript_beacon.json"
            beacon_file.parent.mkdir(parents=True, exist_ok=True)
            beacon_file.write_text('{"noscript": true}')
            gif_1x1 = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
            self._send(200, "image/gif", gif_1x1)
            return

        # Fall back to inline
        if path in INLINE_FIXTURES:
            content = INLINE_FIXTURES[path]
            ctype = self._guess_type(pathlib.Path(path).suffix)
            self._send(200, ctype, content)
            return

        self._send(404, "text/plain", b"Not found: " + path.encode())

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/report":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            report_file = FIXTURES_DIR / "output" / "s3_report.json"
            report_file.parent.mkdir(parents=True, exist_ok=True)
            report_file.write_bytes(body)
            self._send(200, "application/json", b'{"status":"ok"}')
            return
        if path == "/api/report_fp":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            cid = query.get("cid", ["default"])[0]
            report_file = FIXTURES_DIR / "output" / f"fp_report_{cid}.json"
            report_file.parent.mkdir(parents=True, exist_ok=True)
            report_file.write_bytes(body)
            # Also write default fp_report.json for backward compatibility
            (FIXTURES_DIR / "output" / "fp_report.json").write_bytes(body)
            self._send(200, "application/json", b'{"status":"ok"}')
            return
        self._send(404, "text/plain", b"Not found")

    def _guess_type(self, suffix: str) -> str:
        return {
            ".html": "text/html; charset=utf-8",
            ".txt": "text/plain",
            ".json": "application/json",
            ".js": "text/javascript",
            ".css": "text/css",
        }.get(suffix.lower(), "application/octet-stream")

    def _send(self, code: int, ctype: str, body: bytes):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        # Security: never allow cross-origin requests to this local server
        self.send_header("Access-Control-Allow-Origin", "")
        self.end_headers()
        self.wfile.write(body)


def main():
    parser = argparse.ArgumentParser(description="Aegis local mock-page server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="Port (default: 8765)")
    args = parser.parse_args()

    server = http.server.HTTPServer((args.host, args.port), FixtureHandler)
    print(f"Aegis test server running at http://{args.host}:{args.port}/")
    print("Fixtures served from:", FIXTURES_DIR)
    print("Press Ctrl-C to stop.")

    def _shutdown(sig, frame):
        print("\nShutting down test server.")
        server.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)
    server.serve_forever()


if __name__ == "__main__":
    main()
