# 智能项目分析系统 - Next.js 前端

这是基于 Next.js + React + TypeScript 的前端项目，用于替代 Streamlit 提供更好的并发支持和用户体验。

## 安装依赖

```bash
npm install
```

## 启动开发服务器

```bash
npm run dev
```

打开浏览器访问 [http://localhost:3000](http://localhost:3000)

## 构建生产版本

```bash
npm run build
npm start
```

## 技术栈

- **Next.js 14** - React 框架
- **TypeScript** - 类型安全
- **Tailwind CSS** - 样式框架
- **Zustand** - 状态管理
- **Axios** - HTTP 客户端
- **Lucide React** - 图标库

## 项目结构

```
frontend-nextjs/
├── app/                    # Next.js 页面
│   ├── page.tsx           # 首页（输入需求）
│   ├── analysis/          # 分析页面
│   └── layout.tsx         # 全局布局
├── components/            # React 组件
├── lib/                   # API 通信层
│   └── api.ts            # FastAPI 接口封装
├── store/                 # Zustand 状态管理
│   └── useWorkflowStore.ts
├── types/                 # TypeScript 类型定义
│   └── index.ts
└── package.json           # 依赖配置
```

## 环境变量

创建 `.env.local` 文件：

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 注意事项

1. 确保后端 FastAPI 服务已启动（端口 8000）
2. 后端需要配置 CORS 支持跨域请求
3. 开发环境使用轮询方式获取状态，生产环境将使用 WebSocket

## 下一步开发

- [ ] 添加 WebSocket 实时通信
- [ ] 实现工作流可视化（React Flow）
- [ ] 添加审核交互界面
- [ ] 优化报告展示页面
