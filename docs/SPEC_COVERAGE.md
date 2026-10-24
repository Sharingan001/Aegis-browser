# Specification Coverage: Part 5.2 (Surface Levels) and Part 5.3 (Identity Levels)

**Document Version:** 1.2.0  
**Date:** 2026-10-24  
**Status:** Living Verification Matrix (Phase 2c Complete)  
**Target Engine:** Mozilla Firefox ESR 153.5.1esr (Linux x86_64)

---

## 1. Status Definitions

Every row in Spec Part 5.2 is graded against exactly one of four rigorous verification statuses:
1. **Behavior-tested:** Proven at runtime via functional/behavioral execution probes (e.g. DOM API behavior, timing difference, noscript beacon).
2. **Pref verified live:** Proven effective by querying live in-memory engine preferences via Marionette (`Services.prefs`) in a running Firefox ESR instance.
3. **Config only:** Defined and locked in JSON tier files and compiled into `aegis.cfg`, but not yet verified with a live behavioral test.
4. **Not yet:** Not implemented or verified in the browser engine (or tested only in standalone Python prototypes without browser integration).

---

## 2. Part 5.2 Surface Controls Status

| Row | Control Name | Target Levels | Implementation Mechanism | Status | Test / Verification Method & Honest Assessment |
| :---: | :--- | :---: | :--- | :---: | :--- |
| **1** | HTTPS-first (upgrade, fall back with prompt) | S1–S4: on | `dom.security.https_first*` | **Not yet** | `dom.security.https_only_mode` is off in S1, but no test currently demonstrates HTTP->HTTPS upgrade behavior or verifies `https_first` prefs. |
| **2** | HTTPS-only (fallback needs explicit click) | S1: off<br/>S2–S4: on | `dom.security.https_only_mode` | **Pref verified live** | `test_s2_runtime_prefs` (Marionette live query proves pref is locked `true` in S2). |
| **3** | Mixed content blocked | S1–S4: on | `security.mixed_content.block_active_content` | **Config only** | Locked `true` in `aegis.cfg` across all tiers. Cumulativity tests verify inheritance, but no live mixed-content network test has been run. |
| **4** | Third-party storage partitioned | S1–S4: on | `network.cookie.cookieBehavior: 5` (dFPI) | **Config only** | Locked `5` in `aegis.cfg`. (Note: Python `TestPSL` tests PSL domain boundaries in python, not live Gecko cookie partitioning). |
| **5** | Autoplay | S1: allow muted<br/>S2: block audible<br/>S3–S4: block all | `media.autoplay.default` (1 = audible, 5 = all) | **Pref verified live** | `test_s2_runtime_prefs` (Marionette live query proves pref is locked to 1 in S2 and 5 in S3; no media playback probe run). |
| **6** | Notifications / location / camera / mic | S1–S2: ask<br/>S3–S4: deny | Permission policies & `permissions.default.*` | **Not yet** | Slated for Phase 2c permission matrix. |
| **7** | Dangerous protocol handlers | S1: prompt<br/>S2–S4: blocked | `network.protocol-handler.external.*` | **Not yet** | Slated for Phase 2c external handler lockdown. |
| **8** | Downloads | S1–S2: prompt<br/>S3–S4: quarantine | Download policy + Module M8 (Download Inspector) | **Not yet** | Evaluated in standalone Python prototype only (`test_download_disguised_executable`); zero browser integration. |
| **9** | JIT compilers | S1–S2: on<br/>S3–S4: off | `javascript.options.baselinejit`, `javascript.options.ion` | **Behavior-tested** | `test_s1_runtime_enforcement` (<60ms JIT bench), `test_s3_runtime_enforcement` (>=70ms interpreter execution). |
| **10** | WebAssembly | S1–S2: on<br/>S3–S4: off | `javascript.options.wasm` | **Behavior-tested** | `test_s3_runtime_enforcement` (DOM probe confirms `typeof WebAssembly === "undefined"` in S3). |
| **11** | WebGL / WebGPU | S1–S2: on<br/>S3–S4: off | `webgl.disabled` | **Behavior-tested** | `test_s1_runtime_enforcement` (`webgl_null: false`), `test_s3_runtime_enforcement` (`webgl_null: true`). |
| **12** | Risky font/rendering (OT-SVG, MathML) | S1–S2: on<br/>S3–S4: off | `gfx.font_rendering.opentype_svg.enabled`, `mathml.disabled` | **Config only** | Locked `false`/`true` in `aegis.cfg` for S3/S4. Cumulativity tests verify config inheritance, but no SVG-font or MathML rendering test run. |
| **13** | Remote (downloadable) fonts | S1–S3: on<br/>S4: off | `gfx.downloadable_fonts.enabled` | **Config only** | Locked `false` in `aegis.cfg` for S4. Cumulativity tests verify config inheritance, but no `@font-face` fallback test run. |
| **14** | JavaScript | S1–S2: on<br/>S3: HTTPS-only<br/>S4: off by default | `javascript.enabled` (S4 static lock; per-origin allow-list planned) | **Behavior-tested** | `test_s4_runtime_enforcement` & `test_tier_failclosed.py` (proves `<noscript>` beacon triggers and zero `<script>` execution in S4). Per-origin allow-list is Not Yet. |
| **15** | Persistent storage | S1–S2: on<br/>S3: session<br/>S4: none (RAM) | `privacy.sanitize.sanitizeOnShutdown`, RAM profile | **Not yet** | Architecture specified in SPIKE-006; Phase 3 implementation. |
| **16** | Extensions | S1: allowed<br/>S2: vetted<br/>S3: built-in only<br/>S4: none | `ExtensionSettings` policy | **Not yet** | Slated for Phase 2c. |
| **17** | Link Guard thresholds | S1–S2: normal<br/>S3–S4: strict | `prototypes/linkguard_prototype.py` + Module M1 | **Not yet** | Evaluated in standalone Python prototype only (`test_aegis.py`); zero browser integration. |

