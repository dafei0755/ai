# 智能任务拆解策略系统 v7.950

## 📌 核心问题诊断

### 当前问题
1. **硬编码问题**：之前的"5层递进拆解法"（田野调研→解构→策略提取→在地化→验证）仅适合乡村建设类型
2. **类型识别过简**：当前 `_infer_project_type()` 只有3个分类（personal_residential, commercial_enterprise, hybrid）
3. **无法应对广泛性**：q.txt 包含190个多样化问题，涵盖住宅、商业、文化、医疗、情感修复、实验性空间、跨学科设计等

### 解决方案
**智能分类 + 策略匹配系统**：
- 多维度项目分类器（Taxonomy）
- 类型特征自动识别（Feature Detection）
- 拆解策略模板库（Strategy Templates）
- 动态匹配算法（Dynamic Matching）

---

## 📊 Q.txt 问题类型学分析（基于190个实际案例）

### 1. 项目尺度维度（Scale Dimension）

| 尺度级别 | 面积范围 | 典型案例 | 占比 |
|---------|---------|---------|------|
| **Micro** | < 50㎡ | 27号电竞直播间、34号诗意书房、36号求婚场景 | 15% |
| **Small** | 50-200㎡ | 5号Tiffany别墅软装、29号香薰店、77号弄堂老房 | 30% |
| **Medium** | 200-1000㎡ | 1号雅诗阁公寓、8号自闭症家庭、76号酒店客房升级 | 25% |
| **Large** | 1000-5000㎡ | 9号菜市场、17号书法酒店、87号商业综合体 | 20% |
| **Macro** | > 5000㎡ | 152号创意产业园、172号示范社区、179号城市轴线 | 10% |

**关键发现**：
- 50-200㎡ 的 Small 项目占比最高（30%），是核心类型
- Macro 级别（城市规划/社区）需要完全不同的拆解策略

---

### 2. 功能复杂度维度（Functional Complexity）

| 复杂度 | 定义 | 典型案例 | 占比 |
|--------|------|---------|------|
| **Simple** | 单一功能+单一用户 | 27号电竞直播间、34号诗意书房、70号衣帽间 | 20% |
| **Moderate** | 单一功能+多用户 或 多功能+单一用户 | 35号社区活动中心（分时复用）、41号三人合租、23号四层复合建筑 | 40% |
| **Complex** | 多功能+多用户+系统级 | 3号乡村建设（文化+产业+运营）、8号自闭症家庭+长辈短住、180号农业+艺术+居住 | 40% |

**关键发现**：
- 40% 的项目属于 Complex 级别，需要系统级拆解
- Moderate 和 Complex 合计占80%，不能用简单功能拆解法

---

### 3. 约束条件维度（Constraint Dimension）

| 约束类型 | 定义 | 典型案例 | 占比 |
|---------|------|---------|------|
| **Budget** | 预算极度受限 | 33号8000元改造、77号50万预算、78号3000元/㎡豪宅 | 15% |
| **Time** | 时间极度受限 | 84号30小时商场换装、144号临时展馆3个月 | 5% |
| **Technical** | 技术难题主导 | 85号高海拔供氧、86号海边防腐、131号人机共居散热 | 10% |
| **Regulatory** | 政策/规范约束 | 69号保障房标准、151号微更新不能拆建、40号历史建筑保护 | 8% |
| **Cultural** | 文化表达约束 | 116号一带一路多元表达、183号阶层感知控制、37号维族企业家 | 12% |
| **None** | 无特殊约束 | 大多数常规项目 | 50% |

**关键发现**：
- 50% 的项目有明显主导约束，必须用**约束驱动拆解法**
- Budget 约束型需要"成本分解+价值排序"

---

### 4. 精神深度维度（Spiritual Depth）

| 深度级别 | 定义 | 典型案例 | 占比 |
|---------|------|---------|------|
| **Functional** | 纯功能导向 | 27号电竞直播间、46号家庭影院、85号高海拔民宿 | 30% |
| **Lifestyle** | 生活方式表达 | 5号Tiffany女性、6号赫本精神、10号季裕棠叙事 | 50% |
| **Philosophical** | 哲学/精神思辨 | 34号"月亮落在冰湖上"、59号存在与虚无、120号AI伦理、190号后人类伦理 | 20% |

**关键发现**：
- 20% 的项目属于哲学思辨级别，**不能用功能拆解，必须用意象拆解法**
- Lifestyle 级别占50%，需要"情感触点→空间隐喻→材料转译"

---

### 5. 跨学科维度（Interdisciplinary）

| 学科类型 | 定义 | 典型案例 | 占比 |
|---------|------|---------|------|
| **Pure Design** | 纯设计问题 | 大多数常规住宅/商业项目 | 60% |
| **Cultural Anthropology** | 文化人类学 | 3号乡村文化挖掘、98号百年药铺、154号乡村自建房 | 15% |
| **Behavioral Science** | 行为/心理学 | 181号行为经济学体验馆、182号神经科学实验空间、187号注意力经济 | 10% |
| **Philosophy/Ethics** | 哲学/伦理学 | 59号存在与虚无、120号AI伦理、129号宇宙记忆、190号后人类伦理 | 5% |
| **Technical Engineering** | 工程技术 | 85号高海拔、86号海边防腐、131号人机共居 | 10% |

**关键发现**：
- 40% 的项目需要跨学科知识，纯设计拆解不足
- 跨学科项目需要"学科知识图谱注入"

---

### 6. 情感/身份维度（Emotional/Identity）

| 情感类型 | 定义 | 典型案例 | 占比 |
|---------|------|---------|------|
| **Identity** | 身份认同 | 5号Tiffany女性、6号赫本精神、37号维族企业家、66号"香蕉人" | 15% |
| **Healing** | 情感修复 | 28号婚姻修复、47号临终关怀、101号心理干预中心 | 8% |
| **Heritage** | 文化传承 | 52号昆曲教学、98号百年药铺、154号乡村自建房 | 10% |
| **Ideology** | 理念表达 | 38号断舍离极简、97号零碳生活、120号AI伦理 | 7% |
| **None** | 无特殊情感诉求 | 功能导向项目 | 60% |

