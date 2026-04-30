"""
核心任务拆解服务

v7.80.1: 将用户模糊输入拆解为结构化的可执行任务列表
v7.110.0: 智能化任务数量评估，根据输入复杂度动态调整（3-12个弹性范围）
用于 Step 1: 任务梳理
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from loguru import logger


class TaskComplexityAnalyzer:
    """
    任务复杂度分析器 - v7.110.0 / v7.503增强

    根据用户输入的信息密度和复杂程度，智能评估建议的任务数量。
    v7.503: 扩展任务上限到20个，支持超大型项目（城市规划、综合体设计等）。
    """

    # 配置参数（v7.997优化：任务数提升30%，支持更深度的任务拆解）
    MIN_TASKS = 8  # 最少任务数（简单需求，v7.997: 6→8）
    MAX_TASKS = 52  # 最多任务数（v7.997: 40→52，提升30%）
    BASE_TASKS = 13  # 基准任务数（v7.997: 10→13）

    @classmethod
    def analyze(cls, user_input: str, structured_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        分析用户输入复杂度，返回建议的任务数量范围

        Args:
            user_input: 用户原始输入
            structured_data: 结构化数据（可选）

        Returns:
            {
                "recommended_min": int,  # 建议最少任务数
                "recommended_max": int,  # 建议最多任务数
                "complexity_score": float,  # 复杂度得分（0-1）
                "reasoning": str  # 判断依据
            }
        """
        complexity_score = 0.0
        reasoning_parts = []

        # 1. 输入长度评分（基础维度）
        input_length = len(user_input)
        if input_length < 50:
            length_score = 0.2
            reasoning_parts.append("输入较简短")
        elif input_length < 150:
            length_score = 0.4
            reasoning_parts.append("输入中等长度")
        elif input_length < 300:
            length_score = 0.6
            reasoning_parts.append("输入较详细")
        else:
            length_score = 0.8
            reasoning_parts.append("输入非常详细")
        complexity_score += length_score * 0.15

        # 2. 信息维度数量（关键维度）
        # 🔥 v7.996: 面积完全不影响复杂度，只看信息丰富度和设计深度
        dimension_count = 0
        dimensions = {
            "项目类型": [r"别墅", r"住宅", r"办公", r"商业", r"民宿", r"酒店", r"学校", r"医院"],
            "预算约束": [r"\d+万", r"\d+元", r"预算", r"资金", r"成本", r"有限", r"造价", r"限额", r"投资", r"\d+亿"],
            "对标案例": [r"对标", r"参考", r"案例", r"标杆", r"像.*一样"],
            "文化要素": [r"文化", r"传统", r"在地", r"历史", r"特色", r"渔村", r"老街"],
            "客群分析": [r"\d+岁", r"客群", r"用户", r"访客", r"居民", r"女性", r"男性", r"人群"],
            "核心张力": [r'"[^"]+".*与.*"[^"]+"', r"vs", r"对立", r"矛盾", r"平衡"],
            "品牌主题": [r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*", r"为主题", r"品牌"],
            "设计风格": [r"风格", r"杂志级", r"高级感", r"美学", r"氛围"],
            "功能需求": [r"功能", r"需求", r"使用", r"场景", r"动线"],
            "时间约束": [r"\d+个月", r"\d+年", r"工期", r"交付"],
            "地理位置": [r"位于", r"坐落", r"地处", r"所在地", r"当地", r"省", r"市(?!场)", r"区(?!域|间|别)", r"县", r"镇", r"村", r"街道", r"弄堂", r"老城区", r"路\d+号", r"located\s+in", r"downtown", r"district"],
            "特殊场景": [r"老房翻新", r"旧改", r"菜市场", r"历史建筑", r"文保"],
            "多业态融合": [r"[^，。]{2,}\+[^，。]{2,}\+", r"综合体", r"复合", r"一体化"],
            "多阶段工程": [r"分期", r"一期", r"二期", r"首期", r"阶段"],
        }
        # 注：面积（㎡/平米）不在评判维度中，25㎡单间与50000㎡酒店的复杂度取决于设计深度，而非尺度

        for dimension_name, patterns in dimensions.items():
            if any(re.search(pattern, user_input, re.IGNORECASE) for pattern in patterns):
                dimension_count += 1

        dimension_score = min(dimension_count / 10, 1.0)  # 10个维度为满分
        complexity_score += dimension_score * 0.40  # 提高维度权重（从0.35→0.40）
        reasoning_parts.append(f"包含{dimension_count}个信息维度")

        # 3. 结构化数据深度（增强维度）
        structured_score = 0.0
        if structured_data:
            # 检查关键字段
            key_fields = [
                "design_challenge",
                "character_narrative",
                "physical_context",
                "analysis_layers",
                "project_type",
                "core_goals",
            ]
            filled_fields = sum(1 for field in key_fields if structured_data.get(field))
            structured_score = filled_fields / len(key_fields)
            reasoning_parts.append(f"结构化数据包含{filled_fields}个关键字段")
        complexity_score += structured_score * 0.25

        # 4. 特殊场景识别（可能需要更多任务）
        special_scenes = {
            "诗意表达": [r"[如似若像].*[般样]", r"意象", r"隐喻", r"诗意"],
            "多元对立": [r'"[^"]+".*"[^"]+".*"[^"]+"', r"兼顾.*与.*与"],  # 3个以上对立概念
            "跨界融合": [r"融合", r"结合", r"跨界", r"混搭"],
            "文化深度": [r"文化.*文化", r"传统.*现代", r"历史.*未来"],
        }
        special_count = 0
        for scene_name, patterns in special_scenes.items():
            if any(re.search(pattern, user_input, re.IGNORECASE) for pattern in patterns):
                special_count += 1
                reasoning_parts.append(f"检测到{scene_name}")

        special_score = min(special_count / 3, 1.0)
        complexity_score += special_score * 0.15

        # 5. 句子数量（反映思考深度）
        sentence_count = len(re.split(r"[。！？\n]", user_input))
        if sentence_count >= 5:
            sentence_score = 0.1
            reasoning_parts.append(f"包含{sentence_count}个句子/段落")
        else:
            sentence_score = 0.05
        complexity_score += sentence_score

        # 6. 具体数字的出现（反映精确度）
        number_matches = re.findall(r"\d+", user_input)
        if len(number_matches) >= 3:
            complexity_score += 0.1
            reasoning_parts.append("包含多个具体数据")

        # 计算建议任务数量范围（v7.998优化：降低阈值0.30→0.25，提升中等项目下限13→18）
        # 复杂度 0-0.12 -> 8-13个任务（简单需求，阈值从0.15→0.12）
        # 复杂度 0.12-0.25 -> 18-23个任务（中等需求，阈值从0.30→0.25，下限13→18）
        # 复杂度 0.25-0.45 -> 28-36个任务（复杂需求，阈值从0.50→0.45，下限23→28）
        # 复杂度 0.45-1.0 -> 40-52个任务（超大型项目，阈值从0.50→0.45，下限36→40）

        if complexity_score < 0.12:
            recommended_min = 8
            recommended_max = 13
        elif complexity_score < 0.25:
            recommended_min = 18  # 从13提升到18，避免卡在13
            recommended_max = 23
        elif complexity_score < 0.45:
            recommended_min = 28  # 从23提升到28
            recommended_max = 36
        else:
            recommended_min = 40  # 从36提升到40
            recommended_max = cls.MAX_TASKS  # 52

        reasoning = "; ".join(reasoning_parts)

        logger.info(f" [TaskComplexityAnalyzer] 复杂度={complexity_score:.2f}, 建议任务数={recommended_min}-{recommended_max}")

        return {
            "recommended_min": recommended_min,
            "recommended_max": recommended_max,
            "complexity_score": complexity_score,
            "reasoning": reasoning,
        }


class CoreTaskDecomposer:
    """
    核心任务拆解器

    使用 LLM 将用户输入拆解为精准的、可执行的任务列表。
    """

    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._config is None:
            self._load_config()

    def _load_config(self) -> None:
        """加载配置文件"""
        config_path = Path(__file__).parent.parent / "config" / "prompts" / "core_task_decomposer.yaml"
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f)
            logger.info(f" [CoreTaskDecomposer] 配置加载成功: {config_path}")
        except Exception as e:
            logger.warning(f"️ [CoreTaskDecomposer] 配置加载失败: {e}")
            self._config = {}

    @property
    def config(self) -> Dict[str, Any]:
        """获取配置"""
        return self._config or {}

    def _get_feature_label(self, feature_id: str) -> str:
        """🆕 v7.960: 获取特征ID对应的中文标签
        
        Args:
            feature_id: 特征ID（如 'cultural', 'commercial'）
            
        Returns:
            中文标签（如 '文化认同', '商业价值'）
        """
        labels = {
            'cultural': '文化认同',
            'commercial': '商业价值',
            'wellness': '健康疗愈',
            'technical': '技术创新',
            'sustainable': '可持续发展',
            'professional': '专业赋能',
            'inclusive': '包容性设计',
            'functional': '功能实用',
            'emotional': '情感共鸣',
            'aesthetic': '美学体验',
            'social': '社交连接',
            'mixed': '综合需求'
        }
        return labels.get(feature_id, feature_id)
    
    def _get_dynamic_guidance(self, project_features: Dict[str, float]) -> str:
        """🆕 v7.960: 根据特征向量生成动态指导（v7.963优化版）
        
        v7.963核心改进：
        - 增加任务粒度控制（引导独立拆解，避免混合）
        - 增加深度调研示范（明确罗列调研维度）
        - 增加阶段性约束（强调深度调研，避免过早设计）
        
        Args:
            project_features: 12维特征向量字典
            
        Returns:
            拆解策略的动态指导文本
        """
        guidance_parts = []
        
        # 🆕 v7.963: 增加通用任务质量指导
        guidance_parts.append("### 📋 任务拆解质量标准")
        guidance_parts.append("**粒度控制**：")
        guidance_parts.append("  ✅ 每个关键对象独立成任务（如：每位设计师/案例一个独立任务）")
        guidance_parts.append("  ❌ 避免混合多个对象（错误示例：'调研[设计师A]、[设计师B]、[设计师C]等大师'）")
        guidance_parts.append("\n**深度标准**：")
        guidance_parts.append("  ✅ 明确罗列调研维度（如：'建筑哲学、材料策略、空间理念、代表作品'）")
        guidance_parts.append("  ❌ 避免模糊表述（错误示例：'研究XX的设计理念'）")
        guidance_parts.append("\n**阶段定位**：")
        guidance_parts.append("  • 当前为**深度调研阶段**，优先生成'搜索/调研/收集'类任务")
        guidance_parts.append("  • 暂缓'提出方案/设计/制定'类任务（留待专家协作阶段）")
        
        # 按分数排序特征
        sorted_features = sorted(project_features.items(), key=lambda x: x[1], reverse=True)
        
        # 为高分特征（>0.7）提供专项指导
        high_score_features = [(fid, score) for fid, score in sorted_features if score >= 0.7]
        
        if high_score_features:
            guidance_parts.append("\n### 🔥 核心特征（高分 ≥0.7）")
            for feature_id, score in high_score_features:
                label = self._get_feature_label(feature_id)
                guidance_parts.append(
                    f"- **{label}** ({score:.2f}): 该项目在此维度得分极高，"
                    f"需**细粒度拆解**调研任务，确保每个关键要素独立深挖"
                )
        
        # 为中高分特征（0.5-0.7）提供次要指导
        mid_score_features = [(fid, score) for fid, score in sorted_features if 0.5 <= score < 0.7]
        
        if mid_score_features:
            guidance_parts.append("\n### ⭐ 重要特征（0.5-0.7）")
            for feature_id, score in mid_score_features:
                label = self._get_feature_label(feature_id)
                guidance_parts.append(
                    f"- **{label}** ({score:.2f}): 建议针对性调研，"
                    f"明确列举需收集的信息维度"
                )
        
        # 🆕 v7.963: 任务方向建议（提供具体调研维度+粒度示范）
        if high_score_features or mid_score_features:
            guidance_parts.append("\n### 🎯 调研方向与粒度示范")
            top_feature = high_score_features[0][0] if high_score_features else mid_score_features[0][0]
            label = self._get_feature_label(top_feature)
            
            if top_feature == 'cultural':
                guidance_parts.append(f"\n**{label}维度调研建议**（细粒度拆解）：")
                guidance_parts.append("1. **地域文化调研**（独立任务）")
                guidance_parts.append("   - 明确维度：历史文化、农耕传统、民俗特色、建筑语言")
                guidance_parts.append("2. **传统工艺研究**（独立任务）")
                guidance_parts.append("   - 明确维度：手工艺类型、工艺流程、材料特性、传承人信息")
                guidance_parts.append("3. **文化转译案例**（每位设计师/学者独立任务）")
                guidance_parts.append("   - 如：'搜索[设计师A]的设计哲学、精神性空间理念、代表作品与核心手法'")
                guidance_parts.append("   - 如：'搜索[设计师B]的材料创新运用、自然融合策略、代表项目'")
                guidance_parts.append("   - 如：'搜索[设计师C]的地域设计探索、在地材料运用、代表项目'")
                guidance_parts.append("   - 提示：请根据项目实际领域选择相关的设计师/学者进行独立调研")
                guidance_parts.append("4. **文化符号库构建**（独立任务）")
                guidance_parts.append("   - 明确维度：视觉符号、空间原型、仪式场景、叙事线索")
                
            elif top_feature == 'commercial':
                guidance_parts.append(f"\n**{label}维度调研建议**（细粒度拆解）：")
                guidance_parts.append("1. **产业结构调研**（独立任务）")
                guidance_parts.append("   - 明确维度：经济模式、产业布局、主导产业、发展趋势")
                guidance_parts.append("2. **成功案例研究**（每个案例独立任务）")
                guidance_parts.append("   - 明确维度：商业模式、盈利结构、运营策略、用户画像")
                guidance_parts.append("3. **市场定位分析**（独立任务）")
                guidance_parts.append("   - 明确维度：目标客群、竞争格局、差异化策略、品牌定位")
                guidance_parts.append("4. **ROI测算框架**（独立任务）")
                guidance_parts.append("   - 明确维度：成本结构、收入预测、风险因素、盈亏平衡点")
                
            elif top_feature == 'wellness':
                guidance_parts.append(f"\n**{label}维度调研建议**（细粒度拆解）：")
                guidance_parts.append("1. **健康标准研究**（每个标准体系独立任务）")
                guidance_parts.append("   - 如：WELL建筑标准、中国健康建筑评价标准")
                guidance_parts.append("2. **特殊人群需求调研**（每类人群独立任务）")
                guidance_parts.append("   - 明确维度：生理特征、行为模式、空间需求、辅助设施")
                guidance_parts.append("3. **疗愈空间案例**（每个案例独立任务）")
                guidance_parts.append("   - 明确维度：空间类型、疗愈机制、设计手法、效果评估")
                
            elif top_feature == 'aesthetic':
                guidance_parts.append(f"\n**{label}维度调研建议**（细粒度拆解）：")
                guidance_parts.append("1. **美学流派研究**（每个流派独立任务）")
                guidance_parts.append("   - 明确维度：理论基础、设计语言、代表作品、适用场景")
                guidance_parts.append("2. **氛围营造案例**（每个案例独立任务）")
                guidance_parts.append("   - 明确维度：光影策略、材料质感、色彩体系、空间序列")
                guidance_parts.append("3. **艺术装置研究**（每位艺术家独立任务）")
                guidance_parts.append("   - 明确维度：创作理念、材料实验、空间关系、互动机制")
                
            elif top_feature == 'technical':
                guidance_parts.append(f"\n**{label}维度调研建议**（细粒度拆解）：")
                guidance_parts.append("1. **技术体系调研**（每个技术方向独立任务）")
                guidance_parts.append("   - 明确维度：技术原理、成熟度评估、应用案例、成本分析")
                guidance_parts.append("2. **智能系统研究**（每个系统独立任务）")
                guidance_parts.append("   - 明确维度：系统架构、功能模块、集成方案、维护成本")
                guidance_parts.append("3. **工艺创新案例**（每个案例独立任务）")
                guidance_parts.append("   - 明确维度：工艺流程、材料创新、质量控制、效率提升")
                
            elif top_feature == 'sustainable':
                guidance_parts.append(f"\n**{label}维度调研建议**（细粒度拆解）：")
                guidance_parts.append("1. **生态评估标准**（每个标准独立任务）")
                guidance_parts.append("   - 如：LEED认证、绿色建筑评价标准、碳中和路径")
                guidance_parts.append("2. **可再生能源技术**（每种能源独立任务）")
                guidance_parts.append("   - 明确维度：技术原理、适用条件、成本效益、运维要求")
                guidance_parts.append("3. **材料循环案例**（每个案例独立任务）")
                guidance_parts.append("   - 明确维度：材料来源、循环工艺、性能对比、生命周期成本")
        
        # 如果所有特征都较低，提供通用指导
        if not high_score_features and not mid_score_features:
            guidance_parts.append("### ℹ️ 通用指导（无显著特征）")
            guidance_parts.append("- 该项目特征分布较为平均，建议采用综合性拆解策略")
            guidance_parts.append("- 重点关注用户核心需求和实际场景")
        
        return "\n".join(guidance_parts)
    
    def _simple_mode_detection(self, user_input: Optional[str], project_type: str, 
                               project_features: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        🆕 P1-3: 本地简化 mode detection（当 structured_data 中的 mode detection 失败时）
        
        基于关键词和特征向量的快速 mode 检测，只检测核心10个 Mode
        
        Args:
            user_input: 用户输入文本
            project_type: 项目类型
            project_features: 12维特征向量
        
        Returns:
            检测到的 mode 列表 [{'mode': 'M5_rural_context', 'confidence': 0.7}, ...]
        """
        detected = []
        text = (user_input or "") + " " + (project_type or "")
        text_lower = text.lower()
        
        # 10个核心 Mode 的快速检测规则（基于 mode_detector.py 的 MODE_SIGNATURES）
        mode_rules = {
            "M1_concept_driven": {
                "keywords": ["概念", "精神", "品牌", "文化母题", "表达", "哲学", "身份", "艺术", "内涵", "意境"],
                "min_score": 0.4
            },
            "M2_function_efficiency": {
                "keywords": ["效率", "动线", "流程", "办公", "系统", "优化", "功能", "标准化", "工位"],
                "min_score": 0.4
            },
            "M3_emotional_experience": {
                "keywords": ["体验", "情绪", "沉浸", "感知", "氛围", "五感", "酒店", "民宿", "情感", "记忆"],
                "min_score": 0.4
            },
            "M4_capital_asset": {
                "keywords": ["投资", "资产", "增值", "回报", "坪效", "租金", "ROI", "商业模式", "盈利"],
                "min_score": 0.35
            },
            "M5_rural_context": {
                "keywords": ["乡村", "村落", "民宿", "农耕", "在地", "传统", "非遗", "宗族", "田园", "乡建", 
                           "振兴", "工艺", "节庆", "村民", "集群"],
                "feature_keys": ["cultural", "historical", "regional"],
                "min_score": 0.35
            },
            "M6_cultural_heritage": {
                "keywords": ["文化", "遗产", "历史", "传承", "保护", "修复", "博物馆", "展览", "文物"],
                "feature_keys": ["cultural", "historical"],
                "min_score": 0.4
            },
            "M7_tech_integration": {
                "keywords": ["技术", "智能", "科技", "数字", "BIM", "智能化", "集成", "自动化"],
                "feature_keys": ["technical"],
                "min_score": 0.4
            },
            "M8_social_responsibility": {
                "keywords": ["社会", "社区", "公益", "包容", "无障碍", "可达性", "共享", "社群"],
                "feature_keys": ["social", "inclusive"],
                "min_score": 0.35
            },
            "M9_sustainable_design": {
                "keywords": ["可持续", "生态", "环保", "绿色", "节能", "碳", "循环", "气候"],
                "feature_keys": ["sustainable"],
                "min_score": 0.4
            },
            "M10_material_innovation": {
                "keywords": ["材料", "材质", "创新", "实验", "工艺", "建造", "构造"],
                "feature_keys": ["material_innovation"],
                "min_score": 0.35
            },
            "M11_healthcare_healing": {
                "keywords": ["疗愈", "康复", "医疗", "护理", "安全感", "无障碍", "心理", "焦虑", "尊严", "节律", "养老", "临终"],
                "feature_keys": ["healing", "accessibility"],
                "min_score": 0.35
            }
        }
        
        for mode_id, rule in mode_rules.items():
            score = 0.0
            
            # 关键词匹配
            keyword_hits = sum(1 for kw in rule["keywords"] if kw in text_lower)
            
            # 🔧 P1修复: 当project_features为空时，给关键词全部权重（原来0.6浪费了0.4）
            has_features = bool("feature_keys" in rule and project_features)
            kw_weight = 0.6 if has_features else 1.0
            feat_weight = 0.4 if has_features else 0.0
            
            if keyword_hits > 0:
                score += min(keyword_hits / len(rule["keywords"]), 1.0) * kw_weight
            
            # 特征向量匹配
            if has_features:
                feature_scores = [project_features.get(fk, 0) for fk in rule["feature_keys"]]
                if feature_scores:
                    avg_feature_score = sum(feature_scores) / len(feature_scores)
                    score += avg_feature_score * feat_weight
            
            # 🔧 P1修复: 降低阈值（0.35-0.4 → 0.25-0.3），让复杂项目能匹配更多mode
            min_score = rule.get("min_score", 0.4) * 0.7  # 缩放到70%
            if score >= min_score:
                detected.append({
                    "mode": mode_id,
                    "confidence": round(score, 2),
                    "method": "local_simple_detection"
                })
        
        # 按置信度排序
        detected.sort(key=lambda x: x["confidence"], reverse=True)
        
        # 🆕 P1-3: 特别针对 rural 场景的兜底检测
        # 如果文本中包含 rural/village 关键词但 M5_rural_context 未被检测到，强制添加
        rural_keywords = ["乡村", "村落", "民宿", "农耕", "在地", "非遗", "宗族", "田园", "乡建", "村民",
                          "新农村", "农文旅", "乡村振兴", "村建", "农村建设", "农村改造", "集群"]
        if any(kw in text_lower for kw in rural_keywords):
            if not any(d["mode"] == "M5_rural_context" for d in detected):
                detected.append({
                    "mode": "M5_rural_context",
                    "confidence": 0.5,
                    "method": "rural_keyword_fallback"
                })
                logger.info("  [P1-3] 检测到 rural 关键词，强制添加 M5_rural_context")
        
        return detected[:5]  # 🔧 P1修复: 最多返回5个mode（3→5，复杂项目常涉及多模式）

    def _load_few_shot_examples(self) -> Dict[str, Any]:
        """🆕 v7.999.4: 加载Few-shot示例
        
        Returns:
            Few-shot示例字典 {example_name: yaml_content}
        """
        import yaml
        from pathlib import Path
        
        examples = {}
        few_shot_dir = Path(__file__).parent.parent / "config" / "prompts" / "few_shot_examples"
        
        if not few_shot_dir.exists():
            logger.warning(f"⚠️ Few-shot目录不存在: {few_shot_dir}")
            return examples
        
        try:
            for yaml_file in few_shot_dir.glob("*.yaml"):
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    content = yaml.safe_load(f)
                    examples[yaml_file.stem] = content
                    logger.info(f"✅ 加载Few-shot示例: {yaml_file.stem}")
        except Exception as e:
            logger.error(f"❌ Few-shot加载失败: {e}")
        
        return examples
    
    def _select_best_few_shot(self, project_type: str, project_features: Dict[str, float],
                               detected_modes: Optional[List[Dict[str, Any]]] = None,
                               user_input: Optional[str] = None) -> Optional[str]:
        """v8.0 P0-T3: 基于 tags_matrix + 设计模式的智能 Few-shot 匹配
        
        匹配策略（优先级递减）：
        1. 设计模式 + tags_matrix 标签重叠度
        2. 项目类型关键词
        3. 特征向量 top feature
        4. 默认 fallback
        
        Args:
            project_type: 项目类型
            project_features: 12维特征向量
            detected_modes: 检测到的设计模式列表
            
        Returns:
            Few-shot示例文件名 (如 'commercial_dominant_01')
        """
        import yaml
        from pathlib import Path
        
        # 加载 registry
        registry_path = Path(__file__).parent.parent / "config" / "prompts" / "few_shot_examples" / "examples_registry.yaml"
        registry_examples = []
        if registry_path.exists():
            try:
                with open(registry_path, 'r', encoding='utf-8') as f:
                    registry_data = yaml.safe_load(f)
                    registry_examples = registry_data.get("examples", [])
            except Exception as e:
                logger.warning(f"[v8.0 P0-T3] registry 加载失败: {e}")
        
        if not registry_examples:
            # fallback 到原始逻辑
            return self._select_few_shot_fallback(project_type, project_features)
        
        # 🔍 诊断日志: 输入参数检查
        logger.debug("[DIAG] _select_best_few_shot 输入参数:")
        logger.debug(f"  project_type类型: {type(project_type)}, 值: {project_type}")
        logger.debug(f"  project_features类型: {type(project_features)}, 键数量: {len(project_features) if project_features else 0}")
        logger.debug(f"  detected_modes类型: {type(detected_modes)}, 数量: {len(detected_modes) if detected_modes else 0}")
        logger.debug(f"  registry_examples数量: {len(registry_examples)}")
        
        # 构建查询标签集合
        query_tags = set()
        
        # ═══════════════════════════════════════════════════════════
        # v8.000 (P3-T11): 从 YAML 预映射表加载 MODE_TO_TAGS
        # 修正 Mode ID 不一致 + 外部可维护
        # ═══════════════════════════════════════════════════════════
        MODE_TO_TAGS = self._load_mode_to_tags_mapping()
        
        # 🆕 P1-3: 当 detected_modes 为空时，执行本地简化 mode detection
        if not detected_modes or len(detected_modes) == 0:
            logger.info("  [P1-3] detected_modes 为空，启动本地简化 mode detection...")
            detected_modes = self._simple_mode_detection(user_input, project_type, project_features)
            if detected_modes:
                logger.info(f"  [P1-3] 本地检测到 {len(detected_modes)} 个设计模式")
        
        if detected_modes:
            for mode_info in detected_modes:
                mode_id = mode_info.get("mode", "")
                confidence = mode_info.get("confidence", 0)
                if confidence >= 0.3 and mode_id in MODE_TO_TAGS:
                    # 🆕 P0防御: 确保MODE_TO_TAGS返回的是可迭代对象
                    mode_tags = MODE_TO_TAGS[mode_id]
                    if isinstance(mode_tags, (set, list, tuple)):
                        query_tags.update(mode_tags)
                    elif isinstance(mode_tags, str):
                        query_tags.add(mode_tags)
                    else:
                        logger.warning(f"[P0] MODE_TO_TAGS[{mode_id}]类型异常: {type(mode_tags).__name__}")
        
        # 从 project_type 提取标签（guard: project_type 可能为 None 或空字符串）
        pt_lower = str(project_type or "").lower()
        if "commercial" in pt_lower or "retail" in pt_lower:
            query_tags.update({"commercial", "retail"})
        if "residential" in pt_lower or "personal" in pt_lower:
            query_tags.update({"family_residence", "apartment"})
        if "hotel" in pt_lower or "hospitality" in pt_lower:
            query_tags.update({"hotel", "hospitality"})
        if "rural" in pt_lower or "village" in pt_lower:
            query_tags.update({"rural_residence", "cluster"})
        if "cultural" in pt_lower or "museum" in pt_lower:
            query_tags.update({"cultural_heritage", "cultural_research"})
        
        # 从 top features 提取标签
        if project_features:
            top_features = sorted(project_features.items(), key=lambda x: x[1], reverse=True)[:3]
            for feat_id, score in top_features:
                if score >= 0.4:
                    query_tags.add(feat_id)
        
        # ═══════════════════════════════════════════════════════════
        # v8.000 (P3-T12): feature_vector → Mode Engine 统一
        # 当 feature_vector 某维度高分但 detected_modes 未覆盖时，
        # 通过 feature_to_modes 反向推断隐含模式，补充 query_tags
        # ═══════════════════════════════════════════════════════════
        if project_features and not detected_modes:
            implied_mode_tags = self._infer_tags_from_features(project_features)
            if implied_mode_tags:
                # 🆕 P0防御: 确保implied_mode_tags是可迭代对象
                if isinstance(implied_mode_tags, (set, list, tuple)):
                    query_tags.update(implied_mode_tags)
                    logger.info(
                        f"[P3-T12] feature_vector 反向补充 {len(implied_mode_tags)} 个标签"
                    )
                else:
                    logger.warning(f"[P0] implied_mode_tags类型异常: {type(implied_mode_tags).__name__}")
        # ═══════════════════════════════════════════════════════════
        
        if not query_tags:
            return self._select_few_shot_fallback(project_type, project_features)
        
        # 确定实际存在的 YAML 文件集合
        examples_dir = registry_path.parent
        available_stems = set()
        if examples_dir.exists():
            for yaml_file in examples_dir.glob("*.yaml"):
                stem = yaml_file.stem
                if stem != "examples_registry":
                    available_stems.add(stem)
        
        # 计算每个 registry 示例的标签重叠度
        best_score = -1
        best_file = None
        
        # 统计幽灵条目（注册表有但文件不存在）
        ghost_count = 0
        for example in registry_examples:
            file_name = example.get("file", "")
            file_stem = file_name.replace(".yaml", "") if file_name else ""
            if file_stem and file_stem not in available_stems:
                ghost_count += 1
        if ghost_count > 0:
            logger.warning(f"[Few-shot] 注册表有 {ghost_count} 个条目缺少对应YAML文件，已跳过")

        for example in registry_examples:
            # 提前跳过无文件的条目，避免无效计算
            file_name = example.get("file", "")
            file_stem = file_name.replace(".yaml", "") if file_name else ""
            if not file_stem or file_stem not in available_stems:
                continue

            tags_matrix = example.get("tags_matrix", {})
            if not tags_matrix:
                continue

            # 提取所有标签到扁平集合
            example_tags = set()
            for dim_key, dim_val in tags_matrix.items():
                # 🔍 P0诊断: 记录dim_val类型
                logger.debug(f"[P0-DEBUG] dim_key={dim_key}, dim_val type={type(dim_val).__name__}, value={dim_val if not isinstance(dim_val, dict) else '[dict]'}")
                if isinstance(dim_val, list):
                    example_tags.update(dim_val)
                elif isinstance(dim_val, str):
                    example_tags.add(dim_val)
                elif isinstance(dim_val, dict):
                    # 🆕 P0防御: 处理嵌套dict结构（如老版本YAML格式）
                    # 尝试提取dict的values
                    for nested_val in dim_val.values():
                        if isinstance(nested_val, list):
                            example_tags.update(nested_val)
                        elif isinstance(nested_val, str):
                            example_tags.add(nested_val)
                    logger.debug(f"[P0] tags_matrix包含dict: {dim_key}, 已提取{len(dim_val)}个子项")
                else:
                    # 其他类型（int, float等）转为字符串
                    logger.debug(f"[P0] 跳过非标准类型: {dim_key}={type(dim_val).__name__}")
            
            # 计算 Jaccard 相似度
            intersection = query_tags & example_tags
            union = query_tags | example_tags
            jaccard = len(intersection) / len(union) if union else 0

            # ═══ v8.000 (P3-T12): feature_vector 余弦相似度加成 ═══
            feature_bonus = 0.0
            if project_features:
                example_fv = example.get("feature_vector", {})
                if example_fv:
                    feature_bonus = self._cosine_similarity_bonus(
                        project_features, example_fv
                    )
            
            # 综合评分: Jaccard 50% + feature_vector cosine 50%
            # ✨ P2优化: 调整权重比例，提升feature_vector影响力
            score = jaccard * 0.5 + feature_bonus * 0.5
            # ═══════════════════════════════════════════════════════
            
            if score > best_score:
                best_score = score
                best_file = file_stem
        
        if best_file and best_score > 0:
            logger.info(f"[v8.0 P0-T3] tags_matrix 匹配: {best_file} (score={best_score:.3f}, query_tags={len(query_tags)})")
            return best_file
        
        return self._select_few_shot_fallback(project_type, project_features)
    
    def _select_few_shot_fallback(self, project_type: str, project_features: Dict[str, float]) -> Optional[str]:
        """基于项目类型和特征向量的多路由 fallback 逻辑
        
        覆盖5个已有YAML示例文件:
        - commercial_dominant_01: 商业/零售/综合体/办公
        - functional_dominant_01: 住宅/功能主导/特殊需求/医疗/教育
        - cultural_dominant_01: 文化/乡村/遗产/博物馆/酒店
        - technical_dominant_02: 技术/极端环境/可持续/基础设施
        - aesthetic_dominant_01: 审美/品牌/奢华/艺术
        """
        pt_lower = project_type.lower() if project_type else ''
        
        # 1. 基于项目类型关键词的精确路由
        if any(kw in pt_lower for kw in ['commercial', 'retail', 'market', 'mixed_use', 'office']):
            return 'commercial_dominant_01'
        if any(kw in pt_lower for kw in ['residential', 'personal', 'family', 'apartment', 'housing']):
            return 'functional_dominant_01'
        if any(kw in pt_lower for kw in ['cultural', 'heritage', 'museum', 'rural', 'village', 'exhibition']):
            return 'cultural_dominant_01'
        if any(kw in pt_lower for kw in ['technical', 'extreme', 'sustainable', 'industrial', 'infrastructure']):
            return 'technical_dominant_02'
        if any(kw in pt_lower for kw in ['aesthetic', 'brand', 'luxury', 'boutique', 'art']):
            return 'aesthetic_dominant_01'
        if any(kw in pt_lower for kw in ['hotel', 'hospitality', 'resort', 'spa']):
            return 'cultural_dominant_01'
        if any(kw in pt_lower for kw in ['medical', 'healthcare', 'elderly', 'education', 'school']):
            return 'functional_dominant_01'
        
        # 2. 基于特征向量 top feature 的路由
        if project_features:
            top_feature = max(project_features.items(), key=lambda x: x[1])[0]
            feature_to_example = {
                'commercial': 'commercial_dominant_01',
                'social': 'commercial_dominant_01',
                'functional': 'functional_dominant_01',
                'wellness': 'functional_dominant_01',
                'inclusive': 'functional_dominant_01',
                'cultural': 'cultural_dominant_01',
                'historical': 'cultural_dominant_01',
                'regional': 'cultural_dominant_01',
                'technical': 'technical_dominant_02',
                'sustainable': 'technical_dominant_02',
                'material_innovation': 'technical_dominant_02',
                'aesthetic': 'aesthetic_dominant_01',
                'symbolic': 'aesthetic_dominant_01',
                'experiential': 'aesthetic_dominant_01',
            }
            if top_feature in feature_to_example:
                return feature_to_example[top_feature]
        
        # 3. 最终 fallback: 功能主导（最通用）
        return 'functional_dominant_01'

    def _load_mode_to_tags_mapping(self) -> Dict[str, set]:
        """
        从 YAML 预映射表加载 Mode → tags_matrix 映射

        v8.000 (P3-T11): 将硬编码映射外部化为 config/mode_feature_mapping.yaml
        修正了 Mode ID 不一致问题 (M2_function_efficiency, M7_tech_integration)

        Returns:
            {mode_id: {tag1, tag2, ...}, ...}
        """
        if hasattr(self, '_cached_mode_to_tags') and self._cached_mode_to_tags:
            return self._cached_mode_to_tags

        import yaml
        from pathlib import Path

        mapping_path = Path(__file__).parent.parent / "config" / "mode_feature_mapping.yaml"

        # 硬编码 fallback（与 YAML 一致，防止文件缺失）
        fallback = {
            "M1_concept_driven": {"concept", "aesthetic", "cultural"},
            "M2_function_efficiency": {"functional", "operation_efficiency"},
            "M3_emotional_experience": {"experiential", "aesthetic", "narrative_design"},
            "M4_capital_asset": {"commercial", "operation_efficiency", "operation_driven"},
            "M5_rural_context": {"rural_residence", "cultural_heritage", "cultural_research", "cluster"},
            "M6_urban_regeneration": {"urban_renewal", "public_space", "renovation"},
            "M7_tech_integration": {"technical_complexity", "technical_innovation"},
            "M8_extreme_condition": {"technical_complexity", "climate_adaptation", "material_durability"},
            "M9_social_structure": {"social_impact", "family", "community"},
            "M10_future_speculation": {"technical_innovation", "concept"},
            "M11_healthcare_healing": {"healing", "accessibility", "safety", "wellbeing"},
        }

        try:
            if mapping_path.exists():
                with open(mapping_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                mode_to_tags_raw = config.get("mode_to_tags", {})
                if mode_to_tags_raw:
                    result = {k: set(v) for k, v in mode_to_tags_raw.items()}
                    self._cached_mode_to_tags = result
                    logger.info(f"[P3-T11] 从 YAML 加载 mode_to_tags 映射 ({len(result)} 模式)")
                    
                    # 🔍 诊断日志: 检查数据结构
                    logger.debug(f"[DIAG] mode_to_tags_raw类型: {type(mode_to_tags_raw)}")
                    for mode_id, tags in list(result.items())[:3]:  # 只显示前3个
                        logger.debug(f"[DIAG]   {mode_id}: tags类型={type(tags)}, 数量={len(tags)}, 示例={list(tags)[:3]}")
                    
                    return result
        except Exception as e:
            logger.warning(f"[P3-T11] 加载 mode_feature_mapping.yaml 失败，使用 fallback: {e}")

        self._cached_mode_to_tags = fallback
        return fallback

    def _infer_tags_from_features(self, project_features: Dict[str, float]) -> set:
        """
        从 feature_vector 高分维度反向推断 implied modes，提取对应 tags

        v8.000 (P3-T12): feature_vector → Mode Engine 统一桥梁
        当 detected_modes 为空时，用 feature_vector 的 top 维度
        通过 feature_to_modes 映射推断可能的模式，再提取 tags

        Args:
            project_features: 12维特征向量 {dim: score}

        Returns:
            推断出的 tags 集合
        """
        import yaml
        from pathlib import Path

        # 加载 feature_to_modes 映射
        mapping_path = Path(__file__).parent.parent / "config" / "mode_feature_mapping.yaml"
        feature_to_modes = {}
        try:
            if mapping_path.exists():
                with open(mapping_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                feature_to_modes = config.get("feature_to_modes", {})
        except Exception:
            pass

        if not feature_to_modes:
            return set()

        # 找 top 3 高分维度（>= 0.5）
        high_dims = sorted(project_features.items(), key=lambda x: x[1], reverse=True)[:3]
        implied_modes = set()
        for dim, score in high_dims:
            if score >= 0.5 and dim in feature_to_modes:
                implied_modes.update(feature_to_modes[dim])

        # 将 implied modes 转为 tags
        mode_to_tags = self._load_mode_to_tags_mapping()
        result_tags = set()
        for mode_id in implied_modes:
            if mode_id in mode_to_tags:
                result_tags.update(mode_to_tags[mode_id])
        
        return result_tags

    @staticmethod
    def _cosine_similarity_bonus(
        query_fv: Dict[str, float], example_fv: Dict[str, float]
    ) -> float:
        """
        计算两个 feature_vector 之间的余弦相似度

        v8.000 (P3-T12): 作为 Jaccard 标签匹配的补充信号

        Args:
            query_fv: 查询项目的特征向量
            example_fv: 示例的特征向量

        Returns:
            余弦相似度 (0-1)
        """
        import math

        # 统一键集合
        all_keys = set(query_fv.keys()) | set(example_fv.keys())
        if not all_keys:
            return 0.0

        dot = sum(query_fv.get(k, 0) * example_fv.get(k, 0) for k in all_keys)
        norm_a = math.sqrt(sum(query_fv.get(k, 0) ** 2 for k in all_keys))
        norm_b = math.sqrt(sum(example_fv.get(k, 0) ** 2 for k in all_keys))

        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def build_prompt(
        self,
        user_input: str,
        structured_data: Optional[Dict[str, Any]] = None,
        task_count_range: Optional[tuple] = None,
    ) -> str:
        """
        构建 LLM 调用的 prompt（v7.999.4 Few-shot加载 + 直接生成目标数量）

        Args:
            user_input: 用户原始输入
            structured_data: 需求分析阶段产出的结构化数据（可选）
            task_count_range: 建议的任务数量范围 (min, max)，如 (40, 52)

        Returns:
            完整的 prompt 字符串
        """
        # 🆕 v7.999.4: 加载Few-shot示例
        few_shot_examples = self._load_few_shot_examples()
        few_shot_content = ""
        
        # 构建结构化数据摘要
        structured_summary = ""
        feature_visualization = ""  # v7.960: 特征向量可视化
        dynamic_guidance = ""  # v7.960: 动态拆解指导
        
        if structured_data:
            summary_parts = []

            # 提取关键字段
            project_task = structured_data.get("project_task", "")
            if project_task:
                summary_parts.append(f"项目任务: {project_task}")

            character_narrative = structured_data.get("character_narrative", "")
            if character_narrative:
                summary_parts.append(f"人物叙事: {character_narrative}")

            physical_context = structured_data.get("physical_context", "")
            if physical_context:
                summary_parts.append(f"物理场景: {physical_context}")

            project_type = structured_data.get("project_type", "")
            if project_type:
                summary_parts.append(f"项目类型: {project_type}")

            # L1-L5 分析层信息
            analysis_layers = structured_data.get("analysis_layers", {})
            if analysis_layers:
                l3_tension = analysis_layers.get("L3_core_tension", "")
                if l3_tension:
                    summary_parts.append(f"核心张力: {l3_tension}")

            # ⚠️ v9.1: 消费 Phase2 深度分析字段（原为死字段，现已通过 _merge_phase_results 传递）
            core_tensions = structured_data.get("core_tensions", [])
            if core_tensions:
                tension_strs = []
                for t in core_tensions[:3]:
                    if isinstance(t, dict):
                        tension_strs.append(f"{t.get('tension_a', '')} ↔ {t.get('tension_b', '')}")
                    elif isinstance(t, str):
                        tension_strs.append(t)
                if tension_strs:
                    summary_parts.append(f"核心张力对: {'; '.join(tension_strs)}")

            breakthrough_insight = structured_data.get("breakthrough_insight", "")
            if breakthrough_insight:
                summary_parts.append(f"穿透性洞察: {breakthrough_insight}")

            design_principles = structured_data.get("design_principles", [])
            if design_principles:
                summary_parts.append(f"设计原则: {'、'.join(design_principles[:5])}")

            l2_lenses = structured_data.get("l2_disciplinary_lenses", [])
            if l2_lenses:
                summary_parts.append(f"学科透镜: {'、'.join(l2_lenses[:3])}")

            # v8.0 P0-T2: 注入设计模式标签到摘要
            detected_modes = structured_data.get("detected_design_modes", [])
            if detected_modes:
                # 按置信度排序
                sorted_modes = sorted(detected_modes, key=lambda m: m.get("confidence", 0), reverse=True)
                primary = sorted_modes[0]
                mode_name = primary.get("mode", "unknown")
                mode_conf = primary.get("confidence", 0)
                
                # 模式中文名映射
                MODE_LABELS = {
                    "M1_concept_driven": "概念驱动型", "M2_function_efficiency": "功能效率型",
                    "M3_emotional_experience": "情绪体验型", "M4_capital_asset": "资产资本型",
                    "M5_rural_context": "乡建在地型", "M6_urban_regeneration": "城市更新型",
                    "M7_tech_integration": "技术整合型", "M8_extreme_condition": "极端环境型",
                    "M9_social_structure": "社会结构型", "M10_future_speculation": "未来推演型",
                    "M11_healthcare_healing": "健康疗愈型",
                }
                label = MODE_LABELS.get(mode_name, mode_name)
                summary_parts.append(f"\n设计模式: {mode_name} ({label})，置信度 {mode_conf:.2f}")
                
                if len(sorted_modes) > 1:
                    secondary = sorted_modes[1]
                    sec_name = secondary.get("mode", "")
                    sec_label = MODE_LABELS.get(sec_name, sec_name)
                    sec_conf = secondary.get("confidence", 0)
                    if sec_conf >= 0.3:
                        summary_parts.append(f"次要模式: {sec_name} ({sec_label})，置信度 {sec_conf:.2f}")
                
                logger.info(f"[v8.0 P0-T2] 已注入设计模式: {label} ({mode_conf:.2f})")

            structured_summary = "\n".join(summary_parts) if summary_parts else "暂无补充信息"
            
            # 🆕 v7.960: 提取并可视化项目特征向量
            project_features = structured_data.get("project_features", {})
            if project_features:
                logger.info("🎯 [v7.960] 检测到项目特征向量，开始构建动态拆解策略")
                
                # 按分数排序并生成条形图
                sorted_features = sorted(project_features.items(), key=lambda x: x[1], reverse=True)
                
                viz_lines = ["\n## 📊 项目特征向量分析（v7.960 动态矩阵）"]
                viz_lines.append("以下是基于深度分析提取的12维项目特征，请据此调整任务拆解策略：\n")
                
                for feature_id, score in sorted_features:
                    label = self._get_feature_label(feature_id)
                    bar = "█" * int(score * 20)  # 满分20格
                    marker = "🔥" if score >= 0.7 else ("⭐" if score >= 0.5 else "")
                    viz_lines.append(f"  • {label:8s}: {score:.2f} {bar} {marker}")
                
                feature_visualization = "\n".join(viz_lines)
                
                # 生成动态指导
                dynamic_guidance = "\n\n" + self._get_dynamic_guidance(project_features)
                
                logger.info(f"   TOP3特征: {', '.join([self._get_feature_label(f[0]) for f in sorted_features[:3]])}")

        # 获取 prompt 模板
        system_prompt = self.config.get("system_prompt", "")
        user_template = self.config.get("user_prompt_template", "")

        #  v7.118: 修复 KeyError - 使用 task_count_range 参数
        task_min = task_count_range[0] if task_count_range else 5
        task_max = task_count_range[1] if task_count_range else 7

        # 🆕 v7.999.4→v8.0 P0-T3: 选择并注入Few-shot示例（tags_matrix智能匹配）
        if few_shot_examples and structured_data:
            project_type = structured_data.get('project_type', '')
            project_features = structured_data.get('project_features', {})
            detected_modes = structured_data.get('detected_design_modes', [])
            
            selected_example_name = self._select_best_few_shot(project_type, project_features, detected_modes, user_input)
            
            if selected_example_name and selected_example_name in few_shot_examples:
                example_data = few_shot_examples[selected_example_name]
                # 🆕 v7.999.4: YAML结构修正 - ideal_tasks在example键下
                example_content = example_data.get('example', {})
                ideal_tasks = example_content.get('ideal_tasks', [])
                example_name = example_content.get('project_info', {}).get('name', '未命名')
                example_content.get('feature_vector', {}).get('commercial', 0) + example_content.get('feature_vector', {}).get('cultural', 0)
                
                if ideal_tasks:
                    # 🆕 v7.999.5: 增强Few-shot展示，明确说明任务数量差异
                    few_shot_content = "\n\n## 📚 参考案例（Few-shot示例 - 仅用于展示任务格式和粒度规范）\n\n"
                    few_shot_content += f"**示例案例**: {example_name}\n"
                    few_shot_content += f"**示例任务数**: {len(ideal_tasks)}个\n"
                    few_shot_content += f"**你的目标任务数**: {task_min}-{task_max}个 （⚠️ 与示例不同，请严格遵守）\n\n"
                    
                    few_shot_content += "**成功案例的任务拆解方式（参考格式、粒度、语言风格）**:\n\n"
                    
                    # v8.1: 展示更多任务以提供充分的粒度参考（从15提升到25）
                    display_count = min(25, len(ideal_tasks))
                    for i, task in enumerate(ideal_tasks[:display_count], 1):
                        task_title = task.get('title', '未命名')
                        few_shot_content += f"{i}. {task_title}\n"
                    
                    if len(ideal_tasks) > display_count:
                        few_shot_content += f"\n... 等共{len(ideal_tasks)}个任务\n"
                    
                    # 🆕 v7.999.5: 强化警告信息
                    few_shot_content += "\n🚨 **关键要求（最高优先级）**:\n"
                    few_shot_content += f"1. **任务数量**: 你必须生成 {task_min}-{task_max} 个任务（而非示例的{len(ideal_tasks)}个）\n"
                    few_shot_content += "2. **任务粒度**: 参考示例的拆解粒度（每个对象独立成任务，详细列举调研维度）\n"
                    few_shot_content += "3. **独立拆解**: 严禁使用'多个XX'、'XX等'、'专家们'等混合表述\n"
                    few_shot_content += "4. **项目视角**: 所有任务应紧密围绕项目核心领域和诉求表达\n"
                    few_shot_content += "5. **质量标准**: 参考示例的标题格式、描述深度、调研维度数量（3-5个）\n\n"
                    
                    logger.info(f"✅ [Few-shot v7.999.5] 已注入示例: {selected_example_name} ({len(ideal_tasks)}任务) - 目标: {task_min}-{task_max}任务")

        # v7.960: 注入特征向量和动态指导到 user_prompt
        # 首先填充模板中的占位符
        user_prompt = user_template.format(
            user_input=user_input,
            structured_data_summary=structured_summary,
            task_count_min=task_min,
            task_count_max=task_max,
        )

        # 阶段1增强(深化版): 从 mode_ability_activation.yaml + ability_core_essentials.yaml 注入能力激活约束
        # 不仅注入"必须为哪些能力生成任务"，还注入每个能力的判断标准/常见误区/最高形态
        try:
            import os as _os
            _cfg_dir = _os.path.join(
                _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                "config"
            )
            _act_path = _os.path.join(_cfg_dir, "mode_ability_activation.yaml")
            _ess_path = _os.path.join(_cfg_dir, "ability_core_essentials.yaml")
            if _os.path.exists(_act_path):
                import yaml as _yaml
                with open(_act_path, encoding="utf-8") as _f:
                    _act_cfg = _yaml.safe_load(_f)
                # 加载能力5层模型精华（判断标准/常见误区/最高形态）
                _ess_cfg = {}
                if _os.path.exists(_ess_path):
                    with open(_ess_path, encoding="utf-8") as _ef:
                        _ess_cfg = _yaml.safe_load(_ef) or {}
                _detected = structured_data.get("detected_design_modes", []) if structured_data else []
                _ability_sections = []
                for _m in _detected:
                    _mid = _m.get("mode", "")
                    _mconf = _m.get("confidence", 0.0)
                    if _mconf < 0.5 or _mid not in _act_cfg:
                        continue
                    _entry = _act_cfg[_mid]
                    _primary = _entry.get("primary_abilities", [])
                    if not _primary:
                        continue
                    _lines = []
                    for ab in _primary:
                        _ab_id = ab['id']
                        _focus = ab.get('focus', '')
                        _ess = _ess_cfg.get(_ab_id, {})
                        _criteria = _ess.get('judgment_criteria', [])
                        _mistakes = _ess.get('common_mistakes', [])
                        _highest = _ess.get('highest_form', '')
                        _ab_line = f"  - {_ab_id}（{_focus}）"
                        if _criteria:
                            # 注入前2条判断标准（避免prompt过长）
                            _ab_line += f"\n    ✓ 判断标准: {_criteria[0]}"
                            if len(_criteria) > 1:
                                _ab_line += f" / {_criteria[1]}"
                        if _mistakes:
                            # 注入前2条常见误区
                            _ab_line += f"\n    ✗ 避免: {_mistakes[0]}"
                            if len(_mistakes) > 1:
                                _ab_line += f" / {_mistakes[1]}"
                        if _highest:
                            _ab_line += f"\n    ★ 最高形态: {_highest}"
                        _lines.append(_ab_line)
                    _ability_sections.append(
                        f"[{_mid}] 必须为以下能力各生成至少1个深度任务:\n" + "\n".join(_lines)
                    )
                if _ability_sections:
                    _ability_injection = (
                        "\n## 🎯 能力激活约束（来自 Mode×Ability 矩阵 + Ability Core 5层模型）\n"
                        + "\n".join(_ability_sections)
                        + "\n⚠️ 任务列表中必须体现上述每个能力的深度判断标准，不能合并为通用任务，不能重复常见误区\n"
                    )
                    user_prompt = _ability_injection + user_prompt
                    _ess_loaded = "含5层模型精华" if _ess_cfg else "仅能力ID"
                    logger.info(f"[能力激活约束] 已注入 {len(_ability_sections)} 个模式的能力矩阵（{_ess_loaded}）")
        except Exception as _e:
            logger.warning(f"[能力激活约束] 注入失败，已跳过: {_e}")

        # 🆕 v10.1: 基于通用框架信号（不硬编码）注入输出意图到 user_prompt
        try:
            _active_projections = structured_data.get("_v10_active_projections", []) if structured_data else []
            _identity_modes = structured_data.get("_v10_identity_modes", []) if structured_data else []
            _framework_signals = structured_data.get("_v10_framework_signals", {}) if structured_data else {}

            _intent_sections = []

            # ── A. 框架信号驱动的动态约束（替代硬编码交付模板）──
            if _framework_signals:
                _scope = _framework_signals.get("scope", {})
                _constraints = _framework_signals.get("constraints", [])
                _dimensions = _framework_signals.get("mandatory_dimensions", [])
                _calibration = _framework_signals.get("output_calibration", {})
                _audience = _framework_signals.get("audience_needs", [])

                _signal_lines = []
                _signal_lines.append("## 📐 输出框架信号（v10.1 通用检测，非硬编码）")
                _signal_lines.append("")

                # 范围信号
                _obj_count = _scope.get("object_count", "unknown")
                if _obj_count != "unknown":
                    _scope_labels = {
                        "single_space": "单一空间",
                        "single_building": "单体建筑",
                        "district_cluster": "片区/聚落",
                        "theoretical": "理论/方法论",
                    }
                    _signal_lines.append(f"**项目范围**: {_scope_labels.get(_obj_count, _obj_count)}")
                _markers = _scope.get("scale_markers", [])
                if _markers:
                    _marker_strs = [f"{m.get('type','?')}={m.get('value','?')}" for m in _markers[:4]]
                    _signal_lines.append(f"**量化标记**: {', '.join(_marker_strs)}")
                _temporal = _scope.get("temporal_hint")
                if _temporal and _temporal != "permanent":
                    _signal_lines.append(f"**时间属性**: {_temporal}")

                # 约束信号
                if _constraints:
                    _c_labels = {
                        "budget": "预算约束",
                        "regulatory": "法规/安全",
                        "extreme_environment": "极端环境",
                        "special_population": "特殊人群",
                        "time_pressure": "时间紧迫",
                        "extreme_compact": "极限空间",
                        "stakeholder_conflict": "多方冲突",
                    }
                    _c_strs = [_c_labels.get(c.get("type", ""), c.get("type", "?")) for c in _constraints]
                    _signal_lines.append(f"**核心约束**: {', '.join(_c_strs)}")
                    _signal_lines.append("→ 任务列表必须直接回应上述每个约束（各至少1个专属任务或维度）")

                # 特殊领域信号
                if _dimensions:
                    _signal_lines.append(f"**必须覆盖的专业领域**: {', '.join(_dimensions)}")
                    _signal_lines.append("→ 每个领域必须有独立任务或嵌入维度，不可遗漏或合并为通用描述")

                # 输出校准
                _depth = _calibration.get("depth_hint", "standard")
                if _depth != "standard":
                    _depth_labels = {
                        "exhaustive": "全面详尽",
                        "strategic": "策略概要",
                        "compressed": "精简摘要",
                    }
                    _signal_lines.append(f"**输出深度**: {_depth_labels.get(_depth, _depth)}")
                if _calibration.get("quantitative_expectation"):
                    _signal_lines.append("**量化期待**: 需包含数据测算/预算估算/指标对比")
                if _calibration.get("visual_expectation"):
                    _signal_lines.append("**视觉期待**: 需含参考图/效果示意/案例图片")

                # 受众需求
                if _audience:
                    _audience_strs = [a.get("audience_label", a.get("projection_id", "")) for a in _audience]
                    _signal_lines.append(f"**目标受众**: {', '.join(_audience_strs)}")
                    _signal_lines.append("→ 任务拆解粒度和专业深度需匹配受众期待")

                _signal_lines.append("")
                _signal_lines.append("⚠️ 以上信号来自用户原始输入的自动检测。")
                _signal_lines.append("请基于这些信号动态推理合适的任务框架结构，而非套用固定模板。")

                _intent_sections.append("\n".join(_signal_lines))
                logger.info(f"📐 [v10.1] 已注入框架信号: "
                            f"scope={_obj_count}, "
                            f"constraints={len(_constraints)}, "
                            f"dimensions={len(_dimensions)}")

            elif _active_projections:
                # 降级: 如果没有框架信号但有投射类型，给出简单提示
                _proj_labels = {
                    "design_professional": "设计专业报告",
                    "construction_execution": "施工落地执行",
                    "investor_operator": "投资运营分析",
                    "government_policy": "政策汇报方案",
                    "aesthetic_critique": "美学评论与传播",
                }
                _proj_strs = [_proj_labels.get(p, p) for p in _active_projections if isinstance(p, str)]
                if _proj_strs:
                    _intent_sections.append(
                        "## 📐 输出方向提示\n"
                        f"本项目需要覆盖以下视角: {', '.join(_proj_strs)}\n"
                        "请确保任务拆解的深度和粒度能支撑上述各视角的输出需求。"
                    )
                    logger.info(f"📐 [v10.1 降级] 注入 {len(_proj_strs)} 个投射方向提示")

            # ── B. 身份模式注入 ──
            if _identity_modes:
                _mode_labels = []
                for _im in _identity_modes:
                    _label = _im.get("label", _im.get("mode_id", ""))
                    # v10.1 fix: 上游产出 trigger_scenes (List)，兼容旧键 trigger_scenario (str)
                    _trigger_raw = _im.get("trigger_scenes", _im.get("trigger_scenario", ""))
                    _trigger = ", ".join(_trigger_raw) if isinstance(_trigger_raw, list) else str(_trigger_raw)
                    if _label:
                        _mode_labels.append(f"「{_label}」（场景: {_trigger}）" if _trigger else f"「{_label}」")
                if _mode_labels:
                    _intent_sections.append(
                        "## 🎭 身份模式分析要求（v10.0 输出意图检测）\n"
                        f"检测到的使用者身份切换模式: {', '.join(_mode_labels)}\n"
                        "- 每个空间设计任务必须分析: 同一空间如何适配不同身份模式的使用需求\n"
                        "- 不是「为不同人群设计不同空间」, 而是「同一个人在不同身份下对同一空间的不同期待」\n"
                        "- 关注身份切换的触发条件和空间如何无缝支持这种切换"
                    )
                    logger.info(f"🎭 [v10.0] 已注入 {len(_mode_labels)} 个身份模式分析维度")

            if _intent_sections:
                user_prompt += "\n" + "\n\n".join(_intent_sections) + "\n"

        except Exception as _e:
            logger.warning(f"[v10.1 输出意图注入] 失败，已跳过: {_e}")

        # v7.999.4: 注入Few-shot示例（在特征向量之前）
        if few_shot_content:
            user_prompt += few_shot_content
        
        # 然后在结构化摘要后注入特征向量和动态指导
        if feature_visualization:
            user_prompt += f"\n{feature_visualization}{dynamic_guidance}\n"
            logger.info("✅ [v7.960] 特征向量已注入prompt，动态拆解策略已激活")

        return f"{system_prompt}\n\n{user_prompt}"

    def parse_response(self, response: str) -> List[Dict[str, Any]]:
        """
        解析 LLM 响应，提取任务列表

        Args:
            response: LLM 返回的原始响应

        Returns:
            任务列表，每个任务包含 id, title, description, source_keywords, task_type, priority
        """
        try:
            #  P1: 增强 JSON 提取能力 - 添加 debug 日志
            logger.debug(f"[CoreTaskDecomposer] LLM 原始响应 (前500字符): {response[:500]}")

            response_text = response.strip()

            # 策略 1: 移除 markdown 代码块标记
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            elif response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            response_text = response_text.strip()

            # 策略 2: 如果还不是 JSON，尝试提取 { } 之间的内容
            if not response_text.startswith("{"):
                # 查找第一个 {
                start_idx = response_text.find("{")
                if start_idx != -1:
                    # 查找匹配的 }（平衡括号）
                    brace_count = 0
                    end_idx = -1
                    for i in range(start_idx, len(response_text)):
                        if response_text[i] == "{":
                            brace_count += 1
                        elif response_text[i] == "}":
                            brace_count -= 1
                            if brace_count == 0:
                                end_idx = i + 1
                                break

                    if end_idx != -1:
                        response_text = response_text[start_idx:end_idx]
                        logger.info(f" [CoreTaskDecomposer] 使用括号平衡提取 JSON (长度: {len(response_text)})")

            # 策略 3: 尝试移除 JSON 中的注释（// 或 /* */）
            import re

            response_text = re.sub(r"//.*?$", "", response_text, flags=re.MULTILINE)  # 移除单行注释
            response_text = re.sub(r"/\*.*?\*/", "", response_text, flags=re.DOTALL)  # 移除多行注释

            # 解析 JSON
            data = json.loads(response_text)

            # 提取任务列表
            tasks = data.get("tasks", [])

            # v8.000: 任务质量检查日志
            if tasks:
                logger.info(f"[TaskQualityCheck] 开始检查 {len(tasks)} 个任务的质量...")
                quality_issues = []
                
                for idx, task in enumerate(tasks, 1):
                    task_title = task.get('title', '')
                    
                    # 检查1: 标题长度（理想15-30字）
                    title_len = len(task_title)
                    if title_len > 35:
                        quality_issues.append(f"⚠️  任务#{idx} 标题过长({title_len}字): {task_title[:40]}...")
                        # 🔧 P2-B: 自动截断过长标题（>40字时截断为30字）
                        if title_len > 40:
                            task['title'] = task_title[:30] + '...'
                            quality_issues.append(f"   → 已自动截断为: {task['title']}")
                    
                    # 检查2: 多主体问题
                    multi_subject_indicators = ['与', '及', '和']
                    subject_count = sum(task_title.count(ind) for ind in multi_subject_indicators)
                    if subject_count >= 2:
                        quality_issues.append(f"⚠️  任务#{idx} 包含多个主体: {task_title}")
                    
                    # 检查3: 宏大词汇
                    broad_keywords = ['振兴', '战略', '智慧', '逻辑', '体系', '系统']
                    matched_keywords = [kw for kw in broad_keywords if kw in task_title]
                    if len(matched_keywords) >= 2:
                        quality_issues.append(f"⚠️  任务#{idx} 可能过于宏观(含{matched_keywords}): {task_title}")
                
                # 🔧 P2-B: 检查4 — 跨类别主体重复检测（同一建筑师/案例出现在3+个类别）
                subject_category_map: dict[str, set[str]] = {}
                known_architects = ['安藤忠雄', '隈研吾', '王澍', '刘家琨', '贝聿铭', '扎哈',
                                   '妹岛和世', '坂茂', '伊东丰雄', '矶崎新', '丹下健三',
                                   '柯布西耶', '密斯', '赖特', '路易斯康', '阿尔瓦阿尔托',
                                   '伦佐皮亚诺', '诺曼福斯特', '雷姆库哈斯', '彼得卒姆托']
                for task in tasks:
                    title = task.get('title', '')
                    cat = task.get('category', '')
                    for architect in known_architects:
                        if architect in title:
                            if architect not in subject_category_map:
                                subject_category_map[architect] = set()
                            subject_category_map[architect].add(cat)
                
                for subject, cats in subject_category_map.items():
                    if len(cats) >= 3:
                        quality_issues.append(
                            f"⚠️  '{subject}' 散落在{len(cats)}个类别中({', '.join(list(cats)[:3])})，建议集中归属"
                        )
                
                # 输出质量检查结果
                if quality_issues:
                    logger.warning(f"[TaskQualityCheck] 发现 {len(quality_issues)} 个潜在质量问题:")
                    for issue in quality_issues[:10]:  # 最多显示10个
                        logger.warning(f"  {issue}")
                    if len(quality_issues) > 10:
                        logger.warning(f"  ... 还有 {len(quality_issues) - 10} 个问题未显示")
                else:
                    logger.info("[TaskQualityCheck] ✅ 所有任务质量检查通过")

            # 如果 tasks 为空，尝试从其他可能的字段提取
            if not tasks:
                # 可能是直接返回了任务数组
                if isinstance(data, list):
                    tasks = data
                # 或者任务在其他字段中
                elif "task_list" in data:
                    tasks = data["task_list"]
                elif "core_tasks" in data:
                    tasks = data["core_tasks"]

            # 验证和规范化任务
            validated_tasks = []
            for i, task in enumerate(tasks):
                validated_task = {
                    "id": task.get("id", f"task_{i + 1}"),
                    "title": task.get("title", "未命名任务"),
                    "description": task.get("description", ""),
                    "source_keywords": task.get("source_keywords", []),
                    "task_type": task.get("task_type", "research"),
                    "priority": task.get("priority", "medium"),
                    #  v7.106: 添加依赖和执行顺序
                    "dependencies": task.get("dependencies", []),
                    "execution_order": task.get("execution_order", i + 1),
                    #  v7.109+: 添加搜索和概念图配置
                    "support_search": task.get("support_search", False),
                    "needs_concept_image": task.get("needs_concept_image", False),
                    "concept_image_count": task.get("concept_image_count", 1 if task.get("needs_concept_image") else 0),
                    # P2-D1: 维度字段注入（3-5个分析维度）
                    "dimensions": task.get("dimensions", []),
                    # 🔧 P0修复: 保留category字段（之前遗漏导致分组全部塌缩为"基础调研"）
                    "category": task.get("category", ""),
                    # v9.0: 能力标签 — 由 Phase 2 后置处理从 category_info.ability_core 自动填充
                    "ability_tags": task.get("ability_tags", []),
                }
                validated_tasks.append(validated_task)

                #  v7.119: 添加概念图相关日志
                if validated_task["needs_concept_image"]:
                    logger.info(f" [任务 {validated_task['id']}] 需要生成概念图")
                    logger.info(f"   数量: {validated_task['concept_image_count']} 张")
                    logger.info(f"   任务标题: {validated_task['title']}")
                if validated_task["support_search"]:
                    logger.debug(f" [任务 {validated_task['id']}] 支持搜索功能")

            logger.info(f" [CoreTaskDecomposer] 成功解析 {len(validated_tasks)} 个任务")

            # 统计概念图相关任务
            tasks_with_images = [t for t in validated_tasks if t.get("needs_concept_image")]
            total_image_count = sum(t.get("concept_image_count", 0) for t in validated_tasks)
            if tasks_with_images:
                logger.info(f" [概念图统计] {len(tasks_with_images)} 个任务需要概念图，共 {total_image_count} 张")
                for t in tasks_with_images:
                    logger.debug(f"  • {t['title']}: {t.get('concept_image_count', 0)} 张")

            return validated_tasks

        except json.JSONDecodeError as e:
            logger.error(f" [CoreTaskDecomposer] JSON 解析失败: {e}")
            logger.debug(f"[CoreTaskDecomposer] 解析失败的文本: {response_text[:200]}")
            return self._fallback_decompose(response)
        except Exception as e:
            logger.error(f" [CoreTaskDecomposer] 响应解析异常: {e}")
            return []

    def _fallback_decompose(self, text: str) -> List[Dict[str, Any]]:
        """
        回退策略：当 LLM 响应格式不正确时，使用简单的规则提取

        Args:
            text: 原始文本

        Returns:
            简化的任务列表
        """
        logger.warning("️ [CoreTaskDecomposer] 使用回退策略提取任务")

        # 尝试从文本中提取编号列表
        lines = text.split("\n")
        tasks = []

        for i, line in enumerate(lines):
            line = line.strip()
            # 匹配 "1." "1、" "1)" "- " 等格式
            if line and (
                (line[0].isdigit() and len(line) > 2 and line[1] in ".、)")
                or line.startswith("- ")
                or line.startswith("• ")
            ):
                # 提取任务内容
                content = line.lstrip("0123456789.、)- •").strip()
                if content and len(content) > 5:
                    #  v7.109+: 简单规则判断是否需要搜索和概念图
                    is_research_task = any(kw in content for kw in ["研究", "调研", "分析", "对标", "案例"])
                    is_design_task = any(kw in content for kw in ["设计", "方案", "规划", "框架"])

                    tasks.append(
                        {
                            "id": f"task_{len(tasks) + 1}",
                            "title": content[:50] if len(content) > 50 else content,
                            "description": content,
                            "source_keywords": [],
                            "task_type": "research" if is_research_task else "design" if is_design_task else "analysis",
                            "priority": "medium",
                            "dependencies": [],
                            "execution_order": len(tasks) + 1,
                            #  v7.109+: 默认配置
                            "support_search": is_research_task,  # 研究类任务默认需要搜索
                            "needs_concept_image": is_design_task,  # 设计类任务默认需要概念图
                            "concept_image_count": 1 if is_design_task else 0,
                        }
                    )

        # 限制任务数量
        return tasks[:7] if tasks else []

    async def _infer_task_metadata_async(
        self, tasks: List[Dict[str, Any]], user_input: str = "", structured_data: Optional[Dict[str, Any]] = None,
        use_batch_mode: bool = True
    ) -> None:
        """
        异步推断任务元数据（动机类型、推理依据等）

        v7.106: 为每个任务添加：
        - motivation_type: 动机类型ID（如'cultural'）
        - motivation_label: 动机类型中文标签（如'文化认同'）
        - ai_reasoning: LLM推理依据
        - confidence_score: 置信度分数
        
        🆕 P2-3: 批量推断模式（use_batch_mode=True）
        - 将多个任务合并在一次LLM调用中推断
        - 性能提升：44个任务从3.07s降至~0.5-1s
        - 批次大小：每批最多20个任务

        Args:
            tasks: 任务列表
            user_input: 用户原始输入
            structured_data: 需求分析阶段产出的结构化数据
            use_batch_mode: 是否使用批量推断模式（默认True）
        """
        if not tasks:
            return

        from ..services.motivation_engine import get_motivation_engine

        engine = get_motivation_engine()
        logger.info(f"🔄 [v7.106] 使用动机识别引擎处理 {len(tasks)} 个任务 (批量模式: {use_batch_mode})")

        import asyncio
        import time

        start_time = time.time()
        
        # 🆕 P2-3: 批量推断模式
        if use_batch_mode and len(tasks) > 5:
            try:
                await self._infer_task_metadata_batch(tasks, user_input, structured_data, engine)
                elapsed_time = time.time() - start_time
                logger.info(f"✅ [P2-3批量模式] {len(tasks)} 个任务推断完成，耗时 {elapsed_time:.2f}s")
                return
            except Exception as e:
                logger.warning(f"⚠️ [P2-3批量模式] 失败: {e}，回退到单任务模式")
                # 如果批量模式失败，fallback到单任务模式

        # 原有单任务并行模式（v7.122）
        # 创建所有推断协程
        async def infer_single_task(task):
            """单个任务的推断包装函数"""
            try:
                # 执行异步推断
                result = await engine.infer(task=task, user_input=user_input, structured_data=structured_data)

                # 返回成功结果
                return {"task": task, "success": True, "result": result}

            except Exception as e:
                # 返回失败结果
                return {"task": task, "success": False, "error": e}

        # 并行执行所有任务
        inference_coroutines = [infer_single_task(task) for task in tasks]
        results = await asyncio.gather(*inference_coroutines)

        # 处理结果并更新任务
        for result_data in results:
            task = result_data["task"]

            if result_data["success"]:
                result = result_data["result"]
                task["motivation_type"] = result.primary
                task["motivation_label"] = result.primary_label
                task["ai_reasoning"] = result.reasoning
                task["confidence_score"] = result.confidence
                
                # 🆕 P1-2: 存储多标签加权信息
                if result.secondary_weighted:
                    task["motivation_secondary"] = result.secondary_weighted
                    # 格式化日志输出：显示所有标签+权重
                    weights_str = f"{result.primary}({result.scores.get(result.primary, 0):.2f})"
                    if result.secondary_weighted:
                        sec_str = ", ".join([f"{k}({v:.2f})" for k, v in result.secondary_weighted.items()])
                        weights_str += f" + {sec_str}"
                    logger.info(f"    {task['title'][:30]}: {weights_str}")
                else:
                    # 单标签模式（兼容）
                    logger.info(f"    {task['title'][:30]}: {result.primary_label} ({result.confidence:.2f})")
            else:
                error = result_data["error"]
                logger.warning(f"⚠️ 任务 '{task.get('title', 'unknown')}' 动机推断失败: {error}")
                # 降级到默认
                task["motivation_type"] = "mixed"
                task["motivation_label"] = "综合"
                task["ai_reasoning"] = "推断失败，使用默认类型"
                task["confidence_score"] = 0.3

        elapsed_time = time.time() - start_time
        logger.info(f"✅ [单任务并行模式] {len(tasks)} 个任务推断完成，耗时 {elapsed_time:.2f}s")
    
    async def _infer_task_metadata_batch(
        self, tasks: List[Dict[str, Any]], user_input: str, 
        structured_data: Optional[Dict[str, Any]], engine
    ) -> None:
        """
        🆕 P2-3: 批量推断任务元数据
        
        将多个任务合并在一次LLM调用中进行推断，大幅减少API调用次数。
        
        Args:
            tasks: 任务列表
            user_input: 用户原始输入
            structured_data: 结构化数据
            engine: MotivationEngine实例
        """
        from langchain_core.messages import HumanMessage
        from ..services.llm_factory import LLMFactory
        import json
        
        BATCH_SIZE = 20  # 每批最多20个任务
        batches = [tasks[i:i+BATCH_SIZE] for i in range(0, len(tasks), BATCH_SIZE)]
        
        logger.info(f"  [P2-3] 将{len(tasks)}个任务分为{len(batches)}批处理（每批≤{BATCH_SIZE}个）")
        
        # 获取动机类型列表
        from ..services.motivation_engine import MotivationTypeRegistry
        registry = MotivationTypeRegistry()
        all_types = registry.get_all_types()
        type_descriptions = []
        for mtype in all_types:
            if mtype.id != "mixed":
                type_descriptions.append(f"  {mtype.id} ({mtype.label_zh}): {mtype.description}")
        types_text = "\n".join(type_descriptions)
        
        llm = LLMFactory.create_llm()
        
        for batch_idx, batch in enumerate(batches, 1):
            # 构建批量任务列表
            task_list_text = []
            for idx, task in enumerate(batch, 1):
                task_list_text.append(
                    f"{idx}. 标题: {task.get('title', '')}\n"
                    f"   描述: {task.get('description', '')[:150]}\n"
                    f"   关键词: {', '.join(task.get('source_keywords', [])[:5])}"
                )
            
            batch_prompt = f"""你是资深设计项目顾问，需要分析{len(batch)}个项目任务的核心动机类型。

【可选动机类型】
{types_text}

【项目背景】
{user_input[:500]}

【需分析的{len(batch)}个任务】
{chr(10).join(task_list_text)}

⚠️ **任务独立性原则**：
1. 每个任务分析其自身的动机，不要被项目整体描述干扰
2. 同一项目的不同任务可能有完全不同的动机类型
3. 根据任务的动作词和对象判断（参考P1-2多标签加权说明）

请为每个任务输出：
1. primary: 主要动机类型
2. primary_weight: 主要权重（0.4-0.8）
3. secondary_weighted: 次要动机类型及权重（Dict格式，权重和≈1.0）
4. confidence: 置信度（0-1）
5. reasoning: 简短推理（20字以内）

返回纯JSON数组（不要markdown代码块）：
[
  {{"task_index": 1, "primary": "cultural", "primary_weight": 0.6, "secondary_weighted": {{"commercial": 0.3, "functional": 0.1}}, "confidence": 0.85, "reasoning": "文化调研为主"}},
  {{"task_index": 2, "primary": "aesthetic", "primary_weight": 0.7, "secondary_weighted": {{"professional": 0.3}}, "confidence": 0.9, "reasoning": "设计案例研究"}}
]"""
            
            try:
                response = await llm.ainvoke([HumanMessage(content=batch_prompt)])
                response_text = response.content if hasattr(response, "content") else str(response)
                
                # 解析JSON响应
                import re
                json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
                if not json_match:
                    raise ValueError("未找到JSON数组")
                
                results = json.loads(json_match.group())
                
                # 将结果映射到任务
                for result in results:
                    task_idx = result.get("task_index", 0) - 1
                    if 0 <= task_idx < len(batch):
                        task = batch[task_idx]
                        primary_id = result.get("primary", "mixed")
                        primary_type = registry.get_type(primary_id)
                        
                        if not primary_type:
                            primary_id = "mixed"
                            primary_type = registry.get_type("mixed")
                        
                        primary_weight = result.get("primary_weight", 0.5)
                        secondary_weighted = result.get("secondary_weighted", {})
                        confidence = result.get("confidence", 0.5)
                        reasoning = result.get("reasoning", "批量推断")
                        
                        # 存储到任务
                        task["motivation_type"] = primary_id
                        task["motivation_label"] = primary_type.label_zh
                        task["ai_reasoning"] = reasoning
                        task["confidence_score"] = confidence
                        
                        if secondary_weighted:
                            task["motivation_secondary"] = secondary_weighted
                            weights_str = f"{primary_id}({primary_weight:.2f})"
                            sec_str = ", ".join([f"{k}({v:.2f})" for k, v in secondary_weighted.items()])
                            weights_str += f" + {sec_str}"
                            logger.info(f"    [{batch_idx}/{len(batches)}] {task['title'][:25]}: {weights_str}")
                        else:
                            logger.info(f"    [{batch_idx}/{len(batches)}] {task['title'][:25]}: {primary_type.label_zh} ({confidence:.2f})")
                
                logger.info(f"  ✅ 批次{batch_idx}/{len(batches)}完成")
                
            except Exception as e:
                logger.warning(f"  ⚠️ 批次{batch_idx}/{len(batches)}失败: {e}，任务使用默认值")
                # 批次失败时，给该批所有任务设置默认值
                for task in batch:
                    task["motivation_type"] = "mixed"
                    task["motivation_label"] = "综合"
                    task["ai_reasoning"] = f"批量推断失败: {str(e)[:50]}"
                    task["confidence_score"] = 0.3


def _validate_task_granularity(
    tasks: List[Dict[str, Any]], project_features: Optional[Dict[str, float]] = None,
    auto_fix: bool = True
) -> tuple[bool, List[str]]:
    """
     v7.970 → v9.1: 验证任务粒度是否符合质量标准 + 自动修正

    Args:
        tasks: 任务列表（⚠️ auto_fix=True 时会原地修改）
        project_features: 12维特征向量（可选，用于特征对齐验证）
        auto_fix: v9.1 G4 - 是否自动修正粒度问题（默认True）

    Returns:
        (is_valid, errors): 验证是否通过 + 错误/修正信息列表
    """
    errors = []
    fixes_applied = []

    # Rule 1: 检查混合对象（多个对象混在一起）
    mixed_keywords = ["等", "、", "多位", "专家们", "多个", "一系列"]
    tasks_to_add = []  # auto_fix: 拆分出的新任务
    tasks_to_remove_indices = []  # auto_fix: 需要移除的原始任务索引

    for idx, task in enumerate(tasks):
        title = task.get("title", "")
        description = task.get("description", "")
        combined_text = title + " " + description

        # 检测混合表述
        for keyword in mixed_keywords:
            if keyword in combined_text:
                # 排除合理的"、"用法（如罗列维度："建筑哲学、材料策略、空间理念"）
                if keyword == "、":
                    import re
                    dim_pattern = re.findall(r"[^，。：:]{2,12}、[^，。：:]{2,12}", combined_text)
                    if dim_pattern and len(dim_pattern) >= 2:
                        continue

                if auto_fix and keyword == "、":
                    # ⚠️ v9.1 G4: 自动拆分 - 按"、"分割为独立任务
                    import re
                    # 提取"X、Y、Z"模式中的各项
                    split_pattern = re.findall(r"([^，。：:\s]{2,20})[、]", combined_text)
                    last_item = re.findall(r"、([^，。：:\s]{2,20})", combined_text)
                    items = split_pattern + last_item
                    # 去重
                    seen = set()
                    unique_items = []
                    for item in items:
                        if item not in seen:
                            seen.add(item)
                            unique_items.append(item)

                    if len(unique_items) >= 2:
                        tasks_to_remove_indices.append(idx)
                        for sub_item in unique_items[:4]:  # 最多拆4个
                            new_task = {
                                **task,
                                "id": f"task_split_{idx}_{len(tasks_to_add) + 1}",
                                "title": f"{sub_item}深度调研",
                                "description": f"针对{sub_item}进行独立调研分析 (原任务: {title[:30]}...)",
                                "source": "auto_split_v9.1",
                            }
                            tasks_to_add.append(new_task)
                        fixes_applied.append(
                            f"🔧 [G4自动修正] 任务 '{title[:30]}...' 已拆分为 {len(unique_items[:4])} 个独立任务"
                        )
                        break
                else:
                    errors.append(f"❌ 任务 '{title[:30]}...' 混合多个对象（检测到'{keyword}'），违反粒度细分规则")
                    break

    # Rule 2: 检查调研维度明确性（research任务应有3-5个具体维度）
    research_tasks = [t for t in tasks if t.get("task_type") == "research"]
    for task in research_tasks:
        title = task.get("title", "")
        description = task.get("description", "")
        combined_text = title + " " + description

        # 统计"、"数量（代表维度分隔）- 需要至少2个（即3个维度）
        dimension_count = combined_text.count("、")
        if dimension_count < 2:
            if auto_fix:
                # ⚠️ v9.1 G4: 自动扩展描述维度
                # 根据任务标题推断缺失的调研维度
                default_dims = {
                    "调研": ["历史背景", "当前状况", "发展趋势", "典型案例", "关键数据"],
                    "搜索": ["定义范围", "核心要素", "对标案例", "适用条件"],
                    "分析": ["现状分析", "问题诊断", "影响因素", "改进方向"],
                    "研究": ["理论基础", "实践案例", "关键参数", "技术路径"],
                }
                # 匹配最佳维度模板
                matched_dims = None
                for verb, dims in default_dims.items():
                    if verb in title:
                        matched_dims = dims
                        break
                if matched_dims is None:
                    matched_dims = default_dims["调研"]

                # 追加维度到描述
                needed = 3 - dimension_count
                extra_dims = matched_dims[:needed]
                expanded_desc = description + f"（调研维度：{'、'.join(extra_dims)}）"
                task["description"] = expanded_desc
                fixes_applied.append(
                    f"🔧 [G4自动修正] 任务 '{title[:30]}...' 调研维度不足，已补充 {needed} 个维度"
                )
            else:
                errors.append(f"❌ 任务 '{title[:30]}...' 调研维度不明确（需罗列3-5个具体维度，当前仅{dimension_count+1}个）")

    # Rule 3: 检查设计类任务比例（深度调研阶段应<30%）
    design_verbs = ["设计", "制定", "规划", "提出", "构建", "建立"]
    design_tasks = [
        t for t in tasks if any(verb in t.get("title", "") or verb in t.get("description", "") for verb in design_verbs)
    ]

    design_ratio = len(design_tasks) / len(tasks) if tasks else 0
    if design_ratio > 0.3:
        errors.append(f"❌ 设计类任务比例过高 ({len(design_tasks)}/{len(tasks)} = {design_ratio:.1%})，深度调研阶段应<30%")

    # Rule 4: 检查动词规范（research任务建议用专业调研动词开头）
    research_verbs = ["搜索", "调研", "查找", "收集", "检索", "分析", "评估", "研究", "梳理", "对比"]
    verb_errors = []
    for task in research_tasks:
        title = task.get("title", "")
        if not any(title.startswith(verb) for verb in research_verbs):
            verb_errors.append(f"'{title[:30]}...'")

    if verb_errors:
        errors.append(f"❌ {len(verb_errors)}个任务未使用规范动词（建议以'搜索/调研/查找/收集/分析/评估/研究'开头）：{', '.join(verb_errors[:3])}")

    # ⚠️ v9.1 G4: 应用自动修正（原地修改 tasks 列表）
    if auto_fix and (tasks_to_add or tasks_to_remove_indices):
        # 倒序移除，避免索引偏移
        for idx in sorted(tasks_to_remove_indices, reverse=True):
            if idx < len(tasks):
                tasks.pop(idx)
        # 添加拆分后的新任务
        tasks.extend(tasks_to_add)
        # 重新编号
        for i, task in enumerate(tasks):
            task["execution_order"] = i + 1

    # 合并错误和修正信息
    all_messages = errors + fixes_applied

    if fixes_applied:
        logger.info(f"🔧 [v9.1 G4] 自动修正了 {len(fixes_applied)} 个粒度问题")
        for fix in fixes_applied:
            logger.info(f"  {fix}")

    # 返回验证结果
    is_valid = len(errors) == 0
    return is_valid, all_messages


def _validate_requirement_coverage(
    tasks: List[Dict[str, Any]], structured_data: Optional[Dict[str, Any]] = None
) -> tuple[bool, List[str]]:
    """
    ⚠️ v9.1 G2: 需求覆盖溯源验证
    
    检查生成的任务是否覆盖了 structured_data 中的关键需求维度。
    每个关键维度至少应被 ≥1 个任务覆盖。

    Args:
        tasks: 生成的任务列表
        structured_data: 需求分析阶段产出的结构化数据

    Returns:
        (all_covered, uncovered_dimensions): 是否全覆盖 + 未覆盖维度列表
    """
    if not structured_data or not tasks:
        return True, []

    uncovered = []

    # 聚合所有任务文本用于检索
    all_task_text = " ".join(
        (t.get("title", "") + " " + t.get("description", ""))
        for t in tasks
    ).lower()

    # 维度1: design_challenge（核心设计挑战）
    design_challenge = structured_data.get("design_challenge", "")
    if design_challenge and len(design_challenge) > 10:
        # 提取关键词（取前2个关键短语）
        challenge_keywords = [w.strip() for w in design_challenge.replace("，", " ").replace("、", " ").split() if len(w.strip()) >= 2][:5]
        if challenge_keywords and not any(kw.lower() in all_task_text for kw in challenge_keywords):
            uncovered.append(f"design_challenge: {design_challenge[:60]}...")

    # 维度2: character_narrative（核心人物画像）
    character_narrative = structured_data.get("character_narrative", "")
    if character_narrative and len(character_narrative) > 10:
        # 检查任务中是否有人物/用户/业主/使用者相关任务
        user_keywords = ["用户", "业主", "使用者", "居住者", "人群", "画像", "人物", "客群", "访客"]
        if isinstance(character_narrative, dict):
            # Pydantic 模型输出可能是 dict
            char_text = str(character_narrative)
        else:
            char_text = character_narrative
        has_user_task = any(kw in all_task_text for kw in user_keywords)
        if not has_user_task and len(char_text) > 20:
            uncovered.append("character_narrative: 未找到覆盖人物画像的任务")

    # 维度3: core_objectives（核心目标）
    core_objectives = structured_data.get("core_objectives", [])
    if core_objectives:
        for obj in core_objectives[:3]:
            obj_str = str(obj)[:80] if obj else ""
            if obj_str and len(obj_str) > 10:
                obj_keywords = [w.strip() for w in obj_str.replace("，", " ").replace("、", " ").split() if len(w.strip()) >= 2][:3]
                if obj_keywords and not any(kw.lower() in all_task_text for kw in obj_keywords):
                    uncovered.append(f"core_objective: {obj_str[:60]}...")

    # 维度4: physical_context（物理场景）
    physical_context = structured_data.get("physical_context", "")
    if physical_context and len(physical_context) > 10 and physical_context != "待明确":
        site_keywords = ["场地", "地块", "环境", "现场", "场所", "基地", "地形", "建筑", "空间"]
        if not any(kw in all_task_text for kw in site_keywords):
            uncovered.append("physical_context: 未找到覆盖场地/环境调研的任务")

    # 维度5: core_tensions（核心张力，v9.1新增字段）
    core_tensions = structured_data.get("core_tensions", [])
    if core_tensions:
        for tension in core_tensions[:2]:
            if isinstance(tension, dict):
                ta = tension.get("tension_a", "")
                tb = tension.get("tension_b", "")
                if ta and tb and not (ta.lower() in all_task_text or tb.lower() in all_task_text):
                    uncovered.append(f"core_tension: {ta} ↔ {tb} 未被任何任务覆盖")

    all_covered = len(uncovered) == 0
    return all_covered, uncovered


async def decompose_core_tasks(
    user_input: str, structured_data: Optional[Dict[str, Any]] = None, llm: Optional[Any] = None
) -> List[Dict[str, Any]]:
    """
    异步执行核心任务拆解（v7.110.0 智能化版本）

    Args:
        user_input: 用户原始输入
        structured_data: 需求分析阶段产出的结构化数据（可选）
        llm: LLM 实例（可选，如果不提供则使用默认 LLM）

    Returns:
        任务列表（3-12个，根据输入复杂度动态决定）
    """
    decomposer = CoreTaskDecomposer()

    #  v7.110.0: 智能分析输入复杂度，动态决定任务数量
    complexity_analysis = TaskComplexityAnalyzer.analyze(user_input, structured_data)
    recommended_min = complexity_analysis["recommended_min"]
    recommended_max = complexity_analysis["recommended_max"]
    complexity_score = complexity_analysis["complexity_score"]

    logger.info(f" [智能任务数量] 推荐范围: {recommended_min}-{recommended_max}个 (复杂度={complexity_score:.2f})")
    logger.info(f"   分析依据: {complexity_analysis['reasoning']}")

    # 构建 prompt（传入智能计算的任务数量）
    decomposer.build_prompt(user_input, structured_data, task_count_range=(recommended_min, recommended_max))

    # 如果没有提供 LLM，使用默认
    if llm is None:
        from ..services.llm_factory import LLMFactory

        llm = LLMFactory.create_llm()

    try:
        # 调用 LLM
        from langchain_core.messages import HumanMessage, SystemMessage

        system_prompt = decomposer.config.get("system_prompt", "")
        user_template = decomposer.config.get("user_prompt_template", "")

        # 构建结构化数据摘要
        structured_summary = ""
        if structured_data:
            summary_parts = []
            for key in ["project_task", "character_narrative", "physical_context", "project_type"]:
                if structured_data.get(key):
                    summary_parts.append(f"{key}: {structured_data[key]}")
            structured_summary = "\n".join(summary_parts) if summary_parts else "暂无"

        #  v7.117: 直接使用占位符传入任务数量（不再使用正则替换）
        user_prompt = user_template.format(
            user_input=user_input,
            structured_data_summary=structured_summary,
            task_count_min=recommended_min,
            task_count_max=recommended_max,
        )

        #  v7.117: 增强调试日志
        logger.info(f" [智能任务数量] 输入长度={len(user_input)}字符")
        logger.info(f" [智能任务数量] 复杂度分析: {complexity_analysis['reasoning']}")
        logger.info(f" [Prompt] 任务数量要求: {recommended_min}-{recommended_max}个")

        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]

        response = await llm.ainvoke(messages)
        response_text = response.content if hasattr(response, "content") else str(response)

        # 解析响应
        tasks = decomposer.parse_response(response_text)

        if not tasks:
            # 如果解析失败，使用简单回退
            logger.warning("️ LLM 任务拆解为空，使用回退策略")
            tasks = _simple_fallback_decompose(user_input, structured_data, complexity_analysis)
        else:
            #  v7.110.0: 智能截断 - 不超过推荐最大值
            if len(tasks) > recommended_max:
                logger.warning(f"️ LLM生成了{len(tasks)}个任务，超过推荐上限{recommended_max}，智能截断")
                # 优先保留 high priority 的任务
                high_priority_tasks = [t for t in tasks if t.get("priority") == "high"]
                other_tasks = [t for t in tasks if t.get("priority") != "high"]
                tasks = (high_priority_tasks + other_tasks)[:recommended_max]

            # 🆕 v7.999.9: 如果少于推荐最小值的85%，使用分批补充策略
            min_acceptable = int(recommended_min * 0.85)
            if len(tasks) < min_acceptable:
                shortage = recommended_min - len(tasks)
                logger.warning(f"⚠️ LLM生成了{len(tasks)}个任务，少于推荐最小值{recommended_min}的85%（缺少{shortage}个）")
                logger.warning("🔄 [v7.999.9] 启动分批补充机制...")
                
                try:
                    from langchain_core.messages import HumanMessage
                    
                    remaining_shortage = shortage
                    max_rounds = 3
                    batch_size = min(12, remaining_shortage)
                    
                    for round_num in range(1, max_rounds + 1):
                        if remaining_shortage <= 0:
                            break
                        
                        current_batch = min(batch_size, remaining_shortage)
                        existing_titles = chr(10).join([f"{i+1}. {t.get('title', '未命名')}" for i, t in enumerate(tasks)])
                        
                        retry_prompt = f"""你是设计项目任务拆解专家。请为以下项目补充生成{current_batch}个新任务。

项目信息：
{user_input[:800]}

已有{len(tasks)}个任务：
{existing_titles}

请补充{current_batch}个新任务，要求：
1. 不得与已有任务重复
2. 标题格式：动词 + 具体对象 + 3-5个调研维度
3. 任务类型：约70% research, 30% analysis
4. 包含项目具体信息（地点、功能、品牌等）

返回纯JSON：
{{"tasks": [{{"id": "task_N", "title": "搜索/调研 具体对象的 维度1、维度2", "description": "详细说明", "source_keywords": ["词1", "词2"], "task_type": "research", "priority": "high", "dependencies": [], "execution_order": N, "support_search": true}}]}}"""
                        
                        retry_response = await llm.ainvoke([HumanMessage(content=retry_prompt)])
                        retry_text = retry_response.content if hasattr(retry_response, "content") else str(retry_response)
                        
                        additional_tasks = decomposer.parse_response(retry_text)
                        if additional_tasks:
                            next_task_id = len(tasks) + 1
                            for i, task in enumerate(additional_tasks):
                                task['id'] = f"task_{next_task_id + i}"
                                task['execution_order'] = next_task_id + i
                            tasks.extend(additional_tasks)
                            remaining_shortage -= len(additional_tasks)
                            logger.info(f"✅ [补充第{round_num}轮] 成功+{len(additional_tasks)}个，当前{len(tasks)}个")
                        else:
                            logger.warning(f"⚠️ [补充第{round_num}轮] 解析失败，停止")
                            break
                    
                    logger.info(f"📊 分批补充完成，任务总数: {len(tasks)}个")
                except Exception as retry_error:
                    logger.error(f"❌ 补充任务生成失败: {retry_error}")
            elif len(tasks) < recommended_min:
                logger.info(f"ℹ️ 任务数{len(tasks)}略少于推荐{recommended_min}，在可接受范围内（≥85%）")

        #  v7.106: 使用动机识别引擎为任务添加motivation_label字段
        if tasks:
            await decomposer._infer_task_metadata_async(tasks, user_input, structured_data)

        #  v7.970: 任务粒度质量验证
        if tasks:
            # 提取project_features（如果available）
            project_features = structured_data.get("project_features") if structured_data else None

            # 执行验证
            is_valid, validation_errors = _validate_task_granularity(tasks, project_features)

            if not is_valid:
                logger.warning(f"⚠️ [v7.970 粒度验证] 任务列表存在{len(validation_errors)}个质量问题：")
                for error in validation_errors:
                    logger.warning(f"  {error}")
                logger.warning(
                    "💡 建议：重新审视任务拆解，确保每个关键对象独立成任务，明确罗列调研维度（3-5个），"
                    "优先使用'搜索/调研'类任务"
                )
            else:
                logger.info("✅ [v7.970 粒度验证] 任务列表质量检查通过")

        # ⚠️ v9.1 G2: 需求覆盖溯源验证
        if tasks and structured_data:
            all_covered, uncovered_dims = _validate_requirement_coverage(tasks, structured_data)
            if not all_covered:
                logger.warning(f"⚠️ [v9.1 G2 覆盖验证] {len(uncovered_dims)}个需求维度未被任务覆盖：")
                for dim in uncovered_dims:
                    logger.warning(f"  ❌ {dim}")
                logger.warning("💡 建议：在 project_director 阶段补充遗漏任务")
            else:
                logger.info("✅ [v9.1 G2 覆盖验证] 所有关键需求维度已被任务覆盖")

        logger.info(f" [任务拆解完成] 最终生成{len(tasks)}个任务")
        return tasks

    except Exception as e:
        logger.error(f" [decompose_core_tasks] LLM 调用失败: {e}")
        # 回退到简单拆解
        return _simple_fallback_decompose(user_input, structured_data, complexity_analysis)


def _simple_fallback_decompose(
    user_input: str,
    structured_data: Optional[Dict[str, Any]] = None,
    complexity_analysis: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    增强版回退拆解策略（v7.110.0 智能化版本）

    当 LLM 调用失败时，基于结构化数据的多维度信息生成高质量任务列表。
    不再硬编码5-7个，而是根据复杂度分析动态调整任务数量。

    参考：校准问卷的智能补齐机制（questionnaire_optimization_summary.md）

    Args:
        user_input: 用户原始输入
        structured_data: 需求分析产出的结构化数据（包含 design_challenge, character_narrative 等）
        complexity_analysis: 复杂度分析结果（可选）

    Returns:
        任务列表（3-12个，根据复杂度动态决定）
    """

    tasks = []
    logger.info(" [Fallback] 使用增强版回退策略，基于结构化数据生成任务")

    #  v7.110.0: 获取智能推荐的任务数量范围
    if complexity_analysis is None:
        complexity_analysis = TaskComplexityAnalyzer.analyze(user_input, structured_data)

    recommended_min = complexity_analysis["recommended_min"]
    recommended_max = complexity_analysis["recommended_max"]
    logger.info(f" [Fallback智能] 目标任务数: {recommended_min}-{recommended_max}个")

    # 从结构化数据中提取关键信息
    design_challenge = ""
    project_type = ""
    if structured_data:
        design_challenge = structured_data.get("design_challenge", "")
        structured_data.get("character_narrative", "")
        project_type = structured_data.get("project_type", "")
        logger.info(f" [Fallback] 提取到结构化数据: design_challenge={bool(design_challenge)}, project_type={project_type}")

    # ==========================================================================
    # 1. 提取核心张力任务（优先级最高）
    # ==========================================================================
    tension_a = ""
    tension_b = ""
    if design_challenge:
        # 模式1: "A"...与..."B" 格式（中文引号）
        match = re.search(r'"([^"]{2,30})"[^"]{0,50}与[^"]{0,50}"([^"]{2,30})"', design_challenge)
        if match:
            tension_a = match.group(1).strip()
            tension_b = match.group(2).strip()
            logger.info(f' [Fallback] 提取核心张力: "{tension_a}" vs "{tension_b}"')
            tasks.append(
                {
                    "id": f"task_{len(tasks) + 1}",
                    "title": f"{tension_a}与{tension_b}的平衡策略研究",
                    "description": f"研究如何在设计中平衡{tension_a}和{tension_b}的需求，找到最佳解决方案",
                    "source_keywords": [tension_a, tension_b],
                    "task_type": "research",
                    "priority": "high",
                    "dependencies": [],
                    "execution_order": len(tasks) + 1,
                }
            )
        else:
            # 模式2: A vs B 或 A与其对B 格式
            match = re.search(r"(.{5,30}?)[的需求]*(?:vs|与其对)(.{5,30}?)[的需求]*", design_challenge)
            if match:
                tension_a = match.group(1).strip()
                tension_b = match.group(2).strip()
                logger.info(f" [Fallback] 提取核心张力 (模式2): {tension_a} vs {tension_b}")
                tasks.append(
                    {
                        "id": f"task_{len(tasks) + 1}",
                        "title": f"{tension_a}与{tension_b}的平衡策略研究",
                        "description": f"研究如何在设计中平衡{tension_a}和{tension_b}的需求，找到最佳解决方案",
                        "source_keywords": [tension_a, tension_b],
                        "task_type": "research",
                        "priority": "high",
                        "dependencies": [],
                        "execution_order": len(tasks) + 1,
                    }
                )

    # ==========================================================================
    # 2. 提取对标案例任务
    # ==========================================================================
    benchmarking_keywords = ["对标", "参考", "案例", "标杆", "对比"]
    for keyword in benchmarking_keywords:
        if keyword in user_input and not any(keyword in t["title"] for t in tasks):
            # 尝试提取具体的对标对象
            benchmark_patterns = [
                r"对标([^，。、！？\n]{2,30})",  # "对标苏州黄桥菜市场"
                r"参考([^，。、！？\n]{2,30})",
                r"([^，。、！？\n]{2,30})案例",
            ]
            benchmark_target = ""
            for pattern in benchmark_patterns:
                match = re.search(pattern, user_input)
                if match:
                    benchmark_target = match.group(1).strip()
                    break

            if benchmark_target:
                tasks.append(
                    {
                        "id": f"task_{len(tasks) + 1}",
                        "title": "对标案例深度研究",
                        "description": f"重点研究{benchmark_target}，并调研其他成功案例的设计策略和创新要素",
                        "source_keywords": [keyword, benchmark_target],
                        "task_type": "research",
                        "priority": "high",
                        "dependencies": [],
                        "execution_order": len(tasks) + 1,
                    }
                )
            else:
                tasks.append(
                    {
                        "id": f"task_{len(tasks) + 1}",
                        "title": "标杆案例研究",
                        "description": "调研行业内成功案例的设计策略、运营模式和创新要素",
                        "source_keywords": [keyword],
                        "task_type": "research",
                        "priority": "high",
                        "dependencies": [],
                        "execution_order": len(tasks) + 1,
                    }
                )
            break

    # ==========================================================================
    # 3. 提取文化要素任务
    # ==========================================================================
    culture_keywords = ["文化", "传统", "在地", "历史", "特色"]
    for keyword in culture_keywords:
        if keyword in user_input and not any(keyword in t["title"] for t in tasks):
            # 尝试提取具体的文化对象
            culture_patterns = [
                r"([^，。、！？\n]{2,15})[文化传统]",  # "蛇口渔村文化"
                r"融入([^，。、！？\n]{2,15})",
            ]
            culture_target = ""
            for pattern in culture_patterns:
                match = re.search(pattern, user_input)
                if match:
                    culture_target = match.group(1).strip()
                    if any(c in culture_target for c in ["文化", "传统", "特色"]):
                        break

            if culture_target:
                tasks.append(
                    {
                        "id": f"task_{len(tasks) + 1}",
                        "title": f"{culture_target}文化洞察与提炼",
                        "description": f"深入调研{culture_target}的历史文脉和精神内核，提炼可融入设计的文化元素",
                        "source_keywords": [keyword, culture_target],
                        "task_type": "research",
                        "priority": "high",
                        "dependencies": [],
                        "execution_order": len(tasks) + 1,
                    }
                )
            else:
                tasks.append(
                    {
                        "id": f"task_{len(tasks) + 1}",
                        "title": "文化调研与元素提炼",
                        "description": "调研项目相关的文化背景，提炼可融入设计的文化元素和符号",
                        "source_keywords": [keyword],
                        "task_type": "research",
                        "priority": "high",
                        "dependencies": [],
                        "execution_order": len(tasks) + 1,
                    }
                )
            break

    # ==========================================================================
    # 4. 提取客群分析任务
    # ==========================================================================
    audience_keywords = ["客群", "用户", "访客", "居民", "客户", "人群", "岁", "女性", "男性"]
    for keyword in audience_keywords:
        if keyword in user_input and not any("客群" in t["title"] or "生活方式" in t["title"] for t in tasks):
            # 尝试提取具体的客群描述
            audience_patterns = [
                r"(\d+岁[^，。、！？\n]{0,10})",  # "35岁单身女性"
                r"([^，。、！？\n]{2,15})[客群用户访客]",
                r"兼顾([^，。、！？\n]{5,50})",  # "兼顾蛇口老居民街坊、香港访客..."
            ]
            audience_target = ""
            for pattern in audience_patterns:
                match = re.search(pattern, user_input)
                if match:
                    audience_target = match.group(1).strip()
                    break

            # 特别处理: 35岁单身女性等年龄+特征的情况
            age_match = re.search(r"(\d+)岁([^，。、！？\n]{0,10})", user_input)
            if age_match:
                age = age_match.group(1)
                traits = age_match.group(2).strip()
                tasks.append(
                    {
                        "id": f"task_{len(tasks) + 1}",
                        "title": f"{age}岁{traits}生活方式研究",
                        "description": f"深入分析{age}岁{traits}的审美偏好、生活场景、社交需求和精神追求",
                        "source_keywords": [f"{age}岁", traits],
                        "task_type": "analysis",
                        "priority": "high",
                        "dependencies": [],
                        "execution_order": len(tasks) + 1,
                    }
                )
            elif audience_target:
                tasks.append(
                    {
                        "id": f"task_{len(tasks) + 1}",
                        "title": "多元客群分析",
                        "description": f"分析{audience_target}的需求差异与共性，找到设计的平衡点",
                        "source_keywords": [keyword, audience_target],
                        "task_type": "analysis",
                        "priority": "high",
                        "dependencies": [],
                        "execution_order": len(tasks) + 1,
                    }
                )
            else:
                tasks.append(
                    {
                        "id": f"task_{len(tasks) + 1}",
                        "title": "目标客群研究",
                        "description": "分析目标用户的需求特征、使用习惯和期望体验",
                        "source_keywords": [keyword],
                        "task_type": "analysis",
                        "priority": "high",
                        "dependencies": [],
                        "execution_order": len(tasks) + 1,
                    }
                )
            break

    # ==========================================================================
    # 5. 提取品牌相关任务（新增：针对 Tiffany 等品牌主题）
    # ==========================================================================
    # 检测品牌名（通常是英文或品牌关键词）
    brand_patterns = [
        r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",  # Tiffany, Louis Vuitton
        r"([^，。、！？\n]{2,10})为主题",  # "蒂芙尼为主题"
        r"([^，。、！？\n]{2,10})品牌",
    ]
    brand_name = ""
    for pattern in brand_patterns:
        match = re.search(pattern, user_input)
        if match:
            potential_brand = match.group(1).strip()
            # 过滤掉不太像品牌名的内容
            if len(potential_brand) >= 2 and not any(c in potential_brand for c in ["平米", "年", "设计", "项目"]):
                brand_name = potential_brand
                break

    if brand_name and not any(brand_name in t["title"] for t in tasks):
        tasks.append(
            {
                "id": f"task_{len(tasks) + 1}",
                "title": f"{brand_name}品牌文化洞察",
                "description": f"研究{brand_name}的品牌精神、色彩体系、经典设计元素和核心价值观",
                "source_keywords": [brand_name, "品牌"],
                "task_type": "research",
                "priority": "high",
                "dependencies": [],
                "execution_order": len(tasks) + 1,
            }
        )

    # ==========================================================================
    # 6. 提取空间/规模相关任务
    # ==========================================================================
    space_match = re.search(r"(\d+)平米", user_input)
    # v7.220: 项目类型中文名从 PROJECT_TYPE_REGISTRY 读取，不再自维护关键词列表
    from intelligent_project_analyzer.services.project_type_detector import detect_project_type, get_type_label
    _detected_type_id = detect_project_type(user_input, default="")
    space_type = get_type_label(_detected_type_id) if _detected_type_id else ""

    if (space_match or space_type) and not any("空间" in t["title"] or "规划" in t["title"] for t in tasks):
        if space_match and space_type:
            area = space_match.group(1)
            tasks.append(
                {
                    "id": f"task_{len(tasks) + 1}",
                    "title": f"{area}平米{space_type}空间功能规划",
                    "description": f"制定符合用户需求的{area}平米{space_type}空间布局策略和功能分区方案",
                    "source_keywords": [f"{area}平米", space_type],
                    "task_type": "design",
                    "priority": "high",
                    "dependencies": [],
                    "execution_order": len(tasks) + 1,
                }
            )
        elif space_type:
            tasks.append(
                {
                    "id": f"task_{len(tasks) + 1}",
                    "title": f"{space_type}空间设计框架",
                    "description": f"输出{space_type}空间的整体设计框架和功能规划策略",
                    "source_keywords": [space_type],
                    "task_type": "design",
                    "priority": "high",
                    "dependencies": [],
                    "execution_order": len(tasks) + 1,
                }
            )

    # ==========================================================================
    # 7. 补充：最终交付物任务
    # ==========================================================================
    deliverable_keywords = ["框架", "方案", "概念", "设计思路"]
    for keyword in deliverable_keywords:
        if keyword in user_input and not any(keyword in t["title"] for t in tasks):
            # 提取交付物类型
            deliverable_patterns = [
                r"([^，。、！？\n]{2,10})框架",
                r"([^，。、！？\n]{2,10})方案",
                r"([^，。、！？\n]{2,10})设计思路",
            ]
            deliverable_target = ""
            for pattern in deliverable_patterns:
                match = re.search(pattern, user_input)
                if match:
                    deliverable_target = match.group(1).strip()
                    break

            if deliverable_target:
                tasks.append(
                    {
                        "id": f"task_{len(tasks) + 1}",
                        "title": f"{deliverable_target}设计框架输出",
                        "description": f"输出{deliverable_target}的整体设计框架，融合前期研究成果和设计策略",
                        "source_keywords": [keyword, deliverable_target],
                        "task_type": "design",
                        "priority": "high",
                        "dependencies": [],
                        "execution_order": len(tasks) + 1,
                    }
                )
            break

    # ==========================================================================
    # 8.  v7.110.0: 智能补齐和截断（不再固定5-7个）
    # ==========================================================================
    current_count = len(tasks)

    if current_count < recommended_min:
        logger.warning(f"️ [Fallback] 当前仅生成 {current_count} 个任务，补充通用任务至{recommended_min}个")
        # 补充通用任务
        generic_tasks = [
            {"title": "项目需求明确", "description": "明确项目的核心需求、期望目标和关键约束条件", "task_type": "analysis", "priority": "high"},
            {"title": "设计策略制定", "description": "制定整体设计策略和实施路径，确定设计的核心方向", "task_type": "design", "priority": "medium"},
            {"title": "行业趋势研究", "description": "研究相关领域的最新趋势、成功案例和创新实践", "task_type": "research", "priority": "medium"},
            {"title": "设计框架输出", "description": "整合前期研究成果，输出整体设计框架和实施建议", "task_type": "output", "priority": "medium"},
        ]

        for generic_task in generic_tasks:
            if len(tasks) >= recommended_min:
                break
            # 检查是否已有类似任务
            if not any(generic_task["title"] in t["title"] or t["title"] in generic_task["title"] for t in tasks):
                tasks.append(
                    {
                        "id": f"task_{len(tasks) + 1}",
                        **generic_task,
                        "source_keywords": [],
                        "dependencies": [],
                        "execution_order": len(tasks) + 1,
                    }
                )

    #  v7.110.0: 智能截断 - 不超过推荐最大值（优先保留高优先级）
    if len(tasks) > recommended_max:
        logger.warning(f"️ [Fallback] 生成了{len(tasks)}个任务，超过推荐上限{recommended_max}，智能截断")
        # 优先保留 high priority 的任务
        high_priority_tasks = [t for t in tasks if t.get("priority") == "high"]
        other_tasks = [t for t in tasks if t.get("priority") != "high"]
        tasks = (high_priority_tasks + other_tasks)[:recommended_max]

        # 重新编号
        for idx, task in enumerate(tasks, 1):
            task["id"] = f"task_{idx}"
            task["execution_order"] = idx

    logger.info(
        f" [Fallback] 生成 {len(tasks)} 个任务（推荐范围{recommended_min}-{recommended_max}，包含 {sum(1 for t in tasks if t['priority'] == 'high')} 个高优先级任务）"
    )

    return tasks


# =============================================================================
# 🆕 v7.995 P2: 混合生成策略 (LLM + 规则并行)
# =============================================================================


def _generate_feature_driven_tasks(project_features: Dict[str, float]) -> List[Dict[str, Any]]:
    """
    🆕 v7.995 P2: 根据高分特征强制生成关键任务
    
    基于 project_features 高分维度 (≥0.7) 生成对应的关键研究任务,
    确保高权重特征在任务列表中有明确体现。
    
    Args:
        project_features: 12维特征向量 (cultural, commercial, aesthetic等)
        
    Returns:
        特征驱动的强制任务列表
        
    Example:
        >>> features = {'cultural': 0.88, 'commercial': 0.72, 'wellness': 0.65}
        >>> tasks = _generate_feature_driven_tasks(features)
        >>> len(tasks)  # 2个 (cultural和commercial超过0.7)
        2
    """
    forced_tasks = []
    
    # 特征阈值: ≥0.7 = 高分特征
    HIGH_SCORE_THRESHOLD = 0.7
    
    # 特征 → 任务映射表
    FEATURE_TASK_MAP = {
        'cultural': {
            'title': '文化背景与元素提炼',
            'description': '深度调研项目相关的文化历史背景、传统工艺、地域特色,提炼可转译的文化符号和空间原型',
            'keywords': ['文化', '历史', '传统', '在地'],
            'task_type': 'research',
            'priority': 'high'
        },
        'commercial': {
            'title': '商业模式与盈利策略',
            'description': '分析目标客群、竞争格局、商业定位,建立ROI测算模型,制定可行的盈利路径',
            'keywords': ['商业', '盈利', '客群', 'ROI'],
            'task_type': 'analysis',
            'priority': 'high'
        },
        'aesthetic': {
            'title': '美学流派与氛围营造',
            'description': '研究相关美学流派、视觉语言、材料质感、光影策略,建立项目美学体系',
            'keywords': ['美学', '氛围', '视觉', '材料'],
            'task_type': 'research',
            'priority': 'high'
        },
        'technical': {
            'title': '技术系统与创新工艺',
            'description': '调研智能系统、节能技术、施工创新工艺,评估技术可行性与成本效益',
            'keywords': ['技术', '系统', '工艺', '创新'],
            'task_type': 'research',
            'priority': 'high'
        },
        'sustainable': {
            'title': '可持续策略与生态评估',
            'description': '研究绿色建筑标准、可再生能源、材料循环策略,建立生态评估框架',
            'keywords': ['可持续', '绿色', '生态', '能源'],
            'task_type': 'research',
            'priority': 'high'
        },
        'wellness': {
            'title': '健康建筑与疗愈空间',
            'description': '调研WELL标准、健康建筑设计要点、疗愈机制,制定健康空间策略',
            'keywords': ['健康', '疗愈', 'WELL', '舒适'],
            'task_type': 'research',
            'priority': 'high'
        },
        'social': {
            'title': '社会关系与行为模式',
            'description': '分析目标人群的社会结构、权力关系、行为模式,建立社会建模框架',
            'keywords': ['社会', '关系', '行为', '社区'],
            'task_type': 'analysis',
            'priority': 'high'
        },
        'functional': {
            'title': '功能效率与空间优化',
            'description': '分析使用需求、动线流程、空间利用率,制定功能布局优化策略',
            'keywords': ['功能', '效率', '动线', '布局'],
            'task_type': 'analysis',
            'priority': 'high'
        },
        'emotional': {
            'title': '情绪体验与氛围设计',
            'description': '研究空间情感表达、心理需求、体验节奏,构建情绪化设计框架',
            'keywords': ['情绪', '体验', '氛围', '心理'],
            'task_type': 'research',
            'priority': 'high'
        },
        'local': {
            'title': '乡建在地与社区共建',
            'description': '调研地域特征、乡土材料、社区文化,制定在地化设计策略',
            'keywords': ['乡建', '在地', '乡土', '社区'],
            'task_type': 'research',
            'priority': 'high'
        },
        'extreme': {
            'title': '极端环境适应策略',
            'description': '分析气候条件、地理环境、安全需求,制定环境适应性设计方案',
            'keywords': ['气候', '环境', '适应', '安全'],
            'task_type': 'analysis',
            'priority': 'high'
        },
        'futurism': {
            'title': '未来推演与技术前瞻',
            'description': '研究未来趋势、新兴技术、社会变革,建立前瞻性设计框架',
            'keywords': ['未来', '趋势', '科技', '创新'],
            'task_type': 'research',
            'priority': 'high'
        },
        'regulatory': {
            'title': '法规标准与合规研究',
            'description': '调研适用法规、行业标准、认证体系,建立合规性评估框架',
            'keywords': ['法规', '标准', '合规', '认证'],
            'task_type': 'research',
            'priority': 'high'
        },
        'environmental': {
            'title': '环境评估与生态策略',
            'description': '分析环境影响、生态敏感性、自然资源,制定环境友好型方案',
            'keywords': ['环境', '生态', '自然', '影响'],
            'task_type': 'analysis',
            'priority': 'high'
        },
        'spiritual': {
            'title': '精神内涵与叙事表达',
            'description': '研究精神诉求、哲学思考、叙事手法,构建项目精神内核',
            'keywords': ['精神', '叙事', '哲学', '内涵'],
            'task_type': 'research',
            'priority': 'high'
        },
        'innovative': {
            'title': '创新策略与前沿探索',
            'description': '调研前沿创新实践、跨界融合案例、新技术应用,制定创新路径',
            'keywords': ['创新', '前沿', '跨界', '实验'],
            'task_type': 'research',
            'priority': 'high'
        },
        'identity': {
            'title': '身份认同与品牌表达',
            'description': '分析用户身份特征、品牌精神内核、文化归属感,建立身份表达体系',
            'keywords': ['身份', '品牌', '认同', '表达'],
            'task_type': 'analysis',
            'priority': 'high'
        },
        'experiential': {
            'title': '体验设计与场景构建',
            'description': '研究用户旅程、触点体验、场景叙事,构建沉浸式体验策略',
            'keywords': ['体验', '场景', '旅程', '沉浸'],
            'task_type': 'research',
            'priority': 'high'
        },
        'historical': {
            'title': '历史研究与遗产保护',
            'description': '调研历史脉络、文物保护标准、修缮工艺,制定历史资源活化策略',
            'keywords': ['历史', '遗产', '保护', '修缮'],
            'task_type': 'research',
            'priority': 'high'
        },
        'regional': {
            'title': '地域特征与在地化研究',
            'description': '分析地域气候、风土人情、本土材料、地方产业,建立在地化设计框架',
            'keywords': ['地域', '在地', '本土', '风土'],
            'task_type': 'research',
            'priority': 'high'
        },
        'material_innovation': {
            'title': '材料创新与工艺实验',
            'description': '调研新型材料、创新工艺、材料性能测试,建立材料选型与实验方案',
            'keywords': ['材料', '工艺', '创新', '实验'],
            'task_type': 'research',
            'priority': 'high'
        },
        'symbolic': {
            'title': '符号系统与意义构建',
            'description': '研究文化符号、视觉隐喻、象征体系,构建项目符号学设计框架',
            'keywords': ['符号', '象征', '隐喻', '意义'],
            'task_type': 'research',
            'priority': 'high'
        },
        'inclusive': {
            'title': '包容性设计与无障碍研究',
            'description': '调研通用设计原则、无障碍标准、多元人群需求,制定包容性设计策略',
            'keywords': ['包容', '无障碍', '通用', '多元'],
            'task_type': 'research',
            'priority': 'high'
        }
    }
    
    for feature_id, score in sorted(project_features.items(), key=lambda x: x[1], reverse=True):
        # 保护性检查：确保score是数字类型
        if not isinstance(score, (int, float)):
            continue
        
        if score >= HIGH_SCORE_THRESHOLD and feature_id in FEATURE_TASK_MAP:
            task_template = FEATURE_TASK_MAP[feature_id]
            forced_tasks.append({
                'id': f'task_feature_{feature_id}',
                'title': task_template['title'],
                'description': task_template['description'],
                'source_keywords': task_template['keywords'],
                'task_type': task_template['task_type'],
                'priority': task_template['priority'],
                'source': 'rule_feature_driven',  # 标记来源
                'feature_score': round(score, 2),  # 记录特征分数
                'dependencies': [],
                'execution_order': len(forced_tasks) + 1
            })
            logger.info(f"✅ [特征驱动] {feature_id}={score:.2f} → 生成任务: {task_template['title']}")
    
    return forced_tasks


def _calculate_task_similarity(task1: Dict[str, Any], task2: Dict[str, Any]) -> float:
    """
    🆕 v7.995 P2: 计算两个任务的相似度 (基于标题和关键词)
    ✨ P2增强: 添加中文分词支持，提升语义识别准确度
    
    使用标题文本相似度 (50%) + 关键词重叠度 (30%) + 中文字符级相似度 (20%)
    
    Args:
        task1: 任务1
        task2: 任务2
        
    Returns:
        相似度分数 0.0-1.0
        
    Example:
        >>> t1 = {'title': '文化背景调研', 'source_keywords': ['文化', '历史']}
        >>> t2 = {'title': '文化背景与元素提炼', 'source_keywords': ['文化', '传统']}
        >>> _calculate_task_similarity(t1, t2)
        0.78  # 高相似度
    """
    from difflib import SequenceMatcher
    import re
    
    # 标题相似度 (权重50%)
    title1 = task1.get('title', '')
    title2 = task2.get('title', '')
    title_sim = SequenceMatcher(None, title1, title2).ratio()
    
    # 关键词重叠度 (权重30%)
    keywords1 = set(task1.get('source_keywords', []))
    keywords2 = set(task2.get('source_keywords', []))
    
    if keywords1 or keywords2:
        keyword_sim = len(keywords1 & keywords2) / max(len(keywords1 | keywords2), 1)
    else:
        keyword_sim = 0.0
    
    # 🆕 P2: 中文字符级相似度 (权重20%)
    # 提取中文词汇，按字符切分后计算Jaccard相似度
    chinese_pattern = re.compile(r'[\u4e00-\u9fff]+')
    chars1 = set(''.join(chinese_pattern.findall(title1)))
    chars2 = set(''.join(chinese_pattern.findall(title2)))
    
    if chars1 or chars2:
        char_sim = len(chars1 & chars2) / max(len(chars1 | chars2), 1)
    else:
        char_sim = 0.0
    
    # 综合相似度（P2优化权重分配）
    similarity = 0.5 * title_sim + 0.3 * keyword_sim + 0.2 * char_sim
    
    return similarity


def _deduplicate_across_categories(tasks: List[Dict[str, Any]], similarity_threshold: float = 0.75) -> List[Dict[str, Any]]:
    """
    🆕 P1-1: 跨类别语义去重
    
    解决两阶段生成法中Phase 2各类别独立生成导致的重复问题
    例如：3x"农耕文化调研"、4x"运营模型研究"
    
    策略：
    1. 计算所有任务对之间的语义相似度
    2. 相似度>threshold的任务对，保留优先级高的或先出现的
    3. 优先级相同时，保留内容更详细的（description长度）
    
    Args:
        tasks: 任务列表（来自不同类别）
        similarity_threshold: 相似度阈值（默认0.75）
    
    Returns:
        去重后的任务列表
    
    Example:
        >>> tasks = [
        ...     {'id': '1', 'title': '狮岭村农耕文化调研', 'category': 'A', 'description': '...'},
        ...     {'id': '2', 'title': '狮岭村农耕文化与民俗研究', 'category': 'B', 'description': '...'},
        ...     {'id': '3', 'title': '运营模型设计', 'category': 'C', 'description': '...'}
        ... ]
        >>> result = _deduplicate_across_categories(tasks)
        >>> len(result)  # 任务1和2被识别为重复，保留其一
        2
    """
    if len(tasks) <= 1:
        return tasks
    
    # 记录要移除的任务索引
    to_remove = set()
    duplicate_pairs = []
    
    # 两两比较所有任务
    for i in range(len(tasks)):
        if i in to_remove:
            continue
        
        for j in range(i + 1, len(tasks)):
            if j in to_remove:
                continue
            
            task_i = tasks[i]
            task_j = tasks[j]
            
            # 计算相似度
            similarity = _calculate_task_similarity(task_i, task_j)
            
            if similarity > similarity_threshold:
                # 决定保留哪个任务
                priority_i = {'high': 3, 'medium': 2, 'low': 1}.get(task_i.get('priority', 'medium'), 2)
                priority_j = {'high': 3, 'medium': 2, 'low': 1}.get(task_j.get('priority', 'medium'), 2)
                
                desc_len_i = len(task_i.get('description', ''))
                desc_len_j = len(task_j.get('description', ''))
                
                # 决策逻辑：优先级高的保留；优先级相同则保留描述更详细的
                if priority_i > priority_j:
                    to_remove.add(j)
                    keep_idx, remove_idx = i, j
                elif priority_j > priority_i:
                    to_remove.add(i)
                    keep_idx, remove_idx = j, i
                elif desc_len_i >= desc_len_j:
                    to_remove.add(j)
                    keep_idx, remove_idx = i, j
                else:
                    to_remove.add(i)
                    keep_idx, remove_idx = j, i
                
                duplicate_pairs.append({
                    'keep': tasks[keep_idx].get('title', 'unknown')[:40],
                    'remove': tasks[remove_idx].get('title', 'unknown')[:40],
                    'similarity': similarity,
                    'keep_category': tasks[keep_idx].get('category', 'unknown'),
                    'remove_category': tasks[remove_idx].get('category', 'unknown')
                })
    
    # 输出去重详情
    if duplicate_pairs:
        logger.info(f"  [P1-1详情] 发现{len(duplicate_pairs)}对重复任务:")
        for idx, pair in enumerate(duplicate_pairs[:5], 1):  # 最多显示5对
            logger.info(
                f"    {idx}. 保留[{pair['keep_category']}] '{pair['keep']}' "
                f"| 移除[{pair['remove_category']}] '{pair['remove']}' (相似度={pair['similarity']:.2f})"
            )
        if len(duplicate_pairs) > 5:
            logger.info(f"    ... 共{len(duplicate_pairs)}对，显示前5对")
    
    # 构建去重后的列表
    deduplicated = [task for idx, task in enumerate(tasks) if idx not in to_remove]
    
    return deduplicated


def _merge_hybrid_tasks(
    llm_tasks: List[Dict[str, Any]],
    rule_tasks: List[Dict[str, Any]],
    max_tasks: int,
    category_order: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    🆕 v7.995 P2: 融合LLM任务和规则任务,去重并优先级排序
    v8.001 升级: 按Phase 1大纲类别顺序排序（保留分组结构），组内再按priority排序
    
    策略:
    1. 规则任务强制保留 (关键任务保障)
    2. LLM任务与规则任务去重 (相似度>0.70)
    3. 保留LLM独有任务 (创意补充)
    4. 按 category_order 排序（组内按priority）<-- v8.001 新增
    5. 总数不超过max_tasks
    
    Args:
        llm_tasks: LLM生成的任务列表
        rule_tasks: 规则生成的任务列表
        max_tasks: 最大任务数量
        category_order: Phase 1大纲的类别顺序列表（用于排序）
        
    Returns:
        融合后的任务列表（按类别分组，组内按priority排序）
    """
    merged = []
    
    # Step 1: 规则任务全部保留
    merged.extend(rule_tasks)
    logger.info(f"✅ [Merge] 保留 {len(rule_tasks)} 个规则强制任务")
    
    # Step 2: LLM任务去重后加入
    duplicate_count = 0
    for llm_task in llm_tasks:
        # 检查与规则任务的相似度
        is_duplicate = False
        for rule_task in rule_tasks:
            similarity = _calculate_task_similarity(llm_task, rule_task)
            if similarity > 0.70:  # v7.995 P2: 阈值从0.85降至0.70 (减少过严格的去重条件)
                logger.debug(
                    f"⚠️ [Merge] LLM任务 '{llm_task.get('title', '')}' "
                    f"与规则任务 '{rule_task.get('title', '')}' 重复 (相似度={similarity:.2f})"
                )
                is_duplicate = True
                duplicate_count += 1
                break
        
        if not is_duplicate:
            merged.append(llm_task)
    
    logger.info(f"✅ [Merge] 新增 {len(merged) - len(rule_tasks)} 个LLM独有任务 (去重{duplicate_count}个)")
    
    # Step 3: 排序策略
    # v8.001: 如果有category_order，按类别分组顺序排序（保留Phase 1结构）
    # 否则退化为旧的全局priority排序
    def get_priority_score(task):
        priority = task.get('priority', 'medium')
        source = task.get('source', '')
        score = {'high': 3, 'medium': 2, 'low': 1}.get(priority, 2)
        if 'rule_' in source:
            score += 0.5
        return score
    
    if category_order:
        # 构建类别->顺序索引映射（未知类别放末尾）
        cat_idx = {cat: i for i, cat in enumerate(category_order)}
        # 规则任务/整合任务放在最后（兜底分组末尾）
        fallback_categories = ['基础调研', '多源整合']
        for i, fc in enumerate(fallback_categories):
            cat_idx.setdefault(fc, len(category_order) + i)
        
        def sort_key(task):
            cat = task.get('category', '')
            # 查找类别顺序，未知类别置于末尾
            cat_position = cat_idx.get(cat, len(category_order) + 99)
            # 组内按priority降序（priority越高排越前，取负值）
            return (cat_position, -get_priority_score(task))
        
        merged = sorted(merged, key=sort_key)
        logger.info(f"✅ [Merge] 按类别顺序排序完成 (共 {len(cat_idx)} 个类别)")
    else:
        # 降级：按全局priority排序（旧行为）
        merged = sorted(merged, key=get_priority_score, reverse=True)
        logger.info("✅ [Merge] 按priority全局排序（无category_order）")
    
    # Step 4: 数量截断
    if len(merged) > max_tasks:
        logger.warning(f"⚠️ [Merge] 任务总数 {len(merged)} 超过上限 {max_tasks}, 智能截断")
        merged = merged[:max_tasks]
    
    # 重新编号
    for idx, task in enumerate(merged, 1):
        task['id'] = f"task_{idx}"
        task['execution_order'] = idx
    
    logger.info(f"🎯 [Merge] 最终任务数: {len(merged)}")
    return merged


# ============================================================================
# P2 深度增强: D1-D4 通用化增强函数 (v8.0)
# ============================================================================

def _ensure_task_dimensions(tasks: List[Dict[str, Any]]) -> None:
    """
    P2-D1: 维度字段强制注入 -- 确保每个任务携带3-5个dimensions子项
    
    对于LLM未生成dimensions的任务，通过文本分析自动提取。
    该函数原地修改任务列表，不返回新列表。
    
    策略:
    1. 保留LLM已生成的有效dimensions (>=3个)
    2. 从description中提取顿号/逗号分隔的短语作为维度候选
    3. 从source_keywords补充
    4. 根据task_type添加通用维度兜底
    
    Args:
        tasks: 任务列表（原地修改）
    """
    # task_type -> 通用维度兜底映射
    TYPE_DEFAULT_DIMS = {
        'research': ['资料收集', '案例对比', '趋势分析', '要点提炼'],
        'analysis': ['数据整理', '模式识别', '对比分析', '结论提炼'],
        'design': ['方案构思', '可行性评估', '视觉表达', '技术实现'],
        'output': ['内容组织', '格式规范', '质量检查', '成果交付'],
    }
    
    for task in tasks:
        existing = task.get('dimensions', [])
        if isinstance(existing, list) and len(existing) >= 3:
            continue  # 已有足够维度，保留
        
        dimensions = list(existing) if isinstance(existing, list) else []
        description = task.get('description', '')
        task_type = task.get('task_type', 'research')
        
        # 策略1: 从description中提取分隔的语义块
        segments = re.split(r'[，,。；;]', description)
        for seg in segments:
            items = re.split(r'[、和与及]', seg)
            if len(items) >= 2:
                for item in items:
                    cleaned = item.strip()
                    match = re.search(r'([\u4e00-\u9fffA-Za-z]{2,10})', cleaned)
                    if match and match.group(1) not in dimensions and len(dimensions) < 5:
                        dimensions.append(match.group(1))
        
        # 策略2: 从source_keywords补充
        for kw in task.get('source_keywords', []):
            if isinstance(kw, str) and len(kw) >= 2 and kw not in dimensions and len(dimensions) < 5:
                dimensions.append(kw)
        
        # 策略3: 根据task_type添加默认维度兜底
        defaults = TYPE_DEFAULT_DIMS.get(task_type, ['信息梳理', '要点提炼', '逻辑验证'])
        for d in defaults:
            if len(dimensions) >= 3:
                break
            if d not in dimensions:
                dimensions.append(d)
        
        task['dimensions'] = dimensions[:5]
    
    qualified = sum(1 for t in tasks if len(t.get('dimensions', [])) >= 3)
    logger.info(f"✅ [P2-D1] 维度注入完成: {qualified}/{len(tasks)} 个任务达标")


def _fallback_classify_tasks(tasks: List[Dict[str, Any]], user_input: str) -> None:
    """
    🔧 P0-B: 降级路径后置分类
    
    当两阶段生成完全失败、降级为标准单次调用时，任务没有 category 字段。
    使用关键词规则为每个任务分配最合适的类别，避免所有任务堆在"基础调研"中。
    
    Args:
        tasks: 任务列表（会被原地修改）
        user_input: 用户输入（用于上下文判断）
    """
    # 定义分类规则：关键词 → 类别
    classification_rules = [
        {
            "category": "案例调研与设计对标",
            "keywords": ["案例", "对标", "参考", "借鉴", "建筑师", "设计师", "作品", "风格",
                        "安藤", "隈研吾", "王澍", "刘家琨", "贝聿铭", "扎哈", "柯布西耶"],
        },
        {
            "category": "场地调研与环境分析",
            "keywords": ["场地", "地形", "气候", "环境", "地理", "地貌", "水系", "植被",
                        "日照", "风向", "温度", "湿度", "微气候", "土壤", "基础设施"],
        },
        {
            "category": "概念与文化策略",
            "keywords": ["概念", "文化", "叙事", "精神", "哲学", "母题", "意境", "非遗",
                        "传统", "遗产", "传承", "民俗", "节庆", "仪式", "符号"],
        },
        {
            "category": "空间策略与功能规划",
            "keywords": ["空间", "功能", "布局", "动线", "流线", "规划", "组织", "分区",
                        "户型", "公共", "私密", "过渡", "入口", "庭院"],
        },
        {
            "category": "材料与技术策略",
            "keywords": ["材料", "材质", "构造", "工艺", "技术", "结构", "施工", "建造",
                        "竹", "木", "石", "混凝土", "钢", "玻璃", "夯土"],
        },
        {
            "category": "运营策略与商业模型",
            "keywords": ["运营", "商业", "盈利", "经济", "投资", "回报", "产品", "品牌",
                        "业态", "坪效", "客群", "定价", "收益", "模式"],
        },
        {
            "category": "可持续与环境适应",
            "keywords": ["可持续", "生态", "环保", "绿色", "节能", "碳", "循环", "自然",
                        "雨水", "通风", "遮阳", "保温", "低碳"],
        },
        {
            "category": "社区与社会维度",
            "keywords": ["社区", "社会", "村民", "居民", "共建", "参与", "公益", "共享",
                        "乡村", "振兴", "在地", "社群"],
        },
    ]
    
    classified_count = 0
    for task in tasks:
        if task.get('category') and task['category'] not in ('', '基础调研'):
            continue  # 已有有意义的分类，跳过
        
        title = task.get('title', '')
        desc = task.get('description', '')
        text = title + ' ' + desc
        
        best_category = ""
        best_score = 0
        for rule in classification_rules:
            score = sum(1 for kw in rule["keywords"] if kw in text)
            if score > best_score:
                best_score = score
                best_category = rule["category"]
        
        if best_category and best_score >= 1:
            task['category'] = best_category
            classified_count += 1
        else:
            task['category'] = '综合调研'  # 无法分类的归入"综合调研"而非"基础调研"
            classified_count += 1
    
    if classified_count > 0:
        # 统计分类结果
        cat_dist = {}
        for t in tasks:
            cat = t.get('category', '综合调研')
            cat_dist[cat] = cat_dist.get(cat, 0) + 1
        logger.info(f"🔧 [P0-B] 后置分类完成: {classified_count}个任务分配到{len(cat_dist)}个类别")
        for cat, count in cat_dist.items():
            logger.info(f"   {cat}: {count}个")


def _detect_multi_reference_sources(
    user_input: str,
    structured_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    P2-D2: 多源参考检测 -- 检测用户输入中是否包含多个参考源
    
    通用化检测模式（不针对特定领域）：
    - 多个引号名称枚举
    - "多位/多个/几位" + 名词组
    - 人名/品牌名列举
    - 对比/融合模式
    - 结构化数据多源引用
    
    Args:
        user_input: 用户原始输入
        structured_data: 结构化数据
        
    Returns:
        {'detected': bool, 'sources': list, 'source_type': str, 'pattern': str}
    """
    result = {
        'detected': False,
        'sources': [],
        'source_type': 'reference',
        'pattern': ''
    }
    
    # 模式1: 多个引号名称
    quoted_names = re.findall(r'[""「]([^""」]{2,20})[""」]', user_input)
    if len(quoted_names) >= 2:
        result.update({'detected': True, 'sources': quoted_names,
                       'source_type': 'reference', 'pattern': '多个引用名称'})
        return result
    
    # 模式2: "多位/多个/几位" + 名词
    multi_match = re.search(
        r'(多位|多个|几位|数位|若干)([\u4e00-\u9fff]{1,4}(?:师|家|人|者|方))', user_input)
    if multi_match:
        context_names = re.findall(
            r'[\u4e00-\u9fff]{2,4}(?:·[\u4e00-\u9fff]{2,6})?|[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+',
            user_input)
        result.update({'detected': True, 'sources': context_names[:10],
                       'source_type': 'expert',
                       'pattern': f'{multi_match.group(1)}{multi_match.group(2)}'})
        return result
    
    # 模式3: 名称枚举 A、B、C 和 D
    enum_patterns = [
        r'([\u4e00-\u9fff]{2,4})、([\u4e00-\u9fff]{2,4})(?:、([\u4e00-\u9fff]{2,4}))?(?:和|与|及)([\u4e00-\u9fff]{2,4})',
        r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)[,、]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)(?:[,、]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*))?',
    ]
    for pattern in enum_patterns:
        match = re.search(pattern, user_input)
        if match:
            names = [g for g in match.groups() if g]
            if len(names) >= 2:
                result.update({'detected': True, 'sources': names,
                               'source_type': 'expert', 'pattern': '名称枚举'})
                return result
    
    # 模式4: 对比/融合模式
    compare_match = re.search(
        r'(?:对比|比较|参考|融合|结合|整合)([\u4e00-\u9fffA-Za-z\s]{2,20})(?:和|与|及|以及)([\u4e00-\u9fffA-Za-z\s]{2,20})',
        user_input)
    if compare_match:
        sources = [g.strip() for g in compare_match.groups() if g]
        if len(sources) >= 2:
            result.update({'detected': True, 'sources': sources,
                           'source_type': 'methodology', 'pattern': '对比/融合模式'})
            return result
    
    # 模式5: 结构化数据多源引用
    if structured_data:
        design_challenge = structured_data.get('design_challenge', '')
        if design_challenge:
            refs = re.findall(r'[""「]([^""」]{2,20})[""」]', design_challenge)
            if len(refs) >= 2:
                result.update({'detected': True, 'sources': refs,
                               'source_type': 'reference', 'pattern': '结构化数据多源引用'})
                return result
    
    return result


