# 底图到 FloorPlanIR 精准编译方案 v1.0

> 日期：2026-04-14  
> 成熟度：`Planned -> Implementing`  
> 关联文档：  
> - `01-平面图落地思路与执行路径.md`  
> - `02-平面沙盘产品形态与执行方案.md`

---

## 0. 定位

底图到 `FloorPlanIR` 不是“识别一张图”，而是把外部图纸编译成可计算、可校验、可回退的几何真相层。

禁止路线：

```text
上传底图 -> 直接检测对象 -> 直接展示为 FloorPlanIR
```

正确路线：

```text
底图治理
  -> 主平面区抽取
  -> 去干扰分层
  -> 墙图重建
  -> 柱结构节点融合
  -> 开口绑定
  -> 空间拓扑分区
  -> Contract / Geometry / System Gate
  -> Reviewed FloorPlanIR
```

未通过 Gate 的结果只能进入候选层和复核队列，不得进入正式 `FloorPlanIR` 层。

---

## 1. 当前失败根因

当前原型失败不是单一识别精度问题，而是编译链缺层：

1. ROI 只是粗框，未真正抽取主平面建筑主体；
2. 标题栏、轴网、尺寸线、文字、详图线与墙柱线混在同一输入层；
3. 墙被当作线段检测结果，没有形成连续 `WallGraph`；
4. 柱被当作普通矩形，未与墙交点、轴网、结构节点融合；
5. 门、窗、门洞没有分语法，也没有强制绑定 `host_wall_id`；
6. 空间分区直接找闭合块，而不是基于墙图和开口拓扑求解；
7. 失败候选直接进入前端展示，被误认为正式 IR。

---

## 2. 输入分级

输入先分四档，不同档位走不同编译策略：

| 档位 | 输入 | 优先策略 |
|---|---|---|
| A | DXF / CAD | 矢量实体、图层、块解析 |
| B | 矢量 PDF | PDF path / text / stroke 解析 |
| C | 高清栅格图 | CV 分割 + 线段/连通域 |
| D | 拍照/低清扫描 | 透视校正 + 视觉候选 + 强人工复核 |

A/B 档不得优先走纯图像识别；C/D 档不得直接生成正式 IR。

---

## 3. 编译对象链

### 3.1 PlanCanvasBaseline

主平面治理输出：

```ts
type PlanCanvasBaseline = {
  inputType: 'dxf' | 'pdf' | 'raster' | 'scan';
  pageBox: Rect;
  contentBox: Rect;
  recognitionBox: Rect;
  mainPlanBox: Rect;
  rotationDeg: number;
  northDirectionDeg?: number;
  scaleStatus: 'known' | 'estimated' | 'missing';
  unitGuess: 'mm' | 'px';
  noiseRegions: Rect[];
  confidence: number;
};
```

### 3.2 DetectionLayers

去干扰后的候选层：

```ts
type DetectionLayers = {
  structureLines: PrimitiveRef[];
  wallCandidates: WallCandidate[];
  columnCandidates: ColumnCandidate[];
  openingCandidates: OpeningCandidate[];
  textRegions: PrimitiveRef[];
  dimensionRegions: PrimitiveRef[];
  gridRegions: PrimitiveRef[];
  symbolRegions: PrimitiveRef[];
};
```

结构编译只能消费 `structureLines / wallCandidates / columnCandidates`，不得直接消费全量图元。

### 3.3 WallGraph

墙图不是检测框，而是连续结构图：

```ts
type WallGraph = {
  walls: Array<{
    wallId: string;
    centerline: [Point, Point];
    thickness: number;
    confidence: number;
    joints: string[];
    sourceRefs: string[];
  }>;
  joints: WallJoint[];
  thicknessClusters: number[];
  danglingWallIds: string[];
  fragmentGroups: string[][];
};
```

### 3.4 ColumnSet

柱是结构节点，不是孤立矩形：

```ts
type ColumnSet = {
  columns: Array<{
    columnId: string;
    polygon: Point[];
    center: Point;
    size: [number, number];
    shape: 'rect' | 'square' | 'round' | 'pier';
    attachedWalls: string[];
    confidence: number;
    sourceRefs: string[];
  }>;
  suspectedMissingColumns: ReviewIssue[];
};
```

### 3.5 Openings

门、窗、门洞必须拆开：

```ts
type Openings = {
  doors: DoorIR[];
  windows: WindowIR[];
  voids: OpeningVoidIR[];
  unboundCandidates: OpeningCandidate[];
};
```

任何 opening 进入正式 IR 前必须绑定 `host_wall_id`。

### 3.6 SpacePartition

空间必须来自墙图拓扑，不来自像素闭合块：

```ts
type SpacePartition = {
  spaces: SpaceCell[];
  adjacencyMatrix: Record<string, Record<string, boolean>>;
  accessGraph: AccessGraph;
  circulationPaths: CirculationPath[];
  unresolvedCells: ReviewIssue[];
};
```

---

## 4. Gate 规则

### 4.1 Contract Gate

