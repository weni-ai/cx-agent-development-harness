"""dev/sandbox.py: create, list, and clean only marked sandboxes."""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import REPO


class Sandbox(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.env = {**os.environ, "HARNESS_SANDBOX_ROOT": str(self.root)}

    def tearDown(self):
        shutil.rmtree(self.root)

    def run_sandbox(self, *args):
        return subprocess.run([sys.executable, str(REPO / "dev" / "sandbox.py"), *args],
                              env=self.env, capture_output=True, text=True)

    def test_new_list_clean_roundtrip(self):
        for _ in range(4):  # above the warning threshold
            result = self.run_sandbox("new", "weather-simple")
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--plugin-dir", result.stdout)
        self.assertIn("sandboxes exist", result.stdout)
        unmarked = self.root / "keep-me"
        unmarked.mkdir()
        self.assertEqual(self.run_sandbox("list").stdout.count("weather-simple"), 4)
        self.assertIn("4 sandbox(es) removed", self.run_sandbox("clean").stdout)
        self.assertTrue(unmarked.exists())
