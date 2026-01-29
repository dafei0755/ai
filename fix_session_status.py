#!/usr/bin/env python
"""检查和修复会话状态"""
import asyncio
import json
import sys


async def check_session(session_id: str):
    from intelligent_project_analyzer.services.redis_session_manager import RedisSessionManager

    sm = RedisSessionManager()
    await sm.connect()

    try:
        session = await sm.get(session_id)
        if session:
            print(f"会话ID: {session_id}")
            print(f"状态: {session.get('status')}, 进度: {session.get('progress')}")
            print(f"\n=== 会话字段 ===")
            for key in sorted(session.keys()):
                value = session.get(key)
                if isinstance(value, (dict, list)):
                    print(f"  {key}: {type(value).__name__} (长度: {len(value) if value else 0})")
                elif isinstance(value, str) and len(value) > 100:
                    print(f"  {key}: str (长度: {len(value)})")
                else:
                    print(f"  {key}: {value}")

            # 检查关键报告字段
            print(f"\n=== 报告数据检查 ===")
            print(f"  final_report: {bool(session.get('final_report'))}")
            print(f"  report_data: {bool(session.get('report_data'))}")
            print(f"  aggregated_result: {bool(session.get('aggregated_result'))}")
            print(f"  results: {bool(session.get('results'))}")

            # 如果有 aggregated_result，显示其结构
            agg = session.get("aggregated_result")
            if agg:
                print(f"\n=== aggregated_result 结构 ===")
                if isinstance(agg, dict):
                    for k in sorted(agg.keys()):
                        v = agg.get(k)
                        if isinstance(v, (dict, list)):
                            print(f"  {k}: {type(v).__name__} (长度: {len(v) if v else 0})")
                        elif isinstance(v, str) and len(v) > 50:
                            print(f"  {k}: str (长度: {len(v)})")
                        else:
                            print(f"  {k}: {v}")
        else:
            print(f"❌ 会话 {session_id} 不存在")
    finally:
        await sm.disconnect()


if __name__ == "__main__":
    session_id = sys.argv[1] if len(sys.argv) > 1 else "8pdwoxj8-20260107203552-0a8e56cd"
    asyncio.run(check_session(session_id))
