# Few-shot示例库动态进化机制 - 设计方案
# 版本: v8.100规划
# 作者: AI Architecture Team
# 日期: 2026-02-16

## 🎯 设计目标

当前Few-shot示例库已完成静态标杆构建（9个核心示例），但存在以下限制：
1. **覆盖有限**: 仅覆盖190个案例的4.7%
2. **静态更新**: 季度手动更新，无法反映实时热点
3. **匹配单一**: 7维标签匹配，缺少时间/创新/紧急度维度
4. **无自适应**: 无法根据用户行为优化示例选择

动态进化机制旨在构建**三层架构 + 12维匹配 + 自学习反馈**的智能示例库。

## 🏗️ 三层架构设计

### Layer 1: 静态标杆库（Static Benchmark Pool）

**定位**: 质量标杆，代表最佳实践

**特征**:
- 数量: 9-12个精选示例
- 来源: 人工筛选高质量真实项目
- 更新频率: 季度（每3月）
- 质量门槛:
  - 任务粒度细分（无混合对象）
  - specialty_score计算合理
  - 调研类任务 ≥60%
  - 用户修改率 <25%（实测数据）

**当前状态**: ✅ 已完成9个核心示例（Phase 1+2）

**维护机制**:
- 每季度根据Layer 2使用频率补充1-2个新示例
- 淘汰连续2季度未匹配的示例
- 人工质量审核 + 专家评审

---

### Layer 2: 动态热点池（Dynamic Trending Pool）

**定位**: 反映当前设计热点和新兴趋势

**特征**:
- 数量: 20-30个
- 来源: q.txt剩余181个案例 + 外部热点项目
- 更新频率: 月度（每月1日）
- 筛选标准:
  - 与Layer 1特征向量差异度 >0.4（避免重复）
  - 项目发生时间 <2年（保持新鲜度）
  - 涵盖新兴方向（元宇宙空间/碳中和设计/数字孪生/疗愈空间/适老化等）
  - 标签覆盖未被Layer 1覆盖的组合

**筛选算法**:
```python
def select_trending_examples(candidates, layer1_examples):
    """从候选池筛选动态热点示例"""
    scores = []
    for candidate in candidates:
        # 1. 计算与Layer 1的差异度（余弦距离）
        diff_score = min([
            1 - cosine_similarity(candidate.vector, ex.vector)
            for ex in layer1_examples
        ])

        # 2. 时间新鲜度（2年内1.0, 3年0.5, >4年0）
        age_years = (datetime.now() - candidate.project_date).days / 365
        freshness_score = max(0, 1 - (age_years - 2) * 0.5)

        # 3. 标签覆盖新颖度（未被Layer 1覆盖的标签组合）
        layer1_tag_combos = get_tag_combinations(layer1_examples)
        novelty_score = len(candidate.tags - layer1_tag_combos) / len(candidate.tags)

        # 4. 社区热度（可选，外部项目）
        trend_score = get_trending_score(candidate.tags)  # Pinterest/Archdaily热度

        # 综合评分
        final_score = (
            0.35 * diff_score +
            0.25 * freshness_score +
            0.25 * novelty_score +
            0.15 * trend_score
        )
        scores.append((candidate, final_score))

    # 返回Top 20-30
    return sorted(scores, key=lambda x: x[1], reverse=True)[:30]
```

**候选来源**:
1. **q.txt剩余案例** (181个):
   - Q1-Q190中未进入Layer 1的案例
   - 优先筛选特征向量差异大的

2. **外部热点项目** (可选):
   - Archdaily年度优秀项目
   - Pinterest热门设计趋势
   - 国内设计公众号（一条/日日新等）高热度项目

**质量门槛**:
- 任务数量 ≥10个
- specialty_score合理性（0.1-0.9范围）
- 匹配成功率 >15%（月度统计）

---

### Layer 3: 实时生成池（Real-Time Generated Pool）

**定位**: 个性化学习，越用越懂用户

