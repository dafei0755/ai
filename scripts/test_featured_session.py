"""
测试精选展示会话查询
"""
import asyncio
import json
from pathlib import Path


async def test_featured_session():
    session_id = "8pdwoxj8-20260103181555-163e0ad3"

    print(f"\n🔍 测试会话: {session_id}\n")

    # 1. 检查归档数据库
    print("1️⃣ 检查归档数据库...")
    try:
        from intelligent_project_analyzer.services.session_archive_manager import SessionArchiveManager

        archive_manager = SessionArchiveManager()
        archived = await archive_manager.get_archived_session(session_id)
        if archived:
            print(f"   ✅ 归档中找到会话")
            print(f"   - 用户输入: {archived.get('user_input', 'N/A')[:50]}...")
            print(f"   - 状态: {archived.get('status', 'N/A')}")
            print(f"   - 创建时间: {archived.get('created_at', 'N/A')}")
        else:
            print(f"   ❌ 归档中未找到")
    except Exception as e:
        print(f"   ❌ 查询归档失败: {e}")

    # 2. 检查Redis
    print("\n2️⃣ 检查Redis...")
    try:
        from intelligent_project_analyzer.services.redis_session_manager import RedisSessionManager

        redis_manager = RedisSessionManager()
        session = await redis_manager.get_session_state(session_id)
        if session:
            print(f"   ✅ Redis中找到会话")
            print(f"   - 用户输入: {session.get('user_input', 'N/A')[:50]}...")
        else:
            print(f"   ❌ Redis中未找到")
    except Exception as e:
        print(f"   ❌ 查询Redis失败: {e}")

    # 3. 检查概念图
    print("\n3️⃣ 检查概念图...")
    images_path = Path(f"data/generated_images/{session_id}")
    metadata_path = images_path / "metadata.json"

    print(f"   图片目录: {images_path}")
    print(f"   目录存在: {images_path.exists()}")
    print(f"   metadata存在: {metadata_path.exists()}")

    if metadata_path.exists():
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            images = metadata.get("images", [])
            print(f"   ✅ 找到 {len(images)} 张概念图")
            for i, img in enumerate(images[:3], 1):
                print(f"      {i}. {img.get('url', 'N/A')}")
        except Exception as e:
            print(f"   ❌ 读取metadata失败: {e}")
    else:
        print(f"   ❌ 未找到概念图")

    # 4. 列出所有图片文件
    if images_path.exists():
        print("\n4️⃣ 图片目录内容:")
        files = list(images_path.glob("*"))
        if files:
            for f in files[:10]:
                print(f"      - {f.name}")
        else:
            print(f"      (空目录)")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(test_featured_session())
