"""
测试性能监控模块
测试Prometheus指标收集和降级处理

作者: Intelligence Evolution System
创建时间: 2026-02-11
"""

import pytest
import time
from unittest.mock import patch

from intelligent_project_analyzer.intelligence.performance_monitor import (
    PerformanceMonitor,
    MonitorConfig,
    get_monitor,
    reset_monitor,
)


@pytest.fixture
def monitor():
    """创建监控实例（降级模式）"""
    config = MonitorConfig(enable_prometheus=False, enable_logging=True)  # 测试时使用降级模式
    return PerformanceMonitor(config=config)


@pytest.fixture
def prometheus_monitor():
    """创建Prometheus模式监控（需要mock）"""
    with patch("intelligent_project_analyzer.intelligence.performance_monitor.PROMETHEUS_AVAILABLE", True):
        with patch("intelligent_project_analyzer.intelligence.performance_monitor.Counter"), patch(
            "intelligent_project_analyzer.intelligence.performance_monitor.Histogram"
        ), patch("intelligent_project_analyzer.intelligence.performance_monitor.Gauge"):
            config = MonitorConfig(enable_prometheus=True)
            monitor = PerformanceMonitor(config=config)
            return monitor


class TestMonitorConfig:
    """测试监控配置"""

    def test_default_config(self):
        """测试默认配置"""
        config = MonitorConfig()
        assert config.enable_prometheus is True
        assert config.enable_logging is True
        assert len(config.histogram_buckets) > 0
        assert "quality_score_min" in config.alert_thresholds

    def test_custom_config(self):
        """测试自定义配置"""
        config = MonitorConfig(
            enable_prometheus=False, histogram_buckets=(0.1, 0.5, 1.0), alert_thresholds={"quality_score_min": 3.0}
        )
        assert config.enable_prometheus is False
        assert len(config.histogram_buckets) == 3
        assert config.alert_thresholds["quality_score_min"] == 3.0


class TestInitialization:
    """测试初始化"""

    def test_init_fallback_mode(self, monitor):
        """测试降级模式初始化"""
        assert hasattr(monitor, "_fallback_metrics")
        assert "expert_calls_total" in monitor._fallback_metrics
        assert "selection_duration" in monitor._fallback_metrics

    @patch("intelligent_project_analyzer.intelligence.performance_monitor.PROMETHEUS_AVAILABLE", True)
    @patch("intelligent_project_analyzer.intelligence.performance_monitor.Counter")
    @patch("intelligent_project_analyzer.intelligence.performance_monitor.Histogram")
    @patch("intelligent_project_analyzer.intelligence.performance_monitor.Gauge")
    def test_init_prometheus_mode(self, mock_gauge, mock_histogram, mock_counter):
        """测试Prometheus模式初始化"""
        config = MonitorConfig(enable_prometheus=True)
        PerformanceMonitor(config=config)

        # 验证创建了Prometheus指标
        assert mock_counter.called
        assert mock_histogram.called
        assert mock_gauge.called


class TestCallRecording:
    """测试调用记录"""

    def test_record_call(self, monitor):
        """测试记录调用"""
        monitor.record_call("V7_0", "example_selection")
        monitor.record_call("V7_0", "example_selection")
        monitor.record_call("V7_0", "quality_analysis")

        # 验证降级指标
        metrics = monitor._fallback_metrics["expert_calls_total"]
        assert metrics["V7_0:example_selection"] == 2
        assert metrics["V7_0:quality_analysis"] == 1

    def test_record_multiple_roles(self, monitor):
        """测试多角色调用"""
        monitor.record_call("V7_0", "selection")
        monitor.record_call("V2_0", "selection")
        monitor.record_call("V3_0", "selection")

        metrics = monitor._fallback_metrics["expert_calls_total"]
        assert len(metrics) == 3


class TestDurationRecording:
    """测试耗时记录"""

    def test_record_duration(self, monitor):
        """测试记录持续时间"""
        monitor.record_duration("selection", 0.05, "V7_0", "embedding")
        monitor.record_duration("selection", 0.08, "V7_0", "embedding")

        durations = monitor._fallback_metrics["selection_duration"]
        assert len(durations) == 2
        assert durations[0]["duration"] == 0.05
        assert durations[1]["duration"] == 0.08

    def test_timer_context_manager(self, monitor):
        """测试计时器上下文管理器"""
        with monitor.timer("test_operation", "V7_0"):
            time.sleep(0.01)  # 睡眠10ms

        durations = monitor._fallback_metrics["selection_duration"]
        assert len(durations) == 1
        assert durations[0]["duration"] >= 0.01


