# tests/fixtures/README.md — Aegis test fixtures

This directory contains local, offline mock pages for Link Guard and axis enforcement
testing.

## Safety rules (mandatory)

1. **Never put real phishing content here.** All pages must be clearly labeled with
   `<!-- AEGIS TEST FIXTURE: ... -->` comments.
2. **Never fetch live phishing or malicious URLs** to create test fixtures.
   Use synthetic mock pages designed to exercise specific rule patterns.
3. **All fixtures are offline.** The test server (`tests/tools/local_test_server.py`)
   serves them on `127.0.0.1` only, with no external network access.
4. Label every fixture with: what rule it tests, the expected Aegis verdict, and that it
   is a test fixture (not a real site).

## Fixture categories (planned)

| Directory | Purpose |
|---|---|
| `benign/` | Clean, ordinary pages; expected verdict: None |
| `http-only/` | Plain HTTP pages; expected verdict: Notice or Caution (transport stage) |
| `phishing-mock/` | Labeled synthetic pages matching specific Link Guard rules |
| `download/` | Files for Download Inspector tests (type/content mismatch, etc.) |
| `axes/` | Pages for axis enforcement tests (e.g., WebGL probe, WASM probe) |

## Phase 0 status

Inline fixtures are embedded in `tests/tools/local_test_server.py` for the scaffold.
Real fixture files will be added per-rule starting in Phase 5 (Link Guard).
