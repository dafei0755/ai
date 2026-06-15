/**
 * 地理信息系统（GIS）核心数据契约
 *
 * 设计原则：
 *   1. GeoAnchor 是系统唯一的地理真相源，所有地图 provider 都是输入手段
 *   2. 坐标系使用 GCJ-02（国内火星坐标），对应高德/腾讯标准
 *   3. 所有外部 POI/竞品/客源数据最终归一化为本文件定义的结构
 *
 * 版本：v2.0 · 2026-05-07
 * G1-G5 五层引擎架构，从锚点到商业命题全链路覆盖
 */

// ─────────────────────────────────────────────────────────────────────────────
// G1 核心坐标与锚点
// ─────────────────────────────────────────────────────────────────────────────

export interface GeoCoordinates {
  /** 纬度（GCJ-02） */
  lat: number;
  /** 经度（GCJ-02） */
  lng: number;
  /** 海拔高度（米），高德高程 API 异步填充 */
  elevation?: number;
}

export interface GeoAdministrative {
  country: string;
  province: string;
  city: string;
  district: string;
  /** 镇/乡级（山地/乡村项目的关键粒度） */
  township?: string;
  /** 完整格式化地址字符串 */
  formatted_address: string;
  /** 荒野/未命名地块由用户手动覆写 */
  manual_override?: string;
}

export interface GeoFeatures {
  /** 气候带（规则引擎自动打标） */
  climate_zone?: string;
  /** 地形类型 */
  terrain_type?: 'mountain' | 'plain' | 'coastal' | 'basin' | 'plateau' | 'urban';
  /** 地质风险等级 */
  geologic_risk?: 'Low' | 'Medium' | 'High';
  /** 年均降水量（mm） */
  annual_rainfall_mm?: number;
  /** 年均结冰天数 */
  frost_days_per_year?: number;
}

export interface GeoCommercialContext {
  /** 商圈类型 */
  cluster_type?: 'scenic_dependent' | 'urban_core' | 'suburb' | 'remote' | 'industrial';
  /** 距最近景区/商圈核心节点距离（km） */
  distance_to_core_node_km?: number;
  /** 综合交通便利度评分（0–100） */
  accessibility_score?: number;
  /** 物流约束等级（山地/偏远项目的材料运输上限） */
  logistics_constraint?: 'None' | 'Road_Limit' | 'Severe';
}

// ─────────────────────────────────────────────────────────────────────────────
// G2 位置时间轴（新增：区域生命周期 + 趋势）
// ─────────────────────────────────────────────────────────────────────────────

export interface GeoTimeAxis {
  /**
   * 区域生命周期阶段：
   *  emerging = 萌芽期（新兴目的地，认知度低，机遇大）
   *  growth   = 成长期（快速增长，竞争开始涌入）
   *  mature   = 成熟期（市场稳定，差异化是关键）
   *  declining = 衰退期（流量下滑，需要差异化或退出）
   */
  lifecycle_stage?: 'emerging' | 'growth' | 'mature' | 'declining';
  /** 近1年社交平台声量趋势 */
  social_heat_trend?: 'rising' | 'stable' | 'falling';
  /** 近1年区域资本活跃度（土地交易/新开盘等） */
  capital_activity?: 'active' | 'quiet' | 'exiting';
  /** AI 预测2年后生命周期阶段 */
  predicted_stage_2y?: string;
  /** 预测依据摘要 */
  prediction_basis?: string;
}

export interface GeoAnchorMeta {
  /** ISO 8601 时间戳 */
  set_at: string;
  /** 坐标来源 */
  source: 'map_pick' | 'manual_input' | 'import';
  /** 确认度 */
  confidence: 'confirmed' | 'estimated';
  /** 高德 POI ID（如有精确匹配） */
  amap_poi_id?: string;
}

/**
 * GeoAnchor — 项目地理锚点（G1+G2 层核心字段）
 */
export interface GeoAnchor {
  coordinates: GeoCoordinates;
  administrative: GeoAdministrative;
  geo_features: GeoFeatures;
  commercial_context: GeoCommercialContext;
  /** G2 新增：位置时间轴 */
  time_axis?: GeoTimeAxis;
  meta: GeoAnchorMeta;
}

