"""Manager assignment: preflight, record_assignment, EVAL_NOT_ASSIGNED, platform session, Chrome guard hook."""

import json
import subprocess
import sys
import unittest
from datetime import datetime, timedelta, timezone

from helpers import REPO, HarnessProject

try:
    import yaml  # noqa: F401
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

GUARD = REPO / "plugin" / "hooks" / "chrome_guard.py"
UUID = "14fbead6-e54e-43ba-ba49-53719c2b55ab"
MY_AGENTS = f"https://dash.weni.ai/projects/{UUID}/ai-agents/agents"
NEEDS_YAML = "needs PyYAML (create the repo .venv: python3 -m venv .venv && .venv/bin/pip install pyyaml)"


def definition(credentials="", constants=""):
    return ("agents:\n  demo_agent:\n    name: \"Demo Agent\"\n"
            + (f"    credentials:\n{credentials}" if credentials else "")
            + (f"    constants:\n{constants}" if constants else ""))


CONSTANT_WITH_DEFAULT = "      API_URL:\n        label: \"API URL\"\n        type: \"text\"\n        default: \"https://x\"\n"


@unittest.skipUnless(HAS_YAML, NEEDS_YAML)
class Preflight(HarnessProject):
    def preflight(self, text):
        self.add_agent(definition=text)
        return self.script("platform_preflight.py", "--target", "demo").stdout

    def test_constants_with_default_are_auto(self):
        self.assertEqual(self.preflight(definition(constants=CONSTANT_WITH_DEFAULT)).strip(), "ASSIGN_AUTO")

    def test_credential_without_is_confidential_is_manual(self):
        out = self.preflight(definition(credentials="      api_key:\n        label: \"API Key\"\n"))
        self.assertIn("ASSIGN_MANUAL", out)
        self.assertIn("- API Key (confidential credential)", out)

    def test_non_confidential_credential_with_default_is_auto(self):
        out = self.preflight(definition(
            credentials="      base_url:\n        label: \"Base URL\"\n        is_confidential: false\n"
                        "        default: \"https://x\"\n"))
        self.assertEqual(out.strip(), "ASSIGN_AUTO")

    def test_non_confidential_values_without_default_are_manual(self):
        out = self.preflight(definition(
            credentials="      base_url:\n        label: \"Base URL\"\n        is_confidential: false\n",
            constants="      MODE:\n        label: \"Mode\"\n        type: \"text\"\n"))
        self.assertIn("ASSIGN_MANUAL", out)
        self.assertIn("- Base URL\n", out)
        self.assertIn("- Mode", out)


class Assignment(HarnessProject):
    def setUp(self):
        super().setUp()
        self.add_agent()
        self.run_dir = self.new_run()
        self.script("deploy.py", "--target", "demo")

    def check(self, **fake):
        return self.script("run_eval.py", "--run-dir", str(self.run_dir), "--check", **fake)

    def records(self):
        return json.loads((self.root / ".harness" / "deployments.json").read_text())

    def test_deployed_but_not_assigned(self):
        result = self.check()
        self.assertEqual(result.returncode, 6)
        self.assertIn("EVAL_NOT_ASSIGNED", result.stdout)

    def test_assigned_is_ready(self):
        self.assign("demo", "--run-dir", str(self.run_dir))
        self.assertIn("EVAL_READY", self.check().stdout)
        assignment = self.records()["demo"]["assignment"]
        self.assertEqual((assignment["status"], assignment["by"]), ("assigned", "harness"))
        self.assertEqual(assignment["run_id"], self.run_dir.name)

    def test_assigned_in_another_project_does_not_count(self):
        self.assign()
        self.script("deploy.py", "--target", "demo", project_out="Current project: other-project")
        self.assertIn("EVAL_NOT_ASSIGNED", self.check(project_out="Current project: other-project").stdout)

    def test_refuses_to_record_without_a_deployment_here(self):
        result = self.script("record_assignment.py", "--target", "demo", "--status", "assigned",
                             "--by", "user", project_out="Current project: other-project")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("assignment", self.records()["demo"])

    def test_unassigned_is_not_ready(self):
        self.assign()
        self.script("record_assignment.py", "--target", "demo", "--status", "unassigned", "--by", "harness")
        self.assertIn("EVAL_NOT_ASSIGNED", self.check().stdout)

    def test_recording_twice_is_idempotent(self):
        self.assign()
        first = self.records()
        self.assign()
        second = self.records()
        self.assertEqual(list(second), list(first))
        self.assertEqual(set(second["demo"]), {"project", "hash", "pushed_at", "assignment"})
        self.assertEqual({k: v for k, v in second["demo"]["assignment"].items() if k != "at"},
                         {k: v for k, v in first["demo"]["assignment"].items() if k != "at"})

    def test_redeploy_keeps_assignment(self):
        self.assign()
        self.script("deploy.py", "--target", "demo")
        self.assertIn("EVAL_READY", self.check().stdout)


