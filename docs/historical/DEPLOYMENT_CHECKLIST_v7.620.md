# v7.620 生产部署检查清单

**版本**: v7.620 - Fallback优化
**日期**: 2026-02-11
**提交ID**: fc9611e
**优化内容**: Sufficient率 14% → 34% (+143%)

---

## ✅ 部署前检查

### 1. 代码版本确认

- [x] Git提交完成: `fc9611e`
- [ ] 代码已推送到远程仓库: `git push origin main`
- [ ] 标签已创建: `git tag v7.620 && git push origin v7.620`

```bash
# 推送代码和标签
git push origin main
git tag -a v7.620 -m "Fallback优化 - Sufficient率14%→34%"
git push origin v7.620
```

### 2. 核心文件确认

- [x] `capability_detector.py` - 优化逻辑已实现
- [x] `QUICKSTART.md` - 用户文档已更新
- [x] `FALLBACK_OPTIMIZATION_REPORT_v7.620.md` - 完整报告已创建
- [x] `quality_test_results.json` - 测试数据已保存

### 3. 配置参数确认

检查 `intelligent_project_analyzer/utils/capability_detector.py`:

```python
INFO_SUFFICIENT_THRESHOLD = 0.40  # ✅ 应为 0.40 (原0.5)
INFO_ELEMENT_MIN_COUNT = 2         # ✅ 应为 2 (原3)
```

验证命令:
```bash
python -c "from intelligent_project_analyzer.utils.capability_detector import CapabilityDetector; print('Threshold:', CapabilityDetector.INFO_SUFFICIENT_THRESHOLD); print('Min Count:', CapabilityDetector.INFO_ELEMENT_MIN_COUNT)"
```

预期输出:
```
Threshold: 0.40
Min Count: 2
```

---

## 🚀 部署步骤

### Step 1: 停止当前服务

```bash
# Windows
taskkill /F /IM python.exe
Get-Process node | Stop-Process -Force

# Linux/Mac
pkill -f "uvicorn"
pkill -f "next"
```

### Step 2: 拉取最新代码

```bash
git pull origin main
git checkout v7.620  # 或使用 main 分支
```

### Step 3: 检查依赖（无需更新）

本次优化**不需要安装新依赖**，跳过此步骤。

### Step 4: 重启服务

```bash
# 后端
python -B scripts\run_server_production.py

# 前端（新终端）
cd frontend-nextjs && npm run dev
```

### Step 5: 服务健康检查

```bash
# 检查后端API
curl http://localhost:8000/health

# 检查前端
curl http://localhost:3001
```

预期输出:
- 后端: `{"status": "ok"}`
- 前端: HTML页面内容

---

## 🧪 功能验证

### 验证1: 基础功能测试

1. 访问 http://localhost:3001
2. 输入简单需求: "150平米现代简约住宅设计"
3. ✅ 应该跳转到问卷页面（insufficient场景）

### 验证2: Sufficient场景测试

输入以下需求（应直接进入分析，跳过问卷）:

**测试场景1: 高净值用户**
```
一位企业家想在深圳湾设计350平米的海景别墅
```
✅ 预期: `info_status: sufficient`, 跳过问卷

**测试场景2: 特殊需求**
```
35岁程序员，腾讯上班，年薪120万。孩子7岁自闭症。深圳前海160平米住宅设计
```
✅ 预期: `info_status: sufficient`, 识别自闭症特殊需求

**测试场景3: 电竞场景**
```
职业电竞选手，需要将15平米卧室改造为直播+训练空间，要求专业级灯光布局
```
✅ 预期: `info_status: sufficient`, `deliverable: lighting_design`

### 验证3: API端点测试

```bash
# 测试需求分析API
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"user_input": "一位企业家想在深圳湾设计350平米的海景别墅"}'
```

检查响应:
```json
{
  "phase1_result": {
    "info_status": "sufficient",  // ✅ 应为 sufficient
    "fallback": true,              // ✅ 当前Windows环境下应为true
    "primary_deliverables": [...]
  }
}
```

---

## 📊 性能监控

### 监控指标

部署后7天内持续监控以下指标:

| 指标 | 目标值 | 监控方法 |
|------|--------|----------|
| **Sufficient率** | ≥30% | 每日统计数据库session表 |
| **系统稳定性** | 100%成功率 | 错误日志监控 |
| **Phase2成功率** | ≥90% | 数据库分析 |
| **用户满意度** | 无明显下降 | 用户反馈收集 |

### 监控SQL查询

```sql
-- 每日Sufficient率统计
SELECT
  DATE(created_at) as date,
  COUNT(*) as total_sessions,
  SUM(CASE WHEN phase1_result->>'info_status' = 'sufficient' THEN 1 ELSE 0 END) as sufficient_count,
  ROUND(100.0 * SUM(CASE WHEN phase1_result->>'info_status' = 'sufficient' THEN 1 ELSE 0 END) / COUNT(*), 2) as sufficient_rate
FROM sessions
WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

预期结果:
- sufficient_rate 应在 **30-40%** 之间
- 如低于25%，需要调查原因

### 告警阈值

设置以下告警:

1. **P0告警**: Sufficient率 < 20%（连续2天）
2. **P1告警**: 系统错误率 > 1%
3. **P2告警**: Sufficient率 < 25%（连续3天）

---

## 🔄 回滚方案

如果部署后出现严重问题，执行以下回滚步骤:

### 快速回滚

```bash
# 1. 停止服务
taskkill /F /IM python.exe
Get-Process node | Stop-Process -Force

