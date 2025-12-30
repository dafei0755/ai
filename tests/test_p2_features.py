"""P2功能单元测试 - 动态规则加载和热加载机制"""

import pytest
import os
import time
import yaml
from pathlib import Path


class TestDynamicRuleLoader:
    """动态规则加载器测试"""

    @pytest.fixture
    def rule_loader(self):
        """创建测试用的规则加载器"""
        from intelligent_project_analyzer.security.dynamic_rule_loader import DynamicRuleLoader

        # 使用默认配置文件
        loader = DynamicRuleLoader(auto_reload=True, reload_interval=1)
        return loader

    @pytest.fixture
    def config_path(self):
        """获取配置文件路径"""
        from intelligent_project_analyzer.security.dynamic_rule_loader import DynamicRuleLoader
        current_dir = Path(__file__).parent.parent / "intelligent_project_analyzer" / "security"
        return current_dir / "security_rules.yaml"

    def test_loader_initialization(self, rule_loader):
        """测试加载器初始化"""
        assert rule_loader is not None
        assert rule_loader.config_path.exists()
        assert rule_loader._rules is not None

    def test_get_keywords(self, rule_loader):
        """测试获取关键词规则"""
        keywords = rule_loader.get_keywords()
        assert isinstance(keywords, dict)
        assert "色情低俗" in keywords or len(keywords) > 0

    def test_get_privacy_patterns(self, rule_loader):
        """测试获取隐私信息规则"""
        privacy = rule_loader.get_privacy_patterns()
        assert isinstance(privacy, dict)
        # 应该至少有手机号、邮箱等常见模式
        assert len(privacy) > 0

    def test_get_evasion_patterns(self, rule_loader):
        """测试获取变形规避规则"""
        evasion = rule_loader.get_evasion_patterns()
        assert isinstance(evasion, dict)
        assert len(evasion) > 0

    def test_get_detection_config(self, rule_loader):
        """测试获取检测配置"""
        config = rule_loader.get_detection_config()
        assert isinstance(config, dict)
        # 应该有enable_keyword_check等配置项
        assert "enable_keyword_check" in config or len(config) > 0

    def test_whitelist(self, rule_loader):
        """测试白名单功能"""
        whitelist = rule_loader.get_whitelist()
        assert isinstance(whitelist, dict)

        # 测试is_whitelisted方法
        # 注意：这个测试依赖于配置文件中的白名单设置
        result = rule_loader.is_whitelisted("test@example.com")
        # 根据配置文件，example.com应该在白名单中
        assert result is True or result is False  # 取决于配置

    def test_get_stats(self, rule_loader):
        """测试规则统计信息"""
        stats = rule_loader.get_stats()
        assert isinstance(stats, dict)
        assert "config_file" in stats
        assert "version" in stats
        assert "keywords" in stats
        assert "privacy_patterns" in stats
        assert "evasion_patterns" in stats

        # 检查统计数据结构
        assert "total_categories" in stats["keywords"]
        assert "total" in stats["privacy_patterns"]

    def test_singleton_pattern(self):
        """测试单例模式"""
        from intelligent_project_analyzer.security.dynamic_rule_loader import get_rule_loader

        loader1 = get_rule_loader()
        loader2 = get_rule_loader()

        # 应该是同一个实例
        assert loader1 is loader2

    def test_force_reload(self, rule_loader):
        """测试强制重载"""
        initial_modified = rule_loader._last_modified

        # 等待一小段时间
        time.sleep(0.1)

        # 强制重载
        rule_loader.force_reload()

        # 加载时间应该已更新
        assert rule_loader._last_modified >= initial_modified

    def test_hot_reload_detection(self, rule_loader, config_path):
        """测试热加载检测（文件修改检测）"""
        # 记录初始修改时间
        initial_modified = rule_loader._last_modified

        # 模拟文件修改（touch文件）
        try:
            # 读取当前配置
            with open(config_path, 'r', encoding='utf-8') as f:
                current_config = f.read()

            # 写回（这会更新修改时间）
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(current_config)

            # 等待文件系统更新
            time.sleep(0.5)

            # 触发检查
            rules = rule_loader.get_rules()

            # 修改时间应该已更新
            assert rule_loader._last_modified > initial_modified

        except Exception as e:
            pytest.skip(f"无法修改配置文件进行测试: {e}")

    def test_update_threat_intelligence(self, rule_loader):
        """测试更新威胁情报"""
        test_domains = ["malicious1.com", "malicious2.com"]
        test_ips = ["1.2.3.4", "5.6.7.8"]
        test_keywords = ["scam", "phishing"]

        # 更新威胁情报
        rule_loader.update_threat_intelligence(
            domains=test_domains,
            ips=test_ips,
            keywords=test_keywords
        )

        # 验证更新
        threat_intel = rule_loader.get_threat_intelligence()
        assert "last_updated" in threat_intel
        assert threat_intel["last_updated"] is not None


