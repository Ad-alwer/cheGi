"""Tests for the DoctorService class."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from chegi.services.doctor import CheckStatus, DoctorService
from chegi.services.doctor.models import DoctorReport
from chegi.services.git.exceptions import GitNotInstalledError


class TestDoctorHealthChecks:
    """Tests for health-related doctor checks."""

    def test_git_installed_passes(self) -> None:
        """Test that _check_git_installed returns PASS when git is available."""
        with patch.object(DoctorService, "_check_git_installed") as mock_check:
            mock_check.return_value = MagicMock(
                name="Git Installed",
                status=CheckStatus.PASS,
                message="Git is installed and accessible.",
            )
            service = DoctorService(Path("/tmp"))
            result = service._check_git_installed()
            assert result.status == CheckStatus.PASS

    @patch(
        "chegi.services.doctor.doctor_service.GitClient.check_git_installation",
        side_effect=GitNotInstalledError("Git not found"),
    )
    def test_git_installed_fails(self, mock_check: MagicMock) -> None:
        """Test that _check_git_installed returns FAIL when git is missing."""
        service = DoctorService(Path("/tmp"))
        result = service._check_git_installed()
        assert result.status == CheckStatus.FAIL

    @patch("chegi.services.doctor.doctor_service.GitClient.run_command")
    def test_git_identity_passes(self, mock_run: MagicMock) -> None:
        """Test that _check_git_identity returns PASS when both name and email are set."""
        mock_run.side_effect = lambda cmd, **kw: (
            "John Doe" if "user.name" in cmd else "john@example.com"
        )
        service = DoctorService(Path("/tmp"))
        result = service._check_git_identity()
        assert result.status == CheckStatus.PASS

    @patch("chegi.services.doctor.doctor_service.GitClient.run_command")
    def test_git_identity_fails_when_missing(self, mock_run: MagicMock) -> None:
        """Test that _check_git_identity returns FAIL when identity is missing."""
        mock_run.return_value = ""
        service = DoctorService(Path("/tmp"))
        result = service._check_git_identity()
        assert result.status == CheckStatus.FAIL

    def test_gitignore_passes_when_key_patterns_present(self, tmp_path: Path) -> None:
        """Test that _check_gitignore returns PASS when .gitignore has key patterns."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(
            "# Dependencies\nnode_modules/\n.venv/\n__pycache__/\n"
            "# Environment\n.env\n.env.*\n"
            "# Keys\n*.key\n*.pem\n"
            "# OS\n.DS_Store\n"
            "# IDE\n.vscode/\n.idea/\n"
        )
        service = DoctorService(tmp_path)
        result = service._check_gitignore()
        assert result.status == CheckStatus.PASS

    def test_gitignore_warns_when_key_patterns_missing(self, tmp_path: Path) -> None:
        """Test that _check_gitignore returns WARN when some patterns are missing."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("node_modules/\n")
        service = DoctorService(tmp_path)
        result = service._check_gitignore()
        assert result.status == CheckStatus.WARN

    def test_gitignore_fails_when_missing(self, tmp_path: Path) -> None:
        """Test that _check_gitignore returns FAIL when no .gitignore exists."""
        service = DoctorService(tmp_path)
        result = service._check_gitignore()
        assert result.status == CheckStatus.FAIL

    def test_chegi_passes_when_configured(self, tmp_path: Path) -> None:
        """Test that _check_chegi returns PASS when .chegi/ has all files."""
        chegi = tmp_path / ".chegi"
        chegi.mkdir()
        (chegi / "config.json").write_text("{}")
        (chegi / "guard-rules.json").write_text("{}")
        (chegi / ".chegiignore").write_text("")

        service = DoctorService(tmp_path)
        result = service._check_chegi()
        assert result.status == CheckStatus.PASS

    def test_chegi_warns_when_missing(self, tmp_path: Path) -> None:
        """Test that _check_chegi returns WARN when .chegi/ does not exist."""
        service = DoctorService(tmp_path)
        result = service._check_chegi()
        assert result.status == CheckStatus.WARN

    def test_chegi_warns_when_partial(self, tmp_path: Path) -> None:
        """Test that _check_chegi returns WARN when .chegi/ is incomplete."""
        chegi = tmp_path / ".chegi"
        chegi.mkdir()
        (chegi / "config.json").write_text("{}")

        service = DoctorService(tmp_path)
        result = service._check_chegi()
        assert result.status == CheckStatus.WARN


class TestDoctorSecurityChecks:
    """Tests for security-related doctor checks."""

    @patch("chegi.services.doctor.doctor_service.SecurityGuard.scan_repo")
    def test_staged_sensitive_passes(self, mock_scan: MagicMock) -> None:
        """Test that _check_staged_sensitive returns PASS when no sensitive files staged."""
        mock_scan.return_value = MagicMock(is_safe=True, sensitive_files=[])
        service = DoctorService(Path("/tmp/.git"))
        service.is_git_repo = True
        result = service._check_staged_sensitive()
        assert result.status == CheckStatus.PASS

    @patch("chegi.services.doctor.doctor_service.SecurityGuard.scan_repo")
    def test_staged_sensitive_fails(self, mock_scan: MagicMock) -> None:
        """Test that _check_staged_sensitive returns FAIL when sensitive files staged."""
        mock_scan.return_value = MagicMock(is_safe=False, sensitive_files=[".env"])
        service = DoctorService(Path("/tmp/.git"))
        service.is_git_repo = True
        result = service._check_staged_sensitive()
        assert result.status == CheckStatus.FAIL

    def test_staged_sensitive_skips_non_repo(self) -> None:
        """Test that _check_staged_sensitive returns SKIP when not in a git repo."""
        service = DoctorService(Path("/tmp"))
        service.is_git_repo = False
        result = service._check_staged_sensitive()
        assert result.status == CheckStatus.SKIP

    @patch("chegi.services.doctor.doctor_service.GitClient.run_command")
    def test_env_tracked_passes(self, mock_run: MagicMock) -> None:
        """Test that _check_env_tracked returns PASS when no .env files tracked."""
        mock_run.return_value = ""
        service = DoctorService(Path("/tmp/.git"))
        service.is_git_repo = True
        result = service._check_env_tracked()
        assert result.status == CheckStatus.PASS

    @patch("chegi.services.doctor.doctor_service.GitClient.run_command")
    def test_env_tracked_fails(self, mock_run: MagicMock) -> None:
        """Test that _check_env_tracked returns FAIL when .env files are tracked."""
        mock_run.return_value = ".env"
        service = DoctorService(Path("/tmp/.git"))
        service.is_git_repo = True
        result = service._check_env_tracked()
        assert result.status == CheckStatus.FAIL

    def test_pre_commit_hook_passes(self, tmp_path: Path) -> None:
        """Test that _check_pre_commit_hook returns PASS when hook is installed and executable."""
        hooks = tmp_path / ".git" / "hooks"
        hooks.mkdir(parents=True)
        hook_file = hooks / "pre-commit"
        hook_file.write_text("#!/bin/sh\necho 'guard check'")
        hook_file.chmod(0o755)

        service = DoctorService(tmp_path)
        service.is_git_repo = True
        result = service._check_pre_commit_hook()
        assert result.status == CheckStatus.PASS

    def test_pre_commit_hook_warns_when_missing(self, tmp_path: Path) -> None:
        """Test that _check_pre_commit_hook returns WARN when no hook installed."""
        service = DoctorService(tmp_path)
        service.is_git_repo = True
        result = service._check_pre_commit_hook()
        assert result.status == CheckStatus.WARN


class TestDoctorStatsChecks:
    """Tests for statistics-related doctor checks."""

    @patch("chegi.services.doctor.doctor_service.GitClient.run_command")
    def test_commits_passes(self, mock_run: MagicMock) -> None:
        """Test that _check_commits returns PASS when there are commits."""
        mock_run.return_value = "42"
        service = DoctorService(Path("/tmp/.git"))
        service.is_git_repo = True
        result = service._check_commits()
        assert result.status == CheckStatus.PASS
        assert "42" in result.message

    @patch("chegi.services.doctor.doctor_service.GitClient.run_command")
    def test_commits_warns_when_zero(self, mock_run: MagicMock) -> None:
        """Test that _check_commits returns WARN when there are no commits."""
        mock_run.return_value = "0"
        service = DoctorService(Path("/tmp/.git"))
        service.is_git_repo = True
        result = service._check_commits()
        assert result.status == CheckStatus.WARN

    @patch("chegi.services.doctor.doctor_service.GitClient.run_command")
    def test_branches_passes(self, mock_run: MagicMock) -> None:
        """Test that _check_branches returns PASS when branches exist."""
        mock_run.return_value = "* main\n  develop\n  feature/test"
        service = DoctorService(Path("/tmp/.git"))
        service.is_git_repo = True
        result = service._check_branches()
        assert result.status == CheckStatus.PASS

    @patch("chegi.services.doctor.doctor_service.GitClient.run_command")
    def test_remote_passes(self, mock_run: MagicMock) -> None:
        """Test that _check_remote returns PASS when remotes exist."""
        mock_run.return_value = "origin"
        service = DoctorService(Path("/tmp/.git"))
        service.is_git_repo = True
        result = service._check_remote()
        assert result.status == CheckStatus.PASS

    @patch("chegi.services.doctor.doctor_service.GitClient.run_command")
    def test_remote_warns_when_none(self, mock_run: MagicMock) -> None:
        """Test that _check_remote returns WARN when no remotes configured."""
        mock_run.return_value = ""
        service = DoctorService(Path("/tmp/.git"))
        service.is_git_repo = True
        result = service._check_remote()
        assert result.status == CheckStatus.WARN


class TestDoctorHistorySecrets:
    """Tests for history secrets check."""

    @patch("chegi.services.doctor.doctor_service.GuardHistoryService")
    def test_history_secrets_passes(self, mock_guard: MagicMock) -> None:
        """Test that _check_history_secrets returns PASS when no secrets found."""
        mock_guard.return_value.scan.return_value = MagicMock(
            total_findings=0, total_commits_scanned=10
        )
        service = DoctorService(Path("/tmp/.git"))
        service.is_git_repo = True
        result = service._check_history_secrets()
        assert result.status == CheckStatus.PASS

    @patch("chegi.services.doctor.doctor_service.GuardHistoryService")
    def test_history_secrets_fails(self, mock_guard: MagicMock) -> None:
        """Test that _check_history_secrets returns FAIL when secrets found."""
        mock_guard.return_value.scan.return_value = MagicMock(
            total_findings=3, total_commits_scanned=50
        )
        service = DoctorService(Path("/tmp/.git"))
        service.is_git_repo = True
        result = service._check_history_secrets()
        assert result.status == CheckStatus.FAIL
        assert "3" in result.message

    def test_history_secrets_skips_non_repo(self) -> None:
        """Test that _check_history_secrets returns SKIP when not in git repo."""
        service = DoctorService(Path("/tmp"))
        service.is_git_repo = False
        result = service._check_history_secrets()
        assert result.status == CheckStatus.SKIP


class TestDoctorContributors:
    """Tests for contributors check."""

    @patch("chegi.services.doctor.doctor_service.GitClient.run_command")
    def test_contributors_passes(self, mock_run: MagicMock) -> None:
        """Test that _check_contributors returns PASS with contributor count."""
        mock_run.return_value = "    42\tJohn Doe\n    15\tJane Smith"
        service = DoctorService(Path("/tmp/.git"))
        service.is_git_repo = True
        result = service._check_contributors()
        assert result.status == CheckStatus.PASS
        assert "2" in result.message

    def test_contributors_skips_non_repo(self) -> None:
        """Test that _check_contributors returns SKIP when not in git repo."""
        service = DoctorService(Path("/tmp"))
        service.is_git_repo = False
        result = service._check_contributors()
        assert result.status == CheckStatus.SKIP


class TestDoctorRemoteSync:
    """Tests for remote sync check."""

    @patch("chegi.services.doctor.doctor_service.GitClient.run_command")
    def test_remote_sync_passes(self, mock_run: MagicMock) -> None:
        """Test that _check_remote_sync returns PASS when synced."""
        mock_run.side_effect = [
            "main",  # git branch --show-current
            "origin",  # git remote
            "origin/main",  # git rev-parse --abbrev-ref @{u}
            "0\t0",  # git rev-list --left-right --count HEAD...@{u}
        ]
        service = DoctorService(Path("/tmp/.git"))
        service.is_git_repo = True
        result = service._check_remote_sync()
        assert result.status == CheckStatus.PASS

    @patch("chegi.services.doctor.doctor_service.GitClient.run_command")
    def test_remote_sync_ahead(self, mock_run: MagicMock) -> None:
        """Test that _check_remote_sync returns WARN when ahead."""
        mock_run.side_effect = [
            "main",
            "origin",
            "origin/main",
            "3\t0",
        ]
        service = DoctorService(Path("/tmp/.git"))
        service.is_git_repo = True
        result = service._check_remote_sync()
        assert result.status == CheckStatus.WARN

    @patch("chegi.services.doctor.doctor_service.GitClient.run_command")
    def test_remote_sync_behind(self, mock_run: MagicMock) -> None:
        """Test that _check_remote_sync returns WARN when behind."""
        mock_run.side_effect = [
            "main",
            "origin",
            "origin/main",
            "0\t5",
        ]
        service = DoctorService(Path("/tmp/.git"))
        service.is_git_repo = True
        result = service._check_remote_sync()
        assert result.status == CheckStatus.WARN

    @patch("chegi.services.doctor.doctor_service.GitClient.run_command")
    def test_remote_sync_diverged(self, mock_run: MagicMock) -> None:
        """Test that _check_remote_sync returns WARN when diverged."""
        mock_run.side_effect = [
            "main",
            "origin",
            "origin/main",
            "2\t4",
        ]
        service = DoctorService(Path("/tmp/.git"))
        service.is_git_repo = True
        result = service._check_remote_sync()
        assert result.status == CheckStatus.WARN

    def test_remote_sync_skips_non_repo(self) -> None:
        """Test that _check_remote_sync returns SKIP when not in git repo."""
        service = DoctorService(Path("/tmp"))
        service.is_git_repo = False
        result = service._check_remote_sync()
        assert result.status == CheckStatus.SKIP


class TestDoctorServiceRun:
    """Tests for DoctorService.run()."""

    @patch("chegi.services.doctor.doctor_service.GitClient.is_valid_repo")
    @patch("chegi.services.doctor.doctor_service.GitClient.run_command")
    @patch("chegi.services.doctor.doctor_service.GitClient.check_git_installation")
    @patch("chegi.services.doctor.doctor_service.SecurityGuard.scan_repo")
    @patch("chegi.services.doctor.doctor_service.GuardHistoryService")
    def test_run_full_report(
        self,
        mock_history: MagicMock,
        mock_scan: MagicMock,
        mock_check: MagicMock,
        mock_run: MagicMock,
        mock_valid: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that run() returns a DoctorReport with all checks."""
        mock_valid.return_value = True
        mock_check.return_value = True
        mock_scan.return_value = MagicMock(is_safe=True, sensitive_files=[])
        mock_history.return_value.scan.return_value = MagicMock(
            total_findings=0, total_commits_scanned=10
        )

        call_count = [0]

        def run_side_effect(cmd, **kw):
            call_count[0] += 1
            mapping = {
                "git config --global user.name": "John",
                "git config --global user.email": "john@test.com",
                "git ls-files .env .env.*": "",
                "git rev-list --count HEAD": "10",
                "git branch --list": "* main\n  dev",
                "git remote": "origin",
                "git branch --show-current": "main",
                "git rev-parse --abbrev-ref @{u}": "origin/main",
                "git rev-list --left-right --count HEAD...@{u}": "0\t0",
                "git shortlog -sn --all": "42\tJohn Doe\n15\tJane Smith",
            }
            cmd_str = " ".join(cmd)
            return mapping.get(cmd_str, "")

        mock_run.side_effect = run_side_effect

        # Create .gitignore and .git/hooks for passing checks
        (tmp_path / ".gitignore").write_text(
            "# Dependencies\nnode_modules/\n.venv/\n__pycache__/\n"
            "# Environment\n.env\n.env.*\n"
            "# Keys\n*.key\n*.pem\n"
            "# OS\n.DS_Store\n"
            "# IDE\n.vscode/\n.idea/\n"
        )
        hooks = tmp_path / ".git" / "hooks"
        hooks.mkdir(parents=True)
        (hooks / "pre-commit").write_text("#!/bin/sh")
        (hooks / "pre-commit").chmod(0o755)
        chegi = tmp_path / ".chegi"
        chegi.mkdir()
        (chegi / "config.json").write_text("{}")
        (chegi / "guard-rules.json").write_text("{}")
        (chegi / ".chegiignore").write_text("")

        service = DoctorService(tmp_path)
        report = service.run()

        assert isinstance(report, DoctorReport)
        assert report.total > 0
        assert report.pass_count > 0

    def test_run_non_repo_directory(self, tmp_path: Path) -> None:
        """Test that run() works on a non-git directory with SKIP for git-dependent checks."""
        service = DoctorService(tmp_path)
        report = service.run()

        assert isinstance(report, DoctorReport)
        assert report.total > 0
        # Some checks should be SKIP (git-dependent ones)
        skips = [r for r in report.results if r.status == CheckStatus.SKIP]
        assert (
            len(skips) >= 5
        )  # staged, env, history, commits, branches, remote, contributors, sync
