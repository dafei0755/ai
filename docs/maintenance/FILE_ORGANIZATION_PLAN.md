# 根目录文件整理方案

**整理日期**: 2025-12-10
**当前状态**: 根目录有86个Markdown文件，需要分类整理
**目标**: 保持根目录干净，只保留核心文档

---

## 📊 当前状态

### 根目录文件统计
```
总计: 86个Markdown文件
- PHASE1_*.md: 15个
- PHASE2_*.md: 11个
- PHASE3_*.md: 6个
- V*_UPDATED_SYSTEM_PROMPT.md: 24个
- BACKUP_*.md: 2个
- 其他: 28个
```

---

## 📁 整理方案

### 1. 保留在根目录（核心文档）
```
✅ README.md                        # 项目主文档
✅ CLAUDE.md                        # Claude Code工作指南
✅ BACKUP_20251210_SUMMARY.md      # 最新备份总结
✅ FRONTEND_MISSING_CONTENT_FIX.md # 最新修复文档
```

### 2. 移动到 docs/archives/（历史文档）
已经移动的38个文档保持不变

### 3. 新建目录结构

#### docs/phase1/ - Phase 1相关文档（15个）
```
PHASE1_1_BOUNDARY_CORRECTION.md
PHASE1_2_REVIEW_ALIGNMENT.md
PHASE1_3_ANTI_PATTERN_ENFORCEMENT.md
PHASE1_3_P1_IMPLEMENTATION.md
PHASE1_3_QUICK_REFERENCE.md
PHASE1_4_PERFORMANCE_OPTIMIZATION.md
PHASE1_4_PLUS_FRONTEND_FIXES.md
PHASE1_4_PLUS_P3_P4_P5_COMPLETION.md
PHASE1_COMPLETION_SUMMARY.md
phase1_open_framework_summary.md
PHASE1_OPTIMIZATION_SUMMARY.md
PHASE1_QUICK_REFERENCE.md
PHASE1_TEST_FINAL_REPORT.md
PHASE1_TEST_INTERIM_REPORT.md
PHASE1_V6_1_PILOT_COMPLETION_SUMMARY.md
PHASE_1_5_CUSTOM_ANALYSIS_PRIORITY_FIX.md
```

#### docs/phase2/ - Phase 2相关文档（11个）
```
PHASE2_COMPLETE_FINAL_SUMMARY.md
PHASE2_FINAL_PROGRESS_REPORT.md
PHASE2_FINAL_SPRINT_PLAN.md
PHASE2_P0_COMPLETE_ALL_SUMMARY.md
PHASE2_P0_COMPLETION_SUMMARY.md
PHASE2_P1_COMPLETION_SUMMARY.md
PHASE2_P1_V5_1_PROGRESS.md
PHASE2_P3_COMPLETION_SUMMARY.md
PHASE2_PROGRESS_REPORT.md
PHASE2_UNIFIED_ARCHITECTURE_IMPLEMENTATION_PLAN.md
PHASE2_V6_2_COMPLETION_SUMMARY.md
```

#### docs/phase3/ - Phase 3相关文档（6个）
```
PHASE3_BATCH1_V6_COMPLETION.md
PHASE3_BATCH2_V5_COMPLETION.md
PHASE3_BATCH3_V2_COMPLETION.md
PHASE3_BATCH4_V3_V4_COMPLETION.md
PHASE3_COMPLETE_FINAL_SUMMARY.md
PHASE3_TESTING_PLAN.md
```

