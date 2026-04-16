import os
import shutil
import subprocess
from builder.config import APP_NAME, ENTRY_POINT, RELEASES_DIR, DIST_DIR

def setup_environment():
    """Create the releases directory and clean old dist/build folders."""
    if not os.path.exists(RELEASES_DIR):
        os.makedirs(RELEASES_DIR)
    
    for folder in ['build', DIST_DIR]:
        if os.path.exists(folder):
            shutil.rmtree(folder)

def build_base_binary():
    """Run PyInstaller to create the standalone binary."""
    print(f"Building standalone binary for {APP_NAME}...")
    subprocess.run([
        "pyinstaller",
        "--onefile",
        "--name", APP_NAME,
        ENTRY_POINT
    ], check=True)
