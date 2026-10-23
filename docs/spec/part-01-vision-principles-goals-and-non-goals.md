# Part 1. Vision, principles, goals and non-goals

## 1.1 Vision

Aegis is a daily-usable desktop browser that treats **security as the organizing idea of the whole product**, not a settings page. Instead of one global privacy slider, Aegis gives each task its own **Cell** with its own network route, attack-surface level, identity policy, and storage; it explains every protection decision in plain language; and it verifies that its protections are really active.

## 1.2 Principles

1. **Reuse a maintained engine.** Do not write a browser engine for the first release.
2. **Small, traceable patch set.** Prefer policies, built-in extensions, and chrome UI over deep engine changes. Every patch has a reason, an owner, and a test.
3. **Honest claims only.** No claim of anonymity or safety that is not tested. "No warning" never means "safe".
4. **Fail closed.** If a protection cannot be verified, block or clearly degrade; never silently fall back.
5. **Explain everything.** Every block, warning, and escalation shows the rule, the evidence, and a way to revert.
6. **Escalate automatically, de-escalate only by the user.**
7. **Local first.** Analysis happens on the device. Anything that leaves the device is opt-in and disclosed exactly.
8. **Every setting has a test.** If it cannot be tested, it does not ship as a promise.
9. **Updates are part of security.** Track upstream security releases quickly.

## 1.3 Goals (first usable release)

- A branded, usable Gecko-based desktop browser (tabs, address bar, bookmarks, history, downloads, settings).
- Security levels on three independent axes with per-Cell application.
- Tracker blocking, HTTPS-first/only, permission controls, disposable sessions.
- Optional Tor mode that **fails closed**, with a leak-test matrix.
- Link Guard (phishing warnings) and Download Inspector.
- Security panel showing **declared vs verified** protections.
- Tier 1 modules (Link Cleaner, Download Inspector, Session Sweeper, Site X-ray, Command Palette).
- Reproducible build, signed releases, documented update process.

## 1.4 Non-goals (first release)

- Writing a new rendering or JavaScript engine.
- Claiming Tor-Browser-level anonymity.
- A custom password vault, custom TLS stack, or custom crypto.
- Mobile apps.
- Built-in sync (research track only, after external review).
- Exploit, attack, or evasion tooling of any kind.
