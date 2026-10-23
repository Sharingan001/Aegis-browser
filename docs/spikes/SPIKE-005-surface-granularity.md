# SPIKE-005: Per-Cell Surface-Level Granularity and Axis Isolation

**Document Version:** 1.0.0  
**Date:** 2026-10-23  
**Status:** PROPOSAL / AWAITING OWNER APPROVAL  
**Addresses:** D-008, VERIFY-S-022, Spec Parts 5.1, 5.2, 6.1  
**Target Engine:** Firefox ESR 153.5.1esr  

---

## 1. Problem Statement & Context

In Aegis Browser, the 3-axis security model defines granular levels for **Network (N0–N3)**, **Surface (S1–S4)**, and **Identity (I1–I4)** per Cell.

During Phase 0 runtime testing, **Decision D-008** established an essential architectural reality:
* Preferences that control engine-level attack surface (`javascript.options.baselinejit`, `javascript.options.ion`, `javascript.options.wasm`, `webgl.disabled`) operate at the **Gecko instance / process level**.
* Autoconfig files (`autoconfig.js` and `aegis.cfg`) reside in the shared application directory (`firefox-esr/`).
* Within a single stock Gecko process, SpiderMonkey compiles or interprets JavaScript globally. There is no stock per-tab preference to turn JIT compilation off for Tab A while keeping JIT enabled for Tab B in the same process.
* Consequently, if multiple Cells running at different Surface levels (e.g., Cell 1 at S1 with JIT on, Cell 2 at S3 with JIT off) coexist, a single stock process cannot enforce this division purely via preferences.

This spike evaluates the candidate architectures on the fast path to achieve per-Cell surface and network granularity, presents empirical test findings, analyzes trade-offs and risks, and recommends a design for Phase 2 implementation.

---

## 2. Fast-Path Empirical Test Results

We conducted empirical runtime probes against the running Firefox ESR 153.5.1esr engine to determine what mechanisms work.

### 2.1 Test A: Process-per-Tier Isolation
* **Test:** Launched separate isolated processes via `-profile profiles/aegis-s3` (with locked JIT/WASM off) and a control profile (with JIT/WASM on).
* **Finding:** **VERIFIED.** The S3 process strictly disabled WebAssembly (`WebAssembly is undefined`) and executed JavaScript purely via the interpreter (median execution time: 105 ms vs. 10 ms control, a 10.5x ratio). Memory overhead for an idle secondary ESR instance on Linux was ~180–220 MB RAM.

### 2.2 Test B: Autoconfig Sandbox Environment Access (`VERIFY-S-022`)
* **Hypothesis:** Can `aegis.cfg` read an environment variable or profile directory file to apply `lockPref()` dynamically per process, allowing a single binary installation to support multiple tiers?
* **Probe 1 (`getenv`):**
  ```javascript
  var tier = getenv("AEGIS_SURFACE_TIER");
  if (tier === "S3") {
    lockPref("javascript.options.wasm", false);
    lockPref("javascript.options.baselinejit", false);
    lockPref("javascript.options.ion", false);
  }
  ```
  * **Result:** **VERIFIED EFFECTIVE.**
    * Launched with `AEGIS_SURFACE_TIER=S3`: DOM probe reported `wasm_disabled: true` ("WebAssembly is undefined") and interpreter median 103 ms.
    * Launched with `AEGIS_SURFACE_TIER=S1`: DOM probe reported `wasm_disabled: false` (`validate() = true`) and JIT median 27 ms.