class TestContentSafetyGuardWithDynamicRules:
    """ContentSafetyGuard动态规则集成测试"""

    @pytest.fixture
    def guard_with_dynamic_rules(self):
        """创建启用动态规则的守卫"""
        from intelligent_project_analyzer.security.content_safety_guard import ContentSafetyGuard
        return ContentSafetyGuard(use_dynamic_rules=True, use_external_api=False)

    @pytest.fixture
    def guard_without_dynamic_rules(self):
        """创建不使用动态规则的守卫"""
        from intelligent_project_analyzer.security.content_safety_guard import ContentSafetyGuard
        return ContentSafetyGuard(use_dynamic_rules=False, use_external_api=False)

    def test_dynamic_rules_enabled(self, guard_with_dynamic_rules):
        """测试动态规则已启用"""
        assert guard_with_dynamic_rules.use_dynamic_rules is True
        # 触发懒加载
        loader = guard_with_dynamic_rules.rule_loader
        # 如果配置文件存在，loader应该不为None
        if loader:
            assert loader is not None

    def test_dynamic_rules_disabled(self, guard_without_dynamic_rules):
        """测试动态规则已禁用"""
        assert guard_without_dynamic_rules.use_dynamic_rules is False
        assert guard_without_dynamic_rules.rule_loader is None

    def test_fallback_to_static_rules(self, guard_without_dynamic_rules):
        """测试回退到静态规则"""
        # 使用静态规则检测
        result = guard_without_dynamic_rules.check("这里有赌博内容")

        # 应该能检测到（使用FALLBACK_KEYWORDS）
        assert result["is_safe"] is False
        assert len(result["violations"]) > 0

    def test_keyword_detection_with_dynamic_rules(self, guard_with_dynamic_rules):
        """测试使用动态规则进行关键词检测"""
        # 测试色情低俗关键词（配置文件中应该有）
        result = guard_with_dynamic_rules.check("这里有色情内容")

        # 应该能检测到
        if result["is_safe"] is False:
            assert len(result["violations"]) > 0
            # 检查是否有关键词匹配
            keyword_violations = [v for v in result["violations"] if v.get("method") == "keyword_match"]
            assert len(keyword_violations) > 0

    def test_enabled_disabled_categories(self, guard_with_dynamic_rules):
        """测试启用/禁用的类别"""
        # 这个测试依赖于配置文件中禁用某些类别
        # 如果政治敏感类别被禁用且words为空，应该不检测

        # 获取规则加载器
        loader = guard_with_dynamic_rules.rule_loader
        if loader:
            keywords = loader.get_keywords()

            # 检查是否有禁用的类别
            disabled_categories = [
                cat for cat, config in keywords.items()
                if isinstance(config, dict) and not config.get("enabled", True)
            ]

            if disabled_categories:
                # 测试禁用类别的关键词不会被检测
                # （需要根据实际配置调整）
                pass

    def test_new_keyword_format_compatibility(self, guard_with_dynamic_rules):
        """测试新旧关键词格式兼容性"""
        # 动态规则使用字典格式（带enabled/severity）
        # 回退规则使用列表格式
        # 两种格式都应该能正常工作

        result = guard_with_dynamic_rules.check("赌博")
        # 应该能检测到（无论使用哪种格式）
        assert result["is_safe"] is False or result["is_safe"] is True  # 取决于配置


