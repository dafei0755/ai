# 系统诊断报告

**诊断时间:** 2025-12-11 15:11
**系统版本:** Intelligent Project Analyzer v2.0.0

---

## 诊断摘要

系统卡顿的主要原因已找到：

### 🔴 严重问题 (导致卡顿)

1. **Redis 高延迟** - 初始连接延迟 2034ms (正常应 <100ms)
2. **LLM 连接失败** - SSL 连接错误，无法连接到 OpenRouter API
3. **Redis 会话过多** - 69个活跃会话占用内存

### ⚠️ 次要问题

4. **配置文件缺失** - config/prompts 和 config/roles 目录不存在
5. **环境变量问题** - 诊断脚本访问了不存在的属性

---

## 详细分析

### 1. Redis 高延迟 (主要卡顿原因)

**症状:**
```
Redis connection: OK
Latency: 2034.84ms  ← 异常高！
Read/Write latency: 0.23ms  ← 正常
Memory usage: 25.38 MB
Total keys: 70
Active sessions: 69
```

**分析:**
- 初始连接延迟 2秒+，但读写操作正常 (0.23ms)
- 说明 Redis 服务本身正常，但**初始握手慢**
- 可能原因：
  - Redis 服务刚启动，正在加载持久化数据
  - 网络配置问题 (localhost 解析慢)
  - 防火墙/杀毒软件干扰

**影响:**
- 每次新建会话时，初始连接会卡顿 2秒
- 这是用户感受到"卡"的主要原因

**解决方案:**
```bash
# 方案1: 重启 Redis (清理内存)
redis-cli SHUTDOWN
redis-server

# 方案2: 清理过期会话
redis-cli FLUSHDB

# 方案3: 使用 IP 地址代替 localhost
# 修改 .env:
REDIS_URL=redis://127.0.0.1:6379/0
```

---

### 2. LLM 连接失败 (导致功能不可用)

**错误信息:**
```
[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol
openai.APIConnectionError: Connection error.
```

**分析:**
- SSL 握手失败，连接被中断
- 使用的是 OpenRouter API (openai/gpt-4.1)
- 可能原因：
  - 网络代理配置问题
  - 防火墙阻止 HTTPS 连接
  - OpenRouter API 暂时不可用
  - API Key 无效或过期

**影响:**
- 所有 LLM 调用都会失败
- 工作流无法执行分析任务

**解决方案:**
```bash
# 1. 测试网络连接
curl -I https://openrouter.ai/api/v1/models

# 2. 检查 API Key
# 查看 .env 文件中的 OPENROUTER_API_KEYS

# 3. 尝试切换到其他 LLM 提供商
# 修改 .env:
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_key
DEEPSEEK_MODEL=deepseek-chat
```

---

### 3. Redis 会话过多 (内存占用)

**数据:**
```
Total keys: 70
Active sessions: 69
Memory usage: 25.38 MB
```

**分析:**
- 69个会话占用 25MB 内存 (平均每个 ~370KB)
- 这些会话可能是测试遗留的
- 会话 TTL 设置为 72小时，长时间不清理

**影响:**
- 内存占用增加
- Redis 启动时加载数据变慢

**解决方案:**
```bash
# 清理所有会话 (谨慎操作！)
redis-cli KEYS "session:*" | xargs redis-cli DEL

# 或者只清理过期会话
python -c "
import redis
r = redis.Redis(host='localhost', port=6379, db=0)
keys = r.keys('session:*')
print(f'Found {len(keys)} sessions')
# 手动检查后再删除
"
```

---

### 4. 配置文件缺失

**缺失目录:**
- `config/prompts` - 提示词模板
- `config/roles` - 角色定义

**分析:**
- 这些目录应该存在于项目中
- 可能被误删除或未正确克隆

**影响:**
- 工作流可能无法加载提示词
- 角色选择功能可能失败

**解决方案:**
```bash
# 检查是否在 .gitignore 中
cat .gitignore | grep config

# 如果是 Git 子模块问题
git submodule update --init --recursive

# 或者从备份恢复
# (需要确认这些文件是否应该存在)
```

---

## 推荐修复步骤

### 立即执行 (解决卡顿)

1. **重启 Redis 并清理会话**
   ```bash
   redis-cli FLUSHDB
   redis-cli SHUTDOWN
   redis-server
   ```

2. **修改 Redis URL 使用 IP**
   ```bash
   # 编辑 .env
   REDIS_URL=redis://127.0.0.1:6379/0
   ```

3. **测试 LLM 连接**
   ```bash
   # 运行简单测试
   python -c "
   from intelligent_project_analyzer.services.llm_factory import LLMFactory
   llm = LLMFactory.create_llm()
   print(llm.invoke('Hello'))
   "
   ```

### 后续优化

4. **配置会话自动清理**
   - 减少 SESSION_TTL_HOURS (从 72 → 24)
   - 添加定时任务清理过期会话

5. **检查配置文件**
   - 确认 config/prompts 和 config/roles 是否应该存在
   - 如果需要，从 Git 历史恢复

6. **监控 Redis 性能**
   ```bash
   # 实时监控
   redis-cli --latency

   # 查看慢查询
   redis-cli SLOWLOG GET 10
   ```

---

## 性能基准

### 正常指标
- Redis 连接延迟: < 10ms
- Redis 读写延迟: < 1ms
- LLM 响应时间: 1000-3000ms
- 活跃会话数: < 10

### 当前指标
- Redis 连接延迟: **2034ms** ❌
- Redis 读写延迟: 0.23ms ✅
- LLM 响应时间: **失败** ❌
- 活跃会话数: **69** ⚠️

---

## 下一步行动

1. ✅ 运行诊断脚本 (已完成)
2. ⏳ 重启 Redis 并清理会话
3. ⏳ 修复 LLM 连接问题
4. ⏳ 验证系统恢复正常
5. ⏳ 添加监控和告警

---

## 附录: 快速修复脚本

创建文件 `fix_system.bat`:

```batch
@echo off
echo Fixing system issues...

echo.
echo [1/3] Cleaning Redis sessions...
redis-cli FLUSHDB
if %errorlevel% neq 0 (
    echo ERROR: Failed to clean Redis
    pause
    exit /b 1
)

echo.
echo [2/3] Restarting Redis...
redis-cli SHUTDOWN
timeout /t 2 /nobreak >nul
start redis-server

echo.
echo [3/3] Testing system...
python test_system_diagnostics.py

echo.
echo Done! Check the diagnostic report above.
pause
```

运行: `fix_system.bat`
