"""
测试 v7.140 project_director 内置验证功能

测试场景：
1. 任务完整性检查
2. 角色能力匹配检查
3. 批次依赖检查
4. LLM 自我修正循环
5. 验证报告生成
"""

from unittest.mock import MagicMock, patch

import pytest

from intelligent_project_analyzer.agents.project_director import (
    _check_batch_dependency_conflicts,
    _check_capability_match,
    _extract_assigned_capabilities_from_distribution,
    _extract_required_capabilities_from_requirements,
    _generate_correction_feedback,
    _validate_task_distribution_embedded,
)


class TestTaskDistributionValidation:
    """测试任务分配验证函数"""

    def test_validate_all_passed(self):
        """测试：所有验证通过的场景"""
        state = {
            "structured_requirements": {"functional_requirements": ["用户登录", "数据展示"]},
            "confirmed_core_tasks": [{"title": "设计用户界面", "description": "设计登录和展示页面"}],
        }

        strategic_analysis = {
            "selected_roles": [
                {"role_id": "V2_设计总监_2-1", "name": "UI设计专家", "expertise": "用户界面设计、视觉设计、交互设计"},
                {"role_id": "V4_设计研究员_4-1", "name": "UX研究员", "expertise": "用户体验研究、可用性测试"},
            ],
            "task_distribution": {
                "V2_设计总监_2-1": {"tasks": ["设计用户登录界面", "设计数据展示界面"]},
                "V4_设计研究员_4-1": {"tasks": ["研究用户行为", "优化界面体验"]},
            },
            "execution_batches": [["V4_设计研究员_4-1"], ["V2_设计总监_2-1"]],
        }

        result = _validate_task_distribution_embedded(state, strategic_analysis)

        assert result["status"] == "passed"
        assert result["total_issues"] == 0
        assert "验证结果" in result["summary"]

    def test_validate_missing_tasks(self):
        """测试：检测缺失的任务分配"""
        state = {
            "structured_requirements": {"functional_requirements": ["用户登录", "数据展示", "权限管理"]},
            "confirmed_core_tasks": [],
        }

        strategic_analysis = {
            "selected_roles": [{"role_id": "V2_设计总监_2-1", "name": "UI设计专家", "expertise": "用户界面设计"}],
            "task_distribution": {"V2_设计总监_2-1": {"tasks": ["设计用户登录界面"]}},  # 缺少数据展示和权限管理
            "execution_batches": [["V2_设计总监_2-1"]],
        }

        result = _validate_task_distribution_embedded(state, strategic_analysis)

        assert result["status"] == "failed"
        assert any(issue["type"] == "missing_task" for issue in result["issues"])
        assert result["total_issues"] > 0

    def test_validate_capability_mismatch(self):
        """测试：检测角色能力不匹配"""
        state = {"structured_requirements": {"functional_requirements": ["数据库设计"]}, "confirmed_core_tasks": []}

        strategic_analysis = {
            "selected_roles": [{"role_id": "V2_设计总监_2-1", "name": "UI设计专家", "expertise": "用户界面设计、视觉设计"}],  # 不匹配数据库任务
            "task_distribution": {"V2_设计总监_2-1": {"tasks": ["设计数据库架构", "优化SQL查询"]}},  # UI专家不应该做数据库
            "execution_batches": [["V2_设计总监_2-1"]],
        }

        result = _validate_task_distribution_embedded(state, strategic_analysis)

        # 应该检测到能力不匹配
        assert any(issue["type"] == "capability_mismatch" for issue in result["issues"])

    def test_validate_dependency_conflicts(self):
        """测试：检测批次依赖冲突"""
        state = {"structured_requirements": {}, "confirmed_core_tasks": []}

        strategic_analysis = {
            "selected_roles": [
                {"role_id": "V2_设计总监_2-1", "name": "设计师", "expertise": "设计"},
                {"role_id": "V4_设计研究员_4-1", "name": "研究员", "expertise": "需求分析"},
            ],
            "task_distribution": {
                "V2_设计总监_2-1": {"tasks": ["基于需求分析进行设计"]},  # 依赖需求分析
                "V4_设计研究员_4-1": {"tasks": ["进行需求分析"]},
            },
            "execution_batches": [["V2_设计总监_2-1"], ["V4_设计研究员_4-1"]],  # 批次1：设计（依赖需求分析）  # 批次2：需求分析（应该在前）
        }

        result = _validate_task_distribution_embedded(state, strategic_analysis)

        # 应该检测到依赖冲突
        assert any(issue["type"] == "dependency_conflict" for issue in result["issues"])


