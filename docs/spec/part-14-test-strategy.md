# Part 14. Test strategy

## 14.1 Functional

Tabs, navigation, bookmarks, history, downloads, permissions, clear-data, settings persistence, keyboard navigation, update UI.

## 14.2 Security

- **Axis tests:** every control verified inside the running browser; cumulativity (S3 ⊇ S2); conflict rules.
- **Crowd analysis (R2):** record how level combinations change observable values; document which combinations are distinctive.
- **Ledger tests:** each rule fires on crafted local pages, escalates only, explains correctly, reverts.
- **Cell isolation:** cookies, localStorage, IndexedDB, service workers, cache, permissions, identity seeds.
- **Canary and leak tests:** Tor down, proxy misconfigured, IPv6, WebRTC, DNS; fail-closed.
- **Link Guard:** per-rule positive/negative; benign top-site false-positive rate; HTTP-with-password hard warning; HTTPS never labeled "safe"; external-open scrutiny; clipboard-command lure; cross-domain login form; Anchored Cell credential binding.
- **Detonation:** quarantine, no auto-open, storage destroyed, receipt matches reality.
- **Flight Recorder:** tamper detection, redaction.
- **Modules:** manifest permissions enforced; kill switch; cross-Cell isolation; fuzzing of module inputs.
- **Regression on every upstream update:** any pref that disappears or changes meaning fails the build.

## 14.3 Quality

Performance budgets (pre-load Link Guard and Link Cleaner checks must not add noticeable delay), memory with many tabs, crash recovery, accessibility, compatibility corpus per level, localization of warning text.

## 14.4 Safe testing rules

- Use **only your own or explicitly authorized** pages, networks, and systems.
- For phishing tests, use **offline labeled datasets** and **saved, defanged copies** of pages inside an isolated VM; never browse live phishing pages for testing.
- Keep test fixtures local and clearly labeled.
