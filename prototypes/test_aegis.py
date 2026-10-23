"""Run:  python3 -m unittest -v test_aegis.py   (no network needed)"""
import time
import unittest

from aegis_psl import PublicSuffixList
import linkguard_prototype as lg
import aegis_modules as m


class TestPSL(unittest.TestCase):
    def setUp(self):
        self.p = PublicSuffixList.fallback()

    def test_multi_label_suffix(self):
        self.assertEqual(self.p.registrable_domain("a.b.example.co.uk"), "example.co.uk")
        self.assertEqual(self.p.registrable_domain("shop.example.co.in"), "example.co.in")

    def test_private_suffix_isolates_tenants(self):
        self.assertEqual(self.p.registrable_domain("x.github.io"), "x.github.io")

    def test_wildcard_and_exception(self):
        self.assertEqual(self.p.registrable_domain("a.b.ck"), "a.b.ck")
        self.assertEqual(self.p.registrable_domain("www.ck"), "www.ck")

    def test_host_is_suffix(self):
        self.assertEqual(self.p.registrable_domain("co.uk"), "co.uk")


# --- Link Guard evaluation: benign set must stay quiet; bad set must be flagged --------
BENIGN = [
    "https://www.google.com/search?q=weather",
    "https://en.wikipedia.org/wiki/Phishing",
    "https://github.com/mozilla/gecko-dev",
    "https://www.paypal.com/signin",
    "https://accounts.google.com/signin",
    "https://www.amazon.com/dp/B000000000",
    "https://docs.python.org/3/library/urllib.html",
    "https://www.bbc.co.uk/news",
    "https://www.sbi.co.in/web/personal-banking",
    "https://news.ycombinator.com/",
    "https://stackoverflow.com/questions/1",
    "https://support.apple.com/en-in",
    "https://www.responsibility-matters.example/about",   # contains "sbi" but is not a brand lookalike
    "https://applypark.example/",
]
SUSPICIOUS = [
    "http://paypal.com.account-verify.example/login",
    "https://paypa1.example/secure",
    "https://secure-login@198.51.100.7/update",
    "https://\u0430pple.example/id",                       # Cyrillic 'a'
    "javascript:alert(1)",
    "https://microsoft.com.secure-check.example/office",
    "https://netfIix-billing.example/pay",                 # capital I instead of l (lowercased -> netfiix)
    "http://203.0.113.9/login",
]


class TestLinkGuardEval(unittest.TestCase):
    def test_benign_have_no_caution_or_block(self):
        false_positives = []
        for url in BENIGN:
            v = lg.verdict(lg.analyze_url(url))
            if v.level in ("caution", "block"):
                false_positives.append((url, v.level, [f.rule for f in v.findings]))
        self.assertEqual(false_positives, [], f"false positives: {false_positives}")

    def test_suspicious_are_flagged(self):
        missed = [u for u in SUSPICIOUS if lg.verdict(lg.analyze_url(u)).level == "none"]
        self.assertEqual(missed, [], f"missed: {missed}")

    def test_brand_embedded_in_unrelated_domain_gets_caution_by_design(self):
        # Trade-off: legitimate fan sites or resellers may trigger this; the warning explains why
        # and lets the user continue. Tune with the benign-set false-positive rate.
        v = lg.verdict(lg.analyze_url("https://googleplayground.example/"))
        self.assertIn(v.level, ("caution", "block"))

    def test_http_alone_is_notice_not_block(self):
        v = lg.verdict(lg.analyze_url("http://example.test/page"))
        self.assertEqual(v.level, "notice")

    def test_password_over_http_is_hard_warning(self):
        f = lg.analyze_text("Sign in", True, "", "http://example.test/login")
        self.assertIn("form.password_over_http", [x.rule for x in f])

    def test_lure_text_scores(self):
        t = "Congratulations! You have won a free gift. Claim now, urgent: verify your account within 24 hours."
        self.assertGreaterEqual(lg.verdict(lg.analyze_text(t)).score, 5)

    def test_plain_text_is_quiet(self):
        t = "The quarterly report is attached. Let me know if you have questions about the figures."
        self.assertEqual(lg.verdict(lg.analyze_text(t)).level, "none")

    def test_cross_domain_login_form(self):
        f = lg.analyze_text("Login", True, "https://collector.example/post", "https://bank.example/login")
        self.assertIn("form.cross_domain_post", [x.rule for x in f])

    def test_clipboard_command_lure(self):
        self.assertEqual(lg.verdict(lg.analyze_clipboard_write("powershell -w hidden -enc AAAA")).level, "block")
        self.assertEqual(lg.analyze_clipboard_write("hello world"), [])

    def test_https_never_called_safe(self):
        out = lg.explain(lg.verdict(lg.analyze_url("https://www.google.com/")))
        self.assertIn("does NOT prove", out)


