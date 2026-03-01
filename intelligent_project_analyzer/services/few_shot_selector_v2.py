"""
Few-shot示例选择器 v2.0 - 12维匹配升级

Phase 3.1实施：
1. 新增5个维度：discipline/urgency/innovation_quotient/commercial_sensitivity/cultural_depth
2. 12维综合匹配算法
3. 渐进式强度衰减
4. 用户历史项目追踪

Author: AI Architecture Team
Version: v8.100.0
Date: 2026-02-17
"""

import yaml
import json
import math
from pathlib import Path
from typing import Dict, Any, List, Optional
from loguru import logger
from collections import defaultdict


class FewShotSelectorV2:
    """
    Few-shot示例选择器 v2.0 - 12维匹配升级

    新特性：
    - 12维匹配（7维tags + 5维新增）
    - 渐进式强度衰减
    - 用户历史追踪
    - 多样性去重
    """

    def __init__(self, examples_dir: Optional[Path] = None):
        """
        初始化示例选择器

        Args:
            examples_dir: 示例库目录路径
        """
        if examples_dir is None:
            examples_dir = Path(__file__).parent.parent / "config" / "prompts" / "few_shot_examples"

        self.examples_dir = examples_dir
        self.registry: Dict[str, Any] = {}
        self.examples_cache: Dict[str, Dict[str, Any]] = {}

        # 用户历史追踪（示例ID -> 使用次数）— 持久化到 JSON
        self._history_path = Path(__file__).parent.parent / "data" / "few_shot_user_history.json"
        self.user_history: Dict[str, Dict[str, int]] = self._load_user_history()

        # 加载示例注册表
        self._load_registry()

    def _load_user_history(self) -> Dict[str, Dict[str, int]]:
        """从 JSON 文件加载用户使用历史"""
        try:
            if self._history_path.exists():
                with open(self._history_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # 转换为 defaultdict
                history = defaultdict(lambda: defaultdict(int))
                for user_id, examples in data.items():
                    for example_id, count in examples.items():
                        history[user_id][example_id] = count
                logger.info(f" [v2.0] 加载用户历史: {len(data)} 个用户")
                return history
        except Exception as e:
            logger.warning(f" 加载用户历史失败，使用空历史: {e}")
        return defaultdict(lambda: defaultdict(int))

    def _save_user_history(self) -> None:
        """持久化用户使用历史到 JSON 文件"""
        try:
            self._history_path.parent.mkdir(parents=True, exist_ok=True)
            # defaultdict -> 普通 dict 以便 JSON 序列化
            data = {uid: dict(examples) for uid, examples in self.user_history.items()}
            with open(self._history_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f" 保存用户历史失败: {e}")

    def _load_registry(self) -> None:
        """加载示例注册表"""
        registry_path = self.examples_dir / "examples_registry.yaml"

        if not registry_path.exists():
            logger.warning(f"⚠️ 示例注册表不存在: {registry_path}")
            self.registry = {"examples": []}
            return

        try:
            with open(registry_path, "r", encoding="utf-8") as f:
                self.registry = yaml.safe_load(f)

            example_count = len(self.registry.get("examples", []))
            logger.info(f"✅ [v2.0] 加载示例注册表: {example_count} 个示例")

        except Exception as e:
            logger.error(f"❌ 加载示例注册表失败: {e}")
            self.registry = {"examples": []}

    def match_examples_v2(
        self,
        project_input: Dict[str, Any],
        user_id: Optional[str] = None,
        top_k: int = 3,
        enable_diversity: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        v2.0 12维匹配算法

        Args:
            project_input: 项目输入特征
                {
                    "tags_matrix": {...},  # 7维标签
                    "feature_vector": {...},  # 12维能力向量
                    "discipline": str,  # 学科属性
                    "urgency": float,  # 紧急度 0-1
                    "innovation_quotient": float,  # 创新商 0-1
                    "commercial_sensitivity": float,  # 商业敏感度 0-1
                    "cultural_depth": float,  # 文化深度 0-1
                    "project_date": str,  # 项目日期（可选）
                }
            user_id: 用户ID（用于渐进式强度衰减）
            top_k: 返回示例数量
            enable_diversity: 是否启用多样性去重

        Returns:
            匹配的示例列表，按分数排序
        """
        logger.info("🔍 [v2.0] 开始12维匹配...")

        # 提取输入特征
        project_tags = project_input.get("tags_matrix", {})
        project_vector = project_input.get("feature_vector", {})
        discipline = project_input.get("discipline", "multidisciplinary")
        urgency = project_input.get("urgency", 0.5)
        innovation_quotient = project_input.get("innovation_quotient", 0.5)
        commercial_sensitivity = project_input.get("commercial_sensitivity", 0.5)
        cultural_depth = project_input.get("cultural_depth", 0.5)

        # 计算每个示例的综合得分
        scored_examples = []

        for example_meta in self.registry.get("examples", []):
            example_id = example_meta.get("id")
            example_tags = example_meta.get("tags_matrix", {})
            example_vector = example_meta.get("feature_vector", {})

            if not example_tags and not example_vector:
                continue

            # ========== 核心评分 ==========

            # 1. 标签重叠度（35%）
            tag_overlap_score = self._calculate_tag_overlap_v2(project_tags, example_tags)

            # 2. 能力向量相似度（25%）
            vector_similarity = self._cosine_similarity(project_vector, example_vector)

            # 3. 尺度匹配度（20%）
            scale_match_score = self._calculate_scale_match(project_tags.get("scale"), example_tags.get("scale"))

            # 4. 用户画像重叠（15%）
            user_overlap_score = self._calculate_user_profile_overlap(
                project_tags.get("user_profile", []), example_tags.get("user_profile", [])
            )

            # 5. 时间新鲜度（5%）- 仅Layer 2有效
            freshness_score = self._calculate_freshness_score(example_meta, project_input.get("project_date"))

            # ========== 新增5维调节 ==========

            # 6. 学科属性（精确匹配+0.1，不匹配-0.15）
            example_discipline = example_meta.get("discipline", "multidisciplinary")
            discipline_bonus = 0.1 if discipline == example_discipline else -0.15

            # 7. 紧急度（差异惩罚）
            example_urgency = example_meta.get("urgency", 0.5)
            urgency_penalty = -0.1 * abs(urgency - example_urgency)

            # 8. 创新商（影响示例强度选择）
            innovation_bonus = self._calculate_innovation_bonus(
                innovation_quotient, example_meta.get("recommended_strength", "medium")
            )

            # 9. 商业敏感度（差异<0.3加分，>0.5惩罚）
            example_commercial = example_meta.get("commercial_sensitivity", 0.5)
            commercial_bonus = self._calculate_dimension_bonus(commercial_sensitivity, example_commercial)

            # 10. 文化深度（差异<0.3加分，>0.5惩罚）
            example_cultural = example_meta.get("cultural_depth", 0.5)
            cultural_bonus = self._calculate_dimension_bonus(cultural_depth, example_cultural)

            # ========== 综合评分 ==========
            final_score = (
                0.35 * tag_overlap_score
                + 0.25 * vector_similarity
                + 0.20 * scale_match_score
                + 0.15 * user_overlap_score
                + 0.05 * freshness_score
                + discipline_bonus
                + urgency_penalty
                + innovation_bonus
                + commercial_bonus
                + cultural_bonus
            )

            # ========== 渐进式强度衰减 ==========
            if user_id:
                adjusted_strength = self._calculate_progressive_strength(
                    example_id, user_id, example_meta.get("recommended_strength", "medium")
                )
                example_meta["dynamic_strength"] = adjusted_strength

            scored_examples.append(
                {
                    "example_id": example_id,
                    "example_name": example_meta.get("name"),
                    "score": final_score,
                    "score_breakdown": {
                        "tag_overlap": tag_overlap_score,
                        "vector_similarity": vector_similarity,
                        "scale_match": scale_match_score,
                        "user_overlap": user_overlap_score,
                        "freshness": freshness_score,
                        "discipline": discipline_bonus,
                        "urgency": urgency_penalty,
                        "innovation": innovation_bonus,
                        "commercial": commercial_bonus,
                        "cultural": cultural_bonus,
                    },
                    "metadata": example_meta,
                }
            )

        # 排序
        scored_examples.sort(key=lambda x: x["score"], reverse=True)

        # 多样性去重
        if enable_diversity:
            scored_examples = self._select_diverse_top_k(scored_examples, top_k)
        else:
            scored_examples = scored_examples[:top_k]

        logger.info(f"✅ [v2.0] 匹配完成，返回 {len(scored_examples)} 个示例")
        for i, ex in enumerate(scored_examples, 1):
            logger.info(f"   {i}. {ex['example_name']} (分数={ex['score']:.3f})")

        return scored_examples

    def _calculate_tag_overlap_v2(self, project_tags: Dict[str, Any], example_tags: Dict[str, Any]) -> float:
        """
        计算7维标签重叠度

        维度权重：
        - space_type: 25%
        - challenge_type: 20%
        - design_direction: 20%
        - user_profile: 15%
        - scale: 15%
        - methodology: 5%
        - phase: 5%（暂不考虑，phase通常不影响示例选择）
        """
        weights = {
            "space_type": 0.25,
            "challenge_type": 0.20,
            "design_direction": 0.20,
            "user_profile": 0.15,
            "scale": 0.15,
            "methodology": 0.05,
        }

        total_score = 0.0

        for dimension, weight in weights.items():
            project_val = project_tags.get(dimension, [])
            example_val = example_tags.get(dimension, [])

            # 列表类型：Jaccard相似度
            if isinstance(project_val, list) and isinstance(example_val, list):
                if not project_val or not example_val:
                    dim_score = 0.0
                else:
                    intersection = len(set(project_val) & set(example_val))
                    union = len(set(project_val) | set(example_val))
                    dim_score = intersection / union if union > 0 else 0.0

            # 单值类型（如scale）：精确匹配
            elif isinstance(project_val, str) and isinstance(example_val, str):
                dim_score = 1.0 if project_val == example_val else 0.0

            else:
                dim_score = 0.0

            total_score += weight * dim_score

        return total_score

    @staticmethod
    def _cosine_similarity(vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        """计算余弦相似度"""
        if not vec1 or not vec2:
            return 0.0

        all_keys = set(vec1.keys()) | set(vec2.keys())
        if not all_keys:
            return 0.0

        dot_product = sum(vec1.get(k, 0) * vec2.get(k, 0) for k in all_keys)
        norm1 = math.sqrt(sum(vec1.get(k, 0) ** 2 for k in all_keys))
        norm2 = math.sqrt(sum(vec2.get(k, 0) ** 2 for k in all_keys))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    @staticmethod
    def _calculate_scale_match(project_scale: Optional[str], example_scale: Optional[str]) -> float:
        """
        计算尺度匹配度

        Scale顺序：micro < small < medium < large < xlarge
        差异0: 1.0
        差异1: 0.6
        差异2: 0.3
        差异>=3: 0.0
        """
        if not project_scale or not example_scale:
            return 0.5

        scale_order = ["micro", "small", "medium", "large", "xlarge"]

        try:
            p_idx = scale_order.index(project_scale)
            e_idx = scale_order.index(example_scale)
            diff = abs(p_idx - e_idx)

            if diff == 0:
                return 1.0
            elif diff == 1:
                return 0.6
            elif diff == 2:
                return 0.3
            else:
                return 0.0
        except ValueError:
            return 0.5

    @staticmethod
    def _calculate_user_profile_overlap(project_profiles: List[str], example_profiles: List[str]) -> float:
        """计算用户画像重叠度（Jaccard）"""
        if not project_profiles or not example_profiles:
            return 0.0

        intersection = len(set(project_profiles) & set(example_profiles))
        union = len(set(project_profiles) | set(example_profiles))

        return intersection / union if union > 0 else 0.0

    @staticmethod
    def _calculate_freshness_score(example_meta: Dict[str, Any], project_date: Optional[str] = None) -> float:
        """
        计算时间新鲜度（仅Layer 2有效）

        Layer 1/3: 返回0.5（中性）
        Layer 2:
            - <2年: 1.0
            - 2-3年: 0.5
            - >3年: 0.0
        """
        layer = example_meta.get("layer", 1)

        if layer != 2:
            return 0.5

        # TODO: 实际实施时需要从example_meta中读取project_date
        # 当前返回中性值
        return 0.5

    @staticmethod
    def _calculate_innovation_bonus(innovation_quotient: float, example_strength: str) -> float:
        """
        计算创新商调节值

        高创新需求（>0.7）: light示例+0.15，strong示例-0.1
        低创新需求（<0.3）: strong示例+0.15，light示例-0.1
        中等创新（0.3-0.7）: 中性0
        """
        if innovation_quotient > 0.7:
            if example_strength == "light":
                return 0.15
            elif example_strength == "strong":
                return -0.1
        elif innovation_quotient < 0.3:
            if example_strength == "strong":
                return 0.15
            elif example_strength == "light":
                return -0.1

        return 0.0

    @staticmethod
    def _calculate_dimension_bonus(project_value: float, example_value: float) -> float:
        """
        计算维度匹配加成

        差异<0.3: +0.1
        差异0.3-0.5: 0
        差异>0.5: -0.15
        """
        diff = abs(project_value - example_value)

        if diff < 0.3:
            return 0.1
        elif diff > 0.5:
            return -0.15
        else:
            return 0.0

    def _calculate_progressive_strength(self, example_id: str, user_id: str, base_strength: str) -> str:
        """
        渐进式强度衰减

        用户越熟悉某类项目，越应该鼓励创新而非依赖模板。

        规则：
        - 首次使用: 保持原强度
        - 2-3次: 降低一档
        - 3-5次: 降低两档
        - >5次: 全部轻示例
        """
        # 统计用户在该示例类别的使用次数
        # 简化版：直接计算该example_id的使用次数
        usage_count = self.user_history[user_id].get(example_id, 0)

        if usage_count == 0:
            return base_strength
        elif usage_count <= 2:
            strength_map = {"strong": "strong", "medium": "light", "light": "light"}
            return strength_map.get(base_strength, base_strength)
        elif usage_count <= 5:
            strength_map = {"strong": "medium", "medium": "light", "light": "light"}
            return strength_map.get(base_strength, base_strength)
        else:
            return "light"

    def load_example_content(self, example_meta: Dict[str, Any]) -> str:
        """
        [P0-S7.4] 从 YAML 文件加载示例的实际内容（ideal_tasks 等）

        Args:
            example_meta: 注册表中的示例元数据（包含 file 字段）

        Returns:
            示例内容文本，用于注入到专家 prompt 中
        """
        file_name = example_meta.get("file")
        if not file_name:
            return ""

        file_path = self.examples_dir / file_name
        if not file_path.exists():
            logger.debug(f"[S7.4] 示例文件不存在: {file_path}")
            return ""

        try:
            if file_name not in self.examples_cache:
                with open(file_path, "r", encoding="utf-8") as f:
                    self.examples_cache[file_name] = yaml.safe_load(f)

            data = self.examples_cache[file_name]
            if not data:
                return ""

            example_data = data.get("example", data)
            project_info = example_data.get("project_info", {})
            ideal_tasks = example_data.get("ideal_tasks", [])

            # 构建摘要文本
            parts = []
            name = project_info.get("name", example_meta.get("name", ""))
            if name:
                parts.append(f"项目: {name}")

            desc = project_info.get("description", "")
            if desc:
                parts.append(f"描述: {desc.strip()}")

            if ideal_tasks and isinstance(ideal_tasks, list):
                task_summaries = []
                for t in ideal_tasks[:8]:  # 限制前8个任务
                    title = t.get("title", "")
                    if title:
                        task_summaries.append(f"  - {title}")
                if task_summaries:
                    parts.append("参考任务拆解:\n" + "\n".join(task_summaries))

            return "\n".join(parts) if parts else ""

        except Exception as e:
            logger.debug(f"[S7.4] 加载示例内容失败 {file_name}: {e}")
            return ""

    def record_usage(self, example_id: str, user_id: str):
        """记录示例使用，用于渐进式强度衰减（持久化到磁盘）"""
        self.user_history[user_id][example_id] += 1
        logger.debug(
            f"📊 [v2.0] 记录使用: user={user_id}, example={example_id}, " f"count={self.user_history[user_id][example_id]}"
        )
        self._save_user_history()

    def _select_diverse_top_k(self, scored_examples: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
        """
        多样性去重选择

        避免返回的示例过于相似（如都是hotel类型）

        策略：
        1. 选择最高分示例
        2. 后续示例必须与已选示例的space_type重叠度<0.7
        """
        if len(scored_examples) <= top_k:
            return scored_examples

        selected = [scored_examples[0]]

        for candidate in scored_examples[1:]:
            if len(selected) >= top_k:
                break

            # 检查与已选示例的多样性
            is_diverse = True
            candidate_spaces = set(candidate["metadata"].get("tags_matrix", {}).get("space_type", []))

            for sel in selected:
                sel_spaces = set(sel["metadata"].get("tags_matrix", {}).get("space_type", []))

                if candidate_spaces and sel_spaces:
                    overlap = len(candidate_spaces & sel_spaces) / len(candidate_spaces | sel_spaces)
                    if overlap > 0.7:
                        is_diverse = False
                        break

            if is_diverse:
                selected.append(candidate)

        # 如果多样性去重后不足top_k，补充高分示例
        if len(selected) < top_k:
            for candidate in scored_examples:
                if candidate not in selected:
                    selected.append(candidate)
                    if len(selected) >= top_k:
                        break

        return selected


def calculate_project_extended_features(structured_data: Dict[str, Any], user_input: str) -> Dict[str, float]:
    """
    计算项目的5个新增维度特征

    Args:
        structured_data: 需求分析产出的结构化数据
        user_input: 用户原始输入

    Returns:
        {
            "discipline": str,  # architecture/interior/landscape/urban_planning/multidisciplinary
            "urgency": float,  # 0-1
            "innovation_quotient": float,  # 0-1
            "commercial_sensitivity": float,  # 0-1
            "cultural_depth": float,  # 0-1
        }
    """
    # 1. 学科属性（简化规则）
    raw_pt = structured_data.get("project_type", "")
    if isinstance(raw_pt, dict):
        raw_pt = raw_pt.get("primary", "") or str(raw_pt)
    project_type = str(raw_pt).lower()
    if any(kw in project_type for kw in ["building", "complex", "architecture"]):
        discipline = "architecture"
    elif any(kw in project_type for kw in ["interior", "residential", "apartment", "office"]):
        discipline = "interior"
    elif any(kw in project_type for kw in ["landscape", "garden", "park"]):
        discipline = "landscape"
    elif any(kw in project_type for kw in ["urban", "city", "district", "renewal"]):
        discipline = "urban_planning"
    else:
        discipline = "multidisciplinary"

    # 2. 紧急度（基于用户输入中的紧急关键词）
    urgency_keywords = ["urgent", "asap", "紧急", "急", "马上", "立即", "尽快"]
    urgency = 0.7 if any(kw in user_input.lower() for kw in urgency_keywords) else 0.4

    # 3. 创新商（基于用户表达）
    innovation_keywords = ["创新", "突破", "前沿", "实验", "探索", "未来", "颠覆"]
    conventional_keywords = ["传统", "经典", "常规", "标准"]

    innovation_count = sum(1 for kw in innovation_keywords if kw in user_input)
    conventional_count = sum(1 for kw in conventional_keywords if kw in user_input)

    if innovation_count > conventional_count:
        innovation_quotient = min(1.0, 0.5 + innovation_count * 0.15)
    elif conventional_count > innovation_count:
        innovation_quotient = max(0.0, 0.5 - conventional_count * 0.15)
    else:
        innovation_quotient = 0.5

    # 4. 商业敏感度（基于project_type和feature_vector）
    feature_vector = structured_data.get("project_info", {}).get("feature_vector", {})
    commercial_score = feature_vector.get("commercial", 0.0)

    if any(kw in project_type for kw in ["commercial", "retail", "mall", "sales"]):
        commercial_sensitivity = min(1.0, commercial_score + 0.3)
    elif any(kw in project_type for kw in ["public", "community", "social"]):
        commercial_sensitivity = max(0.0, commercial_score - 0.3)
    else:
        commercial_sensitivity = commercial_score

    # 5. 文化深度（基于feature_vector的cultural维度）
    cultural_score = feature_vector.get("cultural", 0.0)
    historical_score = feature_vector.get("historical", 0.0)
    symbolic_score = feature_vector.get("symbolic", 0.0)

    cultural_depth = cultural_score * 0.5 + historical_score * 0.3 + symbolic_score * 0.2

    return {
        "discipline": discipline,
        "urgency": urgency,
        "innovation_quotient": innovation_quotient,
        "commercial_sensitivity": commercial_sensitivity,
        "cultural_depth": cultural_depth,
    }


# [P0-S7] 全局单例
_few_shot_selector_v2: Optional[FewShotSelectorV2] = None


def get_few_shot_selector_v2() -> FewShotSelectorV2:
    """获取全局 FewShotSelectorV2 单例（避免每次调用重新加载注册表和历史）"""
    global _few_shot_selector_v2
    if _few_shot_selector_v2 is None:
        _few_shot_selector_v2 = FewShotSelectorV2()
    return _few_shot_selector_v2