def _generate_integration_tasks(
    reference_info: Dict[str, Any],
    user_input: str
) -> List[Dict[str, Any]]:
    """
    P2-D2: 多源整合任务自动生成 -- 当检测到多个参考源时生成整合类任务
    
    通用整合模板（不针对特定领域）：
    1. 多源对比分析任务
    2. 整合策略任务（3个以上源时触发）
    
    Args:
        reference_info: _detect_multi_reference_sources 返回值
        user_input: 用户原始输入
        
    Returns:
        整合类任务列表
    """
    if not reference_info.get('detected') or not reference_info.get('sources'):
        return []
    
    sources = reference_info['sources']
    source_type = reference_info.get('source_type', 'reference')
    source_names = '、'.join(str(s) for s in sources[:5])
    source_count = len(sources)
    
    type_labels = {
        'expert': '专家', 'brand': '品牌',
        'reference': '参考对象', 'methodology': '方法论',
    }
    type_label = type_labels.get(source_type, '参考对象')
    
    tasks = []
    
    # 整合任务1: 多源对比分析
    tasks.append({
        'id': 'task_integration_1',
        'title': f'多{type_label}对比分析（{source_names[:20]}）',
        'description': (
            f'系统对比{source_count}个{type_label}（{source_names}）的'
            f'核心特征、方法差异、优劣势，建立多维对比矩阵'
        ),
        'source_keywords': [str(s) for s in sources[:5]],
        'task_type': 'analysis',
        'priority': 'high',
        'source': 'rule_integration_d2',
        'category': '多源整合',  # v8.001: 整合任务统一归入"多源整合"分组
        'dependencies': [],
        'execution_order': 0,
        'dimensions': ['特征对比', '方法差异', '优劣分析', '适用场景'],
    })
    
    # 整合任务2: 整合策略（>= 3个源时触发）
    if source_count >= 3:
        tasks.append({
            'id': 'task_integration_2',
            'title': f'{source_names[:20]}整合策略与优先级排序',
            'description': (
                f'基于对比分析结果，提出{source_count}个{type_label}的整合策略，'
                f'确定各{type_label}元素的优先级和应用方式'
            ),
            'source_keywords': [str(s) for s in sources[:5]] + ['整合', '策略'],
            'task_type': 'analysis',
            'priority': 'high',
            'source': 'rule_integration_d2',
            'category': '多源整合',  # v8.001: 整合任务统一归入"多源整合"分组
            'dependencies': ['task_integration_1'],
            'execution_order': 0,
            'dimensions': ['优先级排序', '整合方案', '冲突解决', '协同策略'],
        })
    
    logger.info(f"✅ [P2-D2] 检测到{source_count}个{type_label}，生成{len(tasks)}个整合任务")
    return tasks


