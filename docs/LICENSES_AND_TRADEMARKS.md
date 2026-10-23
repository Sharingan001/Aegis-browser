# Aegis Browser: Licensing, Trademarks, and Upstream Compliance Audit

**Document Version:** 1.0.0  
**Date:** 2026-10-23  
**Status:** Canonical Reference Document  
**Audited Against:** Mozilla Firefox ESR 153.5.1esr, Mozilla Public License 2.0, Mozilla Trademark Policy  

---

## 1. Executive Summary & Legal Disclaimer

> [!CAUTION]
> **LEGAL DISCLAIMER:** This document represents an engineering and architectural analysis of open-source license obligations and trademark guidelines based on publicly available documentation from the Mozilla Foundation, the Free Software Foundation, and the Open Source Initiative. It does not constitute formal legal advice. Sections explicitly designated with `[LEGAL ADVICE REQUIRED]` identify areas where qualified intellectual property counsel must review distribution practices before public releases.

Aegis Browser is built upon the Gecko engine (pinned upstream: Firefox ESR 153.5.1esr). While Gecko and the Firefox codebase are published under liberal open-source terms (primarily the Mozilla Public License 2.0), **Mozilla's trademarks, logos, and hosted cloud service endpoints are strictly proprietary and protected.**

Aegis Browser operates under a strict two-pillar compliance policy:
1. **Full source and copyright compliance:** Strict adherence to MPL 2.0 requirements for covered source files, notices, and patent grants.
2. **Complete de-branding and service decoupling:** 100% removal or replacement of Mozilla trademarks, logos, wordmarks, affiliate links, telemetry channels, and default cloud service endpoints.

---

## 2. Mozilla Public License 2.0 (MPL 2.0) Compliance Analysis