**特征**:
- 数量: 不限（用户级动态）
- 来源: 用户历史项目自动提取
- 更新频率: 实时（每次项目完成）
- 生成条件:
  - 用户对任务修改率 <30%（高质量项目）
  - 项目完成且通过质量验证（≥80%任务完成）
  - 用户授权加入示例池（隐私保护）

**提取算法**:
```python
def extract_user_example(completed_project, user):
    """从用户完成项目提取示例"""
    # 1. 质量验证
    if completed_project.task_edit_rate > 0.3:
        return None  # 修改率过高，说明匹配不佳

    if completed_project.completion_rate < 0.8:
        return None  # 完成度不足

    # 2. 用户授权检查
    if not user.privacy_settings.allow_example_extraction:
        return None

    # 3. 提取示例结构
    example = {
        "project_info": extract_project_info(completed_project),
        "tags_matrix": extract_tags_matrix(completed_project),
        "feature_vector": calculate_feature_vector(completed_project),
        "ideal_tasks": extract_accepted_tasks(completed_project),  # 只保留用户接受的任务
        "specialty_score": calculate_specialty_score(completed_project),
    }

    # 4. 脱敏处理（移除敏感信息）
    example = anonymize_example(example)

    # 5. 标记为用户私有（仅该用户可见）
    example["user_id"] = user.id
    example["is_private"] = True

    return example
```

**隐私保护**:
- 默认关闭，用户主动授权
- 脱敏处理（移除地址/姓名/敏感信息）
- 仅用户本人可见（不跨用户共享）
- 用户可随时删除

**质量保障**:
- 用户修改率 <30%（说明匹配度高）
- 项目完成率 ≥80%
- 任务粒度验证（自动检测混合对象任务）

---

## 🔢 12维匹配升级

### 当前7维 tags_matrix（已实施）

1. **space_type**: 空间类型（hotel/residential/office等）
2. **scale**: 项目规模（micro/small/medium/large/xlarge）
3. **design_direction**: 设计方向主导（cultural/commercial/functional等）
4. **user_profile**: 用户特征（family/elderly/professional等）
5. **challenge_type**: 挑战类型（budget/stakeholder/extreme_environment等）
6. **methodology**: 方法论（benchmarking/participatory_design等）
7. **phase**: 项目阶段（concept/schematic/detailed/construction）

### 新增5维（待实施）

8. **discipline** (学科属性)
   - 类型: 单选
   - 可选值: `architecture | interior | landscape | urban_planning | multidisciplinary`
   - 作用: 区分建筑设计vs室内设计，影响任务类型权重
   - 示例:
     - `architecture`: 书法大酒店（建筑主导）
     - `interior`: 电竞直播间（室内主导）
     - `multidisciplinary`: 菜市场改造（建筑+室内+社区）

9. **urgency** (紧急度)
   - 类型: 浮点数 0-1
   - 计算规则:
     - 1.0: 交付期<1月（应急项目）
     - 0.7: 交付期1-3月（正常紧凑）
     - 0.4: 交付期3-6月（正常）
     - 0.0: 交付期>6月（充裕）
   - 作用: 影响调研深度，紧急度高则压缩调研时间
   - 匹配权重: `research_task_count = base_count * (1.5 - 0.5 * urgency)`

10. **innovation_quotient** (创新商)
    - 类型: 浮点数 0-1
    - 计算规则:
      - 用户明确表达"希望突破常规" → 0.8-1.0
      - 项目类型本身新颖（元宇宙空间/NFT画廊等） → 0.7-0.9
      - 常规项目 → 0.2-0.4
    - 作用: 影响示例强度选择
      - innovation_quotient >0.7 → 优先选light示例（鼓励创新）
      - innovation_quotient <0.3 → 优先选strong示例（提供模板）

11. **commercial_sensitivity** (商业敏感度)
    - 类型: 浮点数 0-1
    - 计算规则:
      - 地产开发/销售中心 → 0.9-1.0
      - 商业空间 → 0.6-0.8
      - 住宅/文化空间 → 0.3-0.5
      - 公共空间/社区项目 → 0-0.2
    - 作用: 影响成本控制/运营策略任务的比重
      - commercial_sensitivity >0.7 → 增加成本/ROI/销售转化任务

