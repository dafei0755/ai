"""
诊断问卷回答显示问题

检查calibration_answers的存储情况和question_id映射
"""

import json
from pathlib import Path
from loguru import logger


def diagnose_questionnaire_state(state_data: dict):
    """
    诊断问卷状态数据

    Args:
        state_data: 工作流状态数据
    """
    logger.info("=" * 80)
    logger.info("📊 问卷回答诊断报告")
    logger.info("=" * 80)

    # 1. 检查calibration_answers字段
    calibration_answers = state_data.get("calibration_answers", {})
    logger.info(f"\n1️⃣ calibration_answers字段:")
    logger.info(f"   - 是否存在: {bool(calibration_answers)}")
    logger.info(f"   - 回答数量: {len(calibration_answers)}")

    if calibration_answers:
        logger.info(f"   - 问题ID列表:")
        for q_id, answer in calibration_answers.items():
            answer_preview = str(answer)[:50] + "..." if len(str(answer)) > 50 else str(answer)
            logger.info(f"      * {q_id}: {answer_preview}")
    else:
        logger.warning("   ⚠️ calibration_answers为空！")

    # 2. 检查questionnaire_responses字段
    questionnaire_responses = state_data.get("questionnaire_responses", {})
    logger.info(f"\n2️⃣ questionnaire_responses字段:")
    logger.info(f"   - 是否存在: {bool(questionnaire_responses)}")

    if questionnaire_responses:
        entries = questionnaire_responses.get("entries", [])
        logger.info(f"   - entries数量: {len(entries)}")
        logger.info(f"   - 提交时间: {questionnaire_responses.get('submitted_at', 'N/A')}")
        logger.info(f"   - 补充说明: {questionnaire_responses.get('notes', 'N/A')}")

        if entries:
            logger.info(f"   - entries详情:")
            for entry in entries:
                q_id = entry.get("id", "unknown")
                question = entry.get("question", "")[:50]
                value = entry.get("value")
                value_preview = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
                logger.info(f"      * {q_id}: {question}...")
                logger.info(f"        回答: {value_preview}")
    else:
        logger.warning("   ⚠️ questionnaire_responses为空！")

    # 3. 检查calibration_questionnaire字段（问卷定义）
    calibration_questionnaire = state_data.get("calibration_questionnaire", {})
    logger.info(f"\n3️⃣ calibration_questionnaire字段（问卷定义）:")
    logger.info(f"   - 是否存在: {bool(calibration_questionnaire)}")

    if calibration_questionnaire:
        questions = calibration_questionnaire.get("questions", [])
        logger.info(f"   - 问题总数: {len(questions)}")
        logger.info(f"   - 问题ID列表:")
        for q in questions:
            q_id = q.get("id", "unknown")
            q_type = q.get("type", "unknown")
            q_text = q.get("question", "")[:50]
            logger.info(f"      * {q_id} ({q_type}): {q_text}...")
    else:
        logger.warning("   ⚠️ calibration_questionnaire为空！")

    # 4. 交叉验证：检查问卷定义的question_id是否都有答案
    logger.info(f"\n4️⃣ 交叉验证（问卷定义 vs 用户回答）:")

    if calibration_questionnaire and calibration_answers:
        questions = calibration_questionnaire.get("questions", [])
        question_ids_in_definition = {q.get("id") for q in questions if q.get("id")}
        question_ids_in_answers = set(calibration_answers.keys())

        # 找出定义中有但回答中没有的question_id
        missing_answers = question_ids_in_definition - question_ids_in_answers
        if missing_answers:
            logger.warning(f"   ⚠️ 以下问题没有回答:")
            for q_id in missing_answers:
                q = next((q for q in questions if q.get("id") == q_id), None)
                if q:
                    logger.warning(f"      * {q_id}: {q.get('question', '')[:50]}...")
        else:
            logger.info(f"   ✅ 所有问题都有回答")

        # 找出回答中有但定义中没有的question_id（可能是旧问卷）
        extra_answers = question_ids_in_answers - question_ids_in_definition
        if extra_answers:
            logger.warning(f"   ⚠️ 以下回答的question_id在当前问卷定义中不存在:")
            for q_id in extra_answers:
                logger.warning(f"      * {q_id}: {calibration_answers.get(q_id, '')[:50]}...")

        # 匹配情况统计
        matched_count = len(question_ids_in_definition & question_ids_in_answers)
        logger.info(f"\n   📊 匹配统计:")
        logger.info(f"      - 问卷定义中的问题数: {len(question_ids_in_definition)}")
        logger.info(f"      - 用户回答的问题数: {len(question_ids_in_answers)}")
        logger.info(f"      - 匹配成功的问题数: {matched_count}")
        logger.info(f"      - 匹配率: {matched_count / len(question_ids_in_definition) * 100:.1f}%")

    # 5. 检查calibration_processed标志
    logger.info(f"\n5️⃣ 问卷处理状态标志:")
    logger.info(f"   - calibration_processed: {state_data.get('calibration_processed', False)}")
    logger.info(f"   - calibration_skipped: {state_data.get('calibration_skipped', False)}")
    logger.info(f"   - calibration_skip_reason: {state_data.get('calibration_skip_reason', 'N/A')}")

    # 6. 生成修复建议
    logger.info(f"\n" + "=" * 80)
    logger.info("🔧 修复建议:")
    logger.info("=" * 80)

    if not calibration_answers:
        logger.error("❌ 问题1: calibration_answers为空")
        logger.info("   修复方案: 检查问卷提交时的数据处理逻辑")
        logger.info("   检查文件: intelligent_project_analyzer/interaction/nodes/calibration_questionnaire.py")
        logger.info("   检查方法: execute() 中的 answers_map 构建逻辑（约Line 1139）")

    if calibration_questionnaire and calibration_answers:
        questions = calibration_questionnaire.get("questions", [])
        question_ids_in_definition = {q.get("id") for q in questions if q.get("id")}
        question_ids_in_answers = set(calibration_answers.keys())
        missing_answers = question_ids_in_definition - question_ids_in_answers

        if missing_answers:
            logger.error(f"❌ 问题2: 有{len(missing_answers)}个问题没有回答")
            logger.info("   可能原因:")
            logger.info("   1. 用户提交时question_id不匹配")
            logger.info("   2. _build_answer_entries()方法的potential_keys匹配失败")
            logger.info("   修复方案: 检查potential_keys列表（约Line 772-776）")

    logger.info(f"\n" + "=" * 80)
    logger.info("✅ 诊断完成")
    logger.info("=" * 80)


