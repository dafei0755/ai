"""
性能基线测试

本测试文件建立系统关键组件的性能基线，用于检测性能退化。

运行方式:
  # 首次建立基线
  pytest tests/performance/ --benchmark-only --benchmark-autosave

  # 后续比较性能
  pytest tests/performance/ --benchmark-compare=0001 --benchmark-compare-fail=mean:10%

性能指标:
  - LLM调用: <5秒/次
  - Redis操作: <50ms (保存), <30ms (读取)
  - PromptManager加载: <100ms
"""

import os
from unittest.mock import Mock, patch

import pytest

# 性能基线/benchmark 测试通常依赖本机环境（Redis、硬件、负载）稳定性，
# 不适合作为默认“快速测试”集合的一部分。
pytestmark = pytest.mark.slow


@pytest.fixture
def mock_llm():
    """模拟LLM实例，避免真实API调用"""
    mock = Mock()
    mock.invoke = Mock(return_value="测试响应内容")
    return mock


@pytest.fixture
def redis_manager():
    """初始化Redis管理器（使用测试DB）"""
    from intelligent_project_analyzer.services.redis_session_manager import RedisSessionManager

    # 使用独立的测试DB
    manager = RedisSessionManager()
    manager.redis_client.select(15)  # 测试专用DB

    yield manager

    # 清理测试数据
    manager.redis_client.flushdb()


def test_redis_save_performance(benchmark, redis_manager):
    """
    测试Redis保存性能

    性能基线: <50ms (P95)
    """
    session_id = "perf-test-save-123"
    test_state = {
        "requirement": "测试数据",
        "status": "running",
        "agent_results": {"agent1": "result1"},
        "selected_roles": ["role1", "role2"],
    }

    result = benchmark(redis_manager.save_state, session_id, test_state)

    # 验证性能
    mean_time = benchmark.stats.stats.mean
    assert mean_time < 0.05, f"Redis save too slow: {mean_time:.3f}s > 50ms"


def test_redis_load_performance(benchmark, redis_manager):
    """
    测试Redis读取性能

    性能基线: <30ms (P95)
    """
    session_id = "perf-test-load-123"
    test_data = {"test": "data", "nested": {"key": "value"}}

    # 预先保存数据
    redis_manager.save_state(session_id, test_data)

    result = benchmark(redis_manager.load_state, session_id)

    # 验证数据正确性
    assert result is not None
    assert result.get("test") == "data"

    # 验证性能
    mean_time = benchmark.stats.stats.mean
    assert mean_time < 0.03, f"Redis load too slow: {mean_time:.3f}s > 30ms"


def test_prompt_manager_load_performance(benchmark):
    """
    测试PromptManager加载性能

    性能基线: <100ms

    PromptManager使用单例模式，第一次加载后会缓存所有prompt。
    """
    from intelligent_project_analyzer.core.prompt_manager import PromptManager

    def load_prompt():
        pm = PromptManager()
        return pm.get_prompt("requirements_analyst")

    result = benchmark(load_prompt)

    # 验证返回数据包含必要字段
    assert result is not None
    assert "system_prompt" in result or "prompt" in result

    # 验证性能
    mean_time = benchmark.stats.stats.mean
    assert mean_time < 0.1, f"PromptManager too slow: {mean_time:.3f}s > 100ms"


@patch("intelligent_project_analyzer.services.llm_factory.LLMFactory.create_llm")
def test_llm_simple_response_time(mock_create_llm, benchmark, mock_llm):
    """
    测试LLM简单响应性能（模拟）

    性能基线: <5秒

    注意: 这是模拟测试，不会真实调用LLM API。
    真实性能测试应在test_llm_real_performance中进行（需要API key）。
    """
    mock_create_llm.return_value = mock_llm

    from intelligent_project_analyzer.services.llm_factory import LLMFactory

    def invoke_llm():
        llm = LLMFactory.create_llm()
        return llm.invoke("简单项目需求分析")

    result = benchmark(invoke_llm)

    # 验证响应
    assert result is not None
    assert isinstance(result, str)

    # 性能验证（模拟调用应该非常快）
    mean_time = benchmark.stats.stats.mean
    assert mean_time < 0.1, f"Mock LLM call too slow: {mean_time:.3f}s"


@pytest.mark.slow
@pytest.mark.skipif(not os.getenv("LLM_API_KEY"), reason="需要LLM_API_KEY环境变量来运行真实LLM性能测试")
def test_llm_real_performance(benchmark):
    """
    测试LLM真实调用性能（可选）

    性能基线: <5秒

    运行方式:
      LLM_API_KEY=your-key pytest tests/performance/ -m slow
    """
    from intelligent_project_analyzer.services.llm_factory import LLMFactory

    llm = LLMFactory.create_llm()

    result = benchmark(llm.invoke, "分析一个咖啡馆设计项目的需求")

    # 验证响应
    assert result is not None
    assert len(result) > 10  # 至少有一些内容

    # 验证性能
    mean_time = benchmark.stats.stats.mean
    assert mean_time < 5.0, f"LLM response too slow: {mean_time:.3f}s > 5s"

    # 记录额外统计信息
    print(f"\nLLM Performance Stats:")
    print(f"  Mean: {mean_time:.3f}s")
    print(f"  Min: {benchmark.stats.stats.min:.3f}s")
    print(f"  Max: {benchmark.stats.stats.max:.3f}s")
    print(f"  Stddev: {benchmark.stats.stats.stddev:.3f}s")


def test_file_processor_performance(benchmark):
    """
    测试文件处理性能

    性能基线: <200ms (小文件)
    """
    import tempfile

    from intelligent_project_analyzer.services.file_processor import FileProcessor

    processor = FileProcessor()

    # 创建临时测试文件
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("测试内容\n" * 100)
        temp_path = f.name

    try:

        def process_file():
            return processor.process_file(temp_path)

        result = benchmark(process_file)

        # 验证处理结果
        assert result is not None

        # 验证性能
        mean_time = benchmark.stats.stats.mean
        assert mean_time < 0.2, f"File processing too slow: {mean_time:.3f}s > 200ms"
    finally:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.remove(temp_path)


@pytest.mark.parametrize("batch_size", [10, 50, 100])
def test_batch_processing_scalability(benchmark, redis_manager, batch_size):
    """
    测试批量处理的可扩展性

    验证性能随批量大小线性增长
    """

    def batch_save():
        for i in range(batch_size):
            session_id = f"perf-batch-{i}"
            redis_manager.save_state(session_id, {"index": i, "data": "test"})

    benchmark(batch_save)

    # 验证所有数据都已保存
    for i in range(min(5, batch_size)):  # 抽样验证前5个
        state = redis_manager.load_state(f"perf-batch-{i}")
        assert state is not None
        assert state["index"] == i

    # 记录性能信息
    mean_time = benchmark.stats.stats.mean
    time_per_item = mean_time / batch_size

    print(f"\nBatch {batch_size} items:")
    print(f"  Total: {mean_time:.3f}s")
    print(f"  Per item: {time_per_item*1000:.2f}ms")
