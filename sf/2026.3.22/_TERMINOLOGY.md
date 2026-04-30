# 统一术语表（几何与视觉化总线）

| 术语主题 | 统一写法 | 不建议写法 | 说明 |
|---|---|---|---|
| 空间程序图谱 | `SpatialProgramGraph (SPG)` | 仅写SPG无全称 | 首次出现必须全称+缩写 |
| 平面真相源 | `FloorPlanIR` | PlanIR（泛称） | 使用统一对象名 |
| 立面规则层 | `ElevationIR` | 立面包/立面模型（泛称） | 对象契约名称固定 |
| 三维体块层 | `Massing3DIR` | 3D体块（口语） | 文档中对象名优先 |
| 三维壳体阶段 | `Massing3DIR.shell` | 白模（无归属） | 指明归属对象 |
| 三维场景阶段 | `Massing3DIR.scene` | 场景模型（泛称） | 指明归属对象 |
| 视觉参数层 | `VizSpec` | 渲染配置（泛称） | 参数层，不具改题权 |
| 视觉交付层 | `VizDeliveryPack` | 效果图包（泛称） | 交付层，需带版本索引 |
| 流线 | `circulation_path` | circulation_paths/circulation混用 | 推荐统一字段命名 |
| 三分法映射 | `zone_3parts_mapping` | 仅文字描述三分法 | 必须对象化 |
| 越权阻断 | `contract_validation_gate` | 审核拦截（泛称） | 对应 Contract 门执行点 |
| 反馈协议 | `feedback_protocol` | 回写逻辑（泛称） | 对应影响评估与回退机制 |
| 影响评估 | `impactScope()` | 影响分析（泛称） | 方法名固定，便于实现 |
| 版本链 | `spg_version/ir_version/viz_version/deployed_version` | 版本号混写 | 用于全链追溯 |
