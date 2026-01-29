#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
会话诊断脚本 - 用于排查需求洞察失败问题

用法:
    python scripts/diagnose_session_current.py <session_id>

示例:
    python scripts/diagnose_session_current.py 8pdwoxj8-20260107093754-fa96a808
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from intelligent_project_analyzer.services.redis_session_manager import RedisSessionManager


async def diagnose_session(session_id: str):
    """诊断会话状态"""
    print("=" * 80)
    print(f"诊断会话: {session_id}")
    print("=" * 80)

    # 连接 Redis
    session_manager = RedisSessionManager()
    await session_manager.connect()

    try:
        # 获取会话数据
        session_data = await session_manager.get(session_id)

        if not session_data:
            print(f"\n❌ 会话不存在: {session_id}")
            print(f"   请检查会话ID是否正确")
            return

        print(f"\n✅ 会话存在")

        # 基本信息
        status = session_data.get("status", "unknown")
        progress = session_data.get("progress", "unknown")
        current_node = session_data.get("current_node", "unknown")

        print(f"   - 状态: {status}")
        print(f"   - 进度: {progress}")
        print(f"   - 当前节点: {current_node}")

        # 检查前置数据
        print(f"\n📊 前置数据检查:")
        confirmed_tasks = session_data.get("confirmed_core_tasks", [])
        gap_filling = session_data.get("gap_filling_answers", {})
        selected_dims = session_data.get("selected_dimensions", [])
        radar_values = session_data.get("radar_dimension_values", {})

        tasks_ok = len(confirmed_tasks) > 0
        gap_ok = len(gap_filling) > 0
        dims_ok = len(selected_dims) > 0
        radar_ok = radar_values is not None and len(radar_values) > 0

        print(f"   - confirmed_core_tasks: {len(confirmed_tasks)} 个 {'✅' if tasks_ok else '❌'}")
        if confirmed_tasks:
            print(f"     示例: {confirmed_tasks[0].get('title', 'N/A')[:50]}...")

        print(f"   - gap_filling_answers: {len(gap_filling)} 个字段 {'✅' if gap_ok else '❌'}")
        if gap_filling:
            print(f"     字段: {list(gap_filling.keys())[:3]}")

        print(f"   - selected_dimensions: {len(selected_dims)} 个 {'✅' if dims_ok else '❌'}")
        if selected_dims:
            # 检查维度格式
            first_dim = selected_dims[0]
            if isinstance(first_dim, dict):
                print(f"     格式: dict (id={first_dim.get('id', 'N/A')})")
            elif isinstance(first_dim, str):
                print(f"     格式: str ({first_dim})")
            else:
                print(f"     格式: {type(first_dim)} ⚠️")

        print(f"   - radar_dimension_values: {len(radar_values) if radar_values else 0} 个 {'✅' if radar_ok else '❌'}")
        if radar_values:
            print(f"     示例: {list(radar_values.keys())[:3]}")

        # 检查输出数据
        print(f"\n📝 输出数据检查:")
        restructured = session_data.get("restructured_requirements")
        summary_text = session_data.get("requirements_summary_text")

        print(f"   - restructured_requirements: {'✅ 存在' if restructured else '❌ 缺失'}")
        if restructured:
            metadata = restructured.get("metadata", {})
            gen_method = metadata.get("generation_method", "unknown")
            priorities = restructured.get("design_priorities", [])

            print(f"     - 生成方法: {gen_method}")
            if gen_method == "fallback_restructure":
                print(f"       ⚠️ 使用了降级逻辑！主流程可能失败")

            print(f"     - 设计重点: {len(priorities)} 个维度")
            if priorities:
                print(f"       示例: {priorities[0].get('label', 'N/A')}")

        print(f"   - requirements_summary_text: {'✅ 存在' if summary_text else '❌ 缺失'}")
        if summary_text:
            print(f"     长度: {len(summary_text)} 字符")

        # 检查问卷流程状态
        print(f"\n🔍 问卷流程状态:")
        step = session_data.get("progressive_questionnaire_step", 0)
        completed = session_data.get("progressive_questionnaire_completed", False)
        summary_completed = session_data.get("questionnaire_summary_completed", False)

        print(f"   - 当前步骤: Step {step}")
        print(f"   - 问卷完成: {'✅' if completed else '❌'}")
        print(f"   - 汇总完成: {'✅' if summary_completed else '❌'}")

        # 检查是否有错误
        error = session_data.get("error")
        if error:
            print(f"\n❌ 错误信息:")
            print(f"   {error}")
        else:
            print(f"\n✅ 无错误信息记录")

        # 诊断结论
        print(f"\n" + "=" * 80)
        print(f"诊断结论:")
        print(f"=" * 80)

        if not tasks_ok or not gap_ok or not dims_ok or not radar_ok:
            print(f"❌ 前置数据不完整")
            print(f"   可能原因: 前面步骤的数据未正确保存")
            print(f"   建议: 检查 progressive_questionnaire.py 的数据保存逻辑")
        elif not restructured:
            print(f"❌ 未生成需求文档")
            print(f"   可能原因: questionnaire_summary 节点未执行或执行失败")
            print(f"   建议: 检查日志中是否有异常")
        elif restructured and restructured.get("metadata", {}).get("generation_method") == "fallback_restructure":
            print(f"⚠️ 使用了降级逻辑")
            print(f"   可能原因: 主流程抛出异常，被 try-except 捕获")
            print(f"   建议: 启用 DEBUG 日志，重新运行捕获异常堆栈")
        elif status == "interrupted":
            print(f"⚠️ 会话卡在 interrupt 状态")
            print(f"   可能原因: 前端未正确处理 interrupt 响应")
            print(f"   建议: 检查前端 Step 4 的 interrupt 处理逻辑")
        else:
            print(f"✅ 数据看起来正常")
            print(f"   如果仍有问题，建议启用 DEBUG 日志重新运行")

        # 保存完整数据到文件
        output_file = Path(__file__).parent.parent / f"session_{session_id}_diagnosis.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)
        print(f"\n💾 完整会话数据已保存到: {output_file}")

    except Exception as e:
        print(f"\n❌ 诊断过程出错: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await session_manager.disconnect()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python diagnose_session_current.py <session_id>")
        print("示例: python diagnose_session_current.py 8pdwoxj8-20260107093754-fa96a808")
        sys.exit(1)

    session_id = sys.argv[1]
    asyncio.run(diagnose_session(session_id))