**关键发现**：
- 40% 的项目有强烈情感/身份诉求
- 这类项目需要"情绪触点映射→叙事结构→物理实现"三层拆解

---

## 🧬 智能分类系统设计（Multi-Dimensional Taxonomy）

### Phase1: 项目特征向量提取

```python
class ProjectFeatureExtractor:
    """项目特征向量提取器"""

    def extract_features(self, structured_data: Dict[str, Any]) -> Dict[str, Any]:
        """提取项目特征向量"""
        return {
            # 1. 尺度维度
            "scale": self._detect_scale(structured_data),  # "micro" | "small" | "medium" | "large" | "macro"

            # 2. 功能复杂度
            "functional_complexity": self._detect_functional_complexity(structured_data),  # "simple" | "moderate" | "complex"

            # 3. 主导约束
            "primary_constraint": self._detect_primary_constraint(structured_data),  # "budget" | "time" | "technical" | "regulatory" | "cultural" | None

            # 4. 精神深度
            "spiritual_depth": self._detect_spiritual_depth(structured_data),  # "functional" | "lifestyle" | "philosophical"

            # 5. 跨学科需求
            "interdisciplinary": self._detect_interdisciplinary(structured_data),  # "pure_design" | "cultural_anthropology" | "behavioral_science" | "philosophy" | "technical_engineering"

            # 6. 情感/身份维度
            "emotional_identity": self._detect_emotional_identity(structured_data),  # "identity" | "healing" | "heritage" | "ideology" | None

            # 7. 业态类型（细分）
            "business_type": self._detect_business_type(structured_data),  # "residential" | "hospitality" | "retail" | "office" | "cultural" | "healthcare" | "mixed_use"

            # 8. 创新程度
            "innovation_level": self._detect_innovation_level(structured_data),  # "conventional" | "innovative" | "experimental"
        }
```

#### 1. 尺度维度检测

```python
def _detect_scale(self, structured_data: Dict[str, Any]) -> str:
    """检测项目尺度"""
    # 方法1: 从 physical_context 提取面积
    physical_context = structured_data.get("physical_context", "")
    area_match = re.search(r"(\d+)[㎡平方米平米]", physical_context)

    if area_match:
        area = int(area_match.group(1))
        if area < 50:
            return "micro"
        elif area < 200:
            return "small"
        elif area < 1000:
            return "medium"
        elif area < 5000:
            return "large"
        else:
            return "macro"

    # 方法2: 关键词识别
    keywords = {
        "macro": ["规划", "社区", "片区", "轴线", "城市更新", "示范区", "综合体", "产业园"],
        "large": ["酒店", "商场", "医院", "学校", "展馆", "会展", "体育馆"],
        "medium": ["菜市场", "办公室", "餐厅", "健身房", "图书馆"],
        "small": ["住宅", "公寓", "别墅", "店铺", "工作室"],
        "micro": ["卧室", "书房", "衣帽间", "直播间", "茶室"]
    }

    project_task = structured_data.get("project_task", "").lower()
    for scale, kw_list in keywords.items():
        if any(kw in project_task for kw in kw_list):
            return scale

    return "small"  # 默认
```

#### 2. 功能复杂度检测

```python
def _detect_functional_complexity(self, structured_data: Dict[str, Any]) -> str:
    """检测功能复杂度"""
    complexity_score = 0

    # Factor 1: 功能数量
    functional_keywords = ["办公", "居住", "展示", "餐饮", "会议", "培训", "零售", "仓储"]
    project_task = structured_data.get("project_task", "")
    function_count = sum(1 for kw in functional_keywords if kw in project_task)
    complexity_score += function_count * 0.15

    # Factor 2: 用户群体数量
    user_groups = ["老人", "儿童", "年轻人", "中年", "家庭", "访客", "员工", "客户"]
    user_count = sum(1 for ug in user_groups if ug in project_task)
    complexity_score += user_count * 0.15

    # Factor 3: 检测"+"符号（表示业态融合）
    if re.search(r"[^，。]{2,}\+[^，。]{2,}", project_task):
        complexity_score += 0.3

    # Factor 4: 检测"分时复用"
    if any(kw in project_task for kw in ["分时", "复用", "可变", "灵活"]):
        complexity_score += 0.2

    # Factor 5: 检测系统级关键词
    system_keywords = ["运营", "商业模式", "长期", "可持续", "闭环"]
    if any(kw in project_task for kw in system_keywords):
        complexity_score += 0.2

    if complexity_score < 0.3:
        return "simple"
    elif complexity_score < 0.6:
        return "moderate"
    else:
        return "complex"
```

#### 3. 主导约束检测

```python
def _detect_primary_constraint(self, structured_data: Dict[str, Any]) -> Optional[str]:
    """检测主导约束"""
    project_task = structured_data.get("project_task", "")

    # Budget 约束
    budget_keywords = ["预算", "成本", "资金", "有限", "低成本", "元/㎡", "万元"]
    if any(kw in project_task for kw in budget_keywords):
        # 检测是否是极度受限
        if re.search(r"(\d+)元/㎡", project_task):
            budget_match = re.search(r"(\d+)元/㎡", project_task)
            budget = int(budget_match.group(1))
            if budget < 5000:
                return "budget"
        if any(kw in project_task for kw in ["有限", "低成本", "极低"]):
            return "budget"

    # Time 约束
    time_keywords = ["紧急", "快速", "小时", "不闭店", "临时"]
    if any(kw in project_task for kw in time_keywords):
        return "time"

    # Technical 约束
    technical_keywords = ["高海拔", "极寒", "高温", "潮湿", "防腐", "散热", "隔音", "供氧"]
    if any(kw in project_task for kw in technical_keywords):
        return "technical"

    # Regulatory 约束
    regulatory_keywords = ["保护", "文保", "历史建筑", "不能拆", "微更新", "保障房", "规范", "标准"]
    if any(kw in project_task for kw in regulatory_keywords):
        return "regulatory"

    # Cultural 约束
    cultural_keywords = ["文化", "民族", "宗教", "传统", "在地", "一带一路", "多元"]
    if any(kw in project_task for kw in cultural_keywords):
        # 进一步判断是否主导
        if len([kw for kw in cultural_keywords if kw in project_task]) >= 2:
            return "cultural"

    return None
```

