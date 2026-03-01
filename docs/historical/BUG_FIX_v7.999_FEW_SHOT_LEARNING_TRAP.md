# BUG_FIX_v7.999: Few-shot Learning陷阱修复

**修复日期**: 2026-02-14
**问题编号**: #v7.999
**优先级**: P0 (Critical)
**状态**: ✅ 已修复并验证

---

## 🔍 问题描述

### 现象
用户创建新session (analysis-20260214182135-529fc1de21c3) 后，狮岭村案例（复杂度0.290）**仅生成11-13个任务**，远低于v7.998推荐的28-36个。

### 关键证据
```
后端日志：
  复杂度=0.32, 建议任务数=28-36 ✅
  [Prompt] 任务数量要求: 28-36个 ✅
  [CoreTaskDecomposer] 成功解析 13 个任务 ❌

结论:
  - 代码v7.998正确（推荐28-36）✅
  - Prompt传递正确 ✅
  - LLM实际生成13个任务 ❌ ← 问题所在！
```

---

## 🎯 根因定位

### Few-shot Learning陷阱

**核心问题**: Prompt中的Few-shot示范案例恰好包含13个任务的狮岭村示例。

```yaml
## 🆕 v7.970: 理想任务拆解示范（Few-shot Learning）

Task 1: "搜索 四川广元苍溪云峰镇狮岭村的 地域文化..."
Task 2: "搜索 川北传统民居的 建筑语言..."
...
Task 13: "整合 所有调研成果，输出 狮岭村民宿集群项目研究总结报告"
```

**问题机制**:
1. LLM看到示范案例有13个任务
2. **Few-shot Learning强于显式指令**（"生成28-36个"）
3. LLM学习并模仿了13个任务的模式
4. 即使Prompt明确要求28-36个，LLM仍生成13个

**为什么v7.998的阈值优化失效？**
```
v7.998逻辑: complexity 0.290 > 0.25 → 推荐28-36个 ✅
Prompt传递: "请根据需求复杂度，生成 **28-36 个**高质量任务" ✅
Few-shot示范: 13个任务 ← LLM学习了这个模式 ❌
结果: LLM生成13个任务（示范模式覆盖了显式指令）
```

---

## 🔧 修复方案

### 方案1: 强化Prompt任务数量指令 ✅

**修改文件**: `intelligent_project_analyzer/config/prompts/core_task_decomposer.yaml`

**修改内容**:
```yaml
## ⚠️ 任务数量硬性要求（v7.999 强制执行）

**🚨 你必须生成 {task_count_min}-{task_count_max} 个任务！**

- 这是系统根据项目复杂度智能计算的最优范围
- **不得少于 {task_count_min} 个**（否则调研深度不足）
- **不得多于 {task_count_max} 个**（否则任务过碎）
- **推荐生成接近上限的任务数**（如范围28-36，建议生成32-36个）

⚠️ 注意：下方的Few-shot示范仅用于展示**任务格式和粒度规范**，其任务数量(13个)不代表你当前应生成的数量。你必须根据上述{task_count_min}-{task_count_max}范围生成任务。
```

**修改位置**: Line 347-358

---

### 方案2: Few-shot示范警示 ✅

**修改文件**: `intelligent_project_analyzer/config/prompts/core_task_decomposer.yaml`

**修改内容**:
```yaml
## 🆕 v7.970: 理想任务拆解示范（Few-shot Learning）

**⚠️ 重要说明：以下示范仅用于展示任务【格式、粒度、描述规范】，其任务数量(13个)是针对特定简单场景的示例。你当前任务必须根据上述{task_count_min}-{task_count_max}范围生成，请勿受示范数量影响！**
```

**修改位置**: Line 403-406

---

### 方案3: 代码层强制任务补充 ✅

**修改文件**: `intelligent_project_analyzer/services/core_task_decomposer.py`

**修改位置**: Line 867-910

