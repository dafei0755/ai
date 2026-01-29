"""
系统配置验证脚本 - v7.142
验证雷达图动态维度和智能问卷生成的配置状态
"""

import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))


def check_env_config():
    """检查环境变量配置"""
    print("=" * 80)
    print("🔍 环境变量配置检查")
    print("=" * 80)

    # 检查关键环境变量
    configs = {
        "USE_DYNAMIC_GENERATION": ("动态维度生成", "true"),
        "ENABLE_DIMENSION_LEARNING": ("维度学习", "false"),
        "USE_LLM_GAP_QUESTIONS": ("LLM智能问卷", "true"),
        "ENABLE_EXPERT_FORESIGHT": ("专家视角预判", "true"),
    }

    for key, (name, default) in configs.items():
        value = os.getenv(key, default)
        status = "✅ 启用" if value.lower() == "true" else "⚠️ 禁用"
        print(f"{status} {name:15s} = {value:6s} (环境变量: {key})")

    print()


def check_config_files():
    """检查配置文件"""
    print("=" * 80)
    print("📋 配置文件检查")
    print("=" * 80)

    config_dir = Path("intelligent_project_analyzer/config/prompts")
    files = [
        ("radar_dimensions.yaml", "雷达图维度库"),
        ("gap_question_generator.yaml", "LLM问卷生成器配置"),
        ("dimension_generation_prompts.yaml", "动态维度生成Prompt"),
    ]

    for filename, description in files:
        filepath = config_dir / filename
        if filepath.exists():
            size = filepath.stat().st_size
            print(f"✅ {description:25s} ({filename})")
            print(f"   路径: {filepath}")
            print(f"   大小: {size:,} bytes")
        else:
            print(f"❌ {description:25s} 文件不存在!")
        print()


def check_services():
    """检查服务类"""
    print("=" * 80)
    print("🔧 服务类检查")
    print("=" * 80)

    try:
        from intelligent_project_analyzer.services.dynamic_dimension_generator import DynamicDimensionGenerator

        print("✅ DynamicDimensionGenerator - 动态维度生成器")
        generator = DynamicDimensionGenerator()
        print(f"   初始化成功")
    except Exception as e:
        print(f"❌ DynamicDimensionGenerator 加载失败: {e}")

    print()

    try:
        from intelligent_project_analyzer.services.llm_gap_question_generator import LLMGapQuestionGenerator

        print("✅ LLMGapQuestionGenerator - LLM智能问卷生成器")
        gen = LLMGapQuestionGenerator()
        print(f"   初始化成功")
    except Exception as e:
        print(f"❌ LLMGapQuestionGenerator 加载失败: {e}")

    print()

    try:
        from intelligent_project_analyzer.services.dimension_selector import DimensionSelector

        print("✅ DimensionSelector - 维度选择器")
        selector = DimensionSelector()
        all_dims = selector.get_all_dimensions()
        print(f"   维度总数: {len(all_dims)}")
    except Exception as e:
        print(f"❌ DimensionSelector 加载失败: {e}")


def main():
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "系统配置验证 - v7.142" + " " * 37 + "║")
    print("╚" + "=" * 78 + "╝")
    print()

    check_env_config()
    check_config_files()
    check_services()

    print("=" * 80)
    print("✅ 系统配置验证完成")
    print("=" * 80)
    print()
    print("📝 总结:")
    print("   1. 动态维度生成: 默认启用，会根据用户需求生成定制维度")
    print("   2. LLM智能问卷: 默认启用，问题会引用用户原话并动态调整选项")
    print("   3. 专家视角预判: 默认启用，会提前预测需要的专家角色")
    print()
    print("🚀 如需测试完整功能:")
    print("   1. 启动后端: python -B scripts\\run_server_production.py")
    print("   2. 启动前端: cd frontend-nextjs && npm run dev")
    print("   3. 访问: http://localhost:3000")
    print()


if __name__ == "__main__":
    main()
