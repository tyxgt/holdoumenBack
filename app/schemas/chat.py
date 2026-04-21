"""聊天接口的数据模型定义。

该文件使用 Pydantic 对请求和响应做结构校验，确保前后端字段约定稳定。
你可以把它理解成：
- 有运行时校验能力的 TypeScript interface
- 同时也是 Swagger 文档的字段来源
"""

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from app.core.prompts import SYSTEM_PROMPT


class ChatRequest(BaseModel):
    """聊天请求体模型。

    用于接收用户输入消息，以及可选的系统提示词。
    """

    # 允许通过字段名填充，配合 `validation_alias` 做新旧字段兼容。
    model_config = ConfigDict(populate_by_name=True)

    # 兼容两种请求字段：
    # 1. 新字段 `message`
    # 2. 旧字段 `content`（前端历史写法）
    message: str = Field(
        ...,
        min_length=1,
        validation_alias=AliasChoices("message", "content"),
        description="用户输入消息。",
    )
    # 系统提示词，可选；不传时会使用 `app/core/prompts.py` 里的默认提示词。
    # 它的作用类似“给模型设定全局角色和回复规则”。
    system_prompt: str | None = Field(
        default=SYSTEM_PROMPT,
        description="可选系统提示词。",
    )
    # 是否启用流式返回；开启后接口会以 SSE 方式逐段返回模型输出。
    stream: bool = Field(
        default=False,
        description="是否启用流式响应（SSE）。",
    )


class ChatResponse(BaseModel):
    """聊天响应体模型。

    返回模型生成结果，以及本次调用的模型与提供方信息。
    """

    # 模型最终回复的纯文本内容。
    answer: str
    # 本次实际使用的模型标识，例如 `gpt-4o-mini` 或某个 Ark endpoint id。
    model: str
    # 模型提供方（如 openai / ark）。
    provider: str
