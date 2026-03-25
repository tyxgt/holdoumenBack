# FastAPI LangChain Backend

这是一个基于 FastAPI 的 Python 后端模板，已经完成基础服务配置，并接入了 LangChain。当前项目已经支持两种模型接入方式：

- OpenAI
- 火山方舟 Ark（通过 OpenAI 兼容接口接入）

如果你是第一次接手这个项目，建议先看完这份 README，再开始改代码。

## 1. 新人先看哪些文件

下面这些文件是你最需要关注的：

- `app/main.py`
  - 项目启动入口。
  - 负责创建 FastAPI 应用、挂载中间件、注册总路由。
- `app/core/config.py`
  - 所有环境变量配置都在这里统一读取。
  - 如果后面要新增配置项，优先改这个文件。
- `app/api/router.py`
  - API 总路由汇总入口。
  - 新增业务路由时，最后要在这里注册。
- `app/api/routes/chat.py`
  - 对外提供聊天接口。
  - 负责接收请求、调用服务层、返回统一响应。
- `app/services/langchain_service.py`
  - LangChain 和模型接入的核心逻辑。
  - 如果你要换模型供应商、改提示词链路、加流式输出，优先从这里开始。
- `app/schemas/chat.py`
  - 请求和响应的数据结构定义。
  - 当前前后端接口字段就是以这里为准。
- `.env`
  - 本地运行时真实配置。
  - 这里通常放 API Key、模型名、服务地址。
- `.env.example`
  - 配置模板。
  - 新人第一次接手项目时，一般从它复制一份生成 `.env`。
- `tests/test_health.py`
  - 当前的基础烟雾测试。
  - 后续新增接口后，建议补充对应测试。

## 2. 项目目录说明

```text
.
├── app
│   ├── api
│   │   ├── router.py
│   │   └── routes
│   │       ├── chat.py
│   │       └── health.py
│   ├── core
│   │   ├── config.py
│   │   └── logging.py
│   ├── schemas
│   │   └── chat.py
│   ├── services
│   │   └── langchain_service.py
│   └── main.py
├── tests
│   └── test_health.py
├── .env
├── .env.example
├── pyproject.toml
└── README.md
```

目录职责可以简单理解为：

- `api/`
  - 负责 HTTP 接口定义。
- `schemas/`
  - 负责请求和响应结构。
- `services/`
  - 负责业务逻辑和三方服务调用。
- `core/`
  - 负责配置、日志等基础设施能力。
- `tests/`
  - 负责测试。

## 3. 项目运行规则

这些规则建议默认遵守：

- Python 版本
  - 当前开发环境已验证通过的是 Python 3.13。
- 虚拟环境
  - 默认使用项目根目录下的 `.venv`。
  - 不建议混用全局 Python 依赖。
- 配置来源
  - 所有运行配置统一从 `.env` 读取。
  - 不要把临时写死的 key、模型名、地址直接写进代码。
- 模型切换规则
  - `LLM_PROVIDER=openai` 时走 OpenAI 配置。
  - `LLM_PROVIDER=ark` 时优先走 `ARK_API_KEY / ARK_BASE_URL / ARK_MODEL`。
- API 前缀
  - 默认统一挂在 `/api/v1` 下。
  - 如果你改了 `API_PREFIX`，前端和文档也要一起改。
- CORS 配置
  - `CORS_ORIGINS` 目前支持逗号分隔写法。
  - 例如：`http://localhost:3000,http://127.0.0.1:3000`
- 密钥管理
  - `.env` 不提交到仓库。
  - `.env.example` 只保留模板，不放真实 key。
- 改完代码后的最低验证
  - 至少执行一次 `pytest`。
  - 如果你改了配置或启动逻辑，最好再手动跑一次服务。

## 4. 第一次运行怎么做

### 4.1 安装依赖

