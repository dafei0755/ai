# 集成测试覆盖扩展文档

> 测试覆盖扩展 - 关键路径集成测试与高频错误场景回归测试
>
> 创建日期: 2026-01-04
> 作者: Copilot AI Testing Assistant

---

## 📊 测试覆盖概览

本次扩展针对系统关键路径补充了端到端集成测试，并为前5个高频错误场景编写了回归测试。

### 新增测试文件

1. **图片生成端到端集成测试** - [tests/integration/test_image_generation_flow.py](../tests/integration/test_image_generation_flow.py)
2. **WebSocket推送集成测试** - [tests/integration/test_websocket_flow.py](../tests/integration/test_websocket_flow.py)
3. **数据库查询集成测试** - [tests/integration/test_redis_session_extended.py](../tests/integration/test_redis_session_extended.py)
4. **高频错误回归测试** - [tests/regression/test_high_frequency_bugs.py](../tests/regression/test_high_frequency_bugs.py)

---

## 🎯 关键路径集成测试

### 1. 图片生成端到端测试

**文件**: `tests/integration/test_image_generation_flow.py`

**覆盖流程**:
```
问卷数据 → ImageGeneratorService → OpenRouter API → 文件存储 → API返回
```

**测试场景**:
- ✅ 完整图片生成管道（正常流程）
- ✅ v7.122 图片Prompt单字符BUG回归测试
- ✅ API超时处理
- ✅ 配额耗尽降级处理
- ✅ 并发多图生成（v7.127）
- ✅ 基于问卷数据的图片生成（v7.121+）
- ✅ 网络错误重试机制
- ✅ 图片存储和检索流程
- ✅ 边缘场景：空prompt、超长prompt、无效宽高比

**运行命令**:
```bash
pytest tests/integration/test_image_generation_flow.py -v -m integration_critical
```

---

### 2. WebSocket推送集成测试

**文件**: `tests/integration/test_websocket_flow.py`

**覆盖流程**:
```
/ws端点 → broadcast_to_websockets() → 客户端接收
```

**测试场景**:
- ✅ WebSocket完整生命周期（连接→推送→断开）
- ✅ 状态更新广播
- ✅ 搜索引用推送（v7.120+ 数据流优化）
- ✅ v7.120-v7.131 连接状态检查缺失BUG回归测试
- ✅ 心跳保活机制
- ✅ Redis Pub/Sub多实例广播
- ✅ 多客户端广播
- ✅ WebSocket发送超时处理（v7.133+）
- ✅ 断开连接清理
- ✅ 错误处理
- ✅ 边缘场景：空消息、大消息、不存在的会话、并发广播

**运行命令**:
```bash
pytest tests/integration/test_websocket_flow.py -v -m integration_critical
```

---

### 3. 数据库查询集成测试

**文件**: `tests/integration/test_redis_session_extended.py`

**覆盖流程**:
```
API请求 → SessionManager → Redis/内存回退 → 数据返回
```

**测试场景**:
- ✅ v7.105/v7.118 Redis连接超时BUG回归测试
- ✅ 高并发会话更新（锁竞态条件）
- ✅ Redis故障内存回退
- ✅ 会话TTL过期清理
- ✅ 会话列表缓存失效机制（v7.105/v7.118）
- ✅ 大型会话数据（>1MB）性能测试
- ✅ 状态缓存机制（v7.105）
- ✅ 分布式锁并发获取
- ✅ Redis重试机制（Fix 1.3）
- ✅ 边缘场景：空会话数据、特殊字符、不存在的会话

**运行命令**:
```bash
pytest tests/integration/test_redis_session_extended.py -v -m integration_critical
```

---

## 🐛 高频错误回归测试

**文件**: `tests/regression/test_high_frequency_bugs.py`

### 前5个高频错误场景

#### 1. v7.122 图片Prompt单字符BUG
- **根因**: `visual_prompts[0]` 只取首字符，导致prompt变成 "M"
- **影响**: 生成的概念图与项目主题完全无关
- **修复**: 使用 `visual_prompts`（完整字符串）
- **测试**: `test_image_prompt_single_char_bug_v7_122()`

