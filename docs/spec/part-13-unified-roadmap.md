# Part 13. Unified roadmap

| Phase | Deliverable | Exit criteria |
|---|---|---|
| **0** | Reproducible **unmodified** Firefox baseline build; fast prototype environment (policies + autoconfig + built-in extension harness) | Baseline runs; commands, versions, and hashes documented |
| **1** | Aegis branding, UI shell, mode/level indicators | Usable branded build; no new security claims |
| **2a** | **Surface axis** S1 to S4 as locked policies | One enforcement test per control |
| **2b** | **Identity axis** I1 to I4 | Fingerprint tests per level; compatibility costs documented |
| **2c** | Presets and conflict rules | Every conflict row tested |
| **2d** | **Tier 1 modules** as built-in extensions: Link Cleaner, Download Inspector, Session Sweeper, Site X-ray, Command Palette | Manifests, tests, kill switches |
| **3** | **Network axis**: strict encrypted DNS, then Tor (N2), bridges (N3) | Leak matrix passes; fail-closed verified independently |
| **4** | **Cells** (storage and identity first, then route); Cells as Workspaces + routing (M1); Scope Guard (M16) | No cross-Cell leakage in tests |
| **5** | Flight Recorder, Verification Layer, Route canary; **Link Guard stages 1 to 3**; request inspector, TLS viewer, redirect analyzer | Declared-vs-verified reporting; per-rule tests; benign false-positive rate within target |
| **6** | Trust Ledger and API Tripwires (observe-only first, then escalate); **Link Guard stages 5 to 7**; Anchored Cells; trusted-path UI | Explainability and revert flows tested; mock-page tests pass |
| **7** | Detonation Cell, quarantine, cleanup receipt | Cleanup tests pass; wording reviewed |
| **8** | Tier 2/3 modules (Evidence Notes, Extension Airlock, Clipboard Guard, QR Preview, Privacy X-ray, Tab Steward, Time Capsule, Reader, Credential Radar, Writeup Export, Focus, Per-Cell Downloads) | Each with manifest, tests, threat note |
| **9** | Hardening, signed updates, reproducible builds, **external review**, release process | Independent assessment completed before strong claims |
| **R** | Research: crowd-awareness measurements, I3 seeded noise feasibility, S4 script-control approach, Servo/Ladybird static renderer, Tier 4 modules (history search, alias vault, translation, encrypted sync) | Documented results; no release dependency |
