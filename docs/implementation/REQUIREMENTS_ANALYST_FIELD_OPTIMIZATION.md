# 需求分析字段优化总结

**日期**: 2025-11-25  
**优化类型**: 术语规范化 + 字段结构优化

---

## ✅ 已完成的4项修改

### 1️⃣ "业主画像" → "核心人物画像"

**修改位置**: 
- `requirements_analyst.yaml` - character_narrative字段说明
- `requirements_analyst.py` - target_users注释

**修改内容**:
```yaml
# 修改前
"character_narrative": "人物与叙事"  

# 修改后  
"character_narrative": "核心人物画像 (适用所有项目类型：住宅=业主，商业=目标用户)"
```

**理由**: 
- "业主"仅适用住宅，"核心人物"涵盖所有项目类型
- 商业项目中业主≠用户（如酒店业主vs客人）

---

### 2️⃣ "核心张力" → "设计挑战"

**修改位置**:
- `requirements_analyst.yaml` - L3系统分析、L5验证、JSON字段、示例、expert_handoff
- `requirements_analyst.py` - 新格式字段验证、备用结构

**修改内容**:
```yaml
# 修改前
"core_tension": "核心张力 (根本性矛盾)"
"core_tension_formula": "..."

# 修改后
"design_challenge": "设计挑战 (项目中最尖锐的对立需求)"
"design_challenge_formula": "..."
```

**理由**:
- "张力"过于学术化，不够直白
- "挑战"更符合设计专业术语习惯
- 增加注释"项目中最尖锐的对立需求"保持原有锋利性

---

### 3️⃣ 灵感和体验需通过问卷收集（不推测）

**修改位置**:
- `requirements_analyst.yaml` - JSON字段说明、问卷模板
- `requirements_analyst.py` - 备用结构占位符

**修改内容**:
```yaml
# 字段说明
"inspiration_references": "灵感参照 (仅记录用户明确提到的案例。若用户未提及，填写'【待问卷收集】请在校准问卷中询问...')"
"experience_behavior": "体验行为 (仅记录用户描述的实际场景。若用户未提及，填写'【待问卷收集】请在校准问卷中询问...')"

# 问卷必需问题
calibration_questionnaire:
  questions:
    - question: "请分享3-5个您喜欢的设计案例..."
      required_if: "inspiration_references为'【待问卷收集】'"
    - question: "请描述您在这个空间中的典型一天..."
      required_if: "experience_behavior为'【待问卷收集】'"
```

**理由**:
- **严格区分事实和推测**：AI不应"脑补"用户未说的内容
- **通过问卷主动收集**：用户未提供时明确标注并在问卷中询问
- **避免误导后续专家**：推测的信息可能导致错误决策

---

### 4️⃣ "空间约束" → 拆分为三个明确字段

**修改位置**:
- `requirements_analyst.yaml` - JSON字段定义、示例
- `requirements_analyst.py` - 字段验证、合并逻辑、备用结构

**修改内容**:
```yaml
# 修改前（混在一起）
"space_constraints": "75平米 + 预算60万 + 高层 + 物业规定 + 4个月工期"

# 修改后（分类清晰）
"physical_context": "物理环境 (75平米的一居室公寓，位于高层，南向采光充足)"
"resource_constraints": "资源限制 (预算60万元人民币，希望在4个月内完成)"
"regulatory_requirements": "规范要求 (物业对施工噪音和作业时间有严格规定，承重墙不可拆改)"
```

**Python兼容处理**:
```python
# 自动合并三个字段供旧逻辑使用
physical = structured_data.get("physical_context", "")
resource = structured_data.get("resource_constraints", "")
regulatory = structured_data.get("regulatory_requirements", "")
combined_constraints = f"{physical} {resource} {regulatory}".strip()
structured_data["constraints"] = {"description": combined_constraints}
```

**理由**:
- **更准确的分类**：物理/资源/规范三类边界条件明确
- **避免"约束"负面色彩**："条件"和"要求"更中性
- **便于后续专家处理**：V6工程师只需关注regulatory_requirements

---

## 📊 修改影响范围

### YAML配置文件
- ✅ `requirements_analyst.yaml` - 12处修改
  - L3系统分析公式
  - L5验证清单术语
  - JSON字段定义和说明
  - 问卷模板增强
  - 输出示例更新
  - expert_handoff术语统一

### Python代码
- ✅ `requirements_analyst.py` - 5处修改
  - 新格式字段验证列表
  - 字段合并逻辑
  - target_users注释
  - 备用结构占位符

---

## 🎯 优化效果

### 术语更规范
- ✅ "核心人物"适配所有项目类型
- ✅ "设计挑战"更贴近专业用语
- ✅ "物理环境/资源限制/规范要求"分类明确

### 避免AI推测
- ✅ 灵感和体验需用户明确提供或通过问卷收集
- ✅ 占位符`【待问卷收集】`明确标注
- ✅ 问卷模板自动包含必需问题

### 数据结构更清晰
- ✅ 空间约束拆分为三个独立字段
- ✅ 向后兼容旧逻辑（自动合并）
- ✅ 便于后续专家分类使用

---

## ⚠️ 注意事项

1. **LLM需要重新训练理解新字段名**
   - 第一次调用可能仍返回旧字段名
   - prompt已明确要求新字段，应能正确输出

2. **前端UI需要适配**
   - 显示"核心人物画像"而非"业主画像"
   - 显示"设计挑战"而非"核心张力"
   - 分别显示三个约束字段

3. **向后兼容已实现**
   - Python代码自动合并新字段为旧格式
   - 现有工作流无需修改

---

**总结**: 完成4项术语和结构优化，使需求分析输出更规范、更准确、更易理解，避免AI过度推测，为后续专家提供更清晰的协作接口。✅
