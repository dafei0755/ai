.PHONY: help test test-fast test-coverage test-unit test-integration
.PHONY: test-agents test-workflow test-interaction test-security
.PHONY: check report clean clean-test lint type-check static-check
.PHONY: lint-ruff test-api-smoke
.PHONY: frontend-lint frontend-type-check frontend-static-check
.PHONY: format security-scan
.PHONY: install-test-deps ci ci-doctor

# 默认目标
help:
	@echo "==================== 测试自动化命令 ===================="
	@echo ""
	@echo "基础测试命令:"
	@echo "  make test              - 运行所有测试"
	@echo "  make test-fast         - 快速测试(跳过慢速测试)"
	@echo "  make test-coverage     - 运行测试并生成覆盖率报告"
	@echo "  make test-unit         - 只运行单元测试"
	@echo "  make test-integration  - 只运行集成测试"
	@echo ""
	@echo "模块化测试:"
	@echo "  make test-agents       - 运行Agents模块测试"
	@echo "  make test-workflow     - 运行Workflow模块测试"
	@echo "  make test-interaction  - 运行Interaction模块测试"
	@echo "  make test-security     - 运行Security模块测试"
	@echo ""
	@echo "辅助命令:"
	@echo "  make check             - 检查测试环境前置条件"
	@echo "  make report            - 生成覆盖率报告"
	@echo "  make clean-test        - 清理测试生成的文件"
	@echo "  make lint              - 代码检查(ruff)"
	@echo "  make type-check        - 类型检查(mypy)"
	@echo "  make static-check      - 静态检查汇总(lint + type-check + security)"
	@echo "  make test-api-smoke    - API稳定回归子集"
	@echo "  make ci-doctor         - CI配置静态体检(workflow字段/门槛/关键作业)"
	@echo "  make frontend-static-check - 前端静态检查(eslint + tsc)"
	@echo "  make format            - 代码格式化(black + isort)"
	@echo "  make security-scan     - 安全扫描(bandit)"
	@echo "  make install-test-deps - 安装测试依赖"
	@echo "  make ci                - 模拟CI环境测试"
	@echo ""
	@echo "======================================================"

# 基础测试
test:
	@echo "🧪 运行所有测试..."
	python -m pytest tests/ -v

test-fast:
	@echo "⚡ 快速测试(跳过慢速测试)..."
	python -m pytest tests/ -m "not slow" -v

test-coverage:
	@echo "📊 运行覆盖率测试..."
	python -m pytest tests/ \
		--cov=intelligent_project_analyzer \
		--cov-report=html \
		--cov-report=term \
		--cov-report=json \
		-v

test-unit:
	@echo "🔬 运行单元测试..."
	python -m pytest tests/ -m unit -v

test-integration:
	@echo "🔗 运行集成测试..."
	python -m pytest tests/ -m integration -v

# 模块化测试
test-agents:
	@echo "🤖 运行Agents模块测试..."
	python -m pytest tests/agents/ -v

test-workflow:
	@echo "🔄 运行Workflow模块测试..."
	python -m pytest tests/workflow/ -v

test-interaction:
	@echo "💬 运行Interaction模块测试..."
	python -m pytest tests/interaction/ -v

test-security:
	@echo "🔒 运行Security模块测试..."
	python -m pytest tests/security/ -v

# 前置条件检查
check:
	@echo "🔍 检查测试环境..."
	@python -c "import sys; print(f'Python版本: {sys.version}')"
	@python -c "import pytest; print(f'pytest版本: {pytest.__version__}')"
	@python -c "import coverage; print(f'coverage版本: {coverage.__version__}')"
	@python scripts/test_automation.py --check

# 生成报告
report:
	@echo "📄 生成测试报告..."
	@python scripts/test_automation.py --report

# 清理测试文件
clean-test:
	@echo "🧹 清理测试文件..."
	@python scripts/test_automation.py --clean

clean: clean-test
	@echo "🧹 清理所有生成文件..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf build/ dist/ .eggs/ 2>/dev/null || true

# 代码质量
lint:
	@echo "🔍 运行代码检查..."
	@python -m ruff check intelligent_project_analyzer/api intelligent_project_analyzer/core intelligent_project_analyzer/external_data_system intelligent_project_analyzer/utils intelligent_project_analyzer/services intelligent_project_analyzer/tools tests

lint-ruff: lint
	@echo "✅ Ruff检查完成"

type-check:
	@echo "🧠 运行类型检查..."
	@python -X utf8 -m mypy --config-file mypy.ini intelligent_project_analyzer/

static-check: lint type-check security-scan
	@echo "✅ 后端静态检查完成"

test-api-smoke:
	@echo "🧪 运行API稳定回归子集..."
	@python -m pytest -q \
		tests/api/test_session_endpoints.py \
		tests/api/test_analysis_endpoints.py \
		tests/unit/api/test_output_intent_file_upload.py

frontend-lint:
	@echo "🖥️ 运行前端Lint检查..."
	@python -c "import os, subprocess, sys; d='frontend-nextjs'; sys.exit(subprocess.call(['npm','run','lint'], cwd=d) if os.path.isdir(d) else 0)"

frontend-type-check:
	@echo "🖥️ 运行前端类型检查..."
	@python -c "import os, subprocess, sys; d='frontend-nextjs'; sys.exit(subprocess.call(['npx','tsc','--noEmit','--pretty','false'], cwd=d) if os.path.isdir(d) else 0)"

frontend-static-check: frontend-lint frontend-type-check
	@echo "✅ 前端静态检查完成"

format:
	@echo "✨ 格式化代码..."
	@python -m black intelligent_project_analyzer/ tests/ --line-length=120
	@python -m isort intelligent_project_analyzer/ tests/ --profile=black

security-scan:
	@echo "🔒 运行安全扫描..."
	@python -c "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('bandit') else 1)" || (echo "❌ bandit未安装，请先执行: make install-test-deps" && exit 1)
	@python -m bandit -r intelligent_project_analyzer/ -ll -f screen

# 安装依赖
install-test-deps:
	@echo "📦 安装测试依赖..."
	@pip install -r requirements-dev.txt || pip install pytest pytest-cov pytest-asyncio pytest-mock ruff mypy bandit pre-commit types-requests

# CI模拟
ci:
	@echo "🤖 模拟CI环境测试..."
	@echo "0️⃣ CI配置体检..."
	@make ci-doctor
	@echo ""
	@echo "1️⃣ 代码检查..."
	@make lint
	@echo ""
	@echo "2️⃣ 运行API稳定回归子集..."
	@make test-api-smoke
	@echo ""
	@echo "3️⃣ 运行测试..."
	@make test-coverage
	@echo ""
	@echo "4️⃣ 安全扫描..."
	@make security-scan || true
	@echo ""
	@echo "✅ CI测试完成"

ci-doctor:
	@echo "🩺 CI配置静态体检..."
	@python scripts/ci/ci_doctor.py