def _extract_user_requirements(user_input: str) -> List[Dict[str, str]]:
    """
    P2-D4: 用户意图提取 -- 从用户输入中解析显式需求条目
    
    通用解析模式（不针对特定文档格式）：
    - 编号列表: "1. xxx" "1) xxx" "1、xxx"
    - 中文编号: "第一、" "第二、"
    - Markdown标题: "## xxx" "### xxx"
    - 意图子句: "需要/要求/希望..." 引导的句子
    - 具体要求块: "具体要求：..." 后的内容
    
    Args:
        user_input: 用户原始输入
        
    Returns:
        需求列表 [{'id': 'req_N', 'text': '需求内容', 'source': '解析来源'}]
    """
    requirements = []
    seen_texts = set()
    
    def _add_req(text: str, source: str):
        text = text.strip()
        if len(text) >= 5 and text not in seen_texts:
            seen_texts.add(text)
            requirements.append({
                'id': f'req_{len(requirements) + 1}',
                'text': text,
                'source': source,
            })
    
    # 模式1: 数字编号列表
    numbered = re.findall(
        r'(?:^|\n)\s*(?:\d+[.）)、]|[①②③④⑤⑥⑦⑧⑨⑩])\s*(.+?)(?=\n\s*(?:\d+[.）)、]|[①②③④⑤⑥⑦⑧⑨⑩])|\n\n|$)',
        user_input, re.DOTALL
    )
    for item in numbered:
        _add_req(item, 'numbered_list')
    
    # 模式2: 中文编号
    chinese_numbered = re.findall(
        r'第[一二三四五六七八九十]+[、，：:]\s*(.+?)(?=第[一二三四五六七八九十]+[、，：:]|$)',
        user_input, re.DOTALL
    )
    for item in chinese_numbered:
        _add_req(item, 'chinese_numbered')
    
    # 模式3: Markdown标题
    md_headings = re.findall(r'#{2,4}\s+(.+?)(?:\n|$)', user_input)
    for item in md_headings:
        _add_req(item, 'markdown_heading')
    
    # 模式4: 意图引导子句
    intent_clauses = re.findall(
        r'(?:需要|要求|希望|包含|涵盖|应该|必须|期望)\s*(.{5,50}?)(?:[。；;！\n]|$)',
        user_input
    )
    for item in intent_clauses:
        _add_req(item, 'intent_clause')
    
    # 模式5: "具体要求" 块
    specific_blocks = re.findall(
        r'(?:具体要求|详细要求|功能要求|设计要求)[：:]\s*(.+?)(?=\n\n|\Z)',
        user_input, re.DOTALL
    )
    for block in specific_blocks:
        items = re.split(r'[;；。\n]', block)
        for item in items:
            _add_req(item, 'specific_block')
    
    if requirements:
        logger.info(f"✅ [P2-D4] 提取到 {len(requirements)} 个用户显式需求")
    
    return requirements


