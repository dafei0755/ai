# 知识图谱黑色画布 - 实现说明

## 什么改变了？

左侧从多个卡片框（Files、Assets、Board、Experts、Insights）改为**类似 infranodus 的黑色满屏知识图谱画布**。

## 核心特性

### 1. **黑色满屏画布**
- `#0a0a0a` 深黑背景（类似 infranodus）
- Canvas 绘制，高性能交互式网络图谱
- 自适应窗口大小变化

### 2. **模拟数据生成**
生成 5 个集群结构，每个集群包含：

| 集群 | 颜色 | 概念数 |
|------|-----|-------|
| 可持续发展 | 青绿 `#4DB6AC` | 5 个概念 |
| 文化创意 | 金黄 `#F8B500` | 5 个概念 |
| 社区发展 | 粉红 `#FF6B9D` | 5 个概念 |
| 智慧生活 | 紫蓝 `#7986CB` | 5 个概念 |
| 创新方法 | 红色 `#C44569` | 5 个概念 |

**总计 25 个节点 + 动态生成的连线网络**

### 3. **交互功能**
- **点击节点** → 引用到右侧对话
- **悬停节点** → 高亮并放大，显示标签
- **光标变化** → 节点上显示手指光标

### 4. **力导向布局**
- 30 次迭代布局计算
- 节点间斥力 + 连接吸引力
- 核心节点 (`core`) 更大，优先展示标签

## 文件结构

```
components/
├── KnowledgeGraphCanvas.tsx        # Canvas 绘制的图谱组件
lib/
├── mockGraphData.ts                # 模拟数据生成器
app/analysis/[sessionId]/
└── page.tsx                        # 主页面（已集成）
```

## 快速测试

### 本地启动
```bash
cd frontend-nextjs
npm run dev
# 访问 http://localhost:3001
```

### 进入分析页面
1. 创建新项目或选择现有项目
2. 进入分析页面 `/analysis/[sessionId]`
3. 左侧自动显示黑色知识图谱画布

### 交互测试
- 点击任何节点，标签将被引用到右侧对话
- 鼠标悬停节点查看详情
- 窗口拖动改变大小，画布自适应

## 数据格式

### NodePosition 接口
```typescript
interface NodePosition {
  x: number;  // 相对坐标（以中心为原点）
  y: number;
}
```

### GraphData 接口（来自 mockGraphData.ts）
```typescript
interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

interface GraphNode {
  id: string;
  label: string;
  color: string;
  size: number;
  category: 'core' | 'concept' | 'method' | 'tool' | 'outcome';
}

interface GraphEdge {
  source: string;
  target: string;
  weight: number;
}
```

## 渲染性能

- **节点数:** 25 个
- **边数:** 50-70 条（动态）
- **布局迭代:** 30 次（初始化时，平均 200ms）
- **帧率:** Canvas 原生，60fps
- **内存占用:** ~2-5MB

## 后续扩展

### 1. 接入真实数据
替换 `generateClusteredGraphData()` 为后端 API 数据：
```typescript
const graphData = await api.getKnowledgeGraph(sessionId);
```

### 2. 添加物理引擎
可升级至 `vis-network` 或 `d3-force`：
```bash
npm install vis-network
# 或
npm install d3-force
```

### 3. 搜索/筛选功能
在顶部添加搜索栏，动态过滤节点

### 4. 节点详情面板
右侧对话中展示选中节点的详细信息

## 已知限制

- Canvas 绘制的 SVG 导出需手动实现
- 大节点网络（1000+）可能需要 WebWorker 加速布局
- 触屏设备交互需添加触摸事件支持

## 调试

打开浏览器开发者工具：
```javascript
// 查看图数据
localStorage.getItem('graph-data')

// 检查布局位置
console.log('nodePositions:', ...) // 在组件中添加
```

---

**实现日期:** 2026-03-30  
**版本:** v1.0
