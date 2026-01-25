# 搜索过滤器（黑白名单）功能说明

> **版本**: v1.0.0
> **创建日期**: 2026-01-04
> **功能**: 管理搜索结果的黑名单（屏蔽）和白名单（优先推荐）

---

## 📋 功能概述

搜索过滤器允许管理员通过黑白名单机制控制搜索结果质量：

- **黑名单** 🚫: 完全过滤指定域名的搜索结果
- **白名单** ⭐: 优先搜索推荐优质域名的内容（提升展示优先级）

### 核心特性

1. ✅ 支持三种匹配规则：完整域名、通配符、正则表达式
2. ✅ 优先级规则：黑名单 > 白名单 > 默认可信域名
3. ✅ 实时生效，支持配置热重载
4. ✅ 完整的管理后台界面
5. ✅ 批注功能，记录添加原因

---

## 🚀 快速开始

### 1. 访问管理后台

```
前端地址: http://localhost:3000/admin/search-filters
API文档: http://localhost:8000/docs#/admin
```

**权限要求**: 需要管理员身份登录

### 2. 添加黑名单

#### 方式一：通过管理界面

1. 访问 `/admin/search-filters`
2. 切换到 "🚫 黑名单" 标签
3. 点击 "➕ 添加规则"
4. 填写域名和备注
5. 点击 "确认添加"

#### 方式二：通过 API

```bash
# 添加完整域名到黑名单
curl -X POST "http://localhost:8000/api/admin/search-filters/blacklist?domain=spam-site.com&match_type=domains&note=低质量内容" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# 添加通配符模式
curl -X POST "http://localhost:8000/api/admin/search-filters/blacklist?domain=*.ads.com&match_type=patterns&note=广告站" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 3. 添加白名单

```bash
# 添加优质站点到白名单
curl -X POST "http://localhost:8000/api/admin/search-filters/whitelist?domain=archdaily.com&match_type=domains&note=权威设计媒体" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 4. 测试过滤器

```bash
# 测试 URL 是否会被过滤
curl "http://localhost:8000/api/admin/search-filters/test?url=https://spam-site.com/page" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## 📚 匹配规则详解

### 1. 完整域名匹配（`domains`）

**用途**: 精确匹配特定域名

**示例**:
```yaml
blacklist:
  domains:
    - "example-spam.com"  # 只匹配 example-spam.com
    - "low-quality.net"
```

**匹配结果**:
- ✅ `https://example-spam.com/page` - 匹配
- ✅ `https://example-spam.com/article` - 匹配
- ❌ `https://sub.example-spam.com` - 不匹配（需要使用通配符）

### 2. 通配符匹配（`patterns`）

**用途**: 匹配一组相似域名

**语法**: 使用 `*` 表示任意字符

**示例**:
```yaml
blacklist:
  patterns:
    - "*.spam-domain.com"   # 匹配所有子域名
    - "ads-*.example.net"   # 匹配 ads- 开头的子域名
    - "*.*.ads.com"         # 匹配两级子域名
```

**匹配结果**:
- ✅ `banner.spam-domain.com` - 匹配 `*.spam-domain.com`
- ✅ `ads-popup.example.net` - 匹配 `ads-*.example.net`
- ❌ `spam-domain.com` - 不匹配（没有子域名）

### 3. 正则表达式匹配（`regex`）

**用途**: 复杂匹配规则

**语法**: 标准 Python 正则表达式

**示例**:
```yaml
blacklist:
  regex:
    - "^.*\\.spam-.*\\.com$"      # 包含 spam- 的子域名
    - "^(ads|banner|popup)\\."    # 特定前缀的域名
```

**匹配结果**:
- ✅ `ads.spam-site.com` - 匹配第一个规则
- ✅ `banner.example.com` - 匹配第二个规则

---

## 🎯 使用场景

### 场景 1：屏蔽低质量内容站

**问题**: 某些聚合站点内容质量差，广告多

**解决方案**:
```bash
# 添加到黑名单
POST /api/admin/search-filters/blacklist
?domain=content-farm.com
&match_type=domains
&note=内容农场，质量差
```

### 场景 2：优先展示权威媒体

