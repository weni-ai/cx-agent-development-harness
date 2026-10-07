"""run_tool_tests.py and run_eval.py behavior."""

import unittest

from helpers import HarnessProject

try:
    import yaml  # noqa: F401
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

DEFINITION = """agents:
  demo_agent:
    tools:
      - lookup:
          source:
            path: custom/lookup_dir
            entrypoint: main.Lookup
"""


@unittest.skipUnless(HAS_YAML, "needs PyYAML (create the repo .venv: python3 -m venv .venv && .venv/bin/pip install pyyaml)")
class ToolTests(HarnessProject):
    def test_traceback_with_exit_zero_is_a_failure(self):
        self.add_agent(definition=DEFINITION)
        result = self.script("run_tool_tests.py", run_out="Traceback (most recent call last):\n  boom")
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL  demo_agent/lookup", result.stdout)

    def test_summary_includes_custom_source_path(self):
        folder = self.add_agent(definition=DEFINITION)
        self.assertEqual(self.script("run_tool_tests.py", run_out="ok").returncode, 0)
        self.assertIn("custom/lookup_dir/test-results.md", (folder / "test-results.md").read_text())


class EvalRounds(HarnessProject):
    def setUp(self):
        super().setUp()
        self.folder = self.add_agent()
        self.run_dir = self.new_run()
        self.tests_md = self.run_dir / "artifacts" / "03-tests.md"
        self.tests_md.write_text("tester owns this")
        deployed = self.script("deploy.py", "--target", "demo")
        self.assertIn("DEPLOY_OK", deployed.stdout, deployed.stdout + deployed.stderr)

    def eval(self, *args, **fake):
        return self.script("run_eval.py", "--run-dir", str(self.run_dir), *args, **fake)

    def test_rounds_are_numbered_and_tester_artifact_untouched(self):
        self.assertIn("EVAL_FAIL", self.eval(eval_rc=1).stdout)
        self.assertIn("EVAL_PASS", self.eval().stdout)
        artifacts = self.run_dir / "artifacts"
        self.assertTrue((artifacts / "03-eval-run-1.md").exists())
        self.assertIn("Status: PASS", (artifacts / "03-eval-run-2.md").read_text())
        self.assertEqual(self.tests_md.read_text(), "tester owns this")

    def test_round_limit_ignores_filtered_reruns(self):
        self.eval("--max-rounds", "1", eval_rc=1)
        self.assertIn("EVAL_PASS", self.eval("--max-rounds", "1", "--filter", "greeting").stdout)
        result = self.eval("--max-rounds", "1")
        self.assertEqual(result.returncode, 3)
        self.assertIn("EVAL_ROUND_LIMIT", result.stdout)

    def test_timeout(self):
        result = self.eval("--timeout", "1", eval_sleep=3)
        self.assertIn("EVAL_TIMEOUT", result.stdout)

    def test_verbose_is_always_passed(self):
        self.eval()
        self.assertIn("eval run --verbose", (self.tmp / "weni.log").read_text())


class EvalNeedsDeployment(HarnessProject):
    def setUp(self):
        super().setUp()
        self.folder = self.add_agent()
        self.run_dir = self.new_run()

    def eval(self, *args, **fake):
        return self.script("run_eval.py", "--run-dir", str(self.run_dir), *args, **fake)

    def test_refuses_when_never_deployed(self):
        result = self.eval()
        self.assertEqual(result.returncode, 4)
        self.assertIn("EVAL_NOT_DEPLOYED", result.stdout)
        self.assertNotIn("eval run", (self.tmp / "weni.log").read_text())

    def test_refuses_when_local_changes_since_push(self):
        self.script("deploy.py", "--target", "demo")
        self.assertIn("EVAL_READY", self.eval("--check").stdout)
        (self.folder / "agent_definition.yaml").write_text("agents: {changed: {}}\n")
        result = self.eval()
        self.assertEqual(result.returncode, 5)
        self.assertIn("EVAL_STALE_DEPLOYMENT", result.stdout)

    def test_eval_plan_edits_do_not_require_redeploy(self):
        self.script("deploy.py", "--target", "demo")
        (self.folder / "agent_evaluation.yml").write_text("tests: {}\n")
        self.assertIn("EVAL_READY", self.eval("--check").stdout)

    def test_deployment_to_another_project_does_not_count(self):
        self.script("deploy.py", "--target", "demo")
        self.assertIn("EVAL_NOT_DEPLOYED", self.eval(project_out="Current project: other-uuid").stdout)

    def test_failed_push_is_not_recorded(self):
        result = self.script("deploy.py", "--target", "demo", push_out="error: invalid definition", push_rc=1)
        self.assertIn("DEPLOY_FAIL", result.stdout)
        self.assertIn("EVAL_NOT_DEPLOYED", self.eval().stdout)

    def test_voided_round_does_not_count(self):
        self.script("deploy.py", "--target", "demo")
        self.eval("--max-rounds", "1", eval_rc=1)
        self.assertIn("EVAL_ROUND_VOIDED", self.eval("--void-last", "Manager answered").stdout)
        self.assertIn("EVAL_PASS", self.eval("--max-rounds", "1").stdout)
        artifacts = self.run_dir / "artifacts"
        self.assertTrue((artifacts / "03-eval-void-1.md").exists())
        self.assertTrue((artifacts / "03-eval-run-1.md").exists())


def python_without_yaml():
    """Return a system python that lacks PyYAML (like a partner's python3), if any."""
    import shutil
    import subprocess as sp
    for candidate in ("/usr/bin/python3", shutil.which("python3")):
        if candidate and sp.run([candidate, "-c", "import yaml"], capture_output=True).returncode != 0:
            return candidate
    return None


@unittest.skipUnless(HAS_YAML and python_without_yaml(), "needs a python3 without PyYAML and a .venv with it")
class RunsInsideProjectVenv(HarnessProject):
    def test_yaml_scripts_work_when_called_with_system_python(self):
        import os
        import subprocess as sp
        from helpers import SCRIPTS
        import shutil
        from helpers import REPO
        shutil.rmtree(self.root / ".venv")
        os.symlink(REPO / ".venv", self.root / ".venv")  # a real venv with PyYAML, like the partner's
        self.add_agent(definition=DEFINITION)
        result = sp.run([python_without_yaml(), str(SCRIPTS / "validate_schema.py"), "--target", "demo"],
                        cwd=str(self.root), env=self.env, capture_output=True, text=True)
        self.assertNotIn("PyYAML is required", result.stdout + result.stderr)
