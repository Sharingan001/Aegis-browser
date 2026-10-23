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

# Part 1. Vision, principles, goals and non-goals

## 1.1 Vision

Aegis is a daily-usable desktop browser that treats **security as the organizing idea of the whole product**, not a settings page. Instead of one global privacy slider, Aegis gives each task its own **Cell** with its own network route, attack-surface level, identity policy, and storage; it explains every protection decision in plain language; and it verifies that its protections are really active.

## 1.2 Principles

1. **Reuse a maintained engine.** Do not write a browser engine for the first release.
2. **Small, traceable patch set.** Prefer policies, built-in extensions, and chrome UI over deep engine changes. Every patch has a reason, an owner, and a test.
3. **Honest claims only.** No claim of anonymity or safety that is not tested. "No warning" never means "safe".
4. **Fail closed.** If a protection cannot be verified, block or clearly degrade; never silently fall back.
5. **Explain everything.** Every block, warning, and escalation shows the rule, the evidence, and a way to revert.
6. **Escalate automatically, de-escalate only by the user.**
7. **Local first.** Analysis happens on the device. Anything that leaves the device is opt-in and disclosed exactly.
8. **Every setting has a test.** If it cannot be tested, it does not ship as a promise.
9. **Updates are part of security.** Track upstream security releases quickly.

## 1.3 Goals (first usable release)

- A branded, usable Gecko-based desktop browser (tabs, address bar, bookmarks, history, downloads, settings).
- Security levels on three independent axes with per-Cell application.
- Tracker blocking, HTTPS-first/only, permission controls, disposable sessions.
- Optional Tor mode that **fails closed**, with a leak-test matrix.
- Link Guard (phishing warnings) and Download Inspector.
- Security panel showing **declared vs verified** protections.
- Tier 1 modules (Link Cleaner, Download Inspector, Session Sweeper, Site X-ray, Command Palette).
- Reproducible build, signed releases, documented update process.

## 1.4 Non-goals (first release)

- Writing a new rendering or JavaScript engine.
- Claiming Tor-Browser-level anonymity.
- A custom password vault, custom TLS stack, or custom crypto.
- Mobile apps.
- Built-in sync (research track only, after external review).
- Exploit, attack, or evasion tooling of any kind.

---

# Part 2. Engine decision and platforms

## 2.1 Decision

| Option | Verdict |
|---|---|
| **Gecko (Firefox ESR)** | **Chosen.** Mature, open source, strong privacy/anti-tracking foundations, process and site isolation, library sandboxing, enterprise policy mechanism, large extension API, and a known path used by hardened forks (Tor Browser, Mullvad Browser, LibreWolf). |
| WebKit | Possible later; weaker cross-platform story for a Linux-first project. |
| Chromium/Blink | **Excluded by requirement.** |
| Servo / Ladybird | **Research only.** Independent engines, not production-ready as primary engines; Ladybird's alpha was targeted for 2026 (verify status). May be evaluated later as a minimal renderer for the S4 static path. |

**Engine rule:** track the ESR line, rebase patches on every security release, and keep an `ARCHITECTURE.md` note on engine abstraction without building a dual-engine system in v1.

## 2.2 Platforms

1. **Development:** Linux (Ubuntu, Arch, or similar).
2. **Initial product:** desktop prototype on Gecko.
3. **Secondary:** Windows 10/11 after the Linux build, tests, and update process are repeatable.
4. Process: reproducible environment, unmodified baseline first, small patches with tests, automated regression checks, packaging last.

---

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

---

# Part 4. Architecture overview

```text
+-------------------------------------------------------------------+
|                          Aegis Browser UI                         |
| Tabs | Address bar | Security panel | Cell switcher | Palette     |
+--------------------------------+----------------------------------+
                                 |
        +------------------------v-------------------------+
        |                    CELL MANAGER                   |
        |  per-Cell: Route (N) + Surface (S) + Identity (I) |
        |  storage, permissions, downloads, log scope       |
        +--------+-----------------+-----------------+------+
                 |                 |                 |
     +-----------v---+   +---------v--------+   +----v------------+
     | Policy Gate   |   | Protection Svcs  |   | Modules (M1..)  |
     | Route Contract|   | Link Guard       |   | built-in ext    |
     | Level policies|   | Trust Ledger     |   | + chrome UI     |
     |               |   | API Tripwires    |   |                 |
     +-------+-------+   | Flight Recorder  |   +--------+--------+
             |           | Verification     |            |
             |           +---------+--------+            |
             +-------------------+-+---------------------+
                                 |
        +------------------------v-------------------------+
        |         Gecko / Firefox ESR foundation            |
        |  rendering | JS | storage | networking | sandbox   |
        +------------------------+-------------------------+
                                 |
        +------------------------v-------------------------+
        |     Network: Direct | Encrypted DNS | Tor | Bridges |
        +---------------------------------------------------+
```

## 4.1 Trust boundaries

- **Website content is untrusted.** Always.
- Privileged UI and services never expose privileged APIs to web content.
- Services consume **structured events**, not page scripts with elevated rights.
- Network policy is enforced in the network/policy layer, **not only in UI preferences**.
- No custom TLS or crypto; use the engine and OS primitives.
- No passwords, tokens, or raw authorization headers in diagnostics or logs.
- Warnings and trust indicators live in Aegis chrome, never in page-controlled space.

## 4.2 Implementation strategy

1. **Policies and locked preferences** (versioned config files) for levels.
2. **Built-in (system) WebExtensions** for modules, using supported APIs (tabs, downloads, cookies, storage, commands, omnibox, sidebar, contextual identities, proxy, webRequest).
3. **Chrome UI** (security panel, Cell switcher) using the engine's supported UI layer.
4. **Engine patches only when 1 to 3 cannot do it**, each tracked in a patch queue.
---

# Part 5. The three-axis security model

> Cumulative levels inside each axis. Every control has a mechanism, a verification test and a user-visible cost. Anything marked **VERIFY** must be confirmed against the pinned Firefox ESR version before it ships.

## 5.1 The three axes

| Axis | Question it answers | Levels |
|---|---|---|
| **N: Network** | Where does traffic go? | N0 Direct, N1 Encrypted DNS, N2 Tor, N3 Tor + bridges |
| **S: Surface** | How much engine functionality can a page reach? | S1 Standard, S2 Guarded, S3 Strict, S4 Static |
| **I: Identity** | What can a site learn about this device? | I1 Native, I2 Uniform, I3 Cell-seeded, I4 Minimal-API |

**R1 (decoupling):** S never changes fingerprint-visible output except where a feature disappears because it is disabled. I never changes memory-safety exposure.
**R2 (crowd awareness):** in N2/N3, I is locked to I2, and only S levels measured as not splitting the crowd are offered without an explicit acknowledgment.

Each level is **cumulative inside its axis** (S3 includes S2, and so on) unless stated.

---

## 5.2 Axis S: Surface levels

| Control | S1 | S2 | S3 | S4 | Mechanism (VERIFY) | Test |
|---|:-:|:-:|:-:|:-:|---|---|
| HTTPS-first (upgrade, fall back with prompt) | on | on | on | on | policy / `dom.security.https_only_mode_*` family | Load an HTTP-only test page: prompt appears; no silent fallback in S2+ |
| HTTPS-only (fallback needs explicit click) | off | on | on | on | `dom.security.https_only_mode` | Same page: blocked until user confirms |
| Mixed content blocked | on | on | on | on | engine default; assert not weakened | Page loading HTTP script over HTTPS: script blocked |
| Third-party storage partitioned | on | on | on | on | `network.cookie.cookieBehavior` (partitioning value) | Cookie set in iframe on site A not visible to same iframe on site B |
| Autoplay | allow muted | block audible | block all | n/a | `media.autoplay.*` | Page with autoplay media: behavior matches level |
| Notifications / location / camera / mic | ask | ask, default deny on first visit | deny by default | deny | permission policies | Prompt or silent denial per level |
| Dangerous protocol handlers | prompt | blocked | blocked | blocked | handler policy | Click on custom-scheme link: no external app launches |
| Downloads | prompt | prompt, no auto-open | quarantine (Download Inspector) | quarantine, no open | download policy + module M8 | Download executable: lands in quarantine, not opened |
| JIT compilers | on | on | **off** | **off** | `javascript.options.baselinejit`, `javascript.options.ion` | Performance micro-test shows interpreter-only; about:support shows state |
| WebAssembly | on | on | **off** | **off** | `javascript.options.wasm` | `typeof WebAssembly` behavior / instantiate fails |
| WebGL / WebGPU | on | on | **off** | **off** | `webgl.disabled`, WebGPU pref | `getContext("webgl")` returns null |
| Risky font/rendering features (OpenType-SVG, MathML) | on | on | **off** | **off** | `gfx.font_rendering.opentype_svg.enabled`, `mathml.disabled` | Test page with SVG-in-font and MathML: not rendered |
| Remote (downloadable) fonts | on | on | on | **off** | `gfx.downloadable_fonts.enabled` | Page with `@font-face`: falls back to system font |
| JavaScript | on | on | **HTTPS only** | **off by default, per-origin allow** | Built-in system extension with per-origin script control (see risk below) | Test pages over HTTP/HTTPS; allow-list works per session |
| Persistent storage | on | on | session only | none | storage policy | Restart: data gone in S3 (session) / S4 |
| Extensions | allowed | allowed (vetted, M12) | built-in only | none | extension policy | Install attempt blocked |
| Link Guard thresholds | normal | normal | strict | strict + no continue shortcut | module config | Same suspicious URL gets stricter verdict |

