import fnmatch
import subprocess
from pathlib import Path
from typing import List, Optional

from chegi.config import DEFAULT_SENSITIVE_PATTERNS


class SecurityGuard:
    """Handles security checks for Git operations to prevent accidental commits of sensitive data.

    This class provides static methods to scan files currently staged in Git and 
    compare them against known sensitive file patterns (e.g., .env, private keys).
    """

    @staticmethod
    def get_staged_files(repo_path: Optional[Path] = None) -> List[str]:
        """Retrieves a list of currently staged files in a Git repository.

        Executes the `git diff --name-only --cached` command to fetch the paths 
        of files that are staged and ready to be committed.

        Args:
            repo_path (Optional[Path]): The path to the repository. If None, uses the current directory.

        Returns:
            List[str]: A list of file paths that are staged for commit. Returns an 
            empty list if the directory is not a git repository or if git is not installed.
        """
        cwd = repo_path if repo_path else Path.cwd()
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", "--cached"],
                cwd=cwd,
                capture_output=True,
                text=True,
                check=True
            )
            return [line.strip() for line in result.stdout.split('\n') if line.strip()]
        except (subprocess.CalledProcessError, FileNotFoundError):
            return []

    @staticmethod
    def find_sensitive_files(files_to_check: List[str]) -> List[str]:
        """Checks a list of file paths against known sensitive file patterns.

        Args:
            files_to_check (List[str]): A list of file paths to scan (typically staged files).

        Returns:
            List[str]: A list of file paths that match any of the sensitive patterns 
            defined in `DEFAULT_SENSITIVE_PATTERNS`.
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
            files_to_unstage (List[str]): A list of file paths to unstage.
            repo_path (Optional[Path]): The path to the repository. If None, uses the current directory.

        Returns:
            bool: True if successfully unstaged, False otherwise.
        """
        if not files_to_unstage:
            return True
            
        cwd = repo_path if repo_path else Path.cwd()
        try:
            subprocess.run(
                ["git", "rm", "--cached"] + files_to_unstage,
                cwd=cwd,
                capture_output=True,
                check=True
            )
            return True
        except subprocess.CalledProcessError:
            return False

    @staticmethod
    def scan_repo(repo_path: Path) -> str:
        """Scans a specific repository for staged sensitive files.

        Args:
            repo_path (Path): The path to the repository to scan.

        Returns:
            str: A formatted status string indicating the security status (e.g., Safe or amount of secrets).
        """
        staged = SecurityGuard.get_staged_files(repo_path)
        if not staged:
            return "[green]✅ Safe[/green]"
            
        sensitive = SecurityGuard.find_sensitive_files(staged)
        if not sensitive:
            return "[green]✅ Safe[/green]"
            
        count = len(sensitive)
        s = "s" if count > 1 else ""
        return f"[red]❌ {count} Staged Secret{s}[/red]"