#### 4. 精神深度检测

```python
def _detect_spiritual_depth(self, structured_data: Dict[str, Any]) -> str:
    """检测精神深度"""
    project_task = structured_data.get("project_task", "")
    character_narrative = structured_data.get("character_narrative", "")

    # Philosophical 级别关键词
    philosophical_keywords = [
        "存在", "虚无", "意识", "灵性", "冥想", "哲学", "伦理",
        "反思", "对话", "思考", "精神性", "宇宙", "终极"
    ]
    if any(kw in project_task for kw in philosophical_keywords):
        return "philosophical"

    # 检测意象表达（诗意描述）
    if re.search(r"[如似若像].*[般样]", project_task):
        return "philosophical"

    # Lifestyle 级别关键词
    lifestyle_keywords = [
        "生活方式", "品牌", "精神", "气质", "态度", "认同",
        "身份", "自我", "表达", "个性", "风格", "审美"
    ]
    if any(kw in project_task for kw in lifestyle_keywords):
        return "lifestyle"

    # 检测品牌名称（大写字母开头）
    if re.search(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", project_task):
        return "lifestyle"

    # 默认为 Functional
    return "functional"
```

#### 5. 跨学科检测

```python
def _detect_interdisciplinary(self, structured_data: Dict[str, Any]) -> str:
    """检测跨学科需求"""
    project_task = structured_data.get("project_task", "")

    # Philosophy/Ethics
    philosophy_keywords = ["哲学", "伦理", "道德", "意识", "存在"]
    if any(kw in project_task for kw in philosophy_keywords):
        return "philosophy"

    # Behavioral Science
    behavioral_keywords = [
        "行为经济学", "认知", "心理学", "神经科学", "注意力",
        "决策", "偏差", "损失厌恶", "锚定效应"
    ]
    if any(kw in project_task for kw in behavioral_keywords):
        return "behavioral_science"

    # Cultural Anthropology
    anthropology_keywords = [
        "文化", "传统", "民俗", "非遗", "在地", "乡土",
        "人类学", "社会学", "身份", "迁徙"
    ]
    if len([kw for kw in anthropology_keywords if kw in project_task]) >= 3:
        return "cultural_anthropology"

    # Technical Engineering
    engineering_keywords = [
        "结构", "声学", "热工", "供氧", "防腐", "散热",
        "恒温恒湿", "新风", "净化", "节能"
    ]
    if any(kw in project_task for kw in engineering_keywords):
        return "technical_engineering"

    return "pure_design"
```

#### 6. 情感/身份检测

```python
def _detect_emotional_identity(self, structured_data: Dict[str, Any]) -> Optional[str]:
    """检测情感/身份维度"""
    project_task = structured_data.get("project_task", "")
    character_narrative = structured_data.get("character_narrative", "")

    # Identity 身份认同
    identity_keywords = [
        "身份", "自我", "认同", "女性", "独立", "海归",
        "富二代", "民族", "文化背景"
    ]
    if any(kw in character_narrative for kw in identity_keywords):
        return "identity"

    # Healing 情感修复
    healing_keywords = [
        "修复", "复合", "治疗", "康复", "恢复", "临终",
        "关怀", "心理", "创伤", "疗愈"
    ]
    if any(kw in project_task for kw in healing_keywords):
        return "healing"

    # Heritage 文化传承
    heritage_keywords = [
        "传承", "保护", "历史", "遗产", "非遗", "百年",
        "老艺术家", "教学", "传授"
    ]
    if any(kw in project_task for kw in heritage_keywords):
        return "heritage"

    # Ideology 理念表达
    ideology_keywords = [
        "理念", "价值观", "主义", "精神", "倡导", "态度",
        "极简", "零碳", "可持续", "伦理"
    ]
    if any(kw in project_task for kw in ideology_keywords):
        return "ideology"

    return None
```

---

## 🎯 拆解策略模板库（Strategy Templates）

### 策略1: 功能驱动拆解法（Functional Decomposition）
**适用场景**：
- `functional_complexity = "simple"` 或 `"moderate"`
- `spiritual_depth = "functional"`
- `interdisciplinary = "pure_design"`

**拆解逻辑**：
```yaml
strategy_name: "功能驱动拆解法"
decomposition_layers:
  - layer_name: "功能识别"
    task_pattern: "识别{功能1}、{功能2}、{功能3}"
    example: "识别卧室功能、客厅功能、厨房功能"

  - layer_name: "流程分解"
    task_pattern: "分析{流程1}→{流程2}→{流程3}"
    example: "分析入户动线→公共区域→私密空间"

  - layer_name: "技术实现"
    task_pattern: "解决{技术点1}、{技术点2}"
    example: "解决隔音、解决收纳"

  - layer_name: "材料选择"
    task_pattern: "选择{材料系统}"
    example: "选择地板材料、墙面材料"

  - layer_name: "成本控制"
    task_pattern: "控制{成本项}"
    example: "控制硬装成本、软装成本"

estimated_task_count: "8-12个"
```

---

### 策略2: 意象驱动拆解法（Metaphor-Driven Decomposition）
**适用场景**：
- `spiritual_depth = "philosophical"`
- 含有诗意表达（如："月亮落在冰湖上"）

