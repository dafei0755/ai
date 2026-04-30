# 2 平面推演

版本：v0.1  
日期：2026-04-29  
状态：主架构已确定；后端 Phase 0 与前端同步已完成第一步

## 一句话定位

平面推演不是 CAD 绘图工具，也不是图纸识别工具，而是空间方案的推演场。

它的任务是：

```text
基于 ProjectContext、真实图纸、用户目标和平台方法论，
生成多种成立的空间布局路径，
让用户选择、锁定、修改、融合和回退，
并把每一次选择沉淀为平台的设计判断数据。
```

## 核心原则

1. 用户主导题目和裁决。
2. 系统负责提出选项、解释依据、提示风险和记录后果。
3. 多版本不是多张图，而是多种空间判断。
4. 几何不追求施工级精度，但空间语义、约束关系和版本来源必须清楚。
5. LLM 不直接画平面，只负责意图理解、策略生成、指令解析和高参解释。
6. 生成结果必须可比较、可回退、可融合、可沉淀。

## 系统主链

```text
标准入口：
项目底盘 / ProjectContext
→ FloorPlanFacts / 结构事实
→ DesignConstraintGraph / 设计约束图
→ DesignIntentSet / 多策略意图
→ LayoutVariant / 多版本布局
→ 高参解释与 Diff
→ 用户选择 / 指令推演
→ LayoutVersionGraph / 版本图谱
→ ProjectBasePatch / 底盘补丁
→ 用户确认
→ 项目底盘升版
```

```text
快速入口：
图纸 / 对话
→ ProjectSeed
→ 底盘缺口卡 / 假设链
→ 轻底盘 ProjectContext
→ Exploratory 平面推演
→ ProjectBasePatch
→ 用户确认后回填项目底盘
```

## 与竞品边界

酷家乐偏绘制、建模、素材、渲染与成交。

qbiq偏空间规划交付包、办公/商业 test-fit 和快速交付。

Finch偏规则驱动的建筑生成与合规反馈。

本系统应聚焦：

```text
中文语境下的高参式空间推演：
多策略、多版本、可解释、用户可主导、过程可沉淀。
```

## 当前已落地

后端：

```text
intelligent_project_analyzer/core/domain_objects.py
intelligent_project_analyzer/services/floor_plan_layout_engine.py
intelligent_project_analyzer/api/routes/floor_plan_layout_routes.py
```

前端：

```text
frontend-nextjs/app/api/floor-plan/generate-variants/route.ts
frontend-nextjs/components/PlanSandboxPanel.tsx
```

测试：

```text
tests/services/test_floor_plan_layout_engine.py
```

## 本目录文档

```text
01-平面推演产品定义.md
02-FloorPlan双向编译器架构.md
03-接口与数据契约.md
04-实施记录与下一步.md
05-模拟平面推演-山地民宿深层脚本.md
06-平面推演与项目底盘关系及协议.md
```
