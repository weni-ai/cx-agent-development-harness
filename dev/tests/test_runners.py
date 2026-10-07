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
        self.add_agent()
        self.run_dir = self.new_run()
        self.tests_md = self.run_dir / "artifacts" / "03-tests.md"
        self.tests_md.write_text("tester owns this")

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
