"""discover_agents.py, adopt_agent.py, the session-start notice, and the edit-mode gate."""

import json
import unittest

from helpers import HarnessProject

try:
    import yaml  # noqa: F401
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

DEFINITION = """agents:
  {key}:
    name: Demo
    tools:
      - lookup:
          source:
            path: {tool_path}
            entrypoint: main.Lookup
"""


class Discovery(HarnessProject):
    def make(self, folder, key="order_bot", tool_path="tools/lookup"):
        base = self.root / folder
        (base / "tools" / "lookup").mkdir(parents=True, exist_ok=True)
        (base / "agent_definition.yaml").write_text(DEFINITION.format(key=key, tool_path=tool_path))
        return base

    def discover(self):
        result = self.script("discover_agents.py", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        return {item["path"]: item for item in json.loads(result.stdout)}

    def test_finds_in_place_loose_and_root_agents(self):
        self.make("agents/demo")
        self.make("Weather_Bot")
        self.make("clients/acme/order")
        self.make(".", key="root_agent")
        (self.root / ".venv" / "lib" / "x").mkdir(parents=True)
        (self.root / ".venv" / "lib" / "x" / "agent_definition.yaml").write_text("agents: {}\n")
        found = self.discover()
        self.assertEqual(found["agents/demo"]["status"], "IN_PLACE")
        self.assertEqual(found["Weather_Bot"]["slug"], "weather-bot")
        self.assertEqual(found["clients/acme/order"]["status"], "LOOSE")
        self.assertEqual(found["."]["status"], "LOOSE")
        self.assertNotIn(".venv/lib/x", found)
        self.assertIn("LOOSE_AGENTS_FOUND 3", self.script("discover_agents.py").stdout)

    @unittest.skipUnless(HAS_YAML, "needs PyYAML")
    def test_root_slug_comes_from_the_agent_key(self):
        self.make(".", key="root_agent")
        self.assertEqual(self.discover()["."]["slug"], "root-agent")

    @unittest.skipUnless(HAS_YAML, "needs PyYAML")
    def test_invalid_definitions_are_reported(self):
        self.make("outside", tool_path="../shared")
        (self.root / "empty").mkdir()
        (self.root / "empty" / "agent_definition.yaml").write_text("agents: {}\n")
        found = self.discover()
        self.assertEqual(found["outside"]["status"], "INVALID")
        self.assertIn("outside the agent folder", found["outside"]["reason"])
        self.assertEqual(found["empty"]["status"], "INVALID")

    def test_dry_run_moves_nothing(self):
        self.make("weather")
        result = self.script("adopt_agent.py", "--all", "--dry-run")
        self.assertIn("ADOPT     weather -> agents/weather", result.stdout)
        self.assertTrue((self.root / "weather").exists())
        self.assertFalse((self.root / "agents").exists())

    def test_adopt_all_moves_folders_with_extra_files(self):
        self.make("weather")
        (self.root / "weather" / "notes.txt").write_text("keep me")
        self.make("orders")
        result = self.script("adopt_agent.py", "--all")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ADOPT_DONE", result.stdout)
        self.assertTrue((self.root / "agents" / "weather" / "notes.txt").exists())
        self.assertTrue((self.root / "agents" / "orders" / "tools" / "lookup").is_dir())
        self.assertIn("AGENTS_IN_PLACE", self.script("discover_agents.py").stdout)

    @unittest.skipUnless(HAS_YAML, "needs PyYAML (root moves come from the tool paths)")
    def test_root_agent_moves_only_its_own_files(self):
        self.make(".", key="root_agent")
        (self.root / "README.md").write_text("project readme")
        result = self.script("adopt_agent.py", "--all")
        self.assertIn("ADOPTED   . -> agents/root-agent", result.stdout)
        target = self.root / "agents" / "root-agent"
        self.assertTrue((target / "agent_definition.yaml").exists())
        self.assertTrue((target / "tools" / "lookup").is_dir())
        self.assertTrue((self.root / "README.md").exists())
        self.assertTrue((self.root / ".venv").exists())

    def test_never_overwrites_an_existing_agent(self):
        self.make("agents/weather")
        self.make("legacy/weather")
        result = self.script("adopt_agent.py", "--all")
        self.assertEqual(result.returncode, 1)
        self.assertIn("agents/weather already exists", result.stdout)
        self.assertTrue((self.root / "legacy" / "weather").exists())
        result = self.script("adopt_agent.py", "--from", "legacy/weather", "--slug", "weather-legacy")
        self.assertIn("ADOPT_DONE", result.stdout)
        self.assertTrue((self.root / "agents" / "weather-legacy" / "agent_definition.yaml").exists())

    def test_session_start_mentions_loose_agents(self):
        self.make("weather")
        result = self.script("check_ready.py", "--hook")
        self.assertIn("1 agent(s) outside agents/: weather", result.stdout)

    def test_session_start_is_silent_outside_weni_projects(self):
        self.assertEqual(self.script("check_ready.py", "--hook").stdout.strip(), "")


class EditModeGate(HarnessProject):
    def test_edit_requires_the_agent_in_agents(self):
        result = self.script("init_run.py", "change", "--target", "ghost", "--mode", "edit")
        self.assertEqual(result.returncode, 1)
        self.assertIn("AGENT_NOT_FOUND", result.stdout)
        self.assertFalse((self.root / ".harness" / "runs").exists())

    def test_edit_starts_when_the_agent_is_in_place(self):
        self.add_agent("demo")
        result = self.script("init_run.py", "change", "--target", "demo", "--mode", "edit")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