// ─────────────────────────────────────────────────────────────────────────────
// G3 GeoIntelligence — 地理情报层（竞品/评价/评分）
// ─────────────────────────────────────────────────────────────────────────────

/** 竞品替代关系类型 */
export type SubstitutionRelation =
  | 'direct'          // 同业态直接竞品
  | 'cross_category'  // 跨业态替代（如：温泉酒店 vs 山地民宿）
  | 'no_spend';       // 不消费替代（如：在城市待着）

export interface CompetitorPOI {
  id: string;
  /** 所属项目 ID */
  project_id: string;
  name: string;
  /** 竞品业态分类 */
  category: string;
  lat: number;
  lng: number;
  /** 距项目直线距离（km） */
  distance_to_project_km?: number;
  /** 驾车时间（分钟） */
  drive_time_to_project_min?: number;
  /** 价格带（元/晚） */
  price_band?: { min: number; max: number };
  room_count?: number;
  /** OTA 评分（0-5） */
  rating?: number;
  /** 竞品替代关系（用于 SubstitutionMap 模型） */
  substitution_relation?: SubstitutionRelation;
  /** 数据来源 */
  source: 'amap_poi' | 'manual' | 'crawler' | 'third_party' | 'history_project';
  /** 数据可信度（0-1） */
  confidence: number;
}

/** 用户评价信号（从多源评价 NLP 抽取） */
export interface ReviewSignal {
  /** 信号类型 */
  type: 'praise' | 'complaint' | 'experience_gap';
  /** 原始关键词 */
  keyword: string;
  /** 出现频率（0-1） */
  frequency: number;
  /** 情感极性 */
  sentiment: 'positive' | 'negative' | 'neutral';
  /** 数据来源 */
  source: string;
  /** 是否是可被设计缓解的痛点（体验套利机会） */
  design_solvable?: boolean;
}

/** 地理摩擦项 */
export interface GeoFrictionItem {
  type: '交通' | '气候' | '季节' | '维护' | '物流' | '认知' | '传播' | '夜间' | '停车' | '价格';
  severity: 'Low' | 'Medium' | 'High';
  /** 可通过设计缓解 */
  design_solvable: boolean;
  /** 解决路径描述 */
  resolution_hint?: string;
}

/**
 * G3 地理情报数据集
 * 坐标锁定后自动聚合，支撑 5 大评分和 G4 命题生成
 */
export interface GeoIntelligence {
  project_id: string;
  /** 竞品及替代关系图 */
  competitors: CompetitorPOI[];
  /** 客源城市分布 */
  customer_origins: CustomerOrigin[];
  /** 多源评价信号（NLP 抽取后归一化） */
  review_signals: ReviewSignal[];
  /** 地理摩擦清单 */
  geo_friction: GeoFrictionItem[];
  /** G3 核心：5 大商业评分 */
  scores: GeoScores;
  last_updated: string;
}

/** G3 五大商业评分（全部 0-100） */
export interface GeoScores {
  /** 地点商业成立度：地点是否适合做当前业态 */
  place_viability: number;
  /** 地理摩擦指数：越低越好 */
  geo_friction_index: number;
  /** 体验套利指数：竞品差评可被设计转化的机会量 */
  experience_gap_index: number;
  /** 设计杠杆指数：设计能对商业结果产生多大影响 */
  design_leverage_score: number;
  /** 地理溢价指数：地点天然溢价能力 + 设计兑现潜力 */
  geo_premium_score: number;
}

// ─────────────────────────────────────────────────────────────────────────────
// G4 GeoThesis — 地点商业命题
// ─────────────────────────────────────────────────────────────────────────────

/**
 * GeoThesis — 地点商业命题（Location Investment Thesis）
 *
 * 每次坐标锁定后，由 G3 情报驱动 LLM 生成。
 * 回答：这个项目在这个地点成立的商业理由是什么？
 */
