"""Request and response schemas for the chat API."""

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    """Incoming payload for a single chat completion request."""

    model_config = ConfigDict(populate_by_name=True)

    # Accept both `message` and the frontend's legacy `content` field so the
    # API can remain compatible while the caller is being updated.
    message: str = Field(
        ...,
        min_length=1,
        validation_alias=AliasChoices("message", "content"),
        description="User input message.",
    )
    system_prompt: str | None = Field(
        default="You are a helpful AI assistant.",
        description="Optional system prompt.",
    )


class ChatResponse(BaseModel):
    """Standard response returned by the chat API."""

    answer: str
    model: str
    provider: str
