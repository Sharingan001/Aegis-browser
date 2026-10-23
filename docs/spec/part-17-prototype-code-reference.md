# Part 17. Prototype code reference

All prototypes are local-only (no network), and `python3 -m unittest test_aegis` runs **27 tests**.

| File | Contents |
|---|---|
| `aegis_psl.py` | Public Suffix List parser: longest-match, wildcard, and exception rules; small fallback subset (load the official list for real use) |
| `linkguard_prototype.py` | Static URL analysis (dangerous schemes, `@`/credentials, IP hosts, punycode and mixed scripts, brand-in-subdomain, token-level lookalikes with confusable characters, shorteners, redirect parameters, link-text mismatch); lure-text scoring; login-form checks (password over HTTP, cross-domain post, lure + login); clipboard-command lure; verdict levels with plain-language reasons |
| `aegis_modules.py` | `clean_link` (M11), `inspect_download` (M8), `breach_lookup_prefix` and `password_basic_checks` (M9), `xray_headers` (M15), `Scope.check` (M16), `route_to_cell` (M1), `sweep` (M10) |
| `test_aegis.py` | PSL tests; Link Guard benign set (12 real sites + a short-brand false-positive case) and suspicious set; module tests including the standard SHA-1 vector |

**Known prototype limits:** small brand list and suffix subset; simple lexicons; no multi-language packs; no real browser integration; thresholds not yet tuned on a large benign corpus.
