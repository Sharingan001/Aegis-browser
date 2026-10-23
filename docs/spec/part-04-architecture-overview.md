# Part 4. Architecture overview

```text
+-------------------------------------------------------------------+
|                          Aegis Browser UI                         |
| Tabs | Address bar | Security panel | Cell switcher | Palette     |
+--------------------------------+----------------------------------+
                                 |
        +------------------------v-------------------------+
        |                    CELL MANAGER                   |
        |  per-Cell: Route (N) + Surface (S) + Identity (I) |
        |  storage, permissions, downloads, log scope       |
        +--------+-----------------+-----------------+------+
                 |                 |                 |
     +-----------v---+   +---------v--------+   +----v------------+
     | Policy Gate   |   | Protection Svcs  |   | Modules (M1..)  |
     | Route Contract|   | Link Guard       |   | built-in ext    |
     | Level policies|   | Trust Ledger     |   | + chrome UI     |
     |               |   | API Tripwires    |   |                 |
     +-------+-------+   | Flight Recorder  |   +--------+--------+
             |           | Verification     |            |
             |           +---------+--------+            |
             +-------------------+-+---------------------+
                                 |
        +------------------------v-------------------------+
        |         Gecko / Firefox ESR foundation            |
        |  rendering | JS | storage | networking | sandbox   |
        +------------------------+-------------------------+
                                 |
        +------------------------v-------------------------+
        |     Network: Direct | Encrypted DNS | Tor | Bridges |
        +---------------------------------------------------+
```

## 4.1 Trust boundaries

- **Website content is untrusted.** Always.
- Privileged UI and services never expose privileged APIs to web content.
- Services consume **structured events**, not page scripts with elevated rights.
- Network policy is enforced in the network/policy layer, **not only in UI preferences**.
- No custom TLS or crypto; use the engine and OS primitives.
- No passwords, tokens, or raw authorization headers in diagnostics or logs.
- Warnings and trust indicators live in Aegis chrome, never in page-controlled space.

## 4.2 Implementation strategy

1. **Policies and locked preferences** (versioned config files) for levels.
2. **Built-in (system) WebExtensions** for modules, using supported APIs (tabs, downloads, cookies, storage, commands, omnibox, sidebar, contextual identities, proxy, webRequest).
3. **Chrome UI** (security panel, Cell switcher) using the engine's supported UI layer.
4. **Engine patches only when 1 to 3 cannot do it**, each tracked in a patch queue.