#### docs/prompts/ - 系统提示词文档（24个）
```
V2_0_UPDATED_SYSTEM_PROMPT.md
V2_1_UPDATED_SYSTEM_PROMPT.md
V2_2_UPDATED_SYSTEM_PROMPT.md
V2_3_UPDATED_SYSTEM_PROMPT.md
V2_4_UPDATED_SYSTEM_PROMPT.md
V2_5_UPDATED_SYSTEM_PROMPT.md
V2_6_UPDATED_SYSTEM_PROMPT.md
V3_1_UPDATED_SYSTEM_PROMPT.md
V3_2_UPDATED_SYSTEM_PROMPT.md
V3_3_UPDATED_SYSTEM_PROMPT.md
V4_1_UPDATED_SYSTEM_PROMPT.md
V4_2_UPDATED_SYSTEM_PROMPT.md
V5_0_UPDATED_SYSTEM_PROMPT.md
V5_1_UPDATED_SYSTEM_PROMPT.md
V5_2_UPDATED_SYSTEM_PROMPT.md
V5_3_UPDATED_SYSTEM_PROMPT.md
V5_4_UPDATED_SYSTEM_PROMPT.md
V5_5_UPDATED_SYSTEM_PROMPT.md
V5_6_UPDATED_SYSTEM_PROMPT.md
V6_1_UPDATED_SYSTEM_PROMPT.md
V6_2_UPDATED_SYSTEM_PROMPT.md
V6_3_UPDATED_SYSTEM_PROMPT.md
V6_4_UPDATED_SYSTEM_PROMPT.md
V15_INTEGRATION_COMPLETE.md
V15_P2_DYNAMIC_ADJUSTMENT_COMPLETION.md
V15_PHILOSOPHY_QUESTIONS_COMPLETION.md
V15_VALUE_POINT1_COMPLETION.md
```

#### docs/implementation/ - 实施相关文档（10个）
```
COMPLEXITY_ROUTING_IMPLEMENTATION.md
COMPLEXITY_ROUTING_VERIFICATION.md
DELIVERABLE_ORIENTED_OPTIMIZATION.md
FLEXIBLE_OUTPUT_TEST_REPORT.md
IMPLEMENTATION_SUMMARY.md
PROJECT_TYPE_INFERENCE_FIX.md
ROLE_ALLOCATION_REDUNDANCY_ROOT_CAUSE_ANALYSIS.md
ROLE_OUTPUT_DYNAMIC_ARCHITECTURE_PROPOSAL.md
REPORT_RESTRUCTURE_V7.md
TENCENT_API_TROUBLESHOOTING.md
```

#### docs/testing/ - 测试相关文档（3个）
```
test_cases_complexity.md
test_key_fix.md
test_phase1_improvements.md
```

#### docs/maintenance/ - 维护相关文档（8个）
```
BACKUP_20251203_STATUS.md
CHANGELOG_PHASE2.md
CLEANUP_SUMMARY.md
COMMIT_MESSAGE.md
LOG_LOCATION_DIAGNOSIS.md
PRE_DEPLOYMENT_CHECKLIST.md
ROLLBACK_ANALYSIS_20251204.md
SYSTEM_STATUS_CHECK.md
```

#### docs/frontend/ - 前端相关文档（2个）
```
FRONTEND_FIXES_PHASE1.md
FRONTEND_MISSING_CONTENT_FIX.md (保留副本在根目录)
```

---

## 🎯 整理后的目录结构

```
langgraph-design/
├── README.md                           # ✅ 项目主文档
├── CLAUDE.md                           # ✅ Claude Code指南
├── BACKUP_20251210_SUMMARY.md          # ✅ 最新备份
├── FRONTEND_MISSING_CONTENT_FIX.md     # ✅ 最新修复
├── docs/
│   ├── README.md                       # 文档索引
│   ├── archives/                       # 历史优化文档（38个）
│   ├── phase1/                         # Phase 1文档（15个）
│   ├── phase2/                         # Phase 2文档（11个）
│   ├── phase3/                         # Phase 3文档（6个）
│   ├── prompts/                        # 系统提示词（27个）
│   ├── implementation/                 # 实施文档（10个）
│   ├── testing/                        # 测试文档（3个）
│   ├── maintenance/                    # 维护文档（8个）
│   └── frontend/                       # 前端文档（2个）
├── frontend-nextjs/
├── intelligent_project_analyzer/
├── tests/
└── ...
```

---

## 📝 执行步骤

### Step 1: 创建新目录
```bash
mkdir -p docs/phase1
mkdir -p docs/phase2
mkdir -p docs/phase3
mkdir -p docs/prompts
mkdir -p docs/implementation
mkdir -p docs/testing
mkdir -p docs/maintenance
mkdir -p docs/frontend
```