def _validate_requirement_coverage(
    tasks: List[Dict[str, Any]],
    requirements: List[Dict[str, str]]
) -> List[Dict[str, str]]:
    """
    P2-D4: 需求覆盖校验 -- 检查每个用户需求是否有对应任务覆盖
    
    使用关键词重叠度判断覆盖关系。覆盖阈值: 40%关键词命中。
    
    Args:
        tasks: 当前任务列表
        requirements: 用户需求列表
        
    Returns:
        未覆盖的需求列表
    """
    uncovered = []
    
    # 构建任务文本索引
    task_texts = []
    for t in tasks:
        text = f"{t.get('title', '')} {t.get('description', '')} {' '.join(t.get('source_keywords', []))}"
        task_texts.append(text.lower())
    
    for req in requirements:
        req_text = req['text']
        keywords = re.findall(r'[\u4e00-\u9fff]{2}|[A-Za-z]{3,}', req_text)
        
        if not keywords:
            continue
        
        # 检查是否有任务覆盖（>=40%关键词命中）
        best_coverage = 0.0
        for task_text in task_texts:
            hits = sum(1 for kw in keywords if kw.lower() in task_text)
            coverage = hits / len(keywords) if keywords else 0
            best_coverage = max(best_coverage, coverage)
        
        if best_coverage < 0.4:
            uncovered.append(req)
    
    if uncovered:
        logger.warning(f"⚠️ [P2-D4] {len(uncovered)}/{len(requirements)} 个用户需求未被任务覆盖")
        for req in uncovered:
            logger.debug(f"  未覆盖: {req['text'][:50]}")
    elif requirements:
        logger.info(f"✅ [P2-D4] 所有 {len(requirements)} 个用户需求已被任务覆盖")
    
    return uncovered


