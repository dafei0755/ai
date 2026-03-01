"""
使用数据跟踪器测试
"""

import pytest
from datetime import datetime, timedelta
import json

from intelligent_project_analyzer.intelligence.usage_tracker import UsageTracker


class TestUsageTracker:
    """使用数据跟踪器测试"""

    @pytest.fixture
    def tracker_sqlite(self, tmp_path):
        """创建SQLite版跟踪器"""
        return UsageTracker(data_dir=tmp_path / "logs_sqlite", use_sqlite=True)

    @pytest.fixture
    def tracker_jsonl(self, tmp_path):
        """创建JSONL版跟踪器"""
        return UsageTracker(data_dir=tmp_path / "logs_jsonl", use_sqlite=False)

    def test_initialization_sqlite(self, tracker_sqlite):
        """测试SQLite初始化"""
        assert tracker_sqlite.data_dir.exists()
        assert tracker_sqlite.db_path.exists()
        assert tracker_sqlite.use_sqlite is True

    def test_initialization_jsonl(self, tracker_jsonl):
        """测试JSONL初始化"""
        assert tracker_jsonl.data_dir.exists()
        assert tracker_jsonl.use_sqlite is False

    def test_log_expert_usage_sqlite(self, tracker_sqlite):
        """测试SQLite记录"""
        tracker_sqlite.log_expert_usage(
            role_id="V2_0",
            user_request="分析住宅项目需求",
            selected_examples=["v2_0_targeted_001", "v2_0_comprehensive_002"],
            output_tokens=1500,
            response_time=2.5,
            user_feedback={"liked": True, "rating": 5},
            session_id="session_001",
            metadata={"version": "1.0"},
        )

        # 查询记录
        logs = tracker_sqlite.get_logs(limit=1)
        assert len(logs) == 1
        assert logs[0]["role_id"] == "V2_0"
        assert logs[0]["output_tokens"] == 1500

    def test_log_expert_usage_jsonl(self, tracker_jsonl):
        """测试JSONL记录"""
        tracker_jsonl.log_expert_usage(
            role_id="V3_1",
            user_request="结构设计分析",
            selected_examples=["v3_1_targeted_001"],
            output_tokens=2000,
            response_time=3.0,
        )

        # 检查文件是否创建
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = tracker_jsonl.data_dir / f"usage_{today}.jsonl"
        assert log_file.exists()

        # 读取并验证
        with open(log_file, "r", encoding="utf-8") as f:
            line = f.readline()
            log = json.loads(line)
            assert log["role_id"] == "V3_1"
            assert log["output_tokens"] == 2000

    def test_get_logs_with_filters(self, tracker_sqlite):
        """测试带过滤条件的查询"""
        # 插入多条记录
        for i in range(5):
            tracker_sqlite.log_expert_usage(
                role_id=f"V{i}_0",
                user_request=f"请求 {i}",
                selected_examples=[f"example_{i}"],
                output_tokens=1000 + i * 100,
                response_time=1.0 + i * 0.5,
                session_id=f"session_{i % 2}",
            )

        # 测试角色过滤
        v0_logs = tracker_sqlite.get_logs(role_id="V0_0")
        assert len(v0_logs) == 1
        assert v0_logs[0]["role_id"] == "V0_0"

        # 测试会话过滤
        session_0_logs = tracker_sqlite.get_logs(session_id="session_0")
        assert all(log["session_id"] == "session_0" for log in session_0_logs)

        # 测试限制返回数量
        limited_logs = tracker_sqlite.get_logs(limit=2)
        assert len(limited_logs) == 2

    def test_get_logs_date_range(self, tracker_sqlite):
        """测试日期范围查询"""
        now = datetime.now()

        # 插入不同时间的记录（通过直接操作时间戳）
        tracker_sqlite.log_expert_usage(
            role_id="V2_0", user_request="最近的请求", selected_examples=["ex1"], output_tokens=1000, response_time=1.0
        )

        # 查询最近1天
        recent_logs = tracker_sqlite.get_logs(start_date=now - timedelta(days=1))
        assert len(recent_logs) >= 1

    def test_analyze_example_effectiveness(self, tracker_sqlite):
        """测试示例有效性分析"""
        role_id = "V2_0"

        # 模拟使用数据
        tracker_sqlite.log_expert_usage(
            role_id=role_id,
            user_request="请求1",
            selected_examples=["v2_0_001", "v2_0_002"],
            output_tokens=1500,
            response_time=2.0,
            user_feedback={"liked": True},
        )

        tracker_sqlite.log_expert_usage(
            role_id=role_id,
            user_request="请求2",
            selected_examples=["v2_0_001", "v2_0_003"],
            output_tokens=1800,
            response_time=2.5,
            user_feedback={"rating": 2},
        )

        tracker_sqlite.log_expert_usage(
            role_id=role_id,
            user_request="请求3",
            selected_examples=["v2_0_002"],
            output_tokens=1200,
            response_time=1.5,
            user_feedback={"liked": True, "rating": 5},
        )

        # 分析示例有效性
        stats = tracker_sqlite.analyze_example_effectiveness(role_id, days=30)

        assert "v2_0_001" in stats
        assert "v2_0_002" in stats
        assert "v2_0_003" in stats

        # v2_0_001 使用了2次
        assert stats["v2_0_001"]["usage_count"] == 2

        # v2_0_002 有2次正面反馈
        assert stats["v2_0_002"]["positive_feedback"] == 2

        # v2_0_003 有1次负面反馈
        assert stats["v2_0_003"]["negative_feedback"] == 1

        # 检查质量分数计算
        assert "quality_score" in stats["v2_0_001"]
        assert isinstance(stats["v2_0_001"]["quality_score"], float)

        print("\n示例有效性分析:")
        for ex_id, stat in stats.items():
            print(f"  {ex_id}:")
            print(f"    使用次数: {stat['usage_count']}")
            print(f"    质量分数: {stat['quality_score']:.2f}")
            print(f"    平均tokens: {stat['avg_tokens']:.1f}")

    def test_get_statistics(self, tracker_sqlite):
        """测试统计信息"""
        # 插入多条记录
        roles = ["V2_0", "V3_1", "V4_1"]
        for role in roles:
            for i in range(3):
                tracker_sqlite.log_expert_usage(
                    role_id=role,
                    user_request=f"请求 {i}",
                    selected_examples=[f"ex_{i}"],
                    output_tokens=1000 + i * 200,
                    response_time=1.0 + i * 0.5,
                )

        # 获取全部统计
        stats = tracker_sqlite.get_statistics(days=7)

        assert stats["total_calls"] == 9
        assert stats["period_days"] == 7
        assert len(stats["role_distribution"]) == 3
        assert stats["role_distribution"]["V2_0"] == 3
        assert stats["avg_response_time"] > 0
        assert stats["avg_output_tokens"] > 0

        print("\n统计信息:")
        print(f"  总调用: {stats['total_calls']}")
        print(f"  角色分布: {stats['role_distribution']}")
        print(f"  平均响应时间: {stats['avg_response_time']:.2f}秒")
        print(f"  平均tokens: {stats['avg_output_tokens']:.1f}")

        # 获取单个角色统计
        v2_stats = tracker_sqlite.get_statistics(role_id="V2_0", days=7)
        assert v2_stats["total_calls"] == 3

    def test_concurrent_logging(self, tracker_sqlite):
        """测试并发记录"""
        import concurrent.futures

        def log_usage(i):
            tracker_sqlite.log_expert_usage(
                role_id=f"V{i % 3}_0",
                user_request=f"并发请求 {i}",
                selected_examples=[f"ex_{i}"],
                output_tokens=1000,
                response_time=1.0,
            )

        # 并发记录100条
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            executor.map(log_usage, range(100))

        # 验证记录数量
        logs = tracker_sqlite.get_logs()
        assert len(logs) >= 100

        print(f"\n并发记录测试: {len(logs)} 条记录")

    def test_jsonl_query_performance(self, tracker_jsonl):
        """测试JSONL查询性能"""
        import time

        # 插入大量记录
        for i in range(100):
            tracker_jsonl.log_expert_usage(
                role_id=f"V{i % 5}_0",
                user_request=f"请求 {i}",
                selected_examples=[f"ex_{i}"],
                output_tokens=1000,
                response_time=1.0,
            )

        # 测试查询性能
        start_time = time.time()
        logs = tracker_jsonl.get_logs(role_id="V0_0")
        query_time = time.time() - start_time

        print("\nJSONL查询性能:")
        print("  记录总数: 100")
        print(f"  匹配记录: {len(logs)}")
        print(f"  查询耗时: {query_time*1000:.1f}ms")

        assert query_time < 1.0, "JSONL查询应该在1秒内完成"
