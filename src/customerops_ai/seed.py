import hashlib

from sqlalchemy import text

from .config import get_settings
from .db import session_scope
from .models import Customer, Document, Tenant, Ticket, User
from .rag import ingest_document
from .security import hash_password

DEMO_TENANT = "11111111-1111-4111-8111-111111111111"
OTHER_TENANT = "22222222-2222-4222-8222-222222222222"


def main():
    password = get_settings().demo_password.get_secret_value()
    if len(password) < 12:
        raise SystemExit("Set DEMO_PASSWORD to at least 12 characters before seeding the database.")
    docs = []
    with session_scope() as db:
        for tenant_id, name in [
            (DEMO_TENANT, "Orbit Workspace"),
            (OTHER_TENANT, "Isolated Workspace"),
        ]:
            db.execute(
                text("SELECT set_config('app.tenant_id', :tenant, true)"), {"tenant": tenant_id}
            )
            if db.get(Tenant, tenant_id):
                continue
            db.add(Tenant(id=tenant_id, name=name))
            db.flush()
            for email, role in [
                ("admin@customerops.local", "admin"),
                ("analyst@customerops.local", "analyst"),
            ]:
                db.add(
                    User(
                        tenant_id=tenant_id,
                        email=email,
                        role=role,
                        password_hash=hash_password(password),
                    )
                )
            names = [
                ("acme", "Acme Corp", -40, 4800),
                ("nova", "Nova Labs", 18, 2400),
                ("atlas", "Atlas Studio", -12, 1600),
                ("pulse", "Pulse Digital", 8, 3200),
            ]
            if tenant_id == OTHER_TENANT:
                names = [("secret", "Confidential Other Tenant", -99, 9999)]
            for external, name, usage, mrr in names:
                customer = Customer(
                    tenant_id=tenant_id,
                    external_id=external,
                    name=name,
                    contact=f"ops@{external}.example",
                    usage_change=usage,
                    mrr=mrr,
                )
                db.add(customer)
                db.flush()
                titles = (
                    [
                        "CRM synchronization interrupted",
                        "Contact import failed",
                        "Order processing timeout",
                    ]
                    if external == "acme"
                    else ["Configuration question"]
                )
                for title in titles:
                    db.add(
                        Ticket(
                            tenant_id=tenant_id,
                            customer_id=customer.id,
                            title=title,
                            body="The customer requests an investigation and a response from support.",
                            priority="critical" if external == "acme" else "normal",
                            status="open" if external in {"acme", "atlas"} else "resolved",
                        )
                    )
            for title, content in [
                (
                    "At-risk account playbook",
                    "At-risk accounts: when critical tickets remain open and product usage drops, "
                    "the account manager should start a priority follow-up. Investigate CRM synchronization, "
                    "business impact, and import failures. Propose a follow-up task. "
                    "Creating the task requires human approval from an administrator.",
                ),
                (
                    "Enterprise support SLA",
                    "The Enterprise SLA specifies an initial response within 1 hour for "
                    "critical incidents, 4 hours for high-priority requests, and 24 hours for normal questions. "
                    "These are response targets, not resolution guarantees. Escalate interrupted CRM synchronization.",
                ),
                (
                    "CRM integration guide",
                    "To investigate interrupted CRM synchronization, check credentials, "
                    "API rate limits, and processing queues. Retry only after validating the root cause. "
                    "Do not expose credentials in responses. Record the investigation and the next customer touchpoint.",
                ),
            ]:
                doc = Document(
                    tenant_id=tenant_id,
                    title=title,
                    content=content,
                    content_hash=hashlib.sha256(content.encode()).hexdigest(),
                )
                db.add(doc)
                db.flush()
                docs.append((doc.id, tenant_id))
    for document_id, tenant_id in docs:
        ingest_document(document_id, tenant_id)
    print("Fictional data created. Login: admin@customerops.local; tenant: " + DEMO_TENANT)


if __name__ == "__main__":
    main()
