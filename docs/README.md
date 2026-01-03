# 📚 文档导航

> Intelligent Project Analyzer 完整文档索引

---

## 🗂️ 文档结构

```
docs/
├── getting-started/        # 入门指南
├── architecture/          # 架构设计
├── deployment/            # 部署运维
├── features/              # 功能文档
├── development/           # 开发指南
├── releases/              # 版本发布
└── archive/               # 历史归档
```

---

## 🚀 入门指南

| 文档 | 说明 |
|------|------|
| [QUICKSTART.md](../QUICKSTART.md) | 5分钟快速启动（根目录） |
| [getting-started/INSTALLATION.md](getting-started/INSTALLATION.md) | 详细安装教程 |
| [getting-started/CONFIGURATION.md](getting-started/CONFIGURATION.md) | 环境配置指南 |
| [getting-started/FAQ.md](getting-started/FAQ.md) | 常见问题解答 |

---

## 🏗️ 架构设计

| 文档 | 说明 |
|------|------|
| [AGENT_ARCHITECTURE.md](AGENT_ARCHITECTURE.md) | 多智能体架构设计 |
| [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) | 项目结构说明 |
| [V716_AGENT_STATE_GRAPHS.md](V716_AGENT_STATE_GRAPHS.md) | LangGraph StateGraph架构（v7.16+） |
| [WORKFLOW_DESIGN.md](WORKFLOW_DESIGN.md) | 工作流设计 |
| [MODE_CONFIG_OPTIMIZATION_SUMMARY.md](MODE_CONFIG_OPTIMIZATION_SUMMARY.md) | 分析模式配置优化总结（v7.110） 🆕 |

---

## 🚢 部署运维

| 文档 | 说明 |
|------|------|
| [DEPLOYMENT.md](DEPLOYMENT.md) | 生产环境部署指南 |
| [SECURITY_SETUP_GUIDE.md](SECURITY_SETUP_GUIDE.md) | 安全配置指南 |
| [../BACKUP_GUIDE.md](../BACKUP_GUIDE.md) | 备份策略（根目录） |
| [../LOGGING_GUIDE.md](../LOGGING_GUIDE.md) | 日志管理（根目录） |
| [../EMERGENCY_RECOVERY.md](../EMERGENCY_RECOVERY.md) | 紧急恢复（根目录） |

---

## 🎯 功能文档

### 分析模式

| 文档 | 说明 |
|------|------|
| [MODE_CONFIG_OPTIMIZATION_SUMMARY.md](MODE_CONFIG_OPTIMIZATION_SUMMARY.md) | 普通模式 vs 深度思考模式配置管理 🆕 |

### WordPress SSO 集成

| 文档 | 说明 |
|------|------|
| [features/wordpress-sso/](features/wordpress-sso/) | WordPress SSO完整文档 |

### 问卷系统

| 文档 | 说明 |
|------|------|
| [questionnaire_task_optimization_summary.md](questionnaire_task_optimization_summary.md) | 问卷任务分配优化实施总结 🆕 |
| [questionnaire_optimization_test_guide.md](questionnaire_optimization_test_guide.md) | 问卷优化测试指南 🆕 |
| [archive/bugfixes/questionnaire/](archive/bugfixes/questionnaire/) | 问卷系统修复记录 |

### 搜索工具

| 文档 | 说明 |
|------|------|
| [V7.120_SEARCH_REFERENCES_RELEASE.md](V7.120_SEARCH_REFERENCES_RELEASE.md) | v7.120 搜索引用功能发布 |
| [V7.121_SEARCH_QUERY_DATA_UTILIZATION.md](V7.121_SEARCH_QUERY_DATA_UTILIZATION.md) | v7.121 搜索查询数据利用优化 🆕 |
| [archive/bugfixes/search/](archive/bugfixes/search/) | 搜索工具历史修复记录 |

---

## 💻 开发指南

