# Repository Agent Instructions

## Pull request descriptions

When creating a pull request, write a clear release-ready description because merged PR descriptions are reused for release notes.

Include these sections:

- `Summary`: concise bullets describing what changed.
- `Validation`: commands or manual checks used to validate the change.
- `Breaking Changes`: explicitly state `None` when there are no breaking changes; otherwise document each breaking change and required migration steps.

Add the appropriate PR label based on the change type:

- `bugfix`: fixes incorrect behavior, regressions, crashes, credential detection issues, or test failures.
- `enhancement`: adds or improves functionality, UI, documentation, or developer experience.

If a PR includes both fixes and new functionality, prefer `enhancement` unless the primary purpose is a production bug fix.
