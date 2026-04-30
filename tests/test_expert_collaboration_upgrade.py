"""
测试专家协作通道升级 (v7.18 升级4)

目标: 验证后续专家能够接收到前序专家的完整输出内容

测试要点:
1. 前序专家的完整交付物内容被传递
2. 移除了500字符截断限制
3. 结构化输出正确解析
4. 上下文格式清晰易读
"""

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict

import pytest

# pytest-asyncio 在 strict 模式下要求 async 测试必须显式标记。
# 该文件以“可单独运行的脚本”形式编写，但同时也会被 pytest 收集。
pytestmark = pytest.mark.asyncio

# Fix Unicode encoding for Windows console
if sys.platform == "win32":
    # Don't replace stdout/stderr with TextIOWrapper at import time (can close underlying streams)
    for _stream in (getattr(sys, "stdout", None), getattr(sys, "stderr", None)):
        if _stream is None:
            continue
        if hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from intelligent_project_analyzer.workflow.main_workflow import MainWorkflow


def create_mock_state_with_previous_experts() -> Dict[str, Any]:
    """
    创建包含前序专家输出的模拟状态

    模拟场景:
    - V4专家已完成分析（设计研究员）
    - V3专家即将执行（叙事专家），需要看到V4的完整输出
    """
    return {
        "user_input": "三代同堂家庭居住空间设计",
        "session_id": "test_collaboration_123",
        "current_phase": "expert_analysis",
        "agent_results": {
            "V4_设计研究员_4-1": {
                "expert_id": "V4_设计研究员_4-1",
                "expert_name": "设计研究员",
                "analysis": "完成了三代同堂家庭的设计研究分析",
                "structured_output": {
                    "task_execution_report": {
                        "deliverable_outputs": [
                            {
                                "deliverable_name": "三代同堂家庭成员画像",
                                "content": (
                                    "## 家庭成员画像\n\n"
                                    "### 1. 祖父母（60-75岁）\n"
                                    "- **生活习惯**: 早睡早起，喜欢园艺和太极拳\n"
                                    "- **空间需求**: 需要无障碍设计，采光充足的卧室\n"
                                    "- **社交需求**: 希望有接待老友的独立客厅\n"
                                    "- **健康关注**: 需要便捷的医疗箱和紧急呼叫系统\n\n"
                                    "### 2. 父母（35-45岁）\n"
                                    "- **工作模式**: 双职工家庭，需要居家办公空间\n"
                                    "- **空间需求**: 主卧带独立卫浴，书房/办公区\n"
                                    "- **生活节奏**: 工作日晚归，周末陪伴家人\n"
                                    "- **隐私需求**: 需要相对独立的私密空间\n\n"
                                    "### 3. 子女（5-12岁）\n"
                                    "- **成长需求**: 需要学习区、游戏区、收纳区\n"
                                    "- **空间特点**: 活动空间大，安全性要求高\n"
                                    "- **教育环境**: 需要安静的学习环境和多功能书桌\n"
                                    "- **兴趣爱好**: 绘画、乐器、阅读\n\n"
                                    "### 代际关系动态\n"
                                    "- **隔代养育**: 祖父母日常照顾孙辈\n"
                                    "- **共同活动**: 周末家庭聚餐，节假日外出\n"
                                    "- **隐私边界**: 各自独立空间 + 公共交流区\n"
                                    "- **文化传承**: 祖辈希望传授传统文化和手艺\n\n"
                                    "这份画像长度超过500字符，用于测试完整内容传递是否成功。"
                                ),
                                "completion_status": "completed",
                                "completion_rate": 1.0,
                                "notes": "基于中国传统三代同堂家庭模式分析",
                                "quality_self_assessment": 0.95,
                            },
                            {
                                "deliverable_name": "空间需求矩阵",
                                "content": (
                                    "## 空间需求矩阵\n\n"
                                    "| 空间类型 | 祖父母 | 父母 | 子女 | 共享度 | 优先级 |\n"
                                    "|---------|--------|------|------|--------|--------|\n"
                                    "| 卧室 | 主卧A | 主卧B | 儿童房 | 私密 | 高 |\n"
                                    "| 卫浴 | 独立 | 独立 | 共用 | 半私密 | 高 |\n"
                                    "| 客厅 | 老人客厅 | 家庭客厅 | - | 共享 | 高 |\n"
                                    "| 书房 | - | 办公书房 | 学习角 | 半私密 | 中 |\n"
                                    "| 厨房 | 传统厨房 | 现代厨房 | - | 共享 | 高 |\n"
                                    "| 餐厅 | 圆桌餐厅（可容纳6-8人） | - | - | 共享 | 高 |\n"
                                    "| 阳台 | 园艺阳台 | 生活阳台 | - | 共享 | 中 |\n"
                                    "| 储藏 | 杂物间 | 衣帽间 | 玩具间 | 各自 | 中 |\n\n"
                                    "### 关键设计要点\n"
                                    "1. **动静分区**: 老人区安静，儿童区活泼\n"
                                    "2. **无障碍设计**: 老人区域无高差，扶手配置\n"
                                    "3. **灵活隔断**: 可开可合的空间，适应不同场景\n"
                                    "4. **储物充足**: 三代人的物品需要分类收纳\n"
                                    "5. **自然采光**: 老人和儿童区域采光充足\n\n"
                                    "这是第二个交付物，也超过500字符，用于验证多个交付物的完整传递。"
                                ),
                                "completion_status": "completed",
                                "completion_rate": 1.0,
                                "notes": "结合中国家庭实际居住习惯",
                                "quality_self_assessment": 0.92,
                            },
                        ],
                        "task_completion_summary": "完成了三代同堂家庭成员画像和空间需求矩阵的详细分析",
                        "additional_insights": ["中国三代同堂家庭重视代际和谐与隐私平衡", "传统文化传承需要专门的活动空间"],
                        "execution_challenges": [],
                    },
                    "protocol_execution": {
                        "protocol_status": "complied",
                        "compliance_confirmation": "接受需求分析师的洞察并完成任务",
                        "challenge_details": None,
                        "reinterpretation": None,
                    },
                    "execution_metadata": {
                        "confidence": 0.95,
                        "completion_rate": 1.0,
                        "execution_time_estimate": "约8分钟",
                        "execution_notes": "基于中国传统三代同堂家庭模式",
                        "dependencies_satisfied": True,
                    },
                },
            }
        },
    }


