from pathlib import Path
from unittest.mock import MagicMock

import pytest

from chegi.utils.finder import find_git_repos


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.max_depth = 3
    config.exclude_dirs = ["node_modules", "venv"]
    return config


def test_find_git_repos_invalid_dir(mock_config):
    with pytest.raises(NotADirectoryError, match="does not exist or is not a directory"):
        list(find_git_repos("/path/that/does/not/exist/12345", mock_config))


def test_find_git_repos_success(tmp_path: Path, mock_config):
    # Setup dummy directory structure
    repo1 = tmp_path / "project1"
    repo1.mkdir()
    (repo1 / ".git").mkdir()

    repo2 = tmp_path / "project2"
    repo2.mkdir()
    # using a file named .git instead of dir (e.g. worktrees/submodules)
    (repo2 / ".git").touch()

    not_repo = tmp_path / "project3"
    not_repo.mkdir()

    repos = list(find_git_repos(str(tmp_path), mock_config))
    
    assert len(repos) == 2
    assert repo1.resolve() in repos
    assert repo2.resolve() in repos


def test_find_git_repos_max_depth(tmp_path: Path, mock_config):
    mock_config.max_depth = 2

    deep_repo = tmp_path / "level1" / "level2" / "repo"
    deep_repo.mkdir(parents=True)
    (deep_repo / ".git").mkdir()

    shallow_repo = tmp_path / "repo2"
    shallow_repo.mkdir()
    (shallow_repo / ".git").mkdir()

    repos = list(find_git_repos(str(tmp_path), mock_config))
    
    assert len(repos) == 1
    assert shallow_repo.resolve() in repos



def test_find_git_repos_exclude_and_hidden(tmp_path: Path, mock_config):
    # Excluded directory
    excluded_dir = tmp_path / "node_modules" / "repo"
    excluded_dir.mkdir(parents=True)
    (excluded_dir / ".git").mkdir()

    # Hidden directory
    hidden_dir = tmp_path / ".hidden_folder" / "repo"
    hidden_dir.mkdir(parents=True)
    (hidden_dir / ".git").mkdir()

    valid_repo = tmp_path / "valid_repo"
    valid_repo.mkdir()
    (valid_repo / ".git").mkdir()

    repos = list(find_git_repos(str(tmp_path), mock_config))
    
    assert len(repos) == 1
    assert valid_repo.resolve() in repos


def test_find_git_repos_smart_pruning(tmp_path: Path, mock_config):
    """Ensures that once a repo is found, it does not scan its subdirectories."""
    parent_repo = tmp_path / "parent_repo"
    parent_repo.mkdir()
    (parent_repo / ".git").mkdir()

    # Nested repo (should not be found because of pruning)
    child_repo = parent_repo / "sub_repo"
    child_repo.mkdir()
    (child_repo / ".git").mkdir()

    repos = list(find_git_repos(str(tmp_path), mock_config))
    
    assert len(repos) == 1
    assert parent_repo.resolve() in repos
