# Layer 2 多源融合架构设计

**版本**: v8.110.0
**日期**: 2026-02-17
**状态**: 架构设计阶段

---

## 🎯 核心理念

Layer 2 = **外部热点池** + **用户私有池** + **人工策展池**

三源融合，动态平衡，实现：
- **时效性**（外部数据源，每月更新）
- **个性化**（用户历史项目，越用越懂）
- **质量保障**（人工策展，兜底方案）

---

## 📊 三源权重策略

### 匹配时权重分配

```python
final_candidates = (
    0.40 * external_pool_candidates +      # 40% 外部热点池
    0.30 * user_private_candidates +       # 30% 用户私有池
    0.30 * curated_pool_candidates         # 30% 人工策展池
)
```

### 动态权重调整

| 场景 | 外部 | 用户 | 策展 |
|------|------|------|------|
| **新用户（使用<3次）** | 30% | 0% | 70% |
| **熟悉用户（3-10次）** | 40% | 20% | 40% |
| **资深用户（>10次）** | 40% | 40% | 20% |
| **外部数据失效** | 0% | 30% | 70% |

---

## 🏗️ 架构设计

### 1. 数据源层（Data Sourcing Layer）

#### 数据源A：外部平台爬虫
**目标平台**:
- Archdaily（https://www.archdaily.cn/cn）
- Gooood（https://www.gooood.cn）
- Dezeen（https://www.dezeen.com）- 可选

**爬取策略**:
```python
# 每月1日自动执行
def crawl_external_sources():
    """
    爬取过去30天热门项目
    筛选标准：
    - 浏览量 >5000
    - 发布时间 <30天
    - 包含完整项目描述
    - 至少5张图片
    """
    sources = [
        ArchdailyCrawler(region="cn", days=30, min_views=5000),
        GoooodCrawler(days=30, featured=True),
    ]

    raw_projects = []
    for crawler in sources:
        raw_projects.extend(crawler.fetch())

    # LLM提取特征
    analyzed_projects = []
    for project in raw_projects:
        features = llm_extract_features(project.description)
        analyzed_projects.append({
            "source": project.source,
            "title": project.title,
            "url": project.url,
            "features": features,  # 12维特征向量
            "tags_matrix": features.tags_matrix,
            "publish_date": project.date,
        })

    # 计算与Layer 1差异度
    candidates = calculate_diversity(analyzed_projects, layer1_examples)

    # 筛选Top 20
    return select_top_k(candidates, k=20, diversity_threshold=0.4)
```

**技术栈**:
- 爬虫：Playwright（应对动态加载）+ BeautifulSoup
- 反爬虫：随机UA + 代理池 + 请求限速
- 存储：`external_layer2_cache.json`（30天有效期）

#### 数据源B：用户历史项目
**触发条件**:
```python
def can_extract_user_project(project):
    """
    判断用户项目是否可作为示例
    """
    return (
        project.completion_rate >= 0.8 and          # 完成度≥80%
        project.edit_rate <= 0.3 and                # 修改率≤30%
        project.user_satisfaction >= 4.0 and        # 满意度≥4星
        project.task_count >= 15 and                # 任务数≥15（充实度）
        project.user_authorization == True          # 用户授权
    )
```

**脱敏处理**:
```python
def anonymize_project(project):
    """
    敏感信息脱敏
    """
    return {
        "project_name": "[用户项目]",                # 隐藏真实项目名
        "location": project.location.city,          # 仅保留城市
        "client_info": "REDACTED",                  # 移除客户信息
        "dimensions": {
            "scale": project.scale,                 # 保留尺度
            "budget_level": project.budget_level,   # 预算等级（高/中/低）
        },
        "tasks": project.tasks,                     # 任务列表（保留）
        "tags_matrix": project.tags_matrix,         # 标签（保留）
        "feature_vector": project.feature_vector,   # 特征向量（保留）
    }
```

**存储策略**:
- 位置：`user_private_layer2/{user_id}/`
- 权限：仅用户本人可见
- 删除：用户可随时删除
- 过期：6个月未使用自动归档

#### 数据源C：人工策展池
**策展原则**:
1. **趋势引领**: 捕捉未被外部数据源覆盖的新兴方向
2. **质量兜底**: 外部爬虫失效时的备选方案
3. **理论深度**: 设计方法论、哲学思考类案例

