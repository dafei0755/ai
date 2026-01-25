# 🌍 GeoIP 地理位置功能配置指南

## 📦 安装状态

✅ **httpx 库已安装**（用于HTTP请求）
✅ **无需下载数据库**（使用在线API）
✅ **无需注册账号**（使用免费API）

## 🚀 快速配置（0 步！）

### ✨ 零配置启动

使用 **ip-api.com** 免费API，无需任何配置即可使用：

- ✅ 无需注册
- ✅ 无需下载数据库
- ✅ 无需配置密钥
- ⚠️ 免费限制：45次/分钟（一般使用足够）

### 📊 API特性

**ip-api.com 免费版**：
- 速率限制：45次/分钟
- 支持字段：国家、省份、城市、经纬度、时区
- 支持中文地名（`lang=zh-CN`）
- 无需认证

如需更高速率，可考虑升级到付费版或使用其他服务。

## 🎯 验证安装

```bash
# 验证 GeoIP 功能
python tests\verify_geoip.py
```

**成功标志**：
```
🌍 测试 6: 公网 IP 处理...
   ✅ 8.8.8.8 -> 山景城 (美国)  # 不再显示"未知"
   ✅ 1.1.1.1 -> 悉尼 (澳大利亚)
```

## 📊 功能对比

| 功能 | 无数据库 | 有数据库 |
|------|---------|---------|
| 系统运行 | ✅ 正常 | ✅ 正常 |
| 本地IP识别 | ✅ 127.0.0.1 → 本地主机 | ✅ 127.0.0.1 → 本地主机 |
| 内网IP识别 | ✅ 192.168.x.x → 局域网 | ✅ 192.168.x.x → 局域网 |
| 公网IP识别 | ⚠️ 8.8.8.8 → 未知 | ✅ 8.8.8.8 → 山景城/美国 |
| 管理后台地区分布 | ⚠️ 显示"未知地区" | ✅ 显示具体城市 |
| 地图可视化 | ❌ 无坐标数据 | ✅ 显示用户分布地图 |

## 📝 数据库信息

- **文件名**：GeoLite2-City.mmdb
- **大小**：约 70 MB
- **更新频率**：每月更新（MaxMind）
- **精度**：
  - 国家：~99%
  - 城市：~80%
  - 坐标：±50-100km
- **许可证**：CC BY-SA 4.0（免费商用）

## 🔄 定期更新

建议每月更新数据库以保持数据准确性：

```bash
# 每月运行一次
python scripts\download_geoip_db.py
```

或设置 Windows 计划任务：

```powershell
# 每月 1 号凌晨 3 点自动更新
schtasks /create /tn "GeoIP Database Update" /tr "python D:\11-20\langgraph-design\scripts\download_geoip_db.py" /sc monthly /d 1 /st 03:00
```

## ❓ 常见问题

### Q: 可以跳过数据库配置吗？

**可以**。系统会优雅降级：
- 核心功能不受影响
- 管理后台显示"未知地区"而非具体城市
- 无法生成用户地理分布地图

### Q: License Key 是免费的吗？

**是的**。MaxMind GeoLite2 完全免费：
- 注册免费
- 下载免费
- 商用免费（需遵守 CC BY-SA 4.0）
- 每周更新免费

### Q: 数据库文件放在哪里？

默认位置：`data/GeoLite2-City.mmdb`

可通过环境变量自定义：
```env
GEOIP_DB_PATH=custom/path/GeoLite2-City.mmdb
```

### Q: 如何测试功能是否正常？

```bash
# 快速测试
python tests\verify_geoip.py

# 完整测试
python tests\run_geoip_tests.py
```

## 📞 需要帮助？

- 数据库下载问题：https://support.maxmind.com
- 功能使用问题：提交 Issue 到项目仓库
- 实现细节：查看 `docs/GEOIP_IMPLEMENTATION.md`

---

**下一步**：运行 `python scripts\download_geoip_db.py` 下载数据库 🚀
