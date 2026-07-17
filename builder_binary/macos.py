"""macOS builder — produces a universal2 binary for Intel and Apple Silicon."""

import os
import tarfile

from builder_binary.config import APP_NAME, DIST_DIR, RELEASES_DIR
from builder_binary.utils import build_base_binary


def build_all_macos(version):
    """Build macOS specific packages (universal2 binary)."""
    build_base_binary(target_arch="universal2")
    binary_path = os.path.join(DIST_DIR, APP_NAME)

    tar_name = f"{APP_NAME}_{version}_macos_universal2.tar.gz"
    tar_path = os.path.join(RELEASES_DIR, tar_name)
    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(binary_path, arcname=APP_NAME)
    print(f"Created {tar_name}")
