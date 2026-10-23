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
