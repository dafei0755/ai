# Phase 2 智能化演进系统 - 使用指南

> **版本**: 1.0.0
> **发布日期**: 2026-03-04
> **前置条件**: Phase 1 已在生产环境运行 ≥ 30 天，已收集 500+ 真实调用数据

---

## 概述

Phase 2 基于 Phase 1 采集的真实使用数据，通过自动化的示例优化、智能生成和 A/B 测试，
实现 Few-Shot 示例库的持续自演进。

**四大核心模块**：

| 模块 | 类 | 功能 |
|------|-----|------|
| 示例优化器 | `ExampleOptimizer` | 识别并自动改写低质量示例 |
| 示例生成器 | `ExampleGenerator` | 为空白场景生成新示例 |
| A/B 测试管理 | `ABTestManager` | 对比新旧示例的真实效果 |
| 性能监控 | `PerformanceMonitor` | 追踪长期质量指标趋势 |

---

## Phase 2 启动前检查清单

在执行 Phase 2 任何操作前，请确认以下项目：

```bash
# 1. 验证 Phase 1 已积累足够数据
python -c "
from intelligent_project_analyzer.intelligence.usage_tracker import UsageTracker
tracker = UsageTracker()
stats = tracker.get_stats()
print(f'总调用次数: {stats.get(\"total_calls\", 0)}')
print(f'覆盖角色数: {stats.get(\"unique_roles\", 0)}')
"
# 期望: total_calls >= 500

# 2. 验证每日质量分析已产生报告
ls data/intelligence/reports/
# 期望: 存在 weekly_*.json 文件

# 3. 验证依赖完整
python -c "from intelligent_project_analyzer.intelligence import ExampleQualityAnalyzer; print('OK')"
```

---

## 一、示例质量分析

### 1.1 手动运行质量分析

```python
from intelligent_project_analyzer.intelligence.example_quality_analyzer import ExampleQualityAnalyzer
from intelligent_project_analyzer.intelligence.usage_tracker import UsageTracker

tracker = UsageTracker()
analyzer = ExampleQualityAnalyzer(tracker=tracker)

# 分析所有角色的示例质量
report = analyzer.analyze_all_roles()
print(report)

# 分析特定角色
role_report = analyzer.analyze_role("V2_0")
print(f"低质量示例: {role_report.low_quality_examples}")
print(f"推荐优化: {role_report.recommendations}")
```

### 1.2 质量评分解读

| 分数区间 | 等级 | 处理建议 |
|---------|------|---------|
| 0.8 - 1.0 | 优秀 | 保留，可作为参考标准 |
| 0.6 - 0.8 | 良好 | 保留，定期复查 |
| 0.4 - 0.6 | 一般 | 加入优化候选列表 |
| < 0.4 | 差 | 优先使用 ExampleOptimizer 处理 |

---

## 二、示例批量优化

### 2.1 使用 ExampleOptimizer

```python
from pathlib import Path
from intelligent_project_analyzer.intelligence.example_optimizer import ExampleOptimizer
from intelligent_project_analyzer.intelligence.example_quality_analyzer import ExampleQualityAnalyzer
from intelligent_project_analyzer.intelligence.usage_tracker import UsageTracker

tracker = UsageTracker()
analyzer = ExampleQualityAnalyzer(tracker=tracker)
optimizer = ExampleOptimizer(quality_analyzer=analyzer)

examples_dir = Path("intelligent_project_analyzer/config/prompts/few_shot_examples")

# 获取低质量示例列表
low_quality = analyzer.get_low_quality_examples(threshold=0.5)
print(f"发现 {len(low_quality)} 个低质量示例: {[e.example_id for e in low_quality]}")

# 批量优化（建议每次处理 5-10 个）
for example in low_quality[:5]:
    result = optimizer.optimize_example(example)
    if result.success:
        print(f"✅ {example.example_id}: {result.improvement_summary}")
    else:
        print(f"❌ {example.example_id}: {result.error}")
```

### 2.2 优化最佳实践