**拆解逻辑**：
```yaml
strategy_name: "意象驱动拆解法"
decomposition_layers:
  - layer_name: "意象解构"
    task_pattern: "解构'{意象}'的核心元素"
    example: "解构'月亮落在冰湖上'→光源（月亮）+反射面（冰湖）+坠落感（动态）"

  - layer_name: "情绪映射"
    task_pattern: "将{意象元素}映射到情绪触点"
    example: "光源→温柔、反射面→冷静、坠落感→孤独"

  - layer_name: "空间隐喻"
    task_pattern: "转译{情绪}为空间特质"
    example: "温柔→柔和照明、冷静→冷色材料、孤独→留白比例"

  - layer_name: "材料诗学"
    task_pattern: "选择{材料}承载{隐喻}"
    example: "选择磨砂玻璃承载'反射面'隐喻"

  - layer_name: "光影控制"
    task_pattern: "设计{光影系统}表达{动态}"
    example: "设计渐变照明表达'坠落感'"

  - layer_name: "声环境"
    task_pattern: "控制{声音}强化{氛围}"
    example: "控制绝对静默强化'冰湖'安静感"

estimated_task_count: "10-15个"
```

---

### 策略3: 约束驱动拆解法（Constraint-Driven Decomposition）
**适用场景**：
- `primary_constraint = "budget"` 或 `"time"` 或 `"technical"`

#### 3.1 预算约束型
```yaml
strategy_name: "预算约束拆解法"
decomposition_layers:
  - layer_name: "价值排序"
    task_pattern: "识别{高价值点}与{低价值点}"
    example: "识别入口第一视觉（高价值）vs 储藏间（低价值）"

  - layer_name: "成本分解"
    task_pattern: "拆解{硬装}、{软装}、{设备}成本"
    example: "拆解地板（硬装）、沙发（软装）、照明（设备）"

  - layer_name: "杠杆策略"
    task_pattern: "找到{低成本高影响}节点"
    example: "找到灯光系统（低成本高影响）"

  - layer_name: "平替方案"
    task_pattern: "为{高成本项}找{平替}"
    example: "为大理石找水磨石平替"

  - layer_name: "分期实施"
    task_pattern: "制定{P0必做}、{P1可延后}计划"
    example: "P0:硬装+基础家具、P1:艺术品+定制"

estimated_task_count: "10-15个"
```

#### 3.2 技术约束型
```yaml
strategy_name: "技术约束拆解法"
decomposition_layers:
  - layer_name: "技术难题识别"
    task_pattern: "识别{技术挑战1}、{技术挑战2}"
    example: "识别高海拔供氧、极寒保温"

  - layer_name: "技术验证"
    task_pattern: "验证{技术方案}可行性"
    example: "验证分散式供氧系统可行性"

  - layer_name: "设备选型"
    task_pattern: "选择{设备A} vs {设备B}"
    example: "选择中央新风 vs 分体式新风"

  - layer_name: "隐藏整合"
    task_pattern: "将{技术设备}整合进{空间}"
    example: "将供氧管线整合进吊顶"

  - layer_name: "备用方案"
    task_pattern: "设计{冗余系统}"
    example: "设计备用电源系统"

estimated_task_count: "12-18个"
```

---

### 策略4: 系统级拆解法（System-Level Decomposition）
**适用场景**：
- `functional_complexity = "complex"`
- `scale = "large"` 或 `"macro"`
- 包含"运营"、"商业模式"等关键词

**拆解逻辑**：
```yaml
strategy_name: "系统级拆解法"
decomposition_layers:
  - layer_name: "利益相关方分析"
    task_pattern: "识别{角色A}、{角色B}、{角色C}需求"
    example: "识别业主、租户、物业、访客需求"

  - layer_name: "业态组合研究"
    task_pattern: "研究{业态1}+{业态2}互动关系"
    example: "研究民宿+餐饮+艺术驻留互动"

  - layer_name: "动线系统设计"
    task_pattern: "设计{主动线}、{辅动线}、{服务动线}"
    example: "设计游客动线、村民动线、供应动线"

  - layer_name: "商业闭环构建"
    task_pattern: "构建{引流}→{转化}→{复购}闭环"
    example: "构建公共空间引流→民宿转化→文创复购"

  - layer_name: "运营模型设计"
    task_pattern: "设计{淡季策略}、{旺季策略}"
    example: "设计冬季本地社交、夏季游客模式"

  - layer_name: "品牌叙事系统"
    task_pattern: "构建{文化故事}→{空间表达}→{传播渠道}"
    example: "构建渔村文化→码头展示→社交媒体"

  - layer_name: "可持续机制"
    task_pattern: "设计{长期维护}、{社区参与}机制"
    example: "设计村民收益分配、培训机制"

estimated_task_count: "20-30个"
```

---

### 策略5: 跨学科融合拆解法（Interdisciplinary Fusion）
**适用场景**：
- `interdisciplinary = "cultural_anthropology"` 或 `"behavioral_science"` 或 `"philosophy"`

#### 5.1 文化人类学型
```yaml
strategy_name: "文化人类学拆解法"
decomposition_layers:
  - layer_name: "田野调研"
    task_pattern: "调研{在地文化}、{传统习俗}、{生活方式}"
    example: "调研乡村农耕文化、节日仪式、老人口述"

  - layer_name: "符号解构"
    task_pattern: "解构{传统符号}的当代意义"
    example: "解构晒场、水井、祠堂的当代功能"

  - layer_name: "文化转译"
    task_pattern: "将{文化元素}抽象为{设计语言}"
    example: "将晒场转译为公共广场、水井转译为聚集节点"

  - layer_name: "记忆触点"
    task_pattern: "植入{触发乡愁的空间元素}"
    example: "植入老木梁、石板路、竹编墙"

  - layer_name: "社区参与"
    task_pattern: "设计{村民共建}机制"
    example: "设计村民手工艺品展示墙"

  - layer_name: "文化展示"
    task_pattern: "构建{文化叙事路径}"
    example: "构建村史展示→传统工艺→当代生活路径"

estimated_task_count: "18-25个"
```

