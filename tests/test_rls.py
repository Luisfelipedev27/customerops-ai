import os

import pytest
from sqlalchemy import text

from customerops_ai.db import session_scope
from customerops_ai.seed import DEMO_TENANT, OTHER_TENANT


@pytest.mark.integration
def test_database_rls_without_application_filter(client):
    role = os.environ.get("TEST_RUNTIME_ROLE")
    if not role:
        pytest.skip("TEST_RUNTIME_ROLE not provisioned")
    assert role.replace("_", "").isalnum()
    with session_scope() as db:
        db.execute(text("SET LOCAL ROLE " + role))
        assert db.execute(text("SELECT count(*) FROM customers")).scalar_one() == 0
        db.execute(
            text("SELECT set_config('app.tenant_id', :tenant, true)"), {"tenant": DEMO_TENANT}
        )
        rows = db.execute(text("SELECT tenant_id FROM customers")).scalars().all()
        assert rows and all(t == DEMO_TENANT for t in rows)
        db.execute(
            text("SELECT set_config('app.tenant_id', :tenant, true)"), {"tenant": OTHER_TENANT}
        )
        rows = db.execute(text("SELECT tenant_id FROM customers")).scalars().all()
        assert rows and all(t == OTHER_TENANT for t in rows)
