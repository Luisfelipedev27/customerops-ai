import math

import pytest
from pydantic import ValidationError

from customerops_ai.config import Settings
from customerops_ai.rag import embed, split_text
from customerops_ai.security import hash_password, verify_password


def test_password_salted_and_verified():
    one, two = hash_password("sample-password"), hash_password("sample-password")
    assert one != two
    assert verify_password("sample-password", one)
    assert not verify_password("incorrect", one)


def test_chunks_overlap_without_losing_text():
    text = "".join(str(i % 10) for i in range(3000))
    chunks = split_text(text)
    assert chunks[0][-200:] == chunks[1][:200]
    assert chunks[-1].endswith(text[-100:])


def test_demo_vectors_normalized_and_deterministic(monkeypatch):
    from customerops_ai.config import get_settings

    monkeypatch.setattr(get_settings(), "ai_mode", "demo")
    first = embed("résumé Support Enterprise")
    assert len(first) == 384
    assert first == embed("resume support enterprise")
    assert math.isclose(sum(x * x for x in first), 1)


@pytest.mark.parametrize("encoded", ["", "invalid", "a$b$c", "z" * 32 + "$" + "0" * 64])
def test_malformed_password_hash_is_rejected(encoded):
    assert not verify_password("sample-password", encoded)


@pytest.mark.parametrize("size,overlap", [(0, 0), (10, 10), (10, -1), (10, 20)])
def test_invalid_chunk_boundaries_are_rejected(size, overlap):
    with pytest.raises(ValueError):
        split_text("document", size=size, overlap=overlap)


@pytest.mark.parametrize(
    "values",
    [
        {"session_hours": 0},
        {"input_usd_per_million": -1},
        {"output_usd_per_million": float("nan")},
    ],
)
def test_invalid_settings_are_rejected(values):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **values)
