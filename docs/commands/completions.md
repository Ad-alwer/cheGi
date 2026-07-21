# `chegi completions`

Generate shell completion scripts for bash, zsh, fish, and PowerShell.

## Synopsis

```bash
chegi completions [SHELL] [OPTIONS]
```

## Description

`chegi completions` generates shell completion scripts for bash, zsh, fish, and PowerShell.

- **With a shell argument** — prints the script to stdout for manual piping
- **Without arguments** — interactive mode: detects your shell and offers to install
- **With `--install`** — auto-detects and installs without prompts

### Supported Shells

| Shell | Argument | Notes |
|-------|----------|-------|
| Bash | `bash` | Requires `bash-completion` package |
| Zsh | `zsh` | macOS Catalina+ uses zsh by default |
| Fish | `fish` | Place in `~/.config/fish/completions/` |
| PowerShell | `powershell` | Windows PowerShell |
| PowerShell Core | `pwsh` | Cross-platform PowerShell |

### Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--install` | `-i` | Auto-detect shell and install completion script | `false` |
| `--help` | | Show help message | |

### Interactive mode (no arguments)

When run without arguments, `chegi completions` detects your current shell
and offers to install completions automatically via a guided prompt:

```bash
chegi completions
# → Detects: zsh
# → "Install completions for zsh? [y/n]"
```

### Auto-install mode

Skip the prompt and install directly:

```bash
chegi completions --install
```

## Install Instructions

### Bash

```bash
chegi completions bash | sudo tee /etc/bash_completion.d/chegi
```

Then restart your terminal or run `source /etc/bash_completion.d/chegi`.

### Zsh

```bash
chegi completions zsh | sudo tee /usr/local/share/zsh/site-functions/_chegi
```

Then restart your terminal. Ensure `/usr/local/share/zsh/site-functions` is in
your `$fpath` (it usually is on macOS via Homebrew).

### Fish

```bash
chegi completions fish > ~/.config/fish/completions/chegi.fish
```

Then restart your terminal.

### PowerShell / PowerShell Core

```powershell
chegi completions powershell | Out-String | Invoke-Expression
```

Add this line to your PowerShell profile (`$PROFILE`) for persistence.

## Examples

```bash
# Generate bash completions
chegi completions bash > chegi-completion.bash

# Source directly in zsh
source <(chegi completions zsh)
```

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Unsupported shell |
