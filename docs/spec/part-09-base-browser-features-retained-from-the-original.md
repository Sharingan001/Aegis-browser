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
