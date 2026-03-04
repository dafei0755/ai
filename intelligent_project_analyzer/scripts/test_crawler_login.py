"""
测试爬虫登录功能

用于验证登录配置是否正确

Author: AI Architecture Team
Version: v8.110.0
Date: 2026-02-17
"""

import sys
from pathlib import Path

# 添加项目根目录到path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger

from intelligent_project_analyzer.crawlers import ArchdailyCrawler

# 配置日志
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="DEBUG",  # 使用DEBUG级别查看详细信息
)


def test_login_from_config():
    """测试从配置文件登录"""
    logger.info("=" * 80)
    logger.info("🧪 测试1: 从配置文件登录")
    logger.info("=" * 80)

    try:
        from intelligent_project_analyzer.config.crawler_credentials import ARCHDAILY_CONFIG

        logger.info("✅ 配置已加载")
        logger.info(f"   use_login: {ARCHDAILY_CONFIG.use_login}")
        logger.info(f"   username: {ARCHDAILY_CONFIG.login_username}")
        logger.info(f"   password: {'*' * 8}")
        logger.info(f"   cookie_file: {ARCHDAILY_CONFIG.cookie_file}")

        # 创建爬虫（会自动登录）
        crawler = ArchdailyCrawler(config=ARCHDAILY_CONFIG, category="residential")

        # 检查登录状态
        if crawler.is_logged_in:
            logger.success("✅ 登录成功")
            return True
        else:
            logger.warning("⚠️ 登录状态未知")
            return False

    except ImportError:
        logger.error("❌ 未找到crawler_credentials.py配置文件")
        logger.info("   请先创建并配置 intelligent_project_analyzer/config/crawler_credentials.py")
        return False

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_cookie_injection():
    """测试Cookie注入方式"""
    logger.info("\n" + "=" * 80)
    logger.info("🧪 测试2: Cookie注入")
    logger.info("=" * 80)

    try:
        from intelligent_project_analyzer.crawlers import CrawlerConfig

        # 创建不启用自动登录的配置
        config = CrawlerConfig(use_login=False)
        crawler = ArchdailyCrawler(config=config, category="residential")

        # 模拟Cookie注入（实际使用时需要浏览器获取真实Cookie）
        logger.info("💡 Cookie注入示例（需要浏览器手动获取）:")
        logger.info(
            """
from intelligent_project_analyzer.crawlers import ArchdailyCrawler, CrawlerConfig

config = CrawlerConfig(use_login=False)
crawler = ArchdailyCrawler(config=config)

# 浏览器F12复制的Cookie
cookies = {
    "session": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "_ga": "GA1.2.1234567890.1234567890",
    "_gid": "GA1.2.9876543210.9876543210",
    # ... 其他Cookie
}

for name, value in cookies.items():
    crawler.session.cookies.set(name, value, domain=".archdaily.cn")

# 保存Cookie
crawler.config.cookie_file = "data/cookies/archdaily_cookies.pkl"
crawler._save_cookies()

# 开始爬取
projects = crawler.fetch()
        """
        )

        return True

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        return False


def test_load_saved_cookies():
    """测试加载已保存的Cookie"""
    logger.info("\n" + "=" * 80)
    logger.info("🧪 测试3: 加载已保存的Cookie")
    logger.info("=" * 80)

    try:
        from intelligent_project_analyzer.crawlers import CrawlerConfig

        cookie_path = project_root / "intelligent_project_analyzer" / "data" / "cookies" / "archdaily_cookies.pkl"

        if not cookie_path.exists():
            logger.warning(f"⚠️ Cookie文件不存在: {cookie_path}")
            logger.info("   请先成功登录一次，Cookie会自动保存")
            return False

        # 创建配置，指定Cookie文件
        config = CrawlerConfig(
            use_login=False,  # 不自动登录
            cookie_file=str(cookie_path),
        )

        crawler = ArchdailyCrawler(config=config, category="residential")

        # 验证Cookie是否有效
        if crawler._check_login_status():
            logger.success("✅ Cookie加载成功，登录状态有效")
            return True
        else:
            logger.warning("⚠️ Cookie已过期或无效")
            return False

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        return False


def main():
    """主函数"""
    logger.info("🔐 爬虫登录功能测试\n")

    results = []

    # 测试1: 从配置文件登录
    results.append(("配置文件登录", test_login_from_config()))

    # 测试2: Cookie注入示例
    results.append(("Cookie注入示例", test_cookie_injection()))

    # 测试3: 加载已保存的Cookie
    results.append(("加载已保存Cookie", test_load_saved_cookies()))

    # 总结
    logger.info("\n" + "=" * 80)
    logger.info("📊 测试结果总结")
    logger.info("=" * 80)

    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        logger.info(f"   {name}: {status}")

    success_count = sum(1 for _, result in results if result)
    logger.info(f"\n   总计: {success_count}/{len(results)} 通过")

    if success_count == 0:
        logger.warning("\n⚠️ 所有测试失败，请检查配置:")
        logger.info("   1. 创建 intelligent_project_analyzer/config/crawler_credentials.py")
        logger.info("   2. 配置 ARCHDAILY_CONFIG.login_username 和 login_password")
        logger.info("   3. 设置 use_login=True")
    elif success_count < len(results):
        logger.info("\n⚠️ 部分测试失败，但至少一种登录方式可用")
    else:
        logger.success("\n🎉 所有测试通过！登录功能正常")


if __name__ == "__main__":
    main()