#### 5.2 行为科学型
```yaml
strategy_name: "行为科学拆解法"
decomposition_layers:
  - layer_name: "行为模式研究"
    task_pattern: "研究{用户行为A}、{行为B}"
    example: "研究商场客流行为、停留时长、购买决策"

  - layer_name: "认知偏差识别"
    task_pattern: "识别{认知偏差}并设计{干预}"
    example: "识别'损失厌恶'→设计限时优惠展示"

  - layer_name: "注意力管理"
    task_pattern: "控制{视觉焦点}、{干扰源}"
    example: "控制入口视觉焦点为主力店、减少走廊干扰"

  - layer_name: "决策节点设计"
    task_pattern: "在{关键节点}植入{引导元素}"
    example: "在分叉口植入地面箭头、灯光引导"

  - layer_name: "情绪节奏控制"
    task_pattern: "设计{兴奋}→{平静}→{高潮}节奏"
    example: "设计入口兴奋→中庭平静→品牌旗舰高潮"

  - layer_name: "实验验证"
    task_pattern: "设计{A/B测试}验证{假设}"
    example: "设计两个动线方案A/B测试客流"

estimated_task_count: "15-20个"
```

---

### 策略6: 情感修复拆解法（Emotional Healing Decomposition）
**适用场景**：
- `emotional_identity = "healing"`
- 如：婚姻修复、临终关怀、心理干预

**拆解逻辑**：
```yaml
strategy_name: "情感修复拆解法"
decomposition_layers:
  - layer_name: "情感诊断"
    task_pattern: "诊断{情感伤痛}、{触发源}"
    example: "诊断婚姻信任缺失、冲突记忆"

  - layer_name: "安全空间构建"
    task_pattern: "构建{物理安全}、{心理安全}"
    example: "构建私密卧室（物理）、柔和材质（心理）"

  - layer_name: "仪式节点设计"
    task_pattern: "设计{重启仪式}空间"
    example: "设计入户洗手台（象征洗去过去）"

  - layer_name: "情绪缓冲区"
    task_pattern: "设计{过渡空间}避免直接冲突"
    example: "设计阳台冥想区（缓冲卧室与客厅）"

  - layer_name: "共同记忆重建"
    task_pattern: "植入{正向记忆触点}"
    example: "植入旅行照片墙（唤起美好回忆）"

  - layer_name: "长期支持机制"
    task_pattern: "设计{可成长}空间"
    example: "设计可调整家具（适应关系变化）"

estimated_task_count: "12-18个"
```

---

## 🤖 动态匹配算法（Dynamic Matching Algorithm）

### 核心逻辑

```python
class TaskDecompositionStrategySelector:
    """任务拆解策略选择器"""

    def select_strategy(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        根据项目特征向量选择最佳拆解策略

        Args:
            features: ProjectFeatureExtractor 提取的特征向量

        Returns:
            {
                "primary_strategy": str,  # 主策略名称
                "secondary_strategy": Optional[str],  # 辅助策略（混合型）
                "estimated_task_count": str,  # 建议任务数量
                "reasoning": str  # 选择依据
            }
        """
        reasoning_parts = []

        # 规则1: Philosophical 精神深度 → 意象驱动拆解法
        if features["spiritual_depth"] == "philosophical":
            reasoning_parts.append("检测到哲学/精神思辨层级，采用意象驱动拆解法")
            return {
                "primary_strategy": "metaphor_driven",
                "secondary_strategy": None,
                "estimated_task_count": "10-15",
                "reasoning": "; ".join(reasoning_parts)
            }

        # 规则2: Healing 情感修复 → 情感修复拆解法
        if features["emotional_identity"] == "healing":
            reasoning_parts.append("检测到情感修复诉求，采用情感修复拆解法")
            return {
                "primary_strategy": "emotional_healing",
                "secondary_strategy": None,
                "estimated_task_count": "12-18",
                "reasoning": "; ".join(reasoning_parts)
            }

        # 规则3: 主导约束 → 约束驱动拆解法
        if features["primary_constraint"]:
            constraint_type = features["primary_constraint"]
            reasoning_parts.append(f"检测到{constraint_type}约束主导，采用约束驱动拆解法")

            task_count_map = {
                "budget": "10-15",
                "time": "8-12",
                "technical": "12-18",
                "regulatory": "10-15",
                "cultural": "15-20"
            }

            return {
                "primary_strategy": "constraint_driven",
                "secondary_strategy": constraint_type,
                "estimated_task_count": task_count_map.get(constraint_type, "10-15"),
                "reasoning": "; ".join(reasoning_parts)
            }

        # 规则4: Complex 功能复杂度 + (Large/Macro 尺度) → 系统级拆解法
        if features["functional_complexity"] == "complex" and features["scale"] in ["large", "macro"]:
            reasoning_parts.append("检测到系统级复杂项目，采用系统级拆解法")
            return {
                "primary_strategy": "system_level",
                "secondary_strategy": None,
                "estimated_task_count": "20-30",
                "reasoning": "; ".join(reasoning_parts)
            }

        # 规则5: 跨学科需求 → 跨学科融合拆解法
        if features["interdisciplinary"] != "pure_design":
            interdisciplinary_type = features["interdisciplinary"]
            reasoning_parts.append(f"检测到{interdisciplinary_type}跨学科需求，采用跨学科融合拆解法")

            task_count_map = {
                "cultural_anthropology": "18-25",
                "behavioral_science": "15-20",
                "philosophy": "15-20",
                "technical_engineering": "12-18"
            }

            return {
                "primary_strategy": "interdisciplinary_fusion",
                "secondary_strategy": interdisciplinary_type,
                "estimated_task_count": task_count_map.get(interdisciplinary_type, "15-20"),
                "reasoning": "; ".join(reasoning_parts)
            }

        # 规则6: Lifestyle 精神深度 → 功能拆解法 + 生活方式增强
        if features["spiritual_depth"] == "lifestyle":
            reasoning_parts.append("检测到生活方式表达，采用功能拆解法+生活方式增强")
            return {
                "primary_strategy": "functional",
                "secondary_strategy": "lifestyle_enhanced",
                "estimated_task_count": "12-18",
                "reasoning": "; ".join(reasoning_parts)
            }

        # 规则7: 默认 - Simple/Moderate 功能复杂度 → 功能驱动拆解法
        reasoning_parts.append("标准功能型项目，采用功能驱动拆解法")

        task_count_map = {
            "simple": "8-12",
            "moderate": "12-18"
        }

        return {
            "primary_strategy": "functional",
            "secondary_strategy": None,
            "estimated_task_count": task_count_map.get(features["functional_complexity"], "10-15"),
            "reasoning": "; ".join(reasoning_parts)
        }
```

