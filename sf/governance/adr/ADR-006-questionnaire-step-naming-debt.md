# ADR-006: 问卷节点命名历史债务记录

- **状态**: 已接受（记录债务，延迟重构）
- **日期**: 2026-03-01
- **影响范围**: `interaction/nodes/progressive_questionnaire.py`, `workflow/main_workflow.py`
- **关联**: ACTION_PLAN.md MT-6

---

## 背景

系统在 v7.87 引入三步递进式问卷，节点顺序基于**业务逻辑演进**：先定核心任务，再补充信息，最后选维度。此顺序在开发中多次调整，最终形成：

```
progressive_step1_core_task  → (LangGraph 节点名)
progressive_step2_radar       → (LangGraph 节点名)
progressive_step3_gap_filling → (LangGraph 节点名)
```

**问题**：代码命名（step1/2/3）与实际执行顺序不一致：

```
实际执行顺序:
  step1_core_task  →  step3_gap_filling  →  step2_radar
  (核心任务确认)      (信息补全)            (偏好雷达图)

代码命名顺序:
  step1  →  step2  →  step3
```

step2（雷达图）在 step3（信息补全）之**后**执行，但名字更小，对维护者极具误导性。

---

## 实际路由链（代码验证结果，2026-03-01）

来源文件：`intelligent_project_analyzer/interaction/nodes/progressive_questionnaire.py`

```python
# step1 出口
L83/L319: goto="progressive_step3_gap_filling"  # ← 跳到 step3！

# step3 出口
L906/L1146: goto="progressive_step2_radar"      # ← 再到 step2

# step2 出口
L574: goto="questionnaire_summary"              # ← 结束问卷循环
```

---

## 历史原因分析

- v7.80 初始设计：step1=核心任务，step2=信息补全，step3=维度选择（顺序正确）
- v7.146 重构：将"信息补全"与"维度选择"的依赖关系反转（先补全信息再激活雷达图语义更准确）
- 节点**字符串标识符**未同步重命名（改名会破坏 checkpoint 兼容性、server.py 事件推送、前端状态机）
- 此后多版本以"兼容优先"策略沿用了错误的命名

---

## 决策

**短期（本轮 Phase 1）：文档化债务，不改代码**

原因：
1. LangGraph checkpoint 中已持久化节点名（重命名 = 历史会话断流）
2. `server.py` 的 WebSocket 事件推送硬编码了节点名
3. 前端 `frontend-nextjs/` 的进度显示依赖节点名字符串
4. 任意遗漏→运行时 KeyError，无静态检查

**中期（MT-6 里程碑）：atomic 重命名**

所有以下操作必须在**同一次提交**中完成：

| 文件 | 变更 |
|------|------|
| `main_workflow.py` add_node 调用 | `step3_gap_filling` → `step1_info_gather`, `step2_radar` → `step2_radar`（可保留）或改名 |
| `progressive_questionnaire.py` goto 字符串 | 同步更新 |
| `api/server.py` WebSocket 事件节点名 | 同步更新 |
| `frontend-nextjs/` 节点名引用 | 全局搜索替换 |
| LangGraph checkpoint 迁移脚本 | 处理已有 checkpoint 的键名映射 |
| 测试固件 | 更新期望节点名 |
| `tests/structural/test_graph_structure.py` | 更新 critical_nodes 集合 |

---

## 正确的业务顺序（代码注释目标态）

```
用户需求输入
  ↓
[step1] 核心任务确认 (progressive_step1_core_task)
  ↓ 信息不足时
[step2] 信息补全/gap filling (★ 当前命名 step3)
  ↓ 补全完成后
[step3] 偏好雷达图维度选择 (★ 当前命名 step2)
  ↓
需求洞察摘要 (questionnaire_summary)
```

---

## 即时行动（无风险，本轮已执行）

在 `progressive_questionnaire.py` 文件头注释处添加业务顺序说明，
帮助维护者理解实际执行顺序（不修改任何功能代码）。

---

## 影响

| 受影响方 | 影响级别 | 内容 |
|--------|---------|------|
| 新开发者 | 高 | 阅读代码时对执行顺序产生误判 |
| 调试日志 | 中 | 日志中 step2/step3 顺序与直觉相反 |
| 故障排查 | 中 | 依赖 checkpoint 回放时顺序混乱 |
| 运行时行为 | 无 | 逻辑完整，无功能缺陷 |

---

## 参考

- [ADR-001](ADR-001.md): analysis_review 废弃决策（同类命名/死路由问题）
- [ACTION_PLAN.md](../ACTION_PLAN.md) MT-6: 节点重命名执行计划
