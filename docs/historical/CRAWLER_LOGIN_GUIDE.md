# 爬虫登录功能使用指南

**版本**: v8.110.0
**更新**: 2026-02-17

---

## 🔐 登录功能概述

爬虫支持3种登录方式：

1. **用户名密码登录**（自动化）
2. **Cookie注入**（手动获取）
3. **Session管理**（持久化）

---

## 🚀 快速开始

### 方式1: 用户名密码登录（推荐）

#### Step 1: 配置凭证

编辑 `intelligent_project_analyzer/config/crawler_credentials.py`:

```python
ARCHDAILY_CONFIG = CrawlerConfig(
    use_login=True,
    login_username="your_email@example.com",   # 修改
    login_password="your_password_here",        # 修改
    cookie_file="data/cookies/archdaily_cookies.pkl",
)
```

⚠️ **安全提示**:
- 不要提交密码到Git仓库
- 使用环境变量存储敏感信息
- 定期更换密码

#### Step 2: 使用配置

```python
from intelligent_project_analyzer.config.crawler_credentials import ARCHDAILY_CONFIG
from intelligent_project_analyzer.crawlers import ArchdailyCrawler

# 自动登录
crawler = ArchdailyCrawler(config=ARCHDAILY_CONFIG)
projects = crawler.fetch()  # 爬取时会自动登录
```

#### Step 3: 验证登录

查看日志输出：
```
🔐 开始登录...
   找到CSRF token: abc123...
   提交登录: https://www.archdaily.cn/cn/login
   ✅ 检测到登录Cookie
✅ 登录成功
💾 Cookie已保存: data/cookies/archdaily_cookies.pkl
```

---

### 方式2: Cookie注入（无需密码）

如果网站登录逻辑复杂（OAuth/验证码等），可以手动获取Cookie。

#### Step 1: 浏览器获取Cookie

1. 浏览器打开 https://www.archdaily.cn/cn
2. 手动登录
3. **F12** 打开开发者工具
4. **Application** → **Cookies** → https://www.archdaily.cn
5. 复制所有Cookie（name和value）

#### Step 2: 注入Cookie

```python
from intelligent_project_analyzer.crawlers import ArchdailyCrawler, CrawlerConfig

# 创建爬虫（不启用自动登录）
config = CrawlerConfig(use_login=False)
crawler = ArchdailyCrawler(config=config)

# 手动注入Cookie
cookies = {
    "_ga": "GA1.2.1234567890.1234567890",
    "session": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "_gid": "GA1.2.9876543210.9876543210",
    # ... 复制所有Cookie
}

for name, value in cookies.items():
    crawler.session.cookies.set(name, value, domain=".archdaily.cn")

# 保存Cookie以便下次使用
crawler.config.cookie_file = "data/cookies/archdaily_cookies.pkl"
crawler._save_cookies()

# 开始爬取
projects = crawler.fetch()
```

#### Step 3: 后续使用

```python
# 后续直接加载Cookie
config = CrawlerConfig(
    cookie_file="data/cookies/archdaily_cookies.pkl"
)
crawler = ArchdailyCrawler(config=config)
projects = crawler.fetch()  # 自动加载Cookie，无需重新登录
```

---

### 方式3: 环境变量（最安全）

#### Step 1: 设置环境变量

**Windows PowerShell**:
```powershell
$env:ARCHDAILY_USERNAME = "your_email@example.com"
$env:ARCHDAILY_PASSWORD = "your_password"
```

**Linux/Mac**:
```bash
export ARCHDAILY_USERNAME="your_email@example.com"
export ARCHDAILY_PASSWORD="your_password"
```

**持久化（Linux/Mac）**:
```bash
# 添加到 ~/.bashrc 或 ~/.zshrc
echo 'export ARCHDAILY_USERNAME="your_email@example.com"' >> ~/.bashrc
echo 'export ARCHDAILY_PASSWORD="your_password"' >> ~/.bashrc
source ~/.bashrc
```

#### Step 2: 使用（自动读取）

```python
# crawler_credentials.py 会自动读取环境变量
from intelligent_project_analyzer.config.crawler_credentials import ARCHDAILY_CONFIG
from intelligent_project_analyzer.crawlers import ArchdailyCrawler

crawler = ArchdailyCrawler(config=ARCHDAILY_CONFIG)
projects = crawler.fetch()
```

---

## 🔧 登录功能详解

### 自动登录流程

```python
1. 初始化爬虫
   ↓
2. 尝试加载本地Cookie
   ↓
3. 检查Cookie是否有效
   ├─ 有效 → 跳过登录
   └─ 无效/不存在 → 执行登录
         ↓
4. 访问登录页面，提取CSRF token
   ↓
5. 提交登录表单（username + password + token）
   ↓
6. 验证登录状态（检查Cookie/响应内容/重定向）
   ↓
7. 保存Cookie到本地文件
   ↓
8. 开始爬取
```

### Session管理

```python
# 配置Session超时时间
config = CrawlerConfig(
    session_timeout=3600,  # 1小时后强制重新登录
)

# 爬虫会自动检查Session状态
crawler.fetch()  # 如果Session过期，自动重新登录
```

### Cookie持久化