**问题**: 希望优先展示 ArchDaily、Dezeen 等权威设计媒体

**解决方案**:
```bash
# 添加到白名单
POST /api/admin/search-filters/whitelist
?domain=archdaily.com&match_type=domains
POST /api/admin/search-filters/whitelist
?domain=dezeen.com&match_type=domains
```

### 场景 3：批量屏蔽广告域名

**问题**: 屏蔽所有 `ads-` 开头的子域名

**解决方案**:
```bash
# 使用通配符模式
POST /api/admin/search-filters/blacklist
?domain=ads-*.*
&match_type=patterns
&note=广告子域名
```

### 场景 4：临时屏蔽问题站点

**问题**: 某站点临时出现问题，需要暂时屏蔽

**解决方案**:
```bash
# 添加到黑名单
POST /api/admin/search-filters/blacklist
?domain=problematic-site.com
&note=临时屏蔽，2026-01-10 后移除
```

---

## 📡 API 接口文档

### 1. 获取配置

```http
GET /api/admin/search-filters
Authorization: Bearer {jwt_token}
```

**响应示例**:
```json
{
  "status": "success",
  "data": {
    "blacklist": {
      "domains": ["spam.com"],
      "patterns": ["*.ads.com"],
      "regex": [],
      "notes": {
        "spam.com": "低质量内容"
      }
    },
    "whitelist": {
      "domains": ["archdaily.com"],
      "boost_score": 0.3
    },
    "statistics": {
      "blacklist": {"total": 2},
      "whitelist": {"total": 1}
    }
  }
}
```

### 2. 添加到黑名单

```http
POST /api/admin/search-filters/blacklist?domain={domain}&match_type={type}&note={note}
Authorization: Bearer {jwt_token}
```

**参数**:
- `domain` (必填): 域名或模式
- `match_type` (必填): `domains` | `patterns` | `regex`
- `note` (可选): 备注说明

### 3. 从黑名单移除

```http
DELETE /api/admin/search-filters/blacklist?domain={domain}&match_type={type}
Authorization: Bearer {jwt_token}
```

### 4. 添加到白名单

```http
POST /api/admin/search-filters/whitelist?domain={domain}&match_type={type}&note={note}
Authorization: Bearer {jwt_token}
```

### 5. 从白名单移除

```http
DELETE /api/admin/search-filters/whitelist?domain={domain}&match_type={type}
Authorization: Bearer {jwt_token}
```

### 6. 测试过滤器

```http
GET /api/admin/search-filters/test?url={url}
Authorization: Bearer {jwt_token}
```

**响应示例**:
```json
{
  "status": "success",
  "data": {
    "url": "https://spam.com/page",
    "is_blacklisted": true,
    "is_whitelisted": false,
    "will_be_blocked": true,
    "boost_score": 0,
    "priority_rule": "黑名单优先（黑名单 > 白名单）"
  }
}
```

### 7. 重载配置

```http
POST /api/admin/search-filters/reload
Authorization: Bearer {jwt_token}
```

---

## ⚙️ 配置文件

### 配置文件位置

```
config/search_filters.yaml
```

### 配置结构

```yaml
# 黑名单
blacklist:
  domains:          # 完整域名列表
    - "spam.com"
  patterns:         # 通配符模式列表
    - "*.ads.com"
  regex:            # 正则表达式列表
    - "^.*\\.spam-.*\\.com$"
  notes:            # 备注说明
    "spam.com": "2026-01-04 添加 - 低质量内容"

# 白名单
whitelist:
  domains:
    - "archdaily.com"
  patterns:
    - "*.edu.cn"
  regex: []
  boost_score: 0.3  # 提升分数（默认 +0.3）
  notes:
    "archdaily.com": "权威设计媒体"

# 生效范围
scope:
  tools:            # 应用到哪些搜索工具
    - "tavily"
    - "serper"
    - "bocha"
  enabled: true     # 是否启用
  priority: "blacklist_first"  # 优先级规则

# 元信息
metadata:
  version: "1.0.0"
  last_updated: "2026-01-04T00:00:00Z"
  updated_by: "admin"
```

### 手动编辑配置

