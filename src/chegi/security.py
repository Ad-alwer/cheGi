import fnmatch
import subprocess
from pathlib import Path
from typing import List

from chegi.config import DEFAULT_SENSITIVE_PATTERNS


class SecurityGuard:
    """Handles security checks for Git operations to prevent accidental commits of sensitive data.

    This class provides static methods to scan files currently staged in Git and 
    compare them against known sensitive file patterns (e.g., .env, private keys).
    """

    @staticmethod
    def get_staged_files() -> List[str]:
        """Retrieves a list of currently staged files in the Git repository.

        Executes the `git diff --name-only --cached` command to fetch the paths 
        of files that are staged and ready to be committed.

        Returns:
            List[str]: A list of file paths that are staged for commit. Returns an 
            empty list if the directory is not a git repository or if git is not installed.
        """
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", "--cached"],
                capture_output=True,
                text=True,
                check=True
            )
            return [line.strip() for line in result.stdout.split('\n') if line.strip()]
        except subprocess.CalledProcessError:
            return []
        except FileNotFoundError:
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
    def unstage_files(files_to_unstage: List[str]) -> bool:
        """Unstages the specified files using git rm --cached.

        Args:
            files_to_unstage (List[str]): A list of file paths to unstage.

        Returns:
            bool: True if successfully unstaged, False otherwise.
        """
        if not files_to_unstage:
            return True
            
        try:
            subprocess.run(
                ["git", "rm", "--cached"] + files_to_unstage,
                capture_output=True,
                check=True
            )
            return True
        except subprocess.CalledProcessError:
            return False

