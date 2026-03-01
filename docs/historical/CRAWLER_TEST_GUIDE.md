# 🧪 爬虫测试快速指南

**版本**: v8.110.0
**更新**: 2026-02-17

---

## 📋 测试清单

我们提供了3个测试脚本，按照以下顺序执行：

### 1️⃣ 爬虫框架测试 ✅ 已完成

```bash
python intelligent_project_analyzer/scripts/test_crawler_framework.py
```

**状态**: ✅ 4/4测试通过

---

### 2️⃣ 登录功能测试（可选）

如果网站需要登录才能访问内容，运行此测试：

```bash
python intelligent_project_analyzer/scripts/test_crawler_login.py
```

**测试项**:
- ✅ 测试1: 从配置文件登录
- ✅ 测试2: Cookie注入示例
- ✅ 测试3: 加载已保存的Cookie

**前置条件**:
1. 创建配置文件（如果不存在）:
   ```bash
   # 复制模板
   cp intelligent_project_analyzer/config/crawler_credentials.py.example \
      intelligent_project_analyzer/config/crawler_credentials.py
   ```

2. 编辑配置文件:
   ```python
   # intelligent_project_analyzer/config/crawler_credentials.py

   ARCHDAILY_CONFIG = CrawlerConfig(
       use_login=True,
       login_username="your_email@example.com",  # 修改
       login_password="your_password_here",       # 修改
       cookie_file="data/cookies/archdaily_cookies.pkl",
   )
   ```

3. 或使用环境变量（更安全）:
   ```powershell
   # PowerShell
   $env:ARCHDAILY_USERNAME = "your_email@example.com"
   $env:ARCHDAILY_PASSWORD = "your_password"
   ```

---

### 3️⃣ 快速爬取测试（小规模）⭐ 推荐首次运行

```bash
python intelligent_project_analyzer/scripts/quick_crawl_test.py
```

**测试参数**:
- 每个来源仅爬取2个项目
- 请求延迟5秒（避免被封）
- DEBUG日志级别（查看详细过程）
- 不限浏览量和发布日期

**预期结果**:
- Archdaily: ✅ 成功爬取1-2个项目
- Gooood: ✅ 成功爬取1-2个项目

**如果失败**:
- 检查网络连接
- 查看错误信息（选择器不匹配？）
- 尝试启用登录
- 增加timeout参数

---

### 4️⃣ 完整爬取测试（测试模式）

框架测试通过后，运行完整爬取（测试模式）：

```bash
# 不登录（默认）
python intelligent_project_analyzer/scripts/crawl_external_layer2.py --test

# 使用登录
python intelligent_project_analyzer/scripts/crawl_external_layer2.py --test --login
```

**测试模式参数**:
- `--test`: 仅爬取3个项目，延迟5秒
- `--login`: 使用登录配置

**预期结果**:
- 爬取Archdaily: 3个项目
- 爬取Gooood: 3个项目
- LLM特征提取: 6次调用（当前为模拟）
- 差异度计算: 6次
- 保存缓存: `intelligent_project_analyzer/data/external_layer2_cache.json`

**检查输出**:
```bash
# 查看缓存文件
cat intelligent_project_analyzer/data/external_layer2_cache.json

# 应该包含
{
  "version": "v8.110.0",
  "crawl_time": "2026-02-17T...",
  "total_selected": 6,
  "candidates": [ ... ]
}
```

---

### 5️⃣ 生产环境运行

测试通过后，运行完整爬取：

```bash
# 不登录
python intelligent_project_analyzer/scripts/crawl_external_layer2.py

# 使用登录（推荐）
python intelligent_project_analyzer/scripts/crawl_external_layer2.py --login
```

**生产参数**:
- 每个来源爬取20个项目
- 请求延迟3秒
- 筛选最近30天内容
- 浏览量>5000

---

## 🐛 故障排查

### 问题1: import错误

```
ModuleNotFoundError: No module named 'intelligent_project_analyzer'
```

**解决**: 在项目根目录运行脚本
```bash
cd D:\11-20\langgraph-design
python intelligent_project_analyzer/scripts/quick_crawl_test.py
```