1. **一次处理不超过 10 个**：避免批量错误扩散
2. **优化后先在测试环境验证**：运行 `pytest tests/services/test_few_shot_optimization.py`
3. **保留原始备份**：`cp intelligent_project_analyzer/config/prompts/few_shot_examples/{file}.yaml {file}.yaml.bak`
4. **记录优化日志**：在 `data/intelligence/reports/` 下保存 diff 摘要

---

## 三、场景补全（示例生成）

### 3.1 识别空白场景

```python
from intelligent_project_analyzer.intelligence.example_quality_analyzer import ExampleQualityAnalyzer

analyzer = ExampleQualityAnalyzer()
gaps = analyzer.find_coverage_gaps()

print("缺少覆盖的场景类型:")
for gap in gaps:
    print(f"  - {gap.space_type} / {gap.design_direction}: {gap.example_count} 个示例（建议至少 2 个）")
```

### 3.2 生成新示例

```python
from intelligent_project_analyzer.intelligence.example_generator import ExampleGenerator

generator = ExampleGenerator()

# 为指定场景生成示例
new_example = generator.generate(
    space_type="healthcare",
    design_direction="functional",
    scale="large",
    description="大型综合医院门诊楼改造项目，重点解决就医流线混乱问题"
)

# 验证生成质量
if new_example.quality_score >= 0.6:
    new_example.save_to(
        Path("intelligent_project_analyzer/config/prompts/few_shot_examples/healthcare_functional_01.yaml")
    )
    print(f"✅ 新示例已保存，质量分数: {new_example.quality_score:.2f}")
```

### 3.3 生成结果验证清单

- [ ] YAML 格式正确（可用 `python -c "import yaml; yaml.safe_load(open('file.yaml'))"` 验证）
- [ ] `project_info.name` 非空且描述准确
- [ ] `ideal_tasks` 包含 3-7 个任务，任务标题切实可行
- [ ] `feature_vector` 各分量总和 ≈ 1.0
- [ ] 与现有示例不重叠（通过语义相似度检查）

---

## 四、A/B 测试

### 4.1 实验设计原则

- **每次只测一个变量**：新旧示例差异要单一明确
- **最小样本量**：每组至少 50 次真实调用（建议 100 次）
- **测试周期**：5-7 天（覆盖工作日和周末的访问模式差异）
- **显著性阈值**：p < 0.05（质量提升 ≥ 5% 才判定有效）

### 4.2 启动 A/B 测试

```python
from intelligent_project_analyzer.intelligence.ab_test_manager import ABTestManager

manager = ABTestManager()

# 定义实验：旧示例 vs 优化后的示例
experiment = manager.create_experiment(
    name="optimize_commercial_example_v1",
    role_id="V2_0",
    control_example_id="commercial_dominant_01",   # 控制组（现有）
    treatment_example_id="commercial_dominant_01_v2",  # 实验组（优化后）
    traffic_split=0.5,   # 50% 流量到实验组
    min_samples=100,
    max_duration_days=7,
)

print(f"实验 ID: {experiment.id}")
print(f"预计完成: {experiment.estimated_completion}")
```

### 4.3 查看实验结果

```python
# 获取实验报告
results = manager.get_experiment_results(experiment_id="optimize_commercial_example_v1")

print(f"控制组质量均分: {results.control_mean:.3f}")
print(f"实验组质量均分: {results.treatment_mean:.3f}")
print(f"提升幅度: {results.improvement_pct:+.1f}%")
print(f"统计显著性: p={results.p_value:.4f} ({'✅ 显著' if results.p_value < 0.05 else '❌ 不显著'})")

if results.is_significant and results.improvement_pct > 5:
    print("→ 建议部署实验组示例到生产")
else:
    print("→ 实验组无明显改进，保留控制组")
```

---

## 五、性能监控与 Grafana Dashboard

### 5.1 关键指标说明

