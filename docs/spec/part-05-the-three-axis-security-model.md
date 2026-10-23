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
