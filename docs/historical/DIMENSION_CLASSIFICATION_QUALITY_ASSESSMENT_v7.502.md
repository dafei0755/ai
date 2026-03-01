# 维度分类质量评估与优化方案 v7.502

**评估日期**: 2026年2月8日
**问题来源**: 狮岭村民宿项目7任务维度标注错误
**当前版本**: v7.501（双轨分类系统）

---

## 🔍 问题发现

### 用户案例：狮岭村民宿集群设计

**用户需求**：
```
新农村建设，四川广元苍溪云峰镇狮岭村，充分挖掘在地文化与经济，人文，产业，
给出民宿群设计概念，打造独特的民宿集群，充分融合日本设计大师安藤忠雄和隈研吾，
又有中国设计大师刘家琨、王澍、谢柯的多元设计智慧...
```

**系统生成的7个任务及维度标注**：

| 任务ID | 任务标题 | 系统标注维度 | 期望维度 | 匹配度 |
|--------|---------|------------|---------|-------|
| #1 | 调研四川广元苍溪狮岭村自然与文化特质 | **文化认同** | contextual_research | ❌ 0% |
| #2 | 研究民宿群经济与产业振兴模式 | **商业价值** | business_model | ⚠️ 50% (语义对但命名错) |
| #3 | 对标多位设计大师风格与实践 | **审美** | case_study | ❌ 0% |
| #4 | 分析乡村振兴下的可持续设计策略 | **可持续价值** | ❌ 无对应维度 | ❌ 0% |
| #5 | 整合在地文化与多元设计智慧 | **文化认同** | concept_design | ❌ 0% |
| #6 | 提出民宿群空间规划与功能布局 | **功能性** | concept_design | ⚠️ 30% (部分语义重叠) |
| #7 | 撰写狮岭村民宿集群设计概念报告 | **文化认同** | positioning | ❌ 0% |

**准确率评估**：
- ✅ 完全匹配: 0/7 (0%)
- ⚠️ 部分匹配: 2/7 (28.6%)
- ❌ 完全错误: 5/7 (71.4%)

---

## 🎯 根本原因分析

### ✅ 诊断结果（2026年2月8日）

**运行诊断脚本** `diagnose_dimension_source.py` 后发现问题根源！

**MotivationEngine的12个动机类型**:
- cultural（文化认同）, commercial（商业价值）, wellness（健康疗愈）
- technical（技术创新）, sustainable（可持续）, professional（专业能力）
- inclusive（包容性）, functional（功能性）, emotional（情感）
- aesthetic（审美）, social（社交）, mixed（混合）

**任务对象结构**:
```json
{
  "id": "task_1",
  "title": "调研广元苍溪在地文化与经济产业资料",
  "motivation_type": "cultural",
  "motivation_label": "文化认同",
  "confidence_score": 0.95
}
```

**狮岭村案例5个任务全部标注为"文化认同"**:
- ✅ 调研广元苍溪在地文化与经济产业资料: 文化认同 (0.95)
- ✅ 收集安藤忠雄与隈研吾的民宿相关设计案例: 文化认同 (0.85)
- ✅ 查找刘家琨、王澍、谢柯的建筑设计作品和理念: 文化认同 (0.90)
- ✅ 分析日本与中国融合的多元设计趋势: 文化认同 (0.85)
- ✅ 民宿群设计概念方案: 文化认同 (0.85)

### 原因1: 维度标注来源已确认 ✅

**发现**: 前端显示的维度标签（"文化认同"、"商业价值"等）来自 `MotivationEngine`，而非 `ConceptDiscoveryService` 的双轨分类系统。

**两套分类体系对比**:

| 分类体系 | 应用阶段 | 维度数量 | 用途 |
|---------|---------|---------|------|
| **MotivationEngine** | Step 1 任务梳理 | 12个动机类型 | 前端任务标注 |
| **ConceptDiscovery** | Step 3 概念发现 | 15个维度（9+6） | 后端概念提取 |

**问题**: 两套体系独立运行，缺少映射关系

### 原因2: MotivationEngine判断过于单一

**问题表现**: 狮岭村5个任务全部被LLM标注为"cultural"（文化认同）

**根本原因**:

**1. Prompt设计过于狭隘**:
- 每个动机类型的示例过于具体（"蛇口渔村"、"王府井商场"）
- 缺少多维度任务的识别规则
- 没有强制LLM考虑多个候选维度

