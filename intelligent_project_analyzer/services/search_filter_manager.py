"""
搜索过滤器管理服务

管理搜索结果的黑名单和白名单配置
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple
from urllib.parse import urlparse

import yaml
from loguru import logger


class SearchFilterManager:
    """
    搜索过滤器管理器

    功能：
    1. 加载和保存黑白名单配置
    2. 验证域名匹配规则
    3. 提供增删改查接口
    4. 支持配置热重载
    5. v7.199: 支持灰名单（查询类型感知过滤）
    """

    def __init__(self, config_path: Path | None = None, register_global: bool = True):
        """
        初始化过滤器管理器

        Args:
            config_path: 配置文件路径，默认为 config/search_filters.yaml
        """
        if config_path is None:
            # 默认配置文件路径
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config" / "search_filters.yaml"

        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self._compiled_regex: Dict[str, re.Pattern] = {}
        self._current_query: str = ""  # v7.199: 当前查询（用于灰名单判断）

        # 加载配置
        self.reload()

        if register_global:
            global _filter_manager
            _filter_manager = self

    def reload(self) -> bool:
        """
        重新加载配置文件

        Returns:
            是否成功加载
        """
        try:
            if not self.config_path.exists():
                logger.warning(f"️ 配置文件不存在: {self.config_path}")
                self._config = self._get_default_config()
                return False

            with open(self.config_path, encoding="utf-8") as f:
                loaded_config = yaml.safe_load(f)

            # 处理空文件或None的情况
            if loaded_config is None:
                logger.warning(f"️ 配置文件为空，使用默认配置: {self.config_path}")
                self._config = self._get_default_config()
                return False

            self._config = loaded_config

            # 预编译正则表达式
            self._compile_regex()

            logger.info(f" 搜索过滤器配置已加载: {self.config_path}")
            return True

        except Exception as e:
            logger.error(f" 加载配置失败: {e}")
            self._config = self._get_default_config()
            return False

    def save(self) -> bool:
        """
        保存配置到文件

        Returns:
            是否成功保存
        """
        try:
            # 更新元信息
            if "metadata" not in self._config:
                self._config["metadata"] = {}

            self._config["metadata"]["last_updated"] = datetime.now().isoformat()

            # 确保目录存在
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            # 保存配置
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(self._config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

            logger.info(f" 配置已保存: {self.config_path}")
            return True

        except Exception as e:
            logger.error(f" 保存配置失败: {e}")
            return False

    def _compile_regex(self):
        """预编译正则表达式"""
        self._compiled_regex = {}

        # 确保配置存在
        if not self._config:
            logger.warning("️ 配置为空，跳过正则表达式编译")
            return

        # 编译黑名单正则
        blacklist = self._config.get("blacklist", {})
        if blacklist:
            regex_list = blacklist.get("regex", [])
            if regex_list:
                for regex_pattern in regex_list:
                    try:
                        self._compiled_regex[f"blacklist_{regex_pattern}"] = re.compile(regex_pattern)
                    except re.error as e:
                        logger.error(f" 黑名单正则表达式编译失败: {regex_pattern} - {e}")

        # 编译白名单正则
        whitelist = self._config.get("whitelist", {})
        if whitelist:
            regex_list = whitelist.get("regex", [])
            if regex_list:
                for regex_pattern in regex_list:
                    try:
                        self._compiled_regex[f"whitelist_{regex_pattern}"] = re.compile(regex_pattern)
                    except re.error as e:
                        logger.error(f" 白名单正则表达式编译失败: {regex_pattern} - {e}")

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "blacklist": {"domains": [], "patterns": [], "regex": [], "notes": {}},
            "whitelist": {"domains": [], "patterns": [], "regex": [], "boost_score": 0.3, "notes": {}},
            "graylist": {"domains": [], "preserve_keywords": [], "notes": {}},  # v7.199
            "metadata": {"version": "1.0.0", "last_updated": datetime.now().isoformat(), "updated_by": "system"},
            "scope": {
                "tools": ["tavily", "serper", "bocha"],
                "enabled": True,
                "priority": "blacklist_first",
                "graylist_enabled": True,
            },
        }

    def is_enabled(self) -> bool:
        """检查过滤器是否启用"""
        scope = self._config.get("scope") or {}
        return scope.get("enabled", True)

    def is_graylist_enabled(self) -> bool:
        """v7.199: 检查灰名单是否启用"""
        scope = self._config.get("scope") or {}
        return scope.get("graylist_enabled", True)

    def set_current_query(self, query: str) -> None:
        """v7.199: 设置当前查询（用于灰名单判断）"""
        self._current_query = query

    def _should_preserve_graylist(self, url: str) -> bool:
        """
        v7.199: 判断灰名单URL是否应该保留

        根据当前查询是否包含保留关键词来决定
        """
        if not self._current_query:
            return False  # 无查询时默认过滤

        graylist = self._config.get("graylist") or {}
        preserve_keywords = graylist.get("preserve_keywords") or []

        # 检查查询是否包含任何保留关键词
        query_lower = self._current_query.lower()
        for keyword in preserve_keywords:
            if keyword.lower() in query_lower:
                return True

        return False

    def is_graylisted(self, url: str) -> bool:
        """
        v7.199: 检查URL是否在灰名单中

        Args:
            url: 要检查的URL

        Returns:
            是否在灰名单中
        """
        if not self.is_graylist_enabled():
            return False

        try:
            url_domain = self._normalize_domain(url)
            url_variants = self._get_domain_variants(url_domain)

            graylist = self._config.get("graylist") or {}
            graylist_domains = graylist.get("domains") or []

            for config_domain in graylist_domains:
                normalized_config = self._normalize_domain(config_domain)
                config_variants = self._get_domain_variants(normalized_config)

                if url_variants & config_variants:
                    return True

                if self._is_subdomain_of(url_domain, normalized_config):
                    return True

            return False

        except Exception as e:
            logger.error(f" 灰名单检查失败: {url} - {e}")
            return False

    def should_filter_url(self, url: str, query: str = "") -> Tuple[bool, str]:
        """
        v7.199: 综合判断URL是否应该被过滤

        Args:
            url: 要检查的URL
            query: 当前搜索查询（用于灰名单判断）

        Returns:
            (should_filter, reason) - 是否过滤及原因
        """
        # 设置当前查询
        if query:
            self.set_current_query(query)

        # 1. 白名单优先
        if self.is_whitelisted(url):
            return False, "whitelist"

        # 2. 黑名单检查
        if self.is_blacklisted(url):
            return True, "blacklist"

        # 3. 灰名单检查（查询感知）
        if self.is_graylisted(url):
            if self._should_preserve_graylist(url):
                logger.debug(f" 灰名单保留: {url} (查询包含保留关键词)")
                return False, "graylist_preserved"
            else:
                logger.debug(f" 灰名单过滤: {url} (查询不包含保留关键词)")
                return True, "graylist_filtered"

        return False, "allowed"

    def _normalize_domain(self, domain_or_url: str) -> str:
        """
        标准化域名格式，提取纯域名

        支持以下格式：
        - https://www.example.com/path -> www.example.com
        - http://www.example.com -> www.example.com
        - www.example.com -> www.example.com
        - example.com -> example.com

        Args:
            domain_or_url: 域名或URL

        Returns:
            标准化后的域名（小写）
        """
        domain = domain_or_url.strip().lower()

        # 如果包含协议，使用 urlparse 提取
        if domain.startswith(("http://", "https://")):
            parsed = urlparse(domain)
            domain = parsed.netloc

        # 移除末尾的斜杠和路径
        domain = domain.split("/")[0]

        # 移除端口号
        domain = domain.split(":")[0]

        return domain

    def _get_domain_variants(self, domain: str) -> Set[str]:
        """
        获取域名的所有变体形式

        Args:
            domain: 标准化后的域名

        Returns:
            域名变体集合
        """
        variants = {domain}

        # 添加/移除 www 前缀
        if domain.startswith("www."):
            variants.add(domain[4:])  # 移除 www.
        else:
            variants.add(f"www.{domain}")  # 添加 www.

        return variants

    def _extract_root_domain(self, domain: str) -> str:
        """
        提取主域名（根域名）

        例如:
        - sub.example.com -> example.com
        - a.b.example.com -> example.com
        - www.example.com -> example.com
        - example.com -> example.com
        - example.co.uk -> example.co.uk (保留二级国家域名)

        Args:
            domain: 标准化后的域名

        Returns:
            主域名
        """
        # 移除 www 前缀
        if domain.startswith("www."):
            domain = domain[4:]

        parts = domain.split(".")

        # 处理特殊的二级国家域名 (如 .co.uk, .com.cn, .org.cn 等)
        special_second_level = {
            "co.uk",
            "org.uk",
            "ac.uk",
            "gov.uk",
            "com.cn",
            "org.cn",
            "net.cn",
            "gov.cn",
            "edu.cn",
            "com.hk",
            "org.hk",
            "edu.hk",
            "gov.hk",
            "com.tw",
            "org.tw",
            "edu.tw",
            "gov.tw",
            "co.jp",
            "or.jp",
            "ne.jp",
            "ac.jp",
            "go.jp",
            "com.au",
            "org.au",
            "net.au",
            "edu.au",
            "gov.au",
        }

        if len(parts) >= 3:
            # 检查是否是特殊二级域名
            potential_sld = ".".join(parts[-2:])
            if potential_sld in special_second_level:
                # 返回 domain.co.uk 格式
                return ".".join(parts[-3:])

        # 普通情况：返回最后两部分
        if len(parts) >= 2:
            return ".".join(parts[-2:])

        return domain

    def _is_subdomain_of(self, url_domain: str, config_domain: str) -> bool:
        """
        检查 url_domain 是否是 config_domain 的子域名

        例如:
        - sub.example.com 是 example.com 的子域名 -> True
        - a.b.example.com 是 example.com 的子域名 -> True
        - example.com 是 example.com 的子域名 -> True (自身匹配)
        - other.com 是 example.com 的子域名 -> False

        Args:
            url_domain: URL 中提取的域名
            config_domain: 配置中的域名

        Returns:
            是否是子域名
        """
        # 移除 www 前缀进行比较
        url_clean = url_domain[4:] if url_domain.startswith("www.") else url_domain
        config_clean = config_domain[4:] if config_domain.startswith("www.") else config_domain

        # 完全匹配
        if url_clean == config_clean:
            return True

        # 子域名匹配：url_domain 以 .config_domain 结尾
        if url_clean.endswith("." + config_clean):
            return True

        return False

    def is_blacklisted(self, url: str) -> bool:
        """
        检查 URL 是否在黑名单中

        支持子域名自动匹配：配置 example.com 会自动屏蔽 sub.example.com

        Args:
            url: 要检查的 URL

        Returns:
            是否在黑名单中
        """
        if not self.is_enabled():
            return False

        try:
            # 提取并标准化域名
            url_domain = self._normalize_domain(url)
            url_variants = self._get_domain_variants(url_domain)

            blacklist = self._config.get("blacklist") or {}
            blacklist_domains = blacklist.get("domains") or []

            # 1. 检查域名匹配（支持多种格式 + 子域名自动匹配）
            for config_domain in blacklist_domains:
                # 标准化配置中的域名
                normalized_config = self._normalize_domain(config_domain)
                config_variants = self._get_domain_variants(normalized_config)

                # 1a. 精确匹配（包含 www 变体）
                if url_variants & config_variants:
                    logger.debug(f" 黑名单匹配: {url_domain} ~ {normalized_config}")
                    return True

                # 1b. 子域名匹配：配置主域名自动屏蔽所有子域名
                if self._is_subdomain_of(url_domain, normalized_config):
                    logger.debug(f" 黑名单匹配（子域名）: {url_domain} ~ {normalized_config}")
                    return True

            # 2. 检查通配符匹配
            for pattern in blacklist.get("patterns") or []:
                for variant in url_variants:
                    if self._match_wildcard(variant, pattern):
                        logger.debug(f" 黑名单匹配（通配符）: {variant} ~ {pattern}")
                        return True

            # 3. 检查正则表达式匹配
            for regex_pattern in blacklist.get("regex") or []:
                compiled = self._compiled_regex.get(f"blacklist_{regex_pattern}")
                if compiled:
                    for variant in url_variants:
                        if compiled.match(variant):
                            logger.debug(f" 黑名单匹配（正则）: {variant} ~ {regex_pattern}")
                            return True

            return False

        except Exception as e:
            logger.error(f" 黑名单检查失败: {url} - {e}")
            return False

    def is_whitelisted(self, url: str) -> bool:
        """
        检查 URL 是否在白名单中

        支持子域名自动匹配：配置 example.com 会自动包含 sub.example.com

        Args:
            url: 要检查的 URL

        Returns:
            是否在白名单中
        """
        if not self.is_enabled():
            return False

        try:
            # 提取并标准化域名
            url_domain = self._normalize_domain(url)
            url_variants = self._get_domain_variants(url_domain)

            whitelist = self._config.get("whitelist") or {}
            whitelist_domains = whitelist.get("domains") or []

            # 1. 检查域名匹配（支持多种格式 + 子域名自动匹配）
            for config_domain in whitelist_domains:
                # 标准化配置中的域名
                normalized_config = self._normalize_domain(config_domain)
                config_variants = self._get_domain_variants(normalized_config)

                # 1a. 精确匹配（包含 www 变体）
                if url_variants & config_variants:
                    return True

                # 1b. 子域名匹配：配置主域名自动包含所有子域名
                if self._is_subdomain_of(url_domain, normalized_config):
                    return True

            # 2. 检查通配符匹配
            for pattern in whitelist.get("patterns") or []:
                for variant in url_variants:
                    if self._match_wildcard(variant, pattern):
                        return True

            # 3. 检查正则表达式匹配
            for regex_pattern in whitelist.get("regex") or []:
                compiled = self._compiled_regex.get(f"whitelist_{regex_pattern}")
                if compiled:
                    for variant in url_variants:
                        if compiled.match(variant):
                            return True

            return False

        except Exception as e:
            logger.error(f" 白名单检查失败: {url} - {e}")
            return False

    def _match_wildcard(self, domain: str, pattern: str) -> bool:
        """
        通配符匹配

        Args:
            domain: 域名
            pattern: 通配符模式（支持 * 通配符）

        Returns:
            是否匹配
        """
        # 将通配符转换为正则表达式
        regex_pattern = pattern.replace(".", r"\.").replace("*", r".*")
        regex_pattern = f"^{regex_pattern}$"

        try:
            return bool(re.match(regex_pattern, domain))
        except re.error:
            return False

    def get_boost_score(self) -> float:
        """获取白名单提升分数"""
        return self._config.get("whitelist", {}).get("boost_score", 0.3)

    def _check_duplicate(self, domain: str, existing_list: List[str], list_type: str = "blacklist") -> str | None:
        """
         v7.171: 检查是否存在重复或冗余的域名

        检查规则：
        1. 完全相同的域名
        2. www 变体（example.com 和 www.example.com 视为相同）
        3. 子域名冗余（已有 example.com，再添加 sub.example.com 是多余的）
        4. 父域名覆盖（已有 sub.example.com，添加 example.com 会覆盖它）

        Args:
            domain: 要添加的域名
            existing_list: 现有域名列表
            list_type: 列表类型（blacklist/whitelist）

        Returns:
            如果存在重复/冗余，返回冲突的域名；否则返回 None
        """
        normalized_new = self._normalize_domain(domain)
        new_variants = self._get_domain_variants(normalized_new)

        for existing in existing_list:
            normalized_existing = self._normalize_domain(existing)
            existing_variants = self._get_domain_variants(normalized_existing)

            # 1. 完全匹配（包含 www 变体）
            if new_variants & existing_variants:
                return existing

            # 2. 新域名是现有域名的子域名（冗余）
            if self._is_subdomain_of(normalized_new, normalized_existing):
                return f"{existing} (已覆盖此子域名)"

            # 3. 新域名是现有域名的父域名（会覆盖现有的）
            if self._is_subdomain_of(normalized_existing, normalized_new):
                return f"{existing} (将被新域名覆盖)"

        return None

    def add_to_blacklist(self, domain: str, match_type: str = "domains", note: str | None = None) -> bool:
        """
        添加到黑名单

        Args:
            domain: 域名或模式
            match_type: 匹配类型（domains/patterns/regex）
            note: 备注说明

        Returns:
            是否成功添加
        """
        try:
            if "blacklist" not in self._config:
                self._config["blacklist"] = {"domains": [], "patterns": [], "regex": [], "notes": {}}

            blacklist = self._config["blacklist"]

            #  v7.171: 增强重复检查
            if match_type == "domains":
                existing_list = blacklist.get("domains", [])
                duplicate = self._check_duplicate(domain, existing_list, "blacklist")
                if duplicate:
                    logger.warning(f"️ 黑名单中已存在相似域名: {domain} -> {duplicate}")
                    return False
            else:
                # 对于 patterns 和 regex，只检查完全相同
                if domain in blacklist.get(match_type, []):
                    logger.warning(f"️ 黑名单中已存在: {domain}")
                    return False

            # 添加到对应列表
            if match_type not in blacklist:
                blacklist[match_type] = []

            blacklist[match_type].append(domain)

            # 添加备注
            if note:
                if "notes" not in blacklist:
                    blacklist["notes"] = {}
                blacklist["notes"][domain] = note

            # 保存配置
            success = self.save()

            if success:
                # 重新加载以更新正则表达式
                self.reload()
                logger.info(f" 已添加到黑名单: {domain} ({match_type})")

            return success

        except Exception as e:
            logger.error(f" 添加到黑名单失败: {domain} - {e}")
            return False

    def remove_from_blacklist(self, domain: str, match_type: str = "domains") -> bool:
        """
        从黑名单移除

        Args:
            domain: 域名或模式
            match_type: 匹配类型

        Returns:
            是否成功移除
        """
        try:
            blacklist = self._config.get("blacklist", {})

            if domain not in blacklist.get(match_type, []):
                logger.warning(f"️ 黑名单中不存在: {domain}")
                return False

            blacklist[match_type].remove(domain)

            # 移除备注
            if "notes" in blacklist and domain in blacklist["notes"]:
                del blacklist["notes"][domain]

            success = self.save()

            if success:
                self.reload()
                logger.info(f" 已从黑名单移除: {domain}")

            return success

        except Exception as e:
            logger.error(f" 从黑名单移除失败: {domain} - {e}")
            return False

    def add_to_whitelist(self, domain: str, match_type: str = "domains", note: str | None = None) -> bool:
        """添加到白名单"""
        try:
            if "whitelist" not in self._config:
                self._config["whitelist"] = {
                    "domains": [],
                    "patterns": [],
                    "regex": [],
                    "boost_score": 0.3,
                    "notes": {},
                }

            whitelist = self._config["whitelist"]

            #  v7.171: 增强重复检查
            if match_type == "domains":
                existing_list = whitelist.get("domains", [])
                duplicate = self._check_duplicate(domain, existing_list, "whitelist")
                if duplicate:
                    logger.warning(f"️ 白名单中已存在相似域名: {domain} -> {duplicate}")
                    return False
            else:
                # 对于 patterns 和 regex，只检查完全相同
                if domain in whitelist.get(match_type, []):
                    logger.warning(f"️ 白名单中已存在: {domain}")
                    return False

            if match_type not in whitelist:
                whitelist[match_type] = []

            whitelist[match_type].append(domain)

            if note:
                if "notes" not in whitelist:
                    whitelist["notes"] = {}
                whitelist["notes"][domain] = note

            success = self.save()

            if success:
                self.reload()
                logger.info(f" 已添加到白名单: {domain} ({match_type})")

            return success

        except Exception as e:
            logger.error(f" 添加到白名单失败: {domain} - {e}")
            return False

    def remove_from_whitelist(self, domain: str, match_type: str = "domains") -> bool:
        """从白名单移除"""
        try:
            whitelist = self._config.get("whitelist", {})

            if domain not in whitelist.get(match_type, []):
                logger.warning(f"️ 白名单中不存在: {domain}")
                return False

            whitelist[match_type].remove(domain)

            if "notes" in whitelist and domain in whitelist["notes"]:
                del whitelist["notes"][domain]

            success = self.save()

            if success:
                self.reload()
                logger.info(f" 已从白名单移除: {domain}")

            return success

        except Exception as e:
            logger.error(f" 从白名单移除失败: {domain} - {e}")
            return False

    def get_config(self) -> Dict[str, Any]:
        """获取完整配置"""
        config = self._config.copy()
        # 确保关键字段不为 None（YAML 中空字段会解析为 None）
        if config.get("blacklist") is None:
            config["blacklist"] = {}
        if config.get("whitelist") is None:
            config["whitelist"] = {}
        if config.get("metadata") is None:
            config["metadata"] = {}
        if config.get("scope") is None:
            config["scope"] = {}
        return config

    def get_blacklist(self) -> Dict[str, Any]:
        """获取黑名单配置"""
        return self._config.get("blacklist") or {}

    def get_whitelist(self) -> Dict[str, Any]:
        """获取白名单配置"""
        return self._config.get("whitelist") or {}

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        # 使用 or {} 确保不为 None（YAML 中空字段会解析为 None）
        blacklist = self._config.get("blacklist") or {}
        whitelist = self._config.get("whitelist") or {}

        return {
            "blacklist": {
                "domains": len(blacklist.get("domains") or []),
                "patterns": len(blacklist.get("patterns") or []),
                "regex": len(blacklist.get("regex") or []),
                "total": sum(
                    [
                        len(blacklist.get("domains") or []),
                        len(blacklist.get("patterns") or []),
                        len(blacklist.get("regex") or []),
                    ]
                ),
            },
            "whitelist": {
                "domains": len(whitelist.get("domains") or []),
                "patterns": len(whitelist.get("patterns") or []),
                "regex": len(whitelist.get("regex") or []),
                "total": sum(
                    [
                        len(whitelist.get("domains") or []),
                        len(whitelist.get("patterns") or []),
                        len(whitelist.get("regex") or []),
                    ]
                ),
            },
            "enabled": self.is_enabled(),
            "last_updated": (self._config.get("metadata") or {}).get("last_updated"),
        }


# 全局单例
_filter_manager: SearchFilterManager | None = None


def get_filter_manager() -> SearchFilterManager:
    """获取全局过滤器管理器实例"""
    global _filter_manager
    if _filter_manager is None:
        _filter_manager = SearchFilterManager()
    return _filter_manager