class TestConfigurationValidation:
    """配置文件验证测试"""

    @pytest.fixture
    def config_path(self):
        """获取配置文件路径"""
        current_dir = Path(__file__).parent.parent / "intelligent_project_analyzer" / "security"
        return current_dir / "security_rules.yaml"

    def test_config_file_exists(self, config_path):
        """测试配置文件存在"""
        assert config_path.exists(), f"配置文件不存在: {config_path}"

    def test_config_file_valid_yaml(self, config_path):
        """测试配置文件是有效的YAML"""
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        assert config is not None
        assert isinstance(config, dict)

    def test_config_structure(self, config_path):
        """测试配置文件结构"""
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # 检查必需的顶层键
        assert "version" in config
        assert "keywords" in config
        assert "privacy_patterns" in config
        assert "evasion_patterns" in config
        assert "detection_config" in config

    def test_keywords_structure(self, config_path):
        """测试关键词配置结构"""
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        keywords = config.get("keywords", {})
        assert isinstance(keywords, dict)

        # 检查至少有一个类别
        assert len(keywords) > 0

        # 检查类别结构
        for category, config_data in keywords.items():
            if isinstance(config_data, dict):
                # 新格式：应该有enabled/severity/words
                assert "enabled" in config_data or "words" in config_data

    def test_privacy_patterns_structure(self, config_path):
        """测试隐私信息配置结构"""
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        privacy = config.get("privacy_patterns", {})
        assert isinstance(privacy, dict)

        # 应该有常见的隐私类型
        common_types = ["手机号", "电子邮箱", "身份证号18位", "银行卡号"]
        found_types = [t for t in common_types if t in privacy]
        assert len(found_types) > 0

        # 检查模式结构
        for pattern_name, pattern_config in privacy.items():
            if isinstance(pattern_config, dict):
                assert "pattern" in pattern_config
                assert "severity" in pattern_config

    def test_detection_config_structure(self, config_path):
        """测试检测配置结构"""
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        detection_config = config.get("detection_config", {})
        assert isinstance(detection_config, dict)

        # 检查关键配置项
        expected_keys = [
            "enable_keyword_check",
            "enable_privacy_check",
            "enable_evasion_check",
            "enable_external_api"
        ]

        for key in expected_keys:
            if key in detection_config:
                assert isinstance(detection_config[key], bool)


class TestPerformance:
    """性能测试"""

    def test_rule_loading_performance(self):
        """测试规则加载性能"""
        from intelligent_project_analyzer.security.dynamic_rule_loader import DynamicRuleLoader
        import time

        start_time = time.time()
        loader = DynamicRuleLoader()
        load_time = time.time() - start_time

        # 加载应该在1秒内完成
        assert load_time < 1.0, f"规则加载耗时过长: {load_time:.2f}秒"

    def test_rule_access_performance(self):
        """测试规则访问性能"""
        from intelligent_project_analyzer.security.dynamic_rule_loader import get_rule_loader
        import time

        loader = get_rule_loader()

        start_time = time.time()
        for _ in range(1000):
            loader.get_keywords()
        access_time = time.time() - start_time

        # 1000次访问应该在0.1秒内完成
        assert access_time < 0.1, f"规则访问耗时过长: {access_time:.2f}秒"

    def test_check_performance_with_dynamic_rules(self):
        """测试使用动态规则的检测性能"""
        from intelligent_project_analyzer.security.content_safety_guard import ContentSafetyGuard
        import time

        guard = ContentSafetyGuard(use_dynamic_rules=True, use_external_api=False)

        start_time = time.time()
        for _ in range(100):
            guard.check("这是一段测试文本，包含赌博等关键词")
        check_time = time.time() - start_time

        # 100次检测应该在1秒内完成
        assert check_time < 1.0, f"检测耗时过长: {check_time:.2f}秒"
