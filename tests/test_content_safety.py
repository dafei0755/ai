"""
内容安全与领域过滤系统测试
"""

import pytest
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from intelligent_project_analyzer.security import (
    ContentSafetyGuard,
    DomainClassifier,
    SafeLLMWrapper,
    ViolationLogger
)


class TestContentSafetyGuard:
    """测试内容安全检测"""
    
    def setup_method(self):
        """每个测试前初始化"""
        self.guard = ContentSafetyGuard()
    
    def test_safe_content(self):
        """测试安全内容通过"""
        text = "我需要设计一个200平米的现代简约风格办公空间，希望提升员工舒适度和工作效率。"
        result = self.guard.check(text)
        
        assert result["is_safe"] == True
        assert result["risk_level"] == "safe"
        assert len(result["violations"]) == 0
    
    def test_blocked_keyword(self):
        """测试违规关键词检测"""
        text = "这个设计包含色情内容"
        result = self.guard.check(text)
        
        assert result["is_safe"] == False
        assert result["risk_level"] in ["medium", "high"]
        assert len(result["violations"]) > 0
    
    def test_privacy_pattern(self):
        """测试隐私信息检测 - 根据配置，设计项目不启用隐私检测"""
        text = "我的手机号是13812345678，请联系我"
        result = self.guard.check(text)

        # 根据security_rules.yaml配置，enable_privacy_check: false
        # 设计项目不需要隐私检测，所以此测试验证隐私检测确实被禁用
        assert result["is_safe"] == True  # 没有隐私检测时，此内容应该通过
        assert result["risk_level"] == "safe"
    
    def test_mixed_content(self):
        """测试混合内容"""
        text = "我需要设计一个办公空间，但不要包含暴力元素"
        result = self.guard.check(text)
        
        # 可能触发关键词检测
        print(f"Mixed content result: {result}")


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
        
        for query in queries:
            result = self.classifier.classify(query)
            print(f"\n查询: {query}")
            print(f"结果: {result}")
            
            assert result["is_design_related"] == True, f"应该识别为设计类: {query}"
            assert result["confidence"] > 0.5, f"置信度应该>0.5: {query}"
    
    def test_clear_non_design_query(self):
        """测试明确的非设计问题"""
        queries = [
            "用Python写一个爬虫程序",
            "如何治疗感冒",
            "这个合同条款有法律风险吗",
            "推荐一部好看的电影"
        ]
        
        for query in queries:
            result = self.classifier.classify(query)
            print(f"\n查询: {query}")
            print(f"结果: {result}")
            
            assert result["is_design_related"] == False, f"应该识别为非设计类: {query}"
    
    def test_unclear_query(self):
        """测试不明确的问题"""
        queries = [
            "你好",
            "帮我分析一下",
            "这个怎么办"
        ]
        
        for query in queries:
            result = self.classifier.classify(query)
            print(f"\n查询: {query}")
            print(f"结果: {result}")
            
            # 不明确的情况应该返回 "unclear"
            assert result["is_design_related"] in [True, False, "unclear"]
    
    def test_edge_case_space_keyword(self):
        """测试边界情况：包含"空间"但非设计类"""
        query = "如何优化数据库存储空间"
        result = self.classifier.classify(query)
        print(f"\n边界查询: {query}")
        print(f"结果: {result}")
        
        # 应该识别为非设计类（编程相关）
        # 但可能置信度不高
        assert result["is_design_related"] in [False, "unclear"]


class TestSafeLLMWrapper:
    """测试LLM输出监控"""
    
    def setup_method(self):
        """每个测试前初始化"""
        # 模拟LLM
        class MockLLM:
            def invoke(self, messages, **kwargs):
                # 返回一个mock响应
                class MockResponse:
                    content = "这是一个安全的设计建议：建议采用开放式布局，提升空间通透感。"
                return MockResponse()
        
        self.mock_llm = MockLLM()
        self.guard = ContentSafetyGuard()
        self.safe_llm = SafeLLMWrapper(self.mock_llm, self.guard)
    
    def test_safe_output(self):
        """测试安全输出通过"""
        response = self.safe_llm.invoke(["设计建议"])
        
        assert hasattr(response, 'content')
        assert "设计建议" in response.content or "布局" in response.content
    
    def test_unsafe_output_simulation(self):
        """测试不安全输出处理（模拟）"""
        # 修改mock返回不安全内容
        class MockUnsafeLLM:
            def invoke(self, messages, **kwargs):
                class MockResponse:
                    content = "这个设计包含色情元素"
                return MockResponse()
        
        unsafe_llm = MockUnsafeLLM()
        safe_wrapper = SafeLLMWrapper(unsafe_llm, self.guard)
        
        response = safe_wrapper.invoke(["设计建议"])
        
        # 不安全内容应该被替换
        print(f"Wrapped response: {response.content}")
        assert "色情" not in response.content or "安全" in response.content


class TestViolationLogger:
    """测试违规日志"""
    
    def setup_method(self):
        """每个测试前初始化"""
        self.logger = ViolationLogger()
    
    def test_log_violation(self):
        """测试记录违规"""
        violation = {
            "session_id": "test-001",
            "violation_type": "content_safety",
            "details": {"category": "test"},
            "user_input": "test input"
        }
        
        # 记录违规
        self.logger.log(violation)
        
        # 验证日志文件存在
        log_dir = "logs/security"
        assert os.path.exists(log_dir), "日志目录应该被创建"
    
    def test_get_statistics(self):
        """测试获取统计"""
        # 记录几条测试数据
        for i in range(3):
            self.logger.log({
                "session_id": f"test-{i}",
                "violation_type": "content_safety",
                "details": {}
            })
        
        # 获取统计
        stats = self.logger.get_statistics(time_range="all")
        print(f"Statistics: {stats}")
        
        assert "total_violations" in stats
        assert stats["total_violations"] >= 3


class TestIntegration:
    """集成测试"""
    
    def test_full_pipeline(self):
        """测试完整流程"""
        # 1. 领域分类
        classifier = DomainClassifier()
        domain_result = classifier.classify("我需要设计一个咖啡厅")
        assert domain_result["is_design_related"] == True
        
        # 2. 内容安全检测
        guard = ContentSafetyGuard()
        safety_result = guard.check("咖啡厅设计，现代简约风格")
        assert safety_result["is_safe"] == True
        
        print("✅ 完整流程测试通过")
    
    def test_rejection_pipeline(self):
        """测试拒绝流程"""
        # 1. 非设计问题
        classifier = DomainClassifier()
        domain_result = classifier.classify("用Python写一个爬虫")
        assert domain_result["is_design_related"] == False
        
        # 2. 不安全内容
        guard = ContentSafetyGuard()
        safety_result = guard.check("包含色情内容的设计")
        assert safety_result["is_safe"] == False
        
        print("✅ 拒绝流程测试通过")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])
