"""
Few-Shot Example Loader
加载和管理专家角色的Few-Shot学习示例

This module provides utilities to load, filter, and inject Few-Shot examples
into expert prompts to improve output quality and consistency.
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Set

import yaml

try:
    import jieba

    _HAS_JIEBA = True
except ImportError:
    _HAS_JIEBA = False

logger = logging.getLogger(__name__)


@dataclass
class FewShotExample:
    """Few-Shot示例数据类"""

    example_id: str
    description: str
    category: str
    user_request: str
    correct_output: str
    context: Dict[str, Any]


class FewShotExampleLoader:
    """Few-Shot示例加载器（v2 — 内置 IntelligentFewShotSelector 语义检索）"""

    def __init__(
        self,
        examples_dir: Path | None = None,
        selector: Any | None = None,
        usage_tracker: Any | None = None,
    ):
        """
        初始化示例加载器

        Args:
            examples_dir: 示例文件目录，默认为 config/roles/examples/
            selector: IntelligentFewShotSelector 实例（可选，优先用于语义检索）
            usage_tracker: UsageTracker 实例（可选，注入使用数据记录）
        """
        if examples_dir is None:
            # 默认路径
            current_file = Path(__file__)
            self.examples_dir = current_file.parent.parent / "config" / "roles" / "examples"
        else:
            self.examples_dir = Path(examples_dir)

        self._cache: Dict[str, List[FewShotExample]] = {}
        self._selector = selector        # IntelligentFewShotSelector（可选）
        self._usage_tracker = usage_tracker  # UsageTracker（可选）
        logger.info(f" Few-Shot示例加载器初始化: {self.examples_dir} selector={'智能' if selector else '关键词'}")

    def load_examples_for_role(self, role_id: str) -> List[FewShotExample]:
        """
        加载指定角色的所有示例

        Args:
            role_id: 角色ID，如 "V2_0"

        Returns:
            示例列表
        """
        # 检查缓存
        if role_id in self._cache:
            return self._cache[role_id]

        # 构造文件路径
        example_file = self.examples_dir / f"{role_id.lower()}_examples.yaml"

        if not example_file.exists():
            logger.warning(f"️ 未找到角色 {role_id} 的示例文件: {example_file}")
            return []

        try:
            # 加载YAML文件
            with open(example_file, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            # 解析示例
            examples = []
            for ex_data in data.get("examples", []):
                example = FewShotExample(
                    example_id=ex_data["example_id"],
                    description=ex_data["description"],
                    category=ex_data["category"],
                    user_request=ex_data["user_request"],
                    correct_output=ex_data["correct_output"],
                    context=ex_data.get("context", {}),
                )
                examples.append(example)

            # 缓存
            self._cache[role_id] = examples

            logger.info(f" 成功加载 {len(examples)} 个Few-Shot示例 for {role_id}")
            return examples

        except Exception as e:
            logger.error(f" 加载示例文件失败 {example_file}: {e}")
            return []

    def get_relevant_examples(
        self, role_id: str, user_request: str, category: str | None = None, max_examples: int = 2
    ) -> List[FewShotExample]:
        """
        获取最相关的Few-Shot示例

        Args:
            role_id: 角色ID
            user_request: 用户请求内容
            category: 过滤类别（targeted_mode/comprehensive_mode）
            max_examples: 最多返回的示例数

        Returns:
            相关示例列表
        """
        all_examples = self.load_examples_for_role(role_id)

        if not all_examples:
            return []

        # 过滤类别
        if category:
            filtered = [ex for ex in all_examples if ex.category == category]
        else:
            filtered = all_examples

        # ── 优先使用 IntelligentFewShotSelector 语义检索 ────────────────
        if self._selector is not None:
            try:
                role_examples = self._selector.select_relevant_examples(
                    role_id=role_id,
                    user_query=user_request,
                    top_k=max_examples,
                    category=category,
                )
                # 将 intelligence.FewShotExample 转换为 utils.FewShotExample（兼容）
                result: List[FewShotExample] = []
                for se in role_examples:
                    result.append(
                        FewShotExample(
                            example_id=getattr(se, "example_id", se.example_id),
                            description=getattr(se, "description", ""),
                            category=getattr(se, "category", category or ""),
                            user_request=getattr(se, "user_request", ""),
                            correct_output=getattr(se, "correct_output", ""),
                            context=getattr(se, "context", {}),
                        )
                    )
                logger.debug(f" [智能检索] 为请求选择了 {len(result)} 个相关示例")
                return result
            except Exception as e:
                logger.warning(f"️ 智能检索失败，回退到关键词匹配: {e}")

        # ── 回退：关键词相似度匹配 ────────────────────────────────────────
        scored_examples = []
        for example in filtered:
            score = self._calculate_similarity(user_request, example.user_request)
            scored_examples.append((score, example))

        # 排序并返回top-k
        scored_examples.sort(key=lambda x: x[0], reverse=True)
        top_examples = [ex for _, ex in scored_examples[:max_examples]]

        # 记录使用数据
        if self._usage_tracker is not None and top_examples:
            try:
                self._usage_tracker.log_expert_usage(
                    role_id=role_id,
                    user_request=user_request,
                    selected_examples=[ex.example_id for ex in top_examples],
                )
            except Exception:
                pass

        logger.debug(f" [关键词匹配] 为请求选择了 {len(top_examples)} 个相关示例")
        return top_examples

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        计算两个文本的相似度（中文分词 + Jaccard）

        Args:
            text1: 文本1
            text2: 文本2

        Returns:
            相似度分数 (0-1)
        """
        keywords1 = self._tokenize(text1)
        keywords2 = self._tokenize(text2)

        if not keywords1 or not keywords2:
            return 0.0

        # Jaccard相似度
        intersection = keywords1 & keywords2
        union = keywords1 | keywords2

        similarity = len(intersection) / len(union) if union else 0.0
        return similarity

    @staticmethod
    def _tokenize(text: str) -> Set[str]:
        """
        中文友好的分词方法

        优先使用 jieba 分词；不可用时回退到字符级 bigram + 空格分词混合策略，
        确保中文文本能产生有意义的 token。

        Args:
            text: 输入文本

        Returns:
            token 集合（已去除停用词和单字符）
        """
        if not text:
            return set()

        # 统一标点为空格
        cleaned = re.sub(r"[？?！!，。、；：\u201c\u201d\u2018\u2019（）()\[\]【】\s]+", " ", text)

        # 停用词（高频无意义词）
        stopwords = {
            "的",
            "了",
            "是",
            "在",
            "和",
            "与",
            "及",
            "或",
            "等",
            "为",
            "对",
            "将",
            "从",
            "到",
            "以",
            "中",
            "上",
            "下",
            "之",
            "有",
            "不",
            "也",
            "都",
            "而",
            "被",
            "这",
            "那",
            "它",
            "他",
            "她",
            "如何",
            "什么",
            "怎样",
            "为什么",
            "哪些",
            "可以",
            "需要",
            "进行",
            "通过",
            "实现",
            "使用",
            "包括",
            "以及",
            "其中",
        }

        if _HAS_JIEBA:
            # jieba 精确分词
            tokens = set(jieba.lcut(cleaned))
            # 过滤：去除停用词、单字符、纯数字
            tokens = {
                t.strip()
                for t in tokens
                if len(t.strip()) >= 2 and t.strip() not in stopwords and not t.strip().isdigit()
            }
        else:
            # 回退策略：空格分词 + 字符级 bigram
            tokens = set()
            # 1) 空格分词（处理英文和已有空格分隔的部分）
            for word in cleaned.split():
                if len(word) >= 2 and word not in stopwords:
                    tokens.add(word)
            # 2) 中文字符 bigram（滑动窗口）
            chinese_chars = re.findall(r"[\u4e00-\u9fff]+", text)
            for segment in chinese_chars:
                for i in range(len(segment) - 1):
                    bigram = segment[i : i + 2]
                    if bigram not in stopwords:
                        tokens.add(bigram)

        return tokens

    def format_examples_for_prompt(self, examples: List[FewShotExample], include_context: bool = False) -> str:
        """
        将示例格式化为可注入到提示词的文本

        Args:
            examples: 示例列表
            include_context: 是否包含上下文信息

        Returns:
            格式化的示例文本
        """
        if not examples:
            return ""

        prompt_section = "###  高质量输出示例（Few-Shot Examples）\n\n"
        prompt_section += "以下是同类任务的高质量输出示例，请严格参照格式和结构输出：\n\n"

        for idx, example in enumerate(examples, 1):
            prompt_section += f"#### 示例 {idx}: {example.description}\n\n"

            if include_context and example.context:
                prompt_section += f"**上下文**: {example.context}\n\n"

            prompt_section += f'**用户请求**: "{example.user_request}"\n\n'
            prompt_section += f"**正确输出** (请参考此格式):\n```json\n{example.correct_output}\n```\n\n"
            prompt_section += "---\n\n"

        prompt_section += "️ **关键要求**: 你的输出必须遵循上述示例的JSON结构，特别注意：\n"
        prompt_section += "1. `deliverable_outputs[].content` 字段必须是string类型（不要输出嵌套对象）\n"
        prompt_section += "2. `confidence` 必须是0-1之间的浮点数\n"
        prompt_section += "3. 输出必须是有效的JSON格式，不要有markdown代码块标记\n\n"

        return prompt_section


