# CLAUDE.md - Development Notes

## Development Workflow (IMPORTANT)

Follow this workflow for feature development:

```
1. User Request     → Understand what the user wants
2. Research/Design  → /research-and-design (→ docs/requirements/, docs/adrs/)
3. Plan             → /create-plan (→ docs/plans/)
4. Implement        → /implement-plan
5. Validate         → /validate-plan
6. Review           → /code-review
7. Deploy           → /deploy-after-dev
8. Commit & Push    → /commit then /push
```

**Key Points:**
- For new features, start with `/research-and-design` to document requirements
- Use `/create-plan` to create detailed implementation plans
- Always validate and deploy locally before pushing
- Commit regularly throughout the process

---

## Continuous Learning (IMPORTANT)

When you encounter errors, mistakes, or learn something important during development:

1. **Identify the pattern** - What went wrong? What was the root cause?
2. **Determine the scope** - Which files/paths does this apply to?
3. **Create a path-scoped rule** - Add to `.claude/rules/` with appropriate frontmatter

### Rule Creation Guidelines

**File naming:** `<topic>-lessons.md` or add to existing topic file

**Example - Adding a lesson learned:**

If you discover that `httpx` async client must be closed explicitly in FastAPI, create:

```markdown
---
paths: ecox-data-platform/**/*.py
---

# HTTP Client Patterns

## AsyncClient Lifecycle
Always use `async with` for httpx.AsyncClient to ensure proper cleanup:

```python
# CORRECT
async with httpx.AsyncClient() as client:
    response = await client.get(url)

# WRONG - resource leak
client = httpx.AsyncClient()
response = await client.get(url)
```
```

### When to Create Rules

- **Pre-commit failures** that required investigation
- **Runtime errors** from incorrect patterns
- **Type errors** from wrong imports or signatures
- **Performance issues** from inefficient approaches
- **API quirks** that weren't obvious

### Rule Quality

- Be specific and actionable
- Include CORRECT and WRONG examples
- Use appropriate path scope (don't make everything global)
- Reference the issue that triggered the rule if applicable

---

## Available Skills

| Skill | Purpose |
|-------|---------|
| `/research-and-design` | Research codebase, design features → requirements/ADRs |
| `/create-plan` | Create implementation plan → `docs/plans/` |
| `/implement-plan` | Execute plan with verification checkpoints |
| `/validate-plan` | Verify implementation matches plan |
| `/code-review` | Spawn Opus agent to review commits |
| `/deploy-after-dev` | Deploy to local Podman containers |
| `/commit` | Verify and commit changes |
| `/push` | Push to remote and create PR |
| `/add-datasource` | Add new data source (full workflow) |
| `/frontend` | Frontend dev guidance (htmx, Alpine.js) |

### Skill Output Expectations

Skills produce specific outputs - do NOT confuse them with plan files:

| Skill | Output Location | Description |
|-------|-----------------|-------------|
| `/research-and-design` | `docs/adrs/`, `docs/requirements/` | ADRs and requirements (NOT plan files) |
| `/create-plan` | `docs/plans/` | Implementation plans |
| `/implement-plan` | Code changes | Executes plans from `docs/plans/` |
| `/validate-plan` | Verification report | Checks implementation against plan |

**CRITICAL**: `/research-and-design` outputs ADRs and requirements, NOT plan files. If plan mode interferes, the skill's documentation output takes precedence.

---

## Available Agents (for Task tool)

| Agent | Purpose |
|-------|---------|
| `codebase-locator` | Find WHERE code lives |
| `codebase-analyzer` | Understand HOW code works |
| `codebase-pattern-finder` | Find similar implementations |
| `docs-locator` | Find docs in `docs/` |
| `docs-analyzer` | Extract insights from docs |
| `web-search-researcher` | External web research |

---

## Parallel Development

Work on multiple features using folder copies with isolated containers.

### Port Allocation

| Instance | ECOX_SUFFIX | PostgreSQL | Platform | Client |
|----------|-------------|------------|----------|--------|
| eco-x | (empty) | 5432 | 8000 | 8080 |
| eco-x-1 | -1 | 5433 | 8001 | 8081 |
| eco-x-2 | -2 | 5434 | 8002 | 8082 |

### Setup New Instance

```bash
cp -r /home/user/eco-x /home/user/eco-x-3

# Create .env with unique ports:
# ECOX_SUFFIX=-3, ECOX_POSTGRES_PORT=5435, ECOX_PLATFORM_PORT=8003, ECOX_CLIENT_PORT=8083
# DATABASE_URL with localhost:5435

cd /home/user/eco-x-3
podman-compose up -d postgres
uv run alembic upgrade head
podman-compose up -d
```

---

## Frontend Hot Reloading

For faster frontend iteration without rebuilding containers:

```bash
# Start client with hot reload (templates, static files, locales)
podman-compose -f podman-compose.yaml -f podman-compose.dev.yaml up -d client
```

### What reloads automatically (just refresh browser):
- `ecox-client/templates/**/*.html` - Jinja2 templates
- `ecox-client/static/**` - JavaScript, CSS
- `ecox-client/locales/*.yaml` - i18n translations

### Python code changes still need:
```bash
podman-compose restart client
```