# 2. 回滚到v7.600
git checkout v7.600  # 或之前的稳定commit

# 3. 重启服务
python -B scripts\run_server_production.py
cd frontend-nextjs && npm run dev
```

### 回滚触发条件

- ⛔ **立即回滚**: 系统崩溃率 > 5%
- ⚠️ **考虑回滚**: Sufficient率 < 15%（低于baseline）
- ⚠️ **考虑回滚**: 用户投诉量显著增加

### 参数微调（替代回滚）

如果Sufficient率过高导致质量下降，可以微调参数:

```python
# 在 capability_detector.py 中调整

# 当前值
INFO_SUFFICIENT_THRESHOLD = 0.40

# 可选调整范围
# 0.42 - 稍严格，sufficient率约28-32%
# 0.38 - 更宽松，sufficient率约36-40%
```

---

## 📝 文档更新清单

- [x] `QUICKSTART.md` - 添加Fallback模式说明
- [x] `FALLBACK_OPTIMIZATION_REPORT_v7.620.md` - 完整技术报告
- [ ] `README.md` - 更新版本号到v7.620（如需要）
- [ ] `CHANGELOG.md` - 添加v7.620更新日志（如需要）
- [ ] API文档 - 更新sufficient率预期（如有独立API文档）

更新命令:
```bash
# 可选: 更新CHANGELOG.md
echo "## v7.620 (2026-02-11)

### 🚀 Features
- Fallback优化: Sufficient率14%→34% (+143%)
- 隐含信息智能推断（高净值+0.20, 特殊需求+0.08-0.15）
- 交付物类型细分（+6种新类型）

### 📊 Performance
- 系统稳定性: 100%成功率
- 受益场景: 自闭症家庭、电竞选手、失眠金融人、高净值用户

### 📖 Documentation
- 更新QUICKSTART.md添加Fallback模式说明
- 新增FALLBACK_OPTIMIZATION_REPORT_v7.620.md
" | cat - CHANGELOG.md > temp && mv temp CHANGELOG.md
```

---

## 🎯 用户沟通

### 对内沟通（团队）

**Slack/钉钉通知模板**:
```
🎉 v7.620已部署上线

📊 核心改进:
- Sufficient率: 14% → 34% (+143%)
- 10个新场景可跳过问卷直达分析
- 100%系统稳定性

🔍 重点关注:
- 监控后7天的sufficient率（目标≥30%）
- 收集用户反馈（尤其高净值/特殊需求用户）

📖 详细报告: FALLBACK_OPTIMIZATION_REPORT_v7.620.md
```

### 对外沟通（用户）

**产品更新公告（可选）**:
```
📢 系统升级通知

我们优化了需求分析引擎，现在您可以:
✅ 提供详细信息直接进入深度分析（34%场景）
✅ 更智能识别高价值需求（企业家、特殊需求场景）
✅ 更精准的交付物推荐

💡 小提示: 输入时包含项目面积、用户身份、特殊需求可获得更好体验
```

---

## ✅ 最终检查清单

部署完成后，确认以下所有项:

### 代码层面
- [ ] Git提交已完成并推送: `git log --oneline -1`
- [ ] 标签已创建: `git tag -l v7.620`
- [ ] 代码已在生产环境更新: `git rev-parse HEAD`

### 功能层面
- [ ] 3个测试场景验证通过（高净值/特殊需求/电竞）
- [ ] API端点返回正确的`info_status`
- [ ] 前端页面正常加载

### 监控层面
- [ ] 数据库监控SQL已设置
- [ ] 告警阈值已配置
- [ ] 日志记录正常（无异常错误）

### 文档层面
- [ ] QUICKSTART.md已更新
- [ ] 团队已通知部署完成
- [ ] 用户公告已发布（如需要）

---

## 📞 支持联系

如部署过程中遇到问题:

1. **优先查阅**: [FALLBACK_OPTIMIZATION_REPORT_v7.620.md](FALLBACK_OPTIMIZATION_REPORT_v7.620.md)
2. **技术问题**: 查看日志文件 `logs/app.log`
3. **回滚决策**: 参考上方"回滚方案"章节

---

## 📈 后续优化路径

v7.620是在emoji编码错误无法修复的限制下的最优方案。

**长期改进方向**:

1. **迁移到Claude API**（推荐）
   - 预期: sufficient率可达50-60%
   - 成本: +30%
   - 时间: 2-3天

2. **Docker Linux环境**
   - 预期: 解决emoji错误，恢复LLM全功能
   - 成本: 服务器迁移
   - 时间: 1周

3. **继续优化Fallback**
   - 扩展隐含信息规则库
   - 多标签交付物识别
   - 知识图谱增强

---

**部署负责人**: _____________
**部署日期**: 2026-02-11
**验证日期**: _____________
**状态**: ⬜ 待部署 / ⬜ 进行中 / ⬜ 已完成
