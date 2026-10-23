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
