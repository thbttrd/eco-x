---
name: push
description: Safely push the current branch to the remote repository with pre-push verification
allowed-tools: Bash(git*), Bash(uv run*)
user-invocable: true
---

You are tasked with safely pushing the current branch to the remote repository. Follow these steps carefully:

## Step 1: Safety Checks

### Check 1: Verify not on protected branch
Run `git branch --show-current` and verify the current branch is NOT:
- `main`
- `master`

If on a protected branch, **STOP** and inform the user:
> "Cannot push directly to `{branch}`. Please create a feature branch first."

### Check 2: Verify clean working directory
Run `git status --porcelain` to check for uncommitted changes.

If there are uncommitted changes, **STOP** and inform the user:
> "There are uncommitted changes. Please commit or stash them first."
>
> Show the list of modified/untracked files.

### Check 3: Verify commits exist to push
Run `git log @{upstream}..HEAD --oneline 2>/dev/null || git log origin/$(git branch --show-current)..HEAD --oneline 2>/dev/null || echo "NEW_BRANCH"`

If no commits to push (empty output), inform the user:
> "No new commits to push. Branch is up to date with remote."

## Step 2: Pre-push Verification

### Run Tests
```bash
uv run pytest
```

If tests fail, **STOP** and inform the user:
> "Tests failed. Please fix failing tests before pushing."
> Show the test output summary.

### Run Type Checking
```bash
uv run mypy src/
```

If type checking fails, **STOP** and inform the user:
> "Type checking failed. Please fix type errors before pushing."

### Run Linting
```bash
uv run ruff check src/
```

If linting fails, **STOP** and inform the user:
> "Linting failed. Please fix lint errors before pushing."

## Step 3: Push to Remote

If all checks pass, push the branch:

```bash
git push -u origin $(git branch --show-current)
```

The `-u` flag sets up tracking for new branches.

## Step 4: Report Results

After successful push, report:
1. Branch name pushed
2. Number of commits pushed
3. Remote URL
4. Suggest next steps (e.g., "Create a pull request at: {repo_url}/pull/new/{branch}")

## Error Handling

If the push fails due to:
- **Authentication**: Suggest checking SSH keys or credentials
- **Rejected (non-fast-forward)**: Suggest `git pull --rebase` first
- **Protected branch rules**: Inform about branch protection

## Summary Format

```
## Push Summary

Branch: {branch_name}
Commits: {count} new commit(s)
Status: Success / Failed

### Verification Results:
- Tests: Passed (X tests)
- Type Check: Passed
- Lint: Passed

### Next Steps:
- Create PR: {url}
```

$ARGUMENTS
