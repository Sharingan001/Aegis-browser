#!/usr/bin/env python3
"""
Unit tests for Aegis UI & Cell Indicator (Phase 1a).
Verifies:
1. Branding theme manifest validity.
2. Cell indicator extension manifest validity, minimal permissions (no tabs, no storage), and justification.
3. Abstract data model integrity (cell -> {N, S, I}).
4. Honest language lint (NO prohibited marketing buzzwords like 'safe', 'secure', 'anonymous').
5. Visible placeholder notice required (explicitly marked NOT ENFORCED, NOT VERIFIED).
6. Flag unverified protection claims (no claims of active routing or active enforcement).
7. Architectural compliance with D-008 (no per-tab pref mutation).
"""

import json
import os
import re
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

PROHIBITED_TERMS = [
    r"\bsafe\b",
    r"\bsecure\b",
    r"\bbulletproof\b",
    r"\bunhackable\b",
    r"\binvulnerable\b",
    r"\banonymous\b",
    r"\bfoolproof\b"
]

UNVERIFIED_PROTECTION_TERMS = [
    r"\broute active\b",
    r"\brouting active\b",
    r"\bsurface profile active\b",
    r"\bidentity posture active\b",
    r"\bonion circuit routing with\b",
    r"\bephemeral state\b(?!\s*\(target\s*spec\))"  # must be qualified as target spec or placeholder
]

class TestBrandingAndTheme(unittest.TestCase):
    def test_theme_manifest_validity(self):
        theme_manifest_path = os.path.join(REPO_ROOT, "branding", "theme", "manifest.json")
        self.assertTrue(os.path.isfile(theme_manifest_path), "Theme manifest.json missing")
        with open(theme_manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data.get("manifest_version"), 2)
        self.assertIn("theme", data)
        self.assertIn("colors", data["theme"])
        colors = data["theme"]["colors"]
        self.assertIn("frame", colors)
        self.assertIn("toolbar", colors)
        self.assertIn("tab_line", colors)

    def test_branding_palette_schema(self):
        palette_path = os.path.join(REPO_ROOT, "branding", "palette.json")
        self.assertTrue(os.path.isfile(palette_path), "branding/palette.json missing")
        with open(palette_path, "r", encoding="utf-8") as f:
            palette = json.load(f)
        self.assertIn("theme", palette)
        self.assertIn("axes", palette)
        self.assertIn("network", palette["axes"])
        self.assertIn("surface", palette["axes"])
        self.assertIn("identity", palette["axes"])

    def test_branding_icons_exist(self):
        for size in [16, 32, 48, 64, 128, 256]:
            icon_path = os.path.join(REPO_ROOT, "branding", "icons", f"icon-{size}.png")
            self.assertTrue(os.path.isfile(icon_path), f"icon-{size}.png missing")
            self.assertGreater(os.path.getsize(icon_path), 0)


