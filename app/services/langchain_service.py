"""LangChain 服务层。

这个文件是项目里最核心的 LLM 接入层，专门负责：
- 根据配置创建模型客户端
- 拼接 prompt 和模型调用链
- 对外暴露统一的同步/流式聊天方法

路由层只需要“调用它”，不用理解 provider 的细节。
"""

from collections.abc import AsyncIterator
from functools import lru_cache

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.core.config import Settings, get_settings
from app.core.prompts import SYSTEM_PROMPT


class LangChainConfigurationError(RuntimeError):
    """LangChain 配置不完整时抛出的异常。"""


class LangChainService:
    """对 LangChain 调用做一层封装。"""

    def __init__(self, settings: Settings):
        # service 本身不保存会话状态，只是持有一份配置对象。
        self.settings = settings

    def _build_llm(self) -> ChatOpenAI:
        """根据当前配置创建模型客户端。

        这里虽然类名叫 `ChatOpenAI`，但并不代表只能连 OpenAI。
        只要第三方平台兼容 OpenAI 接口格式，也可以复用这个客户端，
        Ark 就是这种情况。
        """

        # 显式限制允许的 provider，避免 `.env` 写了奇怪值后排查半天。
        if self.settings.normalized_provider not in {"openai", "ark"}:
            raise LangChainConfigurationError(
                "Only the openai and ark providers are configured in this template."
            )

        # 提前检查 API Key，尽量在请求刚进来时就报清晰错误。
        if not self.settings.resolved_api_key:
            raise LangChainConfigurationError(
                "The selected provider API key is missing. Please configure it in the .env file."
            )

        # 这里组装的是底层模型客户端参数。
        # 前端可以把它理解成一次“SDK 初始化配置”。
        kwargs = {
            "model": self.settings.resolved_model,
            "temperature": self.settings.llm_temperature,
            "timeout": self.settings.llm_timeout,
            "max_retries": self.settings.llm_max_retries,
            "api_key": self.settings.resolved_api_key,
        }
        if self.settings.resolved_base_url:
            # 只有在自定义网关/兼容接口场景下才需要 base_url。
            kwargs["base_url"] = self.settings.resolved_base_url

        return ChatOpenAI(**kwargs)

    def _build_chain(self, system_prompt: str | None = None):
        """构建 LangChain 调用链。

        这一段是 LangChain 的核心写法：
        `prompt | llm | parser`

        可以把它理解成一个数据管道：
        1. `prompt` 负责把 system + user message 组装成模型输入
        2. `llm` 负责真正调用模型
        3. `parser` 负责把模型返回结果转成纯字符串
        """

        # 统一在这里组装 prompt，这样普通调用和流式调用走的是同一套提示词逻辑。
        prompt = ChatPromptTemplate.from_messages(
            [
                # system message 相当于给模型设定“角色”和“行为规则”。
                ("system", system_prompt or SYSTEM_PROMPT),
                # `"{user_input}"` 是占位符，真正调用时再把用户输入塞进去。
                ("human", "{user_input}"),
            ]
        )
        # `|` 是 LangChain Expression Language 的管道写法，不是 Python 位运算在业务里的常见用法。
        # 最终返回的是一条“可执行链”，后面可以 `.ainvoke()` 或 `.astream()`。
        return prompt | self._build_llm() | StrOutputParser()

    async def chat(self, user_message: str, system_prompt: str | None = None) -> str:
        """非流式聊天。

        `ainvoke` 会等待整条链执行完成，然后一次性拿到最终结果。
        使用体验上类似前端里的普通 `await fetch()`。
        """
        chain = self._build_chain(system_prompt=system_prompt)
        return await chain.ainvoke({"user_input": user_message})

    async def stream_chat(
        self, user_message: str, system_prompt: str | None = None
    ) -> AsyncIterator[str]:
        """流式聊天。

        `astream` 会不断产出增量结果，适合打字机效果或流式渲染。
        使用体验上类似消费一个异步文本流。
        """
        chain = self._build_chain(system_prompt=system_prompt)
        async for chunk in chain.astream({"user_input": user_message}):
            # 某些底层实现可能会给出空片段，这里顺手过滤一下。
            if chunk:
                yield chunk


@lru_cache
def get_langchain_service() -> LangChainService:
    # 用缓存复用同一个 service 实例。
    # 因为它本身没有请求级状态，所以没必要每次请求都 new 一个。
    return LangChainService(get_settings())
