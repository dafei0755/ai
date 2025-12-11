"""
监控系统集成示例 - DynamicProjectDirector

展示如何在实际系统中集成运行时监控功能
"""

import time
from typing import Dict, List, Any
from services.role_selection_analytics import RoleSelectionAnalytics


class DynamicProjectDirectorWithAnalytics:
    """
    集成了监控功能的项目总监类
    
    功能增强:
    1. 自动记录每次角色选择
    2. 追踪执行时间
    3. 记录成功/失败状态
    4. 支持用户反馈收集
    """
    
    def __init__(self):
        """初始化,包括监控系统"""
        # 初始化监控系统
        self.analytics = RoleSelectionAnalytics()
        
        # 其他初始化...
        self.role_library = self._load_role_library()
        
        print("✅ 项目总监已初始化 (已启用监控)")
    
    def select_roles(self, state: Dict) -> Dict:
        """
        角色选择主逻辑 (已集成监控)
        
        Args:
            state: 包含用户输入等信息的状态字典
            
        Returns:
            包含选择结果的字典
        """
        start_time = time.time()
        user_request = state.get("user_input", "")
        
        try:
            # ========================================
            # 原有角色选择逻辑
            # ========================================
            
            # 1. 分析用户需求
            intent = self._parse_intent(user_request)
            
            # 2. 匹配keywords
            matched_keywords = self._match_keywords(intent)
            
            # 3. 选择协同模式
            collaboration_mode = self._determine_mode(intent, matched_keywords)
            
            # 4. 选择角色
            selected_roles = self._select_roles_by_mode(
                mode=collaboration_mode,
                keywords=matched_keywords,
                intent=intent
            )
            
            # 5. 计算置信度
            confidence = self._calculate_confidence(
                selected_roles=selected_roles,
                matched_keywords=matched_keywords
            )
            
            # 构建返回结果
            result = {
                "selected_roles": selected_roles,
                "collaboration_mode": collaboration_mode,
                "confidence": confidence,
                "matched_keywords": matched_keywords,
                "success": True
            }
            
            # ========================================
            # 📊 监控集成: 记录成功案例
            # ========================================
            execution_time_ms = (time.time() - start_time) * 1000
            
            self.analytics.record_selection(
                user_request=user_request,
                selected_mode=collaboration_mode,
                selected_roles=selected_roles,
                confidence=confidence,
                keywords_matched=matched_keywords,
                execution_time_ms=execution_time_ms,
                success=True
            )
            
            return result
            
        except Exception as e:
            # ========================================
            # 📊 监控集成: 记录失败案例
            # ========================================
            execution_time_ms = (time.time() - start_time) * 1000
            
            self.analytics.record_selection(
                user_request=user_request,
                selected_mode="失败",
                selected_roles=[],
                confidence=0.0,
                keywords_matched=[],
                execution_time_ms=execution_time_ms,
                success=False,
                error_message=str(e)
            )
            
            # 重新抛出异常
            raise
    
    def collect_user_feedback(self, selection_id: int, feedback_score: float):
        """
        收集用户反馈 (可选功能)
        
        Args:
            selection_id: 选择记录ID
            feedback_score: 用户评分 (1-5)
        """
        # 更新反馈到监控系统
        # 注: 这需要在 RoleSelectionAnalytics 中添加 update_feedback 方法
        pass
    
    def get_daily_stats(self) -> Dict:
        """
        获取今日统计 (用于监控看板)
        
        Returns:
            统计数据字典
        """
        summary = self.analytics.generate_summary(period="daily")
        
        return {
            "total_selections": summary.total_selections,
            "success_rate": summary.success_rate,
            "avg_confidence": summary.avg_confidence,
            "avg_execution_time_ms": summary.avg_execution_time_ms,
            "mode_distribution": summary.mode_distribution,
            "top_roles": summary.top_roles[:5]
        }
    
    def generate_weekly_report(self) -> str:
        """
        生成周报 (用于团队复盘)
        
        Returns:
            报告文件路径
        """
        summary = self.analytics.generate_summary(period="weekly")
        report_path = self.analytics.export_report(summary, format="markdown")
        
        return str(report_path)
    
    # ========================================
    # 以下是原有的辅助方法 (简化示例)
    # ========================================
    
    def _load_role_library(self) -> Dict:
        """加载角色库"""
        # 实际实现: 从YAML文件加载
        return {}
    
    def _parse_intent(self, user_request: str) -> Dict:
        """解析用户意图"""
        # 实际实现: 使用LLM解析
        return {
            "primary_goal": "空间设计",
            "project_type": "住宅",
            "complexity": "medium"
        }
    
    def _match_keywords(self, intent: Dict) -> List[str]:
        """匹配keywords"""
        # 实际实现: 基于intent匹配
        return ["居住空间设计", "住宅"]
    
    def _determine_mode(self, intent: Dict, keywords: List[str]) -> str:
        """决定协同模式"""
        # 实际实现: 基于规则或LLM判断
        if len(keywords) > 3:
            return "多专家并行"
        else:
            return "单一专家深潜"
    
    def _select_roles_by_mode(
        self, 
        mode: str, 
        keywords: List[str], 
        intent: Dict
    ) -> List[Dict]:
        """根据模式选择角色"""
        # 实际实现: 从角色库中选择
        return [
            {
                "role_id": "2-1",
                "role_name": "居住空间设计总监",
                "dynamic_role_name": "现代住宅设计专家"
            }
        ]
    
    def _calculate_confidence(
        self, 
        selected_roles: List[Dict], 
        matched_keywords: List[str]
    ) -> float:
        """计算置信度"""
        # 实际实现: 基于匹配度计算
        return 0.88


# ============================================================================
# 使用示例
# ============================================================================

def example_usage():
    """演示如何使用集成了监控的项目总监"""
    
    print("=" * 80)
    print("监控系统集成示例")
    print("=" * 80)
    
    # 1. 初始化项目总监 (自动启用监控)
    director = DynamicProjectDirectorWithAnalytics()
    
    # 2. 模拟3次角色选择
    test_requests = [
        {"user_input": "为三代同堂的150㎡住宅做空间设计"},
        {"user_input": "设计一个精品咖啡馆"},
        {"user_input": "办公空间改造"}
    ]
    
    print("\n📋 执行角色选择:")
    for i, state in enumerate(test_requests, 1):
        print(f"\n请求 {i}: {state['user_input']}")
        result = director.select_roles(state)
        print(f"✅ 选择模式: {result['collaboration_mode']}")
        print(f"   置信度: {result['confidence']:.2%}")
        print(f"   选中角色: {len(result['selected_roles'])}个")
    
    # 3. 查看今日统计
    print("\n" + "=" * 80)
    print("📊 今日统计数据:")
    stats = director.get_daily_stats()
    print(f"   总选择次数: {stats['total_selections']}")
    print(f"   成功率: {stats['success_rate']:.1%}")
    print(f"   平均置信度: {stats['avg_confidence']:.2%}")
    print(f"   平均响应时间: {stats['avg_execution_time_ms']:.1f}ms")
    
    # 4. 生成周报
    print("\n" + "=" * 80)
    print("📄 生成周报:")
    report_path = director.generate_weekly_report()
    print(f"   报告位置: {report_path}")
    
    print("\n" + "=" * 80)
    print("✅ 演示完成")
    print("=" * 80)


if __name__ == "__main__":
    example_usage()
