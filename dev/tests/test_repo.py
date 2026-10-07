"""Repo-level invariants: edition sync and `./harness init`."""

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import REPO


class EditionSync(unittest.TestCase):
    def test_cursor_edition_is_current(self):
        result = subprocess.run([sys.executable, str(REPO / ".harness" / "scripts" / "sync_editions.py"), "--check"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout)


class HarnessInit(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copy(REPO / "harness", self.tmp / "harness")
        shutil.copytree(REPO / "dev", self.tmp / "dev", ignore=shutil.ignore_patterns("__pycache__"))
        (self.tmp / ".gitignore").write_text("agents/\n")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def init(self):
        return subprocess.run([sys.executable, "harness", "init", "--yes"], cwd=str(self.tmp),
                              capture_output=True, text=True)

    def test_refuses_in_maintainer_checkout(self):
        (self.tmp / "dev" / ".maintainer").touch()
        self.assertEqual(self.init().returncode, 2)
        self.assertTrue((self.tmp / "dev").exists())

    def test_strips_dev_and_installs_project_gitignore(self):
        (self.tmp / "dev" / ".maintainer").unlink(missing_ok=True)
        self.assertEqual(self.init().returncode, 0)
        self.assertFalse((self.tmp / "dev").exists())
        self.assertIn(".venv/", (self.tmp / ".gitignore").read_text())
        self.assertNotIn("agents/", (self.tmp / ".gitignore").read_text())
        self.assertIn("Already initialized", self.init().stdout)
