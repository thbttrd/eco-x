---
paths: ecox-data-platform/**/sources/**/*.py, config/datasets.yaml
---

# Data Sources

| Source | API Base URL | Auth | Config Key |
|--------|--------------|------|------------|
| Eurostat | sdmx.ec.europa.eu | None | eurostat |
| FRED | fred.stlouisfed.org | API key | fred |
| NBS China | data.stats.gov.cn | None | nbs |
| ONS UK | api.beta.ons.gov.uk | None | ons |
| OECD | sdmx.oecd.org | None | oecd |

Configuration in `config/datasets.yaml`. See `ecox-data-platform/src/ecox_platform/sources/` for implementations.
