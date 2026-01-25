"""
🆕 v7.127: 测试多图生成功能

测试普通模式（1张图）和深度思维模式（3张图）的概念图生成
"""

import asyncio
import sys
from pathlib import Path

import pytest

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from intelligent_project_analyzer.services.image_generator import ImageGeneratorService

pytestmark = pytest.mark.asyncio


async def test_single_image_generation():
    """测试普通模式（生成1张图）"""
    print("\n" + "=" * 80)
    print("测试1：普通模式 - 生成1张概念图")
    print("=" * 80)

    generator = ImageGeneratorService()

    metadata = {
        "id": "test-normal-001",
        "name": "现代简约客厅设计",
        "keywords": ["现代", "简约", "自然光"],
        "constraints": {"must_include": ["木质元素", "绿植"]},
        "owner_role": "室内设计师",
        "concept_image_config": {"count": 1, "editable": False},  # 普通模式
    }

    try:
        result = await generator.generate_deliverable_image(
            deliverable_metadata=metadata,
            expert_analysis="基于用户需求，设计现代简约风格的客厅空间",
            session_id="test-session-normal",
            project_type="interior",
        )

        print(f"\n✅ 测试通过！")
        print(f"   - 返回类型: {type(result)}")
        print(f"   - 生成数量: {len(result)} 张")
        assert isinstance(result, list), "返回值应该是列表"
        assert len(result) == 1, "普通模式应该生成1张图"
        print(f"   - 文件名: {result[0].filename}")
        assert "_v1.png" in result[0].filename, "文件名应包含版本号_v1"

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        raise


async def test_multi_image_generation():
    """测试深度思维模式（生成3张图）"""
    print("\n" + "=" * 80)
    print("测试2：深度思维模式 - 生成3张概念图（同一提示词）")
    print("=" * 80)

    generator = ImageGeneratorService()

    metadata = {
        "id": "test-deep-001",
        "name": "海洋风格卧室设计",
        "keywords": ["海洋", "蓝色", "自然"],
        "constraints": {"must_include": ["海洋元素", "柔和灯光"]},
        "owner_role": "室内设计师",
        "concept_image_config": {"count": 3, "editable": True},  # 深度思维模式
    }

    try:
        result = await generator.generate_deliverable_image(
            deliverable_metadata=metadata,
            expert_analysis="打造舒适的海洋风格卧室，强调放松和宁静的氛围",
            session_id="test-session-deep",
            project_type="interior",
        )

        print(f"\n✅ 测试通过！")
        print(f"   - 返回类型: {type(result)}")
        print(f"   - 生成数量: {len(result)} 张")
        assert isinstance(result, list), "返回值应该是列表"
        assert len(result) == 3, "深度思维模式应该生成3张图"

        # 验证文件名唯一性
        filenames = [img.filename for img in result]
        print(f"\n   生成的文件名:")
        for idx, filename in enumerate(filenames, 1):
            print(f"   [{idx}] {filename}")
            assert f"_v{idx}.png" in filename, f"文件名应包含版本号_v{idx}"

        # 验证所有文件名不同
        assert len(set(filenames)) == 3, "所有文件名应该唯一"

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        raise


async def test_backward_compatibility():
    """测试向后兼容性（缺失配置时默认生成1张）"""
    print("\n" + "=" * 80)
    print("测试3：向后兼容性 - 缺失配置时默认生成1张")
    print("=" * 80)

    generator = ImageGeneratorService()

    metadata = {
        "id": "test-compat-001",
        "name": "工业风办公室设计",
        "keywords": ["工业", "现代", "开放"],
        # 注意：没有 concept_image_config
    }

    try:
        result = await generator.generate_deliverable_image(
            deliverable_metadata=metadata,
            expert_analysis="设计开放式工业风办公空间",
            session_id="test-session-compat",
            project_type="interior",
        )

        print(f"\n✅ 测试通过！")
        print(f"   - 生成数量: {len(result)} 张")
        assert len(result) == 1, "缺失配置时应默认生成1张图"
        print(f"   - 文件名: {result[0].filename}")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        raise


async def main():
    """运行所有测试"""
    print("\n" + "=" * 80)
    print("🧪 v7.127 多图生成功能测试套件")
    print("=" * 80)

    try:
        # 运行所有测试
        await test_single_image_generation()
        await test_multi_image_generation()
        await test_backward_compatibility()

        print("\n" + "=" * 80)
        print("✅ 所有测试通过！")
        print("=" * 80)
        print("\n总结:")
        print("  - 普通模式（count=1）: ✅ 正常工作")
        print("  - 深度思维模式（count=3）: ✅ 正常工作")
        print("  - 向后兼容性: ✅ 正常工作")
        print("  - 文件名唯一性: ✅ 验证通过")

    except Exception as e:
        print("\n" + "=" * 80)
        print(f"❌ 测试失败: {e}")
        print("=" * 80)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
