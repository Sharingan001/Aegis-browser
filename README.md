# Aegis Browser

A desktop browser on the Gecko engine (Firefox ESR base) with multi-level security,
isolated Cells, phishing protection, and a module ecosystem.

**Status:** Phase 0 — baseline scaffold and prototype port. Not yet usable as a browser.

## What Aegis is (and is not)

- Aegis gives each browsing task its own **Cell** with its own network route, attack-surface
  level, identity policy, and storage.
- It explains every protection decision in plain language and verifies that protections are
  actually active.
- **Aegis does not claim anonymity or that any site is "safe".** HTTPS is not evidence of
  safety; "no warning" is not evidence of safety.
- Aegis is not an official Mozilla or Tor Project product.
- This is pre-release research code. Do not rely on it for production security.

## Honest limits (repeated here so they appear at the top)

- No browser, level, or Tor setting guarantees anonymity.
- Higher security levels break some websites; this is documented and expected.
- Heuristic phishing detection has false positives and negatives; attackers adapt.
- A browser or OS vulnerability can defeat any browser-level protection until patched.
- External review is required before any strong anonymity or safety claim.

## Engine

Gecko (Firefox ESR). Pinned version: see `upstream/VERSION`.
**No Chromium, Blink, Electron, CEF, or Chromium WebView.**

## Structure

```
docs/          Specification, decisions, build guide, verify log
config/        Level files (axes), presets, policies, rules
services/      Protection services (Cell manager, Link Guard, etc.)
modules/       Built-in WebExtension modules (M1–M24)
tests/         Enforcement tests, leak matrix, fixtures
prototypes/    Python prototype code and unit tests (27 tests)
upstream/      Pinned Firefox ESR version reference and patch queue
```

See `docs/spec/INDEX.md` for the full specification index.
See `docs/BUILD.md` for build and fast-path setup instructions.
See `docs/DECISIONS.md` for design decisions.
See `docs/VERIFY.md` for unverified items needing confirmation against the pinned ESR.

## Reporting security issues

See `SECURITY.md`.
