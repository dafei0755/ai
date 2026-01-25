"""
搜索过滤器管理服务测试

测试黑白名单的核心功能
"""

from pathlib import Path

import pytest

from intelligent_project_analyzer.services.search_filter_manager import SearchFilterManager, get_filter_manager


class TestSearchFilterManager:
    """测试搜索过滤器管理器"""

    def setup_method(self):
        """每个测试前的设置"""
        # 使用临时配置文件
        self.temp_config = Path("test_search_filters.yaml")
        self.manager = SearchFilterManager(self.temp_config)

    def teardown_method(self):
        """每个测试后的清理"""
        if self.temp_config.exists():
            self.temp_config.unlink()

    def test_initialization(self):
        """测试初始化"""
        assert self.manager is not None
        assert self.manager.is_enabled()

    def test_add_to_blacklist(self):
        """测试添加到黑名单"""
        # 添加完整域名
        success = self.manager.add_to_blacklist("spam.com", "domains", "测试黑名单")
        assert success

        # 验证已添加
        assert self.manager.is_blacklisted("https://spam.com/page")

        # 重复添加应该失败
        success = self.manager.add_to_blacklist("spam.com", "domains")
        assert not success

    def test_add_to_whitelist(self):
        """测试添加到白名单"""
        success = self.manager.add_to_whitelist("trusted.com", "domains", "可信站点")
        assert success

        assert self.manager.is_whitelisted("https://trusted.com/article")

    def test_remove_from_blacklist(self):
        """测试从黑名单移除"""
        # 先添加
        self.manager.add_to_blacklist("remove-me.com", "domains")
        assert self.manager.is_blacklisted("https://remove-me.com")

        # 再移除
        success = self.manager.remove_from_blacklist("remove-me.com", "domains")
        assert success
        assert not self.manager.is_blacklisted("https://remove-me.com")

    def test_wildcard_matching(self):
        """测试通配符匹配"""
        # 添加通配符模式
        self.manager.add_to_blacklist("*.ads.com", "patterns")

        # 测试匹配
        assert self.manager.is_blacklisted("https://banner.ads.com/ad")
        assert self.manager.is_blacklisted("https://popup.ads.com/ad")
        assert not self.manager.is_blacklisted("https://ads.com")  # 不匹配根域名
        assert not self.manager.is_blacklisted("https://goodsite.com")

    def test_regex_matching(self):
        """测试正则表达式匹配"""
        # 添加正则模式
        self.manager.add_to_blacklist(r"^.*\.spam-.*\.com$", "regex")

        # 测试匹配
        assert self.manager.is_blacklisted("https://ads.spam-site.com")
        assert self.manager.is_blacklisted("https://banner.spam-ads.com")
        assert not self.manager.is_blacklisted("https://legitimate.com")

    def test_blacklist_priority(self):
        """测试黑名单优先级"""
        # 同时添加到黑名单和白名单
        self.manager.add_to_blacklist("conflict.com", "domains")
        self.manager.add_to_whitelist("conflict.com", "domains")

        # 黑名单应该优先（虽然这是在应用层逻辑，这里只测试基础检查）
        assert self.manager.is_blacklisted("https://conflict.com")
        assert self.manager.is_whitelisted("https://conflict.com")  # 两个都返回 True

    def test_boost_score(self):
        """测试白名单提升分数"""
        boost_score = self.manager.get_boost_score()
        assert isinstance(boost_score, float)
        assert boost_score > 0

    def test_statistics(self):
        """测试统计信息"""
        # 添加一些规则
        self.manager.add_to_blacklist("spam1.com", "domains")
        self.manager.add_to_blacklist("spam2.com", "domains")
        self.manager.add_to_blacklist("*.ads.*", "patterns")
        self.manager.add_to_whitelist("good1.com", "domains")

        stats = self.manager.get_statistics()

        assert stats["blacklist"]["domains"] == 2
        assert stats["blacklist"]["patterns"] == 1
        assert stats["whitelist"]["domains"] == 1
        assert stats["enabled"] is True

    def test_config_persistence(self):
        """测试配置持久化"""
        # 添加规则
        self.manager.add_to_blacklist("persist.com", "domains", "持久化测试")

        # 创建新实例（重新加载配置）
        new_manager = SearchFilterManager(self.temp_config)

        # 验证配置已持久化
        assert new_manager.is_blacklisted("https://persist.com")

    def test_reload(self):
        """测试配置重载"""
        # 添加规则
        self.manager.add_to_blacklist("before-reload.com", "domains")

        # 手动修改配置文件（模拟外部修改）
        config = self.manager.get_config()
        config["blacklist"]["domains"].append("added-externally.com")

        import yaml

        with open(self.temp_config, "w", encoding="utf-8") as f:
            yaml.dump(config, f, allow_unicode=True)

        # 重载配置
        success = self.manager.reload()
        assert success

        # 验证新规则已加载
        assert self.manager.is_blacklisted("https://added-externally.com")


class TestSearchFilterIntegration:
    """测试与 SearchQualityControl 的集成"""

    def setup_method(self):
        """测试前设置"""
        self.temp_config = Path("test_search_filters_integration.yaml")
        # 先创建过滤器管理器
        self.filter_manager = SearchFilterManager(self.temp_config)
        self.filter_manager.add_to_blacklist("blocked-site.com", "domains")
        self.filter_manager.add_to_whitelist("premium-site.com", "domains")

    def teardown_method(self):
        """测试后清理"""
        if self.temp_config.exists():
            self.temp_config.unlink()

    def test_blacklist_filtering(self):
        """测试黑名单过滤"""
        from intelligent_project_analyzer.tools.quality_control import SearchQualityControl

        qc = SearchQualityControl(enable_filters=True)

        # 准备测试数据
        results = [
            {
                "title": "Good Article",
                "url": "https://goodsite.com/article",
                "content": "This is a good article with sufficient content for testing.",
                "score": 0.8,
            },
            {
                "title": "Blocked Article",
                "url": "https://blocked-site.com/spam",
                "content": "This should be filtered out by blacklist.",
                "score": 0.9,
            },
        ]

        # 处理结果
        processed = qc.process_results(results)

        # 验证黑名单站点被过滤
        assert len(processed) == 1
        assert processed[0]["url"] == "https://goodsite.com/article"

    def test_whitelist_boosting(self):
        """测试白名单优先级提升"""
        from intelligent_project_analyzer.tools.quality_control import SearchQualityControl

        qc = SearchQualityControl(enable_filters=True)

        results = [
            {
                "title": "Normal Article",
                "url": "https://normal-site.com/article",
                "content": "Normal content with sufficient length for testing quality control.",
                "score": 0.7,
            },
            {
                "title": "Premium Article",
                "url": "https://premium-site.com/article",
                "content": "Premium content that should get a boost from whitelist.",
                "score": 0.7,
            },
        ]

        processed = qc.process_results(results)

        # 验证白名单站点排序更靠前
        assert len(processed) == 2
        # 白名单站点应该排在第一位（因为获得了加分）
        assert "premium-site.com" in processed[0]["url"]
        assert processed[0].get("whitelist_boosted") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