**Engineering risk (S4 JavaScript allow-list):** Firefox has no public per-origin script-control API for ordinary extensions. Options: (a) ship a built-in system extension with the needed privileges (this is how Tor Browser handles it with NoScript), (b) patch the engine. Decide in a design spike before promising S4.

**User-visible cost**
- S2: occasional HTTP site needs an explicit click.
- S3: slower script-heavy pages, no WebGL/maps/3D, some web apps break.
- S4: most interactive sites unusable until allow-listed.

**Fingerprint note:** disabling WebGL, WebAssembly, or fonts makes those features *absent*, which a script can observe. That is expected and is why R2 limits which S levels are offered in Tor mode.

---

## 5.3 Axis I: Identity levels

| Control | I1 Native | I2 Uniform | I3 Cell-seeded | I4 Minimal-API | Mechanism (VERIFY) |
|---|:-:|:-:|:-:|:-:|---|
| Tracker blocking | standard | standard | standard | strict | Enhanced Tracking Protection policy |
| Fingerprinting-protection baseline | off | **on** | on | on | `privacy.resistFingerprinting` and/or the newer fingerprinting-protection prefs: **evaluate both** before choosing |
| Timezone / locale / window size normalization | no | yes | partial | yes | part of resist-fingerprinting behavior (letterboxing etc.) |
| Timer precision reduction | default | reduced | reduced | reduced | resist-fingerprinting behavior |
| Canvas / audio readback | native | normalized | **seeded noise per Cell and site** | blocked or constant | engine feature if present, otherwise research patch |
| Hardware concurrency, device memory, screen | native | normalized | normalized | constants | resist-fingerprinting behavior |
| High-entropy APIs (gamepad, sensors, media-device enumeration, battery-type APIs, speech voices) | on | on | on | **off** | individual prefs/policies (VERIFY each) |
| Referrer | default | trimmed | trimmed | origin-only or none | `network.http.referer.*` |
| WebRTC | default | no local-IP leak | no local-IP leak | off | `media.peerconnection.*` |
| Language header | native | normalized | normalized | normalized | `intl.accept_languages` handling |

**I3 design (Cell-seeded):** a per-Cell random secret `K_cell` is created with the Cell. Noise for site `D` is derived as `HMAC(K_cell, registrable_domain(D) || api_name)`. Result: stable inside a Cell and site (so pages do not break from changing values on reload), different across sites in the same Cell, and unrelated across Cells. Rotate `K_cell` when the Cell is cleared. **Research first:** check whether the engine's newer fingerprinting protection already provides seeded randomization before building your own.

**Honest limits**
- I2 only blends in if the output matches a large crowd. A derived browser's output will differ from Tor Browser's or Mullvad Browser's unless it is exactly the same. Claim "reduced cross-site linkability", not "anonymity".
- Randomization (I3) can itself be detectable. Test it against public fingerprinting test pages and record the results in `tests/crowd-analysis/`.

---

## 5.4 Axis N: Network levels

| Level | Behavior | Failure mode | Tests |
|---|---|---|---|
| N0 Direct | Normal connection | n/a | Baseline |
| N1 Encrypted DNS | DNS over HTTPS, **strict** (no silent plaintext fallback), resolver configurable | Resolver down: show error, offer N0 explicitly | Block resolver: no plaintext DNS observed on the wire |
| N2 Tor | All Cell traffic via Tor SOCKS, **remote DNS**, no direct fallback, WebRTC off | Tor down: **fail closed** | Kill Tor: no direct traffic; DNS and WebRTC leak tests |
| N3 Tor + bridges | N2 with user-supplied bridges | Same | Same, plus bridge-only network simulation |

Mechanisms (VERIFY): `network.proxy.type`, `network.proxy.socks`, `network.proxy.socks_remote_dns`, `network.trr.mode` (strict mode), proxy-bypass lists emptied, OS firewall rule where available (see Route Contracts).

---

## 5.5 Conflict and interaction rules

| Situation | Resolution |
|---|---|
| N2/N3 selected | I forced to I2 and locked. S limited to S1 and S4 unless the user accepts "this may make me distinguishable". |
| I3 requested with N2/N3 | Refused with explanation. |
| S4 with Link Guard "Continue" | No one-click continue; requires a deliberate extra step. |
| Anchored Cell (banking) | S minimum S2; I minimum I2; extensions off. |
| Detonation Cell | S4 + I2 + N2 (or N1 if Tor unavailable, with a visible warning); ephemeral. |
| User lowers S/I after an automatic escalation | Allowed; recorded in Flight Recorder; no re-escalation for that origin this session unless a new high-severity signal. |
| Level changed on an open page | Applies to the **next load / new tab**; never silently mid-page. |

---

## 5.6 Level file schema (config/axes/*)

```json
{
  "schema": 1,
  "axis": "surface",
  "id": "S3",
  "name": "Strict",
  "extends": "S2",
  "controls": [
    {
      "id": "js.jit",
      "mechanism": "pref",
      "set": { "javascript.options.baselinejit": false, "javascript.options.ion": false },
      "locked": true,
      "verify": { "type": "runtime-check", "test": "tests/axes/test_jit_off" },
      "user_cost": "Slower script-heavy pages"
    }
  ],
  "compat_notes": ["Maps, 3D, and some web apps may not work"],
  "fingerprint_visible": false
}
```

Rules: every control has a `verify` block; `fingerprint_visible` must be honest (R1); CI fails if a level file contains a control without a test.

## 5.7 Presets

```json
{ "schema": 1, "id": "research", "name": "Research", "N": "N2", "S": "S3", "I": "I2", "cell": { "storage": "session" } }
```

| Preset | N | S | I | Cell storage |
|---|---|---|---|---|
| Everyday | N1 | S2 | I1 | persistent |
| Private | N1 | S2 | I3 | session |
| Research | N2 | S3 | I2 | session |
| Detonation | N2 | S4 | I2 | ephemeral (RAM-only) |
| Banking (anchored) | N1 | S2 | I2 | persistent, domain-anchored |

## 5.8 Required tests per release

1. **Enforcement:** for every control, a runtime check inside the running browser confirms it (not just that the config file exists).
2. **Cumulativity:** S3 includes everything in S2; I3 includes I2 baseline where stated.
3. **Conflicts:** every row in section 5.5 has a test.
4. **Compatibility corpus:** a fixed set of local test pages per level, with expected breakage documented.
5. **Crowd analysis (R2):** record observable differences between level combinations.
6. **Regression on upgrade:** after each Firefox ESR update, re-run everything; any pref that no longer exists or changed meaning fails the build.

## 5.9 Open questions (resolve before implementation)

1. Which fingerprinting-protection mechanism does the pinned ESR provide, and what does it normalize?
2. How will S4 per-origin script control be implemented (system extension vs patch)?
3. Does the engine offer seeded canvas/audio noise, or must I3 be custom?
4. Which S levels are acceptable in Tor mode after crowd-analysis measurements?
5. Per-Cell proxy and Tor-circuit isolation: supported by existing mechanisms or does it need patches?

---

# Part 6. Cells and Anchored Cells

## 6.1 Cells (per-purpose compartments)

A **Cell** is the unit that owns: its network route, S level, I policy, cookie jar and storage, permissions, downloads folder, event log scope, and a **color and name** shown in the tab strip and address bar.

- A Cell can be **persistent** (a "Work" Cell), **session** (cleared on close), or **ephemeral** (RAM-only, destroyed on close).
- Cells never share cookies, storage, permission grants, or identity seeds.
- Tabs opened from a link inherit the Cell by default. Cross-Cell navigation requires an explicit action and a clear indicator.
- Per-Cell routing may need Firefox internals changes beyond a UI layer. Prototype with the container and proxy-selection mechanisms first, and treat full per-Cell route isolation (separate Tor circuits per Cell) as a research item to test.

## 6.2 Anchored Cells (strong anti-phishing for sensitive accounts)

A Cell can be **anchored** to a set of registrable domains (for example a "Banking" Cell).

- Saved credentials fill **only** in the anchored Cell and only on anchored domains.
- Navigating to a non-anchored domain from that Cell opens a different Cell and says why.
- A password field on a non-anchored domain inside an anchored Cell is a hard warning.

---

# Part 7. Protection services

## 7.1 Trust Ledger (explainable adaptive escalation)

Existing "adaptive" systems use site popularity. Aegis uses **observed behavior**, with **deterministic, readable rules** (not an opaque model).

**Signals** (all computed locally; nothing leaves the device by default):

| Signal | Example |
|---|---|
| Navigation | First time this origin was visited; unusually deep redirect chain; cross-origin redirect to a different registrable domain |
| Transport | Certificate problems; downgrade attempts; mixed content |
| Content | High number of third-party origins; hits on local tracker/malware lists |
| Behavior | Fingerprinting tripwire counts (7.2); repeated permission requests; automatic download attempts |
| History | Origin previously escalated by the user |

**Rules (examples):**

- `If redirects > N and chain crosses registrable domains → raise S by one level for this origin on next load.`
- `If fingerprint tripwires > T in one page load → move this origin to I4 for the Cell and show why.`
- `If a download starts without user gesture → block, quarantine, raise S.`

**Safety properties (mandatory):**

