# Phase 2c Design Note: Presets, Multi-Axis Mapping Engine, and Identity Architecture

**Document ID:** DN-002 (Revision 3)  
**Date:** 2026-10-24  
**Status:** DESIGN NOTE — Approved in Direction with Owner Corrections  
**Affects:** docs/spec/ (Parts 5.1, 5.3, 5.4, 5.5, 6.1, 6.2, 7.1), `config/axes/identity/`, `tools/generate_autoconfig.py`, Orchestrator IPC  
**Ground Truth Dependencies:** D-008, D-011, D-012, D-013, D-014, A-001, A-002, A-003, SPIKE-005, SPIKE-006, Phase 2b Empirical Findings (`tests/axes/probe_container_canvas.py`, `tests/axes/probe_rfp_fpp.py`)

---

## 1. Executive Summary & Problem Statement

The Aegis Master Specification initially modeled three orthogonal axes for every Cell:
- **Surface ($S$):** $S1$ (Standard) through $S4$ (Static)
- **Identity ($I$):** $I1$ (Native) through $I4$ (Minimal-API)
- **Network ($N$):** $N0$ (Direct) through $N3$ (Tor + Bridges)

Empirical investigations across Phases 0, 2a, and 2b on Firefox ESR 153.5.1esr confirmed key browser engine constraints:
1. **Engine Primitives are Instance-Wide (D-008, D-011, D-012):**
   - JIT compiler flags (`javascript.options.baselinejit`, `ion`, `wasm`) are global to SpiderMonkey.
   - Fingerprinting defenses (`privacy.resistFingerprinting`, `privacy.fingerprintingProtection`) are global Gecko preferences.
   - Proxy configuration (`network.proxy.socks`) and socket routing are instance-wide.
2. **Containers Do Not Partition Canvas Noise (D-012, A-002):**
   - Under `privacy.fingerprintingProtection` (FPP), two tabs in different containers (`userContextId: 1` vs `2`) visiting the same origin produce identical canvas hashes because `EfficientCanvasRandomization` keys strictly on the eTLD+1 site principal. Cross-Cell canvas isolation requires process-level separation.
3. **WebExtensions are Process-Global (D-014, A-003):**
   - Containers cannot restrict or isolate WebExtensions. All active extension scripts execute across all tabs and containers in an instance.
4. **Memory Scalability and Concurrency Cap (D-011, A-001):**
   - A multi-process Firefox ESR instance consumes ~596 MB RSS lower bound (measured under 3 local pages).
   - Rather than fixing a rigid count of 4 total presets, Aegis defines a set of named presets that **spawn on demand**, regulated by a **max concurrently running instances cap (default 4, configurable via orchestrator)**.

This note establishes the canonical presets, non-downgrading mapping engine, dedicated banking preset, and RFP unmeasured crowd semantics.

---

## 2. Canonical Preset Instances

Presets are named configurations that launch dedicated, isolated Gecko process instances on demand. They are referenced exclusively by name:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                   AEGIS ORCHESTRATOR                                    │
│       (Supervision / Capability Tokens / Unified Flight Recorder / Concurrency Cap)    │
└───────────────┬───────────────────┬────────────────────┬───────────────────┬───────────┘
                │                   │                    │                   │
                ▼                   ▼                    ▼                   ▼
        ┌───────────────┐   ┌───────────────┐    ┌───────────────┐   ┌───────────────┐
        │   STANDARD    │   │    GUARDED    │    │    STRICT     │    │    BANKING    │
        ├───────────────┤   ├───────────────┤    ├───────────────┤   ├───────────────┤
        │ S1: Standard  │   │ S2: Guarded   │    │ S3: Strict    │    │ S2: Guarded   │
        │ I3: FPP Noise │   │ I3: FPP Noise │    │ I2: RFP       │    │ I3: FPP Noise │
        │ N1: Strict DoH│   │ N1: Strict DoH│    │ N1: Strict DoH│    │ N1: Strict DoH│
        │ Normal Profile│   │ Guard Profile │    │ Strict Profile│    │ Ext. Disabled │
        └───────────────┘   └───────────────┘    └───────────────┘   └───────────────┘
                │                   │                    │                   │
                ▼                   ▼                    ▼                   ▼
        ┌───────────────┐   ┌───────────────┐    ┌───────────────┐   ┌───────────────┐
        │ RESEARCH TOR  │   │RESEARCH STRICT│    │DETONATION TOR │   │DETONATION LOC.│
        ├───────────────┤   ├───────────────┤    ├───────────────┤   ├───────────────┤
        │ S1: Standard  │   │ S3: Strict    │    │ S4: Static    │    │ S4: Static    │
        │ I2: RFP       │   │ I2: RFP (ACK) │    │ I2: RFP       │    │ I4: Min-API   │
        │ N2/N3: Tor    │   │ N2/N3: Tor    │    │ N2/N3: Tor    │    │ N1: Strict DoH│
        │ Semi-ephem.   │   │ Semi-ephem.   │    │ tmpfs Ephem.  │    │ tmpfs Ephem.  │
        └───────────────┘   └───────────────┘    └───────────────┘   └───────────────┘
