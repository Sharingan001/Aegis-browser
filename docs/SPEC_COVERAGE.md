# Specification Coverage: Part 5.2 (Axis S - Surface Levels)

**Document Version:** 1.1.0  
**Date:** 2026-10-23  
**Status:** Living Verification Matrix (Phase 2a Corrected)  
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

## 3. Quantitative Summary by Status
* **Total Controls in Part 5.2:** 17
* **Behavior-tested:** 4 (JIT compilers, WebAssembly, WebGL, JavaScript S4 lockout)
* **Pref verified live:** 2 (HTTPS-only, Autoplay)
* **Config only:** 4 (Mixed content blocked, Cookie partitioning, Risky font rendering, Remote fonts)
* **Not yet:** 7 (HTTPS-first upgrade, Permission matrix, Protocol handlers, Downloads, Persistent storage, Extensions, Link Guard browser integration)
