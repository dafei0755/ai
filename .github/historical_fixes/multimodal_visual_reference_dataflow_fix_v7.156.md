# 多模态视觉参考数据流修复 v7.156

## 问题描述

**发现日期**: 2026-01-08
**会话示例**: `guest-20260108152419-15952fdd`
**严重程度**: 高 - 核心功能失效

用户通过前端上传多模态参考图片后，图片信息完全无法体现在最终生成的概念图中。经排查发现是**数据流断裂**问题，而非图片处理或概念图生成逻辑问题。

## 根因分析

### 数据流路径

```
用户上传图片 (前端)
    ↓
POST /api/analysis/start-with-files
    ↓ [server.py#L2910-2978]
图片处理:
    ├─ 保存到 data/uploads/{session_id}/
    ├─ 调用 file_processor.extract_image_enhanced() 提取视觉特征
    ├─ 收集到 visual_references 列表
    └─ 调用 _generate_global_style_anchor() 生成全局风格锚点
    ↓
会话数据存储 (Redis) [server.py#L3016-3028]
    {
        "visual_references": [...],           ← ✅ 正常存储
        "visual_style_anchor": "...",         ← ✅ 正常存储
    }
    ↓
run_workflow_async() [server.py#L1573-1627]
    ↓ ⚠️ 断点在这里！
    initial_state = StateManager.create_initial_state(
        user_input=user_input,
        session_id=session_id,
        user_id=user_id,
        analysis_mode=analysis_mode
        # ❌ 没有传递 visual_references 和 visual_style_anchor!
    )
    ↓
create_initial_state() [state.py#L392-478]
    return ProjectAnalysisState(
        ...
        uploaded_visual_references=None,      ← ❌ 硬编码为 None!
        visual_style_anchor=None,             ← ❌ 硬编码为 None!
    )
    ↓
工作流节点尝试读取视觉参考
    ├─ requirements_analyst.py#L720: visual_references = state.get("uploaded_visual_references", None) → None
    └─ task_oriented_expert_factory.py#L508: visual_references = state.get("uploaded_visual_references", None) → None
    ↓
概念图生成 [image_generator.py#L1380]
    generate_deliverable_image(..., visual_references=None, global_style_anchor=None)
    ↓
生成的概念图 ❌ 没有体现用户上传的参考图风格
```

### 核心问题

| 层级 | 字段名 | 存储位置 | 状态 |
|------|--------|----------|------|
| 会话层 | visual_references | Redis Session | ✅ 正常存储 |
| 会话层 | visual_style_anchor | Redis Session | ✅ 正常存储 |
| 工作流层 | uploaded_visual_references | LangGraph State | ❌ 始终为 None |
| 工作流层 | visual_style_anchor | LangGraph State | ❌ 始终为 None |

## 修复方案

### 1. 扩展 `create_initial_state` 函数签名

**文件**: `intelligent_project_analyzer/core/state.py`

```python
# Before
@staticmethod
def create_initial_state(
    user_input: str,
    session_id: str,
    user_id: Optional[str] = None,
    analysis_mode: Optional[str] = "normal"
) -> ProjectAnalysisState:

# After
@staticmethod
def create_initial_state(
    user_input: str,
    session_id: str,
    user_id: Optional[str] = None,
    analysis_mode: Optional[str] = "normal",
    uploaded_visual_references: Optional[List[Dict[str, Any]]] = None,  # 新增
    visual_style_anchor: Optional[str] = None  # 新增
) -> ProjectAnalysisState:
```

### 2. 使用传入参数初始化状态

**文件**: `intelligent_project_analyzer/core/state.py`

```python
# Before
uploaded_visual_references=None,
visual_style_anchor=None,

# After
uploaded_visual_references=uploaded_visual_references,
visual_style_anchor=visual_style_anchor,
```

### 3. 从会话数据传递视觉参考

**文件**: `intelligent_project_analyzer/api/server.py`

```python
# 🆕 v7.156: 从 session_data 提取多模态视觉参考
visual_references = session_data.get("visual_references") if session_data else None
visual_style_anchor = session_data.get("visual_style_anchor") if session_data else None

if visual_references:
    logger.info(f"🖼️ [v7.156] 检测到 {len(visual_references)} 个视觉参考，将注入工作流初始状态")

initial_state = StateManager.create_initial_state(
    user_input=user_input,
    session_id=session_id,
    user_id=user_id,
    analysis_mode=analysis_mode,
    uploaded_visual_references=visual_references,  # 新增
    visual_style_anchor=visual_style_anchor  # 新增
)
```

## 存储优化（附加改进）

### 双路径存储

为了提升容器/分布式部署兼容性，同时存储绝对路径和相对路径：

```python
visual_references.append({
    "file_path": str(file_path),  # 绝对路径（本地快速访问）
    "relative_path": f"{session_id}/{file_path.name}",  # 相对路径（部署兼容）
    "cached_at": datetime.now().isoformat(),  # 缓存时间戳
    ...
})
```

### 按需加载工具

新增 `FileProcessor` 方法：

1. **`load_image_base64(file_path, max_size=1024)`**: 按需加载图片为 base64，支持自动缩放
2. **`resolve_image_path(visual_ref)`**: 自动解析有效图片路径，优先绝对路径，回退相对路径

## 验证方法

1. 重启后端服务
2. 上传多模态参考图片
3. 观察日志中是否出现：
   ```
   🖼️ [v7.156] 检测到 N 个视觉参考，将注入工作流初始状态
   🎨 [v7.156] 检测到全局风格锚点: ...
   🔄 [ASYNC] 初始状态已创建 | visual_refs=N
   ```

## 影响范围

- `intelligent_project_analyzer/core/state.py` - `create_initial_state` 函数
- `intelligent_project_analyzer/api/server.py` - `run_workflow_async` 函数
- `intelligent_project_analyzer/services/file_processor.py` - 新增工具方法

## 后续建议

1. **会话恢复场景**: 检查 `/api/analysis/resume` 端点是否也需要从 Redis 重新加载视觉参考
2. **对象存储集成**: 如需跨服务器共享图片，可上传到 MinIO/S3
3. **缩略图预生成**: 为大图生成小尺寸缩略图，加速前端预览
