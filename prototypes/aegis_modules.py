"""
Aegis feature modules - reference prototypes (local-only, no network calls).

  M11 LinkCleaner        strip tracking parameters from URLs
  M8  DownloadInspector  hash a file, detect disguised types and double extensions
  M9  CredentialRadar    k-anonymity prefix for breach lookups (the lookup itself is opt-in)
  M15 SiteXray           passive review of response headers the browser already received
  M16 ScopeGuard         keep a Lab Cell inside a declared, authorized scope
  M1  CellRouter         route links to Cells by simple, readable rules
  M10 SessionSweeper     decide which site data has expired

These are teaching prototypes: each becomes a built-in extension or chrome-UI component
with a Module Manifest (see Aegis_Modules_Catalog_v1.md).
"""
from __future__ import annotations

import fnmatch
import hashlib
import os
import re
import time
from dataclasses import dataclass, field
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from aegis_psl import registrable_domain

# =============================================================================
# M11 LinkCleaner
# =============================================================================
TRACKING_PARAMS = {
    "fbclid", "gclid", "dclid", "msclkid", "mc_eid", "mc_cid", "igshid", "yclid",
    "_hsenc", "_hsmi", "ref_src", "ref_url", "vero_id", "spm", "si",
}
TRACKING_PREFIXES = ("utm_", "pk_", "mtm_", "hsa_")


def clean_link(url: str, keep: set | None = None) -> tuple[str, list]:
    """Return (cleaned_url, removed_param_names). `keep` lets the user whitelist names."""
    keep = {k.lower() for k in (keep or set())}
    u = urlsplit(url)
    kept, removed = [], []
    for k, v in parse_qsl(u.query, keep_blank_values=True):
        lk = k.lower()
        if lk not in keep and (lk in TRACKING_PARAMS or lk.startswith(TRACKING_PREFIXES)):
            removed.append(k)
        else:
            kept.append((k, v))
    return urlunsplit((u.scheme, u.netloc, u.path, urlencode(kept), u.fragment)), removed


# =============================================================================
# M8 DownloadInspector
# =============================================================================
MAGIC = {                       # file signature -> true type
    b"MZ": "windows-executable",
    b"\x7fELF": "linux-executable",
    b"%PDF": "pdf",
    b"PK\x03\x04": "zip-or-office",
    b"\x89PNG": "png",
    b"\xff\xd8\xff": "jpeg",
    b"GIF8": "gif",
    b"#!": "script",
}
RISKY_EXT = {"exe", "scr", "msi", "bat", "cmd", "ps1", "vbs", "js", "jse", "wsf", "hta", "lnk", "jar", "com", "dll", "sh", "iso", "img"}
DECOY_EXT = {"pdf", "doc", "docx", "xls", "xlsx", "jpg", "jpeg", "png", "txt", "mp4", "mp3", "zip"}


@dataclass
class DownloadReport:
    sha256: str
    size: int
    claimed_ext: str
    detected_type: str
    flags: list = field(default_factory=list)

    @property
    def level(self) -> str:
        if any(f.startswith("HIGH") for f in self.flags):
            return "high"
        return "medium" if self.flags else "low"


def inspect_download(filename: str, data: bytes) -> DownloadReport:
    parts = filename.lower().split(".")
    ext = parts[-1] if len(parts) > 1 else ""
    detected = next((t for sig, t in MAGIC.items() if data.startswith(sig)), "unknown")
    flags = []

    if len(parts) >= 3 and parts[-2] in DECOY_EXT and parts[-1] in RISKY_EXT:
        flags.append(f"HIGH double extension: looks like .{parts[-2]} but is .{parts[-1]}")
    if ext in RISKY_EXT:
        flags.append(f"MEDIUM executable/script type .{ext}: quarantine and do not auto-open")
    if detected in ("windows-executable", "linux-executable") and ext not in RISKY_EXT:
        flags.append(f"HIGH content is {detected} but name says .{ext or 'none'}")
    expected = {"pdf": "pdf", "png": "png", "jpg": "jpeg", "jpeg": "jpeg", "gif": "gif"}.get(ext)
    if expected and detected not in ("unknown", expected) and detected not in ("windows-executable", "linux-executable"):
        flags.append(f"MEDIUM name says .{ext} but content looks like {detected}")
    if re.search(r"[\u202e\u202d]", filename):
        flags.append("HIGH filename contains a right-to-left override character (hides the true extension)")
    if len(filename) > 120:
        flags.append("LOW very long filename")
    return DownloadReport(hashlib.sha256(data).hexdigest(), len(data), ext, detected, flags)