def load_state_from_checkpoints(session_id: str) -> dict:
    """
    从checkpoints目录加载状态数据

    Args:
        session_id: 会话ID（如 "api-20251206193134-3b6b8a7d"）

    Returns:
        状态数据字典
    """
    # 尝试从checkpoints目录加载
    checkpoints_dir = Path("checkpoints")
    if not checkpoints_dir.exists():
        logger.error(f"❌ checkpoints目录不存在: {checkpoints_dir}")
        return {}

    # 查找会话ID对应的checkpoint文件
    session_files = list(checkpoints_dir.glob(f"*{session_id}*"))
    if not session_files:
        logger.error(f"❌ 未找到会话ID {session_id} 的checkpoint文件")
        return {}

    # 使用最新的checkpoint文件
    latest_file = max(session_files, key=lambda p: p.stat().st_mtime)
    logger.info(f"📂 加载checkpoint文件: {latest_file}")

    with open(latest_file, 'r', encoding='utf-8') as f:
        checkpoint_data = json.load(f)

    # 提取state数据
    if "channel_values" in checkpoint_data:
        return checkpoint_data["channel_values"]
    elif "state" in checkpoint_data:
        return checkpoint_data["state"]
    else:
        logger.warning("⚠️ checkpoint文件格式未知，返回完整数据")
        return checkpoint_data


# 示例用法
if __name__ == "__main__":
    import sys

    # 从命令行参数获取session_id或checkpoint文件路径
    if len(sys.argv) < 2:
        print("用法: python diagnose_questionnaire_answers.py <session_id>")
        print("示例: python diagnose_questionnaire_answers.py api-20251206193134-3b6b8a7d")
        sys.exit(1)

    session_id = sys.argv[1]

    # 加载状态数据
    state_data = load_state_from_checkpoints(session_id)

    if not state_data:
        logger.error("❌ 无法加载状态数据")
        sys.exit(1)

    # 执行诊断
    diagnose_questionnaire_state(state_data)
