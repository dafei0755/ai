# 运行时监控系统使用指南

**版本**: v1.0  
**日期**: 2025-11-23  
**模块**: `services/role_selection_analytics.py`

---

## 📋 快速开始

### 1️⃣ 基础使用 (3行代码)

```python
from intelligent_project_analyzer.services.role_selection_analytics import RoleSelectionAnalytics

# 初始化监控系统
analytics = RoleSelectionAnalytics()

# 记录一次角色选择
analytics.record_selection(
    user_request="为三代同堂的150㎡住宅做空间设计",
    selected_mode="多专家并行",
    selected_roles=[
        {"role_id": "2-1", "role_name": "居住空间设计总监", "dynamic_role_name": "三代同堂住宅设计专家"},
        {"role_id": "5-1", "role_name": "居住空间运营顾问", "dynamic_role_name": "家庭生活模式分析师"}
    ],
    confidence=0.92,
    keywords_matched=["居住空间设计", "三代同堂", "住宅"],
    execution_time_ms=245.6,
    success=True
)

print("✅ 选择记录已保存")
```

---

## 🔧 集成到现有系统

### 方式1: 在 DynamicProjectDirector 中集成

```python
# agents/dynamic_project_director.py

from services.role_selection_analytics import RoleSelectionAnalytics
import time

class DynamicProjectDirector:
    def __init__(self):
        # 初始化监控系统
        self.analytics = RoleSelectionAnalytics()
        # ... 其他初始化
    
    def select_roles(self, state: Dict) -> Dict:
        """角色选择主逻辑"""
        start_time = time.time()
        user_request = state.get("user_input", "")
        
        try:
            # 执行角色选择逻辑
            result = self._execute_role_selection(user_request)
            
            # 计算执行时间
            execution_time = (time.time() - start_time) * 1000
            
            # 📊 记录到监控系统
            self.analytics.record_selection(
                user_request=user_request,
                selected_mode=result.get("collaboration_mode", "未知"),
                selected_roles=result.get("selected_roles", []),
                confidence=result.get("confidence", 0.0),
                keywords_matched=result.get("matched_keywords", []),
                execution_time_ms=execution_time,
                success=True
            )
            
            return result
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            
            # 📊 记录失败情况
            self.analytics.record_selection(
                user_request=user_request,
                selected_mode="失败",
                selected_roles=[],
                confidence=0.0,
                keywords_matched=[],
                execution_time_ms=execution_time,
                success=False,
                error_message=str(e)
            )
            
            raise
```

### 方式2: 在 Workflow 中集成

```python
# workflow/main_workflow.py

from services.role_selection_analytics import RoleSelectionAnalytics

# 创建全局监控实例
analytics = RoleSelectionAnalytics()

def role_selection_node(state: Dict) -> Dict:
    """角色选择节点"""
    start_time = time.time()
    
    # 调用角色选择逻辑
    result = director.select_roles(state)
    
    # 记录监控数据
    analytics.record_selection(
        user_request=state["user_input"],
        selected_mode=result["mode"],
        selected_roles=result["roles"],
        confidence=result["confidence"],
        keywords_matched=result["keywords"],
        execution_time_ms=(time.time() - start_time) * 1000,
        success=True
    )
    
    return result
```

---

## 📊 查询和分析

### 1. 查看实时统计

```python
from services.role_selection_analytics import RoleSelectionAnalytics

analytics = RoleSelectionAnalytics()

# 获取今日统计
summary = analytics.generate_summary(period="daily")

print(f"📈 今日选择次数: {summary.total_selections}")
print(f"✅ 成功率: {summary.success_rate:.1%}")
print(f"⚡ 平均响应时间: {summary.avg_execution_time_ms:.1f}ms")
print(f"🎯 平均置信度: {summary.avg_confidence:.2%}")
```

### 2. 生成周度报告

```python
# 获取本周数据
summary = analytics.generate_summary(
    period="weekly",
    start_date="2025-11-17",
    end_date="2025-11-23"
)

print(f"📊 本周数据:")
print(f"   总选择次数: {summary.total_selections}")
print(f"   协同模式分布: {summary.mode_distribution}")
print(f"   高频角色 Top 5: {summary.top_roles[:5]}")
```

### 3. 导出月度报告

```python
# 生成并导出11月报告
summary = analytics.generate_summary(
    period="monthly",
    start_date="2025-11-01",
    end_date="2025-11-30"
)

# 导出为Markdown文件
report_path = analytics.export_report(summary, format="markdown")
print(f"📄 报告已保存到: {report_path}")
```

---

## 🎯 高级功能

### 功能1: 分析角色使用频率

```python
analytics = RoleSelectionAnalytics()

# 获取角色使用统计
role_stats = analytics.get_role_usage_stats(days=30)

print("📊 最近30天角色使用排行:")
for i, (role_id, count) in enumerate(role_stats[:10], 1):
    print(f"   {i}. {role_id}: {count}次")
```