12. **cultural_depth** (文化深度)
    - 类型: 浮点数 0-1
    - 计算规则:
      - 文化主题项目（博物馆/文化中心） → 0.8-1.0
      - 地域文化表达强烈 → 0.6-0.8
      - 现代简约/国际风格 → 0.1-0.3
    - 作用: 影响文化研究/在地调研任务的比重
      - cultural_depth >0.7 → 增加文化研究/符号转译任务

### 12维匹配算法

```python
def match_few_shot_examples_v2(project_input, examples_pool):
    """v8.100 12维匹配算法"""
    scores = []

    for example in examples_pool:
        # ========== 权重分配 ==========
        # 35% 标签重叠度（7维tags_matrix）
        tag_overlap_score = calculate_tag_overlap(
            project_input.tags_matrix,
            example.tags_matrix
        )

        # 25% 能力向量相似度（12维feature_vector）
        vector_similarity = cosine_similarity(
            project_input.feature_vector,
            example.feature_vector
        )

        # 20% 尺度匹配度
        scale_match_score = calculate_scale_match(
            project_input.scale,
            example.scale
        )

        # 15% 用户画像重叠
        user_overlap_score = len(
            set(project_input.user_profile) & set(example.user_profile)
        ) / len(set(project_input.user_profile))

        # 5% 时间新鲜度（仅Layer 2）
        if example.layer == 2:
            freshness_score = calculate_freshness(example.project_date)
        else:
            freshness_score = 0.5  # Layer 1/3中性

        # ========== 新增5维调节 ==========
        # 学科属性（精确匹配+0.1，不匹配-0.15）
        discipline_bonus = 0.1 if (
            project_input.discipline == example.discipline
        ) else -0.15

        # 紧急度（差异惩罚）
        urgency_penalty = -0.1 * abs(
            project_input.urgency - example.urgency
        )

        # 创新商（影响示例强度选择）
        if project_input.innovation_quotient > 0.7:
            # 高创新需求，优先light示例
            innovation_bonus = 0.15 if example.recommended_strength == 'light' else -0.1
        elif project_input.innovation_quotient < 0.3:
            # 低创新需求，优先strong示例
            innovation_bonus = 0.15 if example.recommended_strength == 'strong' else -0.1
        else:
            innovation_bonus = 0  # 中性

        # 商业敏感度（差异<0.3加分，>0.5惩罚）
        commercial_diff = abs(
            project_input.commercial_sensitivity - example.commercial_sensitivity
        )
        if commercial_diff < 0.3:
            commercial_bonus = 0.1
        elif commercial_diff > 0.5:
            commercial_bonus = -0.15
        else:
            commercial_bonus = 0

        # 文化深度（差异<0.3加分，>0.5惩罚）
        cultural_diff = abs(
            project_input.cultural_depth - example.cultural_depth
        )
        if cultural_diff < 0.3:
            cultural_bonus = 0.1
        elif cultural_diff > 0.5:
            cultural_bonus = -0.15
        else:
            cultural_bonus = 0

        # ========== 综合评分 ==========
        final_score = (
            0.35 * tag_overlap_score +
            0.25 * vector_similarity +
            0.20 * scale_match_score +
            0.15 * user_overlap_score +
            0.05 * freshness_score +
            discipline_bonus +
            urgency_penalty +
            innovation_bonus +
            commercial_bonus +
            cultural_bonus
        )

        scores.append((example, final_score))

    # 返回Top 3示例（多样性去重）
    return select_diverse_top_k(scores, k=3)


def calculate_tag_overlap(tags1, tags2):
    """计算7维标签重叠度"""
    overlaps = []
    for dimension in ['space_type', 'scale', 'design_direction',
                      'user_profile', 'challenge_type', 'methodology', 'phase']:
        set1 = set(tags1.get(dimension, []))
        set2 = set(tags2.get(dimension, []))
        if len(set1) == 0 or len(set2) == 0:
            overlaps.append(0)
        else:
            overlap = len(set1 & set2) / len(set1 | set2)  # Jaccard相似度
            overlaps.append(overlap)

    # 加权平均（space_type和challenge_type权重高）
    weights = [0.25, 0.15, 0.20, 0.15, 0.20, 0.05, 0.05]
    return sum(w * o for w, o in zip(weights, overlaps))
```

