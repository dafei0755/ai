"""
概念图全流程测试脚本
专项测试概念图生成的完整过程，并监控可能的bug
"""

import json
import sys
import time
import uuid
from datetime import datetime

import requests

# API配置
BASE_URL = "http://localhost:8000"
SESSION_ID = f"test_concept_{uuid.uuid4().hex[:8]}"
DEVICE_ID = f"device_{uuid.uuid4().hex[:8]}"

# 测试问题
TEST_QUESTION = """
一位在北京长大的美国人，买下了一座小型四合院。他希望保留传统建筑的"气"，但内部要实现纽约Loft的开放、极简和派对功能。
"""


def log_step(message, level="INFO"):
    """记录测试步骤"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")


def log_error(message, error=None):
    """记录错误"""
    log_step(message, "ERROR")
    if error:
        print(f"  详细错误: {error}")


def log_success(message):
    """记录成功"""
    log_step(message, "SUCCESS")


def test_initial_submission():
    """步骤1: 提交初始问题"""
    log_step("步骤1: 提交测试问题")

    url = f"{BASE_URL}/api/analysis/start"
    payload = {"user_input": TEST_QUESTION.strip(), "session_id": SESSION_ID, "device_id": DEVICE_ID}

    try:
        response = requests.post(url, json=payload, timeout=30)
        log_step(f"响应状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            log_success("问题提交成功")
            log_step(f"流程状态: {data.get('status', 'unknown')}")
            return data
        else:
            log_error(f"提交失败: {response.text}")
            return None
    except Exception as e:
        log_error("提交问题时发生异常", e)
        return None


def monitor_session():
    """步骤2-6: 监控会话状态，直到完成或出错"""
    log_step("开始监控会话状态...")

    max_iterations = 100  # 最多监控100次
    iteration = 0

    while iteration < max_iterations:
        iteration += 1
        time.sleep(3)  # 每3秒检查一次

        try:
            # 获取会话状态
            url = f"{BASE_URL}/api/analysis/status/{SESSION_ID}"
            response = requests.get(url, timeout=10)

            if response.status_code != 200:
                log_error(f"获取会话状态失败: {response.status_code}")
                continue

            data = response.json()
            status = data.get("status", "unknown")

            log_step(f"[{iteration}] 当前状态: {status}")

            # 检查是否有中断（需要用户输入）
            if status == "waiting":
                interrupt_type = data.get("interrupt_type")
                log_step(f"  等待中断: {interrupt_type}")

                if interrupt_type == "progressive_questionnaire":
                    # 自动回答问卷
                    handle_questionnaire(data)
                elif interrupt_type == "role_and_task_unified_review":
                    # 自动审批任务
                    handle_task_review(data)
                else:
                    log_step(f"  未知的中断类型: {interrupt_type}")

            # 检查是否完成
            elif status == "completed":
                log_success("分析流程已完成！")
                check_concept_images(data)
                return data

            # 检查是否出错
            elif status == "failed" or status == "error":
                log_error(f"流程失败: {data.get('error', '未知错误')}")
                return data

        except Exception as e:
            log_error(f"监控过程中发生异常", e)

    log_error("达到最大监控次数，测试超时")
    return None


def handle_questionnaire(data):
    """处理问卷中断"""
    log_step("处理渐进式问卷...")

    # 简单的自动回答策略：选择中等选项
    url = f"{BASE_URL}/api/analysis/resume"
    payload = {
        "session_id": SESSION_ID,
        "device_id": DEVICE_ID,
        "user_response": {"action": "continue", "answers": {}},  # 可以为空，使用默认值
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            log_success("问卷已提交")
        else:
            log_error(f"提交问卷失败: {response.text}")
    except Exception as e:
        log_error("提交问卷时发生异常", e)


def handle_task_review(data):
    """处理任务审批中断"""
    log_step("处理任务审批...")

    # 检查是否有概念图配置
    interrupt_data = data.get("interrupt_data", {})
    concept_settings = interrupt_data.get("concept_image_settings", {})

    if concept_settings:
        log_step(f"  发现概念图配置: {len(concept_settings)} 个角色")
        for role_id, config in concept_settings.items():
            deliverables = config.get("deliverables", [])
            enabled_count = sum(1 for d in deliverables if d.get("enable_concept_image"))
            log_step(f"    角色 {role_id}: {enabled_count}/{len(deliverables)} 个交付物启用概念图")

    # 自动批准并继续
    url = f"{BASE_URL}/api/analysis/resume"
    payload = {"session_id": SESSION_ID, "device_id": DEVICE_ID, "user_response": {"action": "approve"}}

    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            log_success("任务已批准")
        else:
            log_error(f"批准任务失败: {response.text}")
    except Exception as e:
        log_error("批准任务时发生异常", e)


def check_concept_images(final_data):
    """步骤7: 检查概念图生成结果"""
    log_step("=" * 60)
    log_step("检查概念图生成结果")
    log_step("=" * 60)

    results = final_data.get("results", {})

    # 检查最终结果中的图片
    total_images = 0
    successful_images = 0
    failed_images = 0

    for role_id, role_data in results.items():
        deliverables = role_data.get("deliverables", [])
        for deliverable in deliverables:
            if "concept_image" in deliverable:
                total_images += 1
                image_url = deliverable.get("concept_image", {}).get("url")
                status = deliverable.get("concept_image", {}).get("status", "unknown")

                log_step(f"  交付物: {deliverable.get('name', 'unknown')}")
                log_step(f"    概念图状态: {status}")

                if status == "completed" and image_url:
                    log_step(f"    图片URL: {image_url}")
                    successful_images += 1
                else:
                    log_error(f"    概念图生成失败")
                    failed_images += 1

    # 总结
    log_step("=" * 60)
    log_step(f"概念图生成总结:")
    log_step(f"  总数: {total_images}")
    log_step(f"  成功: {successful_images}")
    log_step(f"  失败: {failed_images}")
    log_step("=" * 60)

    if failed_images > 0:
        log_error(f"发现 {failed_images} 个概念图生成失败")
        return False
    else:
        log_success("所有概念图都成功生成！")
        return True


def main():
    """主测试流程"""
    log_step("=" * 60)
    log_step("概念图全流程测试开始")
    log_step(f"会话ID: {SESSION_ID}")
    log_step(f"设备ID: {DEVICE_ID}")
    log_step("=" * 60)

    # 步骤1: 提交问题
    result = test_initial_submission()
    if not result:
        log_error("初始提交失败，测试终止")
        return False

    # 步骤2-6: 监控流程
    final_result = monitor_session()
    if not final_result:
        log_error("监控流程失败，测试终止")
        return False

    log_step("=" * 60)
    log_step("测试完成")
    log_step("=" * 60)
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
