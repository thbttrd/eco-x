---
name: code-review
description: Spawn a fresh Opus 4.5 agent to review recent commits or commits since a specific hash
allowed-tools: Task, Bash(git*)
user-invocable: true
---

## Code Review Command

Review the last N commits or commits since a specific commit hash.

**Arguments:** $ARGUMENTS

- **Integer (N)**: Review the last N commits (e.g., `3` reviews last 3 commits)
- **Commit hash**: Review all commits since that hash (exclusive)
- **No arguments (default)**: Review all commits since the last commit on main branch (typically the semantic release commit)

## Instructions

### Step 1: Parse Arguments and Get Commits

First, determine what commits to review:

```bash
git log --oneline -10
```

**Argument parsing:**
- If `$ARGUMENTS` is a small integer (1-50): Get last N commits
- If `$ARGUMENTS` looks like a commit hash (7+ hex chars): Get commits since that hash
- **If empty or invalid**: Review all commits since the last commit on main branch:
  ```bash
  git log main..HEAD --oneline
  ```
  This reviews all work done on the current feature branch since it diverged from main (typically after the semantic release commit).

### Step 2: Spawn Code Review Agent

Use the **Task tool** with the following configuration:

```
Tool: Task
subagent_type: general-purpose
model: opus
```

**Prompt template for the agent:**

```
You are a senior code reviewer performing a thorough code review. Your job is to:

1. **Analyze the changes** - Understand what was modified and why
2. **Challenge decisions** - Question architectural choices, naming, patterns used
3. **Find issues** - Security vulnerabilities, bugs, edge cases, performance issues
4. **Suggest improvements** - Better patterns, cleaner code, missing tests
5. **Verify best practices** - Error handling, logging, documentation

## Commits to Review

[INSERT GIT LOG OUTPUT HERE]

## Review Process

For each commit:

### A. Get the diff
Run: `git show <commit-hash> --stat` to see files changed
Run: `git show <commit-hash>` to see full diff

### B. Analyze and Challenge

For each file changed, consider:

**Code Quality:**
- Is the code readable and well-structured?
- Are variable/function names clear and consistent?
- Is there unnecessary complexity?
- Are there any code smells?

**Architecture:**
- Does this change fit the existing architecture?
- Are there better patterns to use?
- Is there proper separation of concerns?

**Security:**
- Any input validation issues?
- SQL injection, XSS, or other OWASP vulnerabilities?
- Secrets or credentials exposed?
- Proper error handling that doesn't leak info?

**Performance:**
- Any N+1 query issues?
- Unnecessary loops or computations?
- Missing caching opportunities?
- Async/await used correctly?

**Testing:**
- Are there tests for the new code?
- Are edge cases covered?
- Is the code testable?

**Documentation:**
- Are complex parts documented?
- Are public APIs documented?
- Do commit messages explain the "why"?

### C. Generate Review Report

For each significant finding, report:

```
## [COMMIT-HASH]: <commit message>

### Summary
<Brief description of what this commit does>

### Findings

#### Critical Issues (must fix)
- Issue: <description>
  - File: <path>:<line>
  - Suggestion: <how to fix>

#### Warnings (should fix)
- Issue: <description>
  - File: <path>:<line>
  - Suggestion: <how to fix>

#### Suggestions (nice to have)
- <improvement idea>

#### Good Practices Noted
- <positive feedback on well-done parts>
```

## Final Output

End with an executive summary:

```
## Code Review Summary

**Commits Reviewed:** N
**Critical Issues:** X
**Warnings:** Y
**Suggestions:** Z

### Priority Actions
1. <Most important thing to address>
2. <Second most important>
3. ...

### Overall Assessment
<General feedback on code quality, patterns used, areas for improvement>
```

---

Now please review the following commits:

[COMMITS_TO_REVIEW]
```

### Step 3: Execute the Review

1. **Get commit information:**
   - For integer N: `git log -N --oneline` to get commit hashes
   - For commit hash: `git log <hash>..HEAD --oneline` to get commits since
   - **For no arguments**: `git log main..HEAD --oneline` to get all commits since main

2. **Get the full log with details:**
   - `git log -N --format="- %h: %s"` or `git log <hash>..HEAD --format="- %h: %s"`
   - For default: `git log main..HEAD --format="- %h: %s"`

3. **Spawn the Task agent** with:
   - `subagent_type: general-purpose`
   - `model: opus`
   - The prompt template above, with `[COMMITS_TO_REVIEW]` replaced by the actual commit list

4. **Wait for results** and present the review to the user

### Example Usage

```bash
# Review all commits on current branch since main (DEFAULT - most common use case)
/code-review

# Review last 3 commits
/code-review 3

# Review all commits since abc1234
/code-review abc1234
```
