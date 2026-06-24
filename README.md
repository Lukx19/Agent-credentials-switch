# AI Login Switcher

A Windows/Linux TUI and CLI for switching local Claude Code and Codex login profiles.

It keeps separate local credential/config folders for multiple accounts such as work, home, client, and empty-login profiles.

## Install from release

Download the correct archive from GitHub Releases:

- `ai-login-switcher-linux-x64.tar.gz`
- `ai-login-switcher-windows-x64.zip`

Extract it and place the executable somewhere on your PATH.

## Usage

This tool switches between saved Claude Code credentials and saved Codex credentials.
Claude and Codex are controlled independently: one Claude credential and one Codex credential can be active at the same time, and each tool can have multiple saved logins.
On first status/list/TUI run, existing credentials already present in `~/.claude` or `~/.codex` are imported automatically as `claude-default` or `codex-default` when no saved credential exists yet for that tool.

Show the built-in command explanations:

```bash
ai-login-switcher help
ai-login-switcher --help
ai-login-switcher capture --help
ai-login-switcher refresh --help
```

Open the guided TUI:

```bash
ai-login-switcher tui
```

Show which Claude and Codex credentials are currently active:

```bash
ai-login-switcher status
```

Save the currently active Claude or Codex home-folder credentials under a name:

```bash
ai-login-switcher add claude work-claude
ai-login-switcher add codex work-codex
```

To add another login for one tool, temporarily switch that tool to empty credentials, log in with the real CLI, then save the resulting credentials:

```bash
ai-login-switcher switch claude --empty
claude
ai-login-switcher add claude personal-claude

ai-login-switcher switch codex --empty
codex login
ai-login-switcher add codex personal-codex
```

Switch only the tool you want to change. Switching Codex does not change Claude, and switching Claude does not change Codex:

```bash
ai-login-switcher switch claude work-claude
ai-login-switcher switch codex personal-codex
```

Refresh account metadata for the active credentials. This command does not require credential names:

```bash
ai-login-switcher refresh
```

The older `capture` command is still available and is the same as `add`:

```bash
ai-login-switcher capture codex work-codex
```

## Data location

The switcher stores profiles here:

```text
~/.ai-login-switcher/
```

Do not commit or share this directory. It contains credentials.

## Windows notes

On Windows, symlinks may require Developer Mode or administrator privileges. If symlinks are unavailable, this tool falls back to copying directories.

In copy mode, after logging in with empty credentials, run capture so the new credentials are saved into the intended profile.

## Linux notes

On Linux, symlink switching should usually work directly.

## Build locally

Linux:

```bash
chmod +x build.sh
./build.sh
./dist/ai-login-switcher status
```

Windows PowerShell:

```powershell
.\build.ps1
.\dist\ai-login-switcher.exe status
```

## Release

Merging a pull request into `main` runs the build workflow and automatically creates a new release tag.

- If the merged pull request has a `bugfix` label, the workflow increments the patch version. For example, `v0.2.0` becomes `v0.2.1`.
- Otherwise, the workflow increments the minor version. For example, `v0.2.1` becomes `v0.3.0`.
- If no `v*.*.*` tag exists yet, the workflow creates `v0.1.0`.

The workflow uses the merged pull request description as the GitHub Release body so the release explains what is new or what was fixed. Every generated release body also includes an explicit `Breaking Changes` section.

You can also create a release manually by pushing a matching tag yourself:

```bash
git tag v0.2.0
git push origin v0.2.0
```

## Release flow

```bash
git init
git add .
git commit -m "Initial ai-login-switcher"
git branch -M main
git remote add origin git@github.com:YOUR_USER/ai-login-switcher.git
git push -u origin main
```

A merged pull request to `main` creates the next tag automatically. That tag is used for the release, which produces:

- `ai-login-switcher-linux-x64.tar.gz`
- `ai-login-switcher-windows-x64.zip`

Each archive contains one executable. Python does not need to be installed on the target machine.
