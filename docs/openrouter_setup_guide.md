# OpenRouter 多 Key 配置指南

## 📋 配置说明

### 当前配置状态

你的 `.env` 文件已经更新，支持以下两种配置方式：

#### 方式 1: 多 Key 负载均衡（推荐）

```bash
# 配置多个 Keys（逗号分隔，不要有空格）
OPENROUTER_API_KEYS=key1,key2,key3
```

**优势**:
- ✅ 提高稳定性：单个 Key 失败不影响服务
- ✅ 突破速率限制：多个 Key 并行使用
- ✅ 自动故障转移：失败自动切换到其他 Key
- ✅ 负载均衡：请求分散到多个 Key

#### 方式 2: 单 Key（向后兼容）

```bash
# 单个 Key
OPENROUTER_API_KEY=your_key_here
```

**适用场景**:
- 只有一个 API Key
- 不需要负载均衡功能

---

## 🚀 如何获取多个 OpenRouter API Keys

### 选项 1: 使用多个账户（推荐）

1. **注册多个 OpenRouter 账户**
   - 访问 https://openrouter.ai/
   - 使用不同的邮箱注册 2-5 个账户
   - 每个账户充值一定金额

2. **获取 API Keys**
   - 登录每个账户
   - 访问 https://openrouter.ai/keys
   - 创建并复制 API Key

3. **配置到 .env**
   ```bash
   OPENROUTER_API_KEYS=sk-or-v1-account1-key,sk-or-v1-account2-key,sk-or-v1-account3-key
   ```

### 选项 2: 单账户多 Key（不推荐）

OpenRouter 允许单个账户创建多个 API Keys，但它们共享同一个速率限制，无法突破限制。

**不推荐原因**:
- ❌ 共享速率限制，无法提高吞吐量
- ❌ 一个账户被限制，所有 Keys 都受影响

---

## ⚙️ 配置步骤

### 步骤 1: 准备多个 API Keys

假设你有 3 个 OpenRouter API Keys：
```
your_openrouter_api_key_here
sk-or-v1-example-key-2
sk-or-v1-example-key-3
```

### 步骤 2: 更新 .env 文件

打开 `d:\11-20\langgraph-design\.env`，找到 OpenRouter 配置部分：

```bash
# 🆕 v7.4.2: 多 Key 负载均衡配置
# 方式 1: 配置多个 Keys（推荐，用于负载均衡）
# 格式: key1,key2,key3（逗号分隔，不要有空格）
OPENROUTER_API_KEYS=sk-or-v1-key1,sk-or-v1-key2,sk-or-v1-key3

# 负载均衡策略（可选）
# 可选值: round_robin（轮询）| random（随机）| least_used（最少使用）
OPENROUTER_LOAD_BALANCE_STRATEGY=round_robin

# 模型配置
OPENROUTER_MODEL=openai/gpt-4o-2024-11-20
```

**重要提示**:
- ⚠️ Keys 之间用**逗号**分隔
- ⚠️ **不要有空格**
- ⚠️ 确保每个 Key 都是有效的

### 步骤 3: 验证配置

运行测试脚本验证配置：

```bash
python examples/openrouter_load_balancer_example.py
```

或者运行单元测试：

```bash
python -m pytest tests/test_openrouter_load_balancer.py -v
```

---

## 🎯 负载均衡策略选择

### 1. 轮询策略 (round_robin) - 默认推荐

```bash
OPENROUTER_LOAD_BALANCE_STRATEGY=round_robin
```

**特点**:
- 按顺序轮流使用每个 Key
- 负载分配最均匀
- 可预测的使用模式

**适用场景**:
- 所有 Keys 性能相近
- 需要均匀分配负载
- 大多数情况下的最佳选择

### 2. 随机策略 (random)

```bash
OPENROUTER_LOAD_BALANCE_STRATEGY=random
```

**特点**:
- 随机选择 Key
- 负载分配相对均匀
- 不可预测的使用模式

**适用场景**:
- 需要避免可预测的使用模式
- 测试和开发环境

### 3. 最少使用策略 (least_used)

```bash
OPENROUTER_LOAD_BALANCE_STRATEGY=least_used
```

**特点**:
- 优先使用请求次数最少的 Key
- 自动平衡负载
- 适合长时间运行的服务

**适用场景**:
- Keys 性能差异较大
- 需要优先使用空闲的 Key
- 生产环境长期运行

---

## 📊 监控和统计

### 查看实时统计

```python
from intelligent_project_analyzer.services.openrouter_load_balancer import get_global_balancer

balancer = get_global_balancer()
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

## 🔧 高级配置

### 自定义健康检查参数

如果需要更精细的控制，可以在代码中自定义配置：

```python
from intelligent_project_analyzer.services.openrouter_load_balancer import (
    OpenRouterLoadBalancer,
    LoadBalancerConfig
)

config = LoadBalancerConfig(
    strategy="round_robin",
    max_retries=5,                   # 最大重试次数
    retry_delay=3,                   # 重试延迟（秒）
    max_consecutive_failures=5,      # 最大连续失败次数
    failure_cooldown=1800,           # 失败冷却时间（秒）
    rate_limit_per_key=200,          # 每个 Key 每分钟最大请求数
    health_check_interval=600        # 健康检查间隔（秒）
)

balancer = OpenRouterLoadBalancer(config=config)
```

---

## ⚠️ 常见问题

### Q1: 我只有一个 Key，能用负载均衡吗？

**A**: 可以，但没有负载均衡的效果。系统会自动检测到只有一个 Key，正常工作但不会有负载均衡的优势。

### Q2: 多个 Keys 会增加成本吗？

**A**: 是的，多个 Keys 意味着多个账户，总成本会增加。但可以提高稳定性和吞吐量。建议根据实际需求权衡。

### Q3: Keys 之间需要是同一个账户吗？

**A**: 不需要，推荐使用不同账户的 Keys，这样可以突破单账户的速率限制。

### Q4: 如何知道哪个 Key 失败了？

**A**: 查看日志或调用 `balancer.print_stats()` 可以看到每个 Key 的详细统计信息。

### Q5: Key 失败后会自动恢复吗？

**A**: 会的。系统会在冷却期（默认 10 分钟）后自动尝试恢复不健康的 Key。

### Q6: 可以动态添加或移除 Key 吗？

**A**: 当前版本不支持动态修改。需要修改 `.env` 文件并重启服务。

---

## 🎓 最佳实践

1. **使用 3-5 个 Keys**: 平衡成本和稳定性
2. **不同账户**: 使用不同账户的 Keys 以突破速率限制
3. **定期监控**: 定期查看统计信息，及时发现问题
4. **合理充值**: 确保每个账户都有足够的余额
5. **备份配置**: 保存好所有 API Keys，避免丢失
6. **安全存储**: 不要将 Keys 提交到版本控制

---

## 📞 技术支持

如有问题，请查看：
- [完整使用指南](openrouter_load_balancer_guide.md)
- [示例代码](../examples/openrouter_load_balancer_example.py)
- [测试文件](../tests/test_openrouter_load_balancer.py)

---

## 📝 配置检查清单

- [ ] 已获取 2-5 个 OpenRouter API Keys
- [ ] 已在 `.env` 中配置 `OPENROUTER_API_KEYS`
- [ ] Keys 之间用逗号分隔，无空格
- [ ] 已选择负载均衡策略（默认 round_robin）
- [ ] 已验证配置（运行测试脚本）
- [ ] 已查看统计信息确认正常工作

---

**配置完成后，系统将自动启用负载均衡功能！** 🎉
