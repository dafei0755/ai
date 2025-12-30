# Phase 2: 40% 停滞问题 - 快速验证指南

## 🎯 问题总结

**现象**: 角色审核确认后，前端进度停留在 40%，2-5 分钟不动

**根本原因**: `quality_preflight` 节点为每个角色调用 LLM (30-60秒/角色)，5 个角色 = 2.5-5 分钟，期间无进度更新

**修复内容**:
1. ✅ 添加循环内详细日志（让后端日志可见进度）
2. ✅ 返回值添加 `current_stage` 和 `detail`（节点完成后更新前端）

## 🔧 已修改文件

### 文件 1: `quality_preflight.py`

**修改位置**: Line 72-102

**修改前**:
```python
for role_id in active_agents:
    logger.debug(f"📋 检查角色: {role_id}")
    checklist = self._generate_quality_checklist(...)  # ← 阻塞 30-60秒，无日志
```

**修改后**:
```python
logger.info(f"🔄 开始检查 {len(active_agents)} 个角色的任务风险...")

for i, role_id in enumerate(active_agents, 1):
    logger.info(f"📋 [{i}/{len(active_agents)}] 正在检查角色: {role_id}")
    logger.info(f"🤖 调用 LLM 分析风险... (预计 30-60秒)")
    
    checklist = self._generate_quality_checklist(...)
    
    logger.info(f"✅ [{i}/{len(active_agents)}] 角色风险评估完成")
    logger.info(f"   - 风险等级: {checklist.get('risk_level')}")
```

**效果**:
- 后端日志会显示每个角色的检查进度
- 用户可以看到后端在工作，不是卡死

### 文件 2: `quality_preflight.py` (返回值)

**修改位置**: Line 120-128

**修改前**:
```python
return {
    "quality_checklists": quality_checklists,
    "preflight_completed": True,
    "high_risk_count": len(high_risk_warnings)
}
```

**修改后**:
```python
return {
    "quality_checklists": quality_checklists,
    "preflight_completed": True,
    "high_risk_count": len(high_risk_warnings),
    "current_stage": "质量预检完成",  # 🔥 新增
    "detail": f"已完成 {len(active_agents)} 个角色的风险评估"  # 🔥 新增
}
```

**效果**:
- `server.py` 会提取 `current_stage` 和 `detail`
- 广播 `node_update` 消息到前端
- 前端显示"质量预检完成"

## 🧪 验证步骤

### 步骤 1: 重启后端

```cmd
# 在后端终端（运行 server.py 的终端）
Ctrl + C  # 停止服务
python intelligent_project_analyzer/api/server.py  # 重新启动
```

**预期输出**:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Started reloader process using WatchFiles
```

### 步骤 2: 硬刷新前端

```
1. 完全关闭浏览器分析页面标签
2. 按 F12 打开开发者工具
3. 切换到 Console 标签
4. 访问 http://localhost:3000
5. 提交测试: "设计一个咖啡厅"
```

### 步骤 3: 观察后端日志

**关键日志（按时间顺序）**:

```
17:XX:XX | INFO | ✅ 角色审核确认通过
17:XX:XX | INFO | 🔍 Executing quality preflight node
17:XX:XX | INFO | 🔍 开始质量预检（Pre-flight Check）
17:XX:XX | INFO | 📋 检查 5 个活跃代理
17:XX:XX | INFO | 🔄 开始检查 5 个角色的任务风险...

# ← 以下是新增的日志
17:XX:XX | INFO | 📋 [1/5] 正在检查角色: V2_设计总监_2-1 (xxx)
17:XX:XX | INFO | 🤖 调用 LLM 分析风险... (预计 30-60秒)
17:XX:XX | INFO | ✅ Successfully created LLM with provider: openrouter
【等待 30-60 秒 LLM 调用】
17:XX:XX | INFO | ✅ [1/5] 角色 xxx 风险评估完成
17:XX:XX | INFO |    - 风险等级: medium
17:XX:XX | INFO |    - 风险分数: 65/100