1. **Escalate only automatically.** The engine may raise protection. Only the **user** may lower it.
2. **Apply on next load by default**, not mid-page, so pages cannot reliably probe the engine's reaction in-flight.
3. **Always explain.** Every change shows the rule, the evidence, and a one-click revert or "never automate for this site".
4. **No remote scoring** by default. Any URL reputation lookup is opt-in and discloses exactly what leaves the device.
5. **Bounded.** The ledger cannot reduce Tor-mode protections or violate rule R2.
6. **Auditable.** Rules live in versioned files in the repo; every rule has a test.

## 7.2 API Tripwires (metered fingerprint surfaces)

Aegis counts, per origin and per script origin, calls to fingerprint-relevant surfaces: canvas readback, WebGL parameter queries, audio context fingerprinting patterns, font enumeration probes, screen/hardware queries, and similar.

- Shown in the security panel as a **plain-language report** ("This page's script from *example-cdn* read 14 fingerprint surfaces").
- Feeds the Trust Ledger (7.1).
- Does **not** block silently by default at I1; at I3/I4 it can feed spoofing/blocking.
- Honest note: other tools do similar API monitoring. The new part is **integrating it with Cells, the ledger, and the flight recorder**.

## 7.3 Detonation Cell (safe opening of suspicious links)

A one-action "Open in Detonation Cell" for links from email, chat, or the clipboard:

- Ephemeral Cell, RAM-only profile, S4 + N2 + I2 by default.
- Static rendering: JavaScript off; the page is fetched and displayed with scripts and active content removed (reader-style "defanged" view) with an optional "allow scripts for this session" step that is logged.
- Downloads go to a **quarantine** area, never auto-opened; type and extension mismatches flagged.
- On close: storage destroyed, and the UI shows a **cleanup receipt** (what was deleted). The receipt must reflect actual deletion tests, not only a UI message.
- **Safety boundary:** this reduces risk, it does not make hostile content safe. A browser or OS vulnerability can still compromise the machine. Do not market it as a malware-analysis sandbox. For real malware analysis, use a dedicated VM and isolated network.

## 7.4 Route Contracts and the Policy Gate

Each Cell has a **Route Contract**: a declared network policy (e.g., "all traffic via Tor SOCKS, DNS remote, no direct fallback, no WebRTC").

- Enforced at the **network layer** (proxy/policy and OS firewall rules where available), **not only in UI preferences**.
- A **continuous canary** runs in a controlled test Cell (or at startup and on route change) that requests a known test endpoint and checks the observed egress. If the contract is violated, the Cell **fails closed**: navigation is blocked and the UI says why.
- Status shows both the *declared* and the *verified* route: "Declared: Tor. Verified 12 s ago."

## 7.5 Flight Recorder (tamper-evident local log)

- Local security events (blocks, certificate warnings, escalations, Tor failures, permission changes) stored as an **append-only hash chain**, so deletion or edits of earlier entries are detectable.
- Secrets redacted by default; full URLs not stored by default.
- Retention controls and a **one-action wipe** (wiping is a user right; the chain is simply restarted and the wipe is the first entry).
- Exportable sanitized report for authorized testing or support.
- Honest limit: this protects against accidental tampering and simple concealment. Malware with OS control can still alter the files.

## 7.6 Verification Layer (hardening posture check)

At startup and on demand, Aegis reports what is **actually active**, not what is configured:

| Check | Example |
|---|---|
| Process sandboxing | Content processes sandboxed (OS-specific) |
| Site isolation | Active for this build |
| OS exploit mitigations | Hardware-enforced stack protection / control-flow protections where the OS supports them; arbitrary-code-guard-style protections where compatible with JIT settings |
| JIT / WebAssembly state | Matches the S level |
| Route canary | Per 7.4 |
| Update channel | Signature verification status |
| Profile state | Ephemeral Cells in RAM only, where claimed |

Failed checks show as **degraded status**, never silently.

## 7.7 Link Guard: phishing protection at every decision point

**Goal:** when a user clicks, types, or is sent to a link, Aegis checks it, explains any risk **in plain words with specific evidence**, and offers a safer next step. It adds friction and evidence at the moment of decision. It does **not** claim to stop all phishing (see limits below).

A reference prototype of stages 1 to 4 is provided in `linkguard_prototype.py` (static URL checks, lure-text scoring, clipboard-command check, verdicts with reasons).

### Where Link Guard runs

| Trigger | Notes |
|---|---|
| Click on a link in a page | Also compares link text with the real destination |
| Address bar entry or paste | Catches lookalike and mistyped domains |
| **External open** (link from email, chat, a document, or a scanned QR code, with no referrer) | Treated as *untrusted origin* by default and given extra scrutiny |
| Redirect hops and new windows | Re-evaluated at every hop |
| Page load complete | Content stage (see stage 5) |
| Clipboard write, fullscreen request, notification request, download start | Behavior stage |

### Pipeline

| Stage | Network needed? | What it checks |
|---|---|---|
| **1. Static URL analysis** | No | See table below |
| **2. Transport check (HTTP vs HTTPS)** | No | Plain HTTP is flagged. HTTP plus any password or payment field is a **hard warning**. HTTPS gets **no trust credit** by itself: the padlock only means the connection to *that domain* is encrypted. Phishing sites can have valid certificates, so the UI never says "secure site"; it says "encrypted connection to *domain*". |
| **3. Local reputation** | No (lists cached locally) | Known-bad lists, local brand-to-domain map, user's own history. |
| **4. Optional remote reputation** | Yes, **opt-in** | Uses a hash-prefix design: keep a local hash database and send only a matching prefix to confirm. Firefox's Safe Browsing integration works this way (local database refreshed about every 30 minutes, confirmation requests carry only a prefix, with added noise entries). Chrome's newer real-time mode adds a privacy relay. In Tor mode, lookups go through Tor. Aegis documents exactly what leaves the device. |
| **5. Page-content and intent analysis** | No (runs locally) | Runs in the privileged, isolated Link Guard component on **extracted structured features** (text, forms, element geometry), never with page-script privileges. See below. |
| **6. Behavior monitoring** | No | Clipboard writes, fullscreen, notification prompts, auto-downloads, device-code and OAuth consent pages. |
| **7. Verdict and UX** | No | Tiered warning with reasons (see UX). |

### Stage 1: static URL signals (before any request is sent)

| Signal | Example of what is flagged |
|---|---|
| Dangerous scheme | `javascript:` or `data:` links |
| `@` / embedded credentials | Text before `@` is not the real site |
| Raw IP address host, odd ports | Site reached without a normal name |
| Punycode and mixed scripts | Characters from different writing systems that look alike |
| Brand in the wrong place | `brand.com.other-site.example` (brand used as a subdomain) |
| Lookalike and typosquat | One-character edits, digit-for-letter swaps |
| Shorteners | Destination hidden |
| Redirect parameters | `?next=https://other-site` |
| Link text mismatch | Text shows one domain, link goes to another |
| Deep subdomains, very long URLs | Weak signals, low weight |

Production note: use the **Public Suffix List** for registrable domains (the prototype uses a tiny stand-in).

### Stage 5: content and intent analysis

| Technique | What Aegis looks for |
|---|---|
| **Lure wording ("free stuff" and similar)** | Free gift, prize, giveaway, "you've won", claim-now wording; urgency ("within 24 hours"); account-threat wording ("suspended", "unusual sign-in"); verification demands; unusual payment requests (gift cards, crypto, processing fees); regional scam themes (for example KYC-expiry, payment-collect requests, utility-disconnection notices). Weighted, readable rules in a versioned file, with language packs. |
| **Credential harvesting** | Password field on an origin the user has not signed in to before; login form posting to a **different registrable domain**; password field on HTTP; lure wording combined with a login form (higher risk than either alone). |
| **Brand impersonation** | Brand name, title, or logo-like content that does not match the domain according to the local brand map. |
| **Password-manager mismatch** | Aegis only autofills on the exact origin. If a page looks like a brand the user has a saved login for but the origin differs, show: "You have a saved login for *brand*, but this is not that site." |
| **Browser-in-the-Browser (fake pop-up windows)** | Page elements imitating a window frame with a fake address bar, or login iframes styled to look like browser chrome. Counter-measure: see "trusted path" below. |
| **ClickFix / fake CAPTCHA** | Pages that say "verify you are human" or "fix this error" and make the user paste something; clipboard writes containing system-command-like text; warns: "Do not paste this into Run, Terminal, or PowerShell." |
| **OAuth consent and device-code phishing** | Consent or device-login pages reached from an **external open**: show app name, requested permissions, and "you did not start this from the site you trust". |
| **Fake updates and tech-support scams** | "Update your browser" download prompts, fullscreen alarm pages, phone numbers plus "your device is infected" wording. |
| **Passkey downgrade** | If the user registered a passkey for a site and the site now asks only for a password, flag it. |
| **Notification abuse and auto-downloads** | Permission prompts or downloads without a user gesture on an unfamiliar origin. |

### Trusted path: unspoofable parts of the UI

Because phishing pages can imitate browser windows and padlocks, the **real** toolbar shows things a page cannot draw:

- The **Cell name, color, and a user-chosen emblem** (set once by the user and never exposed to web content).
- A consistent "encrypted to *registrable-domain*" label, with the registrable domain highlighted.
- Warnings always appear in Aegis chrome (interstitials and toolbar), never in page-controlled space.

### Anchored Cells (strong anti-phishing for sensitive accounts)

A Cell can be **anchored** to a set of registrable domains (for example a "Banking" Cell).

- Saved credentials fill **only** in the anchored Cell and only on anchored domains.
- Navigating to a non-anchored domain from that Cell opens a different Cell and says why.
- A password field on a non-anchored domain inside an anchored Cell is a hard warning.

