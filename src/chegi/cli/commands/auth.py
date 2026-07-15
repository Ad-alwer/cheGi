"""CLI commands for token-based authentication."""

import shutil
import subprocess
from typing import Optional

import questionary
import typer

from chegi.services.auth import AuthProvider, AuthService
from chegi.services.auth.exceptions import TokenValidationError
from chegi.ui import TerminalUI, console

app = typer.Typer(
    help=(
        "Manage token-based authentication for GitHub and GitLab.\n\n"
        "Store personal access tokens securely and let cheGi handle Git "
        "authentication automatically — no more password prompts."
    )
)


@app.command()
def login(
    token: Optional[str] = typer.Option(
        None, "--token", "-t", help="Token string (skip interactive prompt)"
    ),
    username: Optional[str] = typer.Option(
        None, "--username", "-u", help="Git username (required with --token)"
    ),
    provider: Optional[str] = typer.Option(
        None, "--provider", "-p", help="Provider: github or gitlab"
    ),
    gitlab_url: Optional[str] = typer.Option(
        None, "--gitlab-url", help="Base URL for self-hosted GitLab"
    ),
    label: Optional[str] = typer.Option(
        None, "--label", "-l", help="Account label (e.g. personal, work)"
    ),
) -> None:
    """Authenticate with a Git provider and store the credential securely."""
    is_interactive = token is None

    # ── Resolve provider (flag → detection → interactive) ─────
    detected_provider: Optional[AuthProvider] = None
    if token:
        detected_provider = AuthService.detect_provider(token)

    resolved_provider = _resolve_provider(provider, detected_provider)

    if is_interactive:
        token = _ask_token(resolved_provider)
        detected_from_token = AuthService.detect_provider(token)
        if detected_from_token and resolved_provider is None:
            resolved_provider = detected_from_token
        if resolved_provider is None:
            resolved_provider = _ask_provider()

    if resolved_provider is None:
        TerminalUI.print_error("Could not determine provider. Use --provider.")
        raise typer.Exit(code=1)

    # ── GitLab URL ─────────────────────────────────────────────
    if resolved_provider == AuthProvider.GITLAB and not gitlab_url and is_interactive:
        gitlab_url = _ask_gitlab_url()

    # ── Label ──────────────────────────────────────────────────
    resolved_label: str = "default"
    if is_interactive:
        resolved_label = _ask_label(resolved_provider) or "default"
    elif label:
        resolved_label = label

    # ── Username ───────────────────────────────────────────────
    resolved_username: Optional[str] = username
    if is_interactive and not resolved_username:
        resolved_username = _ask_username(resolved_provider)

    # ── Validate ───────────────────────────────────────────────
    try:
        username_from_api, scopes = AuthService.validate_token(
            resolved_provider, token, api_url=gitlab_url or ""
        )
    except TokenValidationError as e:
        TerminalUI.print_error(str(e))
        raise typer.Exit(code=1) from e

    effective_username = username_from_api or resolved_username or ""

    # ── Scope check ────────────────────────────────────────────
    missing_scopes = AuthService.check_required_scopes(resolved_provider, scopes)
    if missing_scopes:
        TerminalUI.print_warning(
            f"Token is missing recommended scopes: "
            f"[bold]{', '.join(missing_scopes)}[/bold]"
        )

    # ── Make default ──────────────────────────────────────────
    host = _host_for_provider(resolved_provider, gitlab_url)
    existing = AuthService.get_credential_for_host(host)
    make_default = existing is None

    # ── Store ──────────────────────────────────────────────────
    try:
        cred = AuthService.login(
            provider=resolved_provider,
            label=resolved_label,
            username=effective_username,
            token=token,
            api_url=gitlab_url or "",
            make_default=make_default,
            username_from_api=username_from_api,
            scopes=scopes,
        )
    except Exception as e:
        TerminalUI.print_error(f"Failed to store credential: {e}")
        raise typer.Exit(code=1) from e

    TerminalUI.print_success(
        f"Token valid — welcome, [cyan]{effective_username}[/cyan]!"
    )
    if scopes:
        TerminalUI.print_info(f"Scopes: [cyan]{', '.join(scopes)}[/cyan]")

    # ── Git credential helper setup ────────────────────────────
    if make_default and _check_git_installed():
        helper_host = cred.host
        if _has_credential_helper(helper_host):
            TerminalUI.print_info(
                f"Credential helper already configured for [cyan]{helper_host}[/cyan]"
            )
        else:
            if is_interactive:
                setup = questionary.confirm(
                    f"Set up automatic Git authentication for {helper_host}?",
                    default=True,
                ).ask()
                if not setup:
                    return
            _setup_git_credential_helper(helper_host)
            TerminalUI.print_info(
                f"Credential helper registered for [cyan]{helper_host}[/cyan]"
            )


