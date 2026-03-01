"""
测试数据库管理器 (Test Database Manager)

测试本体论学习数据库的操作功能。

版本: v3.0
创建日期: 2026-02-10
"""

import pytest
import tempfile
from pathlib import Path
from intelligent_project_analyzer.learning.database_manager import DatabaseManager, init_database


class TestDatabaseManager:
    """测试数据库管理器"""

    @pytest.fixture
    def temp_db(self):
        """创建临时数据库"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_ontology.db"
            db = DatabaseManager(str(db_path))
            db.initialize()
            yield db

    def test_initialization(self, temp_db):
        """测试数据库初始化"""
        assert temp_db.check_exists()
        version = temp_db.get_schema_version()
        assert version == "3.0"

    def test_insert_dimension(self, temp_db):
        """测试插入维度"""
        dim_id = temp_db.insert_dimension(
            name="测试维度",
            category="test_category",
            project_type="personal_residential",
            description="这是一个测试维度",
            ask_yourself="如何测试？",
            examples="示例1, 示例2",
        )

        assert dim_id is not None
        assert dim_id > 0

    def test_insert_duplicate_dimension(self, temp_db):
        """测试插入重复维度（应该失败）"""
        # 第一次插入
        dim_id1 = temp_db.insert_dimension(
            name="重复维度", category="test", project_type="test_type", description="测试", ask_yourself="测试？", examples="测试"
        )
        assert dim_id1 is not None

        # 第二次插入相同名称（应该因UNIQUE约束失败）
        dim_id2 = temp_db.insert_dimension(
            name="重复维度",
            category="test",
            project_type="test_type",
            description="测试2",
            ask_yourself="测试2？",
            examples="测试2",
        )
        assert dim_id2 is None

    def test_get_dimension(self, temp_db):
        """测试获取维度"""
        # 插入
        dim_id = temp_db.insert_dimension(
            name="获取测试",
            category="test",
            project_type="test_type",
            description="测试获取",
            ask_yourself="能获取吗？",
            examples="可以",
        )

        # 获取
        dim = temp_db.get_dimension(dim_id)
        assert dim is not None
        assert dim["name"] == "获取测试"
        assert dim["category"] == "test"
        assert dim["usage_count"] == 0

    def test_update_dimension_usage(self, temp_db):
        """测试更新使用计数"""
        # 插入
        dim_id = temp_db.insert_dimension(
            name="使用计数测试",
            category="test",
            project_type="test_type",
            description="测试",
            ask_yourself="测试？",
            examples="测试",
        )

        # 更新使用计数
        temp_db.update_dimension_usage(dim_id)
        temp_db.update_dimension_usage(dim_id)

        # 验证
        dim = temp_db.get_dimension(dim_id)
        assert dim["usage_count"] == 2

    def test_get_dimensions_by_project_type(self, temp_db):
        """测试按项目类型查询维度"""
        # 插入多个维度
        for i in range(3):
            temp_db.insert_dimension(
                name=f"商业维度{i}",
                category="test",
                project_type="commercial_enterprise",
                description=f"测试{i}",
                ask_yourself=f"测试{i}？",
                examples=f"示例{i}",
            )

        # 查询
        dimensions = temp_db.get_dimensions_by_project_type("commercial_enterprise")
        assert len(dimensions) == 3
        assert all(d["project_type"] == "commercial_enterprise" for d in dimensions)

    def test_log_learning_session(self, temp_db):
        """测试记录学习会话"""
        success = temp_db.log_learning_session(
            session_id="test_session_001",
            project_type="personal_residential",
            expert_roles=["spatial_planner", "conceptual_designer"],
            extracted_dimensions=[{"name": "维度1", "confidence": 0.8}, {"name": "维度2", "confidence": 0.7}],
            quality_metrics={"avg_confidence": 0.75},
        )

        assert success is True

    def test_add_candidate(self, temp_db):
        """测试添加候选维度"""
        candidate_id = temp_db.add_candidate(
            dimension_data={
                "name": "候选维度",
                "category": "test",
                "project_type": "test",
                "description": "测试候选",
                "ask_yourself": "测试？",
                "examples": "示例",
            },
            confidence_score=0.85,
            source_session_id="test_session_001",
        )

        assert candidate_id is not None
        assert candidate_id > 0

    def test_get_pending_candidates(self, temp_db):
        """测试获取待审核候选"""
        # 添加候选
        temp_db.add_candidate(dimension_data={"name": "候选1"}, confidence_score=0.8)
        temp_db.add_candidate(dimension_data={"name": "候选2"}, confidence_score=0.9)

        # 获取
        candidates = temp_db.get_pending_candidates()
        assert len(candidates) >= 2

    def test_approve_candidate(self, temp_db):
        """测试批准候选维度"""
        # 添加候选
        candidate_id = temp_db.add_candidate(
            dimension_data={
                "name": "待批准维度",
                "category": "test",
                "project_type": "test_type",
                "description": "测试批准",
                "ask_yourself": "能批准吗？",
                "examples": "可以",
            },
            confidence_score=0.9,
        )

        # 批准
        success = temp_db.approve_candidate(candidate_id, reviewer_id="test_reviewer")
        assert success is True

        # 验证：应该在dimensions表中能找到
        dimensions = temp_db.get_dimensions_by_project_type("test_type", status="active")
        assert any(d["name"] == "待批准维度" for d in dimensions)

    def test_get_statistics(self, temp_db):
        """测试获取统计信息"""
        # 插入一些数据
        temp_db.insert_dimension(
            name="统计测试", category="test", project_type="test", description="测试", ask_yourself="测试？", examples="测试"
        )
        temp_db.add_candidate(dimension_data={"name": "候选"}, confidence_score=0.8)

        # 获取统计
        stats = temp_db.get_statistics()

        assert "active_dimensions" in stats
        assert "pending_candidates" in stats
        assert "total_learning_sessions" in stats
        assert "schema_version" in stats
        assert stats["active_dimensions"] >= 1
        assert stats["pending_candidates"] >= 1

    def test_init_database_function(self):
        """测试便捷初始化函数"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_init.db"
            success = init_database(str(db_path))

            assert success is True
            assert db_path.exists()
