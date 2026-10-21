import hashlib
import json
import logging
import time
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAIError
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import SQLAlchemyError

from .agent import run_agent, run_view
from .config import get_settings
from .db import session_scope
from .jobs import ingest_task
from .models import (
    Action,
    Audit,
    Chunk,
    CRMTask,
    Customer,
    Document,
    LoginSession,
    Run,
    Tenant,
    Ticket,
)
from .observability import LATENCY, REQUESTS, instrument
from .rag import search
from .schemas import (
    ChatInput,
    CustomerInput,
    DecisionInput,
    DocumentInput,
    LoginInput,
    ProposalInput,
    SearchInput,
    TicketInput,
    TicketUpdate,
)
from .security import Principal, current_user, login, require_admin, token_hash
from .services import (
    action_view,
    customer_for,
    customer_view,
    decide,
    list_customers,
    propose,
    ticket_view,
)

cfg = get_settings()
app = FastAPI(
    title="CustomerOps AI",
    version="1.0.0",
    description="Customer operations agent: local CRM, RAG, and human approval.",
)
instrument(app)
log = logging.getLogger("customerops")
redis = Redis.from_url(cfg.redis_url, socket_connect_timeout=2, socket_timeout=2)


def rate_limit(key: str, limit: int, seconds: int = 60):
    try:
        count = redis.eval(
            "local n=redis.call('INCR',KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],ARGV[1]) end; return n",
            1,
            "customerops:limit:" + key,
            seconds,
        )
    except RedisError:
        raise HTTPException(503, "Access control service unavailable") from None
    if count > limit:
        raise HTTPException(
            429,
            "Rate limit reached. Please wait one minute.",
            headers={"Retry-After": str(seconds)},
        )


@app.middleware("http")
async def request_context(request: Request, call_next):
    started, request_id = time.monotonic(), str(uuid4())
    response = await call_next(request)
    route = getattr(request.scope.get("route"), "path", "unmatched")
    duration = time.monotonic() - started
    REQUESTS.labels(request.method, route, str(response.status_code)).inc()
    LATENCY.labels(route).observe(duration)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'"
        if not request.url.path.startswith("/docs")
        else "frame-ancestors 'none'"
    )
    if request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-store"
    log.info(
        json.dumps(
            {
                "request_id": request_id,
                "method": request.method,
                "route": route,
                "status": response.status_code,
                "duration_ms": round(duration * 1000),
            }
        )
    )
    return response


@app.exception_handler(SQLAlchemyError)
async def database_error(request, exc):
    log.error("Database operation failed: %s", type(exc).__name__)
    return JSONResponse(status_code=503, content={"detail": "Database unavailable"})


