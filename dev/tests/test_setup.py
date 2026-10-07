"""bootstrap_env.py project preparation (without touching the network)."""

from helpers import HarnessProject

import sys
sys.path.insert(0, str(__import__("helpers").SCRIPTS))


class GitignoreSetup(HarnessProject):
    def test_appends_missing_entries_once(self):
        import importlib
        import os
        os.environ["CLAUDE_PROJECT_DIR"] = str(self.root)
        (self.root / ".gitignore").write_text("node_modules/\n.venv/\n")
        bootstrap = importlib.import_module("bootstrap_env")
        bootstrap.ensure_gitignore()
        bootstrap.ensure_gitignore()
        lines = (self.root / ".gitignore").read_text().splitlines()
        self.assertEqual(lines.count(".venv/"), 1)
        self.assertIn(".harness/", lines)
        self.assertIn("node_modules/", lines)
