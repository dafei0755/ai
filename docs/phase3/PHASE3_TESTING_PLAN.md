# Phase 3 测试计划 - 灵活输出架构验证

**日期**: 2025-12-05
**状态**: 🚀 启动中
**目标**: 为所有23个角色编写完整的测试用例

---

## 一、测试范围

### 1.1 测试对象

**23个Pydantic模型**:
- V6系列: V6_1/2/3/4_FlexibleOutput (4个)
- V5系列: V5_0/1/2/3/4/5/6_FlexibleOutput (7个)
- V2系列: V2_0/1/2/3/4/5/6_FlexibleOutput (7个)
- V3系列: V3_1/2/3_FlexibleOutput (3个)
- V4系列: V4_1/2_FlexibleOutput (2个)

### 1.2 测试维度

1. **模型导入测试**: 验证所有模型可正常导入
2. **Targeted模式测试**: 验证targeted_analysis必需字段
3. **Comprehensive模式测试**: 验证标准字段完整性
4. **验证器逻辑测试**: 测试@model_validator的错误检测
5. **字段类型测试**: 验证Pydantic类型约束（confidence: 0-1, Literal等）
6. **辅助模型测试**: 验证嵌套模型（如FamilyMemberProfile, RetailKPI等）

---

## 二、测试策略

### 2.1 分批测试策略

**批次1: V6系列（4个模型）** - 1小时
- 作为测试范式，编写详细测试用例
- 覆盖所有测试维度
- 建立测试模板

**批次2: V5系列（7个模型）** - 1.5小时
- 复用V6测试模板
- 快速适配业务差异

**批次3: V2系列（7个模型）** - 1.5小时
- 批量生成测试用例
- 自动化测试执行

**批次4: V3/V4系列（5个模型）** - 1小时
- 精简版测试（重点验证核心逻辑）

**总预估时间**: 5小时

### 2.2 测试工具

- **测试框架**: pytest
- **断言库**: pytest内置assert
- **覆盖率工具**: pytest-cov
- **目标覆盖率**: ≥90%

---

## 三、测试文件结构

```
tests/
├── test_flexible_output_models.py          # 主测试文件
├── test_v6_models.py                       # V6系列专项测试
├── test_v5_models.py                       # V5系列专项测试
├── test_v2_models.py                       # V2系列专项测试
├── test_v3_v4_models.py                    # V3/V4系列测试
├── fixtures/
│   ├── v6_test_data.json                   # V6测试数据
│   ├── v5_test_data.json                   # V5测试数据
│   └── ...
└── conftest.py                             # pytest配置
```

---

## 四、测试用例模板

### 4.1 Targeted模式测试模板

```python
def test_v6_1_targeted_mode_valid():
    """测试V6-1 Targeted模式 - 有效输入"""
    data = {
        "output_mode": "targeted",
        "user_question_focus": "如何选择结构体系？",
        "confidence": 0.85,
        "design_rationale": "分析原因...",
        "targeted_analysis": {
            "structural_system_comparison": {
                "options": ["框架结构", "剪力墙结构"],
                "recommendation": "框架结构"
            }
        }
    }

    output = V6_1_FlexibleOutput(**data)
    assert output.output_mode == "targeted"
    assert output.confidence == 0.85
    assert output.targeted_analysis is not None

def test_v6_1_targeted_mode_missing_field():
    """测试V6-1 Targeted模式 - 缺少targeted_analysis"""
    data = {
        "output_mode": "targeted",
        "user_question_focus": "如何选择结构体系？",
        "confidence": 0.85,
        "design_rationale": "分析原因..."
        # 缺少 targeted_analysis
    }

    with pytest.raises(ValueError, match="Targeted mode requires targeted_analysis"):
        V6_1_FlexibleOutput(**data)
```

### 4.2 Comprehensive模式测试模板

```python
def test_v6_1_comprehensive_mode_valid():
    """测试V6-1 Comprehensive模式 - 有效输入"""
    data = {
        "output_mode": "comprehensive",
        "user_question_focus": "完整分析",
        "confidence": 0.9,
        "design_rationale": "综合考虑...",
        "structural_feasibility_analysis": "可行性分析...",
        "structural_system_selection": "选型方案...",
        "load_path_design": "荷载路径...",
        "key_node_detailing": "关键节点...",
        "risk_assessment": "风险评估..."
    }

    output = V6_1_FlexibleOutput(**data)
    assert output.output_mode == "comprehensive"
    assert output.structural_feasibility_analysis is not None

def test_v6_1_comprehensive_mode_missing_fields():
    """测试V6-1 Comprehensive模式 - 缺少必需字段"""
    data = {
        "output_mode": "comprehensive",
        "user_question_focus": "完整分析",
        "confidence": 0.9,
        "design_rationale": "综合考虑...",
        "structural_feasibility_analysis": "可行性分析..."
        # 缺少其他标准字段
    }

    with pytest.raises(ValueError, match="Comprehensive mode missing required fields"):
        V6_1_FlexibleOutput(**data)
```

---

## 五、实施计划

### 5.1 批次1: V6系列（当前）

**目标**: 建立测试范式

**步骤**:
1. ✅ 创建测试计划文档（本文件）
2. ⏳ 创建 `tests/test_v6_models.py`
3. ⏳ 编写 V6-1 完整测试用例（作为模板）
4. ⏳ 复用模板，完成 V6-2/3/4 测试
5. ⏳ 运行测试，验证通过率

**预计耗时**: 1小时

### 5.2 批次2-4: 其余系列

**策略**: 批量生成 + 自动化验证

**预计耗时**: 4小时

---

## 六、验收标准

### 6.1 测试覆盖率

- ✅ 所有23个模型都有测试用例
- ✅ Targeted和Comprehensive两种模式都被测试
- ✅ 验证器逻辑100%覆盖
- ✅ 测试覆盖率 ≥ 90%

### 6.2 测试质量

- ✅ 所有测试用例都能通过
- ✅ 错误场景被正确检测
- ✅ 测试数据真实可信
- ✅ 测试文档完整清晰

---

## 七、风险与挑战

### 7.1 潜在风险

1. **辅助模型复杂度**: 部分模型包含嵌套模型（如FamilyMemberProfile），需要额外测试
2. **测试数据准备**: 23个模型需要大量测试数据
3. **时间压力**: 5小时完成23个模型的测试

### 7.2 应对策略

1. **复用策略**: V6测试模板可复用到其他系列
2. **批量生成**: 使用脚本批量生成测试用例
3. **分批验证**: 每批完成后立即验证，避免积累问题

---

**文档版本**: v1.0
**更新时间**: 2025-12-05
**状态**: 📝 测试计划已制定，准备启动批次1
