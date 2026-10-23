# Aegis Browser

[![Aegis CI](https://github.com/Sharingan001/Aegis-browser/actions/workflows/ci.yml/badge.svg)](https://github.com/Sharingan001/Aegis-browser/actions/workflows/ci.yml)
[![Engine: Firefox ESR](https://img.shields.io/badge/engine-Firefox_ESR_153.5.1esr-orange.svg)](https://www.mozilla.org/en-US/firefox/organizations/)
[![License: MPL 2.0](https://img.shields.io/badge/license-MPL_2.0-blue.svg)](https://www.mozilla.org/en-US/MPL/2.0/)
[![Status: Phase 2a Active](https://img.shields.io/badge/status-Phase_2a_Active-brightgreen.svg)](docs/spec/part-13-unified-roadmap.md)

A privacy- and security-first desktop browser based on the **Gecko** engine (Mozilla Firefox ESR). Aegis provides multi-level attack-surface reduction, isolated task-specific **Cells**, adaptive phishing protection (Link Guard), and an explainable, auditable security architecture.

---

## ⚠️ Honest Limits (Safety Boundaries First)

In accordance with the foundational tenets of the Aegis blueprint:
- **No Absolute Anonymity Claims:** No browser configuration, security tier, or Tor circuit guarantees complete anonymity or invulnerability. Aegis claims *reduced cross-site linkability* and *attack surface reduction*, never absolute anonymity.
- **HTTPS $\neq$ Safe:** HTTPS confirms connection encryption and endpoint identity; it does **not** indicate whether a page is safe, benign, or trustworthy.
- **Expected Web Incompatibility:** High-security tiers (S3 Strict, S4 Static) intentionally disable JIT compilation, WebAssembly, WebGL, and JavaScript. Websites requiring these active technologies will degrade or fail by design.
- **Honest Phishing Limits:** Link Guard employs deterministic, local heuristics and reputation signals. It cannot detect zero-day or expertly crafted targeted phishing lures.
- **Pre-Release Research Code:** This codebase is currently under active research and rapid engineering. Do **not** deploy in hostile production environments without external review.

---

## The Three-Axis Security Model

Aegis organizes browser protections along three independent, cumulative axes:

```
                      [S] Surface (Engine Exposure)
                                  ▲
                                  │   S4: Static (No JS, No WebFonts)
                                  │   S3: Strict (No JIT, No WASM, No WebGL)
                                  │   S2: Guarded (HTTPS-Only, Autoplay Muted)
                                  │   S1: Standard Baseline
                                  │
                                  └────────────────────────► [I] Identity (Fingerprinting)
                                 /    I1: Native
                                /     I2: Uniform (RFP / Normalization)
                               /      I3: Cell-Seeded Randomization
                              ▼       I4: Minimal-API (High-Entropy Blocked)
                     [N] Network (Routing)
                         N0: Direct
                         N1: Encrypted DNS (Strict DoH)
                         N2: Tor (3-Hop Onion + Remote DNS)
                         N3: Tor + User Bridges
```

### 1. Axis S: Surface (What engine features a page can reach)
* **S1 (Standard):** Baseline security. WebGL, WebAssembly, and JIT compilers enabled. Mixed content blocked; third-party cookie partitioning enforced (dFPI).
* **S2 (Guarded):** HTTPS-only mode enforced; audible autoplay blocked; WebRTC ICE candidates restricted to default local address.
* **S3 (Strict):** JIT compilers (Baseline & IonMonkey) locked **OFF** (pure interpreter execution); WebAssembly locked **OFF**; WebGL locked **OFF**; MathML and OpenType-SVG fonts disabled.
* **S4 (Static / Detonation):** Client-side JavaScript completely disabled (`<noscript>` beacon verified); remote web fonts disabled; WebRTC completely disabled.

### 2. Axis N: Network (Where traffic is routed)
* **N0 (Direct):** Standard network stack.
* **N1 (Encrypted DNS):** Strict DNS-over-HTTPS (DoH) with zero silent plaintext fallback.
* **N2 (Tor):** All traffic routed through a 3-hop Tor SOCKS proxy with remote DNS resolution and strict leak isolation.
* **N3 (Tor + Bridges):** N2 routing augmented with user-configured Pluggable Transports.

### 3. Axis I: Identity (What fingerprinting surfaces observe)
* **I1 (Native):** Standard platform headers and capabilities.
* **I2 (Uniform):** Engine-level fingerprinting protection (`privacy.resistFingerprinting`) normalizing canvas, audio, timezone, user-agent, and screen dimensions.
* **I3 (Cell-Seeded):** Seeded per-Cell noise ensuring cross-site unlinkability while maintaining intra-session stability.
* **I4 (Minimal-API):** Total lockdown of high-entropy hardware APIs (gamepad, sensors, device enumeration).

---

## Canonical Presets & Process-Tiered Architecture

Runtime verification on Firefox ESR 153.5.1esr confirmed that compiler and proxy primitives operate at the process level (Decision **D-008**). Under Specification Amendment **A-001**, Aegis enforces levels using a **Process-Tiered Architecture** mapped into four canonical presets:

| Preset Name | N-Axis | S-Axis | I-Axis | Storage Isolation | Engine Execution State |
| :--- | :---: | :---: | :---: | :--- | :--- |
| **Standard** | N0 | S1 | I1 | Persistent | Full JIT & WASM enabled; WebGL active |
| **Guarded / Strict** | N1 | S2–S3 | I2 | Persistent / Session | HTTPS-only; S3 locks JIT/WASM/WebGL off |
| **Research / Tor** | N2 | S3 | I2 | Session Container | 3-hop Tor; remote DNS; JIT & WASM locked off |
| **Detonation** | N2/N1 | S4 | I4 | Ephemeral (RAM `/dev/shm`) | JavaScript disabled; static document rendering |

---

## Current Project Status & Achievements

### Phase 0: Scaffolding & Unmodified Baseline (Completed)
- [x] Pinned baseline engine: **Mozilla Firefox ESR 153.5.1esr (64-bit Linux x86_64)**.
- [x] Cryptographic verification: Source tarball verified against Mozilla Software Releases signing key (`14F2 6682 D091 6CDD 81E3 7B6D 61B7 B526 D98F 0353`).
- [x] Fast-path deployment script: `tools/setup_fastpath_profile.sh` validates version and provisions local profiles.
- [x] Prototype test suite: 27 unit tests ported and verified in `prototypes/test_aegis.py` (Link Guard evaluation, PSL multi-tenant isolation, session sweeper, and download quarantine).
- [x] Continuous Integration: GitHub Actions pipeline (`.github/workflows/ci.yml`) active and running all static, policy, and unit tests.

### Phase 1a: Legal Audit, Branding & UI Scaffolding (Completed)
- [x] Legal & Trademark audit: Completed in `docs/LICENSES_AND_TRADEMARKS.md` covering MPL 2.0 obligations, Mozilla trademark restrictions, and third-party dependencies.
- [x] Visual Identity & Dark Theme: Aegis branding palette and high-resolution icons (16, 32, 48, 128px) in `ui/theme/`.
- [x] Cell Indicator WebExtension: Built-in indicator harness in `ui/extensions/cell-indicator/` utilizing an abstract data model (`cell -> {N, S, I}`), visible placeholder disclosures ("Posture is a declared placeholder; not enforced"), and zero false security claims.
- [x] Phase 1b Source Build Deferral: Formally recorded in Decision **D-010** to preserve disk and compile bandwidth until engine patches are required.

### Phase 2a: Surface Levels, Generator & Runtime Verification (Completed)
- [x] Separation of Policy Scope: Restricted `config/policy/policies.json` strictly to tier-independent policies; eliminated conflicts with S1/S2 WebGL and HTTPS-only defaults.
- [x] Single Source of Truth Generator: Implemented `tools/generate_autoconfig.py` to compile `config/axes/surface/*.json` into ASCII-only `config/autoconfig/aegis.cfg` with strict cumulativity verification ($S_4 \supseteq S_3 \supseteq S_2 \supseteq S_1$).
- [x] CI Drift Detection: Added `tools/generate_autoconfig.py --check` into `tests/runner.sh` to halt builds on any manual configuration drift.
- [x] Autoconfig Sandbox Integrity: Enforced `general.config.sandbox_enabled: true`; tier resolution utilizes native sandbox primitives `getenv("AEGIS_SURFACE_TIER")` and `getPref("aegis.profile.tier")` with zero XPCOM exposure.
- [x] Fail-Closed Tier Lockdown: Verified that unset, invalid, or mismatched tier tokens immediately fail closed to S4 minimal surface.
- [x] Marionette Live Assertions: Replaced placeholder tests with live Gecko chrome preference queries; added AST assertion inspection (`test_all_test_methods_have_assertions`) guaranteeing zero empty tests.
- [x] Spec Coverage Matrix: Completed full 17-row audit of Part 5.2 in `docs/SPEC_COVERAGE.md`.
- [x] Empirical Memory Footprint: Recorded multi-process memory usage (~596 MB RSS under 3 local tabs) as an empirical lower bound in Decision **D-011**.

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
│   ├── axes/surface/
│   │   ├── s1.json                 # S1 Standard tier specification
│   │   ├── s2.json                 # S2 Guarded tier specification (extends S1)
│   │   ├── s3.json                 # S3 Strict tier specification (extends S2)
│   │   └── s4.json                 # S4 Static tier specification (extends S3)
│   └── policy/
│       └── policies.json           # Tier-independent Mozilla enterprise policies
├── docs/
│   ├── spec/                       # Complete 20-part master blueprint
│   ├── spec-amendments/
│   │   └── A-001.md                # Proposed Process-Tiered Architecture amendment
│   ├── spikes/
│   │   ├── SPIKE-005-surface-granularity.md
│   │   └── SPIKE-006-launcher-orchestrator.md
│   ├── BUILD.md                    # Environment preparation and fast-path setup
│   ├── DECISIONS.md                # Complete architectural decisions log (D-001 – D-011)
│   ├── LICENSES_AND_TRADEMARKS.md  # Legal audit and Mozilla trademark compliance
│   ├── SPEC_COVERAGE.md            # Spec Part 5.2 implementation & verification matrix
│   └── VERIFY.md                   # Living verification log against pinned ESR
├── prototypes/
│   ├── aegis_modules.py            # Reference implementations of core Aegis modules
│   ├── aegis_psl.py                # Public Suffix List multi-tenant isolation engine
│   ├── linkguard_prototype.py      # Link Guard heuristics, lure scoring & clipboard checks
│   └── test_aegis.py               # 27 unit tests verifying prototype functionality
├── tests/
│   ├── axes/
│   │   ├── test_surface_levels.py  # Runtime enforcement & Marionette effective pref assertions
│   │   └── test_tier_failclosed.py # Runtime fail-closed tier validation
│   ├── fixtures/                   # Test pages, mock beacons, and micro-benchmarks
│   ├── tools/
│   │   └── local_test_server.py    # Local HTTP test server fixture handler
│   ├── ui/
│   │   └── test_cell_indicator.py  # UI, theme, manifest, and honest language lint tests
│   └── runner.sh                   # Master local test runner (9 test suites)
├── tools/
│   ├── generate_autoconfig.py      # Single source of truth generator & drift checker
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

### 1. Master Test Suite (All 9 Check Suites)
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

### 2. Python Prototype Unit Tests
```bash
cd prototypes && python3 -m unittest test_aegis -v
```

### 3. Autoconfig Drift Check
```bash
python3 tools/generate_autoconfig.py --check
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