---

## 📐 实施方案

### Phase 0: 不改代码,仅在Prompt中增强（2小时）

**修改文件**: `intelligent_project_analyzer/config/prompts/core_task_decomposer.yaml`

在 `system_prompt` 末尾添加：

```yaml
# ═══════════════════════════════════════════════════════════════
# v7.950: 智能拆解策略选择机制
# ═══════════════════════════════════════════════════════════════

## 拆解策略智能选择

在开始任务拆解前，先分析项目特征，选择最合适的拆解策略：

### 策略1: 意象驱动拆解法（Metaphor-Driven）
**触发条件**：
- 输入包含诗意表达（如："月亮落在冰湖上"、"像...一样"）
- 关键词：存在、虚无、意识、灵性、冥想、哲学

**拆解层级**：
1. 意象解构：拆解意象的核心元素
2. 情绪映射：将意象元素映射到情绪触点
3. 空间隐喻：转译情绪为空间特质
4. 材料诗学：选择材料承载隐喻
5. 光影控制：设计光影系统
6. 声环境：控制声音强化氛围

**任务数量**: 10-15个

---

### 策略2: 约束驱动拆解法（Constraint-Driven）
**触发条件**：
- 预算约束：包含"预算有限"、"低成本"、"X元/㎡"
- 时间约束：包含"紧急"、"快速"、"X小时"
- 技术约束：包含"高海拔"、"极寒"、"防腐"、"供氧"

**拆解层级（预算约束型）**：
1. 价值排序：识别高价值点与低价值点
2. 成本分解：拆解硬装、软装、设备成本
3. 杠杆策略：找到低成本高影响节点
4. 平替方案：为高成本项找平替
5. 分期实施：制定P0必做、P1可延后计划

**任务数量**: 10-18个（根据约束类型）

---

### 策略3: 系统级拆解法（System-Level）
**触发条件**：
- 功能复杂：包含"业态融合"、"多功能"、"综合体"
- 尺度大：面积>1000㎡ 或 关键词"规划"、"社区"、"片区"
- 运营导向：包含"运营"、"商业模式"、"可持续"、"闭环"

**拆解层级**：
1. 利益相关方分析：识别多方需求
2. 业态组合研究：研究业态互动
3. 动线系统设计：主动线+辅动线+服务动线
4. 商业闭环构建：引流→转化→复购
5. 运营模型设计：淡季策略+旺季策略
6. 品牌叙事系统：文化故事→空间表达→传播
7. 可持续机制：长期维护+社区参与

**任务数量**: 20-30个

---

### 策略4: 跨学科融合拆解法（Interdisciplinary）
**触发条件**：
- 文化人类学：包含3个以上关键词"文化"、"传统"、"在地"、"民俗"、"非遗"
- 行为科学：包含"行为经济学"、"认知"、"心理学"、"神经科学"、"决策"
- 哲学伦理：包含"哲学"、"伦理"、"道德"、"意识"

**拆解层级（文化人类学型）**：
1. 田野调研：调研在地文化、传统习俗
2. 符号解构：解构传统符号的当代意义
3. 文化转译：将文化元素抽象为设计语言
4. 记忆触点：植入触发乡愁的空间元素
5. 社区参与：设计村民共建机制
6. 文化展示：构建文化叙事路径

**任务数量**: 18-25个

---

### 策略5: 情感修复拆解法（Emotional Healing）
**触发条件**：
- 关键词："修复"、"复合"、"治疗"、"康复"、"临终"、"关怀"、"心理"、"创伤"

**拆解层级**：
1. 情感诊断：诊断情感伤痛、触发源
2. 安全空间构建：物理安全+心理安全
3. 仪式节点设计：设计重启仪式空间
4. 情绪缓冲区：过渡空间避免冲突
5. 共同记忆重建：植入正向记忆触点
6. 长期支持机制：设计可成长空间

**任务数量**: 12-18个

---

### 策略6: 功能驱动拆解法（Functional - 默认）
**触发条件**：
- 不满足上述任何特殊条件

**拆解层级**：
1. 功能识别：识别核心功能
2. 流程分解：分析使用流程
3. 技术实现：解决技术点
4. 材料选择：选择材料系统
5. 成本控制：控制成本项

**任务数量**: 8-15个

---

## 执行指令

**步骤1**: 阅读用户输入和结构化数据，判断符合哪个策略（可能符合多个，选择最主导的）

**步骤2**: 按照对应策略的"拆解层级"生成任务，每个层级可能对应1-5个具体任务

**步骤3**: 确保任务总数在策略建议的"任务数量"范围内

**步骤4**: 在 reasoning 字段说明选择了哪个策略及原因
```

**测试方法**：
1. 用q.txt中的案例3（乡村建设）测试 → 应触发"跨学科融合拆解法（文化人类学型）"，生成18-25个任务
2. 用案例34（诗意书房）测试 → 应触发"意象驱动拆解法"，生成10-15个任务
3. 用案例77（50万预算老房翻新）测试 → 应触发"约束驱动拆解法（预算型）"，生成10-15个任务

---

### Phase 1: 增强Phase2输出（4小时）

**修改文件**: `intelligent_project_analyzer/agents/requirements_analyst.py`

在 `_execute_phase2()` 方法中，增强输出结构：