阻断条件：

1. 缺失 `spg_version` / `source_refs`；
2. 缺失 `building_carrier_ref`；
3. 正式对象缺少 `zone_id/module_id` 绑定；
4. 外部输入试图直接覆写冻结对象；
5. 识别对象没有来源证据。

### 4.2 Geometry Gate

墙柱阶段 v0 阻断条件：

| 指标 | v0 阈值 | 说明 |
|---|---:|---|
| `wall_fragmentation_score` | `<= 0.35` | 当前无标注集，先用保守工程阈值 |
| `dangling_wall_count` | `<= max(3, walls * 0.18)` | 悬空墙过多则失败 |
| `wall_pairing_rate` | `>= 0.35` | 平行双线配对不足说明墙图不稳 |
| `column_attachment_rate` | `>= 0.50` | 柱至少应与墙图/结构线有关系 |
| `main_plan_coverage` | `>= 0.35` | 主结构簇不能只是图纸局部 |

后续稳定后再升级到：墙召回、柱召回、主空间闭合率、开口 host 绑定率等有标注集指标。

### 4.3 System Gate

阻断条件：

1. `hard_fixed` 未覆盖承重墙、柱、核心筒；
2. `built_in_system` 无宿主关系；
3. 家具/洁具/符号倒灌进结构层；
4. 三分法标签断链。

---

## 5. 前端状态模型

前端必须从“结果展示”改为“编译复核”：

1. **底图态**：底图、ROI、比例尺、朝向、主平面框；
2. **编译候选态**：墙候选、柱候选、开口候选、空间候选；
3. **复核态**：按问题桶修复，而不是按对象平铺；
4. **正式 IR 态**：只显示 Gate passed 的 Reviewed `FloorPlanIR`。

失败候选显示为：

```text
墙柱候选已生成，Geometry Gate 未通过
```

不得显示为：

```text
FloorPlanIR 已生成
```

---

## 6. 当前实施优先级

### FloorPlan Compiler v0.1

只实现最小闭环：

```text
输入底图
  -> PlanCanvasBaseline
  -> De-clutter v0
  -> WallGraph v0
  -> ColumnSet v0
  -> Geometry Gate v0
  -> 前端候选层 / Review Queue
```

暂不承诺正式空间分区；暂不把门窗/门洞写入正式 IR。

当前代码落地边界：

1. API 返回 `compileResult / gates / reviewQueue / wallGraph / draftFloorPlanIR`；
2. Contract / Geometry / System Gate 未全部通过时，`floorPlanIR` 必须为空；
3. WallGraph v0 已包含端点吸附、T/L/十字 joint、吸附后二次共线合并；
4. 墙碎片只统计未接入 WallGraph 的短墙段，悬空墙单独进入 Review Queue；
5. 柱集 v0 包含线框小矩形候选、原始线段补检、柱-墙挂接率；
6. 多墙结构节点附近无柱时，只进入“疑似漏柱”复核桶，不直接伪造柱对象；
7. 比例尺优先读取 ROI 内尺寸标注；缺失时可回填主平面邻近标注；若 PDF 文本层无尺寸数字，只能生成 `vector_geometry_guess` 弱估算，并继续阻断 Geometry Gate；
8. `focusBounds` 只能作为调试候选，不得直接升级为 `mainPlanBox`；在 PlanCanvasBaseline 未稳定前，`mainPlanBox` 回退为用户识别区；
9. 前端必须同时显示识别区、`mainPlanBox` 与 `focusBounds`，用于排查坐标基准污染；
10. 前端只展示“编译候选态”，未过 Gate 时禁止确认为 Reviewed FloorPlanIR。

### FloorPlan Compiler v0.2

墙图稳定后实现：

```text
Door Compiler
Window Compiler
OpeningVoid Compiler
Opening Host Binder
Opening Geometry Gate
```

### FloorPlan Compiler v0.3

开口稳定后实现：

```text
Space Topology Solver
Adjacency Matrix
Access Graph
Circulation Paths
Reviewed FloorPlanIR
```

---

## 7. 工程红线

1. 低置信候选不得进入正式 IR；
2. 未绑定墙的门窗门洞不得进入正式 IR；
3. 未通过 Geometry Gate 的结果不得被称为 `FloorPlanIR`；
4. 每个正式对象必须有 `sourceRefs`；
5. 任何影响 `SPG` 的修改必须回退 Node3 升版；
6. LLM 只做异常解释、复核建议、上位约束对齐，不做几何识别主裁决。

---

## 8. 最终判断

底图到 `FloorPlanIR` 的核心不是“看见墙”，而是“编译出可计算墙图并通过门禁”。

平面沙盘的正确目标不是弱化版 CAD，也不是图像检测展示器，而是：

```text
底图治理器 + 图纸语法引擎 + 结构图构建器 + 开口绑定器 + 空间拓扑求解器 + IR 编译器 + 门禁治理器
```

在 v0.1 阶段，先把墙柱编译链打稳；否则门窗和空间分区都会建立在错误几何上。
