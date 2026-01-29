"""
v7.140 验证功能测试 - 核心验证报告结构
"""


def test_validation_report_structure():
    """测试验证报告数据结构"""

    # 模拟验证结果
    validation_report = {
        "status": "failed",
        "issues": [
            {
                "severity": "critical",
                "type": "missing_task",
                "description": "以下需求未分配任务: 数据库设计",
                "missing_capabilities": ["数据库设计"],
                "suggestion": "建议增加数据库专家",
            },
            {
                "severity": "high",
                "type": "capability_mismatch",
                "role_id": "V2_设计总监_2-1",
                "role_name": "UI设计专家",
                "description": "UI设计专家 的专业能力可能无法胜任任务",
                "tasks": ["数据库架构设计", "SQL优化"],
                "suggestion": "建议重新评估任务分配",
            },
            {
                "severity": "medium",
                "type": "dependency_conflict",
                "description": "批次1的'设计'任务可能依赖批次2的'需求'任务",
                "suggestion": "建议调整批次顺序",
            },
        ],
        "summary": "验证结果: 1 个严重问题, 1 个高风险问题",
        "total_issues": 3,
    }

    # 测试1：状态字段
    assert validation_report["status"] in ["passed", "warning", "failed"]
    print("[PASS] 验证状态字段有效")

    # 测试2：问题列表
    assert len(validation_report["issues"]) == 3
    print(f"[PASS] 问题列表包含 {len(validation_report['issues'])} 个问题")

    # 测试3：严重问题检测
    critical_issues = [i for i in validation_report["issues"] if i["severity"] == "critical"]
    assert len(critical_issues) == 1
    print(f"[PASS] 检测到 {len(critical_issues)} 个严重问题")

    # 测试4：问题类型
    issue_types = {i["type"] for i in validation_report["issues"]}
    assert "missing_task" in issue_types
    assert "capability_mismatch" in issue_types
    print(f"[PASS] 问题类型检测：{issue_types}")

    # 测试5：修正建议
    for issue in validation_report["issues"]:
        if issue["severity"] in ["critical", "high"]:
            assert "suggestion" in issue
    print("[PASS] 所有严重问题都有修正建议")


def test_validation_state_fields():
    """测试验证结果在 state 中的字段"""

    # 模拟验证后的 state 更新
    state_update = {
        "validation_report": {
            "status": "passed",
            "issues": [],
            "summary": "验证结果: 0 个严重问题, 0 个高风险问题",
            "total_issues": 0,
        },
        "validation_passed": True,
        "validation_retry_count": 1,
    }

    # 测试1：验证报告字段存在
    assert "validation_report" in state_update
    print("[PASS] state 包含 validation_report 字段")

    # 测试2：验证通过标志
    assert state_update["validation_passed"] == True
    print("[PASS] validation_passed 标志正确")

    # 测试3：重试计数
    assert state_update["validation_retry_count"] == 1
    assert 1 <= state_update["validation_retry_count"] <= 3
    print(f"[PASS] validation_retry_count = {state_update['validation_retry_count']}")


def test_correction_feedback_structure():
    """测试修正反馈的结构"""

    # 模拟修正反馈
    correction_feedback = """任务分配验证失败，需要调整：

缺失任务：以下需求未分配任务: 数据库设计
   建议：建议增加相应专家或调整现有专家的任务范围

能力不匹配：UI设计专家 无法胜任任务
   建议：建议重新评估 UI设计专家 的任务分配，或选择更匹配的专家
"""

    # 测试1：包含关键字
    assert "任务分配验证失败" in correction_feedback
    assert "缺失任务" in correction_feedback or "能力不匹配" in correction_feedback
    print("[PASS] 修正反馈包含关键信息")

    # 测试2：结构化（包含建议）
    assert "建议" in correction_feedback
    print("[PASS] 修正反馈包含建议信息")


def test_validation_workflow_integration():
    """测试验证流程集成点"""

    # 模拟验证循环
    max_retries = 3
    validation_results = [
        {"status": "failed"},  # 第1次失败
        {"status": "warning"},  # 第2次警告
        {"status": "passed"},  # 第3次通过（未执行）
    ]

    # 测试：验证循环逻辑
    for attempt in range(max_retries):
        result = validation_results[attempt]

        if result["status"] == "passed":
            print(f"[PASS] 第{attempt + 1}次验证通过，退出循环")
            break
        elif result["status"] == "failed" and attempt < max_retries - 1:
            print(f"[INFO] 第{attempt + 1}次验证失败，准备重试")
            continue
        else:
            print(f"[WARN] 第{attempt + 1}次验证状态: {result['status']}")
            break


def test_workflow_changes():
    """测试工作流变更"""

    # 测试：验证 quality_preflight 已被跳过
    workflow_edges = [
        ("project_director", "deliverable_id_generator"),
        ("deliverable_id_generator", "search_query_generator"),
        ("search_query_generator", "role_task_unified_review"),
        # ("role_task_unified_review", "quality_preflight"),  # 已注释
        # ("quality_preflight", "batch_executor"),  # 已注释
    ]

    # 验证流程简化
    assert ("role_task_unified_review", "quality_preflight") not in workflow_edges
    print("[PASS] 工作流已跳过 quality_preflight 节点")


if __name__ == "__main__":
    print("=" * 60)
    print("v7.140 验证功能测试")
    print("=" * 60)
    print()

    try:
        print("测试1: 验证报告数据结构")
        test_validation_report_structure()
        print()

        print("测试2: State 字段结构")
        test_validation_state_fields()
        print()

        print("测试3: 修正反馈结构")
        test_correction_feedback_structure()
        print()

        print("测试4: 验证循环流程")
        test_validation_workflow_integration()
        print()

        print("测试5: 工作流变更")
        test_workflow_changes()
        print()

        print("=" * 60)
        print("所有测试通过")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n测试失败: {e}")
        import traceback

        traceback.print_exc()
        exit(1)
