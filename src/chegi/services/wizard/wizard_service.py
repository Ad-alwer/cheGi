"""Service for the first-run wizard."""

import os
import shlex
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer

from chegi.config import ChegiConfig
from chegi.services.wizard.constants import (
    BANNER,
    SSH_KEY_TYPES,
    WELCOME_MESSAGE,
    WIZARD_MARKER_DIR,
    WIZARD_MARKER_FILE,
)
from chegi.ui import TerminalUI, console


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
    def _check_git_installed() -> bool:
        """Checks if Git is available on the system.

        Returns:
            True if Git is installed.
        """
        try:
            subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                check=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    @staticmethod
    def _get_git_config(key: str) -> Optional[str]:
        """Reads a single git config value.

        Args:
            key: The git config key to read.

        Returns:
            The value, or None if not set.
        """
        try:
            result = subprocess.run(
                ["git", "config", "--global", key],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip() or None
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    @staticmethod
    def _set_git_identity(name: str, email: str) -> None:
        """Sets the global Git user name and email.

        Args:
            name: The user name to set.
            email: The user email to set.
        """
        subprocess.run(
            ["git", "config", "--global", "user.name", name],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "config", "--global", "user.email", email],
            check=True,
            capture_output=True,
            text=True,
        )

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
        self._step_ssh_key()
        self._step_project_config()

        self._mark_completed()
        console.print()
        TerminalUI.print_success("Wizard complete! Happy coding with cheGi. 🐆")

    def _step_git_check(self) -> None:
        """Step 1: Check if Git is installed."""
        if self._check_git_installed():
            TerminalUI.print_success("Git is installed.")
        else:
            TerminalUI.print_error("Git is not installed. Please install Git first.")
            raise typer.Exit(code=1)
        console.print()

    def _step_identity(self) -> None:
        """Step 2: Check and configure Git identity."""
        user_name = self._get_git_config("user.name")
        user_email = self._get_git_config("user.email")

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
                "[dim]Skipping identity setup. You can run [bold]chegi setup git[/bold] later.[/dim]"
            )
            console.print()
            return

        name_input = typer.prompt(
            "What is your name?",
            default=user_name or "",
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

        try:
            self._set_git_identity(name_input, email_input)
            TerminalUI.print_success(
                f"Git identity set to: [cyan]{name_input}[/cyan] <[cyan]{email_input}[/cyan]>"
            )
        except subprocess.CalledProcessError:
            TerminalUI.print_error(
                "Failed to set Git identity. Please configure it manually."
            )
        console.print()

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

        email = typer.prompt(
            "Enter your email for the SSH key label",
            default=self._get_git_config("user.email") or "",
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