* **Probe 2 (Profile directory file inspection vs. native sandbox `getPref`):**
  * **Initial Spike Report (Flawed Hypothesis):**
    ```javascript
    var profDir = Services.dirsvc.get("ProfD", Components.interfaces.nsIFile);
    var tierFile = profDir.clone();
    tierFile.append("aegis-surface-tier.txt");
    // read file contents via nsIFileInputStream
    ```
    *Correction:* In the initial fast-path spike test, `AEGIS_SURFACE_TIER=S3` was also present in the environment. Because `getenv("AEGIS_SURFACE_TIER")` evaluated first and applied the S3 locks, and because `try...catch` swallowed the `ReferenceError: Services is not defined`, the initial test erroneously recorded Probe 2 as verified.
  * **Empirical Engine Finding:** In Firefox ESR 153.5.1esr with `general.config.sandbox_enabled: true`, Mozilla strictly isolates the autoconfig sandbox from XPCOM: `typeof Services === 'undefined'` and `typeof Components === 'undefined'`. Direct filesystem access via XPCOM is impossible without disabling sandbox security.
  * **Verified Working Solution (`getPref`):** Mozilla's autoconfig sandbox exposes native preference functions (`getPref`, `defaultPref`, `lockPref`, `getenv`). Because Gecko reads and populates preferences from the profile's `user.js` *before* evaluating `aegis.cfg`, a profile-specific tier token can be read natively and safely:
    ```javascript
    var profTier = getPref("aegis.profile.tier");
    ```
    * **Result:** **VERIFIED EFFECTIVE.** Proven at runtime with zero environment variable present (`test_profile_only_tier_without_env_var`). S3 profile locks JIT/WASM off while S1 profile leaves them enabled.

### 2.3 Test C: Container (`contextualIdentity`) & Proxy Behavior for the N Axis
* **Mechanism:** Multi-Account Containers partition client-side storage (cookies, localStorage, indexedDB, cache).
* **Proxy Routing:** Firefox WebExtension API `browser.proxy.onRequest` provides `requestDetails.cookieStoreId`. An extension can inspect the container ID of the request and return:
  * `{ type: "socks", host: "127.0.0.1", port: 9050, proxyDNS: true }` for Tor tabs (`N2`).
  * `{ type: "direct" }` for direct tabs (`N0`).
* **Risks & Fail-Closed Limitations Identified:**
  1. **Gecko Background Network Traffic:** Requests initiated by the browser infrastructure (OCSP revocation checks, captive portal checks, safe browsing / CRLite updates, extension updates) do not carry a tab's `cookieStoreId`. If an N2 container shares a process with direct N0 browsing, background traffic can leak the user's real IP address unless globally suppressed.
  2. **WebRTC Interface Enumeration:** In a single instance, WebRTC (`RTCPeerConnection`) can query system network adapters. Unless `media.peerconnection.ice.proxy_only: true` is locked globally, WebRTC in an N0 tab can expose local network interfaces, compromising network isolation.
  3. **Crash Domain:** A renderer or memory crash caused by malicious content in an untrusted Cell crashes all open Cells across all tiers.

---

## 3. Comparison of Architectural Options

| Metric / Dimension | Option 1: Process-Tiered Isolation (Multi-Process Tiers) | Option 2: Single Process (Containers + Extension Proxy + Content Script S-Filters) | Option 3: Engine Patch (Per-Context JIT & Socket Routing in C++) |
| :--- | :--- | :--- | :--- |
| **Surface (S) Enforcement** | **Hard (Hardware/OS Level).** SpiderMonkey JIT/WASM compiler backend is disabled entirely at process startup for S3/S4 tiers. Zero risk of JIT compiler exploit. | **Weak (Simulated).** Cannot disable JIT/WASM per-tab in SpiderMonkey. Can only block script tags via CSP or content script, leaving JIT engine active. | **Hard (In-Engine).** Patch SpiderMonkey context flags to toggle JIT per `JSContext` / compartment. |
| **Network (N) Isolation** | **Hard (Process Proxy & Firewall).** SOCKS5 proxy with remote DNS and WebRTC disabled locked globally within the Tor process. Can bind to local network namespace. | **Medium.** `browser.proxy.onRequest` routes container HTTP/HTTPS, but background browser traffic and WebRTC require aggressive suppression. | **Hard.** Route each `nsISocketTransport` according to container routing contract. |
| **Memory Footprint** | ~180–250 MB base RAM per running tier (e.g., 2 tiers = ~450 MB; 3 tiers = ~700 MB). Very comfortable on 16 GiB host (~9 GiB free). | Low (~250–350 MB total for one process). | Low (~250–350 MB total for one process). |
| **Implementation Complexity** | **Low to Moderate.** Proven on fast path using `getenv("AEGIS_SURFACE_TIER")` in `aegis.cfg`. Requires workspace / window launcher coordination. | **Low.** Standard WebExtension APIs, but fails hard security requirements for JIT and leak prevention. | **Extremely High.** Hundreds of lines of C++ patches across Gecko and SpiderMonkey; high maintenance burden on ESR rebases. |
| **Fail-Closed Assurance** | **High.** If the proxy daemon is unavailable, the entire S3/Tor process fails closed. No cross-tier leakage. | **Low.** Extension timing races or proxy API failure can silently fall back to direct sockets. | **High.** Engine level enforcement. |
| **UX & Window Management** | Multiple top-level windows (one per active tier), unified via window switcher / launcher or window manager. | Single window with standard tab bar and container color strips. | Single window with standard tab bar. |

