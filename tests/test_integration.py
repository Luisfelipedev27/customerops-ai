from uuid import uuid4

import pytest
from sqlalchemy import func, select

from customerops_ai.agent import execute_tool
from customerops_ai.db import session_scope
from customerops_ai.models import Action, Chunk, CRMTask, Customer, Document, Run
from customerops_ai.security import authenticate_token
from customerops_ai.seed import DEMO_TENANT, OTHER_TENANT

pytestmark = pytest.mark.integration


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/health/db").json()["pgvector"]


def test_unauthenticated_rejected(client):
    client.cookies.clear()
    assert client.get("/api/customers").status_code == 401


def test_login_cookie_and_logout(client):
    response = client.post(
        "/api/auth/login",
        json={
            "tenant_id": DEMO_TENANT,
            "email": "admin@customerops.local",
            "password": "customerops-test-password",
        },
    )
    assert response.status_code == 200
    assert "HttpOnly" in response.headers["set-cookie"]
    assert client.get("/api/me").status_code == 200
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/me").status_code == 401


def test_cross_origin_login_blocked(client):
    assert (
        client.post(
            "/api/auth/login",
            headers={"Origin": "https://evil.example"},
            json={
                "tenant_id": DEMO_TENANT,
                "email": "admin@customerops.local",
                "password": "customerops-test-password",
            },
        ).status_code
        == 403
    )


def test_csrf_rejected(client):
    from customerops_ai.security import login

    token, _ = login(DEMO_TENANT, "admin@customerops.local", "customerops-test-password")
    client.cookies.set("customerops_session", token)
    result = client.post(
        "/api/chat", headers={"Origin": "https://evil.example"}, json={"question": "hello world"}
    )
    client.cookies.clear()
    assert result.status_code == 403


def test_tenant_isolation_api_and_tool(client, admin):
    with session_scope() as db:
        foreign = db.scalar(select(Customer).where(Customer.tenant_id == OTHER_TENANT))
        foreign_id = foreign.id
    assert all(
        c["name"] != "Confidential Other Tenant"
        for c in client.get("/api/customers", headers=admin).json()
    )
    assert client.get("/api/customers/" + foreign_id, headers=admin).status_code == 404
    assert (
        client.get("/api/tickets", params={"customer_id": foreign_id}, headers=admin).status_code
        == 404
    )
    assert (
        client.post(
            "/api/chat",
            headers=admin,
            json={"question": "Investigate this account", "customer_id": foreign_id},
        ).status_code
        == 404
    )
    user = authenticate_token(admin["Authorization"][7:])
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        execute_tool("get_customer", {"customer_id": foreign_id}, user, "unused")


def test_proposal_approval_is_idempotent(client, admin, analyst):
    customer = client.get("/api/customers", headers=admin).json()[0]
    data = {
        "customer_id": customer["id"],
        "title": "Follow-up integration test",
        "idempotency_key": str(uuid4()),
    }
    a = client.post("/api/actions", headers=analyst, json=data)
    assert a.status_code == 201
    a = a.json()
    assert client.post("/api/actions", headers=analyst, json=data).json()["id"] == a["id"]
    with session_scope() as db:
        assert not db.scalar(select(CRMTask).where(CRMTask.action_id == a["id"]))
    assert (
        client.post(
            "/api/actions/" + a["id"] + "/decision", headers=analyst, json={"decision": "approve"}
        ).status_code
        == 403
    )
    for _ in range(2):
        assert (
            client.post(
                "/api/actions/" + a["id"] + "/decision", headers=admin, json={"decision": "approve"}
            ).json()["status"]
            == "executed"
        )
    assert (
        client.post(
            "/api/actions/" + a["id"] + "/decision", headers=admin, json={"decision": "reject"}
        ).status_code
        == 409
    )
    with session_scope() as db:
        assert db.scalar(select(func.count(CRMTask.id)).where(CRMTask.action_id == a["id"])) == 1


def test_rejection_never_executes(client, admin):
    customer = client.get("/api/customers", headers=admin).json()[0]
    action = client.post(
        "/api/actions",
        headers=admin,
        json={
            "customer_id": customer["id"],
            "title": "Reject this proposal",
            "idempotency_key": str(uuid4()),
        },
    ).json()
    assert (
        client.post(
            "/api/actions/" + action["id"] + "/decision", headers=admin, json={"decision": "reject"}
        ).json()["status"]
        == "rejected"
    )
    with session_scope() as db:
        assert not db.scalar(select(CRMTask).where(CRMTask.action_id == action["id"]))


