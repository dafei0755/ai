"""
测试 SearchFilterManager 对空文件和None配置的处理

验证修复：'NoneType' object is not iterable
"""

from pathlib import Path

import pytest
import yaml

from intelligent_project_analyzer.services.search_filter_manager import SearchFilterManager


class TestEmptyFileHandling:
    """测试空文件和None配置的处理"""

    def test_empty_yaml_file(self, tmp_path):
        """测试空YAML文件的处理"""
        # 创建空配置文件
        config_file = tmp_path / "empty_config.yaml"
        config_file.write_text("", encoding="utf-8")

        # 初始化管理器
        manager = SearchFilterManager(config_path=config_file, register_global=False)

        # 验证使用默认配置
        assert manager._config is not None
        assert "blacklist" in manager._config
        assert "whitelist" in manager._config
        assert isinstance(manager._config["blacklist"]["domains"], list)

    def test_yaml_file_with_null(self, tmp_path):
        """测试包含null的YAML文件"""
        # 创建包含null的配置文件
        config_file = tmp_path / "null_config.yaml"
        config_file.write_text("~", encoding="utf-8")  # YAML中的null

        # 初始化管理器
        manager = SearchFilterManager(config_path=config_file, register_global=False)

        # 验证使用默认配置
        assert manager._config is not None
        assert "blacklist" in manager._config

    def test_yaml_file_with_empty_dict(self, tmp_path):
        """测试空字典配置"""
        # 创建空字典配置文件
        config_file = tmp_path / "empty_dict_config.yaml"
        config_file.write_text("{}", encoding="utf-8")

        # 初始化管理器
        manager = SearchFilterManager(config_path=config_file, register_global=False)

        # 验证可以正常工作
        assert manager._config is not None

        # 验证正则编译不会崩溃
        assert manager._compiled_regex is not None

    def test_missing_blacklist_section(self, tmp_path):
        """测试缺少blacklist部分的配置"""
        # 创建不完整的配置文件
        config_file = tmp_path / "incomplete_config.yaml"
        config_data = {"whitelist": {"domains": ["example.com"]}}
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        # 初始化管理器
        manager = SearchFilterManager(config_path=config_file, register_global=False)

        # 验证不会崩溃
        assert manager._config is not None
        assert not manager.is_blacklisted("http://test.com")

    def test_missing_regex_section(self, tmp_path):
        """测试缺少regex部分的配置"""
        # 创建缺少regex部分的配置文件
        config_file = tmp_path / "no_regex_config.yaml"
        config_data = {"blacklist": {"domains": ["spam.com"]}, "whitelist": {"domains": ["good.com"]}}
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        # 初始化管理器
        manager = SearchFilterManager(config_path=config_file, register_global=False)

        # 验证正则编译不会崩溃
        assert manager._compiled_regex is not None

        # 验证基本功能正常
        assert manager.is_blacklisted("http://spam.com")
        assert not manager.is_blacklisted("http://good.com")

    def test_reload_with_none_config(self, tmp_path):
        """测试reload时遇到None配置"""
        # 创建正常配置文件
        config_file = tmp_path / "normal_config.yaml"
        config_data = {"blacklist": {"domains": ["test.com"]}}
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        # 初始化管理器
        manager = SearchFilterManager(config_path=config_file, register_global=False)
        assert manager.is_blacklisted("http://test.com")

        # 修改文件为空
        config_file.write_text("", encoding="utf-8")

        # 重新加载
        result = manager.reload()

        # 验证：应该返回False但不崩溃
        assert result is False
        assert manager._config is not None  # 应该使用默认配置

    def test_malformed_yaml_graceful_handling(self, tmp_path):
        """测试格式错误的YAML文件的优雅处理"""
        # 创建格式错误的YAML文件
        config_file = tmp_path / "malformed_config.yaml"
        config_file.write_text("blacklist:\n  - invalid yaml structure {[", encoding="utf-8")

        # 初始化管理器（应该捕获异常并使用默认配置）
        manager = SearchFilterManager(config_path=config_file, register_global=False)

        # 验证使用默认配置
        assert manager._config is not None
        assert "blacklist" in manager._config
        assert isinstance(manager._config["blacklist"]["domains"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
