import os
import platform
import shutil
import subprocess
import tarfile

from builder_binary.config import (
    APP_NAME,
    AUTHOR_EMAIL,
    AUTHOR_NAME,
    DESCRIPTION,
    DIST_DIR,
    RELEASES_DIR,
)
from builder_binary.utils import build_base_binary


def _detect_arch():
    """Detect the target architecture for naming."""
    machine = platform.machine()
    if machine == "x86_64":
        return "amd64", "x86_64", "amd64"
    elif machine == "aarch64":
        return "arm64", "aarch64", "arm64"
    return machine, machine, machine


def build_tar_gz(version, binary_path, arch_suffix):
    """Create a standard portable .tar.gz archive."""
    tar_name = f"{APP_NAME}_{version}_linux_{arch_suffix}.tar.gz"
    tar_path = os.path.join(RELEASES_DIR, tar_name)
    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(binary_path, arcname=APP_NAME)
    print(f"Created {tar_name}")


def build_all_linux(version):
    build_base_binary()
    binary_path = os.path.join(DIST_DIR, APP_NAME)
    deb_arch, rpm_arch, tar_suffix = _detect_arch()

    # 1. Portable .tar.gz
    build_tar_gz(version, binary_path, tar_suffix)

    # 2. Debian (.deb)
    deb_dir = f"{APP_NAME}_{version}_{deb_arch}"
    bin_dir = os.path.join(deb_dir, "usr", "local", "bin")
    debian_dir = os.path.join(deb_dir, "DEBIAN")
    os.makedirs(bin_dir, exist_ok=True)
    os.makedirs(debian_dir, exist_ok=True)
    shutil.copy(binary_path, bin_dir)

    control_content = f"""Package: {APP_NAME}
Version: {version}
Architecture: {deb_arch}
Maintainer: {AUTHOR_NAME} <{AUTHOR_EMAIL}>
Description: {DESCRIPTION}
"""
    with open(os.path.join(debian_dir, "control"), "w") as f:
        f.write(control_content)

    subprocess.run(["dpkg-deb", "--build", deb_dir], check=True)
    shutil.move(
        f"{deb_dir}.deb",
        os.path.join(RELEASES_DIR, f"{APP_NAME}_{version}_{deb_arch}.deb"),
    )
    shutil.rmtree(deb_dir)

    # 3. RPM (.rpm)
    try:
        rpmbuild_dir = os.path.expanduser("~/rpmbuild")
        for folder in ["BUILD", "RPMS", "SOURCES", "SPECS", "SRPMS"]:
            os.makedirs(os.path.join(rpmbuild_dir, folder), exist_ok=True)

        spec_content = f"""Name: {APP_NAME}
Version: {version}
Release: 1%{{?dist}}
Summary: {DESCRIPTION}
License: MIT
Packager: {AUTHOR_NAME} <{AUTHOR_EMAIL}>

%description
{DESCRIPTION}

%install
mkdir -p %{{buildroot}}/usr/local/bin
install -m 755 {os.path.abspath(binary_path)} %{{buildroot}}/usr/local/bin/{APP_NAME}

%files
/usr/local/bin/{APP_NAME}
"""
        spec_path = os.path.join(rpmbuild_dir, "SPECS", f"{APP_NAME}.spec")
        with open(spec_path, "w") as f:
            f.write(spec_content)

        subprocess.run(["rpmbuild", "-bb", spec_path], check=True)
        rpm_file = f"{APP_NAME}-{version}-1.{rpm_arch}.rpm"
        rpm_path = os.path.join(rpmbuild_dir, "RPMS", rpm_arch, rpm_file)
        if os.path.exists(rpm_path):
            shutil.copy(rpm_path, os.path.join(RELEASES_DIR, rpm_file))
    except Exception as e:
        print(f"Skipping RPM build (rpmbuild might not be installed): {e}")
