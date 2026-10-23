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
