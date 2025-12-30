"""
从数据库诊断问卷回答显示问题
"""

import sqlite3
import json
from loguru import logger
import sys
from pathlib import Path


def diagnose_questionnaire_from_db(session_id: str):
    """
    从SQLite数据库中诊断问卷状态

    Args:
        session_id: 会话ID（如 "api-20251206193134-3b6b8a7d"）
    """
    db_path = Path("data/archived_sessions.db")
    if not db_path.exists():
        logger.error(f"❌ 数据库文件不存在: {db_path}")
        return

    logger.info("=" * 80)
    logger.info("📊 问卷回答诊断报告")
    logger.info(f"会话ID: {session_id}")
    logger.info("=" * 80)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. 查询session表结构
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    logger.info(f"\n数据库表列表: {[t[0] for t in tables]}")

    # 2. 查询archived_sessions表的schema
    cursor.execute("PRAGMA table_info(archived_sessions)")
    columns = cursor.fetchall()
    logger.info(f"\narchived_sessions表列:")
    for col in columns:
        logger.info(f"  - {col[1]} ({col[2]})")

    # 3. 查询指定session_id的数据
    cursor.execute("""
        SELECT session_id, status, session_data, created_at, completed_at
        FROM archived_sessions
        WHERE session_id = ?
    """, (session_id,))

    row = cursor.fetchone()
    if not row:
        logger.error(f"❌ 未找到会话ID: {session_id}")
        conn.close()
        return

    session_id_db, status, session_data, created_at, completed_at = row
    logger.info(f"\n1️⃣ 会话基本信息:")
    logger.info(f"   - session_id: {session_id_db}")
    logger.info(f"   - status: {status}")
    logger.info(f"   - created_at: {created_at}")
    logger.info(f"   - completed_at: {completed_at}")

    # 4. 解析session_data
    if not session_data:
        logger.error("❌ session_data为空！")
        conn.close()
        return

    try:
        state_data = json.loads(session_data)
    except json.JSONDecodeError as e:
        logger.error(f"❌ 无法解析session_data: {e}")
        conn.close()
        return

    logger.info(f"\n2️⃣ state_snapshot顶层键:")
    logger.info(f"   {list(state_data.keys())}")

    # 5. 检查calibration_answers
    calibration_answers = state_data.get("calibration_answers", {})
    logger.info(f"\n3️⃣ calibration_answers字段:")
    logger.info(f"   - 是否存在: {bool(calibration_answers)}")
    logger.info(f"   - 回答数量: {len(calibration_answers)}")

    if calibration_answers:
        logger.info(f"   - 问题ID和回答:")
        for q_id, answer in calibration_answers.items():
            answer_str = str(answer)
            if len(answer_str) > 100:
                answer_preview = answer_str[:100] + "..."
            else:
                answer_preview = answer_str
            logger.info(f"      * {q_id}:")
            logger.info(f"        {answer_preview}")
    else:
        logger.warning("   ⚠️ calibration_answers为空！")

    # 6. 检查questionnaire_responses
    questionnaire_responses = state_data.get("questionnaire_responses", {})
    logger.info(f"\n4️⃣ questionnaire_responses字段:")
    logger.info(f"   - 是否存在: {bool(questionnaire_responses)}")

    if questionnaire_responses:
        entries = questionnaire_responses.get("entries", [])
        logger.info(f"   - entries数量: {len(entries)}")
        logger.info(f"   - 提交时间: {questionnaire_responses.get('submitted_at', 'N/A')}")

        if entries:
            logger.info(f"   - entries详情:")
            for i, entry in enumerate(entries, 1):
                q_id = entry.get("id", "unknown")
                question_text = entry.get("question", "")
                if len(question_text) > 60:
                    question_preview = question_text[:60] + "..."
                else:
                    question_preview = question_text

                value = entry.get("value")
                if isinstance(value, list):
                    value_preview = f"[列表{len(value)}项]"
                else:
                    value_str = str(value)
                    if len(value_str) > 100:
                        value_preview = value_str[:100] + "..."
                    else:
                        value_preview = value_str

                logger.info(f"      [{i}] {q_id}:")
                logger.info(f"          问题: {question_preview}")
                logger.info(f"          回答: {value_preview}")
    else:
        logger.warning("   ⚠️ questionnaire_responses为空！")

    # 7. 检查calibration_questionnaire（问卷定义）
    calibration_questionnaire = state_data.get("calibration_questionnaire", {})
    logger.info(f"\n5️⃣ calibration_questionnaire字段（问卷定义）:")
    logger.info(f"   - 是否存在: {bool(calibration_questionnaire)}")

    if calibration_questionnaire:
        questions = calibration_questionnaire.get("questions", [])
        logger.info(f"   - 问题总数: {len(questions)}")
        logger.info(f"   - 问题ID列表:")
        for i, q in enumerate(questions, 1):
            q_id = q.get("id", "unknown")
            q_type = q.get("type", "unknown")
            q_text = q.get("question", "")
            if len(q_text) > 60:
                q_preview = q_text[:60] + "..."
            else:
                q_preview = q_text
            logger.info(f"      [{i}] {q_id} ({q_type}): {q_preview}")
    else:
        logger.warning("   ⚠️ calibration_questionnaire为空！")

    # 8. 交叉验证
    logger.info(f"\n6️⃣ 交叉验证（问卷定义 vs 用户回答）:")

    if calibration_questionnaire and calibration_answers:
        questions = calibration_questionnaire.get("questions", [])
        question_ids_in_definition = {q.get("id") for q in questions if q.get("id")}
        question_ids_in_answers = set(calibration_answers.keys())

        logger.info(f"   - 问卷定义中的问题ID: {sorted(question_ids_in_definition)}")
        logger.info(f"   - 用户回答中的问题ID: {sorted(question_ids_in_answers)}")

        # 找出没有回答的问题
        missing_answers = question_ids_in_definition - question_ids_in_answers
        if missing_answers:
            logger.warning(f"\n   ⚠️ 以下{len(missing_answers)}个问题没有回答:")
            for q_id in missing_answers:
                q = next((q for q in questions if q.get("id") == q_id), None)
                if q:
                    q_text = q.get("question", "")[:60]
                    logger.warning(f"      * {q_id}: {q_text}...")
        else:
            logger.info(f"\n   ✅ 所有问题都有回答")

        # 找出多余的回答
        extra_answers = question_ids_in_answers - question_ids_in_definition
        if extra_answers:
            logger.warning(f"\n   ⚠️ 以下{len(extra_answers)}个回答的question_id在当前问卷定义中不存在:")
            for q_id in extra_answers:
                answer_preview = str(calibration_answers[q_id])[:60]
                logger.warning(f"      * {q_id}: {answer_preview}...")

        # 统计
        matched_count = len(question_ids_in_definition & question_ids_in_answers)
        logger.info(f"\n   📊 匹配统计:")
        logger.info(f"      - 问卷定义中的问题数: {len(question_ids_in_definition)}")
        logger.info(f"      - 用户回答的问题数: {len(question_ids_in_answers)}")
        logger.info(f"      - 匹配成功的问题数: {matched_count}")
        if question_ids_in_definition:
            match_rate = matched_count / len(question_ids_in_definition) * 100
            logger.info(f"      - 匹配率: {match_rate:.1f}%")

    # 9. 检查问卷处理标志
    logger.info(f"\n7️⃣ 问卷处理状态标志:")
    logger.info(f"   - calibration_processed: {state_data.get('calibration_processed', False)}")
    logger.info(f"   - calibration_skipped: {state_data.get('calibration_skipped', False)}")

    # 10. 修复建议
    logger.info(f"\n" + "=" * 80)
    logger.info("🔧 诊断结果和修复建议:")
    logger.info("=" * 80)

    issues = []

    if not calibration_answers:
        issues.append("calibration_answers为空")
        logger.error("❌ 问题1: calibration_answers为空")
        logger.info("   可能原因:")
        logger.info("   1. 用户没有提交问卷")
        logger.info("   2. 问卷提交时answers_map构建失败")
        logger.info("   修复方案:")
        logger.info("   - 检查 calibration_questionnaire.py 的 _build_answer_entries() 方法")
        logger.info("   - 查看后端日志中是否有 '📝 Integrating X questionnaire answers' 的记录")

    if calibration_questionnaire and calibration_answers:
        questions = calibration_questionnaire.get("questions", [])
        question_ids_in_definition = {q.get("id") for q in questions if q.get("id")}
        question_ids_in_answers = set(calibration_answers.keys())
        missing_answers = question_ids_in_definition - question_ids_in_answers

        if missing_answers:
            issues.append(f"{len(missing_answers)}个问题没有回答")
            logger.error(f"❌ 问题2: 有{len(missing_answers)}个问题没有回答")
            logger.info("   可能原因:")
            logger.info("   1. 前端提交的question_id与后端期望的不一致")
            logger.info("   2. _build_answer_entries()的potential_keys匹配失败")
            logger.info("   修复方案:")
            logger.info("   - 检查前端提交的数据格式")
            logger.info("   - 检查 potential_keys 列表是否包含前端使用的question_id格式")
            logger.info("   - 相关代码: calibration_questionnaire.py Line 772-776")

    if not issues:
        logger.info("✅ 未检测到明显问题")
        logger.info("   如果前端仍显示'未回答'，可能是前端映射逻辑问题")
        logger.info("   建议检查:")
        logger.info("   1. 前端从哪个字段读取问卷回答（calibration_answers or questionnaire_responses）")
        logger.info("   2. 前端使用的question_id是否与后端存储的一致")
        logger.info("   3. 检查浏览器控制台是否有错误日志")

    logger.info(f"\n" + "=" * 80)
    logger.info("✅ 诊断完成")
    logger.info("=" * 80)

    conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python diagnose_questionnaire_from_db.py <session_id>")
        print("示例: python diagnose_questionnaire_from_db.py api-20251206193134-3b6b8a7d")
        sys.exit(1)

    session_id = sys.argv[1]
    diagnose_questionnaire_from_db(session_id)