```python
def _execute_phase2(self, ...):
    # ... 现有代码 ...

    # 🆕 v7.950: 增加项目特征分析
    project_features = self._analyze_project_features(phase2_result)
    phase2_result["project_features"] = project_features

    return phase2_result

def _analyze_project_features(self, phase2_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    分析项目特征（用于拆解策略选择）

    v7.950: 提取多维度特征向量
    """
    project_task = phase2_result.get("project_task", "")
    character_narrative = phase2_result.get("character_narrative", "")
    physical_context = phase2_result.get("physical_context", "")

    features = {
        "scale": self._detect_scale(physical_context),
        "functional_complexity": self._detect_functional_complexity(project_task),
        "primary_constraint": self._detect_primary_constraint(project_task),
        "spiritual_depth": self._detect_spiritual_depth(project_task, character_narrative),
        "interdisciplinary": self._detect_interdisciplinary(project_task),
        "emotional_identity": self._detect_emotional_identity(project_task, character_narrative),
    }

    logger.info(f"[v7.950] 项目特征分析: {features}")

    return features

def _detect_scale(self, physical_context: str) -> str:
    """检测项目尺度"""
    # 提取面积
    area_match = re.search(r"(\d+)[㎡平方米平米]", physical_context)
    if area_match:
        area = int(area_match.group(1))
        if area < 50:
            return "micro"
        elif area < 200:
            return "small"
        elif area < 1000:
            return "medium"
        elif area < 5000:
            return "large"
        else:
            return "macro"

    # 关键词识别
    if any(kw in physical_context for kw in ["规划", "社区", "片区", "轴线"]):
        return "macro"
    elif any(kw in physical_context for kw in ["酒店", "商场", "医院", "学校"]):
        return "large"
    elif any(kw in physical_context for kw in ["菜市场", "办公室", "餐厅"]):
        return "medium"
    elif any(kw in physical_context for kw in ["住宅", "公寓", "别墅"]):
        return "small"
    else:
        return "micro"

# ... 其他 _detect_* 方法，参考前面的设计 ...
```

---

### Phase 2: 修改CoreTaskDecomposer（8小时）

**修改文件**: `intelligent_project_analyzer/services/core_task_decomposer.py`

```python
class CoreTaskDecomposer:

    def decompose_core_tasks(
        self,
        user_input: str,
        structured_data: Optional[Dict[str, Any]] = None,
        state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        核心任务拆解（v7.950 增强：智能策略选择）
        """
        # ... 现有代码 ...

        # 🆕 v7.950: 提取项目特征
        project_features = structured_data.get("project_features", {})

        # 🆕 v7.950: 选择拆解策略
        strategy_info = self._select_decomposition_strategy(project_features, structured_data)
        logger.info(f" [v7.950] 选择策略: {strategy_info['primary_strategy']}, 原因: {strategy_info['reasoning']}")

        # 构建 Prompt（注入策略信息）
        prompt = self._build_prompt_with_strategy(
            user_input=user_input,
            structured_data=structured_data,
            complexity_analysis=complexity_analysis,
            strategy_info=strategy_info
        )

        # ... LLM 调用 ...

    def _select_decomposition_strategy(
        self,
        project_features: Dict[str, Any],
        structured_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        选择拆解策略（v7.950）

        Returns:
            {
                "primary_strategy": str,
                "secondary_strategy": Optional[str],
                "estimated_task_count": str,
                "reasoning": str,
                "layer_names": List[str]  # 拆解层级名称
            }
        """
        reasoning_parts = []

        # 规则1: Philosophical → 意象驱动
        if project_features.get("spiritual_depth") == "philosophical":
            return {
                "primary_strategy": "metaphor_driven",
                "secondary_strategy": None,
                "estimated_task_count": "10-15",
                "reasoning": "检测到哲学/精神思辨层级，采用意象驱动拆解法",
                "layer_names": ["意象解构", "情绪映射", "空间隐喻", "材料诗学", "光影控制", "声环境"]
            }

        # 规则2: Healing → 情感修复
        if project_features.get("emotional_identity") == "healing":
            return {
                "primary_strategy": "emotional_healing",
                "secondary_strategy": None,
                "estimated_task_count": "12-18",
                "reasoning": "检测到情感修复诉求，采用情感修复拆解法",
                "layer_names": ["情感诊断", "安全空间构建", "仪式节点设计", "情绪缓冲区", "共同记忆重建", "长期支持机制"]
            }

        # 规则3: 主导约束 → 约束驱动
        primary_constraint = project_features.get("primary_constraint")
        if primary_constraint:
            task_count_map = {
                "budget": "10-15",
                "time": "8-12",
                "technical": "12-18",
                "regulatory": "10-15",
                "cultural": "15-20"
            }

            layer_names_map = {
                "budget": ["价值排序", "成本分解", "杠杆策略", "平替方案", "分期实施"],
                "technical": ["技术难题识别", "技术验证", "设备选型", "隐藏整合", "备用方案"]
            }

            return {
                "primary_strategy": "constraint_driven",
                "secondary_strategy": primary_constraint,
                "estimated_task_count": task_count_map.get(primary_constraint, "10-15"),
                "reasoning": f"检测到{primary_constraint}约束主导，采用约束驱动拆解法",
                "layer_names": layer_names_map.get(primary_constraint, ["约束分析", "解决方案", "实施计划"])
            }

        # 规则4: Complex + Large/Macro → 系统级
        if (project_features.get("functional_complexity") == "complex" and
            project_features.get("scale") in ["large", "macro"]):
            return {
                "primary_strategy": "system_level",
                "secondary_strategy": None,
                "estimated_task_count": "20-30",
                "reasoning": "检测到系统级复杂项目，采用系统级拆解法",
                "layer_names": ["利益相关方分析", "业态组合研究", "动线系统设计", "商业闭环构建", "运营模型设计", "品牌叙事系统", "可持续机制"]
            }

        # 规则5: 跨学科 → 跨学科融合
        interdisciplinary = project_features.get("interdisciplinary")
        if interdisciplinary != "pure_design":
            task_count_map = {
                "cultural_anthropology": "18-25",
                "behavioral_science": "15-20",
                "philosophy": "15-20",
                "technical_engineering": "12-18"
            }

            layer_names_map = {
                "cultural_anthropology": ["田野调研", "符号解构", "文化转译", "记忆触点", "社区参与", "文化展示"]
            }

            return {
                "primary_strategy": "interdisciplinary_fusion",
                "secondary_strategy": interdisciplinary,
                "estimated_task_count": task_count_map.get(interdisciplinary, "15-20"),
                "reasoning": f"检测到{interdisciplinary}跨学科需求，采用跨学科融合拆解法",
                "layer_names": layer_names_map.get(interdisciplinary, ["跨学科研究", "方法论", "整合方案"])
            }

        # 默认: 功能驱动
        return {
            "primary_strategy": "functional",
            "secondary_strategy": None,
            "estimated_task_count": "8-15",
            "reasoning": "标准功能型项目，采用功能驱动拆解法",
            "layer_names": ["功能识别", "流程分解", "技术实现", "材料选择", "成本控制"]
        }

    def _build_prompt_with_strategy(
        self,
        user_input: str,
        structured_data: Dict[str, Any],
        complexity_analysis: Dict[str, Any],
        strategy_info: Dict[str, Any]
    ) -> str:
        """
        构建 Prompt（注入策略信息）
        """
        prompt_parts = [self._config["system_prompt"]]

        # 注入策略信息
        prompt_parts.append(f"\n## 本次拆解策略\n")
        prompt_parts.append(f"- 策略: {strategy_info['primary_strategy']}")
        if strategy_info.get("secondary_strategy"):
            prompt_parts.append(f"- 子策略: {strategy_info['secondary_strategy']}")
        prompt_parts.append(f"- 建议任务数: {strategy_info['estimated_task_count']}")
        prompt_parts.append(f"- 拆解层级: {', '.join(strategy_info['layer_names'])}")
        prompt_parts.append(f"- 原因: {strategy_info['reasoning']}\n")

        # ... 后续现有的 prompt 构建逻辑 ...

        return "\n\n".join(prompt_parts)
```

