"""
测试文件上传配置
验证不同分析模式的文件上传限制是否正确配置

v7.350
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from intelligent_project_analyzer.utils.mode_config import get_file_upload_config, is_file_upload_enabled, get_all_modes


def test_file_upload_config():
    """测试文件上传配置"""
    print("=" * 60)
    print("📎 文件上传配置测试")
    print("=" * 60)
    print()

    # 测试所有模式
    modes = get_all_modes()
    print(f"✅ 已加载 {len(modes)} 个分析模式\n")

    for mode_name in modes.keys():
        print(f"🔍 测试模式: {mode_name}")
        print("-" * 60)

        # 获取文件上传配置
        config = get_file_upload_config(mode_name)
        enabled = is_file_upload_enabled(mode_name)

        print(f"  启用状态: {'✅ 启用' if enabled else '❌ 禁用'}")
        print(f"  最大文件数: {config['max_files']}")
        print(f"  允许类型: {', '.join(config['allowed_types']) if config['allowed_types'] else '无'}")
        print()

    # 验证预期行为
    print("=" * 60)
    print("🧪 验证预期行为")
    print("=" * 60)
    print()

    # 测试 normal 模式
    normal_enabled = is_file_upload_enabled("normal")
    assert not normal_enabled, "❌ 普通模式应该禁用文件上传"
    print("✅ 普通模式正确禁用文件上传")

    normal_config = get_file_upload_config("normal")
    assert normal_config["max_files"] == 0, "❌ 普通模式最大文件数应为0"
    assert len(normal_config["allowed_types"]) == 0, "❌ 普通模式不应允许任何文件类型"
    print("✅ 普通模式配置正确")
    print()

    # 测试 deep_thinking 模式
    deep_enabled = is_file_upload_enabled("deep_thinking")
    assert deep_enabled, "❌ 深度思考模式应该启用文件上传"
    print("✅ 深度思考模式正确启用文件上传")

    deep_config = get_file_upload_config("deep_thinking")
    assert deep_config["max_files"] > 0, "❌ 深度思考模式最大文件数应大于0"
    assert len(deep_config["allowed_types"]) > 0, "❌ 深度思考模式应允许某些文件类型"
    print("✅ 深度思考模式配置正确")
    print(f"   - 最大文件数: {deep_config['max_files']}")
    print(f"   - 允许类型: {', '.join(deep_config['allowed_types'])}")
    print()

    print("=" * 60)
    print("🎉 所有测试通过！")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_file_upload_config()
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
