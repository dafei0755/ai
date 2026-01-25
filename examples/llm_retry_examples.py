"""
LLM重试机制使用示例

演示如何在项目中使用新的LLM重试功能

作者：Design Beyond Team
日期：2026-01-04
版本：v7.131
"""

import asyncio

from langchain_core.messages import HumanMessage, SystemMessage


# 示例1: 基础使用 - 使用默认配置
async def example_basic_usage():
    """最简单的使用方式"""
    from intelligent_project_analyzer.services.llm_factory import LLMFactory
    from intelligent_project_analyzer.utils.llm_retry import ainvoke_llm_with_retry

    print("\n" + "=" * 60)
    print("示例1: 基础使用 - 使用默认配置")
    print("=" * 60)

    # 创建LLM
    llm = LLMFactory.create_llm()

    # 准备消息
    messages = [SystemMessage(content="你是一个有帮助的助手"), HumanMessage(content="请用一句话介绍什么是设计思维？")]

    # 使用重试机制调用（使用默认配置：3次重试，30秒超时）
    try:
        response = await ainvoke_llm_with_retry(llm, messages)
        print(f"✅ 成功: {response.content[:100]}...")
    except Exception as e:
        print(f"❌ 失败: {type(e).__name__}: {e}")


# 示例2: 自定义配置 - 调整重试参数
async def example_custom_config():
    """自定义重试配置"""
    from intelligent_project_analyzer.services.llm_factory import LLMFactory
    from intelligent_project_analyzer.utils.llm_retry import LLMRetryConfig, ainvoke_llm_with_retry

    print("\n" + "=" * 60)
    print("示例2: 自定义配置 - 调整重试参数")
    print("=" * 60)

    # 创建LLM
    llm = LLMFactory.create_llm()

    # 自定义重试配置（更激进的重试策略）
    config = LLMRetryConfig(
        max_attempts=5, min_wait=0.5, max_wait=15.0, timeout=60.0  # 最多尝试5次  # 最短等待0.5秒  # 最长等待15秒  # 单次调用60秒超时
    )

    messages = [HumanMessage(content="解释一下室内设计中的动线规划原则")]

    try:
        response = await ainvoke_llm_with_retry(llm, messages, config=config)
        print(f"✅ 成功（使用自定义配置）: {response.content[:100]}...")
    except Exception as e:
        print(f"❌ 失败: {type(e).__name__}: {e}")


# 示例3: 装饰器方式 - 更简洁的代码
async def example_decorator():
    """使用装饰器方式"""
    from intelligent_project_analyzer.services.llm_factory import LLMFactory
    from intelligent_project_analyzer.utils.llm_retry import async_llm_retry

    print("\n" + "=" * 60)
    print("示例3: 装饰器方式 - 更简洁的代码")
    print("=" * 60)

    # 使用装饰器包装函数
    @async_llm_retry(max_attempts=3, timeout=30)
    async def generate_design_analysis(llm, project_description):
        """生成设计分析（自动重试）"""
        messages = [SystemMessage(content="你是一个专业的室内设计分析师"), HumanMessage(content=f"请分析以下项目需求：{project_description}")]
        return await llm.ainvoke(messages)

    # 创建LLM
    llm = LLMFactory.create_llm()

    try:
        response = await generate_design_analysis(llm, "100平米现代简约风格公寓")
        print(f"✅ 成功（装饰器方式）: {response.content[:100]}...")
    except Exception as e:
        print(f"❌ 失败: {type(e).__name__}: {e}")


# 示例4: 在类方法中使用
class DesignAnalyzer:
    """设计分析器示例"""

    def __init__(self):
        from intelligent_project_analyzer.services.llm_factory import LLMFactory

        self.llm = LLMFactory.create_llm()

    async def analyze_with_retry(self, user_input: str) -> str:
        """分析用户需求（带重试）"""
        from intelligent_project_analyzer.utils.llm_retry import LLMRetryConfig, ainvoke_llm_with_retry

        # 配置重试参数（从配置文件读取或使用默认值）
        config = LLMRetryConfig(max_attempts=3, timeout=30.0)

        messages = [SystemMessage(content="你是一个室内设计需求分析专家"), HumanMessage(content=f"请分析：{user_input}")]

        response = await ainvoke_llm_with_retry(self.llm, messages, config=config)
        return response.content


