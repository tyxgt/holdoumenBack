# 登录功能前端对接文档

## 概述

后端已实现登录功能，支持**登录即注册**模式。前端需要对接以下接口实现用户认证流程。

## API 接口

### 1. 登录接口

**POST** `/api/v1/auth/login`

登录接口，未注册用户会自动注册。

#### 请求体

```json
{
  "username": "string",
  "password": "string"
}
```

#### 密码规则

密码必须满足以下所有条件：
- 至少 8 位字符
- 包含至少 1 个小写字母 (a-z)
- 包含至少 1 个大写字母 (A-Z)
- 包含至少 1 个数字 (0-9)
- 包含至少 1 个特殊字符 (!@#$%^&*(),.?":{}|<>)

#### 成功响应 (200)

```json
{
  "message": "登录成功",
  "user": {
    "id": 1,
    "username": "testuser",
    "created_at": "2024-01-01T00:00:00"
  },
  "is_new_user": false
}
```

#### 响应字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| message | string | "登录成功" 或 "注册成功" |
| user.id | number | 用户ID |
| user.username | string | 用户名 |
| user.created_at | string | 账号创建时间 (ISO 8601) |
| is_new_user | boolean | 是否为新注册用户 |

#### 错误响应

| 状态码 | 说明 |
|--------|------|
| 400 | 密码不符合规则 |
| 401 | 密码错误（已注册用户） |

#### Cookie

成功登录后，服务器会自动设置 HttpOnly Cookie：
- 名称：`access_token`
- 有效期：7天
- 属性：HttpOnly, Secure, SameSite=Lax

---

### 2. 退出登录

**POST** `/api/v1/auth/logout`

清除登录状态，删除 Cookie。

#### 响应 (200)

```json
{
  "message": "已退出登录"
}
```

---

### 3. 获取当前用户信息

**GET** `/api/v1/auth/me`

获取当前登录用户的信息。

#### 响应 (200)

```json
{
  "id": 1,
  "username": "testuser",
  "created_at": "2024-01-01T00:00:00"
}
```

#### 错误响应

| 状态码 | 说明 |
|--------|------|
| 401 | 未登录或 Token 已过期 |

---

## 前端实现指南

### 登录流程

```javascript
// 1. 用户填写用户名和密码
const loginData = {
  username: "TestUser",
  password: "Abc123!@#"
};

// 2. 调用登录接口
const response = await fetch('/api/v1/auth/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify(loginData),
  credentials: 'include'  // 重要：允许携带 Cookie
});

const result = await response.json();

// 3. 根据 is_new_user 显示不同提示
if (result.is_new_user) {
  // 新用户注册成功
  showMessage('注册成功！欢迎加入');
} else {
  // 老用户登录成功
  showMessage('登录成功！');
}

// 4. 跳转到主页
navigateToHome();
```

### 检查登录状态

```javascript
async function checkAuth() {
  try {
    const response = await fetch('/api/v1/auth/me', {
      credentials: 'include'
    });
    
    if (response.ok) {
      const user = await response.json();
      return { isLoggedIn: true, user };
    }
  } catch (error) {
    console.error('Auth check failed:', error);
  }
  
  return { isLoggedIn: false, user: null };
}
```

### 退出登录

```javascript
async function logout() {
  await fetch('/api/v1/auth/logout', {
    method: 'POST',
    credentials: 'include'
  });
  
  // 跳转到登录页
  navigateToLogin();
}
```

### 密码验证（前端预校验）

```javascript
function validatePassword(password) {
  const errors = [];
  
  if (password.length < 8) {
    errors.push('密码至少8位');
  }
  if (!/[a-z]/.test(password)) {
    errors.push('密码必须包含小写字母');
  }
  if (!/[A-Z]/.test(password)) {
    errors.push('密码必须包含大写字母');
  }
  if (!/\d/.test(password)) {
    errors.push('密码必须包含数字');
  }
  if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
    errors.push('密码必须包含特殊字符');
  }
  
  return errors;
}

// 使用示例
const errors = validatePassword(userInput);
if (errors.length > 0) {
  showError(errors.join('，'));
}
```

---

## 重要注意事项

### 1. Cookie 配置

所有请求必须设置 `credentials: 'include'`，否则 Cookie 不会被携带：

```javascript
fetch('/api/v1/auth/me', {
  credentials: 'include'  // 必须设置
});
```

### 2. CORS 配置

后端已配置 CORS 支持 credentials，前端需要确保：
- 不能使用 `*` 作为 origin
- 必须使用完整的域名（包括协议和端口）

### 3. 登录状态判断

- 通过调用 `/api/v1/auth/me` 判断是否登录
- 返回 401 表示未登录或 Token 过期
- 返回 200 表示已登录，可获取用户信息

### 4. 受保护接口

对于需要登录才能访问的接口：
- 前端无需额外处理 Token
- Cookie 会自动携带
- 后端返回 401 时，前端跳转到登录页

---

## 错误处理示例

```javascript
async function handleLogin(username, password) {
  try {
    const response = await fetch('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
      credentials: 'include'
    });

    if (!response.ok) {
      const error = await response.json();
      
      if (response.status === 400) {
        // 密码规则错误
        showError('密码不符合规则：' + error.detail);
      } else if (response.status === 401) {
        // 密码错误
        showError('用户名或密码错误');
      } else {
        showError('登录失败，请稍后重试');
      }
      return false;
    }

    const result = await response.json();
    
    if (result.is_new_user) {
      showSuccess('注册成功！欢迎加入');
    } else {
      showSuccess('登录成功！');
    }
    
    return true;
  } catch (error) {
    showError('网络错误，请检查网络连接');
    return false;
  }
}
```

---

## 测试账号

开发环境可以使用以下测试账号：

| 用户名 | 密码 | 说明 |
|--------|------|------|
| TestUser | Abc123!@# | 测试账号 |

或直接使用新用户名登录，系统会自动注册。

---

## 更新日志

- **2024-01-01**: 初始版本，支持登录即注册功能
