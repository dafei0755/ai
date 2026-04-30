# Phase 1.5: Custom Analysis优先级增强 - 解决结构刚性vs任务灵活性冲突

**实施日期**: 2025-12-04
**修复类型**: 提示词优化（方案1）
**影响范围**: V2-V6所有角色配置文件
**修改文件数**: 5个YAML配置文件
**修改位置数**: 23处

---

## 🎯 问题背景

### 用户提出的核心问题

> "V2-V6的yaml提示词有输出定义和结构蓝图，这是否与我要求的任务导向（一些围绕用户问题）有冲突？"

### 诊断结果

**存在部分冲突**：

1. **结构刚性问题**：
   - Pydantic蓝图强制要求7-8个标准字段（如`project_vision_summary`、`master_plan_concept`等）
   - 用户可能只问"如何降低成本"（1个维度）
   - LLM倾向于"凑数填充"不相关字段

2. **Custom Analysis定位模糊**：
   - 标记为"Optional"，LLM可能优先填充标准字段
   - 未明确指出：针对性任务应该**优先使用** `custom_analysis`

3. **示例场景**：
   ```
   用户任务: "如何降低建造成本？"

   旧Prompt行为:
   ✅ 填充 project_vision_summary (凑数)
   ✅ 填充 master_plan_concept (凑数)
   ✅ 填充 sub_project_analysis (凑数)
   ⚠️ custom_analysis: null (应该放这里!)

   新Prompt行为:
   ⚠️ project_vision_summary: "简要背景"
   ⚠️ master_plan_concept: "默认值"
   ✅ custom_analysis: {详细的成本优化分析}
   ```

---

## 🔧 修复方案（方案1）

### 核心改进

修改所有角色YAML配置文件的Workflow第5步（或第6步），增强 `custom_analysis` 的优先级。

### 修改前（旧版本）

```yaml
5. **[处理特殊需求]** 检查用户的**核心任务**。如果其要求已在上述标准字段中得到充分回应，则将 `custom_analysis` 设为 `null`。否则，将所有无法归入标准字段的、针对性的、创造性的分析，完整地放入 `custom_analysis` 字段中。
```

**问题**：
- 优先级不明确
- 默认行为是"先填标准字段，剩下的才放custom_analysis"
- 导致针对性任务被"稀释"到多个标准字段中

### 修改后（新版本）

```yaml
5. **[处理特殊需求 - 优先级调整]** 检查用户的**核心任务**类型：

   **判断逻辑**：
   - 如果用户的**核心任务**是**针对性问题**（如"如何降低成本"、"如何优化动线"、"材料选型建议"等），
     则**优先将主要分析内容放入 `custom_analysis` 字段**，标准字段仅需提供简要的项目背景或设为合理的默认值。

   - 如果用户要求**完整的项目规划分析**（如"进行整体设计"、"制定总体方案"），
     则充分填充所有标准字段，`custom_analysis` 可设为 `null`。

   - **核心原则**：避免为了满足蓝图结构而生成与任务无关的填充内容。质量优先，相关性优先。
```

**改进点**：
✅ 明确区分"针对性问题" vs "完整分析"
✅ **优先使用** `custom_analysis` 处理针对性任务
✅ 允许标准字段设为"简要背景"或"默认值"
✅ 强调"质量优先，相关性优先"原则

---

## 📁 修改清单

### 修改文件统计

| 文件 | 修改位置数 | 涉及角色数 | 备注 |
|------|-----------|-----------|------|
| `v2_design_director.yaml` | 7处 | 7个角色 | V2所有角色 |
| `v3_narrative_expert.yaml` | 3处 | 3个角色 | V3所有角色 |
| `v4_design_researcher.yaml` | 2处 | 2个角色 | V4所有角色 |
| `v5_scenario_expert.yaml` | 7处 | 7个角色 | V5所有角色 |
| `v6_chief_engineer.yaml` | 4处 | 4个角色 | V6所有角色 |
| **总计** | **23处** | **23个角色** | **100%覆盖** |

### 各角色的针对性问题示例

为每个角色类别定制了不同的"针对性问题"示例：

- **V2（设计总监）**: "如何降低成本"、"如何优化动线"、"材料选型建议"
- **V3（叙事专家）**: "如何提升用户体验"、"如何构建品牌故事"、"情感化设计建议"
- **V4（设计研究员）**: "提供对标案例"、"行业趋势分析"、"创新模式研究"
- **V5（场景专家）**: "行业趋势分析"、"竞争对手研究"、"用户画像构建"
- **V6（总工程师）**: "结构优化建议"、"设备选型分析"、"成本控制策略"

---

## 🧪 预期效果

### 场景1：针对性任务（如"如何降低成本"）

#### 修改前

