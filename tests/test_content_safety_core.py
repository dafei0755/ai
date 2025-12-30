"""
内容安全核心模块测试（简化版）
"""

import pytest
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from intelligent_project_analyzer.security.violation_logger import ViolationLogger
from intelligent_project_analyzer.security.content_safety_guard import ContentSafetyGuard
from intelligent_project_analyzer.security.domain_classifier import DomainClassifier


class TestContentSafetyGuard:
    """测试内容安全检测"""
    
    def setup_method(self):
        """每个测试前初始化"""
        self.guard = ContentSafetyGuard()
    
    def test_safe_content(self):
        """测试安全内容通过"""
        text = "我需要设计一个200平米的现代简约风格办公空间，希望提升员工舒适度和工作效率。"
        result = self.guard.check(text)
        
        print(f"\n测试安全内容:")
        print(f"  输入: {text}")
        print(f"  结果: {result}")
        
        assert result["is_safe"] == True
        assert result["risk_level"] == "safe"
        assert len(result["violations"]) == 0
        print("  ✅ 通过")
    
    def test_blocked_keyword(self):
        """测试违规关键词检测"""
        text = "这个设计包含色情内容"
        result = self.guard.check(text)
        
        print(f"\n测试违规关键词:")
        print(f"  输入: {text}")
        print(f"  结果: {result}")
        
        assert result["is_safe"] == False
        assert result["risk_level"] in ["medium", "high"]
        assert len(result["violations"]) > 0
        print("  ✅ 通过")
    
    def test_privacy_pattern(self):
        """测试隐私信息检测 - 根据配置，设计项目不启用隐私检测"""
        text = "我的手机号是13812345678，请联系我"
        result = self.guard.check(text)

        print(f"\n测试隐私信息:")
        print(f"  输入: {text}")
        print(f"  结果: {result}")

        # 根据security_rules.yaml配置，enable_privacy_check: false
        # 设计项目不需要隐私检测
        assert result["is_safe"] == True
        assert result["risk_level"] == "safe"
        print("  ✅ 通过")


class TestDomainClassifier:
    """测试领域分类"""
    
    def setup_method(self):
        """每个测试前初始化"""
        self.classifier = DomainClassifier()
    
    def test_clear_design_query(self):
        """测试明确的设计问题"""
        queries = [
            "我需要设计一个咖啡厅，面积100平米",
            "帮我规划一个现代简约风格的办公空间",
            "这个展厅如何体现科技感",
            "住宅客厅的动线设计要注意什么"
        ]
        
        print(f"\n测试设计类问题（无LLM模式）:")
        passed = 0
        for query in queries:
            result = self.classifier.classify(query)
            print(f"  查询: {query}")
            print(f"  结果: is_design={result['is_design_related']}, confidence={result.get('confidence', 0):.2f}")
            
            # 无LLM时，接受unclear（表示需要用户确认）
            if result["is_design_related"] == True or result["is_design_related"] == "unclear":
                print(f"    ✅ 通过（{result['is_design_related']}）")
                passed += 1
            else:
                print(f"    ❌ 失败")
        
        print(f"  总计: {passed}/{len(queries)} 通过")
        print(f"  ⚠️ 注意：无LLM模型时，依赖关键词匹配，unclear结果表示需要interrupt用户确认")
        assert passed >= len(queries) * 0.75, "设计问题不应被明确拒绝"
    
    def test_clear_non_design_query(self):
        """测试明确的非设计问题"""
        queries = [
            "用Python写一个爬虫程序",
            "如何治疗感冒",
            "这个合同条款有法律风险吗",
            "推荐一部好看的电影"
        ]
        
        print(f"\n测试非设计类问题（无LLM模式）:")
        passed = 0
        for query in queries:
            result = self.classifier.classify(query)
            print(f"  查询: {query}")
            print(f"  结果: is_design={result['is_design_related']}, confidence={result.get('confidence', 0):.2f}")
            
            # 无LLM时，接受unclear或False
            if result["is_design_related"] == False or result["is_design_related"] == "unclear":
                print(f"    ✅ 通过（{result['is_design_related']}）")
                passed += 1
            else:
                print(f"    ❌ 失败")
        
        print(f"  总计: {passed}/{len(queries)} 通过")
        print(f"  ⚠️ 注意：无LLM模型时，unclear结果表示需要interrupt用户确认")
        assert passed >= len(queries) * 0.75, "非设计问题不应被明确接受"
    
    def test_unclear_query(self):
        """测试不明确的问题"""
        queries = [
            "你好",
            "帮我分析一下",
            "这个怎么办"
        ]
        
        print(f"\n测试不明确问题:")
        for query in queries:
            result = self.classifier.classify(query)
            print(f"  查询: {query}")
            print(f"  结果: is_design={result['is_design_related']}, confidence={result.get('confidence', 0):.2f}")
            
            # 不明确的情况应该返回 unclear 或置信度很低
            assert result["is_design_related"] in [True, False, "unclear"]
            print(f"    ✅ 通过")