class TestQualityRecording:
    """测试质量记录"""

    def test_record_quality(self, monitor):
        """测试记录质量评分"""
        monitor.record_quality("V7_0", 4.2)

        metrics = monitor._fallback_metrics["quality_score"]
        assert metrics["V7_0"] == 4.2

    def test_quality_alert_threshold(self, monitor, caplog):
        """测试质量低于阈值时的告警"""
        # 配置的阈值是3.5
        monitor.record_quality("V7_0", 3.0)

        # 验证日志中有警告
        assert any("质量评分低于阈值" in record.message for record in caplog.records)


class TestTokenRecording:
    """测试Token记录"""

    def test_record_tokens(self, monitor):
        """测试记录Token消耗"""
        monitor.record_tokens("V7_0", prompt_tokens=500, completion_tokens=300)
        monitor.record_tokens("V7_0", prompt_tokens=200, completion_tokens=150)

        metrics = monitor._fallback_metrics["token_usage_total"]
        assert metrics["V7_0:prompt"] == 700
        assert metrics["V7_0:completion"] == 450


class TestErrorRecording:
    """测试错误记录"""

    def test_record_error(self, monitor):
        """测试记录错误"""
        monitor.record_error("V7_0", "TimeoutError")
        monitor.record_error("V7_0", "TimeoutError")
        monitor.record_error("V7_0", "ValueError")

        metrics = monitor._fallback_metrics["error_total"]
        assert metrics["V7_0:TimeoutError"] == 2
        assert metrics["V7_0:ValueError"] == 1


class TestPerformanceDecorator:
    """测试性能装饰器"""

    def test_decorator_success(self, monitor):
        """测试装饰器成功情况"""

        @monitor.track_performance("test_operation")
        def sample_function(role_id="V7_0"):
            time.sleep(0.01)
            return "success"

        result = sample_function(role_id="V7_0")

        assert result == "success"

        # 验证记录了调用和耗时
        assert "V7_0:test_operation" in monitor._fallback_metrics["expert_calls_total"]
        assert len(monitor._fallback_metrics["selection_duration"]) > 0

    def test_decorator_error(self, monitor):
        """测试装饰器错误情况"""

        @monitor.track_performance("test_operation")
        def failing_function(role_id="V7_0"):
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            failing_function(role_id="V7_0")

        # 验证记录了错误
        assert "V7_0:ValueError" in monitor._fallback_metrics["error_total"]


class TestMetricsSnapshot:
    """测试指标快照"""

    def test_get_snapshot(self, monitor):
        """测试获取指标快照"""
        # 记录一些数据
        monitor.record_call("V7_0", "selection")
        monitor.record_duration("selection", 0.05, "V7_0")
        monitor.record_quality("V7_0", 4.0)

        snapshot = monitor.get_metrics_snapshot()

        assert "expert_calls_total" in snapshot
        assert "selection_duration" in snapshot
        assert "quality_score" in snapshot


class TestGrafanaDashboard:
    """测试Grafana仪表板生成"""

    def test_generate_dashboard_json(self, monitor):
        """测试生成仪表板JSON"""
        dashboard = monitor.get_grafana_dashboard_json()

        assert "dashboard" in dashboard
        assert "panels" in dashboard["dashboard"]

        panels = dashboard["dashboard"]["panels"]
        assert len(panels) > 0

        # 验证包含关键面板
        panel_titles = [p["title"] for p in panels]
        assert any("Call Rate" in title for title in panel_titles)
        assert any("Duration" in title for title in panel_titles)
        assert any("Quality" in title for title in panel_titles)
        assert any("Token" in title for title in panel_titles)

    def test_dashboard_structure(self, monitor):
        """测试仪表板结构"""
        dashboard = monitor.get_grafana_dashboard_json()

        # 验证每个面板的基本结构
        for panel in dashboard["dashboard"]["panels"]:
            assert "id" in panel
            assert "title" in panel
            assert "type" in panel
            assert "targets" in panel
            assert len(panel["targets"]) > 0