# =============================================================================
# M9 CredentialRadar (k-anonymity prefix only)
# =============================================================================
def breach_lookup_prefix(password: str) -> tuple[str, str]:
    """
    k-anonymity scheme used by breach-check services: hash locally with SHA-1,
    send ONLY the first 5 hex characters, compare the returned suffixes locally.
    Returns (prefix_to_send, suffix_to_compare_locally). The password never leaves the device.
    This function performs no network access; the lookup itself is an opt-in module action.
    """
    digest = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
    return digest[:5], digest[5:]


def password_basic_checks(pw: str) -> list:
    issues = []
    if len(pw) < 12:
        issues.append("shorter than 12 characters")
    if pw.lower() in {"password", "123456", "qwerty", "letmein", "admin", "welcome"}:
        issues.append("extremely common password")
    if len(set(pw)) <= 3:
        issues.append("very low variety of characters")
    return issues


# =============================================================================
# M15 SiteXray (passive: reads headers the browser already received)
# =============================================================================
def xray_headers(headers: dict, is_https: bool) -> list:
    h = {k.lower(): v for k, v in headers.items()}
    out = []

    def add(sev, msg):
        out.append((sev, msg))

    if is_https and "strict-transport-security" not in h:
        add("warn", "No HSTS header: browsers are not told to insist on HTTPS for this site")
    if "content-security-policy" not in h:
        add("warn", "No Content-Security-Policy: limited protection against injected scripts")
    else:
        csp = h["content-security-policy"]
        if "unsafe-inline" in csp or "unsafe-eval" in csp:
            add("info", "CSP allows 'unsafe-inline' or 'unsafe-eval', which weakens its protection")
    if "x-frame-options" not in h and "frame-ancestors" not in h.get("content-security-policy", ""):
        add("warn", "No clickjacking protection (X-Frame-Options or CSP frame-ancestors)")
    if h.get("x-content-type-options", "").lower() != "nosniff":
        add("info", "Missing 'X-Content-Type-Options: nosniff'")
    if "referrer-policy" not in h:
        add("info", "No Referrer-Policy: browser default applies")
    for c in ([h["set-cookie"]] if isinstance(h.get("set-cookie"), str) else h.get("set-cookie", [])):
        flags = c.lower()
        name = c.split("=")[0]
        if is_https and "secure" not in flags:
            add("warn", f"Cookie '{name}' lacks the Secure flag")
        if "httponly" not in flags:
            add("info", f"Cookie '{name}' lacks HttpOnly (readable by page scripts)")
        if "samesite" not in flags:
            add("info", f"Cookie '{name}' has no SameSite attribute")
    if "server" in h and re.search(r"\d+\.\d+", h["server"]):
        add("info", "Server header reveals a version number")
    if not out:
        add("ok", "No common header issues found (this is not a full security assessment)")
    return out


# =============================================================================
# M16 ScopeGuard
# =============================================================================
@dataclass
class Scope:
    """Declared, authorized targets for a Lab Cell. Wildcards allowed: '*.target.example'."""
    allow: list
    deny: list = field(default_factory=list)

    def check(self, url: str) -> tuple[bool, str]:
        host = (urlsplit(url).hostname or "").lower()
        for pat in self.deny:
            if fnmatch.fnmatch(host, pat.lower()):
                return False, f"'{host}' is explicitly out of scope ({pat})"
        for pat in self.allow:
            if fnmatch.fnmatch(host, pat.lower()):
                return True, f"'{host}' matches in-scope rule {pat}"
        return False, f"'{host}' is not in the declared scope"


# =============================================================================
# M1 CellRouter
# =============================================================================
@dataclass
class RouteRule:
    pattern: str               # glob on registrable domain or host
    cell: str
    keyword: str = ""          # optional keyword that must appear in the URL


def route_to_cell(url: str, rules: list, default_cell: str = "Default") -> str:
    u = urlsplit(url)
    host, reg = (u.hostname or "").lower(), registrable_domain(u.hostname or "")
    for r in rules:
        if (fnmatch.fnmatch(host, r.pattern) or fnmatch.fnmatch(reg, r.pattern)) and (not r.keyword or r.keyword in url.lower()):
            return r.cell
    return default_cell


# =============================================================================
# M10 SessionSweeper
# =============================================================================
@dataclass
class SiteData:
    origin: str
    last_interaction: float     # epoch seconds
    has_login: bool = False


def sweep(items: list, now: float, max_age_days: int = 14, keep_domains: set | None = None) -> list:
    """Return the origins whose data should be deleted. Allow-listed domains are never touched."""
    keep_domains = {d.lower() for d in (keep_domains or set())}
    out = []
    for s in items:
        reg = registrable_domain(urlsplit(s.origin).hostname or s.origin)
        if reg in keep_domains:
            continue
        if now - s.last_interaction > max_age_days * 86400:
            out.append(s.origin)
    return out
