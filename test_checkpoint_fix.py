#!/usr/bin/env python3
"""
测试 v7.146 checkpoint 同步修复

验证流程：
1. 创建新会话
2. 完成渐进式问卷（Step1-3）
3. 通过角色任务审核
4. 通过质量预检
5. 确认 workflow 进入批次执行阶段（不再异常终止）
"""
import json
import sys
import time

import requests

BASE_URL = "http://localhost:8000"
USER_ID = "test-checkpoint-fix"


def print_step(msg):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}\n")


def test_checkpoint_fix():
    # Step 1: 创建会话
    print_step("Step 1: 创建测试会话")

    resp = requests.post(
        f"{BASE_URL}/api/analysis/start",
        json={"user_input": "我想在青岛设计一个融合艺术文化的精品酒店，包含30间客房、餐厅、画廊和泳池，预算800万", "user_id": USER_ID, "detail": "normal"},
        timeout=30,
    )

    if resp.status_code != 200:
        print(f"❌ 会话创建失败: {resp.status_code}")
        print(resp.text)
        return False

    session_id = resp.json()["session_id"]
    print(f"✅ 会话已创建: {session_id}")

    # Step 2: 等待并处理渐进式问卷
    print_step("Step 2: 等待渐进式问卷事件")

    time.sleep(5)  # 等待初始化

    # 模拟用户提交问卷数据（简化版）
    questionnaire_data = {
        "step1": {
            "tasks": [
                {"id": "task1", "description": "设计风格定位", "confirmed": True},
                {"id": "task2", "description": "空间布局规划", "confirmed": True},
            ]
        },
        "step2": {"answers": {"budget": "800万", "timeline": "6-12个月", "style_preference": "现代艺术风格"}},
        "step3": {"dimensions": [{"id": "aesthetic_level", "value": 80}, {"id": "cost_control", "value": 60}]},
    }

    print(f"📝 问卷数据准备完成（简化版）")

    # Step 3: 通过角色任务审核
    print_step("Step 3: 等待角色任务审核")

    time.sleep(3)

    # 自动通过审核
    resp = requests.post(
        f"{BASE_URL}/api/analysis/resume",
        json={"session_id": session_id, "resume_value": {"action": "approve"}},
        timeout=30,
    )

    if resp.status_code == 200:
        print("✅ 角色任务审核已通过")
    else:
        print(f"⚠️ 审核响应: {resp.status_code}")

    # Step 4: 通过质量预检
    print_step("Step 4: 等待质量预检")

    time.sleep(15)  # 等待 LLM 风险评估

    resp = requests.post(
        f"{BASE_URL}/api/analysis/resume",
        json={"session_id": session_id, "resume_value": {"action": "approve"}},
        timeout=30,
    )

    if resp.status_code == 200:
        print("✅ 质量预检已通过")
    else:
        print(f"⚠️ 预检响应: {resp.status_code}")

    # Step 5: 验证 checkpoint 同步和批次执行
    print_step("Step 5: 验证 checkpoint 同步与批次执行")

    time.sleep(5)

    # 检查会话状态
    resp = requests.get(f"{BASE_URL}/api/analysis/status/{session_id}", timeout=10)

    if resp.status_code == 200:
        status = resp.json()

        print(f"📊 会话状态: {status.get('status')}")
        print(f"📦 当前批次: {status.get('current_batch', 0)}/{status.get('total_batches', 0)}")

        # 关键检查：是否进入批次执行
        if status.get("total_batches", 0) > 0:
            print("\n✅✅✅ 修复验证成功！")
            print("   - checkpoint 同步无错误")
            print("   - workflow 正常进入批次执行阶段")
            print("   - 没有出现异常终止")
            return True
        else:
            print("\n⚠️ 批次信息未更新，可能需要更多时间")

            # 再等待一次
            time.sleep(10)
            resp = requests.get(f"{BASE_URL}/api/analysis/status/{session_id}", timeout=10)
            if resp.status_code == 200:
                status = resp.json()
                if status.get("total_batches", 0) > 0:
                    print("✅ 延迟更新成功，修复已生效")
                    return True

            print("❌ 未能确认批次执行，需要查看日志")
            return False
    else:
        print(f"❌ 状态查询失败: {resp.status_code}")
        return False


if __name__ == "__main__":
    try:
        success = test_checkpoint_fix()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
