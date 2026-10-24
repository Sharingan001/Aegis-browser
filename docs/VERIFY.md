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
| VERIFY-S-001 | `dom.security.https_only_mode` | S2+ | VERIFIED (SET via autoconfig) | In aegis.cfg: locked true in S2, S3, S4 tiers. Verified in prefs. |
| VERIFY-S-002 | `dom.security.https_only_mode_ever_enabled` | S1+ | OPEN | Verify family of prefs |
| VERIFY-S-003 | `network.cookie.cookieBehavior` (partitioning value) | S1+ | VERIFIED (SET via autoconfig) | Value 5 (dFPI total cookie protection) locked in aegis.cfg baseline. |
| VERIFY-S-004 | `media.autoplay.default` | S2/S3 | VERIFIED (SET via autoconfig) | In aegis.cfg: locked 1 (block audible) in S2; locked 5 (block all) in S3/S4. |
| VERIFY-S-005 | Permission policy prefs (notifications, location, camera, mic) | S2/S3/S4 | OPEN | Verify pref names for default-deny behavior |
| VERIFY-S-006 | Protocol handler policy | S2+ | OPEN | Verify policy/pref name for dangerous handler blocking |
| VERIFY-S-007 | `javascript.options.baselinejit` | S3/S4 | VERIFIED (EFFECTIVE via autoconfig) | In policies.json: REJECTED by ESR 153 for stability reasons. In aegis.cfg: VERIFIED EFFECTIVE via lockPref; execution bench showed 103ms vs 27ms JIT on S1. |
| VERIFY-S-008 | `javascript.options.ion` | S3/S4 | VERIFIED (EFFECTIVE via autoconfig) | In policies.json: REJECTED by ESR 153 for stability reasons. In aegis.cfg: VERIFIED EFFECTIVE via lockPref. |
| VERIFY-S-009 | `javascript.options.wasm` | S3/S4 | VERIFIED (EFFECTIVE via autoconfig) | In policies.json: REJECTED by ESR 153 for stability reasons. In aegis.cfg: VERIFIED EFFECTIVE via lockPref; typeof WebAssembly is undefined in DOM on S3/S4. |
| VERIFY-S-010 | `webgl.disabled` | S3/S4 | VERIFIED (EFFECTIVE via autoconfig) | In policies.json: REMOVED to avoid global conflict with S1/S2. In aegis.cfg: default false in S1/S2; locked true in S3/S4. getContext("webgl") returns null in S3/S4. |
| VERIFY-S-011 | WebGPU pref name | S3/S4 | OPEN | Spec says "WebGPU pref" - find actual pref name in ESR 153 |
| VERIFY-S-012 | `gfx.font_rendering.opentype_svg.enabled` | S3/S4 | VERIFIED (SET via autoconfig) | Locked false in aegis.cfg for S3/S4. |
| VERIFY-S-013 | `mathml.disabled` | S3/S4 | VERIFIED (SET via autoconfig) | Locked true in aegis.cfg for S3/S4. |
| VERIFY-S-014 | `gfx.downloadable_fonts.enabled` | S4 | VERIFIED (SET via autoconfig) | Locked false in aegis.cfg for S4 minimal surface. |
| VERIFY-S-015 | Extension policy (built-in only in S3, none in S4) | S3/S4 | OPEN | Verify enterprise policy key name in ESR 153 |
| VERIFY-S-016 | Download policy (quarantine, no auto-open) | S3/S4 | OPEN | Verify mechanism in ESR 153 |
| VERIFY-S-017 | Policy key `HttpsOnlyMode` | S2+ | VERIFIED (REMOVED from policies.json) | Removed from policies.json to avoid locking S1. Enforced per-tier via `dom.security.https_only_mode` in aegis.cfg (false in S1; locked true in S2+). |
| VERIFY-S-018 | Policy key `DisableTelemetry` | all | VERIFIED (SET via policy) | In policies.json: ACCEPTED. about:policies shows DisableTelemetry=true. |
| VERIFY-S-019 | Policy key `EnableTrackingProtection` with `Fingerprinting` + `Cryptomining` | all | VERIFIED (SET via policy) | In policies.json: ACCEPTED. about:policies shows EnableTrackingProtection with Value=true, Locked=true. |
| VERIFY-S-020 | Policy key `DNSOverHTTPS` with `Locked` flag | N1 | OPEN | Removed from global policies.json to allow direct DNS in N0; reserved for N1 tier-specific configuration. |
| VERIFY-S-021 | Autoconfig mechanism: `autoconfig.js` + `.cfg` file | all | VERIFIED (EFFECTIVE) | Confirmed functional in ESR 153; successfully applies lockPref calls for prefs restricted by policies.json. |
| VERIFY-S-022 | Autoconfig sandbox: check whether `getenv` or profile path inspection is available | S-axis | VERIFIED (EFFECTIVE via getenv and getPref) | In ESR 153 with `general.config.sandbox_enabled: true`, XPCOM (`Components` & `Services`) is strictly undefined in the autoconfig sandbox (correcting earlier spike finding where env var masked XPCOM failure). `getenv('AEGIS_SURFACE_TIER')` is natively available in the sandbox. Profile-level tier selection is read via `getPref('aegis.profile.tier')` (populated from profile `user.js` before cfg evaluation). Proven effective at runtime with zero environment variable present. |
| VERIFY-S-023 | `javascript.enabled` | S4 | VERIFIED (EFFECTIVE via autoconfig) | Locked false in S4 tier and fail-closed state. Proven effective at runtime via `<noscript>` beacon triggering and zero `<script>` execution. |
| VERIFY-S-024 | `media.peerconnection.enabled` | S4 | VERIFIED (SET via autoconfig) | Locked false in aegis.cfg for S4 minimal surface. |

