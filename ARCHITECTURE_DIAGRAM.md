# 🏗️ 架构设计文档 - 多页面胶囊导航

## 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Intelligent Project Analyzer               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────┐  ┌────────────────────────────────────┐  ┌─────────────┐ │
│  │ 胶囊 │  │   中间内容区（CockpitPanel）      │  │   右侧对话  │ │
│  │ 导航 │  │                                  │  │    区域     │ │
│  ├──────┤  ├────────────────────────────────────┤  ├─────────────┤ │
│  │      │  │                                  │  │             │ │
│  │🔵项目│  │ Content changes based on        │  │ Message     │ │
│  │📄    │  │ selected capsule:               │  │ input box   │ │
│  │      │  │                                  │  │             │ │
│  │🟢资源│  │ • files → Project cards        │  │ Right side  │ │
│  │📚    │  │ • assets → Resources           │  │ content is  │ │
│  │      │  │ • board → References           │  │ NEVER       │ │
│  │🟣参考│  │ • experts → Expert advice      │  │ covered     │ │
│  │🖼️    │  │ • insight → Knowledge graph    │  │             │ │
│  │      │  │                                  │  │             │ │
│  │🟡高参│  │ Dynamic content panel:          │  │             │ │
│  │👥    │  │ Click to switch pages           │  │             │ │
│  │      │  │                                  │  │             │ │
│  │🟣思考│  │                                  │  │             │ │
│  │💭    │  │                                  │  │             │ │
│  │      │  │                                  │  │             │ │
│  ├──────┤  ├────────────────────────────────────┤  ├─────────────┤ │
│  │References              │ Project context tags and user input    │ │
│  │ @项目文件              │                                        │ │
│  │ @资源库 ×              │                                        │ │
│  │ @思考概念 ×            │                                        │ │
│  └──────┘  └────────────────────────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

## 组件树结构

```
AnalysisPage
  ├── 左侧面板 (width: 50%)
  │   ├── 胶囊导航按钮组
  │   │   ├── FileStack (项目文件)
  │   │   ├── Library (资源助手)
  │   │   ├── Image (参考画布)
  │   │   ├── Bot (高参助手)
  │   │   └── Network (思考助手)
  │   │
  │   ├── CockpitPanel ← 多页面主组件
  │   │   ├── 条件渲染 (switch moduleKey)
  │   │   ├── insight → KnowledgeGraphCanvas
  │   │   │   ├── Canvas (黑色背景)
  │   │   │   ├── 节点绘制
  │   │   │   └── 事件处理 (onNodeClick)
  │   │   │
  │   │   ├── files → CardList
  │   │   │   ├── 项目卡片（6项）
  │   │   │   └── 事件处理 (onCardClick)
  │   │   │
  │   │   ├── assets → CardList
  │   │   │   ├── 资源卡片（6项）
  │   │   │   └── 事件处理
  │   │   │
  │   │   ├── board → CardList
  │   │   │   ├── 参考卡片（6项）
  │   │   │   └── 事件处理
  │   │   │
  │   │   └── experts → CardList
  │   │       ├── 专家卡片（6项）
  │   │       └── 事件处理
  │   │
  │   └── 引用标签区
  │       ├── 标签列表
  │       └── 移除按钮
  │
  └── 右侧面板 (flex-1)
      ├── 顶部导航栏
      ├── ConversationChat 或 ProjectContent
      ├── 消息列表
      └── 输入框
```

## 数据流示意

### 用户交互流程

```
用户点击胶囊
    ↓
setActiveCockpitModule(moduleKey)
    ↓
state 更新
    ↓
CockpitPanel 重新渲染
    ↓
switch (moduleKey) 执行对应的 renderContent()
    ↓
中间区显示新内容
```

### 引用流程

```
用户点击卡片或节点
    ↓
onNodeClick() 或 onCardClick() 触发
    ↓
injectReferenceToRight(label)  ← 已有函数
    ↓
标签加入 cockpitContextRefs 数组
    ↓
@标签 显示在左下角引用区
    ↓
右侧对话可使用此引用
    ↓
标签点击 ×
    ↓
removeReference(label)  ← 已有函数
    ↓
引用祛除
```

## 状态管理

