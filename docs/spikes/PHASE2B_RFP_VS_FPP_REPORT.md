# Phase 2b Empirical Evaluation: `privacy.resistFingerprinting` (RFP) vs `privacy.fingerprintingProtection` (FPP) on Firefox ESR 153.5.1

**Date:** 2026-10-23 (corrected 2026-10-24)  
**Target Engine:** Firefox ESR 153.5.1esr (x86_64 Linux)  
**Status:** Report Only (No design decisions; no architectural changes)  
**Test Environment:** Offline local test server (`http://127.0.0.1:port/axes/test_fp_surface.html`)  
**Test Mode:** `--headless` (no window manager)

> [!IMPORTANT]
> **Repository is PUBLIC.** All host-specific values (GPU model, CPU core count, timezone,
> display resolution) are redacted in this report and replaced with `<REDACTED_*>` placeholders.
> Raw probe data is stored in `tests/fixtures/output/probe_results_summary.json` which is
> `.gitignore`d and never committed.

---

## 1. Executive Summary & Preference Architecture

Firefox ESR 153.5.1 implements two distinct, parallel anti-fingerprinting subsystems derived from Gecko's `RFPTargetConstants`:

1. **`privacy.resistFingerprinting` (RFP)**:
   - The Tor Browser-derived defense model.
   - Activates `AllTargets` across 80 targets (`RFPTargetConstants.sys.mjs`), including: UTC timezone spoofing, fixed viewport stepping, per-extraction canvas noise, WebGL vendor/renderer sanitization to `"Mozilla"`, hardware concurrency clamping, and timer precision reduction with jitter.
   - Designed for an *anonymity set* where all clients present identical surface attributes.
   - **Scope:** Process/instance-wide.
   - **Source:** [`toolkit/components/resistfingerprinting/RFPTargets.inc`](https://searchfox.org/mozilla-esr153/source/toolkit/components/resistfingerprinting/RFPTargets.inc), [`nsRFPService.cpp`](https://searchfox.org/mozilla-esr153/source/toolkit/components/resistfingerprinting/nsRFPService.cpp).

2. **`privacy.fingerprintingProtection` (FPP)**:
   - Mozilla's modern WebCompat-conscious protection family.
   - Activates a selective subset of targets. In ESR 153 the desktop defaults are (from `RFPTargetConstants.sys.mjs`):
     ```
     DefaultTargetsFPP.DESKTOP_DEFAULT = [
       "CanvasRandomization", "EfficientCanvasRandomization",
       "FontVisibilityLangPack", "JSMathFdlibm",
       "ScreenAvailToResolution", "NavigatorHWConcurrencyTiered",
       "MaxTouchPointsCollapse"
     ]
     ```
   - Leaves timezone, locale, audio, WebGL unmasked vendor/renderer, window sizes, platform, and oscpu unaltered.
   - Per-target override pref: **`privacy.fingerprintingProtection.overrides`** — accepts a comma-separated string of `+TargetName` (add) and `-TargetName` (remove) modifiers applied on top of `DefaultTargetsFPP`. Example:
     ```
     "+JSDateTimeUTC,+NavigatorHWConcurrency,-EfficientCanvasRandomization"
     ```
   - Per-origin overrides: **`privacy.fingerprintingProtection.granularOverrides`** — JSON array for domain-specific target adjustments.
   - Remote overrides: **`privacy.fingerprintingProtection.remoteOverrides.enabled`** (default `true`) — fetches domain-specific web-compat rules via Mozilla RemoteSettings. **Aegis locks this to `false` (D-012).**
   - **Source:** [`FingerprintingWebCompatService.sys.mjs`](https://searchfox.org/mozilla-esr153/source/toolkit/components/resistfingerprinting/FingerprintingWebCompatService.sys.mjs), [`modules/RFPTargetConstants.sys.mjs`](extracted from `omni.ja`).
   - **Scope:** Process/instance-wide.

---

## 2. Empirical Measurement Matrix (ESR 153.5.1, headless mode)

Measurements were taken using `tests/fixtures/axes/test_fp_surface.html` served over HTTP on `127.0.0.1` in `--headless` mode. Each configuration was run twice to check cross-run stability.

> [!NOTE]
> Rows marked **(headless only)** reflect values that may differ under a real window manager.
> Window dimensions, screen dimensions, devicePixelRatio, and WebGL rendering are all affected
> by headless mode's virtual framebuffer. These values must be re-verified with a real display
> before any production conclusions.

| Dimension | Baseline (ESR 153 Default) | RFP (`privacy.resistFingerprinting: true`) | FPP (`privacy.fingerprintingProtection: true`) | RFP Source |
| :--- | :--- | :--- | :--- | :--- |
| **Canvas 2D Hash Stability** | Stable within session; consistent across identical canvases | **Unstable across consecutive reads** (randomized noise per `.toDataURL()` / `.getImageData()`) | **Stable within session/origin** (deterministic origin-keyed seed) | `CanvasRandomization` (target 9) |
| **Canvas Cross-Run Hash** | Varies (baseline `EfficientCanvasRandomization` active) | Varies (fresh random noise) | Varies across fresh profiles; stable per origin within session | `EfficientCanvasRandomization` (target 76) |
| **Web Audio PCM Hash** | Deterministic across all configs | Identical to Baseline | Identical to Baseline | `AudioContext` (target 49) — applies to real-time, not offline rendering |
| **Timer: Default `perf.now()` Step** | 1 ms (`privacy.reduceTimerPrecision: true`, `microseconds=1000`) | **~16.667 ms** (frame-rate clamping via `ReduceTimerPrecision` target, default `microseconds=1000` + jitter) | 1 ms (inherits baseline `reduceTimerPrecision`) | `ReduceTimerPrecision` (target 35); `privacy.resistFingerprinting.reduceTimerPrecision.microseconds` (default: **1000 μs**, i.e. 1 ms pref value; effective clamping is ~16.667 ms due to RFP-specific quantization logic) |
| **Timer: Configured 100ms Step** | N/A | **100 ms** (when `microseconds=100000` is set; Tor Browser default) | N/A | Same target; different pref value |
| **Window Dimensions (headless only)** | `<REDACTED_DISPLAY_W>` × `<REDACTED_DISPLAY_H_MINUS_CHROME>` | **1200 × 600** (clamped/rounded to fixed steps) | `<REDACTED_DISPLAY_W>` × `<REDACTED_DISPLAY_H_MINUS_CHROME>` | `WindowOuterSize` (target 26), `RoundWindowSize` (target 47) |
| **Screen Dimensions (headless only)** | `<REDACTED_DISPLAY_W>` × `<REDACTED_DISPLAY_H>` | **1200 × 600** (clamped to window size) | `<REDACTED_DISPLAY_W>` × `<REDACTED_DISPLAY_H>` | `ScreenRect` (target 30), `ScreenAvailRect` (target 31) |
| **Device Pixel Ratio (headless only)** | 1 | **2** (spoofed) | 1 | `WindowDevicePixelRatio` (target 41) |
| **Letterboxing** | None | Gray margin bars when `letterboxing=true` | None | `RFPHelper.sys.mjs` → `letterboxing.css` |
| **Timezone (`Intl`)** | `<REDACTED_TZ>` | **`Atlantic/Reykjavik` (UTC)** | `<REDACTED_TZ>` | `JSDateTimeUTC` (target 22) |
| **Timezone Offset** | `<REDACTED_TZ_OFFSET>` | **0** | `<REDACTED_TZ_OFFSET>` | Same target |
| **`navigator.userAgent`** | `Mozilla/5.0 (X11; Linux x86_64; rv:153.0) Gecko/20100101 Firefox/153.0` | **Same** (Linux string preserved in ESR 153) | **Same** | `NavigatorUserAgent` (target 19) — active but does not alter UA string on Linux in ESR 153 |
| **`navigator.platform`** | `Linux x86_64` | **Same** | **Same** | `NavigatorPlatform` (target 18) — not spoofed on Linux |
| **`navigator.oscpu`** | `Linux x86_64` | **Same** | **Same** | `NavigatorOscpu` (target 17) |
| **`navigator.appVersion`** | `5.0 (X11)` | **Same** | **Same** | `NavigatorAppVersion` (target 14) |
| **HTTP `User-Agent` Header** | `Mozilla/5.0 (X11; Linux x86_64; rv:153.0) Gecko/20100101 Firefox/153.0` | **Same** | **Same** | `HttpUserAgent` (target 25) |
| **HTTP `Accept-Language` Header** | `en-US,en;q=0.9` | **Same** (`en-US,en;q=0.9`) | **Same** | `JSLocale` (target 13) enforces `en-US` but does not alter Accept-Language header format on this locale |
| **HTTP Header Order** | `Host, User-Agent, Accept, Accept-Language, Accept-Encoding, Connection, Referer, Sec-Fetch-Dest, Sec-Fetch-Mode, Sec-Fetch-Site, Priority` | **Same order** | **Same order** | No header reordering target in RFP |
| **`navigator.language`** | `en-US` | **`en-US`** (enforced) | `en-US` (host setting) | `JSLocale` (target 13) |
| **Hardware Concurrency** | `<REDACTED_CORES>` | **4** (clamped; re-verified 2026-10-24) | **8** (tiered via `NavigatorHWConcurrencyTiered`) | `NavigatorHWConcurrency` (target 16) |
| **Max Touch Points** | 0 | **5** (spoofed; re-verified 2026-10-24) | 0 | `MaxTouchPointsCollapse` (target 73) for FPP; `MaxTouchPoints` (target 72) for RFP |
| **WebGL Unmasked Vendor (headless only)** | `<REDACTED_GPU_VENDOR>` | **`"Mozilla"`** | `<REDACTED_GPU_VENDOR>` | `WebGLRenderInfo` (target 60), `WebGLVendorSanitize` (target 77) |
| **WebGL Unmasked Renderer (headless only)** | `<REDACTED_GPU_MODEL>` | **`"Mozilla"`** | `<REDACTED_GPU_MODEL>` | Same targets |
| **Remote Overrides** | None | None | **Queries Mozilla RemoteSettings** unless disabled | `FingerprintingWebCompatService.sys.mjs` |

### Re-verification Notes (2026-10-24)

The following values were **re-verified** by navigating to a local HTTP page via Marionette and reading DOM properties from the web content context:

| Property | RFP Default Value | Verification Method |
| :--- | :--- | :--- |
| `navigator.hardwareConcurrency` | **4** | Page-loaded JS (in-page execution, not Marionette-injected) |
| `navigator.maxTouchPoints` | **5** | Same |
| `window.devicePixelRatio` | **2** | Same |
| `performance.now()` default step | **~16.667 ms** (frame-rate clamping) | Page-loaded JS; pref `microseconds=1000` (the default); the 100ms figure was from a manually-configured test with `microseconds=100000` |

> [!NOTE]
> RFP spoofing targets apply to the web content execution context's native JS objects.
> When Marionette injects scripts into the content context, some RFP targets (notably timezone
> via `JSDateTimeUTC`) do not apply to the injected evaluation. All timezone findings in this
> report are from in-page JavaScript execution, not Marionette-injected scripts.

---

## 3. Detailed Dimension Analysis

### A. Canvas Readback & Randomization
- **RFP Mechanism:** Uses `CanvasRandomization` (target 9). Every `.toDataURL()` or `.getImageData()` call applies pseudo-random noise, producing different hashes on every extraction — even consecutive reads of the same canvas (`repeatSameCanvasStable: false`). Source: [`nsRFPService.cpp`](https://searchfox.org/mozilla-esr153/source/toolkit/components/resistfingerprinting/nsRFPService.cpp).
- **FPP Mechanism:** Uses `EfficientCanvasRandomization` (target 76). Derives a deterministic perturbation salt per first-party origin per session. Within a page, identical canvases yield identical hashes (`repeatSameCanvasStable: true`), but tracking across first-party origins produces different hashes. Source: Same file, gated by target flag.

### B. Audio Readback
- `OfflineAudioContext` PCM rendering (triangle oscillator + dynamics compressor) produces identical float buffers across Baseline, RFP, and FPP on this system. The `AudioContext` RFP target (49) applies to real-time audio context properties (sample rate, latency), not offline deterministic rendering.

### C. Timer Precision & Quantization
- **Baseline:** `privacy.reduceTimerPrecision: true` + `unconditional: true` (Spectre mitigation), rounding `performance.now()` to 1ms steps.
- **RFP Default:** The pref `privacy.resistFingerprinting.reduceTimerPrecision.microseconds` defaults to **1000** (1ms). However, the `ReduceTimerPrecision` RFP target applies additional frame-rate clamping, resulting in observed steps of **~16.667ms** (60Hz equivalent). Jitter is enabled by default (`privacy.resistFingerprinting.reduceTimerPrecision.jitter: true`). Source: [`nsRFPService.cpp`, `TimerClamping`](https://searchfox.org/mozilla-esr153/search?q=TimerClamping&path=nsRFPService).
- **RFP Configured (Tor-style):** When `microseconds=100000` is explicitly set, `performance.now()` advances in strict 100ms steps (`[1500, 1600, 1700, ...]`).
- **FPP:** Inherits baseline 1ms steps; no additional timer clamping.

### D. Window-Size Handling & Letterboxing
**(Headless only — values will differ under a real window manager.)**
- Under RFP, Gecko rounds window dimensions to fixed steps (1200×600), clamps `screen.*` to window bounds, and spoofs `devicePixelRatio` to 2. Source: `WindowOuterSize` (26), `ScreenRect` (30), `ScreenAvailRect` (31), `RoundWindowSize` (47), `WindowDevicePixelRatio` (41).
- With `letterboxing=true`, pages are padded with margin bars at 200×100px stepping increments. Source: [`RFPHelper.sys.mjs`](https://searchfox.org/mozilla-esr153/source/toolkit/components/resistfingerprinting/RFPHelper.sys.mjs).
- FPP does not alter window or screen dimensions.

### E. Navigator & HTTP Headers
- **RFP does NOT spoof `navigator.userAgent`, `navigator.platform`, `navigator.oscpu`, or HTTP `User-Agent` on Linux in ESR 153.** The targets `NavigatorUserAgent` (19), `NavigatorPlatform` (18), `NavigatorOscpu` (17), `NavigatorAppVersion` (14), and `HttpUserAgent` (25) exist in the target constants but produce no observable change on Linux x86_64. The Tor Browser achieves Windows UA spoofing via additional `general.useragent.override` and `general.platform.override` prefs, not through RFP targets alone.
- HTTP header order is identical across all configurations. No header reordering target exists in RFP.

### F. Hardware & WebGL Unmasking
- RFP clamps CPU concurrency to **4** (target `NavigatorHWConcurrency`, 16), spoofs `maxTouchPoints` to **5** (target 72), and sanitizes WebGL vendor/renderer to `"Mozilla"` (targets 60, 77, 78).
- FPP uses `NavigatorHWConcurrencyTiered` (target 74), which bins to **8** on this host. `MaxTouchPointsCollapse` (target 73) collapses touch points to 0 (no change on desktop). WebGL vendor/renderer are left unmasked.

---

## 4. Impact of Timer Reduction on JIT Measurement

### The Problem
JIT vs interpreter execution is currently distinguished by elapsed-time microbenchmarks (S1: ~10–25ms, S3: ~80–140ms). Under RFP's default ~16.667ms quantization (or Tor-style 100ms), these timings become noisy or fall into the same quantum bucket.

### Decided Approach (D-012)
- **Primary:** Option B — Operation frequency counting per quantum (synchronize to a timer tick edge, count iterations of a calibrated compute function before the next tick).
- **Secondary:** Option C — Engine diagnostic reflection via Marionette chrome context (`Services.prefs.getBoolPref("javascript.options.baselinejit")`).
- **Fallback:** Option A — Scale workload so execution duration ≫ quantum.

---

## 5. Crowd Analysis

> [!WARNING]
> **Single-machine test results say nothing about blending in a crowd.**

Anonymity requires a large population of indistinguishable clients sharing the exact same fingerprint profile. This report measures local observable behaviour only; it cannot measure crowd size.

### Key Observations
1. **RFP does not spoof the User-Agent or platform string on Linux.** An Aegis user on Linux with RFP enabled presents `X11; Linux x86_64` in both `navigator.userAgent` and the HTTP `User-Agent` header. The Tor Browser achieves Windows UA spoofing via additional `general.useragent.override` and `general.platform.override` prefs that are **not** part of the `privacy.resistFingerprinting` pref itself. This means that without those extra overrides, the RFP-enabled Linux fingerprint differs from the Tor Browser crowd.
2. **RFP-only on Linux creates a distinct, small, unmeasured population.** The combination of UTC timezone, 1200×600 viewport, `devicePixelRatio=2`, `hardwareConcurrency=4`, `maxTouchPoints=5`, `WebGL: "Mozilla"`, but *with* a Linux User-Agent, is unlikely to match any large existing browser population. The size of this population is **small and unmeasured** — we cannot quantify it from local tests.
3. **FPP trades population uniformity for site compatibility.** FPP uses origin-keyed deterministic salting for canvas and concurrency tiering, rather than global spoofing. It does not attempt to make all users identical; it aims to reduce cross-site tracking entropy while preserving the user's general appearance as a standard Firefox user.
4. **HTTP headers are identical across all three configurations.** Header order, `Accept`, `Accept-Language`, `Accept-Encoding`, `Sec-Fetch-*`, and `Priority` headers show no difference, providing no additional fingerprint signal between Baseline, RFP, and FPP in this test.

---

## 6. FPP Per-Target Override Mechanism

FPP supports per-target customization via:
- **`privacy.fingerprintingProtection.overrides`** (string pref): comma-separated `+TargetName` / `-TargetName`. Applied on top of `DefaultTargetsFPP`.
  - Verified syntax on ESR 153: `"+CanvasRandomization,-EfficientCanvasRandomization,+JSDateTimeUTC"`
- **`privacy.fingerprintingProtection.granularOverrides`** (string pref): JSON array for per-first-party-domain target adjustments.
- **`privacy.fingerprintingProtection.remoteOverrides.enabled`** (bool, default `true`): fetches domain-specific overrides from Mozilla RemoteSettings. **Aegis locks this to `false` (see D-012).**

**Limitation:** These prefs are instance-wide. All tabs and origins in a single Firefox process share the same override set. Per-container or per-tab override switching is not supported by the engine.

---

## Appendix A: Raw Probe Output Summary (Redacted)

Raw probe results are stored in `tests/fixtures/output/probe_results_summary.json` (not committed; `.gitignore`d).

### Baseline Run 1
```
canvas.dataUrlHash:     <hash_1a>
canvas.imgDataHash:     <hash_1b>
canvas.repeatStable:    true
canvas.crossConsistent: true
audio.pcmHash:          <hash_audio> (44100 Hz, sampleSum: 35.75)
timers.perfDeltas:      [null] (no non-zero deltas captured in tight loop)
timers.dateMinDelta:    1 ms
window:                 <REDACTED_DISPLAY_W> x <REDACTED_DISPLAY_H_MINUS_CHROME>
screen:                 <REDACTED_DISPLAY_W> x <REDACTED_DISPLAY_H>
timezone:               <REDACTED_TZ>, offset: <REDACTED_TZ_OFFSET>
hwConcurrency:          <REDACTED_CORES>
maxTouchPoints:         0
devicePixelRatio:       1
webglVendor:            <REDACTED_GPU_VENDOR>
webglRenderer:          <REDACTED_GPU_MODEL>
```

### RFP Default Run 1
```
canvas.dataUrlHash:     <hash_2a> (different from baseline)
canvas.imgDataHash:     <hash_2b> (different from baseline)
canvas.repeatStable:    false (noise per extraction)
canvas.crossConsistent: false
audio.pcmHash:          <hash_audio> (identical to baseline)
timers.perfDeltas:      [null] (frame-rate clamped; tight loop captured 0 non-zero deltas)
timers.dateMinDelta:    null (clamped)
window:                 1200 x 600
screen:                 1200 x 600, avail: 1200 x 600
timezone:               Atlantic/Reykjavik, offset: 0
hwConcurrency:          4
maxTouchPoints:         5
devicePixelRatio:       2
webglVendor:            "Mozilla"
webglRenderer:          "Mozilla"
```

### FPP Default Run 1
```
canvas.dataUrlHash:     <hash_3a> (different from baseline; origin-keyed)
canvas.imgDataHash:     <hash_1b> (same raw pixels as baseline — efficient randomization only alters toDataURL encoding)
canvas.repeatStable:    true
canvas.crossConsistent: true
audio.pcmHash:          <hash_audio> (identical)
timers.perfDeltas:      [1, 1, 1, ...] (1 ms steps, same as baseline)
timers.dateMinDelta:    1 ms
window:                 <REDACTED_DISPLAY_W> x <REDACTED_DISPLAY_H_MINUS_CHROME>
screen:                 <REDACTED_DISPLAY_W> x <REDACTED_DISPLAY_H>
timezone:               <REDACTED_TZ>, offset: <REDACTED_TZ_OFFSET>
hwConcurrency:          8 (tiered from <REDACTED_CORES>)
maxTouchPoints:         0
devicePixelRatio:       1
webglVendor:            <REDACTED_GPU_VENDOR>
webglRenderer:          <REDACTED_GPU_MODEL>
```

### Cross-Run Stability
| Config | Canvas Stable Across Runs | Audio Stable Across Runs |
| :--- | :--- | :--- |
| Baseline | No (baseline `EfficientCanvasRandomization`) | Yes |
| RFP | No (per-extraction randomization) | Yes |
| FPP | No (origin-keyed per session) | Yes |

### Effective Prefs Snapshot (via Marionette chrome context)
```
privacy.reduceTimerPrecision:                           true  (all configs)
privacy.reduceTimerPrecision.unconditional:             true  (all configs)
privacy.resistFingerprinting.reduceTimerPrecision.microseconds: 1000  (all configs; default)
privacy.resistFingerprinting.reduceTimerPrecision.jitter:       true  (all configs)
privacy.baselineFingerprintingProtection:               true  (all configs; ESR 153 default)
privacy.fingerprintingProtection.pbmode:                true  (all configs; private browsing default)
privacy.fingerprintingProtection.remoteOverrides.enabled: true (default; Aegis locks to false)
```

---

**STOP.** This is a report-only document. No design decisions are made here.