@unittest.skipUnless(HAS_YAML, NEEDS_YAML)
class PlatformSession(HarnessProject):
    def test_open_and_close(self):
        self.add_agent(definition=definition(constants=CONSTANT_WITH_DEFAULT))
        result = self.script("platform_session.py", "--target", "demo", "--operation", "assign",
                             project_out=f"Current project: {UUID} (Demo)")
        self.assertIn("PLATFORM_SESSION_OPEN", result.stdout, result.stderr)
        self.assertIn(MY_AGENTS + "/assign", result.stdout)
        session = json.loads((self.root / ".harness" / "platform_session.json").read_text())
        self.assertEqual((session["project_uuid"], session["agent_name"]), (UUID, "Demo Agent"))
        self.assertIn("PLATFORM_SESSION_CLOSED", self.script("platform_session.py", "--close").stdout)
        self.assertFalse((self.root / ".harness" / "platform_session.json").exists())

    def test_failed_open_removes_the_previous_session(self):
        self.add_agent(definition=definition())
        self.script("platform_session.py", "--target", "demo", "--operation", "assign",
                    project_out=f"Current project: {UUID} (Demo)")
        result = self.script("platform_session.py", "--target", "demo", "--operation", "assign")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / ".harness" / "platform_session.json").exists())

    def test_tab_is_bound_once(self):
        self.add_agent(definition=definition())
        self.assertNotEqual(self.script("platform_session.py", "--bind-tab", "7").returncode, 0)
        self.script("platform_session.py", "--target", "demo", "--operation", "assign",
                    project_out=f"Current project: {UUID} (Demo)")
        self.assertIn("PLATFORM_TAB_BOUND", self.script("platform_session.py", "--bind-tab", "7").stdout)
        self.assertNotEqual(self.script("platform_session.py", "--bind-tab", "8").returncode, 0)
        session = json.loads((self.root / ".harness" / "platform_session.json").read_text())
        self.assertEqual(session["tab_id"], 7)


