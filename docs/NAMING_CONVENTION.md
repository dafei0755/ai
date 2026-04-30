# 📏 文档命名规范

> 统一的文档命名规范，确保文档易于查找和维护

**版本**：v1.0 | **生效日期**：2025-12-29

---

## 🎯 命名原则

1. **清晰性** - 文件名应准确反映内容
2. **一致性** - 相同类型文档使用统一格式
3. **可搜索** - 使用常见关键词，避免缩写
4. **版本化** - 包含版本信息（如适用）

---

## 📝 命名格式规范

### 1. 架构设计文档

**格式**：`[模块名]_ARCHITECTURE.md`

**示例**：
- ✅ `AGENT_ARCHITECTURE.md`
- ✅ `WORKFLOW_ARCHITECTURE.md`
- ❌ `arch.md`（太简略）
- ❌ `系统架构.md`（使用英文）

### 2. 功能实现文档

**格式**：`feature_[功能名]_implementation.md`

**示例**：
- ✅ `feature_chat_mode_implementation.md`
- ✅ `feature_session_archive_implementation.md`
- ❌ `chat功能.md`（中英混杂）
- ❌ `new_feature.md`（不明确）

### 3. Bug 修复文档

**格式**：`bugfix_[问题描述]_[YYYYMMDD].md`（临时）

**归档后**：移动到 `docs/archive/bugfixes/v[版本]/`

**示例**：
- ✅ `bugfix_empty_report_20251129.md`
- ✅ `bugfix_frontend_sync_20251130.md`
- ❌ `fix.md`（不明确）
- ❌ `修复报告为空.md`（使用英文）

### 4. 版本升级文档

**格式**：`V[版本号]_[主要特性]_[类型].md`

**类型**：
- `ARCHITECTURE` - 架构升级
- `UPGRADE` - 功能升级
- `SUMMARY` - 升级总结
- `GUIDE` - 使用指南

**示例**：
- ✅ `V716_AGENT_STATE_GRAPHS.md`
- ✅ `V718_COMPREHENSIVE_UPGRADE_SUMMARY.md`
- ✅ `V15_USER_GUIDE.md`
- ❌ `v7更新.md`（格式不规范）

### 5. 部署与配置文档

**格式**：`[服务名]_[类型]_[说明].md`

**类型**：
- `SETUP` - 初始配置
- `DEPLOYMENT` - 部署指南
- `CONFIGURATION` - 配置说明

**示例**：
- ✅ `redis_persistence_setup.md`
- ✅ `SECURITY_SETUP_GUIDE.md`
- ✅ `DEPLOYMENT.md`
- ❌ `配置.md`（不明确）

### 6. 集成文档

**格式**：`[系统名]_INTEGRATION_GUIDE.md`

**示例**：
- ✅ `WORDPRESS_INTEGRATION_GUIDE.md`
- ✅ `SSO_SYNC_DUAL_MECHANISM_V3.0.21.md`
- ❌ `wp集成.md`（缩写不清晰）

### 7. 调查与分析文档

**格式**：`[主题]_investigation.md` 或 `[主题]_analysis.md`

**示例**：
- ✅ `session_storage_investigation.md`
- ✅ `role_review_analysis.md`
- ❌ `调查报告.md`（不明确）

### 8. 测试文档

**格式**：`[功能]_test_[类型].md`

**类型**：
- `plan` - 测试计划
- `report` - 测试报告
- `guide` - 测试指南

**示例**：
- ✅ `role_review_test_plan.md`
- ✅ `multimodal_integration_test_report.md`
- ❌ `测试.md`（不明确）

### 9. 指南类文档

**格式**：`[主题]_[类型]_GUIDE.md`

**类型**：
- `QUICK_START` - 快速开始
- `SETUP` - 设置指南
- `TROUBLESHOOTING` - 故障排查
- `USAGE` - 使用指南

**示例**：
- ✅ `GRAFANA_QUICK_START.md`
- ✅ `SSO_SYNC_TROUBLESHOOTING_GUIDE.md`
- ✅ `multimodal_usage_guide.md`
- ❌ `指南.md`（不明确）

---

## 📂 目录组织规范

### 主目录结构

```
docs/
├── README.md                      # 文档索引（必需）
├── NAMING_CONVENTION.md           # 本文件
├── [架构文档].md                  # 架构设计文档
├── [部署文档].md                  # 部署配置文档
├── [功能文档].md                  # 功能实现文档
├── archive/                       # 历史归档
│   ├── bugfixes/                  # Bug修复归档
│   │   ├── v7.x/                  # 按版本分类
│   │   └── v3.0.x/
│   └── versions/                  # 版本迭代归档
├── guides/                        # 指南类文档
├── testing/                       # 测试文档
└── wordpress/                     # WordPress专项文档
```

### 归档规则

**触发条件**：
- Bug 已修复且验证通过
- 版本已过时（超过2个主版本）
- 临时文档（如调查分析）完成后

**归档目标**：
- `docs/archive/bugfixes/[版本]/` - Bug修复
- `docs/archive/versions/` - 版本迭代
- `docs/archive/investigations/` - 调查分析

---

## ✅ 检查清单

创建新文档前，请确认：

- [ ] 文件名遵循对应类型的命名格式
- [ ] 使用英文命名（允许下划线分隔）
- [ ] 避免使用缩写（除非是广为人知的如 SSO、API）
- [ ] 包含版本号（如适用）
- [ ] 包含日期（临时文档如 bugfix）
- [ ] 放置在合适的目录
- [ ] 在 `docs/README.md` 中添加索引

---

## 🔄 重命名现有文档

如发现不符合规范的文档：

1. **评估影响** - 检查是否被其他文档引用
2. **创建别名** - 在新位置创建文档，旧位置保留重定向说明
3. **更新索引** - 修改 `docs/README.md`
4. **通知团队** - 在 PR 中说明重命名原因

**重定向文档示例**：
```markdown
# 此文档已移动

本文档已移动到新位置：[新文档名称](新路径.md)

**移动原因**：统一命名规范  
**移动日期**：2025-12-29

请更新您的书签！
```

---

## 📊 常见问题

### Q1：临时文档何时归档？
**A**：问题修复后立即归档到 `docs/archive/bugfixes/[版本]/`

### Q2：中英文如何选择？
**A**：文件名统一使用英文，内容可以是中文

### Q3：版本号格式？
**A**：主版本使用 `V[数字]`（如 V716），子版本使用 `v[语义化版本]`（如 v3.0.21）

### Q4：文档太长怎么办？
**A**：考虑拆分为多个文档，使用索引页面串联

---

## 🔗 相关资源

- [文档索引](README.md)
- [贡献指南](../README.md#贡献指南)
- [开发规范](../.github/DEVELOPMENT_RULES_CORE.md)

---

**维护者**：开发团队 | **最后更新**：2025-12-29
