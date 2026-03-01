# 英文建筑网站的中文应用最佳实践

## 📋 方案对比

### 方案1：实时翻译（不推荐）
```
优点：无需存储翻译
缺点：
  - 每次访问都要API调用，成本高
  - 响应慢（3-5秒）
  - 翻译质量不稳定
  - 无法优化专业术语
```

### 方案2：预翻译+缓存（推荐⭐⭐⭐⭐⭐）
```
优点：
  - 一次翻译，永久使用
  - 响应快（<100ms）
  - 可人工审核和优化
  - 专业术语统一
缺点：
  - 需要存储空间
  - 初次爬取慢一些
```

### 方案3：双语混合（最佳实践⭐⭐⭐⭐⭐）
```
优点：
  - 保留原文，增加翻译
  - 用户可切换中英文
  - SEO友好（双语索引）
  - 适合专业用户
推荐度：★★★★★
```

---

## 🎯 推荐架构：双语存储 + 智能翻译

### 数据库设计

```sql
-- 方案A：单表双语字段
CREATE TABLE external_projects (
    id INTEGER PRIMARY KEY,

    -- 原始英文数据
    title_en TEXT NOT NULL,
    description_en TEXT,

    -- 中文翻译
    title_zh TEXT,
    description_zh TEXT,

    -- 翻译元数据
    translated_at TIMESTAMP,
    translation_engine TEXT,  -- 'gpt4', 'claude', 'deepseek'
    translation_quality FLOAT,
    is_human_reviewed BOOLEAN DEFAULT FALSE,

    -- 公共字段
    url TEXT,
    year INTEGER,
    images JSON,
    architects JSON  -- 人名不翻译
);

-- 方案B：关联表（更灵活）
CREATE TABLE external_projects (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,  -- 英文
    description TEXT,     -- 英文
    -- ... 其他英文字段
);

CREATE TABLE project_translations (
    id INTEGER PRIMARY KEY,
    project_id INTEGER REFERENCES external_projects(id),
    language TEXT NOT NULL,  -- 'zh-CN', 'zh-TW', 'ja'
    title TEXT,
    description TEXT,
    translated_at TIMESTAMP,
    translator TEXT,  -- 'gpt4', 'human'
    quality_score FLOAT,
    UNIQUE(project_id, language)
);
```

### 翻译工作流

```python
# intelligent_project_analyzer/external_data_system/translation/translator.py

class ProjectTranslator:
    """项目内容翻译器"""

    def __init__(self, engine='deepseek'):
        """
        支持的翻译引擎：
        - deepseek: 性价比最高，建筑专业性好
        - gpt4: 质量最高，成本高
        - claude: 平衡选择
        """
        self.engine = engine

    def translate_project(self, project: ProjectData) -> Dict[str, str]:
        """
        翻译项目内容

        策略：
        1. 标题和描述翻译
        2. 专业术语保留英文（括号标注）
        3. 人名、地名不翻译
        4. 分段翻译长文本（避免token限制）
        """

        # 构建专业术语词典
        terminology = {
            'Architect': '建筑师',
            'Facade': '立面',
            'Atrium': '中庭',
            'Cantilever': '悬臂',
            # ... 200+ 专业术语
        }

        # 翻译提示词
        prompt = f"""
        你是专业的建筑设计翻译专家。请将以下英文内容翻译成中文：

        翻译要求：
        1. 保持建筑专业性和准确性
        2. 人名保留英文：如 "Sou Fujimoto" 不翻译
        3. 地名保留英文或使用官方中文名：如 "Abu Dhabi" → "阿布扎比"
        4. 专业术语首次出现时用"中文（英文）"格式：如"立面（Facade）"
        5. 保持原文的段落结构
        6. 数字、单位保持原样

        原文标题：{project.title}

        原文描述：
        {project.description}

        请返回JSON格式：
        {{
            "title_zh": "翻译后的标题",
            "description_zh": "翻译后的描述"
        }}
        """

        # 调用LLM翻译
        translation = self.llm_client.complete(prompt)

        return translation

    def batch_translate(self, projects: List[ProjectData],
                       batch_size: int = 10) -> List[Dict]:
        """批量翻译（提高效率）"""

        results = []
        for i in range(0, len(projects), batch_size):
            batch = projects[i:i+batch_size]

            # 并发翻译
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [
                    executor.submit(self.translate_project, p)
                    for p in batch
                ]

                for future in futures:
                    results.append(future.result())

        return results
```