@app.command()
def logout(
    label: Optional[str] = typer.Option(
        None, "--label", "-l", help="Account label to remove"
    ),
    all_: bool = typer.Option(
        False, "--all", "-a", help="Remove all stored credentials"
    ),
) -> None:
    """Remove stored credentials."""
    if all_:
        creds = AuthService.status()
        for c in creds:
            _remove_git_credential_helper(c.host)
            AuthService.logout(c.label)
        TerminalUI.print_success("All credentials removed.")
        return

    if not label:
        creds = AuthService.status()
        if not creds:
            TerminalUI.print_info("No credentials stored.")
            return
        choices = [c.label for c in creds] + ["Cancel"]
        chosen = questionary.select(
            "Which credential would you like to remove?",
            choices=choices,
        ).ask()
        if not chosen or chosen == "Cancel":
            return
        label = chosen

    # Get credential before deleting so we can remove the helper
    cred = AuthService.get_credential_by_label(label)
    if cred:
        _remove_git_credential_helper(cred.host)

    if AuthService.logout(label):
        TerminalUI.print_success(f"Credential '{label}' removed.")
    else:
        TerminalUI.print_error(f"Credential '{label}' not found.")


@app.command()
def status() -> None:
    """Show all stored credentials."""
    creds = AuthService.status()
    if not creds:
        TerminalUI.print_info("No credentials stored. Run [bold]chegi auth login[/].")
        return

    console.print("[bold]Auth Status[/bold]")
    console.print("─" * 40)
    for cred in creds:
        default_mark = " (default)" if cred.is_default else ""
        provider_label = cred.provider.value.title()
        scope_info = f" [cyan]\\[{cred.scope_hint}][/cyan]" if cred.scope_hint else ""
        console.print(
            f"  {provider_label:<8} \U0001f511 {cred.username}@{cred.host}"
            f"  \u2705 Active{default_mark}{scope_info}"
        )
    console.print()
    TerminalUI.print_info("To switch default: [bold]chegi auth switch <label>[/]")


@app.command()
def switch(
    label: str = typer.Argument(..., help="Account label to make default"),
) -> None:
    """Switch the default account for a host."""
    creds = AuthService.status()
    labels = [c.label for c in creds]

    if not label and labels:
        chosen = questionary.select(
            "Which account should be the default?",
            choices=labels,
        ).ask()
        if not chosen:
            return
        label = chosen

    result = AuthService.switch(label)
    if result:
        TerminalUI.print_success(
            f"Default account switched to [cyan]{result.label}[/cyan]"
            f" ({result.username}@{result.host})."
        )
    else:
        TerminalUI.print_error(f"Credential '{label}' not found.")


@app.command(hidden=True)
def get_credential() -> None:
    """Git credential helper — called by Git, not by users.

    Reads the Git credential protocol from stdin and outputs the
    matching stored credential to stdout.
    """
    import sys

    host = ""
    for line in sys.stdin:
        if line.startswith("host="):
            host = line.strip().split("=", 1)[1]

    if not host:
        return

    cred = AuthService.get_credential_for_host(host)
    if cred:
        sys.stdout.write(f"username={cred.username}\n")
        sys.stdout.write(f"password={cred.token}\n")


# ── Helper functions ─────────────────────────────────────────