```

### 2.1 Standard (`standard`) — Daily Interactive Browsing
- **Surface ($S1$):** Baseline JIT enabled, Ion JIT enabled, WebAssembly enabled, WebGL enabled, third-party cookies partitioned (dFPI), mixed content blocked.
- **Identity ($I3$):** `privacy.fingerprintingProtection: true` (FPP), remote overrides locked `false` (D-012), 1ms timer precision, native timezone and window dimensions, unmasked WebGL. Provides origin-keyed canvas salting (`EfficientCanvasRandomization`) without web breakage.
- **Network ($N1$):** Strict DNS-over-HTTPS (`network.trr.mode: 3` with user-selected DoH provider, fail closed on DNS failure). Direct DNS ($N0$) permitted with an informational prompt.
- **Profile:** Persistent user profile (`profiles/aegis-standard/`).

### 2.2 Guarded (`guarded`) — Hardened Daily Browsing
- **Surface ($S2$):** Everything in $S1$ plus: HTTPS-only mode locked (`dom.security.https_only_mode: true`), audible media autoplay blocked (`media.autoplay.default: 1`), WebRTC ICE restricted to default interface address (`media.peerconnection.ice.default_address_only: true`), dangerous protocol handlers blocked.
- **Identity ($I3$):** `privacy.fingerprintingProtection: true` (FPP) with remote overrides locked `false`. Provides site-keyed canvas noise while preserving local timezone and display geometry.
- **Network ($N1$):** Strict DNS-over-HTTPS (`network.trr.mode: 3`).
- **Profile:** Persistent guarded profile (`profiles/aegis-guarded/`).

### 2.3 Banking (`banking`) — Anchored Account Isolation
- **Surface ($S2$):** HTTPS-only mode locked, audible autoplay blocked, WebRTC ICE restricted to default interface.
- **Identity ($I3$):** `privacy.fingerprintingProtection: true` (FPP) with remote overrides locked `false`. Enforces site-keyed canvas noise while preserving authentic local timezone and display geometry. As specified in **Amendment A-003**, RFP ($I2$) is avoided because artificial UTC timezones, letterboxed viewports, and masked hardware trigger automated anti-fraud heuristics and account lockouts on banking and 2FA platforms.
- **Network ($N1$):** Strict DNS-over-HTTPS (`network.trr.mode: 3`).
- **Extension Policy:** Extensions disabled instance-wide (`extensions.enabledScopes: 0`), fulfilling Master Spec Part 5.5 ("extensions off").
- **Profile:** Dedicated banking profile (`profiles/aegis-banking/`). Spawns on demand.

### 2.4 Strict (`strict`) — Hardened Clearnet Browsing
- **Surface ($S3$):** JIT compilers locked off (`baselinejit: false`, `ion: false`), WebAssembly locked off (`wasm: false`), WebGL locked off (`webgl.disabled: true`), OpenType-SVG fonts and MathML disabled, media autoplay completely blocked (`media.autoplay.default: 5`), session-only storage.
- **Identity ($I2$):** `privacy.resistFingerprinting: true` (RFP, intended to resemble, unmeasured): UTC timezone (`Atlantic/Reykjavik`), 1200×600 rounded window, DPR=2, concurrency=4, touch=5 (measured on Aegis in headless mode; see Bugzilla 1369319 / `nsRFPService.cpp`), ~16.67ms frame-rate timer clamping with jitter, letterboxing margins enabled (`privacy.resistFingerprinting.letterboxing: true`).
- **Network ($N1$):** Strict DNS-over-HTTPS (`network.trr.mode: 3`).
- **Profile:** Ephemeral or semi-ephemeral profile (`profiles/aegis-strict/`).

### 2.5 Research Tor (`research_tor`) — Tor Browsing
- **Surface ($S1$):** Baseline/Ion JIT enabled, WebAssembly enabled, WebGL enabled (sanitized to `"Mozilla"`).
- **Identity ($I2$):** `privacy.resistFingerprinting: true` (RFP, intended to resemble, unmeasured).
- **Network ($N2$ / $N3$):** All traffic routed through local Tor daemon SOCKS5 proxy (`127.0.0.1:9050`), remote DNS resolution over Tor (`network.proxy.socks_remote_dns: true`), WebRTC completely disabled (`media.peerconnection.enabled: false`).
- **Profile:** Semi-ephemeral profile (`profiles/aegis-research/`) cleared on browser close.

### 2.6 Research Strict (`research_strict`) — Hardened Tor (Crowd-Splitting ACK)
- **Surface ($S3$):** JIT compilers locked off (`baselinejit: false`, `ion: false`), WebAssembly locked off (`wasm: false`), WebGL locked off, OpenType-SVG and MathML disabled.
- **Identity ($I2$):** `privacy.resistFingerprinting: true` (RFP, intended to resemble, unmeasured).
- **Network ($N2$ / $N3$):** Tor SOCKS5 proxy (`127.0.0.1:9050`) with remote DNS.
- **Rule R2 Acknowledgment:** Requires an explicit user crowd-splitting acknowledgment: *"Disabling JIT on Tor distinguishes your browser from standard Tor traffic."*
- **Profile:** Semi-ephemeral profile (`profiles/aegis-research-strict/`).

### 2.7 Detonation Tor (`detonation`) — Static Quarantine Over Tor
- **Surface ($S4$):** Static document mode. JavaScript completely disabled (`javascript.enabled: false`), downloadable remote web fonts disabled (`gfx.downloadable_fonts.enabled: false`), extensions disabled.
- **Identity ($I2$):** `privacy.resistFingerprinting: true` (RFP, intended to resemble, unmeasured).
- **Network ($N2$ / $N3$):** Tor SOCKS5 proxy. Cleartext fallback strictly refused.
- **Profile:** Ephemeral RAM profile on `tmpfs` (`/dev/shm/aegis-detonation-XXXXXX`), wiped with zero-fill upon process exit.

### 2.8 Detonation Local (`detonation_local`) — Offline / Clearnet Static Quarantine
- **Surface ($S4$):** JavaScript completely disabled, downloadable remote fonts disabled, extensions disabled.
- **Identity ($I4$):** Minimal-API: RFP enabled plus high-entropy APIs disabled (Gamepad, Battery, Sensors, MediaDevices enumeration).
- **Network ($N1$):** Strict DNS-over-HTTPS (`network.trr.mode: 3`).
- **Profile:** Ephemeral RAM profile on `tmpfs`.

---

## 3. Unambiguous Rule: Tor with JIT / WASM

The relationship between Tor routing ($N2/N3$) and JIT/WASM compiler flags is defined strictly as follows:

1. **Direction 1: Surface $\to$ Tor (Is JIT/WASM permitted on Tor?):**
   - **YES, at Surface $S1$.** Combination $\{S1, I2, N2\}$ is **ALLOWED** as `research_tor`.
2. **Direction 2: Hardened Tor $\to$ JIT/WASM (Can JIT be enabled in hardened Tor tiers?):**
   - **NO.** In `research_strict` ($S3$) and `detonation` ($S4$), JIT and WASM are strictly disabled and locked (`javascript.options.baselinejit: false`, `ion: false`, `wasm: false`). Any attempt to enable JIT within these presets is rejected fail-closed.
3. **Direction 3: The Crowd-Splitting Rule for $S3$ on Tor (R2):**
   - Surface $S3$ over Tor ($N2/N3$) is not offered by default.
   - An active script can measure the absence of JIT and detect that JIT is disabled, which distinguishes this client from standard Tor users.
   - Therefore, $\{S3, I2, N2\}$ is classified as **MAPPED (`research_strict`)** and requires an **explicit user acknowledgment**.
4. **Direction 4: Non-$I2$ with JIT on Tor is Prohibited (R2.1):**
   - Requesting Tor routing while demanding native identity ($I1$), site-keyed noise ($I3$), or minimal-API ($I4$) is **strictly REJECTED**. Tor traffic must always use $I2$.

---

## 4. Banking (Anchored Cells) & Instance Management

### 4.1 Resolution of Extension Scope in Banking
Master Spec Part 5.5 requires "extensions off" for Anchored Cells.
- Empirical testing confirms that Gecko WebExtensions execute process-wide across all containers; containers cannot isolate extensions.
- In accordance with **Decision D-014**, Anchored Cells are assigned a dedicated preset instance: **`banking`** (`{S2, I3, N1}`).
- The `banking` preset disables extensions instance-wide (`extensions.enabledScopes: 0`), operating under an isolated profile directory (`profiles/aegis-banking/`).
- Anti-fraud rationale: Anchored Cells enforce $I3$ (FPP site-keyed noise, **Amendment A-003**) rather than RFP ($I2$) to ensure logins do not fail automated bot heuristics.

### 4.2 Max Concurrently Running Instances Cap
- The concurrency cap is defined as: **Max concurrently running instances (default 4, configurable via orchestrator)**.
- Presets are templates that spawn instances **on demand**. If the user is not actively banking, 0 `banking` instances run.
- When an action requires opening a preset that would exceed the active instance cap, the orchestrator prompts the user to either hibernate/close an idle instance or raise the concurrency limit.
- **Memory Lower Bounds:**
  - Single multi-process ESR 153 instance baseline: **~596 MB RSS lower bound** (measured under 3 local pages).
  - 4 concurrent instances: **~2.38 GB RSS lower bound**.
  - These figures are lower bounds for light local pages, not production ceilings for complex web applications.

---

## 5. Tor Unavailable at Launch: Strict Option A (Decision D-013)

When an instance configured for Tor routing ($N2$ or $N3$) launches:
1. **Strict Fail-Closed (Option A):** If the local Tor daemon is offline, unresponsive, or connection to `127.0.0.1:9050` fails, the instance **MUST refuse to launch**.
2. **Tor Tier Invariance:** A Tor tier must **never mutate into a non-Tor tier**. Silent or automatic fallback to direct clearnet ($N0$) or DoH ($N1$) within the same instance or profile is strictly prohibited.
3. **Separate, Explicit Non-Tor Action:** If Tor is unavailable, the user is offered a distinct, conscious option to open a **different, clearly named non-Tor preset** (e.g., `standard` or `guarded`) under an isolated profile.

---

## 6. Complete 4x4x4 Multi-Axis Combination Matrix (All 64 Rows)

The matrix below is generated deterministically by `tools/tier_matrix.py` and validated by property tests in `tests/axes/test_tier_matrix.py`.

### Non-Downgrading Invariant (Property Verified):
For every MAPPED row:
$$\text{Preset}(S) \ge \text{Requested}(S) \quad \land \quad \text{Preset}(I) \ge \text{Requested}(I) \quad \land \quad (N0 \to N1 \text{ is the ONLY network promotion})$$

### Summary Statistics:
- **Total Combinations:** $4 \times 4 \times 4 = 64$
- **ALLOWED (Exact Presets):** 8 combinations
- **MAPPED (Promoted without Downgrade):** 26 combinations
- **REJECTED (Security Prohibited):** 30 combinations

| # | Requested `{S, I, N}` | Status | Mapped Preset | Governing Rule | Security Rationale |
|---|---|---|---|---|---|
| 01 | `{S1, I1, N0}` | **MAPPED** | `standard` | `RULE_N0_DIRECT_STANDARD` | Direct DNS (N0) permitted in Standard preset with warning; promoted to N1 Strict DoH in standard preset. |
| 02 | `{S1, I1, N1}` | **MAPPED** | `standard` | `RULE_I1_S1_STANDARD` | Native identity (I1) in S1 maps to Standard preset (promoted to I3 FPP baseline defense). |
| 03 | `{S1, I1, N2}` | **REJECTED** | — | `RULE_R2_TOR_IDENTITY_LOCK` | R2 violation: Tor mode (N2) strictly locks Identity to I2 (RFP, intended to resemble, unmeasured). Identity I1 splits the crowd or leaks host parameters. |
| 04 | `{S1, I1, N3}` | **REJECTED** | — | `RULE_R2_TOR_IDENTITY_LOCK` | R2 violation: Tor mode (N3) strictly locks Identity to I2 (RFP, intended to resemble, unmeasured). Identity I1 splits the crowd or leaks host parameters. |
| 05 | `{S1, I2, N0}` | **MAPPED** | `strict` | `RULE_N0_PROMOTED_TO_N1` | RFP Identity (I2) on N0 promoted to N1 Strict DoH in Strict preset (no downgrade on I or S). |
| 06 | `{S1, I2, N1}` | **MAPPED** | `strict` | `RULE_I2_LOCAL_MAPPED_STRICT` | RFP Uniform Identity (I2) requested with surface S1; mapped to Strict preset ({S3, I2, N1}) without downgrading Identity. |
| 07 | `{S1, I2, N2}` | **ALLOWED** | `research_tor` | `RULE_PRESET_TOR_STANDARD` | Exact match for Research Tor preset (S1 Surface, I2 RFP intended to resemble unmeasured, N2 Tor routing). |
| 08 | `{S1, I2, N3}` | **ALLOWED** | `research_tor` | `RULE_PRESET_TOR_STANDARD` | Exact match for Research Tor preset (S1 Surface, I2 RFP intended to resemble unmeasured, N3 Tor routing). |
| 09 | `{S1, I3, N0}` | **MAPPED** | `standard` | `RULE_N0_DIRECT_STANDARD` | Direct DNS (N0) permitted in Standard preset with warning; promoted to N1 Strict DoH in standard preset. |
| 10 | `{S1, I3, N1}` | **ALLOWED** | `standard` | `RULE_PRESET_STANDARD` | Exact match for Standard preset (S1 Surface, I3 FPP Site-keyed noise, N1 Strict DoH). |
| 11 | `{S1, I3, N2}` | **REJECTED** | — | `RULE_R2_TOR_IDENTITY_LOCK` | R2 violation: Tor mode (N2) strictly locks Identity to I2 (RFP, intended to resemble, unmeasured). Identity I3 splits the crowd or leaks host parameters. |
| 12 | `{S1, I3, N3}` | **REJECTED** | — | `RULE_R2_TOR_IDENTITY_LOCK` | R2 violation: Tor mode (N3) strictly locks Identity to I2 (RFP, intended to resemble, unmeasured). Identity I3 splits the crowd or leaks host parameters. |
| 13 | `{S1, I4, N0}` | **REJECTED** | — | `RULE_I4_REQUIRES_S4` | Posture conflict: Identity I4 (minimal-API) disables high-entropy APIs and is reserved for S4 Static surface. It cannot be combined with interactive surface S1. |
| 14 | `{S1, I4, N1}` | **REJECTED** | — | `RULE_I4_REQUIRES_S4` | Posture conflict: Identity I4 (minimal-API) disables high-entropy APIs and is reserved for S4 Static surface. It cannot be combined with interactive surface S1. |
| 15 | `{S1, I4, N2}` | **REJECTED** | — | `RULE_R2_TOR_IDENTITY_LOCK` | R2 violation: Tor mode (N2) strictly locks Identity to I2 (RFP, intended to resemble, unmeasured). Identity I4 splits the crowd or leaks host parameters. |
| 16 | `{S1, I4, N3}` | **REJECTED** | — | `RULE_R2_TOR_IDENTITY_LOCK` | R2 violation: Tor mode (N3) strictly locks Identity to I2 (RFP, intended to resemble, unmeasured). Identity I4 splits the crowd or leaks host parameters. |
| 17 | `{S2, I1, N0}` | **MAPPED** | `guarded` | `RULE_N0_PROMOTED_TO_N1` | Plaintext DNS (N0) prohibited in hardened surface S2. Promoted to N1 Strict DoH in Guarded preset. |
| 18 | `{S2, I1, N1}` | **MAPPED** | `guarded` | `RULE_I1_PROMOTED_GUARDED` | Guarded surface (S2) mandates tracking/fingerprint baseline; I1 promoted to I3 in Guarded preset. |
| 19 | `{S2, I1, N2}` | **REJECTED** | — | `RULE_R2_TOR_IDENTITY_LOCK` | R2 violation: Tor mode (N2) strictly locks Identity to I2 (RFP, intended to resemble, unmeasured). Identity I1 splits the crowd or leaks host parameters. |
| 20 | `{S2, I1, N3}` | **REJECTED** | — | `RULE_R2_TOR_IDENTITY_LOCK` | R2 violation: Tor mode (N3) strictly locks Identity to I2 (RFP, intended to resemble, unmeasured). Identity I1 splits the crowd or leaks host parameters. |
| 21 | `{S2, I2, N0}` | **MAPPED** | `strict` | `RULE_N0_PROMOTED_TO_N1` | Plaintext DNS (N0) prohibited in hardened surface S2. Promoted to N1 Strict DoH in Strict preset (preserving I2). |
| 22 | `{S2, I2, N1}` | **MAPPED** | `strict` | `RULE_I2_LOCAL_MAPPED_STRICT` | RFP Uniform Identity (I2) requested with surface S2; mapped to Strict preset ({S3, I2, N1}) without downgrading Identity. |
| 23 | `{S2, I2, N2}` | **MAPPED** | `research_strict` | `RULE_R2_TOR_S2_PROMOTION` | Rule R2: S2 controls over Tor (N2) split the crowd. Promoted to S3 Research Strict with explicit crowd-splitting acknowledgment. |
| 24 | `{S2, I2, N3}` | **MAPPED** | `research_strict` | `RULE_R2_TOR_S2_PROMOTION` | Rule R2: S2 controls over Tor (N3) split the crowd. Promoted to S3 Research Strict with explicit crowd-splitting acknowledgment. |
| 25 | `{S2, I3, N0}` | **MAPPED** | `guarded` | `RULE_N0_PROMOTED_TO_N1` | Plaintext DNS (N0) prohibited in hardened surface S2. Promoted to N1 Strict DoH in Guarded preset. |
| 26 | `{S2, I3, N1}` | **ALLOWED** | `guarded` | `RULE_PRESET_GUARDED` | Exact match for Guarded preset (S2 Guarded Surface, I3 FPP Site-keyed noise, N1 Strict DoH). |
| 27 | `{S2, I3, N2}` | **REJECTED** | — | `RULE_R2_TOR_IDENTITY_LOCK` | R2 violation: Tor mode (N2) strictly locks Identity to I2 (RFP, intended to resemble, unmeasured). Identity I3 splits the crowd or leaks host parameters. |
| 28 | `{S2, I3, N3}` | **REJECTED** | — | `RULE_R2_TOR_IDENTITY_LOCK` | R2 violation: Tor mode (N3) strictly locks Identity to I2 (RFP, intended to resemble, unmeasured). Identity I3 splits the crowd or leaks host parameters. |
| 29 | `{S2, I4, N0}` | **REJECTED** | — | `RULE_I4_REQUIRES_S4` | Posture conflict: Identity I4 (minimal-API) disables high-entropy APIs and is reserved for S4 Static surface. It cannot be combined with interactive surface S2. |
| 30 | `{S2, I4, N1}` | **REJECTED** | — | `RULE_I4_REQUIRES_S4` | Posture conflict: Identity I4 (minimal-API) disables high-entropy APIs and is reserved for S4 Static surface. It cannot be combined with interactive surface S2. |
| 31 | `{S2, I4, N2}` | **REJECTED** | — | `RULE_R2_TOR_IDENTITY_LOCK` | R2 violation: Tor mode (N2) strictly locks Identity to I2 (RFP, intended to resemble, unmeasured). Identity I4 splits the crowd or leaks host parameters. |
| 32 | `{S2, I4, N3}` | **REJECTED** | — | `RULE_R2_TOR_IDENTITY_LOCK` | R2 violation: Tor mode (N3) strictly locks Identity to I2 (RFP, intended to resemble, unmeasured). Identity I4 splits the crowd or leaks host parameters. |
| 33 | `{S3, I1, N0}` | **MAPPED** | `strict` | `RULE_N0_PROMOTED_TO_N1` | Plaintext DNS (N0) prohibited in hardened surface S3. Promoted to N1 Strict DoH in Strict preset (S3 >= S3, no downgrade). |
| 34 | `{S3, I1, N1}` | **MAPPED** | `strict` | `RULE_S3_LOCAL_STRICT` | S3 surface requires hardened instance; I1 promoted to I2 in Strict preset (S3 >= S3, no downgrade). |
| 35 | `{S3, I1, N2}` | **REJECTED** | — | `RULE_R2_TOR_IDENTITY_LOCK` | R2 violation: Tor mode (N2) strictly locks Identity to I2 (RFP, intended to resemble, unmeasured). Identity I1 splits the crowd or leaks host parameters. |
| 36 | `{S3, I1, N3}` | **REJECTED** | — | `RULE_R2_TOR_IDENTITY_LOCK` | R2 violation: Tor mode (N3) strictly locks Identity to I2 (RFP, intended to resemble, unmeasured). Identity I1 splits the crowd or leaks host parameters. |
| 37 | `{S3, I2, N0}` | **MAPPED** | `strict` | `RULE_N0_PROMOTED_TO_N1` | Plaintext DNS (N0) prohibited in hardened surface S3. Promoted to N1 Strict DoH in Strict preset (S3 >= S3, no downgrade). |
| 38 | `{S3, I2, N1}` | **ALLOWED** | `strict` | `RULE_PRESET_STRICT` | Exact match for Strict preset (S3 Strict Surface, I2 RFP intended to resemble unmeasured, N1 Strict DoH). |
| 39 | `{S3, I2, N2}` | **MAPPED** | `research_strict` | `RULE_R2_TOR_S3_ACK` | Rule R2: S3 (JIT/WASM disabled) over Tor (N2) splits the standard Tor crowd. Allowed ONLY with explicit user crowd-splitting acknowledgment; maps to Research Strict. |
| 40 | `{S3, I2, N3}` | **MAPPED** | `research_strict` | `RULE_R2_TOR_S3_ACK` | Rule R2: S3 (JIT/WASM disabled) over Tor (N3) splits the standard Tor crowd. Allowed ONLY with explicit user crowd-splitting acknowledgment; maps to Research Strict. |
| 41 | `{S3, I3, N0}` | **MAPPED** | `strict` | `RULE_N0_PROMOTED_TO_N1` | Plaintext DNS (N0) prohibited in hardened surface S3. Promoted to N1 Strict DoH in Strict preset (S3 >= S3, no downgrade). |
| 42 | `{S3, I3, N1}` | **MAPPED** | `strict` | `RULE_S3_I3_MAPPED_STRICT` | S3 requested on clearnet DoH maps to Strict preset ({S3, I2, N1}) with identity promoted to I2 RFP (no downgrade on S). |
| 43 | `{S3, I3, N2}` | **REJECTED** | — | `RULE_R2_TOR_IDENTITY_LOCK` | R2 violation: Tor mode (N2) strictly locks Identity to I2 (RFP, intended to resemble, unmeasured). Identity I3 splits the crowd or leaks host parameters. |
| 44 | `{S3, I3, N3}` | **REJECTED** | — | `RULE_R2_TOR_IDENTITY_LOCK` | R2 violation: Tor mode (N3) strictly locks Identity to I2 (RFP, intended to resemble, unmeasured). Identity I3 splits the crowd or leaks host parameters. |
| 45 | `{S3, I4, N0}` | **REJECTED** | — | `RULE_I4_REQUIRES_S4` | Posture conflict: Identity I4 (minimal-API) disables high-entropy APIs and is reserved for S4 Static surface. It cannot be combined with interactive surface S3. |
| 46 | `{S3, I4, N1}` | **REJECTED** | — | `RULE_I4_REQUIRES_S4` | Posture conflict: Identity I4 (minimal-API) disables high-entropy APIs and is reserved for S4 Static surface. It cannot be combined with interactive surface S3. |
| 47 | `{S3, I4, N2}` | **REJECTED** | — | `RULE_R2_TOR_IDENTITY_LOCK` | R2 violation: Tor mode (N2) strictly locks Identity to I2 (RFP, intended to resemble, unmeasured). Identity I4 splits the crowd or leaks host parameters. |
| 48 | `{S3, I4, N3}` | **REJECTED** | — | `RULE_R2_TOR_IDENTITY_LOCK` | R2 violation: Tor mode (N3) strictly locks Identity to I2 (RFP, intended to resemble, unmeasured). Identity I4 splits the crowd or leaks host parameters. |
| 49 | `{S4, I1, N0}` | **MAPPED** | `detonation_local` | `RULE_N0_PROMOTED_TO_N1` | Plaintext DNS (N0) prohibited in static surface S4. Promoted to N1 Strict DoH in Detonation Local preset. |
| 50 | `{S4, I1, N1}` | **MAPPED** | `detonation_local` | `RULE_S4_I1_PROMOTED_DETONATION` | Static surface S4 requires minimal identity; I1 promoted to I4 in Detonation Local preset. |
| 51 | `{S4, I1, N2}` | **REJECTED** | — | `RULE_R2_TOR_IDENTITY_LOCK` | R2 violation: Tor mode (N2) strictly locks Identity to I2 (RFP, intended to resemble, unmeasured). Identity I1 splits the crowd or leaks host parameters. |
| 52 | `{S4, I1, N3}` | **REJECTED** | — | `RULE_R2_TOR_IDENTITY_LOCK` | R2 violation: Tor mode (N3) strictly locks Identity to I2 (RFP, intended to resemble, unmeasured). Identity I1 splits the crowd or leaks host parameters. |
| 53 | `{S4, I2, N0}` | **MAPPED** | `detonation_local` | `RULE_N0_PROMOTED_TO_N1` | Plaintext DNS (N0) prohibited in static surface S4. Promoted to N1 Strict DoH in Detonation Local preset. |
| 54 | `{S4, I2, N1}` | **MAPPED** | `detonation_local` | `RULE_I2_S4_LOCAL_DETONATION` | I2 on local S4 maps to Detonation Local preset (promoted to I4 minimal-API). |
| 55 | `{S4, I2, N2}` | **ALLOWED** | `detonation` | `RULE_PRESET_TOR_SAFEST` | Exact match for Detonation Tor preset (S4 Static Surface, I2 RFP intended to resemble unmeasured, N2 Tor routing). |
| 56 | `{S4, I2, N3}` | **ALLOWED** | `detonation` | `RULE_PRESET_TOR_SAFEST` | Exact match for Detonation Tor preset (S4 Static Surface, I2 RFP intended to resemble unmeasured, N3 Tor routing). |
| 57 | `{S4, I3, N0}` | **MAPPED** | `detonation_local` | `RULE_N0_PROMOTED_TO_N1` | Plaintext DNS (N0) prohibited in static surface S4. Promoted to N1 Strict DoH in Detonation Local preset. |
| 58 | `{S4, I3, N1}` | **MAPPED** | `detonation_local` | `RULE_S4_I3_MAPPED_DETONATION` | S4 Static surface requires minimal identity; I3 promoted to I4 in Detonation Local preset. |
| 59 | `{S4, I3, N2}` | **REJECTED** | — | `RULE_R2_TOR_IDENTITY_LOCK` | R2 violation: Tor mode (N2) strictly locks Identity to I2 (RFP, intended to resemble, unmeasured). Identity I3 splits the crowd or leaks host parameters. |
| 60 | `{S4, I3, N3}` | **REJECTED** | — | `RULE_R2_TOR_IDENTITY_LOCK` | R2 violation: Tor mode (N3) strictly locks Identity to I2 (RFP, intended to resemble, unmeasured). Identity I3 splits the crowd or leaks host parameters. |
| 61 | `{S4, I4, N0}` | **MAPPED** | `detonation_local` | `RULE_N0_PROMOTED_TO_N1` | Plaintext DNS (N0) prohibited in static surface S4. Promoted to N1 Strict DoH in Detonation Local preset. |
| 62 | `{S4, I4, N1}` | **ALLOWED** | `detonation_local` | `RULE_PRESET_DETONATION_LOCAL` | Exact match for Detonation Local preset (S4 Static Surface, I4 Minimal-API, N1 Strict DoH, ephemeral RAM). |
| 63 | `{S4, I4, N2}` | **REJECTED** | — | `RULE_R2_TOR_IDENTITY_LOCK` | R2 violation: Tor mode (N2) strictly locks Identity to I2 (RFP, intended to resemble, unmeasured). Identity I4 splits the crowd or leaks host parameters. |
| 64 | `{S4, I4, N3}` | **REJECTED** | — | `RULE_R2_TOR_IDENTITY_LOCK` | R2 violation: Tor mode (N3) strictly locks Identity to I2 (RFP, intended to resemble, unmeasured). Identity I4 splits the crowd or leaks host parameters. |

---

## 7. Implementation Plan for Phase 2c

1. **Declarative Identity Files (`config/axes/identity/`):**
   - Create `i1.json` (Native), `i2.json` (RFP intended to resemble, unmeasured), `i3.json` (Site-keyed noise FPP), and `i4.json` (Minimal-API).
2. **Generator Extension (`tools/generate_autoconfig.py`):**
   - Extend the generator to parse both `config/axes/surface/*.json` and `config/axes/identity/*.json`.
   - Validate cumulativity across Surface and Identity.
   - Generate `config/autoconfig/aegis.cfg` with both Surface and Identity tier logic.
   - Validate CI drift check (`--check`).
3. **Runtime Enforcement & Override Verification Tests:**
   - Query live prefs and behavior per identity level against running engine.
   - Prove that a per-target override in `privacy.fingerprintingProtection.overrides` changes behavior.
   - Mark prefs `VERIFIED` in `docs/VERIFY.md` only after runtime test execution.
