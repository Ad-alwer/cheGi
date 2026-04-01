from pathlib import Path

import pytest

from chegi.config import ChegiConfig
from chegi.scanner import find_git_repos


def create_mock_repo(base_dir: Path, repo_path: str) -> Path:
    """Helper function to create a mock Git repository structure for testing.

    Args:
        base_dir (Path): The base temporary directory.
        repo_path (str): The relative path for the new mock repository.

    Returns:
        Path: The absolute path to the newly created mock repository.
    """
    full_path = base_dir / repo_path
    full_path.mkdir(parents=True, exist_ok=True)

    # Create the fake .git directory
    git_dir = full_path / ".git"
    git_dir.mkdir(exist_ok=True)

    return full_path


def test_find_basic_repo(tmp_path: Path):
    """Test if a standard, single Git repository is found correctly.

    Args:
        tmp_path (Path): Built-in pytest fixture for temporary directories.
    """
    create_mock_repo(tmp_path, "my_project")

    config = ChegiConfig(base_path=str(tmp_path))
    config.max_depth = 3

    repos = list(find_git_repos(str(tmp_path), config))

    assert len(repos) == 1
    assert repos[0].name == "my_project"


def test_exclude_directories(tmp_path: Path):
    """Test if the scanner properly ignores blacklisted directories.

    Args:
        tmp_path (Path): Built-in pytest fixture for temporary directories.
    """
    create_mock_repo(tmp_path, "valid_repo")
    create_mock_repo(tmp_path, "node_modules/ignored_repo")
    create_mock_repo(tmp_path, ".venv/another_ignored")

    config = ChegiConfig(base_path=str(tmp_path))
    config.max_depth = 3
    config.exclude_dirs = {"node_modules", ".venv"}

    repos = list(find_git_repos(str(tmp_path), config))

    assert len(repos) == 1
    assert repos[0].name == "valid_repo"


def test_max_depth_limit(tmp_path: Path):
    """Test if the scanner accurately halts traversal at the specified max_depth.

    Args:
        tmp_path (Path): Built-in pytest fixture for temporary directories.
    """
    # Depth level: tmp_path (0) -> level1 (1) -> level2 (2) -> deep_repo (3)
    create_mock_repo(tmp_path, "level1/level2/deep_repo")

    config_shallow = ChegiConfig(base_path=str(tmp_path))
    config_shallow.max_depth = 3
    repos_shallow = list(find_git_repos(str(tmp_path), config_shallow))
    assert len(repos_shallow) == 0

    config_deep = ChegiConfig(base_path=str(tmp_path))
    config_deep.max_depth = 4
    repos_deep = list(find_git_repos(str(tmp_path), config_deep))
    assert len(repos_deep) == 1
    assert repos_deep[0].name == "deep_repo"


def test_smart_pruning_nested_repos(tmp_path: Path):
    """Test that subdirectories of a discovered repository are not scanned.

    Ensures that nested repositories (like submodules) are pruned from the scan.

    Args:
        tmp_path (Path): Built-in pytest fixture for temporary directories.
    """
    parent_repo = create_mock_repo(tmp_path, "parent_repo")
    create_mock_repo(parent_repo, "nested_submodule")

    config = ChegiConfig(base_path=str(tmp_path))
    config.max_depth = 5
    repos = list(find_git_repos(str(tmp_path), config))

    assert len(repos) == 1
    assert repos[0].name == "parent_repo"


def test_invalid_start_path(tmp_path: Path):
    """Test if an invalid path gracefully raises a NotADirectoryError.

    Args:
        tmp_path (Path): Built-in pytest fixture for temporary directories.
    """
    invalid_path = str(tmp_path / "does_not_exist")
    config = ChegiConfig(base_path=str(tmp_path))

    with pytest.raises(NotADirectoryError, match="does not exist"):
        list(find_git_repos(invalid_path, config))
