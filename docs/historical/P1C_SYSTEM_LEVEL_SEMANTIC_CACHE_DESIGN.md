# P1-C 系统级语义缓存设计方案

**版本**: v7.626
**日期**: 2025-02-26
**类型**: 系统级基础设施

---

## 🎯 设计理念

语义缓存不应该是某个Agent节点的局部优化，而应该是**系统级的基础设施**，为所有LLM调用提供透明的缓存层。

---

## 🏗️ 架构设计

### 当前问题

❌ **错误做法**：在requirements_analyst_agent.py的Phase2节点手动集成
```python
# ❌ 不好的做法：每个节点都要手动添加缓存逻辑
async def phase2_node(state):
    cached = await semantic_cache.get(user_input)  # 手动检查
    if cached:
        return cached
    result = await llm.invoke(...)
    await semantic_cache.set(user_input, result)  # 手动存储
    return result
```

**问题**：
- 侵入性强，每个节点都要修改
- 容易遗漏，新节点可能忘记添加
- 维护困难，缓存逻辑分散在各处
- 不符合关注点分离原则

---

### 正确做法：系统级拦截

✅ **系统级缓存层**：在LLM调用层面统一拦截

```
┌─────────────────────────────────────────────────────┐
│                   Application Layer                  │
│  (requirements_analyst, task_decomposer, etc.)      │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│              Semantic Cache Middleware               │
│  • 自动拦截所有LLM调用                                │
│  • 透明缓存，应用层无感知                             │
│  • 统一管理缓存策略                                   │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│                   LLM Service Layer                  │
│              (OpenAI, Anthropic, etc.)              │
└─────────────────────────────────────────────────────┘
```

---

## 🔧 技术实现

### 方案1: LLM Factory包装器（推荐）

在`llm_factory.py`中统一包装所有LLM实例：

```python
# intelligent_project_analyzer/services/llm_factory.py

from langchain_core.language_models import BaseChatModel
from .semantic_cache import SemanticCache

class CachedLLMWrapper(BaseChatModel):
    """
    LLM包装器，自动添加语义缓存

    对应用层完全透明，所有LLM调用自动享受缓存
    """

    def __init__(self, llm: BaseChatModel, cache: SemanticCache):
        self.llm = llm
        self.cache = cache

    async def ainvoke(self, messages, **kwargs):
        """异步调用，自动缓存"""

        # 1. 构建缓存键（基于messages内容）
        cache_key = self._build_cache_key(messages)

        # 2. 尝试从缓存获取
        cached_result = await self.cache.get(cache_key)
        if cached_result is not None:
            output, similarity = cached_result
            logger.info(f"[CACHE HIT] similarity={similarity:.4f}")
            return output

        # 3. 缓存未命中，调用实际LLM
        logger.info("[CACHE MISS] Calling LLM...")
        result = await self.llm.ainvoke(messages, **kwargs)

        # 4. 存入缓存
        await self.cache.set(cache_key, result)

        return result

    def _build_cache_key(self, messages):
        """构建缓存键"""
        # 提取所有消息内容
        content_parts = []
        for msg in messages:
            if hasattr(msg, 'content'):
                content_parts.append(msg.content)
        return "\n".join(content_parts)


def create_llm(model_name: str, **kwargs) -> BaseChatModel:
    """
    LLM工厂函数（修改版）

    自动为所有LLM添加语义缓存层
    """

    # 1. 创建原始LLM
    if model_name.startswith("gpt"):
        base_llm = ChatOpenAI(model=model_name, **kwargs)
    elif model_name.startswith("claude"):
        base_llm = ChatAnthropic(model=model_name, **kwargs)
    else:
        raise ValueError(f"Unknown model: {model_name}")

    # 2. 包装缓存层
    cache = SemanticCache(
        similarity_threshold=0.90,
        ttl=604800,  # 7天
    )

    cached_llm = CachedLLMWrapper(base_llm, cache)

    logger.info(f"[LLM Factory] Created {model_name} with semantic cache")

    return cached_llm
```

**优势**：
- ✅ 零侵入：应用层代码无需修改
- ✅ 全覆盖：所有LLM调用自动缓存
- ✅ 易维护：缓存逻辑集中在一处
- ✅ 可配置：统一管理缓存策略

---

### 方案2: LangChain Cache集成

使用LangChain内置的缓存机制：

```python
# intelligent_project_analyzer/services/llm_factory.py

from langchain.globals import set_llm_cache
from langchain.cache import RedisSemanticCache
from langchain_openai import OpenAIEmbeddings

def initialize_semantic_cache():
    """
    初始化系统级语义缓存

    在应用启动时调用一次
    """

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    cache = RedisSemanticCache(
        redis_url="redis://localhost:6379",
        embedding=embeddings,
        score_threshold=0.90,  # 相似度阈值
    )

    # 设置全局缓存
    set_llm_cache(cache)

    logger.info("[System] Semantic cache initialized globally")


# 在 server.py 启动时调用
@app.on_event("startup")
async def startup_event():
    initialize_semantic_cache()
    logger.info("Application started with semantic cache")
```

**优势**：
- ✅ 原生支持：使用LangChain官方API
- ✅ 零侵入：完全透明
- ✅ 成熟稳定：经过大量生产验证

**劣势**：
- ⚠️ 需要Redis Stack（支持向量搜索）
- ⚠️ 灵活性较低（阈值等配置受限）

---

## 📊 缓存策略

### 缓存粒度

**推荐**：基于完整的messages内容

```python
# 缓存键构建
cache_key = hash([
    system_prompt,
    user_input,
    few_shot_examples,
    # ... 所有影响输出的输入
])
```

