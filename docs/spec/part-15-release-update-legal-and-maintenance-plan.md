# Part 15. Release, update, legal and maintenance plan

- **Upstream tracking:** follow Firefox ESR security releases; rebase the patch queue each time; automated test run before release.
- **Builds:** reproducible, pinned toolchain, dependency inventory (SBOM), signed artifacts, published hashes.
- **Updates:** authenticated and integrity-checked; never silently downgrade a Tor Cell's route.
- **Vulnerability handling:** `SECURITY.md` with a reporting address, response targets, and coordinated disclosure.
- **Telemetry:** none by default; any crash reporting is opt-in and disclosed.
- **Rule and list updates:** Link Guard rules, brand maps, and tracker lists are versioned and signed; the Public Suffix List is refreshed regularly.
- **Licensing and trademarks (get proper legal advice before distribution):** Firefox source is under the Mozilla Public License; redistributing a modified build generally requires removing Mozilla's branding and trademarks and following Mozilla's trademark and distribution policies; bundled components (for example a content blocker) have their own licenses; Tor, Mullvad, and other marks belong to their owners. Do not imply Mozilla or Tor Project endorsement.
- **Documentation:** privacy defaults, retention, data flows (especially P3 modules), and user-facing limits.
