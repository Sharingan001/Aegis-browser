# Aegis Browser

[![Aegis CI](https://github.com/Sharingan001/Aegis-browser/actions/workflows/ci.yml/badge.svg)](https://github.com/Sharingan001/Aegis-browser/actions/workflows/ci.yml)
[![Engine: Firefox ESR](https://img.shields.io/badge/engine-Firefox_ESR_153.5.1esr-orange.svg)](https://www.mozilla.org/en-US/firefox/organizations/)
[![License: MPL 2.0](https://img.shields.io/badge/license-MPL_2.0-blue.svg)](https://www.mozilla.org/en-US/MPL/2.0/)
[![Status: Phase 2d Active](https://img.shields.io/badge/status-Phase_2d_Active-brightgreen.svg)](docs/spec/part-13-unified-roadmap.md)

A privacy- and security-first desktop browser based on the **Gecko** engine (Mozilla Firefox ESR). Aegis provides multi-level attack-surface reduction, isolated task-specific **Cells**, adaptive phishing protection (Link Guard), and an explainable, auditable security architecture.

---

## ⚠️ Honest Limits (Safety Boundaries First)

In accordance with the foundational tenets of the Aegis blueprint:
- **No Absolute Anonymity Claims:** No browser configuration, security tier, or Tor circuit guarantees complete anonymity or invulnerability. Aegis claims *reduced cross-site linkability* and *attack surface reduction*, never absolute anonymity.
- **HTTPS ≠ Safe:** HTTPS confirms connection encryption and endpoint identity; it does **not** indicate whether a page is safe, benign, or trustworthy.
- **Expected Web Incompatibility:** High-security tiers (S3 Strict, S4 Static) intentionally disable JIT compilation, WebAssembly, WebGL, and JavaScript. Websites requiring these active technologies will degrade or fail by design.
- **Honest Phishing Limits:** Link Guard employs deterministic, local heuristics and reputation signals. It cannot detect zero-day or expertly crafted targeted phishing lures.
- **RFP Crowd Claim:** Under I2 (Uniform), `privacy.resistFingerprinting` is enabled. This is described as "RFP, intended to resemble Tor Browser defaults, unmeasured". No claim is made that the crowd is matched or that blending is achieved.
- **Pre-Release Research Code:** This codebase is currently under active research and rapid engineering. Do **not** deploy in hostile production environments without external review.

---

## The Three-Axis Security Model

Aegis organizes browser protections along three independent, cumulative axes:

```
                      [S] Surface (Engine Exposure)
                                  ▲
                                  │   S4: Static (No JS, No WebFonts, No WebRTC)
                                  │   S3: Strict (No JIT, No WASM, No WebGL)
                                  │   S2: Guarded (HTTPS-Only, Autoplay Muted)
                                  │   S1: Standard Baseline
                                  │
                                  └────────────────────────► [I] Identity (Fingerprinting)
                                 /    I1: Native (unperturbed)
                                /     I3: Site-Keyed Noise (FPP per-site canvas noise)
                               /      I2: Uniform (RFP, intended to resemble, unmeasured)
                              ▼       I4: Minimal-Signals (passive non-script signals hardened)
                     [N] Network (Routing)
                         N0: Direct
                         N1: Encrypted DNS (Strict DoH)
                         N2: Tor (3-Hop Onion + Remote DNS)
                         N3: Tor + User Bridges
```

### 1. Axis S: Surface (What engine features a page can reach)
* **S1 (Standard):** Baseline security. WebGL, WebAssembly, and JIT compilers enabled. Mixed content blocked; third-party cookie partitioning enforced (dFPI).
* **S2 (Guarded):** HTTPS-only mode enforced; audible autoplay blocked; WebRTC ICE candidates restricted to default local address.
* **S3 (Strict):** JIT compilers (Baseline & IonMonkey) locked **OFF** (pure interpreter); WebAssembly locked **OFF**; WebGL locked **OFF**; MathML and OpenType-SVG fonts disabled.
* **S4 (Static / Detonation):** Client-side JavaScript completely disabled (`<noscript>` beacon verified); remote web fonts disabled; WebRTC completely disabled.

### 2. Axis N: Network (Where traffic is routed)
* **N0 (Direct):** Standard network stack.
* **N1 (Encrypted DNS):** Strict DNS-over-HTTPS (DoH) with zero silent plaintext fallback.
* **N2 (Tor):** All traffic routed through a 3-hop Tor SOCKS proxy with remote DNS resolution and strict leak isolation.
* **N3 (Tor + Bridges):** N2 routing augmented with user-configured Pluggable Transports.

### 3. Axis I: Identity (What fingerprinting surfaces observe)
* **I1 (Native):** Standard platform headers and capabilities; no fingerprint noise. Referer: full URL; WebRTC: host candidates exposed.
* **I3 (Site-Keyed Noise):** Gecko FPP (`privacy.fingerprintingProtection`) with site-keyed canvas noise. Remote overrides locked false (D-012). Referer trimmed to origin. WebRTC host candidates suppressed. Preserves local timezone and native window geometry.
* **I2 (Uniform):** `privacy.resistFingerprinting` enabled. UTC timezone, quantized viewport (letterboxing), ~16.67ms timer clamping, spoofed hardware metrics. RFP, intended to resemble Tor Browser defaults, unmeasured crowd.
* **I4 (Minimal-Signals):** Extends I2 with hardening of **non-script passive signals** reachable even when JavaScript is disabled: Accept-Language header normalized to `en-US, en`; remote font loading disabled; cross-origin referrer policy restricted to origin-only. CSS media query normalization (color scheme, resolution, pointer) tracked as OPEN (no pref available in ESR 153, Phase 3).

> **I4 design rationale:** Under S4 (JavaScript disabled), script APIs (`navigator.getGamepads`, etc.) are unreachable regardless of any pref, so pref-gating them in I4 would be security theater. I4 targets passive HTTP and CSS-visible signals that remain active in a static document renderer.

---

## Canonical Presets & Process-Tiered Architecture

Runtime verification on Firefox ESR 153.5.1esr confirmed that compiler and proxy primitives operate at the process level (Decision **D-008**). Under Specification Amendment **A-001**, Aegis enforces levels using a **Process-Tiered Architecture** mapped into canonical presets:

| Preset | N | S | I | Storage | Notes |
| :--- | :---: | :---: | :---: | :--- | :--- |
| **standard** | N1 | S1 | I3 | Persistent | Daily browsing; FPP site-keyed noise |
| **guarded** | N1 | S2 | I3 | Persistent | HTTPS-only; FPP site-keyed noise |
| **banking** | N1 | S2 | I3 | Persistent | Extensions off instance-wide (D-014); dedicated profile |
| **strict** | N1 | S3 | I2 | Session | JIT/WASM/WebGL off; RFP, unmeasured crowd |
| **research_tor** | N2 | S1 | I2 | Session | Tor; RFP (R2 enforced) |
| **research_strict** | N2 | S3 | I2 | Session | Tor + JIT off; crowd-splitting ACK required |
| **detonation** | N2 | S4 | I2 | Ephemeral RAM | JS off over Tor; R2 enforced |
| **detonation_local** | N1 | S4 | I4 | Ephemeral RAM | JS off, local only; passive signals hardened |

**Concurrency cap:** Maximum 4 concurrently running instances (default, configurable). Presets may exceed 4 and spawn on demand.

**Omitted identity fail-closed:** If `AEGIS_IDENTITY_TIER` is not supplied by the launcher and no profile token is set, the cfg **fails closed to I4**. Auto-resolution from the surface tier is prohibited: it could yield I3 on a Tor surface tier, violating Rule R2 (Tor mode strictly locks Identity to I2). Only the launcher may select a tier, from the preset table.

**Combination rules:** All 64 combinations of (S × I × N) are evaluated by `tools/tier_matrix.py`. 8 are ALLOWED (exact preset match), 26 are MAPPED (promoted to a preset without downgrade), and 30 are REJECTED with a security rationale. No mapping may decrease the S or I protection level.

---

## What is Built vs. What is Not Yet Built

### ✅ Built, verified, and committed

| Component | Files | Status |
| :--- | :--- | :--- |
| Autoconfig compiler (dual-axis: S + I) | `tools/generate_autoconfig.py`, `config/autoconfig/aegis.cfg` | Generates and drift-checks from JSON specs |
| Surface axis S1..S4 definitions | `config/axes/surface/s*.json` | Cumulative, verified at runtime |
| Identity axis I1..I4 definitions | `config/axes/identity/i*.json` | Cumulative, verified at runtime |
| Multi-axis 4×4×4 combination matrix | `tools/tier_matrix.py` | 64 combinations classified; property test verifies zero downgrades |
| Enterprise policy (tier-independent) | `config/policy/policies.json` | Telemetry, tracking protection, no tier conflicts |
| Runtime test suite (Surface + Identity) | `tests/axes/test_surface_levels.py`, `test_identity_levels.py`, `test_tier_failclosed.py` | Marionette live pref queries + behavioral probes + fail-closed tests |
| Preset-vs-cfg consistency test | `test_identity_levels.py::test_preset_identity_matches_cfg` | Asserts every preset identity is a valid cfg tier; enforces R2 for Tor presets |
| Omitted-identity fail-closed test | `test_identity_levels.py::test_identity_omitted_fails_closed_per_surface` | Proves I4 fail-closed on every surface tier when identity is unset |
| Spec coverage matrix (Part 5.2 + 5.3) | `docs/SPEC_COVERAGE.md` | Four-level grades: Behavior-tested / Pref verified live / Config only / Not yet |
| Cell Indicator WebExtension | `ui/extensions/cell-indicator/` | Placeholder posture display with honest language lint |
| Prototype modules | `prototypes/aegis_modules.py` | Reference implementations: LinkCleaner, DownloadInspector, SessionSweeper, SiteXray |
| SPIKE-005 (surface granularity) | `docs/spikes/SPIKE-005-surface-granularity.md` | Process-tiered hypothesis, approved as working design |
| SPIKE-006 (launcher/orchestrator) | `docs/spikes/SPIKE-006-launcher-orchestrator.md` | Design only; no implementation |
| Spec amendments A-001..A-003 | `docs/spec-amendments/` | PROPOSED; require ratification |
| Decisions log D-001..D-014 | `docs/DECISIONS.md` | Full record of all architectural decisions |

### 🔲 Not yet built

| Component | Spec Reference | Phase |
| :--- | :--- | :--- |
| Launcher / orchestrator (process spawning, IPC, URL hand-off) | SPIKE-006, A-001 | Phase 3 |
| Tor integration (N2/N3 network axis, circuit isolation) | SPIKE-004, Part 5.4 | Phase 3 |
| Tier-1 built-in extensions (link-cleaner, download-inspector, session-sweeper, site-xray, command-palette) | Part 5.8, Module Catalog | Phase 2d (in progress) |
| Engine build from source (patches, JIT overrides) | D-010, BUILD.md | Phase 3 |
| CSS media query normalization for I4 (color scheme, resolution, pointer) | VERIFY-I-010 | Phase 3 |
| WebRTC ICE candidate behavioral test (actual candidate inspection) | VERIFY-I-006 | Phase 2d |
| S4 per-origin JavaScript allow-list | SPIKE-001, Part 5.2 row 14 | Phase 3 |
| Per-Cell storage (session/ephemeral RAM profiles) | SPIKE-006, Part 5.2 row 15 | Phase 3 |
| Extension policy enforcement (S3 built-in only, S4 none) | VERIFY-S-015, Part 5.2 row 16 | Phase 2d |
| Permission matrix (notifications, location, camera, mic deny) | VERIFY-S-005 | Phase 2d |
| HTTPS-first upgrade behavioral test | VERIFY-S-002, Part 5.2 row 1 | Phase 2d |
| Download quarantine browser integration | VERIFY-S-016, Part 5.2 row 8 | Phase 2d |

---

## Repository Structure

```
Aegis/
├── .github/
│   └── workflows/ci.yml            # Automated CI workflow for tests & static checks
├── config/
│   ├── autoconfig/
│   │   ├── autoconfig.js           # Mozilla autoconfig loader (sandbox enabled)
│   │   └── aegis.cfg               # Generated ASCII autoconfig (lockPref & fail-closed logic)
│   ├── axes/
│   │   ├── surface/                # s1.json .. s4.json (Surface axis S1..S4)
│   │   └── identity/               # i1.json .. i4.json (Identity axis I1..I4)
│   └── policy/
│       └── policies.json           # Tier-independent Mozilla enterprise policies
├── docs/
│   ├── spec/                       # Complete 20-part master blueprint
│   ├── spec-amendments/
│   │   ├── A-001.md                # Process-Tiered Architecture (PROPOSED)
│   │   ├── A-002.md                # I3 redefined as site-keyed noise / FPP (PROPOSED)
│   │   └── A-003.md                # Anchored Cells use I3 + extension isolation (PROPOSED)
│   ├── spikes/
│   │   ├── SPIKE-005-surface-granularity.md
│   │   └── SPIKE-006-launcher-orchestrator.md
│   ├── design-notes/
│   │   └── PHASE2C_PRESETS_AND_TIER_MAPPING.md
│   ├── BUILD.md                    # Environment preparation and fast-path setup
│   ├── DECISIONS.md                # Architectural decisions log (D-001 – D-014)
│   ├── LICENSES_AND_TRADEMARKS.md  # Legal audit and Mozilla trademark compliance
│   ├── SPEC_COVERAGE.md            # Part 5.2 & 5.3 implementation & verification matrix
│   └── VERIFY.md                   # Living verification log against pinned ESR
├── prototypes/
│   ├── aegis_modules.py            # Reference implementations (LinkCleaner, DownloadInspector, SessionSweeper, SiteXray)
│   ├── aegis_psl.py                # Public Suffix List multi-tenant isolation engine
│   ├── linkguard_prototype.py      # Link Guard heuristics & lure scoring
│   └── test_aegis.py               # 27 unit tests verifying prototype functionality
├── tests/
│   ├── axes/
│   │   ├── test_surface_levels.py  # Surface S1..S4 runtime enforcement & Marionette assertions
│   │   ├── test_identity_levels.py # Identity I1..I4 runtime enforcement, fail-closed, FPP override
│   │   ├── test_tier_failclosed.py # Surface fail-closed tier validation (unset, invalid, mismatch)
│   │   └── test_tier_matrix.py     # 4×4×4 combination matrix; property: zero downgrades
│   ├── fixtures/                   # Test pages, mock beacons, and micro-benchmarks
│   ├── tools/
│   │   └── local_test_server.py    # Local HTTP test server fixture handler
│   ├── ui/
│   │   └── test_cell_indicator.py  # UI, theme, manifest, and honest language lint tests
│   └── runner.sh                   # Master local test runner (11 test suites)
├── tools/
│   ├── generate_autoconfig.py      # Dual-axis (S+I) generator & drift checker
│   ├── tier_matrix.py              # 4×4×4 multi-axis combination matrix engine
│   └── setup_fastpath_profile.sh   # ESR fast-path profile setup & verification tool
├── ui/
│   ├── extensions/cell-indicator/  # Built-in Cell Indicator WebExtension prototype
│   └── theme/                      # Aegis branding palette, manifest, and icons
├── upstream/
│   └── VERSION                     # Pinned engine version (153.5.1esr)
├── CLAUDE.md                       # Development instructions and reporting constraints
└── SECURITY.md                     # Security policy and vulnerability disclosure guide
```

---

## Getting Started & Fast-Path Setup

### Prerequisites
- Linux x86_64 desktop (tested on Arch Linux / Ubuntu).
- Python 3.10+ with standard library.
- Git, GnuPG, and standard POSIX utilities (`curl`, `awk`, `tar`).

### Fast-Path Environment Setup
To download and run against the verified, pinned Firefox ESR 153.5.1esr binary without compiling from source:

```bash
# 1. Download Firefox ESR tarball and cryptographic checksums
mkdir -p downloads
cd downloads
curl -LO https://ftp.mozilla.org/pub/firefox/releases/153.5.1esr/linux-x86_64/en-US/firefox-153.5.1esr.tar.bz2
curl -LO https://ftp.mozilla.org/pub/firefox/releases/153.5.1esr/SHA256SUMS
curl -LO https://ftp.mozilla.org/pub/firefox/releases/153.5.1esr/SHA256SUMS.asc

# 2. Verify SHA-256 hash and Mozilla GPG signature
sha256sum --ignore-missing -c SHA256SUMS
gpg --verify SHA256SUMS.asc SHA256SUMS

# 3. Extract into ignored firefox-esr/ directory
cd ..
tar -xf downloads/firefox-153.5.1esr.tar.bz2
mv firefox firefox-esr

# 4. Provision fast-path configuration and profiles
bash tools/setup_fastpath_profile.sh
```

---

## Running Verification Tests

Aegis includes automated tests across unit logic, static compliance, and live browser runtime enforcement:

### 1. Master Test Suite (All 11 Check Suites)
```bash
bash tests/runner.sh
```
Executes:
1. Prototype unit tests (27 tests: PSL, Link Guard, Modules, Session Sweeper).
2. `docs/VERIFY.md` format and section verification.
3. `docs/DECISIONS.md` existence and format validation.
4. `upstream/VERSION` integrity check.
5. `config/policy/policies.json` validation (disallows unauthorized underscore keys).
6. Autoconfig ASCII check & Single-Source-of-Truth drift verification (`tools/generate_autoconfig.py --check`).
7. `docs/LICENSES_AND_TRADEMARKS.md` presence and legal requirement check.
8. UI, theme, branding, and Cell Indicator tests (including honest language lint).
9. Surface levels runtime enforcement (S1..S4), Marionette effective pref queries, and fail-closed tests.
10. Multi-axis 4×4×4 combination matrix tests (all rules verified, zero-downgrade property).
11. Identity levels runtime enforcement (I1..I4), FPP override probes, omitted-identity fail-closed, and preset-vs-cfg consistency.

### 2. Python Prototype Unit Tests
```bash
cd prototypes && python3 -m unittest test_aegis -v
```

### 3. Autoconfig Drift Check
```bash
python3 tools/generate_autoconfig.py --check
```

### 4. Individual Test Suites
```bash
python3 -m unittest tests/axes/test_identity_levels.py -v
python3 -m unittest tests/axes/test_tier_matrix.py -v
```

---

## Security & Vulnerability Reporting

If you discover a vulnerability or security bypass in Aegis:
- **Do not open a public GitHub issue.**
- Review our disclosure guidelines in [`SECURITY.md`](SECURITY.md).
- Follow responsible disclosure practices.

---

## License

Aegis Browser is free and open-source software licensed under the **Mozilla Public License 2.0 (MPL-2.0)**. See [`docs/LICENSES_AND_TRADEMARKS.md`](docs/LICENSES_AND_TRADEMARKS.md) for full licensing, third-party component acknowledgments, and Mozilla trademark guidelines.
