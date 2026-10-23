# Specification Coverage: Part 5.2 (Axis S - Surface Levels)

**Document Version:** 1.0.0  
**Date:** 2026-10-23  
**Status:** Living Verification Matrix (Phase 2a)  
**Target Engine:** Mozilla Firefox ESR 153.5.1esr (Linux x86_64)

---

## 1. Summary of Surface Controls Status

| Row | Control Name | Target Levels | Implementation Mechanism | Status | Test / Verification Method |
| :---: | :--- | :---: | :--- | :---: | :--- |
| **1** | HTTPS-first (upgrade, fall back with prompt) | S1–S4: on | `dom.security.https_only_mode_*` defaults | **Implemented & Tested** | `tests/axes/test_surface_levels.py` (S1 runtime) |
| **2** | HTTPS-only (fallback needs explicit click) | S1: off<br/>S2–S4: on | `dom.security.https_only_mode` | **Implemented & Tested** | `test_s2_runtime_prefs` (Marionette live query: `true` in S2) |
| **3** | Mixed content blocked | S1–S4: on | `security.mixed_content.block_active_content` | **Implemented & Tested** | `test_surface_cumulativity` (locked `true` across all tiers) |
| **4** | Third-party storage partitioned | S1–S4: on | `network.cookie.cookieBehavior: 5` (dFPI) | **Implemented & Tested** | `prototypes/test_aegis.py` (`TestPSL`), cumulativity assertion |
| **5** | Autoplay | S1: allow muted<br/>S2: block audible<br/>S3–S4: block all | `media.autoplay.default` (1 = audible, 5 = all) | **Implemented & Tested** | `test_s2_runtime_prefs` (Marionette live query: 1 in S2, 5 in S3) |
| **6** | Notifications / location / camera / mic | S1–S2: ask<br/>S3–S4: deny | Permission policies & `permissions.default.*` | **Not Yet** | Slated for Phase 2c permission matrix |
| **7** | Dangerous protocol handlers | S1: prompt<br/>S2–S4: blocked | `network.protocol-handler.external.*` | **Not Yet** | Slated for Phase 2c external handler lockdown |
| **8** | Downloads | S1–S2: prompt<br/>S3–S4: quarantine | Download policy + Module M8 (Download Inspector) | **Not Yet** (Prototype Tested) | `prototypes/test_aegis.py` (`test_download_disguised_executable`); engine hook in Phase 3 |
| **9** | JIT compilers | S1–S2: on<br/>S3–S4: off | `javascript.options.baselinejit`, `javascript.options.ion` | **Implemented & Tested** | `test_s1_runtime_enforcement` (<60ms JIT bench), `test_s3_runtime_enforcement` (>=70ms interpreter) |
| **10** | WebAssembly | S1–S2: on<br/>S3–S4: off | `javascript.options.wasm` | **Implemented & Tested** | `test_s3_runtime_enforcement` (`typeof WebAssembly === "undefined"` in DOM) |
| **11** | WebGL / WebGPU | S1–S2: on<br/>S3–S4: off | `webgl.disabled` | **Implemented & Tested** | `test_s1_runtime_enforcement` (`webgl_null: false`), `test_s3_runtime_enforcement` (`webgl_null: true`) |
| **12** | Risky font/rendering (OT-SVG, MathML) | S1–S2: on<br/>S3–S4: off | `gfx.font_rendering.opentype_svg.enabled`, `mathml.disabled` | **Implemented & Tested** | `test_surface_cumulativity` + Marionette query |
| **13** | Remote (downloadable) fonts | S1–S3: on<br/>S4: off | `gfx.downloadable_fonts.enabled` | **Implemented & Tested** | `test_surface_cumulativity` (locked `false` in S4) |
| **14** | JavaScript | S1–S2: on<br/>S3: HTTPS-only<br/>S4: off by default | `javascript.enabled` (S4 static lock; per-origin allow-list planned) | **Implemented & Tested (S4 static)**<br/>*Per-origin allow-list Not Yet* | `test_s4_runtime_enforcement` & `test_tier_failclosed.py` (`<noscript>` beacon verified) |
| **15** | Persistent storage | S1–S2: on<br/>S3: session<br/>S4: none (RAM) | `privacy.sanitize.sanitizeOnShutdown`, RAM profile | **Not Yet** | Architecture specified in SPIKE-006; implementation in Phase 3 |
| **16** | Extensions | S1: allowed<br/>S2: vetted<br/>S3: built-in only<br/>S4: none | `ExtensionSettings` policy | **Not Yet** | Slated for Phase 2c |
| **17** | Link Guard thresholds | S1–S2: normal<br/>S3–S4: strict | `prototypes/linkguard_prototype.py` + Module M1 | **Implemented & Tested (Prototype)**<br/>*Browser IPC hand-off Not Yet* | 27 unit tests pass in `prototypes/test_aegis.py`; IPC protocol designed in SPIKE-006 |

---

## 2. Quantitative Implementation Summary
* **Total Controls in Part 5.2:** 17
* **Implemented & Verified at Runtime in Engine:** 9 (HTTPS-first, HTTPS-only, Mixed Content, Cookie Partitioning, Autoplay, JIT, WASM, WebGL, Fonts/MathML)
* **Implemented & Verified at Engine Process Boundary:** 1 (S4 Static JavaScript disablement via `<noscript>` beacon)
* **Implemented & Verified at Prototype Level:** 2 (Download Quarantine, Link Guard scoring)
* **Not Yet (Scheduled for Phase 2c / Phase 3):** 5 (Permission policies, dangerous handlers, persistent storage teardown, extension policy restrictions, browser-native IPC hand-off integration)