def _generate_coverage_gap_tasks(
    uncovered: List[Dict[str, str]],
    user_input: str
) -> List[Dict[str, Any]]:
    """
    P2-D4: 意图覆盖补充任务生成 -- 为未覆盖的用户需求生成补充任务
    
    Args:
        uncovered: 未覆盖的需求列表
        user_input: 用户原始输入
        
    Returns:
        补充任务列表（最多5个）
    """
    tasks = []
    
    for req in uncovered[:5]:
        req_text = req['text']
        keywords = re.findall(r'[\u4e00-\u9fff]{2,4}|[A-Za-z]{3,}', req_text)[:5]
        
        # 判断任务类型
        if any(kw in req_text for kw in ['设计', '方案', '规划', '创意']):
            task_type = 'design'
        elif any(kw in req_text for kw in ['分析', '评估', '对比', '诊断']):
            task_type = 'analysis'
        else:
            task_type = 'research'
        
        title_prefix = {'research': '调研', 'analysis': '分析', 'design': '设计'}
        title = f"{title_prefix.get(task_type, '调研')}{req_text[:20]}"
        
        tasks.append({
            'id': f'task_coverage_{len(tasks) + 1}',
            'title': title,
            'description': f'针对用户需求"{req_text[:40]}"进行专项调研与分析，确保设计方案完整覆盖此需求',
            'source_keywords': keywords,
            'task_type': task_type,
            'priority': 'medium',
            'source': 'rule_coverage_d4',
            'dependencies': [],
            'execution_order': 0,
            'dimensions': keywords[:4] if len(keywords) >= 3 else keywords + ['需求分析', '方案建议'],
        })
    
    if tasks:
        logger.info(f"✅ [P2-D4] 生成 {len(tasks)} 个意图覆盖补充任务")
    
    return tasks


