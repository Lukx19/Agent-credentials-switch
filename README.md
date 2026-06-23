# AI Login Switcher

A Windows/Linux TUI and CLI for switching local Claude Code and Codex login profiles.

It keeps separate local credential/config folders for multiple accounts such as work, home, client, and empty-login profiles.

## Install from release

Download the correct archive from GitHub Releases:

- `ai-login-switcher-linux-x64.tar.gz`
- `ai-login-switcher-windows-x64.zip`

Extract it and place the executable somewhere on your PATH.

## Usage

Open the TUI:

```bash
ai-login-switcher tui
```

Show active contexts:

```bash
ai-login-switcher status
```

Create profiles:

```bash
ai-login-switcher init work
ai-login-switcher init home
```

Switch Claude to empty credentials so you can log in:

```bash
ai-login-switcher switch claude --empty
claude
```

Then capture the newly logged-in credentials:

```bash
ai-login-switcher capture claude work
```

Switch Codex to empty credentials:

```bash
ai-login-switcher switch codex --empty
codex login
```

Then capture:

```bash
ai-login-switcher capture codex work
```

Switch active credentials:

```bash
ai-login-switcher switch claude work
ai-login-switcher switch codex home
```

Fetch account metadata from active CLI tools:

```bash
ai-login-switcher refresh-active
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

Push a tag:

```bash
git tag v0.1.0
git push origin v0.1.0
```

GitHub Actions will build Windows/Linux binaries and publish a release.

## Release flow

```bash
git init
git add .
git commit -m "Initial ai-login-switcher"
git branch -M main
git remote add origin git@github.com:YOUR_USER/ai-login-switcher.git
git push -u origin main

git tag v0.1.0
git push origin v0.1.0
```

That tag triggers the workflow and produces:

- `ai-login-switcher-linux-x64.tar.gz`
- `ai-login-switcher-windows-x64.zip`

Each archive contains one executable. Python does not need to be installed on the target machine.