async def example_class_method():
    """在类方法中使用重试"""
    print("\n" + "=" * 60)
    print("示例4: 在类方法中使用")
    print("=" * 60)

    analyzer = DesignAnalyzer()

    try:
        result = await analyzer.analyze_with_retry("深圳200平米办公空间设计")
        print(f"✅ 成功（类方法）: {result[:100]}...")
    except Exception as e:
        print(f"❌ 失败: {type(e).__name__}: {e}")


# 示例5: 实际应用场景 - Gap Question Generator
async def example_gap_question_generator():
    """真实场景：Gap Question Generator 使用重试"""
    from intelligent_project_analyzer.services.llm_factory import LLMFactory
    from intelligent_project_analyzer.services.llm_gap_question_generator import LLMGapQuestionGenerator

    print("\n" + "=" * 60)
    print("示例5: 实际应用 - Gap Question Generator")
    print("=" * 60)

    # 创建生成器（会自动加载配置中的重试参数）
    generator = LLMGapQuestionGenerator()

    # 准备测试数据
    user_input = "深圳蛇口150平米住宅设计"
    confirmed_tasks = [{"title": "空间布局规划", "description": "设计功能分区和动线"}, {"title": "风格定位", "description": "确定设计风格方向"}]
    missing_dimensions = ["预算约束", "时间节点"]
    covered_dimensions = ["基本信息"]

    # 创建LLM
    llm = LLMFactory.create_llm()

    try:
        # 生成问题（内部使用重试机制）
        questions = await generator.generate(
            user_input=user_input,
            confirmed_tasks=confirmed_tasks,
            missing_dimensions=missing_dimensions,
            covered_dimensions=covered_dimensions,
            existing_info_summary="用户提供了基本的项目信息",
            completeness_score=0.3,
            llm=llm,
        )

        print(f"✅ 成功生成 {len(questions)} 个问题")
        for i, q in enumerate(questions[:3], 1):  # 只显示前3个
            print(f"   {i}. {q.get('question', 'N/A')}")
    except Exception as e:
        print(f"❌ 失败: {type(e).__name__}: {e}")


# 示例6: 错误处理和降级策略
async def example_error_handling():
    """演示错误处理和降级策略"""
    from intelligent_project_analyzer.services.llm_factory import LLMFactory
    from intelligent_project_analyzer.utils.llm_retry import LLMRetryConfig, ainvoke_llm_with_retry

    print("\n" + "=" * 60)
    print("示例6: 错误处理和降级策略")
    print("=" * 60)

    # 创建LLM
    llm = LLMFactory.create_llm()

    # 配置较激进的重试（快速失败）
    config = LLMRetryConfig(max_attempts=2, min_wait=0.5, max_wait=2.0, timeout=10.0)

    messages = [HumanMessage(content="测试消息")]

    try:
        response = await ainvoke_llm_with_retry(llm, messages, config=config)
        print(f"✅ LLM调用成功")
        return response.content
    except Exception as e:
        # 降级策略：使用预定义的回答
        print(f"⚠️ LLM调用失败，启用降级策略: {type(e).__name__}")
        fallback_response = "（由于网络问题，使用预定义回答）您好，我们的设计团队会尽快为您提供方案。"
        print(f"🔄 降级回答: {fallback_response}")
        return fallback_response


# 主函数 - 运行所有示例
async def main():
    """运行所有示例"""
    print("\n" + "🚀 LLM重试机制使用示例")
    print("=" * 60)
    print("演示如何在项目中使用新的重试功能\n")

    examples = [
        ("基础使用", example_basic_usage),
        ("自定义配置", example_custom_config),
        ("装饰器方式", example_decorator),
        ("类方法使用", example_class_method),
        ("实际应用", example_gap_question_generator),
        ("错误处理", example_error_handling),
    ]

    for name, example_func in examples:
        try:
            await example_func()
        except Exception as e:
            print(f"\n❌ 示例 '{name}' 执行失败: {type(e).__name__}: {e}")

        # 添加分隔符
        print()

    print("=" * 60)
    print("✅ 所有示例演示完毕")
    print("=" * 60)


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())
