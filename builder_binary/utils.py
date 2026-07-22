import os
import shutil
import subprocess

from builder_binary.config import APP_NAME, DIST_DIR, ENTRY_POINT, RELEASES_DIR


def setup_environment():
    """Create the releases directory and clean old dist/build folders."""
    if not os.path.exists(RELEASES_DIR):
        os.makedirs(RELEASES_DIR)

    for folder in ["build", DIST_DIR]:
        if os.path.exists(folder):
            shutil.rmtree(folder)


def build_base_binary(target_arch=None):
    """Run PyInstaller to create the standalone binary.

    Args:
        target_arch: Optional target architecture for macOS
                     (e.g. 'universal2', 'x86_64', 'arm64').
    """
    print(f"Building standalone binary for {APP_NAME}...")
    hidden_imports = [
        "chegi.cli.commands",
        "chegi.cli.core",
        "chegi.cli.core.checks",
        "chegi.config",
        "chegi.services",
        "chegi.services.auth",
        "chegi.services.branch",
        "chegi.services.clone",
        "chegi.services.commit",
        "chegi.services.completions",
        "chegi.services.doctor",
        "chegi.services.environment",
        "chegi.services.git",
        "chegi.services.git_config",
        "chegi.services.github",
        "chegi.services.guard",
        "chegi.services.hooks",
        "chegi.services.info",
        "chegi.services.init",
        "chegi.services.installer",
        "chegi.services.new_project",
        "chegi.services.reword",
        "chegi.services.scanner",
        "chegi.services.sync",
        "chegi.services.upgrade",
        "chegi.services.wizard",
        "chegi.ui",
    ]
    cmd = ["pyinstaller", "--onefile", "--name", APP_NAME]
    for mod in hidden_imports:
        cmd.extend(["--hidden-import", mod])
    if target_arch:
        cmd.extend(["--target-arch", target_arch])
    cmd.append(ENTRY_POINT)
    subprocess.run(cmd, check=True)
