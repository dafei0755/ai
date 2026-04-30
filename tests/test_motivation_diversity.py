"""测试动机识别的多样性 - 同一项目内的多维度识别"""
import asyncio

import pytest

from intelligent_project_analyzer.services.motivation_engine import MotivationInferenceEngine


@pytest.mark.asyncio
async def test_same_project_diversity():
    """测试同一个项目中不同任务的动机多样性"""
    engine = MotivationInferenceEngine()

    # 冈仁波齐冥想中心项目 - 应该有多种不同的动机类型
    user_input = "一位匿名的亿万富翁，计划在西藏冈仁波齐山脚下建造一座小型的私人冥想中心，不对外开放。他唯一的要求是：'让建筑和室内消失在环境中，让人能在此直面自己的内心和宇宙。'"

    tasks = [
        {
            "title": "冈仁波齐山脚环境综合研究",
            "description": "调研冈仁波齐地区的气候、地势特点以及高原建筑的技术适配方案",
            "source_keywords": ["西藏冈仁波齐", "高原环境", "气候寒冷", "地势复杂"],
            "expected": "technical",  # 技术创新
        },
        {
            "title": "藏族文化符号与精神传承研究",
            "description": "研究冈仁波齐在藏族文化中的象征意义，提炼可融入设计的文化元素",
            "source_keywords": ["藏族文化", "冈仁波齐", "精神传承", "文化符号"],
            "expected": "cultural",  # 文化认同
        },
        {
            "title": "建筑隐形化设计技术研究",
            "description": "研究国际隐形建筑案例和技术手段，如材料选型、地景建筑融合方式等",
            "source_keywords": ["隐形建筑", "建筑与环境融合"],
            "expected": "aesthetic or technical",  # 审美或技术
        },
        {
            "title": "深层精神联系空间设计策略研究",
            "description": "研究能够引发深层精神对话与宇宙连接的空间设计模式",
            "source_keywords": ["深层内心对话", "精神探索", "与宇宙连接"],
            "expected": "emotional",  # 情感性
        },
        {
            "title": "高原生态材料研究与供应链规划",
            "description": "研究适用于高原寒冷气候的可持续生态建筑材料，并制定可行的材料采集与供应方案",
            "source_keywords": ["高原生态材料", "寒冷气候", "可持续"],
            "expected": "sustainable",  # 可持续价值
        },
        {
            "title": "高海拔场地施工与技术策略",
            "description": "分析极端环境下的施工技术难点和解决方案",
            "source_keywords": ["高海拔", "极端环境", "施工技术"],
            "expected": "technical",  # 技术创新
        },
    ]

    print("=" * 80)
    print("冈仁波齐冥想中心 - 多维度动机识别测试")
    print("=" * 80)
    print(f"\n项目整体需求: {user_input[:100]}...\n")

    results = []
    for i, task_data in enumerate(tasks, 1):
        task = {
            "title": task_data["title"],
            "description": task_data["description"],
            "source_keywords": task_data["source_keywords"],
        }

        result = await engine.infer(task=task, user_input=user_input, structured_data={})

        results.append(result.primary)

        match = "✅" if task_data["expected"] in result.primary or result.primary in task_data["expected"] else "❌"
        print(f"{i}. {task['title'][:30]}")
        print(f"   识别结果: {result.primary} ({result.primary_label})")
        print(f"   预期类型: {task_data['expected']}")
        print(f"   置信度: {result.confidence:.2f}")
        print(f"   匹配: {match}")
        print()

    # 统计多样性
    unique_types = set(results)
    print("=" * 80)
    print(f"多样性统计: {len(unique_types)}/{len(tasks)} 种不同动机类型")
    print(f"识别到的类型: {', '.join(unique_types)}")

    if len(unique_types) >= 3:
        print("✅ 多样性测试通过！同一项目中成功识别出多种动机类型")
    else:
        print("❌ 多样性不足！所有任务被识别为相似的动机类型")


if __name__ == "__main__":
    asyncio.run(test_same_project_diversity())
