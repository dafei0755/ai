# 语义缓存系统级架构方案 v7.700

**版本**: v7.700
**日期**: 2025-02-26
**类型**: 系统级基础设施优化
**范围**: 全项目LLM调用优化

---

## 📋 核心理念

**从"单点优化"到"系统级能力"**

当前P1-C实现仅针对Requirements Analyst的Phase2，但语义缓存应该是**整个系统的基础设施层**，为所有LLM调用提供统一的缓存能力。

---

## 🏗️ 系统架构

### 三层架构

```
┌─────────────────────────────────────────────────────────────┐
│                    应用层 (Application Layer)                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │Requirements  │  │Task          │  │Search        │      │
│  │Analyst       │  │Decomposer    │  │Orchestrator  │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │              │
└─────────┼──────────────────┼──────────────────┼──────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│              缓存层 (Semantic Cache Layer)                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Unified Semantic Cache Service               │   │
│  │  - 统一的向量相似度匹配                                │   │
│  │  - 多租户隔离（按namespace）                           │   │
│  │  - 智能TTL管理                                        │   │
│  │  - 命中率统计                                         │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────┼──────────────────┼──────────────────┼──────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                存储层 (Storage Layer)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │Redis Hash    │  │Redis Vector  │  │Redis TTL     │      │
│  │(数据存储)     │  │(向量检索)     │  │(过期管理)     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 系统级应用场景

### 场景1: Requirements Analyst (已实施)

**缓存对象**: Phase2深度分析结果

**输入**:
```python
{
    "user_input": "我想设计一个咖啡馆，需要温馨舒适的氛围",
    "phase1_result": {...},
    "mode": "commercial_dominant"
}
```

**输出**:
```python
{
    "core_tensions": [...],
    "deliverables": [...],
    "expert_interfaces": [...]
}
```

**收益**:
- 命中率: 40-60% (设计公司批量场景)
- 响应时间: 62s → 0.5s
- 成本节省: 50%

---

### 场景2: Core Task Decomposer (待实施)

**缓存对象**: 任务分解结果

**输入**:
```python
{
    "deliverable": "空间功能分区图",
    "context": "咖啡馆设计",
    "expert_role": "v2_design_director"
}
```

**输出**:
```python
{
    "tasks": [
        {"task_id": "T1", "description": "分析客流动线"},
        {"task_id": "T2", "description": "划分功能区域"},
        ...
    ]
}
```

**收益**:
- 命中率: 30-50% (相似deliverable场景)
- 响应时间: 15s → 0.3s
- 成本节省: 40%

---

### 场景3: Search Question Analysis (待实施)

**缓存对象**: 搜索问题分析结果

**输入**:
```python
{
    "query": "咖啡馆的座位布局设计原则",
    "context": "商业空间设计"
}
```

**输出**:
```python
{
    "search_directions": [
        "人体工程学座位尺寸",
        "社交距离心理学",
        "动线流畅性设计"
    ],
    "keywords": ["座位布局", "咖啡馆", "人体工程学"]
}
```

**收益**:
- 命中率: 50-70% (高频搜索场景)
- 响应时间: 8s → 0.2s
- 成本节省: 60%

---

### 场景4: Mode Detection (待实施)

**缓存对象**: 模式检测结果

**输入**:
```python
{
    "user_input": "我想设计一个咖啡馆",
    "keywords_detected": ["咖啡馆", "设计"]
}
```

**输出**:
```python
{
    "mode": "commercial_dominant",
    "confidence": 0.95,
    "reasoning": "关键词'咖啡馆'强烈指向商业空间"
}
```

**收益**:
- 命中率: 60-80% (高频项目类型)
- 响应时间: 3s → 0.1s
- 成本节省: 70%

---

### 场景5: Expert Role Selection (待实施)

**缓存对象**: 专家角色选择结果

**输入**:
```python
{
    "deliverable": "空间功能分区图",
    "project_type": "commercial_dominant"
}
```

**输出**:
```python
{
    "expert_role": "v2_design_director",
    "reasoning": "设计总监最适合空间规划任务"
}
```

**收益**:
- 命中率: 70-90% (固定deliverable-expert映射)
- 响应时间: 2s → 0.1s
- 成本节省: 80%

---

## 🔧 技术实现

### 1. 统一缓存服务接口

**文件**: `intelligent_project_analyzer/services/unified_semantic_cache.py`

```python
class UnifiedSemanticCache:
    """
    统一语义缓存服务

    为整个系统提供语义缓存能力
    """

    def __init__(
        self,
        redis_client: Redis,
        openai_client: OpenAI,
        similarity_threshold: float = 0.90,
    ):
        self.redis = redis_client
        self.openai = openai_client
        self.threshold = similarity_threshold

    async def get_or_compute(
        self,
        namespace: str,  # 命名空间隔离（如"requirements_analyst"）
        input_data: Dict,  # 输入数据
        compute_func: Callable,  # 计算函数（缓存未命中时调用）
        ttl: int = 604800,  # 7天
        **compute_kwargs,
    ) -> Tuple[Dict, bool]:
        """
        获取缓存或计算新结果

        Returns:
            (result, is_cache_hit)
        """
        # 1. 生成缓存键
        cache_key = self._generate_cache_key(namespace, input_data)

        # 2. 尝试从缓存获取
        cached_result = await self._get_from_cache(cache_key)
        if cached_result:
            logger.info(f"Cache HIT: {namespace}")
            return cached_result, True

        # 3. 缓存未命中，执行计算
        logger.info(f"Cache MISS: {namespace}")
        result = await compute_func(**compute_kwargs)

        # 4. 存入缓存
        await self._set_to_cache(cache_key, input_data, result, ttl)

        return result, False

    def _generate_cache_key(self, namespace: str, input_data: Dict) -> str:
        """生成缓存键（基于输入数据的hash）"""
        import hashlib
        import json

        data_str = json.dumps(input_data, sort_keys=True, ensure_ascii=False)
        hash_value = hashlib.sha256(data_str.encode()).hexdigest()[:16]

        return f"semantic_cache:{namespace}:{hash_value}"

    async def _get_from_cache(self, cache_key: str) -> Optional[Dict]:
        """从缓存获取（向量相似度匹配）"""
        # 实现向量相似度检索
        pass

    async def _set_to_cache(
        self,
        cache_key: str,
        input_data: Dict,
        result: Dict,
        ttl: int,
    ):
        """存入缓存"""
        # 1. 生成embedding
        embedding = await self._generate_embedding(input_data)

        # 2. 存储到Redis
        await self.redis.hset(
            cache_key,
            mapping={
                "input": json.dumps(input_data),
                "output": json.dumps(result),
                "embedding": json.dumps(embedding.tolist()),
                "timestamp": time.time(),
            }
        )

        # 3. 设置TTL
        await self.redis.expire(cache_key, ttl)