class TestCellIndicatorExtension(unittest.TestCase):
    def setUp(self):
        self.ext_dir = os.path.join(REPO_ROOT, "ui", "cell-indicator")

    def test_extension_manifest(self):
        manifest_path = os.path.join(self.ext_dir, "manifest.json")
        self.assertTrue(os.path.isfile(manifest_path), "manifest.json missing")
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        self.assertEqual(manifest.get("name"), "Aegis Cell Indicator")
        self.assertIn("browser_action", manifest)
        self.assertIn("background", manifest)

    def test_permissions_removed_and_justified(self):
        """Verify 'tabs' and 'storage' permissions are removed and justification is documented."""
        manifest_path = os.path.join(self.ext_dir, "manifest.json")
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        perms = manifest.get("permissions", [])
        self.assertNotIn("tabs", perms, "'tabs' permission is unused and must be omitted")
        self.assertNotIn("storage", perms, "'storage' permission is unused and must be omitted")
        self.assertEqual(len(perms), 0, "Cell Indicator should operate with 0 elevated permissions")

        # Justification must be present in notes/description
        notes = manifest.get("notes", "")
        self.assertTrue(
            "justification" in notes.lower() or "permission" in notes.lower(),
            "Manifest must document permission justification in 'notes'"
        )

    def test_visible_placeholder_notice_required(self):
        """Verify popup has a visible placeholder notice stating not enforced and not verified."""
        popup_html_path = os.path.join(self.ext_dir, "popup", "popup.html")
        self.assertTrue(os.path.isfile(popup_html_path), "popup.html missing")
        with open(popup_html_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("placeholder-notice", content, "popup.html must contain a visible .placeholder-notice banner")
        self.assertIn("PLACEHOLDER", content)
        self.assertIn("NOT ENFORCED", content)
        self.assertIn("NOT VERIFIED", content)

    def test_abstract_data_model_in_store(self):
        store_path = os.path.join(self.ext_dir, "data", "cell_store.js")
        self.assertTrue(os.path.isfile(store_path), "cell_store.js missing")
        with open(store_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check required axes
        self.assertIn("N0", content)
        self.assertIn("N1", content)
        self.assertIn("N2", content)
        self.assertIn("S1", content)
        self.assertIn("S2", content)
        self.assertIn("S3", content)
        self.assertIn("S4", content)
        self.assertIn("I1", content)
        self.assertIn("I2", content)
        self.assertIn("I4", content)

        # Check abstract mapping pattern
        self.assertIn("route:", content)
        self.assertIn("surface:", content)
        self.assertIn("identity:", content)

    def test_no_per_tab_pref_mutation_d008(self):
        """Verify the extension does NOT attempt to mutate instance preferences (D-008)."""
        js_files = [
            os.path.join(self.ext_dir, "background.js"),
            os.path.join(self.ext_dir, "popup", "popup.js"),
            os.path.join(self.ext_dir, "data", "cell_store.js"),
        ]
        forbidden_apis = [
            "browser.preferences",
            "chrome.preferences",
            "Services.prefs",
            "lockPref",
            "defaultPref"
        ]
        for js_file in js_files:
            with open(js_file, "r", encoding="utf-8") as f:
                content = f.read()
            for api in forbidden_apis:
                self.assertNotIn(api, content, f"Forbidden pref mutation call '{api}' found in {js_file}")

    def test_honest_language_lint(self):
        """Verify UI copy contains NO prohibited security marketing claims."""
        files_to_check = [
            os.path.join(self.ext_dir, "manifest.json"),
            os.path.join(self.ext_dir, "popup", "popup.html"),
            os.path.join(self.ext_dir, "popup", "popup.js"),
            os.path.join(self.ext_dir, "data", "cell_store.js"),
        ]
        for path in files_to_check:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            for line_no, line in enumerate(lines, 1):
                # Ignore code identifiers like 'safe' in comments talking about guidelines
                if "prohibited" in line.lower() or "guidelines" in line.lower():
                    continue
                for pattern in PROHIBITED_TERMS:
                    match = re.search(pattern, line, re.IGNORECASE)
                    self.assertIsNone(
                        match,
                        f"Prohibited security claim '{match.group(0) if match else ''}' found in {path}:{line_no}: {line.strip()}"
                    )

    def test_unverified_protection_claims_lint(self):
        """Verify UI copy does NOT make unverified active protection claims."""
        files_to_check = [
            os.path.join(self.ext_dir, "popup", "popup.html"),
            os.path.join(self.ext_dir, "popup", "popup.js"),
            os.path.join(self.ext_dir, "data", "cell_store.js"),
        ]
        for path in files_to_check:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            for line_no, line in enumerate(lines, 1):
                for pattern in UNVERIFIED_PROTECTION_TERMS:
                    match = re.search(pattern, line, re.IGNORECASE)
                    self.assertIsNone(
                        match,
                        f"Unverified protection claim '{match.group(0) if match else ''}' found in {path}:{line_no}: {line.strip()}"
                    )


if __name__ == "__main__":
    unittest.main()
