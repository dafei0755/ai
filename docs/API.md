# 📡 API 文档

> Intelligent Project Analyzer RESTful API 参考文档

---

## 📑 目录

- [概述](#概述)
- [认证](#认证)
- [端点列表](#端点列表)
  - [会话管理](#会话管理)
  - [分析接口](#分析接口)
  - [交互接口](#交互接口)
  - [报告导出](#报告导出)
- [WebSocket 接口](#websocket-接口)
- [错误处理](#错误处理)
- [示例代码](#示例代码)

---

## 🌐 概述

### Base URL

```
开发环境: http://localhost:8001
生产环境: https://ai.ucppt.com
```

### API 版本

当前主版本仍保留 `v1`，方案高参对话入口使用 `v2`。

所有 API 端点前缀: `/api/v1`

方案高参对话端点前缀：

```text
/api/v2
```

### 响应格式

所有响应均为 JSON 格式：

```json
{
  "success": true,
  "data": { ... },
  "message": "操作成功",
  "timestamp": "2025-12-30T12:00:00Z"
}
```

错误响应：

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述",
    "details": { ... }
  },
  "timestamp": "2025-12-30T12:00:00Z"
}
```

---

## 🔐 认证

### API Key 认证

在请求头中添加：

```http
Authorization: Bearer YOUR_API_KEY
```

### WordPress SSO（可选）

支持 WordPress 单点登录：

```http
Cookie: wordpress_logged_in_xxx=...
```

---

## 📋 端点列表

### 方案高参对话入口

#### 0. 发送对话消息

```http
POST /api/v2/conversation/message
```

该端点负责在同一入口中分流：

- 需求重构：模糊输入先生成行动蓝图；
- 正式任务书入口：明确任务书意向后进入一二轮追问；
- 项目模式：已进入项目后的继续对话。

**请求体：**

```json
{
  "session_id": "conv-optional",
  "message": "50岁男性室内设计师，背井离乡，想在老家建一栋民居，给出建议",
  "in_response_to_card_id": null,
  "selected_option_id": null,
  "card_response": null
}
```

**需求重构响应关键字段：**

```json
{
  "intent": "demand_reconstruction_blueprint",
  "dialogue_layer": "demand_reconstruction",
  "handoff_available": true,
  "reconstruction_type": "demand_reconstruction",
  "artifact_name": "action_blueprint",
  "guidance_card": {
    "card_type": "demand_reconstruction_blueprint",
    "title": "需求重构",
    "artifact_name": "行动蓝图"
  },
  "demand_reconstruction_context": {
    "schema_version": "demand_reconstruction_context.v1",
    "blueprint": {
      "insight_source": "llm",
      "task_reframe": "...",
      "primary_risk": "...",
      "brief_handoff_slots": {}
    }
  }
}
```

`blueprint.insight_source` 用于排障与观测：

| 值 | 含义 |
|---|---|
| `llm` | 需求重构使用受控 LLM 洞察层增强表达 |
| `rule` | 未启用 LLM，直接使用规则蓝图 |
| `rule_fallback` | LLM 不可用、低质或越界，已回退到规则蓝图 |

**正式任务书响应关键字段：**

```json
{
  "intent": "scheme_advisor_entry",
  "dialogue_layer": "brief_intake",
  "handoff_available": false,
  "guidance_card": {
    "card_type": "scheme_round_1"
  }
}
```

`dialogue_layer` 取值：

| 值 | 含义 |
|---|---|
| `demand_reconstruction` | 需求重构阶段，前台展示行动蓝图 |
| `brief_intake` | 正式设计任务书一二轮追问 |
| `project` | 已进入项目后的持续对话 |

需求重构 handoff 到正式任务书时，前端提交：

```json
{
  "selected_option_id": "handoff_to_brief",
  "in_response_to_card_id": "demand_reconstruction-xxxx"
}
```

### 会话管理

#### 1. 创建分析会话

创建新的项目分析会话。

```http
POST /api/v1/sessions
```

**请求体：**

```json
{
  "user_input": "我想设计一个现代咖啡馆，面积120平米",
  "user_id": "user_123",
  "skip_questionnaire": false,
  "metadata": {
    "source": "web",
    "language": "zh-CN"
  }
}
```

**参数说明：**

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `user_input` | string | 是 | 用户需求描述 |
| `user_id` | string | 否 | 用户ID（SSO登录时自动填充） |
| `skip_questionnaire` | boolean | 否 | 是否跳过校准问卷（默认false） |
| `metadata` | object | 否 | 附加元数据 |

**响应示例：**

```json
{
  "success": true,
  "data": {
    "session_id": "session-20251230-abc123",
    "status": "pending_questionnaire",
    "created_at": "2025-12-30T12:00:00Z",
    "questionnaire": {
      "questions": [
        {
          "id": "q1",
          "text": "您的目标客户群体是？",
          "type": "text",
          "options": null
        }
      ]
    }
  }
}
```

**HTTP 状态码：**
- `201`: 创建成功
- `400`: 请求参数错误
- `401`: 未授权
- `500`: 服务器错误

---

#### 2. 获取会话详情

获取指定会话的详细信息。

```http
GET /api/v1/sessions/{session_id}
```

**路径参数：**

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `session_id` | string | 是 | 会话ID |

**查询参数：**

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `include_report` | boolean | 否 | 是否包含完整报告（默认false） |

**响应示例：**

```json
{
  "success": true,
  "data": {
    "session_id": "session-20251230-abc123",
    "user_id": "user_123",
    "status": "completed",
    "user_input": "设计一个现代咖啡馆",
    "created_at": "2025-12-30T12:00:00Z",
    "updated_at": "2025-12-30T12:05:00Z",
    "progress": {
      "current_stage": "completed",
      "completion_percentage": 100,
      "stages": [
        {
          "name": "需求分析",
          "status": "completed",
          "duration": 30
        },
        {
          "name": "专家协作",
          "status": "completed",
          "duration": 120
        }
      ]
    },
    "analysis_result": {
      "summary": "项目可行性良好...",
      "expert_reports": [ ... ]
    }
  }
}
```

**HTTP 状态码：**
- `200`: 成功
- `404`: 会话不存在
- `403`: 无权访问

---

#### 3. 列出用户会话

获取用户的所有会话列表。

```http
GET /api/v1/sessions
```

**查询参数：**

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `user_id` | string | 否 | 用户ID（默认当前用户） |
| `status` | string | 否 | 会话状态（`active`, `completed`, `failed`） |
| `page` | integer | 否 | 页码（默认1） |
| `page_size` | integer | 否 | 每页数量（默认20） |
| `sort_by` | string | 否 | 排序字段（默认`created_at`） |
| `order` | string | 否 | 排序方向（`asc`, `desc`，默认`desc`） |

**响应示例：**

```json
{
  "success": true,
  "data": {
    "sessions": [
      {
        "session_id": "session-001",
        "user_input": "设计咖啡馆",
        "status": "completed",
        "created_at": "2025-12-30T10:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 45,
      "total_pages": 3
    }
  }
}
```

---

#### 4. 删除会话

删除指定会话及其所有数据。

```http
DELETE /api/v1/sessions/{session_id}
```

**响应示例：**

```json
{
  "success": true,
  "message": "会话已删除"
}
```

**HTTP 状态码：**
- `200`: 删除成功
- `404`: 会话不存在
- `403`: 无权删除

---

### 分析接口

#### 5. 开始分析

启动会话的分析流程。

```http
POST /api/v1/sessions/{session_id}/analyze
```

**请求体：**

```json
{
  "questionnaire_answers": {
    "q1": "年轻白领",
    "q2": "20-35岁"
  },
  "confirmed_requirements": true,
  "options": {
    "max_experts": 8,
    "enable_quality_review": true
  }
}
```

**参数说明：**

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `questionnaire_answers` | object | 否 | 问卷回答 |
| `confirmed_requirements` | boolean | 是 | 是否确认需求 |
| `options` | object | 否 | 分析选项 |

**响应示例：**

```json
{
  "success": true,
  "data": {
    "session_id": "session-001",
    "analysis_id": "analysis-001",
    "status": "in_progress",
    "estimated_completion_time": 180
  }
}
```

---

#### 6. 获取分析进度

实时获取分析进度。

```http
GET /api/v1/sessions/{session_id}/progress
```

**响应示例：**

```json
{
  "success": true,
  "data": {
    "status": "in_progress",
    "current_stage": "expert_collaboration",
    "completion_percentage": 65,
    "active_agents": [
      {
        "agent_id": "V2_design_director",
        "status": "running",
        "progress": 80
      }
    ],
    "completed_agents": ["requirements_analyst", "project_director"],
    "estimated_time_remaining": 60
  }
}
```

---

### 交互接口

#### 7. 提交问卷回答

提交校准问卷的回答。

```http
POST /api/v1/sessions/{session_id}/questionnaire
```

**请求体：**

```json
{
  "answers": {
    "q1": "年轻白领",
    "q2": "现代简约",
    "q3": "50-100万"
  }
}
```

**响应示例：**

```json
{
  "success": true,
  "data": {
    "next_step": "requirements_confirmation",
    "structured_requirements": {
      "target_audience": "年轻白领",
      "style": "现代简约",
      "budget_range": "50-100万"
    }
  }
}
```

---

#### 8. 确认需求

确认系统理解的需求是否正确。

```http
POST /api/v1/sessions/{session_id}/confirm-requirements
```

**请求体：**

```json
{
  "confirmed": true,
  "modifications": {
    "budget_range": "60-120万"
  }
}
```

**响应示例：**

```json
{
  "success": true,
  "data": {
    "next_step": "analysis",
    "updated_requirements": { ... }
  }
}
```

---

#### 9. 审批任务分配

审批专家任务分配方案。

```http
POST /api/v1/sessions/{session_id}/approve-tasks
```

**请求体：**

```json
{
  "approved": true,
  "modifications": [
    {
      "expert_id": "V3_narrative_expert",
      "action": "remove",
      "reason": "不需要"
    }
  ]
}
```

---

### 报告导出

#### 10. 导出报告

导出分析报告为指定格式。

```http
POST /api/v1/sessions/{session_id}/export
```

**请求体：**

```json
{
  "format": "pdf",
  "options": {
    "include_charts": true,
    "language": "zh-CN"
  }
}
```

**参数说明：**

| 参数 | 类型 | 可选值 | 说明 |
|------|------|--------|------|
| `format` | string | `pdf`, `markdown`, `json`, `docx` | 导出格式 |
| `options.include_charts` | boolean | - | 是否包含图表 |
| `options.language` | string | `zh-CN`, `en-US` | 报告语言 |

**响应示例：**

```json
{
  "success": true,
  "data": {
    "download_url": "/downloads/report-001.pdf",
    "expires_at": "2025-12-31T12:00:00Z",
    "file_size": 2048576
  }
}
```

---

## 🔌 WebSocket 接口

### 实时进度推送

连接 WebSocket 接收实时进度更新。

```javascript
const ws = new WebSocket('ws://localhost:8001/ws/sessions/{session_id}');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Progress update:', data);
};
```

**消息格式：**

```json
{
  "type": "progress_update",
  "data": {
    "session_id": "session-001",
    "stage": "expert_collaboration",
    "completion_percentage": 75,
    "message": "专家协作进行中..."
  },
  "timestamp": "2025-12-30T12:05:30Z"
}
```

**消息类型：**

| 类型 | 说明 |
|------|------|
| `progress_update` | 进度更新 |
| `stage_completed` | 阶段完成 |
| `error` | 错误通知 |
| `analysis_completed` | 分析完成 |

---

## ⚠️ 错误处理

### 错误码

| 错误码 | HTTP 状态 | 说明 |
|--------|-----------|------|
| `INVALID_INPUT` | 400 | 请求参数无效 |
| `UNAUTHORIZED` | 401 | 未授权访问 |
| `FORBIDDEN` | 403 | 无权限访问 |
| `NOT_FOUND` | 404 | 资源不存在 |
| `RATE_LIMIT_EXCEEDED` | 429 | 请求频率超限 |
| `INTERNAL_ERROR` | 500 | 服务器内部错误 |
| `LLM_ERROR` | 500 | LLM 服务错误 |
| `TIMEOUT` | 504 | 请求超时 |

### 错误响应示例

```json
{
  "success": false,
  "error": {
    "code": "INVALID_INPUT",
    "message": "用户输入不能为空",
    "details": {
      "field": "user_input",
      "constraint": "min_length: 10"
    }
  },
  "timestamp": "2025-12-30T12:00:00Z"
}
```

---

## 📝 示例代码

### Python 示例

```python
import requests

# 创建会话
response = requests.post(
    "http://localhost:8001/api/v1/sessions",
    json={
        "user_input": "设计一个现代咖啡馆，面积120平米",
        "user_id": "user_001"
    }
)

session_data = response.json()['data']
session_id = session_data['session_id']

# 提交问卷回答
requests.post(
    f"http://localhost:8001/api/v1/sessions/{session_id}/questionnaire",
    json={
        "answers": {
            "q1": "年轻白领",
            "q2": "现代简约"
        }
    }
)

# 开始分析
requests.post(
    f"http://localhost:8001/api/v1/sessions/{session_id}/analyze",
    json={"confirmed_requirements": True}
)

# 轮询进度
import time
while True:
    progress = requests.get(
        f"http://localhost:8001/api/v1/sessions/{session_id}/progress"
    ).json()['data']
    
    print(f"进度: {progress['completion_percentage']}%")
    
    if progress['status'] == 'completed':
        break
    
    time.sleep(5)

# 获取结果
result = requests.get(
    f"http://localhost:8001/api/v1/sessions/{session_id}",
    params={"include_report": True}
).json()

print("分析完成！")
```

### JavaScript 示例

```javascript
// 使用 Fetch API
async function createAnalysis() {
  // 创建会话
  const createResponse = await fetch('http://localhost:8001/api/v1/sessions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      user_input: '设计一个现代咖啡馆',
      user_id: 'user_001'
    })
  });

  const { data } = await createResponse.json();
  const sessionId = data.session_id;

  // WebSocket 监听进度
  const ws = new WebSocket(`ws://localhost:8001/ws/sessions/${sessionId}`);
  
  ws.onmessage = (event) => {
    const update = JSON.parse(event.data);
    console.log('Progress:', update.data.completion_percentage + '%');
    
    if (update.type === 'analysis_completed') {
      console.log('分析完成！');
      ws.close();
    }
  };

  // 开始分析
  await fetch(`http://localhost:8001/api/v1/sessions/${sessionId}/analyze`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      confirmed_requirements: true
    })
  });
}

createAnalysis();
```

### cURL 示例

```bash
# 创建会话
curl -X POST http://localhost:8001/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "设计一个现代咖啡馆",
    "user_id": "user_001"
  }'

# 获取会话详情
curl -X GET http://localhost:8001/api/v1/sessions/session-001

# 导出报告
curl -X POST http://localhost:8001/api/v1/sessions/session-001/export \
  -H "Content-Type: application/json" \
  -d '{"format": "pdf"}' \
  -o report.pdf
```

---

## 📊 速率限制

| 端点类型 | 限制 |
|---------|------|
| 创建会话 | 10次/分钟 |
| 查询接口 | 100次/分钟 |
| WebSocket | 5个并发连接/用户 |

超出限制将返回 `429 Too Many Requests`。

---

## 🔄 API 版本说明

- **v1** (当前)：稳定版本，向后兼容
- **v2** (计划中)：增强功能，预计 2025 Q2 发布

---

## 📞 技术支持

- API 文档：http://localhost:8001/docs
- 问题反馈：[GitHub Issues](https://github.com/dafei0755/ai/issues)
- 讨论区：[GitHub Discussions](https://github.com/dafei0755/ai/discussions)

---

**最后更新**: 2025-12-30  
**API 版本**: v1.0.0  
**文档版本**: 1.0.0