**策展清单（初始10个）**:
| ID | 主题 | 来源 | 状态 |
|----|------|------|------|
| C01 | 元宇宙展厅设计方法论 | 人工创作 | ⬜ 待创建 |
| C02 | 碳中和住宅标准 | LEED案例改编 | ⬜ 待创建 |
| C03 | 适老化社区空间 | 日本案例研究 | ⬜ 待创建 |
| C04 | 心理疗愈空间设计 | 医疗研究转译 | ⬜ 待创建 |
| C05 | AI辅助设计流程 | 行业趋势 | ⬜ 待创建 |
| C06 | 模块化预制住宅 | 工业化案例 | ⬜ 待创建 |
| C07 | 共享办公3.0 | WeWork后时代 | ⬜ 待创建 |
| C08 | 零接触酒店设计 | 后疫情趋势 | ⬜ 待创建 |
| C09 | 宠物友好住宅系统 | 新兴市场 | ⬜ 待创建 |
| C10 | 15分钟生活圈社区 | 城市规划转译 | ⬜ 待创建 |

**更新频率**: 每季度人工添加2-3个

---

## 🔄 融合机制

### 匹配流程

```python
def match_layer2_examples(project_features, user_id, top_k=3):
    """
    从三个数据源融合匹配
    """
    # 1. 确定用户熟悉度，动态权重
    user_profile = get_user_profile(user_id)
    weights = calculate_dynamic_weights(user_profile.usage_count)

    # 2. 从三个池分别匹配
    external_matches = match_from_external_pool(
        project_features,
        top_k=int(top_k * weights['external'] * 3)
    )

    user_matches = match_from_user_private_pool(
        project_features,
        user_id,
        top_k=int(top_k * weights['user'] * 3)
    )

    curated_matches = match_from_curated_pool(
        project_features,
        top_k=int(top_k * weights['curated'] * 3)
    )

    # 3. 加权融合
    all_candidates = []
    for match in external_matches:
        match['final_score'] = match['score'] * weights['external']
        match['source'] = 'external'
        all_candidates.append(match)

    for match in user_matches:
        match['final_score'] = match['score'] * weights['user']
        match['source'] = 'user_private'
        all_candidates.append(match)

    for match in curated_matches:
        match['final_score'] = match['score'] * weights['curated']
        match['source'] = 'curated'
        all_candidates.append(match)

    # 4. 排序并去重
    all_candidates.sort(key=lambda x: x['final_score'], reverse=True)
    selected = diversity_dedup(all_candidates, top_k=top_k)

    # 5. 标记来源（用户可见）
    for example in selected:
        if example['source'] == 'external':
            example['badge'] = '🔥 热门案例'
        elif example['source'] == 'user_private':
            example['badge'] = '💡 您的历史项目'
        else:
            example['badge'] = '⭐ 精选案例'

    return selected
```

### 去重策略

**跨源去重**:
- 同一项目在多个数据源中出现，仅保留得分最高的一份
- 特征向量相似度>0.9视为重复

**多样性保障**:
- 前3个示例的space_type必须不同
- 避免同一source连续出现2次

---

## 🛠️ 技术实现

### 文件结构

```
intelligent_project_analyzer/
├── services/
│   ├── few_shot_selector_v2.py          # 12维匹配核心
│   └── multi_source_layer2_manager.py   # 🆕 多源管理器
├── crawlers/                            # 🆕 爬虫模块
│   ├── __init__.py
│   ├── archdaily_crawler.py
│   ├── gooood_crawler.py
│   └── base_crawler.py                  # 爬虫基类
├── data/
│   ├── external_layer2_cache.json       # 🆕 外部数据缓存
│   ├── user_private_layer2/             # 🆕 用户私有池
│   │   ├── {user_id_1}/
│   │   │   ├── project_001.yaml
│   │   │   └── project_002.yaml
│   │   └── {user_id_2}/
│   └── curated_layer2/                  # 🆕 策展池
│       ├── meta_verse_01.yaml
│       ├── carbon_neutral_01.yaml
│       └── ...
└── scripts/
    ├── crawl_external_layer2.py         # 🆕 爬虫定时任务
    └── extract_user_project.py          # 🆕 用户项目提取
```

