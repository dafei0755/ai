# OpenRouter 多 Key 负载均衡使用指南

## 📋 概述

OpenRouter 负载均衡器提供了多个 API Key 的自动负载均衡、健康检查和故障转移功能，显著提高 API 调用的稳定性和吞吐量。

## ✨ 核心特性

### 1. 多 Key 负载均衡
- **轮询策略** (Round Robin): 按顺序轮流使用每个 Key
- **随机策略** (Random): 随机选择一个 Key
- **最少使用策略** (Least Used): 优先使用请求次数最少的 Key

### 2. 自动健康检查
- 实时监控每个 Key 的健康状态
- 连续失败达到阈值后自动标记为不健康
- 冷却期后自动恢复健康状态

### 3. 故障转移
- 自动跳过不健康的 Keys
- 失败后自动切换到其他 Key 重试
- 支持自定义重试次数和延迟

### 4. 速率限制保护
- 每个 Key 独立的速率限制追踪
- 达到限制后自动切换到其他 Key
- 可配置的速率限制窗口

### 5. 使用统计
- 实时统计每个 Key 的使用情况
- 成功率、失败率监控
- 详细的错误日志

---

## 🚀 快速开始

### 1. 配置多个 API Keys

在 `.env` 文件中配置多个 OpenRouter API Keys（逗号分隔）：

```bash
# 方式 1: 配置多个 Keys（推荐）
OPENROUTER_API_KEYS=sk-or-v1-xxx1,sk-or-v1-xxx2,sk-or-v1-xxx3

# 方式 2: 单个 Key（向后兼容）
OPENROUTER_API_KEY=sk-or-v1-xxx
```

### 2. 基本使用

```python
from intelligent_project_analyzer.services.llm_factory import LLMFactory

# 创建负载均衡的 LLM 实例
llm = LLMFactory.create_openrouter_balanced_llm()

# 使用 LLM
response = llm.invoke("你好，请介绍一下你自己")
print(response.content)
```

### 3. 自定义配置

```python
from intelligent_project_analyzer.services.llm_factory import LLMFactory

# 使用随机策略
llm = LLMFactory.create_openrouter_balanced_llm(
    model="openai/gpt-4o-2024-11-20",
    strategy="random",  # round_robin | random | least_used
    temperature=0.7,
    max_tokens=4000
)
```

---

## 📖 详细使用

### 直接使用负载均衡器

```python
from intelligent_project_analyzer.services.openrouter_load_balancer import (
    OpenRouterLoadBalancer,
    LoadBalancerConfig
)

# 1. 创建配置
config = LoadBalancerConfig(
    strategy="round_robin",          # 负载均衡策略
    max_retries=3,                   # 最大重试次数
    retry_delay=2,                   # 重试延迟（秒）
    max_consecutive_failures=3,      # 最大连续失败次数
    failure_cooldown=600,            # 失败冷却时间（秒）
    rate_limit_per_key=100,          # 每个 Key 每分钟最大请求数
    health_check_interval=300        # 健康检查间隔（秒）
)

# 2. 创建负载均衡器
balancer = OpenRouterLoadBalancer(
    config=config,
    model="openai/gpt-4o-2024-11-20",
    temperature=0.7,
    max_tokens=4000
)

# 3. 获取 LLM 实例
llm = balancer.get_llm()

# 4. 使用 LLM
response = llm.invoke("Hello, world!")
```

### 使用重试机制

```python
# 使用内置的重试机制
response = balancer.invoke_with_retry(
    "请分析这个设计项目...",
    temperature=0.8
)
```

### 查看统计信息

```python
# 获取统计摘要
summary = balancer.get_stats_summary()
print(f"总请求数: {summary['total_requests']}")
print(f"成功率: {summary['overall_success_rate']:.2%}")

# 打印详细统计
balancer.print_stats()
```

输出示例：
```
============================================================
📊 OpenRouter 负载均衡器统计
============================================================
总 Keys: 3
健康 Keys: 3
不健康 Keys: 0
总请求数: 150
成功请求: 148
失败请求: 2
总成功率: 98.67%
------------------------------------------------------------
✅ Key sk-or-v1: 50 请求, 100.00% 成功率
✅ Key sk-or-v2: 50 请求, 98.00% 成功率
   最后错误: Rate limit exceeded
✅ Key sk-or-v3: 50 请求, 98.00% 成功率
============================================================
```

---

## 🎯 负载均衡策略

### 1. 轮询策略 (Round Robin)

**适用场景**: 所有 Keys 性能相近，需要均匀分配负载

```python
llm = LLMFactory.create_openrouter_balanced_llm(strategy="round_robin")
```

**特点**:
- 按顺序轮流使用每个 Key
- 负载分配最均匀
- 可预测的使用模式

### 2. 随机策略 (Random)

**适用场景**: 需要避免可预测的使用模式

```python
llm = LLMFactory.create_openrouter_balanced_llm(strategy="random")
```

**特点**:
- 随机选择 Key
- 负载分配相对均匀
- 不可预测的使用模式

### 3. 最少使用策略 (Least Used)

**适用场景**: Keys 性能差异较大，需要优先使用空闲的 Key

```python
llm = LLMFactory.create_openrouter_balanced_llm(strategy="least_used")
```

**特点**:
- 优先使用请求次数最少的 Key
- 自动平衡负载
- 适合长时间运行的服务

---

## 🔧 高级配置

### 自定义健康检查

```python
config = LoadBalancerConfig(
    max_consecutive_failures=5,      # 连续失败 5 次后标记为不健康
    failure_cooldown=1800,           # 30 分钟冷却期
    health_check_interval=600        # 每 10 分钟检查一次
)
```

### 自定义速率限制

