"""
角色权重计算器 - Role Weight Calculator

基于 role_selection_strategy.yaml 配置，计算每个角色的权重分数。

核心功能:
1. 加载客户的权重配置文件
2. 提取需求文本中的关键词（使用 jieba 分词）
3. 匹配标签（persona_narrative, knowledge_aesthetic 等）
4. 计算角色权重（基础权重 + 标签加成）

创建时间: 2025-11-18
版本: 1.0
"""

import yaml
import re
from pathlib import Path
from typing import Dict, List, Any, Set, Optional
from loguru import logger


class RoleWeightCalculator:
    """
    角色权重计算器

    使用场景:
    >>> calculator = RoleWeightCalculator()
    >>> requirements = "为深圳南山一位38岁、英国留学归来的独立女性业主，打造200平米大平层..."
    >>> weights = calculator.calculate_weights(requirements)
    >>> print(weights)
    {'V4_设计研究员': 2.5, 'V3_叙事与体验专家': 2.5, ...}
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化权重计算器

        Args:
            config_path: 配置文件路径，如果为 None 则使用默认路径
        """
        if config_path is None:
            # 使用默认路径
            default_path = Path(__file__).parent.parent / "config" / "role_selection_strategy.yaml"
            config_path = str(default_path)

        self.config_path = Path(config_path)
        self.config = self._load_config()

        # 尝试导入 jieba（用于中文分词）
        try:
            import jieba
            self.jieba = jieba
            self._jieba_available = True
            logger.info("✅ jieba 分词库已加载")
        except ImportError:
            self.jieba = None
            self._jieba_available = False
            logger.warning("⚠️ jieba 未安装，将使用简单分词方法")

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"✅ 已加载权重配置: {self.config_path}")
            logger.info(f"   版本: {config.get('version')}")
            logger.info(f"   策略: {config.get('default_strategy', {}).get('name')}")
            return config
        except Exception as e:
            logger.error(f"❌ 加载配置文件失败: {e}")
            raise

    def calculate_weights(self, requirements: str) -> Dict[str, float]:
        """
        计算角色权重

        Args:
            requirements: 需求文本

        Returns:
            角色权重字典，例如:
            {
                "V4_设计研究员": 2.5,
                "V3_叙事与体验专家": 2.5,
                "V2_设计总监": 2.2,
                ...
            }
        """
        logger.info("🔍 开始计算角色权重...")

        # 1. 提取关键词
        keywords = self._extract_keywords(requirements)
        logger.debug(f"   提取到 {len(keywords)} 个关键词")

        # 2. 匹配标签
        matched_tags = self._match_tags(keywords)
        logger.info(f"   匹配到标签: {matched_tags}")

        # 3. 获取基础权重
        tag_rules = self.config.get("tag_based_rules", {})
        base_weights = tag_rules.get("base_weights", {})

        # 4. 计算每个角色的权重
        weights = {}
        for role_category, base_weight in base_weights.items():
            # 计算标签加成
            tag_bonus = self._calculate_tag_bonus(role_category, matched_tags)

            # 总权重 = 基础权重 + 标签加成
            total_weight = base_weight + tag_bonus
            weights[role_category] = total_weight

            if tag_bonus > 0:
                logger.debug(f"   {role_category}: {base_weight} (基础) + {tag_bonus} (标签) = {total_weight}")

        # 按权重排序（方便查看）
        sorted_weights = dict(sorted(weights.items(), key=lambda x: x[1], reverse=True))

        logger.info(f"📊 权重计算完成:")
        for role, weight in sorted_weights.items():
            logger.info(f"   {role}: {weight:.1f}")

        return sorted_weights

    def _extract_keywords(self, text: str) -> Set[str]:
        """
        提取关键词

        策略:
        1. 如果有 jieba，使用 jieba 分词
        2. 同时提取英文短语（如 "Audrey Hepburn"）
        3. 同时提取原文中的所有字符串片段（用于匹配多字关键词）

        Args:
            text: 需求文本

        Returns:
            关键词集合
        """
        keywords = set()

        # 方法1: 使用 jieba 分词（如果可用）
        if self._jieba_available:
            words = self.jieba.lcut(text)
            keywords.update(words)
        else:
            # 简单分词：按空格、标点分割
            words = re.split(r'[\s,，。！？；：\.\!\?\;]+', text)
            keywords.update([w for w in words if w])

        # 方法2: 提取英文短语（如 "Audrey Hepburn"）
        # 匹配模式：大写字母开头的连续单词
        english_phrases = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        keywords.update(english_phrases)

        # 方法3: 添加原文本（用于匹配多字关键词，如"大平层"）
        # 这样即使分词分开了，仍然可以匹配
        keywords.add(text)

        # 清理空字符串
        keywords = {k.strip() for k in keywords if k.strip()}

        return keywords

    def _match_tags(self, keywords: Set[str]) -> List[str]:
        """
        匹配标签

        Args:
            keywords: 提取的关键词集合

        Returns:
            匹配到的标签列表，例如: ["persona_narrative", "knowledge_aesthetic"]
        """
        matched_tags = []

        tag_rules = self.config.get("tag_based_rules", {})
        tags_config = tag_rules.get("tags", [])

        for tag_config in tags_config:
            tag_name = tag_config.get("tag")
            tag_keywords = tag_config.get("keywords", [])

            # 检查是否有任何关键词匹配
            # 注意：这里使用包含关系，因为 keywords 中有完整文本
            is_match = False
            matched_kws = []

            for tag_kw in tag_keywords:
                # 检查是否有任何提取的关键词包含这个标签关键词
                # 或者标签关键词包含在提取的关键词中
                for extracted_kw in keywords:
                    if tag_kw in extracted_kw or extracted_kw in tag_kw:
                        is_match = True
                        matched_kws.append(tag_kw)
                        break

                if is_match:
                    break

            if is_match:
                matched_tags.append(tag_name)
                logger.debug(f"   ✅ 匹配标签 '{tag_name}': 关键词 {matched_kws}")

        return matched_tags

    def _calculate_tag_bonus(
        self,
        role_category: str,
        matched_tags: List[str]
    ) -> float:
        """
        计算标签加成

        Args:
            role_category: 角色类别（如 "V4_设计研究员"）
            matched_tags: 匹配到的标签列表

        Returns:
            标签加成分数
        """
        bonus = 0.0

        tag_rules = self.config.get("tag_based_rules", {})
        tags_config = tag_rules.get("tags", [])

        for tag_config in tags_config:
            tag_name = tag_config.get("tag")

            # 只计算匹配到的标签
            if tag_name in matched_tags:
                modifiers = tag_config.get("weight_modifiers", {})

                # 如果该角色在这个标签的权重修正中
                if role_category in modifiers:
                    modifier_value = modifiers[role_category]
                    bonus += modifier_value

        return bonus

    def get_weight_explanation(
        self,
        requirements: str,
        weights: Optional[Dict[str, float]] = None
    ) -> str:
        """
        生成权重计算的详细说明

        Args:
            requirements: 需求文本
            weights: 权重字典（如果为 None 则重新计算）

        Returns:
            详细说明文本
        """
        if weights is None:
            weights = self.calculate_weights(requirements)

        keywords = self._extract_keywords(requirements)
        matched_tags = self._match_tags(keywords)

        explanation = f"""
## 权重计算说明

### 需求文本（前100字）
{requirements[:100]}...

### 提取的关键词（部分）
{', '.join(list(keywords)[:20])}

### 匹配的标签
{', '.join(matched_tags) if matched_tags else '无'}

### 计算结果

"""

        tag_rules = self.config.get("tag_based_rules", {})
        base_weights = tag_rules.get("base_weights", {})

        for role, total_weight in weights.items():
            base = base_weights.get(role, 0.0)
            bonus = total_weight - base

            explanation += f"**{role}**: {total_weight:.1f}\n"
            explanation += f"  - 基础权重: {base:.1f}\n"
            if bonus > 0:
                explanation += f"  - 标签加成: +{bonus:.1f}\n"
            explanation += "\n"

        return explanation


