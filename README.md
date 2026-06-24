# AI Login Switcher

A Windows/Linux TUI and CLI for switching local Claude Code and Codex login profiles.

It keeps separate local credential/config folders for multiple accounts such as work, home, client, and empty-login profiles.

## Install with pipx

Install the Python package from PyPI:

```bash
pipx install ai-login-switcher
```

Upgrade later with:

```bash
pipx upgrade ai-login-switcher
```

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

Merging a pull request into `main` runs the build workflow and automatically creates a new release tag.

- If the merged pull request has a `bugfix` label, the workflow increments the patch version. For example, `v0.2.0` becomes `v0.2.1`.
- Otherwise, the workflow increments the minor version. For example, `v0.2.1` becomes `v0.3.0`.
- If no `v*.*.*` tag exists yet, the workflow creates `v0.1.0`.

The workflow uses the merged pull request description as the GitHub Release body so the release explains what is new or what was fixed. Every generated release body also includes an explicit `Breaking Changes` section.

Every version-tagged release also builds and publishes the Python package to PyPI for `pipx` installs. See `docs/pypi-publishing.md` for the one-time PyPI trusted-publishing setup.

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
