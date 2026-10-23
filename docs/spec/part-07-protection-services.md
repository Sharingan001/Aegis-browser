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
