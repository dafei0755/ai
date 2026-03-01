-- 本体论学习系统数据库Schema
-- 版本: v3.0
-- 创建日期: 2026-02-10
-- 数据库: SQLite/PostgreSQL兼容

-- ============================================================
-- 维度定义表 (Dimensions)
-- ============================================================
-- 存储所有动态学习的维度定义及其元数据

CREATE TABLE IF NOT EXISTS dimensions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,  -- spiritual_world, business_positioning等
    project_type TEXT NOT NULL,  -- personal_residential, commercial_enterprise等
    description TEXT,
    ask_yourself TEXT,
    examples TEXT,

    -- 元数据
    version INTEGER DEFAULT 1,
    status TEXT DEFAULT 'active',  -- active, deprecated, testing
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT DEFAULT 'system',  -- human, ai_generated, ai_optimized

    -- 质量指标
    usage_count INTEGER DEFAULT 0,
    effectiveness_score REAL DEFAULT 0.0,
    expert_rating REAL DEFAULT 0.0,

    -- 扩展字段
    metadata TEXT,  -- JSON格式存储额外信息
    source TEXT,  -- 来源：manual, learned_from_session_xxx, optimized_by_ai

    -- 约束
    UNIQUE(name, project_type, category)
);

-- 索引优化
CREATE INDEX IF NOT EXISTS idx_dimensions_project_type ON dimensions(project_type);
CREATE INDEX IF NOT EXISTS idx_dimensions_category ON dimensions(category);
CREATE INDEX IF NOT EXISTS idx_dimensions_status ON dimensions(status);
CREATE INDEX IF NOT EXISTS idx_dimensions_usage ON dimensions(usage_count DESC);


-- ============================================================
-- 维度关系表 (Dimension Relations)
-- ============================================================
-- 存储维度之间的关联关系

CREATE TABLE IF NOT EXISTS dimension_relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_dimension_id INTEGER NOT NULL,
    target_dimension_id INTEGER NOT NULL,
    relation_type TEXT NOT NULL,  -- depends_on, conflicts_with, enhances, prerequisite
    strength REAL DEFAULT 0.5,  -- 关系强度 0.0-1.0
    evidence_count INTEGER DEFAULT 1,  -- 证据数量
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 外键约束
    FOREIGN KEY (source_dimension_id) REFERENCES dimensions(id) ON DELETE CASCADE,
    FOREIGN KEY (target_dimension_id) REFERENCES dimensions(id) ON DELETE CASCADE,

    -- 唯一约束
    UNIQUE(source_dimension_id, target_dimension_id, relation_type)
);

-- 索引优化
CREATE INDEX IF NOT EXISTS idx_relations_source ON dimension_relations(source_dimension_id);
CREATE INDEX IF NOT EXISTS idx_relations_target ON dimension_relations(target_dimension_id);
CREATE INDEX IF NOT EXISTS idx_relations_type ON dimension_relations(relation_type);


-- ============================================================
-- 项目类型定义表 (Project Types)
-- ============================================================
-- 动态扩展的项目类型定义

CREATE TABLE IF NOT EXISTS project_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    display_name TEXT,
    description TEXT,
    parent_type TEXT,  -- 支持类型继承
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT  -- JSON格式
);

-- 初始化现有项目类型
INSERT OR IGNORE INTO project_types (name, display_name, description) VALUES
    ('personal_residential', '个人住宅', '个人或家庭居住空间'),
    ('commercial_enterprise', '商业企业', '商业零售、餐饮等空间'),
    ('cultural_educational', '文化教育', '博物馆、展馆、教育机构'),
    ('healthcare_wellness', '医疗康养', '医疗、康复、养老空间'),
    ('office_coworking', '办公空间', '办公室、联合办公'),
    ('hospitality_tourism', '酒店文旅', '酒店、民宿、旅游设施'),
    ('sports_entertainment_arts', '体育娱乐', '体育场馆、剧院、艺术空间'),
    ('hybrid_residential_commercial', '混合项目', '住商混合、综合体');


-- ============================================================
-- 学习会话表 (Learning Sessions)
-- ============================================================
-- 记录每次项目分析的学习数据

CREATE TABLE IF NOT EXISTS learning_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT UNIQUE NOT NULL,
    project_type TEXT NOT NULL,
    expert_roles TEXT,  -- JSON数组
    extracted_dimensions TEXT,  -- JSON对象
    quality_metrics TEXT,  -- JSON对象
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 索引
    FOREIGN KEY (project_type) REFERENCES project_types(name)
);

CREATE INDEX IF NOT EXISTS idx_sessions_project_type ON learning_sessions(project_type);
CREATE INDEX IF NOT EXISTS idx_sessions_timestamp ON learning_sessions(timestamp DESC);


-- ============================================================
-- 维度候选表 (Dimension Candidates)
-- ============================================================
-- 待审核的候选维度

CREATE TABLE IF NOT EXISTS dimension_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dimension_data TEXT NOT NULL,  -- JSON格式完整维度数据
    confidence_score REAL NOT NULL,
    source_session_id TEXT,
    review_status TEXT DEFAULT 'pending',  -- pending, approved, rejected, modified
    reviewer_id TEXT,
    review_feedback TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP,

    -- 外键
    FOREIGN KEY (source_session_id) REFERENCES learning_sessions(session_id)
);

CREATE INDEX IF NOT EXISTS idx_candidates_status ON dimension_candidates(review_status);
CREATE INDEX IF NOT EXISTS idx_candidates_confidence ON dimension_candidates(confidence_score DESC);


-- ============================================================
-- 维度使用记录表 (Dimension Usage Log)
-- ============================================================
-- 追踪维度的实际使用情况

