"""
execution/skills/transformation_skills.py 鈥?杞崲鍙樻崲鎶€鑳?

Copilot 鐢熸垚锛?026-03-22锛?

鎶€鑳藉垪琛細
  - rewrite_outline    (A 绫婚棬鎺?锛氶噸鍐欐柟妗堝ぇ绾?鏂囨妗嗘灦
  - map_version_params (A 绫婚棬鎺?锛氱増鏈弬鏁版槧灏勶紙v1 鈫?v1.1 鍙傛暟缁ф壙锛?
  - parse_format       (A 绫婚棬鎺?锛氳В鏋愬閮ㄦ牸寮忥紙PDF 瑙勮寖銆丆AD 灞炴€ц〃锛?
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from loguru import logger

from intelligent_project_analyzer.workflow.execution.risk_gates import (
    ActionRequest,
    RiskGateEngine,
)


# ---------------------------------------------------------------------------
# 缁撴灉缁撴瀯
# ---------------------------------------------------------------------------


class RewriteResult:
    def __init__(self, original: str, rewritten: str, rationale: str = "") -> None:
        self.original = original
        self.rewritten = rewritten
        self.rationale = rationale

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original": self.original,
            "rewritten": self.rewritten,
            "rationale": self.rationale,
        }


class VersionMapResult:
    def __init__(
        self,
        from_version: str,
        to_version: str,
        inherited_params: Dict[str, Any],
        overridden_params: Dict[str, Any],
    ) -> None:
        self.from_version = from_version
        self.to_version = to_version
        self.inherited_params = inherited_params
        self.overridden_params = overridden_params

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_version": self.from_version,
            "to_version": self.to_version,
            "inherited_params": self.inherited_params,
            "overridden_params": self.overridden_params,
        }


class ParseFormatResult:
    def __init__(
        self,
        source_format: str,
        extracted_fields: Dict[str, Any],
        parse_errors: List[str],
    ) -> None:
        self.source_format = source_format
        self.extracted_fields = extracted_fields
        self.parse_errors = parse_errors

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_format": self.source_format,
            "extracted_fields": self.extracted_fields,
            "parse_errors": self.parse_errors,
        }


# ---------------------------------------------------------------------------
# 杞崲鎶€鑳?
# ---------------------------------------------------------------------------


def rewrite_outline(
    original_text: str,
    rewrite_instruction: str,
    gate_engine: RiskGateEngine,
    session_id: str = "unknown",
    call_counts: Optional[Dict[str, int]] = None,
) -> RewriteResult:
    """
    A 绫婚棬鎺?鈥?鎸夋寚浠ら噸鍐欐柟妗堝ぇ绾叉垨鏂囨妗嗘灦銆?

    鍙傛暟:
      original_text       鈥?寰呮敼鍐欑殑鍘熷鏂囨湰
      rewrite_instruction 鈥?鏀瑰啓鎸囦护锛堝 "鏇寸畝娲侊紝绐佸嚭鎴愭湰浼樺厛"锛?
    """
    request = ActionRequest(
        action_name="draft_compile",
        context={"session_id": session_id, "task": "rewrite"},
        description=f"閲嶅啓澶х翰: {rewrite_instruction[:80]}",
    )
    outcome = gate_engine.check(request, call_counts=call_counts or {})

    if not outcome.can_proceed:
        return RewriteResult(
            original=original_text,
            rewritten=original_text,
            rationale="gate_blocked",
        )

    logger.info(f"[{session_id}] rewrite_outline: instruction='{rewrite_instruction[:60]}'")
    # 瀹為檯鏀瑰啓鐢?LLM 灞傚畬鎴愶紱姝ゅ杩斿洖鍗犱綅缁撴瀯
    return RewriteResult(
        original=original_text,
        rewritten=original_text,  # placeholder 鈥?LLM 濉厖
        rationale=rewrite_instruction,
    )


def map_version_params(
    from_version: str,
    to_version: str,
    base_params: Dict[str, Any],
    delta_overrides: Dict[str, Any],
    gate_engine: RiskGateEngine,
    session_id: str = "unknown",
    call_counts: Optional[Dict[str, int]] = None,
) -> VersionMapResult:
    """
    A 绫婚棬鎺?鈥?鐗堟湰鍙傛暟缁ф壙鏄犲皠銆?

    灏?from_version 鐨勫熀纭€鍙傛暟涓?delta_overrides 鍚堝苟锛岀敓鎴?to_version 鐨勫弬鏁伴泦銆?
    """
    request = ActionRequest(
        action_name="reasoning_evaluate",
        context={"session_id": session_id, "task": "version_map"},
        description=f"鐗堟湰鍙傛暟鏄犲皠 {from_version} 鈫?{to_version}",
    )
    outcome = gate_engine.check(request, call_counts=call_counts or {})

    if not outcome.can_proceed:
        return VersionMapResult(
            from_version=from_version,
            to_version=to_version,
            inherited_params=base_params,
            overridden_params={},
        )

    # 鍚堝苟锛歜ase_params 瑕嗙洊鍐欏叆 delta_overrides
    inherited = {k: v for k, v in base_params.items() if k not in delta_overrides}
    logger.info(
        f"[{session_id}] map_version_params: {from_version} -> {to_version}, "
        f"overrides={list(delta_overrides.keys())}"
    )
    return VersionMapResult(
        from_version=from_version,
        to_version=to_version,
        inherited_params=inherited,
        overridden_params=delta_overrides,
    )


def parse_format(
    raw_content: str,
    source_format: str,
    gate_engine: RiskGateEngine,
    session_id: str = "unknown",
    call_counts: Optional[Dict[str, int]] = None,
) -> ParseFormatResult:
    """
    A 绫婚棬鎺?鈥?瑙ｆ瀽澶栭儴鏍煎紡锛圥DF 瑙勮寖銆丆AD 灞炴€ц〃銆丣SON 鎽樿绛夛級鎻愬彇缁撴瀯鍖栧瓧娈点€?
    """
    request = ActionRequest(
        action_name="draft_compile",
        context={"session_id": session_id, "task": "parse"},
        description=f"鏍煎紡瑙ｆ瀽: source_format={source_format}",
    )
    outcome = gate_engine.check(request, call_counts=call_counts or {})

    if not outcome.can_proceed:
        return ParseFormatResult(
            source_format=source_format,
            extracted_fields={},
            parse_errors=["gate_blocked"],
        )

    logger.info(f"[{session_id}] parse_format: format={source_format}, len={len(raw_content)}")
    # 瀹為檯瑙ｆ瀽閫昏緫鐢?actions 灞傚畬鎴?
    return ParseFormatResult(
        source_format=source_format,
        extracted_fields={},
        parse_errors=[],
    )