### Step 2: 移动Phase文档
```bash
mv PHASE1_*.md docs/phase1/
mv PHASE_1_5_*.md docs/phase1/
mv phase1_*.md docs/phase1/

mv PHASE2_*.md docs/phase2/

mv PHASE3_*.md docs/phase3/
```

### Step 3: 移动系统提示词文档
```bash
mv V*_UPDATED_SYSTEM_PROMPT.md docs/prompts/
mv V15_*.md docs/prompts/
```

### Step 4: 移动实施文档
```bash
mv COMPLEXITY_ROUTING_*.md docs/implementation/
mv DELIVERABLE_*.md docs/implementation/
mv FLEXIBLE_OUTPUT_*.md docs/implementation/
mv IMPLEMENTATION_SUMMARY.md docs/implementation/
mv PROJECT_TYPE_*.md docs/implementation/
mv ROLE_*.md docs/implementation/
mv REPORT_RESTRUCTURE_*.md docs/implementation/
mv TENCENT_API_*.md docs/implementation/
```

### Step 5: 移动测试文档
```bash
mv test_*.md docs/testing/
```

### Step 6: 移动维护文档
```bash
mv BACKUP_20251203_STATUS.md docs/maintenance/
mv CHANGELOG_*.md docs/maintenance/
mv CLEANUP_*.md docs/maintenance/
mv COMMIT_MESSAGE.md docs/maintenance/
mv LOG_LOCATION_*.md docs/maintenance/
mv PRE_DEPLOYMENT_*.md docs/maintenance/
mv ROLLBACK_*.md docs/maintenance/
mv SYSTEM_STATUS_*.md docs/maintenance/
```

### Step 7: 移动前端文档
```bash
mv FRONTEND_FIXES_*.md docs/frontend/
cp FRONTEND_MISSING_CONTENT_FIX.md docs/frontend/
```

### Step 8: 更新docs/README.md
添加新目录的索引信息

---

## ✅ 预期结果

### 根目录（4个文件）
```
✅ README.md
✅ CLAUDE.md
✅ BACKUP_20251210_SUMMARY.md
✅ FRONTEND_MISSING_CONTENT_FIX.md
```

### docs/目录（120+个文档，分类清晰）
```
✅ archives/        38个历史文档
✅ phase1/          15个Phase 1文档
✅ phase2/          11个Phase 2文档
✅ phase3/          6个Phase 3文档
✅ prompts/         27个系统提示词文档
✅ implementation/  10个实施文档
✅ testing/         3个测试文档
✅ maintenance/     8个维护文档
✅ frontend/        2个前端文档
```

---

## 🔍 验证命令

```bash
# 检查根目录Markdown文件数量（应为4个）
ls -1 *.md 2>/dev/null | wc -l

# 检查docs/目录结构
ls -d docs/*/

# 检查各子目录文件数量
ls docs/phase1/ | wc -l
ls docs/phase2/ | wc -l
ls docs/phase3/ | wc -l
ls docs/prompts/ | wc -l
ls docs/implementation/ | wc -l
ls docs/testing/ | wc -l
ls docs/maintenance/ | wc -l
ls docs/frontend/ | wc -l
```

---

## 📚 文档索引更新

需要更新 `docs/README.md`，添加以下章节：

### 新增章节
```markdown
## 📁 文档分类

### Phase文档
- [Phase 1文档](phase1/) - 15个文档
- [Phase 2文档](phase2/) - 11个文档
- [Phase 3文档](phase3/) - 6个文档

### 系统提示词
- [系统提示词文档](prompts/) - 27个文档

### 实施文档
- [实施相关文档](implementation/) - 10个文档

### 测试文档
- [测试相关文档](testing/) - 3个文档

### 维护文档
- [维护相关文档](maintenance/) - 8个文档

### 前端文档
- [前端相关文档](frontend/) - 2个文档
```

---

## ⚠️ 注意事项

1. **保留副本**: `FRONTEND_MISSING_CONTENT_FIX.md` 在根目录和 `docs/frontend/` 都保留
2. **Git历史**: 使用 `git mv` 保留文件历史
3. **链接更新**: 移动后需要更新文档中的相对链接
4. **备份**: 执行前先创建git提交

---

**整理人**: Claude Code
**预计工时**: 30分钟
**优先级**: P1（高优先级）