```bash
cd /Users/a58/tyx/llm/holdoumenBack
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

如果 `.venv` 已存在，只需要：

```bash
cd /Users/a58/tyx/llm/holdoumenBack
source .venv/bin/activate
```

### 4.2 准备配置文件

首次接手项目时：

```bash
cp .env.example .env
```

当前项目已经配置为使用火山方舟，关键配置如下：

```env
LLM_PROVIDER=ark
ARK_API_KEY=your_ark_api_key
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
ARK_MODEL=your_endpoint_id
```

如果你想切回 OpenAI：

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key
OPENAI_BASE_URL=
LLM_MODEL=gpt-4o-mini
```

### 4.3 启动服务

```bash
source .venv/bin/activate
uvicorn app.main:app --reload
```

启动后默认访问地址：

- 根路径：`http://127.0.0.1:8000/`
- Swagger 文档：`http://127.0.0.1:8000/docs`
- 健康检查：`http://127.0.0.1:8000/api/v1/health`
- 聊天接口：`POST http://127.0.0.1:8000/api/v1/chat`

## 5. 怎么使用这个项目

### 5.1 查看服务是否正常

```bash
curl http://127.0.0.1:8000/api/v1/health
```

正常情况下会返回类似：

```json
{
  "status": "ok",
  "environment": "development",
  "llm_provider": "ark",
  "llm_configured": true
}
```

### 5.2 调用聊天接口

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "请介绍一下 FastAPI",
    "system_prompt": "你是一个专业的 Python 后端助手。"
  }'
```

正常情况下会返回类似：

```json
{
  "answer": "FastAPI 是一个高性能的 Python Web 框架。",
  "model": "ep-xxxx",
  "provider": "ark"
}
```

### 5.3 调用流式聊天（SSE）

在请求体中加上 `stream: true`，接口会返回 `text/event-stream`，并持续推送事件：

- `event: meta`：本次请求的模型和 provider 信息
- `event: delta`：增量文本片段
- `event: done`：流结束标记

```bash
curl -N -X POST "http://127.0.0.1:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "message": "请用三句话介绍 FastAPI",
    "stream": true
  }'
```

## 6. 如果我要继续开发，应该改哪里

常见需求和对应入口如下：

- 新增接口
  - 在 `app/api/routes/` 下新增路由文件。
  - 然后去 `app/api/router.py` 注册。
- 新增请求/响应字段
  - 修改 `app/schemas/` 里的 Pydantic 模型。
- 新增业务逻辑
  - 优先放到 `app/services/`。
  - 路由层尽量只做参数接收和错误转换。
- 新增配置项
  - 修改 `app/core/config.py`。
  - 再把示例值补到 `.env.example`。
- 更换模型供应商
  - 优先修改 `app/services/langchain_service.py` 和 `app/core/config.py`。
- 开启链路追踪
  - 使用 `LANGSMITH_TRACING / LANGSMITH_API_KEY / LANGSMITH_PROJECT`。

## 7. 常见注意事项

- `CORS_ORIGINS` 不是 JSON 数组，当前项目支持直接写逗号分隔字符串。
- 火山方舟这里走的是 OpenAI 兼容接口，所以代码里仍然使用 `ChatOpenAI`，这是正常的。
- 如果聊天接口报 500，优先检查 `.env` 中的 provider、api key、model 是否配对。
- 如果聊天接口报 502，通常是上游模型调用失败，先检查 key、额度、endpoint、网络。
- `.env` 里有真实密钥时，不要提交到 git。

## 8. 测试和校验

运行测试：

```bash
pytest
```

当前最基础的验证标准：

- 服务可以正常启动。
- `/api/v1/health` 能返回 200。
- 聊天接口能正确读取当前 provider 配置。

## 9. 建议的开发顺序

如果你是第一次接这个项目，建议按下面顺序理解：

1. 先看 `README.md`
2. 再看 `app/main.py`
3. 再看 `app/core/config.py`
4. 再看 `app/api/routes/chat.py`
5. 最后看 `app/services/langchain_service.py`

按这个顺序看，基本就能把“配置怎么进来、请求怎么进来、模型怎么被调用、结果怎么返回”串起来。
