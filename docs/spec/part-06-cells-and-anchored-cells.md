# Part 6. Cells and Anchored Cells

## 6.1 Cells (per-purpose compartments)

A **Cell** is the unit that owns: its network route, S level, I policy, cookie jar and storage, permissions, downloads folder, event log scope, and a **color and name** shown in the tab strip and address bar.

- A Cell can be **persistent** (a "Work" Cell), **session** (cleared on close), or **ephemeral** (RAM-only, destroyed on close).
- Cells never share cookies, storage, permission grants, or identity seeds.
- Tabs opened from a link inherit the Cell by default. Cross-Cell navigation requires an explicit action and a clear indicator.
- Per-Cell routing may need Firefox internals changes beyond a UI layer. Prototype with the container and proxy-selection mechanisms first, and treat full per-Cell route isolation (separate Tor circuits per Cell) as a research item to test.

## 6.2 Anchored Cells (strong anti-phishing for sensitive accounts)

A Cell can be **anchored** to a set of registrable domains (for example a "Banking" Cell).

- Saved credentials fill **only** in the anchored Cell and only on anchored domains.
- Navigating to a non-anchored domain from that Cell opens a different Cell and says why.
- A password field on a non-anchored domain inside an anchored Cell is a hard warning.
