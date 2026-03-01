"""
AB Testing Manager Tests
Core functionality testing for A/B test framework

Author: Intelligence Evolution System
Created: 2026-02-11
"""

import pytest
from datetime import datetime

from intelligent_project_analyzer.intelligence.ab_testing import ABTestManager, ABVariant, ABTestResult


@pytest.fixture
def ab_manager():
    """Create A/B test manager instance"""
    return ABTestManager()


@pytest.fixture
def control_config():
    """Control group config"""
    return {"selector": "keyword", "top_k": 3}


@pytest.fixture
def experiment_config():
    """Experiment group config"""
    return {"selector": "embedding", "top_k": 5}


def test_create_test(ab_manager, control_config, experiment_config):
    """Test creating A/B test"""
    ab_manager.create_test(
        test_name="test_1",
        role_id="V7_0",
        description="Test",
        control_config=control_config,
        experiment_config=experiment_config,
    )

    assert "test_1" in ab_manager.active_tests


def test_deterministic_allocation(ab_manager, control_config, experiment_config):
    """Test deterministic user allocation"""
    ab_manager.create_test(
        test_name="test_2",
        role_id="V7_0",
        description="Test",
        control_config=control_config,
        experiment_config=experiment_config,
    )

    user_id = "user_123"
    variant1 = ab_manager.get_variant("test_2", user_id)
    variant2 = ab_manager.get_variant("test_2", user_id)

    assert variant1 == variant2


def test_traffic_distribution(ab_manager, control_config, experiment_config):
    """Test traffic split distribution"""
    ab_manager.create_test(
        test_name="test_3",
        role_id="V7_0",
        description="Test",
        control_config=control_config,
        experiment_config=experiment_config,
        traffic_split=0.3,
    )

    experiment_count = 0
    for i in range(1000):
        variant = ab_manager.get_variant("test_3", f"user_{i}")
        if variant == ABVariant.EXPERIMENT:
            experiment_count += 1

    ratio = experiment_count / 1000
    assert 0.25 < ratio < 0.35


def test_record_result(ab_manager, control_config, experiment_config):
    """Test recording results"""
    ab_manager.create_test(
        test_name="test_4",
        role_id="V7_0",
        description="Test",
        control_config=control_config,
        experiment_config=experiment_config,
    )

    ab_manager.record_result(
        test_name="test_4", variant=ABVariant.CONTROL, user_id="user_1", success=True, response_time=0.05
    )

    assert len(ab_manager.results["test_4"]) == 1


def test_calculate_metrics(ab_manager):
    """Test metrics calculation"""
    results = [
        ABTestResult(ABVariant.CONTROL, "u1", True, 0.05, None, datetime.now().isoformat()),
        ABTestResult(ABVariant.CONTROL, "u2", True, 0.06, None, datetime.now().isoformat()),
        ABTestResult(ABVariant.CONTROL, "u3", False, 0.07, None, datetime.now().isoformat()),
    ]

    metrics = ab_manager._calculate_metrics(results)

    assert "success_rate" in metrics
    assert "avg_response_time" in metrics
    assert metrics["success_rate"] == pytest.approx(0.666, 0.1)


def test_significance_check(ab_manager):
    """Test statistical significance check"""
    control_results = [
        ABTestResult(ABVariant.CONTROL, f"u{i}", (i < 70), 0.05, None, datetime.now().isoformat()) for i in range(100)
    ]

    experiment_results = [
        ABTestResult(ABVariant.EXPERIMENT, f"u{i}", (i < 85), 0.05, None, datetime.now().isoformat())
        for i in range(100)
    ]

    significance = ab_manager._check_significance(control_results, experiment_results, 100)

    assert "is_significant" in significance
    assert "chi_square" in significance


def test_recommendation_adopt(ab_manager):
    """Test recommendation to adopt experiment"""
    rec = ab_manager._generate_recommendation(
        success_improvement=0.15,
        time_improvement=0.10,
        significance={"is_significant": True, "p_value": 0.01},
        total_samples=500,
    )

    assert rec["action"] == "adopt_experiment"


def test_recommendation_continue(ab_manager):
    """Test recommendation to continue testing"""
    rec = ab_manager._generate_recommendation(
        success_improvement=0.05,
        time_improvement=0.03,
        significance={"is_significant": False, "p_value": 0.15},
        total_samples=80,
    )

    assert rec["action"] == "continue_testing"


def test_analyze_test(ab_manager, control_config, experiment_config):
    """Test complete analysis"""
    ab_manager.create_test(
        test_name="test_5",
        role_id="V7_0",
        description="Test",
        control_config=control_config,
        experiment_config=experiment_config,
    )

    for i in range(100):
        ab_manager.record_result(
            test_name="test_5", variant=ABVariant.CONTROL, user_id=f"c{i}", success=(i < 70), response_time=0.08
        )

    for i in range(100):
        ab_manager.record_result(
            test_name="test_5", variant=ABVariant.EXPERIMENT, user_id=f"e{i}", success=(i < 85), response_time=0.06
        )

    analysis = ab_manager.analyze_test("test_5")

    assert "control" in analysis
    assert "experiment" in analysis
    assert analysis["experiment"]["success_rate"] > analysis["control"]["success_rate"]


def test_stop_test(ab_manager, control_config, experiment_config):
    """Test stopping a test"""
    ab_manager.create_test(
        test_name="test_6",
        role_id="V7_0",
        description="Test",
        control_config=control_config,
        experiment_config=experiment_config,
    )

    for i in range(50):
        variant = ABVariant.CONTROL if i % 2 == 0 else ABVariant.EXPERIMENT
        ab_manager.record_result(test_name="test_6", variant=variant, user_id=f"u{i}", success=True, response_time=0.05)

    result = ab_manager.stop_test("test_6")

    test_config = ab_manager.active_tests.get("test_6")
    if test_config:
        assert test_config.status == "stopped"
    assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
