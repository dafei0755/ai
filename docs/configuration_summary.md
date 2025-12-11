# 配置总结 - OpenRouter 专用模式

## ✅ 已完成的配置更改

### 1. 禁用自动降级

**文件**: `.env`

```bash
# 🔄 自动降级开关
# 🔧 v7.4.2: 已禁用自动降级，只使用 OpenRouter + 多 Key 负载均衡
LLM_AUTO_FALLBACK=false
```

**效果**:
- ✅ 系统只使用 OpenRouter，不会自动切换到其他提供商
- ✅ 避免不确定性，确保所有请求都通过 OpenRouter
- ✅ 简化调试和监控

### 2. 配置 OpenRouter 多 Key 负载均衡

**文件**: `.env`

```bash
# LLM 提供商
LLM_PROVIDER=openrouter

# 多 Key 配置
OPENROUTER_API_KEYS=your_openrouter_api_key_here

# 负载均衡策略
OPENROUTER_LOAD_BALANCE_STRATEGY=round_robin

# 模型
OPENROUTER_MODEL=openai/gpt-4o-2024-11-20
```

### 3. 更新 LLM 工厂逻辑

**文件**: `intelligent_project_analyzer/services/llm_factory.py`

**新增逻辑**:
```python
# 1. 检查是否使用 OpenRouter 且配置了多个 Keys
if primary_provider == "openrouter":
    openrouter_keys = os.getenv("OPENROUTER_API_KEYS", "")
    if openrouter_keys and "," in openrouter_keys:
        # 自动启用负载均衡
        return LLMFactory.create_openrouter_balanced_llm(**kwargs)

# 2. 如果禁用自动降级，直接使用原始方法
if not auto_fallback:
    logger.info(f"📌 自动降级已禁用，只使用 {primary_provider}")
    return LLMFactory._create_llm_original(config, **kwargs)
```

---

## 🎯 当前系统行为

### 场景 1: 单个 OpenRouter Key（当前状态）

**配置**:
```bash
LLM_PROVIDER=openrouter
LLM_AUTO_FALLBACK=false
OPENROUTER_API_KEYS=single_key_here
```

**行为**:
1. 系统检测到只有 1 个 Key
2. 直接使用该 Key，不启用负载均衡
3. 不会降级到其他提供商
4. 失败时会重试 3 次（指数退避）

**日志输出**:
```
📌 自动降级已禁用，只使用 openrouter
创建LLM实例: model=openai/gpt-4o-2024-11-20, max_tokens=32000
```

### 场景 2: 多个 OpenRouter Keys（推荐）

**配置**:
```bash
LLM_PROVIDER=openrouter
LLM_AUTO_FALLBACK=false
OPENROUTER_API_KEYS=key1,key2,key3
```

**行为**:
1. 系统检测到多个 Keys
2. 自动启用负载均衡
3. 按照配置的策略（round_robin）轮询使用
4. 自动健康检查和故障转移
5. 不会降级到其他提供商

**日志输出**:
```
🔄 检测到多个 OpenRouter Keys，启用负载均衡
✅ OpenRouter 负载均衡器初始化完成: 3 个 API Keys
📊 负载均衡策略: round_robin
🔄 最大重试次数: 3
```

---

## 📊 功能对比

| 功能 | 旧配置（自动降级） | 新配置（OpenRouter 专用） |
|------|-------------------|-------------------------|
| 主提供商 | OpenRouter | OpenRouter |
| 自动降级 | ✅ 启用 | ❌ 禁用 |
| 多 Key 负载均衡 | ❌ 不支持 | ✅ 支持 |
| 故障转移 | 切换到其他提供商 | 切换到其他 Key |
| 行为确定性 | ❌ 不确定 | ✅ 确定 |
| 调试难度 | 较高 | 较低 |
| 稳定性 | 依赖多个提供商 | 依赖多个 Keys |

---

## 🔧 如何添加更多 Keys

### 步骤 1: 获取多个 OpenRouter API Keys

1. 访问 https://openrouter.ai/
2. 注册 2-4 个账户（使用不同邮箱）
3. 每个账户获取 API Key

### 步骤 2: 更新 .env 配置

```bash
# 将多个 Keys 用逗号分隔（不要有空格）
OPENROUTER_API_KEYS=sk-or-v1-key1,sk-or-v1-key2,sk-or-v1-key3
```

### 步骤 3: 重启服务

```bash
# 重启后端
python -m uvicorn intelligent_project_analyzer.api.server:app --reload
```

### 步骤 4: 验证配置

```python
from intelligent_project_analyzer.services.llm_factory import LLMFactory

# 创建 LLM
llm = LLMFactory.create_llm()

# 测试调用
response = llm.invoke("Hello")
print(response.content)
```

---

## 📝 配置文件位置

| 文件 | 路径 | 说明 |
|------|------|------|
| 环境变量 | `.env` | 主配置文件 |
| LLM 工厂 | `intelligent_project_analyzer/services/llm_factory.py` | LLM 创建逻辑 |
| 负载均衡器 | `intelligent_project_analyzer/services/openrouter_load_balancer.py` | 负载均衡实现 |
| 配置指南 | `docs/openrouter_setup_guide.md` | 详细配置说明 |
| 使用指南 | `docs/openrouter_load_balancer_guide.md` | 功能说明 |

---

## ⚠️ 重要提示

### 1. 当前状态

- ✅ 自动降级已禁用
- ✅ 只使用 OpenRouter
- ⚠️ 目前只有 1 个 Key（建议添加更多）

### 2. 建议操作

1. **添加 2-4 个额外的 OpenRouter Keys**
   - 提高稳定性
   - 突破单 Key 速率限制
   - 自动故障转移

2. **监控使用情况**
   ```python
   from intelligent_project_analyzer.services.openrouter_load_balancer import get_global_balancer

   balancer = get_global_balancer()
   balancer.print_stats()
   ```

3. **定期检查余额**
   - 确保每个账户都有足够的余额
   - 避免因余额不足导致服务中断

### 3. 故障排查

如果遇到问题：

1. **检查日志**
   ```bash
   tail -f logs/api.log
   ```

2. **验证配置**
   ```bash
   python -c "import os; print(os.getenv('OPENROUTER_API_KEYS'))"
   ```

3. **测试连接**
   ```bash
   python examples/openrouter_load_balancer_example.py
   ```

---

## 🎓 最佳实践

1. **使用 3-5 个 Keys**: 平衡成本和稳定性
2. **不同账户**: 使用不同账户的 Keys 以突破速率限制
3. **定期监控**: 定期查看统计信息，及时发现问题
4. **合理充值**: 确保每个账户都有足够的余额
5. **备份配置**: 保存好所有 API Keys，避免丢失
6. **安全存储**: 不要将 Keys 提交到版本控制

---

## 📚 相关文档

- [OpenRouter 配置指南](openrouter_setup_guide.md)
- [负载均衡使用指南](openrouter_load_balancer_guide.md)
- [示例代码](../examples/openrouter_load_balancer_example.py)
- [测试文件](../tests/test_openrouter_load_balancer.py)

---

## 📞 技术支持

如有问题，请查看：
1. 日志文件: `logs/api.log`
2. 配置文件: `.env`
3. 文档: `docs/` 目录

---

**配置已完成！系统现在只使用 OpenRouter，不会自动降级到其他提供商。** 🎉
