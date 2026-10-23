# Aegis Browser — Design Decisions

Format: ID | Date | Decision | Why | Alternatives considered | Open questions

---

## D-001 — 2026-10-23 — Engine choice: Gecko (Firefox ESR)

**Decision:** Use Gecko (Firefox ESR) as the sole browser engine.

**Why:**
- Hard requirement: no Chromium, Blink, Electron, CEF, or Chromium WebView.
- Gecko has strong privacy/anti-tracking foundations, process isolation, RLBox library
  sandboxing, enterprise policy mechanism, large extension API, and a known path used by
  hardened forks (Tor Browser, Mullvad Browser, LibreWolf).
- The ESR line provides ~18 months of security support per major version.

**Alternatives:**
- WebKit: weaker cross-platform story for a Linux-first project.
- Servo/Ladybird: pre-production; research only.
- Custom engine: excluded (non-goal, spec section 1.4).

**Open questions:** none at engine-choice level.

**Spec reference:** Part 2.

---

## D-002 — 2026-10-23 — Pinned ESR version: 153.5.1esr

**Decision:** Pin to Firefox ESR **153.5.1** as the baseline for Phase 0.

**Why:**
- Confirmed as current ESR on 2026-10-23 via Mozilla's organizations/all/ page
  (`data-esr-versions="153.5.1"`).
- Source: https://www.mozilla.org/en-US/firefox/organizations/all/ (live fetch).
- SHA-256 of linux-x86_64/en-US tarball:
  `e289bdc532decf2b54dea9b5ac64cf6f84a62eeec4d4a9ec2f69590f61b0ff1c`