### 功能2: Keywords匹配效果分析

```python
# 获取keywords统计
keyword_stats = analytics.get_keyword_stats(days=30)

print("🔑 高频Keywords Top 20:")
for kw, count in keyword_stats[:20]:
    print(f"   {kw}: {count}次")
```

### 功能3: 失败案例分析

```python
# 获取失败记录
failures = analytics.get_failed_selections(days=7)

print(f"⚠️ 本周失败案例: {len(failures)}个")
for record in failures:
    print(f"   - 用户请求: {record.user_request[:50]}...")
    print(f"     错误信息: {record.error_message}")
```

### 功能4: 置信度趋势分析

```python
# 获取置信度趋势
confidence_trend = analytics.get_confidence_trend(days=30)

print("📈 置信度趋势 (最近30天):")
for date, avg_confidence in confidence_trend:
    print(f"   {date}: {avg_confidence:.2%}")
```

---

## 📁 数据存储位置

监控系统使用SQLite数据库存储数据:

```
intelligent_project_analyzer/
└── data/
    └── role_selection_analytics.db  # SQLite数据库文件
```

### 数据表结构

```sql
CREATE TABLE role_selections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    user_request TEXT NOT NULL,
    selected_mode TEXT NOT NULL,
    selected_roles TEXT NOT NULL,  -- JSON格式
    confidence REAL NOT NULL,
    keywords_matched TEXT,  -- JSON格式
    execution_time_ms REAL NOT NULL,
    success INTEGER NOT NULL,
    feedback_score REAL,
    error_message TEXT
);
```

---

## 🔍 实际使用案例

### 案例1: 每日监控看板

```python
"""
每日运行脚本: daily_analytics.py
"""
from services.role_selection_analytics import RoleSelectionAnalytics
from datetime import datetime, timedelta

analytics = RoleSelectionAnalytics()

# 获取昨天的数据
yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
summary = analytics.generate_summary(
    period="daily",
    start_date=yesterday,
    end_date=yesterday
)

# 发送到企业微信/钉钉
print(f"""
📊 角色选择系统日报 ({yesterday})
━━━━━━━━━━━━━━━━━━━━━━━━
📈 选择次数: {summary.total_selections}
✅ 成功率: {summary.success_rate:.1%}
⚡ 平均响应: {summary.avg_execution_time_ms:.0f}ms
🎯 平均置信度: {summary.avg_confidence:.2%}

🔥 热门协同模式:
{summary.mode_distribution}

⭐ 最活跃角色 Top 3:
{summary.top_roles[:3]}
""")
```

### 案例2: 智能优化建议

```python
"""
每周运行: weekly_optimization.py
"""
from services.role_selection_analytics import RoleSelectionAnalytics

analytics = RoleSelectionAnalytics()
summary = analytics.generate_summary(period="weekly")

print("🎯 本周优化建议:")

# 建议1: 低置信度优化
if summary.avg_confidence < 0.85:
    print(f"⚠️ 平均置信度偏低 ({summary.avg_confidence:.2%})")
    print("   建议: 检查keywords匹配逻辑,补充缺失的关键词")

# 建议2: 响应时间优化
if summary.avg_execution_time_ms > 300:
    print(f"⚠️ 平均响应时间偏慢 ({summary.avg_execution_time_ms:.0f}ms)")
    print("   建议: 优化LLM调用次数或缓存常用结果")

# 建议3: 高频角色分析
top_role = summary.top_roles[0] if summary.top_roles else None
if top_role and top_role[1] > summary.total_selections * 0.3:
    print(f"⚠️ 角色 {top_role[0]} 使用频率过高 ({top_role[1]/summary.total_selections:.1%})")
    print("   建议: 检查是否需要拆分角色职责")
```

### 案例3: A/B测试对比

```python
"""
对比不同版本的效果
"""
analytics = RoleSelectionAnalytics()

# 获取v7.2版本数据 (11月1-15日)
summary_v72 = analytics.generate_summary(
    period="custom",
    start_date="2025-11-01",
    end_date="2025-11-15"
)

# 获取v7.3版本数据 (11月16-23日)
summary_v73 = analytics.generate_summary(
    period="custom",
    start_date="2025-11-16",
    end_date="2025-11-23"
)

# 对比分析
print("📊 版本效果对比:")
print(f"   置信度: v7.2={summary_v72.avg_confidence:.2%} vs v7.3={summary_v73.avg_confidence:.2%}")
print(f"   成功率: v7.2={summary_v72.success_rate:.1%} vs v7.3={summary_v73.success_rate:.1%}")
print(f"   响应时间: v7.2={summary_v72.avg_execution_time_ms:.0f}ms vs v7.3={summary_v73.avg_execution_time_ms:.0f}ms")
```