---

## 4. Risks and Honest Limitations

1. **Window Management UX:**
   * If a user opens an S1 Cell and an S3 Cell, they are in separate OS windows. Tabs cannot be dragged seamlessly across windows between an S1 process and an S3 process because memory spaces and profile storage are strictly separated.
   * *Mitigation:* The Aegis shell / Command Palette (M2) and Cell Switcher provide instant hotkey switching between tier windows.
2. **Tor Network Leaks in Single-Process Mode:**
   * Single-process container proxying cannot guarantee 100% leak-proof Tor routing against advanced local network adversaries due to Gecko socket process sharing.
   * *Mitigation:* N2/N3 Cells must strictly run in the dedicated isolated network process.
3. **Resource Consumption:**
   * Running 4 simultaneous tiers would consume ~800 MB–1 GB of RAM. On the host system with ~9 GiB free, this uses less than 12% of available memory, which is well within safe operating limits.

---

## 5. Recommendation

We recommend **Option 1: Process-Tiered Architecture (orchestrated via verified autoconfig)**:

1. **Surface Axis (S1–S4):**
   * **Tier Default (S1/S2):** Runs with standard baseline autoconfig (`aegis.cfg`). JIT and WebAssembly enabled; hardened WebGL/media defaults.
   * **Tier Restricted (S3):** Launched with `AEGIS_SURFACE_TIER=S3`. `aegis.cfg` dynamically executes `lockPref("javascript.options.baselinejit", false)`, `lockPref("javascript.options.ion", false)`, `lockPref("javascript.options.wasm", false)`, and `lockPref("webgl.disabled", true)`.
   * **Tier Detonation (S4):** Launched with `AEGIS_SURFACE_TIER=S4`. In addition to S3 locks, active script execution is disabled (`javascript.enabled: false`).
2. **Network Axis (N0–N3):**
   * **N0 / N1:** Handled in the default tier (N1 enforces strict DoH/DoT without plaintext fallback).
   * **N2 (Tor) / N3 (Bridges):** Runs in a dedicated Tor profile instance where `network.proxy.type: 1`, `network.proxy.socks: 127.0.0.1:9050`, `network.proxy.socks_remote_dns: true`, and WebRTC are globally locked, eliminating any possibility of background traffic or WebRTC leaking to direct interfaces.
3. **Identity Axis (I1–I4):**
   * Multi-Account Containers (`cookieStoreId`) provide per-Cell storage partitioning (I2) within each process tier.
   * Ephemeral Cells (I4) use disposable temporary profile paths that are wiped on process exit.

---

## 6. Next Steps (Pending Owner Approval)

Upon your approval:
1. Amend spec Parts 5.1, 5.2, and 6.1 in documentation to formalize the Process-Tiered Cell Architecture.
2. Implement S1 through S4 level configuration files in `config/axes/surface/` with automated runtime enforcement tests.
3. Build the process launcher tool `tools/launch_cell.sh` that maps declared Cell `{N, S, I}` parameters to the appropriate process tier.

> **PAUSE:** Awaiting owner approval on SPIKE-005 before proceeding with implementation.