CREATE TABLE IF NOT EXISTS dimension_usage_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dimension_id INTEGER NOT NULL,
    session_id TEXT NOT NULL,
    expert_role TEXT,
    project_type TEXT,
    usage_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (dimension_id) REFERENCES dimensions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_usage_dimension ON dimension_usage_log(dimension_id);
CREATE INDEX IF NOT EXISTS idx_usage_session ON dimension_usage_log(session_id);
CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON dimension_usage_log(usage_timestamp DESC);


-- ============================================================
-- 优化建议表 (Optimization Suggestions)
-- ============================================================
-- 存储AI生成的优化建议

CREATE TABLE IF NOT EXISTS optimization_suggestions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dimension_id INTEGER NOT NULL,
    suggestion_type TEXT NOT NULL,  -- improve_description, add_examples, clarify_question
    suggestion_content TEXT NOT NULL,
    confidence REAL DEFAULT 0.5,
    status TEXT DEFAULT 'pending',  -- pending, accepted, rejected
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP,

    FOREIGN KEY (dimension_id) REFERENCES dimensions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_suggestions_dimension ON optimization_suggestions(dimension_id);
CREATE INDEX IF NOT EXISTS idx_suggestions_status ON optimization_suggestions(status);


-- ============================================================
-- 视图：维度质量仪表板 (Dimension Quality Dashboard View)
-- ============================================================

CREATE VIEW IF NOT EXISTS v_dimension_quality AS
SELECT
    d.id,
    d.name,
    d.category,
    d.project_type,
    d.status,
    d.usage_count,
    d.effectiveness_score,
    d.expert_rating,
    COUNT(DISTINCT ul.session_id) as unique_sessions,
    MAX(ul.usage_timestamp) as last_used,
    (d.effectiveness_score * 0.4 +
     MIN(d.usage_count / 100.0, 1.0) * 0.3 +
     d.expert_rating / 5.0 * 0.3) as composite_score
FROM dimensions d
LEFT JOIN dimension_usage_log ul ON d.id = ul.dimension_id
GROUP BY d.id
ORDER BY composite_score DESC;


-- ============================================================
-- 视图：待审核候选维度 (Pending Candidates View)
-- ============================================================

CREATE VIEW IF NOT EXISTS v_pending_candidates AS
SELECT
    dc.id,
    dc.dimension_data,
    dc.confidence_score,
    dc.source_session_id,
    dc.created_at,
    ls.project_type,
    ls.expert_roles
FROM dimension_candidates dc
LEFT JOIN learning_sessions ls ON dc.source_session_id = ls.session_id
WHERE dc.review_status = 'pending'
ORDER BY dc.confidence_score DESC, dc.created_at ASC;


-- ============================================================
-- 项目类型候选表 (Project Type Candidates)
-- 管理员审核后写入 data/project_type_extensions.json
-- ============================================================

CREATE TABLE IF NOT EXISTS project_type_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- 候选类型信息（管理员可在审核时编辑）
    type_id_suggestion TEXT NOT NULL,        -- 建议的英文ID，如 "auto_showroom"
    name_zh            TEXT NOT NULL,        -- 中文名称，如 "汽车展厅"
    name_en            TEXT DEFAULT '',      -- 英文检索词
    description        TEXT DEFAULT '',      -- 类型说明

    -- 来源信息
    source             TEXT NOT NULL,        -- user_input / crawler / manual
    source_session_id  TEXT,                 -- 来源会话ID
    sample_inputs      TEXT DEFAULT '[]',    -- JSON：触发此候选的原始输入样例（最多5条）
    occurrence_count   INTEGER DEFAULT 1,    -- 累计出现次数

    -- 关键词建议（管理员可在审核时修改）
    suggested_keywords           TEXT DEFAULT '[]',  -- JSON数组
    suggested_secondary_keywords TEXT DEFAULT '[]',  -- JSON数组

    -- 置信度与质量
    confidence_score   REAL DEFAULT 0.5,

    -- 审核字段
    review_status  TEXT DEFAULT 'pending',   -- pending/approved/rejected/merged
    reviewer_id    TEXT,
    reviewer_note  TEXT,
    merge_into     TEXT,                     -- 若合并入已有类型，存该类型ID

    -- 审批后的最终参数（管理员在审核页面填写）
    approved_type_id             TEXT,       -- 最终确认的英文ID（可能与 suggestion 不同）
    approved_keywords            TEXT,       -- JSON：最终关键词
    approved_secondary_keywords  TEXT,       -- JSON：最终次关键词
    approved_priority            INTEGER DEFAULT 6,
    approved_min_secondary_hits  INTEGER DEFAULT 0,

    -- 时间戳
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_at  TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ptc_status      ON project_type_candidates(review_status);
CREATE INDEX IF NOT EXISTS idx_ptc_confidence  ON project_type_candidates(confidence_score DESC);
CREATE INDEX IF NOT EXISTS idx_ptc_source      ON project_type_candidates(source);
CREATE INDEX IF NOT EXISTS idx_ptc_suggestion  ON project_type_candidates(type_id_suggestion);
CREATE INDEX IF NOT EXISTS idx_ptc_occurrence  ON project_type_candidates(occurrence_count DESC);


-- ============================================================
-- 初始化完成
-- ============================================================

-- 插入系统配置
CREATE TABLE IF NOT EXISTS system_config (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT OR REPLACE INTO system_config (key, value) VALUES
    ('schema_version', '3.0'),
    ('last_migration', datetime('now')),
    ('learning_enabled', 'true'),
    ('min_confidence_threshold', '0.7'),
    ('require_human_review', 'true');