export interface GeoThesis {
  project_id: string;
  /** 地点类型标签 */
  site_type: string;
  /** 地点核心资产 */
  core_assets: string[];
  /** 需求捕获描述 */
  demand_catchment: {
    primary_persona: string;
    travel_motivation: string;
    willingness_to_pay: string;
    catchment_radius_desc: string;
  };
  /** 真实替代竞争关系 */
  substitution_summary: {
    direct_competitors: string[];
    cross_category_alternatives: string[];
    no_spend_alternatives: string[];
  };
  /** 用户评价信号摘要 */
  review_signals_summary: {
    top_praise: string[];
    top_complaints: string[];
    experience_gap_opportunities: string[];
  };
  /** 设计杠杆节点（最值得投入的空间节点） */
  design_leverage_nodes: string[];
  /** 商业风险 */
  commercial_risks: string[];
  /** G5 设计指令（Command，非建议） */
  design_commands: {
    must_do: string[];
    must_not: string[];
    defer: string[];
  };
  /** 验证指标（项目交付后用于回写因果数据的指标） */
  validation_metrics: string[];
  /** 关联的 G3 评分快照 */
  scores: GeoScores;
  generated_at: string;
  /** AI 置信度（0-1） */
  confidence: number;
}

// ─────────────────────────────────────────────────────────────────────────────
// 保留原有结构（向后兼容）
// ─────────────────────────────────────────────────────────────────────────────

export interface CustomerOrigin {
  city: string;
  province: string;
  lat: number;
  lng: number;
  /** 该城市客源占比（0-1） */
  share: number;
  /** 年访问人次 */
  annual_visits?: number;
}

export interface MarketGeoDataset {
  project_id: string;
  competitors: CompetitorPOI[];
  customer_origins: CustomerOrigin[];
  /** OTA 汇总统计 */
  poi_stats?: {
    total_count: number;
    avg_rating: number;
    price_distribution: { low: number; mid: number; high: number };
  };
  last_updated: string;
}

