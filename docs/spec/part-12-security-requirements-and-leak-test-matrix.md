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
