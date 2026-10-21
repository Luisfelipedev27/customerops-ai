from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoginInput(StrictModel):
    tenant_id: str = Field(min_length=1, max_length=36)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class ChatInput(StrictModel):
    question: str = Field(min_length=3, max_length=4000)
    customer_id: str | None = Field(default=None, max_length=36)


class DocumentInput(StrictModel):
    title: str = Field(min_length=3, max_length=240)
    content: str = Field(min_length=30, max_length=100000)


class CustomerInput(StrictModel):
    external_id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=2, max_length=160)
    contact: str = Field(min_length=3, max_length=254)
    plan: str = Field(default="Enterprise", max_length=40)
    usage_change: int = Field(default=0, ge=-100, le=1000)
    mrr: int = Field(default=0, ge=0)


class TicketInput(StrictModel):
    customer_id: str = Field(min_length=1, max_length=36)
    title: str = Field(min_length=3, max_length=240)
    body: str = Field(min_length=3, max_length=10000)
    priority: Literal["normal", "high", "critical"] = "normal"


class TicketUpdate(StrictModel):
    status: Literal["open", "in_progress", "resolved"]


class ProposalInput(StrictModel):
    customer_id: str = Field(min_length=1, max_length=36)
    title: str = Field(min_length=3, max_length=240)
    idempotency_key: str = Field(min_length=8, max_length=100)


class DecisionInput(StrictModel):
    decision: Literal["approve", "reject"]


class SearchInput(StrictModel):
    query: str = Field(min_length=2, max_length=1000)
