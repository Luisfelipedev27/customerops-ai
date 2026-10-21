FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app
RUN pip install --no-cache-dir uv==0.13.1 && useradd --create-home app
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src/ src/
RUN uv sync --frozen --no-dev
COPY alembic.ini ./
COPY migrations/ migrations/
COPY evals/ evals/
COPY scripts/ scripts/
COPY --from=web /web/dist/ frontend/dist/
RUN chown -R app:app /app
USER app
EXPOSE 8000
CMD ["uv", "run", "--no-sync", "uvicorn", "customerops_ai.api:app", "--host", "0.0.0.0", "--port", "8000"]
