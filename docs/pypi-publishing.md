# PyPI publishing

This project publishes a Python package for `pipx` on every version-tagged release.

## One-time PyPI setup

1. Create or sign in to a PyPI account at <https://pypi.org/>.
2. Register the `ai-login-switcher` project by either uploading the first release manually or by configuring trusted publishing before the first automated upload.
3. In PyPI, open **Publishing** for the `ai-login-switcher` project and add a trusted publisher with these values:
   - Owner: the GitHub organization or username that owns this repository.
   - Repository name: this repository name.
   - Workflow filename: `release.yml`.
   - Environment name: leave blank unless the workflow is later changed to use a protected environment.
4. After trusted publishing is configured, do not add a PyPI password or API token to GitHub. The workflow uses GitHub OIDC through `pypa/gh-action-pypi-publish`.

## Automated release behavior

When a `v*.*.*` tag is pushed, the release workflow builds the source distribution and wheel, then publishes them to PyPI. The package version is derived from the Git tag, so `v0.3.0` publishes version `0.3.0`.

Merged pull requests to `main` already create the next version tag automatically, so normal releases publish to PyPI without extra steps.

## Installing with pipx

After the package appears on PyPI, install or upgrade it with:

```bash
pipx install ai-login-switcher
pipx upgrade ai-login-switcher
```
