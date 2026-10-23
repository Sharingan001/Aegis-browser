# Aegis Browser - VERIFY Log

All unverified preferences, policies, and APIs must appear here before they are used in
code or config. Status: OPEN (not yet verified), VERIFIED (checked against pinned ESR),
RESOLVED (implemented and tested).

**Pinned ESR:** Firefox 153.5.1esr  
**Source for verification:** Mozilla policy templates, about:config, and Firefox source docs
at https://firefox-source-docs.mozilla.org/ - always against the 153 ESR tag.

---

## ESR Version

| ID | Item | Status | Notes |
|---|---|---|---|
| VERIFY-ESR-001 | Firefox ESR current version = 153.5.1 | VERIFIED | Confirmed 2026-10-23 from Mozilla organizations/all/ (data-esr-versions="153.5.1"). Tarball SHA-256 e289bdc532decf2b54dea9b5ac64cf6f84a62eeec4d4a9ec2f69590f61b0ff1c verified against SHA256SUMS. GPG detached signature SHA256SUMS.asc verified using Mozilla Software Releases key (Primary Fingerprint: 14F2 6682 D091 6CDD 81E3 7B6D 61B7 B526 D98F 0353, Subkey: 827E 6586 0867 9618 CD34 9F93 678E 455D 7676 7AA3). Signing key fingerprint compared against official Mozilla support page: https://support.mozilla.org/en-US/kb/authenticate-firefox-architecture-integrity |

---

## Axis S: Surface level preferences

All policy/pref names below are from spec Part 5.2 and must be verified against ESR 153.

| ID | Pref / Policy name | Axis level | Status | Notes |
|---|---|---|---|---|
| VERIFY-S-001 | `dom.security.https_only_mode` | S2+ | OPEN | Verify exists and behavior in ESR 153 |
| VERIFY-S-002 | `dom.security.https_only_mode_ever_enabled` | S1+ | OPEN | Verify family of prefs |
| VERIFY-S-003 | `network.cookie.cookieBehavior` (partitioning value) | S1+ | OPEN | Verify correct integer value for dFPI in ESR 153 |
| VERIFY-S-004 | `media.autoplay.*` prefs (block audible / block all) | S2/S3 | OPEN | Verify correct pref names and values |
| VERIFY-S-005 | Permission policy prefs (notifications, location, camera, mic) | S2/S3/S4 | OPEN | Verify pref names for default-deny behavior |
| VERIFY-S-006 | Protocol handler policy | S2+ | OPEN | Verify policy/pref name for dangerous handler blocking |
| VERIFY-S-007 | `javascript.options.baselinejit` | S3/S4 | VERIFIED (EFFECTIVE via autoconfig) | In policies.json: REJECTED by ESR 153 for stability reasons. In aegis.cfg: VERIFIED EFFECTIVE via lockPref; execution bench showed 105ms vs 10ms control (interpreter fallback). |
| VERIFY-S-008 | `javascript.options.ion` | S3/S4 | VERIFIED (EFFECTIVE via autoconfig) | In policies.json: REJECTED by ESR 153 for stability reasons. In aegis.cfg: VERIFIED EFFECTIVE via lockPref. |
| VERIFY-S-009 | `javascript.options.wasm` | S3/S4 | VERIFIED (EFFECTIVE via autoconfig) | In policies.json: REJECTED by ESR 153 for stability reasons. In aegis.cfg: VERIFIED EFFECTIVE via lockPref; typeof WebAssembly is undefined in DOM. |
| VERIFY-S-010 | `webgl.disabled` | S3/S4 | VERIFIED (EFFECTIVE via policy) | In policies.json Preferences: ACCEPTED & LOCKED. getContext("webgl") returns null; stderr logs WebGL is currently disabled. |
| VERIFY-S-011 | WebGPU pref name | S3/S4 | OPEN | Spec says "WebGPU pref" - find actual pref name in ESR 153 |
| VERIFY-S-012 | `gfx.font_rendering.opentype_svg.enabled` | S3/S4 | OPEN | Verify pref name in ESR 153 |
| VERIFY-S-013 | `mathml.disabled` | S3/S4 | OPEN | Verify pref name in ESR 153 |
| VERIFY-S-014 | `gfx.downloadable_fonts.enabled` | S4 | OPEN | Verify pref name in ESR 153 |
| VERIFY-S-015 | Extension policy (built-in only in S3, none in S4) | S3/S4 | OPEN | Verify enterprise policy key name in ESR 153 |
| VERIFY-S-016 | Download policy (quarantine, no auto-open) | S3/S4 | OPEN | Verify mechanism in ESR 153 |
| VERIFY-S-017 | Policy key `HttpsOnlyMode` | S1+ | VERIFIED (SET via policy) | In policies.json: ACCEPTED. about:policies shows HttpsOnlyMode="force_enabled". |
| VERIFY-S-018 | Policy key `DisableTelemetry` | all | VERIFIED (SET via policy) | In policies.json: ACCEPTED. about:policies shows DisableTelemetry=true. |
| VERIFY-S-019 | Policy key `EnableTrackingProtection` with `Fingerprinting` + `Cryptomining` | all | VERIFIED (SET via policy) | In policies.json: ACCEPTED. about:policies shows EnableTrackingProtection with Value=true, Locked=true. |
| VERIFY-S-020 | Policy key `DNSOverHTTPS` with `Locked` flag | N1 | VERIFIED (SET via policy) | In policies.json: ACCEPTED. about:policies shows DNSOverHTTPS with Enabled=true, Locked=true. |
| VERIFY-S-021 | Autoconfig mechanism: `autoconfig.js` + `.cfg` file | all | VERIFIED (EFFECTIVE) | Confirmed functional in ESR 153; successfully applies lockPref calls for prefs restricted by policies.json. |
| VERIFY-S-022 | Autoconfig sandbox: check whether `getenv` or profile path inspection is available | S-axis | VERIFIED (EFFECTIVE) | Verified on ESR 153 runtime: `getenv('AEGIS_SURFACE_TIER')` and `Components.classes['@mozilla.org/process/environment;1']` work inside aegis.cfg. Reading a tier file from profile directory via `Services.dirsvc.get('ProfD', Components.interfaces.nsIFile)` also works. Proven effective by disabling WASM/JIT conditionally on S3 while keeping S1 enabled. |

