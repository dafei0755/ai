# P2: 混合生成策略（LLM+规则补充）设计文档

**版本**: v7.995
**日期**: 2026-02-14
**优先级**: P2 (任务分解优化)
**状态**: 🔧 设计中

---

## 📋 背景

### 当前状态（降级策略）
```python
# core_task_decomposer.py - decompose_core_tasks()
try:
    tasks = await llm.ainvoke(...)  # LLM生成
    if not tasks:
        tasks = _simple_fallback_decompose(...)  # 失败时降级
except Exception:
    tasks = _simple_fallback_decompose(...)  # 异常时降级
```

**问题诊断**:
1. ❌ **二选一逻辑**: LLM成功=100%LLM,LLM失败=100%规则
2. ❌ **规则被动**: 只在LLM失败时启用,未充分利用
3. ❌ **结构化数据浪费**: project_features 高分特征未被强制利用
4. ❌ **无互补性**: LLM和规则是替代关系,而非协作关系

---

## 🎯 P2目标

### 核心价值
**从"降级备份"到"协同增强"**

| 维度 | 当前(降级) | P2(混合) |
|------|-----------|----------|
| **生成模式** | 二选一 | 并行生成 |
| **LLM角色** | 主力(80%) | 创意+综合(60%) |
| **规则角色** | 备份(20%) | 关键保障(40%) |
| **结构化数据** | LLM输入 | 规则强制生成 |
| **任务质量** | 不稳定 | 基线保障+创意加成 |

### 量化目标
- ✅ **关键任务覆盖率**: 从75% → **≥95%** (+27%)
- ✅ **特征对齐度**: 从60% →**≥85%** (+42%)
- ✅ **任务多样性**: +30% (LLM创意 + 规则结构)
- ✅ **系统鲁棒性**: LLM部分失败不影响核心任务生成

---

## 🏗️ 架构设计

### 1. 整体流程

```
用户输入 + 结构化数据 (structured_data)
         ↓
    [复杂度分析]
  TaskComplexityAnalyzer
         ↓
  推荐任务数: 5-20个
         ↓
    ┌─────────┴─────────┐
    ↓                   ↓
[Track A: LLM生成]   [Track B: 规则生成]
┌─────────────────┐  ┌──────────────────┐
│ Few-shot Prompt │  │ 基于高分特征      │
│ + 质量标准      │  │ + 结构化数据      │
│ + 特征向量指导  │  │ + 关键词匹配      │
└────────┬────────┘  └────────┬──────────┘
         ↓                   ↓
    LLM任务 (10-15个)    规则任务 (3-6个)
    [创意+综合型]        [关键+强制型]
         ↓                   ↓
         └─────────┬─────────┘
                   ↓
          [智能融合器]
      HybridTaskMerger
                   ↓
          ┌────────┴────────┐
          ↓                 ↓
      [去重合并]        [优先级排序]
      相似度>0.85       规则优先保留
          ↓                 ↓
          └────────┬─────────┘
                   ↓
          [质量验证]
      _validate_task_granularity
                   ↓
          [最终任务列表]
        8-18个高质量任务
```

---

### 2. 核心组件

#### (1) Track A: LLM生成器 (增强版)
**文件**: `core_task_decomposer.py::_generate_tasks_with_llm()`

**输入**:
- user_input
- structured_data
- project_features (v7.960特征向量)
- task_count_range: (min, max)

**增强点**:
```python
# ✅ 明确告知LLM: "规则系统会补充关键任务,你专注创意和综合"
prompt_hint = """
注意: 本系统同时运行规则生成器,将自动补充以下关键任务:
- 基于高分特征的强制任务 (如cultural≥0.8 → "文化元素提炼")
- 基于张力对的核心任务 (如"开放"vs"私密")

你的职责:
1. 生成创意性、综合性任务(如"叙事节奏构建","材料系统策略")
2. 填补规则无法覆盖的语义任务
3. 目标数量: {llm_task_count}个
"""
```

**输出**: `List[Dict]` (LLM任务,10-15个)

---

#### (2) Track B: 规则生成器 (强制版)
**文件**: `core_task_decomposer.py::_generate_rule_based_tasks()`

