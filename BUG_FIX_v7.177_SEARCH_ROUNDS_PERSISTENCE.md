# v7.177 Bug Fix: 搜索页面多轮搜索数据持久化

## 问题描述

用户反馈 `/search/` 页面的多轮搜索功能"未生效"。

**会话示例**: `guest-20260109-12eb9662`

## 问题分析

### 1. 后端多轮搜索正常工作

测试确认 `DeepSearchEngine.search_deep()` 正常执行 5 轮搜索：
- ✅ `search_round_start` 和 `search_round_complete` 事件正确发送
- ✅ 每轮搜索找到 12-14 个来源
- ✅ 最终去重后得到 19+ 个来源

### 2. 数据未持久化到数据库

检查用户会话发现关键问题：
```
isDeepMode: N/A
totalRounds: 0
rounds count: 0
Sources count: 38  ← 有来源但没有轮次数据
```

### 3. 根本原因

`ArchivedSearchSession` 数据库模型缺少以下字段：
- `is_deep_mode` - 是否深度搜索模式
- `thinking_content` - 深度思考内容
- `answer_content` - AI 回答内容
- `search_plan` - 搜索规划 JSON
- `rounds` - 搜索轮次记录 JSON
- `total_rounds` - 总轮数

`archive_search_session()` 和 `get_search_session()` 方法也未处理这些字段。

## 修复方案

### 修改文件

1. **`intelligent_project_analyzer/services/session_archive_manager.py`**
   - 更新 `ArchivedSearchSession` 模型，添加 6 个新字段
   - 更新 `archive_search_session()` 方法，保存新字段
   - 更新 `get_search_session()` 方法，返回新字段

2. **数据库迁移**: `migrate_search_sessions_v177.py`
   - 使用 `ALTER TABLE` 添加新列到现有表

### 代码变更

#### ArchivedSearchSession 模型
```python
# 🆕 v7.177: 新增深度搜索相关字段
is_deep_mode = Column(Integer, default=0)  # 是否深度搜索模式 (0=否, 1=是)
thinking_content = Column(Text, nullable=True)  # 深度思考内容
answer_content = Column(Text, nullable=True)  # AI 回答内容（新字段）
search_plan = Column(Text, nullable=True)  # 搜索规划 JSON
rounds = Column(Text, nullable=True)  # 搜索轮次记录 JSON
total_rounds = Column(Integer, default=0)  # 总轮数
```

#### archive_search_session() 方法
```python
# 🆕 v7.177: 提取新字段
is_deep_mode = 1 if search_result.get('isDeepMode', False) else 0
thinking_content = search_result.get('thinkingContent', '')
answer_content = search_result.get('answerContent', '')
search_plan = search_result.get('searchPlan')
rounds = search_result.get('rounds', [])
total_rounds = search_result.get('totalRounds', 0)
```

#### get_search_session() 方法
```python
# 🆕 v7.177: 新增深度搜索字段
'isDeepMode': bool(getattr(session, 'is_deep_mode', 0)),
'thinkingContent': getattr(session, 'thinking_content', '') or '',
'answerContent': getattr(session, 'answer_content', '') or '',
'searchPlan': json.loads(session.search_plan) if getattr(session, 'search_plan', None) else None,
'rounds': json.loads(session.rounds) if getattr(session, 'rounds', None) else [],
'totalRounds': getattr(session, 'total_rounds', 0) or 0,
```

## 数据库迁移

运行迁移脚本：
```bash
python migrate_search_sessions_v177.py
```

输出：
```
📦 开始迁移数据库: D:\11-20\langgraph-design\data\archived_sessions.db
数据库中的表: ['archived_sessions', 'archived_search_sessions']
当前表列: {'session_id', 'sources', 'content', 'image_count', ...}
✅ 添加列: is_deep_mode INTEGER DEFAULT 0
✅ 添加列: thinking_content TEXT
✅ 添加列: answer_content TEXT
✅ 添加列: search_plan TEXT
✅ 添加列: rounds TEXT
✅ 添加列: total_rounds INTEGER DEFAULT 0
✅ 迁移完成! 添加了 6 个新列
```

## 验证

新创建的搜索会话将正确保存和返回：
- `isDeepMode: true`
- `totalRounds: 5`
- `rounds: [...]`（包含每轮搜索的详细信息）

## 影响范围

- 修复后的新搜索会话将正确显示多轮搜索信息
- 旧会话数据保持不变（使用默认值）
- 前端无需修改（已正确发送和处理数据）

## 相关文件

- `intelligent_project_analyzer/services/session_archive_manager.py`
- `intelligent_project_analyzer/api/search_routes.py`
- `frontend-nextjs/app/search/[session_id]/page.tsx`
- `migrate_search_sessions_v177.py`
