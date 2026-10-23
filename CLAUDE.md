# Aegis Browser: project rules (read first, every session)

Project: "Aegis Browser", a desktop browser on Gecko (Firefox ESR base) with multi-level
security, isolated Cells, phishing protection, and modules.
Spec: docs/spec/INDEX.md lists one file per Part of the master blueprint. Read only the
Parts the current phase needs (see docs/PHASE_READING.md). Full text: docs/MASTER.md.
Prototype code and tests: prototypes/ (run: python3 -m unittest test_aegis).

## Hard constraints
1. No Chromium, Blink, Electron, CEF, or Chromium WebView.
2. No custom browser engine, TLS, cryptography, or password vault.
3. Order of preference: enterprise policies/locked prefs -> built-in WebExtensions ->
   chrome UI -> engine patches (numbered in upstream/patches/, each with reason + test).
4. Web content is untrusted; never expose privileged APIs to it. Services consume
   structured events only.
5. Fail closed. Never silently fall back (especially in Tor mode).
6. Every control needs an enforcement test that runs against the running browser.
7. Local-first, no telemetry. Off-device data is opt-in and disclosed.
8. Honest claims: never say "anonymous" or "safe". HTTPS is not safety; no warning is not safe.
9. Automatic protection changes may only escalate; only the user may lower protection.
10. Warnings and trust indicators live in Aegis chrome, never in page space.
11. No exploit, attack, evasion, or malware functionality. Lab modules observe, scope, document.
12. Never browse live phishing/malicious sites to test. Use offline datasets, local mock pages.
13. Verify every Firefox pref/policy/API name against the pinned ESR version; mark VERIFY.

## Working rules
- One phase per session. Start by stating the goal, files to change, open questions.
- Small commits. Run tests after each change and show exact results. Never claim a test
  passed unless you ran it. Say what you did NOT test.
- Maintain docs/DECISIONS.md (what/why/alternatives/date) and docs/VERIFY.md (unverified items).
- Ask me before: large downloads, long builds, installing system packages, deleting files,
  or any decision the spec does not settle.
- If the spec is wrong or ambiguous, say so plainly and propose a fix.
- End every step with: what you did, files changed, tests + results, not tested, decisions
  needed, next step.

## Pinned ESR version
Firefox ESR **153.5.1** (confirmed 2026-10-23 from https://www.mozilla.org/en-US/firefox/organizations/all/)
All VERIFY items are checked against this version.

## Fast-path setup (Phase 0)
- Firefox ESR tarball extracted to `firefox-esr/` (NOT installed system-wide).
- Profile launched with: `firefox-esr/firefox -profile profiles/aegis-fastpath --no-remote`
- Policies file: `firefox-esr/distribution/policies.json`
- Autoconfig: `firefox-esr/defaults/pref/autoconfig.js` + `firefox-esr/aegis.cfg`
- Do NOT replace or modify system Firefox 156.

## Output format (every step)
1. What you did (short).
2. Files created/changed.
3. Tests run and exact results.
4. What you did NOT test or could not verify.
5. Decisions needed from me.
6. Next step.