### Verdict and UX

| Verdict | When | What the user sees |
|---|---|---|
| **None** | No signals | Normal load. If the user asks, the panel says "No warning signs found. This does **not** prove the site is safe." |
| **Notice** | Low-weight signals | Small toolbar badge with one-line reasons |
| **Caution** | Moderate score | Interstitial **before the page loads**, listing each reason in plain language, with "Go back", "Open in Detonation Cell", and "Continue" |
| **Block** | Known-bad list hit, active scheme, high score, or clipboard command lure | Strong interstitial; continuing requires a deliberate extra step and is logged; never a one-click bypass |

Rules for good warnings:

1. **Specific evidence**, for example: "The address *paypa1-secure.example* imitates *paypal.com*." Not just "this site may be dangerous."
2. **Safe alternative offered** (go back, open the official site you typed, open in Detonation Cell).
3. **Avoid warning fatigue:** calibrate thresholds on benign top sites; track per-rule false positives; scoped "do not warn again for this site" that is visible and revocable.
4. **Escalate protection:** Link Guard signals feed the Trust Ledger (7.1), which can raise the S level, and tripwire counts (7.2) feed Link Guard.
5. **Teach:** a short "Why this looks like phishing" card for each rule.

### Privacy rules

- All analysis is **local by default**; page content never leaves the device.
- Remote reputation is opt-in; only hash prefixes are sent; the endpoint is configurable; in Tor mode it goes through Tor.
- Link Guard events go to the Flight Recorder with URLs redacted by default.

### Limits (must be shown)

- Heuristics produce **false positives and false negatives**. Attackers adapt wording and layout.
- Phishing kits may **cloak** (show benign content to scanners or some regions). New campaigns may not appear on lists yet.
- Text inside images can evade text rules. Targeted, well-researched phishing may trigger no signals.
- HTTPS is **not** evidence of safety. "No warning" is **not** evidence of safety.
- The best defenses remain **passkeys or hardware security keys** (bound to the real site origin), password-manager origin matching, and verifying through a separate channel before acting on urgent requests.

### Testing Link Guard

- Use **offline labeled datasets** of benign and phishing URLs and **saved, defanged copies** of test pages inside an isolated VM. Do not browse live phishing pages for testing.
- Build **local mock pages** for each rule (lure wording, cross-domain login form, fake window frame, clipboard-write lure).
- Metrics: precision and recall per rule; false-positive rate on a top-sites benign set; pre-load check latency budget; per-language lure coverage.
- Every rule needs: an ID, a plain-language explanation, a severity, positive and negative tests.

---

# Part 8. Module catalog

> Modules plug into Cells and the event bus. Prototypes exist for M1, M8, M9, M10, M11, M15, M16.

## 8.1 Module architecture

### 8.1.1 Module Manifest (every module must have one)

```json
{
  "id": "download-inspector",
  "version": "1.0.0",
  "name": "Download Inspector",
  "privacy_class": "P1",
  "permissions": ["downloads.read", "downloads.quarantine", "events.emit"],
  "cells": { "default": "all", "disabled_in": ["detonation-minimal"] },
  "stores": ["quarantine-index"],
  "network": "none",
  "min_surface_level": "S1",
  "kill_switch": true,
  "tests": ["tests/modules/download_inspector/"]
}
```

**Privacy classes**

| Class | Meaning |
|---|---|
| P0 | Stores nothing |
| P1 | Local configuration only |
| P2 | Local user content, **encrypted at rest** |
| P3 | Can send data off-device, **opt-in**, with a disclosure screen listing exactly what leaves |

### 8.1.2 Rules for all modules

1. **No access to page scripts or raw page content.** Modules get structured events and APIs only.
2. **Least privilege.** Permissions declared in the manifest; undeclared access fails.
3. **Per-Cell enable/disable** and a global kill switch.
4. **Ephemeral and Detonation Cells never feed persistent modules** (no history index, no notes sync, no archive) unless the user explicitly saves something.
5. **Every module emits events** to the Flight Recorder (URLs redacted by default).
6. **Every module has tests** and an owner-written threat note.
7. **Fail safe:** if a module crashes, browsing continues and protection modules show a degraded status, never silence.

### 8.1.3 Build path (practical for a small team)

Because Aegis is Firefox-based, many modules can start as **built-in (system) WebExtensions** using supported APIs for tabs, downloads, cookies, storage, commands, omnibox, sidebar, and contextual identities, and only later move into engine or chrome-UI patches where needed. This keeps the patch set small, which matters for security updates.

### 8.1.4 Event bus (how modules cooperate)

```text
Link Guard ──▶ Trust Ledger ──▶ raises S level / offers Detonation Cell
Download Inspector ──▶ Flight Recorder
Scope Guard ──▶ Evidence Notes (auto-log of in/out-of-scope attempts)
Cell Router ──▶ Cells (opens link in the right Cell)
Session Sweeper ──▶ Cells (storage cleanup)
Site X-ray ──▶ Evidence Notes / Time Capsule (attach findings)
```

---

## 8.2 The modules

### Family A: Workspace and navigation

| ID | Module | What it does | Privacy | Effort | Depends on |
|---|---|---|---|---|---|
| **M1** | **Cells as Workspaces** | Vertical tab sidebar, tab tree, split view, per-Cell color and name. **Auto-routing rules** (`*.sbi.co.in` → Banking; `github.com` + keyword `ctf` → Research). Prototype: `route_to_cell()`. | P1 | M | Cells |
| **M2** | **Command Palette** | Keyboard-first search across open tabs, history, bookmarks, notes, commands and Cells with prefixes (`tab:`, `note:`, `cell:`, `cmd:`). Aegis-specific actions: "Open in Detonation Cell", "Raise surface level", "Show why blocked", "Clean this link". | P1 | M | Extensions API |
| **M3** | **Tab Steward** | Suspend idle tabs, per-Cell memory budget, duplicate-tab detection, close-and-restore groups. Never suspends tabs with active uploads or media. | P1 | S–M | Tabs API |

### Family B: Knowledge and research

| ID | Module | What it does | Privacy | Effort |
|---|---|---|---|---|
| **M4** | **Evidence Notes** | Local notes and web clips with **provenance**: URL, time, Cell, and a SHA-256 of the clip. Markdown storage, search, tags. Useful for coursework, CTF writeups, and research. | P2 | M |
| **M5** | **Time Capsule** | Save a page as a **static snapshot** (scripts removed) with hash and timestamp; local full-text search across snapshots. Reuses the static renderer from S4. | P2 | M–L |
| **M6** | **Reader and Focus** | Distraction-free reading using the static renderer; text size, contrast, optional on-device text-to-speech. | P0 | S |
| **M7** | **Local History Search** | **Opt-in, per-Cell** text index of pages you visited so you can find "that article about X". Text only, no screenshots, no form fields, never in Ephemeral/Detonation Cells, encrypted at rest, one-click wipe. | P2 | L |

### Family C: Safety and hygiene

| ID | Module | What it does | Privacy | Effort |
|---|---|---|---|---|
| **M8** | **Download Inspector** | SHA-256 hash, **type vs content check** (a `.jpg` that is really a Windows executable), **double extension** (`invoice.pdf.exe`), **right-to-left override** filename trick, quarantine folder, never auto-open. Optional hash-only lookup (P3). Prototype: `inspect_download()`. | P1 | S–M |
| **M9** | **Credential Radar** | Breach check using **k-anonymity**: hash locally, send only the first 5 characters of the SHA-1, compare the rest locally (prototype: `breach_lookup_prefix()`, verified against the standard test vector). Also flags weak/reused passwords and shows **passkey availability**. **Do not write your own password vault**: integrate an established manager (for example via native messaging) so Aegis fills only on the exact origin. | P3 (opt-in) | S–M |
| **M10** | **Session Sweeper** | Automatically deletes site data not used for N days, with an allow-list. Prototype: `sweep()`. | P1 | S |
| **M11** | **Link Cleaner** | Removes tracking parameters (`utm_*`, `fbclid`, `gclid`, and similar) when you copy or open a link; shows what was removed; user keep-list. Prototype: `clean_link()`. | P0 | S |
| **M12** | **Extension Airlock** | Risk-scores an extension's permissions at install, shows a plain-language summary, **delays enabling by a short period**, and re-prompts when an update **adds** permissions. Extensions are disabled in S3/S4 and Detonation Cells. | P1 | M |
| **M13** | **Privacy X-ray** | One page showing, per site: trackers blocked, third parties contacted, permissions granted, storage used, fingerprint-API tripwire counts. One-click revoke. | P1 | M |
| **M14** | **QR Preview** | Drop or paste an image containing a QR code, decode it **locally**, and send the destination through Link Guard **before** you open it (counter to QR phishing). | P0 | S–M |

### Family D: Security Lab (for students, CTF players, and authorized testers)

| ID | Module | What it does | Privacy | Effort |
|---|---|---|---|---|
| **M15** | **Site X-ray** | **Passive** review of the response headers, cookie flags, TLS details and third-party map that the browser already received: HSTS, CSP quality, clickjacking protection, `nosniff`, Referrer-Policy, `Secure`/`HttpOnly`/`SameSite`, version disclosure. It sends **no extra probing requests**. Prototype: `xray_headers()`. | P0 | M |
| **M16** | **Scope Guard** | A **Lab Cell** that only talks to a declared, authorized scope (allow and deny wildcard lists). Out-of-scope requests are **blocked and logged**, which prevents accidental out-of-scope testing during CTFs, labs, and authorized assessments. Prototype: `Scope.check()`. | P1 | M |
| **M17** | **Writeup Export** | Turns Evidence Notes plus the Flight Recorder timeline of a Lab Cell into a Markdown report skeleton (steps, timestamps, hashes of artifacts). | P2 | S–M |