---

## 🔄 自学习反馈循环

### 数据收集

**用户行为数据**:
1. **edit_rate** (任务修改率)
   - 计算: `修改的任务数 / 生成的任务总数`
   - 阈值: <0.25优秀, 0.25-0.40良好, >0.40需优化

2. **accept_rate** (任务接受率)
   - 计算: `用户标记为"接受"的任务数 / 生成的任务总数`
   - 阈值: >0.75优秀, 0.60-0.75良好, <0.60需优化

3. **dwell_time** (停留时长)
   - 计算: `用户在该任务上的总停留时间`
   - 含义: 停留时长适中（2-5分钟）说明有价值，<30秒说明直接跳过

4. **quality_score** (最终项目质量)
   - 计算: 基于项目完成度、用户反馈、专家评审（如有）
   - 范围: 0-1

**示例级数据**:
- **match_count**: 该示例被匹配的总次数
- **match_success_rate**: 匹配后用户接受率（accept_rate均值）
- **avg_edit_rate**: 该示例的平均修改率
- **last_match_date**: 最后一次匹配时间（判断是否过时）

### 权重更新算法

```python
def update_example_weight(example, user_feedbacks):
    """每周更新示例权重"""
    # 1. 计算综合质量分
    quality_scores = []
    for feedback in user_feedbacks:
        score = (
            (1 - feedback.edit_rate) * 0.4 +           # 低修改率
            feedback.accept_rate * 0.3 +                # 高接受率
            min(1, feedback.dwell_time / 300) * 0.15 +  # 适度停留（5分钟为满分）
            feedback.quality_score * 0.15               # 最终质量
        )
        quality_scores.append(score)

    # 2. 计算加权平均（近期权重高）
    weights = [1.5 ** (-i) for i in range(len(quality_scores))]  # 指数衰减
    weighted_score = sum(s * w for s, w in zip(quality_scores, weights)) / sum(weights)

    # 3. 结合匹配频率（避免冷门示例被误淘汰）
    match_frequency_bonus = min(0.2, example.match_count / 100 * 0.2)

    final_weight = weighted_score + match_frequency_bonus

    return final_weight


def weekly_maintenance():
    """每周维护任务"""
    for example in all_examples:
        # 1. 更新权重
        feedbacks = get_recent_feedbacks(example, days=7)
        if len(feedbacks) > 0:
            new_weight = update_example_weight(example, feedbacks)
            example.weight = 0.7 * example.weight + 0.3 * new_weight  # 平滑更新

        # 2. 淘汰标记（连续4周低权重）
        if example.weight < 0.3:
            example.low_weight_weeks += 1
            if example.low_weight_weeks >= 4:
                example.status = 'deprecated'
                notify_admin(f"示例 {example.name} 被标记为待淘汰")
        else:
            example.low_weight_weeks = 0

        # 3. Layer 2热度更新
        if example.layer == 2:
            # 检查新鲜度（>2年自动降权）
            age_years = (datetime.now() - example.project_date).days / 365
            if age_years > 2:
                example.weight *= 0.9
```

### 渐进式强度衰减

**设计哲学**: 用户越熟悉某类项目，越应该鼓励创新而非依赖模板。

```python
def calculate_progressive_strength(example, user):
    """渐进式强度衰减"""
    # 统计用户在该示例类别的使用次数
    similar_projects = get_user_projects_by_tags(
        user,
        example.tags_matrix,
        similarity_threshold=0.6
    )
    usage_count = len(similar_projects)

    # 原始强度
    base_strength = example.recommended_strength  # 'light' | 'medium' | 'strong'

    # 衰减规则
    if usage_count == 0:
        # 首次使用该类型 → 保持原强度
        return base_strength
    elif usage_count <= 2:
        # 2-3次使用 → 降低一档
        strength_map = {'strong': 'strong', 'medium': 'light', 'light': 'light'}
        return strength_map[base_strength]
    elif usage_count <= 5:
        # 3-5次使用 → 降低两档
        strength_map = {'strong': 'medium', 'medium': 'light', 'light': 'light'}
        return strength_map[base_strength]
    else:
        # >5次使用 → 全部轻示例
        return 'light'
```