**输入**:
- user_input
- structured_data
- project_features (关键)
- task_count_range: (3-6个,固定)

**生成策略** (改进版 `_simple_fallback_decompose`):

##### 策略 1: 特征驱动强制生成 (新增)
```python
# 🆕 根据 project_features 高分维度强制生成任务
def _generate_feature_driven_tasks(project_features: Dict[str, float]) -> List[Dict]:
    """
    基于特征向量高分维度强制生成关键任务

    示例:
    - cultural: 0.85 → "文化背景深度调研" (强制)
    - commercial: 0.78 → "商业定位与ROI分析" (强制)
    - aesthetic: 0.72 → "美学流派研究" (强制)
    """
    forced_tasks = []

    # 特征阈值: ≥0.7 = 高分特征,强制生成
    HIGH_SCORE_THRESHOLD = 0.7

    # 特征 → 任务映射表
    FEATURE_TASK_MAP = {
        'cultural': {
            'title': '文化背景与元素提炼',
            'description': '深度调研项目相关的文化历史背景、传统工艺、地域特色,提炼可转译的文化符号和空间原型',
            'keywords': ['文化', '历史', '传统', '在地'],
            'task_type': 'research',
            'priority': 'high'
        },
        'commercial': {
            'title': '商业模式与盈利策略',
            'description': '分析目标客群、竞争格局、商业定位,建立ROI测算模型,制定可行的盈利路径',
            'keywords': ['商业', '盈利', '客群', 'ROI'],
            'task_type': 'analysis',
            'priority': 'high'
        },
        'aesthetic': {
            'title': '美学流派与氛围营造',
            'description': '研究相关美学流派、视觉语言、材料质感、光影策略,建立项目美学体系',
            'keywords': ['美学', '氛围', '视觉', '材料'],
            'task_type': 'research',
            'priority': 'high'
        },
        'technical': {
            'title': '技术系统与创新工艺',
            'description': '调研智能系统、节能技术、施工创新工艺,评估技术可行性与成本效益',
            'keywords': ['技术', '系统', '工艺', '创新'],
            'task_type': 'research',
            'priority': 'high'
        },
        'sustainable': {
            'title': '可持续策略与生态评估',
            'description': '研究绿色建筑标准、可再生能源、材料循环策略,建立生态评估框架',
            'keywords': ['可持续', '绿色', '生态', '能源'],
            'task_type': 'research',
            'priority': 'high'
        },
        'wellness': {
            'title': '健康建筑与疗愈空间',
            'description': '调研WELL标准、健康建筑设计要点、疗愈机制,制定健康空间策略',
            'keywords': ['健康', '疗愈', 'WELL', '舒适'],
            'task_type': 'research',
            'priority': 'high'
        },
        'social': {
            'title': '社会关系与行为模式',
            'description': '分析目标人群的社会结构、权力关系、行为模式,建立社会建模框架',
            'keywords': ['社会', '关系', '行为', '社区'],
            'task_type': 'analysis',
            'priority': 'high'
        },
        # 更多特征映射...
    }

    for feature_id, score in project_features.items():
        if score >= HIGH_SCORE_THRESHOLD and feature_id in FEATURE_TASK_MAP:
            task_template = FEATURE_TASK_MAP[feature_id]
            forced_tasks.append({
                'id': f'task_feature_{feature_id}',
                'title': task_template['title'],
                'description': task_template['description'],
                'source_keywords': task_template['keywords'],
                'task_type': task_template['task_type'],
                'priority': task_template['priority'],
                'source': 'rule_feature_driven',  # 标记来源
                'feature_score': score  # 记录特征分数
            })

    return forced_tasks
```

##### 策略 2: 结构化数据提取 (保留优化)
```python
# ✅ 保留现有的 design_challenge, character_narrative 提取逻辑
# 优化: 增加source标记
tasks.append({
    ...
    'source': 'rule_structured_data',  # 标记来源
    'extraction_method': 'design_challenge_tension'  # 记录提取方法
})
```

##### 策略 3: 关键词匹配 (保留)
```python
# ✅ 保留对标、文化、客群等关键词匹配
# 优化: 降低优先级(避免与LLM重复)
tasks.append({
    ...
    'source': 'rule_keyword_match',
    'priority': 'medium'  # 从high降为medium
})
```

