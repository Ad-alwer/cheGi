"""Service for preparing and executing secure Git commits."""

from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from chegi.config import ChegiConfig
from chegi.services.commit.constants import BRAND_SUFFIX
from chegi.services.commit.exceptions import CommitError, NoStagedFilesError
from chegi.services.commit.models import CommitContext, CommitStyle
from chegi.services.git.client import GitClient
from chegi.services.guard import GuardScanResult, SecurityGuard


class CommitService:
    """Handles commit preparation, security scanning, and execution.

    Attributes:
        repo_path (Path): The path to the Git repository.
    """

    def __init__(self, repo_path: Path) -> None:
        """Initializes the CommitService.

        Args:
            repo_path (Path): The local directory path of the git repository.
        """
        self.repo_path = repo_path
        self.git_client = GitClient(repo_path)

    def prepare_context(self) -> CommitContext:
        """Gather all information needed for the commit flow.

        Returns:
            CommitContext: Context with staged files, diff stat, scan result,
                and suggested messages.

        Raises:
            NoStagedFilesError: If there are no staged files.
            CommitError: If the repo is not valid.
        """
        if not self.git_client.is_valid_repo():
            raise CommitError("Not a valid Git repository.")

        staged_files = self._get_staged_files()
        if not staged_files:
            raise NoStagedFilesError(
                "No staged files found. Use 'git add' to stage files first."
            )

        diff_stat = self._get_diff_stat()
        name_status = self._get_diff_name_status()
        scan_result = self._scan_staged_files()
        suggested = self.suggest_messages(name_status)

        return CommitContext(
            staged_files=staged_files,
            diff_stat=diff_stat,
            name_status=name_status,
            is_safe=scan_result.is_safe,
            sensitive_files=scan_result.sensitive_files,
            suggested_messages=suggested,
        )

    def _get_staged_files(self) -> List[str]:
        """Retrieves the list of currently staged files.

        Returns:
            List[str]: File paths staged for commit.
        """
        result = self.git_client.run_command(["git", "diff", "--cached", "--name-only"])
        if not result:
            return []
        return [line.strip() for line in result.split("\n") if line.strip()]

    def _get_diff_stat(self) -> str:
        """Retrieves the diff stat summary of staged changes.

        Returns:
            str: The stat output showing insertions/deletions per file.
        """
        return self.git_client.run_command(["git", "diff", "--cached", "--stat"])

    def _get_diff_name_status(self) -> List[Tuple[str, str]]:
        """Retrieves the status of each staged file.

        Returns:
            List[Tuple[str, str]]: List of (status, file_path) tuples.
        """
        result = self.git_client.run_command(
            ["git", "diff", "--cached", "--name-status"]
        )
        if not result:
            return []
        entries: List[Tuple[str, str]] = []
        for line in result.split("\n"):
            line = line.strip()
            if line:
                parts = line.split("\t", 1)
                if len(parts) == 2:
                    entries.append((parts[0], parts[1]))
        return entries

    def _scan_staged_files(self) -> GuardScanResult:
        """Runs the security guard scan on staged files.

        Returns:
            GuardScanResult: The result of the security scan.
        """
        extra: Optional[Set[str]] = None
        try:
            cfg = ChegiConfig(str(self.repo_path))
            if cfg.sensitive_patterns:
                extra = cfg.sensitive_patterns
        except Exception:
            pass
        return SecurityGuard.scan_repo(self.repo_path, extra)

    def unstage_files(self, files: List[str]) -> bool:
        """Unstages the specified files.

        Args:
            files (List[str]): File paths to unstage.

        Returns:
            bool: True if successful, False otherwise.
        """
        return SecurityGuard.unstage_files(files, self.repo_path)

    def suggest_messages(self, name_status: List[Tuple[str, str]]) -> List[str]:
        """Generates suggested commit messages based on staged file changes.

        Analyzes file statuses, paths, and extensions to produce conventional
        commit message suggestions.

        Args:
            name_status (List[Tuple[str, str]]): List of (status, path) tuples.

        Returns:
            List[str]: Up to 3 suggested commit messages.
        """
        if not name_status:
            return []

        additions = sum(1 for s, _ in name_status if s == "A")
        modifications = sum(1 for s, _ in name_status if s == "M")
        deletions = sum(1 for s, _ in name_status if s == "D")

        all_paths = [p for _, p in name_status]

        scope = self._detect_scope(all_paths)
        is_test = any("test" in p.lower() or "spec" in p.lower() for p in all_paths)
        is_doc = any(
            p.endswith((".md", ".rst", ".txt")) or "/docs/" in p for p in all_paths
        )

        suggestions: List[str] = []

        if is_test:
            scope_part = f"({scope})" if scope else ""
            suggestions.append(f"test{scope_part}: add/update tests")
        elif is_doc:
            scope_part = f"({scope})" if scope else ""
            suggestions.append(f"docs{scope_part}: update documentation")
        elif additions > 0 and additions >= modifications:
            scope_part = f"({scope})" if scope else ""
            desc = self._describe_files([p for s, p in name_status if s == "A"])
            suggestions.append(f"feat{scope_part}: {desc}")
        elif modifications > 0:
            scope_part = f"({scope})" if scope else ""
            desc = self._describe_files([p for s, p in name_status if s == "M"])
            suggestions.append(f"fix{scope_part}: {desc}")
        elif deletions > 0:
            scope_part = f"({scope})" if scope else ""
            suggestions.append(f"refactor{scope_part}: remove unused code")

        change_parts = []
        if additions:
            change_parts.append(f"add {additions} file(s)")
        if modifications:
            change_parts.append(f"update {modifications} file(s)")
        if deletions:
            change_parts.append(f"delete {deletions} file(s)")
        if change_parts:
            suggestions.append(f"chore: {', '.join(change_parts)}")

        return suggestions[:3]

    def _detect_scope(self, paths: List[str]) -> Optional[str]:
        """Detects the most specific common directory path as scope.

        Finds the deepest directory segment shared by all file paths.

        Args:
            paths (List[str]): List of file paths.

        Returns:
            Optional[str]: The deepest common directory, or None.
        """
        scope_parts: List[Tuple[str, ...]] = []
        for p in paths:
            parts = Path(p).parts[:-1]
            if parts:
                scope_parts.append(parts)
        if not scope_parts:
            return None
        common = list(scope_parts[0])
        for parts in scope_parts[1:]:
            i = 0
            while i < len(common) and i < len(parts) and common[i] == parts[i]:
                i += 1
            common = common[:i]
        if common:
            return common[-1]
        return None

    def _describe_files(self, paths: List[str]) -> str:
        """Creates a short description from file paths.

        Extracts the most descriptive stem from the first file path.

        Args:
            paths (List[str]): List of file paths.

        Returns:
            str: A short human-readable description.
        """
        if not paths:
            return "update"
        name = Path(paths[0]).stem.replace("_", " ").replace("-", " ")
        words = name.split()[:4]
        return " ".join(words).lower() or "update"

    def execute_commit(self, message: str) -> str:
        """Executes git commit with the given message.

        Args:
            message (str): The commit message.

        Returns:
            str: The output of the git commit command.

        Raises:
            CommitError: If the commit fails.
        """
        try:
            return self.git_client.run_command(["git", "commit", "-m", message])
        except Exception as exc:
            raise CommitError(f"Commit failed: {exc}") from exc

    @staticmethod
    def build_message(style: CommitStyle, values: Dict[str, str]) -> str:
        """Builds a commit message string from a style and field values.

        Args:
            style (CommitStyle): The commit style to use.
            values (Dict[str, str]): Field values keyed by field name.

        Returns:
            str: The formatted commit message.
        """
        if style.name == "free":
            desc = values.get("description", "")
            return desc[0].upper() + desc[1:] if desc else ""

        type_ = values.get("type", "")
        scope = values.get("scope", "")
        desc = values.get("description", "")
        body = values.get("body", "")

        desc_words = desc.split()
        if desc_words:
            desc_words[0] = desc_words[0].capitalize()
        desc = " ".join(desc_words)

        if style.name == "conventional":
            subject = f"{type_}: {desc}"
        elif style.name == "conventional-scope":
            scope_part = f"({scope})" if scope else ""
            subject = f"{type_}{scope_part}: {desc}"
        elif style.name == "conventional-body":
            scope_part = f"({scope})" if scope else ""
            subject = f"{type_}{scope_part}: {desc}"
            if body:
                subject += f"\n\n{body}"
        elif style.name == "gitmoji":
            emoji = style.emojis.get(type_, "") if style.emojis else ""
            if emoji:
                subject = f"{emoji} {type_}: {desc}"
            else:
                subject = f"{type_}: {desc}"
        else:
            scope_part = f"({scope})" if scope else ""
            subject = f"{type_}{scope_part}: {desc}"

        return subject

    @staticmethod
    def apply_brand_suffix(message: str) -> str:
        """Appends the brand cheetah suffix to the subject line.

        Only adds if not already present. Never modifies the body.

        Args:
            message (str): The commit message.

        Returns:
            str: The commit message with brand suffix on the subject.
        """
        lines = message.split("\n")
        subject = lines[0]
        if not subject.rstrip().endswith(BRAND_SUFFIX):
            lines[0] = subject.rstrip() + BRAND_SUFFIX
        return "\n".join(lines)
