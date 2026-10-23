# Aegis Agent Kickoff Pack
**For:** giving the Aegis master blueprint to a coding agent (written for Claude Code with Claude Sonnet 4.6; the same pack works in other agent tools)

The master blueprint is about 90 KB. Do not paste all of it into one chat. Put it in the repo, split it by Part, and let the agent read only what each phase needs. That keeps the model focused and cuts mistakes.

---

## Step 1. Set up the project folder

```bash
mkdir aegis-browser && cd aegis-browser
git init
mkdir -p docs/spec prototypes
cp /path/to/Aegis_Browser_MASTER_Blueprint_A-to-Z.md docs/MASTER.md
cp /path/to/aegis_psl.py /path/to/linkguard_prototype.py /path/to/aegis_modules.py /path/to/test_aegis.py prototypes/
python3 /path/to/split_spec.py docs/MASTER.md docs/spec     # creates docs/spec/part-01 ... part-20 + INDEX.md
```

Then create `CLAUDE.md` in the repo root (Step 2). Claude Code reads `CLAUDE.md` at the start of each session, so your rules survive between sessions.

## Step 2. Put this in `CLAUDE.md`

~~~~markdown
# Aegis Browser: project rules (read first, every session)

Project: "Aegis Browser", a desktop browser on Gecko (Firefox ESR base) with multi-level
security, isolated Cells, phishing protection, and modules.
Spec: docs/spec/INDEX.md lists one file per Part of the master blueprint. Read only the
Parts the current phase needs (see docs/PHASE_READING.md). Full text: docs/MASTER.md.
Prototype code and tests: prototypes/ (run: python3 -m unittest test_aegis).

## Hard constraints
1. No Chromium, Blink, Electron, CEF, or Chromium WebView.
2. No custom browser engine, TLS, cryptography, or password vault.
3. Order of preference: enterprise policies/locked prefs -> built-in WebExtensions ->
   chrome UI -> engine patches (numbered in upstream/patches/, each with reason + test).
4. Web content is untrusted; never expose privileged APIs to it. Services consume
   structured events only.
5. Fail closed. Never silently fall back (especially in Tor mode).
6. Every control needs an enforcement test that runs against the running browser.
7. Local-first, no telemetry. Off-device data is opt-in and disclosed.
8. Honest claims: never say "anonymous" or "safe". HTTPS is not safety; no warning is not safe.
9. Automatic protection changes may only escalate; only the user may lower protection.
10. Warnings and trust indicators live in Aegis chrome, never in page space.
11. No exploit, attack, evasion, or malware functionality. Lab modules observe, scope, document.
12. Never browse live phishing/malicious sites to test. Use offline datasets, local mock pages.
13. Verify every Firefox pref/policy/API name against the pinned ESR version; mark VERIFY.

## Working rules
- One phase per session. Start by stating the goal, files to change, open questions.
- Small commits. Run tests after each change and show exact results. Never claim a test
  passed unless you ran it. Say what you did NOT test.
- Maintain docs/DECISIONS.md (what/why/alternatives/date) and docs/VERIFY.md (unverified items).
- Ask me before: large downloads, long builds, installing system packages, deleting files,
  or any decision the spec does not settle.
- If the spec is wrong or ambiguous, say so plainly and propose a fix.
- End every step with: what you did, files changed, tests + results, not tested, decisions
  needed, next step.
~~~~

## Step 3. Create `docs/PHASE_READING.md`

Copy the table from Section "Which spec Parts to read per phase" below into this file.

## Step 4. Launch the agent

```bash
cd aegis-browser
claude            # start Claude Code in the repo; choose Sonnet 4.6 with /model if needed
```

Keep the default permission mode (it asks before running commands and editing files). **Do not** use any "skip all permission prompts" option for this project: you are about to let an agent run builds and install tooling.

---

## The prompt to paste first (kickoff)

~~~~text
You are the lead engineer on "Aegis Browser". Before doing anything:

1. Read CLAUDE.md and docs/spec/INDEX.md.
2. Read these spec parts fully: part-01, part-02, part-04, part-10, part-11, part-12, part-13,
   part-16, part-17, and part-18 (the building prompt, which defines the phases and the
   output format).
3. Look at prototypes/ and run: cd prototypes && python3 -m unittest test_aegis
   and tell me the exact result.

Then reply with ONLY:
(a) your understanding of the project in 10 lines;
(b) the questions you need answered before Phase 0 (my OS and distro, CPU/RAM/free disk,
    whether to do the fast path first, which Firefox ESR version to pin, and anything in the
    spec that is unclear or contradictory);
(c) your plan for Phase 0 as a numbered list of steps with the files you will create.

Do not write code, install anything, or start a build until I answer.
~~~~

## Answer the agent's questions with something like

~~~~text
OS: Ubuntu 24.04 (replace with yours). CPU/RAM/disk: <cores>, <GB RAM>, <GB free>.
Do the fast path first (policies + autoconfig on a stock Firefox ESR) and only compile
Firefox after the fast path works. Pin the latest ESR that Mozilla's docs list as current,
and tell me which version you chose and why. Proceed with Phase 0. Do not start a source
build without asking me first, because it is slow and large.
~~~~

