# 测试自动化完整使用指南

## 📋 目录

- [概述](#概述)
- [快速开始](#快速开始)
- [测试命令详解](#测试命令详解)
- [配置说明](#配置说明)
- [测试数据工厂](#测试数据工厂)
- [Pre-commit钩子](#pre-commit钩子)
- [CI/CD集成](#cicd集成)
- [覆盖率报告](#覆盖率报告)
- [最佳实践](#最佳实践)
- [故障排除](#故障排除)

---

## 概述

本项目实现了全面的测试自动化系统，包括：

- ✅ 跨平台测试脚本 (Windows/Linux/Mac)
- ✅ pytest配置和标记系统
- ✅ 自动化覆盖率报告生成
- ✅ Pre-commit代码质量检查
- ✅ GitHub Actions CI/CD
- ✅ 测试数据工厂模式
- ✅ 多维度测试分类

---

## 快速开始

### 1. 安装测试依赖

```bash
pip install pytest pytest-cov pytest-asyncio pytest-mock
```

或使用Makefile:
```bash
make install-test-deps
```

### 2. 检查环境

**Windows:**
```cmd
test.bat check
```

**Linux/Mac:**
```bash
make check
```

**跨平台:**
```bash
python scripts/test_automation.py --check
```

### 3. 运行测试

**Windows:**
```cmd
test.bat test
```

**Linux/Mac:**
```bash
make test
```

**跨平台:**
```bash
python scripts/test_automation.py --mode all
```

---

## 测试命令详解

### 基础测试命令

#### 运行所有测试
```bash
# Windows
test.bat test

# Linux/Mac
make test

# 跨平台
python -m pytest tests/ -v
```

#### 快速测试（跳过慢速测试）
```bash
# Windows
test.bat test-fast

# Linux/Mac
make test-fast

# 跨平台
python -m pytest tests/ -m "not slow" -v
```

#### 覆盖率测试
```bash
# Windows
test.bat test-coverage

# Linux/Mac
make test-coverage

# 跨平台
python -m pytest tests/ --cov=intelligent_project_analyzer --cov-report=html -v
```

### 模块化测试

#### Agents模块
```bash
# Windows
test.bat test-agents

# Linux/Mac
make test-agents

# 跨平台
python -m pytest tests/agents/ -v
```

#### Workflow模块
```bash
# Windows
test.bat test-workflow

# Linux/Mac
make test-workflow

# 跨平台
python -m pytest tests/workflow/ -v
```

#### Interaction模块
```bash
# Windows
test.bat test-interaction

# Linux/Mac
make test-interaction

# 跨平台
python -m pytest tests/interaction/ -v
```

#### Security模块
```bash
# Windows
test.bat test-security

# Linux/Mac
make test-security

# 跨平台
python -m pytest tests/security/ -v
```

### 测试标记

使用pytest标记运行特定类型的测试:

```bash
# 只运行单元测试
pytest tests/ -m unit

# 只运行集成测试
pytest tests/ -m integration

# 跳过慢速测试
pytest tests/ -m "not slow"

# 运行安全测试
pytest tests/ -m security

# 组合标记
pytest tests/ -m "unit and not slow"
```

---

## 配置说明

### pytest.ini

主要配置项:

```ini
[pytest]
# 测试搜索路径
testpaths = tests

# 测试文件命名模式
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# 测试标记
markers =
    unit: 单元测试
    integration: 集成测试
    slow: 慢速测试
    security: 安全测试
    agents: Agent模块测试
    workflow: Workflow模块测试
    interaction: Interaction模块测试
```

### 覆盖率配置

```ini
[coverage:run]
source = intelligent_project_analyzer
omit = */tests/*, */frontend/*

[coverage:report]
show_missing = True
precision = 2
```

---

## 测试数据工厂

使用`TestDataFactory`创建标准化测试数据。

### 基本用法

```python
from tests.fixtures import test_state, complete_state, mock_llm

def test_something(env_setup):
    # 创建基本状态
    state = test_state(
        user_input="咖啡馆设计",
        project_type="interior_design"
    )

    # 创建完整状态
    full_state = complete_state(
        user_input="咖啡馆设计",
        agents=["expert1", "expert2"],
        agent_results={"expert1": "结果1"}
    )

    # 创建Mock LLM
    llm = mock_llm("测试响应")
    result = llm.invoke({"input": "test"})
    assert result.content == "测试响应"
```

### 可用方法

#### 1. test_state(**kwargs)
创建基本测试状态:
```python
state = test_state(
    session_id="custom-id",
    user_input="我的项目",
    project_type="web_app"
)
```

#### 2. complete_state(**kwargs)
创建完整状态（包含所有字段）:
```python
state = complete_state(
    user_input="完整项目",
    agents=["agent1", "agent2"],
    agent_results={"agent1": "分析结果"}
)
```

#### 3. mock_llm(content)
创建Mock LLM对象:
```python
llm = mock_llm("LLM响应内容")
response = llm.invoke({"input": "测试"})
assert response.content == "LLM响应内容"
```

#### 4. structured_requirements(**kwargs)
创建结构化需求:
```python
reqs = structured_requirements(
    project_name="我的项目",
    project_type="web_application",
    key_features=["功能1", "功能2"]
)
```

---

## Pre-commit钩子

### 安装

```bash
pip install pre-commit
pre-commit install
```

### 功能

每次commit时自动执行:

1. ✅ **文件检查**
   - 删除尾随空格
   - 检查YAML/JSON语法
   - 检测私钥
   - 检查大文件

2. ✅ **代码格式化**
   - Black格式化
   - isort排序import

3. ✅ **代码检查**
   - flake8代码质量检查

4. ✅ **快速测试**
   - 运行快速测试（跳过慢速测试）

### 手动运行

```bash
# 对所有文件运行
pre-commit run --all-files

# 只运行特定钩子
pre-commit run black --all-files
```

### 临时跳过

```bash
# 跳过所有钩子
git commit --no-verify

# 或设置环境变量
SKIP=pytest-check git commit
```

---

## CI/CD集成

### GitHub Actions

工作流配置在 `.github/workflows/tests.yml`

#### 触发条件
- Push到main/develop分支
- Pull Request
- 每天定时运行 (UTC 0:00)
- 手动触发

#### 测试矩阵
- **操作系统**: Ubuntu, Windows
- **Python版本**: 3.9, 3.10, 3.11

#### 工作流包括
1. **测试执行**
   - 运行所有测试
   - 生成覆盖率报告
   - 上传到Codecov

2. **代码质量**
   - Black格式检查
   - isort排序检查
   - flake8代码检查

3. **安全扫描**
   - Bandit安全扫描
   - Safety依赖检查

---

## 覆盖率报告

### 生成报告

```bash
# Windows
test.bat test-coverage
test.bat report

# Linux/Mac
make test-coverage
make report

# 跨平台
python scripts/test_automation.py --mode coverage
python scripts/test_automation.py --report
```

### 报告格式

1. **HTML报告**
   - 位置: `htmlcov/index.html`
   - 在浏览器中打开查看详细覆盖率

2. **终端报告**
   - 运行测试时直接显示
   - 显示总体覆盖率和缺失行

3. **JSON报告**
   - 位置: `coverage.json`
   - 用于程序化处理

4. **Markdown报告**
   - 位置: `test_reports/coverage_report_YYYYMMDD.md`
   - 包含详细的模块覆盖率表格

### 覆盖率目标

- **当前**: 14%
- **Phase 6目标**: 20%
- **最终目标**: 60%+

---

## 最佳实践

### 开发工作流

1. **开发前**: 运行 `make check` 或 `test.bat check`
2. **开发中**: 运行 `make test-fast` 快速验证
3. **提交前**: 运行 `make test-coverage` 完整测试
4. **Push前**: 确保CI通过

### 测试编写

1. ✅ 使用`TestDataFactory`创建测试数据
2. ✅ 为测试添加适当的标记（unit, integration, slow等）
3. ✅ 慢速测试标记为`@pytest.mark.slow`
4. ✅ 保持测试独立，不依赖执行顺序
5. ✅ 使用描述性的测试名称
6. ✅ 添加文档字符串说明测试目的

### 测试组织

```python
import pytest
from tests.fixtures import test_state, mock_llm


class TestMyFeature:
    """测试我的功能"""

    @pytest.mark.unit
    def test_basic_functionality(self, env_setup):
        """测试基本功能"""
        state = test_state(user_input="测试")
        # 测试逻辑...

    @pytest.mark.integration
    @pytest.mark.slow
    def test_full_workflow(self, env_setup):
        """测试完整工作流"""
        # 测试逻辑...
```

---

## 故障排除

### 测试失败

```bash
# 1. 检查环境
test.bat check  # Windows
make check      # Linux/Mac

# 2. 清理缓存
test.bat clean  # Windows
make clean-test # Linux/Mac

# 3. 重新安装依赖
pip install -r requirements-dev.txt

# 4. 重新运行
test.bat test   # Windows
make test       # Linux/Mac
```

### 编码错误 (Windows)

脚本已包含UTF-8编码修复，如仍有问题:

```cmd
# 方法1: 切换到UTF-8
chcp 65001

# 方法2: 使用Python脚本
python scripts/test_automation.py --check
```

### Pre-commit失败

```bash
# 查看哪个钩子失败
pre-commit run --all-files

# 自动修复格式问题
black intelligent_project_analyzer/ tests/
isort intelligent_project_analyzer/ tests/

# 临时跳过
git commit --no-verify
```

### CI/CD失败

1. **本地模拟CI环境**:
   ```bash
   make ci  # Linux/Mac
   ```

2. **检查特定Python版本**:
   ```bash
   pyenv install 3.9.0
   pyenv local 3.9.0
   make test
   ```

3. **查看GitHub Actions日志**:
   - 访问仓库的Actions标签页
   - 点击失败的工作流
   - 查看详细日志

---

## 高级用法

### 并行测试

```bash
# 安装pytest-xdist
pip install pytest-xdist

# 使用多个CPU核心运行
pytest tests/ -n auto
```

### 生成测试报告

```bash
# 安装pytest-html
pip install pytest-html

# 生成HTML测试报告
pytest tests/ --html=test_reports/report.html
```

### 性能分析

```bash
# 安装pytest-benchmark
pip install pytest-benchmark

# 运行性能测试
pytest tests/ --benchmark-only
```

---

## 相关资源

- [pytest官方文档](https://docs.pytest.org/)
- [pytest-cov文档](https://pytest-cov.readthedocs.io/)
- [pre-commit文档](https://pre-commit.com/)
- [GitHub Actions文档](https://docs.github.com/actions)
- [Black文档](https://black.readthedocs.io/)
- [Codecov文档](https://docs.codecov.com/)

---

## 支持

如有问题或建议，请:
- 查看本文档的[故障排除](#故障排除)部分
- 查看项目的GitHub Issues
- 联系开发团队

---

**最后更新**: 2025-12-31
**版本**: 1.0.0