#### 2. v7.120-v7.131 WebSocket连接状态检查缺失
- **根因**: 发送消息前未检查 `ws.client_state == CONNECTED`
- **影响**: WebSocket发送失败，前端无法接收更新
- **修复**: 添加状态检查，跳过未连接的WebSocket
- **测试**: `test_websocket_connection_state_check_v7_120_131()`

#### 3. v7.105/v7.118 Redis连接超时/竞态条件
- **根因**:
  - socket_timeout过短(10秒)
  - 锁超时过短(30秒)
  - 缺少重试机制
- **修复**:
  - Fix 1.2: 锁超时增加到60秒
  - Fix 1.3: 操作超时增加到30秒
  - 启用 `retry_on_timeout=True`
  - v7.118: 缓存TTL增加到10分钟
- **测试**: `test_redis_timeout_retry_mechanism_v7_105_118()`

#### 4. v7.131 配置文件加载失败 (SearchFilterManager NoneType)
- **根因**: `yaml.safe_load()` 返回None时未检查，直接迭代导致TypeError
- **影响**: SearchFilterManager初始化失败
- **修复**: 添加默认配置兜底 + None检查
- **测试**: `test_config_loading_none_handling_v7_131()`

#### 5. v7.129 模块导入缺失 (os模块局部导入)
- **根因**: os模块在函数内部局部导入，可能被代码路径跳过
- **影响**: 运行时 `NameError: name 'os' is not defined`
- **修复**: 统一移到文件顶部import
- **测试**: `test_module_import_missing_v7_129()`

**运行命令**:
```bash
pytest tests/regression/test_high_frequency_bugs.py -v -m regression
```

---

## 🔧 测试运行器

### 集成测试运行脚本

**文件**: `scripts/run_integration_tests.py`

**使用方法**:
```bash
# 仅运行P0关键测试（CI快速验证）
python scripts/run_integration_tests.py --critical-only

# 运行所有集成测试（发布前全面验证）
python scripts/run_integration_tests.py --full

# 运行回归测试（防止BUG复现）
python scripts/run_integration_tests.py --regression

# 运行集成+回归测试
python scripts/run_integration_tests.py --all
```

**支持参数**:
- `--critical-only`: 仅P0关键测试
- `--full`: 所有集成测试
- `--regression`: 回归测试
- `--all`: 集成+回归
- `-v, --verbose`: 详细输出
- `--failfast`: 第一个失败后停止
- `--no-redis`: 跳过需要Redis的测试

---

## 📝 Pytest配置

### 新增Markers

在 `pytest.ini` 中新增：
- `integration_critical`: P0关键集成测试（必须通过）
- `regression`: 回归测试（防止历史BUG）

**使用示例**:
```bash
# 运行P0关键测试
pytest -m integration_critical

# 运行回归测试
pytest -m regression

# 运行集成测试
pytest -m integration

# 组合使用
pytest -m "integration_critical or regression"
```

---

## 🔄 CI/CD集成

### GitHub Actions配置

**文件**: `.github/workflows/integration-tests.yml`

**触发条件**:
- **每次PR**: 运行P0关键测试 + 回归测试
- **每天定时**: 运行完整集成测试（UTC 2:00 / 北京时间10:00）
- **手动触发**: 可运行完整集成测试

**Jobs概览**:

| Job名称 | 触发条件 | 超时时间 | 测试内容 |
|--------|---------|---------|---------|
| `critical-integration-tests` | 每次PR | 15分钟 | P0关键集成测试 |
| `regression-tests` | 每次PR | 10分钟 | 回归测试 |
| `full-integration-tests` | 定时/手动 | 30分钟 | 完整集成测试 |
| `websocket-integration-tests` | 每次PR | 10分钟 | WebSocket专项测试 |
| `image-generation-integration-tests` | 每次PR | 15分钟 | 图片生成专项测试 |
| `database-integration-tests` | 每次PR | 15分钟 | 数据库专项测试 |