| 文档 | 说明 |
|------|------|
| [../CONTRIBUTING.md](../CONTRIBUTING.md) | 贡献指南（根目录） |
| [../.github/DEVELOPMENT_RULES_CORE.md](../.github/DEVELOPMENT_RULES_CORE.md) | 核心开发规范（200行） |
| [../.github/DEVELOPMENT_RULES.md](../.github/DEVELOPMENT_RULES.md) | 完整开发规范 |
| [../.github/PRE_CHANGE_CHECKLIST.md](../.github/PRE_CHANGE_CHECKLIST.md) | 变更检查清单 |
| [API.md](API.md) | API 文档 |
| [development/testing/](development/testing/) | 测试指南 |
| [../README_TESTING.md](../README_TESTING.md) | 测试概览（根目录） |

---

## 📖 历史修复案例

**精选案例** (位于 `.github/historical_fixes/`)：

1. ⭐ [问卷第三步上下文感知修复 (v7.107.1)](../.github/historical_fixes/step3_llm_context_awareness_fix_v7107.1.md)
2. [雷达图维度混合策略 (v7.105)](../.github/historical_fixes/dimension_hybrid_strategy_implementation.md)
3. [Playwright Python 3.13 修复](../.github/historical_fixes/playwright_python313_windows_fix.md)
4. [问卷用户输入显示修复](../.github/historical_fixes/questionnaire_user_input_display_fix.md)
5. [会话删除权限修复](../.github/historical_fixes/session_delete_permission_fix.md)

**归档案例** (位于 `docs/archive/bugfixes/`)：

- [问卷系统修复记录](archive/bugfixes/questionnaire/)
- [搜索工具修复记录](archive/bugfixes/search/)
- [前端修复记录](archive/bugfixes/frontend/)
- [后端修复记录](archive/bugfixes/backend/)

---

## 📦 版本发布

| 文档 | 说明 |
|------|------|
| [../CHANGELOG.md](../CHANGELOG.md) | 完整更新日志（根目录） |
| [archive/versions/](archive/versions/) | 历史版本归档 |

---

## 🗄️ 历史归档

| 目录 | 说明 |
|------|------|
| [archive/phases/](archive/phases/) | 项目阶段报告 |
| [archive/bugfixes/](archive/bugfixes/) | 临时修复记录（按功能分类） |
| [archive/versions/](archive/versions/) | 历史版本文档 |

---

## 🔧 配置文件文档

| 位置 | 说明 |
|------|------|
| `intelligent_project_analyzer/config/roles/` | 专家角色配置 |
| `intelligent_project_analyzer/config/prompts/` | Prompt模板（Git版本控制） |

---

## 📝 文档维护规范

**新增文档位置规则**：

| 文档类型 | 位置 |
|---------|------|
| 入门教程 | `docs/getting-started/` |
| 架构设计 | `docs/architecture/` |
| 功能文档 | `docs/features/{feature}/` |
| 修复记录 | `docs/archive/bugfixes/{category}/` |
| 开发规范 | `.github/` |
| 核心文档 | 根目录 |

**⚠️ 禁止在根目录创建新的 .md 文档（核心文档除外）**

**详细规范**: [../.github/DOCUMENTATION_RULES.md](../.github/DOCUMENTATION_RULES.md)

---

## 🔍 快速查找

- **快速启动** → [QUICKSTART.md](../QUICKSTART.md)
- **贡献代码** → [CONTRIBUTING.md](../CONTRIBUTING.md)
- **系统架构** → [architecture/](architecture/)
- **API 接口** → [API.md](API.md)
- **生产部署** → [DEPLOYMENT.md](DEPLOYMENT.md)
- **WordPress SSO** → [features/wordpress-sso/](features/wordpress-sso/)
- **测试指南** → [development/testing/](development/testing/)
- **历史案例** → [../.github/historical_fixes/](../.github/historical_fixes/)
- **紧急恢复** → [EMERGENCY_RECOVERY.md](../EMERGENCY_RECOVERY.md)

---

**最后更新**: 2026-01-03 | **文档版本**: v2.1