---

## 3. Part 5.3 Identity Controls Status (Phase 2c)

| Row | Control Name | Target Levels | Implementation Mechanism | Status | Test / Verification Method & Honest Assessment |
| :---: | :--- | :---: | :--- | :---: | :--- |
| **I-1** | Fingerprinting protection baseline | I1: off<br/>I3: FPP on<br/>I2/I4: RFP on | `privacy.fingerprintingProtection`, `privacy.resistFingerprinting` | **Behavior-tested** | `test_i1_runtime_enforcement`, `test_i2_runtime_enforcement`, `test_i3_runtime_enforcement`, `test_i4_runtime_enforcement` verify engine state. Phase 2b behavioral probe proved canvas/audio differences. |
| **I-2** | Remote overrides lockout | I1: off<br/>I3..I4: false | `privacy.fingerprintingProtection.remoteOverrides.enabled` | **Pref verified live** | `test_i3_runtime_enforcement` verifies remoteOverrides locked false in Marionette live query. |
| **I-3** | Timezone / locale / window geometry | I1: native<br/>I3: native (local TZ)<br/>I2/I4: UTC & letterbox | `privacy.resistFingerprinting`, `privacy.resistFingerprinting.letterboxing` | **Behavior-tested** | Phase 2b live probe confirmed `getTimezoneOffset() == 0` and letterboxing viewport snapping under RFP, and local timezone under FPP. |
| **I-4** | Timer precision reduction | I1: default<br/>I2..I4: reduced | `privacy.reduceTimerPrecision`, `privacy.resistFingerprinting.reduceTimerPrecision.microseconds` | **Pref verified live** | `test_i2_runtime_enforcement` verifies live clamp to 16667 microseconds under RFP. |
| **I-5** | Canvas / audio readback | I1: native<br/>I3: site-keyed noise<br/>I2/I4: normalized/constant | FPP canvas randomization (I3), RFP uniform canvas (I2/I4) | **Behavior-tested** | `test_fpp_per_target_override_changes_behavior` proves FPP per-target override switches noise behavior; Phase 2b probe measured canvas hash divergence. |
| **I-6** | Hardware concurrency & touch points | I1: native<br/>I3: native<br/>I2/I4: normalized | `privacy.resistFingerprinting` | **Behavior-tested** | Phase 2b probe confirmed RFP clamps `hardwareConcurrency: 2` and `maxTouchPoints: 0` (headless ESR 153.5.1). |
| **I-7** | High-entropy APIs (Gamepad) | I1..I3: on<br/>I4: off | `dom.gamepad.enabled` | **Pref verified live** | `test_i4_runtime_enforcement` verifies `dom.gamepad.enabled` is false in I4 and true in I1..I3. |
| **I-7** | High-entropy APIs (Gamepad) | NOT in I-axis | **REMOVED FROM I-AXIS** | Under S4 (JavaScript disabled), `navigator.getGamepads` and all script APIs are unreachable regardless of the `dom.gamepad.enabled` pref. Pref-gating it in I4 was security theater. Removed from I4 definition. |
| **I-8** | Referrer policy (trimmingPolicy) | I1: default<br/>I2..I4: origin cross-origin | `network.http.referer.trimmingPolicy: 2` | **Pref verified live** | `test_i1_runtime_enforcement` (0) and `test_i3_runtime_enforcement` (2) verify effective prefs via Marionette. |
| **I-9** | WebRTC local IP leak protection | I1: default<br/>I2..I4: no local host IP | `media.peerconnection.ice.no_host: true` | **Pref verified live** | `test_i1_runtime_enforcement` (false) and `test_i3_runtime_enforcement` (true) verify effective prefs via Marionette. |
| **I-10** | Accept-Language header normalization (I4) | I4 only | `intl.accept_languages: "en-US, en"` locked | **Pref verified live** | I4 locks Accept-Language to static value. `test_i4_runtime_enforcement` verifies `accept_lang` pref via Marionette. Behavioral test (header probe to local server) not yet run. |
| **I-11** | Remote font loading blocked (I4) | I4 only | `gfx.downloadable_fonts.enabled: false` locked | **Pref verified live** | I4 locks remote fonts off. `test_i4_runtime_enforcement` verifies `remote_fonts` pref via Marionette. Closes timing side channel and CSS glyph enumeration in static quarantine. |
| **I-12** | Cross-origin referrer XOriginPolicy (I4) | I4 only | `network.http.referer.XOriginPolicy: 2` locked | **Pref verified live** | I4 locks cross-origin referrer to origin-only. `test_i4_runtime_enforcement` verifies `xorigin_policy` pref via Marionette. |
| **I-13** | CSS media query normalization (`prefers-color-scheme`, `resolution`, `pointer`, `hover`) | I4 intended | No pref available in ESR 153 | **Not yet** | CSS media queries are passive non-script identity signals. No normalization possible without an engine patch. Tracked as VERIFY-I-010, Phase 3. |

