from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pydantic import SecretStr
from sqlalchemy import select

from customerops_ai.agent import run_agent
from customerops_ai.db import session_scope
from customerops_ai.models import User
from customerops_ai.security import Principal
from customerops_ai.seed import DEMO_TENANT


@pytest.mark.integration
def test_real_provider_function_call_contract(client, monkeypatch):
    import customerops_ai.agent as module
    from customerops_ai.config import get_settings

    cfg = get_settings()
    monkeypatch.setattr(cfg, "ai_mode", "openai")
    monkeypatch.setattr(cfg, "openai_api_key", SecretStr("unit-test-not-a-real-key"))
    monkeypatch.setattr(cfg, "openai_model", "test-model")
    call = SimpleNamespace(
        type="function_call", name="list_customers", arguments="{}", call_id="test-call"
    )
    mock = MagicMock()
    mock.responses.create.side_effect = [
        SimpleNamespace(
            output=[call], output_text="", usage=SimpleNamespace(input_tokens=20, output_tokens=5)
        ),
        SimpleNamespace(
            output=[],
            output_text="I checked the authorized accounts.",
            usage=SimpleNamespace(input_tokens=30, output_tokens=10),
        ),
    ]
    monkeypatch.setattr(module, "OpenAI", lambda **kwargs: mock)
    with session_scope() as db:
        user = db.scalar(select(User).where(User.tenant_id == DEMO_TENANT, User.role == "admin"))
        principal = Principal(user.id, user.tenant_id, user.role, user.email)
    result = run_agent(principal, "List the customers")
    assert result["input_tokens"] == 50 and result["output_tokens"] == 15
    assert result["tool_calls"][0]["name"] == "list_customers"
    assert mock.responses.create.call_args_list[0].kwargs["store"] is False
    assert (
        "Always respond in English"
        in mock.responses.create.call_args_list[0].kwargs["instructions"]
    )
    outputs = mock.responses.create.call_args_list[1].kwargs["input"]
    assert any(isinstance(o, dict) and o.get("type") == "function_call_output" for o in outputs)
    mock.close.assert_called_once()