---

## Axis I: Identity level preferences

**Status definitions:**
- **VERIFIED (EFFECTIVE):** A behavioral test (DOM probe, timing check, network probe) confirmed the protection has a measurable effect in the running engine. This is the highest grade.
- **VERIFIED (SET):** A live Marionette chrome-context query (`Services.prefs`) confirmed the pref is set/locked to the expected value in-memory. The pref was not independently exercised at the behavioral level beyond the query itself.
- **OPEN:** Not yet verified against the pinned ESR.

| ID | Pref / Policy name | Axis level | Status | Notes |
|---|---|---|---|---|
| VERIFY-I-001 | `privacy.resistFingerprinting` | I2/I4 | VERIFIED (EFFECTIVE) | Behavioral: Phase 2b probe confirmed UTC timezone spoofing (`getTimezoneOffset() == 0`), rounded viewport geometry, and timer clamping to ~16.67ms. `test_i2_runtime_enforcement` (Marionette) confirms pref locked true. Resembles Tor Browser defaults, unmeasured crowd. |
| VERIFY-I-002 | `privacy.fingerprintingProtection` and sub-prefs | I3 | VERIFIED (EFFECTIVE) | Behavioral: Phase 2b probe confirmed canvas hash divergence between origins. `test_i3_runtime_enforcement` (Marionette) confirms FPP locked true, remoteOverrides locked false (D-012). `test_fpp_per_target_override_changes_behavior` confirms live override switching. |
| VERIFY-I-003 | `privacy.resistFingerprinting.letterboxing` | I2/I4 | VERIFIED (SET) | Marionette query confirmed pref locked true in I2/I4. Behavioral test (viewport quantization measurement) not yet run; labeled VERIFIED (SET) only. |
| VERIFY-I-004 | Timer precision reduction: `privacy.reduceTimerPrecision` + RFP | I2+ | VERIFIED (EFFECTIVE) | Behavioral: Phase 2b probe confirmed timer clamping to 16.667ms frame-rate steps under RFP. Marionette confirms `privacy.reduceTimerPrecision: true`. |
| VERIFY-I-005 | Canvas seeded noise: FPP `EfficientCanvasRandomization` target | I3 | VERIFIED (EFFECTIVE) | Behavioral: Phase 2b probe measured canvas hash divergence between sites under I3 FPP. Container test confirmed noise is keyed by site principal, NOT by `userContextId` (documented in A-002). |
| VERIFY-I-006 | `media.peerconnection.ice.no_host` | I2/I3/I4 | VERIFIED (SET) | Marionette query confirmed pref locked true in I2, I3, I4. Behavioral test (actual WebRTC ICE candidate inspection) not yet run; labeled VERIFIED (SET) only. |
| VERIFY-I-007 | `network.http.referer.trimmingPolicy` | I2/I3/I4 | VERIFIED (SET) | Marionette query confirmed value 2 (origin only cross-origin) in I2, I3, I4. Behavioral test (measured Referer header in HTTP request) not yet run; labeled VERIFIED (SET) only. |
| VERIFY-I-008 | `intl.accept_languages` normalization | I4 | VERIFIED (SET) | I4 locks `intl.accept_languages: "en-US, en"`. Marionette query verifies pref value. Behavioral test (header probe to local server) not yet run; labeled VERIFIED (SET) only. |
| VERIFY-I-009 | `gfx.downloadable_fonts.enabled` disabled in I4 | I4 | VERIFIED (SET) | I4 locks `gfx.downloadable_fonts.enabled: false`. Marionette query verifies pref. Behavioral test (@font-face fallback probe) not yet run; labeled VERIFIED (SET) only. Rationale: closes remote-font timing side channel and CSS glyph enumeration in static quarantine. |
| VERIFY-I-009b | `network.http.referer.XOriginPolicy` | I4 | VERIFIED (SET) | I4 locks `network.http.referer.XOriginPolicy: 2` (origin only on cross-origin). Marionette query verifies pref. |
| VERIFY-I-010 | CSS media query normalization (`prefers-color-scheme`, `resolution`, `pointer`, `hover`) | I4 | OPEN | CSS media query values are emitted passively and are a non-script identity signal. No pref in ESR 153 normalizes these. Normalization requires a patch not yet available. Tracked for Phase 3. |

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
| SPIKE-002 | I3 seeded noise: evaluate `privacy.fingerprintingProtection` sub-prefs in ESR 153 for native seeded canvas/audio noise before building custom implementation. | Phase 2 | RESOLVED (Phase 2b report, D-012) |
| SPIKE-003 | Which S levels are acceptable in Tor mode after crowd-analysis measurements (spec R2 rule)? | Phase 3/R | OPEN |
| SPIKE-004 | Per-Cell Tor circuit isolation: supported by existing proxy mechanisms or requires engine patch? | Phase 4 | OPEN |
| SPIKE-005 | Instance-wide autoconfig vs per-Cell Surface levels: evaluate process-per-tier, per-profile autoconfig (VERIFY-S-022), Tor-style restart, and engine patches (D-008). | Phase 2 | OPEN |

---