# 测试代码（仅在直接运行此文件时执行）
if __name__ == "__main__":
    import sys
    import io

    # 设置 UTF-8 输出编码（Windows 兼容）
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    # 测试用例：Audrey Hepburn 大平层项目
    test_requirements = """
    为深圳南山一位38岁、英国留学归来的独立女性业主，打造一个200平米大平层住宅。
    她热爱 Audrey Hepburn（奥黛丽·赫本）的优雅风格，期望空间能体现"优雅、精致、
    独立、自信"的气质。设计需要融入赫本的美学符号和她所代表的时代精神。
    """

    print("=" * 80)
    print("权重计算器测试")
    print("=" * 80)

    try:
        calculator = RoleWeightCalculator()
        weights = calculator.calculate_weights(test_requirements)

        print("\n" + "=" * 80)
        print("计算结果:")
        print("=" * 80)
        for role, weight in weights.items():
            print(f"{role}: {weight:.1f}")

        print("\n" + "=" * 80)
        print("详细说明:")
        print("=" * 80)
        explanation = calculator.get_weight_explanation(test_requirements, weights)
        print(explanation)

        # 判断 V4 是否被选中
        v4_weight = weights.get("V4_设计研究员", 0.0)
        if v4_weight >= 2.0:
            print(f"\n✅ V4 权重为 {v4_weight:.1f}，应该被选中")
        else:
            print(f"\n⚠️ V4 权重为 {v4_weight:.1f}，可能不会被选中")

    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