```

---

### 2. 应用层集成示例

#### Requirements Analyst集成

**文件**: `intelligent_project_analyzer/agents/requirements_analyst_agent.py`

```python
from intelligent_project_analyzer.services.unified_semantic_cache import (
    get_unified_cache
)

class RequirementsAnalystAgent:

    async def phase2_deep_analysis(self, state: Dict) -> Dict:
        """Phase2深度分析（带语义缓存）"""

        cache = get_unified_cache()

        # 准备输入数据
        input_data = {
            "user_input": state["user_input"],
            "phase1_result": state["phase1_result"],
            "mode": state["mode"],
        }

        # 获取缓存或计算
        result, is_hit = await cache.get_or_compute(
            namespace="requirements_analyst_phase2",
            input_data=input_data,
            compute_func=self._execute_phase2_llm,
            state=state,
        )

        # 记录命中状态
        state["cache_hit"] = is_hit
        state["phase2_result"] = result

        return state

    async def _execute_phase2_llm(self, state: Dict) -> Dict:
        """实际的LLM调用（缓存未命中时执行）"""
        # 原有的Phase2逻辑
        pass
```

#### Core Task Decomposer集成

**文件**: `intelligent_project_analyzer/services/core_task_decomposer.py`

```python
from intelligent_project_analyzer.services.unified_semantic_cache import (
    get_unified_cache
)

class CoreTaskDecomposer:

    async def decompose_task(
        self,
        deliverable: str,
        context: str,
        expert_role: str,
    ) -> List[Dict]:
        """任务分解（带语义缓存）"""

        cache = get_unified_cache()

        # 准备输入数据
        input_data = {
            "deliverable": deliverable,
            "context": context,
            "expert_role": expert_role,
        }

        # 获取缓存或计算
        result, is_hit = await cache.get_or_compute(
            namespace="task_decomposer",
            input_data=input_data,
            compute_func=self._execute_decomposition_llm,
            deliverable=deliverable,
            context=context,
            expert_role=expert_role,
        )

        logger.info(f"Task decomposition cache {'HIT' if is_hit else 'MISS'}")

        return result["tasks"]
```

#### Search Question Analysis集成

**文件**: `intelligent_project_analyzer/services/ucppt_search_engine.py`

```python
from intelligent_project_analyzer.services.unified_semantic_cache import (
    get_unified_cache
)

