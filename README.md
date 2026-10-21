# CustomerOps AI

An AI assistant for customer operations. It reviews account risk and support tickets,
searches internal documents, and proposes follow-up tasks that require human approval.
The project includes fictional customer data and a local CRM.

## Stack

- **Backend:** Python 3.13, FastAPI, Pydantic, SQLAlchemy, Alembic, uv.
- **Frontend:** React, Vite.
- **AI:** LangGraph, OpenAI Responses API, embeddings, MCP.
- **Database and jobs:** PostgreSQL, pgvector, Redis, Celery.
- **Observability:** OpenTelemetry, Jaeger, Prometheus.
- **Tooling:** Docker Compose, pytest, Vitest, Ruff, Prettier, GitHub Actions.

## Setup

Install uv, Node.js 22, and Docker Desktop. Run these commands from the project directory.

```bash
uv sync --frozen
npm --prefix frontend ci
npm --prefix frontend run build
```

If you do not have a `.env` file, create one:

```bash
cp .env.example .env
```

Set `DEMO_PASSWORD` to a password with at least 12 characters. Keep existing database
credentials if your environment is already configured. Never commit `.env`.

Start Docker Desktop, then start the database and Redis:

```bash
docker compose up -d db redis
```

If the older `customerops-db` container is running, stop it with
`docker stop customerops-db` before starting the Compose database; both use port 5434.

Prepare the database once, and after pulling new migrations:

```bash
uv run alembic upgrade head
uv run python -m customerops_ai.seed
```

## Run

**Terminal 1 — API and built frontend:**

```bash
uv run fastapi dev src/customerops_ai/api.py
```

**Terminal 2 — background worker:**

```bash
uv run celery -A customerops_ai.jobs:celery_app worker --loglevel=INFO --pool=solo --concurrency=1
```

Open [the application](http://127.0.0.1:8000) or [API documentation](http://127.0.0.1:8000/docs).

Sign in with organization `11111111-1111-4111-8111-111111111111`, email
`admin@customerops.local`, and the password used during the first seed.
Changing `DEMO_PASSWORD` does not reset existing users.

For frontend hot reload, set `ALLOWED_ORIGIN=http://127.0.0.1:5173` in `.env`,
restart the API, and run `npm --prefix frontend run dev` in a third terminal.
Open [the development frontend](http://127.0.0.1:5173).

## Enable OpenAI (optional)

The default `AI_MODE=demo` uses a deterministic workflow and needs no API key.
For real model responses and semantic retrieval, update `.env`:

```dotenv
AI_MODE=openai
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=your-supported-model-id
```

Choose a model that supports Responses and function calling. Restart the API and worker,
then reindex documents in **Knowledge**. Model calls and embeddings incur API charges.

## Checks

```bash
make lint
make test
```

Backend integration tests require `TEST_DATABASE_URL` pointing to a separate database
whose name ends in `_test`; otherwise, they are skipped.

## Stop

Press `Ctrl+C` in each API, worker, and frontend terminal. Stop infrastructure with:

```bash
docker compose stop db redis
```

See [architecture](docs/architecture.md) and the [operations runbook](docs/runbook.md)
for tenant isolation, deployment details, and optional tracing.