```python
config = LoadBalancerConfig(
    rate_limit_per_key=200,          # 每个 Key 每分钟 200 次请求
    rate_limit_window=60             # 60 秒窗口
)
```

### 自定义重试策略

```python
config = LoadBalancerConfig(
    max_retries=5,                   # 最多重试 5 次
    retry_delay=3                    # 每次重试延迟 3 秒
)
```

---

## 🏗️ 在项目中集成

### 1. 更新 LLM 工厂配置

修改 `llm_factory.py` 中的默认创建方法：

```python
@staticmethod
def create_llm(config: Optional[LLMConfig] = None, **kwargs) -> ChatOpenAI:
    """创建 LLM 实例（默认使用负载均衡）"""

    # 检查是否配置了多个 OpenRouter Keys
    import os
    openrouter_keys = os.getenv("OPENROUTER_API_KEYS", "")

    if openrouter_keys and "," in openrouter_keys:
        # 使用负载均衡
        logger.info("🔄 检测到多个 OpenRouter Keys，启用负载均衡")
        return LLMFactory.create_openrouter_balanced_llm(**kwargs)
    else:
        # 使用原始方法
        return LLMFactory._create_llm_original(config, **kwargs)
```

### 2. 在 Agent 中使用

```python
from intelligent_project_analyzer.services.llm_factory import LLMFactory

class MyAgent:
    def __init__(self):
        # 使用负载均衡的 LLM
        self.llm = LLMFactory.create_openrouter_balanced_llm(
            temperature=0.7,
            max_tokens=4000
        )

    def analyze(self, input_text: str):
        response = self.llm.invoke(input_text)
        return response.content
```

### 3. 在 Workflow 中使用

```python
from intelligent_project_analyzer.services.openrouter_load_balancer import get_global_balancer

# 在 workflow 初始化时创建全局负载均衡器
balancer = get_global_balancer(
    model="openai/gpt-4o-2024-11-20",
    strategy="round_robin"
)

# 在各个节点中使用
def requirements_analyst_node(state):
    llm = balancer.get_llm()
    # ... 使用 llm
```

---

## 📊 监控和调试

### 启用详细日志

```python
import logging
from loguru import logger

# 设置日志级别
logger.add("openrouter_balancer.log", level="DEBUG")
```

### 实时监控

```python
import time

balancer = OpenRouterLoadBalancer()

# 定期打印统计
while True:
    balancer.print_stats()
    time.sleep(60)  # 每分钟打印一次
```

### 导出统计数据

```python
import json

summary = balancer.get_stats_summary()

# 保存为 JSON
with open("balancer_stats.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)
```

---

## ⚠️ 注意事项

### 1. API Key 安全

- **不要**将 API Keys 提交到版本控制
- 使用 `.env` 文件存储 Keys
- 确保 `.env` 在 `.gitignore` 中

### 2. 速率限制

- OpenRouter 有全局速率限制
- 多个 Keys 可以提高总吞吐量，但不能突破单个账户的限制
- 建议使用不同账户的 Keys

### 3. 成本控制

- 多个 Keys 会增加总成本
- 建议设置每个 Key 的使用上限
- 定期检查使用统计

### 4. 健康检查

- 健康检查会消耗少量请求
- 可以根据实际情况调整检查间隔
- 不健康的 Key 会自动恢复，无需手动干预

---

## 🐛 故障排查

### 问题 1: 所有 Keys 都不健康

**原因**: 可能是网络问题或 OpenRouter 服务异常

**解决方案**:
```python
# 手动重置所有 Keys 的健康状态
for stats in balancer.stats.values():
    stats.is_healthy = True
    stats.consecutive_failures = 0
```

### 问题 2: 某个 Key 频繁失败

**原因**: 该 Key 可能已达到配额或被限制

**解决方案**:
```python
# 临时禁用该 Key
balancer.stats["key_id"].is_healthy = False
```

### 问题 3: 负载不均衡

**原因**: 可能是策略选择不当

**解决方案**:
```python
# 切换到轮询策略
config = LoadBalancerConfig(strategy="round_robin")
balancer = OpenRouterLoadBalancer(config=config)
```

---

## 📚 API 参考

### OpenRouterLoadBalancer

```python
class OpenRouterLoadBalancer:
    def __init__(
        self,
        api_keys: Optional[List[str]] = None,
        config: Optional[LoadBalancerConfig] = None,
        model: str = "openai/gpt-4o-2024-11-20",
        **llm_kwargs
    )

    def get_llm(self, **override_kwargs) -> ChatOpenAI
    def invoke_with_retry(self, prompt: str, **kwargs) -> Any
    def get_stats_summary(self) -> Dict[str, Any]
    def print_stats(self)
```

### LoadBalancerConfig

```python
@dataclass
class LoadBalancerConfig:
    health_check_interval: int = 300
    max_consecutive_failures: int = 3
    failure_cooldown: int = 600
    strategy: str = "round_robin"
    max_retries: int = 3
    retry_delay: int = 2
    rate_limit_per_key: int = 100
    rate_limit_window: int = 60
```

---

## 🎓 最佳实践

1. **使用 3-5 个 Keys**: 平衡成本和稳定性
2. **选择合适的策略**: 大多数情况下轮询策略最优
3. **定期监控统计**: 及时发现问题
4. **设置合理的重试**: 避免过度重试导致延迟
5. **配置健康检查**: 根据实际情况调整参数
6. **使用全局单例**: 避免创建多个负载均衡器实例

---

## 📝 更新日志

### v7.4.2 (2025-12-11)
- ✨ 初始版本发布
- ✅ 支持多 Key 负载均衡
- ✅ 自动健康检查和故障转移
- ✅ 速率限制保护
- ✅ 使用统计和监控

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License