---

## 🛠️ 调试和问题排查

### 查看原始SQL数据

```python
import sqlite3
from pathlib import Path

db_path = Path("intelligent_project_analyzer/data/role_selection_analytics.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 查询最近10条记录
cursor.execute("""
    SELECT timestamp, user_request, selected_mode, confidence, success
    FROM role_selections
    ORDER BY timestamp DESC
    LIMIT 10
""")

for row in cursor.fetchall():
    print(row)

conn.close()
```

### 清理历史数据

```python
analytics = RoleSelectionAnalytics()

# 删除30天前的数据
analytics.cleanup_old_data(days=30)
print("🗑️ 历史数据已清理")
```

---

## ⚙️ 配置选项

### 自定义数据库路径

```python
analytics = RoleSelectionAnalytics(
    db_path="custom/path/analytics.db"
)
```

### 批量记录模式 (高性能)

```python
analytics = RoleSelectionAnalytics()

# 开启批量模式
analytics.start_batch_mode(batch_size=100)

# 记录多次选择
for i in range(1000):
    analytics.record_selection(...)

# 手动刷新缓冲区
analytics.flush_batch()
```

---

## 📚 API参考

### RoleSelectionAnalytics 主要方法

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `record_selection()` | user_request, selected_mode, ... | None | 记录一次选择 |
| `generate_summary()` | period, start_date, end_date | AnalyticsSummary | 生成统计摘要 |
| `export_report()` | summary, format | str (文件路径) | 导出报告 |
| `get_role_usage_stats()` | days | List[Tuple] | 角色使用统计 |
| `get_keyword_stats()` | days | List[Tuple] | Keywords统计 |
| `get_failed_selections()` | days | List[Record] | 失败案例 |
| `get_confidence_trend()` | days | List[Tuple] | 置信度趋势 |
| `cleanup_old_data()` | days | int | 清理旧数据 |

---

## 🎓 最佳实践

### ✅ 推荐做法

1. **在角色选择主流程中集成监控**
   ```python
   # ✅ 好: 自动记录所有选择
   def select_roles(self, request):
       result = self._do_selection(request)
       self.analytics.record_selection(...)
       return result
   ```

2. **定期查看监控报告**
   - 每日: 查看成功率和响应时间
   - 每周: 分析角色使用分布
   - 每月: 生成优化建议报告

3. **保留足够的历史数据**
   ```python
   # ✅ 好: 保留3个月数据用于趋势分析
   analytics.cleanup_old_data(days=90)
   ```

4. **添加用户反馈收集**
   ```python
   # 角色执行完成后,收集用户反馈
   feedback_score = get_user_feedback()  # 1-5分
   analytics.update_feedback(record_id, feedback_score)
   ```

### ❌ 避免的做法

1. **不要在循环中频繁初始化**
   ```python
   # ❌ 差: 每次都创建新实例
   for request in requests:
       analytics = RoleSelectionAnalytics()  # 错误!
       analytics.record_selection(...)
   
   # ✅ 好: 复用单个实例
   analytics = RoleSelectionAnalytics()
   for request in requests:
       analytics.record_selection(...)
   ```

2. **不要记录敏感用户信息**
   ```python
   # ❌ 差: 直接记录可能包含隐私的原始输入
   analytics.record_selection(user_request=raw_input)
   
   # ✅ 好: 脱敏处理
   safe_request = remove_sensitive_info(raw_input)
   analytics.record_selection(user_request=safe_request)
   ```

---

## 🚀 快速测试

运行测试脚本验证监控系统工作正常:

```bash
cd d:\11-20\langgraph-design

# 创建测试脚本
python -c "
from intelligent_project_analyzer.services.role_selection_analytics import RoleSelectionAnalytics

analytics = RoleSelectionAnalytics()

# 记录测试数据
analytics.record_selection(
    user_request='测试用例: 为咖啡馆设计',
    selected_mode='单一专家深潜',
    selected_roles=[{'role_id': '2-2', 'role_name': '商业空间设计总监', 'dynamic_role_name': '咖啡馆设计专家'}],
    confidence=0.88,
    keywords_matched=['商业空间', '咖啡馆'],
    execution_time_ms=156.3,
    success=True
)

print('✅ 监控系统工作正常')

# 查看统计
summary = analytics.generate_summary(period='daily')
print(f'📊 今日记录数: {summary.total_selections}')
"
```

---

## 📞 技术支持

如有问题请参考:
- 模块源码: `services/role_selection_analytics.py`
- P0优化文档: `docs/P0_OPTIMIZATION_README.md`
- 测试用例: `tests/test_role_synthesis.py`

---

**最后更新**: 2025-11-23  
**维护者**: LangGraph Design Team
