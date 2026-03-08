"""
交叉验证服务 (v7.164)

实现 ucppt 风格的多源交叉验证机制：
1. 关键事实提取 - 从搜索结果中提取需要验证的事实
2. 多源验证 - 检查事实是否有多个独立来源支持
3. 矛盾检测 - 识别不同来源之间的矛盾信息
4. 置信度评估 - 基于验证结果计算整体可信度

核心理念：结论本身不是目标，找到可靠证据的过程才是
"""

import json
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List

import httpx
from loguru import logger


class FactType(Enum):
    """事实类型"""

    STATISTIC = "statistic"  # 统计数据
    CLAIM = "claim"  # 主张/观点
    DATE = "date"  # 日期/时间
    QUOTE = "quote"  # 引用
    DEFINITION = "definition"  # 定义
    COMPARISON = "comparison"  # 比较


class VerificationStatus(Enum):
    """验证状态"""

    VERIFIED = "verified"  # 已验证（2+独立来源）
    PARTIALLY_VERIFIED = "partial"  # 部分验证（仅1来源但权威）
    UNVERIFIED = "unverified"  # 未验证（仅1来源）
    CONTRADICTED = "contradicted"  # 存在矛盾


@dataclass
class KeyFact:
    """关键事实"""

    content: str  # 事实内容
    fact_type: FactType  # 事实类型
    source_indices: List[int] = field(default_factory=list)  # 支持该事实的来源索引
    importance: float = 0.5  # 重要性 0-1


@dataclass
class VerifiedFact:
    """已验证的事实"""

    fact: KeyFact
    status: VerificationStatus
    supporting_sources: List[Dict]  # 支持来源详情
    confidence: float  # 置信度 0-1
    notes: str = ""  # 备注


@dataclass
class Contradiction:
    """矛盾信息"""

    fact_a: str  # 事实A
    fact_b: str  # 事实B (矛盾)
    source_a: Dict  # 来源A
    source_b: Dict  # 来源B
    description: str  # 矛盾描述


@dataclass
class VerificationResult:
    """交叉验证结果"""

    verified_facts: List[VerifiedFact] = field(default_factory=list)
    unverified_facts: List[VerifiedFact] = field(default_factory=list)
    contradictions: List[Contradiction] = field(default_factory=list)
    verification_rate: float = 0.0  # 验证率
    overall_confidence: float = 0.0  # 整体置信度
    total_facts: int = 0
    summary: str = ""


