"""
运行时监控系统快速演示 (简化版)

演示如何使用监控系统的核心功能
"""

print("\n" + "=" * 80)
print("运行时监控系统使用演示")
print("=" * 80 + "\n")

print("📋 步骤1: 导入监控模块")
print("-" * 80)
print("""
from services.role_selection_analytics import RoleSelectionAnalytics

# 初始化监控系统
analytics = RoleSelectionAnalytics()
""")

print("\n📋 步骤2: 记录角色选择")
print("-" * 80)
print("""
# 在角色选择后记录数据
analytics.record_selection(
    user_request="为三代同堂的150㎡住宅做空间设计",
    selected_mode="多专家并行",
    selected_roles=[
        {
            "role_id": "2-1", 
            "role_name": "居住空间设计总监",
            "dynamic_role_name": "三代同堂住宅设计专家"
        },
        {
            "role_id": "5-1",
            "role_name": "居住空间运营顾问", 
            "dynamic_role_name": "家庭生活模式分析师"
        }
    ],
    confidence=0.92,
    keywords_matched=["居住空间设计", "三代同堂", "住宅"],
    execution_time_ms=245.6,
    success=True
)

print("✅ 记录成功")
""")

print("\n📋 步骤3: 查看统计数据")
print("-" * 80)
print("""
# 生成今日统计
summary = analytics.generate_summary(period="daily")

print(f"📊 今日统计:")
print(f"   总选择次数: {summary.total_selections}")
print(f"   成功率: {summary.success_rate:.1%}")
print(f"   平均置信度: {summary.avg_confidence:.2%}")
print(f"   平均响应时间: {summary.avg_execution_time_ms:.1f}ms")

# 输出示例:
# 📊 今日统计:
#    总选择次数: 25
#    成功率: 96.0%
#    平均置信度: 91.2%
#    平均响应时间: 234.5ms
""")

print("\n📋 步骤4: 生成报告")
print("-" * 80)
print("""
# 生成并导出报告
summary = analytics.generate_summary(period="monthly")
report_path = analytics.export_report(summary, format="markdown")

print(f"📄 月度报告已生成: {report_path}")

# 输出示例:
# 📄 月度报告已生成: reports/role_selection_monthly_2025-11.md
""")

print("\n📋 步骤5: 集成到系统")
print("-" * 80)
print("""
# 在 DynamicProjectDirector 中集成

class DynamicProjectDirector:
    def __init__(self):
        # 初始化监控
        self.analytics = RoleSelectionAnalytics()
    
    def select_roles(self, state):
        start_time = time.time()
        
        try:
            # 执行角色选择
            result = self._do_selection(state)
            
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
""")

print("\n" + "=" * 80)
print("💡 核心要点")
print("=" * 80)
print("""
1. ✅ 在角色选择后立即调用 record_selection()
2. ✅ 定期调用 generate_summary() 查看统计
3. ✅ 每月调用 export_report() 生成分析报告
4. ✅ 使用统计数据优化 keywords 和角色配置
5. ✅ 通过 success=False 追踪失败案例
""")

print("\n" + "=" * 80)
print("📚 完整文档")
print("=" * 80)
print("""
详细使用指南: docs/ANALYTICS_USAGE_GUIDE.md

包含:
- 完整API参考
- 集成示例代码
- 最佳实践建议
- 常见问题解答
- 性能优化技巧
""")

print("\n" + "=" * 80)
print("🚀 快速测试")
print("=" * 80)
print("""
运行以下命令测试监控系统:

cd intelligent_project_analyzer
python -c "
from services.role_selection_analytics import RoleSelectionAnalytics

analytics = RoleSelectionAnalytics()
analytics.record_selection(
    user_request='测试: 咖啡馆设计',
    selected_mode='单一专家深潜',
    selected_roles=[{'role_id': '2-2', 'role_name': '商业空间设计总监'}],
    confidence=0.88,
    keywords_matched=['商业空间', '咖啡馆'],
    execution_time_ms=156.3,
    success=True
)
print('✅ 监控系统正常工作')

summary = analytics.generate_summary(period='daily')
print(f'📊 今日记录: {summary.total_selections}条')
"
""")

print("\n" + "=" * 80)
print("✅ 演示完成")
print("=" * 80 + "\n")