```json
{
  "project_vision_summary": "打造高性价比的现代综合体项目...", // 凑数
  "master_plan_concept": "低成本高效能设计理念...", // 凑数
  "sub_project_analysis": [...], // 凑数
  "integration_strategy": "...", // 凑数
  "implementation_guidance": "...", // 凑数
  "custom_analysis": null,
  "confidence": 0.8
}
```

**问题**：
- 成本分析被"稀释"到多个标准字段
- 不易提取和阅读
- 其他标准字段包含大量不相关内容

#### 修改后

```json
{
  "project_vision_summary": "项目背景：XX平方米商业综合体", // 简要
  "master_plan_concept": "基于用户需求的整体规划", // 默认
  "sub_project_analysis": [], // 空或简要
  "integration_strategy": "详见custom_analysis", // 指向
  "implementation_guidance": "详见custom_analysis", // 指向
  "custom_analysis": {
    "cost_optimization_analysis": {
      "material_cost_reduction": "...",
      "construction_efficiency": "...",
      "lifecycle_cost_analysis": "..."
    }
  },
  "confidence": 0.9
}
```

**改进**：
✅ 主要内容集中在 `custom_analysis`
✅ 标准字段简洁明了
✅ 易于提取和阅读
✅ 相关性提高

### 场景2：完整项目分析（如"进行整体设计"）

#### 行为不变

```json
{
  "project_vision_summary": "完整的项目愿景描述...",
  "master_plan_concept": "核心设计理念...",
  "sub_project_analysis": [...完整分析...],
  "integration_strategy": "整合策略...",
  "implementation_guidance": "实施指导...",
  "custom_analysis": null, // 标准字段已充分
  "confidence": 0.85
}
```

---

## 📊 技术细节

### 修改方法

1. **批量替换**：使用 `replace_all=true` 参数
2. **上下文匹配**：提供足够的上下文确保唯一性
3. **一致性检查**：针对不同角色调整示例

### 实施步骤

1. ✅ 读取 v2_design_director.yaml（801行）
2. ✅ 修改第一个角色（2-0）的第5步
3. ✅ 批量修改V2的其余6个角色
4. ✅ 修改V3所有角色（3处）
5. ✅ 修改V4所有角色（2处）
6. ✅ 修改V5所有角色（7处）
7. ✅ 修改V6所有角色（4处）
8. ✅ 最终验证：0个旧版本残留，23个新版本

### 验证命令

```bash
# 检查旧版本（应该返回0）
grep -r "如果其要求已在上述标准字段中得到充分回应" *.yaml

# 检查新版本（应该返回23）
grep -r "处理特殊需求 - 优先级调整" *.yaml
```

---

## 🎓 关键改进点总结

### 1. 语义清晰化

- **旧版本**: "如果已充分回应...否则..."（二选一逻辑）
- **新版本**: 明确区分两种任务类型，提供清晰的判断标准

### 2. 优先级反转

- **旧版本**: 标准字段优先 → custom_analysis兜底
- **新版本**: 针对性任务优先 custom_analysis → 标准字段简化

### 3. 原则导向

- **旧版本**: 无明确原则
- **新版本**: "避免凑数填充，质量优先，相关性优先"

### 4. 示例具体化

- **旧版本**: 无具体示例
- **新版本**: 每个角色类别提供3个典型针对性问题示例

---

## 🔄 后续改进方案（可选）

如果本次修复效果不理想，可以实施：

### 方案2：轻量级输出模式（中等改动）

在Pydantic模型中添加模式切换：

```python
class V2_0_MasterPlanOutput(BaseModel):
    output_mode: Literal["full_analysis", "focused_task"]

    # 标准字段改为可选
    project_vision_summary: Optional[str] = None

    # 针对性任务响应
    focused_task_response: Optional[Dict[str, Any]] = None
```

### 方案3：动态蓝图生成（较大改动）

根据任务类型动态选择不同的输出模板。

---

## ✅ 验证清单

- [x] 所有5个YAML文件已修改
- [x] 23处修改位置全部完成
- [x] 旧版本文本已清除（0个残留）
- [x] 新版本文本已验证（23个）
- [x] 各角色示例已定制化
- [x] 文档已创建

---

## 📝 使用建议

1. **测试场景1**: 提问"如何降低建造成本？"
   - 预期：`custom_analysis` 包含详细成本分析
   - 预期：标准字段简洁

2. **测试场景2**: 提问"请进行完整的项目设计"
   - 预期：所有标准字段充分填充
   - 预期：`custom_analysis` 为 null

3. **观察指标**:
   - LLM是否正确识别任务类型？
   - `custom_analysis` 使用率是否提升？
   - 标准字段是否避免了"凑数"内容？

---

**修复状态**: ✅ 完成
**测试状态**: ⏳ 待用户测试验证
**版本**: v20251204-custom-analysis-priority

---

**文档创建时间**: 2025-12-04
**作者**: Claude Code Agent
**相关问题**: 结构刚性 vs 任务灵活性冲突