```typescript
// 胶囊选择状态（已存在）
const [activeCockpitModule, setActiveCockpitModule] = 
  useState<CockpitModuleKey>('insight');

// 引用标签状态（已存在）
const [cockpitContextRefs, setCockpitContextRefs] = 
  useState<string[]>([]);

// 对话消息状态（已存在）
const [conversationMessages, setConversationMessages] = 
  useState<ChatMessage[]>([]);
```

## 页面渲染逻辑

### 之前（单一页面）
```
activeCockpitModule 变化
    ↓
(未使用，全是知识图谱)
    ↓
始终显示 KnowledgeGraphCanvas
```

### 现在（多页面）
```
activeCockpitModule 变化
    ↓
<CockpitPanel moduleKey={activeCockpitModule} />
    ↓
switch (moduleKey) {
  case 'insight': return <KnowledgeGraphCanvas ... />
  case 'files': return <CardList data={projectFiles} ... />
  case 'assets': return <CardList data={resources} ... />
  case 'board': return <CardList data={references} ... />
  case 'experts': return <CardList data={experts} ... />
}
```

## 样式布局

### 左侧胶囊（50% 宽）

```
⬜ 胶囊导航区（宽度：固定 48px）
│  - 竖排排列 5 个胶囊按钮
│  - 选中时变大变彩色
│  - 未选中时变小变灰色
│
⬜ 内容区（宽度：calc(100% - 48px)）
│  - padding: clamp(44px, 3.2vw, 72px)
│  - overflow-y: auto（仅 files/assets/board/experts）
│  - overflow: hidden（insight 使用 Canvas 全屏）
│
⬜ 引用标签区（高度：44px）
│  - 水平滚动或换行
│  - 显示已引用的标签
```

### 右侧对话（flex-1）

```
⬜ 顶部导航栏（高度：48px）
│
⬜ 消息列表（flex-1）
│  - 对话态：ConversationChat 组件
│  - 项目态：ProjectContent 组件
│  - padding: adaptive (clamp 计算）
│
⬜ 输入框（高度：auto）
│  - 浮动输入
│  - width: min(1060px, calc(100vw - 64px))
```

## 色彩与样式对应

```
🔵 项目文件  → sky-500/95   → FileStack icon
🟢 资源助手  → emerald-400/95 → Library icon
🟣 参考画布  → fuchsia-500/95 → Image icon
🟡 高参助手  → amber-300/95   → Bot icon
🟣 思考助手  → violet-500/95  → Network icon
```

## 键盘快捷键（可选扩展）

```
Ctrl+1 → 项目文件
Ctrl+2 → 资源助手
Ctrl+3 → 参考画布
Ctrl+4 → 高参助手
Ctrl+5 → 思考助手

Ctrl+K → 打开搜索
( / )  → 快速引用选中内容
```

## 响应式行为

### 桌面 (> 1024px)
```
左50% | 右50%
- 左侧胶囊+内容始终可见
- 右侧对话完整显示
- 最优体验
```

### 平板 (768-1024px)
```
左40% | 右60%
- 左侧内容可能需要滚动
- 右侧对话缩小
- 仍可完全操作
```

### 手机 (< 768px)
```
左胶囊栏 | 右内容 (切换式)
- 胶囊竖排在左
- 内容和对话区右侧（切换显示）
- 需要增强的 tap 事件处理
```

## 性能优化

### 当前优化
- Canvas 知识图谱：原生渲染 (60fps)
- 卡片列表：React 列表虚拟化可选
- 引用标签：轻量级 state

### 可选优化
- 懒加载卡片数据 (API 分页)
- 搜索/过滤功能 (客户端+服务端)
- 缓存内容数据 (useQuery/SWR)
- 图片懒加载 (参考画册)

## 扩展概念

### 新增页面示例

```typescript
// 未来可轻松添加新页面

type CockpitModuleKey = 
  | 'files'           // ✅ 已有
  | 'assets'          // ✅ 已有
  | 'board'           // ✅ 已有
  | 'experts'         // ✅ 已有
  | 'insight'         // ✅ 已有
  | 'timeline'        // 🔜 项目时间线
  | 'budget'          // 🔜 预算跟踪
  | 'team'            // 🔜 团队协作
  | 'documents';      // 🔜 文档管理
```

---

**架构类型**: 组件化、多页面设计  
**设计模式**: Compound Components + State-based Rendering  
**复杂度**: 低 (切换逻辑简单)  
**扩展性**: 高 (只需添加 case 分支)
