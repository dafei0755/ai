"""LLM semantic router for demand reconstruction.

The router owns Stage 1 understanding only: prompt construction, provider
fallback, repair prompting, JSON parsing, and structural validation. It does not
mutate adapter context or choose final blueprints; the orchestration service
keeps those responsibilities.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, Optional

from loguru import logger

JsonParser = Callable[[str], Any]


class DemandReconstructionSemanticRouter:
    """Build an internal semantic understanding package before rule scanning."""

    def __init__(
        self,
        *,
        llm: Any,
        parse_response_json: JsonParser,
        target_aliases: Dict[str, str],
    ) -> None:
        self._llm = llm
        self._parse_response_json = parse_response_json
        self._target_aliases = dict(target_aliases)

    def build_understanding(self, message: str) -> tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
        if self._llm is None:
            return None, {"status": "not_configured"}
        prompt = self.build_prompt(message, target_aliases=self._target_aliases)
        fallback_instances = getattr(self._llm, "llm_instances", None)
        if isinstance(fallback_instances, dict) and fallback_instances:
            last_diagnostics: Dict[str, Any] = {"status": "fallback_exhausted"}
            for provider, llm in fallback_instances.items():
                package, diagnostics = self.invoke_with_llm(
                    llm=llm,
                    prompt=prompt,
                    provider=str(provider),
                )
                last_diagnostics = diagnostics
                if package is not None:
                    return package, diagnostics
                logger.info(
                    "[DemandReconstruction] trying next LLM provider after semantic router failure: "
                    f"provider={provider}, status={diagnostics.get('status')}"
                )
            return None, last_diagnostics

        return self.invoke_with_llm(
            llm=self._llm,
            prompt=prompt,
            provider="default",
        )

    @staticmethod
    def build_prompt(message: str, *, target_aliases: Dict[str, str]) -> str:
        allowed_targets = ", ".join(sorted(set(target_aliases.values())))
        return (
            "你是「方案高参」需求重构阶段的 LLM Semantic Router。\n"
            "任务：先理解用户原文，输出内部语义理解包；不要直接回答用户，不要给方案。\n"
            "所有判断必须有原文证据；没有证据只能省略，不得编造。\n\n"
            f"Allowed scan targets: {allowed_targets}\n"
            "recommended_scan_targets must use these ids; do not invent new target ids.\n"
            "只输出 JSON，不要 Markdown，不要解释。JSON 字段：\n"
            "{\n"
            '  "intent_type": "specific_project_reconstruction|methodology|case_reference|data_request|out_of_scope",\n'
            '  "project_anchor": true,\n'
            '  "project_object": "用户正在处理的项目对象",\n'
            '  "space_candidates": [{"label": "受控空间/原型/语义标签", "confidence": 0.0, "evidence": ["原文片段"]}],\n'
            '  "core_tensions": [{"title": "核心张力", "confidence": 0.0, "evidence": ["原文片段"]}],\n'
            '  "missing_slots": ["会改变后续判断的信息缺口"],\n'
            '  "novelty_level": "known|partial_unknown|unknown",\n'
            '  "recommended_scan_targets": ["建议扫描的规则原型或语义轴"],\n'
            '  "package_ids": ["knowledge package ids; use [] when absent"],\n'
            '  "ontology_dimension_ids": ["ontology dimension ids; use [] when absent"],\n'
            '  "recommended_fragment_targets": [{"group_id": "规则碎片组ID", "fragment_id": "碎片ID", "confidence": 0.0, "evidence": ["原文片段"]}]\n'
            "}\n\n"
            f"用户原文：{message}"
        )

    def invoke_with_llm(
        self,
        *,
        llm: Any,
        prompt: str,
        provider: str,
    ) -> tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
        started_at = time.perf_counter()
        try:
            response = llm.invoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)
            package = self.parse(str(content or ""))
            if package is not None:
                elapsed_ms = int((time.perf_counter() - started_at) * 1000)
                logger.info(
                    "[DemandReconstruction] LLM semantic router response accepted: "
                    f"provider={provider}, prompt_chars={len(prompt)}, elapsed_ms={elapsed_ms}"
                )
                return package, {"status": "used", "provider": provider}
            repair_prompt = self.build_repair_prompt(
                original_prompt=prompt,
                rejected_content=str(content or ""),
            )
            repair_response = llm.invoke(repair_prompt)
            repair_content = repair_response.content if hasattr(repair_response, "content") else str(repair_response)
            repaired = self.parse(str(repair_content or ""))
            if repaired is not None:
                return repaired, {"status": "used", "provider": provider, "repair_attempted": True}
            return None, {"status": "invalid_semantic_router_json", "provider": provider}
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - started_at) * 1000)
            logger.warning(
                "[DemandReconstruction] LLM semantic router failed: "
                f"provider={provider}, prompt_chars={len(prompt)}, elapsed_ms={elapsed_ms}, "
                f"error_type={type(exc).__name__}, error={exc}"
            )
            return None, {
                "status": "invoke_failed",
                "provider": provider,
                "error": str(exc),
                "error_type": type(exc).__name__,
            }

    @staticmethod
    def build_repair_prompt(*, original_prompt: str, rejected_content: str) -> str:
        return (
            "上一次 LLM Semantic Router 输出无法通过结构校验。\n"
            "请严格按原 prompt 的 JSON schema 重写，只输出 JSON，不要解释。\n\n"
            f"原 prompt：\n{original_prompt}\n\n"
            f"被拒绝输出：\n{rejected_content}"
        )

    def parse(self, content: str) -> Optional[Dict[str, Any]]:
        package = self._parse_response_json(content)
        if not isinstance(package, dict):
            return None
        if not self.is_valid(package):
            return None
        return package

    @staticmethod
    def is_valid(package: Dict[str, Any]) -> bool:
        if not str(package.get("intent_type") or "").strip():
            return False
        if "project_anchor" not in package:
            return False
        if not str(package.get("project_object") or "").strip():
            return False
        candidates = package.get("space_candidates")
        tensions = package.get("core_tensions")
        if not isinstance(candidates, list) or not candidates:
            return False
        if not isinstance(tensions, list) or not tensions:
            return False
        for item in candidates + tensions:
            if not isinstance(item, dict):
                return False
            evidence = item.get("evidence")
            if not isinstance(evidence, list) or not any(str(value).strip() for value in evidence):
                return False
        return True