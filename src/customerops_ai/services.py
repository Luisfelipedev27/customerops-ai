import hashlib

from fastapi import HTTPException
from sqlalchemy import and_, func, select, text
from sqlalchemy.orm import Session

from .models import Action, Audit, CRMTask, Customer, Ticket
from .schemas import ProposalInput
from .security import Principal


def customer_for(db: Session, tenant_id: str, customer_id: str) -> Customer:
    customer = db.scalar(
        select(Customer).where(Customer.id == customer_id, Customer.tenant_id == tenant_id)
    )
    if not customer:
        raise HTTPException(404, "Customer not found")
    return customer


def customer_view(db: Session, customer: Customer) -> dict:
    tickets = list(
        db.scalars(
            select(Ticket).where(
                Ticket.tenant_id == customer.tenant_id,
                Ticket.customer_id == customer.id,
            )
        )
    )
    critical = sum(t.priority == "critical" and t.status != "resolved" for t in tickets)
    opened = sum(t.status != "resolved" for t in tickets)
    return _customer_payload(customer, opened, critical)


def _customer_payload(customer: Customer, opened: int, critical: int) -> dict:
    score = min(100, critical * 25 + max(0, -customer.usage_change))
    return {
        "id": customer.id,
        "external_id": customer.external_id,
        "name": customer.name,
        "contact": customer.contact,
        "plan": customer.plan,
        "mrr": customer.mrr,
        "usage_change": customer.usage_change,
        "open_tickets": opened,
        "critical_tickets": critical,
        "risk_score": score,
        "risk": "high" if score >= 60 else "medium" if score >= 25 else "low",
    }


def list_customers(db: Session, tenant_id: str) -> list[dict]:

    query = (
        select(
            Customer,
            func.count(Ticket.id).filter(Ticket.status != "resolved"),
            func.count(Ticket.id).filter(
                Ticket.status != "resolved", Ticket.priority == "critical"
            ),
        )
        .outerjoin(
            Ticket, and_(Ticket.customer_id == Customer.id, Ticket.tenant_id == Customer.tenant_id)
        )
        .where(Customer.tenant_id == tenant_id)
        .group_by(Customer.id)
        .order_by(Customer.name)
        .limit(100)
    )
    return [
        _customer_payload(customer, opened, critical)
        for customer, opened, critical in db.execute(query)
    ]


def ticket_view(ticket: Ticket) -> dict:
    return {
        "id": ticket.id,
        "customer_id": ticket.customer_id,
        "title": ticket.title,
        "body": ticket.body,
        "priority": ticket.priority,
        "status": ticket.status,
        "created_at": ticket.created_at.isoformat(),
    }


def propose(db: Session, user: Principal, data: ProposalInput, run_id: str | None = None) -> Action:
    customer_for(db, user.tenant_id, data.customer_id)
    lock_key = int.from_bytes(
        hashlib.sha256((user.tenant_id + data.idempotency_key).encode()).digest()[:8],
        "big",
        signed=True,
    )
    db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_key})
    existing = db.scalar(
        select(Action).where(
            Action.tenant_id == user.tenant_id,
            Action.idempotency_key == data.idempotency_key,
        )
    )
    if existing:
        if existing.customer_id != data.customer_id or existing.title != data.title:
            raise HTTPException(409, "Idempotency key already used with different content")
        return existing
    action = Action(
        tenant_id=user.tenant_id,
        customer_id=data.customer_id,
        title=data.title,
        run_id=run_id,
        idempotency_key=data.idempotency_key,
    )
    db.add(action)
    db.flush()
    db.add(
        Audit(
            tenant_id=user.tenant_id,
            user_id=user.user_id,
            event="action.proposed",
            resource_id=action.id,
        )
    )
    return action


def action_view(action: Action) -> dict:
    return {
        "id": action.id,
        "customer_id": action.customer_id,
        "title": action.title,
        "status": action.status,
        "run_id": action.run_id,
        "created_at": action.created_at.isoformat(),
    }


def decide(db: Session, user: Principal, action_id: str, decision: str) -> Action:
    if user.role != "admin":
        raise HTTPException(403, "This action requires an administrator")
    action = db.scalar(
        select(Action)
        .where(Action.id == action_id, Action.tenant_id == user.tenant_id)
        .with_for_update()
    )
    if not action:
        raise HTTPException(404, "Action not found")
    expected = "executed" if decision == "approve" else "rejected"
    if action.status == expected:
        return action
    if action.status != "pending":
        raise HTTPException(409, "This action already has a decision")
    if decision == "approve":
        customer_for(db, user.tenant_id, action.customer_id)
        db.add(
            CRMTask(
                tenant_id=user.tenant_id,
                action_id=action.id,
                customer_id=action.customer_id,
                title=action.title,
            )
        )
        action.approved_by = user.user_id
    action.status = expected
    db.add(
        Audit(
            tenant_id=user.tenant_id,
            user_id=user.user_id,
            event=f"action.{expected}",
            resource_id=action.id,
        )
    )
    db.flush()
    return action