def _resolve_provider(
    provider_flag: Optional[str], detected: Optional[AuthProvider]
) -> Optional[AuthProvider]:
    """Resolves the provider from flag, detection, or None."""
    if provider_flag:
        try:
            return AuthProvider(provider_flag.lower())
        except ValueError:
            TerminalUI.print_error(
                f"Unknown provider '{provider_flag}'. Use 'github' or 'gitlab'."
            )
            raise typer.Exit(code=1) from None
    return detected


def _ask_token(provider: Optional[AuthProvider] = None) -> str:
    """Prompts the user to paste their token."""
    provider_hint = f" ({provider.value.title()})" if provider else ""
    token = questionary.password(
        f"Paste your personal access token{provider_hint}:",
        instruction=(
            "Token will be stored encrypted in ~/.config/chegi/auth/"
            if not provider
            else ""
        ),
    ).ask()
    if not token:
        TerminalUI.print_error("Token is required.")
        raise typer.Exit(code=1)
    return token


def _ask_provider() -> AuthProvider:
    """Asks the user to choose a provider."""
    chosen = questionary.select(
        "Choose a Git provider:",
        choices=["GitHub", "GitLab"],
    ).ask()
    if chosen == "GitLab":
        return AuthProvider.GITLAB
    return AuthProvider.GITHUB


def _ask_gitlab_url() -> str:
    """Asks for a self-hosted GitLab URL."""
    url = questionary.text(
        "GitLab instance URL (press Enter for gitlab.com):",
        default="https://gitlab.com",
    ).ask()
    if not url:
        return "https://gitlab.com"
    return url.rstrip("/")


def _ask_label(provider: AuthProvider) -> str:
    """Asks for an account label."""
    label = questionary.text(
        "Account label (e.g. personal, work):",
        default="default",
    ).ask()
    if not label:
        return "default"
    return label.strip()


def _ask_username(provider: AuthProvider) -> str:
    """Asks for the Git username."""
    username = questionary.text(
        f"Username for {provider.value.title()}:",
    ).ask()
    if not username:
        TerminalUI.print_error("Username is required.")
        raise typer.Exit(code=1)
    return username


def _host_for_provider(provider: AuthProvider, gitlab_url: str = "") -> str:
    """Returns the Git hostname for a provider."""
    from chegi.services.auth.constants import PROVIDER_INFO

    if provider == AuthProvider.GITLAB and gitlab_url:
        import urllib.parse

        hostname = urllib.parse.urlparse(gitlab_url).hostname
        if hostname:
            return hostname
    info = PROVIDER_INFO[provider]
    return str(info["default_host"])


# ── Git credential helper ───────────────────────────────────


def _check_git_installed() -> bool:
    """Returns True if Git is installed and accessible."""
    return shutil.which("git") is not None


def _helper_value() -> str:
    """Returns the Git credential helper value for chegi."""
    chegi_path = shutil.which("chegi")
    if chegi_path:
        return f"!{chegi_path} auth get-credential"
    return "!chegi auth get-credential"


def _credential_helper_key(host: str) -> str:
    """Returns the Git config key for a credential helper."""
    return f"credential.https://{host}.helper"


def _has_credential_helper(host: str) -> bool:
    """Checks if the chegi credential helper is already configured."""
    key = _credential_helper_key(host)
    value = _helper_value()
    try:
        result = subprocess.run(
            ["git", "config", "--global", "--get", key],
            capture_output=True,
            text=True,
            check=False,
        )
        return value in result.stdout.strip()
    except Exception:
        return False


def _setup_git_credential_helper(host: str) -> None:
    """Configures Git to use chegi as a credential helper for the given host."""
    key = _credential_helper_key(host)
    value = _helper_value()
    subprocess.run(
        ["git", "config", "--global", "--add", key, value],
        capture_output=True,
        check=False,
    )


def _remove_git_credential_helper(host: str) -> None:
    """Removes the chegi credential helper configuration for the given host."""
    key = _credential_helper_key(host)
    value = _helper_value()
    subprocess.run(
        ["git", "config", "--global", "--unset", key, value],
        capture_output=True,
        check=False,
    )
