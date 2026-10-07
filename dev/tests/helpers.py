"""Shared fixtures: a throwaway project, the real plugin scripts, and a fake `weni`."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "plugin" / "scripts"

# The fake CLI answers from environment variables so each test scripts its behavior.
FAKE_WENI = """#!{python}
import os, sys, time
args = sys.argv[1:]
with open(os.environ["FAKE_WENI_LOG"], "a") as log:
    log.write(" ".join(args) + "\\n")
key = {{"project": "PROJECT", "run": "RUN", "eval": "EVAL"}}.get(args[0] if args else "", "OTHER")
if args[:2] == ["project", "list"]:
    key = "LIST"
if args[:2] == ["project", "push"]:
    key = "PUSH"
time.sleep(float(os.environ.get("FAKE_" + key + "_SLEEP", "0")))
sys.stdout.write(os.environ.get("FAKE_" + key + "_OUT", ""))
sys.exit(int(os.environ.get("FAKE_" + key + "_RC", "0")))
"""


class HarnessProject(unittest.TestCase):
    """Base test case: an empty tmp project with a fake .venv/bin/weni; scripts run from the plugin."""

    logged_in = True
    install_weni = True

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / "project"
        self.root.mkdir()
        self.home = self.tmp / "home"
        self.home.mkdir()
        if self.logged_in:
            (self.home / ".weni_cli").write_text("{}")
        if self.install_weni:
            weni = self.root / ".venv" / "bin" / "weni"
            weni.parent.mkdir(parents=True)
            weni.write_text(FAKE_WENI.format(python=sys.executable))
            weni.chmod(0o755)
        self.env = {
            **os.environ,
            "HOME": str(self.home),
            "CLAUDE_PROJECT_DIR": str(self.root),
            "FAKE_WENI_LOG": str(self.tmp / "weni.log"),
            "FAKE_PROJECT_OUT": "Current project: 8f2a401c (Demo)",
        }

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def script(self, name, *args, **fake):
        """Run a harness script inside the temp project; fake=FAKE_* overrides."""
        env = {**self.env, **{f"FAKE_{key.upper()}": str(value) for key, value in fake.items()}}
        return subprocess.run([sys.executable, str(SCRIPTS / name), *args],
                              cwd=str(self.root), env=env, capture_output=True, text=True)

    def add_agent(self, slug="demo", definition="agents: {}\n"):
        folder = self.root / "agents" / slug
        folder.mkdir(parents=True)
        (folder / "agent_definition.yaml").write_text(definition)
        return folder

    def new_run(self, slug="demo"):
        result = self.script("init_run.py", "demo feature", "--target", slug)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return Path(result.stdout.strip().splitlines()[-1])

    @staticmethod
    def state(run_dir):
        return json.loads((Path(run_dir) / "STATE.json").read_text())