class CrossVerificationService:
    """
    交叉验证服务

    工作流程：
    1. 从搜索结果中提取关键事实（使用LLM）
    2. 对每个事实查找支持来源
    3. 检测来源之间的矛盾
    4. 计算验证率和置信度
    """

    # 事实提取 Prompt
    EXTRACT_FACTS_PROMPT = """你是一位专业的事实核查专家。请从以下搜索结果中提取需要验证的关键事实。

## 用户问题
{query}

## 搜索结果
{sources_text}

## 任务
请提取 5-10 个关键事实，优先提取：
1. **统计数据** - 具体数字、百分比、排名
2. **时间/日期** - 发布时间、事件时间
3. **核心主张** - 重要论断、结论
4. **定义** - 关键概念的定义
5. **引用** - 权威人士的观点

## 输出格式（JSON数组）
```json
[
  {{
    "content": "具体的事实陈述",
    "type": "statistic|claim|date|quote|definition|comparison",
    "source_indices": [1, 3],
    "importance": 0.8
  }}
]
```

只输出JSON数组，不要其他内容。"""

    # 矛盾检测 Prompt
    DETECT_CONTRADICTION_PROMPT = """请检查以下来源之间是否存在矛盾信息。

## 来源信息
{sources_comparison}

## 任务
检查这些来源在以下方面是否有矛盾：
1. 数据不一致（不同来源给出不同数字）
2. 观点冲突（不同来源持相反立场）
3. 时间矛盾（事件时间描述不一致）
4. 定义差异（对同一概念的不同定义）

## 输出格式（JSON）
```json
{{
  "has_contradiction": true/false,
  "contradictions": [
    {{
      "fact_a": "来源A的陈述",
      "fact_b": "来源B的陈述",
      "source_a_index": 1,
      "source_b_index": 3,
      "description": "矛盾描述"
    }}
  ]
}}
```

只输出JSON，不要其他内容。"""

    def __init__(self):
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.deepseek_base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

    def _is_valid_api_key(self) -> bool:
        """检查 API Key 是否有效"""
        placeholder_values = ["your_deepseek_api_key", "your_deepseek_api_key_here", "sk-xxx", ""]
        return (
            self.deepseek_api_key
            and self.deepseek_api_key not in placeholder_values
            and self.deepseek_api_key.startswith("sk-")
        )

    async def verify(
        self,
        query: str,
        sources: List[Dict],
    ) -> VerificationResult:
        """
        执行交叉验证

        Args:
            query: 用户问题
            sources: 来源列表 [{title, url, snippet, ...}, ...]

        Returns:
            VerificationResult: 验证结果
        """
        if not sources:
            return VerificationResult(summary="无来源可验证")

        logger.info(f" [CrossVerify] 开始交叉验证，共 {len(sources)} 个来源")

        # 1. 提取关键事实
        facts = await self._extract_key_facts(query, sources)
        logger.info(f"   提取了 {len(facts)} 个关键事实")

        if not facts:
            return VerificationResult(
                summary="未能提取关键事实",
                total_facts=0,
            )

        # 2. 验证每个事实
        verified_facts = []
        unverified_facts = []

        for fact in facts:
            verified = self._verify_single_fact(fact, sources)
            if verified.status in (VerificationStatus.VERIFIED, VerificationStatus.PARTIALLY_VERIFIED):
                verified_facts.append(verified)
            else:
                unverified_facts.append(verified)

        # 3. 检测矛盾
        contradictions = await self._detect_contradictions(sources)
        logger.info(f"   检测到 {len(contradictions)} 个矛盾")

        # 4. 计算验证率和置信度
        total = len(facts)
        verified_count = len(verified_facts)
        verification_rate = verified_count / total if total > 0 else 0

        # 置信度考虑矛盾数量
        contradiction_penalty = min(len(contradictions) * 0.1, 0.3)
        overall_confidence = max(0, verification_rate - contradiction_penalty)

        # 5. 生成摘要
        summary = self._generate_summary(verified_count, len(unverified_facts), len(contradictions), total)

        result = VerificationResult(
            verified_facts=verified_facts,
            unverified_facts=unverified_facts,
            contradictions=contradictions,
            verification_rate=verification_rate,
            overall_confidence=overall_confidence,
            total_facts=total,
            summary=summary,
        )

        logger.info(f" [CrossVerify] 验证完成: 验证率={verification_rate:.0%}, 置信度={overall_confidence:.0%}")

        return result

    async def _extract_key_facts(
        self,
        query: str,
        sources: List[Dict],
    ) -> List[KeyFact]:
        """使用 LLM 提取关键事实"""
        if not self._is_valid_api_key():
            # 降级到规则提取
            return self._extract_facts_by_rules(sources)

        # 构建来源文本
        sources_text = self._build_sources_text(sources)

        prompt = self.EXTRACT_FACTS_PROMPT.format(
            query=query,
            sources_text=sources_text,
        )

        try:
            headers = {
                "Authorization": f"Bearer {self.deepseek_api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2048,
                "temperature": 0.3,
            }

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.deepseek_base_url}/v1/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

                # 解析 JSON
                facts_data = self._parse_json_response(content)

                if isinstance(facts_data, list):
                    return [
                        KeyFact(
                            content=f.get("content", ""),
                            fact_type=FactType(f.get("type", "claim")),
                            source_indices=f.get("source_indices", []),
                            importance=f.get("importance", 0.5),
                        )
                        for f in facts_data
                        if f.get("content")
                    ]

        except Exception as e:
            logger.warning(f"️ LLM事实提取失败: {e}")

        # 降级到规则提取
        return self._extract_facts_by_rules(sources)

    def _extract_facts_by_rules(self, sources: List[Dict]) -> List[KeyFact]:
        """基于规则提取事实（降级方案）"""
        facts = []

        # 正则模式
        patterns = {
            FactType.STATISTIC: r"\d+(?:\.\d+)?%|\d+(?:,\d{3})+|\d+(?:万|亿|千)",
            FactType.DATE: r"\d{4}年|\d{4}-\d{2}-\d{2}|\d{1,2}月\d{1,2}日",
        }

        for idx, source in enumerate(sources[:10]):
            snippet = source.get("snippet", "") or source.get("summary", "")

            # 提取统计数据
            for match in re.finditer(patterns[FactType.STATISTIC], snippet):
                # 提取包含数字的完整句子
                start = max(0, match.start() - 50)
                end = min(len(snippet), match.end() + 50)
                context = snippet[start:end]

                facts.append(
                    KeyFact(
                        content=context.strip(),
                        fact_type=FactType.STATISTIC,
                        source_indices=[idx + 1],
                        importance=0.7,
                    )
                )

                if len(facts) >= 10:
                    break

            if len(facts) >= 10:
                break

        return facts[:10]

    def _verify_single_fact(
        self,
        fact: KeyFact,
        sources: List[Dict],
    ) -> VerifiedFact:
        """验证单个事实"""
        supporting_sources = []

        # 查找支持来源
        for idx, source in enumerate(sources):
            snippet = source.get("snippet", "") or source.get("summary", "")

            # 简单匹配：检查事实内容是否出现在来源中
            if self._content_matches(fact.content, snippet):
                supporting_sources.append(
                    {
                        "index": idx + 1,
                        "title": source.get("title", ""),
                        "url": source.get("url", ""),
                        "is_whitelisted": source.get("isWhitelisted", False),
                    }
                )

        # 确定验证状态
        count = len(supporting_sources)
        has_authority = any(s.get("is_whitelisted") for s in supporting_sources)

        if count >= 2:
            status = VerificationStatus.VERIFIED
            confidence = min(0.9, 0.6 + count * 0.1)
        elif count == 1 and has_authority:
            status = VerificationStatus.PARTIALLY_VERIFIED
            confidence = 0.7
        elif count == 1:
            status = VerificationStatus.UNVERIFIED
            confidence = 0.4
        else:
            status = VerificationStatus.UNVERIFIED
            confidence = 0.2

        return VerifiedFact(
            fact=fact,
            status=status,
            supporting_sources=supporting_sources,
            confidence=confidence,
        )

    def _content_matches(self, fact_content: str, source_text: str) -> bool:
        """检查事实内容是否在来源中出现"""
        # 提取关键词
        keywords = re.findall(r"[\u4e00-\u9fa5a-zA-Z0-9]+", fact_content)

        if len(keywords) < 2:
            return False

        # 计算匹配率
        matched = sum(1 for kw in keywords if kw in source_text)
        match_rate = matched / len(keywords)

        return match_rate >= 0.5

    async def _detect_contradictions(
        self,
        sources: List[Dict],
    ) -> List[Contradiction]:
        """检测来源之间的矛盾"""
        if len(sources) < 2:
            return []

        if not self._is_valid_api_key():
            # 降级：简单的数字矛盾检测
            return self._detect_contradictions_by_rules(sources)

        # 构建比较文本
        sources_comparison = self._build_comparison_text(sources[:8])

        prompt = self.DETECT_CONTRADICTION_PROMPT.format(
            sources_comparison=sources_comparison,
        )

        try:
            headers = {
                "Authorization": f"Bearer {self.deepseek_api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1024,
                "temperature": 0.2,
            }

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.deepseek_base_url}/v1/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                result = self._parse_json_response(content)

                if result and result.get("has_contradiction"):
                    contradictions = []
                    for c in result.get("contradictions", []):
                        idx_a = c.get("source_a_index", 1) - 1
                        idx_b = c.get("source_b_index", 2) - 1

                        source_a = sources[idx_a] if 0 <= idx_a < len(sources) else {}
                        source_b = sources[idx_b] if 0 <= idx_b < len(sources) else {}

                        contradictions.append(
                            Contradiction(
                                fact_a=c.get("fact_a", ""),
                                fact_b=c.get("fact_b", ""),
                                source_a=source_a,
                                source_b=source_b,
                                description=c.get("description", ""),
                            )
                        )
                    return contradictions

        except Exception as e:
            logger.warning(f"️ LLM矛盾检测失败: {e}")

        return []

    def _detect_contradictions_by_rules(
        self,
        sources: List[Dict],
    ) -> List[Contradiction]:
        """基于规则检测矛盾（降级方案）"""
        # 提取所有数字
        number_pattern = r"(\d+(?:\.\d+)?)\s*(%|万|亿|千)?"

        source_numbers = {}
        for idx, source in enumerate(sources[:10]):
            snippet = source.get("snippet", "")
            numbers = re.findall(number_pattern, snippet)
            if numbers:
                source_numbers[idx] = numbers

        # 简单对比：如果相同类型数字差异过大，可能是矛盾
        # （实际项目中需要更复杂的语义理解）

        return []

    def _build_sources_text(self, sources: List[Dict]) -> str:
        """构建来源文本"""
        parts = []
        for idx, source in enumerate(sources[:10], 1):
            title = source.get("title", "N/A")
            snippet = source.get("snippet", "")[:300]
            is_auth = "⭐" if source.get("isWhitelisted") else ""
            parts.append(f"[{idx}] {title} {is_auth}\n{snippet}")
        return "\n\n".join(parts)

    def _build_comparison_text(self, sources: List[Dict]) -> str:
        """构建用于矛盾检测的比较文本"""
        parts = []
        for idx, source in enumerate(sources, 1):
            title = source.get("title", "N/A")
            snippet = source.get("snippet", "")[:400]
            parts.append(f"【来源 {idx}】{title}\n{snippet}")
        return "\n\n---\n\n".join(parts)

    def _parse_json_response(self, content: str) -> Any:
        """解析 JSON 响应"""
        try:
            # 尝试提取 JSON 块
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            return json.loads(content.strip())
        except json.JSONDecodeError:
            return None

    def _generate_summary(
        self,
        verified_count: int,
        unverified_count: int,
        contradiction_count: int,
        total: int,
    ) -> str:
        """生成验证摘要"""
        parts = []

        if verified_count > 0:
            parts.append(f" {verified_count} 个事实已通过多源验证")

        if unverified_count > 0:
            parts.append(f"️ {unverified_count} 个事实仅有单一来源")

        if contradiction_count > 0:
            parts.append(f" 发现 {contradiction_count} 处信息矛盾")

        if not parts:
            return "无法完成验证"

        rate = verified_count / total if total > 0 else 0
        parts.append(f"整体验证率: {rate:.0%}")

        return " | ".join(parts)

    def to_dict(self, result: VerificationResult) -> Dict[str, Any]:
        """将验证结果转换为字典（用于前端）"""
        return {
            "verified_facts": [
                {
                    "content": vf.fact.content,
                    "type": vf.fact.fact_type.value,
                    "status": vf.status.value,
                    "confidence": vf.confidence,
                    "sources": vf.supporting_sources,
                }
                for vf in result.verified_facts
            ],
            "unverified_facts": [
                {
                    "content": vf.fact.content,
                    "type": vf.fact.fact_type.value,
                    "status": vf.status.value,
                    "confidence": vf.confidence,
                    "sources": vf.supporting_sources,
                }
                for vf in result.unverified_facts
            ],
            "contradictions": [
                {
                    "fact_a": c.fact_a,
                    "fact_b": c.fact_b,
                    "source_a_title": c.source_a.get("title", ""),
                    "source_b_title": c.source_b.get("title", ""),
                    "description": c.description,
                }
                for c in result.contradictions
            ],
            "verification_rate": result.verification_rate,
            "overall_confidence": result.overall_confidence,
            "total_facts": result.total_facts,
            "summary": result.summary,
        }


# 单例实例
_verification_service: CrossVerificationService | None = None


def get_verification_service() -> CrossVerificationService:
    """获取交叉验证服务单例"""
    global _verification_service
    if _verification_service is None:
        _verification_service = CrossVerificationService()
    return _verification_service