---

## Axis I: Identity level preferences

| ID | Pref / Policy name | Axis level | Status | Notes |
|---|---|---|---|---|
| VERIFY-I-001 | `privacy.resistFingerprinting` | I2+ | OPEN | Verify behavior in ESR 153 vs the newer fingerprintingProtection prefs |
| VERIFY-I-002 | `privacy.fingerprintingProtection` and sub-prefs | I2+ | OPEN | Spec says "evaluate both before choosing"; do this in Phase 2 |
| VERIFY-I-003 | Letterboxing / window size normalization pref name | I2 | OPEN | Part of resist-fingerprinting; verify sub-feature pref if any |
| VERIFY-I-004 | Timer precision reduction pref | I2+ | OPEN | Verify pref name in ESR 153 |
| VERIFY-I-005 | Canvas / audio readback normalization: is seeded noise available natively? | I3 | OPEN | Phase 2 evaluation required - SPIKE-002 |
| VERIFY-I-006 | `media.peerconnection.*` prefs for WebRTC local-IP leak | I2+ | OPEN | Verify exact pref names in ESR 153 |
| VERIFY-I-007 | `network.http.referer.*` prefs for referrer trimming | I2+ | OPEN | Verify pref names in ESR 153 |
| VERIFY-I-008 | `intl.accept_languages` handling for language header normalization | I2+ | OPEN | Verify mechanism in ESR 153 |
| VERIFY-I-009 | High-entropy API prefs: gamepad, sensors, media-device enumeration, battery, speech voices | I4 | OPEN | Spec says "VERIFY each"; find individual pref names in ESR 153 |

---

## Axis N: Network level preferences

| ID | Pref / Policy name | Axis level | Status | Notes |
|---|---|---|---|---|
| VERIFY-N-001 | `network.proxy.type` values | N2/N3 | OPEN | Verify correct integer values for SOCKS in ESR 153 |
| VERIFY-N-002 | `network.proxy.socks` and `network.proxy.socks_port` | N2/N3 | OPEN | Verify pref names in ESR 153 |
| VERIFY-N-003 | `network.proxy.socks_remote_dns` | N2/N3 | OPEN | Critical for Tor - verify pref name and that remote DNS works in ESR 153 |
| VERIFY-N-004 | `network.trr.mode` (strict mode value) | N1 | OPEN | Verify correct integer for strict DoH (no plaintext fallback) in ESR 153 |
| VERIFY-N-005 | Proxy bypass list emptying mechanism | N2/N3 | OPEN | Verify how to ensure no bypass in ESR 153 |

---

## Open design spikes (not VERIFY items, but tracked here)

| ID | Spike | Phase | Status |
|---|---|---|---|
| SPIKE-001 | S4 per-origin JavaScript control: system extension with privileges vs engine patch. Compare options, risks, recommendation. | Phase 2 | OPEN |
| SPIKE-002 | I3 seeded noise: evaluate `privacy.fingerprintingProtection` sub-prefs in ESR 153 for native seeded canvas/audio noise before building custom implementation. | Phase 2 | OPEN |
| SPIKE-003 | Which S levels are acceptable in Tor mode after crowd-analysis measurements (spec R2 rule)? | Phase 3/R | OPEN |
| SPIKE-004 | Per-Cell Tor circuit isolation: supported by existing proxy mechanisms or requires engine patch? | Phase 4 | OPEN |
| SPIKE-005 | Instance-wide autoconfig vs per-Cell Surface levels: evaluate process-per-tier, per-profile autoconfig (VERIFY-S-022), Tor-style restart, and engine patches (D-008). | Phase 2 | OPEN |

---
