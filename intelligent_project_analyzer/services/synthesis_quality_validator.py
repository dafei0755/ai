"""
合成质量验证器 - Synthesis Quality Validator (v8.2)

在线实时验证动态合成角色的质量，确保合成结果满足协议约束。
Online real-time validation for dynamically synthesized roles.

核心功能:
1. 验证跨战略层约束（父角色必须来自不同V层级）
2. 验证任务融合深度（非简单堆叠）
3. 验证关键词融合度
4. 评估合成角色的实用性评分
5. 生成合成质量报告
6. [v8.2] 全局角色选择质量评分（任务-角色对齐 + 交付物覆盖）
7. [v8.2] 增强命名质量检测（泛化模式 + 任务关联性）

创建时间: 2026-02-20
版本: v8.2
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger


class SynthesisQualityValidator:
    """
    合成质量在线验证器

    职责:
    - 在 DPD 选角完成后、专家执行前，验证合成角色的质量
    - 提供实时反馈，不合格的合成将触发重新生成或降级
    """

    # 融合深度关键词（表示真正的跨界融合，而非任务堆叠）
    FUSION_INDICATORS = [
        "驱动",
        "融合",
        "整合",
        "协同",
        "平衡",
        "贯穿",
        "统筹",
        "结合",
        "交织",
        "兼顾",
        "联动",
        "嵌入",
        "渗透",
        "赋能",
    ]

    # 堆叠信号词（表示简单的任务拼接，而非深度融合）
    STACKING_INDICATORS = [
        "先做",
        "再做",
        "然后",
        "接着",
        "分别",
        "各自",
        "第一步.*第二步",
        "负责.*负责",
    ]

    # V层级映射
    V_LAYER_MAP = {
        "2": "V2",
        "3": "V3",
        "4": "V4",
        "5": "V5",
        "6": "V6",
        "7": "V7",
    }

    @classmethod
    def validate_synthesis(
        cls,
        role_id: str,
        role_name: str,
        dynamic_role_name: str,
        tasks: List[str],
        keywords: Optional[List[str]] = None,
        dependencies: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        综合验证合成角色质量

        Args:
            role_id: 合成角色ID (如 "2-1+5-1")
            role_name: 合成角色基础名称
            dynamic_role_name: 动态角色名称
            tasks: 任务列表
            keywords: 关键词列表
            dependencies: 依赖列表

        Returns:
            验证报告: {
                "is_valid": bool,
                "total_score": float (0-10),
                "dimension_scores": Dict[str, float],
                "warnings": List[str],
                "errors": List[str],
                "suggestions": List[str],
            }
        """
        errors = []
        warnings = []
        suggestions = []
        scores = {}

        # 1. 检查是否真的是合成角色
        clean_id = role_id.replace("SYNTHESIZED_", "")
        if "+" not in clean_id:
            return {
                "is_valid": True,
                "is_synthesized": False,
                "total_score": 10.0,
                "dimension_scores": {},
                "warnings": [],
                "errors": [],
                "suggestions": [],
                "message": "非合成角色，跳过合成质量验证",
            }

        parent_ids = clean_id.split("+")
        logger.info(f"[v8.1 SQV] 开始验证合成角色 {role_id}, 父角色: {parent_ids}")

        # 2. 维度1: 跨战略层验证 (权重: 25%)
        layer_score, layer_msgs = cls._validate_cross_layer(parent_ids)
        scores["跨战略层"] = layer_score
        if layer_score < 10:
            errors.extend(layer_msgs)
        else:
            logger.info(f"[v8.1 SQV] 跨战略层验证通过: {layer_msgs}")

        # 3. 维度2: 任务融合深度 (权重: 30%)
        fusion_score, fusion_msgs = cls._validate_fusion_depth(tasks)
        scores["融合深度"] = fusion_score
        if fusion_score < 6:
            warnings.extend(fusion_msgs)
            suggestions.append("建议使用融合性动词（驱动、整合、协同等）重构任务描述，避免简单拼接")
        elif fusion_score < 8:
            warnings.extend(fusion_msgs)

        # 4. 维度3: 动态命名质量 (权重: 15%) — v8.2: 传入tasks支持任务关联检查
        naming_score, naming_msgs = cls._validate_naming(role_name, dynamic_role_name, parent_ids, tasks=tasks)
        scores["命名质量"] = naming_score
        if naming_score < 7:
            warnings.extend(naming_msgs)
            suggestions.append("dynamic_role_name应体现跨界融合特征，而非简单拼接两个角色名")

        # 5. 维度4: 关键词融合度 (权重: 15%)
        if keywords:
            kw_score, kw_msgs = cls._validate_keywords_fusion(keywords, parent_ids)
            scores["关键词融合"] = kw_score
            if kw_score < 7:
                warnings.extend(kw_msgs)
        else:
            scores["关键词融合"] = 7.0  # 无关键词时给默认分

        # 6. 维度5: 依赖最小化 (权重: 15%)
        dep_score, dep_msgs = cls._validate_dependency_minimization(dependencies, parent_ids)
        scores["依赖最小化"] = dep_score
        if dep_score < 8:
            warnings.extend(dep_msgs)
            suggestions.append("合成角色应减少依赖，因为已经融合了多个角色的能力")

        # 计算加权总分
        weights = {
            "跨战略层": 0.25,
            "融合深度": 0.30,
            "命名质量": 0.15,
            "关键词融合": 0.15,
            "依赖最小化": 0.15,
        }
        total_score = sum(scores.get(dim, 0) * w for dim, w in weights.items())

        # 判定是否合格
        is_valid = total_score >= 6.0 and scores.get("跨战略层", 0) >= 8

        result = {
            "is_valid": is_valid,
            "is_synthesized": True,
            "total_score": round(total_score, 2),
            "dimension_scores": scores,
            "warnings": warnings,
            "errors": errors,
            "suggestions": suggestions,
            "grade": cls._get_grade(total_score),
            "parent_roles": parent_ids,
        }

        # 日志输出
        status = "PASS" if is_valid else "FAIL"
        logger.info(
            f"[v8.1 SQV] 合成质量验证 [{status}]: "
            f"总分={total_score:.1f}/10, "
            f"跨层={scores.get('跨战略层', 0):.0f}, "
            f"融合={scores.get('融合深度', 0):.0f}, "
            f"命名={scores.get('命名质量', 0):.0f}"
        )

        if not is_valid:
            logger.warning(f"[v8.1 SQV] 合成角色质量不合格!\n" f"  错误: {errors}\n" f"  警告: {warnings}\n" f"  建议: {suggestions}")

        return result

    @classmethod
    def _validate_cross_layer(cls, parent_ids: List[str]) -> Tuple[float, List[str]]:
        """维度1: 验证父角色是否来自不同战略层"""
        layers = set()
        for pid in parent_ids:
            layer_num = pid.split("-")[0]
            layer = cls.V_LAYER_MAP.get(layer_num, f"V{layer_num}")
            layers.add(layer)

        if len(layers) >= 2:
            return 10.0, [f"父角色跨越 {len(layers)} 个战略层: {sorted(layers)}"]
        elif len(layers) == 1:
            return 0.0, [f"违反约束: 所有父角色来自同一战略层 {layers.pop()}，必须跨战略层"]
        else:
            return 0.0, ["无法解析父角色的战略层信息"]

    @classmethod
    def _validate_fusion_depth(cls, tasks: List[str]) -> Tuple[float, List[str]]:
        """维度2: 验证任务是否为深度融合（而非简单堆叠）"""
        if not tasks:
            return 3.0, ["任务列表为空，无法评估融合深度"]

        all_task_text = " ".join(tasks)

        # 计算融合指标出现次数
        fusion_count = sum(1 for indicator in cls.FUSION_INDICATORS if indicator in all_task_text)

        # 计算堆叠信号出现次数
        stacking_count = 0
        for pattern in cls.STACKING_INDICATORS:
            if re.search(pattern, all_task_text):
                stacking_count += 1

        # 融合比例 = 融合词数 / 任务数
        fusion_ratio = fusion_count / max(len(tasks), 1)

        msgs = []

        if stacking_count > 0:
            msgs.append(f"检测到 {stacking_count} 个堆叠信号（先做/再做/分别等），可能是任务拼接而非融合")

        if fusion_ratio >= 0.8:
            score = 10.0
            msgs.append(f"融合深度优秀: {fusion_count}/{len(tasks)} 个任务体现融合特征")
        elif fusion_ratio >= 0.5:
            score = 8.0 - stacking_count
            msgs.append(f"融合深度良好: {fusion_count}/{len(tasks)} 个任务体现融合特征")
        elif fusion_ratio >= 0.3:
            score = 6.0 - stacking_count
            msgs.append(f"融合深度一般: 仅 {fusion_count}/{len(tasks)} 个任务体现融合特征")
        else:
            score = 4.0 - stacking_count
            msgs.append(f"融合深度不足: 仅 {fusion_count}/{len(tasks)} 个任务体现融合特征，可能是简单堆叠")

        return max(0, min(10, score)), msgs

    # v8.2: 泛化命名模式检测 (Phase 3)
    GENERIC_NAME_PATTERNS = [
        r"^.{0,2}专家$",
        r"^.{0,2}设计师$",
        r"^.{0,2}工程师$",
        r"^.{0,2}顾问$",
        r"^.{0,2}分析师$",
        r"^.{0,2}总监$",
        r"^综合.*专家$",
        r"^跨界.*专家$",
        r"^全能.*师$",
    ]

    @classmethod
    def _validate_naming(
        cls,
        role_name: str,
        dynamic_role_name: str,
        parent_ids: List[str],
        tasks: Optional[List[str]] = None,
    ) -> Tuple[float, List[str]]:
        """维度3: 验证动态命名是否体现跨界融合 (v8.2增强: 泛化检测+任务关联)"""
        msgs = []
        score = 10.0

        # 检查dynamic_role_name是否为空
        if not dynamic_role_name or dynamic_role_name == role_name:
            score -= 5
            msgs.append("dynamic_role_name为空或直接复制了role_name")

        # 检查长度
        if dynamic_role_name and len(dynamic_role_name) < 8:
            score -= 2
            msgs.append(f"dynamic_role_name过短({len(dynamic_role_name)}字)，建议10-25字")
        elif dynamic_role_name and len(dynamic_role_name) > 30:
            score -= 1
            msgs.append(f"dynamic_role_name过长({len(dynamic_role_name)}字)，建议10-25字")

        # v8.2 Phase 3: 泛化模式检测
        if dynamic_role_name:
            for pattern in cls.GENERIC_NAME_PATTERNS:
                if re.match(pattern, dynamic_role_name):
                    score -= 3
                    msgs.append(f"命名匹配泛化模式 '{pattern}'，缺乏项目特征词")
                    break

            # v8.2 Phase 3: 任务关键词关联性检查
            if tasks:
                task_text = " ".join(tasks)
                # 提取dynamic_role_name中的实词（>1字的非通用词）
                name_chars = set()
                for i in range(len(dynamic_role_name) - 1):
                    bigram = dynamic_role_name[i : i + 2]
                    if bigram not in {"专家", "设计", "总监", "工程", "分析", "顾问", "首席", "高级"}:
                        name_chars.add(bigram)
                # 检查名称中的特征词是否在任务中出现
                overlap = sum(1 for ng in name_chars if ng in task_text)
                if name_chars and overlap == 0:
                    score -= 1.5
                    msgs.append("dynamic_role_name与任务描述无关键词重叠，名称可能不反映实际任务")

        if not msgs:
            msgs.append("命名质量良好")

        return max(0, min(10, score)), msgs

    @classmethod
    def _validate_keywords_fusion(cls, keywords: List[str], parent_ids: List[str]) -> Tuple[float, List[str]]:
        """维度4: 验证关键词是否充分融合"""
        msgs = []

        if not keywords:
            return 5.0, ["无关键词数据"]

        # 检查去重率
        unique_keywords = set(keywords)
        dedup_rate = len(unique_keywords) / max(len(keywords), 1)

        # 检查是否有来自多个领域的关键词
        # 简单启发式: 不同领域的关键词应该在同一个列表中共存
        keyword_diversity = len(unique_keywords)

        if dedup_rate >= 0.9 and keyword_diversity >= 5:
            score = 10.0
            msgs.append(f"关键词融合良好: {keyword_diversity}个唯一关键词，去重率{dedup_rate:.0%}")
        elif dedup_rate >= 0.7:
            score = 7.0
            msgs.append(f"关键词有一定冗余: 去重率{dedup_rate:.0%}")
        else:
            score = 5.0
            msgs.append(f"关键词冗余较多: 去重率{dedup_rate:.0%}，建议去重后保留最具融合价值的关键词")

        return score, msgs

    @classmethod
    def _validate_dependency_minimization(
        cls, dependencies: Optional[List[str]], parent_ids: List[str]
    ) -> Tuple[float, List[str]]:
        """维度5: 验证依赖是否最小化"""
        msgs = []

        if not dependencies:
            return 10.0, ["无依赖，符合合成角色的最小化依赖原则"]

        # 检查依赖是否指向已被合成的父角色
        parent_set = set(parent_ids)
        redundant_deps = [d for d in dependencies if d in parent_set]

        if redundant_deps:
            score = 3.0
            msgs.append(f"依赖了已被合成的父角色 {redundant_deps}，合成角色应已内化这些能力")
        elif len(dependencies) <= 1:
            score = 9.0
            msgs.append(f"依赖数量合理: {len(dependencies)}个")
        elif len(dependencies) <= 2:
            score = 7.0
            msgs.append(f"依赖数量可接受: {len(dependencies)}个")
        else:
            score = 5.0
            msgs.append(f"依赖过多: {len(dependencies)}个，合成角色应减少对外依赖")

        return score, msgs

    @staticmethod
    def _get_grade(score: float) -> str:
        """根据分数返回等级"""
        if score >= 9.0:
            return "A+ (优秀)"
        elif score >= 8.0:
            return "A (良好)"
        elif score >= 7.0:
            return "B (合格)"
        elif score >= 6.0:
            return "C (待改进)"
        else:
            return "D (不合格)"