class TestModules(unittest.TestCase):
    def test_link_cleaner(self):
        url, removed = m.clean_link("https://shop.example/p?id=7&utm_source=x&fbclid=abc&color=red#top")
        self.assertEqual(url, "https://shop.example/p?id=7&color=red#top")
        self.assertEqual(sorted(removed), ["fbclid", "utm_source"])

    def test_link_cleaner_keep_list(self):
        url, removed = m.clean_link("https://x.example/?utm_source=news&a=1", keep={"utm_source"})
        self.assertEqual(removed, [])

    def test_download_double_extension(self):
        r = m.inspect_download("invoice.pdf.exe", b"MZ\x90\x00")
        self.assertEqual(r.level, "high")

    def test_download_disguised_executable(self):
        r = m.inspect_download("photo.jpg", b"MZ\x90\x00rest")
        self.assertEqual(r.level, "high")

    def test_download_rtl_override(self):
        r = m.inspect_download("report\u202egpj.exe", b"MZ")
        self.assertTrue(any("right-to-left" in f for f in r.flags))

    def test_download_clean_pdf(self):
        r = m.inspect_download("paper.pdf", b"%PDF-1.7 ...")
        self.assertEqual(r.level, "low")
        self.assertEqual(len(r.sha256), 64)

    def test_breach_prefix_is_5_chars_and_password_not_in_it(self):
        prefix, suffix = m.breach_lookup_prefix("correct horse battery staple")
        self.assertEqual(len(prefix), 5)
        self.assertEqual(len(suffix), 35)
        self.assertNotIn("correct", prefix + suffix)

    def test_known_sha1_vector(self):
        # SHA-1("password") = 5BAA61E4C9B93F3F0682250B6CF8331B7EE68FD8
        self.assertEqual(m.breach_lookup_prefix("password"), ("5BAA6", "1E4C9B93F3F0682250B6CF8331B7EE68FD8"))

    def test_xray_flags_missing_headers(self):
        out = m.xray_headers({"Server": "nginx/1.18.0"}, is_https=True)
        text = " ".join(msg for _, msg in out)
        self.assertIn("HSTS", text)
        self.assertIn("Content-Security-Policy", text)
        self.assertIn("version number", text)

    def test_xray_cookie_flags(self):
        out = m.xray_headers({"set-cookie": "sid=1; Path=/"}, is_https=True)
        text = " ".join(msg for _, msg in out)
        self.assertIn("Secure", text)
        self.assertIn("HttpOnly", text)

    def test_scope_guard(self):
        s = m.Scope(allow=["*.lab.example", "lab.example"], deny=["admin.lab.example"])
        self.assertTrue(s.check("https://app.lab.example/x")[0])
        self.assertFalse(s.check("https://admin.lab.example/")[0])
        self.assertFalse(s.check("https://other.example/")[0])

    def test_cell_router(self):
        rules = [m.RouteRule("*.sbi.co.in", "Banking"), m.RouteRule("github.com", "Research", keyword="ctf")]
        self.assertEqual(m.route_to_cell("https://www.sbi.co.in/login", rules), "Banking")
        self.assertEqual(m.route_to_cell("https://github.com/org/ctf-writeups", rules), "Research")
        self.assertEqual(m.route_to_cell("https://github.com/org/app", rules), "Default")

    def test_session_sweeper(self):
        now = time.time()
        items = [m.SiteData("https://old.example", now - 40 * 86400),
                 m.SiteData("https://new.example", now - 1 * 86400),
                 m.SiteData("https://bank.example", now - 90 * 86400)]
        self.assertEqual(m.sweep(items, now, 14, keep_domains={"bank.example"}), ["https://old.example"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