@app.exception_handler(OpenAIError)
async def model_error(request, exc):
    log.error("LLM request failed: %s", type(exc).__name__)
    return JSONResponse(
        status_code=502,
        content={"detail": "AI provider request failed. Check the configuration and try again."},
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
def database_health():
    with session_scope() as db:
        db.execute(text("SELECT 1"))
        version = db.scalar(text("SELECT extversion FROM pg_extension WHERE extname='vector'"))
    if not version:
        raise HTTPException(503, "pgvector unavailable")
    return {"status": "ok", "database": "connected", "pgvector": version}


@app.get("/health/ready")
def ready():
    database_health()
    try:
        redis.ping()
    except RedisError:
        raise HTTPException(503, "Redis unavailable") from None
    return {"status": "ok"}


@app.post("/api/auth/login")
def sign_in(data: LoginInput, request: Request, response: Response):
    if request.headers.get("Origin") not in {None, cfg.allowed_origin}:
        raise HTTPException(403, "Invalid origin")
    rate_limit("login:" + (request.client.host if request.client else "unknown"), 10)
    result = login(data.tenant_id, data.email, data.password)
    if not result:
        raise HTTPException(401, "Invalid credentials")
    token, user = result
    response.set_cookie(
        "customerops_session",
        token,
        httponly=True,
        secure=cfg.cookie_secure,
        samesite="strict",
        max_age=cfg.session_hours * 3600,
        path="/",
    )
    return {"email": user.email, "role": user.role, "tenant_id": user.tenant_id}


@app.get("/api/me")
def me(user: Principal = Depends(current_user)):
    with session_scope() as db:
        tenant_name = db.get(Tenant, user.tenant_id).name
    return {
        "tenant_name": tenant_name,
        "email": user.email,
        "role": user.role,
        "tenant_id": user.tenant_id,
        "ai_mode": cfg.ai_mode,
        "model": cfg.openai_model if cfg.ai_mode == "openai" else "deterministic workflow",
        "cost_configured": cfg.input_usd_per_million > 0 and cfg.output_usd_per_million > 0,
    }


@app.post("/api/auth/logout", status_code=204)
def logout(request: Request, response: Response, user: Principal = Depends(current_user)):
    token = request.cookies.get("customerops_session", "")
    if request.headers.get("Authorization", "").startswith("Bearer "):
        token = request.headers["Authorization"][7:]
    with session_scope(user.tenant_id) as db:
        db.execute(delete(LoginSession).where(LoginSession.token_hash == token_hash(token)))
    response.delete_cookie("customerops_session", path="/")


@app.get("/api/customers")
def customers(user: Principal = Depends(current_user)):
    with session_scope(user.tenant_id) as db:
        return list_customers(db, user.tenant_id)


@app.post("/api/customers", status_code=201)
def create_customer(data: CustomerInput, user: Principal = Depends(require_admin)):
    with session_scope(user.tenant_id) as db:
        if db.scalar(
            select(Customer).where(
                Customer.tenant_id == user.tenant_id,
                Customer.external_id == data.external_id,
            )
        ):
            raise HTTPException(409, "External ID already exists")
        customer = Customer(tenant_id=user.tenant_id, **data.model_dump())
        db.add(customer)
        db.flush()
        return customer_view(db, customer)


@app.get("/api/customers/{customer_id}")
def get_customer(customer_id: str, user: Principal = Depends(current_user)):
    with session_scope(user.tenant_id) as db:
        return customer_view(db, customer_for(db, user.tenant_id, customer_id))


@app.get("/api/tickets")
def tickets(customer_id: str | None = None, user: Principal = Depends(current_user)):
    with session_scope(user.tenant_id) as db:
        query = select(Ticket).where(Ticket.tenant_id == user.tenant_id)
        if customer_id:
            customer_for(db, user.tenant_id, customer_id)
            query = query.where(Ticket.customer_id == customer_id)
        return [
            ticket_view(t) for t in db.scalars(query.order_by(Ticket.created_at.desc()).limit(100))
        ]


@app.post("/api/tickets", status_code=201)
def create_ticket(data: TicketInput, user: Principal = Depends(current_user)):
    with session_scope(user.tenant_id) as db:
        customer_for(db, user.tenant_id, data.customer_id)
        ticket = Ticket(tenant_id=user.tenant_id, **data.model_dump())
        db.add(ticket)
        db.flush()
        return ticket_view(ticket)


@app.patch("/api/tickets/{ticket_id}")
def update_ticket(ticket_id: str, data: TicketUpdate, user: Principal = Depends(current_user)):
    with session_scope(user.tenant_id) as db:
        ticket = db.scalar(
            select(Ticket)
            .where(Ticket.id == ticket_id, Ticket.tenant_id == user.tenant_id)
            .with_for_update()
        )
        if not ticket:
            raise HTTPException(404, "Ticket not found")
        ticket.status = data.status
        db.add(
            Audit(
                tenant_id=user.tenant_id,
                user_id=user.user_id,
                event="ticket." + data.status,
                resource_id=ticket.id,
            )
        )
        return ticket_view(ticket)


@app.post("/api/chat")
def chat(data: ChatInput, user: Principal = Depends(current_user)):
    rate_limit("chat:" + user.user_id, 12)
    return run_agent(user, data.question, data.customer_id)


@app.get("/api/runs")
def runs(user: Principal = Depends(current_user)):
    with session_scope(user.tenant_id) as db:
        return [
            run_view(r)
            for r in db.scalars(
                select(Run)
                .where(Run.tenant_id == user.tenant_id)
                .order_by(Run.created_at.desc())
                .limit(30)
            )
        ]


@app.get("/api/actions")
def actions(user: Principal = Depends(current_user)):
    with session_scope(user.tenant_id) as db:
        return [
            action_view(a)
            for a in db.scalars(
                select(Action)
                .where(Action.tenant_id == user.tenant_id)
                .order_by(Action.created_at.desc())
                .limit(100)
            )
        ]


@app.post("/api/actions", status_code=201)
def create_proposal(data: ProposalInput, user: Principal = Depends(current_user)):
    with session_scope(user.tenant_id) as db:
        return action_view(propose(db, user, data))


@app.post("/api/actions/{action_id}/decision")
def action_decision(action_id: str, data: DecisionInput, user: Principal = Depends(require_admin)):
    with session_scope(user.tenant_id) as db:
        return action_view(decide(db, user, action_id, data.decision))


@app.get("/api/crm/tasks")
def crm_tasks(user: Principal = Depends(current_user)):
    with session_scope(user.tenant_id) as db:
        return [
            {
                "id": t.id,
                "customer_id": t.customer_id,
                "title": t.title,
                "action_id": t.action_id,
            }
            for t in db.scalars(
                select(CRMTask).where(CRMTask.tenant_id == user.tenant_id).limit(100)
            )
        ]


@app.get("/api/documents")
def documents(user: Principal = Depends(current_user)):
    with session_scope(user.tenant_id) as db:
        rows = db.execute(
            select(Document, func.count(Chunk.id))
            .outerjoin(Chunk)
            .where(Document.tenant_id == user.tenant_id)
            .group_by(Document.id)
            .order_by(Document.created_at.desc())
            .limit(100)
        )
        return [
            {
                "id": d.id,
                "title": d.title,
                "status": d.status,
                "chunks": count,
                "error": d.error,
            }
            for d, count in rows
        ]


def enqueue(document_id: str, tenant_id: str):
    try:
        ingest_task.apply_async(args=[document_id, tenant_id], retry=False)
    except Exception:
        raise HTTPException(
            503,
            "Document saved, but the queue is unavailable. Reindex once the worker is running.",
        ) from None


@app.post("/api/documents", status_code=202)
def create_document(data: DocumentInput, user: Principal = Depends(require_admin)):
    rate_limit("ingest:" + user.user_id, 10)
    digest = hashlib.sha256(data.content.encode()).hexdigest()
    with session_scope(user.tenant_id) as db:
        doc = db.scalar(
            select(Document).where(
                Document.tenant_id == user.tenant_id, Document.content_hash == digest
            )
        )
        if not doc:
            doc = Document(
                tenant_id=user.tenant_id,
                title=data.title,
                content=data.content,
                content_hash=digest,
            )
            db.add(doc)
            db.flush()
        document_id = doc.id
        if doc.status == "ready":
            return {"id": document_id, "status": "ready"}
    enqueue(document_id, user.tenant_id)
    return {"id": document_id, "status": "pending"}


@app.post("/api/documents/{document_id}/reindex", status_code=202)
def reindex(document_id: str, user: Principal = Depends(require_admin)):
    rate_limit("ingest:" + user.user_id, 10)
    with session_scope(user.tenant_id) as db:
        doc = db.scalar(
            select(Document).where(Document.id == document_id, Document.tenant_id == user.tenant_id)
        )
        if not doc:
            raise HTTPException(404, "Document not found")
        doc.status, doc.error = "pending", None
    enqueue(document_id, user.tenant_id)
    return {"id": document_id, "status": "pending"}


@app.post("/api/knowledge/search")
def knowledge_search(data: SearchInput, user: Principal = Depends(current_user)):
    rate_limit("search:" + user.user_id, 30)
    with session_scope(user.tenant_id) as db:
        return search(db, user.tenant_id, data.query)


@app.get("/api/audit")
def audit(user: Principal = Depends(require_admin)):
    with session_scope(user.tenant_id) as db:
        return [
            {
                "event": a.event,
                "resource_id": a.resource_id,
                "user_id": a.user_id,
                "created_at": a.created_at.isoformat(),
            }
            for a in db.scalars(
                select(Audit)
                .where(Audit.tenant_id == user.tenant_id)
                .order_by(Audit.created_at.desc())
                .limit(100)
            )
        ]


@app.get("/api/metrics")
def metrics(user: Principal = Depends(current_user)):
    with session_scope(user.tenant_id) as db:
        customers = list_customers(db, user.tenant_id)
        total, latency, tokens, cost = db.execute(
            select(
                func.count(Run.id),
                func.avg(Run.latency_ms),
                func.sum(Run.input_tokens + Run.output_tokens),
                func.sum(Run.estimated_cost),
            ).where(Run.tenant_id == user.tenant_id)
        ).one()
        return {
            "customers": len(customers),
            "at_risk": sum(c["risk"] == "high" for c in customers),
            "open_tickets": sum(c["open_tickets"] for c in customers),
            "runs": total,
            "avg_latency_ms": round(latency or 0),
            "tokens": tokens or 0,
            "estimated_cost": cost or 0,
            "pending_actions": db.scalar(
                select(func.count(Action.id)).where(
                    Action.tenant_id == user.tenant_id, Action.status == "pending"
                )
            ),
        }


@app.get("/metrics", include_in_schema=False)
def prometheus(user: Principal = Depends(require_admin)):
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


if (cfg.frontend_dir / "assets").exists():
    app.mount("/assets", StaticFiles(directory=cfg.frontend_dir / "assets"), name="assets")


@app.get("/", include_in_schema=False)
def index():
    path = cfg.frontend_dir / "index.html"
    if not path.exists():
        return {
            "message": "Run npm ci and npm run build in the frontend directory, then restart the API."
        }
    return FileResponse(path)
