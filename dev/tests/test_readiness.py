"""The readiness gate and its enforcement in init_run.py."""

from helpers import HarnessProject


class ReadinessStates(HarnessProject):
    def test_ready(self):
        result = self.script("check_ready.py")
        self.assertEqual((result.returncode, result.stdout.split()[0]), (0, "READY"))

    def test_server_rejecting_token_means_auth_required(self):
        result = self.script("check_ready.py", list_out="Missing login authorization, please login first")
        self.assertEqual((result.returncode, result.stdout.split()[0]), (10, "AUTH_REQUIRED"))

    def test_no_project_selected(self):
        result = self.script("check_ready.py", project_out="Current project: None")
        self.assertEqual((result.returncode, result.stdout.split()[0]), (11, "PROJECT_NOT_SELECTED"))

    def test_unexpected_failure_is_reported_not_guessed(self):
        result = self.script("check_ready.py", project_out="boom", project_rc=3)
        self.assertEqual(result.returncode, 12)
        self.assertIn("boom", result.stdout)

    def test_token_check_is_cached(self):
        self.script("check_ready.py")
        self.script("check_ready.py")
        self.assertEqual((self.tmp / "weni.log").read_text().count("project list"), 1)

    def test_hook_is_silent_outside_weni_projects(self):
        result = self.script("check_ready.py", "--hook")
        self.assertEqual((result.returncode, result.stdout.strip()), (0, ""))

    def test_hook_reports_without_network_in_weni_projects(self):
        self.add_agent()
        result = self.script("check_ready.py", "--hook", project_out="Current project: None")
        self.assertEqual(result.returncode, 0)
        self.assertIn("PROJECT_NOT_SELECTED", result.stdout)
        self.assertNotIn("project list", (self.tmp / "weni.log").read_text())


class NotLoggedIn(HarnessProject):
    logged_in = False

    def test_missing_config_means_auth_required(self):
        self.assertEqual(self.script("check_ready.py").returncode, 10)

    def test_init_run_refuses_without_login(self):
        result = self.script("init_run.py", "feature", "--target", "demo")
        self.assertEqual(result.returncode, 10)
        self.assertFalse((self.root / ".harness" / "runs").exists() and any((self.root / ".harness" / "runs").iterdir()))

    def test_resume_check_does_not_need_login(self):
        self.assertIn("NO_OPEN_RUN", self.script("init_run.py", "--latest-open").stdout)


class NotInstalled(HarnessProject):
    install_weni = False

    def test_not_installed(self):
        self.assertEqual(self.script("check_ready.py").returncode, 20)


class RunCreation(HarnessProject):
    def test_init_run_creates_run_when_ready(self):
        run_dir = self.new_run()
        self.assertEqual(self.state(run_dir)["target"], "demo")
        self.assertTrue((run_dir / "STATE.md").exists())
