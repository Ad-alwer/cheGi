"""Tests for CommitService."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from chegi.services.commit import CommitError, CommitService, NoStagedFilesError
from chegi.services.commit.models import CommitContext, CommitStyle

TEST_REPO = Path("/fake/repo")


@patch("chegi.services.commit.commit_service.GitClient.is_valid_repo")
@patch("chegi.services.commit.commit_service.CommitService._get_staged_files")
@patch("chegi.services.commit.commit_service.CommitService._get_diff_stat")
@patch("chegi.services.commit.commit_service.CommitService._get_diff_name_status")
@patch("chegi.services.commit.commit_service.CommitService._scan_staged_files")
@patch("chegi.services.commit.commit_service.CommitService.suggest_messages")
def test_prepare_context_basic(
    mock_suggest: MagicMock,
    mock_scan: MagicMock,
    mock_name_status: MagicMock,
    mock_diff_stat: MagicMock,
    mock_staged: MagicMock,
    mock_valid: MagicMock,
):
    """Test preparing a commit context with staged files."""
    mock_valid.return_value = True
    mock_staged.return_value = ["file1.py", "file2.py"]
    mock_diff_stat.return_value = "file1.py | 5 +++++"
    mock_name_status.return_value = [("M", "file1.py"), ("A", "file2.py")]
    mock_scan.return_value = MagicMock(is_safe=True, sensitive_files=[])
    mock_suggest.return_value = ["feat: add file2", "chore: update 1 file(s)"]

    service = CommitService(TEST_REPO)
    context = service.prepare_context()

    assert isinstance(context, CommitContext)
    assert context.staged_files == ["file1.py", "file2.py"]
    assert context.diff_stat == "file1.py | 5 +++++"
    assert context.name_status == [("M", "file1.py"), ("A", "file2.py")]
    assert context.is_safe is True
    assert context.sensitive_files == []
    assert context.suggested_messages == [
        "feat: add file2",
        "chore: update 1 file(s)",
    ]


@patch("chegi.services.commit.commit_service.GitClient.is_valid_repo")
def test_prepare_context_not_a_repo(mock_valid: MagicMock):
    """Test prepare_context raises error when not in a git repo."""
    mock_valid.return_value = False

    service = CommitService(TEST_REPO)
    try:
        service.prepare_context()
        assert False, "Expected CommitError"
    except CommitError as e:
        assert "Not a valid Git repository" in str(e)


@patch("chegi.services.commit.commit_service.GitClient.is_valid_repo")
@patch("chegi.services.commit.commit_service.CommitService._get_staged_files")
def test_prepare_context_no_staged_files(mock_staged: MagicMock, mock_valid: MagicMock):
    """Test prepare_context raises NoStagedFilesError when no files are staged."""
    mock_valid.return_value = True
    mock_staged.return_value = []

    service = CommitService(TEST_REPO)
    try:
        service.prepare_context()
        assert False, "Expected NoStagedFilesError"
    except NoStagedFilesError as e:
        assert "No staged files found" in str(e)


@patch("chegi.services.commit.commit_service.GitClient.is_valid_repo")
@patch("chegi.services.commit.commit_service.CommitService._get_staged_files")
@patch("chegi.services.commit.commit_service.CommitService._get_diff_stat")
@patch("chegi.services.commit.commit_service.CommitService._get_diff_name_status")
@patch("chegi.services.commit.commit_service.CommitService._scan_staged_files")
@patch("chegi.services.commit.commit_service.CommitService.suggest_messages")
def test_prepare_context_sensitive_files_detected(
    mock_suggest: MagicMock,
    mock_scan: MagicMock,
    mock_name_status: MagicMock,
    mock_diff_stat: MagicMock,
    mock_staged: MagicMock,
    mock_valid: MagicMock,
):
    """Test prepare_context correctly reports sensitive files."""
    mock_valid.return_value = True
    mock_staged.return_value = [".env", "main.py"]
    mock_diff_stat.return_value = ""
    mock_name_status.return_value = [("A", ".env"), ("A", "main.py")]
    mock_scan.return_value = MagicMock(is_safe=False, sensitive_files=[".env"])
    mock_suggest.return_value = []

    service = CommitService(TEST_REPO)
    context = service.prepare_context()

    assert context.is_safe is False
    assert context.sensitive_files == [".env"]


@patch("chegi.services.commit.commit_service.GitClient.is_valid_repo")
@patch("chegi.services.commit.commit_service.SecurityGuard.unstage_files")
@patch("chegi.services.commit.commit_service.CommitService._get_staged_files")
@patch("chegi.services.commit.commit_service.CommitService._get_diff_stat")
@patch("chegi.services.commit.commit_service.CommitService._get_diff_name_status")
@patch("chegi.services.commit.commit_service.CommitService._scan_staged_files")
@patch("chegi.services.commit.commit_service.CommitService.suggest_messages")
def test_unstage_files(
    mock_suggest: MagicMock,
    mock_scan: MagicMock,
    mock_name_status: MagicMock,
    mock_diff_stat: MagicMock,
    mock_staged: MagicMock,
    mock_unstage: MagicMock,
    mock_valid: MagicMock,
):
    """Test unstaging files delegates to SecurityGuard."""
    mock_valid.return_value = True
    mock_staged.return_value = [".env", "main.py"]
    mock_diff_stat.return_value = ""
    mock_name_status.return_value = [("A", ".env"), ("A", "main.py")]
    mock_scan.return_value = MagicMock(is_safe=False, sensitive_files=[".env"])
    mock_suggest.return_value = []
    mock_unstage.return_value = True

    service = CommitService(TEST_REPO)
    result = service.unstage_files([".env"])

    assert result is True
    mock_unstage.assert_called_once_with([".env"], TEST_REPO)


def test_suggest_messages_empty():
    """Test suggest_messages returns empty list for empty input."""
    service = CommitService(TEST_REPO)
    assert service.suggest_messages([]) == []


def test_suggest_messages_additions():
    """Test suggest_messages with added files generates feat suggestion."""
    service = CommitService(TEST_REPO)
    name_status = [("A", "src/auth/login.py"), ("A", "src/auth/register.py")]
    suggestions = service.suggest_messages(name_status)

    assert len(suggestions) >= 1
    assert any("feat" in s for s in suggestions)
    assert any("auth" in s for s in suggestions)
    assert any("feat(auth)" in s for s in suggestions)


def test_suggest_messages_modifications():
    """Test suggest_messages with modified files generates fix suggestion."""
    service = CommitService(TEST_REPO)
    name_status = [("M", "src/core/handler.py"), ("M", "src/core/utils.py")]
    suggestions = service.suggest_messages(name_status)

    assert len(suggestions) >= 1
    assert any("fix" in s for s in suggestions)
    assert any("core" in s for s in suggestions)
    assert any("fix(core)" in s for s in suggestions)


def test_suggest_messages_deletions():
    """Test suggest_messages with deleted files generates refactor suggestion."""
    service = CommitService(TEST_REPO)
    name_status = [("D", "src/old/legacy.py")]
    suggestions = service.suggest_messages(name_status)

    assert len(suggestions) >= 1
    assert any("refactor" in s for s in suggestions)


def test_suggest_messages_tests():
    """Test suggest_messages with test files generates test suggestion."""
    service = CommitService(TEST_REPO)
    name_status = [("A", "tests/test_auth.py"), ("M", "tests/test_user.py")]
    suggestions = service.suggest_messages(name_status)

    assert len(suggestions) >= 1
    assert any("test" in s for s in suggestions)


def test_suggest_messages_docs():
    """Test suggest_messages with doc files generates docs suggestion."""
    service = CommitService(TEST_REPO)
    name_status = [("M", "docs/guide.md"), ("M", "README.md")]
    suggestions = service.suggest_messages(name_status)

    assert len(suggestions) >= 1
    assert any("docs" in s for s in suggestions)


def test_suggest_messages_limits_to_three():
    """Test suggest_messages returns at most 3 suggestions."""
    service = CommitService(TEST_REPO)
    name_status = [
        ("A", "a.py"),
        ("A", "b.py"),
        ("A", "c.py"),
        ("A", "d.py"),
        ("A", "e.py"),
    ]
    suggestions = service.suggest_messages(name_status)
    assert len(suggestions) <= 3


def test_suggest_messages_no_scope_for_root_files():
    """Test suggest_messages produces messages without scope for root files."""
    service = CommitService(TEST_REPO)
    name_status = [("A", "main.py")]
    suggestions = service.suggest_messages(name_status)
    assert len(suggestions) >= 1
    assert "feat:" in suggestions[0]


@patch("chegi.services.commit.commit_service.GitClient.run_command")
def test_execute_commit(mock_run: MagicMock):
    """Test execute_commit calls git commit with message."""
    mock_run.return_value = "[main abc1234] test message"

    service = CommitService(TEST_REPO)
    result = service.execute_commit("test message")

    assert result == "[main abc1234] test message"
    mock_run.assert_called_once_with(["git", "commit", "-m", "test message"])


@patch("chegi.services.commit.commit_service.GitClient.run_command")
def test_execute_commit_failure(mock_run: MagicMock):
    """Test execute_commit raises CommitError on failure."""
    mock_run.side_effect = Exception("git error")

    service = CommitService(TEST_REPO)
    try:
        service.execute_commit("test")
        assert False, "Expected CommitError"
    except CommitError as e:
        assert "Commit failed" in str(e)


def test_get_staged_files_empty():
    """Test _get_staged_files returns empty list when no output."""
    service = CommitService(TEST_REPO)

    with patch.object(service.git_client, "run_command", return_value=""):
        assert service._get_staged_files() == []


def test_get_staged_files_success():
    """Test _get_staged_files parses output correctly."""
    service = CommitService(TEST_REPO)

    with patch.object(
        service.git_client,
        "run_command",
        return_value="file1.py\nfile2.py\n",
    ):
        result = service._get_staged_files()
        assert result == ["file1.py", "file2.py"]


def test_get_diff_name_status_empty():
    """Test _get_diff_name_status returns empty list when no output."""
    service = CommitService(TEST_REPO)

    with patch.object(service.git_client, "run_command", return_value=""):
        assert service._get_diff_name_status() == []


def test_get_diff_name_status_success():
    """Test _get_diff_name_status parses output correctly."""
    service = CommitService(TEST_REPO)

    with patch.object(
        service.git_client,
        "run_command",
        return_value="M\tfile1.py\nA\tfile2.py\n",
    ):
        result = service._get_diff_name_status()
        assert result == [("M", "file1.py"), ("A", "file2.py")]


def test_describe_files_empty():
    """Test _describe_files returns 'update' for empty list."""
    service = CommitService(TEST_REPO)
    assert service._describe_files([]) == "update"


def test_describe_files_returns_stem():
    """Test _describe_files extracts stem from file path."""
    service = CommitService(TEST_REPO)
    result = service._describe_files(["src/user_profile.py"])
    assert "user profile" in result


# --- build_message tests ---


def test_build_message_free():
    """Test build_message with free style."""
    style = CommitStyle(
        name="free", label="Free", description="", fields=["description"]
    )
    result = CommitService.build_message(style, {"description": "init project"})
    assert result == "Init project"


def test_build_message_conventional():
    """Test build_message with conventional style."""
    style = CommitStyle(
        name="conventional",
        label="Conventional",
        description="",
        fields=["type", "description"],
        types=["feat", "fix"],
    )
    result = CommitService.build_message(
        style, {"type": "feat", "description": "init project"}
    )
    assert result == "feat: Init project"


def test_build_message_conventional_scope():
    """Test build_message with conventional-scope style."""
    style = CommitStyle(
        name="conventional-scope",
        label="Conventional with scope",
        description="",
        fields=["type", "scope", "description"],
        types=["feat", "fix"],
    )
    result = CommitService.build_message(
        style,
        {"type": "feat", "scope": "init", "description": "setup project"},
    )
    assert result == "feat(init): Setup project"


def test_build_message_conventional_scope_empty():
    """Test build_message without scope when scope is empty."""
    style = CommitStyle(
        name="conventional-scope",
        label="Conventional with scope",
        description="",
        fields=["type", "scope", "description"],
        types=["feat", "fix"],
    )
    result = CommitService.build_message(
        style, {"type": "feat", "scope": "", "description": "init"}
    )
    assert result == "feat: Init"


def test_build_message_conventional_body():
    """Test build_message with conventional-body style including body."""
    style = CommitStyle(
        name="conventional-body",
        label="Conventional with body",
        description="",
        fields=["type", "scope", "description", "body"],
        types=["feat", "fix"],
    )
    result = CommitService.build_message(
        style,
        {
            "type": "feat",
            "scope": "auth",
            "description": "add login",
            "body": "- implement JWT\n- add refresh",
        },
    )
    assert "feat(auth): Add login" in result
    assert "- implement JWT" in result
    assert "- add refresh" in result


def test_build_message_gitmoji():
    """Test build_message with gitmoji style."""
    style = CommitStyle(
        name="gitmoji",
        label="Gitmoji",
        description="",
        fields=["emoji", "type", "description"],
        types=["feat", "fix"],
        emojis={"feat": "✨", "fix": "🐛"},
    )
    result = CommitService.build_message(
        style, {"type": "feat", "emoji": "✨", "description": "add login"}
    )
    assert result == "✨ feat: Add login"


def test_build_message_gitmoji_missing_emoji():
    """Test build_message handles missing emoji gracefully."""
    style = CommitStyle(
        name="gitmoji",
        label="Gitmoji",
        description="",
        fields=["emoji", "type", "description"],
        types=["feat", "fix"],
        emojis={"feat": "✨"},
    )
    result = CommitService.build_message(
        style, {"type": "fix", "emoji": "🐛", "description": "bug"}
    )
    assert result == "fix: Bug"


def test_build_message_empty_description_free():
    """Test build_message with free style and empty description."""
    style = CommitStyle(
        name="free", label="Free", description="", fields=["description"]
    )
    result = CommitService.build_message(style, {"description": ""})
    assert result == ""


# --- apply_brand_suffix tests ---


def test_apply_brand_suffix_single_line():
    """Test apply_brand_suffix adds suffix to single-line message."""
    result = CommitService.apply_brand_suffix("feat: init project")
    assert result == "feat: init project 🐆"


def test_apply_brand_suffix_multiline():
    """Test apply_brand_suffix only affects subject line."""
    message = "feat(auth): Add login\n\n- implement JWT\n- add refresh"
    result = CommitService.apply_brand_suffix(message)
    lines = result.split("\n")
    assert lines[0].endswith("🐆")
    assert lines[2] == "- implement JWT"
    assert lines[3] == "- add refresh"


def test_apply_brand_suffix_already_present():
    """Test apply_brand_suffix does not double-add the suffix."""
    message = "feat: init project 🐆"
    result = CommitService.apply_brand_suffix(message)
    assert result == "feat: init project 🐆"
    assert result.count("🐆") == 1


def test_apply_brand_suffix_empty():
    """Test apply_brand_suffix handles empty string."""
    result = CommitService.apply_brand_suffix("")
    assert result == " 🐆"


def test_suggest_messages_detects_deep_scope():
    """Test suggest_messages detects scope from deepest common directory."""
    service = CommitService(TEST_REPO)
    name_status = [
        ("M", "src/services/auth/login.py"),
        ("M", "src/services/auth/register.py"),
    ]
    suggestions = service.suggest_messages(name_status)

    assert any("auth" in s for s in suggestions)


def test_suggest_messages_scope_for_mixed_dirs():
    """Test suggest_messages handles files in different directories."""
    service = CommitService(TEST_REPO)
    name_status = [
        ("M", "src/auth.py"),
        ("M", "src/user.py"),
    ]
    suggestions = service.suggest_messages(name_status)

    assert len(suggestions) >= 1
    assert any("src" in s for s in suggestions)
