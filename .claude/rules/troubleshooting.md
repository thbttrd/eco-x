# Troubleshooting

## Containers not using new code after rebuild

```bash
# ALWAYS use --force-recreate after rebuilding!
podman-compose build platform && podman-compose up -d --force-recreate platform
```

## Platform won't start

Check `podman logs ecox-platform` for:
- Missing DATABASE_URL
- Database not ready
- Missing unique constraint on datavalue

## Database connection

- **Host** uses `localhost:5432`
- **Containers** use `postgres:5432` (container hostname)
