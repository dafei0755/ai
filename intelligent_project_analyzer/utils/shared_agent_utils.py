"""
v7.16 共享工具函数

将原节点和新 Agent 的重复逻辑提取为共享函数，减少代码重复。
"""

import json
import time
from datetime import datetime
from typing import Any, Dict, List, Tuple

from loguru import logger

# ============================================================================
# 性能监控装饰器
# ============================================================================

class PerformanceMonitor:
    """性能监控器 - 记录执行时间和调用统计"""
    
    _metrics: Dict[str, List[Dict[str, Any]]] = {}
    _enabled: bool = True
    
    @classmethod
    def enable(cls):
        """启用性能监控"""
        cls._enabled = True
    
    @classmethod
    def disable(cls):
        """禁用性能监控"""
        cls._enabled = False
    
    @classmethod
    def record(cls, agent_name: str, execution_time: float, version: str = "v7.16"):
        """记录执行指标"""
        if not cls._enabled:
            return
        
        if agent_name not in cls._metrics:
            cls._metrics[agent_name] = []
        
        cls._metrics[agent_name].append({
            "timestamp": datetime.now().isoformat(),
            "execution_time_ms": execution_time * 1000,
            "version": version
        })
        
        # 只保留最近 100 条记录
        if len(cls._metrics[agent_name]) > 100:
            cls._metrics[agent_name] = cls._metrics[agent_name][-100:]
    
    @classmethod
    def get_stats(cls, agent_name: str) -> Dict[str, Any]:
        """获取统计信息"""
        if agent_name not in cls._metrics or not cls._metrics[agent_name]:
            return {"count": 0, "avg_ms": 0, "min_ms": 0, "max_ms": 0}
        
        times = [m["execution_time_ms"] for m in cls._metrics[agent_name]]
        return {
            "count": len(times),
            "avg_ms": sum(times) / len(times),
            "min_ms": min(times),
            "max_ms": max(times),
            "version": cls._metrics[agent_name][-1].get("version", "unknown")
        }
    
    @classmethod
    def get_comparison(cls) -> Dict[str, Dict[str, Any]]:
        """获取所有 Agent 的性能对比"""
        return {name: cls.get_stats(name) for name in cls._metrics}
    
    @classmethod
    def log_summary(cls):
        """输出性能汇总日志"""
        stats = cls.get_comparison()
        if not stats:
            logger.info(" 暂无性能数据")
            return
        
        logger.info(" v7.16 Agent 性能汇总:")
        logger.info("-" * 60)
        for name, data in stats.items():
            logger.info(f"  {name}: {data['avg_ms']:.2f}ms (avg), {data['count']} 次调用")
        logger.info("-" * 60)
    
    @classmethod
    def reset(cls):
        """重置所有指标"""
        cls._metrics.clear()


def with_performance_monitoring(agent_name: str, version: str = "v7.16"):
    """性能监控装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                execution_time = time.time() - start_time
                PerformanceMonitor.record(agent_name, execution_time, version)
        return wrapper
    return decorator


# ============================================================================
# 挑战检测共享函数
# ============================================================================

def extract_challenge_flags(
    agent_results: Dict[str, Any],
    batch_results: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    从专家输出中提取挑战标记
    
    共享逻辑，被以下组件使用:
    - ChallengeDetectionAgent (v7.16)
    - detect_and_handle_challenges_node (原版)
    
    Args:
        agent_results: 专家结果字典
        batch_results: 批次结果字典
    
    Returns:
        挑战标记列表
    """
    raw_challenges = []
    
    # 从 agent_results 提取
    for agent_id, result in agent_results.items():
        if not isinstance(result, dict):
            continue
        
        # 检查 structured_data.challenge_flags
        structured_data = result.get("structured_data", {})
        if isinstance(structured_data, dict):
            challenge_flags = structured_data.get("challenge_flags", [])
            for flag in challenge_flags:
                raw_challenges.append({
                    "agent_id": agent_id,
                    "source": "agent_results",
                    **flag
                })
        
        # 检查顶层 challenge_flags（兼容旧格式）
        top_level_flags = result.get("challenge_flags", [])
        for flag in top_level_flags:
            raw_challenges.append({
                "agent_id": agent_id,
                "source": "agent_results_top",
                **flag
            })
    
    # 从 batch_results 提取
    for batch_id, batch_data in batch_results.items():
        if not isinstance(batch_data, dict):
            continue
        
        for agent_id, agent_payload in batch_data.items():
            if not isinstance(agent_payload, dict):
                continue
            
            structured_data = agent_payload.get("structured_data", {})
            if isinstance(structured_data, dict):
                challenge_flags = structured_data.get("challenge_flags", [])
                for flag in challenge_flags:
                    raw_challenges.append({
                        "agent_id": agent_id,
                        "source": f"batch_{batch_id}",
                        **flag
                    })
    
    return raw_challenges


