# 概念图生成机制诊断报告

**生成时间**: 2026-01-03
**诊断人员**: GitHub Copilot

---

## ✅ 核心结论

**是的，当前概念图机制是针对专家交付内容进行针对性生成的。**

---

## 📋 完整生成流程

### 1. 交付物元数据生成阶段 (deliverable_id_generator_node)

**位置**: `intelligent_project_analyzer/workflow/nodes/deliverable_id_generator_node.py`

**时机**: Project Director 之后、专家执行之前

**生成内容**:
```python
deliverable_metadata = {
    "2-1_1_143022_abc": {
        "id": "2-1_1_143022_abc",
        "name": "整体设计方案",
        "description": "项目整体设计策略与概念",
        "keywords": ["设计方向", "风格定位", "空间规划"],
        "constraints": {
            "must_include": ["设计理念", "空间布局", "材质选型"],
            "style_preferences": "professional architectural rendering"
        },
        "owner_role": "2-1",
        "created_at": "2025-12-29T14:30:22"
    }
}
```

**特点**:
- ✅ 每个角色有预定义的交付物模板（V2/V3/V4/V5/V6）
- ✅ 包含具体的关键词和约束条件
- ✅ 约束条件包括必须包含的元素和风格偏好

---

### 2. 专家执行阶段 (main_workflow.py)

**位置**: `intelligent_project_analyzer/workflow/main_workflow.py:1470-1520`

**触发时机**: 专家完成分析后

**输入数据**:
1. ✅ **专家分析内容** (`expert_summary`): 专家生成的实际分析文本（前500字符）
2. ✅ **交付物元数据** (`deliverable_metadata`): 包含关键词、约束、风格偏好
3. ✅ **问卷数据** (`questionnaire_data`):
   - `profile_label`: 用户风格标签（如"现代海洋风"）
   - `gap_answers`: 用户详细需求回答

**核心代码**:
```python
# 🆕 v7.121: 读取问卷数据用于概念图生成
questionnaire_summary = state.get("questionnaire_summary", {})

# 为每个交付物生成概念图
for deliverable_id in deliverable_ids:
    metadata = deliverable_metadata.get(deliverable_id)

    image_metadata = await image_generator.generate_deliverable_image(
        deliverable_metadata=metadata,           # ✅ 交付物约束
        expert_analysis=expert_summary,          # ✅ 专家分析内容
        session_id=session_id_for_image,
        project_type=project_type,
        aspect_ratio="16:9",
        questionnaire_data=questionnaire_summary  # ✅ 问卷数据
    )
```

---

### 3. 图片生成阶段 (image_generator.py)

**位置**: `intelligent_project_analyzer/services/image_generator.py:889-1040`

**方法**: `generate_deliverable_image()`

#### 3.1 增强Prompt构建

**组成部分**（优先级从高到低）:

1. **交付物名称**
   ```
   设计可视化需求：整体设计方案
   ```

2. **用户风格偏好**（来自问卷Step 2）
   ```
   【用户风格偏好】
   风格标签：现代海洋风
   ```

3. **交付物核心关键词**
   ```
   【交付物核心关键词】
   设计方向, 风格定位, 空间规划
   ```

4. **必须包含的设计元素**
   ```
   【必须包含的设计元素】
   设计理念, 空间布局, 材质选型
   ```

5. **用户详细需求**（来自问卷Step 3）
   ```
   【用户详细需求】
   1. 希望客厅有大量自然光...
   2. 想保留渔村特色...
   3. 需要考虑收纳空间...
   ```

6. **风格偏好**
   ```
   【风格偏好】
   professional architectural rendering
   ```

7. **专家分析摘要**
   ```
   【专家分析摘要】
   (专家实际生成的分析内容前500字符)
   ```

#### 3.2 LLM语义提取

**位置**: `_llm_extract_visual_prompt()` 方法

**作用**: 将上述中文增强Prompt转换为英文视觉化提示词

**输出示例**:
```
Modern coastal interior design, open-plan living space with abundant natural light,
wooden elements, fishing village cultural elements, professional architectural
rendering, 16:9 aspect ratio, photorealistic quality
```

---

## 🎯 针对性体现在哪里？

### ✅ 1. 针对交付物类型

不同角色的交付物有不同模板：

- **V2 (通用设计)**: 整体设计方案、关键节点深化
- **V3 (高阶设计)**: 叙事与体验策略
- **V4 (研究型)**: 设计研究报告
- **V5 (场景型)**: 场景设计方案
- **V6 (技术型)**: 技术实施方案

每个模板有专属的：
- 关键词列表
- 必须包含的元素
- 风格偏好（rendering style）

### ✅ 2. 针对专家分析内容