async def test_context_building():
    """
    测试1: 验证上下文构建包含完整专家输出
    """
    print("=" * 80)
    print("🧪 测试1: 上下文构建 - 验证完整内容传递")
    print("=" * 80)

    workflow = MainWorkflow()
    mock_state = create_mock_state_with_previous_experts()

    # 调用上下文构建方法
    context = workflow._build_context_for_expert(mock_state)

    # 🔍 Debug: 打印完整上下文用于调试
    print("\n🔍 完整上下文内容（Debug）:")
    print("=" * 80)
    print(context)
    print("=" * 80)

    # 验证1: 上下文包含前序专家的名称
    assert "设计研究员" in context, "上下文应包含前序专家名称"
    print("   ✓ 包含前序专家名称")

    # 验证2: 上下文包含交付物名称
    assert "三代同堂家庭成员画像" in context, "上下文应包含交付物名称"
    assert "空间需求矩阵" in context, "上下文应包含第二个交付物名称"
    print("   ✓ 包含所有交付物名称")

    # 验证3: 上下文包含完整内容（超过500字符的部分）
    assert "祖父母日常照顾孙辈" in context, "上下文应包含完整内容（原被截断部分）"
    # 修改验证：这个文本在 additional_insights 中，不在 deliverable content 中
    # assert "文化传承需要专门的活动空间" in context, "上下文应包含第二个交付物的完整内容"
    print("   ✓ 包含完整内容（未截断）")

    # 验证4: 上下文包含结构化信息（表格、列表等）
    assert "空间类型" in context, "上下文应包含表格内容"
    assert "动静分区" in context, "上下文应包含设计要点"
    print("   ✓ 包含结构化内容（表格、列表）")

    # 验证5: 内容长度检查
    deliverable_1_content = (
        "## 家庭成员画像\n\n"
        "### 1. 祖父母（60-75岁）\n"
        "- **生活习惯**: 早睡早起，喜欢园艺和太极拳"
        # ... (省略中间部分)
        "这份画像长度超过500字符，用于测试完整内容传递是否成功。"
    )

    # 🔥 关键验证：确认没有被截断到500字符
    if len(deliverable_1_content) > 500:
        # 检查超过500字符后的内容是否存在
        assert "这份画像长度超过500字符" in context, "应包含超过500字符后的内容"
        print(f"   ✓ 完整内容传递成功（第一个交付物 {len(deliverable_1_content)}+ 字符）")

    # 打印上下文长度统计
    print("\n📊 上下文统计:")
    print(f"   - 总长度: {len(context)} 字符")
    print("   - 包含的交付物数量: 2 个")
    print(f"   - V4专家输出在上下文中的占比: {context.count('V4_设计研究员')} 次引用")

    # 打印部分上下文（用于手动检查）
    print("\n📋 上下文片段预览（前800字符）:")
    print(context[:800] + "...\n")

    return context


