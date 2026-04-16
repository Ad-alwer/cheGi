import argparse
import platform
from builder.utils import setup_environment
from builder.linux import build_all_linux
from builder.windows import build_all_windows
from builder.macos import build_all_macos

def main():
    """Main entry point for the build orchestration script."""
    parser = argparse.ArgumentParser(description="Build script for Chegi CLI")
    parser.add_argument("--version", default="0.3.0", help="Version to build (e.g., 0.3.0)")
    args = parser.parse_args()

    print(f"Starting build for version: {args.version}")
    setup_environment()
    
    current_os = platform.system()
    
    if current_os == "Linux":
        build_all_linux(args.version)
    elif current_os == "Windows":
        build_all_windows(args.version)
    elif current_os == "Darwin":  # Darwin is the core of macOS
        build_all_macos(args.version)
    else:
        print(f"Unsupported OS: {current_os}")

    print("Build process completed successfully!")

if __name__ == "__main__":
    main()
