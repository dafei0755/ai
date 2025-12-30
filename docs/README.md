# 📚 项目文档导航

> 快速找到您需要的文档 - 最后更新：2025-12-29

---

## 🔥 快速入口

### 新手必读
1. **[项目 README](../README.md)** - 项目简介、快速启动
2. **[核心开发规范](../.github/DEVELOPMENT_RULES_CORE.md)** - 200行精简版，AI工具优先
3. **[完整开发规范](../.github/DEVELOPMENT_RULES.md)** - 深度查阅
4. **[变更检查清单](../.github/PRE_CHANGE_CHECKLIST.md)** - 修改前强制流程

### 常用文档
- 🏗️ [项目架构](AGENT_ARCHITECTURE.md) - 系统架构总览
- 📖 [API 文档](../CLAUDE.md) - Claude Code 工作指南
- 🚀 [部署指南](DEPLOYMENT.md) - 生产环境部署
- 🔐 [安全配置](SECURITY_SETUP_GUIDE.md) - 安全设置指南
- 📊 [日志系统](LOGGING_ADVANCED_FEATURES.md) - 高级日志功能

---

## 📁 文档分类导航

### 🏗️ 架构与设计
| 文档 | 描述 | 更新时间 |
|------|------|----------|
| [AGENT_ARCHITECTURE.md](AGENT_ARCHITECTURE.md) | LangGraph 多智能体架构 | 2025-12 |
| [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) | 项目目录结构说明 | 2025-12 |
| [DYNAMIC_EXPERT_MECHANISM_REVIEW.md](DYNAMIC_EXPERT_MECHANISM_REVIEW.md) | 动态专家机制 | 2025-11 |

### 🚀 部署与运维
| 文档 | 描述 | 更新时间 |
|------|------|----------|
| [DEPLOYMENT.md](DEPLOYMENT.md) | 生产环境部署指南 | 2025-12 |
| [SECURITY_SETUP_GUIDE.md](SECURITY_SETUP_GUIDE.md) | 安全配置指南 | 2025-11 |
| [redis_persistence_setup.md](redis_persistence_setup.md) | Redis 持久化配置 | 2025-11 |
| [GRAFANA_QUICK_START.md](GRAFANA_QUICK_START.md) | Grafana 监控快速开始 | 2025-11 |
| [LOKI_SETUP_GUIDE.md](LOKI_SETUP_GUIDE.md) | Loki 日志系统设置 | 2025-11 |

### 🔐 WordPress SSO 集成
| 文档 | 描述 | 更新时间 |
|------|------|----------|
| [WORDPRESS_INTEGRATION_GUIDE.md](WORDPRESS_INTEGRATION_GUIDE.md) | 综合集成指南 | 2025-12 |
| [SSO_SYNC_DUAL_MECHANISM_V3.0.21.md](SSO_SYNC_DUAL_MECHANISM_V3.0.21.md) | 双机制同步方案 ⭐ | 2025-12 |
| [SSO_SYNC_TROUBLESHOOTING_GUIDE.md](SSO_SYNC_TROUBLESHOOTING_GUIDE.md) | 故障排查指南 | 2025-12 |
| [wordpress/](wordpress/) | WordPress 技术文档目录 | - |

### 📊 日志与监控
| 文档 | 描述 | 更新时间 |
|------|------|----------|
| [LOGGING_ADVANCED_FEATURES.md](LOGGING_ADVANCED_FEATURES.md) | 高级日志功能 | 2025-12 |
| [LOGGING_VERIFICATION_GUIDE.md](LOGGING_VERIFICATION_GUIDE.md) | 日志验证指南 | 2025-12 |
| [../LOGGING_GUIDE.md](../LOGGING_GUIDE.md) | 日志系统使用指南 | 2025-12 |

### 🎨 多模态与扩展功能
| 文档 | 描述 | 更新时间 |
|------|------|----------|
| [multimodal_usage_guide.md](multimodal_usage_guide.md) | 多模态使用指南 | 2025-11 |
| [multimodal_input_implementation.md](multimodal_input_implementation.md) | 多模态实现细节 | 2025-11 |
| [vision_api_final_summary.md](vision_api_final_summary.md) | Vision API 总结 | 2025-11 |
| [openrouter_load_balancer_guide.md](openrouter_load_balancer_guide.md) | OpenRouter 负载均衡 | 2025-11 |

### 📦 功能实现文档
| 文档 | 描述 | 更新时间 |
|------|------|----------|
| [feature_chat_mode_implementation.md](feature_chat_mode_implementation.md) | 聊天模式实现 | 2025-11 |
| [session_archive_feature.md](session_archive_feature.md) | 会话归档功能 | 2025-11 |
| [RESULT_PRESENTATION_REDESIGN.md](RESULT_PRESENTATION_REDESIGN.md) | 结果展示重设计 | 2025-11 |
| [QUESTIONNAIRE_GENERATION_LOGIC_AND_HISTORY.md](QUESTIONNAIRE_GENERATION_LOGIC_AND_HISTORY.md) | 问卷生成逻辑 | 2025-11 |

### 🧪 测试文档
| 文档 | 描述 | 更新时间 |
|------|------|----------|
| [role_review_test_plan.md](role_review_test_plan.md) | 角色审核测试计划 | 2025-11 |
| [multimodal_integration_test_report.md](multimodal_integration_test_report.md) | 多模态集成测试 | 2025-11 |

---

## 📂 历史归档

### 🗂️ 归档目录结构
```
docs/archive/
├── bugfixes/          # 临时修复文档归档
│   ├── v7.x/          # v7.x 版本修复
│   └── v3.0.x/        # v3.0.x 版本修复
└── versions/          # 版本迭代文档归档
    ├── V716_*         # v7.16 相关
    ├── V718_*         # v7.18 相关
    └── V15_*          # v1.5 相关
```

### 🔍 归档文档说明
- **bugfixes/** - 已修复的临时问题文档，按版本分类
- **versions/** - 历史版本的架构升级文档
- 📝 归档文档仍可访问，但不在主导航中显示

---

## 🔍 快速搜索指南

### 按关键词搜索
```bash
# Windows PowerShell
Get-ChildItem -Path docs -Filter "*.md" -Recurse | Select-String "关键词"

# 搜索示例
Get-ChildItem -Path docs -Filter "*.md" -Recurse | Select-String "SSO"
Get-ChildItem -Path docs -Filter "*.md" -Recurse | Select-String "日志"
```

### 按文档类型
- 架构文档：`*ARCHITECTURE*.md`
- 部署文档：`*DEPLOYMENT*.md`, `*SETUP*.md`
- 修复文档：`archive/bugfixes/`
- 版本文档：`archive/versions/`
- WordPress：`wordpress/*.md`, `SSO_*.md`

---

## 📏 文档命名规范

详见 [NAMING_CONVENTION.md](NAMING_CONVENTION.md)

---

## 🤝 贡献新文档

1. 按功能分类选择合适目录
2. 遵循命名规范（见上方链接）
3. 在本 README.md 的对应分类中添加索引
4. 提交 PR 时附上文档摘要

---

## 📊 文档统计

- **总文档数**：~200 个（已优化，2025-12-29）
- **核心文档**：~30 个
- **归档文档**：~100+ 个
- **最后清理**：2025-12-29

---

**维护者**：开发团队 | **最后更新**：2025-12-29
