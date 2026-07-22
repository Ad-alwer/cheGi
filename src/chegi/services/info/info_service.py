"""Service for collecting project status information."""

from pathlib import Path
from typing import List, Optional

from chegi.services.git import GitClient
from chegi.services.git.exceptions import GitCommandError
from chegi.services.guard import SecurityGuard
from chegi.services.hooks import HooksService, HookType
from chegi.services.info.models import InfoReport, LastCommit


class InfoService:
    """Collects comprehensive project status information."""

    def __init__(self, path: Optional[Path] = None) -> None:
        """Initializes the service with an optional target path.

        Args:
            path: The project path. Defaults to current working directory.
        """
        self.path = (path or Path.cwd()).resolve()
        self.git = GitClient(self.path)

    def collect(self) -> InfoReport:
        """Collects all available status information.

        Each field is fetched independently so that partial failures
        do not crash the entire command.

        Returns:
            An InfoReport with all collected data.
        """
        report = InfoReport(path=self.path, is_git_repo=False)

        if not self.git.is_valid_repo():
            report.errors["git"] = "Not a git repository"
            return report

        report.is_git_repo = True

        self._collect_git_info(report)
        self._collect_changes(report)
        self._collect_commit_info(report)
        self._collect_security_info(report)
        self._collect_project_info(report)

        return report

    def _safe_run(self, cmd: List[str], check: bool = True) -> str:
        """Runs a git command safely, returning empty string on failure.

        Args:
            cmd: The git command list.
            check: Whether to raise on non-zero exit.

        Returns:
            The command output, or empty string on failure.
        """
        try:
            return self.git.run_command(cmd, check=check)
        except GitCommandError:
            return ""

    def _collect_git_info(self, report: InfoReport) -> None:
        """Collects branch, remote, and sync information."""
        branch = self._safe_run(["git", "branch", "--show-current"])
        if branch:
            report.branch = branch

        remotes_output = self._safe_run(["git", "remote"])
        if remotes_output:
            remotes = remotes_output.splitlines()
            if remotes:
                report.remote_name = remotes[0]
                url = self._safe_run(["git", "remote", "get-url", remotes[0]])
                if url:
                    report.remote_url = url

        rev_list = self._safe_run(
            ["git", "rev-list", "--left-right", "--count", "HEAD...@{u}"],
            check=False,
        )
        if rev_list:
            parts = rev_list.split()
            if len(parts) == 2:
                report.ahead = int(parts[0])
                report.behind = int(parts[1])

    def _collect_changes(self, report: InfoReport) -> None:
        """Collects staged, modified, untracked, and stash counts."""
        output = self._safe_run(["git", "status", "--porcelain"])
        if output:
            for line in output.splitlines():
                if not line.strip():
                    continue
                if line.startswith("??"):
                    report.untracked += 1
                elif line.startswith(" "):
                    report.modified += 1
                else:
                    report.staged += 1

        stash_output = self._safe_run(["git", "stash", "list"])
        if stash_output:
            report.stash_count = len(
                [ln for ln in stash_output.splitlines() if ln.strip()]
            )

    def _collect_commit_info(self, report: InfoReport) -> None:
        """Collects last commit, contributors, and tag information."""
        log_output = self._safe_run(
            [
                "git",
                "log",
                "-1",
                "--format=%h%n%an%n%ar%n%s",
            ]
        )
        if log_output:
            parts = log_output.split("\n", 3)
            if len(parts) >= 3:
                report.last_commit = LastCommit(
                    hash=parts[0],
                    author=parts[1],
                    date=parts[2],
                    message=parts[3] if len(parts) > 3 else "",
                )

        shortlog = self._safe_run(["git", "shortlog", "-sn", "HEAD"], check=False)
        if shortlog:
            report.contributor_count = len(
                [ln for ln in shortlog.splitlines() if ln.strip()]
            )

        tag_output = self._safe_run(
            ["git", "describe", "--tags", "--abbrev=0"], check=False
        )
        if tag_output:
            report.latest_tag = tag_output.strip()
            since = self._safe_run(
                [
                    "git",
                    "rev-list",
                    "--count",
                    f"{report.latest_tag}..HEAD",
                ],
                check=False,
            )
            if since:
                try:
                    report.commits_since_tag = int(since.strip())
                except ValueError:
                    pass

        identity_set = True
        name = self._safe_run(["git", "config", "user.name"], check=False)
        email = self._safe_run(["git", "config", "user.email"], check=False)
        if not name or not email:
            identity_set = False
        report.git_identity_set = identity_set

    def _collect_security_info(self, report: InfoReport) -> None:
        """Collects guard scan and hooks status."""
        try:
            result = SecurityGuard.scan_repo(self.path)
            report.has_sensitive_files = not result.is_safe
            report.sensitive_file_count = len(result.sensitive_files)
        except Exception:
            report.errors["guard"] = "Guard scan failed"

        try:
            hook_service = HooksService(self.path)
            info = hook_service.is_installed(HookType.PRE_COMMIT)
            report.has_hooks = info.installed
        except Exception:
            report.errors["hooks"] = "Hook check failed"

    def _collect_project_info(self, report: InfoReport) -> None:
        """Collects .chegi/ directory status."""
        try:
            chegi_dir = self.path / ".chegi"
            report.has_chegi_dir = chegi_dir.is_dir()
        except Exception:
            report.errors["chegi"] = ".chegi/ check failed"

    def to_json(self, report: InfoReport) -> dict:
        """Converts an InfoReport to a JSON-serializable dict.

        Args:
            report: The report to convert.

        Returns:
            A dict suitable for JSON serialization.
        """
        data = {
            "path": str(report.path),
            "is_git_repo": report.is_git_repo,
        }

        if report.is_git_repo:
            data.update(
                {
                    "branch": report.branch,
                    "remote": report.remote_name,
                    "remote_url": report.remote_url,
                    "ahead": report.ahead,
                    "behind": report.behind,
                    "changes": {
                        "staged": report.staged,
                        "modified": report.modified,
                        "untracked": report.untracked,
                    },
                    "stash_count": report.stash_count,
                    "contributor_count": report.contributor_count,
                    "has_sensitive_files": report.has_sensitive_files,
                    "sensitive_file_count": report.sensitive_file_count,
                    "has_hooks": report.has_hooks,
                    "has_chegi_dir": report.has_chegi_dir,
                    "git_identity_set": report.git_identity_set,
                    "latest_tag": report.latest_tag,
                    "commits_since_tag": report.commits_since_tag,
                }
            )

            if report.last_commit:
                data["last_commit"] = {
                    "hash": report.last_commit.hash,
                    "message": report.last_commit.message,
                    "author": report.last_commit.author,
                    "date": report.last_commit.date,
                }

            if report.errors:
                data["errors"] = report.errors

        return data

    def to_short(self, report: InfoReport) -> str:
        """Returns a one-line summary string.

        Args:
            report: The report to summarize.

        Returns:
            A concise one-liner.
        """
        if not report.is_git_repo:
            return f"Not a git repository: {report.path}"

        parts = []
        parts.append(report.branch or "?")

        if report.remote_name:
            if report.ahead > 0 or report.behind > 0:
                sync = ""
                if report.ahead > 0:
                    sync += f"\u2191{report.ahead}"
                if report.behind > 0:
                    sync += f"\u2193{report.behind}"
                parts.append(sync)

        change_count = report.staged + report.modified + report.untracked
        if change_count > 0:
            parts.append(f"{change_count} changed")

        if report.has_sensitive_files:
            parts.append("\u2716 sensitive")
        else:
            parts.append("\u2713 clean")

        return " \u00b7 ".join(parts)
