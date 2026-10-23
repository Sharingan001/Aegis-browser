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
