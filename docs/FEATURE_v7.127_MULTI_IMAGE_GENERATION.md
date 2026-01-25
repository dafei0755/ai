# v7.127 多图生成功能实现文档

## 📋 需求确认

- **普通模式 (normal)**：1个交付物 → 生成 1 张概念图
- **深度思维模式 (deep_thinking)**：1个交付物 → 生成 3 张备选概念图（使用同一提示词，供用户选择最佳效果）

## ✅ 实现完成

### 核心修改

#### 1. 图片生成器核心逻辑 ([image_generator.py](intelligent_project_analyzer/services/image_generator.py))

**关键变更**：

- **返回类型更新** (line 900): `-> "List[ImageMetadata]"`
- **配置读取** (line 950-958):
  ```python
  concept_image_config = deliverable_metadata.get("concept_image_config", {})
  image_count = concept_image_config.get("count", 1)  # 默认1（向后兼容）
  ```

- **生成循环实现** (line 1016-1101):
  - 提示词提取1次（所有图片使用同一提示词）
  - `for attempt in range(image_count)` 循环生成
  - 文件名唯一性：
    - 微秒时间戳：`%Y%m%d_%H%M%S_%f`
    - 版本后缀：`_v{attempt + 1}`
    - 示例：`test-deep-001_interior_20260103_182813_735491_v1.png`
  - 部分失败处理：
    - 捕获单次失败，继续下一次
    - 返回成功的图片列表
    - 全部失败则抛出异常

#### 2. 调用方更新

##### [task_oriented_expert_factory.py](intelligent_project_analyzer/agents/task_oriented_expert_factory.py:425-443)

```python
# v7.127: 返回值改为 List[ImageMetadata]
image_metadata_list = await image_generator.generate_deliverable_image(...)

# 遍历添加所有生成的图片
for img_metadata in image_metadata_list:
    concept_images.append(img_metadata.model_dump())

logger.info(f"    ✅ 成功生成 {len(image_metadata_list)} 张概念图")
```

##### [main_workflow.py](intelligent_project_analyzer/workflow/main_workflow.py:1488-1503)

```python
# v7.127: 返回值改为 List[ImageMetadata]
image_metadata_list = await image_generator.generate_deliverable_image(...)

# 遍历添加所有生成的图片
for img_metadata in image_metadata_list:
    concept_images.append(img_metadata.model_dump())
```

### 测试验证

#### 测试脚本：[tests/test_multi_image_generation.py](tests/test_multi_image_generation.py)

**测试覆盖**：

1. ✅ **普通模式测试**：
   - 配置：`count=1, editable=false`
   - 验证：生成1张图，文件名包含`_v1.png`

2. ✅ **深度思维模式测试**：
   - 配置：`count=3, editable=true`
   - 验证：生成3张图，文件名包含`_v1`, `_v2`, `_v3`
   - 验证：所有文件名唯一

3. ✅ **向后兼容性测试**：
   - 配置：无`concept_image_config`
   - 验证：默认生成1张图

**测试结果**：

```
================================================================================
✅ 所有测试通过！
================================================================================

总结:
  - 普通模式（count=1）: ✅ 正常工作
  - 深度思维模式（count=3）: ✅ 正常工作
  - 向后兼容性: ✅ 正常工作
  - 文件名唯一性: ✅ 验证通过
```

### 日志输出示例

#### 深度思维模式（生成3张图）

```
🎨 [v7.108] 为交付物生成概念图: 海洋风格卧室设计
  [v7.127] 将生成 3 张概念图
  🔍 调用LLM提取视觉Prompt...
  ✅ 提取的视觉Prompt: Create a serene ocean-themed bedroom interior...

  🖼️ [图片 1/3] 开始生成 (宽高比: 16:9)...
    ✅ 图片生成成功！
    💾 已保存: test-deep-001_interior_20260103_182813_735491_v1.png

  🖼️ [图片 2/3] 开始生成 (宽高比: 16:9)...
    ✅ 图片生成成功！
    💾 已保存: test-deep-001_interior_20260103_182837_983741_v2.png

  🖼️ [图片 3/3] 开始生成 (宽高比: 16:9)...
    ✅ 图片生成成功！
    💾 已保存: test-deep-001_interior_20260103_182858_645700_v3.png

✅ [v7.127] 成功生成全部 3 张概念图
```

## 🎯 核心特性

1. **同一提示词多次生成**：
   - 提示词只提取1次（减少LLM调用）
   - 所有图片使用相同的视觉描述
   - 确保风格一致性

2. **文件名唯一性保证**：
   - 微秒级时间戳
   - 版本号后缀（v1, v2, v3）
   - 格式：`{deliverable_id}_{project_type}_{timestamp}_{version}.png`

3. **错误处理策略**：
   - 部分失败：返回成功的图片（如2/3成功）
   - 全部失败：抛出异常，不阻塞工作流
   - 调用方捕获异常，继续执行

4. **向后兼容性**：
   - 缺失配置时默认`count=1`
   - 返回值类型改为列表，但调用方已遍历处理
   - 普通模式仍返回1张图的列表

## 📊 返回数据结构

```python
# 深度思维模式返回示例
[
    ImageMetadata(
        deliverable_id="test-deep-001",
        filename="test-deep-001_interior_20260103_182813_735491_v1.png",
        url="sessions/test-session-deep/images/...",
        visual_prompt="Create a serene ocean-themed bedroom...",
        owner_role="室内设计师",
        aspect_ratio="16:9",
        created_at="2026-01-03T18:28:13"
    ),
    ImageMetadata(..._v2.png, ...),
    ImageMetadata(..._v3.png, ...)
]
```

## 🔍 验证清单

- ✅ 普通模式生成1张图
- ✅ 深度思维模式生成3张图
- ✅ 使用同一提示词
- ✅ 文件名唯一且包含版本号
- ✅ 部分失败返回成功的图片
- ✅ 全部失败抛出异常
- ✅ 向后兼容（缺失配置默认1张）
- ✅ 调用方正确处理列表返回值
- ✅ 日志清晰显示进度

## 📦 修改文件清单

| 文件路径 | 修改类型 | 关键行数 |
|---------|---------|---------|
| [intelligent_project_analyzer/services/image_generator.py](intelligent_project_analyzer/services/image_generator.py) | **核心修改** | 25, 31-32, 900, 950-1101 |
| [intelligent_project_analyzer/agents/task_oriented_expert_factory.py](intelligent_project_analyzer/agents/task_oriented_expert_factory.py) | 调用方更新 | 425-443 |
| [intelligent_project_analyzer/workflow/main_workflow.py](intelligent_project_analyzer/workflow/main_workflow.py) | 调用方更新 | 1488-1503 |
| [tests/test_multi_image_generation.py](tests/test_multi_image_generation.py) | **新增测试** | 1-195 |

## 🎉 部署状态

- 实现时间：2026-01-03
- 测试状态：✅ 全部通过
- 版本标记：**v7.127**
- 向后兼容：✅ 是
