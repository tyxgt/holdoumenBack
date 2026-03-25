"""Tests for chat route streaming behavior."""

from collections.abc import AsyncIterator

from fastapi.testclient import TestClient

from app.main import app
from app.services.langchain_service import get_langchain_service


class _FakeLangChainService:
    async def chat(self, user_message: str, system_prompt: str | None = None) -> str:
        return f"echo:{user_message}:{system_prompt or ''}"

    async def stream_chat(
        self, user_message: str, system_prompt: str | None = None
    ) -> AsyncIterator[str]:
        yield "hello"
        yield " "
        yield "world"


def test_chat_stream_returns_sse_events() -> None:
    app.dependency_overrides[get_langchain_service] = lambda: _FakeLangChainService()

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/chat",
                json={"message": "hi", "system_prompt": "sp", "stream": True},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: meta" in response.text
    assert 'event: delta\ndata: {"delta": "hello"}' in response.text
    assert 'event: delta\ndata: {"delta": "world"}' in response.text
    assert "event: done\ndata: [DONE]" in response.text


def test_chat_non_stream_keeps_json_contract() -> None:
    app.dependency_overrides[get_langchain_service] = lambda: _FakeLangChainService()

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/chat",
                json={"message": "hi", "system_prompt": "sp", "stream": False},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    payload = response.json()
    assert payload["answer"] == "echo:hi:sp"
    assert payload["provider"] in {"openai", "ark"}
