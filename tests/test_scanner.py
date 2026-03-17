import pytest
from pathlib import Path
from chegi.scanner import find_git_repos

def create_mock_repo(base_dir: Path, repo_path: str) -> Path:
    """
    Helper function to create a mock Git repository structure for testing.

    This function creates the required directory tree and inserts a dummy
    '.git' folder inside to simulate a valid Git repository.

    Args:
        base_dir (Path): The base temporary directory provided by pytest.
        repo_path (str): The relative path where the mock repository should be created.

    Returns:
        Path: The full absolute path to the newly created mock repository.
    """
    full_path = base_dir / repo_path
    full_path.mkdir(parents=True, exist_ok=True)
    
    # Create the fake .git directory
    git_dir = full_path / ".git"
    git_dir.mkdir(exist_ok=True)
    
    return full_path

def test_find_basic_repo(tmp_path: Path):
    """
    Test if a standard, single Git repository is found correctly.

    Args:
        tmp_path (Path): A built-in pytest fixture providing a temporary directory 
                         unique to this test invocation.
    """
    create_mock_repo(tmp_path, "my_project")
    
    # Run scanner
    repos = list(find_git_repos(str(tmp_path), max_depth=3, exclude_dirs=[]))
    
    assert len(repos) == 1
    assert repos[0].name == "my_project"

def test_exclude_directories(tmp_path: Path):
    """
    Test if the scanner properly ignores blacklisted directories.

    Verifies that repositories located inside directories listed in the 
    `exclude_dirs` parameter (e.g., 'node_modules', '.venv') are skipped.

    Args:
        tmp_path (Path): A built-in pytest fixture providing a temporary directory.
    """
    create_mock_repo(tmp_path, "valid_repo")
    create_mock_repo(tmp_path, "node_modules/ignored_repo")
    create_mock_repo(tmp_path, ".venv/another_ignored")
    
    excludes = ["node_modules", ".venv"]
    repos = list(find_git_repos(str(tmp_path), max_depth=3, exclude_dirs=excludes))
    
    assert len(repos) == 1
    assert repos[0].name == "valid_repo"

def test_max_depth_limit(tmp_path: Path):
    """
    Test if the scanner accurately halts traversal at the specified `max_depth`.

    Creates a deeply nested repository and verifies that it is only discovered
    when the `max_depth` parameter is large enough to reach it.

    Args:
        tmp_path (Path): A built-in pytest fixture providing a temporary directory.
    """
    # Depth level: tmp_path (0) -> level1 (1) -> level2 (2) -> deep_repo (3)
    create_mock_repo(tmp_path, "level1/level2/deep_repo")
    
    # With max_depth=3, the scanner stops traversing at depth 3
    # Therefore, it won't check inside deep_repo (which is at depth 3)
    repos_shallow = list(find_git_repos(str(tmp_path), max_depth=3, exclude_dirs=[]))
    assert len(repos_shallow) == 0
    
    # With max_depth=4, it should find it
    repos_deep = list(find_git_repos(str(tmp_path), max_depth=4, exclude_dirs=[]))
    assert len(repos_deep) == 1
    assert repos_deep[0].name == "deep_repo"

def test_smart_pruning_nested_repos(tmp_path: Path):
    """
    Test that subdirectories of a discovered repository are not scanned (Smart Pruning).

    Ensures that if a repository contains nested repositories (like Git submodules),
    only the parent repository is yielded, and the internal structure is pruned
    from the scan for performance optimization.

    Args:
        tmp_path (Path): A built-in pytest fixture providing a temporary directory.
    """
    # Create a parent repo
    parent_repo = create_mock_repo(tmp_path, "parent_repo")
    
    # Create a nested repo INSIDE the parent repo (e.g., a git submodule)
    create_mock_repo(parent_repo, "nested_submodule")
    
    repos = list(find_git_repos(str(tmp_path), max_depth=5, exclude_dirs=[]))
    
    # It should only yield the parent repo and prune the rest
    assert len(repos) == 1
    assert repos[0].name == "parent_repo"

def test_invalid_start_path(capsys):
    """
    Test the scanner's behavior when provided with a non-existent starting directory.

    Ensures that an invalid path does not crash the application and instead gracefully
    prints an error message to standard output.

    Args:
        capsys (Fixture): A built-in pytest fixture used to capture sys.stdout and sys.stderr.
    """
    invalid_path = "/this/path/does/not/exist/12345"
    repos = list(find_git_repos(invalid_path, max_depth=3, exclude_dirs=[]))
    
    # Ensure no repos are found
    assert len(repos) == 0
    
    # Capture the print output and verify the error message
    captured = capsys.readouterr()
    assert "does not exist" in captured.out
