"""Service for scanning and cleaning Git history for sensitive files."""

import fnmatch
import shlex
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)

from chegi.config import DEFAULT_SENSITIVE_PATTERNS
from chegi.services.git.client import GitClient
from chegi.services.git.exceptions import GitCommandError
from chegi.services.guard.exceptions import HistoryScanError
from chegi.services.guard.models import HistoryFinding, HistoryScanResult
from chegi.services.init import InitService
from chegi.ui import console


class GuardHistoryService:
    """Scans Git history across all branches for sensitive files."""

    def __init__(
        self,
        repo_path: Optional[Path] = None,
        patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
    ) -> None:
        """Initializes the history scanner.

        Args:
            repo_path: Path to the repository. Defaults to CWD.
            patterns: Custom sensitive patterns. Uses defaults if None.
            exclude_patterns: Patterns to exclude from scanning.
        """
        self.repo_path = repo_path or Path.cwd()
        self.git = GitClient(self.repo_path)

        self.patterns: List[str] = list(patterns or DEFAULT_SENSITIVE_PATTERNS)
        self.exclude_patterns: List[str] = exclude_patterns or []

        self._load_project_patterns()

    def _load_project_patterns(self) -> None:
        """Loads custom patterns from .chegi/guard-rules.json if available."""
        project = InitService.load_project(self.repo_path)
        if project is None:
            return

        if project.config and project.config.guard_rules:
            self.patterns.extend(project.config.guard_rules)

        if project.config and project.config.guard_excludes:
            self.exclude_patterns.extend(project.config.guard_excludes)

        if project.guard_rules:
            if project.guard_rules.patterns:
                self.patterns.extend(project.guard_rules.patterns)
            if project.guard_rules.exclude_patterns:
                self.exclude_patterns.extend(project.guard_rules.exclude_patterns)

        if project.chegiignore:
            self.exclude_patterns.extend(project.chegiignore)

    def _should_exclude(self, file_path: str) -> bool:
        """Checks if a file path matches any exclude pattern.

        Args:
            file_path: The file path to check.

        Returns:
            True if the file should be excluded.
        """
        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(file_path.lower(), pattern.lower()):
                return True
            if fnmatch.fnmatch(Path(file_path).name.lower(), pattern.lower()):
                return True
        return False

    def _match_pattern(self, file_path: str) -> Optional[str]:
        """Checks a file path against sensitive patterns.

        Args:
            file_path: The file path to check.

        Returns:
            The matched pattern string, or None if no match.
        """
        file_name = Path(file_path).name
        for pattern in self.patterns:
            if fnmatch.fnmatch(file_name.lower(), pattern.lower()):
                return pattern
            if fnmatch.fnmatch(file_path.lower(), pattern.lower()):
                return pattern
        return None

    def _get_all_commits(self) -> List[str]:
        """Retrieves all commit SHAs across all branches.

        Returns:
            List of commit SHA strings.

        Raises:
            HistoryScanError: If git command fails.
        """
        try:
            output = self.git.run_command(["git", "rev-list", "--all"])
            return [h for h in output.split("\n") if h.strip()] if output else []
        except GitCommandError as e:
            raise HistoryScanError(f"Failed to list commits: {e}") from e

    def _get_commit_info(self, commit_hash: str) -> dict:
        """Retrieves metadata for a single commit.

        Args:
            commit_hash: The commit SHA.

        Returns:
            Dict with message, author, date.
        """
        try:
            info = self.git.run_command(
                [
                    "git",
                    "log",
                    "-1",
                    "--format=%H%n%an%n%ai%n%s",
                    commit_hash,
                ]
            )
            parts = info.split("\n")
            return {
                "hash": parts[0] if len(parts) > 0 else commit_hash,
                "author": parts[1] if len(parts) > 1 else "Unknown",
                "date": parts[2] if len(parts) > 2 else "",
                "message": parts[3] if len(parts) > 3 else "",
            }
        except GitCommandError:
            return {
                "hash": commit_hash,
                "author": "Unknown",
                "date": "",
                "message": "",
            }

    def _get_commit_files(self, commit_hash: str) -> List[str]:
        """Gets the list of files changed in a commit.

        Args:
            commit_hash: The commit SHA.

        Returns:
            List of file paths changed in the commit.
        """
        try:
            output = self.git.run_command(
                [
                    "git",
                    "diff-tree",
                    "--no-commit-id",
                    "-r",
                    "--name-only",
                    "-r",
                    commit_hash,
                ]
            )
            return [f for f in output.split("\n") if f.strip()] if output else []
        except GitCommandError:
            return []

    def scan(self) -> HistoryScanResult:
        """Scans the entire Git history for sensitive files.

        Returns:
            HistoryScanResult with all findings.
        """
        if not self.git.is_valid_repo():
            raise HistoryScanError(f"Not a valid Git repository: {self.repo_path}")

        console.print(f"[dim]🔍 Scanning Git history in '{self.repo_path}'...[/dim]")

        commits = self._get_all_commits()
        if not commits:
            console.print("[bold blue]No commits found in repository.[/bold blue]")
            return HistoryScanResult(
                total_commits_scanned=0,
                total_findings=0,
                repo_path=str(self.repo_path),
            )

        findings: List[HistoryFinding] = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("[cyan]Scanning commits...", total=len(commits))

            for commit_hash in commits:
                files = self._get_commit_files(commit_hash)
                info = self._get_commit_info(commit_hash)

                for file_path in files:
                    if self._should_exclude(file_path):
                        continue

                    matched = self._match_pattern(file_path)
                    if matched:
                        findings.append(
                            HistoryFinding(
                                commit_hash=info["hash"],
                                file_path=file_path,
                                pattern_matched=matched,
                                commit_message=info["message"],
                                author=info["author"],
                                date=info["date"],
                            )
                        )

                progress.advance(task)

        result = HistoryScanResult(
            findings=findings,
            total_commits_scanned=len(commits),
            total_findings=len(findings),
            repo_path=str(self.repo_path),
        )

        return result

    @staticmethod
    def generate_report(result: HistoryScanResult, output_path: Path) -> Path:
        """Generates an HTML report of the history scan findings.

        Args:
            result: The scan result to report on.
            output_path: Directory to write the report to.

        Returns:
            Path to the generated HTML file.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        findings_rows = ""
        for f in result.findings:
            findings_rows += f"""\
        <tr>
          <td><code>{f.commit_hash[:8]}</code></td>
          <td><code>{f.file_path}</code></td>
          <td><span class="pattern">{f.pattern_matched}</span></td>
          <td>{f.author}</td>
          <td>{f.date}</td>
          <td>{f.commit_message[:60]}</td>
        </tr>
