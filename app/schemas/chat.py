"""聊天接口的数据模型定义。

该文件使用 Pydantic 对请求和响应做结构校验，确保前后端字段约定稳定。
你可以把它理解成：
- 有运行时校验能力的 TypeScript interface
- 同时也是 Swagger 文档的字段来源
"""

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    """聊天请求体模型。

    用于接收用户输入消息，以及要扮演的角色。
    """

    model_config = ConfigDict(populate_by_name=True)

    message: str = Field(
        ...,
        min_length=1,
        validation_alias=AliasChoices("message", "content"),
        description="用户输入消息。",
    )
    character: str = Field(
        ...,
        min_length=1,
        description="要扮演的角色名称（必填），如：蒋敦豪、鹭卓、李耕耘等。",
    )
    stream: bool = Field(
        default=False,
        description="是否启用流式响应（SSE）。",
    )


class ChatResponse(BaseModel):
    """聊天响应体模型。

    返回模型生成结果，以及本次调用的模型与提供方信息。
    """

    answer: str
    model: str
    provider: str
