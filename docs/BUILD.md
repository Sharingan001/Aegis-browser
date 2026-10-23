# Aegis Browser — Build Guide

**Status:** Phase 0 — fast path only. No source build yet.

---

## Pinned ESR version

| Item | Value |
|---|---|
| Version | 153.5.1esr |
| Release date | 2026-07-21 |
| Verified | 2026-10-23 from https://www.mozilla.org/en-US/firefox/organizations/all/ |
| Tarball | `firefox-153.5.1esr.tar.xz` (linux-x86_64/en-US) |
| SHA-256 | `e289bdc532decf2b54dea9b5ac64cf6f84a62eeec4d4a9ec2f69590f61b0ff1c` |
| SHA-256 source | https://releases.mozilla.org/pub/firefox/releases/153.5.1esr/SHA256SUMS |
| Signature source | https://releases.mozilla.org/pub/firefox/releases/153.5.1esr/SHA256SUMS.asc |
| Mozilla signing key | https://releases.mozilla.org/pub/firefox/releases/153.5.1esr/KEY |
| Download URL | https://releases.mozilla.org/pub/firefox/releases/153.5.1esr/linux-x86_64/en-US/firefox-153.5.1esr.tar.xz |

---

## Part A: Fast path (Phase 0 — prove levels before compiling)

### Prerequisites (Arch Linux)

The following tools must be present. **Do not install anything without asking the owner.**

```
git python3 curl gpg xz tar
```

Check:
```bash
git --version && python3 --version && curl --version | head -1 && gpg --version | head -1 && xz --version | head -1
```

### A1. Download and verify the tarball

> **Requires owner approval before running.**

```bash
cd /home/god/Ageis

# Download tarball, checksum file, and signature
curl -L -O https://releases.mozilla.org/pub/firefox/releases/153.5.1esr/linux-x86_64/en-US/firefox-153.5.1esr.tar.xz
curl -L -O https://releases.mozilla.org/pub/firefox/releases/153.5.1esr/SHA256SUMS
curl -L -O https://releases.mozilla.org/pub/firefox/releases/153.5.1esr/SHA256SUMS.asc

# Verify SHA-256
grep "linux-x86_64/en-US/firefox-153.5.1esr.tar.xz" SHA256SUMS | sha256sum -c

# Verify GPG signature (import Mozilla's release key first if not present)
# Key fingerprint: verify against https://www.mozilla.org/en-US/security/#
curl -L https://releases.mozilla.org/pub/firefox/releases/153.5.1esr/KEY | gpg --import
gpg --verify SHA256SUMS.asc SHA256SUMS
```

Expected sha256sum output: `firefox-153.5.1esr.tar.xz: OK`

### A2. Extract

```bash
cd /home/god/Ageis
tar -xJf firefox-153.5.1esr.tar.xz
# Creates: firefox-esr/  (the directory name from the tarball; rename if needed)
# VERIFY: the tarball may unpack to 'firefox/' — check and rename to 'firefox-esr/' if so.
```

The extracted directory is in `.gitignore` (large binary, not in repo).

### A3. Apply policies and autoconfig

```bash
# Copy policy file (overwrite the directory if it does not exist)
mkdir -p firefox-esr/distribution
cp config/policy/policies.json firefox-esr/distribution/policies.json

# Copy autoconfig files
cp config/autoconfig/autoconfig.js firefox-esr/defaults/pref/autoconfig.js
cp config/autoconfig/aegis.cfg firefox-esr/aegis.cfg
```

> **VERIFY-S-021:** The autoconfig mechanism (`autoconfig.js` + `.cfg` file) must be
> confirmed to work in ESR 153. The file names and locations may differ from release
> Firefox. Check Mozilla's enterprise documentation for ESR 153.

### A4. Create a test profile and launch

```bash
mkdir -p profiles

# Launch with isolated profile; do NOT use --no-remote if you want to inspect profiles
# from outside. Use --no-remote to prevent interfering with system Firefox.
firefox-esr/firefox -profile profiles/aegis-fastpath --no-remote
```

### A5. Verify policies are applied

In the running Aegis ESR instance, navigate to `about:policies` to confirm that
`policies.json` is being read. Navigate to `about:config` to spot-check prefs.

### A6. Run the test suite

```bash
cd /home/god/Ageis/prototypes
python3 -m unittest test_aegis
```

Expected: `Ran 27 tests in X.XXXs — OK`

---

## Part B: Source build (DEFERRED — do not start without explicit owner approval)

Compiling Firefox requires:
- ~50–60 GB of disk (source + build artifacts)
- 16 GB RAM recommended (20-core build machine available)
- Several hours of build time

Steps will be documented here when approved:

1. Obtain official Firefox 153 ESR source (canonical repo and ESR tag — VERIFY against
   Mozilla's current source documentation; repository paths change between releases).
2. Run `./mach bootstrap` (choose desktop browser option).
3. Create `build/mozconfig-baseline` for an unmodified build.
4. Build (`./mach build`) and run (`./mach run`).
5. Record exact versions, commands, build time, and binary hash in this file.
6. Only then apply branding, one patch at a time, each with a test.

**Do not begin Part B without owner approval.**

---

## Reproducing this setup on a clean machine

1. Clone the repo.
2. Read this file and `docs/VERIFY.md`.
3. Follow Part A steps A1–A6 above.
4. The tarball is not in the repo; download and verify it with the SHA-256 above.
5. The `profiles/` directory is in `.gitignore`; a fresh profile is created on first launch.
