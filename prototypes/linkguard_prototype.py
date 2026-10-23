"""
Aegis Link Guard - reference prototype (defensive, local-only, no network).

Stages covered here:
  1. Static URL analysis (before any request is made)
  2. Lure / intent text analysis (page text, run locally on extracted text)
  3. Clipboard-command check (ClickFix-style "paste this" lures)
  4. Scoring -> verdict with human-readable reasons

This is a teaching prototype. A real build must:
  - load the full official Public Suffix List (a small fallback subset is used by default),
  - run inside the browser's privileged, isolated component (not page context),
  - load rules from versioned files, each rule covered by tests.
"""
import re
import unicodedata
from dataclasses import dataclass, field
from urllib.parse import urlsplit, parse_qs

from aegis_psl import PublicSuffixList

_PSL = PublicSuffixList.fallback()   # replace with PublicSuffixList.from_file("public_suffix_list.dat")

# ---- Local data (would be versioned config files in the real project) -------
BRANDS = {            # brand token -> legitimate registrable domain
    "paypal": "paypal.com",
    "microsoft": "microsoft.com",
    "google": "google.com",
    "amazon": "amazon.com",
    "apple": "apple.com",
    "netflix": "netflix.com",
    "instagram": "instagram.com",
    "sbi": "sbi.co.in",
}
SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "goo.gl", "is.gd", "cutt.ly"}
CONFUSABLES = str.maketrans({"1": "l", "0": "o", "5": "s", "3": "e", "|": "l"})
REDIRECT_PARAMS = {"url", "redirect", "redirect_uri", "next", "continue", "dest", "return"}

# Lure lexicon: (regex, weight, label). Keep readable and testable.
LURE_RULES = [
    (r"\b(free|gift|prize|reward|giveaway)\b", 1, "free/prize wording"),
    (r"\b(you('| ha)ve won|winner|congratulations|claim (your|now))\b", 2, "winner/claim wording"),
    (r"\b(urgent|immediately|within 24 hours|last warning|act now)\b", 2, "urgency"),
    (r"\b(account (has been )?(suspended|locked|limited)|unusual (sign.?in|activity))\b", 2, "account-threat wording"),
    (r"\b(verify (your )?(account|identity)|confirm (your )?(password|details))\b", 2, "verification demand"),
    (r"\b(kyc (expir|update|pending)|collect request|disconnection notice)\b", 2, "regional-scam wording"),
    (r"\b(gift ?card|crypto(currency)? (deposit|wallet)|wire transfer|processing fee)\b", 2, "unusual payment demand"),
    (r"\b(call (us )?(now|immediately)|your (pc|device|computer) (is|has been) infected)\b", 3, "tech-support scam wording"),
    (r"\b(verify you are (a )?human|fix this error|press win\+r|paste (it|this) (into|in))\b", 3, "fake-verification / paste instruction"),
]

# Text that looks like a shell command being handed to a user to paste.
CLIPBOARD_COMMAND_PATTERNS = [
    r"powershell(\.exe)?\s+.*(-enc|-e\s|-w\s+hidden|iex|downloadstring)",
    r"\bmshta\b",
    r"\bcmd(\.exe)?\s+/c\b",
    r"\bcurl\b[^|\n]*\|\s*(ba)?sh\b",
    r"\bwget\b[^|\n]*\|\s*(ba)?sh\b",
]


@dataclass
class Finding:
    rule: str
    points: int
    detail: str


@dataclass
class Verdict:
    level: str                      # "none" | "notice" | "caution" | "block"
    score: int
    findings: list = field(default_factory=list)
    hard_stop: bool = False


# ---- Helpers -----------------------------------------------------------------
def registrable_domain(host: str) -> str:
    """Uses the Public Suffix List (see aegis_psl.py). Load the official list in production."""
    return _PSL.registrable_domain(host)


