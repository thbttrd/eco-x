---
paths: ecox-data-platform/**/*.py, ecox-shared/**/*.py
---

# Database & SQLModel Patterns

## PostgreSQL/asyncpg Limits (IMPORTANT)

- **32,767 parameter limit**: With 7 fields/row, max batch_size ~4,000 rows
- **ON CONFLICT duplicate row error**: Deduplicate input data before upserting
- **Large NOT IN causes stack overflow**: Batch deletes, don't use huge tuple lists
- **Use UPSERT not SELECT-then-INSERT**: SELECT-then-INSERT has race conditions
- **Truncate error messages**: SQLAlchemy exceptions include full SQL with thousands of params

## Database Constraint for UPSERT

The `datavalue` table requires a **UNIQUE CONSTRAINT** for UPSERT:

```sql
ALTER TABLE datavalue ADD CONSTRAINT uq_datavalue_dataset_geo_time_indicator
    UNIQUE (dataset_id, geo, time_period, indicator);
```

## SQLModel Session Patterns

**IMPORTANT:** Use SQLModel's `exec` method instead of SQLAlchemy's `execute` method:

| SQLModel (correct) | SQLAlchemy (deprecated) |
|--------------------|------------------------|
| `session.exec(query)` | `session.execute(query)` |
| `result.one_or_none()` | `result.scalar_one_or_none()` |
| `result.all()` | `result.scalars().all()` |
| `result.one()` | `result.scalar()` |

**When to keep `execute()`:**
- DELETE statements needing `.rowcount`
- GROUP BY queries returning tuples (not models)
- Raw SQL with `text("SELECT ...")`

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
