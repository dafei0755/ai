"""
Layer 2 动态热点池候选筛选工具

Phase 3.2实施：从q.txt的190个案例中筛选20-30个动态热点示例

筛选标准：
1. 与Layer 1特征向量差异度 >0.4（避免重复）
2. 项目发生时间 <2年（保持新鲜度）- 暂时跳过
3. 涵盖新兴方向（元宇宙/碳中和/适老化/疗愈等）
4. 标签覆盖未被Layer 1覆盖的组合

Author: AI Architecture Team
Version: v8.100.0
Date: 2026-02-17
"""

import yaml
import math
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger


class Layer2CandidateSelector:
    """Layer 2候选示例筛选器"""

    def __init__(self, examples_dir: Optional[Path] = None, q_txt_path: Optional[Path] = None):
        """
        初始化筛选器

        Args:
            examples_dir: Few-shot示例目录
            q_txt_path: q.txt文件路径
        """
        if examples_dir is None:
            examples_dir = Path(__file__).parent.parent / "config" / "prompts" / "few_shot_examples"

        if q_txt_path is None:
            q_txt_path = Path(__file__).parent.parent.parent / "sf" / "q.txt"

        self.examples_dir = examples_dir
        self.q_txt_path = q_txt_path

        # 加载Layer 1示例
        self.layer1_examples = self._load_layer1_examples()

        logger.info(f"✅ 初始化Layer2筛选器，Layer 1示例数: {len(self.layer1_examples)}")

    def _load_layer1_examples(self) -> List[Dict[str, Any]]:
        """加载Layer 1（静态标杆库）示例"""
        registry_path = self.examples_dir / "examples_registry.yaml"

        if not registry_path.exists():
            logger.warning(f"⚠️ 注册表不存在: {registry_path}")
            return []

        try:
            with open(registry_path, "r", encoding="utf-8") as f:
                registry = yaml.safe_load(f)

            # 暂时假设所有示例都是Layer 1（未来需要在registry中标记layer）
            examples = registry.get("examples", [])

            return examples

        except Exception as e:
            logger.error(f"❌ 加载注册表失败: {e}")
            return []

    def parse_q_txt(self) -> List[Dict[str, Any]]:
        """
        解析q.txt文件，提取190个项目案例

        Returns:
            项目案例列表
        """
        if not self.q_txt_path.exists():
            logger.error(f"❌ q.txt文件不存在: {self.q_txt_path}")
            return []

        try:
            with open(self.q_txt_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 正则提取编号格式 "1. 项目描述"
            import re

            pattern = r"(\d+)\.\s*(.+?)(?=\d+\.|$)"
            matches = re.findall(pattern, content, re.DOTALL)

            projects = []
            for match in matches:
                q_id, description = match
                description = description.strip()

                if len(description) < 10:  # 过滤太短的
                    continue

                projects.append(
                    {"q_id": f"Q{q_id}", "description": description[:500], "full_description": description}  # 只保留前500字符
                )

            logger.info(f"✅ 从q.txt提取 {len(projects)} 个项目案例")
            return projects

        except Exception as e:
            logger.error(f"❌ 解析q.txt失败: {e}")
            return []

    def extract_features_from_description(self, description: str) -> Dict[str, Any]:
        """
        从项目描述中提取特征向量和标签

        简化版：基于关键词匹配

        Args:
            description: 项目描述文本

        Returns:
            {
                "feature_vector": {...},
                "tags_matrix": {...},
                "dominant_feature": str,
            }
        """
        desc_lower = description.lower()

        # 1. 特征向量（12维）
        feature_vector = {
            "cultural": 0.0,
            "commercial": 0.0,
            "aesthetic": 0.0,
            "functional": 0.0,
            "sustainable": 0.0,
            "social": 0.0,
            "technical": 0.0,
            "historical": 0.0,
            "regional": 0.0,
            "material_innovation": 0.0,
            "experiential": 0.0,
            "symbolic": 0.0,
        }

        # 文化维度关键词
        if any(kw in desc_lower for kw in ["文化", "艺术", "书法", "绘画", "传统", "非遗", "民俗"]):
            feature_vector["cultural"] += 0.3

        # 商业维度关键词
        if any(kw in desc_lower for kw in ["商业", "零售", "销售", "营业额", "盈利", "投资回报", "roi"]):
            feature_vector["commercial"] += 0.3

        # 功能维度关键词
        if any(kw in desc_lower for kw in ["功能", "使用", "效率", "流线", "动线", "空间组织"]):
            feature_vector["functional"] += 0.3

        # 技术维度关键词
        if any(kw in desc_lower for kw in ["技术", "智能", "自动化", "系统", "设备", "科技", "创新技术"]):
            feature_vector["technical"] += 0.3

        # 可持续维度关键词
        if any(kw in desc_lower for kw in ["可持续", "绿色", "节能", "环保", "碳中和", "低碳", "生态"]):
            feature_vector["sustainable"] += 0.3

        # 社会维度关键词
        if any(kw in desc_lower for kw in ["社区", "社会", "公共", "共享", "包容", "无障碍", "适老"]):
            feature_vector["social"] += 0.3

        # 历史维度关键词
        if any(kw in desc_lower for kw in ["历史", "遗产", "保护", "修复", "古建", "传统建筑"]):
            feature_vector["historical"] += 0.3

        # 地域维度关键词
        if any(kw in desc_lower for kw in ["地域", "本土", "在地", "乡村", "村落", "地方"]):
            feature_vector["regional"] += 0.3

        # 审美维度关键词
        if any(kw in desc_lower for kw in ["审美", "美感", "视觉", "形式", "造型", "美学"]):
            feature_vector["aesthetic"] += 0.3

        # 体验维度关键词
        if any(kw in desc_lower for kw in ["体验", "感受", "氛围", "场景", "沉浸", "互动"]):
            feature_vector["experiential"] += 0.3

        # 2. 归一化
        max_val = max(feature_vector.values())
        if max_val > 0:
            for key in feature_vector:
                feature_vector[key] = min(1.0, feature_vector[key] / max_val)

        # 3. 提取主导维度
        dominant_feature = max(feature_vector.items(), key=lambda x: x[1])[0]

        # 4. 提取标签（简化版）
        tags_matrix = {
            "space_type": self._extract_space_type(description),
            "scale": self._extract_scale(description),
            "design_direction": [dominant_feature],
        }

        return {
            "feature_vector": feature_vector,
            "tags_matrix": tags_matrix,
            "dominant_feature": dominant_feature,
        }

    def _extract_space_type(self, description: str) -> List[str]:
        """提取空间类型"""
        space_types = []
        desc_lower = description.lower()

        # 数据标注脚本内部分类（粗粒度标签，不对应 PROJECT_TYPE_REGISTRY ID）
        space_keywords = {
            "hotel": ["酒店", "宾馆", "民宿"],
            "residential": ["住宅", "居住", "公寓", "家庭"],
            "office": ["办公", "写字楼", "联合办公"],
            "commercial": ["商业", "零售", "商场", "店铺"],
            "museum": ["博物馆", "美术馆", "展览"],
            "restaurant": ["餐饮", "餐厅", "咖啡", "茶馆"],
            "public_space": ["公共空间", "广场", "公园"],
            "market": ["市场", "菜市场", "集市"],
        }

        for space_type, keywords in space_keywords.items():
            if any(kw in desc_lower for kw in keywords):
                space_types.append(space_type)

        return space_types if space_types else ["unknown"]

    def _extract_scale(self, description: str) -> str:
        """提取项目规模"""
        import re

        # 提取面积数字
        area_match = re.search(r"(\d+)(?:平米|㎡|平方米)", description)
        if area_match:
            area = int(area_match.group(1))
            if area < 50:
                return "micro"
            elif area < 200:
                return "small"
            elif area < 2000:
                return "medium"
            elif area < 10000:
                return "large"
            else:
                return "xlarge"

        # 客房数量
        room_match = re.search(r"(\d+)(?:间|套)(?:客房|房间)", description)
        if room_match:
            rooms = int(room_match.group(1))
            if rooms < 20:
                return "small"
            elif rooms < 100:
                return "medium"
            else:
                return "large"

        return "medium"

    def calculate_diversity_score(
        self, candidate_features: Dict[str, Any], layer1_examples: List[Dict[str, Any]]
    ) -> float:
        """
        计算候选示例与Layer 1的差异度

        Args:
            candidate_features: 候选项目的特征
            layer1_examples: Layer 1示例列表

        Returns:
            差异度分数 (0-1)，越高越好
        """
        if not layer1_examples:
            return 1.0

        candidate_vector = candidate_features.get("feature_vector", {})

        min_similarity = 1.0
        for example in layer1_examples:
            example_vector = example.get("feature_vector", {})
            if example_vector:
                similarity = self._cosine_similarity(candidate_vector, example_vector)
                min_similarity = min(min_similarity, similarity)

        # 差异度 = 1 - 最小相似度（即最大距离）
        diversity = 1 - min_similarity
        return diversity

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

    def select_layer2_candidates(
        self, target_count: int = 25, diversity_threshold: float = 0.4
    ) -> List[Dict[str, Any]]:
        """
        筛选Layer 2候选示例

        Args:
            target_count: 目标数量（20-30个）
            diversity_threshold: 差异度阈值（>0.4）

        Returns:
            候选示例列表，按差异度排序
        """
        logger.info(f"🔍 开始筛选Layer 2候选示例...")

        # 1. 解析q.txt
        all_projects = self.parse_q_txt()

        if not all_projects:
            logger.warning("⚠️ 未找到任何项目案例")
            return []

        # 2. 提取特征并计算差异度
        scored_candidates = []

        for project in all_projects:
            features = self.extract_features_from_description(project["full_description"])

            diversity_score = self.calculate_diversity_score(features, self.layer1_examples)

            if diversity_score >= diversity_threshold:
                scored_candidates.append(
                    {
                        "q_id": project["q_id"],
                        "description": project["description"],
                        "features": features,
                        "diversity_score": diversity_score,
                    }
                )

        # 3. 排序并选取Top N
        scored_candidates.sort(key=lambda x: x["diversity_score"], reverse=True)
        layer2_candidates = scored_candidates[:target_count]

        logger.info(f"✅ 筛选完成: {len(layer2_candidates)} 个候选示例")
        for i, candidate in enumerate(layer2_candidates[:10], 1):
            logger.info(
                f"   {i}. {candidate['q_id']} "
                f"(差异度={candidate['diversity_score']:.3f}, "
                f"主导={candidate['features']['dominant_feature']})"
            )

        return layer2_candidates

    def export_candidates_to_yaml(self, candidates: List[Dict[str, Any]], output_path: Optional[Path] = None):
        """
        导出候选示例为YAML文件

        Args:
            candidates: 候选示例列表
            output_path: 输出文件路径
        """
        if output_path is None:
            output_path = Path(__file__).parent.parent.parent.parent / "layer2_candidates.yaml"

        export_data = {
            "metadata": {
                "version": "v8.100.0",
                "selection_date": "2026-02-17",
                "total_candidates": len(candidates),
                "diversity_threshold": 0.4,
            },
            "candidates": [],
        }

        for candidate in candidates:
            export_data["candidates"].append(
                {
                    "q_id": candidate["q_id"],
                    "description": candidate["description"],
                    "dominant_feature": candidate["features"]["dominant_feature"],
                    "diversity_score": candidate["diversity_score"],
                    "feature_vector": candidate["features"]["feature_vector"],
                    "tags_matrix": candidate["features"]["tags_matrix"],
                }
            )

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                yaml.dump(export_data, f, allow_unicode=True, sort_keys=False)

            logger.info(f"✅ 候选示例已导出: {output_path}")

        except Exception as e:
            logger.error(f"❌ 导出失败: {e}")


def main():
    """主函数：执行Layer 2候选筛选"""
    selector = Layer2CandidateSelector()

    # 筛选候选示例
    candidates = selector.select_layer2_candidates(target_count=25, diversity_threshold=0.4)

    # 导出结果
    if candidates:
        selector.export_candidates_to_yaml(candidates)

    return candidates


if __name__ == "__main__":
    main()