- 使用专家实际生成的分析文本（前500字符）
- 确保图片反映专家的实际思路和建议

### ✅ 3. 针对用户需求

**v7.121版本强化** - 问卷数据注入：
- **Step 2风格标签**: 如"现代海洋风"直接注入
- **Step 3详细回答**: 提取视觉相关需求（前3条，每条限200字符）

### ✅ 4. 数据流保障

**v7.122优化** - 确保数据传递：
```
用户问卷 → questionnaire_summary → generate_deliverable_image() → LLM提取 → 图片生成
```

---

## 🔍 代码证据

### 证据1: 交付物元数据注入

```python
# image_generator.py:950-986
deliverable_name = deliverable_metadata.get("name", "设计交付物")
keywords = deliverable_metadata.get("keywords", [])
constraints = deliverable_metadata.get("constraints", {})

enhanced_prompt = f"""
设计可视化需求：{deliverable_name}

【交付物核心关键词】
{', '.join(keywords) if keywords else '现代设计'}

【必须包含的设计元素】
{', '.join(constraints.get('must_include', []))}
"""
```

### 证据2: 问卷数据注入

```python
# image_generator.py:950-970
if questionnaire_data:
    profile_label = questionnaire_data.get("profile_label", "")
    gap_answers = questionnaire_data.get("answers", {}).get("gap_answers", {})

    enhanced_prompt += f"""
【用户风格偏好】（来自问卷Step 2）
风格标签：{profile_label or '未定义'}
"""

    if gap_details:
        enhanced_prompt += f"""
【用户详细需求】（来自问卷Step 3）
{chr(10).join(f"{i+1}. {detail}" for i, detail in enumerate(gap_details[:3]))}
"""
```

### 证据3: 专家分析注入

```python
# image_generator.py:990-995
enhanced_prompt += f"""
【专家分析摘要】
{expert_analysis[:500] if expert_analysis else '专业设计分析'}

请基于以上交付物要求和用户需求，提取视觉化提示词。
"""
```

---

## 📊 与旧版本对比

### 旧版本 (v7.50之前)

❌ **generate_concept_images()** - 泛化生成：
- 只基于专家分析摘要
- 使用通用关键词提取
- 无交付物约束
- 无用户需求注入

### 新版本 (v7.108+, v7.121+)

✅ **generate_deliverable_image()** - 精准生成：
- ✅ 基于交付物元数据（名称、关键词、约束）
- ✅ 注入专家分析内容
- ✅ 注入问卷风格标签
- ✅ 注入用户详细需求
- ✅ LLM语义提取提升质量

---

## 🎨 生成质量保障

### 1. 提示词质量检查

```python
# image_generator.py:1020-1023
if len(visual_prompt) < 10:
    logger.error(f"❌ Invalid prompt length: {len(visual_prompt)} chars")
    raise ValueError(f"Prompt too short: {visual_prompt}")
```

### 2. LLM提取失败保护

```python
# image_generator.py:1010-1015
if not visual_prompts:
    logger.warning("⚠️ LLM提取失败，使用基础Prompt")
    visual_prompt = f"{deliverable_name}, {', '.join(keywords)}, professional rendering"
```

### 3. 多重数据源融合

优先级：用户需求 > 交付物约束 > 专家分析 > 默认模板

---

## ✅ 结论

**当前概念图生成机制完全是针对专家交付内容的针对性生成：**

1. ✅ **交付物驱动**: 每个交付物有独立的元数据和约束
2. ✅ **专家内容驱动**: 使用专家实际分析结果
3. ✅ **用户需求驱动**: 注入问卷风格和详细需求
4. ✅ **多维度融合**: 交付物约束 + 专家分析 + 用户需求 = 精准提示词
5. ✅ **质量保障**: LLM语义提取 + Fallback机制

---

## 📈 版本演进

- **v7.50**: 引入LLM语义提取
- **v7.108**: 新增 `generate_deliverable_image()` 方法，交付物元数据注入
- **v7.121**: 增强问卷数据注入（风格标签 + 详细需求）
- **v7.122**: 数据流优化，确保问卷数据传递

---

## 🔗 相关文件

1. **交付物元数据生成**: `intelligent_project_analyzer/workflow/nodes/deliverable_id_generator_node.py`
2. **概念图生成入口**: `intelligent_project_analyzer/workflow/main_workflow.py:1470-1520`
3. **图片生成服务**: `intelligent_project_analyzer/services/image_generator.py:889-1040`
4. **设计文档**: `docs/CONCEPT_IMAGE_PRECISION_DESIGN.md`
5. **数据流优化**: `docs/DATA_FLOW_OPTIMIZATION_V7.122.md`