---

### 问题2: 未爬取到任何项目

**可能原因**:
1. 网站结构变化（选择器不匹配）
2. 被网站封禁（403/429错误）
3. 需要登录才能查看

**解决方案**:

**A. 检查选择器是否匹配**
```python
# 在爬虫代码中添加调试
response = self._request_with_retry(list_url)
print(response.text)  # 打印HTML，检查实际结构
```

**B. 启用登录**
```bash
python quick_crawl_test.py --login
```

**C. 手动Cookie注入**
1. 浏览器打开目标网站并登录
2. F12 → Application → Cookies → 复制所有Cookie
3. 运行脚本注入Cookie

---

### 问题3: 描述长度不足

```
⚠️ 项目验证失败: 描述过短 (50 < 100)
```

**解决**: 降低验证标准
```python
# 在 CrawlerConfig 中
config = CrawlerConfig(
    min_description_length=50,  # 从100降到50
)
```

**或**: 取消验证
```python
# 在 base_crawler.py 的 _validate_project_data 中注释
# if len(project.description) < 100:
#     return False
```

---

### 问题4: 请求超时

```
❌ 请求超时: Read timed out
```

**解决**: 增加超时和延迟
```python
config = CrawlerConfig(
    timeout=60,           # 从30秒增加到60秒
    request_delay=10.0,   # 从5秒增加到10秒
)
```

---

### 问题5: 被封禁（403/429）

```
❌ 请求失败: 403 Forbidden
```

**解决方案**:

**A. 启用登录**（最有效）
```bash
python crawl_external_layer2.py --login
```

**B. 增加延迟**
```python
config = CrawlerConfig(
    request_delay=10.0,  # 增加到10秒
)
```

**C. 使用代理**（高级）
```python
config = CrawlerConfig(
    use_proxy=True,
    proxy_list=[
        "http://proxy1.example.com:8080",
        "http://proxy2.example.com:8080",
    ],
)
```

---

## 📊 预期性能

### 测试模式（--test）
- **项目数**: 3个/来源
- **总耗时**: 约2分钟
- **请求数**: 约10-15次
- **平均延迟**: 5秒/请求

### 生产模式
- **项目数**: 20个/来源
- **总耗时**: 约5-8分钟
- **请求数**: 约50-80次
- **平均延迟**: 3秒/请求

---

## ✅ 成功标准

### 短期（测试阶段）
- [ ] 框架测试4/4通过
- [ ] 快速爬取测试成功爬取≥1个项目
- [ ] 完整测试模式成功爬取3-6个项目
- [ ] 生成`external_layer2_cache.json`文件

### 中期（生产准备）
- [ ] 生产模式成功爬取≥30个项目
- [ ] 爬取成功率>80%
- [ ] 集成真实LLM特征提取
- [ ] 配置定时任务

### 长期（自动化运行）
- [ ] 每月自动爬取
- [ ] 无人工干预
- [ ] 监控Dashboard
- [ ] 自动失败告警

---

## 🔝 推荐测试顺序

```bash
# 1. 框架测试（已完成✅）
python intelligent_project_analyzer/scripts/test_crawler_framework.py

# 2. 快速爬取测试（⭐ 当前步骤）
python intelligent_project_analyzer/scripts/quick_crawl_test.py

# 3. 登录测试（如果第2步失败）
python intelligent_project_analyzer/scripts/test_crawler_login.py

# 4. 完整测试模式
python intelligent_project_analyzer/scripts/crawl_external_layer2.py --test

# 5. 生产环境运行
python intelligent_project_analyzer/scripts/crawl_external_layer2.py --login
```

---

## 📝 下一步

完成测试后：

1. **集成真实LLM**: 替换`extract_features_with_llm()`模拟版本
2. **设置定时任务**: Windows任务计划程序/Linux Cron
3. **监控爬取质量**: 人工抽查前10个项目
4. **优化选择器**: 根据实际HTML结构调整
5. **开始Phase 3.2.1**: 创建人工策展池

---

**创建时间**: 2026-02-17
**维护者**: AI Architecture Team
