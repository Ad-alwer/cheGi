"""Service for the first-run wizard."""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional

import questionary
import typer

from chegi.config import ChegiConfig, GlobalConfig
from chegi.services.auth import AuthProvider, AuthService
from chegi.services.auth.exceptions import TokenValidationError
from chegi.services.git_config.exceptions import GitConfigError
from chegi.services.installer import SystemInstaller
from chegi.services.wizard.constants import (
    BANNER,
    SSH_KEY_TYPES,
    WELCOME_MESSAGE,
    WIZARD_MARKER_DIR,
    WIZARD_MARKER_FILE,
)
from chegi.ui import ChegiTheme, TerminalUI, console, get_theme, list_themes


class WizardService:
    """First-run wizard that guides new users through setup.

    Triggers on the first cheGi command, checks the environment,
    and offers to configure Git identity and project defaults.
    """

    def __init__(self, base_path: Optional[Path] = None) -> None:
        """Initializes the wizard.

        Args:
            base_path: The project base path. Defaults to CWD.
        """
        self.base_path = base_path or Path.cwd()
        self._git_available: bool = True

    def should_run(self) -> bool:
        """Checks if the wizard should run on this invocation.

        Returns:
            True if the wizard marker file does not exist.
        """
        return not os.path.isfile(WIZARD_MARKER_FILE)

    def _mark_completed(self) -> None:
        """Writes the marker file to prevent future wizard runs."""
        os.makedirs(WIZARD_MARKER_DIR, exist_ok=True)
        with open(WIZARD_MARKER_FILE, "w", encoding="utf-8") as f:
            f.write("done\n")

    @staticmethod
    def _get_git_version() -> Optional[str]:
        """Returns the installed Git version string, or None.

        Returns:
            Version string (e.g. 'git version 2.43.0') or None.
        """
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    def execute(self) -> None:
        """Runs the first-run wizard."""
        if not self.should_run():
            return

        if not sys.stdin.isatty():
            return

        console.print()
        console.print(BANNER)
        console.print()
        console.print(WELCOME_MESSAGE)
        console.print()

        self._step_git_check()
        self._step_identity()
        self._step_gh_check()
        self._step_ssh_key()
        self._step_git_aliases()
        self._step_auth_login()
        self._step_project_config()
        self._step_theme_picker()

        self._mark_completed()
        console.print()
        TerminalUI.print_success("Wizard complete! Happy coding with cheGi. 🐆")

    def _step_git_check(self) -> None:
        """Step 1: Check if Git is installed, offer install if missing."""
        version = self._get_git_version()
        if version:
            TerminalUI.print_success(f"Git is installed. [dim]({version})[/dim]")
            self._git_available = True
        else:
            TerminalUI.print_warning("Git is not installed.")
            console.print("[dim]cheGi needs Git for version control features.[/dim]")
            should_install = typer.confirm(
                "Would you like to install Git?", default=True
            )
            if should_install:
                try:
                    ok = SystemInstaller.install_package("git")
                    if ok:
                        TerminalUI.print_success("Git installed successfully!")
                        self._log_wizard_event("git_installed")
                        self._git_available = True
                    else:
                        TerminalUI.print_error(
                            "Failed to install Git. "
                            "See [blue]https://git-scm.com[/blue]"
                        )
                        self._git_available = False
                except Exception:
                    TerminalUI.print_error(
                        "Failed to install Git. See [blue]https://git-scm.com[/blue]"
                    )
                    self._git_available = False
            else:
                console.print("[dim]Skipping Git setup.[/dim]")
                self._git_available = False
        console.print()

    def _step_identity(self) -> None:
        """Step 2: Check and configure Git identity."""
        if not self._git_available:
            console.print("[dim]Skipping Git identity setup (Git not available).[/dim]")
            console.print()
            return

        from chegi.services.git_config import GitConfigService

        user_name = GitConfigService.get("user.name")
        user_email = GitConfigService.get("user.email")

        if user_name and user_email:
            TerminalUI.print_success(
                f"Git identity is set: [cyan]{user_name}[/cyan] <[cyan]{user_email}[/cyan]>"
            )
            console.print()
            return

        if not user_name and not user_email:
            TerminalUI.print_warning("Git identity is not configured.")
            console.print(
                "[dim]Commits need a name and email to be attributed correctly.[/dim]"
            )
        elif not user_name:
            TerminalUI.print_warning("Git [cyan]user.name[/cyan] is not set.")
        elif not user_email:
            TerminalUI.print_warning("Git [cyan]user.email[/cyan] is not set.")

        console.print()
        should_set = typer.confirm(
            "Would you like to configure Git identity now?", default=True
        )
        if not should_set:
            console.print(
                "[dim]Skipping identity setup. You can run [bold]chegi config git set[/bold] later.[/dim]"
            )
            console.print()
            return

        import os

        name_input = typer.prompt(
            "What is your name?",
            default=user_name or os.environ.get("USER", ""),
            show_default=False,
        )
        email_input = typer.prompt(
            "What is your email?",
            default=user_email or "",
            show_default=False,
        )

        if not name_input or not email_input:
            TerminalUI.print_error(
                "Name and email are required. Skipping identity setup."
            )
            console.print()
            return

        # Simple email validation
        if "@" not in email_input or "." not in email_input.split("@")[-1]:
            TerminalUI.print_warning("Email may be invalid (missing @ or domain).")
            if not typer.confirm("Continue with this email?", default=True):
                console.print()
                return

        try:
            GitConfigService.set_identity(name_input, email_input)
            TerminalUI.print_success(
                f"Git identity set to: [cyan]{name_input}[/cyan]"
                f" <[cyan]{email_input}[/cyan]>"
            )
        except Exception:
            TerminalUI.print_error(
                "Failed to set Git identity. Please configure it manually."
            )

        # Offer to set init.defaultBranch
        branch = GitConfigService.get("init.defaultBranch")
        if not branch:
            console.print()
            branch_input = typer.prompt("Set default branch name", default="main")
            if branch_input:
                try:
                    GitConfigService.set("init.defaultBranch", branch_input)
                    TerminalUI.print_success(
                        f"init.defaultBranch set to [cyan]{branch_input}[/cyan]"
                    )
                except GitConfigError:
                    pass

        console.print()

    def _step_gh_check(self) -> None:
        """Step: Check if GitHub CLI (gh) is installed, offer to install/upgrade."""
        if not self._git_available:
            console.print("[dim]Skipping GitHub CLI check (Git not available).[/dim]")
            console.print()
            return
        if shutil.which("gh"):
            gh_version_line: Optional[str] = None
            try:
                result = subprocess.run(
                    ["gh", "--version"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                gh_version_line = result.stdout.strip().split("\n")[0]
                TerminalUI.print_success(
                    f"GitHub CLI is installed. [dim]({gh_version_line})[/dim]"
                )
            except (subprocess.CalledProcessError, FileNotFoundError):
                TerminalUI.print_success("GitHub CLI is installed.")

            installed = (
                self._parse_gh_version(gh_version_line) if gh_version_line else None
            )
            if installed:
                latest = self._check_latest_gh_version()
                if latest and installed != latest:
                    console.print()
                    TerminalUI.print_warning(
                        f"A new version of GitHub CLI is available: [cyan]{latest}[/cyan]"
                    )
                    should_upgrade = typer.confirm(
                        "Would you like to upgrade GitHub CLI?", default=True
                    )
                    if should_upgrade:
                        try:
                            ok = SystemInstaller.install_package("gh")
                            if ok:
                                TerminalUI.print_success(
                                    "GitHub CLI upgraded successfully!"
                                )
                                self._log_wizard_event("gh_upgraded", latest)
                            else:
                                TerminalUI.print_error(
                                    "Failed to upgrade GitHub CLI. "
                                    "See [blue]https://cli.github.com[/blue]"
                                )
                        except Exception:
                            TerminalUI.print_error(
                                "Failed to upgrade GitHub CLI. "
                                "See [blue]https://cli.github.com[/blue]"
                            )
        else:
            TerminalUI.print_warning("GitHub CLI (gh) is not installed.")
            console.print(
                "[dim]The GitHub CLI lets you create repos, manage PRs, "
                "and authenticate from the terminal.[/dim]"
            )
            should_install = typer.confirm(
                "Would you like to install GitHub CLI?", default=True
            )
            if should_install:
                try:
                    ok = SystemInstaller.install_package("gh")
                    if ok:
                        TerminalUI.print_success("GitHub CLI installed successfully!")
                        self._log_wizard_event("gh_installed")
                    else:
                        TerminalUI.print_error(
                            "Failed to install GitHub CLI. "
                            "See [blue]https://cli.github.com[/blue]"
                        )
                except Exception:
                    TerminalUI.print_error(
                        "Failed to install GitHub CLI. "
                        "See [blue]https://cli.github.com[/blue]"
                    )
            else:
                console.print("[dim]Skipping GitHub CLI setup.[/dim]")
        console.print()

    @staticmethod
    def _parse_gh_version(version_line: str) -> Optional[str]:
        """Extracts the version number from the gh --version output.

        Args:
            version_line: First line of gh --version output.

        Returns:
            Version string (e.g. '2.45.0') or None.
        """
        m = re.search(r"(\d+\.\d+\.\d+)", version_line)
        return m.group(1) if m else None

    @staticmethod
    def _check_latest_gh_version() -> Optional[str]:
        """Fetches the latest GitHub CLI release version from the API.

        Returns:
            Version string (e.g. '2.67.0') or None on failure.
        """
        try:
            req = urllib.request.Request(
                "https://api.github.com/repos/cli/cli/releases/latest",
                headers={
                    "User-Agent": "cheGi",
                    "Accept": "application/vnd.github+json",
                },
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                tag = data.get("tag_name", "")
                return tag.lstrip("v")
        except Exception:
            return None

    @staticmethod
    def _find_ssh_keys(ssh_dir: Path) -> list[str]:
        """Finds SSH key pairs (private + .pub) in the given directory.

        Args:
            ssh_dir: Path to the .ssh directory.

        Returns:
            List of key names with both private and public parts present.
        """
        if not ssh_dir.is_dir():
            return []
        found: list[str] = []
        for key_name in SSH_KEY_TYPES:
            private = ssh_dir / key_name
            public = ssh_dir / f"{key_name}.pub"
            if private.is_file() and public.is_file():
                found.append(key_name)
        return found

    @staticmethod
    def _ssh_agent_has_keys() -> bool:
        """Checks if ssh-agent is running and has any keys loaded.

        Returns:
            True if at least one key is loaded in the agent.
        """
        try:
            result = subprocess.run(
                ["ssh-add", "-l"],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False

    @staticmethod
    def _log_wizard_event(event: str, details: str = "") -> None:
        """Logs a wizard event to cheGi's log file.

        Args:
            event: Short event name (e.g. "ssh_key_generated").
            details: Optional extra info (key path, email, etc.).
        """
        log_dir = WIZARD_MARKER_DIR
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "wizard.log"
        timestamp = datetime.now().isoformat()
        line = f"[{timestamp}] {event}"
        if details:
            line += f": {details}"
        line += "\n"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(line)

    @staticmethod
    def _backup_key(key_path: Path) -> Optional[Path]:
        """Backs up an existing SSH key pair before overwriting.

        Args:
            key_path: Path to the private key to back up.

        Returns:
            Path to the backup file, or None if backup failed.
        """
        backup = key_path.with_name(key_path.name + ".backup")
        try:
            shutil.copy2(str(key_path), str(backup))
            pub = key_path.with_suffix(".pub")
            if pub.exists():
                pub_backup = pub.with_name(pub.name + ".backup")
                shutil.copy2(str(pub), str(pub_backup))
            return backup
        except OSError:
            return None

    @staticmethod
    def _backup_ssh_config() -> Optional[Path]:
        """Backs up ~/.ssh/config before modification.

        Returns:
            Path to the backup file, or None if no config existed or backup failed.
        """
        ssh_config = Path.home() / ".ssh" / "config"
        if not ssh_config.is_file():
            return None
        backup = ssh_config.with_name("config.chegi.backup")
        try:
            shutil.copy2(str(ssh_config), str(backup))
            return backup
        except OSError:
            return None

    @staticmethod
    def _generate_ssh_key(
        key_path: Path, email: str, use_passphrase: bool = False
    ) -> bool:
        """Generates an Ed25519 SSH key pair.

        Args:
            key_path: Full path for the private key.
            email: Email label for the key comment.
            use_passphrase: If True, let ssh-keygen prompt interactively.

        Returns:
            True if generation succeeded.
        """
        try:
            cmd = ["ssh-keygen", "-t", "ed25519", "-C", email, "-f", str(key_path)]
            if not use_passphrase:
                cmd += ["-N", ""]
            subprocess.run(cmd, check=True)
            return True
        except subprocess.CalledProcessError:
            return False

    @staticmethod
    def _add_key_to_agent(key_path: Path) -> bool:
        """Adds an SSH private key to the ssh-agent.

        Args:
            key_path: Path to the private key.

        Returns:
            True if the key was added successfully.
        """
        try:
            subprocess.run(
                ["ssh-add", str(key_path)],
                capture_output=True,
                text=True,
                check=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    @staticmethod
    def _add_ssh_config_entry(key_path: Path) -> bool:
        """Adds entries for common Git hosts to ~/.ssh/config.

        Args:
            key_path: Path to the private key to associate.

        Returns:
            True if config was updated, False if skipped or failed.
        """
        ssh_config = Path.home() / ".ssh" / "config"
        hosts = ["github.com"]
        entries = []
        existing = (
            ssh_config.read_text(encoding="utf-8") if ssh_config.is_file() else ""
        )

        for host in hosts:
            host_block = f"Host {host}"
            if host_block not in existing:
                entries.append(
                    f"\n# Added by cheGi\nHost {host}\n"
                    f"  IdentityFile {shlex.quote(str(key_path))}\n"
                    f"  IdentitiesOnly yes\n"
                )

        if not entries:
            return False

        try:
            with open(ssh_config, "a", encoding="utf-8") as f:
                f.writelines(entries)
            return True
        except OSError:
            return False

    def _display_public_key(self, key_path: Path) -> None:
        """Prints the public key content and instructs the user.

        Args:
            key_path: Path to the public key file.
        """
        try:
            pub_content = key_path.read_text(encoding="utf-8").strip()
            console.print()
            TerminalUI.print_info("Here is your public SSH key:")
            console.print(f"[bold yellow]{pub_content}[/bold yellow]")
            console.print()
            console.print("[dim]Add this key to your Git provider:[/dim]")
            console.print(
                "  [cyan]GitHub[/cyan]  → [blue]https://github.com/settings/ssh/new[/blue]"
            )
            console.print(
                "  [cyan]GitLab[/cyan]  → [blue]https://gitlab.com/-/profile/keys[/blue]"
            )
        except OSError:
            TerminalUI.print_error("Could not read the public key file.")

    def _step_ssh_key(self) -> None:
        """Step: Check SSH keys and offer to generate one."""
        ssh_dir = Path.home() / ".ssh"
        key_names = self._find_ssh_keys(ssh_dir)

        if key_names:
            TerminalUI.print_success(
                f"SSH keys found: [cyan]{', '.join(key_names)}[/cyan]"
            )
            if self._ssh_agent_has_keys():
                TerminalUI.print_info("SSH keys are loaded in ssh-agent.")
            else:
                console.print()
                TerminalUI.print_warning("No keys are loaded in ssh-agent.")
                should_add = typer.confirm(
                    "Would you like to add your key to ssh-agent?", default=True
                )
                if should_add:
                    key_path = ssh_dir / f"{key_names[0]}"
                    if self._add_key_to_agent(key_path):
                        TerminalUI.print_success(
                            f"Key [cyan]{key_names[0]}[/cyan] added to ssh-agent."
                        )
                    else:
                        TerminalUI.print_error(
                            "Failed to add key. Run [bold]ssh-add ~/.ssh/<key>[/bold] manually."
                        )
            console.print()
            return

        console.print()
        TerminalUI.print_warning("No SSH keys found.")
        console.print(
            "[dim]SSH keys allow you to push to remote repositories securely without a password.[/dim]"
        )

        should_generate = typer.confirm(
            "Would you like to generate an SSH key?", default=True
        )
        if not should_generate:
            console.print("[dim]Skipping SSH key setup.[/dim]")
            console.print()
            return

        from chegi.services.git_config import GitConfigService

        email = typer.prompt(
            "Enter your email for the SSH key label",
            default=GitConfigService.get("user.email") or "",
            show_default=False,
        )
        if not email:
            TerminalUI.print_error("Email is required. Skipping SSH key generation.")
            console.print()
            return

        ssh_dir.mkdir(parents=True, exist_ok=True)
        key_path = ssh_dir / "id_ed25519"
        backup_path: Optional[Path] = None

        if key_path.exists():
            overwrite = typer.confirm(
                f"[bold]{key_path}[/bold] already exists. Overwrite?", default=False
            )
            if not overwrite:
                console.print("[dim]Skipping SSH key generation.[/dim]")
                self._log_wizard_event(
                    "ssh_key_skipped", f"user declined overwrite of {key_path}"
                )
                console.print()
                return
            backup_path = self._backup_key(key_path)
            if backup_path:
                console.print(
                    f"[dim]Old key backed up to {shlex.quote(str(backup_path))}[/dim]"
                )
            else:
                TerminalUI.print_warning(
                    "Could not back up existing key. Proceeding anyway."
                )

        use_passphrase = typer.confirm(
            "Do you want to protect this key with a passphrase?",
            default=False,
        )

        if use_passphrase:
            console.print(
                "[dim]ssh-keygen will prompt you to enter a passphrase below.[/dim]"
            )
            ok = self._generate_ssh_key(key_path, email, use_passphrase=True)
        else:
            with console.status("[bold yellow]Generating SSH key..."):
                ok = self._generate_ssh_key(key_path, email)

        if ok:
            TerminalUI.print_success(
                f"SSH key generated at [cyan]{shlex.quote(str(key_path))}[/cyan]"
            )
            self._log_wizard_event(
                "ssh_key_generated",
                f"{key_path} for {email}"
                + (" (passphrase protected)" if use_passphrase else ""),
            )
        else:
            TerminalUI.print_error(
                "Failed to generate SSH key. Try [bold]ssh-keygen -t ed25519 -C"
                f" {shlex.quote(email)}[/bold] manually."
            )
            self._log_wizard_event("ssh_key_failed", str(key_path))
            console.print()
            return

        pub_path = key_path.with_suffix(".pub")
        self._display_public_key(pub_path)

        should_add = typer.confirm("Add this key to ssh-agent now?", default=True)
        if should_add:
            if self._add_key_to_agent(key_path):
                TerminalUI.print_success("Key added to ssh-agent.")
            else:
                TerminalUI.print_warning(
                    "Could not start ssh-agent. Run [bold]ssh-add ~/.ssh/id_ed25519[/bold] later."
                )
                self._log_wizard_event("ssh_agent_add_failed", str(key_path))

        config_backup = self._backup_ssh_config()
        if config_backup:
            console.print(
                f"[dim]~/.ssh/config backed up to {shlex.quote(str(config_backup))}[/dim]"
            )

        should_configure = typer.confirm(
            "Add this key to [bold]~/.ssh/config[/bold] for GitHub?", default=True
        )
        if should_configure:
            if self._add_ssh_config_entry(key_path):
                TerminalUI.print_success(
                    "GitHub host entry added to [cyan]~/.ssh/config[/cyan]."
                )
                self._log_wizard_event(
                    "ssh_config_updated", f"github.com -> {key_path}"
                )
            else:
                TerminalUI.print_info(
                    "GitHub host entry already exists in [cyan]~/.ssh/config[/cyan]."
                )

        if backup_path:
            console.print()
            console.print("[dim]To restore your old key:[/dim]")
            console.print(
                f"  [cyan]cp {shlex.quote(str(backup_path))} {shlex.quote(str(key_path))}[/cyan]"
            )
            pub_backup = key_path.with_suffix(".pub.backup")
            if pub_backup.is_file():
                console.print(
                    f"  [cyan]cp {shlex.quote(str(pub_backup))} {shlex.quote(str(key_path.with_suffix('.pub')))}[/cyan]"
                )

        if config_backup:
            console.print(
                f"  [cyan]cp {shlex.quote(str(config_backup))} "
                f"{shlex.quote(str(Path.home() / '.ssh' / 'config'))}[/cyan]"
            )

        console.print()

    def _step_git_aliases(self) -> None:
        """Step: Offer to configure Git alias shortcuts."""
        from chegi.services.git_config import GitConfigService

        if not self._git_available:
            console.print("[dim]Skipping Git aliases (Git not available).[/dim]")
            console.print()
            return

        # Check which aliases are already set
        existing = {}
        for alias_name, full_cmd in [
            ("co", "checkout"),
            ("br", "branch"),
            ("ci", "commit"),
            ("st", "status"),
        ]:
            val = GitConfigService.get(f"alias.{alias_name}")
            if val:
                existing[alias_name] = val

        if len(existing) == 4:
            TerminalUI.print_success(
                "All Git aliases are already configured:"
                " [cyan]co[/], [cyan]br[/], [cyan]ci[/], [cyan]st[/]"
            )
            console.print()
            return

        if existing:
            present = ", ".join(f"[cyan]{k}[/]→{v}" for k, v in existing.items())
            missing_count = 4 - len(existing)
            TerminalUI.print_info(
                f"Some Git aliases already set ({present}). "
                f"[dim]{missing_count} missing[/dim]"
            )
        else:
            TerminalUI.print_warning("Git aliases (co, br, ci, st) are not configured.")
            console.print(
                "[dim]Aliases let you type [bold]git co[/bold] instead of "
                "[bold]git checkout[/bold].[/dim]"
            )

        should_set = typer.confirm("Configure Git shortcut aliases?", default=True)
        if not should_set:
            console.print("[dim]Skipping Git alias setup.[/dim]")
            console.print()
            return

        aliases = [
            ("co", "checkout"),
            ("br", "branch"),
            ("ci", "commit"),
            ("st", "status"),
        ]
        set_count = 0
        for alias_name, full_cmd in aliases:
            if alias_name in existing:
                continue
            try:
                subprocess.run(
                    ["git", "config", "--global", f"alias.{alias_name}", full_cmd],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                set_count += 1
            except subprocess.CalledProcessError:
                pass

        if set_count:
            names = ", ".join(a for a, _ in aliases if a not in existing)
            TerminalUI.print_success(f"Git aliases configured: [cyan]{names}[/cyan]")
            self._log_wizard_event("git_aliases_set", f"{set_count} aliases")
        console.print()

    def _step_auth_login(self) -> None:
        """Step: Offer to set up Git provider token-based authentication."""
        import urllib.parse

        existing = AuthService.status()
        if existing:
            providers = ", ".join(
                sorted(set(c.provider.value.title() for c in existing))
            )
            TerminalUI.print_success(
                f"Token authentication already configured: [cyan]{providers}[/cyan]"
            )
            console.print()
            return

        if not self._git_available:
            console.print("[dim]Skipping auth setup (Git not available).[/dim]")
            console.print()
            return

        TerminalUI.print_info(
            "Token-based authentication lets cheGi interact with GitHub/GitLab APIs "
            "on your behalf."
        )
        should_setup = typer.confirm(
            "Would you like to set up Git provider authentication?", default=True
        )
        if not should_setup:
            console.print(
                "[dim]Skipping auth setup. You can run [bold]chegi auth login[/bold] later.[/dim]"
            )
            console.print()
            return

        # ── Provider ──────────────────────────────────────────
        provider_choices = ["GitHub", "GitLab"]
        chosen = questionary.select(
            "Choose your Git provider:",
            choices=provider_choices,
        ).ask()
        if not chosen:
            console.print("[dim]Skipping auth setup.[/dim]")
            console.print()
            return
        provider = AuthProvider.GITLAB if chosen == "GitLab" else AuthProvider.GITHUB

        # ── GitLab URL ───────────────────────────────────────
        gitlab_url = ""
        if provider == AuthProvider.GITLAB:
            url = questionary.text(
                "GitLab instance URL (press Enter for gitlab.com):",
                default="https://gitlab.com",
            ).ask()
            if url:
                gitlab_url = url.rstrip("/")

        # ── Token ─────────────────────────────────────────────
        token = questionary.password(
            f"Paste your personal access token ({chosen}):",
        ).ask()
        if not token:
            TerminalUI.print_error("Token is required. Skipping auth setup.")
            console.print()
            return

        # ── Detect & validate ─────────────────────────────────
        detected = AuthService.detect_provider(token)
        if detected and detected != provider:
            TerminalUI.print_warning(
                f"Token prefix suggests {detected.value.title()}, "
                f"but you selected {chosen}."
            )
            correct = typer.confirm("Use detected provider instead?", default=False)
            if correct:
                provider = detected
                chosen = provider.value.title()

        try:
            username, scopes = AuthService.validate_token(
                provider, token, api_url=gitlab_url
            )
        except TokenValidationError as e:
            TerminalUI.print_error(f"Token validation failed: {e}")
            console.print(
                "[dim]You can retry with [bold]chegi auth login[/bold] after fixing the token.[/dim]"
            )
            console.print()
            return

        # ── Username ─────────────────────────────────────────
        username_str = username or ""
        if not username_str:
            username_str = typer.prompt(
                f"Username for {chosen}",
            )
            if not username_str:
                TerminalUI.print_error("Username is required. Skipping auth setup.")
                console.print()
                return

        # ── Label ─────────────────────────────────────────────
        label = questionary.text(
            "Account label (e.g. personal, work):",
            default="default",
        ).ask()
        if not label:
            label = "default"

        # ── Scopes ────────────────────────────────────────────
        missing_scopes = AuthService.check_required_scopes(provider, scopes)
        if missing_scopes:
            TerminalUI.print_warning(
                f"Token is missing recommended scopes: "
                f"[bold]{', '.join(missing_scopes)}[/bold]"
            )
            proceed = typer.confirm("Continue anyway?", default=True)
            if not proceed:
                console.print("[dim]Skipping auth setup.[/dim]")
                console.print()
                return

        # ── Host ──────────────────────────────────────────────
        from chegi.services.auth.constants import PROVIDER_INFO

        host = str(PROVIDER_INFO[provider]["default_host"])
        if provider == AuthProvider.GITLAB and gitlab_url:
            parsed_host = urllib.parse.urlparse(gitlab_url).hostname
            if parsed_host:
                host = parsed_host

        existing_cred = AuthService.get_credential_for_host(host)
        make_default = existing_cred is None

        # ── Store ─────────────────────────────────────────────
        try:
            AuthService.login(
                provider=provider,
                label=label,
                username=username_str,
                token=token,
                api_url=gitlab_url,
                make_default=make_default,
                username_from_api=username,
                scopes=scopes,
            )
        except Exception as e:
            TerminalUI.print_error(f"Failed to store credential: {e}")
            console.print()
            return

        TerminalUI.print_success(f"Token valid — welcome, [cyan]{username_str}[/cyan]!")
        self._log_wizard_event("auth_login", f"{provider.value} as {username_str}")

        # ── Credential helper ─────────────────────────────────
        import shutil
        import subprocess

        has_git = shutil.which("git") is not None
        if make_default and has_git:
            setup_helper = typer.confirm(
                f"Set up automatic Git authentication for {host}?",
                default=True,
            )
            if setup_helper:
                key = f"credential.https://{host}.helper"
                chegi_path = shutil.which("chegi")
                value = (
                    f"!{chegi_path} auth get-credential"
                    if chegi_path
                    else "!chegi auth get-credential"
                )
                subprocess.run(
                    ["git", "config", "--global", "--add", key, value],
                    capture_output=True,
                    check=False,
                )
                TerminalUI.print_info(
                    f"Credential helper registered for [cyan]{host}[/cyan]"
                )
                self._log_wizard_event("credential_helper_setup", host)

        console.print()

    def _step_project_config(self) -> None:
        """Step 3: Offer to create .chegi/ project config."""
        chegi_dir = self.base_path / ".chegi"
        if chegi_dir.is_dir():
            return

        should_create = typer.confirm(
            "Would you like to create a [bold].chegi/[/bold] project directory?"
            "\n[dim]This enables project-specific guard rules and config overrides.[/dim]",
            default=True,
        )
        if not should_create:
            console.print("[dim]Skipping project setup.[/dim]")
            console.print()
            return

        from chegi.services.init import InitService

        try:
            InitService.create_project_directory(self.base_path)
            TerminalUI.print_success(
                f".chegi/ created at [cyan]{shlex.quote(str(chegi_dir))}[/cyan]"
            )
        except Exception as e:
            TerminalUI.print_error(f"Failed to create .chegi/: {e}")
            console.print()
            return

        self._step_sensitive_patterns()

        console.print()

    def _step_sensitive_patterns(self) -> None:
        """Ask user for custom sensitive file patterns and save them."""
        has_custom = typer.confirm(
            "Do you want to add custom sensitive file patterns for [bold]chegi guard[/bold]"
            " to scan?\n[dim]These will be checked in addition to the default patterns"
            " (e.g. .env, *.pem, credentials.json).[/dim]",
            default=False,
        )
        if not has_custom:
            console.print("[dim]Using default sensitive patterns only.[/dim]")
            return

        pattern = typer.prompt(
            "Enter a filename or pattern (e.g. secrets.yaml, *.local, config.*)",
            default="",
            show_default=False,
        )
        if not pattern:
            TerminalUI.print_error("No pattern entered. Skipping.")
            return

        try:
            cfg = ChegiConfig(str(self.base_path))
            cfg.add_sensitive_pattern(pattern)
            TerminalUI.print_success(
                f"Pattern [cyan]{shlex.quote(pattern)}[/cyan] added to project config."
            )
        except Exception as e:
            TerminalUI.print_error(f"Failed to save pattern: {e}")

        more = typer.confirm("Add another pattern?", default=False)
        if more:
            self._step_sensitive_patterns()

    def _step_theme_picker(self) -> None:
        """Step: Let the user choose a color theme for cheGi output."""
        current = GlobalConfig().theme

        choices: list[questionary.Choice] = []
        for key, label in list_themes().items():
            selected = key == current
            choices.append(
                questionary.Choice(
                    title=f"{'●' if selected else '○'} {label}",
                    value=key,
                )
            )

        chosen = questionary.select(
            "Pick a color theme for cheGi:",
            choices=choices,
            default=current,
        ).ask()

        if chosen and chosen != current:
            GlobalConfig().theme = chosen
            theme: ChegiTheme = get_theme(chosen)
            TerminalUI.apply_theme(theme)
            self._log_wizard_event("theme_changed", chosen)
            TerminalUI.print_success(f"Theme changed to [cyan]{theme.label}[/cyan].")
        elif chosen:
            TerminalUI.print_info(
                f"Keeping current theme: [cyan]{get_theme(current).label}[/cyan]"
            )
        console.print()