def levenshtein(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def scripts_in(text: str) -> set:
    out = set()
    for ch in text:
        if ch.isalpha():
            out.add(unicodedata.name(ch, "UNKNOWN").split(" ")[0])  # LATIN, CYRILLIC, GREEK...
    return out


def is_ip_literal(host: str) -> bool:
    return bool(re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", host)) or ":" in host


# ---- Stage 1: static URL analysis ---------------------------------------------
def analyze_url(url: str, link_text: str = "") -> list:
    f = []
    u = urlsplit(url)
    scheme = u.scheme.lower()

    if scheme in ("javascript", "data"):
        return [Finding("scheme.active", 100, f"'{scheme}:' links can run content directly")]
    if scheme == "http":
        f.append(Finding("transport.http", 2, "Connection is not encrypted (HTTP). Never enter passwords or payment details."))
    elif scheme != "https":
        f.append(Finding("scheme.unusual", 2, f"Unusual scheme '{scheme}:'"))

    host = (u.hostname or "").lower()
    if not host:
        return f + [Finding("url.nohost", 3, "No host found in address")]

    if u.username is not None:
        f.append(Finding("url.userinfo", 4, "Address contains '@' or credentials: what is before '@' is not the real site"))
    if is_ip_literal(host):
        f.append(Finding("host.ip", 3, "Site is reached by a raw IP address instead of a name"))
    if u.port not in (None, 80, 443):
        f.append(Finding("host.port", 1, f"Non-standard port {u.port}"))

    # Internationalized names / lookalike characters
    if host.startswith("xn--") or ".xn--" in host:
        f.append(Finding("host.punycode", 3, "Name uses punycode (may display as lookalike characters)"))
    try:
        unicode_host = host.encode("ascii").decode("idna")
    except Exception:
        unicode_host = host
    sc = scripts_in(unicode_host)
    if len(sc) > 1:
        f.append(Finding("host.mixed_script", 5, f"Name mixes writing systems {sorted(sc)}: common lookalike trick"))

    reg = registrable_domain(unicode_host)
    label = reg.split(".")[0]
    subdomain_part = unicode_host[: -len(reg)] if unicode_host.endswith(reg) else ""

    if unicode_host in SHORTENERS or reg in SHORTENERS:
        f.append(Finding("host.shortener", 2, "Link shortener hides the real destination"))

    if subdomain_part.count(".") >= 3:
        f.append(Finding("host.deep_subdomain", 2, "Unusually many subdomains"))

    tokens = [t for t in re.split(r"[-_]", label) if t]
    for brand, legit in BRANDS.items():
        if reg == legit:
            continue
        if brand in subdomain_part.split(".") or (len(brand) >= 5 and brand in subdomain_part):
            f.append(Finding("brand.subdomain", 5, f"Contains '{brand}' as a subdomain, but the real domain is '{reg}' (not {legit})"))
            continue
        for tok in tokens:
            norm = tok.translate(CONFUSABLES)
            exact_in_name = tok == brand or (len(brand) >= 5 and brand in tok)
            lookalike = tok != brand and (norm == brand or (len(brand) >= 6 and len(tok) >= 5 and levenshtein(tok, brand) == 1))
            if exact_in_name or lookalike:
                f.append(Finding("brand.lookalike", 5, f"'{reg}' imitates '{legit}'"))
                break

    if re.search(r"[a-z]\d[a-z]", label) and any(b in re.sub(r"\d", "", label) for b in BRANDS):
        f.append(Finding("brand.digit_swap", 3, "Digits used in place of letters in a brand-like name"))

    # Open-redirect style parameters pointing to another site
    for k, vals in parse_qs(u.query).items():
        if k.lower() in REDIRECT_PARAMS:
            for v in vals:
                if re.match(r"https?://", v, re.I):
                    f.append(Finding("url.redirect_param", 2, f"Parameter '{k}' sends you on to another site"))

    # Link text says one place, link goes another
    m = re.search(r"([a-z0-9-]+\.)+[a-z]{2,}", link_text.lower())
    if m and registrable_domain(m.group(0)) != reg:
        f.append(Finding("link.text_mismatch", 4, f"Link text shows '{m.group(0)}' but goes to '{reg}'"))

    if len(url) > 200:
        f.append(Finding("url.long", 1, "Very long address"))
    return f


# ---- Stage 2: lure / intent text ---------------------------------------------
def analyze_text(text: str, has_password_field: bool = False, form_action_url: str = "", page_url: str = "") -> list:
    f, t = [], text.lower()
    total, labels = 0, []
    for pattern, weight, label in LURE_RULES:
        if re.search(pattern, t):
            total += weight
            labels.append(label)
    if total:
        f.append(Finding("lure.text", min(total, 8), "Wording often used in scams: " + ", ".join(labels)))

    if has_password_field and page_url.lower().startswith("http://"):
        f.append(Finding("form.password_over_http", 6, "Password field on an unencrypted page"))
    if has_password_field and form_action_url:
        if registrable_domain(urlsplit(form_action_url).hostname or "") != registrable_domain(urlsplit(page_url).hostname or ""):
            f.append(Finding("form.cross_domain_post", 5, "Login form sends your password to a different site"))
    if has_password_field and total >= 3:
        f.append(Finding("combo.lure_plus_login", 3, "Urgent/prize wording together with a login form"))
    return f


# ---- Stage 3: clipboard command lure -----------------------------------------
def analyze_clipboard_write(text: str) -> list:
    for p in CLIPBOARD_COMMAND_PATTERNS:
        if re.search(p, text, re.I):
            return [Finding("clipboard.command", 8, "This page copied something that looks like a system command. Do not paste it into Run, Terminal or PowerShell.")]
    return []


# ---- Stage 4: verdict --------------------------------------------------------
def verdict(findings: list) -> Verdict:
    score = sum(x.points for x in findings)
    hard = any(x.rule in ("scheme.active", "clipboard.command") for x in findings)
    if hard or score >= 9:
        level = "block" if hard or score >= 12 else "caution"
    elif score >= 5:
        level = "caution"
    elif score >= 2:
        level = "notice"
    else:
        level = "none"
    return Verdict(level, score, findings, hard)


def explain(v: Verdict) -> str:
    lines = [f"Verdict: {v.level.upper()} (score {v.score})"]
    for x in sorted(v.findings, key=lambda z: -z.points):
        lines.append(f"  - [{x.rule}] {x.detail}")
    if v.level == "none":
        lines.append("  No warning signs found. This does NOT prove the site is safe.")
    return "\n".join(lines)


# ---- Self-tests (fictional domains only) ---------------------------------------
if __name__ == "__main__":
    cases = [
        ("https://www.paypal.com/signin", ""),
        ("http://paypal.com.account-verify.example/login", ""),
        ("https://paypa1.example/secure", ""),
        ("https://secure-login@198.51.100.7/update", ""),
        ("https://аpple.example/id", ""),                       # first letter is Cyrillic
        ("https://bit.ly/abc123", "www.google.com/offer"),
        ("https://news.example/?next=https://other.example/x", ""),
    ]
    for url, text in cases:
        print(url)
        print(explain(verdict(analyze_url(url, text))), "\n")

    page = "Congratulations! You have won a free gift. Claim now, urgent: verify your account within 24 hours."
    print("Lure page + login form posting elsewhere:")
    print(explain(verdict(analyze_text(page, True, "https://collector.example/post", "http://prize.example/"))), "\n")

    print("Clipboard lure:")
    print(explain(verdict(analyze_clipboard_write("powershell -w hidden -enc AAAA"))))
