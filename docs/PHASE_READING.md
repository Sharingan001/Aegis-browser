# Aegis Browser: which spec parts to read per phase

Always also read: `CLAUDE.md`, `docs/DECISIONS.md`, `docs/VERIFY.md`.

| Phase | Goal | Spec parts to read (in `docs/spec/`) |
|---|---|---|
| 0 | Baseline build, fast path, test harness, port prototypes | 02, 10, 12, 16, 17 |
| 1 | Branding and UI shell | 01, 04, 09, 15 |
| 2 | Surface and Identity axes, presets, Tier 1 modules | 05, 08 (8.1 to 8.3), 11 |
| 3 | Network axis, Tor, route contracts, leak matrix | 05 (5.4, 5.5), 07 (7.4), 12 |
| 4 | Cells, workspaces, Scope Guard | 06, 08 (M1, M16), 05 (5.5) |
| 5 | Flight Recorder, verification, Link Guard stages 1 to 3 | 07 (7.5, 7.6, 7.7), 09 (9.4), 12, 14 |
| 6 | Trust Ledger, tripwires, Link Guard content stages, Anchored Cells | 07 (7.1, 7.2, 7.7), 06 (6.2), 14 |
| 7 | Detonation Cell | 07 (7.3), 05 (S4 row), 14 |
| 8 | Tier 2 and 3 modules | 08 |
| 9 | Hardening and release | 15, 12, 11 |
