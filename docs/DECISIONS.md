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

## D-006 — 2026-10-23 — Repository root: /home/god/Ageis/

**Decision:** `/home/god/Ageis/` is the repository root. No rename to `aegis-browser/` is
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

**Spec references:** Parts 5.1, 5.2, 6.1.

---