**输出**: `List[Dict]` (规则任务,3-6个,强制保留)

---

#### (3) 智能融合器
**文件**: `core_task_decomposer.py::_merge_hybrid_tasks()`

**算法**:
```python
def _merge_hybrid_tasks(
    llm_tasks: List[Dict],
    rule_tasks: List[Dict],
    max_tasks: int
) -> List[Dict]:
    """
    融合LLM任务和规则任务,去重并优先级排序

    策略:
    1. 规则任务强制保留(关键任务保障)
    2. LLM任务与规则任务去重(相似度>0.85)
    3. 保留LLM独有任务(创意补充)
    4. 总数不超过max_tasks
    """
    merged = []

    # Step 1: 规则任务全部保留
    merged.extend(rule_tasks)
    logger.info(f"✅ [Merge] 保留 {len(rule_tasks)} 个规则强制任务")

    # Step 2: LLM任务去重后加入
    for llm_task in llm_tasks:
        # 检查与规则任务的相似度
        is_duplicate = False
        for rule_task in rule_tasks:
            similarity = _calculate_task_similarity(llm_task, rule_task)
            if similarity > 0.85:
                logger.debug(f"⚠️ [Merge] LLM任务 '{llm_task['title']}' "
                           f"与规则任务 '{rule_task['title']}' 重复 (相似度={similarity:.2f})")
                is_duplicate = True
                break

        if not is_duplicate:
            merged.append(llm_task)

    logger.info(f"✅ [Merge] 新增 {len(merged) - len(rule_tasks)} 个LLM独有任务")

    # Step 3: 优先级排序
    merged = _sort_tasks_by_priority(merged)

    # Step 4: 数量截断
    if len(merged) > max_tasks:
        logger.warning(f"⚠️ [Merge] 任务总数 {len(merged)} 超过上限 {max_tasks},智能截断")
        # 优先保留: high priority + 规则来源
        high_priority = [t for t in merged if t['priority'] == 'high']
        rule_source = [t for t in merged if 'rule_' in t.get('source', '')]
        others = [t for t in merged if t['priority'] != 'high' and 'rule_' not in t.get('source', '')]

        # 合并去重
        priority_tasks = {t['id']: t for t in high_priority + rule_source}.values()
        merged = list(priority_tasks) + others
        merged = merged[:max_tasks]

    logger.info(f"🎯 [Merge] 最终任务数: {len(merged)}")
    return merged


def _calculate_task_similarity(task1: Dict, task2: Dict) -> float:
    """
    计算两个任务的相似度(基于标题和关键词)

    Returns:
        相似度分数 0.0-1.0
    """
    from difflib import SequenceMatcher

    # 标题相似度 (权重60%)
    title_sim = SequenceMatcher(None, task1['title'], task2['title']).ratio()

    # 关键词重叠度 (权重40%)
    keywords1 = set(task1.get('source_keywords', []))
    keywords2 = set(task2.get('source_keywords', []))

    if keywords1 or keywords2:
        keyword_sim = len(keywords1 & keywords2) / max(len(keywords1 | keywords2), 1)
    else:
        keyword_sim = 0.0

    return 0.6 * title_sim + 0.4 * keyword_sim
```

---

## 📂 文件修改清单

### 1. core_task_decomposer.py
**修改位置**: Line 780-900 (主函数 `decompose_core_tasks`)

#### 修改前 (v7.110.0):
```python
async def decompose_core_tasks(...):
    try:
        # LLM生成
        response = await llm.ainvoke(messages)
        tasks = decomposer.parse_response(response_text)

        if not tasks:
            # 降级: 规则生成
            tasks = _simple_fallback_decompose(...)
    except Exception as e:
        # 异常: 规则生成
        tasks = _simple_fallback_decompose(...)
```

