# `chegi completions`

Generate shell completion scripts for bash, zsh, fish, and PowerShell.

## Synopsis

```bash
chegi completions <SHELL>
```

## Description

`chegi completions` prints a shell completion script to stdout. Pipe the output
into your shell's configuration to enable tab completion for all `chegi`
subcommands, options, and arguments.

### Supported Shells

| Shell | Argument | Notes |
|-------|----------|-------|
| Bash | `bash` | Requires `bash-completion` package |
| Zsh | `zsh` | macOS Catalina+ uses zsh by default |
| Fish | `fish` | Place in `~/.config/fish/completions/` |
| PowerShell | `powershell` | Windows PowerShell |
| PowerShell Core | `pwsh` | Cross-platform PowerShell |

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
