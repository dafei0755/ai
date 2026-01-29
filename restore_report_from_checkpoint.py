#!/usr/bin/env python
"""从 LangGraph checkpoint 恢复报告数据到 Redis 会话"""
import asyncio
import json
import sqlite3
import sys

import msgpack


def convert_bytes_to_str(obj):
    """递归转换 bytes 为 str，处理所有嵌套结构"""
    if obj is None:
        return None
    if isinstance(obj, bytes):
        try:
            return obj.decode("utf-8")
        except:
            return obj.decode("utf-8", errors="replace")
    elif isinstance(obj, dict):
        return {convert_bytes_to_str(k): convert_bytes_to_str(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_bytes_to_str(item) for item in obj]
    elif isinstance(obj, (int, float, bool, str)):
        return obj
    else:
        # 对于其他类型，尝试转为字符串
        return str(obj)


async def restore_report(session_id: str):
    from intelligent_project_analyzer.services.redis_session_manager import RedisSessionManager

    # 1. 从 checkpoint 读取数据
    conn = sqlite3.connect("data/checkpoints/workflow.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT checkpoint
        FROM checkpoints
        WHERE thread_id = ?
        ORDER BY checkpoint_id DESC
        LIMIT 1
    """,
        (session_id,),
    )

    row = cursor.fetchone()
    if not row:
        print(f"❌ 未找到会话 {session_id} 的 checkpoint")
        conn.close()
        return

    # 解析 checkpoint 数据
    checkpoint_data = msgpack.unpackb(row[0], raw=False)
    cv = checkpoint_data.get("channel_values", {})

    # 转换 bytes 为 str
    final_report = convert_bytes_to_str(cv.get("final_report"))
    agent_results = convert_bytes_to_str(cv.get("agent_results"))
    structured_requirements = convert_bytes_to_str(cv.get("structured_requirements"))
    strategic_analysis = convert_bytes_to_str(cv.get("strategic_analysis"))
    review_result = convert_bytes_to_str(cv.get("review_result"))

    print(f"✅ 从 checkpoint 读取数据:")
    print(f"  final_report: {type(final_report).__name__} ({len(final_report) if final_report else 0} keys)")
    print(f"  agent_results: {type(agent_results).__name__} ({len(agent_results) if agent_results else 0} keys)")
    print(f"  structured_requirements: {type(structured_requirements).__name__}")
    print(f"  strategic_analysis: {type(strategic_analysis).__name__}")

    conn.close()

    # 验证可序列化
    try:
        test_data = {
            "final_report": final_report,
            "agent_results": agent_results,
            "structured_requirements": structured_requirements,
            "strategic_analysis": strategic_analysis,
            "review_result": review_result,
        }
        json.dumps(test_data, ensure_ascii=False)
        print("  ✅ 所有数据 JSON 序列化测试通过")
    except Exception as e:
        print(f"  ❌ JSON 序列化失败: {e}")
        # 找出问题字段
        for key, val in test_data.items():
            try:
                json.dumps(val, ensure_ascii=False)
            except:
                print(f"    问题字段: {key}")
                # 深度转换
                test_data[key] = convert_bytes_to_str(val)

        # 重新赋值
        final_report = test_data["final_report"]
        agent_results = test_data["agent_results"]
        structured_requirements = test_data["structured_requirements"]
        strategic_analysis = test_data["strategic_analysis"]
        review_result = test_data["review_result"]

    # 2. 更新 Redis 会话
    sm = RedisSessionManager()
    await sm.connect()

    try:
        # 构建 aggregated_result 格式（前端期望的格式）
        aggregated_result = {
            "final_report": final_report,
            "agent_results": agent_results,
            "structured_requirements": structured_requirements,
            "strategic_analysis": strategic_analysis,
            "review_result": review_result,
        }

        await sm.update(
            session_id,
            {
                "status": "completed",
                "progress": 1.0,
                "final_report": final_report,
                "aggregated_result": aggregated_result,
                "report_data": final_report,  # 备用字段
                "error": None,  # 清除错误信息
            },
        )

        print(f"\n✅ 已恢复报告数据到 Redis 会话")

        # 验证
        session = await sm.get(session_id)
        print(f"  status: {session.get('status')}")
        print(f"  final_report: {bool(session.get('final_report'))}")
        print(f"  aggregated_result: {bool(session.get('aggregated_result'))}")

    finally:
        await sm.disconnect()


if __name__ == "__main__":
    session_id = sys.argv[1] if len(sys.argv) > 1 else "8pdwoxj8-20260107203552-0a8e56cd"
    asyncio.run(restore_report(session_id))