def classify_challenges(
    raw_challenges: List[Dict[str, Any]]
) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """
    对挑战进行分类
    
    Returns:
        (high_severity, medium_severity, low_severity) 三个列表
    """
    high = []
    medium = []
    low = []
    
    for challenge in raw_challenges:
        # 根据关键词判断严重程度
        rationale = challenge.get("rationale", "").lower()
        challenged_item = challenge.get("challenged_item", "").lower()
        
        if any(kw in rationale for kw in ["严重", "关键", "必须", "安全"]):
            challenge["severity"] = "high"
            high.append(challenge)
        elif any(kw in rationale for kw in ["建议", "可能", "考虑"]):
            challenge["severity"] = "low"
            low.append(challenge)
        else:
            challenge["severity"] = "medium"
            medium.append(challenge)
    
    return high, medium, low


# ============================================================================
# 报告提取共享函数
# ============================================================================

def extract_expert_reports(
    agent_results: Dict[str, Any],
    selected_roles: List[Dict[str, Any]]
) -> Dict[str, str]:
    """
    提取专家报告内容
    
    共享逻辑，被以下组件使用:
    - ResultAggregatorAgentV2 (v7.16)
    - ResultAggregatorAgent (原版)
    
    Args:
        agent_results: 专家结果字典
        selected_roles: 选定的角色列表
    
    Returns:
        专家名称 -> 报告内容的映射
    """
    # 构建 role_id -> dynamic_role_name 映射
    role_display_names = {}
    for role in selected_roles:
        role_id = role.get("role_id", "")
        dynamic_name = role.get("dynamic_role_name", role.get("role_name", ""))
        role_display_names[role_id] = dynamic_name
    
    expert_reports = {}
    
    for agent_id, result in agent_results.items():
        if not isinstance(result, dict):
            continue
        
        # 跳过需求分析师和项目总监
        if any(skip in agent_id.lower() for skip in ["requirements", "director", "analyst"]):
            continue
        
        # 提取内容
        content = result.get("content", "")
        structured_data = result.get("structured_data", {})
        
        if isinstance(structured_data, dict) and structured_data:
            content = json.dumps(structured_data, ensure_ascii=False, indent=2)
        
        if not content:
            continue
        
        # 构建显示名称
        display_name = _format_display_name(agent_id, role_display_names)
        expert_reports[display_name] = content
    
    return expert_reports


def _format_display_name(
    agent_id: str,
    role_display_names: Dict[str, str]
) -> str:
    """格式化专家显示名称"""
    import re
    
    # 尝试从 agent_id 提取 role_id
    # 格式: "V4_设计研究员_4-1" -> role_id = "4-1"
    match = re.search(r"(\d+-\d+)$", agent_id)
    if match:
        role_id = match.group(1)
        if role_id in role_display_names:
            return f"{role_id} {role_display_names[role_id]}"
    
    # 回退: 直接返回 agent_id
    return agent_id


# ============================================================================
# 问卷上下文提取共享函数
# ============================================================================

