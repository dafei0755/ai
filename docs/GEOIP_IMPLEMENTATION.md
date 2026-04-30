# GeoIP 离线数据库实施指南

## 📦 已完成的集成

### ✅ 1. 依赖安装
已添加 `geoip2>=4.7.0` 到 [requirements.txt](../requirements.txt)

```bash
pip install geoip2
```

### ✅ 2. GeoIP 服务模块
创建了 [geoip_service.py](../intelligent_project_analyzer/services/geoip_service.py)

**核心功能**：
- `get_client_ip(request)` - 获取客户端真实IP（支持代理/负载均衡）
- `get_location(ip)` - 从IP识别地理位置（国家、省份、城市、经纬度）
- 自动处理本地IP/内网IP
- 优雅降级（数据库不存在时返回默认值）

### ✅ 3. 后端API集成
修改了 [server.py](../intelligent_project_analyzer/api/server.py) 的 `start_analysis` 端点：

```python
# 采集IP和地理位置
geoip_service = get_geoip_service()
client_ip = geoip_service.get_client_ip(request)
location_info = geoip_service.get_location(client_ip)

# 保存到session metadata
session_data["metadata"] = {
    "client_ip": client_ip,
    "location": location_info.get("city", "未知"),
    "geo_info": location_info,  # 完整地理信息（含经纬度）
    "user_agent": request.headers.get("User-Agent", ""),
}
```

### ✅ 4. 管理后台统计增强
修改了 [admin_routes.py](../intelligent_project_analyzer/api/admin_routes.py) 的用户分析端点：

**改进点**：
- 优先使用IP定位的城市数据（`metadata.location`）
- 附带经纬度信息到API响应（支持前端地图可视化）
- 回退机制：IP定位失败时从用户输入中检测城市

**API响应格式**：
```json
{
  "region_distribution": [
    {
      "region": "深圳市",
      "count": 15,
      "lat": 22.5431,
      "lng": 114.0579,
      "country": "中国",
      "province": "广东省"
    }
  ]
}
```

### ✅ 5. 数据库下载脚本
创建了 [download_geoip_db.py](../scripts/download_geoip_db.py)

**使用方法**：
```bash
# 方式一：设置环境变量（推荐）
export MAXMIND_LICENSE_KEY=your_license_key_here
python scripts/download_geoip_db.py

# 方式二：手动输入
python scripts/download_geoip_db.py
# 按提示输入 License Key
```

---

## 🚀 快速启动步骤

### 1. 注册 MaxMind 账号（免费）
访问：https://www.maxmind.com/en/geolite2/signup

### 2. 生成 License Key
登录后访问：https://www.maxmind.com/en/accounts/current/license-key

### 3. 下载数据库
```bash
# 安装依赖
pip install geoip2

# 下载数据库（约 70 MB）
python scripts/download_geoip_db.py
```

**下载成功后会看到**：
```
✅ 安装完成！
数据库位置: d:\11-20\langgraph-design\data\GeoLite2-City.mmdb
```

### 4. 启动服务
```bash
# 启动后端
python scripts/run_server.py

# 或使用生产模式（Python 3.13 Windows）
python scripts/run_server_production.py
```

### 5. 测试IP定位
访问 http://localhost:3000 并创建一个分析会话，后端日志会显示：
```
🌍 客户端IP: 1.2.3.4 -> 中国/深圳市
```

---

## 📊 数据流

```
用户请求 → FastAPI Request
    ↓
geoip_service.get_client_ip(request)
    ↓ (优先级)
1. X-Forwarded-For 头
2. X-Real-IP 头
3. request.client.host
    ↓
geoip_service.get_location(ip)
    ↓
GeoLite2-City.mmdb 查询
    ↓
返回: {ip, country, province, city, lat, lng}
    ↓
保存到 session.metadata.geo_info
    ↓
管理后台统计展示
```

---

## 🗺️ 前端地图可视化（待实施）

API现在返回经纬度数据，可以集成地图库：

### 推荐方案 1：ECharts 中国地图
```bash
npm install echarts echarts-for-react
```

```typescript
import ReactECharts from 'echarts-for-react';

const mapOption = {
  geo: {
    map: 'china',
    roam: true,
    label: { show: true }
  },
  series: [{
    type: 'scatter',
    coordinateSystem: 'geo',
    data: regionData.map(item => ({
      name: item.region,
      value: [item.lng, item.lat, item.count]
    })),
    symbolSize: (val) => Math.max(val[2] * 2, 10)
  }]
};

<ReactECharts option={mapOption} style={{ height: '500px' }} />
```

### 推荐方案 2：Leaflet 开源地图
```bash
npm install leaflet react-leaflet
```

```typescript
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet';

<MapContainer center={[35, 105]} zoom={5} style={{ height: '500px' }}>
  <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
  {regionData.map((item, idx) => (
    item.lat && item.lng && (
      <CircleMarker
        key={idx}
        center={[item.lat, item.lng]}
        radius={Math.max(item.count / 2, 5)}
      >
        <Popup>{item.region}: {item.count} 会话</Popup>
      </CircleMarker>
    )
  ))}
</MapContainer>
```

---

## 🔧 配置选项

### 环境变量（可选）
```env
# .env 文件
MAXMIND_LICENSE_KEY=your_license_key_here
```

### 数据库路径
默认：`data/GeoLite2-City.mmdb`

如需自定义：
```python
from intelligent_project_analyzer.services.geoip_service import GeoIPService

# 使用自定义路径
geoip = GeoIPService(db_path="/path/to/GeoLite2-City.mmdb")
```

---

## 📝 维护建议

### 数据库更新频率
- 推荐：每月更新一次
- MaxMind 每周二更新 GeoLite2 数据库

### 自动更新脚本（可选）
```bash
# 添加到 crontab（每月1号执行）
0 0 1 * * cd /path/to/project && python scripts/download_geoip_db.py
```

### 监控数据库健康
- 检查数据库文件大小（应约 70 MB）
- 定期验证查询准确性
- 监控GeoIP服务初始化日志

---

## ⚠️ 常见问题

### Q1: 数据库不存在会怎样？
**A**: 服务会优雅降级，返回"未知"位置，不影响主流程。日志会提示：
```
⚠️ GeoLite2 数据库不存在: data/GeoLite2-City.mmdb
💡 请运行: python scripts/download_geoip_db.py
```

### Q2: 本地测试看不到城市？
**A**: 本地回环地址（127.0.0.1）会返回"本地主机"。部署到生产环境后可以正常识别。

### Q3: 内网IP能识别吗？
**A**: 内网IP（10.x.x.x, 192.168.x.x）会返回"局域网"，无法定位具体城市。

### Q4: 精度有多高？
**A**:
- 国家级：99% 准确
- 城市级：~80% 准确（取决于ISP和代理）
- 经纬度：误差范围约 50-100km

### Q5: 需要付费吗？
**A**: GeoLite2 完全免费，但需要注册账号获取 License Key。

---

## 📚 参考资料

- [MaxMind GeoLite2 官网](https://dev.maxmind.com/geoip/geolite2-free-geolocation-data)
- [geoip2 Python库文档](https://geoip2.readthedocs.io/)
- [GeoLite2 许可协议](https://www.maxmind.com/en/geolite2/eula)

---

**实施完成时间**: 2026年1月3日
**文档版本**: v1.0
