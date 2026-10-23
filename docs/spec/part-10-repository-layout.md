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