---

## 🔄 爬取时自动翻译

```python
# scripts/crawl_from_index.py 修改版

class IndexBasedCrawler:

    def __init__(self, auto_translate=True, translation_engine='deepseek'):
        self.translator = ProjectTranslator(engine=translation_engine)
        self.auto_translate = auto_translate

    def crawl_from_index(self, source, limit=None):
        """爬取并翻译"""

        for project_url in uncrawled_projects:
            # 1. 爬取英文内容
            project_data = spider.fetch_project_detail(project_url)

            # 2. 自动翻译
            if self.auto_translate:
                translation = self.translator.translate_project(project_data)

                # 质量检查
                quality = self._check_translation_quality(
                    project_data.description,
                    translation['description_zh']
                )

                if quality < 0.6:
                    logger.warning(f"翻译质量较低: {quality}")

            # 3. 保存双语数据
            db_project = ExternalProject(
                # 英文原文
                title_en=project_data.title,
                description_en=project_data.description,

                # 中文翻译
                title_zh=translation['title_zh'],
                description_zh=translation['description_zh'],

                # 元数据
                translated_at=datetime.now(),
                translation_engine=self.translator.engine,
                translation_quality=quality,

                # 其他字段
                url=project_url,
                year=project_data.year,
                # ...
            )

            session.add(db_project)
            session.commit()
```

---

## 🎨 前端展示策略

### 1. 默认显示策略

```typescript
// 用户首选语言检测
const userLanguage = navigator.language;  // 'zh-CN', 'en-US'

const displayLanguage = userLanguage.startsWith('zh') ? 'zh' : 'en';

// 显示对应语言
<h1>{project[`title_${displayLanguage}`]}</h1>
<div>{project[`description_${displayLanguage}`]}</div>
```

### 2. 语言切换按钮

```typescript
// 右上角切换按钮
<LanguageToggle>
  <button onClick={() => setLang('zh')}>中文</button>
  <button onClick={() => setLang('en')}>English</button>
</LanguageToggle>

// 保存用户偏好
localStorage.setItem('preferred_language', lang);
```

### 3. 混合显示（推荐）

```typescript
// 标题：中文为主，英文辅助
<h1>
  {project.title_zh}
  <span className="subtitle-en">{project.title_en}</span>
</h1>

// 描述：可展开原文
<div>
  <p>{project.description_zh}</p>
  <Collapse title="查看英文原文">
    <p className="text-gray">{project.description_en}</p>
  </Collapse>
</div>

// 建筑师：保持英文
<div>
  建筑师: <strong>{project.architects.join(', ')}</strong>
</div>
```

---

## 💰 成本估算

### Deepseek API (推荐)

```
单篇文章：
  - 输入: ~4000 tokens (英文原文)
  - 输出: ~4000 tokens (中文翻译)
  - 成本: ¥0.004 (0.4厘/千tokens)

1000篇文章：
  - 总成本: ¥4-6
  - 时间: 约30分钟

性价比: ★★★★★
```

### GPT-4o

```
单篇文章：
  - 成本: ~¥0.12

1000篇文章：
  - 总成本: ¥120
  - 时间: 约1小时

质量: ★★★★★
性价比: ★★★
```

### Claude 3.5 Sonnet

```
单篇文章：
  - 成本: ~¥0.08

1000篇文章：
  - 总成本: ¥80
  - 时间: 约45分钟

平衡选择: ★★★★
```

---

## 📊 翻译质量保障

### 1. 自动质量检测

```python
def check_translation_quality(original: str, translation: str) -> float:
    """
    质量检测指标：
    1. 长度比例 (0.8-1.5 正常)
    2. 关键词覆盖率
    3. 专业术语正确性
    4. 人名地名保留
    """

    # 长度检查
    len_ratio = len(translation) / len(original)
    if not (0.8 <= len_ratio <= 1.5):
        return 0.5

    # 关键词检查（建筑师、项目类型等）
    key_terms_preserved = check_key_terms(original, translation)

    # 专业术语检查
    terminology_correct = check_terminology(translation)

    score = (len_ratio * 0.3 +
             key_terms_preserved * 0.4 +
             terminology_correct * 0.3)

    return score
```

### 2. 人工审核工作流

```python
# 标记需要审核的翻译
if translation_quality < 0.7:
    mark_for_human_review(project_id)

# 审核界面
class TranslationReviewPage:
    """
    显示：
    - 英文原文
    - 机器翻译
    - 编辑器（修改翻译）

    操作：
    - 批准
    - 修改并批准
    - 重新翻译
    """
```