# 全局单例
_global_loader: FewShotExampleLoader | None = None


def get_few_shot_loader() -> FewShotExampleLoader:
    """获取全局 Few-Shot 加载器单例（已注入 IntelligentFewShotSelector + UsageTracker）"""
    global _global_loader
    if _global_loader is None:
        # 尝试注入智能组件（依赖缺失时优雅降级）
        selector = None
        tracker = None
        try:
            from intelligent_project_analyzer.intelligence.intelligent_few_shot_selector import (
                DEPENDENCIES_AVAILABLE,
                IntelligentFewShotSelector,
            )
            from intelligent_project_analyzer.intelligence.usage_tracker import UsageTracker

            tracker = UsageTracker()
            if DEPENDENCIES_AVAILABLE:
                selector = IntelligentFewShotSelector(usage_tracker=tracker)
                logger.info("[few_shot_loader] 已注入 IntelligentFewShotSelector + UsageTracker")
            else:
                logger.info("[few_shot_loader] 语义检索依赖不可用，仅注入 UsageTracker")
        except Exception as _e:
            logger.debug(f"[few_shot_loader] 智能组件加载失败，使用纯关键词模式: {_e}")

        _global_loader = FewShotExampleLoader(selector=selector, usage_tracker=tracker)
    return _global_loader