The upstream Firefox source tree is licensed under the [Mozilla Public License, version 2.0 (MPL 2.0)](https://www.mozilla.org/en-US/MPL/2.0/).

### 2.1 What Aegis CAN Do
* **Modify and distribute source:** Aegis may freely inspect, modify, adapt, build, and redistribute the Gecko engine and Firefox browser frontend source code.
* **Distribute compiled binaries:** Aegis may compile the modified codebase and distribute executable binaries to end users.
* **Combine with other code (Larger Work):** Under MPL 2.0 Section 3.3 (*"Larger Works"*), Aegis may create a Larger Work by combining Covered Software with files under other open-source or proprietary licenses, provided the MPL obligations for Covered Software are met.
* **Commercial or non-commercial deployment:** MPL 2.0 permits commercial distribution, internal organizational deployment, and non-profit distribution.

### 2.2 What Aegis MUST Do (Mandatory Obligations)
1. **Source Availability for Modifications (Section 3.1 & 3.2):**
   * Any file in the upstream source tree that Aegis modifies remains "Covered Software".
   * Whenever Aegis distributes executable binaries containing modified Covered Software, Aegis **must make the source code of all modifications available** in an accessible form under MPL 2.0 (e.g., via public git repository patch series or source archives).
   * Notice must be included informing recipients how they can obtain the source code of the modifications.
2. **Preserve Notices (Section 3.1):**
   * Aegis may not remove or alter any copyright, patent, or trademark notices, or license header blocks present in upstream files.
3. **Patent Grant and Defense (Section 5):**
   * Upstream contributors grant a non-exclusive, royalty-free, worldwide patent license to use, make, and distribute the Covered Software.
   * If Aegis initiates patent litigation against any entity claiming that Covered Software infringes patents, the patent licenses granted to Aegis under MPL 2.0 terminate (patent defense clause).

### 2.3 Distinction: Modifications vs. Independent Files
* **Modified Upstream Files (`upstream/patches/`):** Must be licensed under MPL 2.0.
* **New Independent Modules (`modules/`, `services/`, `ui/`):** Files that are wholly original to Aegis and not derivative works of existing Gecko files can be licensed under Aegis's chosen license (e.g., MPL 2.0, Apache 2.0, or MIT). Aegis elects to license independent Aegis-authored components under **MPL 2.0** or **Apache-2.0 / MIT** for clean compatibility.

---

## 3. Mozilla Trademark Policy Compliance

The Mozilla Foundation owns registered trademarks in wordmarks, logos, and trade dress. Distributing a modified Gecko browser under Mozilla's trademarks is **strictly prohibited** without a separate trademark license agreement.

### 3.1 Governing Policy
Mozilla's official trademark policy ([https://www.mozilla.org/en-US/foundation/trademarks/policy/](https://www.mozilla.org/en-US/foundation/trademarks/policy/)) states:
* *"If you distribute a modified version of Firefox, you must not use the Mozilla or Firefox trademarks or logos in connection with that distribution."*
* The standard open-source build requires configuring an unbranded build or replacing all branding assets.

### 3.2 Complete De-Branding Inventory (What Aegis Must Remove/Replace)

| Category | Upstream Asset / Configuration | Action in Aegis | Target / Replacement |
| :--- | :--- | :--- | :--- |
| **Product Name** | `Firefox` | Replace | `Aegis Browser` (or `Aegis`) |
| **Binary Executable** | `firefox`, `firefox-bin` | Rename | `aegis`, `aegis-bin` |
| **Vendor Identity** | `Mozilla`, `Mozilla Corporation` | Replace | `Aegis Project` (or empty) |
| **Branding Directory** | `browser/branding/official` | Purge / Override | Replace with `branding/` (own artwork) |
| **Logos & Artwork** | Fox curled around globe, Nightly earth | Replace | Aegis Shield insignia (no fox, no globe) |
| **App Icons** | `default*.png`, `firefox.ico`, `icon.svg` | Replace | Aegis custom icon set (16px to 512px) |
| **Profile Path** | `~/.mozilla/firefox` | Divert | `~/.aegis/browser` (or OS-standard XDG) |
| **User-Agent Token** | `Mozilla/5.0 (...) Gecko/... Firefox/153.0` | Review / Neutralize | Retain Gecko compatibility token; avoid infringing mark claims |
| **`about:` Pages** | `about:firefox`, Firefox text in `about:support` | Patch | Aegis custom `about:` information |
| **Default Bookmarks** | Mozilla community, affiliate bookmarks | Purge | Clean baseline; no commercial affiliate URLs |
| **Default Search** | Mozilla search partner revenue plugins | Remove affiliates | Neutral default search providers |

### 3.3 Upstream Cloud Services & Network Decoupling

A critical security and trademark requirement: Aegis **must not hit Mozilla infrastructure** by default.

1. **Telemetry & Crash Reporting:**
   * Disable `MOZ_TELEMETRY_REPORTING`.
   * Disable `MOZ_CRASHREPORTER` or point report submission away from `crash-stats.mozilla.org`.
2. **Firefox Accounts (Sync):**
   * Decouple or disable Firefox Sync endpoints (`identity.sync.tokenserver.uri`, `fxaccounts.*`).
3. **Pocket:**
   * Disable `extensions.pocket.enabled`.
4. **Safe Browsing:**
   * Upstream Firefox fetches Google Safe Browsing and Mozilla phishing blocklists.
   * Aegis replaces external centralized lookups with local Link Guard engines, local brand maps, and local PSL heuristics. Remote lookup is opt-in only.
5. **Add-on Repository (AMO):**
   * Prevent silent background updates or extension discovery hitting `addons.mozilla.org` without user authorization.

---

## 4. Third-Party Bundled Components & Licenses

Gecko integrates numerous upstream third-party libraries. Aegis maintains an ongoing inventory:

| Component | Upstream Role | License | Aegis Status & Constraints |
| :--- | :--- | :--- | :--- |
| **NSS / NSPR** | TLS, PKI, cryptographic primitives | MPL 2.0 | Retained unmodified in baseline. |
| **ICU** | Internationalization, unicode tables | Unicode License / ICU | Retained unmodified. |
| **SQLite** | Storage for history, cookies, permissions | Public Domain / SQLite Blessing | Retained unmodified. |
| **libvpx / dav1d** | VP8/VP9 and AV1 video decode | BSD-3-Clause | Retained unmodified. |
| **Skia / WebRender** | GPU-accelerated rendering pipeline | BSD / Apache 2.0 | Retained unmodified. |
| **Rust Toolchain & Crates** | Core rendering and memory-safe parsers | Apache 2.0 / MIT | Pinned versions in toolchain. |
| **Public Suffix List (PSL)** | Effective TLD / domain boundaries | MPL 2.0 | Used by `aegis_psl.py` and Gecko core. |
| **Tor / Arti** | N2/N3 anonymized routing daemon | BSD-3-Clause / MIT | Integrated out-of-process via SOCKS5/ControlPort. |
| **OpenH264** | Cisco H.264 video codec | BSD-2-Clause (source) / Cisco Binary | [LEGAL ADVICE REQUIRED] Patent indemnification. |
| **Widevine CDM** | Proprietary Encrypted Media Extensions (DRM) | Proprietary / Google EULA | **Excluded.** Aegis disables DRM by default. |

---

## 5. Items Requiring Independent Legal Advice `[LEGAL ADVICE REQUIRED]`

Before public binary or package distribution, the project owner must obtain formal counsel on the following items:

### 5.1 Nominative Fair Use in Technical Descriptions
* **Question:** How may Aegis describe its heritage in user manuals, technical papers, and settings dialogs without infringing Mozilla trademarks?
* **Current Guidance:** Nominative fair use generally allows factual statements such as *"Aegis Browser is built upon the open-source Gecko rendering engine derived from Mozilla Firefox ESR."* However, no phrasing may imply sponsorship, endorsement, or certification by Mozilla.

### 5.2 Patent Licensing and Media Codecs (H.264 / AAC / HEVC)
* **Question:** What is the legal exposure for distributing compiled browser binaries that decode MPEG-LA patented formats (H.264, AAC)?
* **Context:** Mozilla distributes binary OpenH264 downloaded dynamically from Cisco to leverage Cisco's MPEG-LA patent royalty coverage. Directly compiling and bundling open-source H.264 decoders without patent licenses can create patent infringement risk in jurisdictions enforcing software patents.

### 5.3 Export Controls (EAR) and Tor Cryptographic Capabilities
* **Question:** Does packaging Aegis with Tor integration (N2/N3) and advanced cryptographic modules trigger US Export Administration Regulations (EAR) or European Dual-Use export restrictions?
* **Context:** Tor and encryption technologies generally qualify for open-source publicly available exemptions (e.g., License Exception TSU / ENC), but formal classification and self-classification filings may be required prior to hosting downloads.

### 5.4 Third-Party Trademark Treatment (Tor, Mullvad, etc.)
* **Question:** How can Aegis refer to Tor network integration, Tor onion services, and external VPN routes without infringing The Tor Project's or Mullvad's trademarks?
* **Context:** Trademarks like "Tor" and "The Onion Router" belong to The Tor Project, Inc. Aegis UI must clearly state *"Tor is a registered trademark of The Tor Project, Inc. Aegis Browser is an independent project and is not endorsed by or affiliated with The Tor Project."*

---

## 6. Implementation Action Plan for Aegis Builds

1. **Phase 1a (Current):**
   * Complete branding asset suite in `branding/` (Shield insignia, obsidian theme).
   * Verify all prototype code and UI components omit proprietary marks and refrain from false security claims.
2. **Phase 1b / 1c (Source Build & Patch Queue):**
   * Create `upstream/patches/0001-branding-aegis.patch`:
     - Set `MOZ_APP_NAME=aegis` and `MOZ_APP_BASENAME=Aegis`.
     - Point branding directory to `branding/`.
     - Set custom vendor string and profile storage directory (`~/.aegis`).
   * Create `upstream/patches/0002-de-telemetry-de-service.patch`:
     - Strip Mozilla telemetry URLs, crash reporting endpoints, and commercial bookmark feeds.
