# Aegis Browser — Security Policy

## Reporting a vulnerability

**Do not file a public GitHub issue for security vulnerabilities.**

Please send a report to: [TO BE FILLED — set up a security contact before any public release]

Include:
- A description of the vulnerability and the component affected
- Steps to reproduce or a proof-of-concept (against your own test environment only)
- The potential impact and affected versions
- Whether you would like to be credited in the advisory

## Response targets (to be confirmed before first public release)

| Timeframe | Target |
|---|---|
| Acknowledgement | Within 5 business days |
| Initial assessment | Within 10 business days |
| Coordinated disclosure | Agreed with reporter; default 90 days |

## Scope

In scope: the Aegis browser codebase, configuration, and built-in modules.
Out of scope: the upstream Firefox/Gecko engine itself (report those to Mozilla at
https://www.mozilla.org/en-US/security/bug-bounty/); third-party services integrated
via opt-in modules.

## Upstream security releases

Aegis tracks the Firefox ESR security release line. When Mozilla publishes a security
update, the patch queue is rebased and a new Aegis build is tested and released promptly.
The current pinned ESR: see `upstream/VERSION`.

## Limits

Aegis is not an official Mozilla or Tor Project product. Do not report Aegis issues to
Mozilla or the Tor Project.
