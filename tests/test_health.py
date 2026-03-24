"""Basic smoke tests for the HTTP API."""

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.chat import ChatRequest

client = TestClient(app)


def test_health_check() -> None:
    # Verify that the service boots and the health route remains stable.
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["llm_provider"] in {"openai", "ark"}


def test_chat_request_accepts_legacy_content_field() -> None:
    payload = ChatRequest.model_validate({"content": "hello"})

    assert payload.message == "hello"
