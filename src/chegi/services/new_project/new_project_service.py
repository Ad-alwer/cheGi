"""Service for scaffolding new Git projects."""

import datetime
import subprocess
from typing import List, Optional

from chegi.services.environment import EnvManager
from chegi.services.init import InitService
from chegi.services.new_project.constants import (
    AVAILABLE_LICENSES,
    GIT_USER_PLACEHOLDER,
    INITIAL_COMMIT_MESSAGE,
    LICENSE_TEMPLATES,
)
from chegi.services.new_project.exceptions import (
    GitInitError,
    ProjectAlreadyExistsError,
    ProjectCreationError,
)
from chegi.services.new_project.models import NewProjectConfig, NewProjectResult


class NewProjectService:
    """Creates a new Git project from scratch with scaffolding."""

    def __init__(self, config: NewProjectConfig):
        """Initialize the service with project configuration.

        Args:
            config: The project creation configuration.
        """
        self.config = config
        self.project_path = config.path / config.name

    def create(self) -> NewProjectResult:
        """Creates the full project scaffold.

        Returns:
            NewProjectResult with the result details.

        Raises:
            ProjectAlreadyExistsError: If the target directory exists.
            GitInitError: If git init fails.
            ProjectCreationError: If any creation step fails.
        """
        files_created: List[str] = []

        if self.project_path.exists():
            raise ProjectAlreadyExistsError(
                f"Directory '{self.project_path}' already exists. "
                "Choose a different project name or remove it first."
            )

        self.project_path.mkdir(parents=True)

        try:
            self._git_init()
            files_created.append(".git")

            if not self.config.skip_gitignore:
                self._create_gitignore()
                files_created.append(".gitignore")

            if not self.config.skip_chegi:
                self._create_chegi_dir()
                files_created.append(".chegi/")

            if not self.config.skip_readme:
                self._create_readme()
                files_created.append("README.md")

            if self.config.license_type:
                self._create_license()
                files_created.append("LICENSE")

            commit_hash = self._initial_commit()

            return NewProjectResult(
                project_path=self.project_path,
                files_created=files_created,
                commit_hash=commit_hash,
                is_successful=True,
            )

        except (GitInitError, ProjectCreationError):
            raise
        except Exception as e:
            raise ProjectCreationError(f"Failed to create project: {e}") from e

    def _git_init(self) -> None:
        """Initializes a Git repository in the project directory.

        Raises:
            GitInitError: If git init fails.
        """
        try:
            subprocess.run(
                ["git", "init"],
                cwd=str(self.project_path),
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            raise GitInitError(
                f"Failed to initialize Git repository: {e.stderr.strip()}"
            ) from e
        except FileNotFoundError as e:
            raise GitInitError("Git is not installed.") from e

    def _create_gitignore(self) -> None:
        """Generates .gitignore for the selected technologies.

        If technologies are not specified and not in non-interactive mode,
        they should be set before calling this method.
        """
        env_manager = EnvManager()
        if self.config.technologies:
            try:
                env_manager.generate_gitignore(
                    self.config.technologies, str(self.project_path)
                )
            except Exception as e:
                raise ProjectCreationError(f"Failed to generate .gitignore: {e}") from e
        else:
            # Create a minimal .gitignore
            gitignore_path = self.project_path / ".gitignore"
            gitignore_path.write_text(
                "# Dependencies\nnode_modules/\n.venv/\nvenv/\n\n"
                "# OS files\n.DS_Store\nThumbs.db\n\n"
                "# Environment\n.env\n.env.*\n\n"
                "# IDE\n.vscode/\n.idea/\n*.swp\n"
            )

    def _create_chegi_dir(self) -> None:
        """Creates .chegi/ project directory using InitService."""
        try:
            InitService.create_project_directory(self.project_path)
        except Exception as e:
            raise ProjectCreationError(
                f"Failed to create .chegi/ directory: {e}"
            ) from e

    def _create_readme(self) -> None:
        """Generates a README.md with project name and description."""
        readme_path = self.project_path / "README.md"
        name = self.config.name
        description = f"# {name}\n\n"
        description += (
            "Project generated with [cheGi](https://github.com/Ad-alwer/cheGi) 🐆\n\n"
        )
        description += "## Getting Started\n\n"
        description += "```bash\n"
        description += "git clone <your-repo-url>\n"
        description += f"cd {name}\n"
        description += "```\n"
        description += "\n## License\n\n"
        desc_license = self.config.license_type or "MIT"
        description += f"Distributed under the {desc_license.upper()} License.\n"
        readme_path.write_text(description)

    def _create_license(self) -> None:
        """Generates a LICENSE file based on the selected license type."""
        if self.config.license_type not in LICENSE_TEMPLATES:
            raise ProjectCreationError(
                f"Unknown license type: {self.config.license_type}. "
                f"Available: {', '.join(AVAILABLE_LICENSES)}"
            )

        # Try to get author name from git config
        author = self._get_git_user() or GIT_USER_PLACEHOLDER
        year = str(datetime.datetime.now().year)

        template = LICENSE_TEMPLATES[self.config.license_type]
        content = template.replace("{year}", year).replace("{author}", author)

        license_path = self.project_path / "LICENSE"
        license_path.write_text(content)

    def _get_git_user(self) -> Optional[str]:
        """Attempts to retrieve the Git user name from global config.

        Returns:
            The user name or None.
        """
        try:
            result = subprocess.run(
                ["git", "config", "--global", "user.name"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip() or None
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    def _initial_commit(self) -> Optional[str]:
        """Creates the initial commit with all scaffolded files.

        Returns:
            The commit hash, or None if commit fails.
        """
        try:
            subprocess.run(
                ["git", "add", "-A"],
                cwd=str(self.project_path),
                capture_output=True,
                check=True,
            )
            result = subprocess.run(
                ["git", "commit", "-m", INITIAL_COMMIT_MESSAGE],
                cwd=str(self.project_path),
                capture_output=True,
                text=True,
                check=True,
            )
            # Extract commit hash from output: "[main abc1234] message"
            output = result.stdout.strip()
            if output:
                parts = output.split()
                if len(parts) >= 2:
                    return parts[1].strip("[]")
            return None
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None
