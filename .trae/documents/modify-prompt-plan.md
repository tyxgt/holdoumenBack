# 修改Prompt计划 - 简化角色处理

## 概述

修改当前prompt机制，不再在prompt中介绍十个人的角色，而是根据请求中传入的角色名，动态生成该角色的system prompt。

## 当前状态分析

### 现有实现
- `app/core/prompts.py`: 定义了包含十人角色介绍的 `SYSTEM_PROMPT`
- `app/schemas/chat.py`: `ChatRequest` 中 `system_prompt` 默认使用 `SYSTEM_PROMPT`
- `app/services/langchain_service.py`: 使用传入的 `system_prompt` 构建LLM调用链

### 问题
- prompt冗长，包含十人角色介绍，但用户只需要与一个角色对话
- 角色选择流程复杂，需要AI引导用户选择

## 修改方案

### 1. 创建角色数据模块

**文件**: `app/core/characters.py` (新建)

定义十位角色的详细信息：
```python
CHARACTERS = {
    "蒋敦豪": {
        "nickname": "董事长",
        "traits": "稳重大哥，擅长经营",
        "style": "...",
        "catchphrases": ["..."],
    },
    # ... 其他角色
}
```

### 2. 修改请求Schema

**文件**: `app/schemas/chat.py`

- 新增必填字段 `character: str`
- 移除 `system_prompt` 字段（或改为可选，用于覆盖）

### 3. 修改Prompt生成逻辑

**文件**: `app/core/prompts.py`

- 创建函数 `build_character_prompt(character_name: str) -> str`
- 根据角色名动态生成包含该角色信息的system prompt
- prompt格式简化为：角色定义 + 对话风格要求

### 4. 修改服务层

**文件**: `app/services/langchain_service.py`

- `chat()` 和 `stream_chat()` 方法接收 `character` 参数
- 调用 `build_character_prompt()` 生成prompt

### 5. 修改API路由

**文件**: `app/api/routes/chat.py`

- 从请求中获取 `character` 字段
- 验证角色名是否有效
- 传递给服务层

## 具体文件变更

| 文件 | 操作 | 说明 |
|------|------|------|
| `app/core/characters.py` | 新建 | 角色数据定义 |
| `app/core/prompts.py` | 修改 | 添加 `build_character_prompt()` 函数 |
| `app/schemas/chat.py` | 修改 | 添加 `character` 必填字段 |
| `app/services/langchain_service.py` | 修改 | 接收 `character` 参数 |
| `app/api/routes/chat.py` | 修改 | 验证角色名，传递参数 |

## 验证步骤

1. 启动服务，测试不传 `character` 字段应返回校验错误
2. 测试传入无效角色名应返回错误
3. 测试传入有效角色名，验证AI以该角色身份回答
4. 测试流式响应是否正常工作