**依赖服务**:
- Redis 7.x (用于会话管理和Pub/Sub测试)

**环境变量**:
- `REDIS_URL`: Redis连接地址
- `OPENROUTER_API_KEY`: Mock API密钥（测试环境使用mock）

---

## 📈 测试覆盖统计

### 代码覆盖率目标

| 模块 | 当前覆盖率 | 目标覆盖率 |
|-----|-----------|-----------|
| 图片生成 | ~60% | 85%+ |
| WebSocket推送 | ~50% | 80%+ |
| 数据库查询 | ~70% | 90%+ |
| 总体 | ~65% | 85%+ |

### 测试用例数量

- **集成测试**: 30+ 新增用例
- **回归测试**: 15+ 新增用例
- **总计**: 45+ 新增测试用例

---

## 🚀 快速开始

### 本地运行测试

1. **安装依赖**:
```bash
pip install -r requirements.txt
pip install pytest pytest-asyncio httpx pyyaml
```

2. **启动Redis**:
```bash
# Docker方式
docker run -d -p 6379:6379 redis:latest

# 或使用本地Redis
redis-server
```

3. **运行测试**:
```bash
# P0关键测试
python scripts/run_integration_tests.py --critical-only

# 回归测试
python scripts/run_integration_tests.py --regression

# 完整测试
python scripts/run_integration_tests.py --all
```

---

## 🔍 故障排查

### 常见问题

#### 1. Redis连接失败
**错误**: `RedisConnectionError: Error connecting to Redis`

**解决**:
```bash
# 检查Redis是否运行
redis-cli ping

# 或跳过Redis测试
python scripts/run_integration_tests.py --no-redis
```

#### 2. 图片生成测试失败
**错误**: `httpx.ConnectError: [Errno 111] Connection refused`

**解决**: 图片生成测试使用Mock，不需要真实API。如果失败，检查mock配置。

#### 3. WebSocket测试超时
**错误**: `asyncio.TimeoutError`

**解决**: 增加超时时间或检查异步事件循环配置。

---

## 📚 相关文档

- [BUGFIX_v7.122_IMAGE_PROMPT.md](../docs/BUGFIX_v7.122_IMAGE_PROMPT.md) - 图片Prompt单字符BUG修复
- [BUGFIX_v7.120_SEARCH_REFERENCES_INTEGRATION.md](../docs/BUGFIX_v7.120_SEARCH_REFERENCES_INTEGRATION.md) - 搜索引用集成优化
- [BUGFIX_SearchFilterManager_NoneType_v7.131.md](../docs/BUGFIX_SearchFilterManager_NoneType_v7.131.md) - 配置加载失败修复
- [BUGFIX_v7.129_OS_MODULE_IMPORT.md](../docs/BUGFIX_v7.129_OS_MODULE_IMPORT.md) - 模块导入缺失修复
- [BUGFIX_v7.129_COMPLETE_LOG_UNIFICATION.md](../docs/BUGFIX_v7.129_COMPLETE_LOG_UNIFICATION.md) - 日志统一化

---

## 🤝 贡献指南

### 添加新的集成测试

1. **选择合适的文件**:
   - 关键路径: `tests/integration/test_*_flow.py`
   - 回归测试: `tests/regression/test_high_frequency_bugs.py`

2. **添加测试标记**:
```python
@pytest.mark.integration
@pytest.mark.integration_critical  # 如果是P0测试
async def test_your_new_feature():
    pass
```

3. **更新文档**: 在本文档中记录新测试

4. **运行测试**: 确保新测试通过
```bash
pytest tests/integration/test_your_file.py -v
```

---

## 📞 支持

遇到问题？
- 查看 [GitHub Issues](https://github.com/dafei0755/ai/issues)
- 提交新Issue并附上测试日志
- 联系开发团队

---

**最后更新**: 2026-01-04
**维护者**: Copilot AI Testing Team