#### 修改后 (v7.995 P2):
```python
async def decompose_core_tasks_hybrid(...):
    """
    🆕 v7.995 P2: 混合生成策略 (LLM + 规则并行)
    """
    # Step 1: 分配任务数量
    llm_task_count = int(recommended_max * 0.65)  # LLM负责65%
    rule_task_count = max(3, int(recommended_max * 0.35))  # 规则负责35%,最少3个

    # Step 2: 并行生成
    try:
        # Track A: LLM生成
        llm_tasks = await _generate_tasks_with_llm(
            user_input, structured_data, project_features,
            task_count=llm_task_count
        )
    except Exception as e:
        logger.warning(f"⚠️ [Hybrid] LLM生成失败: {e}, LLM任务=空")
        llm_tasks = []

    # Track B: 规则生成 (并行,不依赖LLM结果)
    rule_tasks = _generate_rule_based_tasks(
        user_input, structured_data, project_features,
        task_count=rule_task_count
    )

    logger.info(f"📊 [Hybrid] LLM任务={len(llm_tasks)}, 规则任务={len(rule_tasks)}")

    # Step 3: 智能融合
    merged_tasks = _merge_hybrid_tasks(llm_tasks, rule_tasks, max_tasks=recommended_max)

    # Step 4: 质量验证 (保留)
    if merged_tasks:
        is_valid, errors = _validate_task_granularity(merged_tasks, project_features)
        if not is_valid:
            logger.warning(f"⚠️ [Hybrid] 任务质量验证失败: {len(errors)}个问题")

    return merged_tasks
```

---

### 2. 新增函数

#### (1) `_generate_tasks_with_llm()` - LLM生成器 (拆分)
```python
async def _generate_tasks_with_llm(
    user_input: str,
    structured_data: Optional[Dict[str, Any]],
    project_features: Optional[Dict[str, float]],
    task_count: int
) -> List[Dict[str, Any]]:
    """
    使用LLM生成创意性和综合性任务

    Args:
        task_count: 目标任务数(由混合策略分配)

    Returns:
        LLM生成的任务列表
    """
    # ... (原decompose_core_tasks中的LLM调用逻辑)
```

#### (2) `_generate_rule_based_tasks()` - 规则生成器 (重构)
```python
def _generate_rule_based_tasks(
    user_input: str,
    structured_data: Optional[Dict[str, Any]],
    project_features: Optional[Dict[str, float]],
    task_count: int = 5
) -> List[Dict[str, Any]]:
    """
    基于规则生成关键强制任务

    策略:
    1. 特征驱动: project_features高分特征 (≥0.7) → 强制生成任务
    2. 结构化提取: design_challenge, character_narrative
    3. 关键词匹配: 对标、文化、客群等

    Returns:
        规则生成的任务列表 (带source标记)
    """
    tasks = []

    # 策略1: 特征驱动 (新增)
    if project_features:
        feature_tasks = _generate_feature_driven_tasks(project_features)
        tasks.extend(feature_tasks)

    # 策略2+3: 原_simple_fallback_decompose逻辑 (保留)
    tasks.extend(_extract_structured_data_tasks(user_input, structured_data))
    tasks.extend(_extract_keyword_tasks(user_input))

    # 限制数量
    tasks = tasks[:task_count]

    return tasks
```

#### (3) `_generate_feature_driven_tasks()` - 特征驱动生成 (新增)
```python
def _generate_feature_driven_tasks(
    project_features: Dict[str, float]
) -> List[Dict[str, Any]]:
    """
    根据高分特征强制生成关键任务

    示例:
    - cultural: 0.85 → "文化背景深度调研"
    - commercial: 0.78 → "商业模式与ROI分析"
    """
    # 见上文"策略1"详细实现
```

#### (4) `_merge_hybrid_tasks()` - 融合器 (新增)
```python
def _merge_hybrid_tasks(
    llm_tasks: List[Dict],
    rule_tasks: List[Dict],
    max_tasks: int
) -> List[Dict]:
    """
    融合LLM和规则任务,去重并排序
    """
    # 见上文"智能融合器"详细实现
```

#### (5) `_calculate_task_similarity()` - 相似度计算 (新增)
```python
def _calculate_task_similarity(task1: Dict, task2: Dict) -> float:
    """
    基于标题和关键词计算任务相似度
    """
    # 见上文详细实现
```

---

## 🧪 测试计划

### 测试文件: `test_v7_995_p2_hybrid_generation.py`

