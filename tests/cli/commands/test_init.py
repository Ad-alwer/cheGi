"""Tests for the chegi init CLI command."""

from pathlib import Path

from typer.testing import CliRunner

from chegi.cli.main import app

runner = CliRunner()


class TestInitCli:
    """Tests for the chegi init CLI command."""

    def test_init_creates_chegi_directory(self, tmp_path: Path) -> None:
        """Test that chegi init creates a .chegi/ directory with default files."""
        result = runner.invoke(app, ["init", "--path", str(tmp_path)])
        assert result.exit_code == 0
        assert "cheGi project initialized" in result.stdout

        chegi_dir = tmp_path / ".chegi"
        assert chegi_dir.is_dir()
        assert (chegi_dir / "config.json").is_file()
        assert (chegi_dir / "guard-rules.json").is_file()
        assert (chegi_dir / ".chegiignore").is_file()

    def test_init_defaults_to_cwd(self, tmp_path: Path) -> None:
        """Test that chegi init with no path uses current directory."""
        result = runner.invoke(app, ["init", "--path", str(tmp_path)])
        assert result.exit_code == 0
        assert (tmp_path / ".chegi").is_dir()

    def test_init_fails_already_exists(self, tmp_path: Path) -> None:
        """Test that chegi init warns when .chegi/ already exists."""
        (tmp_path / ".chegi").mkdir()

        result = runner.invoke(app, ["init", "--path", str(tmp_path)])
        assert result.exit_code == 1
        assert "already exists" in result.stdout

    def test_init_with_force_overwrites(self, tmp_path: Path) -> None:
        """Test that chegi init --force overwrites an existing .chegi/ directory."""
        chegi_dir = tmp_path / ".chegi"
        chegi_dir.mkdir()
        old_file = chegi_dir / "old_config.json"
        old_file.write_text("old")

        result = runner.invoke(app, ["init", "--path", str(tmp_path), "--force"])
        assert result.exit_code == 0
        assert "cheGi project initialized" in result.stdout

        # Old file should be gone, new files present
        assert not old_file.exists()
        assert (chegi_dir / "config.json").is_file()

    def test_init_fails_on_nonexistent_path(self) -> None:
        """Test that chegi init fails on a non-existent directory."""
        result = runner.invoke(
            app, ["init", "--path", "/path/that/does/not/exist/99999"]
        )
        assert result.exit_code == 1
        assert "Directory does not exist" in result.stdout
