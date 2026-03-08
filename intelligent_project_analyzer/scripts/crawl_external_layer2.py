"""
外部Layer 2候选爬取脚本

功能:
1. 从Archdaily和Gooood爬取最新项目
2. 使用LLM提取特征向量
3. 计算与Layer 1的差异度
4. 筛选Top 20候选
5. 保存到external_layer2_cache.json

定时任务:
- 每月1日自动执行
- Cron表达式: 0 0 1 * *

Author: AI Architecture Team
Version: v8.110.0
Date: 2026-02-17
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# 添加项目根目录到path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger

from intelligent_project_analyzer.crawlers import (
    ArchdailyCrawler,
    CrawlerConfig,
    GoooodCrawler,
    ProjectData,
)

# 配置日志
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO",
)


def extract_features_with_llm(project: ProjectData) -> Dict[str, Any]:
    """
    使用LLM提取项目特征

    TODO: 集成实际的LLM调用
    当前为模拟版本

    Args:
        project: 项目数据

    Returns:
        {
            "feature_vector": {...},  # 12维特征向量
            "tags_matrix": {...},     # 7维标签矩阵
            "extended_features": {...} # 5个新维度
        }
    """
    # 模拟LLM提取
    # 实际应该调用：llm_service.extract_project_features(project.description)

    logger.info(f"   🤖 提取特征: {project.title}")

    return {
        "feature_vector": {
            "cultural": 0.5,
            "commercial": 0.3,
            "aesthetic": 0.7,
            "functional": 0.6,
            "sustainable": 0.4,
            "social": 0.2,
            "technical": 0.5,
            "historical": 0.1,
            "regional": 0.3,
            "material_innovation": 0.4,
            "experiential": 0.6,
            "symbolic": 0.3,
        },
        "tags_matrix": {
            "space_type": ["residential"] if "residential" in project.url else ["commercial"],
            "scale": "medium",
            "design_direction": ["modern"],
            "user_profile": ["high_end"],
            "challenge_type": ["space_optimization"],
            "methodology": ["systematic"],
            "phase": ["complete"],
        },
        "extended_features": {
            "discipline": "architecture",
            "urgency": 0.3,
            "innovation_quotient": 0.6,
            "commercial_sensitivity": 0.5,
            "cultural_depth": 0.4,
        },
    }


def calculate_diversity_score(candidate_features: Dict[str, Any], layer1_features: List[Dict[str, Any]]) -> float:
    """
    计算候选与Layer 1的差异度

    Args:
        candidate_features: 候选项目特征
        layer1_features: Layer 1示例特征列表

    Returns:
        差异度分数（0-1，越大越不同）
    """
    import math

    candidate_vector = candidate_features["feature_vector"]

    min_similarity = 1.0

    for layer1 in layer1_features:
        layer1_vector = layer1.get("feature_vector", {})

        # 余弦相似度
        dot_product = sum(candidate_vector.get(k, 0) * layer1_vector.get(k, 0) for k in candidate_vector.keys())

        mag_a = math.sqrt(sum(v**2 for v in candidate_vector.values()))
        mag_b = math.sqrt(sum(v**2 for v in layer1_vector.values()))

        if mag_a > 0 and mag_b > 0:
            similarity = dot_product / (mag_a * mag_b)
            min_similarity = min(min_similarity, similarity)

    diversity = 1.0 - min_similarity
    return diversity


def load_layer1_examples() -> List[Dict[str, Any]]:
    """
    加载Layer 1示例特征

    Returns:
        Layer 1示例列表
    """
    registry_path = (
        project_root
        / "intelligent_project_analyzer"
        / "config"
        / "prompts"
        / "few_shot_examples"
        / "examples_registry.yaml"
    )

    if not registry_path.exists():
        logger.warning(f"⚠️ 注册表不存在: {registry_path}")
        return []

    import yaml

    with open(registry_path, encoding="utf-8") as f:
        registry = yaml.safe_load(f)

    # 简化：直接返回示例ID列表
    # 实际应该加载每个示例的完整特征
    examples = registry.get("examples", [])

    logger.info(f"✅ 加载 {len(examples)} 个Layer 1示例")

    # 模拟特征（实际应该从YAML文件加载）
    return [
        {
            "feature_vector": {
                k: 0.5
                for k in [
                    "cultural",
                    "commercial",
                    "aesthetic",
                    "functional",
                    "sustainable",
                    "social",
                    "technical",
                    "historical",
                    "regional",
                    "material_innovation",
                    "experiential",
                    "symbolic",
                ]
            }
        }
        for _ in examples
    ]


def main(use_login: bool = False, test_mode: bool = False):
    """
    主函数

    Args:
        use_login: 是否使用登录（从配置文件读取）
        test_mode: 测试模式（仅爬取3个项目）
    """
    logger.info("=" * 80)
    logger.info("🚀 开始爬取外部Layer 2候选项目")
    logger.info("=" * 80)

    # 1. 配置爬虫
    if use_login:
        # 尝试从配置文件读取
        try:
            from intelligent_project_analyzer.config.crawler_credentials import (
                ARCHDAILY_CONFIG,
                GOOOOD_CONFIG,
            )

            logger.info("✅ 已加载登录配置")
            config_archdaily = ARCHDAILY_CONFIG
            config_gooood = GOOOOD_CONFIG
        except ImportError:
            logger.warning("⚠️ 未配置登录凭证，使用默认配置")
            use_login = False

    if not use_login:
        # 默认配置（无登录）
        config_archdaily = CrawlerConfig(
            max_retries=3,
            request_delay=3.0,  # 3秒延迟，避免被封
            timeout=30,
            days_back=30,  # 最近30天
            min_views=5000,  # 最少5000浏览
            max_projects=3 if test_mode else 20,  # 测试模式：3个
            use_proxy=False,
        )
        config_gooood = config_archdaily

    # 测试模式：减少项目数量
    if test_mode:
        config_archdaily.max_projects = 3
        config_gooood.max_projects = 3
        config_archdaily.request_delay = 5.0  # 测试时更慢，更安全
        config_gooood.request_delay = 5.0
        logger.warning("⚠️ 测试模式：max_projects=3, request_delay=5.0秒")

    all_projects: List[ProjectData] = []

    # 2. 爬取Archdaily
    logger.info("\n" + "=" * 80)
    logger.info("📡 爬取Archdaily中国区")
    logger.info("=" * 80)

    try:
        archdaily = ArchdailyCrawler(config=config_archdaily, category="residential")
        archdaily_projects = archdaily.fetch()
        all_projects.extend(archdaily_projects)
        logger.success(f"✅ Archdaily: {len(archdaily_projects)} 个项目")
    except Exception as e:
        logger.error(f"❌ Archdaily爬取失败: {e}")
        import traceback

        traceback.print_exc()

    # 3. 爬取Gooood
    logger.info("\n" + "=" * 80)
    logger.info("📡 爬取Gooood")
    logger.info("=" * 80)

    try:
        gooood = GoooodCrawler(config=config_gooood, category="residential")
        gooood_projects = gooood.fetch()
        all_projects.extend(gooood_projects)
        logger.success(f"✅ Gooood: {len(gooood_projects)} 个项目")
    except Exception as e:
        logger.error(f"❌ Gooood爬取失败: {e}")

    logger.info(f"\n📊 总计爬取: {len(all_projects)} 个项目")

    if not all_projects:
        logger.error("❌ 未爬取到任何项目，退出")
        return

    # 4. LLM特征提取
    logger.info("\n" + "=" * 80)
    logger.info("🤖 LLM特征提取")
    logger.info("=" * 80)

    layer1_features = load_layer1_examples()

    analyzed_projects = []
    for project in all_projects:
        try:
            features = extract_features_with_llm(project)
            diversity_score = calculate_diversity_score(features, layer1_features)

            analyzed_projects.append(
                {
                    "source": project.source,
                    "title": project.title,
                    "url": project.url,
                    "description": project.description[:500],
                    "location": project.location,
                    "architects": project.architects,
                    "area": project.area,
                    "year": project.year,
                    "tags": project.tags,
                    "publish_date": project.publish_date.isoformat() if project.publish_date else None,
                    "features": features,
                    "diversity_score": diversity_score,
                }
            )

            logger.info(f"   ✅ {project.title} (差异度={diversity_score:.3f})")

        except Exception as e:
            logger.error(f"   ❌ 特征提取失败: {project.title} - {e}")

    # 5. 筛选Top 20（按差异度排序）
    logger.info("\n" + "=" * 80)
    logger.info("🎯 筛选Top 20候选")
    logger.info("=" * 80)

    # 过滤差异度<0.4的
    valid_candidates = [p for p in analyzed_projects if p["diversity_score"] >= 0.4]
    logger.info(f"   通过差异度阈值: {len(valid_candidates)}/{len(analyzed_projects)}")

    # 排序
    valid_candidates.sort(key=lambda x: x["diversity_score"], reverse=True)

    # 取Top 20
    top_candidates = valid_candidates[:20]

    for idx, candidate in enumerate(top_candidates, 1):
        logger.info(f"   {idx}. {candidate['title']} (差异度={candidate['diversity_score']:.3f})")

    # 6. 保存到缓存文件
    logger.info("\n" + "=" * 80)
    logger.info("💾 保存到缓存")
    logger.info("=" * 80)

    cache_path = project_root / "intelligent_project_analyzer" / "data" / "external_layer2_cache.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    cache_data = {
        "version": "v8.110.0",
        "crawl_time": datetime.now().isoformat(),
        "total_crawled": len(all_projects),
        "total_analyzed": len(analyzed_projects),
        "total_selected": len(top_candidates),
        "diversity_threshold": 0.4,
        "candidates": top_candidates,
    }

    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=2)

    logger.success(f"✅ 缓存已保存: {cache_path}")
    logger.success("   有效期: 30天")

    # 7. 统计
    logger.info("\n" + "=" * 80)
    logger.info("📊 爬取统计")
    logger.info("=" * 80)
    logger.info(f"   总爬取: {len(all_projects)} 个项目")
    logger.info(f"   成功分析: {len(analyzed_projects)} 个")
    logger.info(f"   通过筛选: {len(top_candidates)} 个")
    logger.info(f"   平均差异度: {sum(p['diversity_score'] for p in top_candidates) / len(top_candidates):.3f}")

    logger.success("\n🎉 爬取任务完成！")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="爬取外部Layer 2候选项目")
    parser.add_argument("--login", action="store_true", help="使用登录配置（需要先配置crawler_credentials.py）")
    parser.add_argument("--test", action="store_true", help="测试模式（仅爬取3个项目，延迟5秒）")

    args = parser.parse_args()

    main(use_login=args.login, test_mode=args.test)
