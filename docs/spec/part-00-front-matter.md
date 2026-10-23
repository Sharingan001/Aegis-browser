# AEGIS BROWSER: MASTER BLUEPRINT (A to Z)

**A non-Chromium, security-first browser with multi-level protection, isolated Cells, phishing defense, and a module ecosystem**

| | |
|---|---|
| **Document status** | Final consolidated specification (merges the original blueprint, v2 design, `AXES.md`, Link Guard, and the Modules Catalog) |
| **Date** | 22 October 2026 |
| **Engine** | Gecko (Firefox ESR base). **No Chromium, Blink, Electron, CEF, or Chromium WebView.** |
| **First platform** | Linux development build, then Windows |
| **Prototype code** | `aegis_psl.py`, `linkguard_prototype.py`, `aegis_modules.py`, `test_aegis.py` (27 passing tests) |

> **How to use this document:** read Parts 1 to 4 for the idea, Parts 5 to 9 for the specification, Parts 10 to 16 for engineering and process, and **Part 18 for the complete building prompt** you can give to an AI coding agent or use as a team brief.

## Contents

1. Vision, principles, goals and non-goals
2. Engine decision and platforms
3. Survey of existing browsers and the gaps
4. Architecture overview
5. The three-axis security model (Network, Surface, Identity)
6. Cells and Anchored Cells
7. Protection services: Trust Ledger, API Tripwires, Route Contracts, Flight Recorder, Verification Layer, Detonation Cell, **Link Guard**
8. Module catalog (productivity, safety, lab, everyday)
9. Base browser features retained from the original blueprint
10. Repository layout
11. Threat model and honest limits
12. Security requirements and leak-test matrix
13. Unified roadmap
14. Test strategy
15. Release, update, legal and maintenance plan
16. Phase 0 build guide (Linux)
17. Prototype code reference
18. **The complete building prompt**
19. Glossary
20. References

---
