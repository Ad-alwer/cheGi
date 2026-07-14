"""Service for comprehensive project health checks."""

import os
from pathlib import Path
from typing import Optional

from chegi.services.doctor.constants import (
    CHEGI_DIR_NAME,
    GITIGNORE_FILENAME,
    KEY_GITIGNORE_PATTERNS,
    PRE_COMMIT_HOOK_PATH,
)
from chegi.services.doctor.models import (
    CheckCategory,
    CheckResult,
    CheckStatus,
    DoctorReport,
)
from chegi.services.git.client import GitClient
from chegi.services.git.exceptions import GitCommandError, GitNotInstalledError
from chegi.services.guard.history import GuardHistoryService
from chegi.services.guard.security import SecurityGuard


class DoctorService:
    """Performs comprehensive health checks on a Git project.

    Checks cover three categories:
    - Health: Git installation, identity, .gitignore, .chegi/ config
    - Security: Staged sensitive files, .env tracked, history secrets, hooks active
    - Stats: Commits, branches, remote, contributors, remote sync
    """

    def __init__(self, path: Optional[Path] = None):
        """Initialize the doctor service.

        Args:
            path: Path to the project to check. Defaults to current directory.
        """
        self.path = (path or Path.cwd()).resolve()
        self.git = GitClient(self.path)
        self.is_git_repo = False

    def run(self) -> DoctorReport:
        """Runs all health checks and returns a report.

        Returns:
            DoctorReport with all check results.
        """
        report = DoctorReport(repo_path=str(self.path))

        try:
            self.is_git_repo = self.git.is_valid_repo()
        except GitNotInstalledError:
            pass

        report.results.extend(self._health_checks())
        report.results.extend(self._security_checks())
        report.results.extend(self._stats_checks())

        return report

    def _health_checks(self) -> list:
        """Runs health-related checks.

        Returns:
            List of CheckResult.
        """
        results = []

        # 1. Git installed
        results.append(self._check_git_installed())

        # 2. Git identity
        results.append(self._check_git_identity())

        # 3. .gitignore exists
        results.append(self._check_gitignore())

        # 4. .chegi/ configured
        results.append(self._check_chegi())

        return results

    def _security_checks(self) -> list:
        """Runs security-related checks.

        Returns:
            List of CheckResult.
        """
        results = []

        # 1. Sensitive files in staging
        results.append(self._check_staged_sensitive())

        # 2. .env tracked by Git
        results.append(self._check_env_tracked())

        # 3. Secrets in Git history
        results.append(self._check_history_secrets())

        # 4. Pre-commit hook active
        results.append(self._check_pre_commit_hook())

        return results

    def _stats_checks(self) -> list:
        """Runs statistics checks.

        Returns:
            List of CheckResult.
        """
        results = []

        # 1. Total commits
        results.append(self._check_commits())

        # 2. Branches
        results.append(self._check_branches())

        # 3. Remote status
        results.append(self._check_remote())

        # 4. Contributors
        results.append(self._check_contributors())

        # 5. Remote sync status
        results.append(self._check_remote_sync())

        return results

    # --- Individual checks ---

    def _check_git_installed(self) -> CheckResult:
        """Checks if Git is installed."""
        try:
            self.git.check_git_installation()
            return CheckResult(
                name="Git Installed",
                category=CheckCategory.HEALTH,
                status=CheckStatus.PASS,
                message="Git is installed and accessible.",
            )
        except GitNotInstalledError as e:
            return CheckResult(
                name="Git Installed",
                category=CheckCategory.HEALTH,
                status=CheckStatus.FAIL,
                message=str(e),
                suggestion="Install Git from https://git-scm.com/downloads",
            )

    def _check_git_identity(self) -> CheckResult:
        """Checks if Git user.name and user.email are set."""
        try:
            name = self.git.run_command(
                ["git", "config", "--global", "user.name"], check=False
            )
            email = self.git.run_command(
                ["git", "config", "--global", "user.email"], check=False
            )
        except GitNotInstalledError:
            return CheckResult(
                name="Git Identity",
                category=CheckCategory.HEALTH,
                status=CheckStatus.SKIP,
                message="Cannot check identity — Git not installed.",
            )

        if not name and not email:
            return CheckResult(
                name="Git Identity",
                category=CheckCategory.HEALTH,
                status=CheckStatus.FAIL,
                message="user.name and user.email are not set.",
                suggestion='Run: git config --global user.name "Your Name" && git config --global user.email "you@example.com"',
            )
        if not name:
            return CheckResult(
                name="Git Identity",
                category=CheckCategory.HEALTH,
                status=CheckStatus.FAIL,
                message="user.name is not set.",
                suggestion='Run: git config --global user.name "Your Name"',
            )
        if not email:
            return CheckResult(
                name="Git Identity",
                category=CheckCategory.HEALTH,
                status=CheckStatus.FAIL,
                message="user.email is not set.",
                suggestion='Run: git config --global user.email "you@example.com"',
            )

        return CheckResult(
            name="Git Identity",
            category=CheckCategory.HEALTH,
            status=CheckStatus.PASS,
            message=f"user.name: {name}, user.email: {email}",
        )

    def _check_gitignore(self) -> CheckResult:
        """Checks if .gitignore exists with key patterns."""
        gitignore_path = self.path / GITIGNORE_FILENAME

        if not gitignore_path.is_file():
            suggestion = (
                "Run: touch .gitignore and add common patterns.\n"
                "  Or use chegi gitignore to generate one interactively."
            )
            return CheckResult(
                name=".gitignore",
                category=CheckCategory.HEALTH,
                status=CheckStatus.FAIL,
                message="No .gitignore file found.",
                suggestion=suggestion,
            )

        content = gitignore_path.read_text().lower()
        missing = [p for p in KEY_GITIGNORE_PATTERNS if p.lower() not in content]

        if missing:
            return CheckResult(
                name=".gitignore",
                category=CheckCategory.HEALTH,
                status=CheckStatus.WARN,
                message=f"Missing {len(missing)} common patterns: {', '.join(missing[:5])}",
                suggestion="Run: chegi gitignore to add missing patterns.",
            )

        return CheckResult(
            name=".gitignore",
            category=CheckCategory.HEALTH,
            status=CheckStatus.PASS,
            message=".gitignore exists with key patterns.",
        )

    def _check_chegi(self) -> CheckResult:
        """Checks if .chegi/ directory is configured."""
        chegi_dir = self.path / CHEGI_DIR_NAME

        if not chegi_dir.is_dir():
            return CheckResult(
                name=".chegi/ Config",
                category=CheckCategory.HEALTH,
                status=CheckStatus.WARN,
                message="No .chegi/ project directory found.",
                suggestion="Run: chegi init to create .chegi/ with default config.",
            )

        # Check that key files exist
        config_file = chegi_dir / "config.json"
        guard_file = chegi_dir / "guard-rules.json"
        ignore_file = chegi_dir / ".chegiignore"

        missing = []
        if not config_file.is_file():
            missing.append("config.json")
        if not guard_file.is_file():
            missing.append("guard-rules.json")
        if not ignore_file.is_file():
            missing.append(".chegiignore")

        if missing:
            return CheckResult(
                name=".chegi/ Config",
                category=CheckCategory.HEALTH,
                status=CheckStatus.WARN,
                message=f".chegi/ exists but missing: {', '.join(missing)}",
                suggestion="Run: chegi init --force to regenerate missing files.",
            )

        return CheckResult(
            name=".chegi/ Config",
            category=CheckCategory.HEALTH,
            status=CheckStatus.PASS,
            message=".chegi/ directory with all config files present.",
        )

    def _check_staged_sensitive(self) -> CheckResult:
        """Checks if there are sensitive files in staging."""
        if not self.is_git_repo:
            return CheckResult(
                name="Staged Sensitive Files",
                category=CheckCategory.SECURITY,
                status=CheckStatus.SKIP,
                message="Not a Git repository.",
            )

        result = SecurityGuard.scan_repo(self.path)

        if not result.is_safe:
            files_str = ", ".join(result.sensitive_files[:5])
            return CheckResult(
                name="Staged Sensitive Files",
                category=CheckCategory.SECURITY,
                status=CheckStatus.FAIL,
                message=f"{len(result.sensitive_files)} sensitive file(s) staged: {files_str}",
                suggestion="Run: chegi guard to review and unstage sensitive files.",
            )

        return CheckResult(
            name="Staged Sensitive Files",
            category=CheckCategory.SECURITY,
            status=CheckStatus.PASS,
            message="No sensitive files in staging.",
        )

    def _check_env_tracked(self) -> CheckResult:
        """Checks if .env files are tracked by Git."""
        if not self.is_git_repo:
            return CheckResult(
                name=".env Tracked",
                category=CheckCategory.SECURITY,
                status=CheckStatus.SKIP,
                message="Not a Git repository.",
            )

        try:
            tracked = self.git.run_command(
                ["git", "ls-files", ".env", ".env.*"], check=False
            )
        except (GitCommandError, GitNotInstalledError):
            return CheckResult(
                name=".env Tracked",
                category=CheckCategory.SECURITY,
                status=CheckStatus.SKIP,
                message="Could not check tracked files.",
            )

        if tracked.strip():
            return CheckResult(
                name=".env Tracked",
                category=CheckCategory.SECURITY,
                status=CheckStatus.FAIL,
                message=f"Found tracked .env files:\n{tracked.strip()}",
                suggestion="Run: git rm --cached <file> and add to .gitignore.",
            )

        return CheckResult(
            name=".env Tracked",
            category=CheckCategory.SECURITY,
            status=CheckStatus.PASS,
            message="No .env files tracked by Git.",
        )

    def _check_history_secrets(self) -> CheckResult:
        """Checks if secrets exist in Git history."""
        if not self.is_git_repo:
            return CheckResult(
                name="Secrets in History",
                category=CheckCategory.SECURITY,
                status=CheckStatus.SKIP,
                message="Not a Git repository.",
            )

        try:
            scanner = GuardHistoryService(repo_path=self.path)
            result = scanner.scan()
        except Exception:
            return CheckResult(
                name="Secrets in History",
                category=CheckCategory.SECURITY,
                status=CheckStatus.SKIP,
                message="Could not scan history (no commits yet?).",
            )

        if result.total_findings > 0:
            return CheckResult(
                name="Secrets in History",
                category=CheckCategory.SECURITY,
                status=CheckStatus.FAIL,
                message=f"{result.total_findings} secret(s) found in Git history across {result.total_commits_scanned} commits.",
                suggestion="Run: chegi guard history to review findings.",
            )

        return CheckResult(
            name="Secrets in History",
            category=CheckCategory.SECURITY,
            status=CheckStatus.PASS,
            message=f"No secrets found in history ({result.total_commits_scanned} commits scanned).",
        )

    def _check_pre_commit_hook(self) -> CheckResult:
        """Checks if a pre-commit hook is active."""
        if not self.is_git_repo:
            return CheckResult(
                name="Pre-commit Hook",
                category=CheckCategory.SECURITY,
                status=CheckStatus.SKIP,
                message="Not a Git repository.",
            )

        hook_path = self.path / PRE_COMMIT_HOOK_PATH

        if not hook_path.is_file():
            return CheckResult(
                name="Pre-commit Hook",
                category=CheckCategory.SECURITY,
                status=CheckStatus.WARN,
                message="No pre-commit hook installed.",
                suggestion="Consider setting up a pre-commit hook to auto-scan for secrets.",
            )

        # Check if it's executable
        is_exec = os.access(str(hook_path), os.X_OK)

        if not is_exec:
            return CheckResult(
                name="Pre-commit Hook",
                category=CheckCategory.SECURITY,
                status=CheckStatus.WARN,
                message="Pre-commit hook exists but is not executable.",
                suggestion="Run: chmod +x .git/hooks/pre-commit",
            )

        return CheckResult(
            name="Pre-commit Hook",
            category=CheckCategory.SECURITY,
            status=CheckStatus.PASS,
            message="Pre-commit hook is installed and executable.",
        )

    def _check_commits(self) -> CheckResult:
        """Counts total commits."""
        if not self.is_git_repo:
            return CheckResult(
                name="Total Commits",
                category=CheckCategory.STATS,
                status=CheckStatus.SKIP,
                message="Not a Git repository.",
            )

        try:
            count = self.git.run_command(
                ["git", "rev-list", "--count", "HEAD"], check=False
            )
        except (GitCommandError, GitNotInstalledError):
            return CheckResult(
                name="Total Commits",
                category=CheckCategory.STATS,
                status=CheckStatus.SKIP,
                message="Could not count commits (no commits yet?).",
            )

        if not count or count == "0":
            return CheckResult(
                name="Total Commits",
                category=CheckCategory.STATS,
                status=CheckStatus.WARN,
                message="No commits yet.",
                suggestion='Run: git add . && git commit -m "initial commit"',
            )

        return CheckResult(
            name="Total Commits",
            category=CheckCategory.STATS,
            status=CheckStatus.PASS,
            message=f"{count} commit(s) in history.",
        )

    def _check_branches(self) -> CheckResult:
        """Counts local branches."""
        if not self.is_git_repo:
            return CheckResult(
                name="Branches",
                category=CheckCategory.STATS,
                status=CheckStatus.SKIP,
                message="Not a Git repository.",
            )

        try:
            branches = self.git.run_command(["git", "branch", "--list"], check=False)
        except (GitCommandError, GitNotInstalledError):
            return CheckResult(
                name="Branches",
                category=CheckCategory.STATS,
                status=CheckStatus.SKIP,
                message="Could not list branches.",
            )

        branch_list = [
            b.strip().lstrip("* ") for b in branches.splitlines() if b.strip()
        ]
        count = len(branch_list)

        if count == 0:
            return CheckResult(
                name="Branches",
                category=CheckCategory.STATS,
                status=CheckStatus.WARN,
                message="No branches found.",
            )

        return CheckResult(
            name="Branches",
            category=CheckCategory.STATS,
            status=CheckStatus.PASS,
            message=f"{count} branch(es): {', '.join(branch_list[:5])}",
        )

    def _check_remote(self) -> CheckResult:
        """Checks remote configuration and sync status."""
        if not self.is_git_repo:
            return CheckResult(
                name="Remote Status",
                category=CheckCategory.STATS,
                status=CheckStatus.SKIP,
                message="Not a Git repository.",
            )

        try:
            remotes = self.git.run_command(["git", "remote"], check=False)
        except (GitCommandError, GitNotInstalledError):
            return CheckResult(
                name="Remote Status",
                category=CheckCategory.STATS,
                status=CheckStatus.SKIP,
                message="Could not check remotes.",
            )

        if not remotes.strip():
            return CheckResult(
                name="Remote Status",
                category=CheckCategory.STATS,
                status=CheckStatus.WARN,
                message="No remote configured.",
                suggestion="Run: git remote add origin <repository-url>",
            )

        remote_names = remotes.splitlines()
        return CheckResult(
            name="Remote Status",
            category=CheckCategory.STATS,
            status=CheckStatus.PASS,
            message=f"{len(remote_names)} remote(s): {', '.join(remote_names)}",
        )

    def _check_contributors(self) -> CheckResult:
        """Counts unique contributors."""
        if not self.is_git_repo:
            return CheckResult(
                name="Contributors",
                category=CheckCategory.STATS,
                status=CheckStatus.SKIP,
                message="Not a Git repository.",
            )

        try:
            authors = self.git.run_command(
                ["git", "shortlog", "-sn", "--all"], check=False
            )
        except (GitCommandError, GitNotInstalledError):
            return CheckResult(
                name="Contributors",
                category=CheckCategory.STATS,
                status=CheckStatus.SKIP,
                message="Could not count contributors.",
            )

        if not authors.strip():
            return CheckResult(
                name="Contributors",
                category=CheckCategory.STATS,
                status=CheckStatus.WARN,
                message="No contributors found (no commits yet?).",
            )

        lines = [ln.strip() for ln in authors.splitlines() if ln.strip()]
        count = len(lines)
        top = ""
        if lines:
            parts = lines[0].split("\t")
            top = f" (top: {parts[-1].strip()})" if len(parts) > 1 else ""

        return CheckResult(
            name="Contributors",
            category=CheckCategory.STATS,
            status=CheckStatus.PASS,
            message=f"{count} contributor(s){top}.",
        )

    def _check_remote_sync(self) -> CheckResult:
        """Checks ahead/behind status with remote."""
        if not self.is_git_repo:
            return CheckResult(
                name="Remote Sync",
                category=CheckCategory.STATS,
                status=CheckStatus.SKIP,
                message="Not a Git repository.",
            )

        try:
            branch = self.git.run_command(
                ["git", "branch", "--show-current"], check=False
            )
        except (GitCommandError, GitNotInstalledError):
            return CheckResult(
                name="Remote Sync",
                category=CheckCategory.STATS,
                status=CheckStatus.SKIP,
                message="Could not determine current branch.",
            )

        if not branch.strip():
            return CheckResult(
                name="Remote Sync",
                category=CheckCategory.STATS,
                status=CheckStatus.WARN,
                message="No commits yet (detached HEAD or empty repo).",
            )

        try:
            remotes = self.git.run_command(["git", "remote"], check=False)
        except (GitCommandError, GitNotInstalledError):
            return CheckResult(
                name="Remote Sync",
                category=CheckCategory.STATS,
                status=CheckStatus.SKIP,
                message="Could not check remotes.",
            )

        if not remotes.strip():
            return CheckResult(
                name="Remote Sync",
                category=CheckCategory.STATS,
                status=CheckStatus.SKIP,
                message="No remote configured.",
            )

        # Check upstream
        try:
            self.git.run_command(
                ["git", "rev-parse", "--abbrev-ref", "@{u}"], check=True
            )
        except GitCommandError:
            return CheckResult(
                name="Remote Sync",
                category=CheckCategory.STATS,
                status=CheckStatus.WARN,
                message=f"Branch '{branch}' has no upstream configured.",
                suggestion="Run: git push -u origin HEAD",
            )
        except GitNotInstalledError:
            return CheckResult(
                name="Remote Sync",
                category=CheckCategory.STATS,
                status=CheckStatus.SKIP,
                message="Git not installed.",
            )

        # Count ahead/behind
        try:
            rev_list = self.git.run_command(
                ["git", "rev-list", "--left-right", "--count", "HEAD...@{u}"],
                check=True,
            )
        except GitCommandError:
            return CheckResult(
                name="Remote Sync",
                category=CheckCategory.STATS,
                status=CheckStatus.WARN,
                message="Could not determine sync status.",
            )

        counts = rev_list.split()
        ahead = int(counts[0]) if len(counts) > 0 else 0
        behind = int(counts[1]) if len(counts) > 1 else 0

        if ahead > 0 and behind > 0:
            return CheckResult(
                name="Remote Sync",
                category=CheckCategory.STATS,
                status=CheckStatus.WARN,
                message=f"Diverged: {ahead} ahead, {behind} behind origin.",
                suggestion="Run: git pull --rebase && git push",
            )
        if ahead > 0:
            return CheckResult(
                name="Remote Sync",
                category=CheckCategory.STATS,
                status=CheckStatus.WARN,
                message=f"{ahead} commit(s) ahead of origin.",
                suggestion="Run: git push",
            )
        if behind > 0:
            return CheckResult(
                name="Remote Sync",
                category=CheckCategory.STATS,
                status=CheckStatus.WARN,
                message=f"{behind} commit(s) behind origin.",
                suggestion="Run: git pull --rebase",
            )

        return CheckResult(
            name="Remote Sync",
            category=CheckCategory.STATS,
            status=CheckStatus.PASS,
            message="Synced with origin.",
        )