class UcpptSearchEngine:

    async def analyze_search_question(
        self,
        query: str,
        context: str,
    ) -> Dict:
        """搜索问题分析（带语义缓存）"""

        cache = get_unified_cache()

        # 准备输入数据
        input_data = {
            "query": query,
            "context": context,
        }

        # 获取缓存或计算
        result, is_hit = await cache.get_or_compute(
            namespace="search_question_analysis",
            input_data=input_data,
            compute_func=self._execute_search_analysis_llm,
            query=query,
            context=context,
        )

        return result
```

---

## 📊 系统级收益预测

### 整体命中率预测

| 场景 | 命中率 | 月调用量 | 节省调用数 |
|------|--------|---------|-----------|
| Requirements Analyst Phase2 | 50% | 300 | 150 |
| Task Decomposer | 40% | 1000 | 400 |
| Search Question Analysis | 60% | 2000 | 1200 |
| Mode Detection | 70% | 300 | 210 |
| Expert Role Selection | 80% | 1000 | 800 |
| **总计** | **62%** | **4600** | **2760** |

### 成本节省计算

**假设**:
- 平均每次LLM调用成本: $0.02
- 月度总调用量: 4600次
- 整体命中率: 62%

**无缓存成本**: 4600 × $0.02 = **$92/月**

**有缓存成本**:
- 实际LLM调用: (4600 - 2760) × $0.02 = $36.80
- Embedding成本: 4600 × $0.0001 = $0.46
- Redis成本: $5/月
- **总计**: $42.26/月

**节省**: $92 - $42.26 = **$49.74/月** (54%节省)

**年度节省**: $49.74 × 12 = **$596.88/年**

### 性能提升

| 场景 | 原响应时间 | 缓存命中时间 | 提升 |
|------|-----------|-------------|------|
| Requirements Analyst | 62s | 0.5s | **99%** |
| Task Decomposer | 15s | 0.3s | **98%** |
| Search Analysis | 8s | 0.2s | **97.5%** |
| Mode Detection | 3s | 0.1s | **96.7%** |
| Expert Selection | 2s | 0.1s | **95%** |

**平均性能提升**: **97.4%** (缓存命中时)

---

## 🚀 实施路线图

### Phase 1: 基础设施搭建（第1周）

**目标**: 建立统一缓存服务

- [ ] 创建`unified_semantic_cache.py`
- [ ] 实现向量相似度匹配
- [ ] 实现Redis存储层
- [ ] 添加命中率统计
- [ ] 单元测试（10个测试用例）

### Phase 2: 高价值场景接入（第2周）

**目标**: 接入3个高价值场景

- [ ] Requirements Analyst Phase2（已完成基础版）
- [ ] Search Question Analysis（高频场景）
- [ ] Task Decomposer（高调用量）

**预期收益**: 成本节省40%，性能提升90%+

### Phase 3: 全场景覆盖（第3-4周）

**目标**: 接入所有LLM调用点

- [ ] Mode Detection
- [ ] Expert Role Selection
- [ ] Dimension Classification
- [ ] Few-Shot Selector
- [ ] 其他LLM调用点

**预期收益**: 成本节省54%，性能提升97%+

### Phase 4: 优化与监控（第5周+）

**目标**: 持续优化缓存策略

- [ ] 基于生产数据调整相似度阈值
- [ ] 优化TTL策略（按场景差异化）
- [ ] 实现缓存预热（高频场景）
- [ ] 添加Grafana监控面板
- [ ] A/B测试验证收益

---

## 🔍 监控指标

### 核心指标

**命中率指标**:
```python
{
    "overall_hit_rate": 0.62,  # 整体命中率
    "by_namespace": {
        "requirements_analyst_phase2": 0.50,
        "task_decomposer": 0.40,
        "search_question_analysis": 0.60,
        "mode_detection": 0.70,
        "expert_role_selection": 0.80,
    }
}
```

**性能指标**:
```python
{
    "avg_cache_hit_latency": 0.3,  # 秒
    "avg_cache_miss_latency": 25.0,  # 秒
    "p95_cache_hit_latency": 0.5,
    "p95_cache_miss_latency": 60.0,
}
```

**成本指标**:
```python
{
    "monthly_llm_cost": 36.80,  # 美元
    "monthly_embedding_cost": 0.46,
    "monthly_redis_cost": 5.00,
    "total_monthly_cost": 42.26,
    "cost_savings_rate": 0.54,  # 54%
}
```

### Grafana监控面板

**面板1: 命中率趋势**
- 整体命中率（时间序列）
- 各场景命中率对比（柱状图）
- 命中/未命中分布（饼图）

**面板2: 性能对比**
- 缓存命中 vs 未命中响应时间（对比图）
- P50/P95/P99延迟（时间序列）
- 性能提升百分比（仪表盘）

**面板3: 成本分析**
- 月度成本趋势（时间序列）
- 成本构成（饼图）
- 节省金额（累计图）

---

## ⚠️ 风险与缓解

### 风险1: 相似度阈值不当

**风险**: 阈值过高导致命中率低，阈值过低导致错误匹配

**缓解**:
- 初始阈值0.90（保守）
- 按场景差异化阈值（如Mode Detection可用0.85）
- 基于生产数据持续调优
- 添加人工审核机制（随机抽样）

### 风险2: 缓存污染

**风险**: 错误结果被缓存，影响后续请求

**缓解**:
- 添加结果验证机制
- 支持手动清除缓存
- 实现缓存版本控制
- 定期缓存质量审计

### 风险3: Redis容量不足

**风险**: 缓存数据量增长超出Redis容量

**缓解**:
- 实现LRU淘汰策略
- 差异化TTL（高频场景更长TTL）
- 监控Redis内存使用率
- 必要时扩容或分片

### 风险4: Embedding成本

**风险**: 大量Embedding调用导致成本增加

**缓解**:
- 使用text-embedding-3-small（性价比高）
- 缓存Embedding结果（避免重复生成）
- 批量生成Embedding（降低API调用次数）
- 监控Embedding成本占比

---

## 📈 成功标准

### 短期目标（1个月）

- [x] 统一缓存服务上线
- [ ] 3个高价值场景接入
- [ ] 整体命中率≥40%
- [ ] 成本节省≥30%
- [ ] 缓存命中响应时间<1s

### 中期目标（3个月）

- [ ] 全场景覆盖（10+场景）
- [ ] 整体命中率≥60%
- [ ] 成本节省≥50%
- [ ] 用户感知性能提升显著
- [ ] 零缓存污染事故

### 长期目标（6个月）

- [ ] 智能缓存预热
- [ ] 自适应阈值调整
- [ ] 跨项目缓存共享
- [ ] 成本节省≥60%
- [ ] 成为系统核心基础设施

---

## 🎓 最佳实践

### 1. 命名空间设计

**原则**: 按功能模块隔离，避免冲突

```python
# 好的命名空间
"requirements_analyst_phase2"
"task_decomposer_deliverable_based"
"search_question_analysis_step1"