def validate_role_selection_synthesis(selected_roles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    批量验证角色选择中的所有合成角色

    在 DPD select_roles_for_task 返回后调用，验证所有合成角色的质量。

    Args:
        selected_roles: RoleSelection.selected_roles 列表

    Returns:
        验证汇总报告
    """
    synthesis_reports = []
    has_invalid = False

    for role in selected_roles:
        role_id = role.get("role_id", "") if isinstance(role, dict) else getattr(role, "role_id", "")

        # 只验证合成角色
        clean_id = role_id.replace("SYNTHESIZED_", "")
        if "+" not in clean_id:
            continue

        # 提取任务文本
        if isinstance(role, dict):
            tasks = role.get("tasks", [])
            if not tasks:
                ti = role.get("task_instruction", {})
                tasks = [d.get("description", d.get("name", "")) for d in ti.get("deliverables", [])]
            role_name = role.get("role_name", "")
            dynamic_role_name = role.get("dynamic_role_name", "")
            keywords = role.get("keywords", [])
            dependencies = role.get("dependencies", [])
        else:
            tasks = getattr(role, "tasks", [])
            role_name = getattr(role, "role_name", "")
            dynamic_role_name = getattr(role, "dynamic_role_name", "")
            keywords = []
            dependencies = getattr(role, "dependencies", [])

        report = SynthesisQualityValidator.validate_synthesis(
            role_id=role_id,
            role_name=role_name,
            dynamic_role_name=dynamic_role_name,
            tasks=tasks,
            keywords=keywords,
            dependencies=dependencies,
        )

        synthesis_reports.append(report)
        if not report.get("is_valid", True):
            has_invalid = True

    return {
        "total_synthesized": len(synthesis_reports),
        "all_valid": not has_invalid,
        "reports": synthesis_reports,
    }


# =========================================================================
# v8.2 Phase 2: 全局角色选择质量评分（适用于所有角色，非仅合成角色）
# =========================================================================

# 默认阈值（可被 role_selection_strategy.yaml 中的 quality_thresholds 覆盖）
_DEFAULT_QUALITY_THRESHOLDS = {
    "synthesis_minimum": 6.0,
    "synthesis_warning": 7.0,
    "overall_minimum": 0.5,
    "overall_warning": 0.7,
    "alignment_weight": 0.6,
    "coverage_weight": 0.4,
}


def _load_quality_thresholds() -> Dict[str, float]:
    """从 role_selection_strategy.yaml 加载质量阈值，失败时使用默认值"""
    try:
        import yaml
        from pathlib import Path

        config_path = Path(__file__).parent.parent / "config" / "role_selection_strategy.yaml"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            thresholds = config.get("quality_thresholds", {})
            if thresholds:
                merged = {**_DEFAULT_QUALITY_THRESHOLDS, **thresholds}
                logger.debug(f"[v8.2] 已加载质量阈值配置: {merged}")
                return merged
    except Exception as e:
        logger.debug(f"[v8.2] 加载质量阈值失败，使用默认值: {e}")
    return _DEFAULT_QUALITY_THRESHOLDS.copy()


def _score_task_role_alignment(
    roles_data: List[Dict[str, Any]],
    gene_pool_keywords: Optional[Dict[str, List[str]]] = None,
) -> Tuple[float, List[str]]:
    """
    v8.2 Phase 2: 任务-角色对齐度评分

    检查每个角色的任务描述是否与其 gene_pool 关键词高度匹配。
    高分 = 角色被分配了与其专长匹配的任务。

    Args:
        roles_data: 角色数据列表 (含 role_id, tasks)
        gene_pool_keywords: {role_id_prefix: [keywords]} 映射

    Returns:
        (score 0-1, messages)
    """
    if not roles_data:
        return 1.0, ["无角色数据"]

    if not gene_pool_keywords:
        gene_pool_keywords = _load_gene_pool_keywords()

    msgs = []
    alignment_scores = []

    for role in roles_data:
        role_id = role.get("role_id", "")
        tasks = role.get("tasks", [])
        if not tasks:
            continue

        # 根据 role_id 查找对应的 gene_pool keywords
        # role_id 格式: "2-1", "5-3" 等
        role_keywords = gene_pool_keywords.get(role_id, [])
        if not role_keywords:
            # 退化: 无 gene_pool 数据，给中等分
            alignment_scores.append(0.6)
            continue

        task_text = " ".join(tasks).lower()
        matched = sum(1 for kw in role_keywords if kw.lower() in task_text)
        ratio = matched / len(role_keywords) if role_keywords else 0

        alignment_scores.append(min(1.0, ratio * 2))  # 50%匹配即满分

        if ratio < 0.15:
            msgs.append(f"角色 {role_id} 任务与专长匹配度极低 ({ratio:.0%})，" f"关键词: {role_keywords[:3]}")

    avg_score = sum(alignment_scores) / len(alignment_scores) if alignment_scores else 0.6
    if not msgs:
        msgs.append(f"任务-角色整体对齐良好 (平均: {avg_score:.0%})")

    return round(avg_score, 3), msgs


def _score_deliverable_coverage(
    roles_data: List[Dict[str, Any]],
) -> Tuple[float, List[str]]:
    """
    v8.2 Phase 2: 交付物覆盖度评分

    检查角色选择是否覆盖了足够多样化的交付物，避免"少交付物+多角色"的低效配置。

    Args:
        roles_data: 角色数据列表 (含 role_id, deliverable_count)

    Returns:
        (score 0-1, messages)
    """
    if not roles_data:
        return 1.0, ["无角色数据"]

    msgs = []
    total_deliverables = 0
    role_count = len(roles_data)

    for role in roles_data:
        # 统计交付物数量
        deliverable_count = role.get("deliverable_count", 0)
        if deliverable_count == 0:
            # 尝试从 task_instruction 推断
            ti = role.get("task_instruction", {})
            if isinstance(ti, dict):
                deliverable_count = len(ti.get("deliverables", []))
        total_deliverables += deliverable_count

    # 评分: 平均交付物数 >= 2 则满分，<1 则低分
    avg_deliverables = total_deliverables / role_count if role_count else 0

    if avg_deliverables >= 2.5:
        score = 1.0
        msgs.append(f"交付物覆盖充分: 共{total_deliverables}个交付物, 平均{avg_deliverables:.1f}个/角色")
    elif avg_deliverables >= 1.5:
        score = 0.8
        msgs.append(f"交付物覆盖合理: 共{total_deliverables}个, 平均{avg_deliverables:.1f}个/角色")
    elif avg_deliverables >= 1.0:
        score = 0.6
        msgs.append(f"交付物偏少: 共{total_deliverables}个, 平均{avg_deliverables:.1f}个/角色")
    else:
        score = 0.3
        msgs.append(f"交付物严重不足: 共{total_deliverables}个, 平均{avg_deliverables:.1f}个/角色")

    # 检查是否有角色无交付物
    empty_roles = [
        r.get("role_id", "?")
        for r in roles_data
        if r.get("deliverable_count", 0) == 0 and not r.get("task_instruction", {}).get("deliverables")
    ]
    if empty_roles:
        score -= 0.15
        msgs.append(f"存在无交付物的角色: {empty_roles}")

    return round(max(0, score), 3), msgs


def _load_gene_pool_keywords() -> Dict[str, List[str]]:
    """从 role_selection_strategy.yaml 加载 role_gene_pool 的关键词映射"""
    try:
        import yaml
        from pathlib import Path

        config_path = Path(__file__).parent.parent / "config" / "role_selection_strategy.yaml"
        if not config_path.exists():
            return {}

        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        gene_pool = config.get("role_gene_pool", {})
        keywords_map: Dict[str, List[str]] = {}

        for _v_key, v_data in gene_pool.items():
            roles = v_data.get("roles", {})
            for role_id, role_info in roles.items():
                kws = role_info.get("keywords", [])
                if kws:
                    keywords_map[role_id] = kws

        logger.debug(f"[v8.2] 已加载 {len(keywords_map)} 个角色的 gene_pool 关键词")
        return keywords_map
    except Exception as e:
        logger.debug(f"[v8.2] 加载 gene_pool 关键词失败: {e}")
        return {}


def validate_overall_quality(
    selected_roles: List[Dict[str, Any]],
    gene_pool_keywords: Optional[Dict[str, List[str]]] = None,
) -> Dict[str, Any]:
    """
    v8.2 Phase 2: 全局角色选择质量评分

    适用于所有角色选择结果（包含合成和非合成角色），评估:
    1. 任务-角色对齐度: 角色是否被分配了匹配其专长的任务
    2. 交付物覆盖度: 是否覆盖了足够多样化的交付物

    Args:
        selected_roles: 角色数据列表
        gene_pool_keywords: 可选的关键词映射（用于测试注入）

    Returns:
        {
            "overall_score": float (0-1),
            "is_acceptable": bool,
            "alignment_score": float,
            "coverage_score": float,
            "warnings": List[str],
            "thresholds": Dict[str, float],
        }
    """
    thresholds = _load_quality_thresholds()

    alignment_score, alignment_msgs = _score_task_role_alignment(selected_roles, gene_pool_keywords)
    coverage_score, coverage_msgs = _score_deliverable_coverage(selected_roles)

    # 加权总分
    w_align = thresholds.get("alignment_weight", 0.6)
    w_cover = thresholds.get("coverage_weight", 0.4)
    overall_score = alignment_score * w_align + coverage_score * w_cover

    is_acceptable = overall_score >= thresholds.get("overall_minimum", 0.5)
    warnings = []

    if overall_score < thresholds.get("overall_warning", 0.7):
        warnings.extend(alignment_msgs)
        warnings.extend(coverage_msgs)

    logger.info(
        f"[v8.2 OQS] 全局质量评分: {overall_score:.2f} "
        f"(对齐={alignment_score:.2f}, 覆盖={coverage_score:.2f}), "
        f"{'合格' if is_acceptable else '不合格'}"
    )

    return {
        "overall_score": round(overall_score, 3),
        "is_acceptable": is_acceptable,
        "alignment_score": round(alignment_score, 3),
        "coverage_score": round(coverage_score, 3),
        "warnings": warnings,
        "thresholds": thresholds,
    }