"""

        report_path = output_path / "chegi-history-report.html"
        report_path.write_text(
            f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>cheGi History Scan Report</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace;
    background: #1a1a1a; color: #e0e0e0; padding: 2rem;
  }}
  h1 {{ color: #d4af37; font-size: 1.8rem; margin-bottom: 0.5rem; }}
  .subtitle {{ color: #888; margin-bottom: 2rem; }}
  .summary {{ display: flex; gap: 1rem; margin-bottom: 2rem; }}
  .card {{
    background: #2a2a2a; border-radius: 8px; padding: 1.2rem 1.5rem; flex: 1;
    border: 1px solid #333;
  }}
  .card .num {{ font-size: 2rem; font-weight: bold; color: #d4af37; }}
  .card .label {{ font-size: 0.85rem; color: #888; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ text-align: left; padding: 0.75rem 0.5rem; color: #d4af37; border-bottom: 2px solid #d4af37; }}
  td {{ padding: 0.6rem 0.5rem; border-bottom: 1px solid #333; font-size: 0.9rem; }}
  code {{ background: #333; padding: 0.1rem 0.4rem; border-radius: 3px; font-size: 0.85rem; }}
  .pattern {{ color: #ff6b6b; font-weight: bold; }}
  tr:hover {{ background: #2a2a2a; }}
  .footer {{ margin-top: 2rem; color: #555; font-size: 0.8rem; text-align: center; }}
  .safe {{ color: #4caf50; font-size: 1.5rem; text-align: center; padding: 3rem; }}
</style>
</head>
<body>
  <h1>🛡️ cheGi History Scan Report</h1>
  <p class="subtitle">Generated: {timestamp} | Repository: {result.repo_path}</p>

  <div class="summary">
    <div class="card">
      <div class="num">{result.total_commits_scanned}</div>
      <div class="label">Commits Scanned</div>
    </div>
    <div class="card">
      <div class="num">{result.total_findings}</div>
      <div class="label">Secrets Found</div>
    </div>
  </div>
""",
            encoding="utf-8",
        )

        if not result.findings:
            report_path.write_text(
                f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>cheGi History Scan Report</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace;
    background: #1a1a1a; color: #e0e0e0; padding: 2rem;
  }}
  h1 {{ color: #d4af37; font-size: 1.8rem; margin-bottom: 0.5rem; }}
  .subtitle {{ color: #888; margin-bottom: 2rem; }}
  .card {{
    background: #2a2a2a; border-radius: 8px; padding: 1.2rem 1.5rem;
    border: 1px solid #333; display: inline-block;
  }}
  .card .num {{ font-size: 2rem; font-weight: bold; color: #d4af37; }}
  .card .label {{ font-size: 0.85rem; color: #888; }}
  .safe {{ color: #4caf50; font-size: 1.5rem; text-align: center; padding: 3rem; }}
  .footer {{ margin-top: 2rem; color: #555; font-size: 0.8rem; text-align: center; }}
</style>
</head>
<body>
  <h1>🛡️ cheGi History Scan Report</h1>
  <p class="subtitle">Generated: {timestamp} | Repository: {result.repo_path}</p>
  <div class="safe">✅ No secrets found in Git history.</div>
  <div class="summary">
    <div class="card">
      <div class="num">{result.total_commits_scanned}</div>
      <div class="label">Commits Scanned</div>
    </div>
  </div>
  <div class="footer">cheGi v0.4.0 "The Guardian"</div>
</body>
</html>""",
                encoding="utf-8",
            )
            return report_path

        report_path.write_text(
            f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>cheGi History Scan Report</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace;
    background: #1a1a1a; color: #e0e0e0; padding: 2rem;
  }}
  h1 {{ color: #d4af37; font-size: 1.8rem; margin-bottom: 0.5rem; }}
  .subtitle {{ color: #888; margin-bottom: 2rem; }}
  .summary {{ display: flex; gap: 1rem; margin-bottom: 2rem; }}
  .card {{
    background: #2a2a2a; border-radius: 8px; padding: 1.2rem 1.5rem; flex: 1;
    border: 1px solid #333;
  }}
  .card .num {{ font-size: 2rem; font-weight: bold; color: #d4af37; }}
  .card .label {{ font-size: 0.85rem; color: #888; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ text-align: left; padding: 0.75rem 0.5rem; color: #d4af37; border-bottom: 2px solid #d4af37; }}
  td {{ padding: 0.6rem 0.5rem; border-bottom: 1px solid #333; font-size: 0.9rem; }}
  code {{ background: #333; padding: 0.1rem 0.4rem; border-radius: 3px; font-size: 0.85rem; }}
  .pattern {{ color: #ff6b6b; font-weight: bold; }}
  tr:hover {{ background: #2a2a2a; }}
  .footer {{ margin-top: 2rem; color: #555; font-size: 0.8rem; text-align: center; }}
</style>
</head>
<body>
  <h1>🛡️ cheGi History Scan Report</h1>
  <p class="subtitle">Generated: {timestamp} | Repository: {result.repo_path}</p>

  <div class="summary">
    <div class="card">
      <div class="num">{result.total_commits_scanned}</div>
      <div class="label">Commits Scanned</div>
    </div>
    <div class="card">
      <div class="num">{result.total_findings}</div>
      <div class="label">Secrets Found</div>
    </div>
  </div>

  <table>
    <thead>
      <tr>
        <th>Commit</th>
        <th>File</th>
        <th>Pattern</th>
        <th>Author</th>
        <th>Date</th>
        <th>Message</th>
      </tr>
    </thead>
    <tbody>
{findings_rows}
    </tbody>
  </table>

  <div class="footer">cheGi v0.4.0 "The Guardian"</div>
</body>
</html>""",
            encoding="utf-8",
        )
        return report_path

    @staticmethod
    def print_findings(result: HistoryScanResult) -> None:
        """Prints a summary of findings to the console.

        Args:
            result: The scan result to display.
        """
        if not result.findings:
            console.print(
                "\n[bold green]✅ No secrets found in Git history.[/bold green]"
            )
            return

        console.print(
            f"\n[bold red]⚠️  Found {result.total_findings} secrets"
            f" across {result.total_commits_scanned} commits![/bold red]\n"
        )
        for f in result.findings:
            short_hash = f.commit_hash[:8]
            console.print(
                f"  [red]●[/red] [yellow]{short_hash}[/yellow] "
                f"[dim]{f.date}[/dim] "
                f"[cyan]{f.file_path}[/cyan] "
                f"[red]({f.pattern_matched})[/red]"
            )

        console.print(
            "\n[dim]Run [bold]chegi guard history --fix[/bold] to remove these files from history.[/dim]"
        )

    def remove_file_from_history(self, file_path: str) -> bool:
        """Removes a file from all commits using git filter-branch.

        Args:
            file_path: The file path to remove from history.

        Returns:
            True if successful, False otherwise.
        """
        env = {
            "GIT_PAGER": "cat",
            "GIT_TERMINAL_PROMPT": "0",
        }

        cmd = [
            "git",
            "filter-branch",
            "--force",
            "--index-filter",
            f"git rm --cached --ignore-unmatch {shlex.quote(file_path)}",
            "--prune-empty",
            "--tag-name-filter",
            "cat",
            "--",
            "--all",
        ]

        try:
            self.git.run_command(cmd, env=env)
            return True
        except GitCommandError:
            return False