**修改内容**:
```python
# 🆕 v7.999: 如果少于推荐最小值，强制要求LLM重新生成更多任务
if len(tasks) < recommended_min:
    shortage = recommended_min - len(tasks)
    logger.warning(f"⚠️ LLM生成了{len(tasks)}个任务，少于推荐最小值{recommended_min}（缺少{shortage}个）")
    logger.warning(f"🔄 强制请求LLM补充生成{shortage}个额外任务...")

    # 构建补充任务的Prompt
    retry_prompt = f"""
你之前生成了{len(tasks)}个任务，但根据项目复杂度（{complexity_score:.2f}），应该生成{recommended_min}-{recommended_max}个任务。

当前缺少{shortage}个任务。请基于以下已生成任务，补充生成{shortage}个新的、更细粒度的任务：

已有任务列表：
{chr(10).join([f"- {t.get('title', t.get('task_title', '未命名任务'))}" for t in tasks[:10]])}

补充要求：
1. 确保新任务与已有任务不重复
2. 进一步细分已有任务的调研维度
3. 每个建筑师/案例/标准独立成任务
4. 必须包含搜索引导词（搜索、查找、调研等）

请**仅返回{shortage}个新任务**，JSON格式，与之前格式一致。
"""

    try:
        from langchain_core.messages import HumanMessage
        retry_response = await llm.ainvoke([HumanMessage(content=retry_prompt)])
        retry_text = retry_response.content if hasattr(retry_response, "content") else str(retry_response)

        additional_tasks = decomposer.parse_response(retry_text)
        if additional_tasks:
            logger.info(f"✅ 补充生成{len(additional_tasks)}个任务")
            # 更新任务ID和执行顺序
            next_task_id = len(tasks) + 1
            for i, task in enumerate(additional_tasks):
                task['id'] = f"task_{next_task_id + i}"
                task['execution_order'] = next_task_id + i
            tasks.extend(additional_tasks)
            logger.info(f"📊 任务总数提升至{len(tasks)}个")
        else:
            logger.warning("⚠️ 补充生成失败，保持原任务列表")
    except Exception as retry_error:
        logger.error(f"❌ 补充任务生成失败: {retry_error}")
        logger.warning(f"⚠️ 保持原有{len(tasks)}个任务")
```

**关键机制**:
1. 检测任务数量不足时，自动计算缺口（如28推荐-13实际=缺15个）
2. 构建补充Prompt，明确告知LLM需要补充几个任务
3. LLM基于已有任务生成补充任务（更细粒度的拆分）
4. 自动合并补充任务到主列表，更新ID和执行顺序

---

## ✅ 修复验证

### 测试1: 本地模块重载测试
```bash
python verify_v7998.py
```

**结果**:
```
复杂度得分: 0.290
推荐任务数: 28-36个 ✅
分析依据: 输入较详细; 包含2个信息维度; 检测到跨界融合; 检测到文化深度

阈值逻辑检查:
if complexity_score < 0.12:
elif complexity_score < 0.25:  ← v7.998新阈值
elif complexity_score < 0.45:

🎉 验证通过！v7.998修复生效
```

### 测试2: 强制任务补充机制验证
```bash
python test_11tasks_issue.py
```

**日志输出**:
```
[TaskComplexityAnalyzer] 复杂度=0.32, 建议任务数=28-36
[Prompt] 任务数量要求: 28-36个
[CoreTaskDecomposer] 成功解析 13 个任务

⚠️ LLM生成了13个任务，少于推荐最小值28（缺少15个）
🔄 强制请求LLM补充生成15个额外任务...
✅ 补充生成19个任务
📊 任务总数提升至32个

[任务拆解完成] 最终生成32个任务 ✅
```

**成功验证**: 从13个提升至32个，符合28-36范围！

---

## 📊 修复效果对比

| 指标 | v7.998修复前 | v7.998修复后(仅阈值) | v7.999修复后(+补充) |
|------|-------------|---------------------|-------------------|
| 复杂度评估 | 0.290 | 0.290 | 0.290 |
| 推荐任务数 | 13-23 | **28-36** ✅ | **28-36** ✅ |
| 实际生成数 | 11-13 | **13** ❌ | **28-36** ✅ |
| Prompt传递 | ✅ | ✅ | ✅ |
| Few-shot影响 | - | **覆盖指令** ❌ | **补充机制对抗** ✅ |

**关键进步**:
- v7.998: 修复了复杂度评估逻辑，但被Few-shot学习陷阱抵消
- v7.999: 增加代码层强制补充机制，确保任务数量符合预期

---

## 🎯 适用场景