```python
"""
v7.995 P2混合生成策略测试
"""
import asyncio
from intelligent_project_analyzer.services.core_task_decomposer import (
    decompose_core_tasks_hybrid,
    _generate_rule_based_tasks,
    _generate_feature_driven_tasks,
    _merge_hybrid_tasks
)

async def test_hybrid_generation():
    """测试完整混合生成流程"""
    user_input = """
    为文化酒店案例设计,融合传统书法文化与现代奢华体验,
    打造精神地标。需参考安藤忠雄、隈研吾等大师的文化转译策略。
    """

    structured_data = {
        'design_challenge': '"文化深度"与"商业高端"的平衡',
        'project_task': '文化酒店概念设计',
        'project_features': {
            'cultural': 0.88,
            'aesthetic': 0.76,
            'commercial': 0.72,
            'functional': 0.45,
            'technical': 0.38
        }
    }

    tasks = await decompose_core_tasks_hybrid(
        user_input=user_input,
        structured_data=structured_data
    )

    # 验证
    assert len(tasks) >= 8, "任务数量不足"

    # 检查规则任务是否保留
    rule_tasks = [t for t in tasks if 'rule_' in t.get('source', '')]
    assert len(rule_tasks) >= 3, "规则任务未保留"

    # 检查高分特征任务
    feature_titles = [t['title'] for t in tasks]
    assert any('文化' in t for t in feature_titles), "cultural特征任务缺失"
    assert any('商业' in t for t in feature_titles), "commercial特征任务缺失"

    print(f"✅ 混合生成测试通过: {len(tasks)}个任务")
    for i, t in enumerate(tasks, 1):
        source = t.get('source', 'unknown')
        print(f"  {i}. [{source}] {t['title']}")


def test_feature_driven_generation():
    """测试特征驱动生成"""
    project_features = {
        'cultural': 0.88,
        'commercial': 0.72,
        'wellness': 0.68,  # 低于阈值,不生成
        'technical': 0.45
    }

    tasks = _generate_feature_driven_tasks(project_features)

    # 验证
    assert len(tasks) == 2, f"应生成2个任务,实际{len(tasks)}"
    assert any('文化' in t['title'] for t in tasks), "文化任务缺失"
    assert any('商业' in t['title'] for t in tasks), "商业任务缺失"

    print(f"✅ 特征驱动测试通过: {len(tasks)}个任务")


def test_task_deduplication():
    """测试去重逻辑"""
    llm_tasks = [
        {'id': 'llm_1', 'title': '文化背景调研', 'source_keywords': ['文化', '历史']},
        {'id': 'llm_2', 'title': '叙事节奏构建', 'source_keywords': ['叙事', '空间']},
    ]

    rule_tasks = [
        {'id': 'rule_1', 'title': '文化背景与元素提炼', 'source_keywords': ['文化', '传统'], 'priority': 'high'},
    ]

    merged = _merge_hybrid_tasks(llm_tasks, rule_tasks, max_tasks=10)

    # 验证: llm_1应被去重,llm_2应保留
    assert len(merged) == 2, f"去重失败,实际{len(merged)}个任务"
    assert any(t['id'] == 'rule_1' for t in merged), "规则任务未保留"
    assert any(t['id'] == 'llm_2' for t in merged), "LLM独有任务未保留"
    assert not any(t['id'] == 'llm_1' for t in merged), "重复任务未去除"

    print("✅ 去重测试通过")


if __name__ == '__main__':
    # 运行测试
    asyncio.run(test_hybrid_generation())
    test_feature_driven_generation()
    test_task_deduplication()

    print("\n🎉 P2混合生成策略测试全部通过!")
```

---

## 📊 预期效果

### 案例1: 文化酒店项目

**输入**:
- user_input: "书法文化酒店,融合传统与奢华,参考安藤忠雄..."
- project_features: `{'cultural': 0.88, 'aesthetic': 0.76, 'commercial': 0.72}`

**P2混合生成结果** (预期13个任务):

#### Track A: LLM生成 (8个)
1. 安藤忠雄建筑哲学与精神性空间研究
2. 隈研吾负建筑理念与材料创新研究
3. 书法艺术在空间叙事中的转译策略
4. 高端酒店客群生活方式与审美偏好分析
5. 奢华与克制的空间平衡策略
6. 光影系统与情绪营造策略
7. 材料系统：传统工艺与现代质感融合
8. 品牌叙事与精神地标构建策略

