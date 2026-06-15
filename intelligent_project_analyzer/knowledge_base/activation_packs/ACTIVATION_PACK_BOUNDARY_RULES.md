# 激活包 vs ontology 边界规则

> 一句话：**ontology.yaml 是"教科书"（讲所有空间共通的设计议题），激活包是"开店手册"（讲具体业态的落地参数）。两者分层不重叠。**

新建激活包（咖啡馆、服装店、律所、眼镜店、宠物医院…）之前，必须读完这份文档。

> 📚 相关协议:
> - 系统**自我迭代**协议 → `sf/2026.5.16/SELF_EVOLUTION_PROTOCOL.md`
>   (讲系统如何"用得越多越聪明", 含 4 级迭代框架 + 4 条数据回路)
> - 分类系统**主索引** → `intelligent_project_analyzer/config/registries/classification_master_index.yaml`
>   (讲 9 个分类轴的关系 + 改动同步规则)

---

## 分层关系（一张图）

```
┌─────────────────────────────────────────────────────────────────┐
│  ontology.yaml (knowledge_base/ontology.yaml)                    │
│  ─ "教科书" — 写"该想什么问题"                                     │
│                                                                  │
│  ontology_frameworks (17 个):                                    │
│    └ meta_framework                通用本体 (所有空间)            │
│    └ commercial_dining             所有餐饮共通议题 (12 个)        │
│    └ commercial_office             所有办公共通议题                │
│    └ ... 等 17 个                                                │
│                                                                  │
│  activation_profiles (16 个):                                    │
│    └ commercial_dining             推荐激活的 E 维度: [E2,E3,E5,E7]│
│    └ ... 等 16 个                                                │
│                                                                  │
│  expert_extensions (14 个):                                      │
│    └ 灯光工程师 / 资本策略 / 情感洞察 ... 等                       │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │ 激活包"挂在"ontology framework 下,
                              │ 通过 routing_binding.parent_project_type_id 声明继承
                              │
┌─────────────────────────────────────────────────────────────────┐
│  activation_packs/*.yaml                                         │
│  ─ "开店手册" — 写"具体怎么做"                                     │
│                                                                  │
│  tea_drink_store_pack.yaml:                                      │
│    routing_binding.parent_project_type_id: commercial_dining ⭐  │
│    必填维度: [E2, E6, E9]    ← 在 ontology 推荐基础上"收紧 + 新增" │
│    通道净宽: 1100mm          ← 具体量化参数 (ontology 不会写)     │
│    出杯速率: 60-90 杯/小时    ← 具体量化参数 (ontology 不会写)     │
│    必备设备: [水电气...]      ← 具体清单 (ontology 不会写)         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6 条边界规则

每条都说明**人话原则** + **是否可自动校验** + **校验方式**。

### 规则 1：ontology 写"问题"，激活包写"答案"

**人话**：
- ontology 说 "**声学氛围怎么处理是个核心议题**" — 提出问题
- 激活包说 "**茶饮店因为出杯噪音大，吸声材料放天花，混响时间 ≤ 0.6 秒**" — 给出答案

**校验**：✅ **半自动**
- validate_activation_pack.py 检测激活包字段值是否含**数字 + 单位**（mm/秒/次/% 等）
- 如果激活包内全是议题命名风格而无量化参数 → WARN（你写得太抽象了）

---

### 规则 2：激活包"继承 + 收紧 + 新增"E 维度，不重定义

**人话**：
- ontology 推荐 commercial_dining 关注 `[E2, E3, E5, E7]`
- 茶饮包可以：
  - **收紧**：把 E2 从推荐 → 必填（required_dimensions）
  - **新增**：E6（运营系统）原本不在推荐里，茶饮店强加进来
  - **降级**：E3 从推荐 → recommended（备选）
- 茶饮包**不能**重新定义 E2 是什么 — 那是 `ontology_dimension_registry.yaml` 的事

**校验**：✅ **全自动**
- 激活包 `domain_framework.required_dimensions + recommended_dimensions` 内的 E 维度 ID
- 必须存在于 `knowledge_base/ontology_dimension_registry.yaml::ontology_dimensions`
- 如果 ID 不存在 → ERROR
- 如果推荐 E 维度与 ontology.yaml 父 framework 的 activation_profile.elevated_topics 完全无交集 → WARN（继承关系可疑）

---

### 规则 3：抽象议题归 ontology，可量化参数归激活包

**人话**：

| 应该在 ontology.yaml | 应该在激活包 |
|---|---|
| "翻台率与动线设计" (议题名) | "通道最小净宽 1100mm" |
| "声学氛围与噪音控制" (议题名) | "混响时间 ≤ 0.6 秒" |
| "厨房与前厅关系" (议题名) | "制作台到取餐台距离 ≤ 1.2m" |

**判断标准**：能否写出**具体数字、清单、流程图**？
- 能 → 进激活包
- 只是议题命名 → 归 ontology

**校验**：✅ **半自动**
- 检测激活包是否有量化字段（zoning_heuristics / equipment_precheck / *_simulation_profile 等）
- 完全没有 → WARN（你这激活包没落地参数，徒有其名）

---

### 规则 4：跨业态共通归 ontology，业态专属归激活包

**人话**：

- "所有商业餐饮都要考虑翻台" → 进 ontology
- "茶饮店的取餐台必须紧邻制作台" → 进激活包
- "火锅店换气次数 ≥ 30 次/小时" → 火锅激活包（如果建的话）

**校验**：❌ **人工** — 难以自动判断"什么算共通什么算专属"。
- 建议在 Code Review 时人工确认：新增字段时问自己"这个会不会咖啡馆/中餐厅也需要"——是 → 提到 ontology；不是 → 留激活包

---

### 规则 5：激活包**必须**声明 routing_binding.parent_project_type_id

**人话**：
- 激活包就像挂在父类型下的"特化版"
- `routing_binding.parent_project_type_id: commercial_dining` 这一句**是继承声明**
- ontology.yaml 自己**不知道**激活包存在；激活包**必须明示**自己挂在哪
- 这是单向继承，不耦合

**校验**：✅ **全自动**
- 激活包顶层必须有 `routing_binding.parent_project_type_id` 字段
- 该字段的值必须存在于 ontology.yaml::ontology_frameworks 内（除非父 type 是 meta_framework）
- 该字段的值也必须存在于 PROJECT_TYPE_REGISTRY 内
- 任何缺失 → ERROR

---

### 规则 6：ontology 兜底，激活包加分（不能反过来）

**人话**：

> **没有激活包**时，系统仍能用 ontology 给出 **70 分回答**（粗粒度但完整）。
> **有激活包**时，系统给出 **90 分回答**（细粒度且专属）。

**绝对不能出现的情况**：没有激活包，系统就哑火。

例：用户说"做一个宠物殡仪馆"——
- 系统没有 pet_funeral_pack，但**必须**用 meta_framework + healing_repair founding_type 给出通用回答
- **不能**因为没专项包就答不出来

**校验**：✅ **全自动**
- 激活包不存在时，系统 fallback 到父 framework
- 父 framework 必须在 ontology.yaml::ontology_frameworks 内
- 如果父 framework 也不存在 → ERROR（说明 detector 路由错了，或 ontology 不完整）

---

## 激活包必填字段清单（schema v1）

新建任何激活包必须有以下字段（校验器会检查）：

```yaml
schema_version: activation_pack.v1
pack_id: <唯一 ID, snake_case>
status: active_mvp | active_light | reserved_light | reserved
owner: <维护责任人>
last_updated: YYYY-MM-DD

