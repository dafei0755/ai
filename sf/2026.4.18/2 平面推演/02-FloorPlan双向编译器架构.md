# 02 FloorPlan 双向编译器架构

版本：v0.1  
日期：2026-04-29

## 1. 架构判断

原来的几何编译链路主要回答：

```text
上传的图纸里有什么？
```

平面推演还必须回答：

```text
在这些事实与约束下，可以生成哪些布局？
用户修改后，布局如何继续演化？
```

因此 FloorPlan 链路必须从单向解析升级为双向编译：

```text
解析方向：
CAD / PDF / 人工校正 → FloorPlanFacts

生成方向：
SPG / DesignBrief / 平台方法论 → LayoutIR

推演方向：
LayoutIR + 用户指令 → LayoutIR'
```

## 2. 事实与提案必须分离

当前关键设计是：

```text
FloorPlanFacts 记录事实。
LayoutIR 记录提案。
```

二者共用坐标、可视化和门禁逻辑，但不能共享语义身份。

原因：

```text
图纸识别结果代表“系统认为原始建筑里存在什么”。
布局生成结果代表“系统建议可以如何布置”。
```

如果把二者都当成同一个 FloorPlanIR 真相对象，会导致生成建议被误认为建筑事实，后续风险很大。

## 3. 对象链

```text
SpatialProgramGraph
  空间程序图谱：空间清单、面积、邻接、私密等级、流线。

FloorPlanFacts
  空间事实：边界、柱、墙、核心筒、入口、窗、不可动构件、置信度。

DesignConstraintGraph
  设计约束图：硬约束、软约束、用户偏好、平台方法论、知识底盘。

DesignIntent
  设计意图：一个版本的策略身份，不直接包含几何。

LayoutIR
  布局方案：空间块、动线、开闭边界、评分、风险、解释。

LayoutVariant
  候选版本：DesignIntent + LayoutIR + 对比摘要。

LayoutVersionGraph
  版本图谱：选择、否定、冻结、融合、用户指令、决策轨迹。
```

## 4. 三个引擎

### 4.1 Geometry Compiler

职责：

```text
CAD/PDF/人工标注 → FloorPlanFacts
```

目标不是施工级准确，而是尽快得到可推演底座：

```text
外轮廓
柱
核心筒
管井
楼梯
入口
窗与景观面
不可动或疑似不可动墙
可改区域
比例尺状态
置信度与待复核问题
```

LLM 不应阻塞这条路径。LLM 可以作为后台质检员和语义补全器。

### 4.2 Layout Variant Engine

职责：

```text
SPG + FloorPlanFacts → 3-5 个 LayoutVariant
```

Phase 0 采用确定性粗空间块生成。

已内置三类策略：

```text
conservative_low_change 低改造稳妥版
functional_efficiency 功能效率版
experience_value 体验价值版
```

这一步的重点是策略差异，而不是墙线精度。

### 4.3 Design Reasoning Engine

职责：

```text
DesignIntent + LayoutIR + 版本对比 → 高参解释、风险、Diff、下一步建议
```

LLM 应主要放在这一层。

它负责：

```text
解释版本为什么成立
说明版本适配什么项目目标
提示版本牺牲什么
理解用户自然语言修改指令
把指令转换成 LayoutOperation
输出影响范围和下一轮建议
```

## 5. 用户指令不是直接改几何

自然语言应先变成操作原语：

```text
lock_space
move_space
resize_space
swap_space
merge_spaces
split_space
add_buffer
reduce_corridor
increase_privacy
improve_view
shorten_path
separate_flow
open_boundary
close_boundary
merge_strategy
reduce_cost
```

例如：

```text
用户：老人房别太远
→ shorten_path(target=elder_room, anchor=main_living_area, near=bathroom)
```

```text
用户：喜欢 A 的公共区，但想要 B 的私密性
→ merge_strategy(keep=A.public_core + B.private_zone, regenerate=transition/circulation)
```

规则：

```text
用户指令必须被理解和回应。
硬约束不能伪造。
```

如果用户指令触发不可动结构冲突，系统应输出：

```text
冲突说明
最接近用户原意的替代版本
影响评分
风险提示
是否继续调整
```

## 6. 两条响应路径

### 即时路径

用于：

```text
选择版本
锁定空间
简单拖拽
局部面积调整
```

目标：

```text
300ms-1s
```

### 高参路径

用于：

```text
重新生成多版本
融合两个版本
重大策略调整
完整评分与解释
```

目标：

```text
3-30s，异步返回
```

## 7. 版本图谱

平面推演不能只是历史记录。

版本应形成树或图：

```text
baseline
├─ 低改造稳妥版
├─ 功能效率版
│  └─ 用户：减少走廊
└─ 体验价值版
   └─ 用户：保留公共核心，降低成本
```

每个节点保存：

```text
生成策略
用户指令
操作原语
评分变化
风险变化
选择/否定/冻结状态
决策轨迹
```

这是平台沉淀的核心数据结构。