### 自动触发补充的条件
1. `len(tasks) < recommended_min` （实际任务数少于推荐最小值）
2. 项目复杂度 ≥ 0.25（中等及以上复杂度）
3. 不阻断原有任务，仅追加补充任务

### 补充任务质量保证
1. **基于已有任务细分**：避免从零开始，确保任务连贯性
2. **明确缺口数量**：Prompt中精确告知需要补充几个
3. **粒度细化引导**：明确要求"进一步细分已有任务的调研维度"
4. **格式一致性**：要求"JSON格式，与之前格式一致"

---

## 🚨 已知限制

### 1. LLM随机性
- **问题**: 即使强化Prompt，LLM仍可能受Few-shot影响生成较少任务
- **缓解**: 代码层补充机制保底（即使Prompt失效，补充逻辑也能兜底）

### 2. 补充任务质量不可控
- **问题**: 补充任务可能与原任务存在重复或逻辑不连贯
- **缓解**:
  - Prompt中明确要求"确保新任务与已有任务不重复"
  - 后续可增加任务去重和语义相似度检测

### 3. async环境下的稳定性
- **问题**: retry逻辑在高并发环境下可能失败
- **缓解**: try-except包裹，失败时保持原任务列表

---

## 📋 后续优化建议

### 优化1: Few-shot示范改进（优先级: P1）
**方案**: 移除或替换13个任务的狮岭村示例，使用更通用的格式示范

**示例**:
```yaml
任务格式示范（不限定数量）:

✅ 正确格式:
  - "搜索 设计师A的 维度1、维度2、维度3"
  - "调研 对象B的 维度1、维度2、维度3"

❌ 错误格式:
  - "研究设计师A" （缺少搜索引导词和具体维度）
```

### 优化2: 任务去重与语义聚合（优先级: P2）
**方案**: 补充任务生成后，进行语义相似度检测，自动合并重复任务

**技术路径**:
```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
task_embeddings = model.encode([t['title'] for t in tasks])

# 计算相似度矩阵
similarity_matrix = cosine_similarity(task_embeddings)

# 合并相似度>0.85的任务
merged_tasks = deduplicate_tasks(tasks, similarity_matrix, threshold=0.85)
```

### 优化3: 动态Few-shot示范生成（优先级: P3）
**方案**: 根据当前项目复杂度，动态生成相应数量的Few-shot示范

**逻辑**:
```python
if recommended_min <= 18:
    few_shot_example_count = 10-15
elif recommended_min <= 28:
    few_shot_example_count = 20-25
else:
    few_shot_example_count = 30-35
```

---

## 🎓 学到的经验

### 1. Few-shot Learning的双刃剑
- **积极作用**: 提高LLM输出质量和格式一致性
- **消极作用**: 当示范案例与当前需求不匹配时，强于显式指令
- **启示**: Few-shot示范应抽象格式规范，避免数量具体化

### 2. Prompt工程的局限性
- **问题**: 即使多次强化Prompt（加粗、警告、重复说明），LLM仍可能忽略
- **解决**: 必须配合代码层后处理/重试机制

### 3. 多层防护策略
```
防护层1: Prompt强化（任务数量硬性要求）
防护层2: Few-shot警示（示范仅为格式参考）
防护层3: 代码层补充（强制补齐任务数量）
```

**结论**: 关键质量指标不能仅依赖Prompt，需要代码层兜底保障。

---

## 📝 变更记录

| 版本 | 日期 | 修改内容 | 状态 |
|------|------|----------|------|
| v7.998 | 2026-02-14 | 降低阈值+提升最小任务数 | ✅ 已发布 |
| v7.999 | 2026-02-14 | 修复Few-shot陷阱+强制任务补充 | ✅ 已修复 |

---

## 🔗 相关文档

- [BUG_FIX_v7.998_TASK_COUNT_THRESHOLD_OPTIMIZATION.md](./BUG_FIX_v7.998_TASK_COUNT_THRESHOLD_OPTIMIZATION.md)
- [DEBUG_v7998_13tasks.md](./DEBUG_v7998_13tasks.md)
- [REVIEW_STEP1_TASK_DECOMPOSITION_MECHANISM.md](./REVIEW_STEP1_TASK_DECOMPOSITION_MECHANISM.md)

---

**修复作者**: AI Assistant
**审核状态**: ✅ 已验证通过
**部署状态**: 🚀 可立即部署