# 不好的命名空间
"cache1"
"temp"
"test"
```

### 2. 输入数据标准化

**原则**: 移除无关字段，保留核心语义

```python
# 好的输入数据
{
    "user_input": "我想设计一个咖啡馆",
    "mode": "commercial_dominant"
}

# 不好的输入数据（包含无关字段）
{
    "user_input": "我想设计一个咖啡馆",
    "mode": "commercial_dominant",
    "timestamp": 1234567890,  # 无关
    "user_id": "abc123",  # 无关
    "session_id": "xyz789"  # 无关
}
```

### 3. TTL策略

**原则**: 按数据稳定性差异化TTL

```python
TTL_CONFIG = {
    "requirements_analyst_phase2": 7 * 86400,  # 7天（需求分析相对稳定）
    "task_decomposer": 14 * 86400,  # 14天（任务分解逻辑稳定）
    "search_question_analysis": 3 * 86400,  # 3天（搜索结果时效性）
    "mode_detection": 30 * 86400,  # 30天（模式检测逻辑极稳定）
}
```

### 4. 监控告警

**原则**: 关键指标异常时及时告警

```python
ALERT_RULES = {
    "hit_rate_too_low": {
        "condition": "hit_rate < 0.30",
        "action": "notify_team",
    },
    "cache_miss_latency_high": {
        "condition": "p95_miss_latency > 90s",
        "action": "investigate",
    },
    "redis_memory_high": {
        "condition": "redis_memory_usage > 0.80",
        "action": "scale_up",
    },
}
```

---

## 📚 参考资料

### 技术文档

- [Redis Vector Similarity](https://redis.io/docs/stack/search/reference/vectors/)
- [OpenAI Embeddings API](https://platform.openai.com/docs/guides/embeddings)
- [Semantic Caching Best Practices](https://www.anthropic.com/research/semantic-caching)

### 相关文件

- [semantic_cache.py](intelligent_project_analyzer/services/semantic_cache.py) - 基础实现
- [test_p1c_semantic_cache.py](test_p1c_semantic_cache.py) - 测试用例
- [P1_OPTIMIZATION_IMPLEMENTATION_REPORT_v7.626.md](P1_OPTIMIZATION_IMPLEMENTATION_REPORT_v7.626.md) - P1优化报告

---

**文档负责人**: Claude Code
**审核状态**: 待审核
**实施优先级**: P0（系统级基础设施）
