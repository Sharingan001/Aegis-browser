# Part 3. Survey of existing browsers and the gaps

Sources are public documentation and 2026 community and press articles; quality varies, so verify against vendor documents before relying on any single claim. Chrome, Safari's tracking prevention, Vivaldi's security internals, Opera, and Waterfox were not studied in depth.

## 3.1 Security features

| Browser | Engine | Approach | Gap for Aegis |
|---|---|---|---|
| **Tor Browser** | Gecko | Three levels (Standard, Safer, Safest); Safer disables JavaScript on non-HTTPS sites, some fonts and math symbols, and makes media click-to-play; Safest permits only what static sites need; changing level asks for a restart | One global slider that mixes attack-surface reduction with identity effects; a community test suggested the middle level looked more unique (anecdote, unreliable) |
| **Mullvad Browser** | Gecko | Tor Browser's anti-fingerprinting design without Tor, plus uBlock Origin; intended for use with a shared VPN | Needs a large uniform crowd; no per-site levels |
| **LibreWolf / Arkenfox** | Gecko | Hardened Firefox defaults, telemetry removed, resist-fingerprinting, uBlock | Static configuration; no dynamic behavior |
| **Firefox** | Gecko | Site isolation, RLBox library sandboxing, Enhanced Tracking Protection, Total Cookie Protection, optional DNS over HTTPS | No user-visible risk levels; no per-site attack-surface control |
| **Brave** | Chromium (excluded) | Per-session "farbling" randomization of canvas, WebGL, audio, fonts, language; Shields levels | Reference only; randomization can be detectable and gives one identity per session |
| **Apple Lockdown Mode** | WebKit | Disables JIT, WebAssembly, WebGL, MathML, Web Audio, RTCDataChannel, many fonts and features; site exclusions | All-or-nothing; reported usability problems |
| **Edge Enhanced Security Mode** | Chromium (excluded) | Disables JIT and adds OS mitigations (arbitrary-code guard, hardware-enforced stack protection, control-flow guard); Basic/Balanced/Strict, Balanced varies by site popularity | Reference only; adapts by popularity, not behavior |
| **Ladybird / Servo** | Independent | New engines; Ladybird has its own JIT-less JavaScript engine at the time of the sources; Servo reuses SpiderMonkey | Pre-production |

## 3.2 Productivity features

| Browser | Strengths | Gap |
|---|---|---|
| **Zen** (Gecko) | Vertical tabs, named workspaces (may switch the cookie jar), split view up to four panes, compact mode, mods | Workspaces mainly organize; no security levels or per-workspace routing |
| **Arc** | Spaces, pinned tabs, command bar, Boosts | Closed; reported as receiving less attention |
| **Vivaldi** (Chromium) | Tab stacks, tab tiling, command palette (F2) with prefixes, built-in Mail, Calendar, Feeds, Notes | Chromium; feature-first |
| **Edge** | Vertical tabs, Collections, workspaces | One forum report says workspaces do not isolate cookies |
| **Opera** | Workspaces, Tab Islands, sidebar | Lighter model |

A recurring wish: **route tabs to workspaces automatically by URL or keyword.**

## 3.3 Patterns and the gap

1. Levels are static or crude (global slider, on/off, or popularity buckets). None escalate from **observed behavior**.
2. Attack-surface reduction and fingerprinting are tangled in one dial.
3. Isolation is per-process, not per-purpose.
4. Few browsers **verify** that stated protections are active.
5. No fingerprint-API telemetry is shown to the user.
6. Workspaces **organize** while security settings stay **global**.

**Aegis answer:** three independent axes, applied per Cell, with an explainable evidence engine, verification, and modules that all plug into the same model.

## 3.3b What is borrowed vs new

| Element | Status |
|---|---|
| Security levels | Borrowed concept; new: per-Cell and per-axis |
| JIT/WebAssembly disabling | Borrowed |
| Fingerprint uniformity / randomization | Borrowed; new: randomization seeded per Cell, locked to uniform in Tor mode |
| Containers | Borrowed; new: a Cell owns route, levels, identity, storage, and log scope together |
| Adaptive escalation | Partly borrowed (popularity-based in Edge); new: behavior-based, deterministic, explainable, escalate-only |
| API metering | Partly borrowed (extensions exist); new: integrated with ledger and Cells |
| Route canary + fail-closed contracts | New as a default-on, user-visible feature (must still be proven) |
| Tamper-evident local log | New for browser UX (simple hash chain) |
| Detonation Cell with cleanup receipt | New combination |
| Link Guard integrated with Cells/Ledger/Detonation and trusted-path UI | New combination |
| Anchored Cells | New combination |

> "Unique" means a novel combination and decomposition of ideas, not that every mechanism is unprecedented.
