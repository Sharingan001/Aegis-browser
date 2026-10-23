# Part 16. Phase 0 build guide (Linux)

> Commands and file names below are a starting point. **Verify against Mozilla's current source documentation**, because repository hosting, mach commands, and options change between releases.

## 16.1 Hardware and prerequisites

- Linux (Ubuntu LTS or similar), a modern multi-core CPU, **16 GB RAM or more recommended**, and **tens of GB of free disk** for source and build output.
- Tools: `git`, `python3`, a C/C++ toolchain, Rust, Node.js; Mozilla's bootstrap script installs most of them.

## 16.2 Fast path first (recommended): prove the levels before compiling

Compiling Firefox is slow. Prove your policy design on a stock **Firefox ESR** install first:

1. Install Firefox ESR.
2. Use an **enterprise policies file** (`policies.json`) to set and lock settings where supported.
3. Use the **autoconfig** mechanism (`autoconfig.js` + a `.cfg` file) for preferences policies cannot set (VERIFY availability for your version).
4. Develop modules as **built-in WebExtensions** in a test profile.
5. Run the axis tests against this setup.

Illustrative policy fragment (**names and allowed preferences: VERIFY** against Mozilla's policy templates):

```json
{
  "policies": {
    "DisableTelemetry": true,
    "HttpsOnlyMode": "force_enabled",
    "EnableTrackingProtection": { "Value": true, "Locked": true, "Fingerprinting": true, "Cryptomining": true },
    "DNSOverHTTPS": { "Enabled": true, "Locked": true },
    "Preferences": {
      "javascript.options.ion": { "Value": false, "Status": "locked" },
      "javascript.options.baselinejit": { "Value": false, "Status": "locked" },
      "javascript.options.wasm": { "Value": false, "Status": "locked" },
      "webgl.disabled": { "Value": true, "Status": "locked" }
    }
  }
}
```

(The example above is an S3-flavored sketch, not a complete level.)

## 16.3 Building from source

1. Obtain the official Firefox source (check Mozilla's source documentation for the canonical repository and the **ESR branch/tag** you pin).
2. Run Mozilla's bootstrap (`./mach bootstrap`) and choose the desktop browser option.
3. Create a `mozconfig` for an **unmodified** baseline, for example:

```text
ac_add_options --enable-application=browser
mk_add_options MOZ_OBJDIR=@TOPSRCDIR/obj-aegis-baseline
```

4. Build (`./mach build`) and run (`./mach run`).
5. Record exact versions, commands, build time, and the hash of the result in `docs/BUILD.md`.
6. Only then apply branding and the first patches, one at a time, each with a test.

## 16.4 Definition of a successful first prototype

- Builds reproducibly on Linux from a pinned ESR revision.
- Launches as "Aegis" with its own branding and profile directory.
- Has a visible level indicator for the active Cell (even if only S2 exists).
- Passes the axis enforcement tests for the levels implemented so far.
- Has Link Cleaner, Download Inspector, and basic Link Guard (static URL stage) working as built-in extensions.
- Documents what is **not** protected yet.
