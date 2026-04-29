# 聊天接口 API 变更文档

## 变更概述

聊天接口 `/api/v1/chat` 进行了重大调整，简化了角色处理逻辑：

- **移除**：`system_prompt` 字段（前端不再需要传入完整的系统提示词）
- **新增**：`character` 必填字段（只需传入角色名称）

AI 会根据传入的角色名自动生成对应的角色 prompt，不再需要前端维护角色信息。

---

## 接口详情

### 请求地址

```
POST /api/v1/chat
```

### 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `message` | string | ✅ | 用户输入消息，最小长度 1 |
| `character` | string | ✅ | 要扮演的角色名称 |
| `stream` | boolean | ❌ | 是否启用流式响应（SSE），默认 `false` |

### 可用角色列表

| 角色名 | 昵称 | 特点 |
|--------|------|------|
| 蒋敦豪 | 董事长 | 稳重大哥，擅长经营 |
| 鹭卓 | 玫瑰王子 | 自信幽默，有点自恋 |
| 李耕耘 | 孤狼 | 内敛实干，基建达人 |
| 李昊 | 空虚公子 | 话多幽默，语言艺术家 |
| 赵一博 | 啾咪 | 耿直技术流，种麦专家 |
| 卓沅 | 摄政王 | 活泼话多，气氛担当 |
| 赵小童 | 小王子 | 阳光力王，有点孩子气 |
| 何浩楠 | 车神 | 搞怪随性，后陡门车神 |
| 陈少熙 | 少塘主 | 佛系淡然，人生哲学家 |
| 王一珩 | 壮壮妈 | 可爱活泼，弟弟担当 |

---

## 新旧格式对比

### 旧格式（已废弃）

```json
{
  "message": "你好，介绍一下你自己",
  "system_prompt": "你是十个勤天的互动助手...",
  "stream": false
}
```

### 新格式

```json
{
  "message": "你好，介绍一下你自己",
  "character": "蒋敦豪",
  "stream": false
}
```

---

## 响应格式

### 非流式响应（stream: false）

```json
{
  "answer": "大家好，我是蒋敦豪，这个事情我来安排...",
  "model": "gpt-4o-mini",
  "provider": "openai"
}
```

### 流式响应（stream: true）

返回 SSE (Server-Sent Events) 格式：

```
event: meta
data: {"model":"gpt-4o-mini","provider":"openai"}

event: delta
data: {"delta":"大家"}

event: delta
data: {"delta":"好"}

event: done
data: [DONE]
```

---

## 错误处理

### 缺少 character 字段

**请求：**
```json
{
  "message": "你好",
  "stream": false
}
```

**响应：** HTTP 422 Unprocessable Entity
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "character"],
      "msg": "Field required",
      "input": {"message": "你好", "stream": false}
    }
  ]
}
```

### 无效的角色名

**请求：**
```json
{
  "message": "你好",
  "character": "张三",
  "stream": false
}
```

**响应：** HTTP 400 Bad Request
```json
{
  "detail": "无效的角色名: 张三。可用角色: 蒋敦豪, 鹭卓, 李耕耘, 李昊, 赵一博, 卓沅, 赵小童, 何浩楠, 陈少熙, 王一珩"
}
```

---

## 前端改造要点

### 1. 移除 system_prompt 相关逻辑

- 删除前端存储/生成 system_prompt 的代码
- 删除角色选择后拼接 prompt 的逻辑

### 2. 新增 character 字段

- 在聊天请求中添加必填的 `character` 字段
- 用户选择角色后，直接传递角色名称（如 `"蒋敦豪"`）

### 3. 角色选择 UI

- 可在后端获取可用角色列表，或前端硬编码上述 10 个角色
- 建议前端维护角色选择状态，每次聊天请求携带当前选中的角色名

### 4. 错误处理

- 处理 422 错误（缺少 character）
- 处理 400 错误（无效角色名），可提示用户重新选择角色

---

## 示例代码

### TypeScript 接口定义

```typescript
interface ChatRequest {
  message: string;
  character: string;
  stream?: boolean;
}

interface ChatResponse {
  answer: string;
  model: string;
  provider: string;
}

const VALID_CHARACTERS = [
  '蒋敦豪', '鹭卓', '李耕耘', '李昊', '赵一博',
  '卓沅', '赵小童', '何浩楠', '陈少熙', '王一珩'
] as const;

type CharacterName = typeof VALID_CHARACTERS[number];
```

### 发送聊天请求

```typescript
async function sendMessage(message: string, character: CharacterName): Promise<string> {
  const response = await fetch('/api/v1/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      character,
      stream: false,
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || '请求失败');
  }

  const data: ChatResponse = await response.json();
  return data.answer;
}
```

### 流式请求示例

```typescript
async function streamChat(
  message: string,
  character: CharacterName,
  onDelta: (text: string) => void
): Promise<void> {
  const response = await fetch('/api/v1/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, character, stream: true }),
  });

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();

  if (!reader) return;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6);
        if (data === '[DONE]') return;

        try {
          const parsed = JSON.parse(data);
          if (parsed.delta) {
            onDelta(parsed.delta);
          }
        } catch {
          // 忽略解析错误
        }
      }
    }
  }
}
```

---

## 变更时间

- **生效日期**：即日起
- **旧接口兼容**：不兼容，需同步更新前端代码

如有疑问，请联系后端开发团队。