17:XX:XX | INFO | 📋 [2/5] 正在检查角色: V3_叙事与体验专家_3-3
17:XX:XX | INFO | 🤖 调用 LLM 分析风险... (预计 30-60秒)
【等待 30-60 秒】
17:XX:XX | INFO | ✅ [2/5] 角色 xxx 风险评估完成

... (重复 5 次)

17:XX:XX | INFO | ✅ 所有任务风险可控
17:XX:XX | DEBUG | [PROGRESS] 节点: quality_preflight, 详情: 已完成 5 个角色的风险评估
17:XX:XX | INFO | 📡 已广播节点更新到 WebSocket: quality_preflight
```

### 步骤 4: 观察前端 Console

**关键日志**:

```javascript
✅ WebSocket 连接成功
📩 收到 WebSocket 消息 [initial_status]: ...
📩 收到 WebSocket 消息 [interrupt]: ... (问卷)
📩 收到 WebSocket 消息 [interrupt]: ... (需求确认)
📩 收到 WebSocket 消息 [interrupt]: ... (角色审核)

// ← 确认后，应该看到：
📊 节点更新: quality_preflight - 已完成 5 个角色的风险评估
📩 收到 WebSocket 消息 [node_update]: { node_name: "batch_executor", ... }
📊 节点更新: batch_executor - ...
```

## ✅ 成功标志

### 后端日志

- [ ] 看到 5 次"📋 [X/5] 正在检查角色"
- [ ] 看到 5 次"✅ [X/5] 角色风险评估完成"
- [ ] 看到"📡 已广播节点更新到 WebSocket: quality_preflight"

### 前端显示

- [ ] 进度从 40% 变化（即使很慢）
- [ ] 控制台显示"📊 节点更新: quality_preflight"
- [ ] 当前阶段更新为"质量预检完成"或"batch_executor"

### 时间线

```
0:00 - 提交测试
0:05 - 问卷弹出（20%）
0:10 - 需求确认（40%）
0:12 - 角色审核（40%）
0:13 - 质量预检开始 ← 关键：这里开始不应该"卡死"
1:30 - 质量预检完成（5个角色 × 30秒 = 2.5分钟）← 看到进度更新
1:31 - batch_executor 开始（50%）
4:00 - 批次执行完成（80%）
7:00 - 结果聚合（90%）
8:00 - 完成（100%）
```

## ⚠️ 已知问题

### 问题 1: 进度仍然停留 2.5-5 分钟

**原因**: quality_preflight 需要为每个角色调用 LLM，总耗时 2.5-5 分钟

**临时解决**: 
- 后端日志可见进度（每 30-60 秒一条）
- 前端只在节点完成后更新一次

**最终解决** (未实施):
- 改为批量质量预检（一次 LLM 调用处理所有角色）
- 预计可减少到 30-60 秒总时间

### 问题 2: 前端进度条不连续

**原因**: `progress = len(events) * 0.1` 不准确

**解决** (未实施):
- 使用基于时间的进度估算
- 或使用节点权重（quality_preflight 权重更高）

## 📝 后续优化（可选）

### 优化 1: 批量质量预检

**文件**: `quality_preflight.py`

**修改**: 将循环改为一次 LLM 调用

**预计效果**: 从 2.5-5 分钟减少到 30-60 秒

### 优化 2: 异步 WebSocket 广播

**文件**: `quality_preflight.py` + `server.py`

**修改**: 在循环中手动发送进度更新

**预计效果**: 前端每 30-60 秒看到一次更新

### 优化 3: 进度条平滑过渡

**文件**: `page.tsx`

**修改**: 使用 CSS 动画平滑过渡进度

**预计效果**: 进度条动画，减少"卡住"感

---

**文档时间**: 2025-11-27 17:40  
**修复文件**: 1 个  
**修改行数**: ~30 行  
**预计测试时间**: 10-15 分钟（包含完整流程）
