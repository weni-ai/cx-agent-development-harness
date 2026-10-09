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


class DeployAskRule(HarnessProject):
    RULE = "Bash(python3 *scripts/deploy.py*)"

    def test_merges_rule_once_and_keeps_existing_settings(self):
        import importlib
        import json
        import os
        os.environ["CLAUDE_PROJECT_DIR"] = str(self.root)
        settings_path = self.root / ".claude" / "settings.local.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(json.dumps({
            "permissions": {"allow": ["Bash(ls *)"], "ask": ["Bash(git push *)"]},
            "env": {"FOO": "1"},
        }))
        bootstrap = importlib.import_module("bootstrap_env")
        bootstrap.ensure_deploy_ask_rule()
        bootstrap.ensure_deploy_ask_rule()
        settings = json.loads(settings_path.read_text())
        self.assertEqual(settings["permissions"]["ask"], ["Bash(git push *)", self.RULE])
        self.assertEqual(settings["permissions"]["allow"], ["Bash(ls *)"])
        self.assertEqual(settings["env"], {"FOO": "1"})

    def test_creates_settings_and_ignores_them_in_git(self):
        import importlib
        import json
        import os
        os.environ["CLAUDE_PROJECT_DIR"] = str(self.root)
        bootstrap = importlib.import_module("bootstrap_env")
        bootstrap.ensure_deploy_ask_rule()
        bootstrap.ensure_gitignore()
        settings = json.loads((self.root / ".claude" / "settings.local.json").read_text())
        self.assertEqual(settings, {"permissions": {"ask": [self.RULE]}})
        self.assertIn(".claude/settings.local.json", (self.root / ".gitignore").read_text().splitlines())

    def test_leaves_invalid_json_untouched(self):
        import importlib
        import os
        os.environ["CLAUDE_PROJECT_DIR"] = str(self.root)
        settings_path = self.root / ".claude" / "settings.local.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text("{ not json")
        importlib.import_module("bootstrap_env").ensure_deploy_ask_rule()
        self.assertEqual(settings_path.read_text(), "{ not json")


class DeployPermissionHook(HarnessProject):
    def run_hook(self, command):
        import json
        import subprocess
        from helpers import SCRIPTS
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
        result = subprocess.run([sys.executable, str(SCRIPTS / "deploy_permission.py")],
                                input=payload, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        return json.loads(result.stdout)["hookSpecificOutput"] if result.stdout.strip() else None

    def test_asks_for_deploy_in_any_version_and_quoting(self):
        for command in ('python3 "/x/weni/9.9.9/scripts/deploy.py" --target foo',
                        "python3 /x/weni/2.1.1/scripts/deploy.py --target foo --record-only"):
            decision = self.run_hook(command)
            self.assertEqual(decision["permissionDecision"], "ask")
            self.assertIn("live Manager", decision["permissionDecisionReason"])

    def test_no_opinion_on_other_commands(self):
        for command in ("ls", 'python3 "/x/scripts/run_eval.py" --run-dir r --check',
                        "python3 /x/scripts/deploy_permission.py"):
            self.assertIsNone(self.run_hook(command))
