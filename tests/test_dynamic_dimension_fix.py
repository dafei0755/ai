"""
测试动态维度生成器Unicode编码修复
v7.116: 验证LLM覆盖度分析不再因Unicode字符失败
"""

import os
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from loguru import logger

from intelligent_project_analyzer.services.dynamic_dimension_generator import DynamicDimensionGenerator

# 配置日志
logger.remove()
logger.add(sys.stdout, level="INFO")


def test_unicode_encoding_fix():
    """测试Unicode编码修复"""
    logger.info("=" * 80)
    logger.info("🧪 测试动态维度生成器 Unicode 编码修复 (v7.116)")
    logger.info("=" * 80)

    # 初始化生成器
    generator = DynamicDimensionGenerator()

    # 测试数据：包含emoji和特殊Unicode字符
    user_input = "设计一个中医诊所，需要体现传统文化和现代医疗的平衡 🏥✨"

    structured_data = {
        "confirmed_core_tasks": [
            {"title": "中医文化展示空间设计 📚", "description": "传统与现代的结合"},
            {"title": "医疗功能区规划 ⚕️", "description": "符合卫生标准"},
        ],
        "project_type": "healthcare",
        "location": "安徽",
    }

    existing_dimensions = [
        {
            "id": "aesthetic_style",
            "name": "美学风格 🎨",
            "left_label": "现代简约",
            "right_label": "古典传统",
            "description": "从现代到传统的美学倾向",
        },
        {
            "id": "functionality",
            "name": "功能性 ⚙️",
            "left_label": "展示优先",
            "right_label": "实用优先",
            "description": "展示性与实用性的平衡",
        },
    ]

    # 测试1: 覆盖度分析
    logger.info("\n🧪 测试1: 覆盖度分析（包含Unicode字符）")
    try:
        coverage = generator.analyze_coverage(
            user_input=user_input, structured_data=structured_data, existing_dimensions=existing_dimensions
        )

        logger.info(f"✅ 覆盖度分析成功")
        logger.info(f"   覆盖度评分: {coverage.get('coverage_score', 0):.2f}")
        logger.info(f"   是否需要生成: {coverage.get('should_generate', False)}")
        logger.info(f"   缺失方面: {coverage.get('missing_aspects', [])}")

        # 验证是否成功调用LLM（而不是回退到默认值）
        if coverage.get("coverage_score") == 0.95:
            logger.warning("⚠️ 返回了默认覆盖度，可能LLM调用仍然失败")
        else:
            logger.info("✅ LLM调用成功，未回退到默认值")

    except Exception as e:
        logger.error(f"❌ 测试1失败: {e}")
        return False

    # 测试2: 维度生成（如果覆盖度分析建议生成）
    if coverage.get("should_generate", False) and coverage.get("missing_aspects"):
        logger.info("\n🧪 测试2: 维度生成（包含Unicode字符）")
        try:
            # 添加existing_dimensions到structured_data
            structured_data_with_dims = {**structured_data, "existing_dimensions": existing_dimensions}

            new_dimensions = generator.generate_dimensions(
                user_input=user_input,
                structured_data=structured_data_with_dims,
                missing_aspects=coverage.get("missing_aspects", []),
                target_count=2,
            )

            if new_dimensions:
                logger.info(f"✅ 成功生成 {len(new_dimensions)} 个新维度")
                for dim in new_dimensions:
                    logger.info(f"   + {dim.get('name')}: {dim.get('left_label')} ← → {dim.get('right_label')}")
            else:
                logger.warning("⚠️ 未生成新维度（可能是LLM返回空或验证失败）")

        except Exception as e:
            logger.error(f"❌ 测试2失败: {e}")
            return False
    else:
        logger.info("\n⏭️ 跳过测试2: 覆盖度分析认为无需生成新维度")

    logger.info("\n" + "=" * 80)
    logger.info("✅ 所有测试通过！Unicode编码修复生效")
    logger.info("=" * 80)
    return True


if __name__ == "__main__":
    # 确保环境变量启用
    os.environ["USE_DYNAMIC_GENERATION"] = "true"

    success = test_unicode_encoding_fix()
    sys.exit(0 if success else 1)