**Context:**
- ESR 128 reached EOL September 2025 (per owner; consistent with Mozilla's ~18-month cycle).
- ESR 140 reached EOL 2026-09-29 (per owner; confirmed consistent with calendar).
- ESR 153 initial release: 2026-07-21 (per owner).

**Alternatives:** pinning 140 (EOL) is not acceptable.

**Open questions:** none.

---

## D-003 — 2026-10-23 — Fast path first; no source build in Phase 0

**Decision:** Phase 0 uses a stock Firefox ESR 153.5.1 tarball extracted to `firefox-esr/`
(not system-installed), with enterprise policies and autoconfig applied. Source build is
deferred until the fast path is working and explicitly approved.

**Why:**
- Source build is slow (hours) and consumes tens of GB of disk. The fast path can verify
  all axis-level policy logic first.
- System Firefox (156) must not be touched.
- Launched with: `firefox-esr/firefox -profile profiles/aegis-fastpath --no-remote`
- Policies file: `firefox-esr/distribution/policies.json`
- Autoconfig: `firefox-esr/defaults/pref/autoconfig.js` + `firefox-esr/aegis.cfg`

**Alternatives:** building from source immediately (rejected per owner instruction).

**Open questions:** owner must explicitly approve before any source build begins.

---

## D-004 — 2026-10-23 — S4 JavaScript per-origin control: design spike deferred to Phase 2

**Decision:** The S4 per-origin JavaScript allow-list is an open design problem. Two options
exist: (a) a built-in system extension with elevated privileges (Tor Browser / NoScript
approach), or (b) an engine patch. A design spike comparing both will be done in Phase 2.
Phase 0 only records the question.

**Why:** Firefox has no public per-origin script-control API for ordinary extensions (confirmed
in spec Part 5, "Engineering risk" note). Neither option can be decided without first
evaluating ESR 153's system extension capabilities and their implications for the patch set.

**Alternatives:** not investigated yet.

**Open questions:** SPIKE-001 — see docs/VERIFY.md.

**Spec reference:** Part 5.2, S axis, JavaScript row.

---

## D-005 — 2026-10-23 — I3 seeded noise: evaluation deferred to Phase 2

**Decision:** Evaluate what Firefox ESR 153's `privacy.fingerprintingProtection` prefs
already provide (seeded randomization, normalization) before designing a custom I3
implementation. Phase 0 lists the relevant pref names as VERIFY items. Phase 2 does the
evaluation and reports.

**Why:** The spec (Part 5.3) says "research first: check whether the engine's newer
fingerprinting protection already provides seeded randomization before building your own."

**Open questions:** VERIFY-006 through VERIFY-009 — see docs/VERIFY.md.

**Spec reference:** Part 5.3, I3 design note.

---

## D-006 — 2026-10-23 — Repository root: ./ (Ageis)

**Decision:** The cloned repository directory (`./`) is the repository root. No rename to `aegis-browser/` is
proposed at this time; the directory name does not affect the build or tests.

**Why:** Owner instruction. Renaming requires explicit approval.

**Open questions:** none.

---

## D-007 — 2026-10-23 — CI: local pre-commit hook + GitHub Actions YAML (not yet active)

**Decision:** Phase 0 ships `tests/runner.sh` (local), a pre-commit hook calling it, and
`build/ci-github.yml` (GitHub Actions YAML, not pushed or activated). Hosted CI is
deferred until the owner sets up a remote repository.

**Why:** No hosted CI system exists yet. Local hook gives immediate feedback.

**Open questions:** owner to decide when to enable the GitHub Actions workflow.

---

## D-008 — 2026-10-23 — Instance-wide scope of autoconfig & locked prefs vs per-Cell Surface levels

**Decision:** Document that autoconfig (`aegis.cfg`) and Firefox locked preferences operate
at the instance/process level. Because autoconfig files reside in the application directory
shared by all profiles using that binary, and engine preferences (`javascript.options.baselinejit`,
`ion`, `wasm`) are global process-wide primitives in Gecko, per-Cell Surface levels (S1–S4)
cannot be enforced by these preferences alone within a single Gecko instance.

**Options for Phase 2 spike (SPIKE-005):**
1. **Separate instance per surface tier:** Launch an isolated process per active S level
   (e.g., S3 instance with JIT disabled, S1 instance with JIT enabled).
2. **Per-profile autoconfig:** Key autoconfig logic to an environment variable or profile
   file. (Requires verifying `VERIFY-S-022`: check whether `getenv` or profile path inspection
   is permitted in the autoconfig sandbox).
3. **Tor-Browser-style global level with restart:** Security level applies globally with
   restart prompt upon change.
4. **Engine patch:** Patch SpiderMonkey / Gecko runtime to evaluate JIT/WASM policy per
   browsing context or container rather than process-wide flags.

**Status:** Marked as an open design spike for early Phase 2. The specification text remains
unmodified, but Parts 5.1, 5.2, and 6.1 are flagged as requiring architectural amendment once
SPIKE-005 is decided.

## D-009 — 2026-10-23 — Phase 0 Approval and Carried-Forward Items

**Decision:** Phase 0 is approved. Four items are carried forward and resolved immediately
as part of completing Phase 0 wrap-up:
1. **CI Activation:** Activate the GitHub Actions workflow (.github/workflows/ci.yml)
   for unit tests and static checks only (no live browser runtime). Verify the initial run.
2. **Build Guide Reproducibility:** Dry-run docs/BUILD.md Part A in an isolated test directory,
   identify missing prerequisites or unstated assumptions, and amend BUILD.md accordingly.
3. **S3 Profile Isolation as Named Fixture:** The default profile (`profiles/aegis-default`)
   must not lock JIT or WebAssembly off, as the default experience must remain functional
   for daily browsing. S3 controls (JIT/WASM disabled) are isolated to a named fixture
   (`profiles/aegis-s3` or invoked via fixture scripts) used for verification tests.
4. **Robust JIT Microbenchmark:** Make the JIT enforcement timing test robust by running
   multiple iterations, computing the median, using a relative ratio threshold against
   the control profile, and explicitly documenting hardware/system load flakiness boundaries.

**Why:** Ensures reproducible baseline, non-destructive defaults, and deterministic CI.

**Spec references:** Parts 10, 13, 14, 16.
---

## D-010 — 2026-10-23 — Phase 1b Deferral and mozconfig Validation Policy

**Decision:** Phase 1b compiled source build is deferred. Do not download source archives or
initiate source compilation at this time. Prior to any future source compilation:
1. **Pre-flight configure validation:** Run `./mach configure` (or dry configure check) to validate
   all mozconfig options against the engine's build system before launching a full compile.
   Specifically verify whether `--disable-telemetry` is a valid configure option in ESR 153
   (modern Gecko typically regulates telemetry via channel/branding and prefs rather than a configure flag)
   and whether exporting `RUSTFLAGS` is accepted or interferes with `mach` build orchestration.
2. **Empirical resource measurement:** All disk (~45-55 GB), RAM (~6-7.5 GB), and time (~50-75 min)
   estimates are recorded strictly as planning estimates and must be measured empirically on the first
   approved run.

**Why:** Avoids premature multi-gigabyte downloads and prevents long compilation aborts caused by
invalid mozconfig flags on a constrained-disk system (~86 GB free).

**Spec reference:** Part 16, Part 18 (Phase 1b).
---

## D-011 — 2026-10-23 — Phase 2a Surface Architecture, Single Source of Truth Generator, and Memory Lower Bound

**Decision:**
1. **Separation of Policy Scope:** Enterprise policy (`config/policy/policies.json`) is strictly restricted to tier-independent controls (`DisableTelemetry`, `DisableFirefoxStudies`, `DisablePocket`, `EnableTrackingProtection`). Tier-specific surface controls (`webgl.disabled`, `dom.security.https_only_mode`, etc.) must never be placed in `policies.json` because enterprise policies apply unconditionally across all instances and profiles, overriding autoconfig.
2. **Single Source of Truth (`tools/generate_autoconfig.py`):** `config/axes/surface/s*.json` is the sole source of truth for surface levels. `tools/generate_autoconfig.py` validates strict cumulativity across tiers (S4 >= S3 >= S2 >= S1 with documented overrides), generates ASCII-only `config/autoconfig/aegis.cfg`, and provides a `--check` flag enforced by CI to prevent configuration drift.
3. **Autoconfig Sandbox Integrity:** `general.config.sandbox_enabled: true` is strictly enforced. In the ESR 153 autoconfig sandbox, XPCOM (`Components` and `Services`) is isolated/undefined. Tier selection is performed safely using native sandbox primitives: `getenv("AEGIS_SURFACE_TIER")` (orchestrator environment) and `getPref("aegis.profile.tier")` (profile `user.js`). Any unset, invalid, or mismatched tier selection fails closed to S4.
4. **Empirical Memory Baseline:** The multi-process Firefox ESR 153 instance consumes ~596 MB RSS under 3 local pages (`/benign`, `/phishing-mock`, `/axes`). This figure is explicitly labeled as an empirical **lower bound** for light local pages, not an upper bound for heavy production web workloads.

**Spec references:** Parts 5.1, 5.2, 7.1, 14.

---

## D-012 — 2026-10-24 — Phase 2b Fingerprinting Evaluation, Identity Direction (Hybrid), and Offline Defaults

**Decision:**
1. **FPP Remote Overrides Disabled by Default:** `privacy.fingerprintingProtection.remoteOverrides.enabled` is locked to `false` across all tiers in accordance with Hard Rule 7 (local-first, no telemetry). Disabling Mozilla's remote WebCompat override lists means domain-specific exemptions pushed by Mozilla will not be received, which may increase breakage on sites that rely on unrandomized canvas or unmasked hardware. An opt-in web-compat module may be designed in later phases with explicit disclosure.
2. **External Fingerprinting Sites:** External fingerprinting test sites (Cover Your Tracks, BrowserLeaks, CreepJS, AmIUnique) remain unapproved. All verification must be performed using local defanged test pages served by `tests/tools/local_test_server.py`.
3. **JIT Measurement Under Quantized Timers:** Because RFP quantizes `performance.now()` (~16.667ms frame-rate clamping by default; 100ms when configured), in-page microbenchmark duration is supplemented with:
   - Behavioral verification (Option B): Operation frequency counting per timer tick edge (measuring completed iterations within a discrete clock quantum).
   - Live pref verification (Option C): Direct query of `javascript.options.baselinejit` and `ion` via Marionette chrome context.
   - Fallback (Option A): Scaled macro-benchmark workload (duration >> 1,000ms so quantum error is < 5%).
4. **Identity Direction (Hybrid Model):**
   - Standard / Guarded tiers (I1, I2): Deploy `privacy.fingerprintingProtection: true` (FPP) with remote overrides disabled. Provides origin-keyed canvas salting (`EfficientCanvasRandomization`), font restrictions (`FontVisibilityLangPack`), and concurrency tiering (`NavigatorHWConcurrencyTiered`) while preserving site compatibility (local timezone, native window sizes, unmasked WebGL).
   - Strict / Research / Detonation tiers (I3, I4): Deploy `privacy.resistFingerprinting: true` (RFP) with standard upstream defaults and no custom deviations. Enforces strict uniformity (UTC timezone, rounded viewports, 1ms/16.67ms timer clamping with jitter, sanitized WebGL vendor/renderer `"Mozilla"`).
5. **Container Canvas Isolation Limitation:** Empirical testing on ESR 153.5.1 confirmed that `EfficientCanvasRandomization` (FPP) keys the random noise seed strictly by site / eTLD+1 principal, NOT by container (`userContextId`). Two tabs visiting the same origin in different containers (`userContextId: 1` vs `userContextId: 2`) within the same instance produce the **exact same canvas noise** (`dataUrlHash` identical). Multi-Account Containers isolate cookies and storage, but do NOT isolate canvas fingerprint noise within a single instance. True canvas isolation across Cell identities requires separate process instances (supporting the Process-Tiered architecture of A-001).
6. **FPP Per-Target Override Mechanism:** Verified that `privacy.fingerprintingProtection.overrides` accepts comma-separated `+TargetName,-TargetName` strings (e.g., `+CanvasRandomization,-EfficientCanvasRandomization,+JSDateTimeUTC`), evaluated on top of `DefaultTargetsFPP`.

**Why:** Balances daily usability in lower tiers against rigorous Tor-aligned uniformity in strict tiers, honors offline constraints, and grounds architecture in empirical Gecko behavior.

**Spec references:** Parts 5.3, 7.1, 7.3, docs/spec-amendments/A-001.md.

---

## D-013 — 2026-10-24 — Tor Launch Failure Policy (Strict Option A: Refuse to Launch)

**Decision:**
1. **Strict Fail-Closed on Tor Failure (Option A):** If the Tor daemon is offline, unavailable, unresponsive, or fails connection to the local SOCKS proxy (`127.0.0.1:9050`) at launch or during route initialization, any tier configured for Tor routing (N2 / N3) MUST fail closed and refuse to launch.
2. **Tor Tier Invariance (A Tor tier must never become non-Tor):** Silent, automatic, or in-place fallback to direct internet access (N0) or clearnet DoH (N1) within the same instance or profile is strictly prohibited. Once an instance is designated as a Tor instance, it is cryptographically and procedurally locked to Tor routing.
3. **Separate, Explicit Non-Tor Action:** If launch fails due to Tor unavailability, the launcher/orchestrator may offer the user a distinct, explicit user action to open a DIFFERENT, clearly named non-Tor tier (such as Tier 1: Standard or Tier 2: Guarded). This ensures the user consciously acknowledges that they are transitioning from an anonymous onion-routed context to a clearnet-routed context under a completely different profile and identity posture.

**Why:** Prevents catastrophic deanonymization and silent cleartext leaks where sensitive onion links, intelligence sessions, or pseudonym identities are unexpectedly transmitted across cleartext clearnet IP addresses.

**Spec references:** Parts 5.4, 6.1, 7.1, 14, docs/spec-amendments/A-001.md.

---

## D-014 — 2026-10-24 — Dedicated Banking Preset Instance and Extension Isolation Policy

**Decision:**
1. **Dedicated Banking Preset (`banking`):** Anchored Cells (banking, high-value accounts) are assigned a dedicated preset instance (`banking`: `{S2, I3, N1}`) operating under an isolated profile directory (`profiles/aegis-banking/`).
2. **Instance-Wide Extension Isolation:** In the Gecko engine, WebExtensions execute process-wide across all containers; Multi-Account Containers (`userContextId`) cannot restrict or disable extension scripts. To satisfy Master Spec Part 5.5 ("extensions off"), the `banking` preset disables extensions instance-wide (`extensions.enabledScopes: 0`), ensuring third-party extensions cannot access banking DOM or intercept credentials.
3. **On-Demand Concurrency:** Because presets spawn on demand up to the configurable concurrency cap (default: max 4 concurrently running instances), the `banking` preset consumes zero RAM when not actively in use. When active, it provides absolute extension isolation without violating memory safety bounds.

**Why:** Enforces the spec's "extensions off" invariant for sensitive banking while acknowledging engine-level container limitations honestly, and prevents anti-fraud account lockouts via I3 site-keyed noise (Amendment A-003).

**Spec references:** Parts 5.2, 5.5, 6.2, docs/spec-amendments/A-001.md, docs/spec-amendments/A-003.md.