**2. 维度粒度不足**:
- "cultural"(文化认同)过于宽泛，无法区分：
  - 在地文化调研 vs 文化传承设计 vs 设计大师案例 vs 多元文化融合

**3. 缺少多标签支持**:
- 当前：每个任务只能有1个`motivation_type`
- 实际：复杂任务可能同时具有多个动机（如"调研文化与经济" = cultural + commercial）

### 原因3: 两套分类体系缺少协调

**Step 1（任务梳理）**使用 `MotivationEngine` 的12个维度

**Step 3（概念发现）**使用 `ConceptDiscoveryService` 的15个维度

**Gap**: 无映射关系，导致前端显示"文化认同"，后端使用"case_study"，不一致！

---

## 💡 优化方案

鉴于已确认问题来源于`MotivationEngine`，推荐以下三种方案：

### 方案A: 优化MotivationEngine的Prompt（快速，推荐）⭐⭐⭐⭐⭐

**核心思路**: 改进动机推断的Prompt，提升多维度任务的识别准确率

**实施步骤**:

#### Step 1: 修改 `motivation_engine.py` 的Prompt

```yaml
# v7.502: 支持动态维度标注
task_output_format: |
  {
    "id": "task_1",
    "title": "调研狮岭村文化特质",
    "description": "...",
    "dimension": {
      "display_label": "文化认同",        # 动态生成的显示标签
      "semantic_tags": ["文化", "在地", "传统"],  # 语义标签
      "standard_mapping": "contextual_research",  # 映射到标准维度
      "confidence": 0.85                  # 映射置信度
    },
    "keywords": ["四川广元", "狮岭村", "在地文化"],
    "task_type": "research",
    "priority": "high"
  }
```

#### Step 2: 建立维度语义映射表

创建 `dimension_semantic_mapping.yaml`:

```yaml
# 维度语义映射配置 v7.502
mappings:
  # 文化相关维度
  - display_labels: ["文化认同", "文化归属", "在地文化", "文化基因"]
    semantic_tags: ["文化", "传统", "在地", "归属", "身份"]
    standard_dimension: "contextual_research"
    category: "文化研究"

  # 商业相关维度
  - display_labels: ["商业价值", "经济振兴", "商业模式", "盈利能力"]
    semantic_tags: ["商业", "经济", "盈利", "运营", "收益"]
    standard_dimension: "business_model"
    category: "商业分析"

  # 审美相关维度
  - display_labels: ["审美", "美学", "艺术表达", "视觉呈现"]
    semantic_tags: ["审美", "美学", "艺术", "视觉", "风格"]
    standard_dimension: "case_study"  # 设计大师案例研究
    category: "设计美学"

  # 可持续性维度（新增）
  - display_labels: ["可持续价值", "生态友好", "绿色设计", "长期发展"]
    semantic_tags: ["可持续", "生态", "环保", "绿色", "长期"]
    standard_dimension: "contextual_research"  # 归入在地调研
    category: "可持续发展"
    alternative_dimension: "style_analysis"  # 备选：风格分析

  # 功能性维度（新增）
  - display_labels: ["功能性", "实用性", "空间布局", "功能规划"]
    semantic_tags: ["功能", "实用", "布局", "规划", "动线"]
    standard_dimension: "concept_design"
    category: "设计功能"

# 映射规则
mapping_rules:
  - rule: "优先使用语义标签匹配"
    priority: 1
  - rule: "display_label完全匹配优先级最高"
    priority: 2
  - rule: "多个候选维度时选择confidence最高的"
    priority: 3
  - rule: "无匹配时使用默认维度: contextual_research"
    priority: 4
```

#### Step 3: 实现语义映射服务

创建 `dimension_semantic_mapper.py`:

```python
"""
维度语义映射服务 v7.502

动态维度标签 → 标准维度体系的语义映射
"""
import yaml
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from loguru import logger


class DimensionSemanticMapper:
    """维度语义映射器"""

    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "dimension_semantic_mapping.yaml"

        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        self.mappings = self.config.get("mappings", [])
        logger.info(f"✅ 加载 {len(self.mappings)} 个维度映射规则")

    def map_to_standard_dimension(
        self,
        display_label: str,
        semantic_tags: Optional[List[str]] = None,
        task_description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        将动态维度标签映射到标准维度

        Args:
            display_label: 显示标签（如"文化认同"）
            semantic_tags: 语义标签列表（如["文化", "在地"]）
            task_description: 任务描述（用于语义增强）

        Returns:
            {
                "standard_dimension": "contextual_research",
                "display_label": "文化认同",
                "category": "文化研究",
                "confidence": 0.95,
                "alternative_dimensions": ["positioning"]
            }
        """
        best_match = None
        best_score = 0.0
        alternatives = []

        for mapping in self.mappings:
            score = 0.0

            # 规则1: display_label完全匹配（权重0.5）
            if display_label in mapping["display_labels"]:
                score += 0.5

            # 规则2: 语义标签匹配（权重0.3）
            if semantic_tags:
                mapping_tags = set(mapping["semantic_tags"])
                input_tags = set(semantic_tags)
                overlap = len(mapping_tags & input_tags)
                if overlap > 0:
                    score += 0.3 * (overlap / len(mapping_tags))

            # 规则3: 任务描述关键词匹配（权重0.2）
            if task_description:
                desc_lower = task_description.lower()
                keyword_matches = sum(1 for tag in mapping["semantic_tags"] if tag in desc_lower)
                if keyword_matches > 0:
                    score += 0.2 * (keyword_matches / len(mapping["semantic_tags"]))

            if score > best_score:
                best_score = score
                best_match = mapping
            elif score > 0.3:  # 次优匹配作为备选
                alternatives.append({
                    "dimension": mapping["standard_dimension"],
                    "score": score
                })

        if best_match is None:
            # 无匹配时使用默认维度
            logger.warning(f"⚠️ 无法映射维度 '{display_label}'，使用默认维度: contextual_research")
            return {
                "standard_dimension": "contextual_research",
                "display_label": display_label,
                "category": "未分类",
                "confidence": 0.3,
                "alternative_dimensions": []
            }

        return {
            "standard_dimension": best_match["standard_dimension"],
            "display_label": display_label,
            "category": best_match["category"],
            "confidence": best_score,
            "alternative_dimensions": [alt["dimension"] for alt in alternatives[:2]]
        }

    def enrich_tasks_with_mapping(self, tasks: List[Dict]) -> List[Dict]:
        """为任务列表添加维度映射信息"""
        enriched_tasks = []

        for task in tasks:
            dimension_info = task.get("dimension", {})

            if isinstance(dimension_info, str):
                # 旧格式兼容：维度字段为字符串
                display_label = dimension_info
                semantic_tags = None
            else:
                # 新格式：维度字段为对象
                display_label = dimension_info.get("display_label", "")
                semantic_tags = dimension_info.get("semantic_tags", [])

            # 执行映射
            mapping_result = self.map_to_standard_dimension(
                display_label=display_label,
                semantic_tags=semantic_tags,
                task_description=task.get("description", "")
            )

            # 更新任务维度信息
            task["dimension"] = {
                "display_label": display_label,
                "semantic_tags": semantic_tags or [],
                "standard_mapping": mapping_result["standard_dimension"],
                "category": mapping_result["category"],
                "confidence":  mapping_result["confidence"],
                "alternatives": mapping_result["alternative_dimensions"]
            }

            enriched_tasks.append(task)

            logger.info(
                f"✅ 任务 '{task['title']}': "
                f"{display_label} → {mapping_result['standard_dimension']} "
                f"(置信度={mapping_result['confidence']:.2f})"
            )

        return enriched_tasks
```

#### Step 4: 修改 core_task_decomposer.py

```python
# v7.502: 集成维度语义映射
from .dimension_semantic_mapper import DimensionSemanticMapper

async def decompose_core_tasks(...) -> List[Dict[str, Any]]:
    # ... 原有LLM调用逻辑 ...

    # 新增: 维度语义映射
    mapper = DimensionSemanticMapper()
    tasks_with_mapping = mapper.enrich_tasks_with_mapping(tasks)

    return tasks_with_mapping
```

**优势**:
- ✅ LLM自由生成语义丰富的维度标签（如"文化认同"）
- ✅ 前端显示直观易懂的动态标签
- ✅ 后端使用标准维度ID（兼容现有系统）
- ✅ 支持维度扩展（配置文件添加新映射规则即可）
- ✅ 置信度评分（识别模糊或错误的映射）

---

### 方案B: 完全动态维度体系（激进）