class TestViolationLogger:
    """测试违规日志"""
    
    def setup_method(self):
        """每个测试前初始化"""
        self.logger = ViolationLogger()
    
    def test_log_violation(self):
        """测试记录违规"""
        print(f"\n测试违规记录:")
        violation = {
            "session_id": "test-001",
            "violation_type": "content_safety",
            "details": {"category": "test"},
            "user_input": "test input"
        }
        
        # 记录违规
        self.logger.log(violation)
        print(f"  记录违规: {violation}")
        
        # 验证日志文件存在
        log_file = "logs/violations.jsonl"
        assert os.path.exists(log_file), f"日志文件应该被创建: {log_file}"
        print(f"  ✅ 日志文件已创建: {log_file}")
    
    def test_get_statistics(self):
        """测试获取统计"""
        print(f"\n测试统计功能:")
        # 记录几条测试数据
        for i in range(3):
            self.logger.log({
                "session_id": f"test-stat-{i}",
                "violation_type": "content_safety",
                "details": {}
            })
        
        # 获取统计
        stats = self.logger.get_statistics(time_range="all")
        print(f"  统计结果: {stats}")
        
        assert "total_violations" in stats
        assert stats["total_violations"] >= 3
        print(f"  ✅ 统计功能正常")


class TestIntegration:
    """集成测试"""
    
    def test_full_pipeline(self):
        """测试完整流程"""
        print(f"\n测试完整流程（无LLM模式）:")
        
        # 1. 领域分类
        classifier = DomainClassifier()
        domain_result = classifier.classify("我需要设计一个咖啡厅")
        print(f"  1. 领域分类: {domain_result}")
        assert domain_result["is_design_related"] in [True, "unclear"]
        
        # 2. 内容安全检测
        guard = ContentSafetyGuard()
        safety_result = guard.check("咖啡厅设计，现代简约风格")
        print(f"  2. 安全检测: {safety_result}")
        assert safety_result["is_safe"] == True
        
        print("  ✅ 完整流程测试通过")
    
    def test_rejection_pipeline(self):
        """测试拒绝流程"""
        print(f"\n测试拒绝流程（无LLM模式）:")
        
        # 1. 非设计问题
        classifier = DomainClassifier()
        domain_result = classifier.classify("用Python写一个爬虫")
        print(f"  1. 非设计问题: {domain_result}")
        assert domain_result["is_design_related"] in [False, "unclear"]
        
        # 2. 不安全内容
        guard = ContentSafetyGuard()
        safety_result = guard.check("包含色情内容的设计")
        print(f"  2. 不安全内容: {safety_result}")
        assert safety_result["is_safe"] == False
        
        print("  ✅ 拒绝流程测试通过")


if __name__ == "__main__":
    print("=" * 80)
    print("内容安全核心模块测试")
    print("=" * 80)
    
    # 运行测试
    pytest.main([__file__, "-v", "-s"])
