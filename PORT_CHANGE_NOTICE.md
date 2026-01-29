# ⚠️ 前端端口变更通知

## 变更说明

由于增加了 **Milvus 向量数据库服务**，端口分配发生变化：

### 端口分配

| 服务 | 原端口 | 新端口 | 说明 |
|------|--------|--------|------|
| 前端 Next.js | 3000 | **3001** | ✅ 已更新 |
| Milvus Attu管理界面 | - | **3000** | 🆕 新增 |
| 后端 API | 8000 | 8000 | ✅ 无变化 |
| Grafana 监控 | - | 3200 | ✅ 避免冲突 |

---

## 🔧 需要更新的地方

### ✅ 已自动更新

1. **package.json** - 前端启动端口配置
   ```json
   "dev": "next dev -p 3001",
   "start": "next start -p 3001"
   ```

2. **QUICKSTART.md** - 快速启动文档
   - 所有 `localhost:3000` 已更新为 `localhost:3001`
   - 新增 Milvus 管理界面说明

3. **WordPress 嵌入HTML文件** - 所有嵌入代码
   - `docs/WORDPRESS_SHOWCASE_EMBED.html`
   - `docs/WORDPRESS_SHOWCASE_EMBED_CARDS.html`
   - `docs/WORDPRESS_FIX_TEST.html`
   - `docs/WORDPRESS_SHOWCASE_CLEAN.html`

4. **WORDPRESS_SHOWCASE_GUIDE.md** - WordPress集成文档

### ⚠️ 需要手动更新（如果已部署）

如果你已经在 **WordPress 后台**嵌入了展示页面，需要手动更新：

#### 步骤 1：登录 WordPress 后台
访问：https://www.ucppt.com/wp-admin

#### 步骤 2：编辑嵌入页面
找到包含 Next.js 应用的页面（如 `/nextjs` 或展示案例页面）

#### 步骤 3：修改 JavaScript 配置
找到以下代码：
```javascript
const FRONTEND_URL = 'http://localhost:3000';
```

改为：
```javascript
const FRONTEND_URL = 'http://localhost:3001';  // ⚠️ 3000端口被Milvus占用
```

#### 步骤 4：保存并测试
- 保存页面
- 清除浏览器缓存
- 访问页面验证跳转链接正确

---

## 📝 访问地址更新

### 本地开发环境

| 功能 | 原地址 | 新地址 |
|------|--------|--------|
| 前端界面 | ~~http://localhost:3000~~ | **http://localhost:3001** |
| 用户中心 | ~~http://localhost:3000/user/dashboard~~ | **http://localhost:3001/user/dashboard** |
| 管理后台 | ~~http://localhost:3000/admin~~ | **http://localhost:3001/admin** |
| 知识库管理 | ~~http://localhost:3000/admin/knowledge-base~~ | **http://localhost:3001/admin/knowledge-base** |
| Milvus管理 | - | **http://localhost:3000** (Attu) 🆕 |
| API文档 | http://localhost:8000/docs | http://localhost:8000/docs ✅ |

### 生产环境

**无需修改** - 生产环境通常使用域名而非端口号：
- 前端：https://app.ucppt.com 或 https://ai.ucppt.com
- 后端：https://www.ucppt.com/api 或 https://api.ucppt.com

---

## 🐛 常见问题

### Q1: 访问 localhost:3000 看到的是什么？

现在 **localhost:3000** 显示的是 **Milvus Attu 可视化管理界面**，用于管理向量数据库。

### Q2: 为什么我的链接跳转到 3000 端口？

可能原因：
1. **WordPress 嵌入代码未更新** - 按上述步骤更新 WordPress 后台的 HTML 代码
2. **浏览器缓存** - 清除缓存或使用无痕模式
3. **书签/收藏夹** - 更新已保存的书签地址

### Q3: 如何验证前端是否运行在 3001 端口？

启动前端后，查看终端输出：
```bash
✓ Ready in 1846ms
- Local:        http://localhost:3001  # ← 应显示 3001
```

### Q4: Docker 部署是否受影响？

如果使用 Docker Compose，需要检查：
- `docker-compose.yml` 中的端口映射
- `docker-compose.milvus.yml` 中 Attu 的端口配置

---

## 📚 相关文档

- [QUICKSTART.md](QUICKSTART.md) - 快速启动指南（已更新）
- [WORDPRESS_SHOWCASE_GUIDE.md](docs/WORDPRESS_SHOWCASE_GUIDE.md) - WordPress集成指南（已更新）
- [docker-compose.milvus.yml](docker-compose.milvus.yml) - Milvus 服务配置

---

## ✅ 检查清单

在启动服务前，请确认：

- [ ] 前端 package.json 配置为 3001 端口
- [ ] WordPress 后台嵌入代码已更新（如有）
- [ ] 浏览器书签/收藏夹已更新
- [ ] 测试链接能正确跳转到 3001 端口
- [ ] Milvus 服务正常运行（如需使用知识库功能）

---

**更新日期**: 2026-01-07
**影响版本**: v7.146+（增加 Milvus 服务后）
