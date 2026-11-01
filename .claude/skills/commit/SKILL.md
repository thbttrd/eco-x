---
name: commit
description: Verify features, fix pre-commit issues, and create meaningful commit
allowed-tools: Bash(git*), Bash(uv run*), Read, Grep, Edit, Write
user-invocable: true
---

You are tasked with preparing a clean, well-documented commit. Follow these steps carefully:

## Step 1: Analyze Current Changes

Check what has been modified:

```bash
git status
```

```bash
git diff --stat
```

## Step 2: Understand the Changes

Review the actual code changes to understand what features were implemented or modified:

```bash
git diff
```

## Step 3: Run Pre-commit Hooks

Execute pre-commit checks and fix any issues:

```bash
uv run pre-commit run --all-files 2>&1 || true
```

If pre-commit fails:
1. Identify the specific issues (formatting, linting, type errors)
2. Fix each issue automatically where possible
3. Re-run pre-commit until all checks pass

## Step 4: Verify the Application Works

1. **Run tests** if available:
   ```bash
   uv run pytest -x -q 2>&1 | head -30 || echo "No tests or pytest not configured"
   ```

2. **Type checking**:
   ```bash
   uv run mypy src/ 2>&1 | tail -20 || echo "Mypy not configured"
   ```

## Step 5: Start Dev Server and Check UI (if UI changes detected)

If the changes involve templates, frontend, or API routes:
1. Start the dev server if not running
2. Verify the UI works correctly
3. Check for console errors

## Step 6: Propose Commit Message

Based on your analysis, propose a meaningful commit message following these conventions:

**Format:**
```
<type>: <short description>

<detailed description if needed>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code refactoring without feature change
- `style`: Formatting, styling changes
- `docs`: Documentation only
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Guidelines:**
- Keep the first line under 72 characters
- Use imperative mood ("Add feature" not "Added feature")
- Explain WHY the change was made, not just what
- Reference any related issues if mentioned in conversation

## Step 7: Present Options

Present to the user:
1. Summary of changes verified
2. Pre-commit status (passed/fixed issues)
3. Test/type-check results
4. Proposed commit message
5. Ask if they want to proceed with the commit

Only create the commit if the user confirms. Use this format:
```bash
git add -A && git commit -m "<message>"
```

$ARGUMENTS