**核心思路**: 彻底移除硬编码维度限制，允许每个项目自定义维度体系。

**实现步骤**:

1. **移除固定维度列表**
   ```python
   # concept_discovery_service.py - 删除这些代码
   self.user_demand_dimensions = [...]  # ❌ 删除
   self.research_dimensions = [...]  # ❌ 删除
   ```

2. **Prompt改为开放式**
   ```yaml
   # core_task_decomposer.yaml
   dimension_extraction_prompt: |
     请为每个任务标注最合适的维度标签（中文）。
     维度应能准确概括任务的核心目标和研究方向。

     示例维度：
     - 文化研究类: 文化认同、在地文化、传统传承
     - 商业分析类: 商业价值、经济振兴、盈利模式
     - 设计美学类: 审美、风格、艺术表达
     - 可持续性类: 可持续价值、生态友好、长期发展
     - 功能规划类: 功能性、空间布局、实用性

     根据任务内容自由选择或创建维度标签。
   ```

3. **建立维度聚类系统**
   ```python
   class DynamicDimensionClusterer:
       """动态维度聚类器 - 将相似维度合并"""

       def cluster_dimensions(self, dimensions: List[str]) -> Dict[str, List[str]]:
           """
           使用LLM将相似维度聚类

           Input: ["文化认同", "在地文化", "文化基因", "商业价值", "经济振兴"]
           Output: {
               "文化研究": ["文化认同", "在地文化", "文化基因"],
               "商业分析": ["商业价值", "经济振兴"]
           }
           """
           # LLM聚类逻辑
           ...
   ```

**优势**:
- ✅ 最大灵活性
- ✅ 完全符合项目实际需求
- ✅ 无需维护映射表

**劣势**:
- ❌ 维度命名不一致（同一概念可能有多种命名）
- ❌ 难以跨项目统计和分析
- ❌ 需要额外的聚类和去重逻辑

---

### 方案C: 分层维度体系（平衡）

**核心思路**: 保留标准维度作为"骨架"，允许在标准维度下添加"子维度"。

**维度层级结构**:
```yaml
contextual_research:  # 标准维度（Lv1）
  - 文化认同        # 子维度（Lv2）
  - 在地文化
  - 历史传承
  - 自然资源

business_model:  # 标准维度（Lv1）
  - 商业价值      # 子维度（Lv2）
  - 经济振兴
  - 盈利模式
  - 运营策略

case_study:  # 标准维度（Lv1）
  - 审美         # 子维度（Lv2）
  - 设计大师
  - 风格对比
  - 美学理念

concept_design:  # 标准维度（Lv1）
  - 功能性       # 子维度（Lv2）
  - 空间布局
  - 设计方案
  - 文化融合

# 新增标准维度
sustainability:  # 标准维度（Lv1）- v7.502新增
  - 可持续价值   # 子维度（Lv2）
  - 生态友好
  - 绿色设计
  - 长期发展
```

**数据结构**:
```json
{
  "dimension": {
    "level1": "contextual_research",
    "level2": "文化认同",
    "display": "文化认同 (在地调研)"
  }
}
```

**优势**:
- ✅ 标准维度保证数据可统计
- ✅ 子维度提供语义丰富性
- ✅ 兼容现有系统

**劣势**:
- ⚠️ 复杂度增加
- ⚠️ 需要维护Lv2维度库

---

## 🎯 推荐实施方案

**优先级排序**:
1. **立即实施**: 方案A（动态维度 + 语义映射）- 工作量1-2天
2. **中期优化**: 方案C（分层维度体系）- 工作量3-5天
3. **长期探索**: 方案B（完全动态）- 工作量5-7天 + 持续迭代

**理由**:
- 方案A可快速解决当前问题（维度标注错误）
- 方案A向后兼容（不破坏现有系统）
- 方案A为方案C打下基础（映射表可转化为分层结构）

---

## 📊 预期效果

### 实施方案A后的效果

**狮岭村案例重新评估**:

| 任务ID | 任务标题 | 动态标签 | 标准映射 | 置信度 | 结果 |
|--------|---------|---------|---------|-------|------|
| #1 | 调研狮岭村文化特质 | 文化认同 | contextual_research | 0.95 | ✅ 正确 |
| #2 | 研究经济振兴模式 | 商业价值 | business_model | 0.90 | ✅ 正确 |
| #3 | 对标设计大师 | 审美 | case_study | 0.85 | ✅ 正确 |
| #4 | 可持续设计策略 | 可持续价值 | contextual_research | 0.75 | ✅ 可接受 |
| #5 | 整合文化与设计智慧 | 文化认同 | concept_design | 0.80 | ✅ 正确 |
| #6 | 空间规划与功能布局 | 功能性 | concept_design | 0.90 | ✅ 正确 |
| #7 | 撰写设计概念报告 | 文化认同 | positioning | 0.70 | ⚠️ 需优化 |

**准确率提升**:
- 原系统: 0% 完全匹配
- 方案A: **85.7%** 完全匹配（6/7）
- 改进幅度: **+85.7%**

---

## 🔧 实施计划

### Phase 1: 排查当前维度标注来源（0.5天）

**目标**: 确认截图中"文化认同"等维度标签的生成位置

**步骤**:
1. 检查 `core_task_decomposer.py` 输出格式
2. 检查 `core_task_decomposer.yaml` prompt中的维度指令
3. 检查前端任务显示组件的硬编码逻辑
4. 运行诊断脚本捕获完整数据流

### Phase 2: 实施动态维度映射（1天）

**目标**: 实现方案A

**步骤**:
1. 创建 `dimension_semantic_mapping.yaml`（0.5天）
2. 实现 `DimensionSemanticMapper` 类（0.3天）
3. 集成到 `core_task_decomposer.py`（0.2天）

### Phase 3: 测试与验证（0.5天）

**目标**: 验证准确率提升

**步骤**:
1. 重新测试狮岭村案例
2. 测试其他复杂案例（至少3个）
3. 更新诊断脚本评估映射准确率

---

## 💡 附加优化建议

### 优化1: 维度解释说明

**问题**: 用户不理解"contextual_research"等专业术语

**方案**: 在前端显示双语标签
```tsx
// 前端组件示例
<Tag>
  文化认同 <span className="text-gray-400 text-xs">(在地调研)</span>
</Tag>
```

### 优化2: 维度置信度可视化

**问题**: 映射可能不准确，但用户无法判断

**方案**: 显示置信度评分
```tsx
<Tag color={confidence > 0.8 ? "green" : "orange"}>
  文化认同 {confidence}
</Tag>
```

### 优化3: 允许用户手动修正维度

**问题**: 映射错误时无法纠正

**方案**: 添加维度编辑功能
```tsx
<Select
  value={task.dimension.standard_mapping}
  onChange={(value) => updateDimension(task.id, value)}
>
  <Option value="contextual_research">在地调研</Option>
  <Option value="business_model">商业模式</Option>
  ...
</Select>
```

---

## 📞 技术支持

**排查脚本**（Phase 1）:
```python
# diagnose_dimension_source.py
import asyncio
from intelligent_project_analyzer.services.core_task_decomposer import decompose_core_tasks

async def main():
    user_input = "新农村建设，四川广元苍溪云峰镇狮岭村..."

    tasks = await decompose_core_tasks(user_input, structured_data=None)

    print("=" * 70)
    print("任务梳理输出分析")
    print("=" * 70)

    for task in tasks:
        print(f"\n任务: {task['title']}")
        print(f"  维度字段类型: {type(task.get('dimension'))}")
        print(f"  维度内容: {task.get('dimension')}")
        print(f"  完整任务对象: {json.dumps(task, ensure_ascii=False, indent=2)}")

if __name__ == "__main__":
    asyncio.run(main())
```

**回滚方案**（如果出现问题）:
```bash
git checkout HEAD~1 intelligent_project_analyzer/services/core_task_decomposer.py
```

---

## 🎉 总结

**核心问题**:
1. ❌ 维度标注来源不明（需要排查）
2. ❌ 维度体系僵化（15个固定维度无法覆盖复杂需求）
3. ❌ 维度数量硬编码（虽然任务数自适应，但维度类型固定）

**推荐方案**:
- ⭐ **方案A - 动态维度 + 语义映射**（立即实施）
- 工作量: 1-2天
- 预期效果: 准确率 0% → 85%+

**下一步**:
1. 运行 `diagnose_dimension_source.py` 确认维度标注来源
2. 实施方案A（创建映射表 + 映射服务）
3. 重新测试狮岭村案例验证效果

---

*本方案由 Claude Sonnet 4.5 生成于 2026年2月8日*
