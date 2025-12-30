"""
运行时监控系统演示脚本 (Analytics Demo)

快速验证监控系统的功能:
1. 记录模拟的角色选择数据
2. 生成统计报告
3. 展示分析能力

运行方式:
    python intelligent_project_analyzer/examples/analytics_demo.py
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from intelligent_project_analyzer.services.role_selection_analytics import RoleSelectionAnalytics
from datetime import datetime, timedelta
import random
import time


def demo_basic_recording():
    """演示1: 基础记录功能"""
    print("=" * 80)
    print("演示1: 基础记录功能")
    print("=" * 80)
    
    analytics = RoleSelectionAnalytics()
    
    # 模拟记录5次角色选择
    test_cases = [
        {
            "user_request": "为三代同堂的150㎡住宅做空间设计",
            "selected_mode": "多专家并行",
            "selected_roles": [
                {"role_id": "2-1", "role_name": "居住空间设计总监", "dynamic_role_name": "三代同堂住宅设计专家"},
                {"role_id": "5-1", "role_name": "居住空间运营顾问", "dynamic_role_name": "家庭生活模式分析师"}
            ],
            "confidence": 0.92,
            "keywords_matched": ["居住空间设计", "三代同堂", "住宅"],
            "execution_time_ms": 245.6,
            "success": True
        },
        {
            "user_request": "打造宋代美学主题精品酒店",
            "selected_mode": "动态角色合成",
            "selected_roles": [
                {"role_id": "3-3+2-4+5-4", "role_name": "文化驱动的酒店体验设计专家", "dynamic_role_name": "宋代美学酒店总设计师"}
            ],
            "confidence": 0.88,
            "keywords_matched": ["文化转译", "酒店设计", "主题酒店", "美学"],
            "execution_time_ms": 312.8,
            "success": True
        },
        {
            "user_request": "新零售体验店设计",
            "selected_mode": "多专家并行",
            "selected_roles": [
                {"role_id": "3-2", "role_name": "品牌叙事专家", "dynamic_role_name": "零售品牌故事专家"},
                {"role_id": "2-2", "role_name": "商业空间设计总监", "dynamic_role_name": "新零售空间设计师"},
                {"role_id": "5-2", "role_name": "商业零售运营顾问", "dynamic_role_name": "坪效优化专家"}
            ],
            "confidence": 0.95,
            "keywords_matched": ["品牌叙事", "商业空间设计", "零售运营", "坪效"],
            "execution_time_ms": 198.3,
            "success": True
        },
        {
            "user_request": "咖啡馆设计",
            "selected_mode": "单一专家深潜",
            "selected_roles": [
                {"role_id": "2-2", "role_name": "商业空间设计总监", "dynamic_role_name": "精品咖啡馆设计专家"}
            ],
            "confidence": 0.90,
            "keywords_matched": ["商业空间设计", "咖啡馆"],
            "execution_time_ms": 156.2,
            "success": True
        },
        {
            "user_request": "办公空间改造",
            "selected_mode": "单一专家深潜",
            "selected_roles": [
                {"role_id": "2-3", "role_name": "办公空间设计总监", "dynamic_role_name": "现代办公空间设计师"}
            ],
            "confidence": 0.87,
            "keywords_matched": ["办公空间设计", "办公"],
            "execution_time_ms": 178.9,
            "success": True
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        analytics.record_selection(**case)
        print(f"✅ 记录 {i}/{len(test_cases)}: {case['user_request'][:30]}... (置信度: {case['confidence']:.2%})")
        time.sleep(0.1)  # 模拟时间间隔
    
    print(f"\n✅ 成功记录 {len(test_cases)} 条数据\n")


def demo_statistics():
    """演示2: 统计分析功能"""
    print("=" * 80)
    print("演示2: 统计分析功能")
    print("=" * 80)
    
    analytics = RoleSelectionAnalytics()
    
    # 生成今日统计
    summary = analytics.generate_summary(period="daily")
    
    print(f"\n📊 今日统计摘要:")
    print(f"   总选择次数: {summary.total_selections}")
    print(f"   成功率: {summary.success_rate:.1%}")
    print(f"   平均置信度: {summary.avg_confidence:.2%}")
    print(f"   平均响应时间: {summary.avg_execution_time_ms:.1f}ms")
    
    print(f"\n🎯 协同模式分布:")
    for mode, count in summary.mode_distribution.items():
        percentage = (count / summary.total_selections * 100) if summary.total_selections > 0 else 0
        print(f"   {mode}: {count}次 ({percentage:.1f}%)")
    
    print(f"\n⭐ 热门角色 Top 5:")
    for i, (role_id, count) in enumerate(summary.top_roles[:5], 1):
        print(f"   {i}. {role_id}: {count}次")
    
    print(f"\n🔑 高频Keywords Top 10:")
    for i, (keyword, count) in enumerate(summary.top_keywords[:10], 1):
        print(f"   {i}. {keyword}: {count}次")
    
    print()


def demo_report_generation():
    """演示3: 报告生成功能"""
    print("=" * 80)
    print("演示3: 报告生成功能")
    print("=" * 80)
    
    analytics = RoleSelectionAnalytics()
    
    # 生成统计摘要
    summary = analytics.generate_summary(period="daily")
    
    # 导出Markdown报告
    report_path = analytics.export_report(summary, format="markdown")
    
    print(f"\n📄 报告已生成: {report_path}")
    print(f"   格式: Markdown")
    print(f"   大小: {report_path.stat().st_size} bytes")
    
    # 显示报告预览
    print(f"\n📋 报告预览 (前500字符):")
    print("-" * 80)
    with open(report_path, 'r', encoding='utf-8') as f:
        preview = f.read(500)
        print(preview)
        if len(preview) >= 500:
            print("...")
    print("-" * 80)
    print()


def demo_advanced_queries():
    """演示4: 高级查询功能"""
    print("=" * 80)
    print("演示4: 高级查询功能")
    print("=" * 80)
    
    analytics = RoleSelectionAnalytics()
    
    # 角色使用统计
    print("\n📊 角色使用统计 (最近30天):")
    role_stats = analytics.get_role_usage_stats(days=30)
    for i, (role_id, count) in enumerate(role_stats[:5], 1):
        print(f"   {i}. {role_id}: {count}次")
    
    # Keywords统计
    print("\n🔑 Keywords统计 (最近30天):")
    keyword_stats = analytics.get_keyword_stats(days=30)
    for i, (keyword, count) in enumerate(keyword_stats[:5], 1):
        print(f"   {i}. {keyword}: {count}次")
    
    # 失败案例
    failures = analytics.get_failed_selections(days=7)
    print(f"\n⚠️ 最近7天失败案例: {len(failures)}个")
    if failures:
        for record in failures[:3]:
            print(f"   - {record.user_request[:40]}...")
            print(f"     错误: {record.error_message}")
    
    print()


def demo_optimization_suggestions():
    """演示5: 智能优化建议"""
    print("=" * 80)
    print("演示5: 智能优化建议")
    print("=" * 80)
    
    analytics = RoleSelectionAnalytics()
    summary = analytics.generate_summary(period="daily")
    
    print("\n🎯 基于数据的优化建议:")
    
    suggestions_count = 0
    
    # 建议1: 置信度分析
    if summary.avg_confidence < 0.85:
        suggestions_count += 1
        print(f"\n   {suggestions_count}. ⚠️ 平均置信度偏低 ({summary.avg_confidence:.2%})")
        print("      建议: 检查keywords匹配逻辑,补充缺失的关键词")
        print("      参考: docs/KEYWORDS_GUIDELINE.md")
    else:
        suggestions_count += 1
        print(f"\n   {suggestions_count}. ✅ 置信度良好 ({summary.avg_confidence:.2%})")
        print("      当前表现优秀,继续保持")
    
    # 建议2: 响应时间分析
    if summary.avg_execution_time_ms > 300:
        suggestions_count += 1
        print(f"\n   {suggestions_count}. ⚠️ 平均响应时间偏慢 ({summary.avg_execution_time_ms:.0f}ms)")
        print("      建议: 优化LLM调用次数或缓存常用结果")
        print("      目标: <300ms")
    else:
        suggestions_count += 1
        print(f"\n   {suggestions_count}. ✅ 响应时间优秀 ({summary.avg_execution_time_ms:.0f}ms)")
        print("      性能表现良好")
    
    # 建议3: 协同模式分布分析
    if summary.mode_distribution:
        suggestions_count += 1
        total = summary.total_selections
        single_expert = summary.mode_distribution.get("单一专家深潜", 0)
        
        if single_expert / total > 0.7:
            print(f"\n   {suggestions_count}. ⚠️ 单一专家模式占比过高 ({single_expert/total:.1%})")
            print("      建议: 检查是否需要增加跨界场景的识别能力")
        else:
            print(f"\n   {suggestions_count}. ✅ 协同模式分布合理")
            print(f"      单一专家: {single_expert/total:.1%}")
            print(f"      多专家并行: {summary.mode_distribution.get('多专家并行', 0)/total:.1%}")
            print(f"      动态合成: {summary.mode_distribution.get('动态角色合成', 0)/total:.1%}")
    
    # 建议4: 角色使用频率分析
    if summary.top_roles:
        suggestions_count += 1
        top_role_id, top_role_count = summary.top_roles[0]
        usage_rate = top_role_count / summary.total_selections
        
        if usage_rate > 0.4:
            print(f"\n   {suggestions_count}. ⚠️ 角色 {top_role_id} 使用频率过高 ({usage_rate:.1%})")
            print("      建议: 考虑拆分角色职责或检查选择逻辑")
        else:
            print(f"\n   {suggestions_count}. ✅ 角色使用分布均衡")
            print(f"      最高频角色 {top_role_id} 占比 {usage_rate:.1%}")
    
    print()


def main():
    """主函数"""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "运行时监控系统演示 (Analytics Demo)" + " " * 23 + "║")
    print("╚" + "═" * 78 + "╝")
    print()
    
    try:
        # 演示1: 记录数据
        demo_basic_recording()
        
        # 演示2: 统计分析
        demo_statistics()
        
        # 演示3: 报告生成
        demo_report_generation()
        
        # 演示4: 高级查询
        demo_advanced_queries()
        
        # 演示5: 优化建议
        demo_optimization_suggestions()
        
        # 总结
        print("=" * 80)
        print("✅ 演示完成!")
        print("=" * 80)
        print("\n📚 更多信息请参考:")
        print("   - 使用指南: docs/ANALYTICS_USAGE_GUIDE.md")
        print("   - 源码: services/role_selection_analytics.py")
        print("   - P0优化文档: docs/P0_OPTIMIZATION_README.md")
        print()
        
    except Exception as e:
        print(f"\n❌ 演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
