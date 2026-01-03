"""
测试 v7.106 LLM智能维度生成功能

测试场景：
1. 儿童主题餐厅（应生成：儿童安全性、教育元素、趣味性）
2. 禅意茶室（应生成：禅意氛围、极简程度）
3. 科技展厅（应生成：科技感、互动性、数字化）
"""

import json
import time

import requests

API_BASE = "http://localhost:8000"


def run_dimension_generation_test(test_name: str, user_input: str):
    """测试维度生成"""
    print(f"\n{'='*80}")
    print(f"🧪 测试场景: {test_name}")
    print(f"{'='*80}")
    print(f"📝 用户输入:\n{user_input}\n")

    # 1. 创建会话
    print("1️⃣ 创建会话...")
    response = requests.post(
        f"{API_BASE}/api/v1/sessions", json={"user_input": user_input, "user_id": "test_user_v7106"}
    )

    if response.status_code != 200:
        print(f"❌ 创建会话失败: {response.text}")
        return

    session_id = response.json()["session_id"]
    print(f"✅ 会话创建成功: {session_id}\n")

    # 2. 等待Step 1完成（任务梳理）
    print("2️⃣ 等待Step 1（任务梳理）...")
    time.sleep(2)

    # 检查会话状态
    response = requests.get(f"{API_BASE}/api/v1/sessions/{session_id}")
    session_data = response.json()

    if session_data.get("status") == "waiting_for_input":
        interaction_data = session_data.get("current_interaction", {})
        if interaction_data.get("interaction_type") == "progressive_questionnaire_step1":
            print("✅ Step 1已触发，确认核心任务...\n")

            # 确认任务（使用默认提取的任务）
            response = requests.post(f"{API_BASE}/api/v1/sessions/{session_id}/response", json={"action": "confirm"})

            if response.status_code == 200:
                print("✅ 核心任务已确认\n")
            else:
                print(f"❌ 确认失败: {response.text}")
                return

    # 3. 等待Step 2（雷达图维度）
    print("3️⃣ 等待Step 2（雷达图维度生成）...")
    time.sleep(5)  # LLM生成需要时间

    # 检查雷达图维度
    response = requests.get(f"{API_BASE}/api/v1/sessions/{session_id}")
    session_data = response.json()

    if session_data.get("status") == "waiting_for_input":
        interaction_data = session_data.get("current_interaction", {})
        if interaction_data.get("interaction_type") == "progressive_questionnaire_step2":
            dimensions = interaction_data.get("dimensions", [])
            print(f"✅ Step 2已触发，生成了 {len(dimensions)} 个维度\n")

            print("📊 维度列表:")
            print("-" * 80)
            for i, dim in enumerate(dimensions, 1):
                dim_id = dim.get("id", "unknown")
                name = dim.get("name", "未命名")
                left = dim.get("left_label", "")
                right = dim.get("right_label", "")

                # 标记动态生成的维度
                is_dynamic = dim_id.startswith("dimension_") and not dim_id.startswith("dimension_modern")
                marker = "🆕" if is_dynamic else "📌"

                print(f"{marker} {i}. {name} ({dim_id})")
                print(f"   {left} ← → {right}")

            print("-" * 80)

            # 统计动态生成的维度
            dynamic_dims = [
                d
                for d in dimensions
                if d.get("id", "").startswith("dimension_") and not d.get("id", "").startswith("dimension_modern")
            ]

            print(f"\n🎯 动态生成维度数量: {len(dynamic_dims)}/{len(dimensions)}")

            if dynamic_dims:
                print("\n🆕 动态生成的维度:")
                for dim in dynamic_dims:
                    print(f"   • {dim.get('name')}: {dim.get('left_label')} ← → {dim.get('right_label')}")
            else:
                print("\n⚠️ 未检测到动态生成的维度（可能覆盖度评分 >= 85）")

            return session_id, dimensions

    print("❌ 未能到达Step 2")
    return None, []


def main():
    """运行所有测试"""
    print(f"\n🚀 开始测试 v7.106 LLM智能维度生成功能")
    print(f"📅 测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    test_cases = [
        ("儿童主题餐厅", "我需要设计一个儿童主题餐厅，面积200平米，注重安全性和趣味性，希望融入教育元素。"),
        ("禅意茶室", "设计一个禅意茶室，80平米，追求极简和静谧的氛围，适合冥想和品茶。"),
        ("科技展厅", "设计一个科技展厅，500平米，需要强烈的科技感、互动性，以及数字化体验。"),
    ]

    results = []

    for test_name, user_input in test_cases:
        session_id, dimensions = test_dimension_generation(test_name, user_input)
        results.append(
            {
                "test_name": test_name,
                "session_id": session_id,
                "dimensions_count": len(dimensions),
                "dynamic_dims": len(
                    [
                        d
                        for d in dimensions
                        if d.get("id", "").startswith("dimension_")
                        and not d.get("id", "").startswith("dimension_modern")
                    ]
                ),
            }
        )

        print("\n⏸️ 等待10秒后继续下一个测试...")
        time.sleep(10)

    # 汇总结果
    print(f"\n{'='*80}")
    print("📊 测试结果汇总")
    print(f"{'='*80}")

    for result in results:
        print(f"\n🧪 {result['test_name']}")
        print(f"   会话ID: {result['session_id']}")
        print(f"   总维度: {result['dimensions_count']}")
        print(f"   动态生成: {result['dynamic_dims']}")

        if result["dynamic_dims"] > 0:
            print(f"   状态: ✅ LLM生成成功")
        elif result["dimensions_count"] > 0:
            print(f"   状态: ⚠️ 仅使用基础维度（覆盖度可能 >= 85）")
        else:
            print(f"   状态: ❌ 测试失败")

    print(f"\n{'='*80}")
    print("✅ 测试完成！")
    print("\n💡 提示：")
    print("   - 查看后端日志确认LLM调用详情")
    print("   - 日志关键词: '智能生成', '覆盖度分析', '新增定制维度'")
    print("   - 使用命令: Get-Content logs\\server.log -Wait -Tail 100 -Encoding UTF8")


if __name__ == "__main__":
    main()