**Boundary for Family D:** these modules help you *observe, scope, and document*. They contain **no exploit, attack, or evasion functionality**, and Lab Cells are for systems you own or are explicitly authorized to test.

### Family E: Everyday features

| ID | Module | What it does | Privacy | Effort |
|---|---|---|---|---|
| **M18** | **Alias and Identity Vault** | Per-Cell, per-site **email aliases** via an established alias service integration, so a site breach does not expose your real address; shows which alias belongs to which site. | P3 (opt-in) | M |
| **M19** | **Focus Sessions** | Per-Cell schedules that block listed distracting domains; local-only usage summaries (time per Cell). | P1 | S |
| **M20** | **Clipboard Guard** | Warns when a page writes command-like text to the clipboard (shares logic with Link Guard); optional auto-clear of copied sensitive text after N seconds; never reads the clipboard without a user gesture. | P0 | S |
| **M21** | **Per-Cell Downloads** | Each Cell gets its own download folder and quarantine; Detonation downloads cannot reach your normal Documents folder. | P1 | S |
| **M22** | **On-device Translation** | Reuse the engine's on-device translation if present (VERIFY); also lets Link Guard's lure rules cover more languages without sending text to a server. | P0 | M |

### Family F: Sync and backup (later)

| ID | Module | What it does | Privacy | Effort |
|---|---|---|---|---|
| **M23** | **Encrypted Sync** | End-to-end encrypted, self-hostable sync of settings, Cell definitions, and notes. **Highest-risk module**: key management, recovery, and server trust. Do not ship before an external review. | P3 | L |
| **M24** | **Signed Settings Export** | Export/import of levels, presets, Link Guard rules and Cell definitions as signed files, with a diff view before import. | P1 | S |

---

## 8.3 Priority and build order

| Tier | Modules | Why |
|---|---|---|
| **Tier 1 (build first; small, high value)** | M11 Link Cleaner, M8 Download Inspector, M10 Session Sweeper, M15 Site X-ray, M2 Command Palette | Small effort, immediately useful, mostly extension-level |
| **Tier 2** | M1 Cells as Workspaces, M16 Scope Guard, M4 Evidence Notes, M12 Extension Airlock, M20 Clipboard Guard, M14 QR Preview, M13 Privacy X-ray | Need Cells; show off the unique design |
| **Tier 3** | M3 Tab Steward, M5 Time Capsule, M6 Reader, M9 Credential Radar, M17 Writeup Export, M19 Focus, M21 Per-Cell Downloads | Quality-of-life and integrations |
| **Tier 4 (research or later)** | M7 Local History Search, M18 Alias Vault, M22 Translation, M23 Encrypted Sync, M24 Signed Export | Larger scope or higher risk |

**Scope-creep warning:** a browser is a security product first. Each module increases attack surface and maintenance load. Ship Tier 1, measure, and add modules only when the previous ones have tests and a threat note.

---

## 8.4 Per-module threat notes (summary)

| Module | Main risk | Mitigation |
|---|---|---|
| M4/M5/M7 (stored content) | Local data theft or accidental retention | Encrypt at rest, exclude sensitive Cells, one-click wipe |
| M8 | False sense of safety | Wording: "no flags found" is not "safe"; keep quarantine on |
| M9 | Leaking password info | Only 5-char hash prefix leaves, opt-in, via Tor in Tor mode; never log passwords |
| M12 | Annoyance leads users to bypass | Short delay, clear summaries, remember informed choices |
| M15 | Misread as a full audit | Label: passive header review only |
| M16 | Scope typed wrongly | Show the compiled scope; require explicit confirmation of wildcards |
| M18/M23 | Third-party trust | Opt-in, documented data flows, self-host option |
| Any module | Becomes a privileged bridge for page scripts | No page-script APIs; structured events only; fuzz module inputs |

---
---

# Part 9. Base browser features retained from the original blueprint

## 9.1 Browser essentials

Tabs and tab groups; address/search bar; back, forward, reload, stop; bookmarks and a privacy-conscious history option; download manager; permission prompts (camera, microphone, location, notifications, clipboard); clear-data controls; search-engine selection; accessible keyboard navigation; dark interface with readable contrast; update and security-status indicators.

## 9.2 Privacy features

- Tracker and known-malicious-domain blocking using maintained lists.
- HTTPS-first and HTTPS-only modes with explicit handling of sites that cannot use HTTPS.
- Third-party cookie and storage controls; per-site permission controls.
- Disposable/private sessions; cleanup on exit when configured.
- Clear indicators for standard, private, and Tor modes (now: the N/S/I levels of the active Cell).
- DNS and proxy configuration that **cannot silently fall back** in Tor mode.
- Reduced exposure of unnecessary browser APIs where safe and compatible.
- Every privacy setting explains its compatibility impact.

## 9.3 Tor integration

- Optional Tor mode (N2/N3), clearly configured; connection status and clear errors; `.onion` support.
- **No direct-network fallback** when Tor mode is shown as active.
- Proxy, DNS, IPv4/IPv6, WebRTC and other leak paths tested explicitly (Part 12).
- "New identity" only if its behavior is well-defined and verified.
- Warnings that logging in, downloading, or opening files externally can reveal identity.
- **Critical:** do not route an ordinary browser through a SOCKS proxy and call it anonymous. Use Tor Browser's published design as the reference and treat anonymity claims as requiring specialist review.

## 9.4 Cybersecurity tools

| Tool | Behavior |
|---|---|
| **Request inspector** | Requests of the current tab: method, origin, destination, status, type, timing; third-party and tracker identification; filter and export a **sanitized** report; cookies and authorization headers redacted by default |
| **TLS/certificate viewer** | Subject, issuer, validity, chain; explains certificate errors; **no one-click unsafe bypass**; HTTPS and mixed-content status |
| **Redirect analyzer** | Redirect chain per navigation; transparent heuristics; a URL is never called malicious solely because it redirects |
| **Download protection** | File name, type, origin, location; warns on executable types; never auto-executes; optional local scanner integration only with consent and disclosure (now Module M8) |
| **Tracker and content report** | Blocked trackers and the rule that blocked them; temporary per-site exceptions that are visible and revocable |
| **Security event log** | Local events (blocks, certificate warnings, permission changes, Tor failures), retention controls, one-action clear, secrets redacted, no full URLs by default (now the Flight Recorder, Part 7.5) |

## 9.5 Later features

Stronger isolation where the engine supports it; multiple isolated profiles (now Cells); disposable containers for risky research (now Detonation Cell); optional local threat-intelligence feeds; safe URL reputation with clear disclosure of what leaves the device; local rule customization for researchers; sanitized diagnostics export; reproducible builds and signed update verification.

---

# Part 10. Repository layout

```text
aegis-browser/
├── README.md
├── SECURITY.md                 # how to report vulnerabilities
├── THREAT_MODEL.md
├── ARCHITECTURE.md             # includes engine-abstraction note
├── docs/
│   ├── AXES.md
│   ├── CELLS.md
│   ├── TRUST_LEDGER.md
│   ├── LINK_GUARD.md
│   ├── ROUTE_CONTRACTS.md
│   ├── MODULES.md
│   ├── PRIVACY_DEFAULTS.md
│   ├── BUILD.md
│   ├── RELEASE.md
│   ├── TEST_PLAN.md
│   └── LICENSES_AND_TRADEMARKS.md
├── upstream/                   # pinned Firefox ESR source reference + patch queue
│   ├── VERSION
│   └── patches/                # numbered, each with reason + test
├── branding/                   # Aegis name, icons, theme
├── config/
│   ├── axes/{network,surface,identity}/
│   ├── presets/
│   ├── policy/policies.json
│   ├── ledger-rules/           # versioned, each rule has a test
│   ├── linkguard-rules/        # lure lexicons per language, brand map, weights
│   └── contracts/              # route contract definitions
├── services/
│   ├── cell-manager/
│   ├── trust-ledger/
│   ├── api-tripwires/
│   ├── route-canary/
│   ├── flight-recorder/
│   ├── posture-check/
│   └── link-guard/
├── modules/                    # one folder per module with manifest.json
│   ├── link-cleaner/  download-inspector/  session-sweeper/
│   ├── site-xray/  command-palette/  cell-router/  scope-guard/
│   └── evidence-notes/  extension-airlock/  clipboard-guard/  qr-preview/ ...
├── ui/                         # chrome UI: security panel, Cell switcher, interstitials
├── tor/                        # Tor integration, bridge config, bootstrap handling
├── tests/
│   ├── axes/  conflicts/  cells/  ledger/  linkguard/  canary/
│   ├── detonation/  modules/  network-leaks/  crowd-analysis/  compat-corpus/
├── tools/                      # build, lint, release, test-page server
└── build/                      # mozconfig files, CI configuration
```

---

# Part 11. Threat model and honest limits

## 11.1 Assets

Browsing history and search queries; account sessions and tokens; local files and downloads; IP address and network metadata; DNS requests; profile data, cookies, local storage; cross-site identity and behavior patterns; integrity of updates and configuration; **module data (notes, snapshots, indexes)**.

## 11.2 Threats