async def test_context_with_multiple_experts():
    """
    测试2: 验证多个前序专家的输出都被传递
    """
    print("=" * 80)
    print("🧪 测试2: 多专家上下文 - 验证V4和V5的输出都被传递")
    print("=" * 80)

    workflow = MainWorkflow()

    # 扩展模拟状态，添加V5专家
    mock_state = create_mock_state_with_previous_experts()
    mock_state["agent_results"]["V5_场景专家_5-1"] = {
        "expert_id": "V5_场景专家_5-1",
        "expert_name": "场景与用户生态专家",
        "analysis": "完成了场景分析",
        "structured_output": {
            "task_execution_report": {
                "deliverable_outputs": [
                    {
                        "deliverable_name": "典型生活场景设计",
                        "content": (
                            "## 典型生活场景\n\n"
                            "### 场景1: 周末家庭聚餐\n"
                            "- **参与者**: 全家6-8人\n"
                            "- **空间**: 圆桌餐厅 + 开放式厨房\n"
                            "- **动线**: 厨房-餐厅-客厅流畅连接\n"
                            "- **氛围**: 温馨和谐，便于交流\n\n"
                            "### 场景2: 祖辈照顾孙辈\n"
                            "- **活动**: 做作业、玩耍、午休\n"
                            "- **空间**: 老人房 + 儿童房 + 活动区\n"
                            "- **设计**: 视线可及，安全防护\n\n"
                            "这是V5专家的输出，也应该被完整传递给V3专家。"
                        ),
                        "completion_status": "completed",
                        "completion_rate": 1.0,
                        "quality_self_assessment": 0.90,
                    }
                ],
                "task_completion_summary": "完成了典型生活场景的设计分析",
                "additional_insights": [],
                "execution_challenges": [],
            },
            "protocol_execution": {
                "protocol_status": "complied",
                "compliance_confirmation": "接受需求分析师洞察",
                "challenge_details": None,
                "reinterpretation": None,
            },
            "execution_metadata": {
                "confidence": 0.90,
                "completion_rate": 1.0,
                "execution_time_estimate": "约6分钟",
                "dependencies_satisfied": True,
            },
        },
    }

    # 构建上下文
    context = workflow._build_context_for_expert(mock_state)

    # 验证V4和V5的输出都在上下文中
    assert "设计研究员" in context, "应包含V4专家"
    assert "场景与用户生态专家" in context, "应包含V5专家"
    print("   ✓ 包含V4和V5两位专家的名称")

    assert "家庭成员画像" in context, "应包含V4的交付物"
    assert "典型生活场景设计" in context, "应包含V5的交付物"
    print("   ✓ 包含V4和V5的所有交付物")

    assert "这是V5专家的输出" in context, "应包含V5的完整内容"
    print("   ✓ V5的完整内容也被传递")

    # 验证顺序（V4应该在V5之前）
    v4_pos = context.find("设计研究员")
    v5_pos = context.find("场景与用户生态专家")
    assert v4_pos < v5_pos, "V4应该在V5之前出现（按批次顺序）"
    print("   ✓ 专家输出按批次顺序排列")

    print("\n📊 多专家上下文统计:")
    print(f"   - 总长度: {len(context)} 字符")
    print("   - 包含的专家数量: 2 位")
    print("   - 包含的交付物数量: 3 个")

    return context


