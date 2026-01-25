# 精选案例展示 - WordPress 嵌入指南

## 📋 快速使用

### 步骤 1：复制HTML代码
打开文件：[WORDPRESS_SHOWCASE_EMBED.html](WORDPRESS_SHOWCASE_EMBED.html)

### 步骤 2：配置API地址
在代码中找到配置部分（约第202行），修改为实际地址：

```javascript
// 🔥 配置：修改为你的实际环境地址
const API_URL = 'https://api.yoursite.com';  // 后端API地址
const FRONTEND_URL = 'https://app.yoursite.com';  // Next.js前端地址
```

**本地测试环境：**
```javascript
const API_URL = 'http://localhost:8000';
const FRONTEND_URL = 'http://localhost:3001';  // ⚠️ 3000端口被Milvus Attu占用
```

**生产环境示例：**
```javascript
const API_URL = 'https://www.ucppt.com/api';  // 如果后端部署在WordPress同域名下
const FRONTEND_URL = 'https://app.ucppt.com';  // Next.js前端地址
```

### 步骤 3：嵌入到WordPress
1. 进入WordPress后台编辑 `https://www.ucppt.com/js` 页面
2. 点击"添加区块" → 选择"自定义HTML"
3. 粘贴完整的HTML代码
4. 保存并预览

## 🎨 功能特性

### ✅ 已实现
- ⭐ 从管理后台配置的精选会话中自动加载
- 🖼️ 显示概念图作为案例背景
- 🎡 自动轮播（支持配置间隔时间）
- 📱 响应式设计（支持PC、平板、手机）
- 🎯 点击跳转到完整报告页面
- 🧠 显示"深度思考模式"标签
- 💫 优雅的加载动画和错误提示

### ⚙️ 配置项（来自后端配置）
- `rotation_interval_seconds`: 自动切换间隔（默认5秒）
- `autoplay`: 是否自动播放（默认true）
- `loop`: 是否循环播放（默认true）
- `show_navigation`: 是否显示导航按钮（默认true）
- `show_pagination`: 是否显示分页指示器（默认true）

## 🔧 API 端点

### 后端API
**端点**: `GET /api/showcase/featured`

**返回数据结构**:
```json
{
  "featured_sessions": [
    {
      "session_id": "8pdwoxj8-20260103181555-163e0ad3",
      "title": "现代简约别墅设计",
      "user_input": "我需要设计一个150平米的现代简约风格住宅...",
      "created_at": "2026-01-03T18:15:55",
      "analysis_mode": "deep_thinking",
      "concept_image": {
        "url": "/generated_images/8pdwoxj8-20260103181555-163e0ad3/2-0_1_xxx.png",
        "prompt": "Modern minimalist living room...",
        "owner_role": "2-0",
        "created_at": "2026-01-03T18:21:36"
      },
      "status": "completed"
    }
  ],
  "config": {
    "rotation_interval_seconds": 5,
    "autoplay": true,
    "loop": true,
    "show_navigation": true,
    "show_pagination": true
  }
}
```

## 📸 效果预览

### 轮播展示
- 每张卡片展示一个精选案例
- 概念图作为背景，带渐变遮罩
- 标题、描述、日期信息
- "查看详情"按钮跳转到完整报告

### 响应式布局
- **PC（>1024px）**: 每行显示3个案例
- **平板（640-1024px）**: 每行显示2个案例
- **手机（<640px）**: 每行显示1个案例

## 🐛 故障排查

### 问题1：显示"暂无精选案例"
**原因**: 管理后台未配置精选会话
**解决**:
1. 访问 `http://localhost:3000/admin/showcase-config`
2. 输入要展示的会话ID
3. 点击"保存配置"

### 问题2：显示"加载失败"
**原因**: 无法连接到后端API
**解决**:
1. 检查 `API_URL` 配置是否正确
2. 确认后端服务正在运行
3. 检查浏览器控制台的错误信息
4. 确认CORS配置允许跨域请求

### 问题3：图片不显示
**原因**: 图片路径不正确或CORS问题
**解决**:
1. 检查概念图文件是否存在：`data/generated_images/{session_id}/`
2. 确认后端静态文件服务配置正确
3. 检查图片URL是否可以直接访问

### 问题4：点击卡片无法跳转
**原因**: `FRONTEND_URL` 配置不正确
**解决**:
1. 确认 Next.js 前端地址配置正确
2. 测试报告URL是否可以直接访问：`{FRONTEND_URL}/analysis/{session_id}`

## 🔒 安全建议

### 生产环境部署
1. **启用HTTPS**: 确保API和前端都使用HTTPS
2. **配置CORS**: 限制允许的域名
3. **API鉴权**: 如需要，添加API认证机制

### CORS配置（后端）
在 `server.py` 中添加：
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://www.ucppt.com",
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 📞 技术支持

如遇问题：
1. 检查浏览器控制台日志（F12 → Console）
2. 检查后端服务日志
3. 参考完整文档：[ADMIN_DASHBOARD_GUIDE.md](ADMIN_DASHBOARD_GUIDE.md)