**示例**:
- 用户首次做"精品民宿"项目 → 匹配林芝民宿示例（strong强度）→ 提供14个详细任务
- 用户第3次做"精品民宿"项目 → 匹配林芝民宿示例（medium强度）→ 提供10个核心任务
- 用户第6次做"精品民宿"项目 → 匹配林芝民宿示例（light强度）→ 提供6个思路启发

---

## 📊 实施路线图

### Phase 3.1: 12维匹配升级（预计2周）

**任务清单**:
- [ ] 在`tags_matrix`模型中添加5个新维度字段
- [ ] 实现`calculate_tag_overlap_v2()`函数（12维）
- [ ] 实现新增5维的计算规则
- [ ] 更新`match_few_shot_examples()`主函数
- [ ] 单元测试（30个测试用例）
- [ ] A/B测试对比新旧匹配算法效果

**验收标准**:
- 匹配精度提升 ≥15%（用户修改率下降）
- 计算耗时 <200ms（可接受性能）

---

### Phase 3.2: Layer 2动态热点池（预计4周）

**任务清单**:
- [ ] 从q.txt筛选20-30个候选示例
- [ ] 实现`select_trending_examples()`算法
- [ ] 建立月度自动更新Cron任务
- [ ] 实现外部热点项目爬虫（可选）
- [ ] 可视化Dashboard展示热点趋势

**验收标准**:
- Layer 2示例覆盖率达到15-20%
- 月度更新成功率 >95%
- 热点示例匹配成功率 >15%

---

### Phase 3.3: 自学习反馈系统（预计3周）

**任务清单**:
- [ ] 实现用户行为数据收集（edit_rate/accept_rate/dwell_time）
- [ ] 实现`update_example_weight()`权重更新算法
- [ ] 实现`weekly_maintenance()`定期维护任务
- [ ] 实现渐进式强度衰减`calculate_progressive_strength()`
- [ ] 建立示例质量监控Dashboard

**验收标准**:
- 权重更新周期稳定（每周日凌晨）
- 低质量示例自动淘汰（4周低权重）
- 用户满意度提升 ≥20%

---

### Phase 3.4: Layer 3实时生成池（预计6周）

**任务清单**:
- [ ] 实现`extract_user_example()`提取算法
- [ ] 实现脱敏处理`anonymize_example()`
- [ ] 建立用户隐私授权机制
- [ ] 实现用户私有示例库
- [ ] 可视化展示用户示例贡献

**验收标准**:
- 用户授权率 >30%
- 提取示例质量达标率 >80%
- 隐私保护100%合规

---

## 🎯 预期效果

### 定量指标
- **示例覆盖率**: 4.7% → 25%（Layer 1+2）
- **匹配精度**: 用户修改率 35% → 20%
- **用户满意度**: NPS分数提升 20-30分
- **系统适应性**: 新兴项目类型识别率 >70%

### 定性价值
- **智能化**: 从静态查询到动态推荐
- **个性化**: 越用越懂用户偏好
- **自进化**: 无需人工维护，自动优化
- **开放性**: 用户贡献示例，共建生态

---

## 📚 参考文献

1. **推荐系统**:
   - Collaborative Filtering in Recommender Systems (Netflix)
   - Deep Learning for Personalized Recommendations (Google)

2. **自适应学习**:
   - Multi-Armed Bandit Algorithms (Thompson Sampling)
   - Contextual Bandits for User Behavior Modeling

3. **相似度匹配**:
   - Cosine Similarity in High-Dimensional Spaces
   - Jaccard Index for Tag-based Matching

4. **质量评估**:
   - User Engagement Metrics (Dwell Time, Edit Rate)
   - Implicit Feedback Systems (Spotify, YouTube)

---

**文档版本**: v8.100 Draft
**待审核**: 技术团队 + 产品经理
**预计启动时间**: Phase 2完成后1周内