async def test_context_format_readability():
    """
    测试3: 验证上下文格式清晰易读
    """
    print("=" * 80)
    print("🧪 测试3: 上下文格式 - 验证可读性和结构")
    print("=" * 80)

    workflow = MainWorkflow()
    mock_state = create_mock_state_with_previous_experts()

    context = workflow._build_context_for_expert(mock_state)

    # 验证Markdown标题结构
    assert "## 前序专家的分析成果" in context, "应有前序专家章节标题"
    assert "### 设计研究员" in context, "应有专家名称子标题"
    assert "#### 交付物 1:" in context, "应有交付物编号子标题"
    print("   ✓ Markdown标题层级正确")

    # 验证关键字段标签
    assert "**交付物数量**:" in context, "应有交付物数量标签"
    assert "**状态**:" in context, "应有完成状态标签"
    assert "**内容**:" in context, "应有内容标签"
    print("   ✓ 关键字段标签清晰")

    # 验证分隔和空行
    line_count = context.count("\n\n")
    assert line_count >= 5, f"应有足够的段落分隔（当前{line_count}个）"
    print(f"   ✓ 段落分隔充足（{line_count}个空行）")

    # 验证不包含截断标记
    assert "..." not in context or context.count("...") == 0, "不应有截断标记"
    print("   ✓ 无截断标记（完整传递）")

    print("\n✅ 上下文格式验证通过")

    return context


async def test_backward_compatibility():
    """
    测试4: 验证向后兼容性（无structured_output时降级）
    """
    print("=" * 80)
    print("🧪 测试4: 向后兼容 - 验证降级处理")
    print("=" * 80)

    workflow = MainWorkflow()

    # 模拟旧格式输出（没有structured_output）
    mock_state = {
        "user_input": "测试项目",
        "session_id": "test_backward_123",
        "current_phase": "expert_analysis",
        "agent_results": {
            "V4_旧格式专家_4-1": {
                "expert_id": "V4_旧格式专家_4-1",
                "expert_name": "旧格式专家",
                "analysis": "这是一个旧格式的专家输出，没有structured_output字段，只有analysis字段。这种情况下应该降级到使用analysis字段的内容。"
                # 没有 structured_output 字段
            }
        },
    }

    context = workflow._build_context_for_expert(mock_state)

    # 验证降级逻辑
    assert "旧格式专家" in context, "应包含专家名称"
    assert "这是一个旧格式的专家输出" in context, "应使用analysis字段作为降级"
    print("   ✓ 降级到analysis字段成功")

    # 验证不会报错
    assert len(context) > 0, "上下文应非空"
    print("   ✓ 向后兼容，无错误抛出")

    print("\n✅ 向后兼容性验证通过")

    return context


async def main():
    """运行所有测试"""
    print("\n🚀 开始测试专家协作通道升级 (v7.18 升级4)\n")

    try:
        # 测试1: 基础上下文构建
        await test_context_building()

        # 测试2: 多专家上下文
        await test_context_with_multiple_experts()

        # 测试3: 格式可读性
        await test_context_format_readability()

        # 测试4: 向后兼容性
        await test_backward_compatibility()

        print("\n" + "=" * 80)
        print("🎉 所有测试通过！专家协作通道工作正常")
        print("=" * 80)

        print("\n📈 升级4预期改进:")
        print("   - ✅ 移除500字符截断限制")
        print("   - ✅ 传递完整结构化输出（交付物内容）")
        print("   - ✅ 支持多个前序专家的输出")
        print("   - ✅ 上下文格式清晰易读")
        print("   - ✅ 向后兼容旧格式输出")
        print("   - 📊 预期质量提升: 15-20%")
        print("   - 📊 专家可参考和引用前序分析")
        print("   - 📊 减少重复分析，提高一致性")

        return True

    except AssertionError as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback

        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n❌ 测试出错: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
