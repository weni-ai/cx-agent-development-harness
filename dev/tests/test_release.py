"""Versioning invariants: users only get updates when plugin.json's version changes."""

import json
import re
import subprocess
import sys
import unittest

from helpers import REPO

sys.path.insert(0, str(REPO / "dev"))
import release  # noqa: E402

CHANGELOG = (REPO / "plugin" / "CHANGELOG.md").read_text(encoding="utf-8")
MANIFEST = json.loads((REPO / "plugin" / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))


def git(*args):
    return subprocess.run(["git", *args], cwd=str(REPO), capture_output=True, text=True)


class Versioning(unittest.TestCase):
    def test_manifest_matches_latest_changelog_release(self):
        self.assertEqual(MANIFEST["version"], release.released_version(CHANGELOG))

    def test_marketplace_does_not_pin_a_second_version(self):
        marketplace = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
        self.assertTrue(all("version" not in entry for entry in marketplace["plugins"]))

    def test_plugin_changes_since_last_release_are_in_the_changelog(self):
        tag = f"v{MANIFEST['version']}"
        if git("rev-parse", "-q", "--verify", f"refs/tags/{tag}").returncode != 0:
            self.skipTest(f"tag {tag} not created yet")
        changed = [path for path in git("diff", "--name-only", tag, "--", "plugin").stdout.split()
                   if not path.endswith("CHANGELOG.md")]
        if changed:
            self.assertTrue(release.unreleased_entries(CHANGELOG),
                            "plugin/ changed since the last release but `## Unreleased` is empty: "
                            + ", ".join(changed))


class ReleaseMath(unittest.TestCase):
    def test_bump_kind_follows_entry_sections(self):
        self.assertEqual(release.inferred_kind("### Breaking\n- x"), "major")
        self.assertEqual(release.inferred_kind("### New\n- x\n### Fixed\n- y"), "minor")
        self.assertEqual(release.inferred_kind("### Fixed\n- y"), "patch")
        self.assertEqual(release.bump("2.3.4", "minor"), "2.4.0")

    def test_changelog_entries_use_known_sections(self):
        for heading in re.findall(r"^### (.+)$", CHANGELOG, re.MULTILINE):
            self.assertIn(heading, ("Breaking", "New", "Changed", "Fixed"))
