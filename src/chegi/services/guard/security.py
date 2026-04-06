import fnmatch
import subprocess
from pathlib import Path
from typing import List, Optional

from chegi.config import DEFAULT_SENSITIVE_PATTERNS
from chegi.services.guard.models import GuardScanResult


class SecurityGuard:
    """Handles security checks for Git operations to prevent accidental commits of sensitive data."""

    @staticmethod
    def get_staged_files(repo_path: Optional[Path] = None) -> List[str]:
        """Retrieves a list of currently staged files in a Git repository.

        Args:
            repo_path (Optional[Path]): The path to the repository. Defaults to current working directory.

        Returns:
            List[str]: A list of file paths staged for commit. Returns an empty list on failure.
        """
        cwd = repo_path if repo_path else Path.cwd()
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", "--cached"],
                cwd=cwd,
                capture_output=True,
                text=True,
                check=True,
            )
            return [line.strip() for line in result.stdout.split("\n") if line.strip()]
        except (subprocess.CalledProcessError, FileNotFoundError):
            return []

    @staticmethod
    def find_sensitive_files(files_to_check: List[str]) -> List[str]:
        """Checks a list of file paths against known sensitive file patterns.

        Args:
            files_to_check (List[str]): A list of file paths to scan.

        Returns:
            List[str]: A list of file paths matching any sensitive pattern.
        """
        detected_files = []
        for file_path in files_to_check:
            file_name = Path(file_path).name
            for pattern in DEFAULT_SENSITIVE_PATTERNS:
                if fnmatch.fnmatch(file_name.lower(), pattern.lower()):
                    detected_files.append(file_path)
                    break

        return detected_files

    @staticmethod
    def unstage_files(files_to_unstage: List[str], repo_path: Optional[Path] = None) -> bool:
        """Unstages the specified files using git rm --cached.

        Args:
            files_to_unstage (List[str]): Paths of files to unstage.
            repo_path (Optional[Path]): The path to the repository. Defaults to current working directory.

        Returns:
            bool: True if unstaged successfully or if list is empty, False otherwise.
        """
        if not files_to_unstage:
            return True

        cwd = repo_path if repo_path else Path.cwd()
        try:
            subprocess.run(
                ["git", "rm", "--cached"] + files_to_unstage,
                cwd=cwd,
                capture_output=True,
                check=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False

    @staticmethod
    def scan_repo(repo_path: Path) -> GuardScanResult:
        """Scans a repository for staged sensitive files.

        Args:
            repo_path (Path): The path to the repository to scan.

        Returns:
            GuardScanResult: An object containing safety status and detected files.
        """
        staged = SecurityGuard.get_staged_files(repo_path)
        if not staged:
            return GuardScanResult(is_safe=True, sensitive_files=[])

        sensitive = SecurityGuard.find_sensitive_files(staged)
        if not sensitive:
            return GuardScanResult(is_safe=True, sensitive_files=[])

        return GuardScanResult(is_safe=False, sensitive_files=sensitive)