---

## 🔍 搜索优化

### 双语全文搜索

```python
# 使用PostgreSQL全文搜索
CREATE INDEX idx_project_search_zh ON external_projects
USING GIN(to_tsvector('chinese', title_zh || ' ' || description_zh));

CREATE INDEX idx_project_search_en ON external_projects
USING GIN(to_tsvector('english', title_en || ' ' || description_en));

# 搜索时同时查询中英文
SELECT * FROM external_projects
WHERE
    to_tsvector('chinese', title_zh || ' ' || description_zh) @@
    plainto_tsquery('chinese', '立面设计')
    OR
    to_tsvector('english', title_en || ' ' || description_en) @@
    plainto_tsquery('english', 'facade design');
```

### 语义搜索（向量化）

```python
# 双语向量存储
class BilingualEmbedding:

    def embed_project(self, project):
        """生成双语向量"""

        # 1. 中文向量
        zh_vector = self.embed_model.encode(
            f"{project.title_zh} {project.description_zh[:500]}"
        )

        # 2. 英文向量
        en_vector = self.embed_model.encode(
            f"{project.title_en} {project.description_en[:500]}"
        )

        # 3. 融合向量（可选）
        combined_vector = (zh_vector + en_vector) / 2

        return combined_vector

    def search(self, query: str, language='auto'):
        """智能语言检测并搜索"""

        # 检测查询语言
        if language == 'auto':
            language = detect_language(query)  # 'zh' or 'en'

        # 生成查询向量
        query_vector = self.embed_model.encode(query)

        # 向量搜索
        results = vector_db.similarity_search(
            query_vector,
            top_k=20
        )

        return results
```

---

## 🎯 实施建议

### 短期方案（1-2天）

```bash
# 1. 修改数据库Schema
python scripts/migrate_add_translation_fields.py

# 2. 测试翻译单篇文章
python scripts/test_translation.py --url "<文章URL>"

# 3. 小批量翻译（10篇）
python scripts/crawl_from_index.py \
    --source dezeen \
    --limit 10 \
    --auto-translate \
    --engine deepseek
```

### 中期方案（1周）

```bash
# 1. 批量翻译已爬取内容
python scripts/batch_translate.py \
    --source all \
    --batch-size 50 \
    --engine deepseek

# 2. 设置质量审核
python scripts/review_translations.py --quality-threshold 0.7

# 3. 优化专业术语词典
python scripts/build_terminology_dict.py
```

### 长期方案（持续优化）

1. **术语库建设**：收集200+建筑专业术语
2. **人工审核**：每周审核10-20篇低质量翻译
3. **用户反馈**：添加"翻译建议"功能
4. **多语言扩展**：支持日文、韩文（针对亚洲项目）

---

## 📈 性能优化

### 缓存策略

```python
# Redis缓存翻译结果
class TranslationCache:

    def get_translation(self, text_hash: str):
        """从缓存获取翻译"""
        return redis.get(f"translation:{text_hash}")

    def set_translation(self, text_hash: str, translation: str):
        """缓存翻译（永久）"""
        redis.set(f"translation:{text_hash}", translation)
```

### 异步翻译

```python
# Celery后台任务
@celery.task
def translate_project_async(project_id):
    """异步翻译项目"""

    project = get_project(project_id)
    translation = translator.translate_project(project)

    # 更新数据库
    update_project_translation(project_id, translation)

    # 通知前端（WebSocket）
    notify_translation_complete(project_id)
```

---

## ✅ 总结：最佳实践

| 维度 | 推荐方案 |
|------|---------|
| 存储策略 | 双语字段（title_zh + title_en） |
| 翻译引擎 | Deepseek（性价比）/ GPT-4（质量） |
| 翻译时机 | 爬取时自动翻译 + 缓存 |
| 前端展示 | 中文为主 + 英文辅助悬浮 |
| 搜索策略 | 双语全文搜索 + 向量语义搜索 |
| 质量保障 | 自动检测 + 人工审核 |
| 成本控制 | Deepseek: ¥4-6/千篇 |

**核心原则**：
1. ✅ 保留英文原文（权威性）
2. ✅ 提供中文翻译（可读性）
3. ✅ 用户可切换（灵活性）
4. ✅ 专业术语双语对照（专业性）
5. ✅ 人名地名不翻译（准确性）
