"""LangChain 服务层。

这个文件是项目里最核心的 LLM 接入层，专门负责：
- 根据配置创建模型客户端
- 拼接 prompt 和模型调用链
- 对外暴露统一的同步/流式聊天方法

路由层只需要"调用它"，不用理解 provider 的细节。
"""

from collections.abc import AsyncIterator
from functools import lru_cache

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.core.config import Settings, get_settings
from app.core.prompts import build_character_prompt


class LangChainConfigurationError(RuntimeError):
    """LangChain 配置不完整时抛出的异常。"""


class LangChainService:
    """对 LangChain 调用做一层封装。"""

    def __init__(self, settings: Settings):
        self.settings = settings

    def _build_llm(self) -> ChatOpenAI:
        """根据当前配置创建模型客户端。"""
        if self.settings.normalized_provider not in {"openai", "ark"}:
            raise LangChainConfigurationError(
                "Only the openai and ark providers are configured in this template."
            )

        if not self.settings.resolved_api_key:
            raise LangChainConfigurationError(
                "The selected provider API key is missing. Please configure it in the .env file."
            )

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

    def _build_chain(self, system_prompt: str):
        """构建 LangChain 调用链。"""
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                ("human", "{user_input}"),
            ]
        )
        return prompt | self._build_llm() | StrOutputParser()

    async def chat(self, user_message: str, character: str) -> str:
        """非流式聊天。

        Args:
            user_message: 用户输入消息
            character: 要扮演的角色名称

        Returns:
            模型回复内容
        """
        system_prompt = build_character_prompt(character)
        chain = self._build_chain(system_prompt=system_prompt)
        return await chain.ainvoke({"user_input": user_message})

    async def stream_chat(
        self, user_message: str, character: str
    ) -> AsyncIterator[str]:
        """流式聊天。

        Args:
            user_message: 用户输入消息
            character: 要扮演的角色名称

        Yields:
            模型回复的增量文本片段
        """
        system_prompt = build_character_prompt(character)
        chain = self._build_chain(system_prompt=system_prompt)
        async for chunk in chain.astream({"user_input": user_message}):
            if chunk:
                yield chunk


@lru_cache
def get_langchain_service() -> LangChainService:
    return LangChainService(get_settings())