1. 编辑 `config/search_filters.yaml`
2. 访问管理后台，点击 "🔄 重载配置"
3. 或调用 API: `POST /api/admin/search-filters/reload`

---

## 🔍 工作原理

### 搜索结果处理流程

```
原始搜索结果
    ↓
Step 0: 🚫 黑名单过滤（完全移除）
    ↓
Step 1: 相关性过滤
    ↓
Step 2: 内容完整性过滤
    ↓
Step 3: 去重
    ↓
Step 4: 可信度评估 + 质量评分
    ↓
Step 5: ⭐ 白名单优先级提升（+0.3 分）
    ↓
Step 6: 排序（按质量分数降序）
    ↓
最终结果
```

### 优先级规则

1. **黑名单优先**: 即使域名在白名单，黑名单仍然生效
2. **白名单提升**: 白名单域名获得额外 +0.3 分（可配置）
3. **默认可信域名**: 内置的 `TRUSTED_DOMAINS`（最低优先级）

---

## 🧪 测试

### 运行单元测试

```bash
# 运行所有测试
pytest tests/test_search_filter_manager.py -v

# 运行特定测试
pytest tests/test_search_filter_manager.py::TestSearchFilterManager::test_add_to_blacklist -v
```

### 手动测试

```bash
# 1. 添加黑名单
curl -X POST "http://localhost:8000/api/admin/search-filters/blacklist?domain=test-spam.com&match_type=domains" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 2. 测试是否生效
curl "http://localhost:8000/api/admin/search-filters/test?url=https://test-spam.com/page" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 3. 移除黑名单
curl -X DELETE "http://localhost:8000/api/admin/search-filters/blacklist?domain=test-spam.com&match_type=domains" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## ⚠️ 注意事项

### 1. 黑名单误杀

**风险**: 黑名单配置错误可能过滤优质内容

**建议**:
- 使用 "测试过滤器" 功能预览影响
- 添加详细备注，方便后续审核
- 定期审查黑名单规则

### 2. 正则表达式性能

**风险**: 复杂正则表达式可能影响性能

**建议**:
- 优先使用完整域名或通配符
- 正则表达式尽量简单
- 避免过度使用

### 3. 配置热重载

**说明**: 配置修改后需要手动重载或等待自动重载

**触发方式**:
- 通过 API 添加/删除规则（自动保存并重载）
- 手动编辑 YAML 文件（需调用重载 API）

### 4. 权限控制

**重要**: 仅管理员可以修改黑白名单

**验证**: 所有 API 都经过 `require_admin` 中间件验证

---

## 📊 监控与统计

### 查看统计信息

```bash
# 获取黑白名单统计
curl "http://localhost:8000/api/admin/search-filters" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**返回信息**:
- 黑名单数量（按匹配类型分类）
- 白名单数量
- 上次更新时间
- 启用状态

### 日志监控

搜索过滤器会在日志中记录：

```
🚫 黑名单过滤: 移除 3 个结果
⭐ 白名单提升: 2 个结果获得优先级
```

---

## 🔄 后续扩展

### 计划功能

1. **临时规则**: 支持过期时间（如临时屏蔽 7 天）
2. **批量导入**: 支持 CSV/文本批量导入黑白名单
3. **历史记录**: 记录所有配置变更历史
4. **影响预览**: 显示规则影响的历史搜索数量
5. **自动建议**: 基于用户反馈自动建议黑名单
6. **分组管理**: 按项目类型分组管理不同规则

---

## 📞 技术支持

### 常见问题

**Q: 配置修改后多久生效？**
A: 通过 API 修改立即生效。手动编辑 YAML 需要调用重载 API。

**Q: 黑白名单支持 IP 地址吗？**
A: 暂不支持，仅支持域名匹配。

**Q: 可以导出配置吗？**
A: 直接复制 `config/search_filters.yaml` 文件。

**Q: 如何批量导入？**
A: 当前需要手动编辑 YAML 或循环调用 API，批量导入功能计划中。

### 联系方式

- 📧 Email: support@example.com
- 📝 Issues: https://github.com/your-repo/issues
- 💬 Discussions: https://github.com/your-repo/discussions

---

**版本历史**:
- v1.0.0 (2026-01-04): 初始版本发布
