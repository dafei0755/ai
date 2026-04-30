# Next.js 前端启动指南

## ✅ 阶段 1 完成情况

所有基础框架已创建完成！现在可以开始测试了。

## 📦 步骤 1：安装 Node.js（如果还没有）

1. 访问 https://nodejs.org/
2. 下载 LTS 版本（推荐 18.x 或 20.x）
3. 安装完成后验证：

```cmd
node --version
npm --version
```

## 🚀 步骤 2：安装前端依赖

```cmd
cd d:\11-20\langgraph-design\frontend-nextjs
npm install
```

**预计安装时间**：2-5 分钟（取决于网络速度）

如果遇到网络问题，可以使用淘宝镜像：
```cmd
npm install --registry=https://registry.npmmirror.com
```

## ▶️ 步骤 3：启动服务

### 3.1 启动后端（确保已启动）

在项目根目录打开一个命令行窗口：
```cmd
cd d:\11-20\langgraph-design
python intelligent_project_analyzer\api\server.py
```

确认看到：
```
✅ 服务器启动成功
📍 API 文档: http://localhost:8000/docs
```

### 3.2 启动前端

在另一个命令行窗口：
```cmd
cd d:\11-20\langgraph-design\frontend-nextjs
npm run dev
```

应该看到：
```
  ▲ Next.js 14.2.5
  - Local:        http://localhost:3000
  
✓ Ready in 3.2s
```

## 🧪 步骤 4：测试流程

1. **打开浏览器**，访问 http://localhost:3000

2. **输入测试需求**：
   ```
   我需要为一个150㎡的三代同堂家庭设计住宅空间
   ```

3. **点击"开始分析"按钮**

4. **验证跳转**：
   - 应该自动跳转到 `/analysis/[session_id]` 页面
   - URL 示例：`http://localhost:3000/analysis/api-20251127xxxxxx`

5. **观察实时更新**：
   - 会话 ID 正确显示
   - 状态每 2 秒更新一次
   - 进度条实时变化
   - 活跃 Agent 列表显示

## ✅ 验证清单

请确认以下所有项目：

- [ ] Node.js 已安装（node --version 有输出）
- [ ] npm install 成功完成（无红色错误）
- [ ] 后端服务已启动（http://localhost:8000/docs 可访问）
- [ ] 前端服务已启动（http://localhost:3000 可访问）
- [ ] 首页正常显示（标题、输入框、按钮）
- [ ] 输入需求后可以点击按钮
- [ ] 点击后跳转到分析页面
- [ ] 分析页面显示会话信息
- [ ] 状态每 2 秒自动刷新

## 🐛 常见问题解决

### 问题 1：npm install 失败

**症状**：出现红色 ERR! 信息

**解决方案**：
```cmd
# 清除缓存
npm cache clean --force

# 使用淘宝镜像
npm install --registry=https://registry.npmmirror.com
```

### 问题 2：端口 3000 被占用

**症状**：Port 3000 is already in use

**解决方案**：
```cmd
# 使用其他端口
npm run dev -- -p 3001
```

然后访问 http://localhost:3001

### 问题 3：CORS 跨域错误

**症状**：浏览器控制台显示 CORS policy blocked

**解决方案**：
FastAPI 已配置 CORS，如果仍有问题，检查：
1. 后端是否正常启动（访问 http://localhost:8000/docs）
2. 浏览器控制台的具体错误信息

### 问题 4：点击按钮无反应

**症状**：点击"开始分析"没有跳转

**解决方案**：
1. 打开浏览器开发者工具（F12）
2. 查看 Console 标签的错误信息
3. 查看 Network 标签，确认是否发送了请求
4. 复制错误信息反馈给我

### 问题 5：TypeScript 报错

**症状**：红色波浪线或编译错误

**解决方案**：
```cmd
# 重新生成类型文件
npm run build

# 如果还有问题，删除缓存重试
rd /s /q .next
npm run dev
```

## 📸 期望效果截图说明

### 首页应该看到：
- 标题："智能项目分析系统"
- 副标题："基于 LangGraph 多智能体协作，提供专业的设计分析"
- 大文本输入框（6 行）
- 蓝色按钮："开始分析"
- 示例需求提示框（蓝色背景）

### 分析页面应该看到：
- 标题："智能分析进行中"
- 会话 ID 显示
- 状态显示（initializing/running/completed）
- 进度条（如果有进度数据）
- 活跃 Agent 列表（如果有）
- 黄色提示框："工作流可视化将在下一阶段实现"

## 🎯 下一步

完成测试后，请告诉我：

1. **所有步骤是否成功？** （是/否）
2. **遇到的具体错误**（如果有，完整复制错误信息）
3. **截图或描述看到的界面**

确认无误后，我们将进入 **阶段 2**：
- WebSocket 实时通信
- React Flow 工作流可视化
- 交互式审核界面

## 💡 提示

- 前端和后端需要同时运行
- 修改代码后 Next.js 会自动热重载（无需重启）
- 浏览器开发者工具（F12）是调试的好帮手
- 如有任何问题，随时反馈！
