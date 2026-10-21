# Operations runbook

## Connectivity

Docker Desktop must be running. Confirm PostgreSQL on port 5434 and Redis on 6381 with `docker ps`.
`/health` checks the process; `/health/db` checks PostgreSQL and pgvector; `/health/ready` also
checks Redis. Resolve port conflicts by stopping the conflicting service or changing mappings,
not by deleting persistent volumes.

## Pending or failed documents

Inspect the worker terminal. Check worker availability with:

```bash
uv run celery -A customerops_ai.jobs:celery_app inspect ping
```

Reindexing replaces chunks atomically and is safe to retry. After changing the AI mode, embedding
model, or document language, restart API and worker with matching settings and reindex documents.
Real-mode indexing sends text to the configured provider and consumes API usage.

## Migrations

Run `uv run alembic upgrade head`. Create new revisions rather than modifying applied revisions.
The initial schema snapshot is frozen in migrations/schema_v1.py. Test upgrades from an empty
schema and downgrades on a disposable database before production operations.

## Backup

```bash
docker exec customerops-db pg_dump -U customerops -Fc customerops > customerops-backup.dump
```

Protect the backup and verify restoration into another database, never over the only working copy.

## Local accounts

DEMO_PASSWORD is used by the first seed, not as a live password reset setting. Changing it does
not update existing users. Use an administrative transaction with the security module for local
resets; implement a proper recovery/SSO flow for production. Keep credentials out of logs and Git.

## Runtime role and RLS

DATABASE_URL must use a non-superuser role; MIGRATION_DATABASE_URL is reserved for administration.
The provisioning script grants DML permissions, not DDL. Check rolsuper=false and rolbypassrls=false.
Never supply administrative credentials to the model, tool callers, or an MCP client.

## Tracing

Enable the Compose observability profile and set OTEL_ENDPOINT. No endpoint means spans are not
exported, while execution history is still persisted. See README.md for host/container endpoints.

## Shutdown

Use Ctrl+C for host API and worker processes, or `docker compose down` for containers.
Do not add `-v` if data must be retained.