def extract_questionnaire_context(
    user_input: str,
    structured_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    提取问卷生成所需的上下文信息
    
    共享逻辑，被以下组件使用:
    - QuestionnaireAgent (v7.16)
    - LLMQuestionGenerator (原版)
    
    Args:
        user_input: 用户输入
        structured_data: 结构化数据
    
    Returns:
        上下文信息字典
    """
    # 提取关键词
    keywords = []
    
    # 从 structured_data 提取
    if isinstance(structured_data, dict):
        keywords.extend(structured_data.get("keywords", []))
        
        # 从 project_type 提取
        project_type = structured_data.get("project_type", "")
        if project_type:
            keywords.append(project_type)
    
    # 从 user_input 提取（简单分词）
    import re
    words = re.findall(r"[\u4e00-\u9fa5]{2,6}", user_input)
    keywords.extend(words[:5])  # 最多取 5 个
    
    # 去重
    keywords = list(dict.fromkeys(keywords))
    
    return {
        "user_input": user_input,
        "keywords": keywords[:10],  # 最多 10 个关键词
        "project_type": structured_data.get("project_type", "") if isinstance(structured_data, dict) else "",
        "summary_length": len(user_input)
    }


# ============================================================================
# 质量预检共享函数
# ============================================================================

def analyze_task_risks(
    selected_roles: List[Dict[str, Any]],
    user_requirements: str
) -> List[Dict[str, Any]]:
    """
    分析任务风险
    
    共享逻辑，被以下组件使用:
    - QualityPreflightAgent (v7.16)
    - QualityPreflightNode (原版)
    
    Args:
        selected_roles: 选定的角色列表
        user_requirements: 用户需求描述
    
    Returns:
        风险列表
    """
    risks = []
    
    # 检查角色数量
    if len(selected_roles) < 3:
        risks.append({
            "type": "insufficient_roles",
            "severity": "medium",
            "description": f"角色数量不足: {len(selected_roles)}/3"
        })
    
    # 检查任务覆盖
    for role in selected_roles:
        task_instruction = role.get("task_instruction", {})
        if isinstance(task_instruction, dict):
            deliverables = task_instruction.get("deliverables", [])
            if not deliverables:
                risks.append({
                    "type": "missing_deliverables",
                    "severity": "high",
                    "role_id": role.get("role_id"),
                    "description": f"{role.get('dynamic_role_name', '未知角色')} 缺少交付物定义"
                })
    
    # 检查用户需求复杂度
    if len(user_requirements) > 500:
        risks.append({
            "type": "complex_requirements",
            "severity": "low",
            "description": "用户需求较长，可能需要更多轮次的澄清"
        })
    
    return risks


def generate_quality_checklists(
    selected_roles: List[Dict[str, Any]]
) -> Dict[str, List[str]]:
    """
    为每个专家生成质量检查清单
    
    Args:
        selected_roles: 选定的角色列表
    
    Returns:
        角色ID -> 检查项列表的映射
    """
    checklists = {}
    
    for role in selected_roles:
        role_id = role.get("role_id", "unknown")
        role_name = role.get("dynamic_role_name", role.get("role_name", ""))
        
        # 基础检查项
        checks = [
            f" {role_name} 是否理解任务目标",
            f" {role_name} 是否有明确的交付物",
            f" {role_name} 是否考虑了用户约束"
        ]
        
        # 根据角色类型添加特定检查
        if "研究" in role_name or "4-" in role_id:
            checks.append(f" {role_name} 是否提供了数据支撑")
        if "设计" in role_name or "2-" in role_id:
            checks.append(f" {role_name} 是否考虑了美观与功能平衡")
        if "叙事" in role_name or "3-" in role_id:
            checks.append(f" {role_name} 是否创建了情感连接")
        
        checklists[role_id] = checks
    
    return checklists


# ============================================================================
#  v7.18: 问卷生成共享函数
# ============================================================================

def build_questionnaire_analysis_summary(structured_data: Dict[str, Any]) -> str:
    """
     v7.18: 从需求分析结果中提取关键信息，构建 LLM 提示词上下文
    
    统一 llm_generator.py 和 questionnaire_agent.py 的 _build_analysis_summary 逻辑
    
    Args:
        structured_data: 需求分析师的结构化输出
        
    Returns:
        构建的分析摘要文本
    """
    summary_parts = []
    
    # 项目概览（优先级最高）
    project_overview = structured_data.get("project_overview", "")
    if project_overview:
        summary_parts.append(f"## 项目概览\n{project_overview}")
    
    # 项目任务（兼容旧字段名）
    project_task = structured_data.get("project_task", "") or structured_data.get("project_tasks", "")
    if isinstance(project_task, list):
        project_task = "；".join(project_task[:5])
    if project_task and project_task != project_overview:
        summary_parts.append(f"## 项目任务\n{project_task}")
    
    # 核心目标
    core_objectives = structured_data.get("core_objectives", [])
    if core_objectives:
        if isinstance(core_objectives, list):
            objectives_text = "\n".join([f"- {obj}" for obj in core_objectives[:5]])
        else:
            objectives_text = str(core_objectives)
        summary_parts.append(f"## 核心目标\n{objectives_text}")
    
    # 项目类型
    project_type = structured_data.get("project_type", "")
    if project_type:
        type_label = {
            "personal_residential": "个人住宅",
            "hybrid_residential_commercial": "混合型（住宅+商业）",
            "commercial_enterprise": "商业/企业项目",
            "cultural_educational": "文化/教育项目",
            "healthcare_wellness": "医疗/康养项目",
            "office_coworking": "办公/联合办公",
            "hospitality_tourism": "酒店/文旅项目",
            "sports_entertainment_arts": "体育/娱乐/艺术"
        }.get(project_type, project_type)
        summary_parts.append(f"## 项目类型\n{type_label}")
    
    # 设计挑战
    design_challenge = structured_data.get("design_challenge", "")
    if design_challenge:
        summary_parts.append(f"## 核心设计挑战\n{design_challenge}")
    
    # 核心张力
    core_tension = structured_data.get("core_tension", "")
    if core_tension:
        summary_parts.append(f"## 核心矛盾/张力\n{core_tension}")
    
    # 人物叙事（优先 narrative_characters，兼容 character_narrative）
    narrative_characters = structured_data.get("narrative_characters", "") or structured_data.get("character_narrative", "")
    if isinstance(narrative_characters, list):
        narrative_characters = "\n".join([f"- {char}" for char in narrative_characters[:3]])
    if narrative_characters:
        summary_parts.append(f"## 人物叙事/用户画像\n{narrative_characters}")
    
    # 物理环境
    physical_contexts = structured_data.get("physical_contexts", "")
    if isinstance(physical_contexts, list):
        physical_contexts = "；".join(physical_contexts[:3])
    if physical_contexts:
        summary_parts.append(f"## 物理环境\n{physical_contexts}")
    
    # 资源约束
    resource_constraints = structured_data.get("resource_constraints", "")
    if resource_constraints:
        summary_parts.append(f"## 资源约束\n{resource_constraints}")
    
    # 约束与机遇
    constraints_opportunities = structured_data.get("constraints_opportunities", "")
    if isinstance(constraints_opportunities, dict):
        co_parts = []
        if constraints_opportunities.get("constraints"):
            co_parts.append(f"约束: {constraints_opportunities['constraints']}")
        if constraints_opportunities.get("opportunities"):
            co_parts.append(f"机遇: {constraints_opportunities['opportunities']}")
        constraints_opportunities = "；".join(co_parts)
    if constraints_opportunities and constraints_opportunities != resource_constraints:
        summary_parts.append(f"## 约束与机遇\n{constraints_opportunities}")
    
    if not summary_parts:
        logger.warning("️ [build_questionnaire_analysis_summary] structured_data 字段全部为空")
        return "（需求分析数据不足，请基于用户原始输入生成问卷）"
    
    return "\n\n".join(summary_parts)


def extract_user_keywords(user_input: str, max_keywords: int = 15) -> List[str]:
    """
     v7.18: 从用户输入中提取关键词
    
    统一各处关键词提取逻辑
    
    Args:
        user_input: 用户原始输入
        max_keywords: 最大返回关键词数量
        
    Returns:
        关键词列表
    """
    import re
    
    if not user_input:
        return []
    
    keywords = []
    
    # 1. 提取数字+单位
    num_patterns = re.findall(r'\d+[\u4e00-\u9fa5㎡a-zA-Z]+', user_input)
    keywords.extend(num_patterns)
    
    # 2. 提取引号内容
    quoted = re.findall(r'[""「」『』【】]([^""「」『』【】]+)[""「」『』【】]', user_input)
    keywords.extend(quoted)
    
    # 3. 提取关键名词
    stopwords = {
        "的", "是", "在", "有", "我", "你", "他", "她", "它", "们",
        "这", "那", "和", "与", "或", "但", "而", "了", "着", "过",
        "需要", "希望", "想要", "一个", "一些", "这个", "那个",
        "如何", "怎么", "什么", "哪些", "为什么", "请", "帮",
        "进行", "实现", "完成", "考虑", "包括", "通过", "使用",
        "设计", "项目", "方案", "建议", "能够", "可以"
    }
    
    chinese_words = re.findall(r'[\u4e00-\u9fa5]{2,8}', user_input)
    for word in chinese_words:
        if word not in stopwords and word not in keywords:
            keywords.append(word)
    
    # 去重并限制数量
    unique_keywords = list(dict.fromkeys(keywords))
    return unique_keywords[:max_keywords]


def check_questionnaire_relevance(
    questions: List[Dict[str, Any]],
    user_input: str,
    threshold: float = 0.3
) -> Tuple[float, List[str]]:
    """
     v7.18: 检查问题与用户输入的相关性
    
    统一相关性验证逻辑
    
    Args:
        questions: 问题列表
        user_input: 用户原始输入
        threshold: 阈值，低于此值的问题将被标记
        
    Returns:
        Tuple[平均相关性分数, 低相关性问题ID列表]
    """
    import re
    
    if not questions or not user_input:
        return 1.0, []
    
    # 提取用户输入关键词
    stopwords = {
        "的", "是", "在", "有", "我", "你", "他", "她", "它", "们",
        "这", "那", "和", "与", "或", "但", "而", "了", "着", "过"
    }
    
    user_words = set()
    chinese_words = re.findall(r'[\u4e00-\u9fa5]{2,10}', user_input)
    for word in chinese_words:
        if word not in stopwords:
            user_words.add(word)
    
    numbers = re.findall(r'\d+[\u4e00-\u9fa5㎡]+', user_input)
    user_words.update(numbers)
    
    if not user_words:
        return 1.0, []
    
    scores = []
    low_relevance = []
    
    for q in questions:
        question_text = q.get("question", "") + " ".join(q.get("options", []))
        hits = sum(1 for word in user_words if word in question_text)
        score = min(1.0, hits / max(3, len(user_words) * 0.3))
        scores.append(score)
        
        if score < threshold:
            low_relevance.append(q.get("id", "unknown"))
    
    avg_score = sum(scores) / len(scores) if scores else 0
    return avg_score, low_relevance
