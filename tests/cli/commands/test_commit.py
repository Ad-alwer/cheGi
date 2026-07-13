"""Tests for the chegi commit CLI command."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from chegi.cli.main import app

runner = CliRunner()


@patch("chegi.cli.commands.commit.GitClient.is_valid_repo")
def test_commit_fails_when_not_in_git_repo(mock_is_valid: MagicMock):
    """Test commit command exits with error when not in a git repo."""
    mock_is_valid.return_value = False

    result = runner.invoke(app, ["commit"])

    assert result.exit_code == 1
    assert "not a git repository" in result.stdout.lower()


@patch("chegi.cli.commands.commit.GitClient.is_valid_repo")
@patch("chegi.cli.commands.commit.CommitService.prepare_context")
def test_commit_fails_when_no_staged_files(
    mock_prepare: MagicMock, mock_is_valid: MagicMock
):
    """Test commit command shows error when no files are staged."""
    mock_is_valid.return_value = True
    from chegi.services.commit import NoStagedFilesError

    mock_prepare.side_effect = NoStagedFilesError("No staged files found")

    result = runner.invoke(app, ["commit"])

    assert result.exit_code == 1
    assert "no staged files" in result.stdout.lower()


@patch("chegi.services.commit.commit_service.GitClient.run_command")
@patch("chegi.cli.commands.commit.GitClient.is_valid_repo")
@patch("chegi.cli.commands.commit.CommitService.prepare_context")
def test_commit_with_message_flag(
    mock_prepare: MagicMock,
    mock_is_valid: MagicMock,
    mock_run: MagicMock,
):
    """Test commit with -m flag uses provided message and skips prompt."""
    mock_is_valid.return_value = True
    mock_context = MagicMock()
    mock_context.staged_files = ["file.py"]
    mock_context.diff_stat = "file.py | 1 +"
    mock_context.is_safe = True
    mock_context.sensitive_files = []
    mock_context.suggested_messages = ["feat: add file"]
    mock_prepare.return_value = mock_context
    mock_run.return_value = "[main abc123] feat: add file"

    result = runner.invoke(app, ["commit", "-m", "feat: add file"])

    assert result.exit_code == 0
    assert "Commit successful" in result.stdout
    mock_run.assert_called_once_with(["git", "commit", "-m", "feat: add file"])


@patch("chegi.cli.commands.commit.GitClient.is_valid_repo")
@patch("chegi.cli.commands.commit.CommitService.prepare_context")
@patch("chegi.services.commit.commit_service.GitClient.run_command")
def test_commit_force_flag_skips_guard(
    mock_run: MagicMock,
    mock_prepare: MagicMock,
    mock_is_valid: MagicMock,
):
    """Test commit --force skips sensitive files warning."""
    mock_is_valid.return_value = True
    mock_context = MagicMock()
    mock_context.staged_files = [".env", "main.py"]
    mock_context.diff_stat = ".env | 1 +"
    mock_context.is_safe = False
    mock_context.sensitive_files = [".env"]
    mock_context.suggested_messages = []
    mock_prepare.return_value = mock_context
    mock_run.return_value = "[main abc123] commit"

    result = runner.invoke(app, ["commit", "-m", "test", "--force"])

    assert result.exit_code == 0
    assert "Commit successful" in result.stdout


@patch("chegi.cli.commands.commit.questionary")
@patch("chegi.cli.commands.commit.GitClient.is_valid_repo")
@patch("chegi.cli.commands.commit.CommitService.prepare_context")
def test_commit_sensitive_files_interactive_abort(
    mock_prepare: MagicMock,
    mock_is_valid: MagicMock,
    mock_questionary: MagicMock,
):
    """Test commit aborts when user selects abort in sensitive files prompt."""
    mock_is_valid.return_value = True
    mock_context = MagicMock()
    mock_context.staged_files = [".env", "main.py"]
    mock_context.diff_stat = ".env | 1 +"
    mock_context.is_safe = False
    mock_context.sensitive_files = [".env"]
    mock_context.suggested_messages = []
    mock_prepare.return_value = mock_context
    mock_questionary.select.return_value.ask.return_value = "abort"

    result = runner.invoke(app, ["commit"])

    assert result.exit_code == 1
    assert "Commit aborted" in result.stdout


@patch("chegi.cli.commands.commit.questionary")
@patch("chegi.cli.commands.commit.GitClient.is_valid_repo")
@patch("chegi.cli.commands.commit.CommitService.prepare_context")
@patch("chegi.cli.commands.commit.CommitService.unstage_files")
@patch("chegi.services.commit.commit_service.GitClient.run_command")
def test_commit_sensitive_files_interactive_unstage(
    mock_run: MagicMock,
    mock_unstage: MagicMock,
    mock_prepare: MagicMock,
    mock_is_valid: MagicMock,
    mock_questionary: MagicMock,
):
    """Test commit unstages sensitive files and continues on user choice."""
    mock_is_valid.return_value = True
    mock_context = MagicMock()
    mock_context.staged_files = [".env", "main.py"]
    mock_context.diff_stat = ".env | 1 +\nmain.py | 5 +++"
    mock_context.is_safe = False
    mock_context.sensitive_files = [".env"]
    mock_context.suggested_messages = ["feat: add main"]
    mock_prepare.return_value = mock_context
    mock_unstage.return_value = True
    mock_run.return_value = "[main abc123] feat: add main"
    mock_questionary.select.return_value.ask.return_value = "unstage"

    result = runner.invoke(app, ["commit", "-m", "feat: add main"])

    assert result.exit_code == 0
    assert "Commit successful" in result.stdout
    mock_unstage.assert_called_once_with([".env"])


@patch("chegi.services.commit.commit_service.GitClient.run_command")
@patch("chegi.cli.commands.commit.GitClient.is_valid_repo")
@patch("chegi.cli.commands.commit.CommitService.prepare_context")
def test_commit_shows_diff_stat(
    mock_prepare: MagicMock,
    mock_is_valid: MagicMock,
    mock_run: MagicMock,
):
    """Test commit displays diff stat to user."""
    mock_is_valid.return_value = True
    mock_context = MagicMock()
    mock_context.staged_files = ["main.py"]
    mock_context.diff_stat = "main.py | 10 ++++++++++"
    mock_context.is_safe = True
    mock_context.sensitive_files = []
    mock_context.suggested_messages = []
    mock_prepare.return_value = mock_context
    mock_run.return_value = "[main abc123] test"

    result = runner.invoke(app, ["commit", "-m", "test"])

    assert result.exit_code == 0
    assert "Staged Changes" in result.stdout


@patch("chegi.services.commit.commit_service.GitClient.run_command")
@patch("chegi.cli.commands.commit.GitClient.is_valid_repo")
@patch("chegi.cli.commands.commit.CommitService.prepare_context")
def test_commit_execution_failure(
    mock_prepare: MagicMock,
    mock_is_valid: MagicMock,
    mock_run: MagicMock,
):
    """Test commit handles execution failure gracefully."""
    mock_is_valid.return_value = True
    mock_context = MagicMock()
    mock_context.staged_files = ["main.py"]
    mock_context.diff_stat = "main.py | 1 +"
    mock_context.is_safe = True
    mock_context.sensitive_files = []
    mock_context.suggested_messages = []
    mock_prepare.return_value = mock_context
    from chegi.services.commit import CommitError

    mock_run.side_effect = CommitError("commit failed")

    result = runner.invoke(app, ["commit", "-m", "test"])

    assert result.exit_code == 1
    assert "Commit failed" in result.stdout


@patch("chegi.cli.commands.commit.questionary")
@patch("chegi.cli.commands.commit.GitClient.is_valid_repo")
@patch("chegi.cli.commands.commit.CommitService.prepare_context")
@patch("chegi.cli.commands.commit.CommitService.unstage_files")
@patch("chegi.services.commit.commit_service.GitClient.run_command")
def test_commit_unstage_and_no_files_remaining(
    mock_run: MagicMock,
    mock_unstage: MagicMock,
    mock_prepare: MagicMock,
    mock_is_valid: MagicMock,
    mock_questionary: MagicMock,
):
    """Test commit exits when all files are sensitive and user unstages them."""
    mock_is_valid.return_value = True
    mock_context = MagicMock()
    mock_context.staged_files = [".env"]
    mock_context.diff_stat = ".env | 1 +"
    mock_context.is_safe = False
    mock_context.sensitive_files = [".env"]
    mock_context.suggested_messages = []
    mock_prepare.return_value = mock_context
    mock_unstage.return_value = True
    mock_questionary.select.return_value.ask.return_value = "unstage"

    result = runner.invoke(app, ["commit"])

    assert result.exit_code == 1
    assert "No files remaining to commit" in result.stdout


@patch("chegi.cli.commands.commit.questionary")
@patch("chegi.cli.commands.commit.GitClient.is_valid_repo")
@patch("chegi.cli.commands.commit.CommitService.prepare_context")
@patch("chegi.cli.commands.commit.CommitService.unstage_files")
@patch("chegi.services.commit.commit_service.GitClient.run_command")
def test_commit_unstage_fails(
    mock_run: MagicMock,
    mock_unstage: MagicMock,
    mock_prepare: MagicMock,
    mock_is_valid: MagicMock,
    mock_questionary: MagicMock,
):
    """Test commit shows error when unstaging fails."""
    mock_is_valid.return_value = True
    mock_context = MagicMock()
    mock_context.staged_files = [".env", "main.py"]
    mock_context.diff_stat = ""
    mock_context.is_safe = False
    mock_context.sensitive_files = [".env"]
    mock_context.suggested_messages = []
    mock_prepare.return_value = mock_context
    mock_unstage.return_value = False
    mock_questionary.select.return_value.ask.return_value = "unstage"

    result = runner.invoke(app, ["commit"])

    assert result.exit_code == 1
    assert "Failed to unstage" in result.stdout


@patch("chegi.cli.commands.commit.questionary")
@patch("chegi.services.commit.commit_service.GitClient.run_command")
@patch("chegi.cli.commands.commit.GitClient.is_valid_repo")
@patch("chegi.cli.commands.commit.CommitService.prepare_context")
def test_commit_ch_flag_with_message(
    mock_prepare: MagicMock,
    mock_is_valid: MagicMock,
    mock_run: MagicMock,
    mock_questionary: MagicMock,
):
    """Test commit --ch appends brand suffix to subject line."""
    mock_is_valid.return_value = True
    mock_context = MagicMock()
    mock_context.staged_files = ["main.py"]
    mock_context.diff_stat = "main.py | 1 +"
    mock_context.is_safe = True
    mock_context.sensitive_files = []
    mock_context.suggested_messages = []
    mock_prepare.return_value = mock_context
    mock_run.return_value = "[main abc123] test"

    result = runner.invoke(app, ["commit", "-m", "feat: init project", "--ch"])

    assert result.exit_code == 0
    mock_run.assert_called_once_with(["git", "commit", "-m", "feat: init project 🐆"])


@patch("chegi.cli.commands.commit.questionary")
@patch("chegi.services.commit.commit_service.GitClient.run_command")
@patch("chegi.cli.commands.commit.GitClient.is_valid_repo")
@patch("chegi.cli.commands.commit.CommitService.prepare_context")
def test_commit_ch_flag_does_not_double_add(
    mock_prepare: MagicMock,
    mock_is_valid: MagicMock,
    mock_run: MagicMock,
    mock_questionary: MagicMock,
):
    """Test commit --ch does not double-add brand suffix."""
    mock_is_valid.return_value = True
    mock_context = MagicMock()
    mock_context.staged_files = ["main.py"]
    mock_context.diff_stat = "main.py | 1 +"
    mock_context.is_safe = True
    mock_context.sensitive_files = []
    mock_context.suggested_messages = []
    mock_prepare.return_value = mock_context
    mock_run.return_value = "[main abc123] test"

    result = runner.invoke(app, ["commit", "-m", "feat: init project 🐆", "--ch"])

    assert result.exit_code == 0
    mock_run.assert_called_once_with(["git", "commit", "-m", "feat: init project 🐆"])


@patch("chegi.cli.commands.commit.questionary")
@patch("chegi.services.commit.commit_service.GitClient.run_command")
@patch("chegi.cli.commands.commit.GitClient.is_valid_repo")
@patch("chegi.cli.commands.commit.CommitService.prepare_context")
@patch("chegi.cli.commands.commit.CommitStyleManager")
def test_commit_guided_flow(
    mock_mgr_cls: MagicMock,
    mock_prepare: MagicMock,
    mock_is_valid: MagicMock,
    mock_run: MagicMock,
    mock_questionary: MagicMock,
):
    """Test guided flow uses questionary for style selection and field input."""
    mock_is_valid.return_value = True
    mock_context = MagicMock()
    mock_context.staged_files = ["main.py"]
    mock_context.diff_stat = "main.py | 1 +"
    mock_context.is_safe = True
    mock_context.sensitive_files = []
    mock_context.suggested_messages = ["feat: add main"]
    mock_context.name_status = [("A", "main.py")]
    mock_prepare.return_value = mock_context
    mock_run.return_value = "[main abc123] test"

    # Mock style manager
    mock_style_mgr = MagicMock()
    from chegi.services.commit import CommitStyle

    style = CommitStyle(
        name="free",
        label="Free",
        description="just a message",
        fields=["description"],
    )
    mock_style_mgr.get_styles.return_value = [style]
    mock_style_mgr.get_last_style.return_value = None
    mock_mgr_cls.return_value = mock_style_mgr

    # Mock questionary flow:
    # 1. select style -> style object
    # 2. text description -> "init project"
    # 3. confirm -> True
    mock_questionary.select.return_value.ask.side_effect = [
        style,
    ]
    mock_questionary.text.return_value.ask.side_effect = [
        "init project",
    ]
    mock_questionary.confirm.return_value.ask.return_value = True

    result = runner.invoke(app, ["commit"])

    assert result.exit_code == 0
    mock_style_mgr.save_last_style.assert_called_once_with("free")
    mock_run.assert_called_once_with(["git", "commit", "-m", "Init project"])


@patch("chegi.cli.commands.commit.questionary")
@patch("chegi.services.commit.commit_service.GitClient.run_command")
@patch("chegi.cli.commands.commit.GitClient.is_valid_repo")
@patch("chegi.cli.commands.commit.CommitService.prepare_context")
@patch("chegi.cli.commands.commit.CommitStyleManager")
def test_commit_guided_flow_preview_confirms(
    mock_mgr_cls: MagicMock,
    mock_prepare: MagicMock,
    mock_is_valid: MagicMock,
    mock_run: MagicMock,
    mock_questionary: MagicMock,
):
    """Test guided flow shows preview and asks for confirmation."""
    mock_is_valid.return_value = True
    mock_context = MagicMock()
    mock_context.staged_files = ["main.py"]
    mock_context.diff_stat = "main.py | 1 +"
    mock_context.is_safe = True
    mock_context.sensitive_files = []
    mock_context.suggested_messages = []
    mock_context.name_status = []
    mock_prepare.return_value = mock_context
    mock_run.return_value = "[main abc123] test"

    mock_style_mgr = MagicMock()
    from chegi.services.commit import CommitStyle

    style = CommitStyle(
        name="free",
        label="Free",
        description="",
        fields=["description"],
    )
    mock_style_mgr.get_styles.return_value = [style]
    mock_style_mgr.get_last_style.return_value = None
    mock_style_mgr.should_show_hint.return_value = False
    mock_mgr_cls.return_value = mock_style_mgr

    mock_questionary.select.return_value.ask.return_value = style
    mock_questionary.text.return_value.ask.return_value = "init project"
    mock_questionary.confirm.return_value.ask.return_value = True

    result = runner.invoke(app, ["commit"])

    assert result.exit_code == 0
    assert "Commit Preview" in result.stdout
    assert "Init project" in result.stdout


@patch("chegi.cli.commands.commit.questionary")
@patch("chegi.services.commit.commit_service.GitClient.run_command")
@patch("chegi.cli.commands.commit.GitClient.is_valid_repo")
@patch("chegi.cli.commands.commit.CommitService.prepare_context")
@patch("chegi.cli.commands.commit.CommitStyleManager")
def test_commit_guided_flow_cancel(
    mock_mgr_cls: MagicMock,
    mock_prepare: MagicMock,
    mock_is_valid: MagicMock,
    mock_run: MagicMock,
    mock_questionary: MagicMock,
):
    """Test guided flow exits when user cancels at style selection."""
    mock_is_valid.return_value = True
    mock_context = MagicMock()
    mock_context.staged_files = ["main.py"]
    mock_context.diff_stat = "main.py | 1 +"
    mock_context.is_safe = True
    mock_context.sensitive_files = []
    mock_context.suggested_messages = []
    mock_context.name_status = []
    mock_prepare.return_value = mock_context

    mock_style_mgr = MagicMock()
    from chegi.services.commit import CommitStyle

    style = CommitStyle(
        name="free",
        label="Free",
        description="",
        fields=["description"],
    )
    mock_style_mgr.get_styles.return_value = [style]
    mock_style_mgr.get_last_style.return_value = None
    mock_mgr_cls.return_value = mock_style_mgr

    mock_questionary.select.return_value.ask.return_value = style
    mock_questionary.text.return_value.ask.return_value = None

    result = runner.invoke(app, ["commit"])

    assert result.exit_code == 1
    assert "Commit aborted" in result.stdout


@patch("chegi.cli.commands.commit.questionary")
@patch("chegi.services.commit.commit_service.GitClient.run_command")
@patch("chegi.cli.commands.commit.GitClient.is_valid_repo")
@patch("chegi.cli.commands.commit.CommitService.prepare_context")
@patch("chegi.cli.commands.commit.CommitStyleManager")
def test_commit_guided_flow_brand_hint(
    mock_mgr_cls: MagicMock,
    mock_prepare: MagicMock,
    mock_is_valid: MagicMock,
    mock_run: MagicMock,
    mock_questionary: MagicMock,
):
    """Test guided flow shows brand hint on first single-line commit."""
    mock_is_valid.return_value = True
    mock_context = MagicMock()
    mock_context.staged_files = ["main.py"]
    mock_context.diff_stat = "main.py | 1 +"
    mock_context.is_safe = True
    mock_context.sensitive_files = []
    mock_context.suggested_messages = []
    mock_context.name_status = []
    mock_prepare.return_value = mock_context
    mock_run.return_value = "[main abc123] test"

    mock_style_mgr = MagicMock()
    from chegi.services.commit import CommitStyle

    style = CommitStyle(
        name="free",
        label="Free",
        description="",
        fields=["description"],
    )
    mock_style_mgr.get_styles.return_value = [style]
    mock_style_mgr.get_last_style.return_value = None
    mock_style_mgr.should_show_hint.return_value = True
    mock_mgr_cls.return_value = mock_style_mgr

    mock_questionary.select.return_value.ask.return_value = style
    mock_questionary.text.return_value.ask.return_value = "init"
    mock_questionary.confirm.return_value.ask.return_value = True

    result = runner.invoke(app, ["commit"])

    assert result.exit_code == 0
    assert "chegi commit --ch" in result.stdout
    mock_style_mgr.mark_hint_shown.assert_called_once_with("commit_brand")