---

## Prompt for each later session (template)

Start a **fresh session** for each phase (use the clear/new-session command so the context is clean), then paste:

~~~~text
Continue Aegis, PHASE <N>: <phase name>.

Read CLAUDE.md, docs/DECISIONS.md, docs/VERIFY.md, and the spec parts listed for this phase
in docs/PHASE_READING.md. Summarize the state of the repo in 8 lines (what exists, what tests
pass, what is open). Then give me your plan for this phase: files to create/change, tests you
will write first, open questions. Wait for my OK before changing code.

When I approve: work in small commits, write tests first where possible, run them, and report
using the output format in CLAUDE.md. Stop at the end of the phase and report.
~~~~

## Review prompt (between phases, ideally in a new session)

~~~~text
Review the repo against the Aegis spec for PHASE <N>. Read CLAUDE.md and the phase's spec parts.
List: requirements now met (with the test that proves each, and run the tests now); requirements
partly met or untested; any claim in code, UI text, or docs stronger than what is tested; new
attack surface introduced and its mitigation; VERIFY items resolved and still open.
Be blunt. Do not mark anything done unless you ran its test.
~~~~

---

## Which spec Parts to read per phase (`docs/PHASE_READING.md`)

| Phase | Goal | Spec parts to read (in `docs/spec/`) |
|---|---|---|
| 0 | Baseline build, fast path, test harness, port prototypes | 02, 10, 12, 16, 17 |
| 1 | Branding and UI shell | 01, 04, 09, 15 |
| 2 | Surface and Identity axes, presets, Tier 1 modules | 05, 08 (8.1 to 8.3), 11 |
| 3 | Network axis, Tor, route contracts, leak matrix | 05 (5.4, 5.5), 07 (7.4), 12 |
| 4 | Cells, workspaces, Scope Guard | 06, 08 (M1, M16), 05 (5.5) |
| 5 | Flight Recorder, verification, Link Guard stages 1 to 3 | 07 (7.5, 7.6, 7.7), 09 (9.4), 12, 14 |
| 6 | Trust Ledger, tripwires, Link Guard content stages, Anchored Cells | 07 (7.1, 7.2, 7.7), 06 (6.2), 14 |
| 7 | Detonation Cell | 07 (7.3), 05 (S4 row), 14 |
| 8 | Tier 2 and 3 modules | 08 |
| 9 | Hardening and release | 15, 12, 11 |

Always also read: `CLAUDE.md`, `docs/DECISIONS.md`, `docs/VERIFY.md`.

---

## Tips for working with Sonnet 4.6 on a project this size

1. **One phase per session.** Long sessions drift. Use the clear/new-session command between phases and rely on `CLAUDE.md`, `DECISIONS.md`, and `VERIFY.md` as memory.
2. **Make it plan first.** Ask for a plan and wait for your OK before it edits code. If your tool has a plan mode, use it for Phases 2, 3, and 6.
3. **Force evidence.** Always ask for the exact test output. If it says "this should work", reply: "Run it and show me the output."
4. **Watch for confident guesses about Firefox internals.** Preference names, policy keys, and APIs change between versions. Insist on `docs/VERIFY.md` entries and have the agent check the pinned version's documentation or source.
5. **Keep builds under your control.** Compiling Firefox is slow and large. Tell it to ask before starting, and run long builds yourself in a separate terminal if you prefer.
6. **Commit often and review diffs.** Use git branches per phase (`phase-2-axes`) and read each diff before merging, especially anything touching network policy, Cells, or Link Guard rules.
7. **Split big spikes.** For S4 script control and I3 seeded noise, ask for a short comparison document first (options, risks, recommendation), then decide.
8. **Run an independent review between phases** in a new session with the review prompt. A fresh context catches things the building session normalizes.
9. **Do not let it expand scope.** If it proposes extra features, answer: "Not in this phase. Add it to docs/BACKLOG.md."
10. **Keep security honesty rules visible.** If any UI text or doc says "secure", "safe", or "anonymous", tell the agent to rewrite it to match what is actually tested.

## Red flags: stop and correct the agent if it

- Suggests Chromium, Electron, or a Chromium-based component "just for convenience".
- Writes its own crypto, TLS handling, or password storage.
- Marks a task done without showing test output.
- Disables a test or loosens a rule to make a test pass without telling you why.
- Browses or fetches live phishing pages to "test" Link Guard.
- Adds telemetry, analytics, or any off-device call that is not opt-in and disclosed.
- Puts warnings or trust indicators inside page-controlled UI.
- Adds exploit or evasion functionality to a Lab module.

## Quick start checklist

- [ ] Repo created, `git init` done
- [ ] `docs/MASTER.md`, `docs/spec/` (from `split_spec.py`), `prototypes/` in place
- [ ] `CLAUDE.md` and `docs/PHASE_READING.md` created
- [ ] Claude Code started in the repo, Sonnet 4.6 selected, default permissions on
- [ ] Kickoff prompt pasted; questions answered
- [ ] Phase 0 plan approved
