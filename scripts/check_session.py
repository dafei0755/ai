import sys

sys.path.insert(0, "d:/11-20/langgraph-design")

import asyncio

from intelligent_project_analyzer.services.redis_session_manager import RedisSessionManager


async def main():
    mgr = RedisSessionManager()
    await mgr.initialize()
    session = await mgr.get("api-20251231130355-b45109e4")

    if session:
        print(f"Status: {session.get('status')}")
        print(f"Current node: {session.get('current_node')}")
        print(f"Has interrupt_data: {'interrupt_data' in session}")

        if "interrupt_data" in session and session["interrupt_data"]:
            interrupt = session["interrupt_data"]
            if isinstance(interrupt, dict):
                print(f"Interaction type: {interrupt.get('interaction_type')}")
                print(f"Step: {interrupt.get('step')}/{interrupt.get('total_steps')}")
                print(f"Title: {interrupt.get('title')}")
                print(f"Message: {interrupt.get('message')}")
                if "extracted_tasks" in interrupt:
                    print(f"Number of tasks: {len(interrupt['extracted_tasks'])}")
            else:
                print(f"Interrupt data type: {type(interrupt)}")
    else:
        print("Session not found")

    await mgr.close()


asyncio.run(main())
