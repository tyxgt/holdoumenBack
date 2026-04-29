"""Tests for chat route streaming behavior."""

from collections.abc import AsyncIterator

from fastapi.testclient import TestClient

from app.main import app
from app.services.langchain_service import get_langchain_service


class _FakeLangChainService:
    async def chat(self, user_message: str, character: str) -> str:
        return f"echo:{user_message}:{character}"

    async def stream_chat(
        self, user_message: str, character: str
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
                json={"message": "hi", "character": "蒋敦豪", "stream": True},
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
                json={"message": "hi", "character": "蒋敦豪", "stream": False},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    payload = response.json()
    assert payload["answer"] == "echo:hi:蒋敦豪"
    assert payload["provider"] in {"openai", "ark"}


def test_chat_invalid_character_returns_400() -> None:
    app.dependency_overrides[get_langchain_service] = lambda: _FakeLangChainService()

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/chat",
                json={"message": "hi", "character": "无效角色", "stream": False},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert "无效的角色名" in response.json()["detail"]


def test_chat_missing_character_returns_422() -> None:
    app.dependency_overrides[get_langchain_service] = lambda: _FakeLangChainService()

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/chat",
                json={"message": "hi", "stream": False},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
