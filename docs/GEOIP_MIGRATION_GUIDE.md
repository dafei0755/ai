# 🌍 GeoIP 迁移指南：从 MaxMind 到 ip-api.com

> **迁移日期**：2026-01-03
> **原因**：MaxMind 注册流程复杂，改用无需注册的免费API

---

## 📋 迁移概述

### 旧方案（已弃用）
- **服务商**：MaxMind GeoLite2
- **类型**：离线数据库（.mmdb文件）
- **依赖**：`geoip2>=4.7.0`
- **问题**：
  - ❌ 需要注册MaxMind账号
  - ❌ 需要生成License Key
  - ❌ 需要下载70MB数据库文件
  - ❌ 需要定期更新数据库

### 新方案（当前）
- **服务商**：ip-api.com
- **类型**：在线API
- **依赖**：`httpx`（已包含在项目中）
- **优势**：
  - ✅ 无需注册
  - ✅ 零配置
  - ✅ 自动更新（实时查询）
  - ✅ 支持中文地名
  - ✅ 包含经纬度信息
  - ⚠️ 速率限制：45次/分钟（免费版）

---

## 🔧 代码变更

### 1. 服务初始化

**旧代码**：
```python
class GeoIPService:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or self._get_default_db_path()
        self.reader = geoip2.database.Reader(self.db_path)
        self.is_available = True
```

**新代码**：
```python
class GeoIPService:
    API_URL = "http://ip-api.com/json/{ip}"

    def __init__(self):
        self.is_available = True
        self._request_times = []  # 速率限制追踪
```

### 2. IP查询方法

**旧代码**：
```python
def get_location(self, ip: str) -> Dict[str, Any]:
    response = self.reader.city(ip)
    return {
        "country": response.country.names.get("zh-CN"),
        "city": response.city.names.get("zh-CN"),
        # ...
    }
```

**新代码**：
```python
def get_location(self, ip: str) -> Dict[str, Any]:
    url = self.API_URL.format(ip=ip)
    with httpx.Client(timeout=5.0) as client:
        response = client.get(url, params=self.API_PARAMS)
        data = response.json()
    return {
        "country": data.get("country", "未知"),
        "city": data.get("city", "未知"),
        # ...
    }
```

### 3. 新增速率限制保护

```python
def _check_rate_limit(self) -> bool:
    """检查是否超过速率限制（45次/分钟）"""
    now = time.time()
    self._request_times = [t for t in self._request_times
                           if now - t < self.RATE_WINDOW]

    if len(self._request_times) >= self.RATE_LIMIT:
        return False

    self._request_times.append(now)
    return True
```

---

## 📦 依赖变更

### requirements.txt

**移除**：
```diff
- geoip2>=4.7.0        # IP地理位置识别（离线数据库）
```

**无需添加**（httpx已存在）：
```python
httpx>=0.27.0  # 已包含在项目中
```

---

## 🗑️ 可删除的文件

以下文件已不再需要（可选择性删除）：

```
scripts/download_geoip_db.py          # 数据库下载脚本
install_geoip2.bat                    # Windows安装脚本
data/GeoLite2-City.mmdb              # 离线数据库文件（如果存在）
```

---

## ✅ 迁移检查清单

- [x] 更新 `geoip_service.py` 使用HTTP API
- [x] 移除 `requirements.txt` 中的 `geoip2` 依赖
- [x] 更新文档：
  - [x] `docs/GEOIP_IMPLEMENTATION.md`
  - [x] `docs/GEOIP_SETUP_GUIDE.md`
- [x] 更新测试脚本 `tests/verify_geoip.py`
- [x] 运行测试验证功能正常
- [ ] （可选）删除不再需要的脚本和数据库文件

---

## 🧪 测试验证

```bash
# 验证新实现
python tests\verify_geoip.py

# 预期输出：
# ✅ 所有测试通过！GeoIP 功能正常
# 💡 提示:
#    - 使用 ip-api.com 免费API（无需注册）
#    - 速率限制：45次/分钟
```

---

## 📊 性能对比

| 指标 | MaxMind离线库 | ip-api.com API |
|------|---------------|----------------|
| 查询速度 | ~1ms | ~500-1000ms |
| 配置复杂度 | 高（需注册+下载） | 零配置 |
| 数据新鲜度 | 月度更新 | 实时更新 |
| 维护成本 | 高 | 零维护 |
| 速率限制 | 无限制 | 45次/分钟 |
| 适用场景 | 高频查询 | 一般使用 |

---

## 🚀 升级建议

### 如果速率限制不够用？

**方案1**：升级到付费版
- ip-api.com Pro：$13/月，1000次/分钟
- ipapi.co：$10/月，30K次/月

**方案2**：自建缓存
```python
from cachetools import TTLCache

class GeoIPService:
    def __init__(self):
        self._cache = TTLCache(maxsize=1000, ttl=3600)  # 1小时缓存

    def get_location(self, ip: str):
        if ip in self._cache:
            return self._cache[ip]

        result = self._fetch_from_api(ip)
        self._cache[ip] = result
        return result
```

**方案3**：回到离线数据库
- 如果有大量查询需求，可恢复MaxMind方案
- 参考历史版本的实现代码

---

## 📞 问题反馈

遇到问题？
- 📖 查看文档：[docs/GEOIP_SETUP_GUIDE.md](GEOIP_SETUP_GUIDE.md)
- 🧪 运行测试：`python tests\verify_geoip.py`
- 🐛 提交Issue：https://github.com/dafei0755/ai/issues

---

**迁移完成！** 🎉
