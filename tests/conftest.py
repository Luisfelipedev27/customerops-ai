import os

import pytest

test_url = os.environ.get("TEST_DATABASE_URL")
if test_url:
    from sqlalchemy.engine import make_url

    if not make_url(test_url).database.endswith("_test"):
        raise RuntimeError("TEST_DATABASE_URL must name a database ending in _test")
    os.environ["DATABASE_URL"] = test_url
    os.environ["AI_MODE"] = "demo"
    os.environ["DEMO_PASSWORD"] = "customerops-test-password"
    os.environ["ALLOWED_ORIGIN"] = "http://testserver"


@pytest.fixture(scope="session")
def client():
    if not test_url:
        pytest.skip("Set TEST_DATABASE_URL to an isolated *_test database")
    from fastapi.testclient import TestClient

    from customerops_ai.api import app
    from customerops_ai.seed import main

    main()
    with TestClient(
        app, base_url="http://testserver", headers={"Origin": "http://testserver"}
    ) as client:
        yield client


@pytest.fixture
def admin(client):
    from customerops_ai.security import login
    from customerops_ai.seed import DEMO_TENANT

    token, _ = login(DEMO_TENANT, "admin@customerops.local", "customerops-test-password")
    client.cookies.clear()
    return {"Authorization": "Bearer " + token}


@pytest.fixture
def analyst(client):
    from customerops_ai.security import login
    from customerops_ai.seed import DEMO_TENANT

    token, _ = login(DEMO_TENANT, "analyst@customerops.local", "customerops-test-password")
    return {"Authorization": "Bearer " + token}