def test_rag_provenance_and_tenant_filter(client, admin):
    sources = client.post(
        "/api/knowledge/search",
        headers=admin,
        json={"query": "Enterprise SLA critical incidents hour"},
    ).json()
    assert sources
    assert any("hour" in s["text"] for s in sources)
    with session_scope() as db:
        assert all(db.get(Chunk, s["id"]).tenant_id == DEMO_TENANT for s in sources)


def test_chat_uses_tools_and_persists(client, admin):
    result = client.post(
        "/api/chat",
        headers=admin,
        json={"question": "Why is Acme Corp at risk? Propose a follow-up task."},
    )
    assert result.status_code == 200
    run = result.json()
    names = {c["name"] for c in run["tool_calls"]}
    assert {"get_customer", "get_tickets", "search_knowledge", "propose_follow_up"} <= names
    assert run["sources"] and run["mode"] == "demo"
    assert "There are 3 open tickets" in run["answer"]
    assert "awaiting human approval" in run["answer"]
    with session_scope() as db:
        assert db.get(Run, run["id"]).status == "completed"
        actions = list(db.scalars(select(Action).where(Action.run_id == run["id"])))
        assert actions and all(a.status == "pending" for a in actions)


def test_unknown_tool_and_extra_arguments_rejected(client, admin):
    user = authenticate_token(admin["Authorization"][7:])
    assert "error" in execute_tool("execute_sql", {}, user, "unused")
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        execute_tool("list_customers", {"tenant_id": OTHER_TENANT}, user, "unused")


def test_model_cannot_approve(client, admin):
    user = authenticate_token(admin["Authorization"][7:])
    assert "error" in execute_tool("approve_action", {}, user, "unused")


def test_document_ingestion_idempotent(client, admin):
    import hashlib

    from customerops_ai.rag import ingest_document

    content = "Unique integration test: Enterprise support responds within one hour."
    with session_scope() as db:
        doc = db.scalar(
            select(Document).where(
                Document.tenant_id == DEMO_TENANT,
                Document.content_hash == hashlib.sha256(content.encode()).hexdigest(),
            )
        )
        if not doc:
            doc = Document(
                tenant_id=DEMO_TENANT,
                title="Test document",
                content=content,
                content_hash=hashlib.sha256(content.encode()).hexdigest(),
            )
            db.add(doc)
            db.flush()
        document_id = doc.id
    ingest_document(document_id, DEMO_TENANT)
    ingest_document(document_id, DEMO_TENANT)
    with session_scope() as db:
        assert db.scalar(select(func.count(Chunk.id)).where(Chunk.document_id == document_id)) == 1


def test_analyst_cannot_ingest(client, analyst):
    assert (
        client.post(
            "/api/documents",
            headers=analyst,
            json={
                "title": "A document",
                "content": "This is a sufficiently long internal document.",
            },
        ).status_code
        == 403
    )


def test_ticket_resolution_updates_risk(client, admin):
    customer = client.post(
        "/api/customers",
        headers=admin,
        json={"name": "Test Risk", "external_id": str(uuid4()), "contact": "test@example.com"},
    ).json()
    ticket = client.post(
        "/api/tickets",
        headers=admin,
        json={
            "customer_id": customer["id"],
            "title": "Critical error",
            "body": "Something is broken",
            "priority": "critical",
        },
    ).json()
    assert client.get("/api/customers/" + customer["id"], headers=admin).json()["risk_score"] == 25
    assert (
        client.patch(
            "/api/tickets/" + ticket["id"], headers=admin, json={"status": "resolved"}
        ).status_code
        == 200
    )
    assert client.get("/api/customers/" + customer["id"], headers=admin).json()["risk_score"] == 0


def test_metrics_require_admin(client, analyst, admin):
    assert client.get("/metrics", headers=analyst).status_code == 403
    assert client.get("/metrics", headers=admin).status_code == 200


def test_concurrent_proposals_create_one_action(client, admin):
    from concurrent.futures import ThreadPoolExecutor

    from customerops_ai.schemas import ProposalInput
    from customerops_ai.services import propose

    user = authenticate_token(admin["Authorization"][7:])
    customer = client.get("/api/customers", headers=admin).json()[0]
    data = ProposalInput(
        customer_id=customer["id"], title="Concurrent proposal", idempotency_key=str(uuid4())
    )

    def create():
        with session_scope(user.tenant_id) as db:
            return propose(db, user, data).id

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: create(), range(2)))
    assert results[0] == results[1]
