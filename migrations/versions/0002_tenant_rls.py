"""Defense-in-depth tenant row policies for non-superuser runtime connections."""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None
TABLES = [
    "customers",
    "tickets",
    "documents",
    "chunks",
    "runs",
    "actions",
    "crm_tasks",
    "audit_events",
]


def upgrade():
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} USING (tenant_id = current_setting('app.tenant_id', true)) WITH CHECK (tenant_id = current_setting('app.tenant_id', true))"
        )


def downgrade():
    for table in TABLES:
        op.execute(f"DROP POLICY tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
