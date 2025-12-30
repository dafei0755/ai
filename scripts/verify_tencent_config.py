"""
腾讯云内容安全配置验证脚本
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from loguru import logger

# 加载环境变量
load_dotenv()


def verify_config():
    """验证腾讯云内容安全配置"""

    logger.info("=" * 60)
    logger.info("腾讯云内容安全配置验证")
    logger.info("=" * 60)

    errors = []
    warnings = []

    # 1. 检查是否启用
    enabled = os.getenv("ENABLE_TENCENT_CONTENT_SAFETY", "false").lower() == "true"
    if not enabled:
        logger.warning("⚠️ 腾讯云内容安全未启用 (ENABLE_TENCENT_CONTENT_SAFETY=false)")
        logger.info("💡 如需启用，请在.env文件中设置: ENABLE_TENCENT_CONTENT_SAFETY=true")
        return False

    logger.info("✅ 功能已启用 (ENABLE_TENCENT_CONTENT_SAFETY=true)")

    # 2. 检查SecretId
    secret_id = os.getenv("TENCENT_CLOUD_SECRET_ID")
    if not secret_id:
        errors.append("❌ 缺少TENCENT_CLOUD_SECRET_ID")
    elif not secret_id.startswith("AKID"):
        errors.append(f"❌ TENCENT_CLOUD_SECRET_ID格式错误（应以AKID开头）: {secret_id[:10]}...")
    else:
        logger.info(f"✅ SecretId已配置: {secret_id[:10]}...")

    # 3. 检查SecretKey
    secret_key = os.getenv("TENCENT_CLOUD_SECRET_KEY")
    if not secret_key:
        errors.append("❌ 缺少TENCENT_CLOUD_SECRET_KEY")
    elif len(secret_key) < 20:
        errors.append("❌ TENCENT_CLOUD_SECRET_KEY长度不足（应至少20字符）")
    else:
        logger.info(f"✅ SecretKey已配置 (长度: {len(secret_key)}字符)")

    # 4. 检查Region
    region = os.getenv("TENCENT_CLOUD_REGION")
    valid_regions = ["ap-guangzhou", "ap-beijing", "ap-shanghai", "ap-nanjing", "ap-chengdu"]
    if not region:
        warnings.append("⚠️ 未配置TENCENT_CLOUD_REGION，将使用默认值ap-guangzhou")
    elif region not in valid_regions:
        warnings.append(f"⚠️ TENCENT_CLOUD_REGION可能无效: {region}")
        warnings.append(f"   建议值: {', '.join(valid_regions)}")
    else:
        logger.info(f"✅ Region已配置: {region}")

    # 5. 检查应用配置
    app_id = os.getenv("TENCENT_CONTENT_SAFETY_APP_ID")
    if not app_id:
        errors.append("❌ 缺少TENCENT_CONTENT_SAFETY_APP_ID")
    else:
        logger.info(f"✅ 应用ID已配置: {app_id}")

    # 6. 检查BizType
    biztype_text = os.getenv("TENCENT_CONTENT_SAFETY_BIZTYPE_TEXT", "txt")
    biztype_image = os.getenv("TENCENT_CONTENT_SAFETY_BIZTYPE_IMAGE", "pic")
    logger.info(f"✅ 文本BizType: {biztype_text}")
    logger.info(f"✅ 图片BizType: {biztype_image}")

    # 7. 显示错误和警告
    if errors:
        logger.error("\n".join(errors))

    if warnings:
        for warning in warnings:
            logger.warning(warning)

    if errors:
        logger.error("❌ 配置验证失败，请修复以上错误")
        return False

    # 8. API调用测试（如果没有错误）
    logger.info("\n" + "=" * 60)
    logger.info("开始API调用测试...")
    logger.info("=" * 60)

    try:
        from intelligent_project_analyzer.security.tencent_content_safety import (
            TencentContentSafetyClient
        )

        client = TencentContentSafetyClient()

        # 测试正常文本
        test_text_safe = "这是一段测试文本，用于验证腾讯云内容安全API配置。"
        result_safe = client.check_text(test_text_safe)

        if result_safe.get("is_safe"):
            logger.info(f"✅ 正常文本检测通过: {result_safe['suggestion']}")
        else:
            logger.warning(f"⚠️ 正常文本被误判为违规: {result_safe}")

        # 测试敏感文本
        test_text_unsafe = "测试敏感词：赌博"
        result_unsafe = client.check_text(test_text_unsafe)

        logger.info(f"ℹ️ 敏感文本检测结果: {result_unsafe['suggestion']}")
        logger.info(f"   风险等级: {result_unsafe['risk_level']}")
        logger.info(f"   标签: {result_unsafe.get('label', 'N/A')}")
        logger.info(f"   分数: {result_unsafe.get('score', 0)}")

        logger.info("\n" + "=" * 60)
        logger.info("✅ 配置验证成功！腾讯云内容安全API可正常使用")
        logger.info("=" * 60)
        return True

    except Exception as e:
        logger.error(f"❌ API调用测试失败: {e}")
        logger.error("请检查:")
        logger.error("1. 子账号sf2025是否已分配QcloudTMSFullAccess权限")
        logger.error("2. SecretId和SecretKey是否正确")
        logger.error("3. Region是否正确")
        logger.error("4. 应用ID和BizType是否正确")
        return False


if __name__ == "__main__":
    success = verify_config()
    sys.exit(0 if success else 1)
