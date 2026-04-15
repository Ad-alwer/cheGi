from chegi.services.installer.models import InstallTask


def test_install_task_default_values():
    """Test InstallTask creation with only required fields to check defaults."""
    task = InstallTask(name="git", cmd="apt install git")
    
    assert task.name == "git"
    assert task.cmd == "apt install git"
    assert task.level == "default"
    assert task.requires == []


def test_install_task_custom_values():
    """Test InstallTask creation with all fields provided explicitly."""
    task = InstallTask(
        name="nodejs",
        cmd="nvm install node",
        level="framework",
        requires=["nvm", "curl"]
    )
    
    assert task.name == "nodejs"
    assert task.cmd == "nvm install node"
    assert task.level == "framework"
    assert task.requires == ["nvm", "curl"]
