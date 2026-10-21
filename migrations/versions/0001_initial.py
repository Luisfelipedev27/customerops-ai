"""Initial CustomerOps schema. Schema snapshot is intentionally frozen in this revision."""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    from migrations.schema_v1 import metadata

    metadata.create_all(bind=op.get_bind())


def downgrade():
    from migrations.schema_v1 import metadata

    metadata.drop_all(bind=op.get_bind())
