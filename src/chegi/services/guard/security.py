import fnmatch
import os
import subprocess
from pathlib import Path
from typing import List, Optional, Set, Tuple

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
    def get_unstaged_files(repo_path: Optional[Path] = None) -> List[str]:
        """Retrieves a list of unstaged (modified but not staged) files.

        Args:
            repo_path (Optional[Path]): The path to the repository. Defaults to current working directory.

        Returns:
            List[str]: A list of file paths modified but not staged.
        """
        cwd = repo_path if repo_path else Path.cwd()
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only"],
                cwd=cwd,
                capture_output=True,
                text=True,
                check=True,
            )
            return [line.strip() for line in result.stdout.split("\n") if line.strip()]
        except (subprocess.CalledProcessError, FileNotFoundError):
            return []

    @staticmethod
    def find_sensitive_files(
        files_to_check: List[str],
        extra_patterns: Optional[Set[str]] = None,
    ) -> List[str]:
        """Checks a list of file paths against known sensitive file patterns.

        Args:
            files_to_check: A list of file paths to scan.
            extra_patterns: Additional patterns from project config (optional).

        Returns:
            A list of file paths matching any sensitive pattern.
        """
        patterns: tuple[str, ...] = DEFAULT_SENSITIVE_PATTERNS
        if extra_patterns:
            patterns = tuple(sorted(set(DEFAULT_SENSITIVE_PATTERNS) | extra_patterns))

        detected_files = []
        for file_path in files_to_check:
            file_name = Path(file_path).name
            for pattern in patterns:
                if fnmatch.fnmatch(file_name.lower(), pattern.lower()):
                    detected_files.append(file_path)
                    break

        return detected_files

    @staticmethod
    def unstage_files(
        files_to_unstage: List[str], repo_path: Optional[Path] = None
    ) -> bool:
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
    def scan_repo(
        repo_path: Path,
        extra_patterns: Optional[Set[str]] = None,
    ) -> GuardScanResult:
        """Scans a repository for staged sensitive files.

        Args:
            repo_path: The path to the repository to scan.
            extra_patterns: Additional patterns from project config (optional).

        Returns:
            GuardScanResult with safety status and detected files.
        """
        staged = SecurityGuard.get_staged_files(repo_path)
        if not staged:
            return GuardScanResult(is_safe=True, sensitive_files=[])

        sensitive = SecurityGuard.find_sensitive_files(staged, extra_patterns)
        if not sensitive:
            return GuardScanResult(is_safe=True, sensitive_files=[])

        return GuardScanResult(is_safe=False, sensitive_files=sensitive)

    @staticmethod
    def scan_strict(
        repo_path: Optional[Path] = None,
        extra_patterns: Optional[Set[str]] = None,
    ) -> Tuple[GuardScanResult, GuardScanResult]:
        """Scans both staged and unstaged files for sensitive content.

        Args:
            repo_path: Path to the repository. Defaults to cwd.
            extra_patterns: Additional patterns from project config (optional).

        Returns:
            Tuple of (staged_result, unstaged_result).
        """
        cwd = repo_path if repo_path else Path.cwd()
        staged = SecurityGuard.get_staged_files(cwd)
        unstaged = SecurityGuard.get_unstaged_files(cwd)

        staged_sensitive = (
            SecurityGuard.find_sensitive_files(staged, extra_patterns) if staged else []
        )
        unstaged_sensitive = (
            SecurityGuard.find_sensitive_files(unstaged, extra_patterns)
            if unstaged
            else []
        )

        staged_result = GuardScanResult(
            is_safe=len(staged_sensitive) == 0,
            sensitive_files=staged_sensitive,
        )
        unstaged_result = GuardScanResult(
            is_safe=len(unstaged_sensitive) == 0,
            sensitive_files=unstaged_sensitive,
        )
        return staged_result, unstaged_result

    @staticmethod
    def scan_directory(
        path: Path,
        extra_patterns: Optional[Set[str]] = None,
    ) -> GuardScanResult:
        """Recursively scans a directory tree for sensitive files.

        Args:
            path: The directory path to scan.
            extra_patterns: Additional patterns from project config (optional).

        Returns:
            GuardScanResult with all sensitive files found.
        """
        if not path.exists():
            return GuardScanResult(is_safe=True, sensitive_files=[])

        sensitive: List[str] = []
        for root, dirs, files in os.walk(str(path)):
            dirs[:] = [d for d in dirs if d != ".git"]
            for file in files:
                filepath = os.path.join(root, file)
                detected = SecurityGuard.find_sensitive_files(
                    [filepath], extra_patterns
                )
                if detected:
                    sensitive.extend(detected)

        return GuardScanResult(
            is_safe=len(sensitive) == 0,
            sensitive_files=sensitive,
        )