| Threat | Main mitigations |
|---|---|
| Advertising and tracking networks | Tracker blocking, partitioning, I-axis, tripwires |
| Malicious or compromised websites | S-axis, site/process isolation, sandbox, ledger escalation |
| **Phishing sites and harmful downloads** | **Link Guard, Anchored Cells, Download Inspector, Detonation Cell, trusted-path UI** |
| Local malware / compromised OS | Out of scope to defeat; posture check reports degraded state |
| Network observers and hostile Wi-Fi | HTTPS-only, encrypted DNS, Tor mode |
| Malicious extensions | Extension Airlock, disabled in S3/S4/Detonation, built-in only in strict levels |
| Misconfigured proxy/DNS | Route Contracts, canary, fail closed |
| Supply-chain compromise | Pinned upstream, reproducible builds, signed updates, dependency inventory |
| Browser bug that defeats a level | Fast ESR updates; defense in depth; posture check |

## 11.3 Threats introduced by Aegis itself

| New risk | Mitigation |
|---|---|
| A site detects escalation and uses it as a signal | Apply on next load; minimal visible change; test for observable differences |
| Attacker triggers false positives to degrade usability | Escalate-only, per-site caps, rate limits |
| Per-Cell randomization makes the user look suspicious | Explain; allow I1 per Cell |
| Cell isolation bug leaks cookies or identity seeds | Automated isolation tests every release |
| Canary reveals metadata | Configurable endpoint; disclosure; offline mode |
| Flight Recorder leaks data | Redaction, no full URLs, optional encryption at rest |
| Users over-trust Detonation | Honest wording: reduces risk, not a malware sandbox |
| Phishing page imitates browser UI | Warnings only in Aegis chrome; user-chosen emblem and Cell color invisible to pages |
| Too many warnings cause users to ignore them | Calibrate on benign set; per-rule false-positive tracking; visible, revocable exceptions |
| Module becomes a privileged bridge for page scripts | Structured events only; no page-script APIs; fuzz module inputs |
| Complexity creates bugs | Phased rollout; every setting has a test; small patch set |

## 11.4 Limits that must be shown to users

- No browser, level, or Tor setting guarantees anonymity; logins, behavior, and shared files can identify you.
- Aegis users form a **small crowd**. Aegis cannot claim the blending of Tor Browser or Mullvad Browser unless its output is identical, which a derived product generally cannot assume. The honest claim is **reduced cross-site linkability and attack surface**.
- A browser or OS vulnerability can defeat any level until patched; updates are part of the model.
- Higher S levels break sites; the browser says so before and after.
- Local malware or a compromised OS defeats local protections and logs.
- Heuristic phishing detection has false positives and negatives and can be cloaked or evaded; **"no warning" is not "safe"**, and HTTPS is not evidence of safety.
- A security dashboard is not proof that a site is safe.
- Aegis is not an official Mozilla or Tor Project product.

---

# Part 12. Security requirements and leak-test matrix

## 12.1 Mandatory release requirements

- [ ] No Chromium/Blink dependency in the supported desktop build.
- [ ] Upstream security updates tracked and applied promptly.
- [ ] Certificate errors never silently ignored; no one-click unsafe bypass.
- [ ] Website content cannot reach privileged browser controls.
- [ ] Permission prompts are clear, per-site, and revocable.
- [ ] Tor mode has a verified **no-fallback** policy, validated at the network layer.
- [ ] DNS and network leak tests pass for supported configurations.
- [ ] Logs redact sensitive values by default.
- [ ] Downloads never execute automatically.
- [ ] Updates are authenticated and integrity-checked.
- [ ] Build artifacts and dependencies documented; build reproducible.
- [ ] Every level control has an enforcement test (not just a config check).
- [ ] Every Link Guard rule has positive and negative tests and a measured false-positive rate on a benign set.
- [ ] Cell isolation tests pass (cookies, storage, service workers, cache, permissions, identity seeds).
- [ ] Privacy defaults and data retention documented.
- [ ] **Independent security review before any strong anonymity or safety claim.**

## 12.2 Network leak-test matrix

1. Normal mode with the expected route.
2. Tor mode with Tor available.
3. Tor mode with the Tor process unavailable.
4. Tor mode during a connection interruption.
5. DNS resolution behavior in each mode (no plaintext DNS in N1/N2/N3).
6. IPv4 and IPv6 behavior.
7. WebRTC exposure.
8. Redirects, downloads, service workers, background requests.
9. Browser restart and session restoration.
10. Proxy misconfiguration and failed bootstrap.
11. **Per-Cell:** a Direct Cell and a Tor Cell open together do not cross routes.
12. **Canary:** declared route vs observed egress agree; violation fails closed.

**Expected result:** if the required route cannot be maintained, browsing fails closed. Validate with controlled test endpoints, never only the status icon.

---

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

---

# Part 14. Test strategy

## 14.1 Functional

Tabs, navigation, bookmarks, history, downloads, permissions, clear-data, settings persistence, keyboard navigation, update UI.

## 14.2 Security

- **Axis tests:** every control verified inside the running browser; cumulativity (S3 ⊇ S2); conflict rules.
- **Crowd analysis (R2):** record how level combinations change observable values; document which combinations are distinctive.
- **Ledger tests:** each rule fires on crafted local pages, escalates only, explains correctly, reverts.
- **Cell isolation:** cookies, localStorage, IndexedDB, service workers, cache, permissions, identity seeds.
- **Canary and leak tests:** Tor down, proxy misconfigured, IPv6, WebRTC, DNS; fail-closed.
- **Link Guard:** per-rule positive/negative; benign top-site false-positive rate; HTTP-with-password hard warning; HTTPS never labeled "safe"; external-open scrutiny; clipboard-command lure; cross-domain login form; Anchored Cell credential binding.
- **Detonation:** quarantine, no auto-open, storage destroyed, receipt matches reality.
- **Flight Recorder:** tamper detection, redaction.
- **Modules:** manifest permissions enforced; kill switch; cross-Cell isolation; fuzzing of module inputs.
- **Regression on every upstream update:** any pref that disappears or changes meaning fails the build.

## 14.3 Quality

Performance budgets (pre-load Link Guard and Link Cleaner checks must not add noticeable delay), memory with many tabs, crash recovery, accessibility, compatibility corpus per level, localization of warning text.

## 14.4 Safe testing rules

- Use **only your own or explicitly authorized** pages, networks, and systems.
- For phishing tests, use **offline labeled datasets** and **saved, defanged copies** of pages inside an isolated VM; never browse live phishing pages for testing.
- Keep test fixtures local and clearly labeled.

---

# Part 15. Release, update, legal and maintenance plan

- **Upstream tracking:** follow Firefox ESR security releases; rebase the patch queue each time; automated test run before release.
- **Builds:** reproducible, pinned toolchain, dependency inventory (SBOM), signed artifacts, published hashes.
- **Updates:** authenticated and integrity-checked; never silently downgrade a Tor Cell's route.
- **Vulnerability handling:** `SECURITY.md` with a reporting address, response targets, and coordinated disclosure.
- **Telemetry:** none by default; any crash reporting is opt-in and disclosed.
- **Rule and list updates:** Link Guard rules, brand maps, and tracker lists are versioned and signed; the Public Suffix List is refreshed regularly.
- **Licensing and trademarks (get proper legal advice before distribution):** Firefox source is under the Mozilla Public License; redistributing a modified build generally requires removing Mozilla's branding and trademarks and following Mozilla's trademark and distribution policies; bundled components (for example a content blocker) have their own licenses; Tor, Mullvad, and other marks belong to their owners. Do not imply Mozilla or Tor Project endorsement.
- **Documentation:** privacy defaults, retention, data flows (especially P3 modules), and user-facing limits.

---

# Part 16. Phase 0 build guide (Linux)

> Commands and file names below are a starting point. **Verify against Mozilla's current source documentation**, because repository hosting, mach commands, and options change between releases.

## 16.1 Hardware and prerequisites

- Linux (Ubuntu LTS or similar), a modern multi-core CPU, **16 GB RAM or more recommended**, and **tens of GB of free disk** for source and build output.
- Tools: `git`, `python3`, a C/C++ toolchain, Rust, Node.js; Mozilla's bootstrap script installs most of them.

## 16.2 Fast path first (recommended): prove the levels before compiling

Compiling Firefox is slow. Prove your policy design on a stock **Firefox ESR** install first:

1. Install Firefox ESR.
2. Use an **enterprise policies file** (`policies.json`) to set and lock settings where supported.
3. Use the **autoconfig** mechanism (`autoconfig.js` + a `.cfg` file) for preferences policies cannot set (VERIFY availability for your version).
4. Develop modules as **built-in WebExtensions** in a test profile.
5. Run the axis tests against this setup.

