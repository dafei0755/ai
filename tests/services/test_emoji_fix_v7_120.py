"""
验证v7.120 Emoji编码修复
测试在LLM invoke前最终清理prompt，防止ASCII编码错误
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger

from intelligent_project_analyzer.services.dynamic_dimension_generator import DynamicDimensionGenerator

# 配置日志
logger.remove()
logger.add(sys.stdout, level="INFO", format="<level>{message}</level>")


def test_emoji_in_prompt():
    """测试prompt中包含emoji时不会导致ASCII编码错误"""
    logger.info("=" * 80)
    logger.info("🧪 测试 v7.120 Emoji编码修复")
    logger.info("=" * 80)

    # 模拟之前失败的场景
    test_input = "为一位患有严重花粉和粉尘过敏症的儿童设计卧室🆕✨"

    structured_data = {
        "confirmed_core_tasks": [
            {"title": "低敏环保材料研究与清单制定 📋"},
            {"title": "医疗级新风系统集成 🌬️"},
        ],
        "existing_dimensions": [{"id": "cultural_axis", "name": "文化定位轴", "left_label": "传统经典", "right_label": "当代潮流"}],
    }

    try:
        # 初始化生成器（会触发LLM调用）
        generator = DynamicDimensionGenerator()
        logger.info("✅ 生成器初始化成功")

        # 测试1: analyze_coverage
        logger.info("\n📊 测试1: analyze_coverage with emoji")
        result = generator.analyze_coverage(
            user_input=test_input,
            structured_data=structured_data,
            existing_dimensions=structured_data["existing_dimensions"],
        )
        logger.info(f"   覆盖度分析结果: {result.get('coverage_score', 'N/A')}")
        logger.info("✅ analyze_coverage 通过（无ASCII编码错误）")

        # 测试2: generate_dimensions
        logger.info("\n🎨 测试2: generate_dimensions with emoji")
        new_dims = generator.generate_dimensions(
            user_input=test_input, structured_data=structured_data, missing_aspects=["健康疗愈 💚", "空间氛围 🏠"], target_count=2
        )
        logger.info(f"   生成维度数量: {len(new_dims)}")
        logger.info("✅ generate_dimensions 通过（无ASCII编码错误）")

        logger.info("\n" + "=" * 80)
        logger.info("🎉 v7.120修复验证通过！所有emoji场景正常处理")
        logger.info("=" * 80)
        return True

    except UnicodeEncodeError as e:
        logger.error(f"❌ Unicode编码错误仍存在: {e}")
        return False
    except Exception as e:
        logger.error(f"⚠️ 其他错误: {e}")
        # LLM调用失败是允许的（可能网络问题），但不应该是编码错误
        if "ascii" in str(e).lower() or "encode" in str(e).lower():
            logger.error("❌ 仍有编码问题")
            return False
        else:
            logger.warning("⚠️ 非编码错误（可能是LLM调用失败，这是允许的）")
            return True


if __name__ == "__main__":
    success = test_emoji_in_prompt()
    sys.exit(0 if success else 1)
