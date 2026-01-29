"""
简化的验证函数测试
直接测试验证逻辑，无需完整的模块导入
"""

import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# 测试验证函数的核心逻辑
def test_capability_match_logic():
    """测试能力匹配的核心逻辑"""

    def _check_capability_match(expertise: str, tasks: list) -> bool:
        """简化的能力匹配检查"""
        if not expertise or not tasks:
            return True

        expertise_lower = expertise.lower()

        for task in tasks:
            task_lower = str(task).lower()
            task_keywords = [w for w in task_lower.split() if len(w) > 2]

            matched = any(keyword in expertise_lower for keyword in task_keywords[:5])
            if not matched:
                return False

        return True

    # 测试用例1：匹配成功
    expertise1 = "用户界面设计、交互设计、视觉设计"
    tasks1 = ["设计用户界面", "创建交互原型"]
    result1 = _check_capability_match(expertise1, tasks1)
    print(f"测试1: expertise='{expertise1}', tasks={tasks1}")
    print(f"  结果: {result1}, 预期: True")
    assert result1 == True, f"预期True, 实际{result1}"
    print("  [PASS] 测试1通过：能力匹配成功")

    # 测试用例2：匹配失败
    expertise2 = "用户界面设计、视觉设计"
    tasks2 = ["数据库架构设计", "优化SQL查询"]
    assert _check_capability_match(expertise2, tasks2) == False
    print("✓ 测试2通过：检测到能力不匹配")

    # 测试用例3：空专长时默认通过
    expertise3 = ""
    tasks3 = ["任意任务"]
    assert _check_capability_match(expertise3, tasks3) == True
    print("✓ 测试3通过：空专长默认通过")


def test_extract_capabilities_logic():
    """测试能力提取的核心逻辑"""

    def _extract_required_capabilities(state: dict) -> list:
        """从需求中提取所需能力"""
        capabilities = []

        requirements = state.get("structured_requirements", {})
        confirmed_tasks = state.get("confirmed_core_tasks", [])

        # 从功能需求中提取
        if "functional_requirements" in requirements:
            for req in requirements["functional_requirements"]:
                if isinstance(req, str):
                    capabilities.append(req[:30])

        # 从确认任务中提取
        if confirmed_tasks:
            for task in confirmed_tasks:
                if isinstance(task, dict):
                    title = task.get("title", "")
                    if title:
                        capabilities.append(title[:30])

        return capabilities

    def _extract_assigned_capabilities(task_distribution: dict) -> list:
        """从任务分配中提取已分配能力"""
        capabilities = []

        for role_id, task_data in task_distribution.items():
            if isinstance(task_data, dict) and "tasks" in task_data:
                tasks_list = task_data["tasks"]
            else:
                tasks_list = [str(task_data)]

            for task in tasks_list:
                task_str = str(task)
                capabilities.append(task_str[:30])

        return capabilities

    # 测试用例1：提取所需能力
    state = {
        "structured_requirements": {"functional_requirements": ["用户认证系统", "数据可视化"]},
        "confirmed_core_tasks": [{"title": "设计登录界面", "description": "创建登录页面"}],
    }

    required = _extract_required_capabilities(state)
    assert len(required) == 3  # 2个功能需求 + 1个确认任务
    print(f"✓ 测试4通过：提取到 {len(required)} 个所需能力")

    # 测试用例2：提取已分配能力
    task_distribution = {"V2_设计总监_2-1": {"tasks": ["设计用户界面", "创建视觉规范"]}, "V4_设计研究员_4-1": {"tasks": ["用户研究"]}}

    assigned = _extract_assigned_capabilities(task_distribution)
    assert len(assigned) == 3  # 3个任务
    print(f"✓ 测试5通过：提取到 {len(assigned)} 个已分配能力")


def test_correction_feedback_generation():
    """测试修正反馈生成逻辑"""

    def _generate_correction_feedback(validation_result: dict) -> str:
        """生成修正反馈"""
        feedback_parts = ["任务分配验证失败，需要调整：\n\n"]

        for issue in validation_result["issues"]:
            if issue["severity"] in ["critical", "high"]:
                if issue["type"] == "missing_task":
                    feedback_parts.append(
                        f"❌ 缺失任务：{issue['description']}\n" f"   建议：{issue.get('suggestion', '请为这些能力需求分配合适的专家')}\n\n"
                    )
                elif issue["type"] == "capability_mismatch":
                    feedback_parts.append(
                        f"⚠️  能力不匹配：{issue['role_name']} 无法胜任任务\n"
                        f"   建议：{issue.get('suggestion', '重新选择具有相关专业能力的专家')}\n\n"
                    )

        return "".join(feedback_parts)

    # 测试用例：生成修正反馈
    validation_result = {
        "status": "failed",
        "issues": [
            {"severity": "critical", "type": "missing_task", "description": "数据库设计未分配专家", "suggestion": "增加数据库专家"},
            {
                "severity": "high",
                "type": "capability_mismatch",
                "role_name": "UI设计专家",
                "description": "UI设计专家无法胜任数据库任务",
                "suggestion": "选择数据库专家",
            },
        ],
    }

    feedback = _generate_correction_feedback(validation_result)

    assert "任务分配验证失败" in feedback
    assert "缺失任务" in feedback
    assert "能力不匹配" in feedback
    assert "数据库设计" in feedback
    print("✓ 测试6通过：生成修正反馈")
    print(f"\n生成的反馈示例：\n{feedback}")


def test_validation_status_determination():
    """测试验证状态判定逻辑"""

    def _determine_validation_status(issues: list) -> str:
        """根据问题列表判定验证状态"""
        critical_count = sum(1 for i in issues if i["severity"] == "critical")
        high_count = sum(1 for i in issues if i["severity"] == "high")

        if critical_count > 0:
            return "failed"
        elif high_count > 2:
            return "warning"
        else:
            return "passed"

    # 测试用例1：无问题 - 通过
    issues1 = []
    assert _determine_validation_status(issues1) == "passed"
    print("✓ 测试7通过：无问题时状态为 passed")

    # 测试用例2：有严重问题 - 失败
    issues2 = [{"severity": "critical", "type": "missing_task"}, {"severity": "high", "type": "capability_mismatch"}]
    assert _determine_validation_status(issues2) == "failed"
    print("✓ 测试8通过：有严重问题时状态为 failed")

    # 测试用例3：高风险问题过多 - 警告
    issues3 = [
        {"severity": "high", "type": "capability_mismatch"},
        {"severity": "high", "type": "capability_mismatch"},
        {"severity": "high", "type": "capability_mismatch"},
    ]
    assert _determine_validation_status(issues3) == "warning"
    print("✓ 测试9通过：高风险问题>2时状态为 warning")


if __name__ == "__main__":
    print("=" * 60)
    print("开始测试 v7.140 验证函数核心逻辑")
    print("=" * 60)

    try:
        test_capability_match_logic()
        print()
        test_extract_capabilities_logic()
        print()
        test_correction_feedback_generation()
        print()
        test_validation_status_determination()

        print()
        print("=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ 测试失败：{e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 发生错误：{e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
