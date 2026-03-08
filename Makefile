.PHONY: help test test-fast test-coverage test-unit test-integration
.PHONY: test-agents test-workflow test-interaction test-security
.PHONY: check report clean clean-test lint format type-check security-scan
.PHONY: install-test-deps ci

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
	@echo "  make check             - 代码质量全量检查 (lint + type-check)"
	@echo "  make report            - 生成覆盖率报告"
	@echo "  make clean-test        - 清理测试生成的文件"
	@echo "  make lint              - 代码检查 (ruff check)"
	@echo "  make format            - 代码格式化 (ruff format + fix)"
	@echo "  make type-check        - 类型检查 (mypy)"
	@echo "  make security-scan     - 安全扫描 (bandit)"
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
	@echo "🔍 ST-4: 代码质量全量检查 (lint + type-check)..."
	@$(MAKE) lint
	@$(MAKE) type-check

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

# 代码质量 (ST-4: 已替换为 ruff)
lint:
	@echo "🔍 运行 ruff 代码检查..."
	@python -m ruff check intelligent_project_analyzer/ --statistics

format:
	@echo "✨ 运行 ruff 格式化..."
	@python -m ruff format intelligent_project_analyzer/
	@python -m ruff check intelligent_project_analyzer/ --fix --unsafe-fixes

type-check:
	@echo "🧠 运行 mypy 类型检查..."
	@python -m mypy --config-file mypy.ini

security-scan:
	@echo "🔒 运行安全扫描..."
	@python -m bandit -r intelligent_project_analyzer/ -ll -f screen

# 安装依赖
install-test-deps:
	@echo "📦 安装测试依赖..."
	@pip install -r requirements-dev.txt || pip install pytest pytest-cov pytest-asyncio pytest-mock

# CI模拟
ci:
	@echo "🤖 模拟CI环境测试..."
	@echo "1️⃣ 代码检查..."
	@make lint || true
	@echo ""
	@echo "2️⃣ 运行测试..."
	@make test-coverage
	@echo ""
	@echo "3️⃣ 安全扫描..."
	@make security-scan || true
	@echo ""
	@echo "✅ CI测试完成"
