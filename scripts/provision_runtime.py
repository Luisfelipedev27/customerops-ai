"""Provision a non-superuser runtime role using the administrator migration DSN.
Run after migrations. Password must be provided in RUNTIME_DATABASE_PASSWORD.
"""

import os

import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url

from customerops_ai.config import get_settings


def main():
    cfg = get_settings()
    url = make_url(cfg.migration_database_url or cfg.database_url)
    password = os.environ.get("RUNTIME_DATABASE_PASSWORD", "")
    role = os.environ.get("RUNTIME_DATABASE_USER", "customerops_runtime")
    if len(password) < 16:
        raise SystemExit("RUNTIME_DATABASE_PASSWORD must have 16+ characters")
    with psycopg.connect(
        host=url.host, port=url.port, dbname=url.database, user=url.username, password=url.password
    ) as conn:
        if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (role,)).fetchone():
            conn.execute(
                sql.SQL("CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOBYPASSRLS").format(
                    sql.Identifier(role), sql.Literal(password)
                )
            )
        else:
            conn.execute(
                sql.SQL("ALTER ROLE {} PASSWORD {} NOSUPERUSER NOBYPASSRLS").format(
                    sql.Identifier(role), sql.Literal(password)
                )
            )
        conn.execute(
            sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                sql.Identifier(url.database), sql.Identifier(role)
            )
        )
        conn.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(role)))
        tables = [
            "tenants",
            "users",
            "login_sessions",
            "customers",
            "tickets",
            "documents",
            "chunks",
            "runs",
            "actions",
            "crm_tasks",
            "audit_events",
        ]
        for table in tables:
            conn.execute(
                sql.SQL("GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE {} TO {}").format(
                    sql.Identifier(table), sql.Identifier(role)
                )
            )
    print("Runtime role provisioned (NOSUPERUSER, NOBYPASSRLS). Configure DATABASE_URL to use it.")


if __name__ == "__main__":
    main()