def _generate_mode_specific_tasks(
    detected_modes: List[Dict[str, Any]],
    user_input: str,
    structured_data: Optional[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    🆕 P1-2: 基于检测到的设计模式生成专项任务
    
    Args:
        detected_modes: 检测到的设计模式列表 [{"mode": "M5_rural_context", "confidence": 0.6}]
        user_input: 用户原始输入
        structured_data: 结构化数据
        
    Returns:
        模式驱动的任务列表
    """
    tasks = []
    
    # 模式到专项任务的映射
    # ✨ P2优化: 扩展至10个设计模式（覆盖完整本体论）
    MODE_TASK_TEMPLATES = {
        "M1_concept_driven": [
            {
                'title': '核心设计概念提炼与叙事构建',
                'description': '提炼项目的核心设计理念，构建完整的设计叙事体系',
                'keywords': ['设计概念', '叙事', '理念'],
                'task_type': 'design',
                'priority': 'high'
            }
        ],
        "M2_function_efficiency": [
            {
                'title': '动线最优化与功能模块标准化设计',
                'description': '分层设计主线/次级/后勤/紧急疏散动线，消除逆行冲突和瓶颈节点；将空间拆解为可复制、可替换的标准模块',
                'keywords': ['动线优化', '功能模块', '标准化', '效率'],
                'task_type': 'design',
                'priority': 'high'
            }
        ],
        "M3_emotional_experience": [
            {
                'title': '情绪节奏曲线与五感调动系统设计',
                'description': '构建完整的情绪曲线（压缩→释放→提升→高潮→沉静），整合视觉、听觉、嗅觉、触觉、温度五感联动体验',
                'keywords': ['情绪节奏', '五感体验', '记忆锚点', '沉浸'],
                'task_type': 'design',
                'priority': 'high'
            }
        ],
        "M4_capital_asset": [
            {
                'title': '投资回报模型与商业策略研究',
                'description': '分析项目的商业价值，构建投资回报模型和运营策略',
                'keywords': ['商业模式', '投资回报', '运营'],
                'task_type': 'analysis',
                'priority': 'high'
            }
        ],
        "M5_rural_context": [
            # A1-概念建构：地域概念命题
            {
                'title': '在地文化解码与核心概念命题建构',
                'description': '提炼真正属于该地域的文化结构（历史路径、生产方式、气候特征、聚落形态），凝缩为一个不可替换的设计命题；验证：脱离该地域是否仍然成立？如成立则为伪在地',
                'keywords': ['在地文化', '概念命题', '地域解码', '文化结构'],
                'task_type': 'design',
                'priority': 'high'
            },
            # A2-空间结构：聚落空间逻辑
            {
                'title': '乡村聚落空间结构与场地功能分区策略',
                'description': '分析村落形态、地形高差与水系分布，制定散点聚落+线性串联的空间组织逻辑；明确公共/半公共/私密的层级系统，设计多群体动线分离方案',
                'keywords': ['聚落空间', '功能分区', '动线组织', '地形适配'],
                'task_type': 'design',
                'priority': 'high'
            },
            # A4-材料系统：本地材料策略  
            {
                'title': '本地材料系统构建与在地工艺整合',
                'description': '构建本地材料逻辑（易获得、易维护、可复制）；调研现存手工艺与生态材料；与现代工艺结合，避免简单复古堆砌；评估成本可控性与可维护性',
                'keywords': ['本地材料', '在地工艺', '材料系统', '可维护性'],
                'task_type': 'research',
                'priority': 'high'
            },
            # A7-资本策略：产业闭环与盈利模式
            {
                'title': '乡村产业闭环设计与可持续盈利模式',
                'description': '设计住宿+餐饮+手工艺+农产品销售+教育体验的完整产业闭环；构建独立现金流模型；设计村民参与和受益机制，避免"人类动物园"化',
                'keywords': ['产业闭环', '盈利模式', '村民受益', '现金流'],
                'task_type': 'analysis',
                'priority': 'high'
            },
            # A9-社会建模：村民与游客关系
            {
                'title': '村民-游客-运营三方社会关系建模',
                'description': '构建村民受益者角色（就业/股权/农产品供应链）、游客参与式体验设计（下田/手作/共餐，非旁观式）、冲突缓冲机制（噪音隔离/时段分区/隐私分级）',
                'keywords': ['社会建模', '村民受益', '游客体验', '关系演化'],
                'task_type': 'design',
                'priority': 'medium'
            },
            # A10-环境适应：乡村自然环境
            {
                'title': '在地气候与自然环境被动式设计策略',
                'description': '基于当地气候（温湿度/风向/降水/日照）制定自然通风+被动采光+深檐遮阳+夯土蓄热策略；设计雨水收集与场地水循环系统；评估材料耐久性与自然灾害应对',
                'keywords': ['气候适应', '被动式设计', '自然通风', '雨水管理'],
                'task_type': 'design',
                'priority': 'medium'
            },
            # A11-运营产品化：骨架标准化+表皮可变
            {
                'title': '乡建项目运营标准化与品牌产品体系',
                'description': '制定"骨架标准（结构/材料/运营流程）+表皮可变（在地文化不同）"的模块化路径；设计淡旺季收入平衡机制；制定软装更新周期与品牌视觉系统',
                'keywords': ['运营标准化', '品牌系统', '模块化', '产品线'],
                'task_type': 'analysis',
                'priority': 'medium'
            },
            # A12-文明表达：乡村第三条路
            {
                'title': '乡村文明表达路径与跨学科整合策略',
                'description': '构建"非城市化、非博物馆化"的第三条路论题；整合社会学（乡土差序格局）、经济学（产业闭环）、人类学（农耕仪式）、生态学（林田系统）；定义50年视角的可持续文化传承路径',
                'keywords': ['文明议题', '跨学科整合', '乡村叙事', '50年视角'],
                'task_type': 'design',
                'priority': 'medium'
            },
        ],
        "M6_urban_regeneration": [
            {
                'title': '城市更新策略与历史保护研究',
                'description': '研究城市更新中的历史建筑保护、功能置换和社区活化策略',
                'keywords': ['城市更新', '历史保护', '活化'],
                'task_type': 'research',
                'priority': 'high'
            }
        ],
        "M7_tech_integration": [
            {
                'title': '系统隐形化与数据反馈驱动结构设计',
                'description': '实现技术系统隐形化（预埋管线、模块化检修口、隐藏式传感器），构建数据闭环驱动空间自适应调整',
                'keywords': ['智能系统', '隐形化', '数据反馈', '可迭代'],
                'task_type': 'design',
                'priority': 'high'
            }
        ],
        "M8_extreme_condition": [
            {
                'title': '结构抗性系统与材料适应系统设计',
                'description': '基于当地气候数据设计抗风压/抗震/抗腐蚀方案，选择适应极端环境的材料系统，构建能源自给与生理舒适保障',
                'keywords': ['结构抗性', '材料适应', '能源系统', '极端环境'],
                'task_type': 'design',
                'priority': 'high'
            }
        ],
        "M9_social_structure": [
            {
                'title': '权力距离建模与隐私分级系统设计',
                'description': '明确空间中的权力关系结构，设计四级隐私系统（公共→半公共→半私密→完全私密），构建冲突缓冲机制和关系演化适配能力',
                'keywords': ['权力距离', '隐私分级', '冲突缓冲', '关系演化'],
                'task_type': 'design',
                'priority': 'high'
            }
        ],
        "M10_future_speculation": [
            {
                'title': '未来场景推演与前瞻性设计研究',
                'description': '推演未来生活场景和社会趋势，探索前瞻性设计方向',
                'keywords': ['未来', '推演', '前瞻'],
                'task_type': 'research',
                'priority': 'low'
            }
        ],
        "M11_healthcare_healing": [
            {
                'title': '心理安全环境与生理疗愈节律系统设计',
                'description': '设计低刺激、高安全感的空间环境系统，包括色彩约束、声学控制、昼夜光节律、材料安全性；同时为服务提供者和被服务者设计双视角动线',
                'keywords': ['心理安全', '疗愈节律', '无障碍', '尊严'],
                'task_type': 'design',
                'priority': 'high'
            }
        ]
    }
    
    # 根据detected_modes生成任务
    for mode_info in detected_modes:
        mode_id = mode_info.get("mode", "")
        confidence = mode_info.get("confidence", 0)
        
        # 🔧 阈值修复: 与 _simple_mode_detection 检测阈值(0.245)保持一致
        # 原0.4阈值会导致低置信度模式（如M5 confidence=0.33）产生0个任务
        if confidence >= 0.25 and mode_id in MODE_TASK_TEMPLATES:
            templates = MODE_TASK_TEMPLATES[mode_id]
            for template in templates:
                tasks.append({
                    'id': f'task_{len(tasks) + 1}',
                    'title': template['title'],
                    'description': template['description'],
                    'source_keywords': template['keywords'],
                    'task_type': template['task_type'],
                    'priority': template['priority'],
                    'source': f'rule_mode_{mode_id}',
                    'detected_mode': mode_id,
                    'mode_confidence': confidence,
                    'dependencies': [],
                    'execution_order': len(tasks) + 1,
                    'dimensions': template['keywords'],
                })
                logger.debug(f"  [P1-2] {mode_id} (conf={confidence:.2f}) → {template['title']}")
    
    return tasks


def _generate_rule_based_tasks(
    user_input: str,
    structured_data: Optional[Dict[str, Any]],
    project_features: Optional[Dict[str, float]],
    task_count: int = 5,
    detected_modes: Optional[List[Dict[str, Any]]] = None  # 🆕 P1: 新增参数
) -> List[Dict[str, Any]]:
    """
    🆕 v7.995 P2 + P1优化: 基于规则生成关键强制任务
    
    策略:
    1. 特征驱动: project_features高分特征 (≥0.7) → 强制生成任务
    2. 结构化提取: design_challenge, character_narrative
    3. 关键词匹配: 对标、文化、客群等 (优先级medium)
    4. 🆕 P1: 设计模式驱动（detected_modes为空时使用关键词fallback）
    
    Args:
        user_input: 用户原始输入
        structured_data: 结构化数据
        project_features: 12维特征向量
        task_count: 目标任务数 (建议3-6个)
        detected_modes: 检测到的设计模式列表（P1新增）
        
    Returns:
        规则生成的任务列表 (带source标记)
    """
    tasks = []
    
    logger.info(f"🔄 [规则生成] 开始生成,目标数量: {task_count}个")
    
    # 🆕 P1-1: detected_modes为空时，使用关键词简单推断
    if not detected_modes or len(detected_modes) == 0:
        logger.info("  [P1-1] detected_modes为空，启动关键词fallback...")
        from .core_task_decomposer import CoreTaskDecomposer
        decomposer = CoreTaskDecomposer()
        detected_modes = decomposer._simple_mode_detection(
            user_input, 
            structured_data.get('project_type', '') if structured_data else '',
            project_features
        )
        if detected_modes:
            logger.info(f"  [P1-1] 关键词推断出 {len(detected_modes)} 个模式: {[m['mode'] for m in detected_modes]}")
    
    # 🆕 P1-2: 基于detected_modes生成专项任务
    if detected_modes:
        mode_tasks = _generate_mode_specific_tasks(detected_modes, user_input, structured_data)
        tasks.extend(mode_tasks)
        logger.info(f"✅ [P1-2] 模式驱动生成 {len(mode_tasks)} 个任务")

    # 策略1: 特征驱动 (最高优先级)
    # P2-D3: 重新启用特征驱动（依赖merge阶段去重机制避免污染LLM任务）
    if project_features:
        feature_tasks = _generate_feature_driven_tasks(project_features)
        tasks.extend(feature_tasks)
        logger.info(f"✅ [规则生成] 特征驱动生成 {len(feature_tasks)} 个任务")
    
    # 策略2: 结构化数据提取 (design_challenge等)
    if structured_data:
        design_challenge = structured_data.get("design_challenge", "")
        
        # 提取核心张力任务
        if design_challenge:
            match = re.search(r'"([^"]{2,30})"[^"]{0,50}与[^"]{0,50}"([^"]{2,30})"', design_challenge)
            if match:
                tension_a = match.group(1).strip()
                tension_b = match.group(2).strip()
                tasks.append({
                    "id": f"task_{len(tasks) + 1}",
                    "title": f"{tension_a}与{tension_b}的平衡策略研究",
                    "description": f"研究如何在设计中平衡{tension_a}和{tension_b}的需求,找到最佳解决方案",
                    "source_keywords": [tension_a, tension_b],
                    "task_type": "research",
                    "priority": "high",
                    "source": "rule_structured_data",
                    "extraction_method": "design_challenge_tension",
                    "dependencies": [],
                    "execution_order": len(tasks) + 1
                })
                logger.info(f"✅ [规则生成] 张力提取: {tension_a} vs {tension_b}")
    
    # 策略3: 关键词匹配 (优先级medium,避免与LLM重复)
    if '对标' in user_input or '参考' in user_input or '案例' in user_input:
        if not any('对标' in t.get('title', '') or '案例' in t.get('title', '') for t in tasks):
            tasks.append({
                "id": f"task_{len(tasks) + 1}",
                "title": "标杆案例研究",
                "description": "调研行业内成功案例的设计策略、运营模式和创新要素",
                "source_keywords": ['对标', '案例'],
                "task_type": "research",
                "priority": "medium",  # 从high降为medium
                "source": "rule_keyword_match",
                "dependencies": [],
                "execution_order": len(tasks) + 1
            })
            logger.info("✅ [规则生成] 关键词匹配: 对标案例")
    
    # 策略4 (P2-D3): 通用关键规则模板（基于模式检测，领域无关）
    universal_rules = [
        {
            'patterns': [r'客户|用户|住户|访客|居民|业主|受众|客群|人群|利益相关'],
            'task': {
                'title': '利益相关方需求分析',
                'description': '识别项目涉及的各类利益相关方，系统分析其需求、期望和潜在冲突',
                'keywords': ['利益相关方', '需求', '用户'],
                'task_type': 'analysis',
                'priority': 'high'
            }
        },
        {
            'patterns': [r'预算|资金|成本|造价|投资|有限|约束|限制'],
            'task': {
                'title': '资源约束与可行性评估',
                'description': '评估项目面临的预算、时间、技术、法规等约束条件，制定应对策略',
                'keywords': ['资源', '约束', '可行性'],
                'task_type': 'analysis',
                'priority': 'medium'
            }
        },
        {
            'patterns': [r'分期|一期|二期|阶段|里程碑|时间线|工期|进度'],
            'task': {
                'title': '项目阶段规划与里程碑设计',
                'description': '制定项目分期实施计划，明确各阶段目标、交付物和关键里程碑',
                'keywords': ['阶段', '规划', '里程碑'],
                'task_type': 'analysis',
                'priority': 'medium'
            }
        },
        {
            'patterns': [r'可持续|环保|绿色|节能|低碳|生态|循环'],
            'task': {
                'title': '可持续发展策略研究',
                'description': '研究适用于本项目的可持续发展策略，包括材料选择、能源效率和生态影响',
                'keywords': ['可持续', '绿色', '生态'],
                'task_type': 'research',
                'priority': 'medium'
            }
        },
    ]
    
    for rule in universal_rules:
        if any(re.search(p, user_input) for p in rule['patterns']):
            task_template = rule['task']
            # 避免与已有任务重复
            if not any(task_template['title'][:6] in t.get('title', '') for t in tasks):
                tasks.append({
                    'id': f'task_{len(tasks) + 1}',
                    'title': task_template['title'],
                    'description': task_template['description'],
                    'source_keywords': task_template['keywords'],
                    'task_type': task_template['task_type'],
                    'priority': task_template['priority'],
                    'source': 'rule_universal_d3',
                    'dependencies': [],
                    'execution_order': len(tasks) + 1,
                    'dimensions': task_template['keywords'],
                })
                logger.info(f"✅ [规则-通用D3] 模式匹配 → 生成: {task_template['title']}")
    
    # 🆕 P2-1: Enhanced rule-based fallback - 确保至少生成3个通用任务
    if len(tasks) < 3:
        logger.warning(f"⚠️ [P2-1] 规则生成任务不足({len(tasks)}个)，启用通用fallback模板...")
        
        fallback_templates = [
            {
                'title': '项目背景与目标梳理',
                'description': '系统梳理项目的背景信息、核心目标和关键约束条件',
                'keywords': ['背景', '目标', '约束'],
                'task_type': 'analysis',
                'priority': 'high'
            },
            {
                'title': '核心利益相关方需求研究',
                'description': '识别并分析项目涉及的所有利益相关方，梳理其核心需求和期望',
                'keywords': ['利益相关方', '需求', '期望'],
                'task_type': 'research',
                'priority': 'high'
            },
            {
                'title': '行业标杆案例调研',
                'description': '调研行业内的成功案例和最佳实践，提取可借鉴的设计策略',
                'keywords': ['标杆', '案例', '最佳实践'],
                'task_type': 'research',
                'priority': 'medium'
            },
            {
                'title': '项目特色与差异化策略',
                'description': '基于项目特点和市场定位，提出差异化的设计策略',
                'keywords': ['特色', '差异化', '策略'],
                'task_type': 'design',
                'priority': 'high'
            },
            {
                'title': '可行性与风险评估',
                'description': '评估项目在技术、经济、法规等方面的可行性，识别潜在风险',
                'keywords': ['可行性', '风险', '评估'],
                'task_type': 'analysis',
                'priority': 'medium'
            }
        ]
        
        # 按顺序添加fallback任务，直到达到3个
        needed = 3 - len(tasks)
        for i, template in enumerate(fallback_templates[:needed]):
            tasks.append({
                'id': f'task_{len(tasks) + 1}',
                'title': template['title'],
                'description': template['description'],
                'source_keywords': template['keywords'],
                'task_type': template['task_type'],
                'priority': template['priority'],
                'source': 'rule_fallback_p2',
                'category': '基础调研',  # v8.001: 规则任务统一归入"基础调研"分组
                'dependencies': [],
                'execution_order': len(tasks) + 1,
                'dimensions': template['keywords'],
            })
            logger.info(f"  [P2-1 Fallback] 添加通用任务 {i+1}/{needed}: {template['title']}")
    
    # 限制数量
    tasks = tasks[:task_count]
    
    logger.info(f"🎯 [规则生成] 完成,实际生成 {len(tasks)} 个任务 (含<bdi hidden>P2-1 fallback:{sum(1 for t in tasks if t.get('source')=='rule_fallback_p2')}个</bdi>)")
    return tasks


def _calculate_few_shot_strength(
    project_features: Optional[Dict[str, float]],
    user_input: str,
    structured_data: Optional[Dict[str, Any]] = None
) -> tuple[str, str]:
    """
    🆕 Few-shot平衡改进: 动态Few-shot强度控制
    
    根据项目特征计算"特殊性"分数，决定Few-shot的影响力。
    
    Args:
        project_features: 12维特征向量
        user_input: 用户输入
        structured_data: 结构化数据
    
    Returns:
        (strength, description): 强度等级 + 描述
        - 'light': 轻度参考（显示1个任务 + "仅供启发"）
        - 'medium': 中度参考（显示3个任务 + "参考质量标准"）
        - 'strong': 强度参考（显示5个任务 + "建议遵循"）
    """
    
    specialty_score = 0.0
    reasons = []
    
    # 规则1: 特殊用户群体（自闭症、残障、特殊需求等）
    special_users = ['自闭症', '残障', '特殊需求', '无障碍', '康复', '老年痴呆', '失智']
    if any(kw in user_input for kw in special_users):
        specialty_score += 0.3
        reasons.append('特殊用户群体')
    
    # 规则2: 技术主导项目（技术创新、智能化、BIM等）
    if project_features and project_features.get('technical', 0) > 0.7:
        specialty_score += 0.25
        reasons.append('技术主导')
    
    tech_keywords = ['BIM', '智能化', '物联网', 'IoT', '人工智能', 'AI', '数字孪生', '参数化', '算法生成']
    if any(kw in user_input for kw in tech_keywords):
        specialty_score += 0.2
        reasons.append('技术创新')
    
    # 规则3: 跨界融合项目（3个以上高分特征）
    if project_features:
        high_features = [k for k, v in project_features.items() if v > 0.6]
        if len(high_features) >= 3:
            specialty_score += 0.2
            reasons.append(f'跨界融合({len(high_features)}维度)')
    
    # 规则4: 极端环境/特殊场景
    extreme_keywords = ['极寒', '极热', '高海拔', '沙漠', '水下', '漂浮', '极地', '地震带']
    if any(kw in user_input for kw in extreme_keywords):
        specialty_score += 0.25
        reasons.append('极端环境')
    
    # 规则5: 实验性/前瞻性项目
    experimental_keywords = ['实验', '未来', '概念', '前瞻', '探索', '试点', '创新实验室']
    if any(kw in user_input for kw in experimental_keywords):
        specialty_score += 0.15
        reasons.append('实验探索')
    
    # 决定Few-shot强度
    if specialty_score > 0.5:
        strength = 'light'
        description = '轻度参考（项目特殊性高，鼓励创新）'
    elif specialty_score > 0.25:
        strength = 'medium'
        description = '中度参考（平衡标准与创新）'
    else:
        strength = 'strong'
        description = '标准参考（建议遵循行业标准）'
    
    if reasons:
        logger.info(f"📊 [Few-shot强度] {strength.upper()}: {description} | 原因: {', '.join(reasons)} | 分数: {specialty_score:.2f}")
    
    return strength, description


def _stratify_task_priorities(tasks: List[Dict[str, Any]], user_input: str, 
                              structured_data: Optional[Dict[str, Any]] = None) -> None:
    """
    🆕 P2-2: 优先级分层策略
    
    根据任务类型、交付物依赖和12 Ability Core重要性进行优先级分层。
    修改原地进行（in-place modification）。
    
    分层逻辑：
    - **High**: 
      1. 核心概念建构任务（concept, narrative）
      2. 用户明确要求的交付物相关任务
      3. 12 Ability Core中高权重维度（cultural>0.6, functional>0.6等）
    - **Medium**: 
      1. 支撑性研究任务（案例调研、技术研究）
      2. 设计策略制定任务
    - **Low**: 
      1. 次要细节任务
      2. 可选优化任务
    
    Args:
        tasks: 任务列表（会被原地修改）
        user_input: 用户输入
        structured_data: 结构化数据
    """
    if not tasks:
        return
    
    logger.info(f"🎯 [P2-2] 开始优先级分层: {len(tasks)}个任务")
    
    # 提取用户明确要求的交付物关键词
    deliverable_keywords = []
    import re
    deliverable_patterns = [
        r'(\w{2,8})(框架|概念|策略|体系|模型|方案|系统|设计)',
        r'需要(.{2,10})', r'希望(.{2,10})', r'包括(.{2,30})'
    ]
    for pattern in deliverable_patterns:
        matches = re.findall(pattern, user_input)
        for match in matches:
            deliverable = match if isinstance(match, str) else ''.join(match)
            if deliverable and len(deliverable.strip()) >= 2:
                deliverable_keywords.append(deliverable.strip())
    
    # 获取特征向量（用于判断核心维度）
    project_features = structured_data.get('project_features', {}) if structured_data else {}
    high_features = {k: v for k, v in project_features.items() if v >= 0.6}
    
    # 优先级调整计数
    changed_to_high = 0
    changed_to_medium = 0
    changed_to_low = 0
    
    for task in tasks:
        title = task.get('title', '')
        description = task.get('description', '')
        task_type = task.get('task_type', 'research')
        current_priority = task.get('priority', 'medium')
        category = task.get('category', '')
        
        # 计算新优先级
        score = 0
        reasons = []
        
        # 规则1: 核心概念建构任务 → High
        concept_keywords = ['概念', '哲学', '理念', '叙事', '主题', '精神', '核心', '定位']
        if any(kw in title or kw in description or kw in category for kw in concept_keywords):
            score += 3
            reasons.append('核心概念建构')
        
        # 规则2: 用户明确要求的交付物 → High
        if deliverable_keywords:
            if any(kw in title or kw in description for kw in deliverable_keywords[:5]):
                score += 3
                reasons.append('用户明确交付物')
        
        # 规则3: 高权重12 Ability Core维度 → High
        if high_features:
            ability_keywords_map = {
                'cultural': ['文化', '传统', '历史', '遗产'],
                'functional': ['功能', '空间', '布局', '动线'],
                'aesthetic': ['美学', '风格', '语言', '表达'],
                'commercial': ['商业', '运营', '盈利', '回报']
            }
            for feat, keywords in ability_keywords_map.items():
                if feat in high_features and any(kw in title or kw in description for kw in keywords):
                    score += 2
                    reasons.append(f'{feat}高分维度')
                    break
        
        # 规则4: 任务类型权重
        if task_type in ['design', 'strategy']:
            score += 1
            reasons.append('设计/策略类')
        elif task_type == 'analysis':
            score += 0
        else:  # research
            score -= 1
        
        # 规则5: 案例调研、对标研究 → Medium（降级，非核心）
        if any(kw in title for kw in ['案例', '对标', '参考', '标杆']):
            score -= 1
            reasons.append('案例调研（支撑性）')
        
        # 规则6: 细节优化任务 → Low
        if any(kw in title for kw in ['优化', '细化', '补充', '完善', '调整']):
            score -= 2
            reasons.append('细节优化')
        
        # 决策：根据分数设置优先级
        new_priority = current_priority
        if score >= 3:
            new_priority = 'high'
        elif score >= 0:
            new_priority = 'medium'
        else:
            new_priority = 'low'
        
        # 更新优先级（如有变化）
        if new_priority != current_priority:
            task['priority'] = new_priority
            task['priority_reason'] = ', '.join(reasons) if reasons else '默认'
            
            if new_priority == 'high':
                changed_to_high += 1
            elif new_priority == 'medium':
                changed_to_medium += 1
            else:
                changed_to_low += 1
    
    # 统计最终分布
    priority_dist = {'high': 0, 'medium': 0, 'low': 0}
    for task in tasks:
        p = task.get('priority', 'medium')
        priority_dist[p] = priority_dist.get(p, 0) + 1
    
    logger.info(f"✅ [P2-2] 优先级分层完成: High={priority_dist['high']}, Medium={priority_dist['medium']}, Low={priority_dist['low']}")
    logger.info(f"  调整: ↑{changed_to_high}个→High, ↔{changed_to_medium}个→Medium, ↓{changed_to_low}个→Low")


async def decompose_core_tasks_hybrid(
    user_input: str, 
    structured_data: Optional[Dict[str, Any]] = None, 
    llm: Optional[Any] = None,
    enable_hybrid: bool = True
) -> List[Dict[str, Any]]:
    """
    🆕 v7.995 P2: 混合生成策略 (LLM + 规则并行)
    
    从"LLM优先→失败降级规则"升级为"LLM并行+规则强制补充→智能融合"。
    
    工作流程:
    1. 复杂度分析 → 智能推荐任务数量
    2. Track A: LLM生成创意性任务 (65%)
    3. Track B: 规则生成关键强制任务 (35%)
    4. 智能融合: 去重 + 优先级排序
    5. 质量验证
    
    Args:
        user_input: 用户原始输入
        structured_data: 需求分析阶段产出的结构化数据 (包含project_features)
        llm: LLM 实例 (可选)
        enable_hybrid: 是否启用混合策略 (默认True, False时回退到纯LLM模式)
        
    Returns:
        任务列表 (8-52个，根据复杂度动态决定)
        
    Example:
        >>> tasks = await decompose_core_tasks_hybrid(
        ...     user_input="文化酒店设计,融合传统书法与现代奢华",
        ...     structured_data={'project_features': {'cultural': 0.88, 'aesthetic': 0.76}}
        ... )
        >>> len(tasks)  # 混合生成
        28
    """
    if not enable_hybrid:
        # 回退到原始纯LLM模式
        logger.info("ℹ️ [混合策略] 已禁用,使用纯LLM模式")
        return await decompose_core_tasks(user_input, structured_data, llm)
    
    decomposer = CoreTaskDecomposer()
    
    # Step 1: 复杂度分析
    complexity_analysis = TaskComplexityAnalyzer.analyze(user_input, structured_data)
    recommended_min = complexity_analysis["recommended_min"]
    recommended_max = complexity_analysis["recommended_max"]
    complexity_score = complexity_analysis["complexity_score"]
    
    logger.info(f"📊 [混合策略] 推荐任务数: {recommended_min}-{recommended_max}个 (复杂度={complexity_score:.2f})")
    
    # 从structured_data提取project_features
    project_features = structured_data.get("project_features") if structured_data else None
    detected_modes = structured_data.get("detected_design_modes", []) if structured_data else []
    
    # 🆕 v7.999.4: 混合模式不再缩窄LLM任务数量（用户反馈修复）
    # LLM接收完整推荐范围，规则引擎作为补充
    llm_task_count_min = recommended_min
    llm_task_count_max = recommended_max
    rule_task_count = max(3, int(recommended_max * 0.35))
    
    logger.info(f"📋 [混合策略 v7.999.4] 任务分配: LLM={llm_task_count_min}-{llm_task_count_max}个 + 规则补充最多{rule_task_count}个")
    
    # Step 3: Track A - LLM生成 (完整范围)
    llm_tasks = []
    outline_category_order: List[str] = []  # v8.001: Phase 1 大纲类别顺序，失败时为空列表
    try:
        logger.info(f"🤖 [Track A] LLM生成开始 (范围: {llm_task_count_min}-{llm_task_count_max}个)...")

        # 🔧 修复：初始化LangChain全局缓存，避免"no cache found"错误
        try:
            import langchain
            if not hasattr(langchain, 'llm_cache') or langchain.llm_cache is None:
                from langchain_community.cache import InMemoryCache
                langchain.llm_cache = InMemoryCache()
                logger.debug("[CacheInit] Initialized langchain.llm_cache")
        except Exception as cache_init_error:
            logger.warning(f"[CacheInit] Failed to init cache: {cache_init_error}, continuing...")

        # 如果没有提供 LLM，使用默认
        if llm is None:
            from ..services.llm_factory import LLMFactory
            llm = LLMFactory.create_llm()
        
        from langchain_core.messages import HumanMessage, SystemMessage
        
        system_prompt = decomposer.config.get("system_prompt", "")
        user_template = decomposer.config.get("user_prompt_template", "")
        
        # 构建结构化数据摘要
        structured_summary = ""
        if structured_data:
            summary_parts = []
            for key in ["project_task", "character_narrative", "physical_context", "project_type"]:
                if structured_data.get(key):
                    summary_parts.append(f"{key}: {structured_data[key]}")
            structured_summary = "\n".join(summary_parts) if summary_parts else "暂无"
        
        # 🆕 v8.2 P0: 预加载配置文件（Phase 1/2 共用）
        import os as _os
        import yaml as _yaml
        _cfg_dir = _os.path.join(
            _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
            "config"
        )
        # 加载 Mode×Ability 激活矩阵
        _mode_activation_cfg = {}
        _mode_act_path = _os.path.join(_cfg_dir, "mode_ability_activation.yaml")
        try:
            if _os.path.exists(_mode_act_path):
                with open(_mode_act_path, encoding="utf-8") as _f:
                    _mode_activation_cfg = _yaml.safe_load(_f) or {}
                logger.debug(f"[v8.2] 已加载 mode_ability_activation.yaml ({len(_mode_activation_cfg)} entries)")
        except Exception as _e:
            logger.warning(f"[v8.2] 加载 mode_ability_activation.yaml 失败: {_e}")
        
        # 加载 Ability Core 5层模型精华
        _ability_essentials_cfg = {}
        _ess_path = _os.path.join(_cfg_dir, "ability_core_essentials.yaml")
        try:
            if _os.path.exists(_ess_path):
                with open(_ess_path, encoding="utf-8") as _f:
                    _ability_essentials_cfg = _yaml.safe_load(_f) or {}
                logger.debug(f"[v8.2] 已加载 ability_core_essentials.yaml ({len(_ability_essentials_cfg)} entries)")
        except Exception as _e:
            logger.warning(f"[v8.2] 加载 ability_core_essentials.yaml 失败: {_e}")

        # 🆕 v7.999.4→v8.0 P0-T3: 手动注入Few-shot示例（tags_matrix智能匹配）
        few_shot_content = ""
        _selected_ideal_tasks = []  # v8.2: 存储已选example的ideal_tasks,供Phase 2片段注入
        _selected_example_name = None  # v8.2: 记录选中的example名称
        few_shot_examples = decomposer._load_few_shot_examples()
        if few_shot_examples and structured_data:
            project_type = structured_data.get('project_type') or ''  # guard: key存在但值为None时也返回''
            project_features = structured_data.get('project_features', {})
            detected_modes = structured_data.get('detected_design_modes', [])
            selected_example_name = decomposer._select_best_few_shot(project_type, project_features, detected_modes, user_input)
            
            if selected_example_name and selected_example_name in few_shot_examples:
                example_data = few_shot_examples[selected_example_name]
                # 🆕 v7.999.4: YAML结构修正 - ideal_tasks在example键下
                example_content = example_data.get('example', {})
                ideal_tasks = example_content.get('ideal_tasks', [])
                example_name = example_content.get('project_info', {}).get('name', '未命名')
                
                # v8.2: 存储到外部作用域,供Phase 2片段注入
                _selected_ideal_tasks = ideal_tasks
                _selected_example_name = selected_example_name
                
                # 🆕 Few-shot平衡改进: 动态强度控制
                strength, strength_desc = _calculate_few_shot_strength(project_features, user_input, structured_data)
                
                # 根据强度决定显示任务数量
                show_count = {'light': 1, 'medium': 3, 'strong': 5}.get(strength, 3)
                
                if ideal_tasks:
                    few_shot_content = "\n\n## 📚 参考案例（Few-shot示例）\n"
                    few_shot_content += f"**案例**: {example_name}\n"
                    few_shot_content += f"**任务数量**: {len(ideal_tasks)}个\n"
                    few_shot_content += f"**参考模式**: {strength_desc}\n\n"
                    
                    if strength == 'light':
                        few_shot_content += "**示例任务（仅供启发，大胆创新）**:\n\n"
                    elif strength == 'medium':
                        few_shot_content += "**示例任务（参考质量标准，灵活调整内容）**:\n\n"
                    else:
                        few_shot_content += "**示例任务（建议遵循标准和格式）**:\n\n"
                    
                    for i, task in enumerate(ideal_tasks[:show_count], 1):
                        few_shot_content += f"{i}. {task.get('title', '未命名')}\n"
                    
                    if len(ideal_tasks) > show_count:
                        few_shot_content += f"\n... 等共{len(ideal_tasks)}个任务\n"
                    
                    # 🆕 Few-shot平衡改进: 增强创新鼓励提示
                    few_shot_content += "\n⚠️ **重要原则**:\n"
                    few_shot_content += "- 📐 **参考质量标准**：系统性拆解、独立原则、3-5维度、紧扣项目核心\n"
                    few_shot_content += "- 🎨 **鼓励内容创新**：如项目有独特性/特殊需求，大胆设计示例中没有的创新类别\n"
                    few_shot_content += "- 🎯 **用户需求优先**：用户明确要求的交付物优先级 > 示例内容（不要被示例束缚）\n"
                    few_shot_content += f"- 请生成{llm_task_count_min}-{llm_task_count_max}个同等质量的任务\n"
                    
                    logger.info(f"✅ [Few-shot] 已注入示例: {selected_example_name} ({len(ideal_tasks)}任务) | 强度: {strength.upper()} | 显示: {show_count}个")
        
        user_prompt = user_template.format(
            user_input=user_input,
            structured_data_summary=structured_summary,
            task_count_min=llm_task_count_min,
            task_count_max=llm_task_count_max,
        )
        
        # 注入Few-shot内容
        if few_shot_content:
            user_prompt += few_shot_content
        
        # 🆕 v7.999.7: 两阶段生成法（统一规划 + 按纲填充）
        # 核心理念：先规划大纲（轻松），再按纲细化（可控）
        # Phase 1: LLM生成10-12个任务类别
        # Phase 2: 每个类别生成2-3个详细任务 → 总计28-36个
        try:
            logger.info("🎯 [v7.999.7 两阶段生成] 开始执行统一规划方案")
            logger.info(f"📋 Phase 1: 生成任务大纲（目标{llm_task_count_min}-{llm_task_count_max}个任务）")
            
            # Phase 1: 生成任务大纲（v7.999.11: 交付物驱动 + 12 Ability Core覆盖）
            # 🎯 P0改进：从"流程阶段"转向"能力维度+交付成果"
            
            # Step 1.1: 提取用户明确要求的交付物
            import re
            explicit_deliverables = []
            deliverable_patterns = [
                r'(\w{2,8})(框架|概念|策略|体系|模型|方案|系统|设计)',
                r'提出(.{2,10})', r'给出(.{2,10})', r'包括(.{2,30})'
            ]
            for pattern in deliverable_patterns:
                matches = re.findall(pattern, user_input)
                for match in matches:
                    deliverable = match if isinstance(match, str) else ''.join(match)
                    if deliverable and len(deliverable.strip()) >= 2:
                        explicit_deliverables.append(deliverable.strip())
            
            deliverable_context = ""
            if explicit_deliverables:
                deliverable_context = "\n\n🎯 **用户明确要求的交付物**（必须覆盖）：\n" + \
                                    "\n".join([f"  - {d}" for d in explicit_deliverables[:5]])
            
            outline_prompt = f"""你是一位资深设计项目专家。请从**能力维度**和**交付成果**角度制定任务大纲。

项目信息：
{user_input}

结构化摘要：
{structured_summary}
{deliverable_context}

## 🏗️ 12 Ability Core框架参考

在设计项目中，专业能力通常可归为以下12个核心维度（适用于建筑/空间/品牌/产品等领域）：

1. **概念建构 (Concept)**: 核心理念提炼、设计哲学、叙事主题
2. **空间结构 (Spatial)**: 布局逻辑、动线组织、尺度控制、几何规则
3. **叙事节奏 (Narrative)**: 体验时间线、情绪曲线、场景序列
4. **材料系统 (Material)**: 材质策略、肌理语言、构造逻辑
5. **灯光系统 (Lighting)**: 光环境设计、氛围营造、光影策略
6. **功能效率 (Functional)**: 功能规划、运营效率、技术适配
7. **资本策略 (Capital)**: 成本控制、投资回报、经济模型
8. **技术整合 (Technical)**: 技术创新、BIM应用、智能化集成
9. **社会建模 (Social)**: 社群关系、社会价值、利益相关方平衡
10. **环境适应 (Environmental)**: 气候响应、生态策略、可持续性
11. **运营产品化 (Operational)**: 运营模型、服务体系、产品化设计
12. **文明表达 (Cultural)**: 文化传承、地域特色、美学表达

**关键原则**：
- 📋 不是所有项目都需要全部12项能力，根据项目类型选择8-12项核心能力
- 🎯 每个任务类别应明确对应某个/某几个能力维度
- 🔄 如果用户明确提出交付物（如"建筑语言框架"、"运营模型"），必须有对应类别确保产出

## 🎯 你的任务

生成8-10个**能力导向的任务类别**（包括标准类别 + 创新类别）：

### 【标准类别】(6-8个)

1. **类别命名原则**：
   - 优先使用"XX能力"、"XX系统"、"XX策略"等能力维度名称
   - 例如："概念建构与设计哲学"、"空间结构与动线策略"、"材料系统与构造逻辑"
   - 而非："调研阶段"、"设计阶段"等流程阶段名

2. **覆盖12 Ability Core**：
   - 至少覆盖8个核心能力维度
   - 缺失维度可在summary中说明理由（如"本项目为纯室内改造，无需环境适应能力"）

3. **对齐用户交付物**：
   - 如果用户要求"材料策略"，必须有"材料系统"类别
   - 如果用户要求"运营模型"，必须有"运营产品化"类别

### 【创新类别】(1-2个) 🆕

如果本项目具有以下特点之一，请设计1-2个**创新类别**：
- 特殊用户群体（自闭症/残障/康复等）→ 设计"特殊需求适配系统"
- 技术创新驱动（BIM/智能化/AI）→ 设计"技术集成与验证策略"
- 极端环境挑战（极寒/沙漠/水下）→ 设计"极端条件适应性设计"
- 跨界融合实验（艺术+科技+社会）→ 设计"跨学科整合方法论"

创新类别要求：
- 必须与项目的独特性/挑战性强相关
- 类别名称体现创新维度（如"感统训练空间系统"、"气候模拟与韧性验证"）
- 不要为了创新而创新，如项目为常规类型则无需强行添加

### 【任务数量配置】

- 为每个类别指定子任务数量（subtask_count: 2-5个，根据重要性调整）
- 总任务数应在{llm_task_count_min}-{llm_task_count_max}个之间

输出JSON格式（注意：使用单层花括号）：
```json
{{
  "outline": [
    {{"category": "概念建构与设计哲学", "ability_core": ["concept"], "subtask_count": 4, "priority": "high", "description": "提炼核心设计理念和叙事主题"}},
    {{"category": "空间结构与动线策略", "ability_core": ["spatial"], "subtask_count": 5, "priority": "high", "description": "建立空间组织逻辑和尺度规则"}},
    {{"category": "材料系统与构造策略", "ability_core": ["material"], "subtask_count": 4, "priority": "medium", "description": "构建材料语言体系和构造逻辑"}}
  ],
  "ability_coverage": ["concept", "spatial", "material", "functional", "capital", "environmental", "operational", "cultural"],
  "missing_abilities": ["lighting", "technical", "social", "narrative"],
  "missing_reason": "本项目为商业空间设计，暂不涉及灯光专项、技术集成等维度",
  "total_tasks": {llm_task_count_min}-{llm_task_count_max}
}}
```

⚠️ 重要：
- JSON中必须使用单层花括号 {{ }}，不要使用双层花括号 {{{{ }}}}
- ability_core字段必须从12个标准值中选择: concept, spatial, narrative, material, lighting, functional, capital, technical, social, environmental, operational, cultural

现在开始制定大纲："""

            # 🆕 v8.2 P1-A: 注入 Mode Engine guidance（从 mode_ability_activation.yaml）
            if detected_modes and _mode_activation_cfg:
                _sorted_modes = sorted(detected_modes, key=lambda m: m.get("confidence", 0), reverse=True)
                _mode_guidance_parts = []
                for _m in _sorted_modes[:2]:  # 最多取主/次模式
                    _mid = _m.get("mode", "")
                    _mconf = _m.get("confidence", 0.0)
                    if _mid not in _mode_activation_cfg or _mconf < 0.3:
                        continue
                    _entry = _mode_activation_cfg[_mid]
                    _essence = _entry.get("mode_essence", "")
                    _primary = _entry.get("primary_abilities", [])
                    _is_primary = (_m == _sorted_modes[0])
                    _strength = "主要" if _is_primary else "次要"
                    _part = f"  **{_mid}**（{_strength}，置信度 {_mconf:.0%}）\n"
                    if _essence:
                        _part += f"  设计DNA: {_essence}\n"
                    if _primary:
                        _focus_list = [f"{ab.get('id', '')}({ab.get('focus', '')})" for ab in _primary[:3]]
                        _part += f"  核心能力焦点: {' / '.join(_focus_list)}\n"
                    _mode_guidance_parts.append(_part)
                
                if _mode_guidance_parts:
                    _injection_strength = "建议参考" if _sorted_modes[0].get("confidence", 0) < 0.6 else "推荐采纳"
                    _mode_block = f"\n\n## 🧬 项目设计模式识别（{_injection_strength}）\n\n"
                    _mode_block += "以下模式反映了本项目的设计DNA，可据此调整类别结构和能力侧重：\n\n"
                    _mode_block += "\n".join(_mode_guidance_parts)
                    _mode_block += "\n💡 模式信息仅用于辅助你理解项目特征，不限制你的类别创新。\n"
                    outline_prompt += _mode_block
                    logger.info(f"✅ [v8.2 P1-A] Phase 1 已注入 Mode guidance: {[m.get('mode') for m in _sorted_modes[:2]]}")

            # 🆕 v8.2 P1-B: 注入 Feature Vector 可视化
            if project_features:
                _sorted_feats = sorted(project_features.items(), key=lambda x: x[1], reverse=True)
                _feat_labels = {
                    'cultural': '文化认同', 'commercial': '商业价值', 'wellness': '健康疗愈',
                    'technical': '技术创新', 'sustainable': '可持续发展', 'professional': '专业赋能',
                    'inclusive': '包容性设计', 'functional': '功能实用', 'emotional': '情感共鸣',
                    'aesthetic': '美学体验', 'social': '社交连接', 'mixed': '综合需求'
                }
                _fv_lines = ["\n\n## 📊 项目特征向量（重点提示）\n"]
                _fv_lines.append("高分维度应获得更多任务覆盖，低分维度可精简：\n")
                for _fid, _fscore in _sorted_feats[:6]:  # 仅展示TOP6，控制prompt长度
                    _flabel = _feat_labels.get(_fid, _fid)
                    _bar = "█" * int(_fscore * 15)
                    _marker = " 🔥" if _fscore >= 0.7 else (" ⭐" if _fscore >= 0.5 else "")
                    _fv_lines.append(f"  {_flabel:8s}: {_fscore:.2f} {_bar}{_marker}")
                outline_prompt += "\n".join(_fv_lines) + "\n"
                logger.info(f"✅ [v8.2 P1-B] Phase 1 已注入 Feature Vector (TOP3: {', '.join([_feat_labels.get(f[0], f[0]) for f in _sorted_feats[:3]])})")

            # 🆕 v8.2 P2: Phase 1 使用 SystemMessage 提供角色设定
            outline_messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=outline_prompt)
            ]
            outline_response = await llm.ainvoke(outline_messages)
            outline_text = outline_response.content if hasattr(outline_response, "content") else str(outline_response)
            
            # 解析大纲
            import json
            import re
            
            # v7.999.9: 使用括号平衡算法提取完整JSON（修复非贪婪正则在嵌套JSON中截断的致命bug）
            def _extract_balanced_json(text: str) -> str:
                """提取括号平衡的完整JSON对象"""
                # 先尝试从 ```json ... ``` 代码块中提取
                code_block_match = re.search(r'```json\s*', text)
                if code_block_match:
                    search_start = code_block_match.end()
                else:
                    search_start = 0
                
                # 找到第一个 { 的位置
                brace_start = text.find('{', search_start)
                if brace_start == -1:
                    return None
                
                # 括号平衡计数
                depth = 0
                in_string = False
                escape_next = False
                for i in range(brace_start, len(text)):
                    ch = text[i]
                    if escape_next:
                        escape_next = False
                        continue
                    if ch == '\\':
                        escape_next = True
                        continue
                    if ch == '"':
                        in_string = not in_string
                        continue
                    if in_string:
                        continue
                    if ch == '{':
                        depth += 1
                    elif ch == '}':
                        depth -= 1
                        if depth == 0:
                            return text[brace_start:i+1]
                return None
            
            balanced_json = _extract_balanced_json(outline_text)
            
            if balanced_json:
                try:
                    outline_data = json.loads(balanced_json)
                except json.JSONDecodeError as je:
                    logger.warning(f"⚠️ Phase 1 JSON解析失败: {je}，尝试多阶段修复...")
                    fixed = balanced_json
                    # 修复1: 移除行内注释
                    fixed = re.sub(r'//[^\n]*', '', fixed)
                    # 修复2: 移除尾随逗号（对象/数组末尾多余逗号）
                    fixed = re.sub(r',\s*([}\]])', r'\1', fixed)
                    # 修复3: 修复缺少逗号（数字/字符串/bool后换行接下一个key）
                    fixed = re.sub(r'("(?:[^"\\]|\\.)*"|true|false|null|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*\n\s*(")', r'\1,\n\2', fixed)
                    # 🔧 修复4: 中文标点→英文标点（LLM常见错误）
                    fixed = fixed.replace('\uff0c', ',').replace('\uff1a', ':').replace('\uff1b', ';')
                    # 🔧 修复5: 修复字符串内未转义的双引号
                    fixed = re.sub(r'(?<=: )"([^"]*?)"([^,}\]\s][^"]*?)"', r'"\1\\"\2"', fixed)
                    # 🔧 修复6 [v7.621]: 修复字符串内的真实换行符（Expecting ',' delimiter 的常见根因）
                    _buf, _in_str, _esc = [], False, False
                    for _ch in fixed:
                        if _esc:
                            _buf.append(_ch)
                            _esc = False
                        elif _ch == '\\':
                            _buf.append(_ch)
                            _esc = True
                        elif _ch == '"':
                            _in_str = not _in_str
                            _buf.append(_ch)
                        elif _in_str and _ch == '\n':
                            _buf.append('\\n')
                        elif _in_str and _ch == '\r':
                            pass
                        else:
                            _buf.append(_ch)
                    fixed = ''.join(_buf)
                    try:
                        outline_data = json.loads(fixed)
                        logger.info("\u2705 Phase 1 JSON多阶段修复成功（6阶段）")
                    except json.JSONDecodeError as je2:
                        logger.warning(f"⚠️ Phase 1 JSON修复后仍失败: {je2}")
                        outline_data = None
            else:
                outline_data = None
            
            # 🔧 P1-C: 大纲解析失败时的重试 + 默认框架模板
            if outline_data is None:
                logger.warning("⚠️ Phase 1 JSON解析失败，尝试重试...")
                retry_success = False
                try:
                    retry_response = await llm.ainvoke(outline_messages)
                    retry_text = retry_response.content if hasattr(retry_response, "content") else str(retry_response)
                    retry_json = _extract_balanced_json(retry_text)
                    if retry_json:
                        retry_fixed = retry_json
                        retry_fixed = re.sub(r'//[^\n]*', '', retry_fixed)
                        retry_fixed = re.sub(r',\s*([}\]])', r'\1', retry_fixed)
                        retry_fixed = re.sub(r'("(?:[^"\\]|\\.)*"|true|false|null|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*\n\s*(")', r'\1,\n\2', retry_fixed)
                        retry_fixed = retry_fixed.replace('\uff0c', ',').replace('\uff1a', ':').replace('\uff1b', ';')
                        # 🔧 修复6 [v7.621]: 修复字符串内的真实换行符
                        _r_buf, _r_in, _r_esc = [], False, False
                        for _rc in retry_fixed:
                            if _r_esc:
                                _r_buf.append(_rc)
                                _r_esc = False
                            elif _rc == '\\':
                                _r_buf.append(_rc)
                                _r_esc = True
                            elif _rc == '"':
                                _r_in = not _r_in
                                _r_buf.append(_rc)
                            elif _r_in and _rc == '\n':
                                _r_buf.append('\\n')
                            elif _r_in and _rc == '\r':
                                pass
                            else:
                                _r_buf.append(_rc)
                        retry_fixed = ''.join(_r_buf)
                        outline_data = json.loads(retry_fixed)
                        outline = outline_data.get("outline", [])
                        if outline and len(outline) >= 3:
                            logger.info(f"\u2705 Phase 1 重试成功: 生成{len(outline)}个类别")
                            retry_success = True
                except Exception as retry_err:
                    logger.warning(f"⚠️ Phase 1 重试也失败: {retry_err}")
                
                if not retry_success:
                    # 🔧 P1-C: 使用默认框架模板（模式感知：M5乡建使用Ability Core分类）
                    logger.warning("⚠️ Phase 1 彻底失败，使用默认框架模板")
                    
                    # 检测是否是乡建/M5场景 → 使用12 Ability Core导向的分类
                    _rural_kws = ["乡村", "乡建", "新农村", "民宿集群", "农耕", "在地", "村落", "振兴"]
                    _is_rural = any(kw in user_input for kw in _rural_kws)
                    
                    if _is_rural:
                        # 乡建/M5专用分类：基于Ability Core框架
                        logger.info("📋 [乡建模式] 使用12 Ability Core导向的分类框架")
                        outline_data = {"outline": [
                            {"category": "概念建构与在地文化解码", "subtask_count": 4, "priority": "high",
                             "description": "核心设计命题提炼、地域文化结构分析、在地性验证（脱离该地域是否仍成立）"},
                            {"category": "空间结构与聚落形态设计", "subtask_count": 4, "priority": "high",
                             "description": "村落空间组织逻辑、公共-半公共-私密层级、动线分离策略"},
                            {"category": "叙事节奏与体验路径设计", "subtask_count": 3, "priority": "high",
                             "description": "到达-压缩-释放-沉浸-记忆的完整叙事弧线、场景节点设计"},
                            {"category": "材料系统与在地工艺整合", "subtask_count": 4, "priority": "high",
                             "description": "本地材料清单、与现代工艺结合方案、成本可控性与可维护性评估"},
                            {"category": "功能效率与运营动线优化", "subtask_count": 3, "priority": "medium",
                             "description": "主客动线分离、后勤隐藏、功能组团效率评估"},
                            {"category": "资本策略与产业闭环模型", "subtask_count": 4, "priority": "high",
                             "description": "住宿+餐饮+手工艺+农产品+教育体验闭环、独立现金流模型、投资回报周期"},
                            {"category": "社会建模与村民受益机制", "subtask_count": 3, "priority": "medium",
                             "description": "村民受益者角色设计、游客参与式体验、三方利益平衡与冲突缓冲"},
                            {"category": "环境适应与被动式气候策略", "subtask_count": 3, "priority": "medium",
                             "description": "气候响应构造技术、自然通风采光、雨水管理、材料耐久性评估"},
                            {"category": "运营产品化与品牌体系", "subtask_count": 3, "priority": "medium",
                             "description": "骨架标准化+表皮可变路径、软装更新周期、IP打造与品牌视觉系统"},
                            {"category": "文明表达与跨学科整合", "subtask_count": 2, "priority": "low",
                             "description": "乡村第三条路（非城市化、非博物馆化）、50年视角可持续文化传承"},
                        ]}
                    else:
                        # 通用默认分类
                        outline_data = {"outline": [
                            {"category": "场地调研与环境分析", "subtask_count": 3, "priority": "high", "description": "场地环境、气候、地形、基础设施现状调研"},
                            {"category": "案例调研与设计对标", "subtask_count": 4, "priority": "high", "description": "相关案例研究、设计师方法论分析"},
                            {"category": "概念与文化策略", "subtask_count": 3, "priority": "high", "description": "设计概念提炼、文化元素整合"},
                            {"category": "空间策略与功能规划", "subtask_count": 4, "priority": "medium", "description": "空间组织、功能布局、动线设计"},
                            {"category": "材料与技术策略", "subtask_count": 3, "priority": "medium", "description": "材料选型、构造方式、技术集成"},
                            {"category": "运营策略与商业模型", "subtask_count": 3, "priority": "medium", "description": "运营模式、盈利策略、产品化设计"},
                            {"category": "可持续与环境适应", "subtask_count": 2, "priority": "medium", "description": "生态策略、节能设计、气候响应"},
                        ]}
                    logger.info(f"📋 [默认框架] 使用{'乡建Ability Core(10类)' if _is_rural else '通用7类'}模板")
            
            # 统一的大纲处理（无论来自LLM解析、重试、还是默认模板）
            outline = outline_data.get("outline", [])
            logger.info(f"\u2705 Phase 1完成: 生成{len(outline)}个任务类别")
            # v8.001: 记录大纲类别顺序（用于后续Merge保持类别分组）
            outline_category_order = [item.get('category', '') for item in outline if item.get('category')]
            logger.info(f"\U0001f4cb [v8.001] 类别顺序: {outline_category_order}")
            
            # 🆕 P0改进：记录12 Ability Core覆盖情况
            ability_coverage = outline_data.get("ability_coverage", [])
            missing_abilities = outline_data.get("missing_abilities", [])
            missing_reason = outline_data.get("missing_reason", "")
            
            if ability_coverage:
                logger.info(f"\U0001f3af [12 Ability Core] 已覆盖 {len(ability_coverage)}/12: {', '.join(ability_coverage)}")
            if missing_abilities:
                logger.warning(f"⚠️ [12 Ability Core] 缺失 {len(missing_abilities)}/12: {', '.join(missing_abilities)}")
                if missing_reason:
                    logger.info(f"   缺失原因: {missing_reason}")
            
            # Phase 2: 按大纲生成详细任务
            logger.info("\U0001f4dd Phase 2: 按类别生成详细任务...")
            llm_tasks = []

            for idx, category_info in enumerate(outline, 1):
                category = category_info.get("category", "")
                subtask_count = category_info.get("subtask_count", 2)
                priority = category_info.get("priority", "medium")
                category_desc = category_info.get("description", "")

                # v8.001: 收集已覆盖的具体研究对象（从source_keywords提取）
                covered_subjects: list[str] = []
                for prev_task in llm_tasks:
                    covered_subjects.extend(prev_task.get("source_keywords", []))
                seen_subjects: set[str] = set()
                unique_covered: list[str] = []
                for kw in reversed(covered_subjects):
                    if kw not in seen_subjects and len(kw) > 1:
                        seen_subjects.add(kw)
                        unique_covered.append(kw)
                    if len(unique_covered) >= 15:
                        break
                unique_covered.reverse()
                
                # 🔧 P1-B+: 同时收集已生成任务的标题
                covered_titles = [t.get('title', '') for t in llm_tasks[-15:] if t.get('title')]

                cross_category_constraint = ""
                if unique_covered or covered_titles:
                    constraint_parts = []
                    constraint_parts.append("\u26a0\ufe0f **跨类别重复限制**（v8.001）：")
                    if unique_covered:
                        constraint_parts.append("以下研究对象已在前面的类别中被覆盖，本类别**请勿重复引用同一主体**：")
                        constraint_parts.extend(f'  - {kw}' for kw in unique_covered)
                    if covered_titles:
                        constraint_parts.append("\n已生成的任务标题（避免重复相同角度）：")
                        constraint_parts.extend(f'  {i+1}. {t}' for i, t in enumerate(covered_titles))
                    constraint_parts.append("如需研究上述对象的不同维度，需使用完全不同的任务切入点。")
                    cross_category_constraint = chr(10).join(constraint_parts)

                category_prompt = f"""请为类别"{category}"生成{subtask_count}个详细任务。

项目背景：
{user_input}

结构化摘要：
{structured_summary}

类别要求：
- 类别名称：{category}
- 类别说明：{category_desc}
- 任务数量：{subtask_count}个
- 优先级：{priority}

\u26a0\ufe0f **任务生成要求**：
1. **任务标题必须体现项目的具体信息**（地点、人物、文化元素、设计师风格等）
2. **任务描述必须包含可执行的具体行动**（调研什么、分析什么、设计什么）
3. **任务应该是该类别下的具体子任务**，而不是重复类别名称
4. 避免使用通用模板化语言
5. **每个任务必须包含 dimensions 字段**（3-5个具体分析维度）
{cross_category_constraint}
示例对比（假设类别是"场地调研与分析"）：
- \u274c 错误："场地调研与分析" → "对项目场地进行全面调研..."（重复类别名）
- \u2705 正确："[项目地名]地形地貌与自然景观调研" → "调研项目所在地的地形高差、水系分布、植被类型..."
- \u2705 正确："[项目地名]气候特征与微气候分析" → "收集项目所在地的温度、湿度、风向、日照数据..."

\u26a0\ufe0f **重要说明**：
- 这是**任务梳理阶段**（问卷第一步），仅定义需要执行的任务
- **不涉及概念图生成**，不要包含needs_concept_image和concept_image_count字段
- 每个任务必须添加category字段，值为"{category}"

输出JSON格式（注意：使用单层花括号）：
```json
{{
  "tasks": [
    {{
      "id": "task_{idx}_1",
      "title": "具体任务标题（必须包含项目特定信息）",
      "description": "详细任务描述（必须包含可执行的具体行动）",
      "category": "{category}",
      "source_keywords": ["关键词1", "关键词2", "关键词3"],
      "task_type": "research",
      "priority": "{priority}",
      "dependencies": [],
      "execution_order": {idx},
      "support_search": true,
      "dimensions": ["维度1", "维度2", "维度3"],
      "ability_tags": []
    }}
  ]
}}
```

\u26a0\ufe0f 重要：JSON中必须使用单层花括号 {{ }}，不要使用双层花括号 {{{{ }}}}

现在生成{subtask_count}个任务："""

                # 🆕 v8.2 P0-A: 注入 Ability Core Essentials（判断标准 + 常见误区）
                _category_abilities = category_info.get("ability_core", [])
                if _category_abilities and _ability_essentials_cfg:
                    # ability_core 值格式: ["concept", "spatial"] → 映射到 A1_concept_architecture 等
                    _ABILITY_SHORT_TO_FULL = {
                        "concept": "A1_concept_architecture", "spatial": "A2_spatial_structuring",
                        "narrative": "A3_narrative_orchestration", "material": "A4_material_intelligence",
                        "lighting": "A5_lighting_architecture", "functional": "A6_functional_optimization",
                        "capital": "A7_capital_strategy", "technical": "A8_technology_integration",
                        "social": "A9_social_structure_modeling", "environmental": "A10_environmental_adaptation",
                        "operational": "A11_operation_productization", "cultural": "A12_civilizational_expression",
                    }
                    _ess_lines = []
                    for _ab_short in _category_abilities[:2]:  # 最多注入2个能力的标准，控制prompt长度
                        _ab_full = _ABILITY_SHORT_TO_FULL.get(_ab_short, "")
                        _ess = _ability_essentials_cfg.get(_ab_full, {})
                        if not _ess:
                            continue
                        _ab_name = _ess.get("name", _ab_short)
                        _criteria = _ess.get("judgment_criteria", [])
                        _mistakes = _ess.get("common_mistakes", [])
                        _line = f"\n**{_ab_name}** 质量标准："
                        if _criteria:
                            _line += f"\n  ✓ {_criteria[0]}"
                            if len(_criteria) > 1:
                                _line += f"\n  ✓ {_criteria[1]}"
                        if _mistakes:
                            _line += f"\n  ✗ 避免: {_mistakes[0]}"
                        _ess_lines.append(_line)
                    
                    if _ess_lines:
                        _ess_block = "\n\n## 📋 本类别能力判断标准（Ability Core Essentials）\n"
                        _ess_block += "生成的任务应触达以下深度，避免常见误区：\n"
                        _ess_block += "\n".join(_ess_lines) + "\n"
                        category_prompt += _ess_block
                        logger.debug(f"  📋 [v8.2 P0-A] {category}: 注入 {len(_ess_lines)} 个能力标准")

                # 🆕 v8.2 P0-B: 注入类别级 Few-shot 片段（从已选 example 按 task_type 过滤）
                if _selected_ideal_tasks:
                    # 推断本类别的主要 task_type
                    _cat_lower = category.lower()
                    _inferred_type = "research"  # 默认
                    if any(kw in _cat_lower for kw in ["分析", "评估", "对比", "策略"]):
                        _inferred_type = "analysis"
                    elif any(kw in _cat_lower for kw in ["设计", "规划", "整合", "创新", "方案"]):
                        _inferred_type = "design"
                    
                    # 按 task_type 过滤 + 宽松匹配（无精确匹配时放宽到全部）
                    _type_matched = [t for t in _selected_ideal_tasks if t.get("task_type", "") == _inferred_type]
                    if not _type_matched:
                        _type_matched = _selected_ideal_tasks  # fallback: 不过滤
                    
                    _fragment_tasks = _type_matched[:3]  # 最多3个
                    if _fragment_tasks:
                        _frag_block = f"\n\n## 📚 类别参考示例（{_inferred_type}类任务片段）\n"
                        _frag_block += f"来自参考案例「{_selected_example_name}」的同类任务（仅参考格式和粒度）：\n"
                        for _fi, _ft in enumerate(_fragment_tasks, 1):
                            _frag_block += f"  {_fi}. {_ft.get('title', '未命名')}\n"
                        _frag_block += "⚠️ 请勿照搬内容，仅参考拆解粒度和维度数量。\n"
                        category_prompt += _frag_block
                        logger.debug(f"  📚 [v8.2 P0-B] {category}: 注入 {len(_fragment_tasks)} 个{_inferred_type}类任务片段")

                # 🆕 v8.2 P2: Phase 2 使用 SystemMessage 提供角色设定
                category_messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=category_prompt)
                ]
                category_response = await llm.ainvoke(category_messages)
                category_text = category_response.content if hasattr(category_response, "content") else str(category_response)

                category_tasks = decomposer.parse_response(category_text)

                # v9.0: 自动填充 ability_tags（从 category_info.ability_core 映射到完整 ID）
                _ABILITY_SHORT_TO_FULL_POST = {
                    "concept": "A1_concept_architecture", "spatial": "A2_spatial_structuring",
                    "narrative": "A3_narrative_orchestration", "material": "A4_material_intelligence",
                    "lighting": "A5_lighting_architecture", "functional": "A6_functional_optimization",
                    "capital": "A7_capital_strategy", "technical": "A8_technology_integration",
                    "social": "A9_social_structure_modeling", "environmental": "A10_environmental_adaptation",
                    "operational": "A11_operation_productization", "cultural": "A12_civilizational_expression",
                }
                _cat_abilities = category_info.get("ability_core", [])
                _full_tags = [_ABILITY_SHORT_TO_FULL_POST[a] for a in _cat_abilities if a in _ABILITY_SHORT_TO_FULL_POST]

                for task in category_tasks:
                    if 'category' not in task:
                        task['category'] = category
                    # v9.0: 若 LLM 未返回 ability_tags，从类别配置自动填充
                    if not task.get('ability_tags') and _full_tags:
                        task['ability_tags'] = _full_tags

                llm_tasks.extend(category_tasks)
                logger.info(f"  \u2705 {category}: 生成{len(category_tasks)}个任务")

            logger.info(f"\U0001f389 Phase 2完成: 总计生成{len(llm_tasks)}个任务")
            
            # P1-1: 跨类别语义去重
            if len(llm_tasks) > 1:
                logger.info("\U0001f504 [P1-1] 开始跨类别语义去重...")
                original_count = len(llm_tasks)
                llm_tasks = _deduplicate_across_categories(llm_tasks)
                removed_count = original_count - len(llm_tasks)
                if removed_count > 0:
                    logger.info(f"\u2705 [P1-1] 跨类别去重完成: 移除{removed_count}个重复任务，保留{len(llm_tasks)}个")
                else:
                    logger.info(f"\u2705 [P1-1] 跨类别去重完成: 无重复，保持{len(llm_tasks)}个任务")

            # 质量验证
            quality_issues_phase2 = []
            category_distribution = {}
            for task in llm_tasks:
                cat = task.get('category', 'unknown')
                category_distribution[cat] = category_distribution.get(cat, 0) + 1

            if len(category_distribution) > 12:
                quality_issues_phase2.append(f"类别过多: {len(category_distribution)}个（建议8-10个）")
            elif len(category_distribution) < 6:
                quality_issues_phase2.append(f"类别过少: {len(category_distribution)}个（建议8-10个）")

            for cat, count in category_distribution.items():
                if count < 2:
                    quality_issues_phase2.append(f"类别'{cat}'任务过少: {count}个（建议2-5个）")
                if count > 6:
                    quality_issues_phase2.append(f"类别'{cat}'任务过多: {count}个（建议2-5个）")

            if quality_issues_phase2:
                logger.warning(f"\u26a0\ufe0f 任务质量问题 ({len(quality_issues_phase2)}个):")
                for issue in quality_issues_phase2:
                    logger.warning(f"  - {issue}")
            else:
                logger.info(f"\u2705 任务质量验证通过: {len(category_distribution)}个类别，分布均衡")
            
        except Exception as phase_error:
            # 降级：两阶段生成彻底失败，回退到标准调用
            logger.warning(f"⚠️ [两阶段生成] 失败，回退到标准调用: {phase_error}")
            outline_category_order = []  # v8.001: 降级时无类别顺序
            messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
            response = await llm.ainvoke(messages)
            response_text = response.content if hasattr(response, "content") else str(response)
            llm_tasks = decomposer.parse_response(response_text)
            
            # 🔧 P0-B: 降级路径后置分类 — 对无category的任务进行规则分组
            _fallback_classify_tasks(llm_tasks, user_input)
        
        logger.info(f"✅ [Track A] LLM生成完成: {len(llm_tasks)}个任务")
        
    except Exception as e:
        import traceback
        stack_trace = traceback.format_exc()
        logger.error(
            f"❌ [Track A] LLM生成失败详情:\n"
            f"{'='*80}\n"
            f"错误类型: {type(e).__name__}\n"
            f"错误信息: {str(e)}\n"
            f"{'='*80}\n"
            f"Stack Trace:\n{stack_trace}\n"
            f"{'='*80}"
        )
        llm_tasks = []
    
    # Step 4: Track B - 规则生成 (并行, 不依赖LLM结果)
    logger.info("📐 [Track B] 规则生成开始...")
    # 🆕 P1: 从 structured_data 提取 detected_modes
    detected_modes = structured_data.get('detected_design_modes', []) if structured_data else []
    rule_tasks = _generate_rule_based_tasks(
        user_input, structured_data, project_features, 
        task_count=rule_task_count,
        detected_modes=detected_modes  # 🆕 P1: 传递detected_modes
    )
    logger.info(f"✅ [Track B] 规则生成完成: {len(rule_tasks)}个任务")
    
    # 检查特殊情况: LLM完全失败
    if not llm_tasks and not rule_tasks:
        logger.error("❌ [混合策略] LLM和规则均失败, 使用降级策略")
        return _simple_fallback_decompose(user_input, structured_data, complexity_analysis)
    
    # Step 5: 智能融合
    logger.info(f"🔀 [混合策略] 开始融合: LLM={len(llm_tasks)}个 + 规则={len(rule_tasks)}个")
    # v8.001: 传入 outline_category_order 以保留 Phase 1 类别分组顺序
    merged_tasks = _merge_hybrid_tasks(llm_tasks, rule_tasks, max_tasks=recommended_max, category_order=outline_category_order)
    
    # Step 6: 质量验证 (保留v7.970机制)
    if merged_tasks and project_features:
        is_valid, validation_errors = _validate_task_granularity(merged_tasks, project_features)
        
        if not is_valid:
            logger.warning(f"⚠️ [混合策略] 任务质量验证发现{len(validation_errors)}个问题:")
            for error in validation_errors:
                logger.warning(f"  {error}")
        else:
            logger.info("✅ [混合策略] 任务质量验证通过")
    
    # Step 6.1 (P2-D2): 多源整合任务检测与生成
    integration_info = _detect_multi_reference_sources(user_input, structured_data)
    if integration_info['detected']:
        integration_tasks = _generate_integration_tasks(integration_info, user_input)
        if integration_tasks:
            merged_tasks.extend(integration_tasks)
            logger.info(f"✅ [P2-D2] 追加 {len(integration_tasks)} 个多源整合任务")
    
    # Step 6.2 (P2-D4): 用户意图覆盖校验
    user_requirements = _extract_user_requirements(user_input)
    if user_requirements:
        uncovered_reqs = _validate_requirement_coverage(merged_tasks, user_requirements)
        if uncovered_reqs:
            gap_tasks = _generate_coverage_gap_tasks(uncovered_reqs, user_input)
            if gap_tasks:
                merged_tasks.extend(gap_tasks)
                logger.info(f"✅ [P2-D4] 追加 {len(gap_tasks)} 个意图覆盖补充任务")
    
    # Step 6.3 (P2-D1): 维度字段强制注入
    _ensure_task_dimensions(merged_tasks)
    
    # 重新编号所有任务（确保D2/D4追加的任务有正确的id和顺序）
    for idx, task in enumerate(merged_tasks, 1):
        task['id'] = f"task_{idx}"
        task['execution_order'] = idx
    
    # Step 7: 添加motivation_label (v7.106机制)
    if merged_tasks:
        await decomposer._infer_task_metadata_async(merged_tasks, user_input, structured_data)
    
    # 🆕 v7.999.9: 改进补充机制 - 降低阈值到85%，并使用分批补充策略
    # 旧版70%阈值导致很多不达标的情况被跳过（如推荐40个但只生成28个时=70%刚好不触发）
    min_acceptable_tasks = int(recommended_min * 0.85)  # v7.999.9: 70%→85%
    
    if len(merged_tasks) < min_acceptable_tasks:
        shortage = recommended_min - len(merged_tasks)
        logger.warning(f"⚠️ [混合策略] 任务总数{len(merged_tasks)}低于推荐最小值{recommended_min}（仅为目标的{len(merged_tasks)/recommended_min*100:.0f}%，<85%阈值）")
        logger.warning(f"🔄 [混合策略 v7.999.9] 启动分批补充机制（总需补充{shortage}个）...")
    elif len(merged_tasks) < recommended_min:
        # 85%-100%范围内，只警告但不补充
        logger.info(f"ℹ️ [混合策略] 任务总数{len(merged_tasks)}略少于推荐最小值{recommended_min}（达到{len(merged_tasks)/recommended_min*100:.0f}%，在可接受范围内）")
        shortage = 0
    else:
        shortage = 0
    
    if shortage > 0:
        # 🆕 v7.999.9: 分批补充策略 - 每批最多补充10个任务，多轮迭代
        # 解决一次性要求LLM补充28+个任务时可靠性极低的问题
        try:
            if llm is None:
                from ..services.llm_factory import LLMFactory
                llm = LLMFactory.create_llm()
            
            from langchain_core.messages import HumanMessage
            
            remaining_shortage = shortage
            max_supplement_rounds = 3  # 最多3轮补充，避免无限循环
            batch_size = min(12, remaining_shortage)  # 每批最多12个
            
            for round_num in range(1, max_supplement_rounds + 1):
                if remaining_shortage <= 0:
                    break
                
                current_batch = min(batch_size, remaining_shortage)
                logger.info(f"🔄 [补充第{round_num}轮] 请求生成{current_batch}个任务（剩余缺口{remaining_shortage}个）")
                
                existing_titles = chr(10).join([f"{i+1}. {t.get('title', '未命名')}" for i, t in enumerate(merged_tasks)])
                
                # v8.001: 提取已有任务的category分布，用于补充任务归档
                existing_categories = list(dict.fromkeys(
                    t.get('category', '') for t in merged_tasks if t.get('category')
                ))
                category_hint = ""
                if existing_categories:
                    category_hint = f"\n已有任务类别分布: {', '.join(existing_categories)}\n请为每个补充任务分配最合适的category（从上述类别中选择，或新建类别）。"
                
                retry_prompt = f"""你是设计项目任务拆解专家。请为以下项目补充生成{current_batch}个新任务。

项目信息：
{user_input[:800]}

已有{len(merged_tasks)}个任务，标题列表：
{existing_titles}
{category_hint}
请补充{current_batch}个新任务，要求：
1. 不得与已有任务重复（调研新的对象或维度）
2. 标题格式：动词 + 具体对象 + 3-5个调研维度
3. 任务类型分布：约70% research, 30% analysis
4. 任务应紧密围绕项目核心诉求表达
5. 包含项目的具体信息（地点、功能、品牌等）
6. 每个任务必须包含 category 字段（所属框架分类，从已有类别中选择）

返回纯JSON（不要markdown代码块标记）：
{{"tasks": [{{"id": "task_N", "title": "搜索/调研 具体对象的 维度1、维度2、维度3", "description": "详细说明", "category": "所属类别", "source_keywords": ["词1", "词2"], "task_type": "research", "priority": "high", "dependencies": [], "execution_order": N, "support_search": true}}]}}"""
                
                retry_response = await llm.ainvoke([HumanMessage(content=retry_prompt)])
                retry_text = retry_response.content if hasattr(retry_response, "content") else str(retry_response)
                
                additional_tasks = decomposer.parse_response(retry_text)
                if additional_tasks:
                    next_task_id = len(merged_tasks) + 1
                    for i, task in enumerate(additional_tasks):
                        task['id'] = f"task_{next_task_id + i}"
                        task['execution_order'] = next_task_id + i
                    merged_tasks.extend(additional_tasks)
                    remaining_shortage -= len(additional_tasks)
                    logger.info(f"✅ [补充第{round_num}轮] 成功补充{len(additional_tasks)}个任务，当前总计{len(merged_tasks)}个")
                else:
                    logger.warning(f"⚠️ [补充第{round_num}轮] 解析失败，停止补充")
                    break
            
            if remaining_shortage > 0:
                logger.warning(f"⚠️ [混合策略] 补充后仍缺少{remaining_shortage}个任务，当前{len(merged_tasks)}个")
            else:
                logger.info(f"✅ [混合策略] 分批补充完成，最终{len(merged_tasks)}个任务")
                
        except Exception as e:
            logger.error(f"❌ [混合策略] 补充机制执行失败: {e}")
            logger.warning(f"⚠️ [混合策略] 继续使用当前{len(merged_tasks)}个任务")
    
    # P0-F3: 补充任务动机推断 - 对缺少motivation_type的补充任务统一推断元数据
    tasks_needing_metadata = [t for t in merged_tasks if not t.get('motivation_type')]
    if tasks_needing_metadata:
        try:
            logger.info(f"🔄 [P0-F3] 对 {len(tasks_needing_metadata)} 个补充任务进行动机推断...")
            await decomposer._infer_task_metadata_async(tasks_needing_metadata, user_input, structured_data)
            logger.info("✅ [P0-F3] 补充任务动机推断完成")
        except Exception as e:
            logger.warning(f"⚠️ [P0-F3] 补充任务动机推断失败: {e}")
    
    # 🆕 P2-2: 优先级分层策略（基于任务类型和交付物依赖）
    _stratify_task_priorities(merged_tasks, user_input, structured_data)

    # 🔧 P0-B: 最终分类兜底 — 确保所有任务都有有意义的category
    tasks_without_category = [t for t in merged_tasks if not t.get('category') or t['category'] in ('', '基础调研')]
    if len(tasks_without_category) > len(merged_tasks) * 0.5:
        # 超过50%的任务缺少分类，执行后置分类
        logger.info(f"🔧 [P0-B] 检测到{len(tasks_without_category)}/{len(merged_tasks)}个任务缺少分类，执行后置分类...")
        _fallback_classify_tasks(merged_tasks, user_input)

    logger.info(f"🎉 [混合策略] 完成! 最终任务数: {len(merged_tasks)}")
    return merged_tasks


# 同步版本（用于非异步上下文）
def decompose_core_tasks_sync(
    user_input: str, structured_data: Optional[Dict[str, Any]] = None, llm: Optional[Any] = None
) -> List[Dict[str, Any]]:
    """
    同步执行核心任务拆解

    Args:
        user_input: 用户原始输入
        structured_data: 需求分析阶段产出的结构化数据 (可选)
        llm: LLM 实例 (可选)

    Returns:
        任务列表
    """
    import asyncio

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 如果已经在事件循环中，使用回退策略
            logger.warning("️ 检测到运行中的事件循环，使用回退策略")
            return _simple_fallback_decompose(user_input)
        else:
            return loop.run_until_complete(decompose_core_tasks(user_input, structured_data, llm))
    except RuntimeError:
        # 没有事件循环，创建一个
        return asyncio.run(decompose_core_tasks(user_input, structured_data, llm))