class ChromeGuard(HarnessProject):
    def setUp(self):
        super().setUp()
        (self.root / ".harness" / "runs").mkdir(parents=True)

    def open_session(self, started=None, **extra):
        started = started or datetime.now(timezone.utc)
        session = {"project_uuid": UUID, "agent_name": "Demo Agent", "operation": "assign",
                   "started_at": started.isoformat(timespec="seconds"), "tab_id": 1, **extra}
        (self.root / ".harness" / "platform_session.json").write_text(json.dumps(session))

    def guard(self, tool, tool_input, root=None, raw=None):
        payload = raw if raw is not None else json.dumps(
            {"tool_name": f"mcp__claude-in-chrome__{tool}", "tool_input": tool_input})
        env = {**self.env, "CLAUDE_PROJECT_DIR": str(root or self.root)}
        result = subprocess.run([sys.executable, str(GUARD)], input=payload, env=env,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)["hookSpecificOutput"] if result.stdout.strip() else None

    def decision(self, tool, tool_input):
        return self.guard(tool, tool_input)["permissionDecision"]

    def test_allowed_urls(self):
        self.open_session()
        for url in (MY_AGENTS, MY_AGENTS + "/", MY_AGENTS + "/assign", MY_AGENTS.removeprefix("https://")):
            self.assertEqual(self.decision("navigate", {"url": url, "tabId": 1}), "allow", url)

    def test_blocked_urls(self):
        self.open_session()
        for url in (MY_AGENTS.replace(UUID, "00000000-0000-0000-0000-000000000000"),
                    f"https://dash.weni.ai/projects/{UUID}/insights",
                    f"https://evil.example/projects/{UUID}/ai-agents/agents",
                    MY_AGENTS + "/assign?x=1", "back", "forward"):
            out = self.guard("navigate", {"url": url, "tabId": 1})
            self.assertEqual(out["permissionDecision"], "deny", url)
            self.assertIn(url, out["permissionDecisionReason"])

    def test_no_session_denies(self):
        self.assertEqual(self.decision("navigate", {"url": MY_AGENTS}), "deny")
        self.assertEqual(self.decision("computer", {"action": "screenshot", "tabId": 1}), "deny")
        self.assertEqual(self.decision("tabs_context_mcp", {}), "deny")

    def test_expired_future_or_malformed_session_denies(self):
        for started, extra in ((datetime.now(timezone.utc) - timedelta(hours=2), {}),
                               (datetime.now(timezone.utc) + timedelta(hours=1), {}),
                               (None, {"operation": "delete"}), (None, {"agent_name": ""})):
            self.open_session(started, **extra)
            self.assertEqual(self.decision("navigate", {"url": MY_AGENTS, "tabId": 1}), "deny", (started, extra))
        (self.root / ".harness" / "platform_session.json").write_text("[1, 2]")
        self.assertEqual(self.decision("navigate", {"url": MY_AGENTS, "tabId": 1}), "deny")

    def test_malformed_payload_denies_in_a_weni_project(self):
        self.open_session()
        for raw in ("{bad json", json.dumps({"tool_input": {}}),
                    json.dumps({"tool_name": "mcp__claude-in-chrome__navigate", "tool_input": "x"})):
            self.assertEqual(self.guard(None, None, raw=raw)["permissionDecision"], "deny", raw)

    def test_only_the_session_tab(self):
        self.open_session()
        for tool, tool_input in (("computer", {"action": "screenshot", "tabId": 999}),
                                 ("find", {"query": "x", "tabId": 999}),
                                 ("tabs_close_mcp", {"tabId": 999}),
                                 ("navigate", {"url": MY_AGENTS, "tabId": 999}),
                                 ("navigate", {"url": MY_AGENTS})):
            self.assertEqual(self.decision(tool, tool_input), "deny", (tool, tool_input))
        self.assertEqual(self.decision("tabs_close_mcp", {"tabId": 1}), "allow")

    def test_before_binding_only_tab_tools(self):
        self.open_session(tab_id=None)
        self.assertEqual(self.decision("tabs_create_mcp", {}), "allow")
        self.assertEqual(self.decision("tabs_context_mcp", {}), "allow")
        self.assertEqual(self.decision("computer", {"action": "screenshot", "tabId": None}), "deny")

    def test_keyboard_shortcuts_are_denied(self):
        self.open_session()
        for keys in ("cmd+l", "ctrl+L", "alt+Left", "cmd+[", "F6", "Tab cmd+t"):
            self.assertEqual(self.decision("computer", {"action": "key", "text": keys, "tabId": 1}), "deny", keys)
        self.assertEqual(self.decision("computer", {"action": "key", "text": "Escape", "tabId": 1}), "allow")

    def test_omnibox_batch_is_denied(self):
        self.open_session()
        self.assertEqual(self.decision("browser_batch", {"actions": [
            {"name": "computer", "input": {"action": "key", "text": "cmd+l", "tabId": 1}},
            {"name": "computer", "input": {"action": "type", "text": "https://evil.example", "tabId": 1}},
            {"name": "computer", "input": {"action": "key", "text": "Return", "tabId": 1}}]}), "deny")

    def test_computer_actions_are_not_prompted(self):
        self.open_session()
        for action in ("screenshot", "left_click", "type", "scroll", "wait"):
            self.assertEqual(self.decision("computer", {"action": action, "tabId": 1}), "allow", action)
        for action in ("right_click", "left_click_drag"):
            self.assertEqual(self.decision("computer", {"action": action, "tabId": 1}), "deny", action)

    def test_always_denied_tools(self):
        self.open_session()
        for tool in ("javascript_tool", "form_input", "read_network_requests", "file_upload", "upload_image"):
            self.assertEqual(self.decision(tool, {"tabId": 1}), "deny", tool)

    def test_read_page_must_be_scoped(self):
        self.open_session()
        self.assertEqual(self.decision("read_page", {"tabId": 1}), "deny")
        self.assertEqual(self.decision("read_page", {"tabId": 1, "ref_id": "ref_3"}), "allow")
        self.assertEqual(self.decision("find", {"tabId": 1, "query": "Assign new agents button"}), "allow")
        self.assertEqual(self.decision("get_page_text", {"tabId": 1}), "deny")

    def test_batch_with_a_click_is_allowed(self):
        self.open_session()
        self.assertEqual(self.decision("browser_batch", {"actions": [
            {"name": "computer", "input": {"action": "left_click", "coordinate": [1, 2], "tabId": 1}},
            {"name": "computer", "input": {"action": "screenshot", "tabId": 1}}]}), "allow")

    def test_batch_with_a_blocked_navigation_denies(self):
        self.open_session()
        out = self.guard("browser_batch", {"actions": [
            {"name": "computer", "input": {"action": "left_click", "coordinate": [1, 2], "tabId": 1}},
            {"name": "navigate", "input": {"url": "https://dash.weni.ai/insights", "tabId": 1}}]})
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertIn("insights", out["permissionDecisionReason"])

    def test_batch_of_safe_actions_allows(self):
        self.open_session()
        self.assertEqual(self.decision("browser_batch", {"actions": [
            {"name": "navigate", "input": {"url": MY_AGENTS, "tabId": 1}},
            {"name": "computer", "input": {"action": "wait", "duration": 3, "tabId": 1}},
            {"name": "computer", "input": {"action": "screenshot", "scale": 0.5, "tabId": 1}}]}), "allow")

    def test_no_opinion_outside_a_weni_project(self):
        other = self.tmp / "other"
        other.mkdir()
        self.assertIsNone(self.guard("navigate", {"url": "https://example.com"}, root=other))


if __name__ == "__main__":
    unittest.main()