---

## 🧪 测试用例（基于 q.txt）

### 测试1: 乡村建设（案例3 - 狮岭村）
**预期策略**: `interdisciplinary_fusion` (cultural_anthropology)
**预期任务数**: 18-25个
**预期层级**: 田野调研、符号解构、文化转译、记忆触点、社区参与、文化展示

---

### 测试2: 诗意书房（案例34）
**预期策略**: `metaphor_driven`
**预期任务数**: 10-15个
**预期层级**: 意象解构、情绪映射、空间隐喻、材料诗学、光影控制、声环境

---

### 测试3: 预算约束（案例77 - 50万老房翻新）
**预期策略**: `constraint_driven` (budget)
**预期任务数**: 10-15个
**预期层级**: 价值排序、成本分解、杠杆策略、平替方案、分期实施

---

### 测试4: 行为经济学体验馆（案例181）
**预期策略**: `interdisciplinary_fusion` (behavioral_science)
**预期任务数**: 15-20个
**预期层级**: 行为模式研究、认知偏差识别、注意力管理、决策节点设计、情绪节奏控制、实验验证

---

### 测试5: 婚姻修复主卧（案例28）
**预期策略**: `emotional_healing`
**预期任务数**: 12-18个
**预期层级**: 情感诊断、安全空间构建、仪式节点设计、情绪缓冲区、共同记忆重建、长期支持机制

---

### 测试6: 电竞直播间（案例27）
**预期策略**: `functional`
**预期任务数**: 8-12个
**预期层级**: 功能识别、流程分解、技术实现、材料选择、成本控制

---

## 📈 预期效果

### 定量指标
- **策略覆盖率**: 100%（所有190个案例都能匹配到合适策略）
- **任务数量准确度**: 误差 < 20%（实际任务数在预期范围内）
- **分类准确率**: > 90%（策略选择符合人工判断）

### 定性指标
- **开放性**: 无硬编码，支持未来新类型项目
- **广泛性**: 覆盖住宅、商业、文化、医疗、情感、实验性等全场景
- **智能性**: 自动识别特征，动态选择最优策略

---

## 🎯 实施优先级

| Priority | 内容 | 工作量 | 效果 | ROI |
|---------|------|--------|------|-----|
| **P0** | Prompt增强（Phase 0） | 2小时 | 立即可用，策略提示 | ⭐⭐⭐⭐⭐ |
| **P1** | Phase2增强（Phase 1） | 4小时 | 特征自动提取 | ⭐⭐⭐⭐ |
| **P2** | CoreTaskDecomposer重构（Phase 2） | 8小时 | 完整智能系统 | ⭐⭐⭐⭐⭐ |

**推荐路径**: P0 → 测试验证 → P1 → 测试验证 → P2 → 全面测试

---

## 📝 总结

### 核心创新点
1. **多维度分类法**: 尺度、复杂度、约束、精神、跨学科、情感 6个维度
2. **策略模板库**: 6大拆解策略（意象、约束、系统、跨学科、情感、功能）
3. **动态匹配算法**: 基于特征向量自动选择最优策略
4. **分层实施**: P0/P1/P2 三阶段，渐进式优化

### 与硬编码方案对比

| 维度 | 硬编码方案（5层递进法） | 智能分类方案 |
|-----|---------------------|------------|
| 适用范围 | 仅乡村建设 | 全场景（190个案例） |
| 扩展性 | 需要为每个类型写硬编码 | 自动识别新类型 |
| 维护成本 | 高（每次改6个策略） | 低（改1个规则） |
| 智能程度 | 低（人工分类） | 高（自动分类） |
| 任务数准确度 | 中（11个 vs 20-30个） | 高（误差<20%） |

---

**下一步**: 是否开始实施 P0（Prompt增强）？
