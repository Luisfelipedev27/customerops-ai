from celery import Celery
from sqlalchemy import select

from .config import get_settings
from .db import session_scope
from .models import Document
from .observability import configure_tracing
from .rag import ingest_document

configure_tracing()

celery_app = Celery("customerops", broker=get_settings().redis_url)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    task_ignore_result=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    task_soft_time_limit=240,
    task_time_limit=300,
)


@celery_app.task(bind=True, max_retries=3, name="customerops.ingest")
def ingest_task(self, document_id: str, tenant_id: str):
    try:
        ingest_document(document_id, tenant_id)
    except Exception as exc:
        with session_scope(tenant_id) as db:
            doc = db.scalar(
                select(Document).where(Document.id == document_id, Document.tenant_id == tenant_id)
            )
            if doc:
                doc.status = "failed" if self.request.retries >= self.max_retries else "pending"
                doc.error = "Indexing failed; check the worker logs."
        raise self.retry(exc=exc, countdown=min(60, 2**self.request.retries)) from exc
