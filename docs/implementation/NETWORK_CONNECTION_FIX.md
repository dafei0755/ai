# 网络连接错误修复指南

## 问题现象

后端在 `ProjectDirector` 节点调用 OpenAI API 时出现连接错误：

```
httpcore.ConnectError: [SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol (_ssl.c:1028)
openai.APIConnectionError: Connection error.
```

## 根本原因

这是一个 **SSL/TLS 握手失败**导致的网络连接问题，可能由以下原因引起：

1. **网络代理配置问题**（系统或 Python 代理设置）
2. **SSL 证书验证失败**（中间人代理、企业防火墙）
3. **网络不稳定或超时**
4. **OpenAI API Base URL 配置错误**

## 已实施的防御性修复

### 1. 防止级联崩溃

**修改文件**: `intelligent_project_analyzer/interaction/nodes/quality_preflight.py`

```python
# 添加 None 检查，防止 AttributeError
strategic_analysis = state.get("strategic_analysis", None)

if strategic_analysis is None:
    logger.error("❌ strategic_analysis 为 None，ProjectDirector 可能失败了")
    logger.error("⚠️ 无法进行质量预检，跳过此节点")
    return {}
```

**修改文件**: `intelligent_project_analyzer/workflow/main_workflow.py`

```python
# ProjectDirector 失败时返回明确的错误状态
except Exception as e:
    return {
        "error": str(e),
        "strategic_analysis": None,  # 明确标记为 None
        "active_agents": [],
        "execution_mode": "dynamic",
        "errors": [{...}]
    }
```

### 2. 增强重试机制

**修改文件**: `intelligent_project_analyzer/agents/dynamic_project_director.py`

```python
except Exception as e:
    # 捕获网络连接错误
    if "Connection" in error_type or "SSL" in str(e):
        logger.error("🌐 检测到网络连接问题")
        logger.error("   - 建议: 检查 .env 中的 OPENAI_API_BASE/OPENAI_PROXY 设置")
    
    if attempt < max_retries - 1:
        wait_time = 2 ** attempt  # 指数退避
        time.sleep(wait_time)
        continue
```

## 用户侧解决方案

### 方案 1: 检查代理设置（推荐）

如果你在使用代理上网，请在 `.env` 文件中配置：

```env
# .env 文件
OPENAI_API_KEY=sk-xxxxx
OPENAI_API_BASE=https://api.openai.com/v1

# 如果使用代理（HTTP/HTTPS）
HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890

# 或者使用 SOCKS5 代理
# HTTP_PROXY=socks5://127.0.0.1:7890
# HTTPS_PROXY=socks5://127.0.0.1:7890
```

### 方案 2: 禁用 SSL 验证（仅用于测试）

**⚠️ 警告：不推荐在生产环境使用**

临时禁用 SSL 验证（仅用于排查问题）：

```python
# intelligent_project_analyzer/services/llm_factory.py
import httpx

# 创建自定义 HTTP 客户端
http_client = httpx.Client(
    verify=False,  # 禁用 SSL 验证
    timeout=60.0
)

llm = ChatOpenAI(
    model=model_name,
    http_client=http_client
)
```

### 方案 3: 使用国内中转 API

如果 OpenAI 官方 API 访问困难，可以使用国内中转服务：

```env
# .env 文件
OPENAI_API_KEY=your-api-key
OPENAI_API_BASE=https://api.example-proxy.com/v1  # 中转服务地址
```

### 方案 4: 检查网络连接

运行诊断脚本检查连接：

```cmd
python -c "import httpx; response = httpx.get('https://api.openai.com', verify=True); print(f'Status: {response.status_code}')"
```

### 方案 5: 使用本地 LLM（终极方案）

如果网络问题无法解决，可以切换到本地 LLM（如 Ollama）：

```env
# .env 文件
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:14b
```

## 验证修复

重启后端服务后，系统会：

1. **自动重试** 3 次（间隔 1s/2s/4s）
2. **记录详细错误信息**（查看日志）
3. **优雅降级**（即使失败也不会崩溃到 100%）

查看日志确认问题：

```cmd
# 查看最新日志
type intelligent_project_analyzer\logs\api.log | findstr "Connection\|SSL\|网络"
```

## 后续改进建议

1. **添加健康检查 API**：在启动时测试 OpenAI 连接
2. **支持降级策略**：自动切换到备用 LLM 服务
3. **增强错误提示**：前端显示网络错误并提供操作指南
4. **添加超时配置**：允许用户自定义 API 超时时间

---

**最后更新**: 2025-11-27  
**相关 Issue**: ProjectDirector SSL Connection Error
