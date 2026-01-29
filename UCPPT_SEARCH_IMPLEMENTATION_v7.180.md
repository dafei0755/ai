# ucppt 深度迭代搜索实现 (v7.180)

> 借鉴 ucppt 的21轮迭代搜索范式，将当前系统从"预设流程执行器"升级为"自主探索引擎"


## 🎯 核心改进

### 与传统5轮搜索的对比

| 维度 | 原5轮搜索 | ucppt搜索 |
|------|----------|--------------|
| 轮次控制 | 固定5轮 | 动态1-30轮 |
| 停止条件 | 执行完5轮 | 置信度≥0.8 或 无新信息 |
| 搜索策略 | 预设模式（概念→维度→学术→案例→数据）| 动态生成（根据信息缺口调整）|
| 反思评估 | 无 | 每轮用gpt-4o-mini评估 |
| 知识结构 | 平面列表 | 树状框架（概念→维度→证据）|
| 进度可见性 | 无 | 实时SSE推送 |
| 深度钻取 | 无 | 发现关键概念后自动深挖 |


## 📁 新增文件

### 后端

1. **[ucppt_search_engine.py](intelligent_project_analyzer/services/ucppt_search_engine.py)**
   - ucppt深度迭代搜索引擎
   - 30轮动态搜索
   - 知识框架构建
   - 反思-搜索循环
   - gpt-4o-mini反思 + gpt-4o整合

2. **[ucppt_search_node.py](intelligent_project_analyzer/workflow/nodes/ucppt_search_node.py)**
   - LangGraph工作流节点封装
   - 可配置max_rounds和confidence_threshold

3. **[search_routes.py](intelligent_project_analyzer/api/search_routes.py)** (修改)
   - 新增 `/api/search/ucppt/stream` 端点
   - SSE流式返回搜索进度

### 前端

4. **[UcpptSearchProgress.tsx](frontend-nextjs/components/search/UcpptSearchProgress.tsx)**
   - 实时搜索进度面板
   - 知识框架可视化
   - 轮次状态列表
   - 置信度进度条
   - 答案流式展示

### 配置

5. **[search_strategy.yaml](config/search_strategy.yaml)** (修改)
   - 新增 `ucppt_search` 配置块
   - 可配置轮数、阈值、模型等


## 🔧 使用方式

### 1. API调用

```bash
# 流式深度搜索
curl -X POST http://localhost:8000/api/search/ucppt/stream \
  -H "Content-Type: application/json" \
  -d '{
    "query": "从一代创业者的视角，给出设计概念：深圳湾海景别墅",
    "max_rounds": 30,
    "confidence_threshold": 0.8
  }'
```

### 2. 前端组件

```tsx
import { UcpptSearchProgress } from '@/components/search';

<UcpptSearchProgress
  query="深圳湾海景别墅设计"
  maxRounds={30}
  confidenceThreshold={0.8}
  onComplete={(result) => console.log('完成', result)}
/>
```

### 3. LangGraph工作流

```python
from intelligent_project_analyzer.workflow.nodes.ucppt_search_node import (
    ucppt_search_node,
    create_ucppt_search_node,
)

# 添加到工作流
workflow.add_node("ucppt_search", ucppt_search_node)
# 或使用配置化版本
workflow.add_node("ucppt_search", create_ucppt_search_node(max_rounds=20))
```


## 📊 SSE事件类型

| 事件 | 数据 | 说明 |
|------|------|------|
| `phase` | `{phase, phase_name, message}` | 搜索阶段变化 |
| `framework` | `{core_concepts, dimensions, initial_gaps}` | 知识框架 |
| `round_start` | `{round, total, topic, query, confidence}` | 轮次开始 |
| `round_sources` | `{round, sources_count, new_concepts, sources}` | 搜索结果 |
| `round_reflecting` | `{round, status, message}` | 反思中 |
| `round_complete` | `{round, confidence, confidence_delta, should_continue, gaps, reasoning}` | 轮次完成 |
| `search_complete` | `{reason, total_rounds, final_confidence}` | 搜索阶段结束 |
| `drill_start` | `{round, concept, query}` | 深度钻取开始 |
| `drill_complete` | `{round, concept, sources_count}` | 深度钻取完成 |
| `answer_chunk` | `{content}` | 答案片段（流式）|
| `done` | `{total_rounds, total_sources, final_confidence, execution_time}` | 全部完成 |
| `error` | `{message}` | 错误 |


## 🔬 四阶段搜索流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Phase 1: 框架构建                                │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ 分析问题 → 提取核心概念 → 识别知识维度 → 发现信息缺口           │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────────┐
│                     Phase 2: 迭代搜索（最多30轮）                     │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐      │
│  │ 生成查询  │ → │ 执行搜索  │ → │ 更新框架  │ → │ 反思评估  │      │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘      │
│        ↑                                              │             │
│        └──────────── 置信度 < 0.8 ────────────────────┘             │
└─────────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────────┐
│                     Phase 3: 深度钻取（可选）                         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ 识别低置信度概念 → 生成专项查询 → 深入探索 → 更新概念状态       │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────────┐
│                     Phase 4: 整合输出                                │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ 综合所有结果 → 构建知识图谱 → 流式生成答案 → 返回最终报告       │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```


## 💰 成本优化



## 📈 性能预期

| 场景 | 轮数 | 耗时 | 来源数 |
|------|------|------|--------|
| 简单问题 | 3-5轮 | 30-60s | 20-40 |
| 中等问题 | 8-12轮 | 60-120s | 50-100 |
| 复杂问题 | 15-25轮 | 120-300s | 100-200 |
| 极复杂问题 | 25-30轮 | 300-600s | 150-300 |


## 🚀 下一步

1. **前端集成**: 在首页添加"深度搜索"模式切换
2. **历史记录**: 持久化搜索结果和知识框架
3. **知识图谱**: 可视化概念关系
4. **用户中断**: 支持手动调整搜索方向
5. **缓存优化**: 相似问题复用已有框架


## 📝 配置参考

```yaml
# config/search_strategy.yaml

ucppt_search:
  enabled: true
  max_rounds: 30
  min_rounds: 3
  confidence_threshold: 0.80

  models:
    reflect: "gpt-4o-mini"
    framework: "gpt-4o-mini"
    synthesis: "gpt-4o"

  reflection:
    enabled: true
    stop_conditions:
      confidence_reached: true
      no_new_info_rounds: 2
      max_rounds_reached: true

  deep_drilling:
    enabled: true
    max_drill_concepts: 3
    drill_threshold: 0.6
```


**作者**: AI Assistant
**日期**: 2026-01-10
**版本**: v7.180
