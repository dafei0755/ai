"""
本体论服务 (Ontology Service)

提供本体论框架的读取、搜索和验证功能。

版本: v1.0
创建日期: 2026-02-11
"""

import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from loguru import logger


class OntologyService:
    """本体论框架服务"""

    def __init__(self):
        self.ontology_path = Path(__file__).parent.parent / "knowledge_base" / "ontology.yaml"
        self._cache: Optional[Dict[str, Any]] = None

    def _load_ontology(self) -> Dict[str, Any]:
        """加载本体论文件（带缓存）"""
        if self._cache is None:
            try:
                with open(self.ontology_path, "r", encoding="utf-8") as f:
                    self._cache = yaml.safe_load(f)
                logger.info(f" 加载本体论文件: {self.ontology_path}")
            except Exception as e:
                logger.error(f" 加载本体论失败: {e}")
                self._cache = {"ontology_frameworks": {}}
        return self._cache

    def reload(self):
        """重新加载本体论（清除缓存）"""
        self._cache = None
        return self._load_ontology()

    def get_all_frameworks(self) -> List[Dict[str, Any]]:
        """
        获取所有本体论框架概览

        Returns:
            [
                {
                    "id": "personal_residential",
                    "name": "个人/住宅项目框架",
                    "categories": ["spiritual_world", "social_coordinates", ...],
                    "total_dimensions": 25
                },
                ...
            ]
        """
        ontology = self._load_ontology()
        frameworks = ontology.get("ontology_frameworks", {})

        result = []
        framework_names = {
            "meta_framework": "通用元框架",
            "personal_residential": "个人/住宅项目",
            "hybrid_residential_commercial": "混合型项目",
            "commercial_enterprise": "商业/企业项目",
            "cultural_educational": "文化/教育项目",
            "healthcare_wellness": "医疗/康养项目",
            "office_coworking": "办公/共享空间",
            "hospitality_tourism": "酒店/文旅项目",
            "sports_entertainment_arts": "体育/娱乐/艺术",
            "industrial_manufacturing": "工业/制造空间",
            "transportation": "交通枢纽",
            "urban_planning": "城市规划",
            "sustainable_regenerative": "可持续/再生项目",
        }

        for framework_id, framework_data in frameworks.items():
            categories = list(framework_data.keys())

            # 统计总维度数
            total_dims = 0
            for category_data in framework_data.values():
                if isinstance(category_data, list):
                    total_dims += len(category_data)

            result.append(
                {
                    "id": framework_id,
                    "name": framework_names.get(framework_id, framework_id),
                    "categories": categories,
                    "total_dimensions": total_dims,
                }
            )

        logger.info(f" 获取框架概览: {len(result)} 个框架")
        return result

    def get_framework_detail(self, project_type: str) -> Optional[Dict[str, Any]]:
        """
        获取单个框架的详细维度树

        Args:
            project_type: 项目类型（如 "personal_residential"）

        Returns:
            {
                "id": "personal_residential",
                "name": "个人/住宅项目框架",
                "categories": [
                    {
                        "id": "spiritual_world",
                        "name": "精神世界",
                        "dimensions": [
                            {
                                "name": "核心价值观 (Core Values)",
                                "description": "...",
                                "ask_yourself": "...",
                                "examples": "..."
                            },
                            ...
                        ]
                    },
                    ...
                ]
            }
        """
        ontology = self._load_ontology()
        frameworks = ontology.get("ontology_frameworks", {})

        framework_data = frameworks.get(project_type)
        if not framework_data:
            logger.warning(f"️ 框架不存在: {project_type}")
            return None

        # 转换为结构化格式
        categories = []
        for category_id, dimensions in framework_data.items():
            if not isinstance(dimensions, list):
                continue

            categories.append(
                {"id": category_id, "name": self._prettify_category_name(category_id), "dimensions": dimensions}
            )

        logger.info(f" 获取框架详情: {project_type}, {len(categories)} 个类别")

        return {"id": project_type, "name": self._get_framework_name(project_type), "categories": categories}

    def search_dimensions(self, keyword: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        按关键词搜索维度

        Args:
            keyword: 搜索关键词
            limit: 返回结果数量

        Returns:
            [
                {
                    "name": "核心价值观 (Core Values)",
                    "description": "...",
                    "framework": "personal_residential",
                    "category": "spiritual_world",
                    "match_score": 0.95
                },
                ...
            ]
        """
        ontology = self._load_ontology()
        frameworks = ontology.get("ontology_frameworks", {})

        keyword_lower = keyword.lower()
        results = []

        for framework_id, framework_data in frameworks.items():
            for category_id, dimensions in framework_data.items():
                if not isinstance(dimensions, list):
                    continue

                for dim in dimensions:
                    # 计算匹配度
                    score = 0
                    if keyword_lower in dim.get("name", "").lower():
                        score += 10
                    if keyword_lower in dim.get("description", "").lower():
                        score += 5
                    if keyword_lower in dim.get("ask_yourself", "").lower():
                        score += 3
                    if keyword_lower in dim.get("examples", "").lower():
                        score += 2

                    if score > 0:
                        results.append(
                            {
                                "name": dim.get("name", "Unknown"),
                                "description": dim.get("description", ""),
                                "ask_yourself": dim.get("ask_yourself", ""),
                                "examples": dim.get("examples", ""),
                                "framework": framework_id,
                                "framework_name": self._get_framework_name(framework_id),
                                "category": category_id,
                                "category_name": self._prettify_category_name(category_id),
                                "match_score": score,
                            }
                        )

        # 按匹配度排序
        results.sort(key=lambda x: x["match_score"], reverse=True)

        logger.info(f" 搜索维度 '{keyword}': {len(results)} 个结果")

        return results[:limit]

    def validate_yaml_syntax(self) -> bool:
        """验证 ontology.yaml 语法正确性"""
        try:
            with open(self.ontology_path, "r", encoding="utf-8") as f:
                yaml.safe_load(f)
            logger.info(" ontology.yaml 语法验证通过")
            return True
        except Exception as e:
            logger.error(f" ontology.yaml 语法错误: {e}")
            return False

    # ============ 辅助方法 ============

    def _get_framework_name(self, framework_id: str) -> str:
        """获取框架的友好名称"""
        names = {
            "meta_framework": "通用元框架",
            "personal_residential": "个人/住宅项目框架",
            "hybrid_residential_commercial": "混合型项目框架",
            "commercial_enterprise": "商业/企业项目框架",
            "cultural_educational": "文化/教育项目框架",
            "healthcare_wellness": "医疗/康养项目框架",
            "office_coworking": "办公/共享空间框架",
            "hospitality_tourism": "酒店/文旅项目框架",
            "sports_entertainment_arts": "体育/娱乐/艺术框架",
            "industrial_manufacturing": "工业/制造空间框架",
            "transportation": "交通枢纽框架",
            "urban_planning": "城市规划框架",
            "sustainable_regenerative": "可持续/再生项目框架",
        }
        return names.get(framework_id, framework_id)

    def _prettify_category_name(self, category_id: str) -> str:
        """美化类别名称"""
        names = {
            "universal_dimensions": "通用维度",
            "contemporary_imperatives": "当代命题",
            "spiritual_world": "精神世界",
            "social_coordinates": "社会坐标",
            "material_life": "物质生活",
            "dual_identity": "双重身份",
            "business_positioning": "商业定位",
            "operational_strategy": "运营策略",
            "customer_experience": "顾客体验",
            "staff_team": "员工与团队",
            "brand_communication": "品牌传播",
        }
        return names.get(category_id, category_id.replace("_", " ").title())


# ============ 全局实例 ============

_ontology_service: Optional[OntologyService] = None


def get_ontology_service() -> OntologyService:
    """获取全局本体论服务实例"""
    global _ontology_service
    if _ontology_service is None:
        _ontology_service = OntologyService()
    return _ontology_service