#### Track B: 规则生成 (6个)
1. **[特征驱动] 文化背景与元素提炼** ← cultural=0.88强制生成
2. **[特征驱动] 美学流派与氛围营造** ← aesthetic=0.76强制生成
3. **[特征驱动] 商业模式与盈利策略** ← commercial=0.72强制生成
4. **[结构化] "文化深度"与"商业高端"的平衡策略研究** ← design_challenge提取
5. **[关键词] 对标案例深度研究** ← "参考安藤忠雄"匹配
6. **[关键词] 书法文化洞察与提炼** ← "书法文化"匹配

#### 融合去重后 (最终13个):
- 保留规则任务1-6 (关键任务保障)
- 去除LLM任务5 (与规则任务4重复)
- 保留LLM任务1-4, 6-8 (创意补充)

**关键任务覆盖率**: 100% ✅
- ✅ 文化特征任务 (规则强制)
- ✅ 商业特征任务 (规则强制)
- ✅ 核心张力任务 (规则强制)
- ✅ 大师研究任务 (LLM创意)
- ✅ 叙事策略任务 (LLM创意)

---

### 案例2: LLM部分失败场景

**假设**: LLM只返回4个任务 (网络波动/token限制)

**P2表现**:
```
Track A (LLM): 4个任务 ← 生成不足
Track B (规则): 6个任务 ← 正常生成
融合后: 10个任务 (4 LLM + 6 规则)
```

**关键任务覆盖率**: ≥95% ✅ (规则任务保障)

**对比当前降级策略**:
- 当前: LLM成功但不足 → 不触发fallback → 只有4个任务 ❌
- P2: LLM不足 + 规则补充 → 10个任务 ✅

---

## ⚠️ 注意事项

### 1. 性能影响
- **LLM调用时间**: 不变 (仍然是1次异步调用)
- **规则生成时间**: +50ms (轻量级规则计算)
- **融合去重时间**: +20ms (O(n²)相似度计算)
- **总增加**: ~70ms (相对LLM的3-8秒,可忽略)

### 2. 成本影响
- **LLM tokens**: 可减少10-15% (因为任务数从15→10个LLM任务)
- **规则计算**: 零成本 (本地计算)
- **总体**: 成本略降 ✅

### 3. 兼容性
- **向后兼容**: 完全兼容
- **可降级**: LLM完全失败时 → 纯规则模式 (等同当前fallback)
- **配置开关**: 可通过环境变量控制 `USE_HYBRID_GENERATION=true`

---

## 🚀 实施步骤

### Phase 1: 核心实现 (2-3小时)
1. ✅ 设计文档完成 (本文档)
2. ⏳ 实现 `_generate_feature_driven_tasks()`
3. ⏳ 实现 `_merge_hybrid_tasks()`
4. ⏳ 重构 `decompose_core_tasks()` → `decompose_core_tasks_hybrid()`

### Phase 2: 测试验证 (1-2小时)
5. ⏳ 创建 `test_v7_995_p2_hybrid_generation.py`
6. ⏳ 运行3个核心测试用例
7. ⏳ 对比P2 vs 当前策略效果

### Phase 3: 集成与文档 (1小时)
8. ⏳ 更新 `progressive_questionnaire.py` 调用逻辑
9. ⏳ 创建 `P2_HYBRID_GENERATION_IMPLEMENTATION_REPORT.md`
10. ⏳ 更新 CHANGELOG.md

---

## 📚 参考文档

- [IMPLEMENTATION_REPORT_v7.970.md](./IMPLEMENTATION_REPORT_v7.970.md) - P2混合策略原型
- [P1_COMPLETION_REPORT_v7.990.md](./P1_COMPLETION_REPORT_v7.990.md) - v7.990架构基础
- [INTELLIGENT_TASK_DECOMPOSITION_STRATEGY_SYSTEM_v7_950.md](./INTELLIGENT_TASK_DECOMPOSITION_STRATEGY_SYSTEM_v7_950.md) - 任务分解策略系统

---

**状态**: 🔧 设计完成,待实施
**下一步**: 开始Phase 1实现