Illustrative policy fragment (**names and allowed preferences: VERIFY** against Mozilla's policy templates):

```json
{
  "policies": {
    "DisableTelemetry": true,
    "HttpsOnlyMode": "force_enabled",
    "EnableTrackingProtection": { "Value": true, "Locked": true, "Fingerprinting": true, "Cryptomining": true },
    "DNSOverHTTPS": { "Enabled": true, "Locked": true },
    "Preferences": {
      "javascript.options.ion": { "Value": false, "Status": "locked" },
      "javascript.options.baselinejit": { "Value": false, "Status": "locked" },
      "javascript.options.wasm": { "Value": false, "Status": "locked" },
      "webgl.disabled": { "Value": true, "Status": "locked" }
    }
  }
}
```

(The example above is an S3-flavored sketch, not a complete level.)

## 16.3 Building from source

1. Obtain the official Firefox source (check Mozilla's source documentation for the canonical repository and the **ESR branch/tag** you pin).
2. Run Mozilla's bootstrap (`./mach bootstrap`) and choose the desktop browser option.
3. Create a `mozconfig` for an **unmodified** baseline, for example:

```text
ac_add_options --enable-application=browser
mk_add_options MOZ_OBJDIR=@TOPSRCDIR/obj-aegis-baseline
```

4. Build (`./mach build`) and run (`./mach run`).
5. Record exact versions, commands, build time, and the hash of the result in `docs/BUILD.md`.
6. Only then apply branding and the first patches, one at a time, each with a test.

## 16.4 Definition of a successful first prototype

- Builds reproducibly on Linux from a pinned ESR revision.
- Launches as "Aegis" with its own branding and profile directory.
- Has a visible level indicator for the active Cell (even if only S2 exists).
- Passes the axis enforcement tests for the levels implemented so far.
- Has Link Cleaner, Download Inspector, and basic Link Guard (static URL stage) working as built-in extensions.
- Documents what is **not** protected yet.

---

# Part 17. Prototype code reference

All prototypes are local-only (no network), and `python3 -m unittest test_aegis` runs **27 tests**.

| File | Contents |
|---|---|
| `aegis_psl.py` | Public Suffix List parser: longest-match, wildcard, and exception rules; small fallback subset (load the official list for real use) |
| `linkguard_prototype.py` | Static URL analysis (dangerous schemes, `@`/credentials, IP hosts, punycode and mixed scripts, brand-in-subdomain, token-level lookalikes with confusable characters, shorteners, redirect parameters, link-text mismatch); lure-text scoring; login-form checks (password over HTTP, cross-domain post, lure + login); clipboard-command lure; verdict levels with plain-language reasons |
| `aegis_modules.py` | `clean_link` (M11), `inspect_download` (M8), `breach_lookup_prefix` and `password_basic_checks` (M9), `xray_headers` (M15), `Scope.check` (M16), `route_to_cell` (M1), `sweep` (M10) |
| `test_aegis.py` | PSL tests; Link Guard benign set (12 real sites + a short-brand false-positive case) and suspicious set; module tests including the standard SHA-1 vector |

**Known prototype limits:** small brand list and suffix subset; simple lexicons; no multi-language packs; no real browser integration; thresholds not yet tuned on a large benign corpus.
---

# Part 18. The complete building prompt

> **How to use:** paste the block below into an AI coding agent (for example Claude Code) at the root of an empty repository, and attach this master document plus the prototype files (`aegis_psl.py`, `linkguard_prototype.py`, `aegis_modules.py`, `test_aegis.py`). If the prototype files are missing, the agent re-implements them from Parts 7, 8 and 17. Run **one phase at a time** and review before continuing. Shorter per-phase prompts follow the master prompt.

## 18.1 Master prompt

~~~~text
ROLE
You are a senior browser-security engineer and technical lead. You are helping me build
"Aegis Browser": a desktop browser on the Gecko engine (Firefox ESR base) with
multi-level security, isolated Cells, phishing protection, and a module ecosystem.
Work carefully, verify before you claim, and keep the patch set small and auditable.

SOURCE OF TRUTH
The attached document "AEGIS BROWSER: MASTER BLUEPRINT (A to Z)" is the specification.
Parts 5 to 8 define behavior; Parts 11 and 12 define security requirements; Part 13 is
the roadmap. If something is ambiguous or contradicts itself, stop and ask me instead of
guessing. If the specification and upstream Firefox documentation disagree about a
preference, policy, or API, trust the pinned upstream version and tell me.

HARD CONSTRAINTS (never violate)
1. No Chromium, Blink, Electron, CEF, or Chromium WebView anywhere in the supported build.
2. Do not write a browser engine, custom TLS, custom cryptography, or a custom password
   vault. Reuse the engine and OS primitives; integrate established tools for credentials.
3. Prefer, in this order: enterprise policies and locked preferences -> built-in
   (system) WebExtensions -> chrome UI -> engine patches. Every engine patch must be
   numbered in upstream/patches/ with a written reason, an owner field, and a test.
4. Website content is untrusted. Never expose privileged APIs to web content. Protection
   services consume structured events, never page scripts with elevated rights.
5. Fail closed: if a protection cannot be verified, block or show a clear degraded state.
   Never silently fall back (especially in Tor mode).
6. Every setting or control must have an enforcement test that runs against the running
   browser, not only a check that a config file exists.
7. Local-first: no telemetry. Anything that sends data off the device is opt-in, disclosed
   exactly, and routed through Tor when the Cell is in Tor mode.
8. Honest claims only: never write UI text, docs, or comments claiming anonymity or that a
   site is "safe". HTTPS is not evidence of safety; "no warning" is not "safe".
9. Automatic protection changes may only ESCALATE; only the user may lower protection.
   Every automatic change shows its rule, its evidence, and a one-click revert.
10. Warnings and trust indicators appear only in Aegis chrome, never in page-controlled space.
11. Do not implement exploit, attack, evasion, or malware functionality. Security Lab
    modules only observe, scope, and document, for systems the user owns or is authorized
    to test.
12. Do not browse live phishing or malicious sites for testing. Use offline labeled
    datasets, local mock pages, and saved defanged copies inside an isolated VM.
13. Verify every Firefox preference name, policy key, and API against the pinned ESR
    version before using it. Anything unverified is marked VERIFY in code comments and docs.

PRODUCT MODEL (summary of the spec)
- Three independent axes: Network N0..N3 (Direct, Encrypted DNS, Tor, Tor+bridges),
  Surface S1..S4 (Standard, Guarded, Strict, Static), Identity I1..I4 (Native, Uniform,
  Cell-seeded, Minimal-API). R1: S never changes fingerprint-visible output except where a
  feature disappears; I never changes memory-safety exposure. R2: in N2/N3, I is locked to
  I2 and only measured S levels are offered without acknowledgment.
- Cells: per-task compartments owning route, S level, I policy, storage, permissions,
  downloads, log scope, a name, a color. Types: persistent, session, ephemeral (RAM-only).
  Anchored Cells bind credentials and navigation to declared registrable domains.
- Services: Trust Ledger (deterministic, explainable, escalate-only), API Tripwires,
  Route Contracts + Policy Gate + canary (fail closed), Flight Recorder (append-only hash
  chain, redacted), Verification Layer (declared vs verified posture), Detonation Cell,
  Link Guard (pre-click and content-stage phishing defense, trusted-path UI).
- Modules M1..M24 per Part 8, each with a Module Manifest (id, version, permissions,
  privacy class P0..P3, Cell scope, stores, network, kill switch, tests).

WORKING PROTOCOL
- Work in PHASES from Part 13, one phase per session. At the start of each phase: restate
  the goal, list the files you will create or change, list open questions, and wait for my
  approval if any decision is not already settled in the spec.
- Make small, reviewable commits. After each change: run the relevant tests and show me the
  results. Do not report a test as passing unless you ran it.
- Keep a running docs/DECISIONS.md (what, why, alternatives, date) and docs/VERIFY.md (every
  unverified preference/policy/API and its verification status).
- When you find a flaw in the spec or in earlier work, say so plainly, fix it, and add a
  test that would have caught it.
- Never claim something works that you have not exercised. Say what you did NOT test.
- Prefer boring, readable code with comments explaining security reasoning. Rust for
  separate services where a service is needed; JavaScript/TypeScript for built-in
  extensions; Python for tooling and test harnesses. Follow the upstream project's style
  for any engine patch.

REPOSITORY LAYOUT
Create the layout from Part 10 of the spec (docs/, upstream/, branding/, config/axes,
config/presets, config/policy, config/ledger-rules, config/linkguard-rules,
config/contracts, services/, modules/, ui/, tor/, tests/, tools/, build/).

PHASE 0: BASELINE (start here)
Goal: a reproducible, unmodified Firefox ESR baseline and a fast prototype environment.
Tasks:
 a) Write docs/BUILD.md for my Linux machine: prerequisites, how to obtain the pinned
    ESR source (verify the canonical repository and tag in Mozilla's current docs), the
    bootstrap step, an unmodified mozconfig, build, run. Record versions and hashes.
 b) Create the "fast path": a test profile that applies enterprise policies and locked
    preferences to a stock Firefox ESR install, plus a harness for developing and loading
    built-in extensions. Document which settings policies can and cannot set (VERIFY).
 c) Create the test harness skeleton in tests/ (runner, fixtures, a local test-page
    server that serves labeled local mock pages) and CI configuration that runs the unit
    tests on every commit.
 d) Port the provided prototypes into the repo (aegis_psl, linkguard, modules) with their
    27 tests, and make them pass. Point the PSL loader at the official Public Suffix List
    text file instead of the fallback subset, with a refresh script.
Acceptance: baseline builds and runs; fast-path profile launches with policies applied;
tests run in CI; BUILD.md reproduces the result on a clean machine; docs/VERIFY.md exists.
Then STOP and report.

PHASE 1: IDENTITY AND SHELL
Branding (name, icons, theme, own profile directory, no Mozilla marks), UI shell, and a
visible level indicator for the active Cell (placeholder values allowed). No security
claims in UI text. Acceptance: branded build launches; trademark review notes recorded in
docs/LICENSES_AND_TRADEMARKS.md. STOP and report.

PHASE 2: AXES S AND I, PRESETS, TIER-1 MODULES
2a Save Part 5 of the spec as docs/AXES.md, then implement S1..S4 from it as versioned level files plus locked policies. For
   every control, a runtime enforcement test. CI fails if a control lacks a test.
   For S4 per-origin script control, first write a design spike comparing a built-in
   system extension with privileges versus an engine patch; recommend one; wait for my OK.
