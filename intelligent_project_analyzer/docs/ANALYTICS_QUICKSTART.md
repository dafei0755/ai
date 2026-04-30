# 运行时监控系统 - 快速开始

## 🎯 3分钟上手

### 第1步: 初始化监控

```python
from services.role_selection_analytics import RoleSelectionAnalytics

analytics = RoleSelectionAnalytics()
```

### 第2步: 记录数据

```python
analytics.record_selection(
    user_request="为咖啡馆做空间设计",
    selected_mode="单一专家深潜",
    selected_roles=[{
        "role_id": "2-2",
        "role_name": "商业空间设计总监",
        "dynamic_role_name": "精品咖啡馆设计专家"
    }],
    confidence=0.88,
    keywords_matched=["商业空间设计", "咖啡馆"],
    execution_time_ms=156.3,
    success=True
)
```

### 第3步: 查看统计

```python
summary = analytics.generate_summary(period="daily")

print(f"今日选择: {summary.total_selections}次")
print(f"成功率: {summary.success_rate:.1%}")
print(f"平均置信度: {summary.avg_confidence:.2%}")
```

---

## 📚 完整文档

- **详细使用指南**: [docs/ANALYTICS_USAGE_GUIDE.md](ANALYTICS_USAGE_GUIDE.md)
  - 完整API参考
  - 高级查询功能
  - 最佳实践建议
  
- **集成示例**: [examples/analytics_integration_example.py](../examples/analytics_integration_example.py)
  - DynamicProjectDirector集成示例
  - 完整的代码实现
  
- **快速演示**: [examples/analytics_quickstart.py](../examples/analytics_quickstart.py)
  - 5步使用流程
  - 核心功能展示

---

## 🔧 集成到系统

在 `agents/dynamic_project_director.py` 中添加:

```python
from services.role_selection_analytics import RoleSelectionAnalytics
import time

class DynamicProjectDirector:
    def __init__(self):
        self.analytics = RoleSelectionAnalytics()  # 添加这行
    
    def select_roles(self, state):
        start_time = time.time()
        
        try:
            result = self._execute_selection(state)
            
            # 记录成功
            self.analytics.record_selection(
                user_request=state["user_input"],
                selected_mode=result["mode"],
                selected_roles=result["roles"],
                confidence=result["confidence"],
                keywords_matched=result["keywords"],
                execution_time_ms=(time.time() - start_time) * 1000,
                success=True
            )
            
            return result
        except Exception as e:
            # 记录失败
            self.analytics.record_selection(
                user_request=state["user_input"],
                selected_mode="失败",
                selected_roles=[],
                confidence=0.0,
                keywords_matched=[],
                execution_time_ms=(time.time() - start_time) * 1000,
                success=False,
                error_message=str(e)
            )
            raise
```

---

## 📊 核心功能

| 功能 | 方法 | 说明 |
|------|------|------|
| 记录选择 | `record_selection()` | 记录每次角色选择 |
| 日报统计 | `generate_summary(period="daily")` | 获取今日数据 |
| 周报统计 | `generate_summary(period="weekly")` | 获取本周数据 |
| 月报统计 | `generate_summary(period="monthly")` | 获取本月数据 |
| 导出报告 | `export_report()` | 生成Markdown报告 |
| 角色排行 | `get_role_usage_stats()` | 角色使用频率 |
| Keywords分析 | `get_keyword_stats()` | 高频关键词统计 |
| 失败分析 | `get_failed_selections()` | 失败案例追踪 |

---

## 💡 使用场景

### 场景1: 每日监控

```python
# 每天早上查看昨日数据
summary = analytics.generate_summary(period="daily")
if summary.success_rate < 0.9:
    print("⚠️ 成功率偏低,需要检查")
```

### 场景2: 性能优化

```python
# 追踪响应时间
if summary.avg_execution_time_ms > 300:
    print("⚠️ 响应偏慢,需要优化")
```

### 场景3: Keywords优化

```python
# 分析高频keywords
keyword_stats = analytics.get_keyword_stats(days=30)
print("Top 10 Keywords:", keyword_stats[:10])
```

### 场景4: 月度复盘

```python
# 生成月度报告
summary = analytics.generate_summary(period="monthly")
report_path = analytics.export_report(summary)
print(f"月度报告: {report_path}")
```

---

## ✅ 检查清单

在部署前确认:

- [ ] 已在角色选择主流程中集成监控
- [ ] 已测试成功和失败两种情况的记录
- [ ] 已验证统计数据正确性
- [ ] 已设置定期报告生成任务
- [ ] 已配置数据库存储路径
- [ ] 已规划数据清理策略 (建议保留3个月)

---

## 🚀 下一步

1. 阅读完整文档: [ANALYTICS_USAGE_GUIDE.md](ANALYTICS_USAGE_GUIDE.md)
2. 查看集成示例: [analytics_integration_example.py](../examples/analytics_integration_example.py)
3. 运行快速演示: `python examples/analytics_quickstart.py`
4. 集成到你的系统
5. 开始收集数据!

---

**版本**: v1.0  
**日期**: 2025-11-23  
**状态**: ✅ 生产就绪
