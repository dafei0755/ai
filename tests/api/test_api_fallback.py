"""
快速测试 API + 降级机制

测试流程:
1. 启动分析 → 触发 requirements_analyst
2. 观察日志：应该看到降级链创建和自动切换
3. 验证：OpenAI 429 → 自动切换到 DeepSeek/OpenRouter

运行: python test_api_fallback.py
"""

import requests
import time
import json
from loguru import logger
import sys

# 配置日志
logger.remove()
logger.add(sys.stdout, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")

BASE_URL = "http://127.0.0.1:8000"


def test_start_analysis():
    """测试启动分析（触发降级机制）"""
    logger.info("=" * 60)
    logger.info("📋 测试：启动分析 + 降级机制")
    logger.info("=" * 60)

    try:
        # 发送分析请求
        payload = {"user_id": "test_fallback", "user_input": "我需要设计一个现代化的住宅空间"}

        logger.info("🚀 发送分析请求...")
        response = requests.post(f"{BASE_URL}/api/analysis/start", json=payload, timeout=120)

        if response.status_code != 200:
            logger.error(f"❌ 请求失败: {response.status_code}")
            logger.error(f"响应: {response.text}")
            return False

        data = response.json()
        session_id = data.get("session_id")

        logger.success(f"✅ 分析已启动: {session_id}")

        # 等待几秒，让日志输出
        logger.info("\n⏳ 等待 5 秒，查看后端日志...")
        time.sleep(5)

        # 查询状态
        logger.info(f"\n📊 查询分析状态...")
        status_response = requests.get(f"{BASE_URL}/api/analysis/status/{session_id}", timeout=30)

        if status_response.status_code == 200:
            status_data = status_response.json()
            logger.info(f"当前状态: {status_data.get('status')}")
            logger.info(f"当前阶段: {status_data.get('current_stage')}")
            if status_data.get("errors"):
                logger.warning(f"错误信息: {status_data['errors']}")

        logger.info("\n" + "=" * 60)
        logger.info("💡 提示：查看后端终端日志，应该能看到：")
        logger.info("  1. 🔄 启用自动降级: deepseek → openrouter → openai")
        logger.info("  2. ✅ 预创建 deepseek/openrouter/openai LLM 成功")
        logger.info("  3. 🔄 降级链就绪: deepseek → openrouter → openai")
        logger.info("  4. ✅ deepseek 调用成功 (或自动切换)")
        logger.info("=" * 60)

        return True

    except requests.exceptions.Timeout:
        logger.error("❌ 请求超时（120秒）")
        return False
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    logger.info("🚀 开始 API + 降级机制测试\n")

    # 检查服务是否运行
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        logger.success(f"✅ 后端服务运行中: {response.json()}")
    except:
        logger.error("❌ 后端服务未启动，请先运行: python intelligent_project_analyzer/api/server.py")
        return 1

    # 测试启动分析
    success = test_start_analysis()

    if success:
        logger.success("\n🎉 测试完成！请查看后端终端日志确认降级机制是否生效")
        return 0
    else:
        logger.error("\n❌ 测试失败")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
