# cheGi

**The ultimate Git companion. Type less, do more.**

`cheGi` is a powerful, lightning-fast Command Line Interface (CLI) designed to supercharge your Git workflow. Built for developers who want to manage, track, and interact with multiple Git repositories effortlessly, `cheGi` drastically reduces manual typing and provides a beautiful, unified view of your workspace.

While it currently excels at rapid repository discovery and status analysis, `cheGi` is evolving into a comprehensive suite for all your daily Git operations.

## Key Features

- **Blazing Fast Concurrent Operations:** Utilizes Python's `ThreadPoolExecutor` to process multiple repositories simultaneously without bottlenecking your system.
- **Beautiful Terminal UI:** Say goodbye to boring logs. `cheGi` displays complex data in highly readable, colorful tables powered by `Rich`.
- **Smart Workspace Scanning:** Quickly discover Git repositories across your system. It intelligently prunes irrelevant directories (like `.venv`, `node_modules`) to save time.
- **Instant Status Insights:** Get a bird's-eye view of your projects—instantly see branch names, dirty working trees (uncommitted changes), and remote configurations.
- **Extensible Architecture:** Designed from the ground up to support a wide range of Git automation and management commands (More features coming soon!).

## Prerequisites

- Python 3.10 or higher
- Git installed on your system

## Installation

You can install `cheGi` locally for development and usage using `pip`:

1. Clone the repository:
```bash
git clone <your-repo-url>
cd cheGi
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Linux/macOS
# .venv\Scripts\activate   # On Windows
```

3. Install the package in editable mode:
```bash
pip install -e .
```

## Usage

Once installed, the `chegi` command will be available globally in your terminal environment.

To quickly analyze all repositories in your current directory:
```bash
chegi .
```

To target a specific workspace path:
```bash
chegi /path/to/your/projects/folder
```

### Example Output

The tool will output a beautiful summary table showing:

- **Repository Name**
- **Path**
- **Branch**
- **Status** (Clean/Dirty)
- **Remote** (Yes/No)

## Configuration

`cheGi` is highly customizable. It currently reads a `config.json` file in the root directory to set rules like `max_depth` and `exclude_dirs`.
*(Note: Dedicated CLI configuration management commands are planned for version `v0.2.0`)*.

Default configuration fallback:
```json
{
  "max_depth": 3,
  "exclude_dirs": [".git", "node_modules", "venv", ".venv", "__pycache__"]
}
```

## Development and Testing

`cheGi` comes with a comprehensive test suite covering 100% of the core modules to ensure maximum reliability. We use `pytest` for testing.

To run the full test suite:
```bash
pytest -v
```

## License

This project is licensed under the MIT License.