class TestExamplePoolSize:
    """测试示例池大小记录"""

    def test_update_pool_size(self, monitor):
        """测试更新示例池大小"""
        monitor.update_example_pool_size("V7_0", 45)

        # 在降级模式下，这应该不会崩溃（即使没有实际作用）
        # 主要测试接口可用性
        assert True


class TestGlobalMonitor:
    """测试全局监控实例"""

    def teardown_method(self):
        """每次测试后重置全局实例"""
        reset_monitor()

    def test_get_global_monitor(self):
        """测试获取全局监控实例"""
        # 创建降级模式监控避免Prometheus注册冲突
        with patch("intelligent_project_analyzer.intelligence.performance_monitor.PROMETHEUS_AVAILABLE", False):
            monitor1 = get_monitor()
            monitor2 = get_monitor()

            # 应该返回同一实例
            assert monitor1 is monitor2

    def test_reset_monitor(self):
        """测试重置监控实例"""
        # 使用降级模式
        with patch("intelligent_project_analyzer.intelligence.performance_monitor.PROMETHEUS_AVAILABLE", False):
            monitor1 = get_monitor()
            reset_monitor()
            monitor2 = get_monitor()

            # 重置后应该是不同实例
            assert monitor1 is not monitor2


class TestIntegration:
    """集成测试"""

    def test_full_monitoring_workflow(self, monitor):
        """完整监控工作流"""
        # 模拟完整的监控场景

        # 1. 记录调用
        monitor.record_call("V7_0", "example_selection")

        # 2. 使用装饰器追踪性能
        @monitor.track_performance("selection")
        def select_examples(role_id):
            time.sleep(0.02)
            return ["example1", "example2"]

        select_examples(role_id="V7_0")

        # 3. 记录质量
        monitor.record_quality("V7_0", 4.5)

        # 4. 记录Token消耗
        monitor.record_tokens("V7_0", 1000, 500)

        # 5. 获取快照
        snapshot = monitor.get_metrics_snapshot()

        # 验证所有指标都被记录
        assert "V7_0:example_selection" in snapshot["expert_calls_total"]
        assert len(snapshot["selection_duration"]) > 0
        assert snapshot["quality_score"]["V7_0"] == 4.5
        assert snapshot["token_usage_total"]["V7_0:prompt"] == 1000

    def test_concurrent_operations(self, monitor):
        """测试并发操作"""
        import threading

        def record_operations():
            for i in range(10):
                monitor.record_call("V7_0", "operation")
                monitor.record_duration("op", 0.01, "V7_0")

        threads = [threading.Thread(target=record_operations) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证所有操作都被记录（50次调用）
        metrics = monitor._fallback_metrics["expert_calls_total"]
        assert metrics["V7_0:operation"] == 50


class TestMetricRecording:
    """测试通用指标记录"""

    def test_record_metric_quality(self, monitor):
        """测试记录质量指标"""
        monitor.record_metric("quality_score", 4.2, labels={"role_id": "V7_0"})

        assert monitor._fallback_metrics["quality_score"]["V7_0"] == 4.2

    def test_record_metric_duration(self, monitor):
        """测试记录耗时指标"""
        monitor.record_metric("duration", 0.05, labels={"role_id": "V7_0", "operation": "test_op"})

        durations = monitor._fallback_metrics["selection_duration"]
        assert len(durations) > 0
        assert durations[-1]["duration"] == 0.05


class TestAlertThresholds:
    """测试告警阈值"""

    def test_custom_alert_thresholds(self):
        """测试自定义告警阈值"""
        config = MonitorConfig(
            enable_prometheus=False,
            alert_thresholds={"quality_score_min": 4.0, "response_time_p95_max": 0.2, "error_rate_max": 0.1},
        )

        assert config.alert_thresholds["quality_score_min"] == 4.0
        assert config.alert_thresholds["response_time_p95_max"] == 0.2

    def test_quality_threshold_alert(self, monitor, caplog):
        """测试质量阈值告警"""
        # 默认阈值是3.5
        monitor.record_quality("V7_0", 3.0)  # 低于阈值

        # 应该有警告日志
        warning_logs = [r for r in caplog.records if r.levelname == "WARNING"]
        assert len(warning_logs) > 0
        assert any("质量评分低于阈值" in r.message for r in warning_logs)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