routing_binding:                                # ⭐ 规则 5
  parent_project_type_id: <必填, 存在于 PROJECT_TYPE_REGISTRY>
  subdomain_id: <必填, 存在于 SUBDOMAIN_REGISTRY>

domain_framework:                                # ⭐ 规则 2
  required_dimensions:   [E?_xxx, ...]           # 必填的本体维度 (ID 必须存在于 ontology_dimension_registry)
  recommended_dimensions: [E?_xxx, ...]          # 推荐的本体维度
```

可选但**强烈推荐**：

```yaml
supported_project_scales: [...]      # 支持的 project_scale
default_project_conditions: [...]    # 默认的 project_conditions
active_spatial_layer_ids: [...]      # 激活的空间层
active_discipline_ids: [...]         # 涉及的学科
zoning_heuristics: { ... }           # 规则 3: 量化参数
equipment_precheck: { ... }          # 规则 3: 量化参数
operation_model: { ... }             # 规则 3: 运营节点
ask_yourself: [...]                  # 认知槽位
knowledge_recall_profile: { ... }    # 知识召回偏置
risk_control: { ... }                # 风险红线
```

---

## 怎么跑校验器

```bash
# 校验所有激活包
cd d:/11-20/2026.2.25/langgraph-design
python -m intelligent_project_analyzer.services.validate_activation_pack

