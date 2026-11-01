---
paths: ecox-data-platform/**/tests/**/*.py, ecox-client/**/tests/**/*.py, ecox-shared/**/tests/**/*.py, ecox-agents/**/tests/**/*.py, **/*.feature
---

# Testing (BDD with pytest-bdd)

```bash
# Run BDD tests
cd ecox-data-platform && uv run pytest tests/bdd/ -v
cd ecox-client && uv run pytest tests/bdd/ -v

# Run by epic
cd ecox-data-platform && uv run pytest -m "epic_1"

# Run by type
cd ecox-data-platform && uv run pytest -m "api"
```

See `docs/testing.md` for comprehensive documentation.
