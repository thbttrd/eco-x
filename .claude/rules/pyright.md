---
paths: ecox-data-platform/**/*.py, ecox-client/**/*.py, ecox-shared/**/*.py, ecox-agents/**/*.py
---

# Type Checking (Pyright)

This project uses **pyright** for type checking. Run with `uv run pyright src/`.

## Running Type Checks

```bash
uv run pyright src/           # Check source code only
uv run pyright                # Check everything (including tests)
uv run pre-commit run --all   # Runs pyright as part of all checks
```

## SQLModel Session Patterns

**IMPORTANT:** Use SQLModel's `exec` method instead of SQLAlchemy's `execute` method:

| SQLModel (correct) | SQLAlchemy (deprecated) |
|--------------------|------------------------|
| `session.exec(query)` | `session.execute(query)` |
| `result.one_or_none()` | `result.scalar_one_or_none()` |
| `result.all()` | `result.scalars().all()` |
| `result.one()` | `result.scalar()` |

## AsyncSession Import

**CRITICAL:** Use SQLModel's AsyncSession, not SQLAlchemy's:

```python
# CORRECT - has the .exec() method
from sqlmodel.ext.asyncio.session import AsyncSession

# WRONG - missing .exec(), causes "Cannot access attribute" errors
from sqlalchemy.ext.asyncio import AsyncSession
```

## Model ID Types

SQLModel models have `id: int | None` (None before database save). When passing to schemas expecting `int`:

```python
# Add type ignore for IDs that are guaranteed to exist after flush/commit
return ResponseSchema(
    id=model.id,  # type: ignore[arg-type]
    name=model.name,
)
```
