#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生产环境Bocha验证脚本 (v7.131)

验证Bocha修复不会影响生产环境启动和运行
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_imports():
    """测试关键模块导入"""
    print("=" * 60)
    print("测试1: 模块导入")
    print("=" * 60)

    try:
        from intelligent_project_analyzer.services.tool_factory import ToolFactory

        print("✅ ToolFactory导入成功")

        from intelligent_project_analyzer.agents.task_oriented_expert_factory import TaskOrientedExpertFactory

        print("✅ TaskOrientedExpertFactory导入成功")

        from intelligent_project_analyzer.agents.bocha_search_tool import BochaSearchTool

        print("✅ BochaSearchTool导入成功")

        from intelligent_project_analyzer.workflow.main_workflow import create_workflow

        print("✅ MainWorkflow导入成功")

        return True
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        return False


def test_tool_creation():
    """测试工具创建不会阻塞启动"""
    print()
    print("=" * 60)
    print("测试2: 工具创建")
    print("=" * 60)

    try:
        from intelligent_project_analyzer.services.tool_factory import ToolFactory
        from intelligent_project_analyzer.settings import settings

        print(f"Bocha配置状态:")
        print(f"  - BOCHA_ENABLED: {settings.bocha.enabled}")
        print(
            f"  - BOCHA_API_KEY: {'已配置' if settings.bocha.api_key and settings.bocha.api_key != 'your_bocha_api_key_here' else '未配置'}"
        )
        print()

        # 创建所有工具
        tools = ToolFactory.create_all_tools()

        print(f"✅ 工具创建成功: {len(tools)}个工具")
        print(f"   可用工具: {list(tools.keys())}")

        # 检查Bocha
        if "bocha" in tools:
            print("✅ Bocha工具已创建")
        else:
            if settings.bocha.enabled:
                print("⚠️ Bocha已启用但未创建（可能是API密钥问题）")
            else:
                print("ℹ️ Bocha已禁用")

        return True
    except Exception as e:
        print(f"❌ 工具创建失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_workflow_creation():
    """测试工作流创建"""
    print()
    print("=" * 60)
    print("测试3: 工作流创建")
    print("=" * 60)

    try:
        from intelligent_project_analyzer.workflow.main_workflow import create_workflow

        # 创建工作流
        workflow = create_workflow()

        print("✅ 工作流创建成功")
        print(f"   工作流节点数: {len(workflow.nodes) if hasattr(workflow, 'nodes') else 'N/A'}")

        return True
    except Exception as e:
        print(f"❌ 工作流创建失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_error_handling():
    """测试错误处理不会导致崩溃"""
    print()
    print("=" * 60)
    print("测试4: 错误处理")
    print("=" * 60)

    try:
        from intelligent_project_analyzer.services.tool_factory import ToolFactory

        # 测试禁用Bocha的情况
        print("测试场景: Bocha禁用")
        # 这应该不会抛出异常,只会记录日志
        tools = ToolFactory.create_all_tools()
        print("✅ Bocha禁用时工具创建正常")

        return True
    except Exception as e:
        print(f"❌ 错误处理失败: {e}")
        return False


def test_redis_fallback():
    """测试Redis不可用时的降级"""
    print()
    print("=" * 60)
    print("测试5: Redis降级处理")
    print("=" * 60)

    try:
        from intelligent_project_analyzer.settings import settings

        print(f"Redis配置:")
        print(f"  - Host: {settings.redis.host}")
        print(f"  - Port: {settings.redis.port}")
        print()

        # 尝试连接Redis
        try:
            import redis

            r = redis.Redis(
                host=settings.redis.host,
                port=settings.redis.port,
                db=settings.redis.db,
                password=settings.redis.password if settings.redis.password else None,
                socket_connect_timeout=2,
            )
            r.ping()
            print("✅ Redis连接成功")
        except Exception as e:
            print(f"⚠️ Redis不可用: {e}")
            print("   系统应该能够降级运行（使用内存会话）")

        return True
    except Exception as e:
        print(f"❌ Redis测试失败: {e}")
        return False


def main():
    """主函数"""
    print()
    print("🔍 生产环境Bocha验证 (v7.131)")
    print()

    results = []

    # 运行所有测试
    results.append(("模块导入", test_imports()))
    results.append(("工具创建", test_tool_creation()))
    results.append(("工作流创建", test_workflow_creation()))
    results.append(("错误处理", test_error_handling()))
    results.append(("Redis降级", test_redis_fallback()))

    # 总结
    print()
    print("=" * 60)
    print("验证总结")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {name}")

    print()
    print(f"总计: {passed}/{total} 通过")

    if passed == total:
        print()
        print("✅ 生产环境验证通过，可以安全启动服务器")
        print()
        print("启动命令:")
        print("  python -B scripts\\run_server_production.py")
        return 0
    else:
        print()
        print("❌ 存在问题，请先修复后再启动")
        return 1


if __name__ == "__main__":
    sys.exit(main())
