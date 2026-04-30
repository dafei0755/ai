"""
OpenRouter 负载均衡器使用示例

演示如何使用多 Key 负载均衡提高 API 调用的稳定性。
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from intelligent_project_analyzer.services.llm_factory import LLMFactory
from intelligent_project_analyzer.services.openrouter_load_balancer import (
    OpenRouterLoadBalancer,
    LoadBalancerConfig,
    get_global_balancer
)
from loguru import logger


def example_1_basic_usage():
    """示例 1: 基本使用"""
    logger.info("=" * 60)
    logger.info("示例 1: 基本使用")
    logger.info("=" * 60)

    # 方式 1: 通过 LLMFactory 创建（推荐）
    llm = LLMFactory.create_openrouter_balanced_llm()

    # 使用 LLM
    response = llm.invoke("用一句话介绍 OpenRouter")
    logger.info(f"响应: {response.content}")


def example_2_custom_strategy():
    """示例 2: 自定义负载均衡策略"""
    logger.info("=" * 60)
    logger.info("示例 2: 自定义负载均衡策略")
    logger.info("=" * 60)

    # 使用随机策略
    llm_random = LLMFactory.create_openrouter_balanced_llm(
        strategy="random",
        temperature=0.8
    )

    # 使用最少使用策略
    llm_least_used = LLMFactory.create_openrouter_balanced_llm(
        strategy="least_used",
        temperature=0.7
    )

    logger.info("✅ 创建了两个不同策略的 LLM 实例")


def example_3_direct_balancer():
    """示例 3: 直接使用负载均衡器"""
    logger.info("=" * 60)
    logger.info("示例 3: 直接使用负载均衡器")
    logger.info("=" * 60)

    # 创建自定义配置
    config = LoadBalancerConfig(
        strategy="round_robin",
        max_retries=5,
        retry_delay=2,
        rate_limit_per_key=100
    )

    # 创建负载均衡器
    balancer = OpenRouterLoadBalancer(
        config=config,
        model="openai/gpt-4o-2024-11-20",
        temperature=0.7,
        max_tokens=4000
    )

    # 获取 LLM 实例
    llm = balancer.get_llm()

    # 使用 LLM
    response = llm.invoke("什么是负载均衡？")
    logger.info(f"响应: {response.content}")

    # 查看统计
    balancer.print_stats()


def example_4_retry_mechanism():
    """示例 4: 使用重试机制"""
    logger.info("=" * 60)
    logger.info("示例 4: 使用重试机制")
    logger.info("=" * 60)

    balancer = OpenRouterLoadBalancer()

    # 使用内置的重试机制
    try:
        response = balancer.invoke_with_retry(
            "请用一句话解释什么是 API 负载均衡",
            temperature=0.7
        )
        logger.info(f"响应: {response.content}")
    except Exception as e:
        logger.error(f"所有重试都失败: {e}")


def example_5_statistics():
    """示例 5: 查看统计信息"""
    logger.info("=" * 60)
    logger.info("示例 5: 查看统计信息")
    logger.info("=" * 60)

    balancer = OpenRouterLoadBalancer()

    # 执行多次请求
    prompts = [
        "什么是人工智能？",
        "什么是机器学习？",
        "什么是深度学习？",
        "什么是神经网络？",
        "什么是自然语言处理？"
    ]

    for prompt in prompts:
        try:
            llm = balancer.get_llm()
            response = llm.invoke(prompt)
            logger.info(f"✅ 请求成功: {prompt[:20]}...")
        except Exception as e:
            logger.error(f"❌ 请求失败: {e}")

    # 打印统计
    balancer.print_stats()

    # 获取统计摘要
    summary = balancer.get_stats_summary()
    logger.info(f"\n总成功率: {summary['overall_success_rate']:.2%}")


def example_6_global_singleton():
    """示例 6: 使用全局单例"""
    logger.info("=" * 60)
    logger.info("示例 6: 使用全局单例")
    logger.info("=" * 60)

    # 获取全局负载均衡器
    balancer1 = get_global_balancer()
    balancer2 = get_global_balancer()

    # 验证是同一个实例
    assert balancer1 is balancer2
    logger.info("✅ 全局单例验证成功")

    # 使用全局负载均衡器
    llm = balancer1.get_llm()
    response = llm.invoke("Hello, world!")
    logger.info(f"响应: {response.content}")


def example_7_batch_requests():
    """示例 7: 批量请求"""
    logger.info("=" * 60)
    logger.info("示例 7: 批量请求")
    logger.info("=" * 60)

    balancer = OpenRouterLoadBalancer()

    # 批量请求
    questions = [
        "什么是设计思维？",
        "什么是用户体验？",
        "什么是产品设计？",
        "什么是交互设计？",
        "什么是视觉设计？",
        "什么是品牌设计？",
        "什么是服务设计？",
        "什么是系统设计？"
    ]

    results = []
    for i, question in enumerate(questions, 1):
        try:
            llm = balancer.get_llm()
            response = llm.invoke(question)
            results.append({
                "question": question,
                "answer": response.content,
                "success": True
            })
            logger.info(f"✅ [{i}/{len(questions)}] 完成: {question}")
        except Exception as e:
            results.append({
                "question": question,
                "error": str(e),
                "success": False
            })
            logger.error(f"❌ [{i}/{len(questions)}] 失败: {question}")

    # 统计结果
    success_count = sum(1 for r in results if r["success"])
    logger.info(f"\n批量请求完成: {success_count}/{len(questions)} 成功")

    # 打印统计
    balancer.print_stats()


def main():
    """主函数"""
    logger.info("🚀 OpenRouter 负载均衡器示例")
    logger.info("=" * 60)

    # 检查环境变量
    if not os.getenv("OPENROUTER_API_KEYS") and not os.getenv("OPENROUTER_API_KEY"):
        logger.error("❌ 未找到 OPENROUTER_API_KEYS 或 OPENROUTER_API_KEY 环境变量")
        logger.info("请在 .env 文件中配置:")
        logger.info("  OPENROUTER_API_KEYS=key1,key2,key3")
        return

    # 运行示例
    examples = [
        ("基本使用", example_1_basic_usage),
        ("自定义策略", example_2_custom_strategy),
        ("直接使用负载均衡器", example_3_direct_balancer),
        ("重试机制", example_4_retry_mechanism),
        ("统计信息", example_5_statistics),
        ("全局单例", example_6_global_singleton),
        ("批量请求", example_7_batch_requests)
    ]

    logger.info("\n可用示例:")
    for i, (name, _) in enumerate(examples, 1):
        logger.info(f"  {i}. {name}")

    # 运行所有示例（或根据需要选择）
    try:
        # 运行示例 1
        example_1_basic_usage()

        # 运行示例 5
        example_5_statistics()

    except KeyboardInterrupt:
        logger.info("\n\n⏹️ 用户中断")
    except Exception as e:
        logger.error(f"\n\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