2b Implement I1..I4. Before writing custom seeded noise for I3, evaluate what the pinned
   engine's fingerprinting protection already provides and report. Add crowd-analysis
   test scaffolding.
2c Presets and the conflict rules from section 5.5, each with a test.
2d Build Tier-1 modules as built-in extensions with manifests, kill switches, tests:
   Link Cleaner (M11), Download Inspector (M8), Session Sweeper (M10), Site X-ray (M15),
   Command Palette (M2).
Acceptance: all level controls enforced and tested; conflict tests pass; modules pass
their tests and respect their manifests.

PHASE 3: NETWORK AXIS
N1 strict encrypted DNS (no silent plaintext fallback). N2 Tor with remote DNS, WebRTC
policy, no direct fallback. N3 bridges. Implement Route Contracts enforced at the network
layer (and OS firewall rules where available), plus the canary. Build the full leak matrix
in tests/network-leaks (Part 12.2) using controlled local test endpoints. Acceptance: kill
Tor mid-session and prove no direct traffic; DNS/IPv6/WebRTC tests pass. Wording in UI is
honest about limits. Independent verification steps documented.

PHASE 4: CELLS
Cell manager: persistent/session/ephemeral Cells, per-Cell storage, permissions, downloads
folder, identity seed, color/name/emblem. Start with storage and identity isolation, then
route. Cells as Workspaces with auto-routing (M1) and Scope Guard (M16). Acceptance:
isolation tests prove no cookie, localStorage, IndexedDB, service worker, cache,
permission, or seed crosses Cells; two Cells with different routes do not cross routes.

PHASE 5: VERIFICATION AND LINK GUARD (STAGES 1-3)
Flight Recorder (hash chain, redaction, wipe), Verification Layer (declared vs verified
posture), request inspector, TLS viewer (no unsafe bypass), redirect analyzer. Link Guard
stages 1 to 3 (static URL, transport HTTP/HTTPS, local reputation) running at click,
address bar, external-open, and redirect hops. Verdict UI with plain-language evidence
and safe alternatives. Build a benign-site corpus and measure false positives per rule.
Acceptance: every rule has an id, explanation, severity, positive and negative tests;
benign false-positive rate reported and within target agreed with me.

PHASE 6: TRUST LEDGER, TRIPWIRES, LINK GUARD (STAGES 5-7), ANCHORED CELLS
Trust Ledger rules as versioned files (observe-only first, then escalate-only with next-load
application, explanations, and revert). API Tripwires with a plain-language report.
Link Guard content and behavior stages: lure wording packs (multi-language), credential-
harvesting checks, brand impersonation via local brand map, password-manager origin
mismatch, fake-window (Browser-in-the-Browser) detection with the trusted-path UI,
ClickFix/clipboard-command warnings, OAuth/device-code consent warnings, passkey-downgrade
warning, notification and auto-download abuse. Anchored Cells. Acceptance: mock-page tests
for every rule; warnings reviewed for clarity; no remote lookups unless opted in.

PHASE 7: DETONATION CELL
Ephemeral RAM-only Cell, S4+I2+N2 defaults, static rendering path, quarantined downloads,
cleanup receipt that reflects verified deletion. Wording: reduces risk; not a malware
sandbox. Acceptance: cleanup tests pass.

PHASE 8: TIER 2 AND 3 MODULES
Per Part 8 build order, each with manifest, tests, threat note. Do not start Tier 4.

PHASE 9: HARDENING AND RELEASE
Reproducible builds, SBOM, signed artifacts and updates, SECURITY.md, privacy docs,
update-tracking automation for ESR security releases, and a package for an external
security review. Do not make strong anonymity or safety claims before the review.

OUTPUT FORMAT FOR EVERY STEP
1) What you did (short). 2) Files created/changed. 3) Tests run and exact results.
4) What you did NOT test or could not verify. 5) Decisions needed from me. 6) Next step.

START NOW
Begin with PHASE 0. First reply with: your understanding of the project in 10 lines,
the list of questions you need answered (OS and distro, CPU/RAM/disk, whether you want
the fast path first, ESR version preference), and your plan for Phase 0. Do not write code
until I answer.
~~~~

## 18.2 Short per-phase prompts

Use these after the master prompt is loaded, to restart a phase in a fresh session.

| Phase | Prompt |
|---|---|
| 0 | "Continue Aegis Phase 0 per the master prompt. Produce docs/BUILD.md, the fast-path profile, the test harness skeleton, and port the prototypes with all 27 tests passing. Report test output." |
| 1 | "Aegis Phase 1: branding and UI shell with a Cell level indicator. No security claims in UI text. Record trademark/licence notes." |
| 2 | "Aegis Phase 2: implement S1 to S4 and I1 to I4 as level files with enforcement tests; start with a design spike for S4 script control and for I3 seeded noise; then presets, conflict rules, and the Tier-1 modules." |
| 3 | "Aegis Phase 3: implement N1 to N3, Route Contracts, the canary, and the complete leak matrix with controlled endpoints. Prove fail-closed behavior." |
| 4 | "Aegis Phase 4: implement Cells (storage and identity isolation first, then route), Cells as Workspaces with routing, and Scope Guard, with isolation tests." |
| 5 | "Aegis Phase 5: Flight Recorder, Verification Layer, request inspector, TLS viewer, redirect analyzer, and Link Guard stages 1 to 3 with a benign corpus and per-rule false-positive measurement." |
| 6 | "Aegis Phase 6: Trust Ledger, API Tripwires, Link Guard content/behavior stages, trusted-path UI, and Anchored Cells, with mock-page tests for every rule." |
| 7 | "Aegis Phase 7: Detonation Cell with RAM-only storage, static rendering, quarantine, and a verified cleanup receipt." |
| 8 | "Aegis Phase 8: Tier 2 and 3 modules in the order of Part 8.3, each with manifest, tests, and a threat note." |
| 9 | "Aegis Phase 9: reproducible builds, SBOM, signed updates, SECURITY.md, ESR tracking automation, and an external-review package." |

## 18.3 Review prompt (use between phases)

~~~~text
Review the work from the last phase against the Aegis master specification. List:
(1) every requirement in Parts 5 to 8 and 12 that is now met, with the test that proves it;
(2) requirements that are partly met or untested;
(3) any claim in code, UI text, or docs that is stronger than what is tested;
(4) new attack surface introduced and how it is mitigated;
(5) VERIFY items resolved and still open.
Be blunt. Do not mark anything as done unless you ran its test.
~~~~

---

# Part 19. Glossary

| Term | Meaning |
|---|---|
| **Aegis** | Working name of this browser |
| **Anchored Cell** | A Cell bound to a set of registrable domains; credentials fill only there |
| **Attack surface (S axis)** | The amount of engine functionality a page can reach |
| **Cell** | Isolated browsing compartment owning route, levels, identity, storage, permissions, downloads, logs |
| **Detonation Cell** | Ephemeral, static, Tor-routed Cell for opening suspicious links |
| **ESR** | Firefox Extended Support Release line |
| **Fail closed** | Block when a protection cannot be verified, rather than falling back |
| **Fingerprinting** | Identifying a device from observable browser characteristics |
| **Flight Recorder** | Local append-only, hash-chained security event log |
| **Gecko** | Mozilla's browser engine |
| **I axis (Identity)** | What a site can learn about the device |
| **JIT** | Just-in-time compilation of JavaScript; disabling reduces some attack surface |
| **k-anonymity lookup** | Send only a short hash prefix to a service and compare the rest locally |
| **Link Guard** | Aegis phishing-defense pipeline |
| **N axis (Network)** | Where traffic goes |
| **PSL** | Public Suffix List, used to find the registrable domain |
| **R1 / R2** | Design rules: decoupling of S and I; crowd awareness in Tor mode |
| **Registrable domain** | The domain a user can register, such as `example.co.uk` |
| **Route Contract** | Declared, enforced network policy for a Cell |
| **RLBox** | Firefox's sandboxing of certain third-party libraries |
| **Trust Ledger** | Explainable, escalate-only risk engine |
| **Tripwire** | Counter of calls to fingerprint-relevant APIs |
| **Trusted path** | UI elements a web page cannot imitate |
| **VERIFY** | A preference, policy, or API that must be confirmed on the pinned version |

---

# Part 20. References

Verify that links are current before relying on them.

- Mozilla source documentation: https://firefox-source-docs.mozilla.org/
- Firefox enterprise policy templates: https://mozilla.github.io/policy-templates/
- WebExtensions documentation: https://developer.mozilla.org/docs/Mozilla/Add-ons/WebExtensions
- Tor Browser manual (security settings) and design documentation: https://tb-manual.torproject.org/ and the Tor Project's published Tor Browser design document
- Arkenfox user.js (hardened Firefox preferences reference): https://github.com/arkenfox/user.js
- LibreWolf: https://librewolf.net/ ; Mullvad Browser: https://mullvad.net/en/browser
- Public Suffix List: https://publicsuffix.org/list/
- Safe Browsing and hash-prefix privacy approach: Mozilla and Google Safe Browsing documentation
- Breach-check k-anonymity range API: Have I Been Pwned "Pwned Passwords" documentation
- Apple Lockdown Mode and Microsoft Edge Enhanced Security Mode: vendor documentation (used here as design references only)
- Ladybird: https://ladybird.org/ ; Servo: https://servo.org/

---

*End of master document.*