### 核心类设计

```python
class MultiSourceLayer2Manager:
    """
    多源Layer 2管理器
    """
    def __init__(self):
        self.external_pool = ExternalProjectPool()
        self.user_pool = UserPrivatePool()
        self.curated_pool = CuratedExamplePool()

    def match_examples(self, project_features, user_id, top_k=3):
        """融合匹配"""
        pass

    def refresh_external_pool(self):
        """刷新外部数据（每月1日）"""
        pass

    def extract_user_project(self, project_id, user_id):
        """提取用户项目"""
        pass

    def add_curated_example(self, example_data):
        """添加人工策展示例"""
        pass
```

---

## 📅 实施路线图

### Phase 3.2.1: 人工策展池（1周）
**目标**: 快速构建兜底方案

- [ ] 创建10个精选示例YAML
- [ ] 实现CuratedExamplePool类
- [ ] 集成到FewShotSelectorV2

**交付物**:
- `curated_layer2/` 10个示例文件
- `curated_example_pool.py` 策展池管理器

### Phase 3.2.2: 外部爬虫（2周）
**目标**: 实现自动化热点捕捉

- [ ] 开发Archdaily爬虫
- [ ] 开发Gooood爬虫
- [ ] LLM特征提取接口
- [ ] 差异度计算与筛选
- [ ] 定时任务（每月1日）

**交付物**:
- `crawlers/` 爬虫模块
- `crawl_external_layer2.py` 定时任务脚本
- `external_layer2_cache.json` 数据缓存

### Phase 3.2.3: 用户私有池（2周）
**目标**: 实现个性化学习

- [ ] 项目质量评估算法
- [ ] 脱敏处理逻辑
- [ ] 用户授权机制
- [ ] 私有池管理界面

**交付物**:
- `user_private_pool.py` 私有池管理器
- `extract_user_project.py` 提取脚本
- 用户授权API

### Phase 3.2.4: 多源融合（1周）
**目标**: 统一接口，动态权重

- [ ] MultiSourceLayer2Manager类
- [ ] 动态权重算法
- [ ] 跨源去重逻辑
- [ ] 来源标记UI

**交付物**:
- `multi_source_layer2_manager.py` 融合管理器
- 更新FewShotSelectorV2集成

---

## 🎯 成功标准

### 定量指标

| 指标 | 目标值 |
|------|--------|
| **外部池示例数** | 20个（每月更新） |
| **策展池示例数** | 10个（每季度+2） |
| **用户私有池增长** | 活跃用户每月+1个 |
| **三源覆盖率** | 25-30% |
| **匹配精度提升** | 用户修改率 <25% |

### 定性指标

✅ **时效性**: 外部池每月更新，捕捉最新趋势
✅ **个性化**: 资深用户40%推荐来自私有池
✅ **质量保障**: 策展池兜底，爬虫失效时仍可用
✅ **用户信任**: 用户可查看示例来源，选择信任的池

---

## ⚠️ 风险与应对

### 风险1：爬虫被封禁
**应对**:
- 降低爬取频率（每月1次）
- 使用代理池轮换
- 策展池作为兜底

### 风险2：外部数据质量低
**应对**:
- LLM质量评分过滤（<4分丢弃）
- 人工抽查前10%
- 用户可标记"不适用"，自动移除

### 风险3：用户隐私泄露
**应对**:
- 默认关闭自动提取
- 强制脱敏处理
- 用户随时删除
- 私有池仅本人可见（数据库行级权限）

### 风险4：三源权重失衡
**应对**:
- A/B测试验证权重配置
- 用户反馈调节（"更多热门案例"/"更多我的项目"）
- 监控三源使用率，动态平衡

---

## 🚀 立即开始

建议从**Phase 3.2.1 人工策展池**开始：
1. 最容易实施（纯手动）
2. 快速验证多源架构
3. 为爬虫和私有池打样

**第一步**: 创建首批5个策展示例
- C01: 元宇宙展厅设计方法论
- C02: 碳中和住宅标准
- C03: 适老化社区空间
- C04: 心理疗愈空间设计
- C10: 15分钟生活圈社区

需要我立即创建这5个示例YAML吗？
