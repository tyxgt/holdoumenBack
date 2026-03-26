"""LangChain service abstraction.

This file hides provider-specific model setup from the API layer and exposes a
simple async `chat` method for the rest of the application.
"""

from collections.abc import AsyncIterator
from functools import lru_cache

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.core.config import Settings, get_settings
from app.core.prompts import SYSTEM_PROMPT


class LangChainConfigurationError(RuntimeError):
    """Raised when the LangChain provider configuration is incomplete."""


class LangChainService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _build_llm(self) -> ChatOpenAI:
        # Keep the supported providers explicit so startup failures are easier
        # to diagnose when someone edits `.env`.
        if self.settings.normalized_provider not in {"openai", "ark"}:
            raise LangChainConfigurationError(
                "Only the openai and ark providers are configured in this template."
            )

        # Fail fast if the selected provider is missing its credential.
        if not self.settings.resolved_api_key:
            raise LangChainConfigurationError(
                "The selected provider API key is missing. Please configure it in the .env file."
            )

        # Both OpenAI and Ark can be called through the same OpenAI-compatible client.
        kwargs = {
            "model": self.settings.resolved_model,
            "temperature": self.settings.llm_temperature,
            "timeout": self.settings.llm_timeout,
            "max_retries": self.settings.llm_max_retries,
            "api_key": self.settings.resolved_api_key,
        }
        if self.settings.resolved_base_url:
            kwargs["base_url"] = self.settings.resolved_base_url

        return ChatOpenAI(**kwargs)

    def _build_chain(self, system_prompt: str | None = None):
        # Keep prompt composition in one place so sync/stream paths stay aligned.
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt or SYSTEM_PROMPT),
                ("human", "{user_input}"),
            ]
        )
        return prompt | self._build_llm() | StrOutputParser()

    async def chat(self, user_message: str, system_prompt: str | None = None) -> str:
        # Compose a minimal prompt -> model -> string-output chain so callers
        # receive plain text instead of provider-specific message objects.
        chain = self._build_chain(system_prompt=system_prompt)
        return await chain.ainvoke({"user_input": user_message})

    async def stream_chat(
        self, user_message: str, system_prompt: str | None = None
    ) -> AsyncIterator[str]:
        # Yield partial text chunks as soon as the provider emits them.
        chain = self._build_chain(system_prompt=system_prompt)
        async for chunk in chain.astream({"user_input": user_message}):
            if chunk:
                yield chunk


@lru_cache
def get_langchain_service() -> LangChainService:
    # Reuse one service instance across requests because it only wraps settings.
    return LangChainService(get_settings())
