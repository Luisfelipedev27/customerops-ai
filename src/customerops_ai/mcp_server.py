"""Local stdio MCP server. Pass a short-lived session token via MCP_SESSION_TOKEN.
No tenant argument is accepted from tool callers. Never expose this process as unauthenticated HTTP.
"""

import os

from mcp.server.fastmcp import FastMCP
from sqlalchemy import select

from .db import session_scope
from .models import Ticket
from .rag import search
from .security import authenticate_token
from .services import customer_for, customer_view, list_customers, ticket_view

mcp = FastMCP("CustomerOps — read-only tools")


def principal():
    token = os.environ.get("MCP_SESSION_TOKEN", "")
    if not token:
        raise ValueError("MCP_SESSION_TOKEN is required")
    return authenticate_token(token)


@mcp.tool()
def customers() -> list[dict]:
    """List customers of the authenticated tenant."""
    user = principal()
    with session_scope(user.tenant_id) as db:
        return list_customers(db, user.tenant_id)


@mcp.tool()
def customer_details(customer_id: str) -> dict:
    """Read customer details, scoped to the authenticated tenant."""
    user = principal()
    with session_scope(user.tenant_id) as db:
        return customer_view(db, customer_for(db, user.tenant_id, customer_id))


@mcp.tool()
def customer_tickets(customer_id: str) -> list[dict]:
    """Read support tickets for an authorized customer."""
    user = principal()
    with session_scope(user.tenant_id) as db:
        customer_for(db, user.tenant_id, customer_id)
        return [
            ticket_view(t)
            for t in db.scalars(
                select(Ticket)
                .where(
                    Ticket.tenant_id == user.tenant_id,
                    Ticket.customer_id == customer_id,
                )
                .limit(50)
            )
        ]


@mcp.tool()
def knowledge(query: str) -> list[dict]:
    """Retrieve internal document excerpts with sources."""
    if len(query) > 1000:
        raise ValueError("Query is too long")
    user = principal()
    with session_scope(user.tenant_id) as db:
        return search(db, user.tenant_id, query)


if __name__ == "__main__":
    mcp.run(transport="stdio")
