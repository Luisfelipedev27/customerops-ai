from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from .config import get_settings


@lru_cache
def get_engine():
    return create_engine(
        get_settings().database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        connect_args={"connect_timeout": 5},
    )


@contextmanager
def session_scope(tenant_id: str | None = None):
    with Session(get_engine(), expire_on_commit=False) as session:
        try:
            if tenant_id:
                session.execute(
                    text("SELECT set_config('app.tenant_id', :tenant, true)"), {"tenant": tenant_id}
                )
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