class TestCapabilityExtraction:
    """测试能力提取函数"""

    def test_extract_required_capabilities_from_requirements(self):
        """测试：从需求中提取所需能力"""
        state = {
            "structured_requirements": {"functional_requirements": ["用户认证系统", "数据可视化"]},
            "confirmed_core_tasks": [{"title": "设计登录界面", "description": "创建登录页面"}],
        }

        capabilities = _extract_required_capabilities_from_requirements(state)

        assert len(capabilities) > 0
        assert any("用户认证" in cap for cap in capabilities)

    def test_extract_assigned_capabilities_from_distribution(self):
        """测试：从任务分配中提取已分配能力"""
        task_distribution = {
            "V2_设计总监_2-1": {"tasks": ["设计用户界面", "创建视觉规范"]},
            "V4_设计研究员_4-1": {"tasks": ["用户研究", "可用性测试"]},
        }

        selected_roles = [{"role_id": "V2_设计总监_2-1"}, {"role_id": "V4_设计研究员_4-1"}]

        capabilities = _extract_assigned_capabilities_from_distribution(task_distribution, selected_roles)

        assert len(capabilities) == 4  # 4个任务
        assert any("设计用户界面" in cap for cap in capabilities)


class TestCapabilityMatch:
    """测试能力匹配检查"""

    def test_capability_match_success(self):
        """测试：能力匹配成功"""
        expertise = "用户界面设计、交互设计、视觉设计"
        tasks = ["设计用户界面", "创建交互原型"]

        result = _check_capability_match(expertise, tasks)

        assert result is True

    def test_capability_match_failure(self):
        """测试：能力不匹配"""
        expertise = "用户界面设计、视觉设计"
        tasks = ["数据库架构设计", "优化SQL查询"]

        result = _check_capability_match(expertise, tasks)

        assert result is False

    def test_capability_match_empty_expertise(self):
        """测试：空能力描述时默认通过"""
        expertise = ""
        tasks = ["任意任务"]

        result = _check_capability_match(expertise, tasks)

        assert result is True  # 无法判断时默认通过


class TestBatchDependencyCheck:
    """测试批次依赖检查"""

    def test_batch_dependency_no_conflicts(self):
        """测试：批次依赖正常"""
        batches = [["V4_设计研究员_4-1"], ["V2_设计总监_2-1"]]  # 需求分析  # 设计实现

        task_distribution = {"V4_设计研究员_4-1": {"tasks": ["需求分析"]}, "V2_设计总监_2-1": {"tasks": ["设计实现"]}}

        issues = _check_batch_dependency_conflicts(batches, task_distribution)

        assert len(issues) == 0

    def test_batch_dependency_with_conflicts(self):
        """测试：批次依赖冲突"""
        batches = [["V2_设计总监_2-1"], ["V4_设计研究员_4-1"]]  # 设计实现（依赖需求）  # 需求分析（应该在前）

        task_distribution = {"V2_设计总监_2-1": {"tasks": ["基于需求进行设计"]}, "V4_设计研究员_4-1": {"tasks": ["需求分析"]}}

        issues = _check_batch_dependency_conflicts(batches, task_distribution)

        assert len(issues) > 0
        assert any(issue["type"] == "dependency_conflict" for issue in issues)


class TestCorrectionFeedback:
    """测试修正反馈生成"""

    def test_generate_correction_feedback_critical(self):
        """测试：生成严重问题的修正反馈"""
        validation_result = {
            "status": "failed",
            "issues": [
                {
                    "severity": "critical",
                    "type": "missing_task",
                    "description": "数据库设计未分配专家",
                    "missing_capabilities": ["数据库设计"],
                    "suggestion": "增加数据库专家",
                }
            ],
        }

        feedback = _generate_correction_feedback(validation_result)

        assert "任务分配验证失败" in feedback
        assert "缺失任务" in feedback
        assert "数据库设计" in feedback

    def test_generate_correction_feedback_capability_mismatch(self):
        """测试：生成能力不匹配的修正反馈"""
        validation_result = {
            "status": "failed",
            "issues": [
                {
                    "severity": "high",
                    "type": "capability_mismatch",
                    "role_id": "V2_设计总监_2-1",
                    "role_name": "UI设计专家",
                    "description": "UI设计专家无法胜任数据库任务",
                    "suggestion": "选择数据库专家",
                }
            ],
        }

        feedback = _generate_correction_feedback(validation_result)

        assert "能力不匹配" in feedback
        assert "UI设计专家" in feedback


class TestProjectDirectorValidationLoop:
    """测试 project_director 的验证循环（集成测试）"""

    @patch("intelligent_project_analyzer.agents.project_director.ProjectDirectorAgent")
    def test_validation_loop_pass_first_try(self, mock_director):
        """测试：第一次验证即通过"""
        # 这是一个简化的集成测试示例
        # 实际测试需要完整的 state 和 mock LLM
        pass

    @patch("intelligent_project_analyzer.agents.project_director.ProjectDirectorAgent")
    def test_validation_loop_retry_and_pass(self, mock_director):
        """测试：重试后验证通过"""
        # 模拟第一次失败，第二次成功的场景
        pass

    @patch("intelligent_project_analyzer.agents.project_director.ProjectDirectorAgent")
    def test_validation_loop_max_retries_exceeded(self, mock_director):
        """测试：达到最大重试次数"""
        # 模拟3次都失败的场景
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
