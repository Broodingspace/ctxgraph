# Example PR For `ctxgraph` Impact Checking

This document gives you a concrete pull request scenario you can use to validate the `ctxgraph` GitHub Action locally and on GitHub.

The goal is to simulate a realistic PR that includes:

- a code change
- a related test change
- an expected structural impact report

## Scenario

We will pretend a PR changes the display formatting of `User.get_display_name()` and also updates tests to reflect that behavior.

This is a good validation case because:

- the changed symbol is easy to map
- the action should detect a method-level change, not just the module
- the PR should also show a non-zero test-change signal

## Example PR Title

`Refine User display name formatting and cover it with tests`

## Example PR Body

```md
## What this PR does

Updates `User.get_display_name()` in the sample project fixture to include the user ID in the display output, and adds test coverage for the changed behavior.

## Changes

- update `tests/fixtures/sample_project/models.py`
- add or update tests related to `User.get_display_name()`

## Why

This is a small but useful example for validating the `ctxgraph` PR impact workflow:

- changed code should map to a specific symbol
- impacted area should be visible in the report
- test changes should be detected as part of PR coverage signals

## Test coverage

- added or updated tests for `User.get_display_name()`
- validated the `ctxgraph` impact action locally with `--markdown-out`
```

## Recommended Demo Branch

```bash
git checkout -b demo/pr-impact-check
```

## Example Code Change

File:

`tests/fixtures/sample_project/models.py`

Change:

```python
def get_display_name(self) -> str:
    return f"User<{self.id}>: {self.name}"
```

## Example Test Change

An example test file is already included in this repository:

`tests/fixtures/sample_project/test_models.py`

Example:

```python
from sample_project.models import User


def test_user_display_name_includes_id() -> None:
    user = User(7, "Ada")
    assert user.get_display_name() == "User<7>: Ada"
```

This is useful for the action because it gives the PR:

- one production code change
- one test file change

## Local Validation Command

Run the action script against the branch diff:

```bash
python scripts/github_action.py \
  --repo-path . \
  --base-ref main \
  --head-ref HEAD \
  --comment-mode none \
  --markdown-out .ctxgraph/impact-report.md
```

Or use the local preview wrapper:

```bash
python scripts/run_impact_preview.py --base-ref main --head-ref HEAD
```

## What You Want To See

At minimum, the report should show:

- the changed symbol mapped to `User.get_display_name`
- a non-zero blast radius
- `Changed test files: 1`
- a PR coverage section showing whether impacted files are already touched

## Example Expected Report Shape

```md
## `ctxgraph` impact report

- Changed Python files: **2**
- Changed symbols: **1**
- Combined blast radius: **N nodes**
- Overall severity: **low** or **medium**

### Changed symbols

- `sample_project.models.User.get_display_name` (function, blast radius: N, severity: low)

### PR coverage signals

- Impacted nodes already touched in PR: **X/Y**
- Impacted files already touched in PR: **A/B**
- Changed test files in PR: **1**
- Structural coverage assessment: **partial** or **well-covered**
```

## GitHub Validation

Once the workflow exists on `main`, open a PR from your demo branch and verify:

1. the action runs on `pull_request`
2. the step summary contains the impact report
3. the PR comment is posted or updated
4. the report includes test-file and coverage signals

## Why This Example Matters

This gives you a simple, believable example to show that `ctxgraph` is not only reporting impacted nodes, but also helping answer:

- did the PR touch the affected area?
- were tests updated too?
- does the PR look structurally complete?
