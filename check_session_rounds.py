"""检查会话是否包含 rounds 数据"""
import asyncio

import httpx

    print("🧪 测试新会话多轮搜索功能 (ucppt)")
    """创建新会话并测试多轮搜索"""
    print("=" * 60)
    print("🧪 测试新会话多轮搜索功能 (ucppt)")
    async with client.stream('POST', f'{base_url}/api/search/ucppt/stream', json={

    base_url = 'http://127.0.0.1:8000'
            'max_rounds': 5,
            'confidence_threshold': 0.8,
    print("\n1️⃣ 创建新搜索会话...")
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(f'{base_url}/api/search/session/create', json={
            'query': '测试多轮搜索功能',
            'deep_mode': True,
        })
        data = response.json()
        if not data.get('success'):
        response = await client.get(f'{base_url}/api/search/session/{session_id}')
            return
        session_id = data['session_id']
        print(f"✅ 会话创建成功: {session_id}")
        print(f"   deep_mode: {data.get('deep_mode')}")

    # 2. 执行搜索（使用 ucppt API）
    print("\n2️⃣ 执行搜索（收集事件）...")
    events_received = []
    rounds_received = []

    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream('POST', f'{base_url}/api/search/ucppt/stream', json={
            'query': '测试多轮搜索功能',
            'max_rounds': 5,
            'confidence_threshold': 0.8,
        }) as response:
            async for line in response.aiter_lines():
                if line.startswith('event:'):
                    event_type = line[6:].strip()
                    events_received.append(event_type)
                    if event_type in ('round_complete', 'search_round_complete'):
                        rounds_received.append(True)
                        print(f"   📦 第 {len(rounds_received)} 轮搜索完成")

    print(f"\n✅ 搜索完成，收到 {len(events_received)} 个事件")
    print(f"   轮次: {len(rounds_received)}")

    # 3. 等待一下让后端保存数据
    await asyncio.sleep(2)

    # 4. 获取会话数据
    print("\n3️⃣ 检查会话数据...")
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(f'{base_url}/api/search/session/{session_id}')
        data = response.json()

        if data.get('success'):
            session = data['session']
            print(f"\n📊 会话数据:")
            print(f"   Query: {session.get('query', 'N/A')}")
            print(f"   isDeepMode: {session.get('isDeepMode', 'N/A')}")
            print(f"   totalRounds: {session.get('totalRounds', 0)}")
            print(f"   rounds count: {len(session.get('rounds', []))}")
            print(f"   sources count: {len(session.get('sources', []))}")
            print(f"   thinkingContent: {len(session.get('thinkingContent', '')) if session.get('thinkingContent') else 0} chars")
            print(f"   answerContent: {len(session.get('answerContent', '')) if session.get('answerContent') else 0} chars")

            rounds = session.get('rounds', [])
            if rounds:
                print("\n   轮次详情:")
                for r in rounds:
                    print(f"     Round {r.get('round')}: {r.get('topicName')} - {r.get('sourcesFound')} sources")
            else:
                print("\n   ⚠️ 没有轮次数据!")
        else:
            print(f"❌ 获取会话失败: {data}")

if __name__ == '__main__':
    asyncio.run(test_new_session())
