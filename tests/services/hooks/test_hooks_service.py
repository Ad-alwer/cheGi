"""Tests for the HooksService class."""

import shutil
import stat
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from chegi.services.hooks.constants import CHEGI_HOOK_MARKER
from chegi.services.hooks.exceptions import HookInstallError, HookRemoveError
from chegi.services.hooks.hooks_service import HooksService


def _init_repo(path: Path) -> None:
    """Initialize a real Git repository at the given path."""
    subprocess.run(["git", "init"], cwd=path, capture_output=True, check=True)


class TestHooksServiceInstall:
    """Tests for HooksService.install()."""

    def test_install_creates_hook(self, tmp_path: Path) -> None:
        """Test that install() creates the pre-commit hook file."""
        _init_repo(tmp_path)
        service = HooksService(tmp_path)
        hook_path = service.install()
        assert hook_path.exists()
        content = hook_path.read_text()
        assert CHEGI_HOOK_MARKER in content
        assert "chegi guard --fix" in content

    def test_install_makes_executable(self, tmp_path: Path) -> None:
        """Test that install() makes the hook file executable."""
        _init_repo(tmp_path)
        service = HooksService(tmp_path)
        hook_path = service.install()
        st = hook_path.stat()
        assert st.st_mode & stat.S_IXUSR
        assert st.st_mode & stat.S_IXGRP
        assert st.st_mode & stat.S_IXOTH

    def test_install_on_non_repo_raises(self, tmp_path: Path) -> None:
        """Test that install() raises HookInstallError on non-repo."""
        service = HooksService(tmp_path)
        with pytest.raises(HookInstallError, match="Not a valid Git repository"):
            service.install()

    def test_install_without_force_on_existing_hook_raises(
        self,
        tmp_path: Path,
    ) -> None:
        """Test that install() raises when a non-chegi hook already exists."""
        _init_repo(tmp_path)
        hooks_dir = tmp_path / ".git" / "hooks"
        existing = hooks_dir / "pre-commit"
        existing.write_text("#!/bin/sh\necho 'custom hook'")
        existing.chmod(0o755)

        service = HooksService(tmp_path)
        with pytest.raises(HookInstallError, match="already exists"):
            service.install()

    def test_install_with_force_overwrites_existing(
        self,
        tmp_path: Path,
    ) -> None:
        """Test that install(force=True) overwrites an existing hook."""
        _init_repo(tmp_path)
        hooks_dir = tmp_path / ".git" / "hooks"
        existing = hooks_dir / "pre-commit"
        existing.write_text("#!/bin/sh\necho 'custom hook'")
        existing.chmod(0o755)

        service = HooksService(tmp_path)
        hook_path = service.install(force=True)
        content = hook_path.read_text()
        assert CHEGI_HOOK_MARKER in content

    def test_install_creates_hooks_dir_if_missing(self, tmp_path: Path) -> None:
        """Test that install() creates the hooks directory if needed."""
        _init_repo(tmp_path)
        hooks_dir = tmp_path / ".git" / "hooks"
        shutil.rmtree(str(hooks_dir))

        service = HooksService(tmp_path)
        hook_path = service.install()
        assert hook_path.parent.exists()
        assert hook_path.exists()

    @patch("chegi.services.hooks.hooks_service.Path.write_text")
    def test_install_raises_on_write_error(
        self,
        mock_write: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that install() raises HookInstallError on write failure."""
        _init_repo(tmp_path)
        mock_write.side_effect = OSError("Permission denied")

        service = HooksService(tmp_path)
        with pytest.raises(HookInstallError, match="Failed to write"):
            service.install()

    def test_install_with_force_on_existing_chegi_hook_raises(
        self,
        tmp_path: Path,
    ) -> None:
        """Test that install() without force raises even for chegi hooks."""
        _init_repo(tmp_path)
        service = HooksService(tmp_path)
        service.install()

        with pytest.raises(HookInstallError, match="already installed"):
            service.install()


class TestHooksServiceRemove:
    """Tests for HooksService.remove()."""

    def test_remove_removes_hook(self, tmp_path: Path) -> None:
        """Test that remove() deletes the cheGi hook file."""
        _init_repo(tmp_path)
        service = HooksService(tmp_path)
        service.install()
        assert service.remove() is True
        assert not service._hook_path().exists()

    def test_remove_returns_false_when_no_hook(self, tmp_path: Path) -> None:
        """Test that remove() returns False when no hook exists."""
        service = HooksService(tmp_path)
        assert service.remove() is False

    def test_remove_leaves_non_chegi_hook(self, tmp_path: Path) -> None:
        """Test that remove() does not delete non-cheGi hooks."""
        _init_repo(tmp_path)
        hooks_dir = tmp_path / ".git" / "hooks"
        existing = hooks_dir / "pre-commit"
        existing.write_text("#!/bin/sh\necho 'custom'")
        existing.chmod(0o755)

        service = HooksService(tmp_path)
        assert service.remove() is False
        assert existing.exists()

    @patch("chegi.services.hooks.hooks_service.Path.unlink")
    def test_remove_raises_on_error(
        self,
        mock_unlink: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that remove() raises HookRemoveError on failure."""
        _init_repo(tmp_path)
        service = HooksService(tmp_path)
        service.install()
        mock_unlink.side_effect = OSError("Permission denied")

        with pytest.raises(HookRemoveError, match="Failed to remove"):
            service.remove()


class TestHooksServiceIsInstalled:
    """Tests for HooksService.is_installed()."""

    def test_is_installed_returns_true(self, tmp_path: Path) -> None:
        """Test that is_installed returns True after install."""
        _init_repo(tmp_path)
        service = HooksService(tmp_path)
        service.install()
        info = service.is_installed()
        assert info.installed is True

    def test_is_installed_returns_false(self, tmp_path: Path) -> None:
        """Test that is_installed returns False before install."""
        service = HooksService(tmp_path)
        info = service.is_installed()
        assert info.installed is False

    def test_is_installed_returns_false_for_custom_hook(
        self,
        tmp_path: Path,
    ) -> None:
        """Test that is_installed returns False for non-cheGi hooks."""
        _init_repo(tmp_path)
        hooks_dir = tmp_path / ".git" / "hooks"
        existing = hooks_dir / "pre-commit"
        existing.write_text("#!/bin/sh\necho 'custom'")
        existing.chmod(0o755)

        service = HooksService(tmp_path)
        info = service.is_installed()
        assert info.installed is False
