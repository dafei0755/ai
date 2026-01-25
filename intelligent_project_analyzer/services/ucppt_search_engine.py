"""
ucppt 深度迭代搜索引擎 (v7.207)

实现 ucppt 范式的"目标导向探索引擎"：

v7.207 更新（L0+L1-L5 统一分析）：
- 合并分析：将 L0 对话分析和 L1-L5 深度分析合并为单次 LLM 调用
- 统一模型：使用 thinking_model (DeepSeek-Reasoner) 同时输出对话内容和结构化分析
- 响应加速：从 2 次 LLM 调用减少到 1 次，预计节省 3-5 秒
- 输出分流：thinking 内容作为对话输出，content 包含 JSON 框架
- 事件简化：unified_analysis_chunk (对话), question_analyzed (框架)

v7.206 更新（L0 对话式任务理解 - 已合并到 v7.207）：
- 对话式输出：L0 结构化信息提取改为对话式自然语言输出
- JSON 内部化：结构化 JSON 仅供系统内部使用，不展示给用户

v7.204 更新（统一思考流 - 消除轮次间停顿）：
- 融合思考+反思：将原来每轮2次LLM调用（思考+反思）合并为1次
- 消除停顿：反思在下一轮思考中完成，不再有独立的等待期
- 首轮优化：首轮无上轮结果，prompt 跳过"回顾"部分
- 减少Token：避免重复传递上下文，预计减少30-40%消耗
- 新数据结构：UnifiedThinkingResult 统一输出回顾+规划+校准

v7.199 更新（搜索质量全面增强）：
- 查询分类器：识别学术/新闻/案例等8种查询类型
- OpenAlex 学术搜索：学术类查询时自动调用 2.5亿+ 学术论文库
- 语义去重：使用 embedding 向量去除语义相似的结果
- 动态权重：根据查询类型调整时效性/可信度权重

核心理念：
- 用户问题导向：所有过程都指向最后的结果
- 层层递进：每一步都在向"完美回答"靠近
- 完成度追踪：不是"发现了多少"，而是"还差多少能回答完整"
- 动态停止：当能够完整回答用户问题时自动结束

关键机制：
1. 问题分析 - 理解用户真正想要的答案是什么
2. 关键面追踪 - 识别回答问题需要的关键信息面
3. 目标导向搜索 - 每轮搜索都为填补回答的空白
4. 完成度评估 - "能否完整回答？还缺什么？"
5. 答案聚焦 - 所有信息最终服务于生成最佳答案

v7.195 更新（网页内容深度提取）：
- 混合提取方案：Trafilatura(静态) + Playwright(动态)
- 智能策略：已知动态站点直接用 Playwright，其他先 Trafilatura 再降级
- Top-5 深度提取：每轮搜索对前5条结果进行内容深度获取
- 低质量站点过滤：百家号等低质量来源跳过深度提取
- 配置开关：DEEP_CONTENT_EXTRACTION_ENABLED 控制是否启用

v7.194 更新（答案生成优化）：
- 来源去重：按URL去重避免重复引用
- 400字内容摘要：每条来源包含400字正文摘要，让LLM能真正利用来源内容
- 相关性排序：来源按与问题框架的相关性排序，Top-25进入Prompt
- 累积反思：所有轮次的反思洞察都加入Prompt，充分利用研究过程
- 答案扩容：max_tokens从2000提升到3000，字数要求1000-2000字

v7.192 更新：
- 提高深度标准：最少3轮，最大30轮
- 完成度阈值提升至 0.88
- alignment 阈值提升至 0.92
- 饱和检测需连续3轮无进展且完成度>=0.75
- 必须满足最小轮数才能触发停止

v7.190 更新：
- 答案生成 Prompt 改进：来源列表带编号 [1]、[2]...
- 要求 LLM 使用 [编号] 格式引用来源，便于用户追溯
- round_sources 事件发送全部来源（而非前5条），确保编号一致性

作者: AI Assistant
日期: 2026-01-11
"""

import asyncio
import json
import os
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple, Union

import httpx
from loguru import logger

# 导入现有搜索服务
try:
    from intelligent_project_analyzer.services.bocha_ai_search import (
        BochaAISearchService,
        AISearchResult,
        SourceCard,
        get_ai_search_service,
    )
except ImportError:
    BochaAISearchService = None
    AISearchResult = None
    SourceCard = None
    get_ai_search_service = None

# v7.195: 导入混合网页内容提取器
try:
    from intelligent_project_analyzer.services.web_content_extractor import (
        get_web_content_extractor,
        ExtractionResult,
        ExtractionMethod,
    )
    WEB_EXTRACTOR_AVAILABLE = True
except ImportError:
    get_web_content_extractor = None
    ExtractionResult = None
    ExtractionMethod = None
    WEB_EXTRACTOR_AVAILABLE = False
    logger.warning("⚠️ WebContentExtractor 未可用，使用 snippet 模式")

# v7.199: 导入查询分类器
try:
    from intelligent_project_analyzer.tools.query_classifier import (
        classify_query,
        QueryType,
        QueryClassification,
    )
    QUERY_CLASSIFIER_AVAILABLE = True
except ImportError:
    classify_query = None
    QueryType = None
    QueryClassification = None
    QUERY_CLASSIFIER_AVAILABLE = False
    logger.warning("⚠️ 查询分类器未可用")

# v7.199: 导入 OpenAlex 学术搜索
try:
    from intelligent_project_analyzer.tools.openalex_search import (
        OpenAlexSearchTool,
    )
    OPENALEX_AVAILABLE = True
except ImportError:
    OpenAlexSearchTool = None
    OPENALEX_AVAILABLE = False
    logger.warning("⚠️ OpenAlex 学术搜索未可用")

# v7.199: 导入语义去重
try:
    from intelligent_project_analyzer.tools.semantic_dedup import (
        semantic_deduplicate,
    )
    SEMANTIC_DEDUP_AVAILABLE = True
except ImportError:
    semantic_deduplicate = None
    SEMANTIC_DEDUP_AVAILABLE = False
    logger.warning("⚠️ 语义去重模块未可用")


# ==================== 常量配置 ====================

# v7.200: 搜索质量优化
MAX_SEARCH_ROUNDS = 30  # 最大搜索轮数（深度探索）
MIN_SEARCH_ROUNDS = 4   # 最小搜索轮数（6→4，简单问题允许提前终止）
COMPLETENESS_THRESHOLD = 0.88  # 回答完整度阈值（0.92→0.88，避免过度搜索）

# v7.246: 动态延展与并行搜索配置
MAX_EXTENSION_ROUNDS = 3        # 最大延展轮次（控制延展深度）
MAX_PARALLEL_MAINLINES = 4      # 最大并行主线数（避免 API 限流）
EXTENSION_COVERAGE_THRESHOLD = 0.80  # 触发延展的覆盖度阈值

# 模型配置 - DeepSeek V3.2
# DeepSeek 使用官方 API（更稳定），其他模型使用 OpenRouter
THINKING_MODEL = "deepseek-reasoner"          # DeepSeek 官方 API：思考模式
EVAL_MODEL = "deepseek-chat"                   # DeepSeek 官方 API：评估模式
SYNTHESIS_MODEL = "openai/gpt-4o"              # OpenRouter：答案生成

# v7.195: 网页内容深度提取配置
DEEP_CONTENT_EXTRACTION_ENABLED = os.getenv("DEEP_CONTENT_EXTRACTION_ENABLED", "true").lower() == "true"
DEEP_CONTENT_TOP_N = int(os.getenv("DEEP_CONTENT_TOP_N", "5"))  # 每轮最多深度提取的来源数

# v7.199: 搜索质量增强配置
OPENALEX_SEARCH_ENABLED = os.getenv("OPENALEX_SEARCH_ENABLED", "true").lower() == "true"
SEMANTIC_DEDUP_ENABLED = os.getenv("SEMANTIC_DEDUP_ENABLED", "true").lower() == "true"
SEMANTIC_DEDUP_THRESHOLD = float(os.getenv("SEMANTIC_DEDUP_THRESHOLD", "0.85"))

# v7.212: 搜索结果质量筛选配置
SEARCH_QUALITY_THRESHOLD = float(os.getenv("SEARCH_QUALITY_THRESHOLD", "0.3"))
SEARCH_QUALITY_LLM_FILTER = os.getenv("SEARCH_QUALITY_LLM_FILTER", "true").lower() == "true"
SEARCH_MIN_QUALITY_SOURCES = int(os.getenv("SEARCH_MIN_QUALITY_SOURCES", "3"))
SEARCH_SUPPLEMENT_MAX_RETRIES = int(os.getenv("SEARCH_SUPPLEMENT_MAX_RETRIES", "3"))

# DeepSeek 官方 API 配置
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"


class SearchPhase(Enum):
    """搜索阶段"""
    QUESTION_ANALYSIS = "question_analysis"  # 问题分析
    GOAL_DIRECTED_SEARCH = "goal_directed_search"  # 目标导向搜索
    ANSWER_SYNTHESIS = "answer_synthesis"  # 答案整合


class AnalysisPhase(Enum):
    """分析阶段枚举 - v7.214"""
    L0_DIALOGUE = "l0_dialogue"           # L0: 对话式理解
    L1_L5_FRAMEWORK = "l1_l5_framework"   # L1-L5: 深度框架分析  
    SYNTHESIS = "synthesis"               # 综合: 搜索任务生成


class AnswerReadiness(Enum):
    """回答就绪状态"""
    NOT_READY = "not_ready"        # 信息不足，无法回答
    PARTIAL = "partial"            # 可以部分回答
    READY = "ready"                # 可以完整回答
    EXCELLENT = "excellent"        # 可以深度回答


# ==================== 数据结构 ====================

@dataclass
class PhaseResult:
    """分析阶段结果基类 - v7.214"""
    phase: AnalysisPhase
    content: Dict[str, Any]
    quality_score: float
    execution_time: float = 0.0
    next_phase: Optional[AnalysisPhase] = None
    retry_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase": self.phase.value,
            "content": self.content,
            "quality_score": self.quality_score,
            "execution_time": self.execution_time,
            "retry_count": self.retry_count
        }

@dataclass
class L0DialogueResult(PhaseResult):
    """L0 对话分析结果 - v7.214"""
    user_profile: 'StructuredUserInfo' = None
    context_understanding: str = ""
    implicit_needs: List[str] = None
    dialogue_content: str = ""
    
    def __post_init__(self):
        self.phase = AnalysisPhase.L0_DIALOGUE
        if self.implicit_needs is None:
            self.implicit_needs = []
        if self.user_profile is None:
            # 需要导入 StructuredUserInfo，这里先用 None 处理
            pass

@dataclass
class L1L5FrameworkResult(PhaseResult):
    """L1-L5 框架分析结果 - v7.214"""
    l1_facts: List[str] = None
    l2_models: Dict[str, str] = None
    l3_tensions: str = ""
    l4_jtbd: str = ""
    l5_sharpness: Dict[str, Any] = None
    framework_coherence: float = 0.0
    
    def __post_init__(self):
        self.phase = AnalysisPhase.L1_L5_FRAMEWORK
        if self.l1_facts is None:
            self.l1_facts = []
        if self.l2_models is None:
            self.l2_models = {}
        if self.l5_sharpness is None:
            self.l5_sharpness = {}

@dataclass
class SynthesisResult(PhaseResult):
    """综合分析结果 - v7.214"""
    search_master_line: 'SearchMasterLine' = None
    answer_framework: 'AnswerFramework' = None
    execution_plan: Dict[str, Any] = None
    
    def __post_init__(self):
        self.phase = AnalysisPhase.SYNTHESIS
        if self.execution_plan is None:
            self.execution_plan = {}

@dataclass
class QualityGate:
    """质量门控 - v7.214"""
    threshold: float = 0.75
    retry_limit: int = 2
    fallback_strategy: str = "continue_with_warning"
    
    criteria: Dict[str, Dict[str, float]] = field(default_factory=lambda: {
        "L0_DIALOGUE": {
            "profile_completeness": 0.80,
            "implicit_need_depth": 0.75,
            "dialogue_naturalness": 0.70
        },
        "L1_L5_FRAMEWORK": {
            "fact_atomization": 0.85,
            "model_integration": 0.80,
            "tension_precision": 0.85,
            "actionability": 0.75
        },
        "SYNTHESIS": {
            "task_completeness": 0.90,
            "logical_progression": 0.85,
            "executability": 0.80
        }
    })
    
    def check_phase_quality(self, phase: AnalysisPhase, result: PhaseResult) -> bool:
        """检查阶段质量是否达标"""
        phase_criteria = self.criteria.get(phase.value, {})
        if not phase_criteria:
            return result.quality_score >= self.threshold
        
        # 检查各维度是否都达标
        for criterion, min_score in phase_criteria.items():
            actual_score = result.content.get(f"{criterion}_score", result.quality_score)
            if actual_score < min_score:
                return False
        return True

@dataclass
class AnalysisSession:
    """分析会话管理 - v7.214"""
    session_id: str
    query: str
    context: Dict[str, Any] = None
    current_phase: AnalysisPhase = AnalysisPhase.L0_DIALOGUE
    phase_results: Dict[AnalysisPhase, PhaseResult] = field(default_factory=dict)
    quality_gate: QualityGate = field(default_factory=QualityGate)
    start_time: float = field(default_factory=time.time)
    
    # v7.214 新增字段用于存储各阶段结果
    l0_result: Optional[L0DialogueResult] = None
    framework_result: Optional[L1L5FrameworkResult] = None 
    synthesis_result: Optional[SynthesisResult] = None
    overall_quality: float = 0.0
    total_execution_time: float = 0.0
    
    def __post_init__(self):
        if self.context is None:
            self.context = {}
    
    def can_proceed_to_next_phase(self) -> bool:
        """检查是否可以进入下一阶段"""
        current_result = self.phase_results.get(self.current_phase)
        if not current_result:
            return False
        return self.quality_gate.check_phase_quality(self.current_phase, current_result)
    
    def get_analysis_trace(self) -> Dict[str, Any]:
        """获取完整分析轨迹"""
        return {
            "session_id": self.session_id,
            "query": self.query,
            "phases": {phase.value: result.to_dict() 
                      for phase, result in self.phase_results.items()},
            "total_time": time.time() - self.start_time
        }
    
    def get_next_phase(self) -> Optional[AnalysisPhase]:
        """获取下一个分析阶段"""
        phase_order = [AnalysisPhase.L0_DIALOGUE, AnalysisPhase.L1_L5_FRAMEWORK, AnalysisPhase.SYNTHESIS]
        try:
            current_index = phase_order.index(self.current_phase)
            if current_index < len(phase_order) - 1:
                return phase_order[current_index + 1]
        except ValueError:
            pass
        return None

@dataclass
class StructuredUserInfo:
    """
    L0 结构化用户信息 - v7.205

    增强版数据结构，支持：
    1. 语境分析（每个字段都有对应的 _context 字段）
    2. 隐性需求推断
    3. 地点特殊考量
    4. 信息完整度评估
    """
    # 用户基础画像
    demographics: Dict[str, str] = field(default_factory=lambda: {
        "location": "",
        "location_context": "",
        "age": "",
        "age_context": "",
        "gender": "",
        "occupation": "",
        "occupation_context": "",
        "education": "",
        "education_context": "",
    })

    # 身份标签
    identity_tags: List[str] = field(default_factory=list)

    # 生活方式
    lifestyle: Dict[str, Any] = field(default_factory=lambda: {
        "living_situation": "",
        "family_status": "",
        "hobbies": [],
        "pets": [],
    })

    # 项目/场景信息
    project_context: Dict[str, Any] = field(default_factory=lambda: {
        "type": "",
        "scale": "",
        "scale_context": "",
        "constraints": [],
        "budget_range": "",
        "timeline": "",
    })

    # 偏好与参照
    preferences: Dict[str, List[str]] = field(default_factory=lambda: {
        "style_references": [],
        "style_keywords": [],
        "color_palette": [],
        "material_preferences": [],
        "cultural_influences": [],
    })

    # 核心诉求
    core_request: Dict[str, Any] = field(default_factory=lambda: {
        "explicit_need": "",
        "implicit_needs": [],
    })

    # 地点特殊考量
    location_considerations: Dict[str, str] = field(default_factory=lambda: {
        "climate": "",
        "architecture": "",
        "lifestyle": "",
    })

    # 信息完整度评估
    completeness: Dict[str, Any] = field(default_factory=lambda: {
        "provided_dimensions": [],
        "missing_dimensions": [],
        "confidence_score": 0.0,
    })

    # 原始提取文本（用于调试）
    raw_extraction: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典用于前端展示和 JSON 序列化"""
        return {
            "demographics": self.demographics,
            "identity_tags": self.identity_tags,
            "lifestyle": self.lifestyle,
            "project_context": self.project_context,
            "preferences": self.preferences,
            "core_request": self.core_request,
            "location_considerations": self.location_considerations,
            "completeness": self.completeness,
        }

    def has_user_profile(self) -> bool:
        """是否包含用户画像信息"""
        has_demographics = any(
            self.demographics.get(k)
            for k in ["location", "age", "gender", "occupation", "education"]
        )
        has_tags = len(self.identity_tags) > 0
        return has_demographics or has_tags

    def has_preferences(self) -> bool:
        """是否包含偏好信息"""
        return (
            len(self.preferences.get("style_references", [])) > 0 or
            len(self.preferences.get("style_keywords", [])) > 0
        )

    def has_implicit_needs(self) -> bool:
        """是否有推断的隐性需求"""
        return len(self.core_request.get("implicit_needs", [])) > 0

    def get_summary(self) -> str:
        """获取简短摘要（用于日志）"""
        parts = []
        if self.demographics.get("location"):
            parts.append(f"地点:{self.demographics['location']}")
        if self.demographics.get("age"):
            parts.append(f"年龄:{self.demographics['age']}")
        if self.identity_tags:
            parts.append(f"标签:{','.join(self.identity_tags[:3])}")
        if self.preferences.get("style_references"):
            parts.append(f"风格:{','.join(self.preferences['style_references'][:2])}")
        return " | ".join(parts) if parts else "无用户画像"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StructuredUserInfo':
        """从字典创建实例"""
        return cls(
            demographics=data.get("demographics", {}),
            identity_tags=data.get("identity_tags", []),
            lifestyle=data.get("lifestyle", {}),
            project_context=data.get("project_context", {}),
            preferences=data.get("preferences", {}),
            core_request=data.get("core_request", {}),
            location_considerations=data.get("location_considerations", {}),
            completeness=data.get("completeness", {}),
            raw_extraction=data.get("raw_extraction", ""),
        )


# ==================== v7.220: 统一搜索框架 ====================

@dataclass
class SearchTarget:
    """
    统一的搜索目标 - v7.236

    合并原来的 SearchTask 和 KeyAspect，成为唯一的搜索单元。
    从第一阶段分析生成，贯穿整个搜索流程。

    v7.236 更新（字段语义明确化）：
    - 新增 question: 用问句描述任务目标（替代模糊的 name）
    - 新增 search_for: 具体搜索内容（替代模糊的 description）
    - 新增 why_need: 说明对回答的贡献（替代抽象的 purpose）
    - 新增 success_when: 完成标准（替代 quality_criteria）
    - 保留旧字段 name/description/purpose 用于向后兼容
    
    v7.232 更新：
    - 添加 preset_keywords: 预设搜索关键词列表（在分析阶段生成）
    - 搜索时优先使用 preset_keywords，而非临时生成
    """
    # === 基础信息 ===
    id: str                              # 目标ID (T1, T2, ...)
    
    # === v7.236: 新字段（语义明确） ===
    question: str = ""                   # 这个任务要回答什么问题？（问句形式，15字内）
    search_for: str = ""                 # 具体搜索什么内容（列出实体名称）
    why_need: str = ""                   # 找到后对回答有什么帮助
    success_when: List[str] = field(default_factory=list)  # 什么情况算搜索成功
    
    # === 旧字段（向后兼容） ===
    name: str = ""                       # 搜索目标名称（简短）- 兼容旧代码
    description: str = ""                # 详细描述 - 兼容旧代码
    purpose: str = ""                    # 为什么要搜这个 - 兼容旧代码
    answer_goal: str = ""                # 回答目标

    # === 分类与优先级 ===
    priority: int = 1                    # 优先级 1(高) / 2(中) / 3(低)
    category: str = "品牌调研"           # 类别: 品牌调研 / 案例参考 / 方案验证 / 背景知识

    # === 状态追踪 ===
    status: str = "pending"              # pending / searching / complete

    # === v7.232: 预设搜索关键词（核心改进）===
    preset_keywords: List[str] = field(default_factory=list)  # 预设的精准搜索关键词（分析阶段生成）
    current_keyword_index: int = 0       # 当前使用的关键词索引
    quality_criteria: List[str] = field(default_factory=list) # 质量达标标准（旧字段，兼容）

    # === 搜索执行 ===
    search_queries: List[str] = field(default_factory=list)   # 已执行的搜索词
    expected_info: List[str] = field(default_factory=list)    # 期望获取的信息类型

    # === 结果追踪 ===
    sources: List[Dict[str, Any]] = field(default_factory=list)  # 收集到的来源
    collected_info: List[str] = field(default_factory=list)      # 已收集的信息摘要
    sources_count: int = 0               # 来源数量
    completion_score: float = 0.0        # 完成度 0-1
    rounds_spent: int = 0                # 花费的搜索轮数

    # === 质量评估 ===
    quality_score: float = 0.0           # 信息质量评分
    coverage_score: float = 0.0          # 信息覆盖度评分

    # === v7.260: 全局并行支持 ===
    dependencies: List[str] = field(default_factory=list)  # 依赖的任务ID（空=可立即并行）
    execution_order: int = 1                                # 执行顺序（仅用于无依赖时的优先级排序）
    group_id: str = ""                                      # 所属任务组ID（用于UI分组展示）
    can_parallel: bool = True                               # 是否可并行（默认True，全局并行策略）
    search_action: str = ""                                 # 搜索引导词：搜索/查找/调研/收集/对比/验证

    # === v7.260: 子任务支持 ===
    sub_tasks: List[Dict[str, Any]] = field(default_factory=list)  # 子任务列表（LLM动态生成）

    def __post_init__(self):
        """v7.236: 自动填充兼容字段"""
        # 如果新字段有值，同步到旧字段（向后兼容）
        if self.question and not self.name:
            self.name = self.question
        if self.search_for and not self.description:
            self.description = self.search_for
        if self.why_need and not self.purpose:
            self.purpose = self.why_need
        if self.success_when and not self.quality_criteria:
            self.quality_criteria = self.success_when
        
        # 反向：如果旧字段有值但新字段为空，同步到新字段
        if self.name and not self.question:
            self.question = self.name
        if self.description and not self.search_for:
            self.search_for = self.description
        if self.purpose and not self.why_need:
            self.why_need = self.purpose
        if self.quality_criteria and not self.success_when:
            self.success_when = self.quality_criteria

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            # v7.236: 新字段
            "question": self.question,
            "search_for": self.search_for,
            "why_need": self.why_need,
            "success_when": self.success_when,
            # 旧字段（兼容）
            "name": self.name or self.question,
            "description": self.description or self.search_for,
            "purpose": self.purpose or self.why_need,
            "priority": self.priority,
            "category": self.category,
            "status": self.status,
            "completion_score": self.completion_score,
            "sources_count": self.sources_count,
            "preset_keywords": self.preset_keywords,
            "quality_criteria": self.quality_criteria or self.success_when,
            "search_queries": self.search_queries,
            "expected_info": self.expected_info,
            # v7.260: 全局并行支持
            "dependencies": self.dependencies,
            "execution_order": self.execution_order,
            "group_id": self.group_id,
            "can_parallel": self.can_parallel,
            "search_action": self.search_action,
            "sub_tasks": self.sub_tasks,
        }

    def is_complete(self) -> bool:
        """判断是否完成"""
        return self.status == "complete" or self.completion_score >= 0.8

    def mark_searching(self):
        """标记为搜索中"""
        self.status = "searching"

    def mark_complete(self, score: float = 1.0):
        """标记为完成"""
        self.status = "complete"
        self.completion_score = score

    def get_next_preset_keyword(self) -> Optional[str]:
        """
        获取下一个预设关键词 - v7.232

        返回下一个未使用的预设关键词，如果都用完了返回 None
        """
        if not self.preset_keywords:
            return None
        if self.current_keyword_index >= len(self.preset_keywords):
            return None
        return self.preset_keywords[self.current_keyword_index]

    def has_more_keywords(self) -> bool:
        """是否还有未使用的预设关键词"""
        return self.current_keyword_index < len(self.preset_keywords)


@dataclass
class SearchFramework:
    """
    搜索框架 - v7.220

    替代原来的 SearchMasterLine + AnswerFramework 双系统。
    统一管理搜索目标、分析结果和进度追踪。
    """
    # === 问题锚点 ===
    original_query: str = ""             # 原始用户问题
    core_question: str = ""              # 问题一句话本质
    answer_goal: str = ""                # 回答目标
    boundary: str = ""                   # 搜索边界（不搜什么）

    # === 搜索目标列表 ===
    targets: List[SearchTarget] = field(default_factory=list)

    # === 深度分析结果 ===
    l1_facts: List[str] = field(default_factory=list)         # L1 事实解构
    l2_models: Dict[str, str] = field(default_factory=dict)   # L2 多视角建模
    l3_tension: str = ""                                       # L3 核心张力
    l4_jtbd: str = ""                                          # L4 用户任务
    l5_sharpness: Dict[str, Any] = field(default_factory=dict) # L5 锐度评估

    # === 用户画像 ===
    user_profile: Dict[str, Any] = field(default_factory=dict)

    # === 进度追踪 ===
    current_target_id: str = ""          # 当前搜索目标ID
    completed_count: int = 0             # 已完成目标数
    overall_completeness: float = 0.0    # 整体完成度

    # === 收集的证据 ===
    all_sources: List[Dict[str, Any]] = field(default_factory=list)
    collected_evidence: Dict[str, Any] = field(default_factory=dict)  # v7.229: 兼容旧代码

    # === v7.229: 轮次洞察累积 ===
    round_insights: List["RoundInsights"] = field(default_factory=list)

    # === v7.240: 框架清单 ===
    framework_checklist: Optional["FrameworkChecklist"] = None

    def get_next_target(self) -> Optional[SearchTarget]:
        """获取下一个待搜索的目标"""
        # 按优先级排序，返回第一个未完成的
        pending = [t for t in self.targets if not t.is_complete()]
        if not pending:
            return None
        pending.sort(key=lambda t: t.priority)
        return pending[0]

    def get_parallel_targets(self, max_parallel: int = 4) -> List[SearchTarget]:
        """
        获取所有可并行执行的目标 - v7.260 全局并行策略

        返回所有满足以下条件的目标：
        1. 未完成（status != complete）
        2. 依赖已满足（dependencies中的所有任务都已完成）
        3. can_parallel = True

        Args:
            max_parallel: 最大并行数量（默认4）

        Returns:
            可并行执行的目标列表，按优先级排序
        """
        if not self.targets:
            return []

        # 获取已完成的目标ID集合
        completed_ids = {t.id for t in self.targets if t.is_complete()}

        # 筛选可并行执行的目标
        parallel_targets = []
        for t in self.targets:
            if t.is_complete():
                continue
            if not t.can_parallel:
                continue
            # 检查依赖是否满足
            if t.dependencies:
                deps_satisfied = all(dep_id in completed_ids for dep_id in t.dependencies)
                if not deps_satisfied:
                    continue
            parallel_targets.append(t)

        # 按优先级和执行顺序排序
        parallel_targets.sort(key=lambda t: (t.priority, t.execution_order))

        # 限制最大并行数量
        return parallel_targets[:max_parallel]

    def get_ready_targets(self) -> List[SearchTarget]:
        """
        获取所有依赖已满足的待执行目标 - v7.260

        与 get_parallel_targets 的区别：
        - get_parallel_targets: 只返回 can_parallel=True 的目标
        - get_ready_targets: 返回所有依赖已满足的目标（包括串行任务）

        Returns:
            依赖已满足的目标列表，按优先级排序
        """
        if not self.targets:
            return []

        completed_ids = {t.id for t in self.targets if t.is_complete()}

        ready_targets = []
        for t in self.targets:
            if t.is_complete():
                continue
            # 检查依赖是否满足
            if t.dependencies:
                deps_satisfied = all(dep_id in completed_ids for dep_id in t.dependencies)
                if not deps_satisfied:
                    continue
            ready_targets.append(t)

        ready_targets.sort(key=lambda t: (t.priority, t.execution_order))
        return ready_targets

    def get_target_for_round(self, round_number: int) -> Optional[SearchTarget]:
        """
        按轮次轮换获取搜索目标 - v7.245

        策略：每轮搜索不同的主线，确保覆盖所有搜索方向
        - 第1轮选第1个目标
        - 第2轮选第2个目标
        - ...
        - 超过目标数量后循环

        Args:
            round_number: 当前轮次（从1开始）

        Returns:
            当前轮次应该搜索的目标
        """
        if not self.targets:
            return None
        # 按优先级排序
        sorted_targets = sorted(self.targets, key=lambda t: t.priority)
        # 轮换选择：第1轮选第1个，第2轮选第2个...
        index = (round_number - 1) % len(sorted_targets)
        return sorted_targets[index]

    def get_target_by_id(self, target_id: str) -> Optional[SearchTarget]:
        """根据ID获取目标"""
        for t in self.targets:
            if t.id == target_id:
                return t
        return None

    def update_completeness(self):
        """更新整体完成度"""
        if not self.targets:
            self.overall_completeness = 0.0
            return

        total_score = sum(t.completion_score for t in self.targets)
        self.overall_completeness = total_score / len(self.targets)
        self.completed_count = sum(1 for t in self.targets if t.is_complete())

    def can_answer_completely(self) -> bool:
        """
        是否能够完整回答用户问题 - v7.233 新增
        
        判断标准：所有高优先级(priority=1)的目标都至少是partial状态
        """
        if not self.targets:
            return False
        # 所有高优先级(priority=1)的目标都至少不是pending
        high_priority = [t for t in self.targets if t.priority == 1]
        if not high_priority:
            # 没有高优先级目标，检查所有目标
            high_priority = self.targets
        return all(t.status != "pending" for t in high_priority)

    def calculate_completeness(self) -> float:
        """
        计算回答完成度 - v7.233 新增
        
        基于目标的优先级加权计算完成度
        """
        if not self.targets:
            return 0.0
        # 优先级越高(数值越小)权重越大
        total_weight = 0.0
        achieved = 0.0
        for t in self.targets:
            weight = 1.0 / max(t.priority, 1)  # priority=1 -> weight=1.0, priority=2 -> weight=0.5
            total_weight += weight
            achieved += weight * t.completion_score
        return achieved / total_weight if total_weight > 0 else 0.0

    def get_mainline_targets(self) -> List[SearchTarget]:
        """
        v7.246: 获取所有未完成的主线目标（非延展任务）

        用于并行主线搜索，排除延展任务

        Returns:
            未完成的主线目标列表，按优先级排序
        """
        mainline_targets = [
            t for t in self.targets
            if not t.is_complete() and t.category != "延展"
        ]
        return sorted(mainline_targets, key=lambda t: t.priority)

    def get_extension_targets(self) -> List[SearchTarget]:
        """
        v7.246: 获取所有未完成的延展目标

        用于串行延展搜索

        Returns:
            未完成的延展目标列表，按优先级排序
        """
        extension_targets = [
            t for t in self.targets
            if not t.is_complete() and t.category == "延展"
        ]
        return sorted(extension_targets, key=lambda t: t.priority)

    def get_extension_count(self) -> int:
        """
        v7.246: 获取当前延展任务数量

        用于控制延展轮次不超过 MAX_EXTENSION_ROUNDS
        """
        return len([t for t in self.targets if t.category == "延展"])


# ==================== v7.240: 框架清单 ====================

@dataclass
class FrameworkChecklist:
    """
    框架清单 - v7.261

    纯文字结构化的搜索框架清单，用于：
    1. 前端展示给用户，明确搜索主线
    2. 每轮搜索时作为上下文，指导搜索方向
    3. 防止搜索跑题，确保框架一致性

    v7.261 更新（动机类型系统化）：
    - main_directions 按动机类型分组聚合
    - 新增 motivation_distribution: 动机分布统计
    - 每个方向包含 motivation_id, motivation_priority, motivation_color

    v7.260 更新（全局并行 + LLM动态生成）：
    - 新增 complexity_score: 任务复杂度评估
    - 新增 recommended_task_count: 推荐任务数量
    - main_directions 增强：每个方向包含 sub_tasks 子任务列表

    v7.250 更新：
    - 新增深度分析摘要字段（user_context, key_entities, core_tension等）
    - 保留L0-L5分析结果，用于前端展示和后续搜索参考
    """
    # === 核心问题 ===
    core_summary: str = ""               # 核心问题一句话总结（20字内）

    # === 搜索主线（v7.261 增强：按动机类型分组） ===
    main_directions: List[Dict[str, Any]] = field(default_factory=list)
    # 每个方向包含:
    # - direction: 动机类型中文名（如"文化认同"）
    # - motivation_id: 动机类型ID（如"cultural"）
    # - motivation_priority: 优先级（P0/P1/P2/BASELINE）
    # - motivation_color: 展示颜色
    # - purpose: 动机类型描述
    # - targets: 该动机下的搜索目标列表
    # - sub_tasks: 扁平化的子任务列表
    # - target_count: 目标数量

    # === 搜索边界 ===
    boundaries: List[str] = field(default_factory=list)  # 不搜什么

    # === 回答目标 ===
    answer_goal: str = ""                # 最终要给用户什么样的答案

    # === 生成时间戳 ===
    generated_at: str = ""

    # === v7.260 新增：复杂度评估 ===
    complexity_score: float = 0.0        # 任务复杂度评分 (0-1)
    recommended_task_count: int = 5      # 推荐任务数量

    # === v7.261 新增：动机分布统计 ===
    motivation_distribution: Dict[str, int] = field(default_factory=dict)  # {motivation_id: count}

    # === v7.250 新增：深度分析摘要 ===
    user_context: Dict[str, Any] = field(default_factory=dict)  # 用户画像摘要
    key_entities: List[Dict[str, str]] = field(default_factory=list)  # L1关键实体
    analysis_perspectives: List[str] = field(default_factory=list)  # L2视角列表
    core_tension: str = ""  # L3核心张力
    user_task: str = ""  # L4 JTBD
    sharpness_check: Dict[str, str] = field(default_factory=dict)  # L5锐度自检

    def to_plain_text(self) -> str:
        """
        生成纯文字格式的框架清单 - v7.250

        用于后续搜索轮次的prompt注入，包含深度分析摘要
        """
        lines = []

        # 核心问题
        lines.append("## 核心问题")
        lines.append(self.core_summary)
        lines.append("")

        # v7.250 新增：用户画像摘要
        if self.user_context:
            lines.append("## 用户画像")
            if self.user_context.get("identity"):
                lines.append(f"- 身份特征: {self.user_context['identity']}")
            if self.user_context.get("implicit_needs"):
                needs = self.user_context['implicit_needs']
                if isinstance(needs, list) and needs:
                    lines.append(f"- 隐性需求: {', '.join(str(n) for n in needs[:2])}")
            lines.append("")

        # v7.250 新增：关键实体
        if self.key_entities:
            lines.append("## 关键实体")
            for e in self.key_entities[:5]:
                detail = f" ({e['detail']})" if e.get('detail') else ""
                lines.append(f"- [{e.get('type', '')}] {e.get('name', '')}{detail}")
            lines.append("")

        # v7.250 新增：核心张力
        if self.core_tension:
            lines.append("## 核心张力")
            lines.append(self.core_tension)
            lines.append("")

        # v7.250 新增：用户任务
        if self.user_task:
            lines.append("## 用户任务(JTBD)")
            lines.append(self.user_task)
            lines.append("")

        # 搜索主线（v7.261 增强：按动机类型分组展示）
        lines.append(f"## 搜索主线（{len(self.main_directions)}个方向）")
        for i, d in enumerate(self.main_directions, 1):
            # v7.261: 展示动机类型信息
            motivation_id = d.get('motivation_id')
            motivation_priority = d.get('motivation_priority', '')
            direction_name = d.get('direction', '')

            if motivation_id:
                # 有动机信息时，展示动机类型和优先级
                priority_badge = f"({motivation_priority})" if motivation_priority else ""
                lines.append(f"{i}. **{direction_name}** {priority_badge}")
            else:
                # 降级模式，无动机信息
                lines.append(f"{i}. **{direction_name}**")

            if d.get('purpose'):
                lines.append(f"   - 目的：{d.get('purpose', '')}")

            # v7.261: 展示该动机下的目标列表
            targets = d.get('targets', [])
            if targets:
                lines.append(f"   - 搜索目标（{len(targets)}个）：")
                for t in targets[:5]:  # 最多显示5个
                    t_name = t.get('name', '') if isinstance(t, dict) else str(t)
                    lines.append(f"     • {t_name}")

            # v7.260: 展示子任务
            sub_tasks = d.get('sub_tasks', [])
            if sub_tasks:
                lines.append(f"   - 子任务（{len(sub_tasks)}个）：")
                for st in sub_tasks[:5]:  # 最多显示5个
                    action = st.get('search_action', '搜索')
                    question = st.get('question', '')
                    can_parallel = "✓并行" if st.get('can_parallel', True) else "→串行"
                    lines.append(f"     • [{action}] {question} ({can_parallel})")
        lines.append("")

        # 搜索边界
        if self.boundaries:
            lines.append("## 搜索边界（不涉及）")
            for b in self.boundaries:
                lines.append(f"- {b}")
            lines.append("")

        # 回答目标
        lines.append("## 回答目标")
        lines.append(self.answer_goal)

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典 - v7.261 增强"""
        return {
            "core_summary": self.core_summary,
            "main_directions": self.main_directions,
            "boundaries": self.boundaries,
            "answer_goal": self.answer_goal,
            "generated_at": self.generated_at,
            "plain_text": self.to_plain_text(),
            # v7.260 新增
            "complexity_score": self.complexity_score,
            "recommended_task_count": self.recommended_task_count,
            # v7.261 新增
            "motivation_distribution": self.motivation_distribution,
            # v7.250 新增
            "user_context": self.user_context,
            "key_entities": self.key_entities,
            "analysis_perspectives": self.analysis_perspectives,
            "core_tension": self.core_tension,
            "user_task": self.user_task,
            "sharpness_check": self.sharpness_check,
        }


# ==================== v7.213: 框架性搜索任务主线（保留兼容） ====================

@dataclass
class SearchTask:
    """
    明确的搜索任务 - v7.213 增强
    
    与 KeyAspect 的区别：
    - KeyAspect: "需要收集什么信息" (信息面)
    - SearchTask: "具体要搜什么" (执行任务)
    
    SearchTask 更明确、更可执行、更可追踪
    
    v7.213 新增：
    - 阶段化组织（phase）：基础信息→深度案例→对比验证
    - 任务依赖（depends_on）：明确前置条件
    - 验证标准（validation_criteria）：完成度判断依据
    - 延展追踪（is_extension, extended_from）：动态补充任务溯源
    """
    id: str                                  # 任务ID (T1, T2, ...)
    task: str                                # 具体搜索任务描述
    purpose: str                             # 为什么要搜这个（与回答的关联）
    priority: int = 1                        # 优先级 P1(必须)/P2(重要)/P3(补充)
    status: str = "pending"                  # 状态: pending/searching/complete
    expected_info: List[str] = field(default_factory=list)   # 期望获取的信息
    actual_findings: List[str] = field(default_factory=list) # 实际发现
    search_queries: List[str] = field(default_factory=list)  # 已执行的搜索查询
    rounds_spent: int = 0                    # 花费轮次
    completion_score: float = 0.0            # 完成度 0-1
    source_urls: List[str] = field(default_factory=list)     # 信息来源
    # v7.213 新增字段
    phase: str = ""                          # 所属阶段（基础信息/深度案例/对比验证）
    depends_on: List[str] = field(default_factory=list)      # 依赖的任务ID列表
    validation_criteria: List[str] = field(default_factory=list)  # 验证标准
    is_extension: bool = False               # 是否为延展任务（动态补充的）
    extended_from: str = ""                  # 延展来源（触发该任务的原任务ID或触发条件）
    extension_reason: str = ""               # 延展原因
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task": self.task,
            "purpose": self.purpose,
            "priority": self.priority,
            "status": self.status,
            "expected_info": self.expected_info,
            "actual_findings": self.actual_findings,
            "completion_score": self.completion_score,
            "rounds_spent": self.rounds_spent,
            # v7.213 新增
            "phase": self.phase,
            "depends_on": self.depends_on,
            "validation_criteria": self.validation_criteria,
            "is_extension": self.is_extension,
            "extended_from": self.extended_from,
            "extension_reason": self.extension_reason,
        }


@dataclass
class SearchMasterLine:
    """
    搜索主线 - v7.213 框架性增强
    
    在分析阶段生成的宏观搜索清单，作为后续多轮搜索的锚点：
    1. 确保搜索不跑题（boundary 边界约束）
    2. 明确搜索任务（search_tasks 任务清单）
    3. 允许延展探索（exploration_triggers 探索触发）
    
    v7.213 新增：
    - 框架概要（framework_summary）：搜索路线图概览
    - 阶段检查点（checkpoint_rounds）：复盘时机控制
    - 延展日志（extension_log）：记录动态补充轨迹
    - 阶段完成追踪：分阶段管理进度
    """
    # === 问题锚点 ===
    core_question: str = ""                  # 用户问题一句话本质
    boundary: str = ""                       # 边界定义（防止跑题）
    
    # === v7.213: 框架概要 ===
    framework_summary: str = ""              # 搜索路线图概览（如：分3阶段搜索...）
    search_phases: List[str] = field(default_factory=list)   # 阶段列表（基础信息/深度案例/对比验证）
    
    # === 搜索任务清单 ===
    search_tasks: List[SearchTask] = field(default_factory=list)
    
    # === 探索触发条件 ===
    exploration_triggers: List[str] = field(default_factory=list)  # 触发延展探索的条件
    
    # === 禁区 ===
    forbidden_zones: List[str] = field(default_factory=list)  # 明确排除的方向
    
    # === v7.213: 检查点与复盘 ===
    checkpoint_rounds: List[int] = field(default_factory=list)   # 复盘检查点（轮次号列表）
    phase_checkpoints: Dict[str, int] = field(default_factory=dict)  # 阶段完成后的检查点轮次
    
    # === v7.213: 延展日志 ===
    extension_log: List[Dict[str, Any]] = field(default_factory=list)  # 延展记录
    
    # === 进度追踪 ===
    current_task_id: str = ""                # 当前执行的任务ID
    completed_tasks: int = 0                 # 已完成任务数
    exploration_rounds: int = 0              # 已使用的探索轮次
    max_exploration_rounds: int = 3          # 最大探索轮次
    
    def get_next_task(self) -> Optional['SearchTask']:
        """
        获取下一个待执行的搜索任务 - v7.213 增强
        
        调度逻辑：
        1. 检查依赖是否满足
        2. 按优先级排序（P1→P2→P3）
        3. 继续上次未完成的任务
        """
        pending = [t for t in self.search_tasks if t.status in ("pending", "searching")]
        if not pending:
            return None
        
        # v7.213: 过滤掉依赖未完成的任务
        ready_tasks = []
        for t in pending:
            if not t.depends_on:
                ready_tasks.append(t)
            else:
                # 检查所有依赖是否已完成
                deps_satisfied = all(
                    self.get_task_by_id(dep_id) and self.get_task_by_id(dep_id).status == "complete"
                    for dep_id in t.depends_on
                )
                if deps_satisfied:
                    ready_tasks.append(t)
        
        if not ready_tasks:
            # 如果没有就绪任务但有待处理任务，可能存在循环依赖，降级为按优先级选择
            ready_tasks = pending
        
        # 优先级高 + 状态为searching（继续上次未完成的）
        return min(ready_tasks, key=lambda t: (t.priority, 0 if t.status == "searching" else 1))
    
    def get_task_by_id(self, task_id: str) -> Optional['SearchTask']:
        """根据ID获取任务"""
        for t in self.search_tasks:
            if t.id == task_id:
                return t
        return None
    
    def update_task_status(self, task_id: str, status: str, 
                          findings: List[str] = None, 
                          completion_score: float = None):
        """更新任务状态"""
        task = self.get_task_by_id(task_id)
        if task:
            task.status = status
            if findings:
                task.actual_findings.extend(findings)
            if completion_score is not None:
                task.completion_score = completion_score
            if status == "complete":
                self.completed_tasks += 1
    
    def get_progress_summary(self) -> str:
        """获取进度摘要 - v7.213 增强"""
        total = len(self.search_tasks)
        completed = sum(1 for t in self.search_tasks if t.status == "complete")
        p1_done = sum(1 for t in self.search_tasks if t.priority == 1 and t.status == "complete")
        p1_total = sum(1 for t in self.search_tasks if t.priority == 1)
        # v7.213: 添加阶段进度
        if self.search_phases:
            current_phase = self._get_current_phase()
            return f"总进度: {completed}/{total} | P1: {p1_done}/{p1_total} | 阶段: {current_phase}"
        return f"总进度: {completed}/{total} | P1任务: {p1_done}/{p1_total}"
    
    def _get_current_phase(self) -> str:
        """v7.213: 获取当前所处阶段"""
        if not self.search_phases:
            return "未定义"
        for phase in self.search_phases:
            phase_tasks = [t for t in self.search_tasks if t.phase == phase]
            if phase_tasks and any(t.status != "complete" for t in phase_tasks):
                return phase
        return self.search_phases[-1] if self.search_phases else "完成"
    
    def get_phase_progress(self) -> Dict[str, Dict[str, Any]]:
        """v7.213: 获取各阶段进度详情"""
        result = {}
        for phase in self.search_phases:
            phase_tasks = [t for t in self.search_tasks if t.phase == phase]
            if phase_tasks:
                completed = sum(1 for t in phase_tasks if t.status == "complete")
                result[phase] = {
                    "total": len(phase_tasks),
                    "completed": completed,
                    "percentage": round(completed / len(phase_tasks) * 100, 1) if phase_tasks else 0,
                    "status": "complete" if completed == len(phase_tasks) else "in_progress" if completed > 0 else "pending"
                }
        return result
    
    def should_checkpoint(self, current_round: int) -> bool:
        """v7.213: 检查是否应该进行阶段复盘"""
        return current_round in self.checkpoint_rounds
    
    def add_extension_task(self, task: 'SearchTask', trigger: str, reason: str) -> None:
        """v7.213: 添加延展任务并记录日志"""
        task.is_extension = True
        task.extended_from = trigger
        task.extension_reason = reason
        self.search_tasks.append(task)
        
        # 记录延展日志
        self.extension_log.append({
            "task_id": task.id,
            "trigger": trigger,
            "reason": reason,
            "timestamp": time.time(),
            "priority": task.priority,
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典 - v7.213 增强"""
        return {
            "core_question": self.core_question,
            "boundary": self.boundary,
            # v7.213 新增
            "framework_summary": self.framework_summary,
            "search_phases": self.search_phases,
            "checkpoint_rounds": self.checkpoint_rounds,
            "extension_log": self.extension_log,
            # 原有字段
            "search_tasks": [t.to_dict() for t in self.search_tasks],
            "exploration_triggers": self.exploration_triggers,
            "forbidden_zones": self.forbidden_zones,
            "completed_tasks": self.completed_tasks,
            "total_tasks": len(self.search_tasks),
            # v7.213: 阶段进度
            "phase_progress": self.get_phase_progress() if self.search_phases else {},
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SearchMasterLine':
        """从字典创建实例 - v7.213 增强"""
        tasks = []
        for t_data in data.get("search_tasks", []):
            tasks.append(SearchTask(
                id=t_data.get("id", ""),
                task=t_data.get("task", ""),
                purpose=t_data.get("purpose", ""),
                priority=t_data.get("priority", 2),
                status=t_data.get("status", "pending"),
                expected_info=t_data.get("expected_info", []),
                # v7.213 新增字段
                phase=t_data.get("phase", ""),
                depends_on=t_data.get("depends_on", []),
                validation_criteria=t_data.get("validation_criteria", []),
                is_extension=t_data.get("is_extension", False),
                extended_from=t_data.get("extended_from", ""),
                extension_reason=t_data.get("extension_reason", ""),
            ))
        return cls(
            core_question=data.get("core_question", ""),
            boundary=data.get("boundary", ""),
            # v7.213 新增
            framework_summary=data.get("framework_summary", ""),
            search_phases=data.get("search_phases", []),
            checkpoint_rounds=data.get("checkpoint_rounds", []),
            extension_log=data.get("extension_log", []),
            # 原有字段
            search_tasks=tasks,
            exploration_triggers=data.get("exploration_triggers", []),
            forbidden_zones=data.get("forbidden_zones", []),
        )


@dataclass
class KeyAspect:
    """
    关键信息面 - v7.183 核心创新

    ⚠️ DEPRECATED (v7.220): 此类已被 SearchTarget 替代
    保留此类仅用于向后兼容，新代码请使用 SearchTarget

    每个 KeyAspect 代表"完整回答用户问题"需要的一个信息面
    与 InformationGap 的区别：
    - InformationGap: "我们不知道什么" (探索导向)
    - KeyAspect: "回答问题需要什么" (目标导向)
    """
    id: str                                  # 唯一标识
    aspect_name: str                         # 信息面名称（如"核心原因"、"具体案例"）
    answer_goal: str                         # 这个信息面要回答什么（如"要说明为什么会发生"）
    importance: int = 5                      # 重要性 1-5，5为必需
    status: str = "missing"                  # 状态: missing/partial/complete
    collected_info: List[str] = field(default_factory=list)  # 已收集的信息
    source_urls: List[str] = field(default_factory=list)     # 信息来源
    completion_score: float = 0.0            # 完成度 0-1
    search_query: str = ""                   # 用于搜索此信息面的查询
    last_searched_round: int = 0             # 上次搜索轮次


@dataclass
class ReflectionResult:
    """
    增强反思结果 - v7.186 核心结构
    
    反思的双重角色：既是上一轮的总结，又是下一轮的开始
    始终围绕用户问题和第一轮的宏观统筹（隐形的指导线）
    """
    # === 回顾部分（上一轮总结） ===
    goal_achieved: bool = False              # 本轮目标是否达成
    goal_achievement_reason: str = ""        # 达成/未达成的原因
    info_sufficiency: float = 0.0            # 信息充分度 0-1
    info_quality: float = 0.0                # 信息质量 0-1
    quality_issues: List[str] = field(default_factory=list)  # 质量问题
    
    # === 收获提取 ===
    key_findings: List[str] = field(default_factory=list)     # 直接发现
    inferred_insights: List[str] = field(default_factory=list)  # 推断洞察
    
    # === 下一轮规划（承上启下） ===
    needs_deeper_search: bool = False        # 是否需要深入搜索
    deeper_search_points: List[str] = field(default_factory=list)  # 深入点
    suggested_next_query: str = ""           # 建议的下一轮查询
    next_round_purpose: str = ""             # 下一轮的目的
    
    # === 全局校准（回到原点） ===
    alignment_with_goal: float = 0.0         # 与用户目标对齐度 0-1
    alignment_note: str = ""                 # 对齐说明
    remaining_gaps: List[str] = field(default_factory=list)  # 剩余缺口
    estimated_rounds_remaining: int = 0      # 预估剩余轮次
    
    # === 叙事输出 ===
    reflection_narrative: str = ""           # 完整反思叙述（自然语言）
    cumulative_progress: str = ""            # 累积进展描述


@dataclass
class UnifiedThinkingResult:
    """
    统一思考结果 - v7.204 核心结构
    
    将"思考"和"反思"融合为一次 LLM 调用：
    - 首轮：仅做初始规划（无回顾）
    - 后续轮：回顾上轮 + 规划本轮 + 全局校准
    
    优势：
    - 减少一次 LLM 调用（从每轮2次降为1次）
    - 消除轮次间停顿
    - 反思和规划在同一上下文中，更连贯
    """
    # === 回顾上轮（仅 round > 1 时有值） ===
    key_findings: List[str] = field(default_factory=list)     # 上轮直接发现
    inferred_insights: List[str] = field(default_factory=list)  # 上轮推断洞察
    info_sufficiency: float = 0.0            # 上轮信息充分度 0-1
    info_quality: float = 0.0                # 上轮信息质量 0-1
    goal_achieved: bool = False              # 上轮目标是否达成
    quality_issues: List[str] = field(default_factory=list)  # 上轮质量问题
    
    # === 本轮规划 ===
    thinking_narrative: str = ""             # 思考叙事（自然语言）
    search_strategy: str = ""                # 搜索策略
    search_query: str = ""                   # 搜索查询
    reasoning_content: str = ""              # DeepSeek 推理内容
    
    # === 全局校准 ===
    alignment_score: float = 0.0             # 与用户目标对齐度 0-1
    alignment_note: str = ""                 # 对齐说明
    remaining_gaps: List[str] = field(default_factory=list)  # 剩余缺口
    estimated_rounds_remaining: int = 0      # 预估剩余轮次
    
    # === 累积描述 ===
    cumulative_progress: str = ""            # 累积进展描述
    reflection_narrative: str = ""           # 反思叙述（兼容旧字段）
    
    def to_reflection_result(self) -> 'ReflectionResult':
        """转换为 ReflectionResult 以兼容现有代码"""
        return ReflectionResult(
            goal_achieved=self.goal_achieved,
            goal_achievement_reason="",
            info_sufficiency=self.info_sufficiency,
            info_quality=self.info_quality,
            quality_issues=self.quality_issues,
            key_findings=self.key_findings,
            inferred_insights=self.inferred_insights,
            needs_deeper_search=len(self.remaining_gaps) > 0,
            deeper_search_points=self.remaining_gaps[:2] if self.remaining_gaps else [],
            suggested_next_query=self.search_query,
            next_round_purpose=self.search_strategy,
            alignment_with_goal=self.alignment_score,
            alignment_note=self.alignment_note,
            remaining_gaps=self.remaining_gaps,
            estimated_rounds_remaining=self.estimated_rounds_remaining,
            reflection_narrative=self.reflection_narrative,
            cumulative_progress=self.cumulative_progress,
        )


@dataclass
class AnswerFramework:
    """
    答案框架 - 目标导向的核心结构

    ⚠️ DEPRECATED (v7.220): 此类已被 SearchFramework 替代
    保留此类仅用于向后兼容，新代码请使用 SearchFramework

    追踪"回答用户问题"的完成度，而非"探索信息"的覆盖度
    """
    original_query: str                      # 用户原始问题
    answer_goal: str = ""                    # 回答目标：用户期望得到什么样的答案
    key_aspects: List[KeyAspect] = field(default_factory=list)  # 关键信息面
    collected_evidence: Dict[str, List[str]] = field(default_factory=dict)  # url -> 证据列表
    overall_completeness: float = 0.0        # 整体完成度
    readiness: AnswerReadiness = AnswerReadiness.NOT_READY  # 回答就绪状态
    created_at: float = 0.0
    updated_at: float = 0.0
    # v7.186: 累积进展追踪
    cumulative_progress: str = ""            # 累积进展描述（每轮更新）
    last_reflection: Optional['ReflectionResult'] = None  # 上一轮反思（驱动下一轮）
    # v7.230: 轮次洞察累积存储（不再覆盖）
    round_insights: List['RoundInsights'] = field(default_factory=list)  # 所有轮次的结构化洞察
    
    def get_missing_aspects(self) -> List[KeyAspect]:
        """获取缺失的关键信息面"""
        return [a for a in self.key_aspects if a.status == "missing"]
    
    def get_incomplete_aspects(self) -> List[KeyAspect]:
        """获取不完整的信息面"""
        return [a for a in self.key_aspects if a.status in ("missing", "partial")]
    
    def get_next_search_target(self) -> Optional[KeyAspect]:
        """获取下一个需要搜索的信息面（按重要性排序）"""
        incomplete = self.get_incomplete_aspects()
        if not incomplete:
            return None
        # 优先搜索重要性高且未被搜索过的
        return min(incomplete, key=lambda a: (-a.importance, a.last_searched_round))
    
    def can_answer_completely(self) -> bool:
        """是否能够完整回答用户问题"""
        if not self.key_aspects:
            return False
        # 所有高重要性(>=4)的信息面都至少是partial
        high_importance = [a for a in self.key_aspects if a.importance >= 4]
        return all(a.status != "missing" for a in high_importance)
    
    def calculate_completeness(self) -> float:
        """计算回答完成度"""
        if not self.key_aspects:
            return 0.0
        total_weight = sum(a.importance for a in self.key_aspects)
        achieved = sum(a.importance * a.completion_score for a in self.key_aspects)
        return achieved / total_weight if total_weight > 0 else 0.0


@dataclass
class RoundInsights:
    """
    轮次洞察累积器 - v7.230 新增
    
    每轮搜索后的结构化洞察，累积存储而非覆盖
    用于最终答案生成时充分利用所有轮次的发现
    """
    round_number: int                        # 轮次编号
    target_aspect: str = ""                  # 搜索目标
    search_query: str = ""                   # 搜索查询
    
    # === 核心发现（保留结构） ===
    key_findings: List[str] = field(default_factory=list)       # 直接发现
    inferred_insights: List[str] = field(default_factory=list)  # 推断洞察
    
    # === 质量评价（不再丢弃） ===
    info_sufficiency: float = 0.0            # 信息充分度 0-1
    info_quality: float = 0.0                # 信息质量 0-1
    quality_issues: List[str] = field(default_factory=list)  # 质量问题
    
    # === 对齐评估 ===
    alignment_score: float = 0.0             # 与用户目标对齐度 0-1
    alignment_note: str = ""                 # 对齐说明
    remaining_gaps: List[str] = field(default_factory=list)  # 剩余缺口
    
    # === 本轮最佳来源 ===
    best_source_urls: List[str] = field(default_factory=list)  # 本轮最佳来源URLs（Top-3）
    sources_count: int = 0                   # 本轮来源总数
    
    # === 累积进展 ===
    progress_description: str = ""           # 本轮进展描述（不截断）


@dataclass
class SearchRoundState:
    """单轮搜索状态 - v7.186 增强反思驱动"""
    round_number: int
    phase: SearchPhase
    target_aspect: str              # 本轮搜索的目标信息面
    search_query: str               # 搜索查询
    status: str = "pending"
    sources_found: int = 0
    info_collected: List[str] = field(default_factory=list)
    completeness_delta: float = 0.0
    execution_time: float = 0.0
    # v7.186: 专家叙事内容持久化
    thinking_narrative: str = ""    # 搜索前的思考叙事（自然语言）
    reflection: str = ""            # 搜索后的反思复盘（含推断）
    search_strategy: str = ""       # 搜索策略说明


@dataclass
class UcpptSearchResult:
    """ucppt搜索结果"""
    original_query: str
    framework: AnswerFramework
    rounds: List[SearchRoundState] = field(default_factory=list)
    all_sources: List[Dict[str, Any]] = field(default_factory=list)
    final_answer: str = ""
    total_rounds: int = 0
    final_completeness: float = 0.0
    total_execution_time: float = 0.0


# ==================== v7.214: DeepSeek 专用分析引擎 ====================

class DeepSeekAnalysisEngine:
    """DeepSeek-Reasoner 专用分析引擎 - v7.214"""
    
    def __init__(self):
        self.thinking_model = "deepseek-reasoner"
        self.eval_model = "deepseek-chat"
        self.quality_threshold = 0.75
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.deepseek_base_url = DEEPSEEK_BASE_URL
        
        if not self.deepseek_api_key:
            logger.warning("⚠️ [DeepSeek Analysis] DEEPSEEK_API_KEY 未配置")
    
    async def _deepseek_call(
        self,
        prompt: str,
        model: str = None,
        max_tokens: int = 4000,
        temperature: float = 0.7
    ) -> Optional[str]:
        """DeepSeek API 调用"""
        if not self.deepseek_api_key:
            logger.error("❌ [DeepSeek Analysis] API Key 未配置")
            return None
        
        model = model or self.thinking_model
        
        try:
            import httpx
            
            logger.info(f"🚀 [DeepSeek Analysis] 开始API调用 | model={model} | max_tokens={max_tokens}")
            start_time = time.time()
            
            # 缩短超时到60秒，快速失效避免长时间卡住
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.deepseek_base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.deepseek_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                        "stream": False
                    }
                )
                
                call_time = time.time() - start_time
                logger.info(f"⏱️ [DeepSeek Analysis] API调用完成 | 耗时={call_time:.2f}秒")
                
                if response.status_code == 200:
                    result = response.json()
                    message = result["choices"][0]["message"]

                    # 🔧 v7.215: 修复 DeepSeek Reasoner 响应字段读取
                    # deepseek-reasoner 返回 reasoning_content，deepseek-chat 返回 content
                    content = message.get("reasoning_content") or message.get("content", "")

                    # 验证内容非空
                    if not content or not content.strip():
                        logger.error(f"❌ [DeepSeek Analysis] API返回空内容 | model={model} | response={result}")
                        return None

                    logger.info(f"✅ [DeepSeek Analysis] 获得响应 | 长度={len(content)}字符")
                    return content
                else:
                    logger.error(f"❌ [DeepSeek Analysis] API调用失败: {response.status_code} | 响应: {response.text}")
                    return None
        
        except asyncio.TimeoutError:
            logger.error("⏰ [DeepSeek Analysis] API调用超时（60秒） - 启用快速备份策略")
            return {
                "status": "timeout",
                "error": "API调用超时，已启用备份搜索模式",
                "content": "由于网络延迟，已切换到快速搜索模式"
            }
        except Exception as e:
            import traceback
            logger.error(f"❌ [DeepSeek Analysis] API调用异常: {e}")
            logger.error(f"📋 [DeepSeek Analysis] 异常堆栈:\n{traceback.format_exc()}")
            return None
    
    async def execute_l0_dialogue(
        self, 
        query: str, 
        context: Dict[str, Any] = None
    ) -> Optional[L0DialogueResult]:
        """L0 对话式分析 - 专注用户理解"""
        
        logger.info("🔍 [L0 Debug] 开始execute_l0_dialogue方法")
        prompt = self._build_l0_prompt(query, context or {})
        logger.info(f"📝 [L0 Debug] 构建prompt完成 | 长度={len(prompt)}字符")
        
        start_time = time.time()
        logger.info(f"🚀 [L0 Debug] 准备调用_deepseek_call | model={self.thinking_model}")
        raw_result = await self._deepseek_call(prompt, self.thinking_model)
        execution_time = time.time() - start_time
        logger.info(f"⏱️ [L0 Debug] _deepseek_call完成 | 耗时={execution_time:.2f}秒 | 有结果={raw_result is not None}")
        
        if not raw_result:
            logger.error("❌ [L0 Debug] DeepSeek API调用失败，无结果")
            return None

        # 🔧 v7.215: 检测空响应
        if isinstance(raw_result, str) and not raw_result.strip():
            logger.error("❌ [L0 Debug] DeepSeek API返回空字符串")
            return None

        logger.info("🔄 [L0 Debug] 开始解析L0结果")
        result = self._parse_l0_result(raw_result, execution_time)
        logger.info(f"✅ [L0 Debug] L0结果解析完成 | 成功={result is not None}")
        return result
    
    async def execute_l1_l5_framework(
        self,
        query: str,
        l0_result: L0DialogueResult
    ) -> Optional[L1L5FrameworkResult]:
        """L1-L5 深度框架分析 - 专注理论建模"""
        
        prompt = self._build_framework_prompt(query, l0_result)
        
        start_time = time.time()
        raw_result = await self._deepseek_call(prompt, self.thinking_model)
        execution_time = time.time() - start_time
        
        if not raw_result:
            return None
            
        return self._parse_framework_result(raw_result, execution_time, l0_result)
    
    async def execute_synthesis(
        self,
        query: str,
        l0_result: L0DialogueResult,
        framework_result: L1L5FrameworkResult
    ) -> Optional[SynthesisResult]:
        """综合分析 - 生成搜索任务"""
        
        prompt = self._build_synthesis_prompt(query, l0_result, framework_result)
        
        start_time = time.time()
        raw_result = await self._deepseek_call(prompt, self.eval_model)  # 使用eval模型
        execution_time = time.time() - start_time
        
        if not raw_result:
            return None
            
        return self._parse_synthesis_result(raw_result, execution_time)
    
    def _build_l0_prompt(self, query: str, context: Dict[str, Any]) -> str:
        """L0 专用 Prompt - 专注对话式用户理解"""
        return f"""你是一位资深的用户研究专家。请用温暖、专业的对话方式分析用户。

## 用户问题
{query}

## 上下文
{json.dumps(context, ensure_ascii=False, indent=2)}

## 你的分析任务

### 对话输出（thinking 部分 - 展示给用户）
请像与用户面对面交谈一样，自然地分析以下内容：

1. **用户画像识别** 
   - 从地理位置推断：气候特点、文化背景、生活节奏
   - 从表达方式推断：年龄段、教育背景、职业倾向
   - 从关注点推断：身份标签、价值观、生活态度

2. **项目背景理解**
   - 项目的真实规模和约束条件
   - 该背景下的可能性边界

3. **隐性需求挖掘**（重点）
   基于用户画像，推断未明说但重要的需求：
   - 功能性隐需：空间、设施、系统
   - 情感性隐需：氛围、体验、归属感
   - 社会性隐需：身份认同、社交关系

请保持**亲切专业**的语气，用**自然段落**组织，重要信息用**加粗**标注。

### 结构化输出（content 部分 - 系统使用）
```json
{{
    "user_profile": {{
        "demographics": {{"location": "", "age_range": "", "occupation": "", "education": ""}},
        "identity_tags": ["标签1", "标签2"],
        "lifestyle_indicators": ["指标1", "指标2"],
        "value_system": "价值体系描述"
    }},
    "project_context": {{
        "scale": "项目规模",
        "constraints": ["约束1", "约束2"],  
        "opportunities": ["机会1", "机会2"]
    }},
    "implicit_needs": {{
        "functional": ["功能需求1", "功能需求2"],
        "emotional": ["情感需求1", "情感需求2"],
        "social": ["社会需求1", "社会需求2"]
    }},
    "confidence_assessment": {{
        "profile_confidence": 0.85,
        "need_identification_confidence": 0.80,
        "missing_info": ["缺失信息1", "缺失信息2"]
    }}
}}
```

**质量标准**：
- 用户画像完整性 ≥ 80%
- 隐性需求识别 ≥ 3 项
- 对话自然度主观评分 ≥ 4/5"""
    
    def _build_framework_prompt(self, query: str, l0_result: L0DialogueResult) -> str:
        """L1-L5 专用 Prompt - 专注深度理论分析"""
        return f"""你是一位跨学科分析专家。基于 L0 用户理解，进行深度理论建模。

## 用户问题
{query}

## L0 分析结果
- **用户画像**：{l0_result.user_profile.to_dict()}
- **隐性需求**：{l0_result.implicit_needs}
- **对话理解**：{l0_result.context_understanding[:200]}...

## 分层分析框架

### L1：第一性原理分解（Facts Atomization）
将问题分解为不可再分的事实原子，每个原子必须：
- 可独立验证
- 无主观判断
- 可量化或可观测

**输出格式**：["事实原子1", "事实原子2", ...]

### L2：跨学科建模（Multi-Disciplinary Modeling）
从至少 3 个学科视角建模，要求：
- **心理学视角**：用户的认知模式、情感需求、行为模式
- **社会学视角**：社会角色、权力关系、文化符号
- **美学视角**：审美偏好、风格语言、感知体验
- **（可选）经济学/人类学/现象学视角**

### L3：核心张力识别（Core Tension Analysis）
识别最关键的对立面，形成 "A vs B" 的张力公式：
- 必须是真正的两难选择
- 必须影响设计的根本方向
- 必须有具体的实现路径差异

### L4：JTBD任务识别（Jobs-to-be-Done）
用户雇佣这个项目要完成什么"进步"：
- 从什么状态 → 到什么状态
- 解决什么具体问题
- 实现什么具体价值

### L5：锐度评估（Sharpness Assessment）
评估分析的专业深度：
- **专一性**（Specificity）：是否针对特定情况，避免泛泛而谈
- **可操作性**（Actionability）：是否提供具体可执行的方向
- **深度**（Depth）：是否触及问题的本质层面

输出 JSON 格式，包含所有 L1-L5 的分析结果。

**质量标准**：
- 事实原子化 ≥ 5 个独立事实
- 跨学科整合度 ≥ 80%
- 张力识别精度 ≥ 85%
- 总体锐度评分 ≥ 80"""
    
    def _build_synthesis_prompt(
        self, 
        query: str, 
        l0_result: L0DialogueResult, 
        framework_result: L1L5FrameworkResult
    ) -> str:
        """综合分析 Prompt - 生成搜索任务"""
        return f"""基于前面的分析，现在生成结构化的搜索执行计划。

## 用户问题
{query}

## L0 用户理解
{l0_result.context_understanding}

## L1-L5 框架分析
- **L1 事实原子**：{framework_result.l1_facts}
- **L3 核心张力**：{framework_result.l3_tensions}
- **L4 JTBD**：{framework_result.l4_jtbd}

## 生成搜索主线和任务

请输出 JSON 格式的搜索执行计划：

```json
{{
    "search_master_line": {{
        "core_question": "一句话概括核心问题",
        "boundary": "搜索边界定义",
        "framework_summary": "搜索路线图概览",
        "search_phases": ["基础信息", "深度案例", "对比验证"]
    }},
    "search_tasks": [
        {{
            "id": "task_1",
            "task": "具体搜索任务描述",
            "purpose": "任务目的",
            "phase": "基础信息",
            "priority": 1,
            "depends_on": [],
            "expected_info": ["期望获得的信息1", "期望获得的信息2"],
            "validation_criteria": ["验证标准1", "验证标准2"]
        }}
    ],
    "execution_plan": {{
        "total_estimated_rounds": 6,
        "critical_path": ["task_1", "task_3", "task_5"],
        "quality_checkpoints": [2, 4, 6]
    }}
}}
```

确保：
1. 任务之间有逻辑依赖关系
2. 每个阶段至少2个任务
3. 搜索范围聚焦且可执行
"""
    
    def _parse_l0_result(self, raw_result: str, execution_time: float) -> L0DialogueResult:
        """解析 L0 分析结果"""
        try:
            # 分离 thinking 和 content 部分
            if "```json" in raw_result:
                # thinking 部分是 json 之前的内容
                dialogue_content = raw_result.split("```json")[0].strip()
                # content 部分是 json 内容
                json_part = raw_result.split("```json")[1].split("```")[0]
                content = json.loads(json_part)
            else:
                # 降级处理：整个结果作为对话内容
                dialogue_content = raw_result
                content = {
                    "user_profile": {},
                    "implicit_needs": {"functional": [], "emotional": [], "social": []},
                    "confidence_assessment": {"profile_confidence": 0.5}
                }
            
            # 构建用户画像
            user_profile_data = content.get("user_profile", {})
            user_profile = StructuredUserInfo()
            if "demographics" in user_profile_data:
                user_profile.demographics.update(user_profile_data["demographics"])
            if "identity_tags" in user_profile_data:
                user_profile.identity_tags = user_profile_data["identity_tags"]
            
            # 提取隐性需求
            implicit_needs_data = content.get("implicit_needs", {})
            implicit_needs = []
            for category, needs in implicit_needs_data.items():
                implicit_needs.extend(needs)
            
            # 计算质量评分
            confidence = content.get("confidence_assessment", {})
            quality_score = (
                confidence.get("profile_confidence", 0.5) * 0.4 +
                confidence.get("need_identification_confidence", 0.5) * 0.4 +
                (len(implicit_needs) / 6) * 0.2  # 隐性需求数量贡献
            )
            
            return L0DialogueResult(
                phase=AnalysisPhase.L0_DIALOGUE,
                content=content,
                quality_score=min(quality_score, 1.0),
                execution_time=execution_time,
                user_profile=user_profile,
                context_understanding=dialogue_content,
                implicit_needs=implicit_needs,
                dialogue_content=dialogue_content
            )
            
        except Exception as e:
            logger.error(f"❌ [DeepSeek Analysis] L0结果解析失败: {e}")
            # 降级处理
            return L0DialogueResult(
                phase=AnalysisPhase.L0_DIALOGUE,
                content={"error": str(e)},
                quality_score=0.3,
                execution_time=execution_time,
                user_profile=StructuredUserInfo(),
                context_understanding=raw_result[:200],
                implicit_needs=[],
                dialogue_content=raw_result[:500]
            )
    
    def _parse_framework_result(
        self, 
        raw_result: str, 
        execution_time: float,
        l0_result: L0DialogueResult
    ) -> L1L5FrameworkResult:
        """解析 L1-L5 框架分析结果"""
        try:
            # 尝试提取JSON
            if "```json" in raw_result:
                json_part = raw_result.split("```json")[1].split("```")[0]
                content = json.loads(json_part)
            else:
                # 简单JSON解析尝试
                import re
                json_match = re.search(r'\{.*\}', raw_result, re.DOTALL)
                if json_match:
                    content = json.loads(json_match.group())
                else:
                    raise ValueError("未找到JSON内容")
            
            # 提取各层分析结果
            l1_facts = content.get("l1_facts", [])
            l2_models = content.get("l2_models", {})
            l3_tensions = content.get("l3_tensions", "")
            l4_jtbd = content.get("l4_jtbd", "")
            l5_sharpness = content.get("l5_sharpness", {})
            
            # 计算框架一致性
            framework_coherence = min(
                len(l1_facts) / 5,  # 事实原子数量
                len(l2_models) / 3,  # 跨学科模型数量
                1.0 if l3_tensions else 0.0,  # 张力识别
                1.0 if l4_jtbd else 0.0,  # JTBD识别
                l5_sharpness.get("overall_sharpness", 0) / 100  # 锐度评分
            )
            
            # 计算质量评分
            quality_score = (
                (len(l1_facts) / 6) * 0.25 +
                (len(l2_models) / 4) * 0.25 +
                (1.0 if l3_tensions else 0.0) * 0.25 +
                framework_coherence * 0.25
            )
            
            return L1L5FrameworkResult(
                phase=AnalysisPhase.L1_L5_FRAMEWORK,
                content=content,
                quality_score=min(quality_score, 1.0),
                execution_time=execution_time,
                l1_facts=l1_facts,
                l2_models=l2_models,
                l3_tensions=l3_tensions,
                l4_jtbd=l4_jtbd,
                l5_sharpness=l5_sharpness,
                framework_coherence=framework_coherence
            )
            
        except Exception as e:
            logger.error(f"❌ [DeepSeek Analysis] L1-L5结果解析失败: {e}")
            # 降级处理
            return L1L5FrameworkResult(
                phase=AnalysisPhase.L1_L5_FRAMEWORK,
                content={"error": str(e)},
                quality_score=0.3,
                execution_time=execution_time,
                l1_facts=[],
                l2_models={},
                l3_tensions="",
                l4_jtbd="",
                l5_sharpness={},
                framework_coherence=0.0
            )
    
    def _parse_synthesis_result(self, raw_result: str, execution_time: float) -> SynthesisResult:
        """解析综合分析结果"""
        try:
            # 提取JSON
            if "```json" in raw_result:
                json_part = raw_result.split("```json")[1].split("```")[0]
                content = json.loads(json_part)
            else:
                import re
                json_match = re.search(r'\{.*\}', raw_result, re.DOTALL)
                if json_match:
                    content = json.loads(json_match.group())
                else:
                    raise ValueError("未找到JSON内容")
            
            # 构建搜索主线
            search_master_data = content.get("search_master_line", {})
            search_master_line = SearchMasterLine(
                core_question=search_master_data.get("core_question", ""),
                boundary=search_master_data.get("boundary", ""),
                framework_summary=search_master_data.get("framework_summary", ""),
                search_phases=search_master_data.get("search_phases", [])
            )
            
            # 构建搜索任务
            tasks_data = content.get("search_tasks", [])
            for task_data in tasks_data:
                task = SearchTask(
                    id=task_data.get("id", ""),
                    task=task_data.get("task", ""),
                    purpose=task_data.get("purpose", ""),
                    priority=task_data.get("priority", 1),
                    phase=task_data.get("phase", "基础信息"),
                    depends_on=task_data.get("depends_on", []),
                    expected_info=task_data.get("expected_info", []),
                    validation_criteria=task_data.get("validation_criteria", [])
                )
                search_master_line.search_tasks.append(task)
            
            # 构建答案框架（简化版）
            answer_framework = AnswerFramework(
                user_info=StructuredUserInfo(),  # 会在后续填入
                core_aspects=[],
                overall_completeness=0.0
            )
            
            # 执行计划
            execution_plan = content.get("execution_plan", {})
            
            quality_score = min(
                len(search_master_line.search_tasks) / 6,  # 任务数量
                1.0 if search_master_line.core_question else 0.0,  # 核心问题
                len(search_master_line.search_phases) / 3  # 阶段数量
            )
            
            return SynthesisResult(
                phase=AnalysisPhase.SYNTHESIS,
                content=content,
                quality_score=min(quality_score, 1.0),
                execution_time=execution_time,
                search_master_line=search_master_line,
                answer_framework=answer_framework,
                execution_plan=execution_plan
            )
            
        except Exception as e:
            logger.error(f"❌ [DeepSeek Analysis] 综合结果解析失败: {e}")
            # 降级处理
            return SynthesisResult(
                phase=AnalysisPhase.SYNTHESIS,
                content={"error": str(e)},
                quality_score=0.3,
                execution_time=execution_time,
                search_master_line=SearchMasterLine(),
                answer_framework=AnswerFramework(StructuredUserInfo(), [], 0.0),
                execution_plan={}
            )

# ==================== 主引擎类 ====================

class UcpptSearchEngine:
    """
    ucppt 深度迭代搜索引擎 (v7.187) - 流式思考+搜索查询修复
    
    核心理念：像资深专家一样思考和表达
    
    核心创新：
    1. 专家叙事：用自然语言讲述思考过程（"让我先了解..."）
    2. 思考-搜索-反思：每轮三步走，思考在前
    3. 推断能力：从间接信息中提取洞察
    4. 语义完成度："能否回答问题"而非数值评分
    5. 动态策略：根据知识状态决定下一步
    """
    
    def __init__(
        self,
        max_rounds: int = MAX_SEARCH_ROUNDS,
        completeness_threshold: float = COMPLETENESS_THRESHOLD,
        thinking_model: str = THINKING_MODEL,
        eval_model: str = EVAL_MODEL,
    ):
        """
        初始化搜索引擎
        
        Args:
            max_rounds: 最大搜索轮数（默认15）
            completeness_threshold: 回答完整度阈值（默认0.8）
            thinking_model: 思考模式模型（问题分析、搜索策略）
            eval_model: 评估模型（完成度评估）
        """
        self.max_rounds = max_rounds
        self.completeness_threshold = completeness_threshold
        self.thinking_model = thinking_model
        self.eval_model = eval_model
        
        # DeepSeek 官方 API 配置（thinking_model 和 eval_model 使用）
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.deepseek_base_url = DEEPSEEK_BASE_URL
        if self.deepseek_api_key:
            logger.info("🧠 [Ucppt v7.187] DeepSeek 官方 API 已配置")
        else:
            logger.warning("⚠️ [Ucppt v7.187] DEEPSEEK_API_KEY 未配置，思考功能可能受限")
        
        # OpenRouter API 配置（synthesis_model 使用）
        openrouter_keys = os.getenv("OPENROUTER_API_KEYS", "")
        if openrouter_keys:
            self.openai_api_key = openrouter_keys.split(",")[0].strip()
            self.openai_base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
            logger.info("🧠 [Ucppt v7.187] OpenRouter API 已配置（用于答案生成）")
        else:
            self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
            self.openai_base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        
        # 初始化搜索服务
        self.bocha_service = get_ai_search_service() if get_ai_search_service else None
        
        # v7.199: 初始化 OpenAlex 学术搜索
        self.openalex_tool = None
        if OPENALEX_AVAILABLE and OPENALEX_SEARCH_ENABLED:
            try:
                self.openalex_tool = OpenAlexSearchTool()
                logger.info("🎓 [Ucppt v7.199] OpenAlex 学术搜索已初始化")
            except Exception as e:
                logger.warning(f"⚠️ [Ucppt v7.199] OpenAlex 初始化失败: {e}")
        
        # v7.199: 查询分类结果缓存
        self._query_classification = None  # Optional[QueryClassification]

        # v7.199: 查询去重 - 记录已使用的查询
        self._used_queries: List[str] = []
        self._query_similarity_threshold = 0.8  # 相似度阈值

        # 🆕 v7.237: 搜索质量配置集成（方案C）
        from intelligent_project_analyzer.settings import settings
        self.search_quality_config = settings.search_quality
        
        # 应用质量优化配置
        if self.search_quality_config.design_professional_mode:
            self.completeness_threshold = max(completeness_threshold, 0.75)  # 提升完成度要求
            logger.info(f"🎨 [v7.237] 专业设计搜索模式已启用 | threshold={self.completeness_threshold}")

        # v7.238: 内心独白过滤模式列表（中度过滤）
        self._verbose_patterns = [
            r'^好的[，,].*?(?:用户|需求|问题)',
            r'^让我(?:想想|思考|分析)',
            r'^首先[，,]?我需要',
            r'^接下来[，,]?我(?:需要|要|将)',
            r'^我(?:理解|明白)了',
            r'^现在[，,]?我(?:来|开始)',
            r'^嗯[，,]',
            r'^这个问题(?:涉及|需要)',
            r'^OK[，,]',
            r'^Alright[，,]',
        ]
        self._verbose_regex = re.compile('|'.join(self._verbose_patterns), re.IGNORECASE)

        # v7.214: 结构化分析引擎和质量控制
        self.deepseek_analysis_engine = DeepSeekAnalysisEngine()
        self.quality_gates = {}  # 质量门控管理
        self.analysis_session = None  # 当前分析会话

        logger.info(f"🧠 [Ucppt v7.200] 引擎初始化 | max_rounds={max_rounds} | threshold={completeness_threshold}")
        logger.info("🔬 [Ucppt v7.214] 结构化分析引擎已初始化")
    
    # ==================== v7.238: 思考内容过滤 ====================
    
    def _filter_verbose_monologue(self, text: str) -> str:
        """
        过滤冗余内心独白 - v7.238
        
        中度过滤策略：
        - 去除开场白（"好的，用户要求..."）
        - 去除自言自语（"让我想想..."）
        - 保留实质性分析内容
        """
        if not text:
            return text
        
        # 按行处理，过滤匹配的行首模式
        lines = text.split('\n')
        filtered_lines = []
        
        for line in lines:
            stripped = line.strip()
            # 检查是否匹配冗余模式
            if stripped and self._verbose_regex.match(stripped):
                # 跳过匹配的开头，但保留后续内容
                # 尝试提取冒号或逗号后的实质内容
                for sep in ['：', ':', '，', ',']:
                    if sep in stripped:
                        parts = stripped.split(sep, 1)
                        if len(parts) > 1 and len(parts[1].strip()) > 10:
                            filtered_lines.append(parts[1].strip())
                            break
                # 如果没有实质内容，跳过整行
                continue
            else:
                filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)
    
    # ==================== v7.214: 结构化问题分析方法 ====================
    
    async def structured_problem_analysis(
        self, 
        query: str, 
        context: Dict[str, Any] = None
    ) -> Optional[AnalysisSession]:
        """
        结构化问题分析 - v7.214 新架构
        
        分为三个独立阶段：
        1. L0 对话式分析：用户理解和需求挖掘
        2. L1-L5 深度分析：理论建模和框架构建 
        3. 综合分析：生成搜索任务和执行计划
        """
        logger.info("🔬 [结构化分析 v7.214] 开始三阶段分析流程")
        logger.info(f"🎯 [v7.214 Debug] 输入参数 | query长度={len(query)} | context={bool(context)}")
        
        start_time = time.time()
        session_id = f"analysis_{int(time.time())}"
        context = context or {}
        
        # 创建分析会话
        analysis_session = AnalysisSession(
            session_id=session_id,
            query=query,
            context=context,
            start_time=start_time
        )
        logger.info(f"📝 [v7.214 Debug] 创建分析会话成功 | session_id={session_id}")
        
        try:
            # === 阶段 1: L0 对话式分析 ===
            logger.info("🎯 [L0 阶段] 执行对话式用户分析")
            logger.info("🚀 [v7.214 Debug] 准备调用deepseek_analysis_engine.execute_l0_dialogue")
            l0_result = await self.deepseek_analysis_engine.execute_l0_dialogue(query, context)
            logger.info(f"📊 [v7.214 Debug] L0阶段返回结果: {l0_result is not None}")
            
            if not l0_result:
                logger.error("❌ [L0 阶段] 用户分析失败")
                return None
            
            analysis_session.l0_result = l0_result
            logger.info("✅ [v7.214 Debug] L0结果已保存到analysis_session")
            
            # 质量门控检查
            l0_quality_gate = QualityGate(threshold=0.7)
            
            if not l0_quality_gate.check_phase_quality(AnalysisPhase.L0_DIALOGUE, l0_result):
                logger.warning("⚠️ [L0 质量门控] 用户分析质量不足，但继续执行")
            else:
                logger.info("✅ [L0 质量门控] 用户分析质量合格")
            
            # === 阶段 2: L1-L5 深度框架分析 ===
            logger.info("🧠 [L1-L5 阶段] 执行深度理论分析")
            framework_result = await self.deepseek_analysis_engine.execute_l1_l5_framework(
                query, l0_result
            )
            
            if not framework_result:
                logger.error("❌ [L1-L5 阶段] 深度分析失败")
                return None
            
            analysis_session.framework_result = framework_result
            
            # L1-L5 质量门控
            framework_quality_gate = QualityGate(threshold=0.8)
            
            if not framework_quality_gate.check_phase_quality(AnalysisPhase.L1_L5_FRAMEWORK, framework_result):
                logger.warning("⚠️ [L1-L5 质量门控] 理论分析深度不足")
            else:
                logger.info("✅ [L1-L5 质量门控] 理论分析质量优秀")
            
            # === 阶段 3: 综合分析和搜索规划 ===
            logger.info("🎯 [综合阶段] 生成搜索执行计划")
            synthesis_result = await self.deepseek_analysis_engine.execute_synthesis(
                query, l0_result, framework_result
            )
            
            if not synthesis_result:
                logger.error("❌ [综合阶段] 搜索规划失败")
                return None
            
            analysis_session.synthesis_result = synthesis_result
            
            # 综合质量门控
            synthesis_quality_gate = QualityGate(threshold=0.75)
            
            if not synthesis_quality_gate.check_phase_quality(AnalysisPhase.SYNTHESIS, synthesis_result):
                logger.warning("⚠️ [综合质量门控] 搜索计划完整性不足")
            else:
                logger.info("✅ [综合质量门控] 搜索计划质量优秀")
            
            # 计算总体分析质量
            total_time = time.time() - start_time
            analysis_session.total_execution_time = total_time
            analysis_session.overall_quality = (
                l0_result.quality_score * 0.3 +
                framework_result.quality_score * 0.4 +
                synthesis_result.quality_score * 0.3
            )
            
            logger.info(
                f"🎉 [结构化分析完成] "
                f"总耗时: {total_time:.1f}s | "
                f"总体质量: {analysis_session.overall_quality:.1%} | "
                f"生成任务: {len(synthesis_result.search_master_line.search_tasks) if synthesis_result.search_master_line else 0}个"
            )
            
            # 保存分析会话
            self.analysis_session = analysis_session
            return analysis_session
            
        except Exception as e:
            logger.error(f"❌ [结构化分析] 执行失败: {e}")
            return None
    
    async def enhanced_quality_assessment(
        self,
        search_results: List[Dict[str, Any]],
        query_context: str,
        phase: str = "search"
    ) -> Dict[str, Any]:
        """
        增强的多层次质量评估 - v7.214
        
        评估层次：
        1. 规则基础：基本筛选（重复、长度、格式）
        2. 语义相关性：内容与查询的相关度
        3. 上下文一致性：与已有信息的整合度
        4. LLM 深度评估：专业性和可信度
        """
        logger.info(f"🔍 [质量评估 v7.214] 开始 {len(search_results)} 条结果的多层评估")
        
        if not search_results:
            return {
                "filtered_results": [],
                "quality_metrics": {"total_score": 0.0, "layer_scores": {}},
                "assessment_summary": "无搜索结果"
            }
        
        assessment_start = time.time()
        
        # === 第一层：规则基础筛选 ===
        rule_filtered = []
        for result in search_results:
            content = result.get("content", "")
            title = result.get("title", "")
            
            # 基本质量检查
            if (
                len(content.strip()) >= 50 and  # 最小内容长度
                len(title.strip()) >= 5 and     # 最小标题长度
                not self._is_duplicate_content(content, [r["content"] for r in rule_filtered])
            ):
                result["rule_score"] = self._calculate_rule_score(result)
                rule_filtered.append(result)
        
        logger.info(f"📋 [规则筛选] {len(search_results)} → {len(rule_filtered)} 条")
        
        if not rule_filtered:
            return {
                "filtered_results": [],
                "quality_metrics": {"total_score": 0.0, "layer_scores": {"rule": 0.0}},
                "assessment_summary": "规则筛选后无结果"
            }
        
        # === 第二层：语义相关性评估 ===
        semantic_scores = []
        for result in rule_filtered:
            semantic_score = await self._assess_semantic_relevance(
                result["content"],
                query_context
            )
            result["semantic_score"] = semantic_score
            semantic_scores.append(semantic_score)

        # v7.235: 降低阈值并添加保底逻辑
        SEMANTIC_THRESHOLD = 0.3  # 从 0.5 降低到 0.3
        semantic_filtered = [r for r in rule_filtered if r.get("semantic_score", 0) > SEMANTIC_THRESHOLD]

        # 保底逻辑：如果过滤后为空但规则筛选有结果，保留前5条
        if len(semantic_filtered) == 0 and len(rule_filtered) > 0:
            logger.warning(f"⚠️ [v7.235] 语义筛选过于严格，保留规则筛选前5条")
            semantic_filtered = rule_filtered[:5]

        logger.info(f"🎯 [语义筛选] {len(rule_filtered)} → {len(semantic_filtered)} 条")
        
        # === 第三层：上下文一致性评估 ===
        if self.analysis_session and semantic_filtered:
            context_scores = []
            session_context = {
                "user_profile": self.analysis_session.l0_result.user_profile.to_dict() if self.analysis_session.l0_result else {},
                "implicit_needs": self.analysis_session.l0_result.implicit_needs if self.analysis_session.l0_result else [],
                "core_tensions": self.analysis_session.framework_result.l3_tensions if self.analysis_session.framework_result else ""
            }
            
            for result in semantic_filtered:
                context_score = await self._assess_context_consistency(
                    result["content"],
                    session_context
                )
                result["context_score"] = context_score
                context_scores.append(context_score)
            
            # 保留上下文一致性 > 0.4 的结果
            context_filtered = [r for r in semantic_filtered if r.get("context_score", 0) > 0.4]
            logger.info(f"🔗 [上下文筛选] {len(semantic_filtered)} → {len(context_filtered)} 条")
        else:
            context_filtered = semantic_filtered
            logger.info("ℹ️ [上下文筛选] 无分析会话，跳过上下文评估")
        
        # === 第四层：LLM 深度质量评估 ===
        if context_filtered:
            llm_assessments = await self._llm_quality_assessment(
                context_filtered,
                query_context,
                phase
            )
            
            # 整合 LLM 评估结果
            for i, result in enumerate(context_filtered):
                if i < len(llm_assessments):
                    result.update(llm_assessments[i])
            
            # 按综合质量评分排序
            final_filtered = sorted(
                context_filtered,
                key=lambda x: x.get("total_quality_score", 0),
                reverse=True
            )
        else:
            final_filtered = context_filtered
        
        # 计算质量指标
        assessment_time = time.time() - assessment_start
        quality_metrics = {
            "total_score": sum(r.get("total_quality_score", 0) for r in final_filtered) / max(len(final_filtered), 1),
            "layer_scores": {
                "rule": sum(r.get("rule_score", 0) for r in rule_filtered) / max(len(rule_filtered), 1),
                "semantic": sum(r.get("semantic_score", 0) for r in semantic_filtered) / max(len(semantic_filtered), 1),
                "context": sum(r.get("context_score", 0) for r in context_filtered) / max(len(context_filtered), 1),
                "llm": sum(r.get("llm_quality_score", 0) for r in final_filtered) / max(len(final_filtered), 1)
            },
            "assessment_time": assessment_time,
            "filtering_ratio": len(final_filtered) / len(search_results)
        }
        
        assessment_summary = (
            f"四层筛选: {len(search_results)}→{len(rule_filtered)}→"
            f"{len(semantic_filtered)}→{len(context_filtered)}→{len(final_filtered)} | "
            f"总质量: {quality_metrics['total_score']:.1%} | "
            f"耗时: {assessment_time:.1f}s"
        )
        
        logger.info(f"📊 [质量评估完成] {assessment_summary}")
        
        return {
            "filtered_results": final_filtered[:10],  # 限制返回数量
            "quality_metrics": quality_metrics,
            "assessment_summary": assessment_summary
        }
    
    def _is_duplicate_content(self, content: str, existing_contents: List[str]) -> bool:
        """检查内容重复性"""
        if not existing_contents:
            return False
        
        content_words = set(content.lower().split())
        for existing in existing_contents:
            existing_words = set(existing.lower().split())
            if content_words and existing_words:
                similarity = len(content_words & existing_words) / len(content_words | existing_words)
                if similarity > 0.8:  # 80% 相似度阈值
                    return True
        return False
    
    def _calculate_rule_score(self, result: Dict[str, Any]) -> float:
        """计算规则基础评分"""
        score = 0.0
        
        content = result.get("content", "")
        title = result.get("title", "")
        
        # 内容长度评分 (0-0.3)
        content_length = len(content)
        if content_length > 1000:
            score += 0.3
        elif content_length > 500:
            score += 0.2
        elif content_length > 200:
            score += 0.1
        
        # 标题质量评分 (0-0.2)
        if len(title) > 20:
            score += 0.2
        elif len(title) > 10:
            score += 0.1
        
        # 来源可信度 (0-0.3)
        url = result.get("url", "")
        if any(domain in url for domain in [".edu", ".gov", ".org"]):
            score += 0.3
        elif any(domain in url for domain in ["wikipedia", "arxiv", "scholar"]):
            score += 0.25
        else:
            score += 0.1
        
        # 时效性 (0-0.2)
        publish_time = result.get("publish_time", "")
        if publish_time and "2024" in publish_time or "2025" in publish_time:
            score += 0.2
        elif publish_time and any(year in publish_time for year in ["2022", "2023"]):
            score += 0.1
        
        return min(score, 1.0)
    
    async def _assess_semantic_relevance(self, content: str, query_context: str) -> float:
        """语义相关性评估 - v7.235 增强版"""
        try:
            # v7.235: 验证查询有效性
            if not query_context or len(query_context.strip()) < 2:
                logger.debug(f"⚠️ [语义评估] 查询无效，返回默认分数 0.5")
                return 0.5  # 提高默认分数，避免过滤有效内容

            content_lower = content.lower()
            query_lower = query_context.lower().strip()

            # 移除纯空格和标点
            query_keywords = set(w for w in query_lower.split() if len(w) > 1)
            content_keywords = set(w for w in content_lower.split() if len(w) > 1)

            if not query_keywords:
                logger.debug(f"⚠️ [语义评估] 无有效关键词，返回默认分数 0.5")
                return 0.5

            # 关键词重叠度
            if query_keywords and content_keywords:
                keyword_overlap = len(query_keywords & content_keywords) / len(query_keywords | content_keywords)
                return min(keyword_overlap * 2, 1.0)  # 放大相关性

            return 0.3  # 默认基础相关性
        except Exception as e:
            logger.warning(f"⚠️ [语义评估] 异常: {e}")
            return 0.3
    
    async def _assess_context_consistency(
        self, 
        content: str, 
        session_context: Dict[str, Any]
    ) -> float:
        """上下文一致性评估"""
        try:
            score = 0.0
            content_lower = content.lower()
            
            # 与用户画像的一致性
            user_profile = session_context.get("user_profile", {})
            demographics = user_profile.get("demographics", {})
            
            if demographics.get("location"):
                location = demographics["location"].lower()
                if location in content_lower:
                    score += 0.3
            
            # 与隐性需求的匹配度
            implicit_needs = session_context.get("implicit_needs", [])
            for need in implicit_needs:
                if need.lower() in content_lower:
                    score += 0.1
            
            # 与核心张力的相关性
            tensions = session_context.get("core_tensions", "")
            if tensions and any(word.lower() in content_lower for word in tensions.split()):
                score += 0.2
            
            return min(score, 1.0)
        except:
            return 0.5  # 默认中等一致性
    
    async def _llm_quality_assessment(
        self,
        results: List[Dict[str, Any]],
        query_context: str,
        phase: str
    ) -> List[Dict[str, Any]]:
        """LLM 深度质量评估"""
        try:
            # 构建评估 prompt
            results_summary = []
            for i, result in enumerate(results[:5]):  # 限制评估数量
                results_summary.append({
                    "index": i,
                    "title": result.get("title", "")[:100],
                    "content": result.get("content", "")[:300],
                    "url": result.get("url", "")
                })
            
            prompt = f"""作为信息质量评估专家，请评估以下搜索结果的质量。

查询上下文：{query_context}
搜索阶段：{phase}

搜索结果：
{json.dumps(results_summary, ensure_ascii=False, indent=2)}

请对每个结果评估以下维度（0-1分）：
1. 专业性：内容的专业程度和权威性
2. 可信度：信息来源的可靠性
3. 实用性：对回答查询的帮助程度
4. 完整性：信息的全面性

输出 JSON 格式：
```json
[
    {{
        "index": 0,
        "professional_score": 0.8,
        "credibility_score": 0.9,
        "utility_score": 0.7,
        "completeness_score": 0.8,
        "llm_quality_score": 0.8,
        "quality_explanation": "评估理由"
    }}
]
```"""
            
            # 调用 DeepSeek 评估模型
            response = await self.deepseek_analysis_engine._deepseek_call(
                prompt, 
                self.deepseek_analysis_engine.eval_model,
                max_tokens=2000
            )
            
            if response:
                # 解析评估结果
                assessments = self._safe_parse_json(response, "LLM质量评估")
                if assessments and isinstance(assessments, list):
                    # 计算总体质量评分
                    for assessment in assessments:
                        if isinstance(assessment, dict):
                            professional = assessment.get("professional_score", 0.5)
                            credibility = assessment.get("credibility_score", 0.5)
                            utility = assessment.get("utility_score", 0.5)
                            completeness = assessment.get("completeness_score", 0.5)
                            
                            total_quality = (professional * 0.3 + credibility * 0.3 + 
                                           utility * 0.3 + completeness * 0.1)
                            assessment["total_quality_score"] = total_quality
                    
                    return assessments
            
            # 降级处理：返回默认评分
            return [
                {
                    "index": i,
                    "llm_quality_score": 0.6,
                    "total_quality_score": 0.6,
                    "quality_explanation": "LLM评估失败，使用默认评分"
                }
                for i in range(len(results))
            ]
            
        except Exception as e:
            logger.error(f"❌ [LLM质量评估] 执行失败: {e}")
            # 返回默认评分
            return [
                {
                    "index": i,
                    "llm_quality_score": 0.5,
                    "total_quality_score": 0.5,
                    "quality_explanation": f"评估异常: {str(e)}"
                }
                for i in range(len(results))
            ]
    
    def _safe_parse_json(self, text: str, context: str = "", expect_dict: bool = True) -> Optional[Dict[str, Any]]:
        """
        安全的 JSON 解析，支持多种格式 (v7.214 增强)
        
        解析策略（按优先级）：
        1. 直接解析：尝试将整个文本作为 JSON 解析
        2. ```json``` 块：提取 Markdown JSON 代码块
        3. ``` 块：提取通用代码块
        4. 正则提取：提取最外层的 {} 或 []
        5. 清理后重试：移除注释、Unicode 转义等
        
        v7.214 增强：
        - 新增 expect_dict 参数，当期望字典时不返回数组
        - 如果返回数组但期望字典，尝试提取数组中的第一个字典元素
        
        Args:
            text: 待解析的文本
            context: 上下文描述（用于日志）
            expect_dict: 是否期望返回字典类型（默认 True）
            
        Returns:
            解析后的字典，失败返回 None
        """
        if not text or not text.strip():
            logger.warning(f"⚠️ [JSON解析] 空文本 | context={context}")
            return None
        
        text = text.strip()
        
        def _ensure_dict(result: Any) -> Optional[Dict[str, Any]]:
            """确保返回字典类型 (v7.214)"""
            if result is None:
                return None
            if isinstance(result, dict):
                return result
            if expect_dict and isinstance(result, list):
                # 如果期望字典但得到数组，尝试提取第一个字典元素
                logger.warning(f"⚠️ [JSON解析] 期望字典但得到数组 | context={context} | len={len(result)}")
                for item in result:
                    if isinstance(item, dict):
                        logger.info(f"✅ [JSON解析] 从数组中提取第一个字典元素")
                        return item
                return None
            return None
        
        # 策略1: 直接解析
        try:
            result = json.loads(text)
            final = _ensure_dict(result)
            if final is not None:
                return final
        except json.JSONDecodeError:
            pass
        
        # 策略2: 提取 ```json``` 块
        if "```json" in text:
            try:
                json_block = text.split("```json")[1].split("```")[0].strip()
                result = json.loads(json_block)
                final = _ensure_dict(result)
                if final is not None:
                    return final
            except (IndexError, json.JSONDecodeError):
                pass
        
        # 策略3: 提取 ``` 块
        if "```" in text:
            try:
                json_block = text.split("```")[1].split("```")[0].strip()
                # 检查是否以 json 开头（去掉语言标记）
                if json_block.startswith("json"):
                    json_block = json_block[4:].strip()
                result = json.loads(json_block)
                final = _ensure_dict(result)
                if final is not None:
                    return final
            except (IndexError, json.JSONDecodeError):
                pass
        
        # 策略4: 正则提取最外层 {} 或 []
        try:
            # 优先匹配最外层的 JSON 对象（字典）
            obj_match = re.search(r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}', text, re.DOTALL)
            if obj_match:
                result = json.loads(obj_match.group())
                if isinstance(result, dict):
                    return result
            
            # 如果没有字典或不期望字典，尝试匹配数组
            if not expect_dict:
                arr_match = re.search(r'\[(?:[^\[\]]|(?:\[[^\[\]]*\]))*\]', text, re.DOTALL)
                if arr_match:
                    return json.loads(arr_match.group())
        except json.JSONDecodeError:
            pass
        
        # 策略5: 清理后重试
        try:
            # 移除可能的 BOM 和控制字符
            cleaned = text.encode('utf-8', errors='ignore').decode('utf-8')
            # 移除单行注释
            cleaned = re.sub(r'//.*?$', '', cleaned, flags=re.MULTILINE)
            # 移除多行注释
            cleaned = re.sub(r'/\*.*?\*/', '', cleaned, flags=re.DOTALL)
            # 提取 JSON
            obj_match = re.search(r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}', cleaned, re.DOTALL)
            if obj_match:
                result = json.loads(obj_match.group())
                if isinstance(result, dict):
                    return result
        except (json.JSONDecodeError, Exception):
            pass
        
        # 🔧 [Bug修复] 所有策略失败时，针对不同上下文使用合适的日志级别
        # 查询扩展等有降级机制的场景使用debug级别，避免误报警告
        if context in ["查询扩展", "统一思考流", "语义变体生成", "查询增强"]:
            logger.debug(f"ℹ️ [JSON解析] 解析失败但有降级策略 | context={context} | text[:200]={text[:200]}...")
        else:
            logger.warning(f"⚠️ [JSON解析] 所有策略失败 | context={context} | text[:200]={text[:200]}...")
        
        # v7.233: 针对特定上下文提供降级默认值，避免下游代码崩溃
        if context == "查询扩展":
            # 查询扩展失败时，返回空扩展列表（让下游使用原始查询）
            logger.info(f"ℹ️ [JSON解析] 查询扩展降级：返回空 expansions")
            return {"expansions": []}
        elif context == "统一思考流":
            # 统一思考流失败时，返回最小必要结构
            logger.info(f"ℹ️ [JSON解析] 统一思考流降级：返回最小结构")
            return {
                "current_round_planning": {
                    "thinking": "解析失败，使用默认策略",
                    "strategy": "继续搜索相关信息",
                    "search_query": ""
                },
                "global_alignment": {
                    "alignment_score": 0.5,
                    "remaining_gaps": []
                }
            }
        
        return None

    # ==================== v7.199: 查询去重 ====================

    def _calculate_query_similarity(self, query1: str, query2: str) -> float:
        """
        计算两个查询的相似度（简单的字符级Jaccard相似度）

        Args:
            query1: 查询1
            query2: 查询2

        Returns:
            相似度 0-1
        """
        # 分词（简单按空格和标点分割）
        import re
        def tokenize(text: str) -> set:
            # 移除标点，按空格分词
            text = re.sub(r'[^\w\s]', ' ', text)
            return set(text.lower().split())

        tokens1 = tokenize(query1)
        tokens2 = tokenize(query2)

        if not tokens1 or not tokens2:
            return 0.0

        intersection = tokens1 & tokens2
        union = tokens1 | tokens2

        return len(intersection) / len(union) if union else 0.0

    def _is_duplicate_query(self, query: str) -> Tuple[bool, Optional[str]]:
        """
        检查查询是否与已使用的查询重复

        Args:
            query: 待检查的查询

        Returns:
            (is_duplicate, similar_query) - 是否重复及相似的查询
        """
        for used_query in self._used_queries:
            similarity = self._calculate_query_similarity(query, used_query)
            if similarity >= self._query_similarity_threshold:
                return True, used_query
        return False, None

    def _diversify_query(self, query: str, target_aspect: str, round_number: int) -> str:
        """
        多样化查询 - 当检测到重复时生成不同的查询

        Args:
            query: 原始查询
            target_aspect: 目标信息面
            round_number: 当前轮次

        Returns:
            多样化后的查询
        """
        # 策略1: 添加不同的修饰词
        modifiers = [
            "最新", "详细", "专业", "深度", "案例",
            "分析", "研究", "报告", "趋势", "实践"
        ]
        modifier = modifiers[round_number % len(modifiers)]

        # 策略2: 重组查询结构
        # 提取核心关键词（前20字）
        core = query[:20].strip() if len(query) > 20 else query

        diversified = f"{modifier} {target_aspect} {core}"
        logger.info(f"🔄 [Ucppt v7.199] 查询多样化: {query[:30]}... → {diversified[:30]}...")

        return diversified

    def _record_query(self, query: str) -> None:
        """记录已使用的查询"""
        self._used_queries.append(query)
        # 保留最近20个查询
        if len(self._used_queries) > 20:
            self._used_queries = self._used_queries[-20:]

    def _validate_search_query(self, query: str, context: str = "") -> bool:
        """
        验证搜索查询是否有效 - v7.235

        Args:
            query: 待验证的查询
            context: 上下文信息（用于日志）

        Returns:
            True if valid, False otherwise
        """
        if not query:
            logger.warning(f"⚠️ [Query Validation] 空查询被拒绝 | context={context}")
            return False

        query_stripped = query.strip()

        if not query_stripped:
            logger.warning(f"⚠️ [Query Validation] 纯空格查询被拒绝 | context={context}")
            return False

        if len(query_stripped) < 2:
            logger.warning(f"⚠️ [Query Validation] 查询过短: '{query_stripped}' | context={context}")
            return False

        # 检查是否只包含标点符号
        import re
        if re.match(r'^[\s\W]+$', query_stripped):
            logger.warning(f"⚠️ [Query Validation] 查询仅包含标点: '{query_stripped}' | context={context}")
            return False

        return True

    def _get_search_query_with_preset(self, target: SearchTarget, llm_query: str) -> str:
        """
        获取搜索查询，优先使用预设关键词 - v7.232

        策略：
        1. 如果有未使用的预设关键词，优先使用
        2. 如果 LLM 生成的查询与预设关键词相似度高，使用预设关键词
        3. 如果 LLM 生成的查询足够具体（包含具体名词），可以使用
        4. 否则回退到预设关键词

        Args:
            target: 搜索目标
            llm_query: LLM 生成的查询

        Returns:
            最终使用的搜索查询
        """
        # 获取下一个预设关键词
        preset_keyword = target.get_next_preset_keyword()

        if not preset_keyword:
            # v7.235: 没有预设关键词，验证 LLM 生成的查询
            if not llm_query or len(llm_query.strip()) < 5:
                # LLM 查询也无效，使用目标名称或默认查询
                if target and hasattr(target, 'name'):
                    fallback = target.question or target.name or target.search_for or f"目标{target.id}"
                else:
                    fallback = "设计研究案例"
                logger.warning(f"⚠️ [v7.235] 无预设关键词且LLM失败，使用降级查询: {fallback}")
                return fallback
            logger.info(f"📝 [v7.232] 无预设关键词，使用 LLM 生成: {llm_query[:40]}...")
            return llm_query

        if not llm_query or len(llm_query.strip()) < 5:
            # LLM 没有生成有效查询，使用预设
            logger.info(f"📌 [v7.232] LLM 查询无效，使用预设关键词: {preset_keyword[:40]}...")
            return preset_keyword

        # 检查 LLM 查询的质量
        # 质量标准：长度 >= 15，包含具体名词（非泛化词）
        vague_words = ["设计理念", "美学特点", "风格特点", "设计风格", "核心理念", "设计思想", "基本概念"]
        is_vague = any(vw in llm_query for vw in vague_words) and len(llm_query) < 25

        if is_vague:
            logger.info(f"📌 [v7.232] LLM 查询过于宏观，使用预设关键词: {preset_keyword[:40]}...")
            return preset_keyword

        # LLM 查询看起来足够具体，但仍然优先使用预设关键词（除非 LLM 查询明显更好）
        # 判断标准：LLM 查询长度 > 预设关键词长度 * 1.2，且包含预设关键词的核心词
        preset_core_words = set(preset_keyword.split()[:3])  # 取前3个词作为核心词
        llm_has_core = any(word in llm_query for word in preset_core_words if len(word) > 2)

        if len(llm_query) > len(preset_keyword) * 1.2 and llm_has_core:
            logger.info(f"📝 [v7.232] LLM 查询更具体，使用: {llm_query[:40]}...")
            return llm_query

        # 默认使用预设关键词
        logger.info(f"📌 [v7.232] 使用预设关键词: {preset_keyword[:40]}...")
        return preset_keyword
    
    # ==================== 主入口 ====================
    
    async def search_deep(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        max_rounds: Optional[int] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        深度迭代搜索（流式输出）- 目标导向版本
        
        核心流程：
        1. 分析问题 → 确定回答目标和关键信息面
        2. 目标导向搜索 → 每轮填补一个信息面
        3. 评估完成度 → 能完整回答时停止
        4. 生成答案 → 整合所有信息给出最佳回答
        """
        start_time = time.time()
        max_rounds = max_rounds or self.max_rounds

        # v7.199: 重置查询历史
        self._used_queries = []

        logger.info(f"🚀 [Ucppt v7.199] 开始目标导向搜索 | query={query[:50]}...")
        
        # v7.199: 查询分类
        if QUERY_CLASSIFIER_AVAILABLE and classify_query:
            self._query_classification = classify_query(query)
            logger.info(f"🏷️ [Ucppt v7.199] 查询分类: {self._query_classification.query_type.value} | confidence={self._query_classification.confidence:.2f}")
        else:
            self._query_classification = None

        all_sources: List[Dict[str, Any]] = []
        rounds: List[SearchRoundState] = []
        seen_urls: set = set()  # 🔧 [Bug修复] 初始化seen_urls集合，避免延展搜索时变量未定义错误

        try:
            # ==================== Phase 0: v7.214 结构化问题分析检查 ====================
            # 检查是否启用v7.214引擎
            enable_v7214 = os.getenv("ENABLE_STRUCTURED_ANALYSIS_V7214", "true").lower() == "true"
            logger.info(f"🔍 [v7.214 Debug] 配置检查 | ENABLE_STRUCTURED_ANALYSIS_V7214={os.getenv('ENABLE_STRUCTURED_ANALYSIS_V7214')} | enable_v7214={enable_v7214}")
            
            if not enable_v7214:
                logger.info("🔄 [Ucppt] v7.214结构化分析引擎已禁用，跳过到标准搜索流程")
                analysis_session = None
            else:
                logger.info("✅ [v7.214 Debug] v7.214结构化分析引擎已启用，开始执行")
                # ==================== Phase 0: v7.214 结构化问题分析 ====================
                yield {
                    "type": "phase",
                    "data": {
                        "phase": "structured_analysis",
                        "phase_name": "结构化问题分析 v7.214",
                        "message": "正在进行三阶段结构化分析：L0对话理解 → L1-L5深度建模 → 综合搜索规划",
                    }
                }
                
                # v7.218: 立即推送分析进度提示，避免用户看到页面"冻住"
                yield {
                    "type": "analysis_progress",
                    "data": {
                        "stage": "starting",
                        "stage_name": "深度分析启动",
                        "message": "正在启动 DeepSeek 深度推理引擎...",
                        "estimated_time": 180,
                        "current_step": 0,
                        "total_steps": 3,
                    }
                }
                
                logger.info("🚀 [v7.219] 开始调用流式统一分析方法")
                
                # 🔧 v7.219: 使用流式分析替代阻塞式分析，实现实时输出
                # 用户可以看到 DeepSeek 的思考过程，而不是空白等待
                try:
                    analysis_session = None
                    framework = None
                    search_master_line = None
                    structured_info = None
                    
                    async with asyncio.timeout(180):
                        async for event in self._unified_analysis_stream(query, context):
                            event_type = event.get("type")
                            
                            # 流式输出 thinking 内容给前端
                            if event_type == "unified_dialogue_chunk":
                                yield event
                            
                            # 对话完成
                            elif event_type == "unified_dialogue_complete":
                                yield event
                            
                            # 结构化信息就绪
                            elif event_type == "structured_info_ready":
                                structured_info = event.get("_internal_data")
                                yield {
                                    "type": "structured_info_ready",
                                    "data": event.get("data"),
                                }

                            # 搜索主线就绪
                            elif event_type == "search_master_line_ready":
                                search_master_line = event.get("_internal_master_line")
                                yield {
                                    "type": "search_master_line",
                                    "data": event.get("data"),
                                }

                            # v7.243: 搜索框架就绪（修复清单不显示问题）
                            # 这个事件包含 targets 数据，前端用于显示 SearchTaskListCard
                            elif event_type == "search_framework_ready":
                                yield event

                            # 分析完成
                            elif event_type == "analysis_complete":
                                framework = event.get("framework")
                                if not search_master_line:
                                    search_master_line = event.get("_search_master_line")
                                
                                # 创建一个模拟的 analysis_session 以兼容后续代码
                                analysis_session = True  # 标记为成功
                                
                                # v7.219: 发送进度完成事件
                                yield {
                                    "type": "analysis_progress",
                                    "data": {
                                        "stage": "complete",
                                        "stage_name": "深度分析完成",
                                        "message": "结构化分析完成，准备开始搜索...",
                                        "estimated_time": 0,
                                        "current_step": 3,
                                        "total_steps": 3,
                                    }
                                }
                    
                    logger.info(f"📊 [v7.219] 流式分析完成 | framework={framework is not None} | search_master_line={search_master_line is not None}")
                except asyncio.TimeoutError:
                    logger.error("⏰ [v7.214 Debug] v7.214引擎整体超时(180s)，立即回退到传统搜索")
                    analysis_session = None
                    yield {
                        "type": "warning",
                        "data": {
                            "message": "深度分析超时，正在切换到快速搜索模式...",
                            "error_type": "v7214_timeout"
                        }
                    }
                except Exception as e:
                    logger.error(f"❌ [v7.214 Debug] structured_problem_analysis执行异常: {e}")
                    import traceback
                    logger.error(f"📋 [v7.214 Debug] 异常堆栈: {traceback.format_exc()}")
                    analysis_session = None
                    yield {
                        "type": "warning",
                        "data": {
                            "message": "分析引擎异常，已切换到快速搜索模式",
                            "error_type": "v7214_exception"
                        }
                    }

                if not analysis_session:
                    logger.warning("⚠️ [v7.214] 结构化分析失败，回退到快速搜索模式")
                    yield {
                        "type": "phase",
                        "data": {
                            "phase": "fallback",
                            "phase_name": "快速搜索模式",
                            "message": "正在使用快速搜索模式..."
                        }
                    }

                    # 🔧 v7.220: 直接使用简单搜索框架，跳过统一分析（避免再次调用 LLM）
                    logger.info("⚡ [v7.220] 使用简单搜索框架，跳过 LLM 分析")
                    structured_info = None
                    framework = self._build_simple_search_framework(query)
                    search_master_line = None
                # v7.219: 新流程中 analysis_session 是布尔标记，结果已在流式处理中提取
                # 不再需要额外的处理

            # v7.220: 确保 framework 不为空（流式分析中已设置）
            if framework is None:
                framework = self._build_simple_search_framework(query)
            
            # v7.220: 使用新的 SearchFramework 结构
            # 推送分析结果（包含搜索目标清单）
            # v7.232: 添加预设关键词信息
            question_analyzed_data = {
                "answer_goal": framework.answer_goal,
                "core_question": framework.core_question,
                "boundary": framework.boundary,
                # v7.232: 使用 targets 替代 key_aspects，包含预设关键词
                "search_targets": [
                    {
                        "id": t.id,
                        "name": t.name,
                        "goal": t.purpose,
                        "priority": t.priority,
                        "status": "complete" if t.is_complete() else "pending",
                        "completion_score": t.completion_score,
                        "preset_keywords": t.preset_keywords,  # v7.232: 预设搜索关键词
                        "quality_criteria": t.quality_criteria,  # v7.232: 质量达标标准
                    }
                    for t in framework.targets
                ],
                "total_targets": len(framework.targets),
                "message": f"识别到 {len(framework.targets)} 个搜索目标需要完成",
            }
            
            # v7.208: 添加搜索任务清单
            if search_master_line:
                question_analyzed_data["search_master_line"] = {
                    "core_question": search_master_line.core_question,
                    "boundary": search_master_line.boundary,
                    "task_count": len(search_master_line.search_tasks),
                    "tasks": [
                        {
                            "id": t.id,
                            "task": t.task,
                            "purpose": t.purpose,
                            "priority": t.priority,
                            "status": t.status,
                            "expected_info": t.expected_info,
                        }
                        for t in search_master_line.search_tasks
                    ],
                    "exploration_triggers": search_master_line.exploration_triggers,
                    "forbidden_zones": search_master_line.forbidden_zones,
                }
                question_analyzed_data["message"] = f"识别到 {len(search_master_line.search_tasks)} 个搜索任务（P1={sum(1 for t in search_master_line.search_tasks if t.priority==1)}个）"
            
            yield {
                "type": "question_analyzed",
                "data": question_analyzed_data,
            }
            
            # ==================== Phase 2: 专家叙事搜索 v7.220 ====================
            phase_2_data = {
                "phase": "expert_narrative_search",
                "phase_name": "专家叙事搜索",
                "message": "像资深专家一样，思考、搜索、反思...",
                "total_targets": len(framework.targets),
            }
            # v7.220: 使用 targets 数量
            if framework.targets:
                phase_2_data["message"] = f"执行 {len(framework.targets)} 个搜索目标，深度探索..."
            
            yield {
                "type": "phase",
                "data": phase_2_data,
            }
            
            current_round = 0
            
            # v7.204: 记录上一轮的搜索结果，用于统一思考
            last_round_sources: List[Dict[str, Any]] = []
            last_search_query = ""
            
            while current_round < max_rounds:
                current_round += 1
                round_start = time.time()
                
                # v7.202: 强制最低4轮约束，最高优先级
                force_continue = current_round < MIN_SEARCH_ROUNDS
                if force_continue:
                    logger.info(f"🟡 [Ucppt v7.202] 轮数{current_round}/{MIN_SEARCH_ROUNDS}，强制继续模式")

                # v7.245: 使用轮次轮换策略选择目标，确保每轮搜索不同的主线
                # 替代原来的 get_next_target()，避免前4轮一直搜索同一个目标
                target: Optional[SearchTarget] = framework.get_target_for_round(current_round)
                if target:
                    target_desc = target.question or target.name or target.search_for or f"目标{target.id}"
                    logger.info(f"🎯 [v7.245] 第{current_round}轮选择目标: {target_desc[:40]}...")

                # v7.208: 兼容旧的搜索任务清单（如果存在）
                current_task: Optional[SearchTask] = None
                if search_master_line and target is None:
                    current_task = search_master_line.get_next_task()
                    if current_task:
                        logger.info(f"📋 [v7.208] 执行任务 {current_task.id}: {current_task.task[:30]}... (P{current_task.priority})")
                        # 创建临时 SearchTarget 用于搜索流程
                        target = SearchTarget(
                            id=f"task_{current_task.id}",
                            name=current_task.task[:50],
                            description=current_task.task,
                            purpose=current_task.purpose,
                            priority=current_task.priority,
                        )
                        framework.targets.append(target)
                        logger.info(f"🔧 [v7.208] 创建临时搜索目标: {target.question or target.name or target.search_for or f'目标{target.id}'}")

                if target is None:
                    # v7.201: 检查最小轮数约束
                    if current_round < MIN_SEARCH_ROUNDS:
                        # 未达到最小轮数，强制重置一个目标继续搜索
                        logger.warning(f"⚠️ [Ucppt v7.201] 轮数{current_round}<{MIN_SEARCH_ROUNDS}但所有目标已complete，强制继续搜索")

                        # v7.220: 如果 targets 为空，使用默认框架
                        if not framework.targets:
                            logger.warning(f"⚠️ [Ucppt v7.220] targets 为空，使用默认框架")
                            default_framework = self._build_simple_search_framework(framework.original_query)
                            framework.targets = default_framework.targets
                            current_round -= 1  # 🔧 v7.229: 回退轮次计数，避免跳过轮次
                            continue

                        for t in framework.targets:
                            if t.is_complete():
                                t.status = "partial"
                                t.completion_score = max(0.3, t.completion_score - 0.3)
                                # v7.243: 使用更多备选字段
                                target_desc = t.question or t.name or t.search_for or f"目标{t.id}"
                                logger.info(f"🔄 重置目标 '{target_desc}' 为partial，继续搜索")
                                break
                        current_round -= 1  # 🔧 v7.229: 回退轮次计数，避免跳过轮次
                        continue  # 继续下一轮循环

                    # 已达到最小轮数，所有目标都已完成
                    logger.info(f"✅ [Ucppt] 轮数{current_round}≥{MIN_SEARCH_ROUNDS}，所有搜索目标已完成")
                    yield {
                        "type": "search_complete",
                        "data": {
                            "reason": "所有搜索目标已完成",
                            "totalRounds": current_round - 1,
                            "completeness": framework.overall_completeness,
                        }
                    }
                    break
                
                # ==================== Step 1: 统一思考 v7.204 ====================
                # 融合了原来的"思考"和"反思"，一次 LLM 调用完成：
                # - 回顾上轮搜索结果（round > 1 时）
                # - 规划本轮搜索
                # - 全局校准
                thinking_narrative = ""
                search_strategy = ""
                search_query = ""
                reasoning_content = ""
                unified_result: Optional[UnifiedThinkingResult] = None
                
                # 使用统一思考流，实时推送推理过程
                # v7.220: 传入 SearchTarget 而非 KeyAspect
                async for thinking_event in self._generate_unified_thinking_stream(
                    framework, target, current_round, all_sources,
                    last_round_sources, last_search_query
                ):
                    if thinking_event.get("type") == "thinking_chunk":
                        # 流式推送思考片段
                        # v7.218: 添加 phase 字段区分 Phase 0（解题思考）和 Phase 2（轮次思考）
                        yield {
                            "type": "thinking_chunk",
                            "data": {
                                "round": current_round,
                                "content": thinking_event.get("content", ""),
                                "is_reasoning": thinking_event.get("is_reasoning", False),
                                "phase": "search_round",  # v7.218: 标记为搜索轮次思考
                            }
                        }
                        if thinking_event.get("is_reasoning"):
                            reasoning_content += thinking_event.get("content", "")
                    elif thinking_event.get("type") == "unified_thinking_complete":
                        # v7.204: 统一思考完成，提取结果
                        unified_result = thinking_event.get("result")
                        if unified_result:
                            thinking_narrative = unified_result.thinking_narrative
                            search_strategy = unified_result.search_strategy
                            search_query = unified_result.search_query
                            reasoning_content = unified_result.reasoning_content
                        
                        # v7.204: 如果是 round > 1，立即处理上轮回顾结果
                        if current_round > 1 and unified_result and last_round_sources:
                            # 推送上轮回顾内容（融合的反思）
                            yield {
                                "type": "narrative_reflection",
                                "data": {
                                    "round": current_round - 1,  # 这是对上轮的反思
                                    "target": target.question or target.name or target.search_for or f"目标{target.id}",  # v7.243: 使用备选字段
                                    "reflection": unified_result.reflection_narrative,
                                    "key_findings": unified_result.key_findings,
                                    "inferred_insights": unified_result.inferred_insights,
                                    "goal_achieved": unified_result.goal_achieved,
                                    "info_sufficiency": unified_result.info_sufficiency,
                                    "info_quality": unified_result.info_quality,
                                    "quality_issues": unified_result.quality_issues,
                                    # 全局校准（在思考阶段输出）
                                    "alignment_score": unified_result.alignment_score,
                                    "alignment_note": unified_result.alignment_note,
                                    "remaining_gaps": unified_result.remaining_gaps,
                                    "estimated_rounds_remaining": unified_result.estimated_rounds_remaining,
                                    "cumulative_progress": unified_result.cumulative_progress,
                                    "message": f"第{current_round}轮：回顾上轮结果...",
                                    "is_unified": True,  # 标记这是统一思考中的回顾
                                }
                            }

                # v7.199: 查询去重检查
                is_duplicate, similar_query = self._is_duplicate_query(search_query)
                if is_duplicate:
                    logger.info(f"🔄 [Ucppt v7.199] 检测到重复查询: {search_query[:30]}... ≈ {similar_query[:30] if similar_query else ''}...")
                    # v7.232: 如果有预设关键词，尝试使用下一个
                    if target.preset_keywords and target.current_keyword_index + 1 < len(target.preset_keywords):
                        target.current_keyword_index += 1
                        search_query = target.preset_keywords[target.current_keyword_index]
                        logger.info(f"📌 [v7.232] 使用下一个预设关键词: {search_query[:40]}...")
                    else:
                        # v7.243: 使用更多备选字段
                        target_desc = target.question or target.name or target.search_for or f"目标{target.id}"
                        search_query = self._diversify_query(search_query, target_desc, current_round)

                # 记录查询
                self._record_query(search_query)

                # v7.220: 更新 SearchTarget 状态
                target.search_query = search_query
                target.last_searched_round = current_round
                # v7.232: 更新已使用的关键词索引
                if target.preset_keywords and search_query in target.preset_keywords:
                    target.current_keyword_index = target.preset_keywords.index(search_query) + 1
                target.search_queries.append(search_query)  # 记录已执行的搜索词

                # v7.243: 获取目标描述，优先使用有值的字段
                target_desc = target.question or target.name or target.search_for or f"目标{target.id}"

                round_state = SearchRoundState(
                    round_number=current_round,
                    phase=SearchPhase.GOAL_DIRECTED_SEARCH,
                    target_aspect=target_desc,  # v7.243: 使用备选字段
                    search_query=search_query,
                    status="thinking",
                    thinking_narrative=thinking_narrative,
                    search_strategy=search_strategy,
                )

                # 推送思考叙事（新事件类型）
                yield {
                    "type": "narrative_thinking",
                    "data": {
                        "round": current_round,
                        "target": target_desc,  # v7.243: 使用备选字段
                        "thinking": thinking_narrative,
                        "strategy": search_strategy,
                        "message": f"第{current_round}轮：思考中...",
                    }
                }

                # ==================== Step 2: 搜索 ====================
                round_state.status = "searching"

                # 推送搜索状态
                yield {
                    "type": "round_start",
                    "data": {
                        "round": current_round,
                        "target": target_desc,  # v7.243: 使用备选字段
                        "target_goal": target.why_need or target.purpose or "",  # v7.243: 使用备选字段
                        "query": search_query,
                        "thinking": thinking_narrative,
                        "strategy": search_strategy,
                        "current_completeness": framework.overall_completeness,
                        "message": f"正在搜索: {search_query}",
                    }
                }
                
                # v7.212: 执行带质量筛选的搜索（自动补齐不足的高质量来源）
                # v7.229: 修复使用 target 替代 target_aspect
                round_sources = await self._execute_search_with_quality_filter(
                    search_query, target
                )
                # v7.230: 为每个来源标记轮次，用于来源选择时的轮次权重
                for source in round_sources:
                    source['_round'] = current_round
                all_sources.extend(round_sources)
                round_state.sources_found = len(round_sources)
                
                # v7.227: 诊断日志 - 追踪搜索结果
                logger.info(f"📦 [round_sources v7.227] 准备发送 | round={current_round} | sources_count={len(round_sources)}")
                if round_sources:
                    for i, src in enumerate(round_sources[:3]):
                        logger.debug(f"  └─ [{i+1}] {src.get('title', '无标题')[:40]}")
                else:
                    logger.warning(f"⚠️ [round_sources v7.227] 搜索结果为空！query={search_query[:50]}")

                # v7.190: 推送搜索结果（v7.212: 只推送通过质量筛选的来源）
                yield {
                    "type": "round_sources",
                    "data": {
                        "round": current_round,
                        "query": search_query,  # v7.187: 添加搜索查询
                        "target": target_desc,  # v7.243: 使用备选字段
                        "sources_count": len(round_sources),
                        "sources": round_sources,  # v7.212: 只包含高质量来源
                    }
                }

                # ==================== v7.204: 统一思考已完成反思 ====================
                # 反思已在 Step 1 的统一思考中完成（下一轮开始时回顾本轮）
                # 这里只需要更新状态和保存本轮数据
                old_completeness = framework.overall_completeness

                # v7.204: 从统一思考结果或创建默认结果
                if unified_result:
                    reflection_result = unified_result.to_reflection_result()
                else:
                    # 首轮或降级情况，创建简单反思结果
                    reflection_result = ReflectionResult(
                        goal_achieved=len(round_sources) > 0,
                        info_sufficiency=0.3 if round_sources else 0.0,
                        info_quality=0.5 if round_sources else 0.0,
                        key_findings=[f"搜索到{len(round_sources)}条结果"],
                        reflection_narrative=f"本轮搜索到{len(round_sources)}条结果",
                        cumulative_progress=f"已完成{current_round}轮搜索",
                        needs_deeper_search=True,
                        estimated_rounds_remaining=max(MIN_SEARCH_ROUNDS - current_round, 2),
                    )

                # 合并收获（直接发现 + 推断洞察）
                all_findings = reflection_result.key_findings + reflection_result.inferred_insights

                # v7.220: 更新 SearchTarget
                # v7.229: 修复 - SearchTarget 使用 sources 而非 source_urls
                target.collected_info.extend(all_findings)
                target.sources.extend(round_sources[:3])
                
                # v7.208: 更新搜索任务状态
                if current_task and search_master_line:
                    task_findings = all_findings[:5] if all_findings else [f"搜索到{len(round_sources)}条结果"]
                    completion_score = min(1.0, len(round_sources) * 0.1) if round_sources else 0.0
                    search_master_line.update_task_status(
                        current_task.id, 
                        "complete" if completion_score >= 0.5 else "searching",
                        task_findings,
                        completion_score
                    )
                    logger.info(f"📋 [v7.208] 任务 {current_task.id} 更新: status={current_task.status}, score={current_task.completion_score:.2f}")
                    
                    # 推送任务进度
                    yield {
                        "type": "task_progress",
                        "data": {
                            "round": current_round,
                            "task_id": current_task.id,
                            "task": current_task.task,
                            "status": current_task.status,
                            "completion_score": current_task.completion_score,
                            "findings": task_findings[:3],
                            "overall_progress": search_master_line.get_progress_summary(),
                        }
                    }

                # 基于搜索结果更新完成度（简化版，因为完整评估会在下一轮思考中进行）
                # 这里用搜索结果数量作为粗略估计
                if round_sources:
                    completion_delta = min(0.2, len(round_sources) * 0.03)  # 每条结果贡献 3%，最多 20%
                else:
                    completion_delta = 0.0
                target.completion_score = min(1.0, target.completion_score + completion_delta)  # v7.220

                # v7.202: 判断状态，前4轮不能直接标记complete
                if force_continue:
                    # 强制继续模式：最多标记为partial
                    if len(round_sources) > 0:
                        target.status = "partial"  # v7.220
                    else:
                        target.status = "missing"  # v7.220
                    logger.info(f"🟡 [v7.204] 强制模式: {target.question or target.name or target.search_for or f'目标{target.id}'} 状态={target.status}")  # v7.243
                elif len(round_sources) >= 5 and target.completion_score >= 0.7:  # v7.220
                    target.status = "complete"  # v7.220
                elif len(round_sources) > 0:
                    target.status = "partial"  # v7.220
                else:
                    target.status = "missing"  # v7.220

                # v7.220: 更新框架完成度
                framework.update_completeness()
                framework.cumulative_progress = reflection_result.cumulative_progress
                framework.last_reflection = reflection_result  # 保存反思结果供下一轮使用
                
                # v7.230: 创建并累积轮次洞察（不再覆盖，完整保留每轮结构化信息）
                round_insight = RoundInsights(
                    round_number=current_round,
                    target_aspect=target.question or target.name or target.search_for or f"目标{target.id}",  # v7.243: 使用备选字段
                    search_query=search_query,
                    key_findings=reflection_result.key_findings.copy(),
                    inferred_insights=reflection_result.inferred_insights.copy(),
                    info_sufficiency=reflection_result.info_sufficiency,
                    info_quality=reflection_result.info_quality,
                    quality_issues=reflection_result.quality_issues.copy(),
                    alignment_score=reflection_result.alignment_with_goal,
                    alignment_note=reflection_result.alignment_note,
                    remaining_gaps=reflection_result.remaining_gaps.copy(),
                    best_source_urls=[s.get("url", "") for s in round_sources[:3]],
                    sources_count=len(round_sources),
                    progress_description=reflection_result.cumulative_progress,  # 完整保留，不截断
                )
                framework.round_insights.append(round_insight)
                logger.info(f"📊 [v7.230] 累积第{current_round}轮洞察: key_findings={len(round_insight.key_findings)}, insights={len(round_insight.inferred_insights)}, quality={round_insight.info_quality:.2f}")

                round_state.completeness_delta = framework.overall_completeness - old_completeness
                round_state.reflection = reflection_result.reflection_narrative
                round_state.execution_time = time.time() - round_start
                round_state.status = "completed"
                rounds.append(round_state)

                # v7.204: 保存本轮数据供下一轮统一思考使用
                last_round_sources = round_sources
                last_search_query = search_query

                # v7.204: 反思内容已在 Step 1 统一思考中推送（如果 round > 1）
                # 首轮没有上轮结果，不需要推送反思
                # 后续轮的反思在下一轮开始时推送

                # 推送本轮完成状态
                yield {
                    "type": "round_complete",
                    "data": {
                        "round": current_round,
                        "target": target.question or target.name or target.search_for or f"目标{target.id}",  # v7.243: 使用备选字段
                        "target_status": target.status,  # v7.220: 使用 target
                        "target_completion": target.completion_score,  # v7.220: 使用 target
                        "overall_completeness": framework.overall_completeness,
                        "completeness_delta": round_state.completeness_delta,
                        "execution_time": round_state.execution_time,
                        # v7.186: 包含思考和反思内容
                        "thinking": thinking_narrative,
                        "reflection": reflection_result.reflection_narrative,
                        # v7.186: 反思驱动下一轮
                        "next_round_planning": {
                            "needs_deeper_search": reflection_result.needs_deeper_search,
                            "deeper_search_points": reflection_result.deeper_search_points,
                            "suggested_next_query": reflection_result.suggested_next_query,
                            "next_round_purpose": reflection_result.next_round_purpose,
                        },
                        # v7.186: 全局校准
                        "global_alignment": {
                            "alignment_score": reflection_result.alignment_with_goal,
                            "remaining_gaps": reflection_result.remaining_gaps,
                            "estimated_rounds_remaining": reflection_result.estimated_rounds_remaining,
                        },
                        # 各信息面状态 - v7.229: 使用 targets 替代 key_aspects
                        "aspects_status": [
                            {
                                "name": a.name,
                                "status": a.status,
                                "completion": a.completion_score,
                            }
                            for a in framework.targets
                        ],
                    }
                }
                
                # ==================== v7.213: 阶段复盘检查点 ====================
                if search_master_line and search_master_line.should_checkpoint(current_round):
                    checkpoint_event = await self._generate_phase_checkpoint(
                        search_master_line, framework, current_round, all_sources
                    )
                    if checkpoint_event:
                        yield checkpoint_event
                        
                        # 检查是否触发延展任务
                        extension_tasks = checkpoint_event.get("data", {}).get("extension_tasks", [])
                        for ext_task_data in extension_tasks:
                            ext_task = SearchTask(
                                id=ext_task_data.get("id", f"T{len(search_master_line.search_tasks)+1}"),
                                task=ext_task_data.get("task", ""),
                                purpose=ext_task_data.get("purpose", ""),
                                priority=ext_task_data.get("priority", 3),
                                phase=ext_task_data.get("phase", "对比验证"),
                                expected_info=ext_task_data.get("expected_info", []),
                            )
                            search_master_line.add_extension_task(
                                ext_task,
                                trigger=ext_task_data.get("trigger", f"checkpoint_round_{current_round}"),
                                reason=ext_task_data.get("reason", "阶段复盘发现需要补充")
                            )
                            
                            # v7.235: 同步创建 SearchTarget 到 framework.targets，确保延展任务被搜索引擎直接执行
                            ext_target = SearchTarget(
                                id=f"ext_{ext_task.id}",
                                name=ext_task.task[:50] if ext_task.task else "延展任务",
                                description=ext_task.task,
                                purpose=ext_task.purpose,
                                priority=ext_task.priority,
                                category="延展",
                                preset_keywords=ext_task_data.get("preset_keywords", []),
                                quality_criteria=ext_task_data.get("quality_criteria", []),
                            )
                            framework.targets.append(ext_target)
                            logger.info(f"🔄 [v7.235] 添加延展任务并同步到targets: {ext_task.id} - {ext_task.task[:30]}...")

                # ==================== v7.246: 动态延展评估 ====================
                # 每轮结束后评估是否需要动态延展（不依赖固定检查点）
                if not force_continue and framework.get_extension_count() < MAX_EXTENSION_ROUNDS:
                    needs_extension, extension_points = await self._evaluate_extension_need(
                        framework, all_sources, current_round
                    )
                    if needs_extension and extension_points:
                        new_ext_targets = await self._add_extension_targets(
                            framework, extension_points, current_round
                        )
                        if new_ext_targets:
                            yield {
                                "type": "extension_triggered",
                                "data": {
                                    "round": current_round,
                                    "extension_count": len(new_ext_targets),
                                    "extensions": [
                                        {"name": t.name, "purpose": t.purpose}
                                        for t in new_ext_targets
                                    ],
                                    "message": f"发现 {len(new_ext_targets)} 个新延展方向",
                                }
                            }

                # ==================== 完成度检查 v7.202 ====================
                # v7.202: 强制最低4轮，前4轮跳过所有退出检查
                if force_continue:
                    logger.info(f"🟡 [v7.202] 轮数{current_round}<{MIN_SEARCH_ROUNDS}，强制模式，确保完成搜索")
                    # 🔧 修复：不直接跳过，让每轮完整执行搜索流程
                    # continue  # 注释掉直接跳过逻辑
                
                # 以下检查仅在 current_round >= MIN_SEARCH_ROUNDS 时执行
                # 🔧 修复：在强制模式下跳过所有退出检查
                if not force_continue:
                    # 如果反思认为可以回答了（基于剩余缺口判断）
                    # v7.200: 优化标准 - alignment >= 0.90 且无剩余缺口（0.95→0.90）
                    if (not reflection_result.remaining_gaps and
                        reflection_result.alignment_with_goal >= 0.90 and
                        reflection_result.estimated_rounds_remaining == 0):
                        yield {
                            "type": "ready_to_answer",
                            "data": {
                                "message": f"综合判断信息足够：{reflection_result.alignment_note}",
                                "completeness": framework.overall_completeness,
                                "totalRounds": current_round,
                                "semantic_judgment": True,
                            }
                        }
                        break

                    # v7.198: 每5轮或达到较高阈值时进行额外语义判断（4→5轮）
                    should_check_semantically = (
                        current_round % 5 == 0 or framework.overall_completeness >= 0.85
                    )

                    if should_check_semantically:
                        can_answer, reason = await self._can_answer_semantically(framework, current_round)
                        if can_answer:
                            yield {
                                "type": "ready_to_answer",
                                "data": {
                                    "message": f"综合判断信息足够：{reason}",
                                    "completeness": framework.overall_completeness,
                                    "totalRounds": current_round,
                                    "semantic_judgment": True,
                                }
                            }
                            break

                        # 数值兜底检查
                        if framework.can_answer_completely() and framework.overall_completeness >= self.completeness_threshold:
                            logger.info(f"✅ [Ucppt v7.202] 数值兜底检查通过: 轮数{current_round}≥{MIN_SEARCH_ROUNDS}, 完成度{framework.overall_completeness:.2f}≥{self.completeness_threshold}")
                            yield {
                                "type": "ready_to_answer",
                                "data": {
                                    "message": "已收集足够信息，可以生成完整答案",
                                    "completeness": framework.overall_completeness,
                                    "totalRounds": current_round,
                                }
                            }
                            break

                # v7.200: 检查是否需要继续（优化饱和检测）
                # v7.203 修复：饱和检测也需要受 MIN_SEARCH_ROUNDS 约束
                if not force_continue and len(rounds) >= 2:
                    recent_deltas = [r.completeness_delta for r in rounds[-2:]]
                    # v7.200: 完成度达到 0.78 即可认为饱和（0.82→0.78）
                    if all(d < 0.03 for d in recent_deltas) and framework.overall_completeness >= 0.78:
                        yield {
                            "type": "search_complete",
                            "data": {
                                "reason": "信息收集趋于饱和",
                                "totalRounds": current_round,
                                "completeness": framework.overall_completeness,
                            }
                        }
                        break

            # 达到最大轮数
            if current_round >= max_rounds:
                yield {
                    "type": "search_complete",
                    "data": {
                        "reason": f"达到最大轮数限制（{max_rounds}轮）",
                        "totalRounds": current_round,
                        "completeness": framework.overall_completeness,
                    }
                }

            # ==================== v7.246: 串行执行延展任务 ====================
            # 主线搜索完成后，串行执行所有延展任务
            extension_targets = framework.get_extension_targets()
            if extension_targets:
                logger.info(f"📎 [v7.246] 主线搜索完成，开始串行执行 {len(extension_targets)} 个延展任务...")
                async for ext_event in self._execute_serial_extensions(
                    framework, all_sources, seen_urls
                ):
                    yield ext_event

            # ==================== v7.213: 搜索历程最终回顾 ====================
            if search_master_line:
                retrospective_event = await self._generate_search_retrospective(
                    search_master_line, framework, current_round, all_sources, rounds
                )
                if retrospective_event:
                    yield retrospective_event
            
            # ==================== Phase 3: 答案整合 ====================
            yield {
                "type": "phase",
                "data": {
                    "phase": "answer_synthesis",
                    "phase_name": "生成答案",
                    "message": "正在整合所有信息，生成完整答案...",
                }
            }
            
            # v7.194: 传递 rounds 参数，用于累积反思摘要
            async for chunk in self._generate_final_answer(query, framework, all_sources, rounds):
                yield chunk
            
            # 完成
            total_time = time.time() - start_time
            yield {
                "type": "done",
                "data": {
                    "totalRounds": len(rounds),
                    "total_sources": len(all_sources),
                    "final_completeness": framework.overall_completeness,
                    "execution_time": total_time,
                    "answer_goal": framework.answer_goal,
                    "aspects_completed": sum(1 for a in framework.targets if a.status == "complete"),
                    "aspects_total": len(framework.targets),
                }
            }
            
        except Exception as e:
            logger.error(f"❌ [Ucppt] 搜索失败: {e}", exc_info=True)
            yield {
                "type": "error",
                "data": {"message": str(e)}
            }

    # ==================== 统一分析 (v7.207 合并 L0 + L1-L5) ====================

    def _build_unified_analysis_prompt(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        构建统一分析 Prompt - v7.234

        v7.234 更新：
        1. 强化实体提取（6类实体动态识别）
        2. L1-L5分析输出结构化实体清单
        3. 搜索查询质量评估（v7.237 改为软约束）
        4. 锐度三问自检机制
        """
        context_str = json.dumps(context or {}, ensure_ascii=False, indent=2)

        return f"""你是顶级战略顾问。用**庖丁解牛**的方式分析问题——精准、高效、直击要害。

## 用户问题
{query}

## 上下文
{context_str}

## 输出规范（强制）

⛔ **绝对禁止**（违反则输出无效）：
1. 元认知叙述：不描述你要怎么思考、要遵守什么规则
   - ❌ "用户要我分析..."、"我得用庖丁解牛的方式..."
   - ❌ "用户希望我扮演..."、"这个身份意味着..."
   - ❌ "首先看用户问题..."、"我得从理解用户开始..."
2. 过程解释：不解释为什么要分析某个维度
   - ❌ "这是一个设计融合问题，核心是..."
   - ❌ "现在提取实体，这是分析的关键..."
3. 口语化词汇："好的"、"嗯"、"我想"、"我记得"

✅ **正确做法**：直接输出分析结果，像填表一样

**示例**：

❌ 错误（元认知叙述）：
"好的，用户要我分析这个民宿设计问题。首先看用户问题，这是一个设计融合问题，核心是要把北欧的HAY风格和四川峨眉山的山地环境结合起来。我得从理解用户开始，用户能提出这么具体的设计概念，应该是个专业人士..."

✅ 正确（直接输出结果）：
"**核心矛盾**：HAY几何工业感 × 峨眉山有机自然感

**用户画像**
- 身份：民宿主/设计师
- 定位：中高端，设计驱动
- 标签：文化融合探索者、设计敏感型业主

**实体清单**
| 类型 | 名称 | 关键属性 |
|-----|-----|---------|
| 品牌 | HAY | Palissade系列、Mags沙发、粉末涂层钢 |
| 地点 | 峨眉山七里坪 | 海拔1300m、湿润多雾、冷杉木/竹材 |"

## 分析要求

### 第一部分：理解用户（动态实体提取）

1. **用户画像**
   - 从表达推断：地理位置、职业、年龄段、消费能力
   - 身份标签：3-5个具体标签

2. **实体提取**（v7.234 核心改进）
   必须识别并分类以下6类实体：
   
   | 类型 | 定义 | 提取要求 |
   |------|------|----------|
   | 品牌实体 | 用户提及或暗示的品牌 | 品牌名 + 已知产品线/系列 + 核心设计师（如有） |
   | 地点实体 | 项目所在地 | 地名 + 气候/海拔/在地材料/建筑风格 |
   | 风格实体 | 设计风格关键词 | 具体风格名 + 代表性特征 |
   | 场景实体 | 应用场景 | 场景类型 + 目标用户群 + 商业模式特征 |
   | 竞品实体 | 类似定位的成功案例 | 案例名 + 差异化特点 |
   | 人物实体 | 相关设计师/创始人 | 姓名 + 代表作品 |

   ⚠️ 你需要基于问题内容**自行推断**具体实体，而非等待用户提供
   ⚠️ 如果用户提到品牌，必须推断其具体产品线、设计师、色彩系统等

3. **隐性需求**
   基于提取的实体进行关联推断：
   - 品牌→用户审美偏好→可能的价格敏感度
   - 地点→环境约束→在地化融合需求
   - 场景→商业逻辑→成功标准

4. **动机类型识别**（从12种类型中选择1-3个主导类型）

   | 类型ID | 中文名 | 典型特征 |
   |--------|--------|----------|
   | cultural | 文化认同 | 传统文化、地域特色、民族符号、精神传承 |
   | commercial | 商业价值 | ROI、坪效、运营效率、竞争策略 |
   | wellness | 健康疗愈 | 物理健康、心理疗愈、医疗标准 |
   | technical | 技术创新 | 智能化、工程技术、系统集成 |
   | sustainable | 可持续价值 | 环保、社会责任、绿色低碳 |
   | professional | 专业职能 | 行业标准、专业设备、工作流程 |
   | inclusive | 包容性 | 无障碍设计、特殊人群、尊严平等 |
   | functional | 功能性 | 空间功能、实用性、动线布局 |
   | emotional | 情感性 | 情感体验、氛围营造、心理感受 |
   | aesthetic | 审美 | 视觉美感、艺术表达、风格呈现 |
   | social | 社交 | 人际互动、社群关系、交流空间 |
   | mixed | 综合 | 多种动机混合，无明显主导 |

   输出格式：
   - 主导动机：[类型ID] + 判断依据（一句话）
   - 次要动机：[类型ID]（如有）

### 第二部分：深度分析（可操作化）

5. **L1 事实解构**
   输出结构化实体清单，必须具体到名称而非泛化描述：
   - 品牌实体：品牌名 + 产品线列表 + 核心设计师
   - 地点实体：地名 + 气候特征 + 在地材料 + 建筑风格
   - 竞品案例：案例名 + 定位特点

6. **L2 多视角建模**（动态选择3-5个视角）
   视角池：心理学/社会学/美学/经济学/技术可行性/生态/人类学/符号学

   选择原则：
   - 创造型问题：优先 美学+心理学+符号学
   - 决策型问题：优先 经济学+技术可行性+风险评估
   - 探索型问题：优先 人类学+社会学+趋势分析

   每个视角必须有具体支撑，避免泛化描述。

7. **L3 核心张力**
   必须输出：
   - 张力公式："[具体元素A] vs [具体元素B]"（不是泛化的"现代vs传统"）
   - 解决策略：至少1条可操作的融合手法

8. **L4 用户任务（JTBD）**
   用户真正想要完成的任务是什么？
   用"当...时，我想要...，以便..."的格式描述。

9. **L5 锐度自检**（三问测试）
   回答以下三个问题：
   ① 此分析只适用于本问题吗？（专一性）
   ② 能直接指导下一步行动吗？（可操作性）
   ③ 触及了用户未明说的深层诉求吗？（深度）

### 分析→搜索规划（系统性思考）v7.254

⚠️ 重要：搜索框架不是L1实体的机械映射，而是综合L1-L5分析后的**系统性规划**！

**核心原则**：
- ❌ 禁止机械映射："每个品牌→1个任务"、"每个地点→1个任务"
- ✅ 要求系统规划：围绕核心问题，设计有主次、有逻辑的搜索策略

**规划步骤**：

**第一步：识别核心问题**（基于L3张力和L4 JTBD）
- 用户真正要解决的问题是什么？
- 核心动词是什么？（融合/选择/对比/了解/验证...）
- 这决定了搜索的主线和P1任务

**第二步：设计搜索策略**（有主次、有逻辑）

| 优先级 | 任务类型 | 设计原则 | 数量 |
|-------|---------|---------|------|
| P1（核心） | 直接回答核心问题 | 围绕L4 JTBD的核心动词设计 | 1-2个 |
| P2（支撑） | 为P1提供必要背景 | 只搜索P1需要的支撑信息 | 1-3个 |
| P3（拓展） | 开阔视野的参考 | 可选，视问题复杂度决定 | 0-2个 |

**第三步：建立任务逻辑链**
- 每个任务的why_need要说明它如何服务于核心问题
- 任务之间形成"支撑→核心→验证"的逻辑关系

**示例对比**：

问题："HAY风格的峨眉山七里坪民宿设计方案"

❌ 机械映射（错误）：
T1: 搜索HAY品牌产品线（因为有品牌实体）
T2: 搜索峨眉山气候和材料（因为有地点实体）
T3: 搜索松赞酒店案例（因为有竞品实体）
T4: 搜索北欧与中式融合（因为有张力）
→ 问题：4个任务平铺直叙，缺乏主次，没有逻辑关联

✅ 系统性规划（正确）：
核心问题：如何在山地民宿中融合北欧极简与在地材料？
核心动词：融合

T1 [P1-核心]: 北欧风格与中国在地材料融合的成功案例
   why_need: 直接回答"如何融合"，这是用户最想知道的
   → 这是核心任务，其他任务都为它服务

T2 [P2-支撑]: HAY品牌的材质特点和色彩系统
   why_need: 为T1提供"北欧风格"的具体设计语言，知道融合的一端是什么
   → 支撑T1，不是独立的品牌调研

T3 [P2-支撑]: 峨眉山地区可用的在地材料和传统工艺
   why_need: 为T1提供"在地材料"的具体选项，知道融合的另一端是什么
   → 支撑T1，不是独立的地点调研

T4 [P3-拓展]: 松赞/既下山等高端民宿的设计策略
   why_need: 看看类似定位的项目如何处理风格融合，验证T1的可行性
   → 拓展验证，不是独立的竞品调研

→ 4个任务形成逻辑链：T2+T3支撑T1，T4验证T1

**规划自检**（生成targets前必须回答这5个问题）：
1. 核心问题是什么？核心动词是什么？
2. P1任务是否直接回答核心问题？
3. P2任务是否明确说明如何支撑P1？
4. 任务之间的逻辑关系是什么？（不是平铺直叙）
5. 是否避免了"每个实体→1个任务"的机械映射？

### 第三部分：搜索规划（系统性输出）

9. **搜索目标清单**（v7.265：价值驱动，拒绝硬编码）

   **任务数量原则**（⚠️ 核心变更）：
   - ❌ 禁止硬编码数量：不要预设"3-6个"、"2-3个"等范围
   - ✅ 价值驱动：只生成对回答核心问题**有实际价值**的搜索任务
   - ✅ 宁缺毋滥：1个精准任务 > 5个宽泛任务
   - ✅ 完全响应分析：任务数量由 L1-L5 分析中识别的**关键信息缺口**决定

   **任务生成判断标准**（每个任务必须通过）：
   ① 该任务搜索的内容，用户自己无法轻易获得吗？（信息增量）
   ② 该任务的结果能直接用于回答用户问题吗？（直接相关）
   ③ 该任务的搜索词适合搜索引擎吗？（可执行性）
   → 三问都是"是"才生成，否则跳过

   **任务结构**：每个任务必须包含以下字段

   | 字段 | 含义 | 示例 |
   |------|------|------|
   | question | 这个任务要回答什么问题？ | "北欧风格如何与中国在地材料融合？" |
   | search_for | 具体搜索什么内容？ | "北欧家具与中式空间融合案例、HAY在亚洲项目应用" |
   | why_need | **关键：说明此任务如何服务于核心问题** | "直接回答用户的融合需求，是P1核心任务" |
   | priority | 优先级（1=核心，2=支撑，3=拓展） | 1 |
   | success_when | 什么情况算搜索成功？ | "找到2-3个融合成功案例" |

   **分类标签**（v7.253：根据问题类型从标签池中选择，不必使用全部）：

   标签池：
   - **品牌调研**: 品牌产品线、设计语言、核心设计师
   - **案例参考**: 成功项目、最佳实践、类似定位案例
   - **方案验证**: 对比分析、融合策略、可行性验证
   - **背景知识**: 概念定义、文化背景、技术标准
   - **趋势洞察**: 行业动态、创新方向、未来趋势
   - **技术实现**: 材料工艺、施工方法、落地细节

   选择原则：
   - 根据L1实体类型选择相关标签（有品牌→用品牌调研，有地点→用背景知识）
   - 根据L3张力选择验证标签（有融合需求→用方案验证）
   - 简单问题用2-3种标签，复杂问题用4-5种
   - 不要为了使用所有标签而强行分类

   **搜索查询生成指南**（v7.265 强化版）：
   preset_keywords 是**直接可用于搜索引擎的查询语句**，质量决定搜索效果。

   **核心原则**：
   - ✅ 像真人搜索：想象用户会在百度/Google输入什么
   - ✅ 聚焦具体：每条查询只问一个问题
   - ✅ 包含实体：必须有品牌名/地名/人名/产品名等专有名词
   - ✅ 长度适中：15-35字最佳（太短无上下文，太长噪音多）

   **相关性约束**（v7.265 新增）：
   - ❌ 禁止宽泛查询："设计趋势"、"室内设计风格"、"民宿行业分析"
   - ❌ 禁止无关查询：与用户问题中的实体/场景无直接关联
   - ✅ 必须锚定用户问题：每个查询都应包含用户问题中的核心实体

   ❌ 错误示例（关键词堆砌）：
   - "HAY Palissade 户外家具 粉末涂层钢 民宿庭院 色彩搭配 Bouroullec"
   - "松赞 既下山 山地 在地材料 竹木 设计 案例 融合"

   ❌ 错误示例（过于宽泛，与用户问题弱相关）：
   - "室内设计 2024 趋势"（用户没问趋势）
   - "民宿行业发展报告"（用户问的是具体设计方案）
   - "北欧风格特点"（太泛，应聚焦用户提到的HAY品牌）

   ✅ 正确示例（自然语言 + 锚定用户问题实体）：
   - "HAY Mags 沙发 酒店项目应用案例"
   - "HAY 与木质材料搭配 室内设计实景"
   - "松赞酒店 在地材料 竹木运用 设计细节"
   - "峨眉山七里坪 精品民宿 北欧风格改造"

10. **搜索边界**
    明确列出**不搜索**的内容类型（反向定义）：
    - 不搜索的主题
    - 不搜索的内容类型
    - 不搜索的时间范围

11. **回答目标**
    最终要给用户什么样的答案。

---

分析完成后，输出以下 JSON：

```json
{{
    "user_profile": {{
        "location": "",
        "occupation": "",
        "identity_tags": [],
        "explicit_need": "",
        "implicit_needs": [],
        "motivation_types": {{
            "primary": "类型ID（如aesthetic/cultural/commercial等）",
            "primary_reason": "判断依据（一句话）",
            "secondary": ["次要类型ID"],
            "secondary_reason": "次要类型判断依据"
        }}
    }},
    "analysis": {{
        "l1_facts": {{
            "brand_entities": [
                {{"name": "品牌名", "product_lines": ["产品线1", "产品线2"], "designers": ["设计师1"], "color_system": ["色彩1"], "materials": ["材质1"]}}
            ],
            "location_entities": [
                {{"name": "地名", "climate": "气候特征", "altitude": "海拔", "local_materials": ["材料1"], "architecture_style": "建筑风格"}}
            ],
            "competitor_entities": [
                {{"name": "案例名", "positioning": "定位", "differentiator": "差异化特点"}}
            ],
            "style_entities": ["风格1"],
            "person_entities": [{{"name": "人名", "role": "角色", "works": ["作品1"]}}]
        }},
        "l2_models": {{
            "selected_perspectives": ["视角1", "视角2", "视角3"],
            "psychological": "心理学分析（具体描述）",
            "sociological": "社会学分析（具体描述）",
            "aesthetic": "美学分析（具体描述）"
        }},
        "l3_tension": {{
            "formula": "[具体元素A] vs [具体元素B]",
            "description": "张力详细描述",
            "resolution_strategy": "解决策略"
        }},
        "l4_jtbd": "当...时，我想要...，以便...",
        "l5_sharpness": {{
            "score": 0,
            "specificity": "此分析只适用于本问题吗？回答",
            "actionability": "能直接指导下一步行动吗？回答",
            "depth": "触及了用户未明说的深层诉求吗？回答"
        }}
    }},
    "search_framework": {{
        "core_question": "问题一句话本质（20字内）",
        "answer_goal": "用户期望得到的答案是...",
        "boundary": "不搜索：1.xxx 2.xxx 3.xxx",
        "targets": [
            // ⚠️ v7.265：任务数量由分析价值决定，不硬编码
            // 只生成通过"三问检验"的任务：信息增量？直接相关？可搜索？
            {{
                "id": "T1",
                "question": "【必填】这个任务要回答什么问题？（问句形式，15字内）",
                "search_for": "【必填】具体搜索什么内容（必须包含用户问题中的实体名称）",
                "why_need": "【必填】说明此任务如何直接帮助回答用户的核心问题",
                "priority": 1,
                "category": "品牌调研",
                "preset_keywords": [
                    "自然语言搜索查询（15-35字，必须包含专有名词）"
                ],
                "success_when": ["什么情况算搜索成功"],
                "expected_info": ["期望获取的信息"]
            }}
            // 继续添加其他有价值的任务（数量不限，但每个都必须有明确价值）
        ]
    }}
}}
```

**完整示例1**（复杂问题，用户问："HAY风格的民宿设计方案"）：
- L1实体：HAY品牌、民宿场景、北欧风格 → 3个基础任务
- L3张力：北欧极简 vs 在地材料 → 1个验证任务
- 总计：3-4个任务（中等复杂度）

```json
{{
    "search_framework": {{
        "core_question": "如何打造HAY风格民宿",
        "answer_goal": "一套可落地的HAY风格民宿设计方案，包含产品选型、色彩搭配、空间布局建议",
        "boundary": "不搜索：1.HAY公司财报 2.其他无关品牌 3.纯理论设计文章",
        "targets": [
            {{
                "id": "T1",
                "question": "HAY品牌的核心产品线有哪些？",
                "search_for": "HAY Palissade户外系列、Mags模块沙发、Bouroullec兄弟设计作品、HAY标志性色彩系统",
                "why_need": "从中提取可用于民宿的设计元素：色彩搭配、材质选择、家具造型",
                "priority": 1,
                "category": "品牌调研",
                "preset_keywords": [
                    "HAY 品牌设计理念 Rolf Hay 创始人访谈",
                    "HAY Mags 沙发 酒店项目应用案例"
                ],
                "success_when": ["找到HAY产品高清图片", "了解HAY色彩搭配原则", "知道HAY常用材质"],
                "expected_info": ["产品实拍图", "色彩系统说明", "材质清单"]
            }},
            {{
                "id": "T2",
                "question": "有哪些融合北欧风与在地材料的民宿案例？",
                "search_for": "松赞系列民宿、既下山酒店、大理白族风格精品民宿等类似定位项目",
                "why_need": "从成功案例中提取可复用的设计策略和材料选择",
                "priority": 2,
                "category": "案例参考",
                "preset_keywords": [
                    "松赞酒店 室内设计 在地材料运用",
                    "既下山酒店 现代与传统融合设计"
                ],
                "success_when": ["找到2-3个相似定位民宿案例", "有室内实景照片"],
                "expected_info": ["案例介绍", "设计师信息", "材料选择"]
            }},
            {{
                "id": "T3",
                "question": "HAY产品与在地材料如何融合搭配？",
                "search_for": "北欧家具与中式空间融合案例、HAY产品在亚洲项目中的应用",
                "why_need": "验证HAY风格在中国民宿场景的可行性，获取具体搭配方法",
                "priority": 3,
                "category": "方案验证",
                "preset_keywords": [
                    "北欧风格民宿 中国本土化设计案例",
                    "HAY家具 亚洲酒店项目 实际应用"
                ],
                "success_when": ["找到融合案例", "有具体搭配建议"],
                "expected_info": ["融合技巧", "搭配注意事项", "避坑指南"]
            }}
        ]
    }}
}}
```

**完整示例2**（简单问题，用户问："什么是侘寂风格"）：
- L1实体：侘寂风格 → 1个基础任务
- L3张力：无明显张力
- 总计：2个任务（简单查询）

```json
{{
    "search_framework": {{
        "core_question": "侘寂风格的定义与特点",
        "answer_goal": "清晰解释侘寂风格的起源、核心理念和视觉特征",
        "boundary": "不搜索：1.商品购买链接 2.装修公司广告",
        "targets": [
            {{
                "id": "T1",
                "question": "侘寂风格的起源和核心理念是什么？",
                "search_for": "侘寂美学起源、日本茶道文化、千利休美学思想",
                "why_need": "理解侘寂的文化根源和哲学内涵",
                "priority": 1,
                "category": "背景知识",
                "preset_keywords": [
                    "侘寂美学 日本传统文化 起源",
                    "wabi-sabi 设计理念 核心特征"
                ],
                "success_when": ["了解侘寂的历史背景", "理解核心美学理念"],
                "expected_info": ["起源历史", "哲学内涵", "代表人物"]
            }},
            {{
                "id": "T2",
                "question": "侘寂风格在室内设计中如何体现？",
                "search_for": "侘寂风格室内设计案例、材质选择、色彩搭配",
                "why_need": "获取可视化的设计参考",
                "priority": 2,
                "category": "案例参考",
                "preset_keywords": [
                    "侘寂风格 室内设计 实景案例",
                    "wabi-sabi interior design examples"
                ],
                "success_when": ["找到设计案例图片", "了解常用材质"],
                "expected_info": ["设计案例", "材质清单", "色彩方案"]
            }}
        ]
    }}
}}
```

请只输出JSON，不要有其他内容。"""

    async def _unified_analysis_stream(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        统一分析流式处理 - v7.220

        重构版本：
        - 使用新的 Prompt 结构
        - 解析为 SearchFramework（统一数据结构）
        - thinking 内容作为对话输出给用户
        - content 内容解析为 SearchFramework
        """
        logger.info(f"🔍 [统一分析 v7.220] 开始统一分析 | query={query[:50]}...")

        prompt = self._build_unified_analysis_prompt(query, context)
        full_reasoning = ""
        full_content = ""

        try:
            async for chunk in self._call_deepseek_stream_with_reasoning(
                prompt,
                model=self.thinking_model,
                max_tokens=2500
            ):
                if chunk.get("type") == "reasoning":
                    reasoning_text = chunk.get("content", "")
                    full_reasoning += reasoning_text
                    # v7.238: 过滤冗余内心独白，保留有价值的分析
                    filtered_text = self._filter_verbose_monologue(reasoning_text)
                    if filtered_text.strip():
                        yield {
                            "type": "unified_dialogue_chunk",
                            "content": filtered_text,
                        }
                elif chunk.get("type") == "content":
                    full_content += chunk.get("content", "")

            # 对话内容完成
            yield {
                "type": "unified_dialogue_complete",
                "content": full_reasoning,
            }

            logger.info(f"✅ [统一分析 v7.220] 对话完成 | reasoning_len={len(full_reasoning)}, content_len={len(full_content)}")

            # 解析 JSON 结果
            data = self._safe_parse_json(full_content, context="统一分析(v7.220)")
            if data is None:
                raise ValueError("无法解析统一分析结果")

            # v7.244: 增强诊断日志 - 检查 LLM 返回的原始数据
            search_framework_data = data.get("search_framework", {})
            raw_targets = search_framework_data.get("targets", [])
            logger.info(f"🔍 [v7.244] JSON解析完成 | targets数量={len(raw_targets)}")
            for i, t in enumerate(raw_targets[:3]):
                logger.info(f"🔍 [v7.244] 原始target[{i}] 字段: question='{t.get('question', '')[:30] if t.get('question') else '空'}', name='{t.get('name', '')[:30] if t.get('name') else '空'}', search_for='{t.get('search_for', '')[:30] if t.get('search_for') else '空'}'")

            # v7.234: 质量评估（不阻塞流程）
            quality = self._evaluate_analysis_quality_v234(data)
            
            # 发送质量状态（简化展示，只发送等级）
            yield {
                "type": "analysis_status",
                "data": {
                    "status": "complete" if quality["pass"] else "refining",
                    "quality_grade": quality["grade"],
                    "quality_score": quality["score"],
                }
            }

            # v7.234: 低分时尝试轻量优化（阈值55分）
            if not quality["pass"]:
                data, quality = await self._refine_analysis_v234(query, data, quality)
                
                # 发送优化后的状态
                yield {
                    "type": "analysis_status",
                    "data": {
                        "status": "refined" if quality["pass"] else "warning",
                        "quality_grade": quality["grade"],
                        "quality_score": quality["score"],
                    }
                }
                
                # 如果仍未达标，发送建议性提示（不阻塞）
                if not quality["pass"] and quality["suggestions"]:
                    yield {
                        "type": "analysis_warning",
                        "data": {
                            "message": "分析深度有限，建议补充更多细节",
                            "suggestions": quality["suggestions"][:2],
                        }
                    }

            # v7.220: 构建 SearchFramework
            framework = self._build_search_framework_from_json(query, data)

            # 发送用户画像就绪信号
            user_profile = data.get("user_profile", {})
            yield {
                "type": "structured_info_ready",
                "data": {
                    "has_profile": bool(user_profile.get("identity_tags") or user_profile.get("occupation")),
                    "has_preferences": bool(user_profile.get("implicit_needs")),
                },
                "_internal_data": user_profile,
            }

            # v7.220: 发送搜索框架就绪信号
            # v7.241: 始终生成框架清单，即使targets为空（修复重启后不显示问题）
            if framework:
                logger.info(f"📋 [v7.241] 搜索框架解析完成 | 目标数={len(framework.targets) if framework.targets else 0}, 质量={quality['grade']}, 核心问题={framework.core_question[:30] if framework.core_question else 'N/A'}...")

                # v7.241: 始终生成框架清单（添加错误处理）
                framework_checklist = None
                try:
                    framework_checklist = self._generate_framework_checklist(framework, data)
                    framework.framework_checklist = framework_checklist
                    logger.debug(f"✅ [v7.241] 框架清单生成成功 | 方向数={len(framework_checklist.main_directions)}, 边界数={len(framework_checklist.boundaries)}")
                except Exception as checklist_error:
                    logger.error(f"❌ [v7.241] 框架清单生成失败: {checklist_error}", exc_info=True)
                    # 创建一个最小化的框架清单作为降级方案
                    from datetime import datetime
                    framework_checklist = FrameworkChecklist(
                        core_summary=framework.core_question[:30] if framework.core_question else framework.original_query[:30],
                        main_directions=[],
                        boundaries=[],
                        answer_goal=framework.answer_goal or "为用户提供完整解答",
                        generated_at=datetime.now().isoformat(),
                    )

                # v7.238: 生成纯文字格式的 1/2/3 清单
                targets_text_list = []
                if framework.targets:
                    for i, t in enumerate(framework.targets, 1):
                        name = getattr(t, 'name', '') or getattr(t, 'question', '') or f"目标{i}"
                        desc = getattr(t, 'search_for', '') or getattr(t, 'description', '') or ""
                        if desc:
                            targets_text_list.append(f"{i}. {name} — {desc}")
                        else:
                            targets_text_list.append(f"{i}. {name}")

                framework_summary = "📋 搜索主线：\n" + "\n".join(targets_text_list) if targets_text_list else "📋 搜索主线：待规划"

                # v7.241: 始终发送 search_framework_ready 事件
                logger.info(f"📤 [v7.241] 发送 search_framework_ready 事件 | framework_checklist={'已生成' if framework_checklist else '未生成'}")
                # 🔍 v7.242 诊断日志：检查发送的 targets 数据
                logger.info(f"🔍 [诊断] 发送 targets 数量 = {len(framework.targets) if framework.targets else 0}")
                if framework.targets:
                    logger.info(f"🔍 [诊断] 发送 targets[0] = {framework.targets[0].to_dict() if framework.targets else 'None'}")
                yield {
                    "type": "search_framework_ready",
                    "data": {
                        "core_question": framework.core_question,
                        "answer_goal": framework.answer_goal,
                        "boundary": framework.boundary,
                        "target_count": len(framework.targets) if framework.targets else 0,
                        "targets": [t.to_dict() for t in framework.targets] if framework.targets else [],
                        "targets_summary": framework_summary,  # v7.238: 纯文字清单
                        "quality_grade": quality["grade"],
                        # v7.241: 始终包含框架清单（即使为空）
                        "framework_checklist": framework_checklist.to_dict() if framework_checklist else None,
                    },
                    "_internal_framework": framework,
                }

            yield {
                "type": "analysis_complete",
                "framework": framework,
                "quality": quality,  # v7.234: 添加质量信息
            }

        except Exception as e:
            logger.warning(f"⚠️ [统一分析 v7.234] 分析失败: {e}")
            # 如果有对话内容，先发送
            if full_reasoning:
                yield {
                    "type": "unified_dialogue_complete",
                    "content": full_reasoning,
                }
            yield {
                "type": "analysis_complete",
                "framework": self._build_simple_search_framework(query),
            }

    def _build_search_framework_from_json(self, query: str, data: Dict[str, Any]) -> SearchFramework:
        """
        从 JSON 数据构建 SearchFramework - v7.236

        v7.236 更新：
        - 解析新字段 question/search_for/why_need/success_when
        - 兼容旧字段 name/description/purpose/quality_criteria
        
        v7.232 更新：
        - 解析 preset_keywords（预设搜索关键词）
        - 解析 quality_criteria（质量达标标准）
        
        v7.234 更新：
        - 如果 targets 为空，使用默认目标兜底
        """
        user_profile = data.get("user_profile", {})
        analysis = data.get("analysis", {})
        search_data = data.get("search_framework", {})

        # 🔍 v7.242 诊断日志：检查 LLM 返回的 JSON 结构
        logger.info(f"🔍 [诊断] data keys = {list(data.keys())}")
        logger.info(f"🔍 [诊断] search_framework = {json.dumps(search_data, ensure_ascii=False)[:500] if search_data else 'None'}")
        logger.info(f"🔍 [诊断] targets 原始数据 = {search_data.get('targets', [])[:2] if search_data.get('targets') else '空'}")

        # 构建搜索目标列表
        targets = []
        for t in search_data.get("targets", []):
            # v7.244: 增强兜底逻辑 - 从多个字段推断有意义的名称
            if not any([t.get("question"), t.get("name"), t.get("search_for"), t.get("description")]):
                logger.warning(f"⚠️ [v7.244] LLM 返回的 target 缺少描述字段: {t}")
                # 按优先级尝试从其他字段推断
                inferred_name = None
                if t.get("purpose"):
                    inferred_name = t["purpose"][:50]
                elif t.get("why_need"):
                    inferred_name = t["why_need"][:50]
                elif t.get("expected_info") and len(t.get("expected_info", [])) > 0:
                    inferred_name = f"搜索: {', '.join(t['expected_info'][:2])}"
                elif t.get("preset_keywords") and len(t.get("preset_keywords", [])) > 0:
                    # 从预设关键词提取核心内容
                    first_keyword = t["preset_keywords"][0]
                    inferred_name = first_keyword[:40] if first_keyword else None
                elif t.get("success_when") and len(t.get("success_when", [])) > 0:
                    inferred_name = t["success_when"][0][:40]
                elif t.get("category"):
                    # 使用 category + 序号，添加更多上下文
                    inferred_name = f"{t['category']}方向_{t.get('id', 'X')}"
                else:
                    inferred_name = f"搜索方向_{t.get('id', len(targets)+1)}"

                t["name"] = inferred_name
                t["question"] = inferred_name
                logger.info(f"📝 [v7.244] 推断名称: {inferred_name}")

            # v7.232: 解析预设关键词
            preset_keywords = t.get("preset_keywords", [])

            # v7.236: 优先使用新字段，回退到旧字段
            question = t.get("question", "") or t.get("name", "")
            search_for = t.get("search_for", "") or t.get("description", "")
            why_need = t.get("why_need", "") or t.get("purpose", "")
            success_when = t.get("success_when", []) or t.get("quality_criteria", [])

            # 🔍 v7.243 诊断日志：检查每个 target 的字段值
            logger.info(f"🔍 [诊断] target[{t.get('id', '?')}] question='{question}', search_for='{search_for[:30] if search_for else ''}'...")
            
            # v7.237: 增强场景化关键词生成（方案B）
            if not preset_keywords:
                preset_keywords = self._generate_enhanced_keywords(
                    query, question, search_for, why_need, targets
                )

            target = SearchTarget(
                id=t.get("id", f"T{len(targets)+1}"),
                # v7.236: 新字段
                question=question,
                search_for=search_for,
                why_need=why_need,
                success_when=success_when,
                # 旧字段（通过 __post_init__ 自动同步）
                name=t.get("name", ""),
                description=t.get("description", ""),
                purpose=t.get("purpose", ""),
                priority=t.get("priority", 2),
                category=t.get("category", "品牌调研"),
                preset_keywords=preset_keywords,
                quality_criteria=t.get("quality_criteria", []),
                expected_info=t.get("expected_info", []),
                # v7.260: 全局并行支持
                dependencies=t.get("dependencies", []),
                execution_order=t.get("execution_order", 1),
                group_id=t.get("group_id", ""),
                can_parallel=t.get("can_parallel", True),
                search_action=t.get("search_action", ""),
                sub_tasks=t.get("sub_tasks", []),
            )
            targets.append(target)

            # v7.244: 验证关键字段不为空
            if not (target.question and target.question.strip()) and not (target.name and target.name.strip()) and not (target.search_for and target.search_for.strip()):
                logger.warning(f"⚠️ [v7.244] target[{target.id}] 关键字段全为空，使用 category 作为名称")
                # 如果所有描述字段都为空，至少用 category + id 区分
                if not target.name or not target.name.strip():
                    target.name = f"{target.category}_{target.id}"
                if not target.question or not target.question.strip():
                    target.question = target.name

        # 🔍 v7.242 诊断日志：检查构建后的 targets 数量
        logger.info(f"🔍 [诊断] 构建后 targets 数量 = {len(targets)}")

        # v7.234: 如果 targets 为空，使用默认目标兜底
        if not targets:
            logger.warning(f"⚠️ [v7.234] targets 为空，创建默认目标 | query={query[:30]}...")
            default_framework = self._build_simple_search_framework(query)
            targets = default_framework.targets

        # v7.234: 处理 l1_facts 类型（可能是 list 或 dict）
        raw_l1_facts = analysis.get("l1_facts", [])
        if isinstance(raw_l1_facts, dict):
            # v7.234 新格式：从 dict 提取关键实体作为事实列表
            l1_facts_list = []
            for entity_type, entities in raw_l1_facts.items():
                if isinstance(entities, list):
                    for entity in entities[:2]:  # 每类取前2个
                        if isinstance(entity, dict):
                            name = entity.get("name", "")
                            if name:
                                l1_facts_list.append(f"{name}({entity_type[:2]})")
                        elif isinstance(entity, str):
                            l1_facts_list.append(entity)
        elif isinstance(raw_l1_facts, list):
            l1_facts_list = raw_l1_facts
        else:
            l1_facts_list = []

        # v7.234: 处理 l3_tension 类型（可能是 str 或 dict）
        raw_l3_tension = analysis.get("l3_tension", "")
        if isinstance(raw_l3_tension, dict):
            l3_tension_str = raw_l3_tension.get("formula", "") or raw_l3_tension.get("description", "")
        else:
            l3_tension_str = str(raw_l3_tension) if raw_l3_tension else ""

        # v7.251: 确保L1实体和L3张力都有对应的搜索任务（兜底逻辑）
        targets = self._ensure_entity_coverage(targets, data, query)

        return SearchFramework(
            original_query=query,
            core_question=search_data.get("core_question", ""),
            answer_goal=search_data.get("answer_goal", ""),
            boundary=search_data.get("boundary", ""),
            targets=targets,
            l1_facts=l1_facts_list,
            l2_models=analysis.get("l2_models", {}),
            l3_tension=l3_tension_str,
            l4_jtbd=analysis.get("l4_jtbd", ""),
            l5_sharpness=analysis.get("l5_sharpness", {}),
            user_profile=user_profile,
        )

    def _ensure_entity_coverage(
        self,
        targets: List[SearchTarget],
        analysis_data: Dict[str, Any],
        query: str
    ) -> List[SearchTarget]:
        """
        确保L1实体和L3张力都有对应的搜索任务 - v7.251

        作为prompt优化的兜底，检查并补充缺失的搜索任务
        """
        analysis = analysis_data.get("analysis", {})
        l1_facts = analysis.get("l1_facts", {})
        l3_tension = analysis.get("l3_tension", {})

        # 收集现有targets中已覆盖的实体名称
        covered_text = ""
        for t in targets:
            # 从search_for和preset_keywords中提取已覆盖的实体
            covered_text += (t.search_for or "").lower() + " "
            covered_text += " ".join(t.preset_keywords or []).lower() + " "
            covered_text += (t.question or "").lower() + " "

        new_targets = []
        next_id = len(targets) + 1

        # 1. 检查品牌实体覆盖
        if isinstance(l1_facts, dict):
            for brand in l1_facts.get("brand_entities", []):
                if isinstance(brand, dict):
                    brand_name = brand.get("name", "")
                    if brand_name and brand_name.lower() not in covered_text:
                        product_lines = brand.get("product_lines", [])
                        search_for_text = f"{brand_name} " + ", ".join(product_lines[:3]) if product_lines else brand_name
                        new_targets.append(SearchTarget(
                            id=f"T{next_id}",
                            question=f"{brand_name}品牌的核心产品线有哪些？",
                            search_for=search_for_text,
                            why_need=f"了解{brand_name}的设计语言和产品特点",
                            priority=2,
                            category="品牌调研",
                            preset_keywords=[
                                f"{brand_name} 品牌设计理念",
                                f"{brand_name} 产品系列 代表作品"
                            ],
                            expected_info=["产品线", "设计特点", "色彩系统"],
                        ))
                        next_id += 1
                        logger.info(f"📝 [v7.251] 补充品牌实体搜索任务: {brand_name}")

            # 2. 检查地点实体覆盖
            for location in l1_facts.get("location_entities", []):
                if isinstance(location, dict):
                    loc_name = location.get("name", "")
                    if loc_name and loc_name.lower() not in covered_text:
                        new_targets.append(SearchTarget(
                            id=f"T{next_id}",
                            question=f"{loc_name}的建筑风格和在地材料有哪些？",
                            search_for=f"{loc_name} 建筑风格 在地材料 气候特点",
                            why_need=f"了解{loc_name}的环境约束和本土设计元素",
                            priority=2,
                            category="背景知识",
                            preset_keywords=[
                                f"{loc_name} 传统建筑 设计特点",
                                f"{loc_name} 民宿设计 在地化"
                            ],
                            expected_info=["建筑风格", "在地材料", "气候适应"],
                        ))
                        next_id += 1
                        logger.info(f"📝 [v7.251] 补充地点实体搜索任务: {loc_name}")

            # 3. 检查竞品实体覆盖
            for competitor in l1_facts.get("competitor_entities", []):
                if isinstance(competitor, dict):
                    comp_name = competitor.get("name", "")
                    if comp_name and comp_name.lower() not in covered_text:
                        new_targets.append(SearchTarget(
                            id=f"T{next_id}",
                            question=f"{comp_name}的设计特点和成功经验？",
                            search_for=f"{comp_name} 设计案例 成功经验",
                            why_need=f"从{comp_name}案例中提取可借鉴的设计策略",
                            priority=2,
                            category="案例参考",
                            preset_keywords=[
                                f"{comp_name} 室内设计 案例分析",
                                f"{comp_name} 设计理念 特色"
                            ],
                            expected_info=["设计特点", "成功经验", "差异化"],
                        ))
                        next_id += 1
                        logger.info(f"📝 [v7.251] 补充竞品实体搜索任务: {comp_name}")

        # 4. 检查L3张力覆盖
        tension_formula = ""
        if isinstance(l3_tension, dict):
            tension_formula = l3_tension.get("formula", "")
        elif isinstance(l3_tension, str):
            tension_formula = l3_tension

        if tension_formula and "vs" in tension_formula.lower():
            # 检查是否有对应的验证任务
            has_tension_task = any(
                "融合" in (t.search_for or "") or "对比" in (t.search_for or "") or "验证" in (t.category or "")
                for t in targets
            )
            if not has_tension_task:
                # 安全分割张力公式
                parts = tension_formula.lower().split(" vs ")
                if len(parts) >= 2:
                    keyword1 = parts[0].strip()
                    keyword2 = parts[-1].strip()
                    preset_kw1 = f"{keyword1} {keyword2} 融合设计案例"
                    preset_kw2 = f"{keyword1} {keyword2} 结合"
                else:
                    preset_kw1 = tension_formula.replace(" vs ", " ") + " 融合设计案例"
                    preset_kw2 = tension_formula + " 解决方案"

                new_targets.append(SearchTarget(
                    id=f"T{next_id}",
                    question="如何解决核心设计张力？",
                    search_for=f"{tension_formula} 融合案例 解决方案",
                    why_need="找到解决核心张力的成功案例和策略",
                    priority=1,  # 张力验证是高优先级
                    category="方案验证",
                    preset_keywords=[preset_kw1, preset_kw2],
                    expected_info=["融合案例", "解决策略", "注意事项"],
                ))
                next_id += 1
                logger.info(f"📝 [v7.251] 补充张力验证搜索任务: {tension_formula}")

        if new_targets:
            logger.info(f"✅ [v7.251] 共补充 {len(new_targets)} 个搜索任务")

        return targets + new_targets

    def _generate_framework_checklist(
        self,
        framework: SearchFramework,
        analysis_data: Dict[str, Any]
    ) -> FrameworkChecklist:
        """
        生成框架清单 - v7.261 增强版（动机类型系统化）

        从 SearchFramework 和分析数据中提取结构化的框架清单，
        用于前端展示和指导后续搜索。

        v7.261 更新：
        - 集成 MotivationEngine 进行动机类型识别
        - 按动机类型对 targets 进行分组聚合
        - main_directions 按动机优先级排序

        v7.260 更新：
        - 集成 TaskComplexityAnalyzer 进行复杂度评估
        - 从 SearchTarget.sub_tasks 提取子任务列表
        - 支持全局并行调度

        v7.250 更新：
        - 从 analysis_data 中提取深度分析摘要（用户画像、关键实体、核心张力等）
        - 保留L0-L5分析结果，用于前端展示和后续搜索参考
        """
        from datetime import datetime

        # v7.260: 复杂度评估
        complexity_score = 0.0
        recommended_task_count = 5
        try:
            from intelligent_project_analyzer.services.core_task_decomposer import TaskComplexityAnalyzer
            complexity_result = TaskComplexityAnalyzer.analyze(
                framework.original_query,
                analysis_data
            )
            complexity_score = complexity_result.get("complexity_score", 0.0)
            recommended_task_count = complexity_result.get("recommended_max", 5)
            logger.info(f"📊 [v7.260] 复杂度评估: score={complexity_score:.2f}, recommended_tasks={recommended_task_count}")
        except Exception as e:
            logger.warning(f"⚠️ [v7.260] 复杂度评估失败: {e}，使用默认值")

        # 提取核心问题（限制长度）
        core_summary = framework.core_question or framework.original_query[:50]
        if len(core_summary) > 30:
            core_summary = core_summary[:27] + "..."

        # v7.263: 修复框架清单显示 - 直接展示具体搜索任务，动机作为辅助标签
        # 问题：v7.261按动机分组导致前端显示动机类型名称而非具体任务
        # 修复：改为逐任务展示，动机类型作为标签
        main_directions = []
        motivation_distribution = {}

        try:
            from intelligent_project_analyzer.services.motivation_engine import (
                MotivationTypeRegistry, MotivationInferenceEngine
            )

            registry = MotivationTypeRegistry()
            engine = MotivationInferenceEngine()

            # v7.263: 逐任务生成 main_directions，动机作为标签
            for target in framework.targets:
                # 提取任务名称
                direction_name = None
                for field in [target.question, target.name, target.search_for, target.description]:
                    if field and field.strip():
                        direction_name = field.strip()[:50]
                        break
                if not direction_name:
                    direction_name = f"{target.category}_{target.id}"

                # 提取期望结果
                expected_outcome = ""
                if target.success_when:
                    expected_outcome = ", ".join(target.success_when[:2])
                elif target.expected_info:
                    expected_outcome = ", ".join(target.expected_info[:2])

                # 识别动机类型（作为标签）
                task_dict = {
                    "title": target.question or target.name or "",
                    "description": target.search_for or target.description or "",
                    "source_keywords": target.preset_keywords or [],
                }
                result = engine._keyword_matching(
                    task_dict,
                    framework.original_query,
                    None
                )
                motivation_id = result.primary
                motivation_type = registry.get_type(motivation_id)
                if not motivation_type:
                    motivation_type = registry.get_type("mixed")

                # 统计分布
                motivation_distribution[motivation_id] = motivation_distribution.get(motivation_id, 0) + 1

                # 收集子任务
                sub_tasks_list = []
                if hasattr(target, 'sub_tasks') and target.sub_tasks:
                    sub_tasks_list = target.sub_tasks

                # v7.263: 每个任务作为独立的 direction
                direction = {
                    "direction": direction_name,  # ✅ 显示具体任务名称
                    "purpose": target.why_need or target.purpose or "",  # ✅ 显示任务目的
                    "expected_outcome": expected_outcome,  # ✅ 显示期望结果
                    "sub_tasks": sub_tasks_list,
                    # 动机作为辅助标签
                    "motivation_tag": motivation_type.label_zh if motivation_type else "",
                    "motivation_id": motivation_id,
                    "motivation_color": motivation_type.color if motivation_type else "#808080",
                    "priority": target.priority,
                    "target_id": target.id,
                }
                main_directions.append(direction)

            # 按优先级排序
            main_directions.sort(key=lambda x: x.get("priority", 99))

            logger.info(f"📋 [v7.263] 框架清单生成完成 | 任务数={len(main_directions)}, 动机分布={motivation_distribution}")

        except Exception as e:
            logger.warning(f"⚠️ [v7.263] 框架清单生成失败: {e}，使用降级逻辑")
            # 降级：使用原有的逐个target提取逻辑
            main_directions = self._generate_main_directions_fallback(framework)
            motivation_distribution = {}

        # 提取搜索边界
        boundaries = []
        if framework.boundary:
            # 解析边界字符串（格式可能是："不搜索：1.xxx 2.xxx" 或 "不涉及xxx、xxx"）
            import re
            boundary_text = framework.boundary
            # 移除前缀
            boundary_text = re.sub(r'^(不搜索|不涉及|边界)[：:]\s*', '', boundary_text)
            # 按数字分割
            parts = re.split(r'\d+[\.、]', boundary_text)
            for p in parts:
                p = p.strip()
                if p:
                    # 按顿号或逗号分割
                    sub_parts = re.split(r'[、，,]', p)
                    for sp in sub_parts:
                        sp = sp.strip()
                        if sp and len(sp) > 1:
                            boundaries.append(sp)

        # 回答目标
        answer_goal = framework.answer_goal or f"为用户提供关于「{core_summary}」的完整解答"

        # === v7.250 新增：提取深度分析摘要 ===

        # 1. 提取用户画像摘要
        user_profile = analysis_data.get("user_profile", {})
        user_context = {}
        if user_profile:
            identity_tags = user_profile.get("identity_tags", [])
            user_context = {
                "identity": ", ".join(identity_tags[:3]) if identity_tags else "",
                "occupation": user_profile.get("occupation", ""),
                "implicit_needs": user_profile.get("implicit_needs", [])[:3]
            }

        # 2. 提取L1关键实体（从6类实体中提取核心信息）
        analysis = analysis_data.get("analysis", {})
        l1_facts = analysis.get("l1_facts", {})
        key_entities = []

        # 处理 l1_facts 可能是 dict 或 list 的情况
        if isinstance(l1_facts, dict):
            # 品牌实体
            for e in l1_facts.get("brand_entities", [])[:2]:
                if isinstance(e, dict) and e.get("name"):
                    product_lines = e.get("product_lines", [])
                    detail = ", ".join(product_lines[:2]) if product_lines else ""
                    key_entities.append({
                        "type": "brand",
                        "name": e.get("name", ""),
                        "detail": detail
                    })

            # 地点实体
            for e in l1_facts.get("location_entities", [])[:2]:
                if isinstance(e, dict) and e.get("name"):
                    key_entities.append({
                        "type": "location",
                        "name": e.get("name", ""),
                        "detail": e.get("climate", "") or e.get("architecture_style", "")
                    })

            # 竞品实体
            for e in l1_facts.get("competitor_entities", [])[:2]:
                if isinstance(e, dict) and e.get("name"):
                    key_entities.append({
                        "type": "competitor",
                        "name": e.get("name", ""),
                        "detail": e.get("positioning", "")
                    })

            # 风格实体
            style_entities = l1_facts.get("style_entities", [])
            for style in style_entities[:2]:
                if isinstance(style, str) and style:
                    key_entities.append({
                        "type": "style",
                        "name": style,
                        "detail": ""
                    })

            # 人物实体
            for e in l1_facts.get("person_entities", [])[:2]:
                if isinstance(e, dict) and e.get("name"):
                    works = e.get("works", [])
                    detail = ", ".join(works[:2]) if works else e.get("role", "")
                    key_entities.append({
                        "type": "person",
                        "name": e.get("name", ""),
                        "detail": detail
                    })

        # 3. 提取L2分析视角
        l2_models = analysis.get("l2_models", {})
        analysis_perspectives = []
        if isinstance(l2_models, dict):
            analysis_perspectives = l2_models.get("selected_perspectives", [])[:4]

        # 4. 提取L3核心张力
        l3_tension = analysis.get("l3_tension", {})
        core_tension = ""
        if isinstance(l3_tension, dict):
            core_tension = l3_tension.get("formula", "") or l3_tension.get("description", "")
        elif l3_tension:
            core_tension = str(l3_tension)

        # 5. 提取L4 JTBD
        user_task = analysis.get("l4_jtbd", "")

        # 6. 提取L5锐度自检
        l5_sharpness = analysis.get("l5_sharpness", {})
        sharpness_check = {}
        if isinstance(l5_sharpness, dict):
            sharpness_check = {
                "specificity": l5_sharpness.get("specificity", ""),
                "actionability": l5_sharpness.get("actionability", ""),
                "depth": l5_sharpness.get("depth", "")
            }

        logger.debug(f"📋 [v7.260] 框架清单深度分析摘要 | 实体数={len(key_entities)}, 视角数={len(analysis_perspectives)}, 张力={bool(core_tension)}, JTBD={bool(user_task)}, 复杂度={complexity_score:.2f}")

        return FrameworkChecklist(
            core_summary=core_summary,
            main_directions=main_directions,
            boundaries=boundaries[:5],  # 最多5个边界
            answer_goal=answer_goal,
            generated_at=datetime.now().isoformat(),
            # v7.260 新增字段
            complexity_score=complexity_score,
            recommended_task_count=recommended_task_count,
            # v7.261 新增字段
            motivation_distribution=motivation_distribution,
            # v7.250 新增字段
            user_context=user_context,
            key_entities=key_entities,
            analysis_perspectives=analysis_perspectives,
            core_tension=core_tension,
            user_task=user_task,
            sharpness_check=sharpness_check,
        )

    def _generate_main_directions_fallback(self, framework: SearchFramework) -> List[Dict[str, Any]]:
        """
        降级方法：生成 main_directions（不使用动机引擎）- v7.261

        当动机引擎不可用时，使用原有的逐个target提取逻辑
        """
        main_directions = []
        for target in framework.targets:
            # 提取方向名称
            direction_name = None
            for field in [target.question, target.name, target.search_for, target.description]:
                if field and field.strip():
                    direction_name = field.strip()[:50]
                    break

            if not direction_name and target.preset_keywords and len(target.preset_keywords) > 0:
                first_kw = target.preset_keywords[0]
                if first_kw and first_kw.strip():
                    direction_name = first_kw.strip()[:40]

            if not direction_name and target.expected_info and len(target.expected_info) > 0:
                direction_name = f"搜索: {', '.join(target.expected_info[:2])}"

            if not direction_name:
                if target.why_need and target.why_need.strip():
                    direction_name = target.why_need.strip()[:40]
                elif target.purpose and target.purpose.strip():
                    direction_name = target.purpose.strip()[:40]

            if not direction_name:
                direction_name = f"{target.category}_{target.id}"

            if direction_name and len(direction_name) > 50:
                direction_name = direction_name[:47] + "..."

            purpose = target.why_need or target.purpose or ""
            expected_outcome = ""
            if target.success_when:
                expected_outcome = ", ".join(target.success_when[:2])
            elif target.expected_info:
                expected_outcome = ", ".join(target.expected_info[:2])

            sub_tasks_list = []
            if hasattr(target, 'sub_tasks') and target.sub_tasks:
                sub_tasks_list = target.sub_tasks

            if direction_name:
                direction = {
                    "direction": direction_name,
                    "purpose": purpose,
                    "expected_outcome": expected_outcome,
                    "sub_tasks": sub_tasks_list,
                    # 降级模式不包含动机信息
                    "motivation_id": None,
                    "motivation_priority": None,
                    "motivation_color": None,
                }
                main_directions.append(direction)

        return main_directions

    def _generate_enhanced_keywords(self, query: str, question: str, search_for: str, why_need: str, all_targets: list) -> List[str]:
        """
        生成增强场景化关键词 - v7.237 (方案B)
        
        基于具体需求生成更精准、场景化的搜索关键词，
        优先关注实际应用案例和融合策略
        """
        keywords = []
        
        # 提取查询中的核心实体
        query_lower = query.lower()
        
        # 品牌+场景组合关键词
        if any(brand in query_lower for brand in ['hay', '丹麦', '北欧']):
            if '民宿' in query_lower or '酒店' in query_lower:
                keywords.extend([
                    f"HAY家具 中式空间 搭配案例",
                    f"北欧极简风格 民宿设计 实际案例",
                    f"现代丹麦家具 传统建筑 融合设计"
                ])
        
        # 地点+风格融合关键词
        if any(loc in query_lower for loc in ['峨眉山', '四川', '山地']):
            keywords.extend([
                f"四川山地建筑 现代家具 适应性设计",
                f"中国山区民宿 国际品牌家具 实用案例",
                f"松赞林卡 现代设计 本土材料 融合策略"
            ])
        
        # 成功案例关键词（优先级最高）
        if search_for and '案例' not in search_for:
            # 为非案例搜索添加案例导向
            enhanced_search = f"{search_for} 成功案例 项目实践"
            keywords.append(enhanced_search)
        
        # 基于问题类型优化
        if question:
            if '如何' in question or 'how' in question.lower():
                keywords.append(f"{question.replace('如何', '')} 实施方法 具体步骤")
            elif '什么' in question or 'what' in question.lower():
                keywords.append(f"{question.replace('什么', '')} 专业解读 深度分析")
        
        # 回退到基础关键词
        if not keywords:
            if search_for:
                keywords = [f"{query[:20]} {search_for[:40]}"]
            elif question:
                keywords = [f"{query[:20]} {question[:30]}"]
            else:
                keywords = [f"{query[:30]} 专业分析"]
        
        return keywords[:3]  # 限制关键词数量，保证质量

    def _should_include_source(self, source: Dict[str, Any], query: str) -> bool:
        """
        判断是否应该包含此搜索结果 - v7.237 (方案B+C)
        
        基于质量配置应用不同的过滤策略
        """
        if not self.search_quality_config.design_professional_mode:
            return True  # 非专业模式，不过滤
        
        title = source.get("title", "").lower()
        content = source.get("content", "").lower()
        site_name = source.get("siteName", "").lower()
        
        # 1. 商业内容过滤
        if self.search_quality_config.filter_commercial_content:
            commercial_keywords = [
                "价格", "购买", "优惠", "促销", "订购", "商品",
                "price", "buy", "sale", "discount", "shop", "store"
            ]
            if any(kw in title or kw in content for kw in commercial_keywords):
                if not any(kw in title or kw in content for kw in ["案例", "项目", "设计", "应用"]):
                    return False
        
        # 2. 案例研究优先
        if self.search_quality_config.prioritize_case_studies:
            case_study_keywords = [
                "案例", "项目", "实践", "应用", "设计", "方案",
                "case", "project", "practice", "application", "design"
            ]
            has_case_keywords = any(kw in title or kw in content for kw in case_study_keywords)
            
            # 非案例内容的相关性要求更高
            if not has_case_keywords:
                query_words = set(query.lower().split())
                title_words = set(title.split())
                if len(query_words.intersection(title_words)) < 2:
                    return False
        
        # 3. 专业域名优先
        professional_domains = [
            "archdaily", "dezeen", "designboom", "interiordesign", 
            "tuozhe8", "jianshu", "zhihu", "douban"
        ]
        is_professional = any(domain in site_name for domain in professional_domains)
        
        # 非专业域名的内容质量要求更高
        if not is_professional:
            min_content_length = 100
            if len(content) < min_content_length:
                return False
        
        return True

    def _build_simple_search_framework(self, query: str) -> SearchFramework:
        """
        构建简单的搜索框架（降级方案）- v7.220
        """
        # 创建默认的搜索目标 - v7.232: 添加预设关键词
        default_targets = [
            SearchTarget(
                id="T1",
                name="基础信息",
                description=f"搜索关于 {query[:30]} 的基础信息",
                purpose="建立基础认知",
                priority=1,
                category="基础",
                preset_keywords=[
                    f"{query[:40]} 核心概念 定义 背景知识",
                    f"{query[:40]} 基础介绍 入门指南",
                ],
                expected_info=["核心概念", "基本定义"],
            ),
            SearchTarget(
                id="T2",
                name="案例参考",
                description=f"搜索 {query[:30]} 相关案例",
                purpose="获取实际案例参考",
                priority=2,
                category="案例",
                preset_keywords=[
                    f"{query[:40]} 案例分析 实际应用",
                    f"{query[:40]} 最佳实践 成功经验",
                ],
                expected_info=["成功案例", "最佳实践"],
            ),
        ]

        return SearchFramework(
            original_query=query,
            core_question=query[:50],
            answer_goal=f"为用户提供关于 {query[:30]} 的完整答案",
            boundary="",
            targets=default_targets,
        )

    # ==================== v7.234 质量评估与优化 ====================

    def _calculate_proper_noun_ratio(self, text: str) -> float:
        """
        计算专有名词占比 - v7.234
        
        通过以下特征识别专有名词：
        1. 英文大写字母开头的词
        2. 中文品牌/地名/人名模式（2-4字连续）
        3. 已知的专有名词列表匹配
        """
        import re
        
        if not text:
            return 0.0
        
        # 移除标点和空格计算总长度
        clean_text = re.sub(r'[^\w\u4e00-\u9fff]', '', text)
        total_chars = len(clean_text)
        if total_chars == 0:
            return 0.0
        
        proper_noun_chars = 0
        
        # 1. 英文专有名词（大写开头的词）
        english_proper = re.findall(r'\b[A-Z][a-zA-Z]{2,}\b', text)
        for word in english_proper:
            proper_noun_chars += len(word)
        
        # 2. 常见品牌/设计相关专有名词
        known_proper_nouns = [
            # 品牌
            "HAY", "MUJI", "IKEA", "Vitra", "Fritz Hansen", "Knoll", "Herman Miller",
            "Flos", "Artemide", "B&B Italia", "Cassina", "Zanotta", "Moroso",
            "无印良品", "宜家", "造作", "吱音", "梵几",
            # 设计师
            "Bouroullec", "Diez", "Bentzen", "Jasper Morrison", "Naoto Fukasawa",
            "原研哉", "深�的良品", "安藤忠雄", "隈研吾",
            # 酒店/民宿品牌
            "松赞", "既下山", "安缦", "虹夕诺雅", "青普", "大乐之野", "过云山居",
            # 地名
            "峨眉山", "七里坪", "莫干山", "千岛湖", "大理", "丽江", "阳朔",
        ]
        
        for noun in known_proper_nouns:
            if noun.lower() in text.lower():
                proper_noun_chars += len(noun)
        
        # 3. 产品线模式（英文+数字/系列名）
        product_patterns = re.findall(r'[A-Z][a-zA-Z]+\s*(?:系列|Series|Collection|Chair|Sofa|Table|Lamp)', text)
        for pattern in product_patterns:
            proper_noun_chars += len(re.sub(r'\s', '', pattern))
        
        # 防止重复计算，取最小值
        ratio = min(1.0, proper_noun_chars / total_chars)
        return ratio

    def _evaluate_analysis_quality_v234(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        通用化质量评估 - v7.265
        
        评分维度（100分制）：
        1. 实体类型覆盖度 (20分) - 是否覆盖品牌/地点/竞品/人物至少3类
        2. 实体具体度 (20分) - 专有名词密度而非特定词检测
        3. 搜索查询质量 (20分) - 自然语言短语，包含具体实体（v7.237 软约束）
        4. 任务相关性 (20分) - v7.265 新增：任务是否与用户问题直接相关
        5. 张力可操作性 (10分) - 是否有vs结构+解决策略
        6. 锐度三问 (10分) - 是否通过专一性/可操作性/深度测试
        """
        score = 0
        issues = []
        suggestions = []
        
        analysis = analysis_data.get("analysis", {})
        l1_facts = analysis.get("l1_facts", {})
        
        # 将l1_facts转为文本用于分析
        if isinstance(l1_facts, dict):
            l1_text = json.dumps(l1_facts, ensure_ascii=False)
        elif isinstance(l1_facts, list):
            l1_text = json.dumps(l1_facts, ensure_ascii=False)
        else:
            l1_text = str(l1_facts)
        
        # 1. 实体类型覆盖度 (25分)
        entity_types_found = 0
        entity_checks = {
            "brand": ["brand_entities", "品牌", "产品线", "product_lines"],
            "location": ["location_entities", "地点", "地名", "气候", "climate"],
            "competitor": ["competitor_entities", "竞品", "案例", "松赞", "既下山", "安缦"],
            "style": ["style_entities", "风格", "北欧", "极简", "现代"],
            "person": ["person_entities", "设计师", "创始人", "designers"],
            "scene": ["场景", "民宿", "酒店", "空间", "室内"],
        }
        
        for entity_type, keywords in entity_checks.items():
            if any(kw in l1_text for kw in keywords):
                entity_types_found += 1
        
        entity_coverage_score = min(20, entity_types_found * 4)
        score += entity_coverage_score
        
        if entity_types_found < 3:
            issues.append(f"实体类型覆盖不足：仅覆盖{entity_types_found}/6类")
            suggestions.append("补充品牌产品线、地点特征、竞品案例等实体")
        
        # 2. 实体具体度 (20分) - 基于专有名词密度
        proper_noun_ratio = self._calculate_proper_noun_ratio(l1_text)
        specificity_score = min(20, int(proper_noun_ratio * 50))
        score += specificity_score
        
        if proper_noun_ratio < 0.3:
            issues.append(f"实体具体度不足：专有名词占比{proper_noun_ratio:.1%}")
            suggestions.append("补充具体品牌名、产品名、设计师名、地名等专有名词")
        
        # 3. 搜索查询质量 (20分) - v7.265 调整权重
        search_framework = analysis_data.get("search_framework", {})
        targets = search_framework.get("targets", [])
        keyword_scores = []

        for t in targets:
            for kw in t.get("preset_keywords", []):
                kw_len = len(kw)
                # v7.265: 调整长度范围为15-35字（更精确）
                length_ok = 15 <= kw_len <= 35

                # v7.237: 专有名词占比作为参考，不再硬性要求≥40%
                kw_ratio = self._calculate_proper_noun_ratio(kw)

                if length_ok and kw_ratio >= 0.3:
                    keyword_scores.append(1.0)
                elif length_ok:
                    keyword_scores.append(0.7)  # 长度合适但专有名词少，仍给分
                elif kw_len < 15:
                    keyword_scores.append(0.3)
                    issues.append(f"搜索查询较短：'{kw[:20]}...'（{kw_len}字），建议补充更多上下文")
                elif kw_len > 35:
                    keyword_scores.append(0.5)  # 过长但仍可用
                else:
                    keyword_scores.append(0.6)

        if keyword_scores:
            avg_kw_score = sum(keyword_scores) / len(keyword_scores)
            keyword_density_score = min(20, int(avg_kw_score * 20))
        else:
            keyword_density_score = 0
            issues.append("缺少搜索查询")

        score += keyword_density_score

        if keyword_density_score < 12:
            suggestions.append("建议优化搜索查询：使用自然语言短语，包含具体实体名称")
        
        # 4. 任务相关性检查 (20分) - v7.265 新增
        # 检查搜索任务是否与用户问题中的关键实体相关
        user_profile = analysis_data.get("user_profile", {})
        original_query = user_profile.get("explicit_need", "") or analysis_data.get("original_query", "")
        core_question = search_framework.get("core_question", "")
        
        relevance_score = 0
        irrelevant_tasks = []
        
        # 从用户问题和核心问题中提取关键实体
        query_text = (original_query + " " + core_question).lower()
        
        # 检查每个任务的相关性
        for t in targets:
            task_text = (
                (t.get("question", "") or "") + " " +
                (t.get("search_for", "") or "") + " " +
                " ".join(t.get("preset_keywords", []))
            ).lower()
            
            # 计算与用户问题的关键词重叠度
            query_words = set(re.findall(r'[\u4e00-\u9fa5]{2,}|[a-zA-Z]{3,}', query_text))
            task_words = set(re.findall(r'[\u4e00-\u9fa5]{2,}|[a-zA-Z]{3,}', task_text))
            
            if query_words:
                overlap = len(query_words & task_words)
                overlap_ratio = overlap / len(query_words)
                
                if overlap_ratio >= 0.2:  # 至少20%的关键词重叠
                    relevance_score += 5
                elif overlap == 0:  # 完全不相关
                    task_name = t.get("question", "") or t.get("search_for", "")[:30]
                    irrelevant_tasks.append(task_name[:30])
        
        relevance_score = min(20, relevance_score)
        score += relevance_score
        
        if irrelevant_tasks:
            issues.append(f"部分任务与用户问题弱相关：{', '.join(irrelevant_tasks[:2])}")
            suggestions.append("确保每个搜索任务都包含用户问题中的关键实体")
        
        if relevance_score < 10:
            issues.append("任务与用户问题相关性不足")
            suggestions.append("重新审视搜索任务是否直接服务于回答用户问题")
        
        # 5. 张力可操作性 (10分) - v7.265 调整权重
        l3_tension = analysis.get("l3_tension", {})
        if isinstance(l3_tension, dict):
            tension_formula = l3_tension.get("formula", "")
            tension_strategy = l3_tension.get("resolution_strategy", "")
        else:
            tension_formula = str(l3_tension)
            tension_strategy = ""
        
        has_vs = "vs" in tension_formula.lower() or "与" in tension_formula
        has_strategy = bool(tension_strategy) or any(
            w in str(analysis_data) for w in ["策略", "手法", "融合", "建议", "resolution"]
        )
        
        tension_score = (5 if has_vs else 0) + (5 if has_strategy else 0)
        score += tension_score
        
        if not has_vs:
            issues.append("L3张力未明确对立面结构（缺少 'A vs B' 格式）")
            suggestions.append("明确核心张力公式，如 '[品牌现代感] vs [在地传统感]'")
        if not has_strategy:
            issues.append("缺少张力解决策略")
            suggestions.append("补充具体的设计融合策略")
        
        # 6. 锐度三问 (10分) - 基于L5输出检测
        l5 = analysis.get("l5_sharpness", {})
        sharpness_score = 0
        
        if isinstance(l5, dict):
            if l5.get("specificity") and len(str(l5.get("specificity"))) > 10:
                sharpness_score += 4
            if l5.get("actionability") and len(str(l5.get("actionability"))) > 10:
                sharpness_score += 3
            if l5.get("depth") and len(str(l5.get("depth"))) > 10:
                sharpness_score += 3
        
        score += sharpness_score
        
        if sharpness_score < 7:
            issues.append("L5锐度自检不完整")
        
        # 确定等级和是否通过
        grade = "A" if score >= 75 else "B" if score >= 55 else "C"
        passed = score >= 55
        
        logger.info(f"📊 [v7.234] 质量评估完成 | score={score}/100 | grade={grade} | issues={len(issues)}")
        
        return {
            "score": score,
            "max_score": 100,
            "pass": passed,
            "grade": grade,
            "issues": issues,
            "suggestions": suggestions,
            "breakdown": {
                "entity_coverage": entity_coverage_score,
                "entity_specificity": specificity_score,
                "keyword_density": keyword_density_score,
                "task_relevance": relevance_score,  # v7.265 新增
                "tension_actionability": tension_score,
                "sharpness": sharpness_score,
            }
        }

    def _merge_analysis_data(self, original: Dict[str, Any], supplement: Dict[str, Any]) -> Dict[str, Any]:
        """
        合并优化后的分析数据 - v7.234
        
        将补充内容合并到原始数据中
        """
        import copy
        merged = copy.deepcopy(original)
        
        # 合并 analysis 部分
        if "analysis" in supplement:
            if "analysis" not in merged:
                merged["analysis"] = {}
            
            supp_analysis = supplement["analysis"]
            
            # 合并 l1_facts
            if "l1_facts" in supp_analysis:
                if isinstance(supp_analysis["l1_facts"], dict) and isinstance(merged["analysis"].get("l1_facts"), dict):
                    for key, value in supp_analysis["l1_facts"].items():
                        if key not in merged["analysis"]["l1_facts"] or not merged["analysis"]["l1_facts"][key]:
                            merged["analysis"]["l1_facts"][key] = value
                        elif isinstance(value, list) and isinstance(merged["analysis"]["l1_facts"][key], list):
                            merged["analysis"]["l1_facts"][key].extend(value)
                else:
                    merged["analysis"]["l1_facts"] = supp_analysis["l1_facts"]
            
            # 合并 l3_tension
            if "l3_tension" in supp_analysis:
                if isinstance(supp_analysis["l3_tension"], dict):
                    if not isinstance(merged["analysis"].get("l3_tension"), dict):
                        merged["analysis"]["l3_tension"] = {}
                    merged["analysis"]["l3_tension"].update(supp_analysis["l3_tension"])
                else:
                    merged["analysis"]["l3_tension"] = supp_analysis["l3_tension"]
        
        # 合并 search_framework 部分
        if "search_framework" in supplement:
            if "search_framework" not in merged:
                merged["search_framework"] = {}
            
            supp_framework = supplement["search_framework"]
            
            # 合并 targets 的 preset_keywords
            if "targets" in supp_framework:
                orig_targets = {t["id"]: t for t in merged["search_framework"].get("targets", [])}
                for supp_target in supp_framework["targets"]:
                    target_id = supp_target.get("id")
                    if target_id in orig_targets:
                        # 合并关键词
                        if "preset_keywords" in supp_target:
                            existing_kws = orig_targets[target_id].get("preset_keywords", [])
                            new_kws = supp_target["preset_keywords"]
                            orig_targets[target_id]["preset_keywords"] = existing_kws + [
                                kw for kw in new_kws if kw not in existing_kws
                            ]
                    else:
                        # v7.234: 如果原始数据中没有这个target，直接添加
                        orig_targets[target_id] = supp_target
                
                merged["search_framework"]["targets"] = list(orig_targets.values())
                
                # v7.234: 如果合并后targets仍为空，保留原始targets
                if not merged["search_framework"]["targets"] and merged["search_framework"].get("targets"):
                    pass  # 保持原样
        
        return merged

    async def _refine_analysis_v234(
        self,
        query: str,
        original_data: Dict[str, Any],
        quality_result: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        轻量级优化 - v7.234
        
        设计原则：
        1. 最多1次迭代（成本控制）
        2. 使用chat模型而非reasoning模型
        3. 只针对top3问题进行优化
        4. 失败不阻塞，记录警告继续执行
        """
        if quality_result["pass"]:
            return original_data, quality_result
        
        logger.info(f"🔄 [v7.234] 开始分析优化 | 当前分数={quality_result['score']} | 问题数={len(quality_result['issues'])}")
        
        # 只取top3问题
        top_issues = quality_result["issues"][:3]
        top_suggestions = quality_result["suggestions"][:3]
        
        # 提取原始分析的关键部分
        analysis_excerpt = {
            "l1_facts": original_data.get("analysis", {}).get("l1_facts", {}),
            "l3_tension": original_data.get("analysis", {}).get("l3_tension", {}),
        }
        
        # 提取原始搜索目标
        original_targets = original_data.get("search_framework", {}).get("targets", [])
        targets_excerpt = [
            {"id": t.get("id"), "name": t.get("name"), "preset_keywords": t.get("preset_keywords", [])}
            for t in original_targets[:3]
        ]
        
        refinement_prompt = f"""请针对以下问题优化分析结果。

## 原始问题
{query}

## 发现的问题
{chr(10).join(f"- {issue}" for issue in top_issues)}

## 优化建议
{chr(10).join(f"- {s}" for s in top_suggestions)}

## 原始分析（节选）
L1实体: {json.dumps(analysis_excerpt["l1_facts"], ensure_ascii=False)[:800]}
L3张力: {json.dumps(analysis_excerpt["l3_tension"], ensure_ascii=False)[:300]}
搜索目标: {json.dumps(targets_excerpt, ensure_ascii=False)[:500]}

## 优化要求

请只输出需要**补充**的内容（JSON格式），格式如下：

```json
{{
    "analysis": {{
        "l1_facts": {{
            "brand_entities": [...],
            "location_entities": [...],
            "competitor_entities": [...]
        }},
        "l3_tension": {{
            "formula": "[A] vs [B]",
            "resolution_strategy": "..."
        }}
    }},
    "search_framework": {{
        "targets": [
            {{
                "id": "T1",
                "preset_keywords": ["优化后的搜索查询（自然语言短语）"]
            }}
        ]
    }}
}}
```

重点：
1. 补充具体实体名称（品牌产品线、设计师、竞品案例）
2. 优化搜索查询：使用自然语言短语，包含具体实体名称
3. 明确张力公式和解决策略

请只输出JSON，不要其他内容。"""

        try:
            # 使用chat模型而非reasoning模型，成本更低
            result = await self._call_deepseek(
                refinement_prompt,
                model="deepseek-chat",  # 非reasoning模型
                max_tokens=1500
            )
            
            supplement = self._safe_parse_json(result, context="优化补充(v7.234)")
            
            if supplement:
                # 合并补充内容到原始数据
                merged = self._merge_analysis_data(original_data, supplement)
                new_quality = self._evaluate_analysis_quality_v234(merged)
                
                logger.info(f"✅ [v7.234] 优化完成 | {quality_result['score']}→{new_quality['score']} | 等级={new_quality['grade']}")
                return merged, new_quality
            else:
                logger.warning("⚠️ [v7.234] 优化结果解析失败，使用原始分析")
                
        except Exception as e:
            logger.warning(f"⚠️ [v7.234] 优化失败，继续使用原始分析 | error={e}")
        
        return original_data, quality_result

    # ==================== v7.234 质量评估与优化 结束 ====================

    
    def _parse_search_master_line(self, data: Dict[str, Any]) -> Optional[SearchMasterLine]:
        """
        解析搜索主线数据 - v7.213 增强
        
        将 LLM 输出的 search_master_line JSON 转换为 SearchMasterLine 对象
        v7.213: 支持阶段、依赖、验证标准、检查点等新字段
        """
        if not data:
            return None
        
        try:
            tasks = []
            for task_data in data.get("search_tasks", []):
                task = SearchTask(
                    id=task_data.get("id", f"T{len(tasks)+1}"),
                    task=task_data.get("task", ""),
                    purpose=task_data.get("purpose", ""),
                    priority=task_data.get("priority", 2),
                    expected_info=task_data.get("expected_info", []),
                    # v7.213 新增字段
                    phase=task_data.get("phase", ""),
                    depends_on=task_data.get("depends_on", []),
                    validation_criteria=task_data.get("validation_criteria", []),
                )
                tasks.append(task)
            
            # v7.213: 解析检查点，默认为 [2, 4, 6]
            checkpoint_rounds = data.get("checkpoint_rounds", [2, 4, 6])
            
            return SearchMasterLine(
                core_question=data.get("core_question", ""),
                boundary=data.get("boundary", ""),
                # v7.213 新增
                framework_summary=data.get("framework_summary", ""),
                search_phases=data.get("search_phases", ["基础信息", "深度案例", "对比验证"]),
                checkpoint_rounds=checkpoint_rounds,
                # 原有字段
                search_tasks=tasks,
                exploration_triggers=data.get("exploration_triggers", []),
                forbidden_zones=data.get("forbidden_zones", []),
            )
        except Exception as e:
            logger.warning(f"⚠️ [v7.213] 解析搜索主线失败: {e}")
            return None

    # ==================== L0 结构化信息提取 (v7.206 - 保留用于兼容) ====================

    def _build_l0_dialogue_prompt(self, query: str) -> str:
        """
        构建 L0 对话式分析 Prompt - v7.206
        像专家与用户交流一样，分析用户输入并以自然语言输出
        """
        return f"""你是一位专业的需求分析师，正在与用户进行友好的对话。请仔细分析用户的输入，像和用户聊天一样，分享你从输入中发现的信息和洞察。

## 用户输入
{query}

## 你的任务
用自然、友好、专业的语言，向用户展示你对他们需求的理解。按以下结构组织你的分析：

### 分析要点（请全部覆盖，但语言要自然连贯）

1. **用户画像识别**
   - 识别地理位置，分析该地点的气候、文化、生活方式特点
   - 识别年龄、性别、职业、教育背景等
   - 提取身份标签（如独立女性、海归、不婚主义等）

2. **项目/场景理解**
   - 识别项目类型和规模
   - 分析该规模带来的设计可能性

3. **偏好与风格分析**
   - 识别用户提到的风格参照（人物、作品、品牌等）
   - 从参照中推导风格关键词、色彩偏好、材质偏好
   - 例如：Audrey Hepburn → 经典优雅、简约、黑白灰、法式细节

4. **隐性需求推断**（重要！）
   基于用户的身份标签和背景，推断他们可能需要但没有明说的需求：
   - 英国海归 → 可能偏好：英式收纳、书房、茶室、高品质音响
   - 不婚主义 → 可能需要：个人衣帽间/SPA室、开放式社交空间、工作与生活分区
   - 深圳南山 → 需要考虑：遮阳隔热、通风设计、现代都市氛围

5. **地点特殊考量**
   如果有地点信息，分析该地点对项目的具体影响

## 输出格式要求
- 使用自然的段落形式，不要用列表符号
- 语气亲切专业，像在和用户交谈
- 重点信息可以用**加粗**标注
- 每个分析要点之间空一行
- 结尾用一句话总结你对用户核心需求的理解

## 示例风格
"我注意到您是位于**深圳南山**的用户。这是一个现代化的都市区域，夏季炎热潮湿，在设计上需要特别关注通风和遮阳..."

请直接开始你的分析，不要有任何前缀或标题。"""

    def _build_l0_json_extraction_prompt(self, query: str, dialogue_content: str) -> str:
        """
        构建 L0 JSON提取 Prompt - v7.206
        基于对话内容提取结构化JSON（内部使用，不展示给用户）
        """
        return f"""基于以下用户输入和分析内容，提取结构化的JSON数据。

## 用户原始输入
{query}

## 分析内容参考
{dialogue_content}

## 输出要求
请提取以下结构的JSON，确保与分析内容一致：

```json
{{
  "demographics": {{
    "location": "",
    "location_context": "",
    "age": "",
    "age_context": "",
    "gender": "",
    "occupation": "",
    "occupation_context": "",
    "education": "",
    "education_context": ""
  }},
  "identity_tags": [],
  "lifestyle": {{
    "living_situation": "",
    "family_status": "",
    "hobbies": [],
    "pets": []
  }},
  "project_context": {{
    "type": "",
    "scale": "",
    "scale_context": "",
    "constraints": [],
    "budget_range": "",
    "timeline": ""
  }},
  "preferences": {{
    "style_references": [],
    "style_keywords": [],
    "color_palette": [],
    "material_preferences": [],
    "cultural_influences": []
  }},
  "core_request": {{
    "explicit_need": "",
    "implicit_needs": []
  }},
  "location_considerations": {{
    "climate": "",
    "architecture": "",
    "lifestyle": ""
  }},
  "completeness": {{
    "provided_dimensions": [],
    "missing_dimensions": [],
    "confidence_score": 0.0
  }}
}}
```

请只输出JSON，不要有其他内容。"""

    def _build_l0_extraction_prompt(self, query: str) -> str:
        """
        构建 L0 结构化信息提取 Prompt - v7.205 (保留用于兼容)
        """
        return f"""你是一位信息提取专家。请从用户输入中提取结构化信息，并进行深度推断。

## 用户输入
{query}

## 提取要求

### 1. 用户基础画像 (demographics)
不仅提取字面信息，还要补充语境分析：
- location: 地理位置
- location_context: 该地点的特点（气候、文化、生活方式）
- age: 年龄
- age_context: 年龄阶段特点
- gender: 性别
- occupation: 职业
- occupation_context: 职业特点和需求
- education: 教育背景
- education_context: 该背景可能带来的审美/生活偏好

### 2. 身份标签 (identity_tags)
提取所有身份描述词，如：独立女性、不婚主义、创业者等

### 3. 生活方式 (lifestyle)
- living_situation: 居住情况
- family_status: 家庭状态
- hobbies: 爱好
- pets: 宠物

### 4. 项目/场景信息 (project_context)
- type: 项目类型（室内设计、产品咨询等）
- scale: 规模/面积
- scale_context: 该规模的设计可能性
- constraints: 约束条件
- budget_range: 预算范围（如有）
- timeline: 时间线（如有）

### 5. 偏好与参照 (preferences)
- style_references: 风格参照人物/作品
- style_keywords: 从参照中推断的风格关键词
- color_palette: 推断的色彩偏好
- material_preferences: 推断的材质偏好
- cultural_influences: 文化影响

### 6. 核心诉求 (core_request)
- explicit_need: 用户明确要求的是什么
- implicit_needs: 从身份标签、背景、偏好中推断的隐含需求（重要！）

### 7. 地点特殊考量 (location_considerations)
如果有地点信息，分析该地点对项目的影响：
- climate: 气候因素
- architecture: 建筑特点
- lifestyle: 生活方式

## 推断规则示例
- "英国海归" → 可能偏好：英式管家式收纳、书房、茶室、高品质音响
- "不婚主义" → 可能需要：个人衣帽间/SPA室、大型开放式公共空间、工作与生活平衡
- "深圳南山" → 需要考虑：遮阳隔热、高层观景、现代都市氛围
- "Audrey Hepburn" → 风格关键词：经典优雅、简约、黑白灰、法式/英式、复古细节
- "程序员" → 可能需要：人体工学办公区、多屏幕支架、良好的网络布线
- "有宠物" → 可能需要：耐磨地板、宠物活动区、易清洁材质
- "30-40岁" → 事业上升期，注重品质和效率

## 输出格式（JSON）
```json
{{
  "demographics": {{
    "location": "",
    "location_context": "",
    "age": "",
    "age_context": "",
    "gender": "",
    "occupation": "",
    "occupation_context": "",
    "education": "",
    "education_context": ""
  }},
  "identity_tags": [],
  "lifestyle": {{
    "living_situation": "",
    "family_status": "",
    "hobbies": [],
    "pets": []
  }},
  "project_context": {{
    "type": "",
    "scale": "",
    "scale_context": "",
    "constraints": [],
    "budget_range": "",
    "timeline": ""
  }},
  "preferences": {{
    "style_references": [],
    "style_keywords": [],
    "color_palette": [],
    "material_preferences": [],
    "cultural_influences": []
  }},
  "core_request": {{
    "explicit_need": "",
    "implicit_needs": []
  }},
  "location_considerations": {{
    "climate": "",
    "architecture": "",
    "lifestyle": ""
  }},
  "completeness": {{
    "provided_dimensions": [],
    "missing_dimensions": [],
    "confidence_score": 0.0
  }}
}}
```

请只输出JSON，不要有其他内容。"""

    async def _extract_structured_info_stream(
        self,
        query: str,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        L0: 对话式结构化信息提取 - v7.206
        
        双输出模式：
        - Step A: 对话式分析（流式输出给用户看）
        - Step B: JSON提取（静默执行，系统内部使用）
        """
        logger.info(f"🔍 [L0 v7.206] 开始对话式信息提取 | query={query[:50]}...")

        dialogue_content = ""
        
        try:
            # ==================== Step A: 对话式分析（流式，给用户看）====================
            dialogue_prompt = self._build_l0_dialogue_prompt(query)
            
            async for chunk in self._call_openrouter_stream(
                dialogue_prompt,
                model="openai/gpt-4o-mini",
                max_tokens=1500
            ):
                content = chunk.get("content", "")
                dialogue_content += content
                # 流式推送对话内容给前端
                yield {
                    "type": "l0_dialogue_chunk",
                    "content": content,
                }
            
            # 对话完成
            yield {
                "type": "l0_dialogue_complete",
                "content": dialogue_content,
            }
            
            logger.info(f"✅ [L0 v7.206] 对话式分析完成 | length={len(dialogue_content)}")
            
            # ==================== Step B: JSON提取（静默，系统内部用）====================
            json_prompt = self._build_l0_json_extraction_prompt(query, dialogue_content)
            json_content = ""
            
            # 非流式调用，不输出给前端
            async for chunk in self._call_openrouter_stream(
                json_prompt,
                model="openai/gpt-4o-mini",
                max_tokens=1000
            ):
                json_content += chunk.get("content", "")
            
            # 解析 JSON 结果
            data = self._safe_parse_json(json_content, context="L0结构化提取(JSON)")
            if data:
                structured_info = StructuredUserInfo(
                    demographics=data.get("demographics", {}),
                    identity_tags=data.get("identity_tags", []),
                    lifestyle=data.get("lifestyle", {}),
                    project_context=data.get("project_context", {}),
                    preferences=data.get("preferences", {}),
                    core_request=data.get("core_request", {}),
                    location_considerations=data.get("location_considerations", {}),
                    completeness=data.get("completeness", {}),
                    raw_extraction=dialogue_content,  # 保存对话内容用于调试
                )
                logger.info(f"✅ [L0 v7.206] JSON结构化完成 | {structured_info.get_summary()}")
                # 只发送完成信号，不发送JSON内容给前端
                yield {
                    "type": "l0_extraction_complete",
                    "data": structured_info.to_dict(),
                }
            else:
                # 解析失败，返回空结构
                logger.warning("⚠️ [L0 v7.206] JSON 解析失败，返回空结构")
                yield {
                    "type": "l0_extraction_complete",
                    "data": StructuredUserInfo().to_dict(),
                }

        except Exception as e:
            logger.warning(f"⚠️ [L0 v7.206] 结构化提取失败: {e}")
            # 如果已有对话内容，先发送对话完成
            if dialogue_content:
                yield {
                    "type": "l0_dialogue_complete",
                    "content": dialogue_content,
                }
            yield {
                "type": "l0_extraction_complete",
                "data": StructuredUserInfo().to_dict(),
            }

    async def _call_openrouter_stream(
        self,
        prompt: str,
        model: str = "openai/gpt-4o-mini",
        max_tokens: int = 1000,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        调用 OpenRouter API（流式）- v7.205
        """
        if not self.openai_api_key:
            logger.warning("⚠️ OpenRouter API Key 未配置")
            return

        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://intelligent-project-analyzer.com",
            "X-Title": "Intelligent Project Analyzer",
        }

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "stream": True,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.openai_base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                ) as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str.strip() == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                delta = data.get("choices", [{}])[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield {"content": content}
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            logger.error(f"❌ OpenRouter API 调用失败: {e}")

    # ==================== 问题分析 ====================
    
    async def _stream_analyze_question(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式分析用户问题 - v7.188
        让用户在问题分析阶段也能看到实时进度
        """
        prompt = self._build_analysis_prompt(query, context)
        full_reasoning = ""
        full_content = ""
        
        try:
            async for chunk in self._call_deepseek_stream_with_reasoning(prompt, model=self.thinking_model, max_tokens=1500):
                if chunk.get("type") == "reasoning":
                    reasoning_text = chunk.get("content", "")
                    full_reasoning += reasoning_text
                    yield {
                        "type": "analysis_chunk",
                        "content": reasoning_text,
                        "is_reasoning": True,
                    }
                elif chunk.get("type") == "content":
                    full_content += chunk.get("content", "")
            
            # v7.200: 使用统一 JSON 解析器
            data = self._safe_parse_json(full_content, context="流式问题分析")
            if data is None:
                raise ValueError("无法解析问题分析结果")
            
            framework = self._parse_analysis_result(data, query)
            
            yield {
                "type": "analysis_complete",
                "framework": framework,
            }
            
        except Exception as e:
            logger.warning(f"⚠️ 流式问题分析失败: {e}")
            yield {
                "type": "analysis_complete",
                "framework": self._build_simple_framework(query),
            }

    async def _stream_analyze_question_with_l0(
        self,
        query: str,
        structured_info: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式分析用户问题（注入 L0 结果）- v7.205
        在 L1-L5 分析中利用 L0 提取的结构化信息
        """
        prompt = self._build_analysis_prompt_with_l0(query, structured_info, context)
        full_reasoning = ""
        full_content = ""

        try:
            async for chunk in self._call_deepseek_stream_with_reasoning(prompt, model=self.thinking_model, max_tokens=1500):
                if chunk.get("type") == "reasoning":
                    reasoning_text = chunk.get("content", "")
                    full_reasoning += reasoning_text
                    yield {
                        "type": "analysis_chunk",
                        "content": reasoning_text,
                        "is_reasoning": True,
                    }
                elif chunk.get("type") == "content":
                    full_content += chunk.get("content", "")

            # v7.200: 使用统一 JSON 解析器
            data = self._safe_parse_json(full_content, context="流式问题分析(L0增强)")
            if data is None:
                raise ValueError("无法解析问题分析结果")

            framework = self._parse_analysis_result(data, query)

            yield {
                "type": "analysis_complete",
                "framework": framework,
            }

        except Exception as e:
            logger.warning(f"⚠️ 流式问题分析(L0增强)失败: {e}")
            yield {
                "type": "analysis_complete",
                "framework": self._build_simple_framework(query),
            }

    def _build_analysis_prompt_with_l0(
        self,
        query: str,
        structured_info: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        构建包含 L0 结构化信息的分析 prompt - v7.205
        """
        # 构建 L0 摘要
        l0_summary = ""
        if structured_info:
            demographics = structured_info.get("demographics", {})
            identity_tags = structured_info.get("identity_tags", [])
            preferences = structured_info.get("preferences", {})
            core_request = structured_info.get("core_request", {})
            location_considerations = structured_info.get("location_considerations", {})
            completeness = structured_info.get("completeness", {})

            l0_parts = []

            # 用户画像
            profile_parts = []
            if demographics.get("location"):
                loc_ctx = f"（{demographics.get('location_context')}）" if demographics.get('location_context') else ""
                profile_parts.append(f"- 地点: {demographics['location']}{loc_ctx}")
            if demographics.get("age"):
                age_ctx = f"（{demographics.get('age_context')}）" if demographics.get('age_context') else ""
                profile_parts.append(f"- 年龄: {demographics['age']}{age_ctx}")
            if demographics.get("gender"):
                profile_parts.append(f"- 性别: {demographics['gender']}")
            if demographics.get("education"):
                edu_ctx = f"（{demographics.get('education_context')}）" if demographics.get('education_context') else ""
                profile_parts.append(f"- 教育背景: {demographics['education']}{edu_ctx}")
            if demographics.get("occupation"):
                occ_ctx = f"（{demographics.get('occupation_context')}）" if demographics.get('occupation_context') else ""
                profile_parts.append(f"- 职业: {demographics['occupation']}{occ_ctx}")
            if identity_tags:
                profile_parts.append(f"- 身份标签: {', '.join(identity_tags)}")

            if profile_parts:
                l0_parts.append("### 用户画像\n" + "\n".join(profile_parts))

            # 项目信息
            project_context = structured_info.get("project_context", {})
            project_parts = []
            if project_context.get("type"):
                project_parts.append(f"- 类型: {project_context['type']}")
            if project_context.get("scale"):
                scale_ctx = f"（{project_context.get('scale_context')}）" if project_context.get('scale_context') else ""
                project_parts.append(f"- 规模: {project_context['scale']}{scale_ctx}")

            if project_parts:
                l0_parts.append("### 项目信息\n" + "\n".join(project_parts))

            # 偏好参照
            pref_parts = []
            if preferences.get("style_references"):
                pref_parts.append(f"- 风格参照: {', '.join(preferences['style_references'])}")
            if preferences.get("style_keywords"):
                pref_parts.append(f"- 风格关键词: {', '.join(preferences['style_keywords'])}")
            if preferences.get("color_palette"):
                pref_parts.append(f"- 色彩偏好: {', '.join(preferences['color_palette'][:6])}")
            if preferences.get("material_preferences"):
                pref_parts.append(f"- 材质偏好: {', '.join(preferences['material_preferences'][:5])}")

            if pref_parts:
                l0_parts.append("### 偏好参照\n" + "\n".join(pref_parts))

            # 核心诉求
            request_parts = []
            if core_request.get("explicit_need"):
                request_parts.append(f"- 显性需求: {core_request['explicit_need']}")
            if core_request.get("implicit_needs"):
                request_parts.append(f"- 隐性需求（推断）: {', '.join(core_request['implicit_needs'])}")

            if request_parts:
                l0_parts.append("### 核心诉求\n" + "\n".join(request_parts))

            # 地点考量
            loc_parts = []
            if location_considerations.get("climate"):
                loc_parts.append(f"- 气候: {location_considerations['climate']}")
            if location_considerations.get("architecture"):
                loc_parts.append(f"- 建筑: {location_considerations['architecture']}")
            if location_considerations.get("lifestyle"):
                loc_parts.append(f"- 生活方式: {location_considerations['lifestyle']}")

            if loc_parts:
                l0_parts.append("### 地点考量\n" + "\n".join(loc_parts))

            # 信息完整度
            if completeness:
                conf_score = completeness.get("confidence_score", 0)
                missing = completeness.get("missing_dimensions", [])
                l0_parts.append(f"### 信息完整度\n- 置信度: {conf_score:.0%}\n- 缺失维度: {', '.join(missing) if missing else '无'}")

            if l0_parts:
                l0_summary = "## L0 结构化信息提取结果（已完成）\n\n" + "\n\n".join(l0_parts) + "\n\n---\n\n"

        # 获取原始 prompt 并注入 L0 结果
        original_prompt = self._build_analysis_prompt(query, context)

        if l0_summary:
            # 在原始 prompt 的开头注入 L0 结果
            return f"""{l0_summary}基于以上 L0 结构化信息，请进行 L1-L5 深度分析。注意：
1. L0 已经提取了用户画像和隐性需求，请在 L1 解构时直接利用这些信息
2. L0 推断的隐性需求应该被纳入关键信息面的设计中
3. 地点考量应该影响搜索策略和建议方向

{original_prompt}"""
        else:
            return original_prompt

    def _build_analysis_prompt(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        构建问题分析prompt - v7.196 融合需求分析方法论

        升级内容：
        - 从三步分析法升级为 L1-L5 五层分析框架
        - 新增人性维度分析（条件触发）
        - 新增专家接口构建
        """
        # 检测是否需要启用人性维度分析
        human_dimension_triggers = [
            "设计", "装修", "空间", "生活", "家", "居住",
            "体验", "感受", "氛围", "风格", "冥想", "休息",
            "舒适", "温馨", "私密", "放松", "卧室", "客厅"
        ]
        enable_human_dimensions = any(trigger in query for trigger in human_dimension_triggers)

        human_dimensions_section = ""
        human_dimensions_output = ""
        if enable_human_dimensions:
            human_dimensions_section = """
## 人性维度分析（本问题涉及设计/生活/体验，请启用）

请分析以下5个人性维度：
1. **emotional_landscape（情绪地图）**: 用户当前情绪状态和期望的情绪转化
   - 示例："从进门时的都市压力 → 玄关放下包袱的仪式感 → 客厅的社交安全感"
2. **spiritual_aspirations（精神追求）**: 穿透功能需求的精神层面渴望
   - 示例："通过空间建立'慢生活'的仪式感"
3. **psychological_safety_needs（心理安全需求）**: 用户在对抗什么恐惧或不确定性
   - 示例："需要一个绝对不被打扰的角落（对抗职场失控感）"
4. **ritual_behaviors（仪式行为）**: 问题背后涉及的日常仪式或习惯
   - 示例："每天晨间的手冲咖啡（需要专属吧台+自然光）"
5. **memory_anchors（记忆锚点）**: 影响用户期望的情感记忆或过往经验
   - 示例："祖母的瓷器收藏（需要展示空间）"

⚠️ 禁止使用空洞词汇（"温馨"、"舒适"等），必须具体到用户的独特情境。
"""
            human_dimensions_output = """
    "human_dimensions": {{{{
        "enabled": true,
        "emotional_landscape": "具体的情绪转化路径",
        "spiritual_aspirations": "具体的精神追求",
        "psychological_safety_needs": "具体的心理安全需求",
        "ritual_behaviors": "具体的仪式行为",
        "memory_anchors": "具体的记忆锚点"
    }}}},"""
        else:
            human_dimensions_output = """
    "human_dimensions": {{{{
        "enabled": false
    }}}},"""

        context_str = json.dumps(context or {}, ensure_ascii=False, indent=2)

        return f"""你是一位资深的问题分析专家。请对用户问题进行深度分析。

## 用户问题
{query}

## 上下文
{context_str}

## L1-L5 分析流程

### L1: 解构 - 将问题分解为第一性原理事实原子 (MECE原则)
- 用户是谁？（身份、角色、背景）
- 要什么？（显性需求）
- 为什么？（隐性动机）
- 约束是什么？（时间、资源、能力）

### L2: 建模 - 构建用户系统模型（v7.265 增强：12维动机分析）

请从以下12个动机维度逐一分析用户需求的相关性（0-5分，0=完全不相关，5=核心相关）：

**P0 核心维度（必须分析）**：
1. **文化认同(cultural)**: 是否涉及传统文化、地域特色、民族符号、精神传承？
2. **商业价值(commercial)**: 是否涉及ROI、坪效、运营效率、竞争策略？
3. **健康疗愈(wellness)**: 是否涉及物理健康、心理疗愈、医疗标准、安全环境？

**P1 趋势维度（按需分析）**：
4. **技术创新(technical)**: 是否涉及智能化、工程技术、未来体验、系统集成？
5. **可持续价值(sustainable)**: 是否涉及环保、社会责任、可持续发展？

**P2 专业维度（按需分析）**：
6. **专业职能(professional)**: 是否涉及行业标准、专业设备、职业形象？
7. **包容性(inclusive)**: 是否涉及无障碍设计、特殊人群、尊严平等？

**BASELINE 基础维度（必须分析）**：
8. **功能性(functional)**: 空间功能、实用性、基础需求满足
9. **情感性(emotional)**: 情感体验、氛围营造、心理感受
10. **审美(aesthetic)**: 视觉美感、艺术表达、风格呈现
11. **社交(social)**: 人际互动、社群关系、交流空间

**输出要求**：
- 主导动机（1-2个，得分≥4）：这是搜索的核心方向
- 次要动机（2-3个，得分2-3）：需要兼顾的维度
- 核心张力：主导动机之间的对立或融合关系

### L3: 识别杠杆点 - 寻找最尖锐对立面
- 基于L2识别的主导动机，找出它们之间的核心张力
- 输出：核心张力公式（使用动机类型表达）
- 示例："北欧极简美学(aesthetic) vs 峨眉山在地文化(cultural)"

### L4: JTBD定义 - "用户雇佣搜索完成什么任务？"
- 公式：为[用户身份]提供[信息类型]，帮助完成[任务1]与[任务2]

### L5: 锐度测试 - 验证分析质量
- 专一性：这个分析是否只适用于此用户/此问题？
- 可操作性：能否直接指导搜索策略？
- 深度：是否超越了表面需求？
{human_dimensions_section}
## 关键信息面识别（v7.265 增强：基于动机类型的覆盖检查）

要完整回答这个问题，需要收集哪些信息？

### 数量要求（v7.264 强制）
- **信息面数量：5-8个**（要充分覆盖问题的各个维度）
- 每个信息面必须分解为2-4个具体的子任务
- 按重要性排序（5=必需，4=重要，3=有帮助）

### 覆盖维度检查清单（v7.265 基于动机类型）

请确保搜索任务覆盖L2分析中识别的动机维度：

**主导动机（必须有专门的搜索任务）**：
- 每个主导动机至少对应1-2个搜索任务
- 示例：如果aesthetic是主导动机，需要有"HAY品牌设计语言研究"

**次要动机（建议有相关搜索任务）**：
- 每个次要动机至少对应1个搜索任务

**交叉融合（核心张力解决）**：
- 必须有1-2个搜索任务专门研究主导动机之间的融合案例
- 示例："北欧极简与在地文化融合的民宿案例"

### 搜索任务命名规范（v7.264 强制）

❌ **禁止以下格式**：
- 关键词堆砌："HAY Mags沙发 About A Chair 民宿室内设计案例"
- 抽象问题："如何解决核心设计张力？"
- 模糊描述："相关案例研究"

✅ **要求**：
- **name 字段**：必须是可理解的自然语言短语（5-15字）
  - 格式：[研究对象] + [研究目的/角度]
  - 示例："HAY品牌设计语言研究"、"峨眉山气候与建筑特点"、"北欧民宿案例分析"
- **question 字段**：必须是问句形式，以"？"结尾
  - 示例："HAY品牌的核心设计理念是什么？"
- **search_for 字段**：具体的搜索关键词（可以是关键词组合）
  - 示例："HAY design philosophy minimalist Scandinavian"
- **why_need 字段**：说明这个搜索对回答问题的贡献
  - 示例："为民宿设计提供风格参照基础"
- **motivation_tag 字段**：标注该任务对应的动机类型
  - 示例："aesthetic" 或 "cultural"

### 子任务要求（v7.260 全局并行策略）
1. **搜索引导词**（强制）：每个子任务必须以搜索行为动词开头
   - 搜索/查找/调研/检索/收集（研究类）
   - 对比/分析/评估/整理（分析类）
   - 验证/查证/确认（验证类）
2. **具体化**：包含具体的搜索目标（品牌名、案例名、数据类型）
3. **依赖关系**：默认所有子任务可并行执行（dependencies为空），仅当存在明确的信息依赖时才标记

## 专家接口构建

为后续处理提供：
1. **critical_questions** - 需要深入探索的关键问题
2. **challenge_points** - 可能存在的挑战或矛盾点
3. **divergence_permission** - 授权后续处理挑战分析结论

## 输出格式（JSON）
```json
{{{{
    "analysis_layers": {{{{
        "L1_facts": ["事实1: 用户是...", "事实2: 要...", "事实3: 因为..."],
        "L2_motivation_analysis": {{{{
            "primary": [
                {{{{"id": "aesthetic", "score": 5, "reason": "HAY品牌气质是核心设计参照"}}}},
                {{{{"id": "cultural", "score": 4, "reason": "峨眉山地域文化需要融入"}}}}
            ],
            "secondary": [
                {{{{"id": "functional", "score": 3, "reason": "民宿基础功能需求"}}}},
                {{{{"id": "emotional", "score": 3, "reason": "度假放松的情感体验"}}}}
            ],
            "all_scores": {{{{
                "cultural": 4, "commercial": 2, "wellness": 1, "technical": 1,
                "sustainable": 2, "professional": 1, "inclusive": 1,
                "functional": 3, "emotional": 3, "aesthetic": 5, "social": 2
            }}}}
        }}}},
        "L3_core_tension": "北欧极简美学(aesthetic) vs 峨眉山在地文化(cultural)",
        "L4_search_task": "为[用户身份]提供[信息类型]，帮助完成[任务]",
        "L5_sharpness": {{{{
            "score": 75,
            "specificity": "高/中/低",
            "actionability": "高/中/低",
            "depth": "高/中/低"
        }}}}
    }}}},{human_dimensions_output}
    "macro_overview": {{{{
        "domains": ["涉及的领域1", "领域2"],
        "essence": "问题的本质诉求（一句话）",
        "hidden_needs": ["隐含需求1", "隐含需求2"]
    }}}},
    "entry_point": {{{{
        "core_insight": "核心切入点洞察",
        "approach_angle": "建议的切入角度",
        "key_concepts": ["关键概念1", "关键概念2"]
    }}}},
    "answer_goal": "用户期望的答案是...",
    "key_aspects": [
        {{{{
            "name": "HAY品牌设计语言研究",
            "goal": "理解HAY的核心设计哲学和标志性元素",
            "importance": 5,
            "search_hint": "HAY官网、设计媒体、设计师访谈",
            "sub_tasks": [
                {{{{
                    "task_id": "T1.1",
                    "search_action": "搜索",
                    "question": "HAY品牌的核心设计理念是什么？",
                    "search_for": "HAY design philosophy brand identity minimalist",
                    "why_need": "为民宿设计提供风格参照基础",
                    "dependencies": [],
                    "can_parallel": true
                }}}}
            ]
        }}}}
    ],
    "expert_handoff": {{{{
        "critical_questions": ["关键问题1", "关键问题2"],
        "challenge_points": ["挑战点1"],
        "divergence_permission": "授权后续处理挑战分析结论"
    }}}}
}}}}
```

请只输出JSON。"""

    def _parse_analysis_result(self, data: Dict[str, Any], query: str) -> AnswerFramework:
        """
        解析分析结果为 AnswerFramework - v7.196 支持 L1-L5 和人性维度

        升级内容：
        - 解析 L1-L5 分析层结果
        - 解析人性维度分析（如果启用）
        - 解析专家接口
        - 保持向后兼容（macro_overview, entry_point）
        """
        # 提取 L1-L5 分析层
        analysis_layers = data.get("analysis_layers", {})
        human_dims = data.get("human_dimensions", {})
        expert_handoff = data.get("expert_handoff", {})

        # 保持向后兼容
        macro = data.get("macro_overview", {})
        entry = data.get("entry_point", {})

        framework = AnswerFramework(
            original_query=query,
            answer_goal=data.get("answer_goal", ""),
            created_at=time.time(),
        )

        # ==================== 存储 L1-L5 分析结果 ====================
        if analysis_layers:
            framework.collected_evidence["_L1_facts"] = analysis_layers.get("L1_facts", [])

            l2_model = analysis_layers.get("L2_user_model", {})
            framework.collected_evidence["_L2_user_model"] = [
                f"心理: {l2_model.get('psychological', '')}",
                f"社会: {l2_model.get('sociological', '')}",
                f"美学: {l2_model.get('aesthetic', '')}",
            ]

            framework.collected_evidence["_L3_core_tension"] = [
                analysis_layers.get("L3_core_tension", "")
            ]

            framework.collected_evidence["_L4_search_task"] = [
                analysis_layers.get("L4_search_task", "")
            ]

            l5_sharpness = analysis_layers.get("L5_sharpness", {})
            framework.collected_evidence["_L5_sharpness"] = [
                f"锐度评分: {l5_sharpness.get('score', 0)}",
                f"专一性: {l5_sharpness.get('specificity', '中')}",
                f"可操作性: {l5_sharpness.get('actionability', '中')}",
                f"深度: {l5_sharpness.get('depth', '中')}",
            ]

        # ==================== 存储人性维度（如果启用）====================
        if human_dims.get("enabled"):
            framework.collected_evidence["_human_dimensions"] = [
                f"情绪地图: {human_dims.get('emotional_landscape', '')}",
                f"精神追求: {human_dims.get('spiritual_aspirations', '')}",
                f"心理安全: {human_dims.get('psychological_safety_needs', '')}",
                f"仪式行为: {human_dims.get('ritual_behaviors', '')}",
                f"记忆锚点: {human_dims.get('memory_anchors', '')}",
            ]

        # ==================== 存储专家接口 ====================
        if expert_handoff and isinstance(expert_handoff, dict):
            framework.collected_evidence["_expert_handoff"] = [
                f"关键问题: {'; '.join(expert_handoff.get('critical_questions', []) if isinstance(expert_handoff.get('critical_questions'), list) else [])}",
                f"挑战点: {'; '.join(expert_handoff.get('challenge_points', []) if isinstance(expert_handoff.get('challenge_points'), list) else [])}",
                f"发散授权: {str(expert_handoff.get('divergence_permission', ''))}",
            ]

        # ==================== 保持向后兼容：宏观统筹和切入点 ====================
        if isinstance(macro, dict):
            framework.collected_evidence["_macro_overview"] = [
                f"涉及领域: {', '.join(macro.get('domains', []) if isinstance(macro.get('domains'), list) else [])}",
                f"本质诉求: {str(macro.get('essence', ''))}",
                f"隐含需求: {', '.join(macro.get('hidden_needs', []) if isinstance(macro.get('hidden_needs'), list) else [])}",
            ]
        if isinstance(entry, dict):
            framework.collected_evidence["_entry_point"] = [
                f"核心切入点: {str(entry.get('core_insight', ''))}",
                f"切入角度: {str(entry.get('approach_angle', ''))}",
                f"关键概念: {', '.join(entry.get('key_concepts', []) if isinstance(entry.get('key_concepts'), list) else [])}",
            ]

        # ==================== v7.215: 增强 key_aspects 解析鲁棒性 ====================
        raw_aspects = data.get("key_aspects", [])
        
        # v7.215: 添加诊断日志
        logger.debug(f"🔍 [Ucppt v7.215] key_aspects 原始数据类型: {type(raw_aspects)}, 内容预览: {str(raw_aspects)[:200]}")
        
        if not isinstance(raw_aspects, list):
            logger.warning(f"⚠️ [Ucppt v7.215] key_aspects 不是列表类型: {type(raw_aspects)}, 尝试转换")
            # 尝试从字典中提取
            if isinstance(raw_aspects, dict):
                # 可能是 {"items": [...]} 或 {"aspects": [...]} 格式
                for key in ["items", "aspects", "list", "data"]:
                    if key in raw_aspects and isinstance(raw_aspects[key], list):
                        raw_aspects = raw_aspects[key]
                        logger.info(f"✅ [Ucppt v7.215] 从 key_aspects.{key} 提取到列表")
                        break
                else:
                    raw_aspects = []
            elif isinstance(raw_aspects, str):
                # 尝试解析字符串为 JSON
                try:
                    parsed = json.loads(raw_aspects)
                    if isinstance(parsed, list):
                        raw_aspects = parsed
                        logger.info(f"✅ [Ucppt v7.215] 从字符串解析出列表")
                except:
                    raw_aspects = []
            else:
                raw_aspects = []
        
        # v7.215: 如果列表为空，记录完整的 data 结构
        if not raw_aspects:
            logger.warning(f"⚠️ [Ucppt v7.215] key_aspects 为空，data 结构预览: {list(data.keys()) if isinstance(data, dict) else type(data)}")
            
        for i, aspect_data in enumerate(raw_aspects):
            # 确保每个 aspect_data 是字典
            if not isinstance(aspect_data, dict):
                logger.warning(f"⚠️ [Ucppt v7.214] key_aspects[{i}] 不是字典类型，跳过")
                continue

            # 提取字段时进行类型检查
            name = str(aspect_data.get("name", "")) if aspect_data.get("name") else ""
            goal = str(aspect_data.get("goal", "")) if aspect_data.get("goal") else ""
            importance_raw = aspect_data.get("importance", 3)
            importance = int(importance_raw) if isinstance(importance_raw, (int, float)) else 3
            search_hint = str(aspect_data.get("search_hint", "")) if aspect_data.get("search_hint") else ""

            # v7.260: 提取子任务列表
            sub_tasks = aspect_data.get("sub_tasks", [])
            if not isinstance(sub_tasks, list):
                sub_tasks = []

            # 跳过名称为空的信息面
            if not name:
                logger.warning(f"⚠️ [Ucppt v7.214] key_aspects[{i}] 名称为空，跳过")
                continue

            aspect = KeyAspect(
                id=f"aspect_{i+1}",
                aspect_name=name,
                answer_goal=goal,
                importance=importance,
                search_query=search_hint,
            )
            # v7.260: 将子任务存储到 collected_info 中（临时方案，后续会转换为 SearchTarget）
            if sub_tasks:
                aspect.collected_info = [json.dumps(sub_tasks, ensure_ascii=False)]
            framework.key_aspects.append(aspect)

        # ==================== 日志输出 ====================
        logger.info(f"📐 [Ucppt v7.215] 深度问题分析完成")

        # L1-L5 日志
        if analysis_layers and isinstance(analysis_layers, dict):
            l1_facts = analysis_layers.get('L1_facts', [])
            logger.info(f"   🔍 L1 事实: {len(l1_facts) if isinstance(l1_facts, list) else 0}个")
            l3_tension = str(analysis_layers.get('L3_core_tension', ''))
            if l3_tension:
                logger.info(f"   🧠 L3 核心张力: {l3_tension[:60]}...")
            l5_score = analysis_layers.get('L5_sharpness', {}).get('score', 0)
            logger.info(f"   📊 L5 锐度: {l5_score}")

        # 人性维度日志
        if human_dims.get("enabled"):
            logger.info(f"   💫 人性维度: 已启用")

        # 基础日志
        logger.info(f"   🌐 宏观统筹: {macro.get('essence', '')[:50]}...")
        logger.info(f"   🎯 切入点: {entry.get('core_insight', '')[:50]}...")
        logger.info(f"   📋 信息面: {len(framework.key_aspects)}个")

        # v7.215 修复：如果没有解析出任何信息面，使用默认值
        if not framework.key_aspects:
            logger.warning(f"⚠️ [Ucppt v7.215] 未解析出任何信息面，使用默认值")
            default_aspects = [
                ("核心概念", "解释基本定义和核心内容", 5),
                ("原因分析", "说明背后的原因和逻辑", 4),
                ("具体案例", "提供实际例子或数据支撑", 4),
                ("最新动态", "介绍最新的发展和变化", 3),
                ("专业观点", "引用专家或权威的看法", 3),
            ]
            for i, (name, goal, importance) in enumerate(default_aspects):
                framework.key_aspects.append(KeyAspect(
                    id=f"aspect_{i+1}",
                    aspect_name=name,
                    answer_goal=goal,
                    importance=importance,
                ))
            logger.info(f"   📋 使用默认信息面: {len(framework.key_aspects)}个")

        return framework
    
    async def _analyze_question(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AnswerFramework:
        """
        分析用户问题 - v7.183 核心机制（非流式版本，保留作为降级）
        
        三步分析法：
        1. 宏观统筹 - 理解问题全貌，识别涉及的领域和维度
        2. 切入点洞察 - 找到问题的核心切入点，什么是关键突破口
        3. 关键信息面 - 完整回答需要收集哪些信息
        """
        prompt = f"""你是一个资深的问题分析专家。请对用户问题进行深度分析。

## 用户问题
{query}

## 上下文
{json.dumps(context or {}, ensure_ascii=False, indent=2)}

## 分析任务

### 第一步：宏观统筹
从全局视角理解这个问题：
- 这个问题涉及哪些领域/维度？
- 问题的本质诉求是什么？
- 有哪些隐含的需求或假设？

### 第二步：切入点洞察
找到解决问题的关键突破口：
- 什么是回答这个问题的核心切入点？
- 应该从哪个角度入手最有效？
- 有哪些关键概念/人物/方法需要深入理解？

### 第三步：关键信息面
要完整回答这个问题，需要收集哪些信息？
- 每个信息面是具体的、可搜索的
- 按重要性排序（5=必需，4=重要，3=有帮助）
- 3-6个信息面为宜

## 输出格式（JSON）
```json
{{
    "macro_overview": {{
        "domains": ["涉及的领域1", "领域2"],
        "essence": "问题的本质诉求（一句话）",
        "hidden_needs": ["隐含需求1", "隐含需求2"]
    }},
    "entry_point": {{
        "core_insight": "核心切入点洞察（这是最关键的突破口）",
        "approach_angle": "建议的切入角度",
        "key_concepts": ["需要深入理解的关键概念/人物/方法"]
    }},
    "answer_goal": "用户期望的答案是...",
    "key_aspects": [
        {{
            "name": "信息面名称",
            "goal": "这个信息面要回答什么",
            "importance": 5,
            "search_hint": "建议的搜索方向"
        }}
    ]
}}
```

## 示例
用户问题："用季裕棠（Tony Chi）的手法，帮00后富二代设计一个400平米的大平层"

分析：
1. 宏观统筹：
   - 涉及领域：室内设计、设计师风格、目标人群画像、空间设计
   - 本质诉求：用特定设计师的风格为特定人群创造匹配的居住空间
   - 隐含需求：理解设计师手法、理解业主审美、空间功能规划

2. 切入点洞察：
   - 核心切入点：季裕棠的设计语言如何与00后富二代的审美碰撞融合
   - 切入角度：先深入理解季裕棠的设计哲学，再分析如何转化为年轻化表达
   - 关键概念：季裕棠、东方美学、潮玩文化、大平层空间规划

3. 关键信息面：
   - 季裕棠设计手法（importance=5）：核心设计语言和标志性元素
   - 业主画像分析（importance=5）：00后富二代的审美偏好
   - 风格融合策略（importance=4）：如何将经典手法年轻化
   - 客厅空间设计（importance=4）：重点空间的处理方式

请只输出JSON。"""

        try:
            # v7.187: 使用 DeepSeek 官方 API
            result = await self._call_deepseek(prompt, model=self.thinking_model, max_tokens=1500)
            
            # v7.200: 使用统一 JSON 解析器
            data = self._safe_parse_json(result, context="非流式问题分析")
            if data is None:
                raise ValueError("无法解析问题分析结果")
            
            # 提取宏观统筹和切入点
            macro = data.get("macro_overview", {})
            entry = data.get("entry_point", {})
            
            framework = AnswerFramework(
                original_query=query,
                answer_goal=data.get("answer_goal", ""),
                created_at=time.time(),
            )
            
            # 存储宏观统筹和切入点信息（用于后续搜索和答案生成）
            framework.collected_evidence["_macro_overview"] = [
                f"涉及领域: {', '.join(macro.get('domains', []))}",
                f"本质诉求: {macro.get('essence', '')}",
                f"隐含需求: {', '.join(macro.get('hidden_needs', []))}",
            ]
            framework.collected_evidence["_entry_point"] = [
                f"核心切入点: {entry.get('core_insight', '')}",
                f"切入角度: {entry.get('approach_angle', '')}",
                f"关键概念: {', '.join(entry.get('key_concepts', []))}",
            ]
            
            # 构建关键信息面
            for i, aspect_data in enumerate(data.get("key_aspects", [])):
                aspect = KeyAspect(
                    id=f"aspect_{i+1}",
                    aspect_name=aspect_data.get("name", ""),
                    answer_goal=aspect_data.get("goal", ""),
                    importance=aspect_data.get("importance", 3),
                    search_query=aspect_data.get("search_hint", ""),
                )
                framework.key_aspects.append(aspect)
            
            # 日志输出分析结果
            logger.info(f"📐 [Ucppt] 问题分析完成")
            logger.info(f"   🌐 宏观统筹: {macro.get('essence', '')[:50]}...")
            logger.info(f"   🎯 切入点: {entry.get('core_insight', '')[:50]}...")
            logger.info(f"   📋 信息面: {len(framework.key_aspects)}个")
            
            return framework
            
        except Exception as e:
            logger.warning(f"⚠️ [Ucppt] 问题分析失败，使用简单框架: {e}")
            return self._build_simple_framework(query)
    
    def _build_simple_framework(self, query: str) -> AnswerFramework:
        """简单框架（LLM失败时使用）"""
        framework = AnswerFramework(
            original_query=query,
            answer_goal=f"全面解答关于「{query}」的问题",
            created_at=time.time(),
        )
        
        # 通用信息面
        default_aspects = [
            ("核心概念", "解释基本定义和核心内容", 5),
            ("原因分析", "说明背后的原因和逻辑", 4),
            ("具体案例", "提供实际例子或数据支撑", 4),
            ("最新动态", "介绍最新的发展和变化", 3),
            ("专业观点", "引用专家或权威的看法", 3),
        ]
        
        for i, (name, goal, importance) in enumerate(default_aspects):
            framework.key_aspects.append(KeyAspect(
                id=f"aspect_{i+1}",
                aspect_name=name,
                answer_goal=goal,
                importance=importance,
            ))
        
        return framework
    
    # ==================== v7.186: 专家叙事思考（反思驱动） ====================
    
    async def _generate_narrative_thinking(
        self,
        framework: AnswerFramework,
        target_aspect: KeyAspect,
        current_round: int,
        all_sources: List[Dict[str, Any]],
    ) -> Tuple[str, str, str]:
        """
        生成专家叙事思考 - v7.186 增强版
        
        关键改进：利用上一轮反思驱动本轮思考
        - 如果有上一轮反思，优先使用其建议的搜索方向
        - 保持与宏观统筹和用户问题的对齐
        
        返回: (thinking_narrative, search_strategy, search_query)
        """
        # 构建当前知识状态描述
        collected_summary = []
        for aspect in framework.key_aspects:
            if aspect.collected_info:
                info_preview = aspect.collected_info[0][:80] if aspect.collected_info else ""
                collected_summary.append(f"• {aspect.aspect_name}: {info_preview}...")
        
        knowledge_state = "\n".join(collected_summary) if collected_summary else "（这是首次搜索，暂无已知信息）"
        
        # 获取宏观统筹和切入点
        macro_info = framework.collected_evidence.get("_macro_overview", [])
        entry_info = framework.collected_evidence.get("_entry_point", [])
        
        # v7.186: 获取上一轮反思的建议（反思驱动下一轮）
        last_reflection = framework.last_reflection
        reflection_guidance = ""
        if last_reflection and current_round > 1:
            reflection_guidance = f"""
## 📝 上一轮反思的建议（承上启下）
- 上轮发现：{'; '.join(last_reflection.key_findings[:2]) if last_reflection.key_findings else '无'}
- 需要深入的点：{'; '.join(last_reflection.deeper_search_points[:2]) if last_reflection.deeper_search_points else '无'}
- 上轮建议的查询：{last_reflection.suggested_next_query}
- 上轮建议的目的：{last_reflection.next_round_purpose}
- 剩余缺口：{'; '.join(last_reflection.remaining_gaps[:2]) if last_reflection.remaining_gaps else '无'}
"""
        
        prompt = f"""你是一位资深设计顾问，正在帮客户做项目研究。请用自然、专业的语言描述你的思考过程。

## 客户问题（始终回归的锚点）
{framework.original_query}

## 我的回答目标
{framework.answer_goal}

## 宏观统筹（第一轮建立的整体框架）
{chr(10).join(macro_info) if macro_info else "正在建立整体理解..."}

## 核心切入点
{chr(10).join(entry_info) if entry_info else "正在寻找突破口..."}
{reflection_guidance}
## 当前已知信息
{knowledge_state}

## 当前是第 {current_round} 轮搜索
目标信息面：{target_aspect.aspect_name}
需要回答：{target_aspect.answer_goal}
重要程度：{target_aspect.importance}/5

## 任务
请用第一人称描述你的思考过程，要求：
1. {"参考上一轮反思的建议，但保持独立判断" if last_reflection else "自然流畅，像在向客户讲解研究思路"}
2. 解释"为什么"要搜索这个（不只是"搜索A"）
3. 确保与用户问题和宏观统筹保持对齐
4. 最后给出精准的搜索查询（15-35字中文，包含：核心概念+修饰词+领域词+类型词）

## 搜索查询示例（v7.198 优化）
- 好的查询："Tony Chi 季裕棠 设计手法 设计风格 酒店设计 室内设计 特点"
- 好的查询："00后富二代 居家设计 潮玩 室内设计 趋势"
- 差的查询："季裕棠设计"（太短，缺少修饰词和领域词）

## 输出格式（JSON）
```json
{{
    "thinking": "你的思考叙事（100-200字，第一人称，自然语言，承上启下）",
    "strategy": "搜索策略（一句话说明你的搜索意图）",
    "search_query": "精准的搜索查询（多关键词组合）"
}}
```

只输出JSON。"""

        try:
            # v7.187: 使用 DeepSeek 官方 API
            result = await self._call_deepseek(prompt, model=self.thinking_model, max_tokens=600)
            
            # v7.200: 使用统一 JSON 解析器
            data = self._safe_parse_json(result, context="叙事思考")
            if data is None:
                raise ValueError("无法解析叙事思考结果")
            
            thinking = data.get("thinking", "")
            strategy = data.get("strategy", "")
            search_query = data.get("search_query", "")
            
            # 确保查询不为空
            if not search_query or len(search_query.strip()) < 3:
                search_query = f"{framework.original_query} {target_aspect.aspect_name} {target_aspect.answer_goal[:15]}"
                logger.warning(f"⚠️ [Ucppt] LLM返回空查询，使用降级: {search_query}")
            
            logger.info(f"🤔 [Ucppt] 第{current_round}轮思考完成")
            logger.info(f"   💭 {thinking[:60]}...")
            logger.info(f"   🔍 查询: {search_query}")
            
            return thinking, strategy, search_query.strip()
            
        except Exception as e:
            logger.warning(f"⚠️ [Ucppt] 叙事思考失败: {e}")
            # 降级
            default_query = f"{framework.original_query} {target_aspect.aspect_name}"
            default_thinking = f"让我来搜索关于「{target_aspect.aspect_name}」的信息，这对于回答用户的问题很重要..."
            default_strategy = f"搜索{target_aspect.aspect_name}相关信息"
            return default_thinking, default_strategy, default_query
    
    # ==================== v7.187: 流式思考生成 ====================
    
    async def _generate_narrative_thinking_stream(
        self,
        framework: AnswerFramework,
        target_aspect: KeyAspect,
        current_round: int,
        all_sources: List[Dict[str, Any]],
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式生成专家叙事思考 - v7.187 核心创新
        
        流式输出 DeepSeek 的推理过程（reasoning_content），
        让用户实时看到 AI 的思考过程。
        
        Yields:
        - {"type": "thinking_chunk", "content": "...", "is_reasoning": True/False}
        - {"type": "thinking_complete", "thinking": "...", "strategy": "...", "query": "..."}
        """
        # 构建当前知识状态描述
        collected_summary = []
        for aspect in framework.key_aspects:
            if aspect.collected_info:
                info_preview = aspect.collected_info[0][:80] if aspect.collected_info else ""
                collected_summary.append(f"• {aspect.aspect_name}: {info_preview}...")
        
        knowledge_state = "\n".join(collected_summary) if collected_summary else "（这是首次搜索，暂无已知信息）"
        
        # 获取宏观统筹和切入点
        macro_info = framework.collected_evidence.get("_macro_overview", [])
        entry_info = framework.collected_evidence.get("_entry_point", [])
        
        # v7.186: 获取上一轮反思的建议
        last_reflection = framework.last_reflection
        reflection_guidance = ""
        if last_reflection and current_round > 1:
            reflection_guidance = f"""
## 📝 上一轮反思的建议（承上启下）
- 上轮发现：{'; '.join(last_reflection.key_findings[:2]) if last_reflection.key_findings else '无'}
- 需要深入的点：{'; '.join(last_reflection.deeper_search_points[:2]) if last_reflection.deeper_search_points else '无'}
- 上轮建议的查询：{last_reflection.suggested_next_query}
- 剩余缺口：{'; '.join(last_reflection.remaining_gaps[:2]) if last_reflection.remaining_gaps else '无'}
"""
        
        prompt = f"""你是一位资深设计顾问，正在帮客户做项目研究。请用自然、专业的语言描述你的思考过程。

## 客户问题（始终回归的锚点）
{framework.original_query}

## 我的回答目标
{framework.answer_goal}

## 宏观统筹（第一轮建立的整体框架）
{chr(10).join(macro_info) if macro_info else "正在建立整体理解..."}
{reflection_guidance}
## 当前已知信息
{knowledge_state}

## 当前是第 {current_round} 轮搜索
目标信息面：{target_aspect.aspect_name}
需要回答：{target_aspect.answer_goal}

## 任务
请用第一人称描述你的思考过程，要求：
1. {"参考上一轮反思的建议，但保持独立判断" if last_reflection else "自然流畅，像在向客户讲解研究思路"}
2. 解释"为什么"要搜索这个
3. 确保与用户问题保持对齐
4. 最后给出精准的搜索查询（15-35字中文，包含：核心概念+修饰词+领域词+类型词）

## 搜索查询示例（v7.198 优化）
- 好的查询："Tony Chi 季裕棠 设计手法 设计风格 酒店设计 室内设计 特点"
- 好的查询："00后富二代 居家设计 潮玩 室内设计 趋势"
- 差的查询："季裕棠设计"（太短，缺少修饰词和领域词）

## 输出格式（JSON）
```json
{{
    "thinking": "你的思考叙事（100-200字，第一人称，自然语言）",
    "strategy": "搜索策略（一句话）",
    "search_query": "精准的搜索查询"
}}
```

只输出JSON。"""

        full_reasoning = ""
        full_content = ""
        
        try:
            # v7.187: 使用 DeepSeek 官方 API，支持 reasoning_content
            async for chunk in self._call_deepseek_stream_with_reasoning(prompt, model=self.thinking_model, max_tokens=800):
                if chunk.get("type") == "reasoning":
                    reasoning_text = chunk.get("content", "")
                    full_reasoning += reasoning_text
                    # 流式输出推理过程
                    yield {
                        "type": "thinking_chunk",
                        "content": reasoning_text,
                        "is_reasoning": True,
                        "round": current_round,
                    }
                elif chunk.get("type") == "content":
                    content_text = chunk.get("content", "")
                    full_content += content_text
                elif chunk.get("type") == "error":
                    logger.error(f"流式思考出错: {chunk.get('content')}")
            
            # v7.200: 使用统一 JSON 解析器
            data = self._safe_parse_json(full_content, context="流式叙事思考")
            
            if data:
                thinking = data.get("thinking", "")
                strategy = data.get("strategy", "")
                search_query = data.get("search_query", "")
            else:
                # v7.200: 降级处理 - 使用简短查询而非完整原始需求
                thinking = full_reasoning[:200] if full_reasoning else f"正在分析「{target_aspect.aspect_name}」..."
                strategy = f"搜索{target_aspect.aspect_name}相关信息"
                # 提取原始查询的核心关键词（前30字）+ 目标面
                core_query = framework.original_query[:30].strip() if len(framework.original_query) > 30 else framework.original_query
                search_query = f"{core_query} {target_aspect.aspect_name}"
            
            # v7.188: 确保查询不为空且不过长
            if not search_query or len(search_query.strip()) < 3:
                search_query = f"{target_aspect.aspect_name} {target_aspect.answer_goal[:20] if target_aspect.answer_goal else ''}"
            
            logger.info(f"🤔 [Ucppt v7.187] 第{current_round}轮流式思考完成")
            logger.info(f"   💭 推理长度: {len(full_reasoning)} 字符")
            logger.info(f"   🔍 查询: {search_query}")
            
            # 发送完成事件
            yield {
                "type": "thinking_complete",
                "thinking": thinking,
                "strategy": strategy,
                "query": search_query.strip(),
                "reasoning": full_reasoning if full_reasoning else "",  # v7.188: 保留完整推理内容
                "round": current_round,
            }
            
        except Exception as e:
            logger.warning(f"⚠️ [Ucppt] 流式思考失败: {e}")
            # 降级
            default_query = f"{framework.original_query} {target_aspect.aspect_name}"
            default_thinking = f"让我来搜索关于「{target_aspect.aspect_name}」的信息..."
            default_strategy = f"搜索{target_aspect.aspect_name}相关信息"
            yield {
                "type": "thinking_complete",
                "thinking": default_thinking,
                "strategy": default_strategy,
                "query": default_query,
                "reasoning": "",
                "round": current_round,
            }
    async def _generate_unified_thinking_stream(
        self,
        framework: SearchFramework,  # v7.220: 使用 SearchFramework
        target: SearchTarget,  # v7.220: 使用 SearchTarget
        current_round: int,
        all_sources: List[Dict[str, Any]],
        last_round_sources: List[Dict[str, Any]],
        last_search_query: str = "",
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        统一思考流 - v7.220 更新

        将"思考"和"反思"融合为一次 LLM 调用：
        - 首轮（round=1）：仅做初始规划，无回顾
        - 后续轮（round>1）：回顾上轮搜索结果 + 规划本轮 + 全局校准

        v7.220 更新：
        - 使用 SearchFramework 替代 AnswerFramework
        - 使用 SearchTarget 替代 KeyAspect

        Yields:
        - {"type": "thinking_chunk", "content": "...", "is_reasoning": True/False}
        - {"type": "unified_thinking_complete", ...}
        """
        # v7.220: 构建当前知识状态描述（使用 targets）
        collected_summary = []
        for t in framework.targets:
            if t.collected_info:
                info_preview = t.collected_info[0][:80] if t.collected_info else ""
                # v7.243: 使用更多备选字段
                target_desc = t.question or t.name or t.search_for or f"目标{t.id}"
                collected_summary.append(f"• {target_desc}: {info_preview}...")

        knowledge_state = "\n".join(collected_summary) if collected_summary else "（这是首次搜索，暂无已知信息）"

        # v7.220: 移除宏观统筹（SearchFramework 不再使用 collected_evidence）
        # 直接使用 L1-L5 分析结果

        # 构建上轮搜索结果摘要（仅 round > 1 时）
        last_round_section = ""
        if current_round > 1 and last_round_sources:
            source_summaries = []
            for s in last_round_sources[:5]:
                title = s.get('title', '')[:50]
                content = s.get('content', '')[:150]
                source_summaries.append(f"【{title}】\n{content}")
            sources_text = "\n\n".join(source_summaries) if source_summaries else "无结果"

            last_round_section = f"""
## 📄 上一轮搜索结果（需要回顾评估）
上轮查询：{last_search_query}
结果：
{sources_text}
"""

        # v7.220: 构建 targets 状态
        targets_status = []
        for t in framework.targets:
            status_emoji = "✅" if t.is_complete() else ("🔶" if t.status == "partial" else "❌")
            info_preview = t.collected_info[0][:50] if t.collected_info else "待收集"
            # v7.243: 使用更多备选字段
            target_desc = t.question or t.name or t.search_for or f"目标{t.id}"
            targets_status.append(f"{status_emoji} {target_desc}({t.completion_score:.0%}): {info_preview}")
        cumulative_state = "\n".join(targets_status)

        # 构建回顾部分的指令（仅 round > 1）
        retrospective_instruction = ""
        if current_round > 1:
            retrospective_instruction = """
### 一、回顾上轮（必填，评估上轮搜索结果）
1. 上轮目标是否达成？信息充分吗？质量如何？
2. 直接获得了什么关键发现？可以推断出什么洞察？
3. 有什么质量问题？"""
        else:
            retrospective_instruction = """
### 一、初始评估（首轮无需回顾）
- 这是首轮搜索，暂无上轮结果需要评估"""

        # v7.220: 构建深度分析背景（如果有）
        deep_analysis_section = ""
        if framework.l1_facts or framework.l3_tension:
            deep_analysis_section = f"""
## 🧠 深度分析背景
"""
            if framework.l1_facts:
                # v7.234: 安全处理 l1_facts（确保是 list）
                facts_list = framework.l1_facts if isinstance(framework.l1_facts, list) else []
                if facts_list:
                    deep_analysis_section += f"**事实解构**: {'; '.join(str(f) for f in facts_list[:3])}\n"
            if framework.l3_tension:
                deep_analysis_section += f"**核心张力**: {framework.l3_tension}\n"
            if framework.l4_jtbd:
                deep_analysis_section += f"**用户任务**: {framework.l4_jtbd}\n"

        # v7.232: 获取预设关键词
        preset_keywords = target.preset_keywords if target.preset_keywords else []
        preset_keyword_section = ""
        if preset_keywords:
            # 获取下一个未使用的预设关键词
            next_keyword_idx = target.current_keyword_index
            if next_keyword_idx < len(preset_keywords):
                suggested_keyword = preset_keywords[next_keyword_idx]
                preset_keyword_section = f"""
## 📌 预设搜索关键词（优先使用）
建议使用: **{suggested_keyword}**
备选关键词: {', '.join(preset_keywords[next_keyword_idx+1:next_keyword_idx+3]) if len(preset_keywords) > next_keyword_idx+1 else '无'}

⚠️ 重要：优先使用预设关键词，除非有充分理由需要调整。
如需调整，必须保持相同的具体程度（包含具体品牌名/人名/地点名）。
"""

        # v7.240: 构建框架清单上下文（指导搜索方向）
        framework_checklist_section = ""
        if framework.framework_checklist:
            checklist = framework.framework_checklist
            framework_checklist_section = f"""
## 📋 搜索框架清单（始终遵循）

**核心问题**: {checklist.core_summary}

**搜索主线**:
"""
            for i, d in enumerate(checklist.main_directions, 1):
                framework_checklist_section += f"{i}. {d.get('direction', '')}: {d.get('purpose', '')}\n"

            if checklist.boundaries:
                framework_checklist_section += f"\n**不涉及**: {', '.join(checklist.boundaries)}\n"

            framework_checklist_section += f"\n**回答目标**: {checklist.answer_goal}\n"

        prompt = f"""你是一位资深设计顾问，正在帮客户做项目研究。请用自然、专业的语言描述你的思考过程。

## 🎯 客户问题（始终回归的锚点）
{framework.original_query}

## 🎯 问题本质
{framework.core_question}
{framework_checklist_section}
{deep_analysis_section}
{last_round_section}
## 📊 截至目前的累积进展
{cumulative_state}
整体完成度：{framework.overall_completeness:.0%}

## 🎯 本轮目标（第 {current_round} 轮）
目标：{target.question or target.name or target.search_for or target.description or f'搜索目标{target.id}'}
搜索内容：{target.search_for or target.description or ''}
目的：{target.why_need or target.purpose or target.answer_goal or ''}
{preset_keyword_section}
---

## 请完成以下任务（一次性输出）
{retrospective_instruction}

### 二、本轮规划
1. 基于{"上轮结果分析" if current_round > 1 else "当前状态"}，本轮应该搜索什么？
2. 搜索策略是什么？
3. {"使用预设关键词，或在保持具体程度的前提下微调" if preset_keywords else "给出精准的搜索查询（15-35字，包含核心概念+修饰词+领域词）"}

### 三、全局校准
1. 我们走在正确方向上吗？（0-1 打分）
2. 还有哪些信息缺口？
3. 预计还需几轮？

## 输出格式（JSON）
```json
{{
    {"\"retrospective\": {" if current_round > 1 else "\"initial_assessment\": {"}
        {"\"goal_achieved\": true," if current_round > 1 else ""}
        "key_findings": ["发现1", "发现2"],
        "inferred_insights": ["推断洞察1"],
        "info_sufficiency": 0.7,
        "info_quality": 0.8,
        "quality_issues": ["问题1"]
    }},
    "current_round_planning": {{
        "thinking": "思考叙事（100-200字，第一人称，自然语言）",
        "strategy": "搜索策略（一句话）",
        "search_query": "{"使用预设关键词或微调后的关键词" if preset_keywords else "精准搜索查询"}"
    }},
    "global_alignment": {{
        "alignment_score": 0.8,
        "alignment_note": "方向正确/需要调整...",
        "remaining_gaps": ["缺口1", "缺口2"],
        "estimated_rounds_remaining": 2
    }},
    "cumulative_progress": "综合前{current_round}轮搜索的累积进展描述（50-100字）"
}}
```

只输出JSON。"""

        full_reasoning = ""
        full_content = ""
        
        try:
            # 使用 DeepSeek 官方 API，支持 reasoning_content
            async for chunk in self._call_deepseek_stream_with_reasoning(prompt, model=self.thinking_model, max_tokens=1200):
                if chunk.get("type") == "reasoning":
                    reasoning_text = chunk.get("content", "")
                    full_reasoning += reasoning_text
                    # v7.238: 过滤冗余内心独白
                    filtered_text = self._filter_verbose_monologue(reasoning_text)
                    if filtered_text.strip():
                        yield {
                            "type": "thinking_chunk",
                            "content": filtered_text,
                            "is_reasoning": True,
                            "round": current_round,
                        }
                elif chunk.get("type") == "content":
                    content_text = chunk.get("content", "")
                    full_content += content_text
                elif chunk.get("type") == "error":
                    logger.error(f"统一思考流出错: {chunk.get('content')}")
            
            # v7.214: 解析 JSON，强制期望字典类型
            data = self._safe_parse_json(full_content, context="统一思考流", expect_dict=True)
            
            # v7.214: 额外类型检查，确保 data 是字典
            if data and isinstance(data, dict):
                # 提取回顾部分
                retro_key = "retrospective" if current_round > 1 else "initial_assessment"
                retro = data.get(retro_key, {})
                # v7.214: 确保 retro 是字典
                if not isinstance(retro, dict):
                    logger.warning(f"⚠️ [Ucppt v7.214] {retro_key} 不是字典类型，使用默认值")
                    retro = {}
                    
                planning = data.get("current_round_planning", {})
                if not isinstance(planning, dict):
                    logger.warning(f"⚠️ [Ucppt v7.214] current_round_planning 不是字典类型，使用默认值")
                    planning = {}
                    
                alignment = data.get("global_alignment", {})
                if not isinstance(alignment, dict):
                    logger.warning(f"⚠️ [Ucppt v7.214] global_alignment 不是字典类型，使用默认值")
                    alignment = {}
                
                result = UnifiedThinkingResult(
                    # 回顾
                    key_findings=retro.get("key_findings", []) if isinstance(retro.get("key_findings"), list) else [],
                    inferred_insights=retro.get("inferred_insights", []) if isinstance(retro.get("inferred_insights"), list) else [],
                    info_sufficiency=float(retro.get("info_sufficiency", 0.5)) if isinstance(retro.get("info_sufficiency"), (int, float)) else 0.5,
                    info_quality=float(retro.get("info_quality", 0.5)) if isinstance(retro.get("info_quality"), (int, float)) else 0.5,
                    goal_achieved=bool(retro.get("goal_achieved", False)),
                    quality_issues=retro.get("quality_issues", []) if isinstance(retro.get("quality_issues"), list) else [],
                    # 规划
                    thinking_narrative=str(planning.get("thinking", "")),
                    search_strategy=str(planning.get("strategy", "")),
                    # v7.232: 优先使用预设关键词
                    search_query=self._get_search_query_with_preset(target, str(planning.get("search_query", ""))),
                    reasoning_content=full_reasoning,
                    # 全局校准
                    alignment_score=float(alignment.get("alignment_score", 0.7)) if isinstance(alignment.get("alignment_score"), (int, float)) else 0.7,
                    alignment_note=str(alignment.get("alignment_note", "")),
                    remaining_gaps=alignment.get("remaining_gaps", []) if isinstance(alignment.get("remaining_gaps"), list) else [],
                    estimated_rounds_remaining=int(alignment.get("estimated_rounds_remaining", 2)) if isinstance(alignment.get("estimated_rounds_remaining"), (int, float)) else 2,
                    # 累积
                    cumulative_progress=str(data.get("cumulative_progress", "")),
                    reflection_narrative=str(planning.get("thinking", "")),  # 兼容
                )
            else:
                # 降级处理 - v7.232: 优先使用预设关键词
                preset_keyword = target.get_next_preset_keyword()
                if preset_keyword:
                    fallback_query = preset_keyword
                    logger.info(f"📌 [v7.232] 降级处理使用预设关键词: {preset_keyword[:40]}...")
                else:
                    core_query = framework.original_query[:30].strip() if len(framework.original_query) > 30 else framework.original_query
                    # v7.243: 使用更多备选字段，确保 target 信息不为空
                    target_info = target.question or target.name or target.search_for or target.description or ""
                    fallback_query = f"{core_query} {target_info}".strip()

                # v7.243: 获取目标描述，优先使用有值的字段
                target_desc = target.question or target.name or target.search_for or f"目标{target.id}"
                result = UnifiedThinkingResult(
                    thinking_narrative=full_reasoning[:200] if full_reasoning else f"正在分析「{target_desc}」...",
                    search_strategy=f"搜索{target_desc}相关信息",
                    search_query=fallback_query,
                    reasoning_content=full_reasoning,
                    info_sufficiency=0.3,
                    estimated_rounds_remaining=3,
                )

            # 确保查询不为空 - v7.232: 优先使用预设关键词
            if not result.search_query or len(result.search_query.strip()) < 3:
                preset_keyword = target.get_next_preset_keyword()
                if preset_keyword:
                    result.search_query = preset_keyword
                else:
                    result.search_query = f"{target.question or target.name or target.search_for or f'目标{target.id}'} {target.answer_goal[:20] if target.answer_goal else ''}"
            
            logger.info(f"🤔 [Ucppt v7.204] 第{current_round}轮统一思考完成")
            logger.info(f"   💭 推理长度: {len(full_reasoning)} 字符")
            logger.info(f"   🔍 查询: {result.search_query}")
            if current_round > 1:
                logger.info(f"   📊 上轮信息充分度: {result.info_sufficiency:.0%}")
            logger.info(f"   🧭 方向对齐: {result.alignment_score:.0%}")
            
            # 发送完成事件
            yield {
                "type": "unified_thinking_complete",
                "result": result,
                "round": current_round,
            }
            
        except Exception as e:
            logger.warning(f"⚠️ [Ucppt v7.204] 统一思考失败: {e}")
            # 降级 - v7.232: 优先使用预设关键词
            preset_keyword = target.get_next_preset_keyword()
            # v7.243: 获取目标描述，优先使用有值的字段
            target_desc = target.question or target.name or target.search_for or f"目标{target.id}"
            if preset_keyword:
                default_query = preset_keyword
                logger.info(f"📌 [v7.232] 异常降级使用预设关键词: {preset_keyword[:40]}...")
            else:
                target_info = target.question or target.name or target.search_for or ""
                default_query = f"{framework.original_query[:30]} {target_info}".strip()

            result = UnifiedThinkingResult(
                thinking_narrative=f"让我来搜索关于「{target_desc}」的信息...",
                search_strategy=f"搜索{target_desc}相关信息",
                search_query=default_query,
                reasoning_content="",
                info_sufficiency=0.3,
                estimated_rounds_remaining=3,
            )
            yield {
                "type": "unified_thinking_complete",
                "result": result,
                "round": current_round,
            }

    async def _enhanced_reflection(
        self,
        framework: AnswerFramework,
        target_aspect: KeyAspect,
        current_round: int,
        round_sources: List[Dict[str, Any]],
        search_query: str,
        search_strategy: str,
    ) -> ReflectionResult:
        """
        增强反思 - v7.186 核心机制
        
        反思的双重角色：
        1. 回顾：评估本轮达成度、信息质量
        2. 规划：识别深入点、规划下一轮
        3. 校准：回到用户问题和宏观统筹
        
        关键：反思既是上一轮的总结，又是下一轮的开始
        """
        # 获取宏观统筹和切入点（始终回归的锚点）
        macro_overview = framework.collected_evidence.get("_macro_overview", [])
        entry_point = framework.collected_evidence.get("_entry_point", [])
        
        # 提取搜索结果摘要
        source_summaries = []
        for s in round_sources[:5]:
            title = s.get('title', '')[:50]
            content = s.get('content', '')[:150]
            source_summaries.append(f"【{title}】\n{content}")
        sources_text = "\n\n".join(source_summaries) if source_summaries else "未找到相关结果"
        
        # 构建累积进展描述
        aspects_status = []
        for a in framework.key_aspects:
            status_emoji = {"complete": "✅", "partial": "🔶", "missing": "❌"}.get(a.status, "❓")
            info_preview = a.collected_info[0][:50] if a.collected_info else "待收集"
            aspects_status.append(f"{status_emoji} {a.aspect_name}({a.completion_score:.0%}): {info_preview}")
        cumulative_state = "\n".join(aspects_status)
        
        prompt = f"""你是资深设计顾问，正在进行第{current_round}轮搜索后的反思。

## 🎯 用户的原始问题（始终回归的锚点）
{framework.original_query}

## 🌐 第一轮的宏观统筹
{chr(10).join(macro_overview) if macro_overview else "正在建立整体理解..."}

## 💡 第一轮的核心切入点
{chr(10).join(entry_point) if entry_point else "正在寻找突破口..."}

## 📋 本轮搜索目标
目标信息面：{target_aspect.aspect_name}
期望获得：{target_aspect.answer_goal}
搜索策略：{search_strategy}

## 🔍 本轮搜索
查询词：{search_query}

## 📄 搜索结果
{sources_text}

## 📊 截至目前的累积进展
{cumulative_state}
整体完成度：{framework.overall_completeness:.0%}

---

## 请进行深度反思（三段式）

### 一、回顾本轮（上一轮总结）
1. 本轮目标是否达成？为什么？
2. 信息充分吗？质量如何？有什么问题？
3. 直接获得了什么？可以推断出什么？

### 二、规划下一轮（下一轮思考）
4. 哪些点值得深入挖掘？发现了新的关键概念吗？
5. 下一轮应该搜索什么？为什么？

### 三、全局校准（回到原点）
6. 回到用户问题和宏观统筹，我们走在正确方向上吗？
7. 还需要补充什么才能完整回答？预计还需几轮？

## 输出格式（JSON）
```json
{{
    "retrospective": {{
        "goal_achieved": true,
        "goal_achievement_reason": "达成/未达成的具体原因",
        "info_sufficiency": 0.7,
        "info_quality": 0.8,
        "quality_issues": ["问题1", "问题2"],
        "key_findings": ["关键发现1", "关键发现2"],
        "inferred_insights": ["推断洞察1", "推断洞察2"]
    }},
    "next_round_planning": {{
        "needs_deeper_search": true,
        "deeper_search_points": ["需要深入的点1", "点2"],
        "suggested_next_query": "建议的下一轮搜索查询",
        "next_round_purpose": "下一轮的目的"
    }},
    "global_alignment": {{
        "alignment_score": 0.8,
        "alignment_note": "方向正确/需要调整...",
        "remaining_gaps": ["剩余缺口1", "缺口2"],
        "estimated_rounds_remaining": 2
    }},
    "reflection_narrative": "完整的反思叙述（150-250字，第一人称，自然语言，承上启下）",
    "cumulative_progress": "综合前{current_round}轮搜索的累积进展描述（50-100字）"
}}
```

只输出JSON。"""

        try:
            # v7.187: 使用 DeepSeek 官方 API
            result = await self._call_deepseek(prompt, model=self.eval_model, max_tokens=1000)
            
            # v7.200: 使用统一 JSON 解析器
            data = self._safe_parse_json(result, context="增强反思")
            if data is None:
                raise ValueError("无法解析增强反思结果")
            
            retro = data.get("retrospective", {})
            planning = data.get("next_round_planning", {})
            alignment = data.get("global_alignment", {})
            
            reflection_result = ReflectionResult(
                # 回顾
                goal_achieved=retro.get("goal_achieved", False),
                goal_achievement_reason=retro.get("goal_achievement_reason", ""),
                info_sufficiency=retro.get("info_sufficiency", 0.5),
                info_quality=retro.get("info_quality", 0.5),
                quality_issues=retro.get("quality_issues", []),
                key_findings=retro.get("key_findings", []),
                inferred_insights=retro.get("inferred_insights", []),
                # 规划
                needs_deeper_search=planning.get("needs_deeper_search", True),
                deeper_search_points=planning.get("deeper_search_points", []),
                suggested_next_query=planning.get("suggested_next_query", ""),
                next_round_purpose=planning.get("next_round_purpose", ""),
                # 全局校准
                alignment_with_goal=alignment.get("alignment_score", 0.7),
                alignment_note=alignment.get("alignment_note", ""),
                remaining_gaps=alignment.get("remaining_gaps", []),
                estimated_rounds_remaining=alignment.get("estimated_rounds_remaining", 2),
                # 叙事
                reflection_narrative=data.get("reflection_narrative", ""),
                cumulative_progress=data.get("cumulative_progress", ""),
            )
            
            logger.info(f"📝 [Ucppt v7.186] 第{current_round}轮增强反思完成")
            logger.info(f"   🎯 目标达成: {reflection_result.goal_achieved}")
            logger.info(f"   📊 信息充分度: {reflection_result.info_sufficiency:.0%}")
            logger.info(f"   🧭 方向对齐: {reflection_result.alignment_with_goal:.0%}")
            logger.info(f"   ⏳ 预估剩余: {reflection_result.estimated_rounds_remaining}轮")
            
            return reflection_result
            
        except Exception as e:
            logger.warning(f"⚠️ [Ucppt] 增强反思失败，使用简化版: {e}")
            return ReflectionResult(
                goal_achieved=len(round_sources) > 0,
                goal_achievement_reason="基于搜索结果数量的简单判断",
                info_sufficiency=0.3 if round_sources else 0.0,
                info_quality=0.5 if round_sources else 0.0,
                key_findings=[f"搜索到{len(round_sources)}条结果"],
                reflection_narrative=f"本轮搜索到{len(round_sources)}条结果，正在分析中...",
                cumulative_progress=f"已完成{current_round}轮搜索",
                needs_deeper_search=True,
                estimated_rounds_remaining=3,
            )
    
    async def _reflect_with_inference(
        self,
        framework: AnswerFramework,
        target_aspect: KeyAspect,
        current_round: int,
        round_sources: List[Dict[str, Any]],
        search_query: str,
    ) -> Tuple[str, List[str], float, str]:
        """
        推断式反思 - v7.185/v7.186 保留
        
        不只是评估结果，而是：
        1. 批判性分析搜索结果
        2. 从间接信息中推断洞察
        3. 判断下一步方向
        
        返回: (reflection, useful_info, completion_delta, new_status)
        """
        # 提取搜索结果摘要
        source_summaries = []
        for s in round_sources[:5]:
            title = s.get('title', '')[:50]
            content = s.get('content', '')[:150]
            source_summaries.append(f"【{title}】\n{content}")
        
        sources_text = "\n\n".join(source_summaries) if source_summaries else "未找到相关结果"
        
        prompt = f"""作为资深设计顾问，请对本轮搜索进行反思复盘。

## 用户问题
{framework.original_query}

## 本轮搜索目标
{target_aspect.aspect_name}: {target_aspect.answer_goal}

## 搜索查询
{search_query}

## 搜索结果
{sources_text}

## 任务
请进行深度反思，包括：

1. **直接收获**：搜索结果直接回答了什么？
2. **间接推断**：虽然没有直接结果，但可以从这些信息推断出什么？
   （重要！即使结果不完全匹配，也要尝试从中提取有价值的洞察）
3. **信息缺口**：还缺什么关键信息？
4. **下一步建议**：接下来应该关注什么？

## 输出格式（JSON）
```json
{{
    "reflection": "你的反思复盘（100-150字，第一人称，包含推断）",
    "useful_info": ["提取的关键信息点1", "关键信息点2", "推断的洞察3"],
    "completion_score": 0.6,
    "status": "partial",
    "next_suggestion": "下一步建议"
}}
```

## 示例（展示推断能力）
如果搜索"王思聪居家风格"没有直接结果：
{{
    "reflection": "搜索结果似乎没有直接展示王思聪的居家设计风格，但我可以从这些片段中推断：他偏好科技产品（可能喜欢智能家居）、有养狗习惯（需要宠物友好设计）、电竞爱好明显（可能需要专业娱乐空间）。这些间接线索对设计方向仍有参考价值...",
    "useful_info": ["推断：偏好科技产品，智能家居需求高", "推断：有宠物，需要宠物友好设计", "推断：电竞爱好，需要专业娱乐空间"],
    "completion_score": 0.4,
    "status": "partial",
    "next_suggestion": "继续搜索00后富二代的生活方式趋势"
}}

status可选值：missing（无有用信息）、partial（有部分信息）、complete（信息充分）

只输出JSON。"""

        try:
            # v7.187: 使用 DeepSeek 官方 API
            result = await self._call_deepseek(prompt, model=self.eval_model, max_tokens=600)
            
            # v7.200: 使用统一 JSON 解析器
            data = self._safe_parse_json(result, context="推断式反思")
            if data is None:
                raise ValueError("无法解析推断式反思结果")
            
            reflection = data.get("reflection", "")
            useful_info = data.get("useful_info", [])
            completion_score = data.get("completion_score", 0.3)
            status = data.get("status", "partial")
            
            logger.info(f"📝 [Ucppt] 第{current_round}轮反思完成")
            logger.info(f"   💡 {reflection[:60]}...")
            logger.info(f"   📊 完成度贡献: {completion_score:.0%}")
            
            return reflection, useful_info, completion_score, status
            
        except Exception as e:
            logger.warning(f"⚠️ [Ucppt] 反思失败: {e}")
            return (
                f"搜索到{len(round_sources)}条结果，正在分析中...",
                [],
                0.2 if round_sources else 0.0,
                "partial" if round_sources else "missing"
            )
    
    async def _generate_phase_checkpoint(
        self,
        master_line: SearchMasterLine,
        framework: SearchFramework,  # v7.235: 修复类型标注，与实际使用一致
        current_round: int,
        all_sources: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """
        生成阶段复盘检查点 - v7.213 新增
        
        在指定轮次进行阶段性复盘：
        1. 评估当前阶段完成度
        2. 检查是否需要触发延展任务
        3. 生成复盘报告和下一步建议
        
        返回: checkpoint 事件或 None
        """
        logger.info(f"🔍 [v7.213] 触发阶段复盘检查点 | round={current_round}")
        
        # 整理当前任务状态
        task_summary = []
        for task in master_line.search_tasks:
            status_emoji = {"complete": "✅", "searching": "🔄", "pending": "⏳"}.get(task.status, "❓")
            findings_preview = "; ".join(task.actual_findings[:2]) if task.actual_findings else "暂无"
            task_summary.append(
                f"{status_emoji} [{task.id}|P{task.priority}|{task.phase}] {task.task[:40]}... → {findings_preview[:60]}"
            )
        
        # 整理阶段进度
        phase_progress = master_line.get_phase_progress()
        phase_summary = []
        for phase, progress in phase_progress.items():
            status_emoji = {"complete": "✅", "in_progress": "🔄", "pending": "⏳"}.get(progress["status"], "❓")
            phase_summary.append(f"{status_emoji} {phase}: {progress['completed']}/{progress['total']} ({progress['percentage']}%)")
        
        # 整理探索触发条件
        triggers_text = "\n".join([f"- {t}" for t in master_line.exploration_triggers])
        
        prompt = f"""作为搜索协调专家，请对当前搜索进度进行阶段性复盘。

## 用户问题
{framework.original_query}

## 搜索主线
- 核心问题：{master_line.core_question}
- 边界约束：{master_line.boundary}
- 框架概要：{master_line.framework_summary}

## 当前任务状态（已完成第{current_round}轮搜索）
{chr(10).join(task_summary)}

## 阶段进度
{chr(10).join(phase_summary)}

## 探索触发条件
{triggers_text}

## 已收集信息源数量: {len(all_sources)}

## 复盘任务
1. 评估当前阶段是否已充分完成
2. 检查是否有探索触发条件被满足
3. 决定是否需要补充延展任务
4. 生成下一步搜索建议

## 输出格式（JSON）
```json
{{
    "checkpoint_summary": "当前进度的一句话总结",
    "current_phase": "当前所处阶段",
    "phase_completion": 0.75,
    "key_findings_so_far": ["已发现的关键信息1", "已发现的关键信息2"],
    "gaps_identified": ["发现的信息缺口1"],
    "triggered_conditions": ["被触发的探索条件"],
    "extension_tasks": [
        {{
            "id": "T_EXT1",
            "task": "延展搜索任务描述",
            "purpose": "为什么需要这个延展",
            "priority": 3,
            "phase": "对比验证",
            "expected_info": ["期望获取的信息"],
            "trigger": "触发原因",
            "reason": "详细理由"
        }}
    ],
    "next_steps_suggestion": "下一步搜索建议",
    "should_continue": true,
    "estimated_remaining_rounds": 2
}}
```

只输出JSON，不要有其他内容。"""

        try:
            result = await self._call_deepseek(prompt, model=self.eval_model, max_tokens=800)
            data = self._safe_parse_json(result, context="阶段复盘检查点(v7.213)")
            
            if data is None:
                logger.warning(f"⚠️ [v7.213] 解析阶段复盘结果失败")
                return None
            
            logger.info(f"📋 [v7.213] 阶段复盘完成 | phase={data.get('current_phase')}, completion={data.get('phase_completion')}, extensions={len(data.get('extension_tasks', []))}")
            
            return {
                "type": "phase_checkpoint",
                "data": {
                    "round": current_round,
                    "checkpoint_summary": data.get("checkpoint_summary", ""),
                    "current_phase": data.get("current_phase", ""),
                    "phase_completion": data.get("phase_completion", 0.0),
                    "key_findings": data.get("key_findings_so_far", []),
                    "gaps_identified": data.get("gaps_identified", []),
                    "triggered_conditions": data.get("triggered_conditions", []),
                    "extension_tasks": data.get("extension_tasks", []),
                    "next_steps": data.get("next_steps_suggestion", ""),
                    "should_continue": data.get("should_continue", True),
                    "estimated_remaining": data.get("estimated_remaining_rounds", 2),
                    "phase_progress": phase_progress,
                    "message": f"第{current_round}轮：阶段复盘检查点",
                }
            }
            
        except Exception as e:
            logger.error(f"❌ [v7.213] 阶段复盘检查点生成失败: {e}")
            return None
    
    async def _generate_search_retrospective(
        self,
        master_line: SearchMasterLine,
        framework: AnswerFramework,
        total_rounds: int,
        all_sources: List[Dict[str, Any]],
        rounds: List[SearchRoundState],
    ) -> Optional[Dict[str, Any]]:
        """
        生成搜索历程最终回顾 - v7.213 新增
        
        在所有搜索完成后，生成一个完整的搜索回顾报告：
        1. 回顾整个搜索路径
        2. 总结主线任务完成情况
        3. 评估延展任务贡献
        4. 为最终答案生成提供上下文
        
        返回: retrospective 事件或 None
        """
        logger.info(f"📊 [v7.213] 生成搜索历程最终回顾 | rounds={total_rounds}, tasks={len(master_line.search_tasks)}")
        
        # 整理任务完成情况
        task_results = []
        for task in master_line.search_tasks:
            status_emoji = {"complete": "✅", "searching": "🔶", "pending": "❌"}.get(task.status, "❓")
            ext_marker = "[延展]" if task.is_extension else ""
            findings_count = len(task.actual_findings)
            task_results.append(
                f"{status_emoji} {ext_marker}[{task.id}|P{task.priority}] {task.task[:50]}... → 发现{findings_count}条信息 (完成度:{task.completion_score:.0%})"
            )
        
        # 整理轮次摘要
        round_summary = []
        for r in rounds[-6:]:  # 最近6轮
            round_summary.append(f"R{r.round_number}: {r.target_aspect} | query={r.search_query[:30] if r.search_query else ''}... | Δ={r.completeness_delta:.2%}")
        
        # 整理延展日志
        extension_summary = []
        for ext in master_line.extension_log:
            extension_summary.append(f"- {ext.get('task_id')}: {ext.get('reason', '')} (触发:{ext.get('trigger', '')})")
        
        prompt = f"""作为搜索历程分析专家，请对整个搜索过程进行最终回顾。

## 用户问题
{framework.original_query}

## 搜索主线信息
- 核心问题：{master_line.core_question}
- 边界约束：{master_line.boundary}
- 框架概要：{master_line.framework_summary}

## 任务完成情况（共{len(master_line.search_tasks)}个任务）
{chr(10).join(task_results)}

## 搜索轮次摘要（最近{min(6, len(rounds))}轮）
{chr(10).join(round_summary)}

## 延展任务日志
{chr(10).join(extension_summary) if extension_summary else "无延展任务"}

## 总体数据
- 总轮数：{total_rounds}
- 总信息源：{len(all_sources)}
- 最终完成度：{framework.overall_completeness:.1%}

## 回顾任务
1. 回顾搜索路径是否符合预设框架
2. 评估主线任务和延展任务的贡献
3. 识别搜索中的关键转折点
4. 总结对最终答案最有价值的发现
5. 指出仍存在的知识盲区

## 输出格式（JSON）
```json
{{
    "retrospective_narrative": "一段自然语言的搜索历程回顾（150字内）",
    "framework_adherence": 0.85,
    "key_discoveries": ["最重要的发现1", "最重要的发现2", "最重要的发现3"],
    "turning_points": ["关键转折点1"],
    "mainline_contribution": "主线任务贡献总结",
    "extension_contribution": "延展任务贡献总结",
    "knowledge_gaps": ["仍存在的知识盲区"],
    "answer_preparation_notes": "为生成最终答案的准备说明",
    "search_efficiency_score": 0.8,
    "overall_assessment": "整体评价（一句话）"
}}
```

只输出JSON，不要有其他内容。"""

        try:
            result = await self._call_deepseek(prompt, model=self.eval_model, max_tokens=800)
            data = self._safe_parse_json(result, context="搜索历程回顾(v7.213)")
            
            if data is None:
                logger.warning(f"⚠️ [v7.213] 解析搜索历程回顾结果失败")
                return None
            
            logger.info(f"📊 [v7.213] 搜索历程回顾完成 | adherence={data.get('framework_adherence')}, efficiency={data.get('search_efficiency_score')}")
            
            return {
                "type": "search_retrospective",
                "data": {
                    "total_rounds": total_rounds,
                    "total_sources": len(all_sources),
                    "total_tasks": len(master_line.search_tasks),
                    "completed_tasks": sum(1 for t in master_line.search_tasks if t.status == "complete"),
                    "extension_tasks_count": sum(1 for t in master_line.search_tasks if t.is_extension),
                    "retrospective_narrative": data.get("retrospective_narrative", ""),
                    "framework_adherence": data.get("framework_adherence", 0.0),
                    "key_discoveries": data.get("key_discoveries", []),
                    "turning_points": data.get("turning_points", []),
                    "mainline_contribution": data.get("mainline_contribution", ""),
                    "extension_contribution": data.get("extension_contribution", ""),
                    "knowledge_gaps": data.get("knowledge_gaps", []),
                    "answer_preparation_notes": data.get("answer_preparation_notes", ""),
                    "search_efficiency_score": data.get("search_efficiency_score", 0.0),
                    "overall_assessment": data.get("overall_assessment", ""),
                    "extension_log": master_line.extension_log,
                    "final_completeness": framework.overall_completeness,
                    "message": "搜索历程最终回顾",
                }
            }
            
        except Exception as e:
            logger.error(f"❌ [v7.213] 搜索历程回顾生成失败: {e}")
            return None
    
    async def _can_answer_semantically(
        self,
        framework: Union[AnswerFramework, SearchFramework],
        current_round: int,
    ) -> Tuple[bool, str]:
        """
        语义完成度判断 - v7.186 增强版

        不是看数值，而是问LLM："基于当前信息，能否完整回答用户问题？"

        返回: (can_answer, reason)
        """
        # 整理当前知识状态 - v7.229: 兼容 SearchFramework 和 AnswerFramework
        knowledge_summary = []
        aspects = getattr(framework, 'targets', None) or getattr(framework, 'key_aspects', [])
        for aspect in aspects:
            status_emoji = {"complete": "✅", "partial": "🔶", "missing": "❌"}.get(aspect.status, "❓")
            info_preview = "; ".join(aspect.collected_info[:2]) if aspect.collected_info else "暂无"
            aspect_name = getattr(aspect, 'name', None) or getattr(aspect, 'aspect_name', '')
            knowledge_summary.append(f"{status_emoji} {aspect_name}: {info_preview[:100]}")
        
        prompt = f"""作为资深顾问，请判断是否有足够信息回答用户问题。

## 用户问题
{framework.original_query}

## 回答目标
{framework.answer_goal}

## 当前已收集的信息
{chr(10).join(knowledge_summary)}

## 已搜索 {current_round} 轮

## 判断标准
1. 能否给出一个让用户满意的、有实质内容的回答？
2. 核心问题是否已经有足够的信息支撑？
3. 缺失的信息是"必须有"还是"有了更好"？

## 输出格式（JSON）
```json
{{
    "can_answer": true,
    "confidence": 0.8,
    "reason": "综合判断理由（一句话）",
    "critical_missing": ["必须补充的关键信息"],
    "nice_to_have": ["可选补充的信息"]
}}
```

只输出JSON。"""

        try:
            # v7.187: 使用 DeepSeek 官方 API
            result = await self._call_deepseek(prompt, model=self.eval_model, max_tokens=300)
            
            # v7.200: 使用统一 JSON 解析器
            data = self._safe_parse_json(result, context="语义完成度判断")
            if data is None:
                raise ValueError("无法解析语义完成度判断结果")
            
            can_answer = data.get("can_answer", False)
            confidence = data.get("confidence", 0.5)
            reason = data.get("reason", "")
            critical_missing = data.get("critical_missing", [])
            
            # 如果置信度较高且无关键缺失，认为可以回答
            if can_answer and confidence >= 0.7 and len(critical_missing) == 0:
                logger.info(f"✅ [Ucppt] 语义判断：可以回答 | {reason}")
                return True, reason
            else:
                logger.info(f"🔄 [Ucppt] 语义判断：继续搜索 | 缺失: {critical_missing}")
                return False, f"还缺: {', '.join(critical_missing)}" if critical_missing else reason
                
        except Exception as e:
            logger.warning(f"⚠️ [Ucppt] 语义判断失败: {e}")
            # 降级到数值判断
            return framework.overall_completeness >= self.completeness_threshold, "基于数值评估"
    
    # ==================== 搜索查询生成 ====================
    
    async def _generate_search_query(
        self,
        framework: AnswerFramework,
        target_aspect: KeyAspect,
        existing_sources: List[Dict[str, Any]],
    ) -> str:
        """
        生成搜索查询 - v7.214 智能关键词扩展
        
        新增功能：
        1. 基于用户画像的个性化关键词
        2. 上下文相关的语义扩展
        3. 动态查询多样化策略
        4. 质量驱动的查询优化
        """
        # 如果有预设的搜索提示，第一次使用它
        if target_aspect.search_query and target_aspect.last_searched_round == 0:
            base_query = f"{framework.original_query} {target_aspect.search_query}"
        else:
            base_query = framework.original_query
        
        # v7.214: 智能关键词扩展
        enhanced_query = await self._enhance_query_with_context(
            base_query,
            target_aspect,
            existing_sources,
            framework
        )
        
        return enhanced_query
    
    async def _enhance_query_with_context(
        self,
        base_query: str,
        target_aspect: KeyAspect,
        existing_sources: List[Dict[str, Any]],
        framework: AnswerFramework
    ) -> str:
        """
        基于上下文智能增强查询 - v7.214
        
        策略：
        1. 用户画像增强：基于地理位置、身份特征添加相关关键词
        2. 语义扩展：基于目标信息面进行专业术语扩展
        3. 多样化策略：避免重复搜索相同关键词
        4. 质量优化：基于之前搜索结果的质量调整策略
        """
        try:
            # 构建上下文信息
            context_info = self._build_query_context(target_aspect, existing_sources, framework)
            
            # 构建智能扩展提示
            prompt = f"""作为搜索专家，请对查询进行智能优化和关键词扩展。

## 基础查询
{base_query}

## 搜索目标
- 信息面：{target_aspect.aspect_name}
- 目标：{target_aspect.answer_goal}
- 已搜索轮次：{target_aspect.last_searched_round}

## 上下文信息
{context_info}

## 优化策略
1. **用户个性化**：根据用户特征添加相关限定词
2. **专业术语扩展**：添加领域相关的专业关键词
3. **地理本土化**：结合地理位置添加本地化关键词
4. **多样化策略**：{self._get_diversification_strategy(target_aspect.last_searched_round)}

## 输出要求
生成 1-2 个优化后的中文搜索查询（每个15-40字）：

```json
{{
    "primary_query": "主要优化查询",
    "alternative_query": "备选查询（可选）",
    "enhancement_strategy": "使用的优化策略说明",
    "expected_improvements": ["预期改进点1", "预期改进点2"]
}}
```"""

            # 调用 DeepSeek 进行智能扩展
            result = await self.deepseek_analysis_engine._deepseek_call(
                prompt, 
                self.deepseek_analysis_engine.thinking_model,
                max_tokens=500
            )
            
            if result:
                # 解析结果
                enhanced_data = self._safe_parse_json(result, "查询增强")
                if enhanced_data:
                    primary_query = enhanced_data.get("primary_query", base_query)
                    alternative_query = enhanced_data.get("alternative_query", "")
                    strategy = enhanced_data.get("enhancement_strategy", "")
                    
                    logger.info(f"🎯 [查询增强 v7.214] 策略: {strategy}")
                    
                    # 根据搜索轮次选择查询
                    if target_aspect.last_searched_round % 2 == 0:
                        selected_query = primary_query
                    else:
                        selected_query = alternative_query or primary_query
                    
                    # 记录查询历史避免重复
                    self._used_queries.append(selected_query)
                    return selected_query
            
            # 降级处理：使用基础多样化策略
            return self._apply_basic_diversification(base_query, target_aspect)
            
        except Exception as e:
            logger.warning(f"⚠️ [查询增强] 执行失败: {e}")
            return self._apply_basic_diversification(base_query, target_aspect)
    
    def _build_query_context(
        self, 
        target_aspect: KeyAspect, 
        existing_sources: List[Dict[str, Any]],
        framework: AnswerFramework
    ) -> str:
        """构建查询增强的上下文信息"""
        context_parts = []
        
        # 用户画像信息（如果有结构化分析结果）
        if self.analysis_session and self.analysis_session.l0_result:
            user_profile = self.analysis_session.l0_result.user_profile
            context_parts.append(f"**用户特征**: {user_profile.demographics}")
            
            implicit_needs = self.analysis_session.l0_result.implicit_needs
            if implicit_needs:
                context_parts.append(f"**隐性需求**: {', '.join(implicit_needs[:3])}")
        
        # 已收集信息质量
        if target_aspect.collected_info:
            context_parts.append(f"**已有信息**: {len(target_aspect.collected_info)} 条")
            context_parts.append(f"**信息预览**: {target_aspect.collected_info[-1][:100]}...")
        
        # 搜索历史反馈
        search_quality = self._assess_previous_search_quality(existing_sources)
        context_parts.append(f"**前轮质量**: {search_quality}")
        
        return "\n".join(context_parts) if context_parts else "无特殊上下文"
    
    def _get_diversification_strategy(self, round_number: int) -> str:
        """获取多样化策略说明"""
        strategies = [
            "使用同义词和相关概念替换",
            "添加具体的案例或实例关键词", 
            "使用更专业或更通俗的表达方式",
            "从不同角度重新组织关键词",
            "添加时间、地点等限定词"
        ]
        return strategies[round_number % len(strategies)]
    
    def _assess_previous_search_quality(self, sources: List[Dict[str, Any]]) -> str:
        """评估之前搜索结果的质量"""
        if not sources:
            return "首次搜索"
        
        # 简单的质量评估
        avg_content_length = sum(len(s.get("content", "")) for s in sources) / len(sources)
        unique_domains = len(set(s.get("siteName", "") for s in sources))
        
        if avg_content_length > 500 and unique_domains >= 3:
            return "高质量，需更精准"
        elif avg_content_length > 200:
            return "中等质量，可扩展"
        else:
            return "质量较低，需换角度"
    
    def _apply_basic_diversification(self, base_query: str, target_aspect: KeyAspect) -> str:
        """应用基础多样化策略"""
        round_number = target_aspect.last_searched_round
        
        # 策略1: 添加不同的修饰词
        modifiers = [
            "最新", "详细", "专业", "深度", "案例",
            "分析", "研究", "报告", "趋势", "实践"
        ]
        modifier = modifiers[round_number % len(modifiers)]
        
        # 策略2: 重组查询结构
        # 提取核心关键词（前20字）
        core_keywords = base_query[:20]
        aspect_keywords = target_aspect.aspect_name
        
        if round_number % 3 == 0:
            return f"{modifier} {core_keywords} {aspect_keywords}"
        elif round_number % 3 == 1:
            return f"{aspect_keywords} {core_keywords} {modifier}"
        else:
            return f"{core_keywords} {modifier} {aspect_keywords}"
    
    # ==================== 搜索执行 ====================
    
    async def _execute_search(self, query: str, retry_count: int = 2) -> List[Dict[str, Any]]:
        """
        执行搜索 - v7.214 自适应扩展版
        
        新增功能：
        1. 智能查询扩展：根据初始结果质量动态调整
        2. 多源并行搜索：根据查询类型选择合适的搜索源
        3. 质量驱动的递增搜索：结果不足时自动扩展
        4. 实时结果评估：边搜索边评估，达标即停
        """
        logger.info(f"🔍 [自适应搜索 v7.214] 开始执行: {query[:50]}...")
        
        all_sources: List[Dict[str, Any]] = []
        search_session = {
            "original_query": query,
            "attempts": 0,
            "quality_progression": [],
            "expansion_strategies": []
        }
        
        # 第一阶段：基础搜索
        initial_sources = await self._execute_basic_search(query, retry_count)
        all_sources.extend(initial_sources)
        search_session["attempts"] += 1
        
        if not initial_sources:
            logger.warning("⚠️ [自适应搜索] 基础搜索无结果，尝试查询扩展")
            expanded_queries = await self._generate_expanded_queries(query)
            
            for expanded_query in expanded_queries[:2]:  # 限制扩展次数
                expanded_sources = await self._execute_basic_search(expanded_query, 1)
                all_sources.extend(expanded_sources)
                search_session["attempts"] += 1
                search_session["expansion_strategies"].append(f"查询扩展: {expanded_query}")
                
                if expanded_sources:
                    break
        
        if not all_sources:
            logger.error("❌ [自适应搜索] 所有搜索策略均无结果")
            return []
        
        # 第二阶段：质量评估和自适应扩展
        current_quality = await self._assess_search_quality(all_sources, query)
        search_session["quality_progression"].append(current_quality)
        
        logger.info(f"📊 [质量评估] 初始质量: {current_quality['overall_score']:.1%}")
        
        # 如果质量不足，进行自适应扩展
        if (current_quality["overall_score"] < 0.6 and 
            search_session["attempts"] < 3):
            
            expansion_sources = await self._adaptive_search_expansion(
                query, all_sources, current_quality, search_session
            )
            all_sources.extend(expansion_sources)
        
        # 第三阶段：最终质量控制和结果优化
        final_results = await self.enhanced_quality_assessment(
            all_sources, query, "adaptive_search"
        )
        
        optimized_sources = final_results.get("filtered_results", all_sources)
        
        logger.info(
            f"🎯 [自适应搜索完成] "
            f"原始: {len(all_sources)} → 优化: {len(optimized_sources)} | "
            f"尝试次数: {search_session['attempts']} | "
            f"最终质量: {final_results.get('quality_metrics', {}).get('total_score', 0):.1%}"
        )
        
        return optimized_sources[:8]  # 限制返回数量
    
    async def _execute_basic_search(self, query: str, retry_count: int = 2) -> List[Dict[str, Any]]:
        """执行基础搜索（原有逻辑）"""
        all_sources: List[Dict[str, Any]] = []
        
        for attempt in range(retry_count + 1):
            try:
                if not self.bocha_service:
                    logger.warning("⚠️ [Ucppt] Bocha服务未初始化")
                    break
                
                logger.debug(f"🔍 [Ucppt] Bocha搜索 | query={query[:50]}...")
                
                # v7.233: Ucppt模式禁用图片搜索，避免不必要的API调用
                result = await self.bocha_service.search(
                    query=query,
                    count=10,
                    freshness="oneYear",
                    include_images=False,  # 禁用图片搜索
                )
                
                # 🆕 v7.237: 应用搜索质量过滤（方案B+C）
                sources = []
                for s in result.sources:
                    source = {
                        "title": s.title,
                        "url": s.url,
                        "content": s.snippet,  # 初始为 snippet
                        "siteName": s.site_name,
                        "_source_type": "bocha",
                    }
                    
                    # 质量过滤
                    if self._should_include_source(source, query):
                        sources.append(source)
                
                logger.info(f"✅ [Ucppt] Bocha搜索成功 | 原始结果={len(result.sources)} | 过滤后={len(sources)}")
                all_sources.extend(sources)
                break
                
            except Exception as e:
                logger.warning(f"⚠️ [Ucppt] Bocha搜索失败 (attempt {attempt+1}): {e}")
                if attempt < retry_count:
                    await asyncio.sleep(1)
                continue
        
        # v7.199: 学术类查询自动调用 OpenAlex
        if self._is_academic_query(query):
            openalex_sources = await self._search_openalex(query)
            all_sources.extend(openalex_sources)
        
        return all_sources
    
    async def _generate_expanded_queries(self, original_query: str) -> List[str]:
        """生成扩展查询 - v7.214"""
        try:
            prompt = f"""为搜索查询生成3个有效的扩展版本：

原始查询：{original_query}

扩展策略：
1. 同义词替换：使用相关概念替换关键词
2. 具体化：添加更具体的限定词
3. 角度转换：从不同角度重新组织查询

输出JSON格式：
```json
{{
    "expansions": [
        "扩展查询1",
        "扩展查询2", 
        "扩展查询3"
    ]
}}
```"""
            
            result = await self.deepseek_analysis_engine._deepseek_call(
                prompt,
                self.deepseek_analysis_engine.thinking_model,
                max_tokens=300
            )
            
            if result:
                data = self._safe_parse_json(result, "查询扩展")
                if data and "expansions" in data:
                    return data["expansions"]
        
        except Exception as e:
            logger.warning(f"⚠️ [查询扩展] 生成失败: {e}")
        
        # 降级处理：简单的关键词变换
        return [
            f"详细 {original_query}",
            f"{original_query} 案例",
            f"{original_query} 方法"
        ]
    
    async def _assess_search_quality(
        self, 
        sources: List[Dict[str, Any]], 
        query: str
    ) -> Dict[str, Any]:
        """评估搜索结果质量 - v7.214"""
        if not sources:
            return {
                "overall_score": 0.0,
                "relevance_score": 0.0,
                "diversity_score": 0.0,
                "completeness_score": 0.0,
                "issues": ["无搜索结果"]
            }
        
        # 1. 相关性评估
        relevance_scores = []
        for source in sources:
            content = source.get("content", "")
            title = source.get("title", "")
            combined_text = f"{title} {content}".lower()
            query_lower = query.lower()
            
            # 改进的关键词匹配评分
            # 方法1: 直接子串匹配（适用于中文短语）
            substring_match = 0
            if query_lower in combined_text:
                substring_match = 1.0
            elif len(query_lower) > 3:
                # 查找查询词的部分匹配
                partial_matches = sum(1 for i in range(len(query_lower) - 2) 
                                    if query_lower[i:i+3] in combined_text)
                substring_match = min(partial_matches / max(1, len(query_lower) - 2), 1.0)
            
            # 方法2: 词汇重叠评分
            query_words = set(query_lower.split())
            text_words = set(combined_text.split())
            word_overlap = 0
            if query_words:
                word_overlap = len(query_words & text_words) / len(query_words)
            
            # 综合相关性分数
            relevance_score = max(substring_match, word_overlap)
            relevance_scores.append(relevance_score)
        
        avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0
        
        # 2. 多样性评估
        unique_domains = len(set(s.get("siteName", "") for s in sources))
        diversity_score = min(unique_domains / 5, 1.0)  # 理想情况5个不同域名
        
        # 3. 完整性评估
        avg_content_length = sum(len(s.get("content", "")) for s in sources) / len(sources)
        completeness_score = min(avg_content_length / 200, 1.0)  # 理想情况200字以上
        
        # 综合评分
        overall_score = (
            avg_relevance * 0.5 +
            diversity_score * 0.3 +
            completeness_score * 0.2
        )
        
        # 识别问题
        issues = []
        if avg_relevance < 0.3:
            issues.append("相关性不足")
        if unique_domains < 3:
            issues.append("来源单一")
        if avg_content_length < 100:
            issues.append("内容过短")
        
        return {
            "overall_score": overall_score,
            "relevance_score": avg_relevance,
            "diversity_score": diversity_score,
            "completeness_score": completeness_score,
            "issues": issues
        }
    
    async def _adaptive_search_expansion(
        self,
        original_query: str,
        existing_sources: List[Dict[str, Any]],
        quality_assessment: Dict[str, Any],
        search_session: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """自适应搜索扩展 - v7.214"""
        logger.info("🔄 [自适应扩展] 基于质量评估进行搜索扩展")
        
        expansion_sources = []
        issues = quality_assessment.get("issues", [])
        
        # 根据具体问题选择扩展策略
        if "相关性不足" in issues:
            # 策略1：语义相关扩展
            semantic_queries = await self._generate_semantic_variants(original_query)
            for query_variant in semantic_queries[:2]:
                sources = await self._execute_basic_search(query_variant, 1)
                expansion_sources.extend(sources)
                search_session["expansion_strategies"].append(f"语义扩展: {query_variant}")
        
        if "来源单一" in issues:
            # 策略2：多源搜索
            if self._is_academic_query(original_query):
                academic_sources = await self._search_openalex(original_query)
                expansion_sources.extend(academic_sources)
                search_session["expansion_strategies"].append("学术源扩展")
        
        if "内容过短" in issues:
            # 策略3：深度内容获取（对现有结果进行内容提取）
            enhanced_sources = await self._enhance_content_extraction(existing_sources)
            expansion_sources.extend(enhanced_sources)
            search_session["expansion_strategies"].append("内容深度提取")
        
        logger.info(f"🔄 [自适应扩展] 新增 {len(expansion_sources)} 条结果")
        return expansion_sources
    
    async def _generate_semantic_variants(self, query: str) -> List[str]:
        """生成语义变体查询"""
        try:
            # 基于用户画像和上下文生成语义相关的查询变体
            if self.analysis_session and self.analysis_session.framework_result:
                l3_tensions = self.analysis_session.framework_result.l3_tensions
                l4_jtbd = self.analysis_session.framework_result.l4_jtbd
                
                context_prompt = f"""
基于以下上下文为查询生成语义相关的变体：

原查询：{query}
核心张力：{l3_tensions}
任务目标：{l4_jtbd}

生成3个从不同语义角度的查询变体：
1. 基于核心张力的查询
2. 基于任务目标的查询  
3. 基于相关概念的查询

JSON格式输出：
```json
{{
    "variants": ["变体1", "变体2", "变体3"]
}}
```"""
                
                result = await self.deepseek_analysis_engine._deepseek_call(
                    context_prompt,
                    self.deepseek_analysis_engine.thinking_model,
                    max_tokens=200
                )
                
                if result:
                    data = self._safe_parse_json(result, "语义变体生成")
                    if data and "variants" in data:
                        return data["variants"]
        
        except Exception as e:
            logger.warning(f"⚠️ [语义变体] 生成失败: {e}")
        
        # 降级处理
        return [
            f"如何 {query}",
            f"{query} 解决方案",
            f"{query} 最佳实践"
        ]
    
    async def _enhance_content_extraction(
        self, 
        sources: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """增强内容提取 - 对现有源进行深度内容获取"""
        enhanced_sources = []
        
        for source in sources[:3]:  # 限制处理数量
            if len(source.get("content", "")) > 300:
                continue  # 已经有足够内容
            
            try:
                # 这里可以集成 Playwright 或其他工具进行深度内容提取
                # 暂时用模拟的方式
                enhanced_content = await self._extract_detailed_content(source.get("url", ""))
                if enhanced_content:
                    enhanced_source = source.copy()
                    enhanced_source["content"] = enhanced_content
                    enhanced_source["_enhanced"] = True
                    enhanced_sources.append(enhanced_source)
            
            except Exception as e:
                logger.debug(f"⚠️ [内容提取] URL {source.get('url', '')} 提取失败: {e}")
                continue
        
        return enhanced_sources
    
    async def _extract_detailed_content(self, url: str) -> Optional[str]:
        """详细内容提取（模拟实现）"""
        # 这里应该集成实际的内容提取工具
        # 暂时返回 None，表示功能占位
        return None
    
    def _is_academic_query(self, query: str = None) -> bool:
        """判断是否为学术查询 - v7.214 增强"""
        if query is None and hasattr(self, '_query_classification'):
            return self._query_classification and self._query_classification.query_type.value == "academic"
        
        if query:
            academic_keywords = [
                "研究", "论文", "学术", "理论", "模型", "算法",
                "实验", "数据", "分析", "方法论", "文献"
            ]
            return any(keyword in query for keyword in academic_keywords)
        
        return False
    

    
    async def _search_openalex(self, query: str) -> List[Dict[str, Any]]:
        """v7.199: 调用 OpenAlex 学术搜索"""
        if not self.openalex_tool:
            return []
        
        try:
            logger.info(f"🎓 [Ucppt v7.199] OpenAlex 学术搜索 | query={query[:50]}...")
            
            result = self.openalex_tool.search(
                query=query,
                max_results=5,
                from_year=2020,  # 近5年
            )
            
            # OpenAlex 返回格式: {"status": "success", "results": [...]}
            papers = result.get("results", [])
            sources = []
            
            for paper in papers:
                sources.append({
                    "title": paper.get("title", ""),
                    "url": paper.get("url", ""),
                    "content": paper.get("abstract", ""),
                    "siteName": paper.get("venue", "OpenAlex"),
                    "_source_type": "openalex",
                    "_cited_by": paper.get("cited_by_count", 0),
                    "_year": paper.get("publication_year"),
                })
            
            logger.info(f"✅ [Ucppt v7.199] OpenAlex 搜索成功 | 结果数={len(sources)}")
            return sources
            
        except Exception as e:
            logger.warning(f"⚠️ [Ucppt v7.199] OpenAlex 搜索失败: {e}")
            return []
    
    async def _enhance_sources_with_deep_content(
        self,
        sources: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        v7.195: 对搜索结果进行深度内容提取
        
        策略：
        - 只对 Top-N 个来源进行深度提取（避免延迟过长）
        - 使用混合方案：Trafilatura(静态) + Playwright(动态)
        - 提取失败则保留原 snippet
        """
        if not get_web_content_extractor:
            return sources
        
        extractor = get_web_content_extractor()
        
        # 只提取前 N 个
        urls_to_extract = [s.get("url") for s in sources[:DEEP_CONTENT_TOP_N] if s.get("url")]
        
        if not urls_to_extract:
            return sources
        
        logger.info(f"🔍 [Ucppt v7.195] 深度内容提取 | URLs={len(urls_to_extract)}")
        
        try:
            # 批量提取
            extraction_results = await extractor.extract_batch(
                urls=urls_to_extract,
                max_concurrent=3,
                max_urls=DEEP_CONTENT_TOP_N,
            )
            
            # 更新来源内容
            enhanced_count = 0
            for source in sources:
                url = source.get("url")
                if url and url in extraction_results:
                    result = extraction_results[url]
                    if result.content and len(result.content) > len(source.get("content", "")):
                        source["content"] = result.content
                        source["_extraction_method"] = result.method.value if result.method else "unknown"
                        enhanced_count += 1
            
            logger.info(f"✅ [Ucppt v7.195] 深度提取完成 | 增强={enhanced_count}/{len(urls_to_extract)}")
            
        except Exception as e:
            logger.warning(f"⚠️ [Ucppt v7.195] 深度提取异常: {e}")
        
        return sources
    
    # ==================== v7.212: 搜索结果质量筛选 ====================
    
    def _calculate_source_quality_score(
        self,
        source: Dict[str, Any],
        query: str,
        whitelist_domains: set = None,
        graylist_domains: set = None,
    ) -> float:
        """
        v7.227: 计算单条搜索结果的质量评分 (0-1)
        
        评分维度：
        - 内容长度权重 (0.15)：内容 >50 字得分高（降低要求）
        - 关键词匹配 (0.35)：与查询关键词的重叠度（支持中文）
        - 来源可信度 (0.3)：白名单站点加分，灰名单减分
        - 内容完整性 (0.2)：是否有标题、摘要、正文
        """
        score = 0.0
        
        content = source.get("content", "") or ""
        title = source.get("title", "") or ""
        url = source.get("url", "") or ""
        site_name = source.get("siteName", "") or ""
        
        # 1. 内容长度权重 (0.15) - v7.227: 降低阈值以适应 snippet
        content_len = len(content)
        if content_len >= 200:
            score += 0.15
        elif content_len >= 100:
            score += 0.12
        elif content_len >= 50:
            score += 0.1
        elif content_len >= 20:
            score += 0.08
        elif content_len > 0:
            score += 0.05  # 只要有内容就给基础分
        
        # 2. 关键词匹配 (0.35) - v7.227: 支持中文字符匹配
        # 提取查询中的中文词汇和英文单词
        import re
        # 中文词（2-4字）和英文单词
        query_words = re.findall(r'[\u4e00-\u9fff]{2,4}|[a-zA-Z]+', query.lower())
        content_lower = (content + " " + title).lower()
        
        if query_words:
            matched = sum(1 for word in query_words if word in content_lower)
            keyword_ratio = matched / len(query_words)
            score += keyword_ratio * 0.35
        else:
            # 如果没有提取到词汇，检查整个查询字符串的子串匹配
            if any(c in content_lower for c in query[:10]):
                score += 0.15
        
        # 3. 来源可信度 (0.3)
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.lower()
        except:
            domain = ""
        
        # 白名单域名加分
        if whitelist_domains and any(wd in domain for wd in whitelist_domains):
            score += 0.3
        # 灰名单域名减分
        elif graylist_domains and any(gd in domain for gd in graylist_domains):
            score += 0.1  # 降低分数但不完全排除
        # 学术来源加分
        elif source.get("_source_type") == "openalex":
            score += 0.28
        # 普通来源
        else:
            # 有明确站点名称
            if site_name and len(site_name) > 2:
                score += 0.2
            else:
                score += 0.15
        
        # 4. 内容完整性 (0.2)
        completeness = 0.0
        if title and len(title) > 5:
            completeness += 0.07
        if content and len(content) > 50:
            completeness += 0.08
        if url and url.startswith("http"):
            completeness += 0.05
        score += completeness
        
        return min(score, 1.0)
    
    def _filter_sources_by_quality(
        self,
        sources: List[Dict[str, Any]],
        query: str,
        threshold: float = None,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        v7.212: 根据质量评分筛选搜索结果
        
        Args:
            sources: 原始搜索结果
            query: 搜索查询
            threshold: 质量阈值（默认使用配置）
            
        Returns:
            (通过筛选的结果, 被过滤的结果)
        """
        if threshold is None:
            threshold = SEARCH_QUALITY_THRESHOLD
        
        # 获取白/灰名单域名
        whitelist_domains = self._get_whitelist_domains()
        graylist_domains = self._get_graylist_domains()
        
        passed = []
        filtered = []
        
        for source in sources:
            score = self._calculate_source_quality_score(
                source, query, whitelist_domains, graylist_domains
            )
            source["_quality_score"] = score  # 添加评分字段
            
            if score >= threshold:
                passed.append(source)
            else:
                filtered.append(source)
                # v7.227: 诊断日志 - 显示被过滤的原因
                logger.debug(f"🚫 [v7.227] 过滤: score={score:.2f} < {threshold} | {source.get('title', '无标题')[:30]}")
        
        # 按评分排序
        passed.sort(key=lambda x: x.get("_quality_score", 0), reverse=True)
        
        # v7.227: 增强日志，显示通过和过滤的详情
        if sources:
            scores = [s.get("_quality_score", 0) for s in sources]
            logger.info(f"🎯 [v7.227] 质量筛选: {len(sources)} → {len(passed)} | 阈值={threshold} | 评分范围=[{min(scores):.2f}, {max(scores):.2f}]")
        
        return passed, filtered
    
    def _get_whitelist_domains(self) -> set:
        """获取白名单域名集合"""
        try:
            from intelligent_project_analyzer.services.search_filter_manager import get_filter_manager
            manager = get_filter_manager()
            if manager:
                whitelist = manager.get_whitelist()
                return {item.get("domain", "") for item in whitelist if item.get("domain")}
        except:
            pass
        return set()
    
    def _get_graylist_domains(self) -> set:
        """获取灰名单域名集合"""
        try:
            from intelligent_project_analyzer.services.search_filter_manager import get_filter_manager
            manager = get_filter_manager()
            if manager:
                graylist = manager.get_graylist()
                return {item.get("domain", "") for item in graylist if item.get("domain")}
        except:
            pass
        return set()
    
    def _generate_supplement_query(
        self,
        original_query: str,
        attempt: int,
        target_aspect: Optional[Any] = None,
        is_empty_retry: bool = False,
    ) -> str:
        """
        v7.227: 增强版补充搜索查询生成
        
        策略：
        - 普通补充：添加限定词
        - 空结果重试：简化查询、提取核心关键词、尝试不同表述
        """
        import re
        
        if is_empty_retry:
            # v7.227: 空结果时的激进简化策略
            simplify_strategies = [
                # 策略1: 提取前2-3个中文词组
                lambda q: " ".join(re.findall(r'[\u4e00-\u9fff]{2,4}', q)[:3]),
                # 策略2: 只保留核心名词
                lambda q: " ".join(re.findall(r'[\u4e00-\u9fff]{2,4}', q)[:2]) + " 是什么",
                # 策略3: 添加通用后缀
                lambda q: " ".join(re.findall(r'[\u4e00-\u9fff]{2,4}', q)[:2]) + " 介绍",
                # 策略4: 使用信息面名称
                lambda q: getattr(target_aspect, 'aspect_name', '') if target_aspect else q[:10],
                # 策略5: 极简核心词
                lambda q: re.findall(r'[\u4e00-\u9fff]{2,4}', q)[0] if re.findall(r'[\u4e00-\u9fff]{2,4}', q) else q[:8],
            ]
            
            if attempt < len(simplify_strategies):
                try:
                    simplified = simplify_strategies[attempt](original_query)
                    if simplified and len(simplified) >= 2:
                        logger.info(f"🔄 [v7.227] 空结果重试策略 #{attempt+1}: '{original_query[:20]}' → '{simplified}'")
                        return simplified
                except:
                    pass
            
            # 降级：使用信息面名称
            if target_aspect and hasattr(target_aspect, "aspect_name"):
                return target_aspect.aspect_name
            return original_query[:15]
        
        # 普通补充搜索
        suffixes = [
            "案例分析 专业解读",
            "深度研究 专家观点", 
            "最新资讯 权威媒体",
            "定义 概念 解释",
            "教程 指南 入门",
        ]
        
        if attempt < len(suffixes):
            supplement = f"{original_query} {suffixes[attempt]}"
        else:
            supplement = f"{original_query} 详细解析"
        
        # 如果有目标信息面，加入更具体的上下文
        if target_aspect and hasattr(target_aspect, "aspect_name"):
            supplement = f"{supplement} {target_aspect.aspect_name}"
        
        return supplement
    
    def _generate_query_variants(
        self,
        query: str,
        target_aspect: Optional[Any] = None,
    ) -> List[str]:
        """
        v7.228: 生成查询变体用于并行搜索
        
        策略：
        1. 原始查询
        2. 核心词提取版
        3. 信息面聚焦版
        
        v7.233: 增强空查询保护
        """
        import re
        
        # v7.233: 空查询保护 - 如果原始查询为空或过短，尝试从 target_aspect 获取
        if not query or len(query.strip()) < 3:
            if target_aspect:
                # 尝试从 target_aspect 获取名称作为查询
                if hasattr(target_aspect, 'name') and target_aspect.name:
                    query = f"{target_aspect.name} 详细介绍"
                    logger.warning(f"⚠️ [v7.233] 原始查询为空，使用目标名称: {query}")
                elif hasattr(target_aspect, 'aspect_name') and target_aspect.aspect_name:
                    query = f"{target_aspect.aspect_name} 详细介绍"
                    logger.warning(f"⚠️ [v7.233] 原始查询为空，使用信息面名称: {query}")
            
            # 仍然为空则使用通用查询
            if not query or len(query.strip()) < 3:
                query = "设计趋势 2024"
                logger.warning(f"⚠️ [v7.233] 无法获取有效查询，使用通用查询: {query}")
        
        variants = [query]  # 原始查询
        
        # 提取中文关键词（2-4字词组）
        chinese_words = re.findall(r'[\u4e00-\u9fff]{2,4}', query)
        
        # 变体2: 核心词版本（前3个关键词）
        if len(chinese_words) >= 2:
            core_query = " ".join(chinese_words[:3])
            if core_query != query and len(core_query) >= 4:
                variants.append(core_query)
        
        # 变体3: 信息面聚焦版本
        if target_aspect and hasattr(target_aspect, "aspect_name"):
            aspect_name = target_aspect.aspect_name
            if chinese_words:
                aspect_query = f"{chinese_words[0]} {aspect_name}"
                if aspect_query not in variants:
                    variants.append(aspect_query)
        
        # 变体4: 添加通用限定词
        if len(variants) < 3 and chinese_words:
            general_query = f"{chinese_words[0] if chinese_words else query[:8]} 是什么 定义"
            if general_query not in variants:
                variants.append(general_query)
        
        logger.info(f"🔄 [v7.228] 生成 {len(variants)} 个查询变体: {[q[:20] for q in variants]}")
        return variants[:3]  # 最多3个变体
    
    async def _execute_parallel_search(
        self,
        queries: List[str],
    ) -> List[Dict[str, Any]]:
        """
        v7.228: 并行执行多个搜索查询
        
        同时发起多个搜索请求，合并去重结果
        
        v7.233: 增强空查询过滤，避免 API 400 错误
        """
        if not queries:
            return []
        
        # v7.233: 过滤掉空查询或过短的查询
        valid_queries = [q for q in queries if q and len(q.strip()) >= 2]
        if not valid_queries:
            logger.warning(f"⚠️ [v7.233] 所有查询都无效（空或过短），跳过搜索")
            return []
        
        if len(valid_queries) < len(queries):
            logger.warning(f"⚠️ [v7.233] 过滤掉 {len(queries) - len(valid_queries)} 个无效查询")
        
        logger.info(f"🚀 [v7.228] 并行搜索 {len(valid_queries)} 个查询...")
        
        # 并行执行所有搜索 - v7.233: 使用过滤后的有效查询
        tasks = [self._execute_basic_search(q, retry_count=1) for q in valid_queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 合并去重
        all_sources: List[Dict[str, Any]] = []
        seen_urls: set = set()
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"⚠️ [v7.228] 查询 {i+1} 失败: {result}")
                continue
            
            for src in result:
                url = src.get("url", "")
                if url and url not in seen_urls:
                    all_sources.append(src)
                    seen_urls.add(url)
        
        logger.info(f"✅ [v7.228] 并行搜索完成 | 合并后来源={len(all_sources)}")
        return all_sources
    
    async def _execute_search_with_quality_filter(
        self,
        query: str,
        target_aspect: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """
        v7.228: 多查询并行搜索 + 质量筛选 + 空结果重试
        
        1. 生成多个查询变体
        2. 并行执行搜索
        3. 合并去重结果
        4. 规则评分筛选
        5. 如果结果不足，补充搜索
        6. 如果结果为空，激进简化重试
        """
        all_quality_sources: List[Dict[str, Any]] = []
        seen_urls: set = set()
        
        # v7.228: 生成查询变体并并行搜索
        query_variants = self._generate_query_variants(query, target_aspect)
        raw_sources = await self._execute_parallel_search(query_variants)
        
        logger.info(f"📥 [v7.228 诊断] 并行搜索原始结果: {len(raw_sources)}条 | 查询数={len(query_variants)}")
        
        # 质量筛选（使用原始查询匹配）
        quality_sources, _ = self._filter_sources_by_quality(raw_sources, query)
        logger.info(f"📥 [v7.228 诊断] 质量筛选后: {len(quality_sources)}条 (原始{len(raw_sources)}条)")
        
        # v7.212: LLM 二次过滤（在规则筛选后进行）
        if SEARCH_QUALITY_LLM_FILTER and quality_sources:
            quality_sources = await self._llm_filter_sources(
                quality_sources, query, target_aspect
            )
        
        # 去重并收集
        for src in quality_sources:
            url = src.get("url", "")
            if url and url not in seen_urls:
                all_quality_sources.append(src)
                seen_urls.add(url)
        
        # v7.227: 如果结果完全为空，使用激进的简化策略重试
        empty_retry_attempt = 0
        MAX_EMPTY_RETRIES = 5
        while len(all_quality_sources) == 0 and empty_retry_attempt < MAX_EMPTY_RETRIES:
            empty_retry_attempt += 1
            simplified_query = self._generate_supplement_query(
                query, empty_retry_attempt - 1, target_aspect, is_empty_retry=True
            )

            # v7.235: 验证查询有效性
            if not self._validate_search_query(simplified_query, f"空结果重试#{empty_retry_attempt}"):
                logger.error(f"❌ [v7.235] 重试查询无效，停止重试: '{simplified_query}'")
                break  # 退出重试循环

            logger.warning(
                f"🔄 [v7.227] 空结果激进重试 #{empty_retry_attempt}/{MAX_EMPTY_RETRIES} | "
                f"简化查询: '{simplified_query}'"
            )

            retry_sources = await self._execute_search(simplified_query)
            # 对简化查询使用更宽松的筛选（使用简化后的查询匹配）
            quality_retry, _ = self._filter_sources_by_quality(retry_sources, simplified_query)

            for src in quality_retry:
                url = src.get("url", "")
                if url and url not in seen_urls:
                    all_quality_sources.append(src)
                    seen_urls.add(url)

            if all_quality_sources:
                logger.info(f"✅ [v7.227] 空结果重试成功！找到 {len(all_quality_sources)} 条来源")
                break
        
        # 常规补充搜索（结果不足时）
        supplement_attempt = 0
        while (
            len(all_quality_sources) < SEARCH_MIN_QUALITY_SOURCES
            and supplement_attempt < SEARCH_SUPPLEMENT_MAX_RETRIES
        ):
            supplement_attempt += 1
            supplement_query = self._generate_supplement_query(
                query, supplement_attempt - 1, target_aspect, is_empty_retry=False
            )
            
            logger.info(
                f"🔄 [Ucppt v7.212] 补充搜索 #{supplement_attempt} | "
                f"当前高质量来源={len(all_quality_sources)}, 目标={SEARCH_MIN_QUALITY_SOURCES}"
            )
            
            supplement_sources = await self._execute_search(supplement_query)
            quality_supplement, _ = self._filter_sources_by_quality(supplement_sources, query)
            
            # v7.212: 补充结果也进行 LLM 过滤
            if SEARCH_QUALITY_LLM_FILTER and quality_supplement:
                quality_supplement = await self._llm_filter_sources(
                    quality_supplement, query, target_aspect
                )
            
            # 去重并收集
            added_count = 0
            for src in quality_supplement:
                url = src.get("url", "")
                if url and url not in seen_urls:
                    all_quality_sources.append(src)
                    seen_urls.add(url)
                    added_count += 1
            
            logger.debug(f"📥 [Ucppt v7.212] 补充搜索新增 {added_count} 条高质量来源")
            
            # 如果补充搜索没有新增任何内容，提前退出
            if added_count == 0:
                logger.info(f"⚠️ [Ucppt v7.212] 补充搜索无新增结果，停止补充")
                break
        
        # 最终按质量评分排序
        all_quality_sources.sort(key=lambda x: x.get("_quality_score", 0), reverse=True)
        
        logger.info(
            f"✅ [Ucppt v7.228] 质量筛选完成 | "
            f"最终高质量来源={len(all_quality_sources)}, 并行查询={len(query_variants)}, 空结果重试={empty_retry_attempt}, 补充轮次={supplement_attempt}"
        )
        
        return all_quality_sources

    # ==================== v7.246: 并行主线搜索 ====================

    async def _search_single_mainline(
        self,
        target: SearchTarget,
        all_sources: List[Dict[str, Any]],
        seen_urls: set,
    ) -> Dict[str, Any]:
        """
        v7.246: 搜索单条主线

        为并行主线搜索提供的单主线搜索方法

        Args:
            target: 搜索目标
            all_sources: 全局来源列表（用于去重）
            seen_urls: 已见URL集合（用于去重）

        Returns:
            搜索结果字典，包含来源和状态
        """
        query = target.question or target.name or target.search_for or target.description
        if not query:
            logger.warning(f"⚠️ [v7.246] 主线 {target.id} 无有效查询，跳过")
            return {"target_id": target.id, "sources": [], "status": "skipped"}

        target_desc = query[:40]
        logger.info(f"🔍 [v7.246] 搜索主线: {target_desc}...")

        try:
            # 执行搜索
            round_sources = await self._execute_search_with_quality_filter(query, target)

            # 去重
            new_sources = []
            for src in round_sources:
                url = src.get("url", "")
                if url and url not in seen_urls:
                    new_sources.append(src)
                    seen_urls.add(url)

            # 更新目标状态
            if len(new_sources) >= 3:
                target.status = "complete"
                target.completion_score = min(1.0, target.completion_score + 0.3)
            elif len(new_sources) > 0:
                target.status = "partial"
                target.completion_score = min(1.0, target.completion_score + 0.15)
            else:
                target.status = "missing"

            logger.info(f"✅ [v7.246] 主线 {target_desc[:20]} 完成 | 新增来源={len(new_sources)}, 状态={target.status}")

            return {
                "target_id": target.id,
                "target_name": target_desc,
                "sources": new_sources,
                "status": target.status,
                "completion_score": target.completion_score,
            }

        except Exception as e:
            logger.error(f"❌ [v7.246] 主线 {target_desc[:20]} 搜索失败: {e}")
            return {"target_id": target.id, "sources": [], "status": "error", "error": str(e)}

    async def _execute_parallel_mainlines(
        self,
        framework: SearchFramework,
        all_sources: List[Dict[str, Any]],
        seen_urls: set,
    ) -> List[Dict[str, Any]]:
        """
        v7.246: 并行执行所有主线搜索

        策略：
        1. 获取所有未完成的主线目标（非延展任务）
        2. 限制并行数量（MAX_PARALLEL_MAINLINES）
        3. 使用 asyncio.gather 并行执行
        4. 合并去重结果

        Args:
            framework: 搜索框架
            all_sources: 全局来源列表
            seen_urls: 已见URL集合

        Returns:
            所有主线的搜索结果列表
        """
        # 获取未完成的主线目标
        mainline_targets = framework.get_mainline_targets()

        if not mainline_targets:
            logger.info(f"📋 [v7.246] 无未完成的主线目标")
            return []

        # 限制并行数量
        targets_to_search = mainline_targets[:MAX_PARALLEL_MAINLINES]

        logger.info(f"🚀 [v7.246] 并行搜索 {len(targets_to_search)} 条主线（共 {len(mainline_targets)} 条未完成）...")

        # 创建并行任务
        tasks = [
            self._search_single_mainline(target, all_sources, seen_urls)
            for target in targets_to_search
        ]

        # 并行执行
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理结果
        all_results = []
        total_new_sources = 0

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"⚠️ [v7.246] 主线 {i+1} 执行异常: {result}")
                continue

            all_results.append(result)
            new_sources = result.get("sources", [])
            total_new_sources += len(new_sources)

            # 将新来源添加到全局列表
            all_sources.extend(new_sources)

        logger.info(f"✅ [v7.246] 并行主线搜索完成 | 主线数={len(all_results)}, 新增来源={total_new_sources}")

        # 更新框架完成度
        framework.update_completeness()

        return all_results

    # ==================== v7.246: 动态延展评估 ====================

    async def _evaluate_extension_need(
        self,
        framework: SearchFramework,
        all_sources: List[Dict[str, Any]],
        current_round: int,
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        v7.246: 评估是否需要延展搜索

        评估标准：
        1. 信息覆盖度 < EXTENSION_COVERAGE_THRESHOLD
        2. 发现新的信息缺口
        3. 搜索结果中出现新的关键词/概念

        Args:
            framework: 搜索框架
            all_sources: 已收集的所有来源
            current_round: 当前轮次

        Returns:
            (是否需要延展, 延展点列表)
        """
        # 检查延展次数限制
        extension_count = framework.get_extension_count()
        if extension_count >= MAX_EXTENSION_ROUNDS:
            logger.info(f"📋 [v7.246] 已达最大延展次数 {MAX_EXTENSION_ROUNDS}，不再延展")
            return False, []

        # 计算当前信息覆盖度
        coverage = framework.overall_completeness

        # 覆盖度足够，不需要延展
        if coverage >= 0.85:
            logger.info(f"📋 [v7.246] 覆盖度 {coverage:.2%} >= 85%，不需要延展")
            return False, []

        # 覆盖度较高但未达标，检查是否有明显缺口
        if coverage >= EXTENSION_COVERAGE_THRESHOLD:
            logger.info(f"📋 [v7.246] 覆盖度 {coverage:.2%} >= {EXTENSION_COVERAGE_THRESHOLD:.0%}，使用 LLM 评估是否需要延展")

        # 整理已搜索主线
        mainlines_summary = []
        for t in framework.targets:
            if t.category != "延展":
                status_emoji = {"complete": "✅", "partial": "🔄", "pending": "⏳", "missing": "❌"}.get(t.status, "❓")
                mainlines_summary.append(f"{status_emoji} {t.name or t.question or t.search_for}: {t.status} ({t.completion_score:.0%})")

        # 整理已收集信息摘要
        sources_summary = []
        for src in all_sources[:10]:
            sources_summary.append(f"- {src.get('title', '无标题')[:50]}")

        prompt = f"""评估当前搜索是否需要延展。

## 用户问题
{framework.original_query}

## 已搜索主线
{chr(10).join(mainlines_summary)}

## 当前覆盖度
{coverage:.2%}

## 已收集信息源（前10条）
{chr(10).join(sources_summary) if sources_summary else "暂无"}

## 当前轮次
第 {current_round} 轮

## 已延展次数
{extension_count} / {MAX_EXTENSION_ROUNDS}

## 任务
1. 判断是否存在明显的信息缺口
2. 如果需要延展，给出具体的延展方向（最多2个）
3. 延展方向应该是主线未覆盖的、对回答问题有价值的新角度

## 输出格式（JSON）
```json
{{
    "needs_extension": true,
    "reason": "判断理由（简洁）",
    "extension_points": [
        {{
            "name": "延展方向名称（10字内）",
            "description": "具体描述（30字内）",
            "purpose": "为什么需要这个延展（20字内）"
        }}
    ]
}}
```

只输出JSON。"""

        try:
            result = await self._call_deepseek(prompt, model=self.eval_model, max_tokens=500)
            data = self._safe_parse_json(result, context="延展评估(v7.246)")

            if data is None:
                logger.warning(f"⚠️ [v7.246] 延展评估 JSON 解析失败")
                return False, []

            needs_extension = data.get("needs_extension", False)
            extension_points = data.get("extension_points", [])
            reason = data.get("reason", "")

            if needs_extension and extension_points:
                logger.info(f"🔄 [v7.246] 需要延展 | 原因: {reason[:50]} | 延展点数: {len(extension_points)}")
                return True, extension_points[:2]  # 最多2个延展点
            else:
                logger.info(f"📋 [v7.246] 不需要延展 | 原因: {reason[:50]}")
                return False, []

        except Exception as e:
            logger.error(f"❌ [v7.246] 延展评估失败: {e}")
            return False, []

    async def _add_extension_targets(
        self,
        framework: SearchFramework,
        extension_points: List[Dict[str, Any]],
        current_round: int,
    ) -> List[SearchTarget]:
        """
        v7.246: 添加延展目标到框架

        Args:
            framework: 搜索框架
            extension_points: 延展点列表
            current_round: 当前轮次

        Returns:
            新添加的延展目标列表
        """
        new_targets = []

        for i, ext_point in enumerate(extension_points):
            ext_target = SearchTarget(
                id=f"ext_{current_round}_{i+1}",
                name=ext_point.get("name", f"延展{i+1}"),
                description=ext_point.get("description", ""),
                purpose=ext_point.get("purpose", ""),
                priority=3,  # 延展任务优先级较低
                category="延展",
            )
            framework.targets.append(ext_target)
            new_targets.append(ext_target)
            logger.info(f"🔄 [v7.246] 添加延展目标: {ext_target.name}")

        return new_targets

    async def _execute_serial_extensions(
        self,
        framework: SearchFramework,
        all_sources: List[Dict[str, Any]],
        seen_urls: set,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        v7.246: 串行执行延展任务

        主线并行完成后，串行执行延展任务

        Args:
            framework: 搜索框架
            all_sources: 全局来源列表
            seen_urls: 已见URL集合

        Yields:
            延展搜索事件
        """
        extension_targets = framework.get_extension_targets()

        if not extension_targets:
            return

        logger.info(f"📎 [v7.246] 开始串行执行 {len(extension_targets)} 个延展任务...")

        for ext_target in extension_targets:
            ext_name = ext_target.name or ext_target.description or f"延展{ext_target.id}"
            logger.info(f"📎 [v7.246] 串行执行延展: {ext_name[:30]}...")

            # 发送延展开始事件
            yield {
                "type": "extension_start",
                "data": {
                    "target_id": ext_target.id,
                    "target_name": ext_name,
                    "message": f"开始延展搜索: {ext_name[:30]}",
                }
            }

            # 执行搜索
            result = await self._search_single_mainline(ext_target, all_sources, seen_urls)

            # 将新来源添加到全局列表
            new_sources = result.get("sources", [])
            all_sources.extend(new_sources)

            # 发送延展完成事件
            yield {
                "type": "extension_complete",
                "data": {
                    "target_id": ext_target.id,
                    "target_name": ext_name,
                    "new_sources_count": len(new_sources),
                    "status": result.get("status", "unknown"),
                    "message": f"延展搜索完成: {ext_name[:30]} | 新增 {len(new_sources)} 条来源",
                }
            }

            # 更新框架完成度
            framework.update_completeness()

            # 检查是否可以提前结束
            if framework.overall_completeness >= 0.9:
                logger.info(f"✅ [v7.246] 覆盖度达到 {framework.overall_completeness:.2%}，停止延展")
                break

        logger.info(f"✅ [v7.246] 串行延展执行完成")

    # ==================== 评估与更新 ====================
    
    async def _llm_filter_sources(
        self,
        sources: List[Dict[str, Any]],
        query: str,
        target_aspect: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """
        v7.212: LLM 二次过滤 - 判断搜索结果与查询的相关性
        
        只保留与查询高度相关的来源
        """
        if not SEARCH_QUALITY_LLM_FILTER:
            return sources
        
        if not sources:
            return sources
        
        # 构建来源摘要
        sources_list = []
        for i, src in enumerate(sources[:10]):  # 最多评估10条
            sources_list.append(f"{i+1}. [{src.get('title', '无标题')}] {src.get('content', '')[:150]}")
        
        sources_text = "\n".join(sources_list)
        
        aspect_info = ""
        if target_aspect and hasattr(target_aspect, "aspect_name"):
            aspect_info = f"\n## 信息面目标\n{target_aspect.aspect_name}: {getattr(target_aspect, 'answer_goal', '')}"
        
        prompt = f"""判断以下搜索结果与用户查询的相关性。

## 用户查询
{query}
{aspect_info}

## 搜索结果
{sources_text}

## 任务
判断每条结果是否与查询高度相关。只返回相关的结果编号。

## 输出格式（JSON）
```json
{{
    "relevant_ids": [1, 3, 5],
    "reasoning": "简要说明筛选理由"
}}
```

只输出JSON。"""

        try:
            result = await self._call_deepseek(prompt, model=self.eval_model, max_tokens=300)
            data = self._safe_parse_json(result, context="LLM来源过滤")
            
            if data is None:
                return sources
            
            relevant_ids = data.get("relevant_ids", [])
            if not relevant_ids:
                return sources
            
            # 筛选相关来源
            filtered = []
            for i, src in enumerate(sources[:10]):
                if (i + 1) in relevant_ids:
                    filtered.append(src)
            
            # 保留未评估的来源（第10条之后）
            if len(sources) > 10:
                filtered.extend(sources[10:])
            
            if len(filtered) < len(sources):
                logger.info(
                    f"🎯 [Ucppt v7.212] LLM二次过滤: {len(sources)} → {len(filtered)} "
                    f"(理由: {data.get('reasoning', 'N/A')[:50]})"
                )
            
            return filtered
            
        except Exception as e:
            logger.warning(f"⚠️ [Ucppt v7.212] LLM过滤失败: {e}")
            return sources
    
    async def _evaluate_and_update(
        self,
        framework: AnswerFramework,
        target_aspect: KeyAspect,
        new_sources: List[Dict[str, Any]],
    ) -> None:
        """
        评估搜索结果并更新框架 - 目标导向评估
        
        不是问"发现了什么"，而是问"这对回答问题有多大帮助"
        """
        if not new_sources:
            return
        
        # 提取搜索结果的关键信息
        sources_summary = "\n".join([
            f"- {s.get('title', '')}: {s.get('content', '')[:100]}"
            for s in new_sources[:5]
        ])
        
        prompt = f"""评估搜索结果对回答问题的贡献。

## 用户问题
{framework.original_query}

## 回答目标
{framework.answer_goal}

## 当前搜索的信息面
- 名称：{target_aspect.aspect_name}
- 目标：{target_aspect.answer_goal}

## 搜索结果
{sources_summary}

## 任务
1. 从搜索结果中提取对回答有用的信息（2-3条关键点）
2. 评估这些信息对该信息面的完成度贡献（0-1，1表示完全满足）
3. 判断该信息面的状态

## 输出格式（JSON）
```json
{{
    "useful_info": ["关键信息点1", "关键信息点2"],
    "completion_contribution": 0.6,
    "status": "partial",
    "reasoning": "为什么这样评估"
}}
```

status可选值：missing（没有有用信息）、partial（有部分有用信息）、complete（信息充分）

只输出JSON。"""

        try:
            # v7.187: 使用 DeepSeek 官方 API
            result = await self._call_deepseek(prompt, model=self.eval_model, max_tokens=500)
            
            # v7.200: 使用统一 JSON 解析器
            data = self._safe_parse_json(result, context="信息面更新")
            if data is None:
                raise ValueError("无法解析信息面更新结果")
            
            # 更新信息面
            useful_info = data.get("useful_info", [])
            target_aspect.collected_info.extend(useful_info)
            target_aspect.source_urls.extend([s.get("url", "") for s in new_sources[:3]])
            
            contribution = data.get("completion_contribution", 0.3)
            target_aspect.completion_score = min(1.0, target_aspect.completion_score + contribution)
            target_aspect.status = data.get("status", "partial")
            
            # 更新框架
            framework.overall_completeness = framework.calculate_completeness()
            framework.updated_at = time.time()
            
            # 更新就绪状态
            if framework.can_answer_completely():
                if framework.overall_completeness >= 0.9:
                    framework.readiness = AnswerReadiness.EXCELLENT
                elif framework.overall_completeness >= 0.7:
                    framework.readiness = AnswerReadiness.READY
                else:
                    framework.readiness = AnswerReadiness.PARTIAL
            else:
                framework.readiness = AnswerReadiness.NOT_READY
            
            logger.info(f"📊 [Ucppt] 评估 | {target_aspect.aspect_name} | 完成度={target_aspect.completion_score:.0%} | 整体={framework.overall_completeness:.0%}")
            
        except Exception as e:
            logger.warning(f"⚠️ [Ucppt] 评估失败: {e}")
            # 降级：简单更新
            target_aspect.completion_score = min(1.0, target_aspect.completion_score + 0.3)
            if target_aspect.completion_score >= 0.7:
                target_aspect.status = "complete"
            elif target_aspect.completion_score >= 0.3:
                target_aspect.status = "partial"
            framework.overall_completeness = framework.calculate_completeness()
    
    # ==================== 答案生成 ====================
    
    def _calculate_source_relevance(
        self,
        source: Dict[str, Any],
        framework: AnswerFramework,
    ) -> float:
        """
        计算来源与问题框架的相关性分数 - v7.230 增强版
        
        基于标题和内容与关键信息面的匹配程度
        v7.230: 增加轮次权重（后期搜索更精准，给予更高权重）
        """
        title = source.get('title', '').lower()
        content = source.get('content', '').lower()
        combined = title + ' ' + content
        
        score = 0.0
        
        # 与原始问题的匹配
        query_words = framework.original_query.lower().split()
        for word in query_words:
            if len(word) >= 2 and word in combined:
                score += 0.1
        
        # 与关键信息面的匹配 - v7.232: 兼容 SearchFramework (targets) 和 AnswerFramework (key_aspects)
        aspects = getattr(framework, 'key_aspects', None) or getattr(framework, 'targets', [])
        for aspect in aspects:
            aspect_name = (getattr(aspect, 'aspect_name', None) or getattr(aspect, 'name', '')).lower()
            if aspect_name in combined:
                score += 0.3
            # 检查目标中的关键词
            answer_goal = getattr(aspect, 'answer_goal', '') or ''
            goal_words = answer_goal.lower().split()
            for word in goal_words:
                if len(word) >= 2 and word in combined:
                    score += 0.05
        
        # 与回答目标的匹配
        if framework.answer_goal:
            goal_words = framework.answer_goal.lower().split()
            for word in goal_words:
                if len(word) >= 2 and word in combined:
                    score += 0.1
        
        # v7.230: 轮次权重加成（后期轮次搜索更精准，每轮 +5%）
        round_num = source.get('_round', 1)
        round_weight = 1 + (round_num - 1) * 0.05
        score = score * round_weight
        
        # v7.230: 质量分加成（来源自带的质量评分）
        quality_score = source.get('quality_score', 0)
        if quality_score > 0:
            score += quality_score * 0.2
        
        return min(score, 5.0)  # 最高5分
    
    async def _generate_final_answer(
        self,
        query: str,
        framework: Union[AnswerFramework, SearchFramework],
        all_sources: List[Dict[str, Any]],
        rounds: Optional[List['SearchRoundState']] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        生成最终答案（流式）- v7.196 优化版

        优化内容：
        1. 来源去重（按URL）
        2. 每条来源包含400字内容摘要
        3. 相关性排序
        4. 累积所有轮次的反思内容
        5. v7.196: 加入 L1-L5 分析结果和人性维度洞察
        """

        # ==================== v7.231: 兼容 SearchFramework ====================
        # 获取 collected_evidence，兼容两种框架类型
        collected_evidence = getattr(framework, 'collected_evidence', {}) or {}

        # ==================== v7.196: 提取 L1-L5 分析结果 ====================
        l1_facts = collected_evidence.get("_L1_facts", [])
        l2_model = collected_evidence.get("_L2_user_model", [])
        l3_tension = collected_evidence.get("_L3_core_tension", [""])[0] if collected_evidence.get("_L3_core_tension") else ""
        l4_task = collected_evidence.get("_L4_search_task", [""])[0] if collected_evidence.get("_L4_search_task") else ""
        l5_sharpness = collected_evidence.get("_L5_sharpness", [])
        human_dims = collected_evidence.get("_human_dimensions", [])
        expert_handoff = collected_evidence.get("_expert_handoff", [])

        # 构建深度分析部分
        deep_analysis_section = ""
        if l1_facts or l2_model or l3_tension:
            deep_analysis_section = f"""
## 深度分析结果（L1-L5）

### L1 事实解构
{chr(10).join(f"- {f}" for f in l1_facts) if l1_facts else "无"}

### L2 用户模型
{chr(10).join(l2_model) if l2_model else "无"}

### L3 核心张力
{l3_tension if l3_tension else "无"}

### L4 搜索任务
{l4_task if l4_task else "无"}
"""

        # 构建人性维度部分
        human_dims_section = ""
        if human_dims:
            human_dims_section = f"""
## 人性维度洞察
{chr(10).join(human_dims)}
"""

        # 提取宏观统筹和切入点（保持向后兼容）
        macro_info = collected_evidence.get("_macro_overview", [])
        entry_info = collected_evidence.get("_entry_point", [])

        # 整理收集的信息 - v7.231: 兼容 SearchFramework (targets) 和 AnswerFramework (key_aspects)
        aspects_info = []
        aspects = getattr(framework, 'key_aspects', None) or getattr(framework, 'targets', [])
        for aspect in aspects:
            collected_info = getattr(aspect, 'collected_info', [])
            aspect_name = getattr(aspect, 'aspect_name', None) or getattr(aspect, 'name', '')
            if collected_info:
                aspects_info.append(f"### {aspect_name}\n" + "\n".join(f"- {info}" for info in collected_info))

        # ==================== v7.230: 智能来源选择优化 ====================

        # 1. URL 去重
        seen_urls = set()
        unique_sources = []
        for source in all_sources:
            url = source.get('url', source.get('link', ''))
            if url:
                if url not in seen_urls:
                    seen_urls.add(url)
                    unique_sources.append(source)
            else:
                # 无 URL 的来源也保留（基于标题去重）
                title = source.get('title', '')
                if title and title not in seen_urls:
                    seen_urls.add(title)
                    unique_sources.append(source)

        logger.info(f"📊 [v7.230] 来源去重: {len(all_sources)} → {len(unique_sources)}")

        # 2. v7.230: 智能来源选择 - 每轮保证Top-3入选 + 相关性排序
        # 基于 round_insights 确保每轮最佳来源入选
        guaranteed_urls = set()
        top_sources = []
        
        # 2a. 从 round_insights 中获取每轮最佳来源（保证入选）
        if framework.round_insights:
            for insight in framework.round_insights:
                for url in insight.best_source_urls[:3]:  # 每轮Top-3
                    if url and url not in guaranteed_urls:
                        guaranteed_urls.add(url)
                        # 从 unique_sources 中找到对应来源
                        for source in unique_sources:
                            if source.get('url', source.get('link', '')) == url:
                                top_sources.append(source)
                                break
            logger.info(f"📊 [v7.230] 轮次保证来源: {len(top_sources)}条 (from {len(framework.round_insights)} rounds)")

        # 2b. 相关性排序剩余来源
        remaining_sources = [s for s in unique_sources 
                           if s.get('url', s.get('link', '')) not in guaranteed_urls]
        scored_sources = [
            (source, self._calculate_source_relevance(source, framework))
            for source in remaining_sources
        ]
        scored_sources.sort(key=lambda x: x[1], reverse=True)

        # 2c. 补足到 30 条（v7.230: 从25增加到30，充分利用搜索结果）
        slots_remaining = 30 - len(top_sources)
        for source, score in scored_sources[:slots_remaining]:
            top_sources.append(source)
        
        logger.info(f"📊 [v7.230] 最终来源选择: {len(top_sources)}条 (保证:{len(guaranteed_urls)}, 补充:{len(top_sources)-len(guaranteed_urls)})")

        # 3. 构建带内容摘要的来源列表（每条400字）
        numbered_sources = []
        for idx, source in enumerate(top_sources, start=1):
            title = source.get('title', '未知标题')[:80]
            url = source.get('url', source.get('link', ''))
            content = source.get('content', source.get('snippet', ''))[:400]  # 400字摘要

            source_text = f"[{idx}] 《{title}》"
            if url:
                source_text += f"\n    链接: {url}"
            if content:
                source_text += f"\n    内容: {content}"
            numbered_sources.append(source_text)
        
        sources_text = chr(10).join(numbered_sources) if numbered_sources else "无可用来源"
        
        # ==================== v7.230: 结构化研究过程洞察（基于 round_insights）====================
        # v7.220: 智能压缩，避免上下文过载
        research_insights_text = ""
        if framework.round_insights:
            insights_parts = []

            # 质量阈值：只有高质量轮次才完整展示
            QUALITY_THRESHOLD = 0.6  # info_quality >= 0.6 才完整展示

            high_quality_rounds = []
            low_quality_rounds = []

            for insight in framework.round_insights:
                if insight.info_quality >= QUALITY_THRESHOLD:
                    high_quality_rounds.append(insight)
                else:
                    low_quality_rounds.append(insight)

            # 1. 完整展示高质量轮次
            for insight in high_quality_rounds:
                round_text = f"""### 第{insight.round_number}轮：{insight.target_aspect} ⭐
**搜索查询**: {insight.search_query}
**质量评价**: 充分度 {insight.info_sufficiency:.0%} | 质量 {insight.info_quality:.0%} | 对齐度 {insight.alignment_score:.0%}

**关键发现**:
{chr(10).join(f"- {f}" for f in insight.key_findings[:5]) if insight.key_findings else "- 无"}

**推断洞察**:
{chr(10).join(f"- {i}" for i in insight.inferred_insights[:4]) if insight.inferred_insights else "- 无"}

**进展描述**: {insight.progress_description[:200]}{"..." if len(insight.progress_description) > 200 else ""}
"""
                if insight.quality_issues:
                    round_text += f"""
**质量问题**: {', '.join(insight.quality_issues[:2])}
"""
                if insight.remaining_gaps:
                    round_text += f"""
**剩余缺口**: {', '.join(insight.remaining_gaps[:3])}
"""
                insights_parts.append(round_text)

            # 2. 精简展示低质量轮次（只保留核心发现）
            if low_quality_rounds:
                low_quality_summary = "### 其他轮次（精简）\n"
                for insight in low_quality_rounds:
                    # 只保留最重要的 1-2 条发现
                    top_findings = insight.key_findings[:2] if insight.key_findings else []
                    if top_findings:
                        low_quality_summary += f"- **第{insight.round_number}轮**（{insight.target_aspect}）: {'; '.join(top_findings)}\n"
                insights_parts.append(low_quality_summary)

            research_insights_text = chr(10).join(insights_parts)
            logger.info(f"📊 [v7.220] 构建研究洞察: 高质量{len(high_quality_rounds)}轮(完整), 低质量{len(low_quality_rounds)}轮(精简), 总findings={sum(len(i.key_findings) for i in framework.round_insights)}, 总insights={sum(len(i.inferred_insights) for i in framework.round_insights)}")

        # 兼容旧版：同时保留 rounds 的反思（不截断）
        reflection_summary = []
        if rounds:
            for r in rounds:
                if hasattr(r, 'reflection') and r.reflection:
                    round_num = getattr(r, 'round_number', '?')
                    target = getattr(r, 'target_aspect', '')
                    # v7.230: 不再截断，完整保留
                    reflection_summary.append(
                        f"• 第{round_num}轮（{target}）: {r.reflection}"
                    )
        
        reflection_text = chr(10).join(reflection_summary) if reflection_summary else "无"

        # ==================== v7.230: 重构后的 Prompt ====================
        # 新增「研究过程洞察」章节，展示每轮结构化发现
        research_section = ""
        if research_insights_text:
            research_section = f"""
## 研究过程洞察（按轮次结构化展示，请重点参考）

{research_insights_text}
"""
        
        prompt = f"""基于深度分析和多轮搜索的结构化洞察，为用户问题生成完整、专业的答案。

## 用户问题
{query}

## 回答目标
{framework.answer_goal}
{deep_analysis_section}{human_dims_section}
## 宏观统筹（问题全貌）
{chr(10).join(macro_info) if macro_info else "无"}

## 切入点洞察（核心突破口）
{chr(10).join(entry_info) if entry_info else "无"}
{research_section}
## 收集的信息（按信息面组织）
{chr(10).join(aspects_info) if aspects_info else "（信息较少，请基于常识回答）"}

## 参考来源（共{len(top_sources)}条，每轮Top-3保证入选 + 相关性排序补充）
{sources_text}

## 回答要求
1. **开头先点明核心洞察**（L3核心张力或切入点），让用户立刻抓住要点
2. **充分利用研究过程洞察**：每轮的关键发现和推断洞察是经过深度思考的结论，务必融入答案
3. **围绕用户模型展开**：基于L2用户模型（心理/社会/美学）组织内容
4. {"**融入人性维度洞察**：在适当位置体现情绪地图、精神追求等人性维度分析" if human_dims else "结构清晰，分点阐述"}
5. **重要：引用信息时使用 [编号] 格式标注来源**，例如"根据研究[1]..."、"专家指出[3][5]..."
6. **充分利用每条来源的内容摘要**，确保引用有据可查
7. 涵盖各个关键信息面，综合每轮的质量评价（高质量轮次重点引用）
8. 结尾给出可行的建议或结论
9. 字数：1500-2500字（v7.230: 鼓励更详尽的回答）

请生成专业、有深度、引用充分的答案。"""

        try:
            # v7.232: 兼容 SearchFramework (targets) 和 AnswerFramework (key_aspects)
            aspects = getattr(framework, 'key_aspects', None) or getattr(framework, 'targets', [])
            aspects_with_info = [a for a in aspects if getattr(a, 'collected_info', [])]
            aspect_names = [getattr(a, 'aspect_name', None) or getattr(a, 'name', '') for a in aspects[:3]]

            # 🆕 先流式输出答案生成的思考过程
            thinking_prompt = f"""作为专家，我现在要基于搜索结果生成最终答案。让我先梳理一下思路：

## 用户问题
{query}

## 收集到的信息概况
- 总共 {len(top_sources)} 条高质量来源
- 涵盖 {len(aspects_with_info)} 个关键信息面
- 反思洞察轮数：{len([r for r in (rounds or [])])} 轮

## 我的答案构思
1. 核心洞察切入：{l3_tension or '从整体框架入手'}
2. 关键信息面覆盖：需要回答用户关于{', '.join(aspect_names)}等方面的问题
3. 可行建议导向：最终要给用户实用的指导

现在开始生成详细答案..."""

            # 🔧 修复：使用DeepSeek Reasoner进行总结性思考流式输出
            async for chunk in self._call_deepseek_stream_with_reasoning(thinking_prompt, model=THINKING_MODEL, max_tokens=1000):
                if chunk.get("type") == "reasoning":
                    yield {
                        "type": "answer_chunk",
                        "data": {"content": chunk.get("content", ""), "is_thinking": True}
                    }
            
            # 标记思考完成
            yield {
                "type": "answer_thinking_complete",
                "data": {"message": "思考完成，开始生成答案..."}
            }
            
            # 然后生成实际答案
            async for chunk in self._call_llm_stream(prompt, model=SYNTHESIS_MODEL, max_tokens=3000):
                if chunk and isinstance(chunk, str):
                    yield {
                        "type": "answer_chunk",
                        "data": {"content": chunk, "is_thinking": False}
                    }
        except Exception as e:
            error_msg = str(e).encode('utf-8', errors='replace').decode('utf-8')
            logger.error(f"❌ [Ucppt] 答案生成失败: {error_msg}")
            yield {
                "type": "answer_chunk",
                "data": {"content": f"答案生成失败: {error_msg}"}
            }
    
    # ==================== LLM调用 ====================
    
    # ==================== DeepSeek 官方 API 调用 ====================
    
    async def _call_deepseek(
        self,
        prompt: str,
        model: str = "deepseek-chat",
        max_tokens: int = 1024,
    ) -> str:
        """调用 DeepSeek 官方 API（非流式）"""
        if not self.deepseek_api_key:
            raise ValueError("DEEPSEEK_API_KEY 未配置")
        
        headers = {
            "Authorization": f"Bearer {self.deepseek_api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.3,
        }
        
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{self.deepseek_base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
    
    async def _call_deepseek_stream(
        self,
        prompt: str,
        model: str = "deepseek-chat",
        max_tokens: int = 2000,
    ) -> AsyncGenerator[str, None]:
        """调用 DeepSeek 官方 API（流式，普通内容）"""
        if not self.deepseek_api_key:
            yield "DEEPSEEK_API_KEY 未配置"
            return
        
        headers = {
            "Authorization": f"Bearer {self.deepseek_api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.3,
            "stream": True,
        }
        
        try:
            async with httpx.AsyncClient(timeout=180) as client:
                async with client.stream(
                    "POST",
                    f"{self.deepseek_base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    buffer = ""
                    async for chunk in response.aiter_bytes():
                        buffer += chunk.decode('utf-8', errors='replace')
                        while '\n' in buffer:
                            line, buffer = buffer.split('\n', 1)
                            line = line.strip()
                            if line.startswith("data: "):
                                data_str = line[6:]
                                if data_str == "[DONE]":
                                    return
                                try:
                                    parsed = json.loads(data_str)
                                    content = parsed.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                    if content:
                                        yield content
                                except json.JSONDecodeError:
                                    continue
        except Exception as e:
            logger.error(f"DeepSeek流式调用失败: {e}")
            yield f"[错误: {e}]"
    
    async def _call_deepseek_stream_with_reasoning(
        self,
        prompt: str,
        model: str = "deepseek-reasoner",
        max_tokens: int = 2000,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        调用 DeepSeek 官方 API（流式），支持 reasoning_content
        
        DeepSeek-R1 模型会返回 reasoning_content（思考过程）和 content（最终输出）
        
        返回格式:
        - {"type": "reasoning", "content": "..."}  # 推理过程
        - {"type": "content", "content": "..."}    # 最终输出
        """
        if not self.deepseek_api_key:
            yield {"type": "error", "content": "DEEPSEEK_API_KEY 未配置"}
            return
        
        headers = {
            "Authorization": f"Bearer {self.deepseek_api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "stream": True,
        }
        
        try:
            async with httpx.AsyncClient(timeout=300) as client:
                async with client.stream(
                    "POST",
                    f"{self.deepseek_base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    buffer = ""
                    async for chunk in response.aiter_bytes():
                        buffer += chunk.decode('utf-8', errors='replace')
                        while '\n' in buffer:
                            line, buffer = buffer.split('\n', 1)
                            line = line.strip()
                            if line.startswith("data: "):
                                data_str = line[6:]
                                if data_str == "[DONE]":
                                    return
                                try:
                                    parsed = json.loads(data_str)
                                    delta = parsed.get("choices", [{}])[0].get("delta", {})
                                    
                                    # DeepSeek-R1 返回 reasoning_content（思考过程）
                                    reasoning = delta.get("reasoning_content", "")
                                    if reasoning:
                                        yield {"type": "reasoning", "content": reasoning}
                                    
                                    # 正常内容
                                    content = delta.get("content", "")
                                    if content:
                                        yield {"type": "content", "content": content}
                                        
                                except json.JSONDecodeError:
                                    continue
        except Exception as e:
            logger.error(f"DeepSeek Reasoner 流式调用失败: {e}")
            yield {"type": "error", "content": str(e)}
    
    # ==================== OpenRouter API 调用 ====================
    
    def _get_llm_headers(self) -> Dict[str, str]:
        """获取LLM API请求头"""
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json; charset=utf-8",
        }
        if "openrouter" in self.openai_base_url.lower():
            headers["HTTP-Referer"] = os.getenv("OPENROUTER_SITE_URL", "https://github.com/dafei0755/ai")
            headers["X-Title"] = os.getenv("OPENROUTER_APP_NAME", "Intelligent Project Analyzer")
        return headers
    
    def _get_model_name(self, model: str) -> str:
        """获取正确的模型名称"""
        if "openrouter" in self.openai_base_url.lower():
            # DeepSeek 模型已经是正确格式
            if "/" in model:
                return model
            # OpenAI 模型需要添加前缀
            return f"openai/{model}"
        return model
    
    async def _call_llm(
        self,
        prompt: str,
        model: str = "gpt-4o-mini",
        max_tokens: int = 1024,
    ) -> str:
        """调用LLM（非流式）"""
        if not self.openai_api_key:
            raise ValueError("API_KEY 未配置")
        
        headers = self._get_llm_headers()
        model_name = self._get_model_name(model)
        
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.3,
        }
        
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.openai_base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
    
    async def _call_llm_stream(
        self,
        prompt: str,
        model: str = "gpt-4o",
        max_tokens: int = 2000,
    ) -> AsyncGenerator[str, None]:
        """调用LLM（流式）"""
        if not self.openai_api_key:
            yield "API_KEY 未配置"
            return
        
        headers = self._get_llm_headers()
        model_name = self._get_model_name(model)
        
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.7,
            "stream": True,
        }
        
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                f"{self.openai_base_url}/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                response.raise_for_status()
                buffer = ""
                async for chunk in response.aiter_bytes():
                    buffer += chunk.decode('utf-8', errors='replace')
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.strip()
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                return
                            try:
                                parsed = json.loads(data)
                                content = parsed.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                continue

    # ==================== v7.187: 支持 DeepSeek reasoning 的流式调用 ====================
    
    async def _call_llm_stream_with_reasoning(
        self,
        prompt: str,
        model: str = "deepseek/deepseek-reasoner",
        max_tokens: int = 2000,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        调用LLM（流式），支持 DeepSeek reasoning_content
        
        返回格式:
        - {"type": "reasoning", "content": "..."}  # DeepSeek 的推理过程
        - {"type": "content", "content": "..."}    # 最终输出内容
        """
        if not self.openai_api_key:
            yield {"type": "error", "content": "API_KEY 未配置"}
            return
        
        headers = self._get_llm_headers()
        model_name = self._get_model_name(model)
        
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.3,
            "stream": True,
        }
        
        try:
            async with httpx.AsyncClient(timeout=180) as client:
                async with client.stream(
                    "POST",
                    f"{self.openai_base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    buffer = ""
                    async for chunk in response.aiter_bytes():
                        buffer += chunk.decode('utf-8', errors='replace')
                        while '\n' in buffer:
                            line, buffer = buffer.split('\n', 1)
                            line = line.strip()
                            if line.startswith("data: "):
                                data_str = line[6:]
                                if data_str == "[DONE]":
                                    return
                                try:
                                    parsed = json.loads(data_str)
                                    delta = parsed.get("choices", [{}])[0].get("delta", {})
                                    
                                    # DeepSeek-R1 返回 reasoning_content（思考过程）
                                    reasoning = delta.get("reasoning_content", "")
                                    if reasoning:
                                        yield {"type": "reasoning", "content": reasoning}
                                    
                                    # 正常内容
                                    content = delta.get("content", "")
                                    if content:
                                        yield {"type": "content", "content": content}
                                        
                                except json.JSONDecodeError:
                                    continue
        except Exception as e:
            logger.error(f"流式LLM调用失败: {e}")
            yield {"type": "error", "content": str(e)}
    
    # ==================== v7.214: 分析会话辅助方法 ====================
    
    def _build_framework_summary(self, framework_result: L1L5FrameworkResult) -> str:
        """构建框架分析摘要"""
        summary_parts = []
        
        # L1 事实原子
        if framework_result.l1_facts:
            summary_parts.append(f"**L1 核心事实**: {', '.join(framework_result.l1_facts[:3])}")
        
        # L3 核心张力
        if framework_result.l3_tensions:
            summary_parts.append(f"**L3 核心张力**: {framework_result.l3_tensions}")
        
        # L4 任务目标
        if framework_result.l4_jtbd:
            summary_parts.append(f"**L4 任务目标**: {framework_result.l4_jtbd}")
        
        # 质量评估
        summary_parts.append(f"**框架一致性**: {framework_result.framework_coherence:.1%}")
        
        return "\n\n".join(summary_parts)
    
    def _build_search_plan_summary(self, synthesis_result: SynthesisResult) -> str:
        """构建搜索计划摘要"""
        master_line = synthesis_result.search_master_line
        execution_plan = synthesis_result.execution_plan
        
        summary_parts = []
        
        # 核心问题
        if master_line.core_question:
            summary_parts.append(f"**核心问题**: {master_line.core_question}")
        
        # 搜索边界
        if master_line.boundary:
            summary_parts.append(f"**搜索边界**: {master_line.boundary}")
        
        # 搜索阶段
        if master_line.search_phases:
            summary_parts.append(f"**搜索阶段**: {' → '.join(master_line.search_phases)}")
        
        # 任务统计
        task_count = len(master_line.search_tasks)
        summary_parts.append(f"**搜索任务**: {task_count} 个任务")
        
        # 预估轮次
        if execution_plan and "total_estimated_rounds" in execution_plan:
            summary_parts.append(f"**预估轮次**: {execution_plan['total_estimated_rounds']} 轮")
        
        return "\n\n".join(summary_parts)
    
    def _extract_structured_info_from_session(self, session: AnalysisSession) -> Dict[str, Any]:
        """从分析会话中提取结构化信息"""
        if not session.l0_result:
            return {}
        
        l0 = session.l0_result
        return {
            "user_profile": l0.user_profile.to_dict(),
            "implicit_needs": l0.implicit_needs,
            "context_understanding": l0.context_understanding,
            "dialogue_content": l0.dialogue_content
        }
    
    def _extract_framework_from_session(self, session: AnalysisSession) -> Optional[Any]:
        """从分析会话中提取框架信息"""
        if not session.synthesis_result:
            return None
        
        # 构建与原有系统兼容的框架对象
        synthesis = session.synthesis_result
        framework = session.framework_result
        
        # 这里需要构建一个与原有 framework 兼容的对象
        # 暂时返回简化的框架信息
        class CompatibleFramework:
            def __init__(self):
                self.answer_goal = synthesis.search_master_line.core_question
                self.collected_evidence = {
                    "_macro_overview": [framework.l4_jtbd] if framework else [],
                    "_entry_point": [framework.l3_tensions] if framework else []
                }
                self.key_aspects = [
                    {
                        "aspect": task.task,
                        "purpose": task.purpose,
                        "priority": task.priority,
                        "information_needed": task.expected_info
                    }
                    for task in synthesis.search_master_line.search_tasks[:5]  # 限制数量
                ]
        
        return CompatibleFramework()


# ==================== 全局单例 ====================

_ucppt_engine: Optional[UcpptSearchEngine] = None


def get_ucppt_engine() -> UcpptSearchEngine:
    """获取ucppt引擎单例"""
    global _ucppt_engine
    if _ucppt_engine is None:
        _ucppt_engine = UcpptSearchEngine()
    return _ucppt_engine