**存储位置**: `data/cookies/<site>_cookies.pkl`

**数据格式**: Python pickle序列化的`requests.cookies.RequestsCookieJar`

**有效期**: 由网站Session决定（通常7-30天）

**安全性**:
- Cookie文件包含敏感信息，不要分享
- 添加到 `.gitignore`
- 使用文件系统权限保护（chmod 600）

---

## ⚙️ 配置参数

### CrawlerConfig登录相关

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `use_login` | bool | False | 是否启用自动登录 |
| `login_username` | str | None | 用户名/邮箱 |
| `login_password` | str | None | 密码 |
| `cookie_file` | str | None | Cookie持久化文件路径 |
| `session_timeout` | int | 3600 | Session超时时间（秒） |

---

## 🐛 故障排查

### 问题1: 登录失败（401/403）

**症状**:
```
❌ 登录失败
⚠️ 无法确认登录状态，可能失败
```

**原因**:
- 用户名或密码错误
- 网站登录逻辑变更（表单字段名改变）
- 需要验证码

**解决**:
1. 验证账号密码正确
2. 手动登录网站，检查是否需要验证码
3. 使用Cookie注入方式（绕过登录表单）
4. 检查爬虫日志，查看提交的表单数据

### 问题2: Cookie自动失效

**症状**:
```
⚠️ Cookie已过期
🔄 Session过期，重新登录...
```

**原因**:
- 网站Session时间较短
- IP变化导致Cookie失效
- 网站安全策略（同一账号多地登录）

**解决**:
```python
# 方案1: 增加Session检查频率
config = CrawlerConfig(
    session_timeout=1800,  # 减少到30分钟
)

# 方案2: 禁用Cookie缓存，每次重新登录
config = CrawlerConfig(
    cookie_file=None,  # 不缓存
)
```

### 问题3: CSRF Token错误

**症状**:
```
❌ 登录过程出错: CSRF token验证失败
```

**原因**:
- 登录页面结构变化
- Token字段名不匹配

**解决**:
```python
# 在 archdaily_crawler.py 中调试
# 打印登录页面HTML
response = self._request_with_retry(self.LOGIN_URL)
print(response.text)  # 查看实际表单结构

# 手动指定Token字段名
csrf_input = soup.find("input", {"name": "authenticity_token"})  # 修改字段名
```

### 问题4: 登录需要验证码

**症状**: 登录页面显示验证码

**解决方案**:

**方案1: Cookie注入**（推荐）
- 浏览器手动登录
- 复制Cookie注入爬虫

**方案2: 使用Playwright**（自动化浏览器）
```bash
pip install playwright
playwright install chromium
```

```python
from playwright.sync_api import sync_playwright

def login_with_playwright(username, password):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # 显示浏览器
        page = browser.new_page()

        page.goto("https://www.archdaily.cn/cn/login")
        page.fill("input[name='username']", username)
        page.fill("input[name='password']", password)

        # 人工输入验证码（暂停等待）
        input("请输入验证码后按回车...")

        page.click("button[type='submit']")
        page.wait_for_load_state("networkidle")

        # 提取Cookie
        cookies = page.context.cookies()
        browser.close()

        return cookies
```

---

## 📊 登录状态监控

### 检查登录状态

```python
from intelligent_project_analyzer.crawlers import ArchdailyCrawler

crawler = ArchdailyCrawler(config=ARCHDAILY_CONFIG)

# 手动检查
if crawler._check_login_status():
    print("✅ 已登录")
else:
    print("❌ 未登录或已过期")
```

### 日志级别

```python
# 调试登录问题，启用DEBUG日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 或使用loguru
from loguru import logger
logger.add("crawler_login.log", level="DEBUG")
```

---

## 🔒 安全最佳实践

### 1. 不要硬编码密码

❌ **错误**:
```python
config = CrawlerConfig(
    login_password="mypassword123",  # 不要这样做！
)
```

✅ **正确**:
```python
import os

config = CrawlerConfig(
    login_password=os.getenv("ARCHDAILY_PASSWORD"),
)
```

### 2. 使用 .gitignore

确保凭证文件不被提交：

```gitignore
# .gitignore
intelligent_project_analyzer/config/crawler_credentials.py
data/cookies/*.pkl
*.env
```

### 3. 加密Cookie文件

```python
from cryptography.fernet import Fernet

# 生成密钥
key = Fernet.generate_key()
cipher = Fernet(key)

# 加密Cookie
with open("cookies.pkl", "rb") as f:
    encrypted = cipher.encrypt(f.read())

with open("cookies.pkl.enc", "wb") as f:
    f.write(encrypted)

# 解密Cookie
with open("cookies.pkl.enc", "rb") as f:
    decrypted = cipher.decrypt(f.read())
```

### 4. 使用专用爬虫账号

- 不要使用个人主账号
- 创建专用爬虫账号
- 限制权限（只读权限）
- 定期更换密码

---

## 📝 下一步

- [ ] 测试Archdaily登录功能
- [ ] 实现Gooood登录（如果需要）
- [ ] 添加验证码处理（Playwright）
- [ ] 实现代理IP轮换
- [ ] 监控登录成功率

---

**创建时间**: 2026-02-17
**维护者**: AI Architecture Team