**不推荐**：仅基于user_input
- 问题：相同user_input但不同system_prompt会错误命中

---

### 缓存范围

**全局缓存**（推荐）：
- 所有LLM调用共享缓存
- 跨Agent、跨节点复用
- 最大化缓存命中率

**分层缓存**（可选）：
```python
# 不同类型的LLM调用使用不同的缓存命名空间
cache_namespace = {
    "requirements_analyst": "ra_cache:",
    "task_decomposer": "td_cache:",
    "search_query": "sq_cache:",
}
```

---

### 缓存失效策略

1. **TTL失效**（主要）
   - 默认7天自动过期
   - 防止缓存无限增长

2. **版本失效**（可选）
   ```python
   cache_key = f"v{PROMPT_VERSION}:{content_hash}"
   # Prompt更新时自动失效旧缓存
   ```

3. **手动清理**（管理）
   ```python
   # 管理员接口
   @app.post("/admin/cache/clear")
   async def clear_cache(namespace: str = None):
       await semantic_cache.clear(namespace)
   ```

---

## 🎯 实施步骤

### Phase 1: 基础设施（本周）

1. **完善semantic_cache.py**
   - [x] 基础功能已实现
   - [ ] 添加命名空间支持
   - [ ] 添加统计监控接口
   - [ ] 添加管理接口（清理、查询）

2. **修改llm_factory.py**
   - [ ] 实现CachedLLMWrapper
   - [ ] 修改create_llm()函数
   - [ ] 添加缓存开关配置

3. **配置管理**
   ```yaml
   # config/SYSTEM_CONFIG.yaml
   semantic_cache:
     enabled: true
     similarity_threshold: 0.90
     ttl: 604800  # 7天
     redis_url: "redis://localhost:6379"
     namespace_prefix: "semantic_cache:"
   ```

### Phase 2: 测试验证（本周）

4. **单元测试**
   - [ ] 测试CachedLLMWrapper
   - [ ] 测试缓存命中/未命中
   - [ ] 测试命名空间隔离

5. **集成测试**
   - [ ] 测试requirements_analyst自动缓存
   - [ ] 测试task_decomposer自动缓存
   - [ ] 验证缓存命中率

### Phase 3: 生产部署（下周）

6. **监控仪表盘**
   ```python
   @app.get("/admin/cache/stats")
   async def cache_stats():
       return {
           "total_requests": 1000,
           "cache_hits": 450,
           "cache_misses": 550,
           "hit_rate": 0.45,
           "avg_similarity": 0.92,
           "cache_size": 120,
           "cost_saved": "$45.00",
       }
   ```

7. **性能监控**
   - [ ] 监控命中率（目标40-60%）
   - [ ] 监控响应时间（命中<1s）
   - [ ] 监控成本节省

---

## 📈 预期收益

### 系统级 vs 节点级对比

| 指标 | 节点级缓存 | 系统级缓存 |
|------|----------|----------|
| **覆盖范围** | 单个节点 | 所有LLM调用 |
| **命中率** | 20-30% | 40-60% |
| **维护成本** | 高（分散） | 低（集中） |
| **侵入性** | 高 | 零 |
| **可扩展性** | 差 | 优秀 |

### 成本节省

**场景**：每天100次LLM调用，50%命中率

| 项目 | 无缓存 | 系统级缓存 | 节省 |
|------|--------|----------|------|
| LLM调用次数 | 100 | 50 | 50% |
| 月度成本 | $400 | $200 | $200 |
| 年度成本 | $4,800 | $2,400 | $2,400 |

---

## 🔒 风险管理

### 风险1: 缓存污染

**问题**：错误的缓存结果影响后续请求

**缓解**：
- 高相似度阈值（0.90）
- 定期审查缓存质量
- 提供手动清理接口

### 风险2: 缓存穿透

**问题**：大量相似但不同的请求导致缓存无效

**缓解**：
- 监控命中率，动态调整阈值
- 使用布隆过滤器预判

### 风险3: 内存/存储压力

**问题**：缓存数据量过大

**缓解**：
- 7天TTL自动过期
- 监控缓存大小，设置上限
- LRU淘汰策略

---

## ✅ 验收标准

### 功能验收

- [ ] 所有LLM调用自动享受缓存（零侵入）
- [ ] 命中率达到40-60%
- [ ] 命中响应时间<1s
- [ ] 支持命名空间隔离

### 性能验收

- [ ] 成本节省≥40%
- [ ] 缓存查询延迟<100ms
- [ ] 系统整体响应时间提升≥30%

### 监控验收

- [ ] 实时命中率监控
- [ ] 成本节省统计
- [ ] 缓存大小监控
- [ ] 相似度分布分析

---

## 📚 参考资料

### LangChain缓存文档
- https://python.langchain.com/docs/modules/model_io/llms/llm_caching

### Redis向量搜索
- https://redis.io/docs/stack/search/reference/vectors/

### 语义缓存最佳实践
- https://www.anthropic.com/research/semantic-caching

---

## 🎓 总结

**核心原则**：
1. **系统级设计**：缓存是基础设施，不是业务逻辑
2. **零侵入**：应用层无需修改，完全透明
3. **统一管理**：集中配置、监控、维护
4. **可观测性**：完善的监控和统计

**实施优先级**：
- P0: 实现CachedLLMWrapper（本周）
- P1: 集成到llm_factory（本周）
- P2: 监控仪表盘（下周）
- P3: 高级特性（命名空间、版本管理）

---

**设计负责人**: Claude Code
**审核状态**: 待审核
**实施状态**: 设计完成，待实施