| 指标名 | 含义 | 期望目标 |
|-------|------|---------|
| `few_shot_selection_latency_ms` | 示例检索延迟 | p99 < 100ms |
| `few_shot_quality_score_avg` | 示例平均质量分 | > 0.7 |
| `few_shot_cache_hit_rate` | FAISS 缓存命中率 | > 95% |
| `ab_test_active_experiments` | 当前活跃 A/B 实验数 | ≤ 3 |
| `example_low_quality_count` | 低质量示例数（< 0.5） | < 5 |

### 5.2 Grafana Dashboard 导入步骤

```bash
# 1. 启动 Grafana（若未运行）
start_grafana.bat

# 2. 访问 Grafana
# URL: http://localhost:3200
# 默认账号: admin / admin

# 3. 导入 Dashboard
# Dashboards → Import → 上传 docker/grafana/dashboards/intelligence_phase2.json
```

### 5.3 告警规则配置示例

在 Prometheus/AlertManager 中添加以下规则：

```yaml
groups:
  - name: few_shot_alerts
    rules:
      - alert: FewShotHighLatency
        expr: few_shot_selection_latency_ms{quantile="0.99"} > 200
        for: 5m
        annotations:
          summary: "Few-Shot 检索延迟过高（>200ms p99），请检查 FAISS 索引是否加载"

      - alert: FewShotLowQuality
        expr: few_shot_quality_score_avg < 0.5
        for: 1h
        annotations:
          summary: "Few-Shot 平均质量分低于 0.5，建议运行 ExampleOptimizer"
```

---

## 六、生产部署检查清单

### Phase 1 验证项目（部署 Phase 2 前必须全部通过）

- [ ] `data/intelligence/indexes/all_examples.faiss` 存在（运行 `python scripts/build_all_indexes.py` 生成）
- [ ] 定时任务已激活（服务器启动日志含"Phase 1 定时任务已启动"）
- [ ] `data/intelligence/reports/weekly_*.json` 存在至少一份
- [ ] `pytest tests/intelligence/ -q` 全部通过（36 个测试）
- [ ] Phase 1 累计真实调用 ≥ 500 次（`UsageTracker().get_stats()["total_calls"]`）

### Phase 2 启用流程

1. **导入实验配置**（`config/ab_tests/default_experiments.yaml`）
2. **部署 Grafana Dashboard**（步骤见第五节）
3. **启动首个 A/B 测试**（建议先选质量最低的示例做实验）
4. **5-7 天后评估**：达到显著性则部署实验组，否则继续收集数据

### 回滚预案

若 Phase 2 操作导致质量下降：

```bash
# 1. 立即停止 A/B 测试
python -c "
from intelligent_project_analyzer.intelligence.ab_test_manager import ABTestManager
ABTestManager().stop_all_experiments()
print('所有 A/B 测试已停止')"

# 2. 恢复备份示例
cp intelligent_project_analyzer/config/prompts/few_shot_examples/*.yaml.bak \
   intelligent_project_analyzer/config/prompts/few_shot_examples/

# 3. 重建索引
python scripts/build_all_indexes.py --force

# 4. 重启服务
# 重启后 IntelligentFewShotSelector 将自动加载新索引
```

---

## 七、30 天演进路线图

| 时间 | 里程碑 | 关键可交付物 |
|------|---------|-----------| 
| 第 1 周 | Phase 1 生产部署 ✅ | FAISS 索引 + 定时任务 + 本文档 |
| 第 2-4 周 | 数据收集期 | ≥500 次真实调用，每周质量报告 |
| 第 5 周 | 数据分析 + 调优 | 优化 5-10 个低质量示例，设计 2-3 个 A/B 实验 |
| 第 6 周 | Phase 2 完整部署 | A/B 测试上线，Grafana Dashboard，本文档最终版 |

---

## 相关文档

- [Phase 1 使用指南](INTELLIGENCE_PHASE1_GUIDE.md) — API 参考与故障排查
- [Phase 1 演示脚本](../scripts/demo_phase1_intelligence.py) — 交互式功能演示
- [索引构建脚本](../scripts/build_all_indexes.py) — FAISS 索引一次性预构建
- [测试套件](../tests/intelligence/) — 36 个单元与集成测试
- [CHANGELOG](../CHANGELOG.md) — 完整版本历史
