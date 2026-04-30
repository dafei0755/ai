# 测试覆盖率提升 - 下一步行动计划

**更新时间**: 2025-12-30 21:15
**当前状态**: Phase 2进行中 (26%完成)

---

## 快速概览

### ✅ 已完成 (Phase 0-2基础)

1. **测试基础设施** - [tests/conftest.py](tests/conftest.py)
   - 延迟加载FastAPI app
   - 异步client fixture
   - 完整Mock套件
   - 环境配置

2. **详细规划文档** - 5份完整文档
   - 100%覆盖率计划 (673个测试)
   - 进度跟踪报告
   - 工作总结
   - 交付报告

3. **测试修复** - 8个测试 + 1个文件重构
   - test_tavily_search.py ✅ (6测试通过，覆盖率+18%)
   - test_content_safety.py ✅ (3个测试)
   - test_p2_features.py ✅ (3个配置验证)
   - test_analysis_endpoints.py 🟡 (重构完成，待验证)

### ⏳ 待完成 (Phase 2剩余)

**还需修复3个文件 (46个测试)**:
1. tests/api/test_session_endpoints.py (16测试)
2. tests/services/test_redis_session_manager.py (17测试)
3. tests/report/test_result_aggregator.py (13测试)

**预期覆盖率提升**: 7% → 20-25%

---

## 立即执行步骤

### Step 1: 运行已修复的测试获取基线

```bash
# 运行所有已修复的测试
python -m pytest \
  tests/test_minimal.py \
  tests/test_phase2_lite_fixed.py \
  tests/tools/test_tavily_search.py \
  tests/test_content_safety*.py \
  -v -s --cov=intelligent_project_analyzer --cov-report=html --cov-report=term

# 预期: 30-40个测试通过，覆盖率8-10%
```

### Step 2: 修复test_session_endpoints.py

**模式**: 与test_analysis_endpoints.py相同

```python
# 修改前
from intelligent_project_analyzer.api.server import app  # ❌

# 修改后
class TestSessionEndpoints:
    @pytest.mark.asyncio
    async def test_create_session(self, client, mock_redis):  # ✅
        response = await client.post("/api/session/create", json={...})
        assert response.status_code == 200
```

### Step 3: 修复test_redis_session_manager.py

**策略**: 使用conftest的mock_session_manager

```python
def test_session_manager(mock_session_manager):
    # 使用已配置的mock
    assert mock_session_manager.create.return_value == "test-session-123"
```

### Step 4: 修复test_result_aggregator.py

**策略**: 使用sample_analysis_result fixture

```python
def test_aggregator(sample_analysis_result):
    from intelligent_project_analyzer.report.result_aggregator import aggregate
    result = aggregate(sample_analysis_result)
    assert "summary" in result
```

### Step 5: 验证Phase 2完成

```bash
# 运行所有Phase 2测试
python -m pytest tests/api/ tests/tools/ tests/services/ tests/report/ \
  -v -s --cov=intelligent_project_analyzer --cov-report=html --cov-report=term

# 预期: 70个测试通过，覆盖率20-25%
```

---

## 快速参考

### 核心文件
- **配置**: [tests/conftest.py](tests/conftest.py)
- **计划**: [COVERAGE_100_PLAN.md](COVERAGE_100_PLAN.md)
- **交付**: [TESTING_DELIVERY_REPORT.md](TESTING_DELIVERY_REPORT.md)

### 常用命令
```bash
# 运行测试 (避免I/O错误)
pytest tests/ -v -s --cov=intelligent_project_analyzer --cov-report=html

# 查看HTML覆盖率
start htmlcov/index.html  # Windows
open htmlcov/index.html   # macOS

# 只运行失败的
pytest --lf -v -s
```

### Fixture使用
```python
# API测试
async def test_api(client, mock_redis):
    response = await client.get("/api/endpoint")

# 数据测试
def test_logic(sample_requirement, mock_llm):
    result = process(sample_requirement)
```

---

## Phase 2-7 时间估算

| Phase | 任务 | 测试数 | 预计时间 | 覆盖率 |
|-------|------|--------|---------|--------|
| Phase 2剩余 | 修复3个文件 | 46 | 2小时 | 7% → 20% |
| Phase 3 | Workflow测试 | 50 | 4小时 | 20% → 45% |
| Phase 4 | API Server完整 | 80 | 6小时 | 45% → 65% |
| Phase 5 | Agents测试 | 140 | 10小时 | 65% → 85% |
| Phase 6 | Services/Utils | 90 | 6小时 | 85% → 95% |
| Phase 7 | 前端+集成 | 50 | 4小时 | 95% → 100% |

**总计**: 32小时工作量，预计5-7天完成

---

## 问题与解决方案

### 问题: Pytest I/O Error
**临时方案**: 使用`-s`标志
```bash
pytest -v -s  # 禁用输出捕获
```

**永久方案**:
- 选项1: 降级到Python 3.11
- 选项2: 使用Docker容器
- 选项3: 等待pytest更新

### 问题: 测试收集失败
**检查**: 是否直接import了app
```python
# 错误
from intelligent_project_analyzer.api.server import app

# 正确
async def test_something(client):  # 使用fixture
```

---

## 成功标准

### Phase 2完成标准
- [ ] 70个Phase 2测试全部通过
- [ ] 覆盖率达到20-25%
- [ ] 无新增失败测试
- [ ] HTML报告生成成功

### 最终目标
- [ ] 673个测试全部编写
- [ ] 100%代码覆盖率
- [ ] CI/CD集成
- [ ] 所有文档完善

---

## 下次开始时

1. **检查状态**: 运行基线测试确认覆盖率
2. **选择任务**: 从test_session_endpoints.py开始
3. **参考模式**: 查看test_analysis_endpoints.py的修复模式
4. **运行验证**: 每修复一个文件立即运行测试
5. **更新文档**: 完成后更新此文件

---

**创建时间**: 2025-12-30 21:15
**下次更新**: Phase 2完成后
**联系**: 参见项目文档