/** 位置评分洞察（旧版，逐步迁移至 GeoScores） */
export interface LocationInsight {
  project_id: string;
  scores: {
    accessibility: number;
    market_gap: number;
    competition_pressure: number;
    customer_fit: number;
    seasonality_risk: number;
    operation_potential: number;
  };
  conclusions: string[];
  evidence_refs: string[];
  generated_at: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// GeoProvider 接口（Adapter 模式）
// ─────────────────────────────────────────────────────────────────────────────

export interface GeoSearchResult {
  name: string;
  address: string;
  lat: number;
  lng: number;
  poi_id?: string;
}

export interface GeoReverseResult {
  administrative: GeoAdministrative;
  poi_name?: string;
}

/**
 * GeoProvider 接口 — 所有地图服务商必须实现此契约
 * 业务代码只依赖此接口，不直接耦合高德/腾讯/Mapbox
 */
export interface GeoProvider {
  readonly name: string;
  searchPlace(query: string, lat?: number, lng?: number): Promise<GeoSearchResult[]>;
  reverseGeocode(lat: number, lng: number): Promise<GeoReverseResult>;
  getElevation(lat: number, lng: number): Promise<number>;
}


// ─────────────────────────────────────────────────────────────────────────────
// 核心坐标与锚点
// ─────────────────────────────────────────────────────────────────────────────

export interface GeoCoordinates {
  /** 纬度（GCJ-02） */
  lat: number;
  /** 经度（GCJ-02） */
  lng: number;
  /** 海拔高度（米），高德高程 API 异步填充 */
  elevation?: number;
}

export interface GeoAdministrative {
  country: string;
  province: string;
  city: string;
  district: string;
  /** 镇/乡级（山地/乡村项目的关键粒度） */
  township?: string;
  /** 完整格式化地址字符串 */
  formatted_address: string;
  /** 荒野/未命名地块由用户手动覆写 */
  manual_override?: string;
}

export interface GeoFeatures {
  /** 气候带（规则引擎自动打标） */
  climate_zone?: string;
  /** 地形类型 */
  terrain_type?: 'mountain' | 'plain' | 'coastal' | 'basin' | 'plateau' | 'urban';
  /** 地质风险等级 */
  geologic_risk?: 'Low' | 'Medium' | 'High';
  /** 年均降水量（mm） */
  annual_rainfall_mm?: number;
  /** 年均结冰天数 */
  frost_days_per_year?: number;
}

export interface GeoCommercialContext {
  /** 商圈类型 */
  cluster_type?: 'scenic_dependent' | 'urban_core' | 'suburb' | 'remote' | 'industrial';
  /** 距最近景区/商圈核心节点距离（km） */
  distance_to_core_node_km?: number;
  /** 综合交通便利度评分（0–100） */
  accessibility_score?: number;
  /** 物流约束等级（山地/偏远项目的材料运输上限） */
  logistics_constraint?: 'None' | 'Road_Limit' | 'Severe';
}

export interface GeoAnchorMeta {
  /** ISO 8601 时间戳 */
  set_at: string;
  /** 坐标来源 */
  source: 'map_pick' | 'manual_input' | 'import';
  /** 确认度 */
  confidence: 'confirmed' | 'estimated';
  /** 高德 POI ID（如有精确匹配） */
  amap_poi_id?: string;
}

/**
 * GeoAnchor — 项目地理锚点（L1 层核心字段）
 *
 * 设计语义：
 *   坐标是「空间认知飞轮」的触发器。锚点一旦确立，
 *   气候、竞品、历史项目召回、AI 洞察均以此为基准自动触发。
 */
export interface GeoAnchor {
  coordinates: GeoCoordinates;
  administrative: GeoAdministrative;
  geo_features: GeoFeatures;
  commercial_context: GeoCommercialContext;
  meta: GeoAnchorMeta;
}

// ─────────────────────────────────────────────────────────────────────────────
// 竞品 POI（归一化结构，支持多来源合并）
// ─────────────────────────────────────────────────────────────────────────────

export interface CompetitorPOI {
  id: string;
  /** 所属项目 ID */
  project_id: string;
  name: string;
  /** 竞品业态分类 */
  category: string;
  lat: number;
  lng: number;
  /** 距项目直线距离（km） */
  distance_to_project_km?: number;
  /** 驾车时间（分钟） */
  drive_time_to_project_min?: number;
  /** 价格带（元/晚） */
  price_band?: { min: number; max: number };
  room_count?: number;
  /** OTA 评分（0-5） */
  rating?: number;
  /** 数据来源 */
  source: 'amap_poi' | 'manual' | 'crawler' | 'third_party' | 'history_project';
  /** 数据可信度（0-1） */
  confidence: number;
}

// ─────────────────────────────────────────────────────────────────────────────
// 市场数据集
// ─────────────────────────────────────────────────────────────────────────────

export interface CustomerOrigin {
  city: string;
  province: string;
  lat: number;
  lng: number;
  /** 该城市客源占比（0-1） */
  share: number;
  /** 年访问人次 */
  annual_visits?: number;
}

export interface MarketGeoDataset {
  project_id: string;
  competitors: CompetitorPOI[];
  customer_origins: CustomerOrigin[];
  /** OTA 汇总统计 */
  poi_stats?: {
    total_count: number;
    avg_rating: number;
    price_distribution: { low: number; mid: number; high: number };
  };
  last_updated: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// 位置评分洞察
// ─────────────────────────────────────────────────────────────────────────────

export interface LocationInsight {
  project_id: string;
  scores: {
    /** 交通可达性（0-100） */
    accessibility: number;
    /** 市场空白度（0-100，越高越蓝海） */
    market_gap: number;
    /** 竞争压力（0-100，越高越红海） */
    competition_pressure: number;
    /** 客群匹配度（0-100） */
    customer_fit: number;
    /** 季节性风险（0-100，越高越不稳定） */
    seasonality_risk: number;
    /** 运营潜力（0-100） */
    operation_potential: number;
  };
  /** AI 生成的文字洞察列表 */
  conclusions: string[];
  /** 依据的证据/数据引用 */
  evidence_refs: string[];
  generated_at: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// GeoProvider 接口（Adapter 模式）
// ─────────────────────────────────────────────────────────────────────────────

export interface GeoSearchResult {
  name: string;
  address: string;
  lat: number;
  lng: number;
  poi_id?: string;
}

export interface GeoReverseResult {
  administrative: GeoAdministrative;
  poi_name?: string;
}

/**
 * GeoProvider 接口 — 所有地图服务商必须实现此契约
 * 业务代码只依赖此接口，不直接耦合高德/腾讯/Mapbox
 */
export interface GeoProvider {
  readonly name: string;
  /** 地名/关键词搜索 → 候选坐标列表 */
  searchPlace(query: string, lat?: number, lng?: number): Promise<GeoSearchResult[]>;
  /** 坐标反解析 → 行政区划文字 */
  reverseGeocode(lat: number, lng: number): Promise<GeoReverseResult>;
  /** 获取坐标点海拔（米） */
  getElevation(lat: number, lng: number): Promise<number>;
}