# 校验单个激活包
python -m intelligent_project_analyzer.services.validate_activation_pack \
    intelligent_project_analyzer/knowledge_base/activation_packs/tea_drink_store_pack.yaml
```

输出示例：
```
[PASS] tea_drink_store_pack.yaml
  ✅ Rule 5: parent_project_type_id=commercial_dining (found in registry)
  ✅ Rule 5: subdomain_id=tea_drink_store (found in SUBDOMAIN_REGISTRY)
  ✅ Rule 2: All E dimensions exist in ontology_dimension_registry
  ✅ Rule 3: Found quantitative parameters (zoning_heuristics, equipment_precheck)
  ✅ Rule 6: Parent framework exists in ontology.yaml
  ⚠️ Rule 1: 1 field name uses topic-style naming (consider rephrasing)
```

CI / 上线前必须跑校验器，**任何 ERROR 直接拒绝合并**，WARN 由 Code Review 决定。

---

## 新建激活包的标准动作（人话版）

假设你要建 `coffee_shop_pack.yaml`：

1. **复制 tea_drink_store_pack.yaml 当模板**
2. **改 routing_binding**：parent=commercial_dining, subdomain_id=coffee_shop
3. **改 domain_framework**：从 ontology.yaml::activation_profiles.commercial_dining.elevated_topics 抄推荐维度，按咖啡馆特点收紧/新增
4. **改 zoning_heuristics**：咖啡馆通道宽度、吧台高度、座位间距（具体数字）
5. **改 equipment_precheck**：咖啡机、磨豆机、奶泡机的水电气需求
6. **改 operation_model**：咖啡馆的核心运营节点（点单 / 制作 / 取餐 / 堂食）
7. **改 ask_yourself**：咖啡馆的认知槽位
8. **跑校验器**：`python -m intelligent_project_analyzer.services.validate_activation_pack`
9. **跑 190 题回归**：确认零回归
10. **在 SUBDOMAIN_REGISTRY 加 coffee_shop 条目**（不能跳步）

---

## 常见反模式（不要做）

| ❌ 反模式 | ✅ 应该 |
|---|---|
| 在激活包里重新定义 E2 是什么 | 在 ontology_dimension_registry.yaml 改 E2 |
| 在 ontology.yaml 里写"茶饮店通道宽 1100mm" | 这是茶饮专属参数，写到 tea_drink_store_pack |
| 激活包不写 parent_project_type_id（让系统猜） | 必填，必须明示挂在哪个 framework 下 |
| 激活包列出 30 个 E 维度（全部 required） | 收紧到 3-5 个 required，其余 recommended |
| 没建激活包，系统就报错说"不支持" | 系统应该用父 framework 兜底，永远不哑火（规则 6） |
| 重复字段：knowledge_base_binding + knowledge_binding + knowledge_recall_profile 都列同样内容 | 只留 knowledge_recall_profile（v1.9 正式协议） |

---

## 字段命名约定（避免与 ontology 重叠）

为了让"ontology 议题 vs 激活包参数"在字段命名上一眼能分辨，建议：

| 议题命名（ontology 风格） | 参数命名（激活包风格） |
|---|---|
| `elevated_topics` | `required_dimensions` / `recommended_dimensions` |
| `key_tensions` | `operation_model.key_conflicts` |
| `guidance` (文字段落) | `zoning_heuristics` (键值表) |
| `typical_depth` | `domain_framework.profile_id` |

激活包里**不要**使用 `_topics / _themes / _philosophy` 这类纯议题命名风格，**多用** `_rules / _heuristics / _profile / _params / _thresholds` 这类参数命名风格。

校验器会基于此命名约定做启发式检测。