---

## 4. Quantitative Summary by Status

> **Grade definitions (Axis I):**
> - **Behavior-tested:** A behavioral probe (DOM, timing, network probe) confirmed measurable effect in running engine.
> - **Pref verified live:** Marionette `Services.prefs` query confirmed pref set/locked in-memory. No independent behavioral exercise.
> - **Config only:** Defined in JSON and compiled into `aegis.cfg`; no live test run.
> - **Not yet:** Not implemented or verified at engine level.

* **Part 5.2 Surface Controls (17 total):**
  - **Behavior-tested:** 4 (JIT compilers, WebAssembly, WebGL, JavaScript S4 lockout)
  - **Pref verified live:** 2 (HTTPS-only, Autoplay)
  - **Config only:** 4 (Mixed content blocked, Cookie partitioning, Risky font rendering, Remote fonts)
  - **Not yet:** 7 (HTTPS-first upgrade, Permission matrix, Protocol handlers, Downloads, Persistent storage, Extensions, Link Guard browser integration)
* **Part 5.3 Identity Controls (13 rows, including I4 redefinition):**
  - **Behavior-tested:** 4 (FP baseline, Timezone/letterboxing under RFP, Canvas/audio divergence under FPP, Hardware/touch normalization under RFP)
  - **Pref verified live:** 6 (Remote overrides lockout, Timer precision, Referrer trimming, WebRTC no_host, Accept-Language I4, Remote fonts I4, XOriginPolicy I4) — note: 7 individual prefs across these rows
  - **Config only:** 0
  - **Not yet:** 1 (CSS media query normalization for I4, Phase 3)
  - **Removed:** 1 (Gamepad API — security theater under S4 JS-off)

