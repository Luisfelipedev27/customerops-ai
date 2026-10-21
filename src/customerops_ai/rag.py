import hashlib
import math
import re
import unicodedata

from openai import OpenAI
from sqlalchemy import delete, select

from .config import get_settings
from .db import session_scope
from .models import Chunk, Document
from .observability import tracer


def normalize(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", text.lower()) if not unicodedata.combining(c)
    )


def embedding_name() -> str:
    cfg = get_settings()
    return "demo-hash-v1" if cfg.ai_mode == "demo" else cfg.embedding_model


def embed(text: str) -> list[float]:
    cfg = get_settings()
    if cfg.ai_mode == "openai":
        if not cfg.openai_api_key.get_secret_value():
            raise ValueError("OPENAI_API_KEY is not configured")
        with OpenAI(
            api_key=cfg.openai_api_key.get_secret_value(), timeout=30, max_retries=2
        ) as client:
            return (
                client.embeddings.create(model=cfg.embedding_model, input=text, dimensions=384)
                .data[0]
                .embedding
            )

    vector = [0.0] * 384
    for word in re.findall(r"[a-z0-9]{3,}", normalize(text)):
        digest = hashlib.sha256(word.encode()).digest()
        vector[int.from_bytes(digest[:4], "big") % 384] += 1
    norm = math.sqrt(sum(x * x for x in vector)) or 1
    return [x / norm for x in vector]


def split_text(content: str, size: int = 1200, overlap: int = 200) -> list[str]:
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError("Chunk size must be positive and overlap must be between zero and size")
    return [
        content[i : i + size]
        for i in range(0, len(content), size - overlap)
        if content[i : i + size].strip()
    ]


def ingest_document(document_id: str, tenant_id: str):
    with session_scope(tenant_id) as db:
        document = db.scalar(
            select(Document)
            .where(Document.id == document_id, Document.tenant_id == tenant_id)
            .with_for_update()
        )
        if not document:
            raise ValueError("Document not found")
        model = embedding_name()

        db.execute(
            delete(Chunk).where(Chunk.document_id == document_id, Chunk.tenant_id == tenant_id)
        )
        with tracer.start_as_current_span("rag.ingest"):
            for position, text in enumerate(split_text(document.content)):
                db.add(
                    Chunk(
                        tenant_id=tenant_id,
                        document_id=document_id,
                        text=text,
                        position=position,
                        embedding_model=model,
                        embedding=embed(text),
                    )
                )
        document.status, document.error = "ready", None


def search(db, tenant_id: str, query: str, limit: int = 4) -> list[dict]:
    vector = embed(query)
    distance = Chunk.embedding.cosine_distance(vector)
    with tracer.start_as_current_span("rag.search"):
        rows = db.execute(
            select(Chunk, Document.title, distance.label("distance"))
            .join(Document, Chunk.document_id == Document.id)
            .where(
                Chunk.tenant_id == tenant_id,
                Document.tenant_id == tenant_id,
                Document.status == "ready",
                Chunk.embedding_model == embedding_name(),
                distance < 0.95,
            )
            .order_by(distance)
            .limit(limit)
        ).all()
    return [
        {
            "id": chunk.id,
            "document_id": chunk.document_id,
            "title": title,
            "text": chunk.text,
            "score": round(max(0, 1 - float(dist)), 3),
        }
        for chunk, title, dist in rows
    ]
