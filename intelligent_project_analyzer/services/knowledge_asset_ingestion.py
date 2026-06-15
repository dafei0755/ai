"""File-backed knowledge asset ingestion helpers."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .knowledge_asset_models import validate_candidate_bundle


ASSET_ROOT = Path(__file__).resolve().parent.parent / "knowledge_base" / "assets"
CARD_ID = "KC-SPACE-DIFFERENTIATION-CULTURAL-MOTIF-001"
CASE_GROUP_ID = "HEYTEA_2_0_chinese_inspiration_theme_stores"


def _write_yaml(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def parse_store_cases(markdown_text: str) -> List[Dict[str, Any]]:
    cases: List[Dict[str, Any]] = []
    for line in markdown_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 6 or not cells[0].isdigit():
            continue
        cases.append(
            {
                "case_id": f"CASE-HEYTEA-2-0-{int(cells[0]):02d}",
                "brand": "喜茶 HEYTEA",
                "city": cells[1],
                "store_name": cells[2],
                "theme_name": cells[3],
                "poetic_expression": cells[4],
                "motif_tags": [item.strip() for item in cells[5].replace("、", ",").split(",") if item.strip()],
                "case_group_id": CASE_GROUP_ID,
                "verification_status": "not_individually_verified",
            }
        )
    return cases


def build_motif_vocabulary() -> Dict[str, Any]:
    return {
        "vocabulary_id": "VOCAB-CULTURAL-MOTIF-SPACE-001",
        "title": "东方文化母题空间转译词表",
        "status": "approved_mvp",
        "motif_families": {
            "architectural_component": {
                "name_cn": "建筑构件母题",
                "motifs": ["檐", "亭", "窗", "柱", "馆", "山房"],
            },
            "landscape_garden": {
                "name_cn": "山水园林母题",
                "motifs": ["石", "岩", "园", "峦", "泉", "流", "水境", "江海"],
            },
            "literati_object": {
                "name_cn": "文人器物母题",
                "motifs": ["茶", "扇", "弦", "陶", "炉", "纸", "书"],
            },
            "celestial_color": {
                "name_cn": "天象色彩母题",
                "motifs": ["天青", "月轮", "清辉", "烟云", "日月星", "氤氲"],
            },
            "social_gathering": {
                "name_cn": "雅集社交母题",
                "motifs": ["知音", "友来", "雅集", "家友", "围炉", "品茗"],
            },
        },
    }


def build_heytea_cultural_motif_candidate(
    source_path: Path | str,
    source_text: Optional[str] = None,
) -> Dict[str, Any]:
    source_path = Path(source_path)
    text = source_text if source_text is not None else source_path.read_text(encoding="utf-8")
    case_objects = parse_store_cases(text)
    bundle = {
        "schema_version": "knowledge_asset_bundle.v1",
        "source_document": {
            "source_id": "SRC-XHS-HEY-20260608-002",
            "source_path": str(source_path),
            "source_type": "manual_visible_xiaohongshu_page",
            "raw_text_stored": False,
            "screenshot_stored": False,
            "user_identifier_stored": False,
            "full_url_stored": False,
        },
        "observation_card": {
            "observation_id": "OBS-XHS-HEY-20260608-002",
            "source_type": "manual_visible_xiaohongshu_page",
            "sample_count": len(case_objects),
            "raw_text_stored": False,
            "screenshot_stored": False,
            "user_identifier_stored": False,
            "full_url_stored": False,
        },
        "candidate_card": {
            "card_id": CARD_ID,
            "title": "文化母题驱动的连锁空间去同质化机制",
            "status": "candidate",
            "source_role": "translation_method",
            "species": ["MechanismCard", "MeaningExpressionCard", "TranslationMethodCard"],
            "production_method": "CL",
            "layer": "SpaceType",
            "source_refs": [
                "SRC-XHS-HEY-20260608-002",
                "OBS-XHS-HEY-20260608-002",
                CASE_GROUP_ID,
            ],
            "grid_coordinate": {
                "primary_lens": "E8_symbol_narrative",
                "secondary_lens": ["E7_social_relation", "E3_light_material"],
                "layer": "SpaceType",
            },
            "time_validity": {
                "variable_type": "medium",
                "review_cycle": "12 months",
            },
            "transferability": {
                "level": "SpaceType",
                "limitation": "仅可迁移文化母题转译机制，不可推断商业业绩或单店真实运营状态。",
            },
            "output_usage": ["DesignBrief_2_0", "ConceptMatrix", "SpatialNarrative"],
            "task_brief_chapter": ["concept_strategy", "spatial_narrative", "brand_memory"],
            "judgment_bet": {
                "is_verifiable": False,
                "judgment": "文化母题可帮助连锁空间形成差异化叙事。",
                "why_this_judgment": "来自已整理的门店主题、母题和诗性表达样本。",
                "what_would_prove_it_right": "后续案例复盘显示母题确实被用户识别并参与空间记忆。",
                "what_would_prove_it_wrong": "用户记忆只来自产品或品牌标识，与空间母题无关。",
                "expected_observation": "访谈、传播素材或复盘中出现对空间母题的稳定引用。",
                "review_time": "after project post-occupancy review",
            },
            "primary_domain": "food_beverage",
            "secondary_domains": ["retail", "hospitality", "bookstore", "cultural_tourism"],
            "knowledge_status": "processed_insight",
            "evidence_level": "supporting_evidence",
            "evidence_strength": "B",
            "ontology_dimension_ids": [
                "E8_symbol_narrative",
                "E7_social_relation",
                "E3_light_material",
                "E1_spatial_order",
            ],
            "package_ids": [
                "kp.cultural_motif_translation",
                "kp.theme_naming_system",
                "kp.chain_store_differentiation",
                "kp.spatial_narrative",
                "kp.tea_drink_store",
            ],
            "allowed_use": [
                "theme_generation",
                "concept_inspiration",
                "motif_recall",
                "spatial_narrative_design",
                "chain_store_differentiation_strategy",
            ],
            "not_allowed_use": [
                "business_performance_claim",
                "construction_standard",
                "compliance_basis",
                "confirmed_user_preference",
                "verified_store_status",
            ],
            "evidence_case_ids": [CASE_GROUP_ID],
            "summary": "连锁空间可在统一品牌与运营底盘上，通过文化母题、双字主题命名、诗性短句和局部空间构件形成门店差异化身份。",
            "review_required": True,
        },
        "case_objects": case_objects,
        "motif_vocabulary": build_motif_vocabulary(),
    }
    validate_candidate_bundle(bundle)
    return bundle


def write_candidate_bundle(bundle: Dict[str, Any], asset_root: Path | str = ASSET_ROOT) -> Dict[str, str]:
    validate_candidate_bundle(bundle)
    asset_root = Path(asset_root)
    card_id = bundle["candidate_card"]["card_id"]
    paths = {
        "candidate": asset_root / "candidates" / f"{card_id}.yaml",
        "source": asset_root / "sources" / f"{bundle['source_document']['source_id']}.yaml",
        "observation": asset_root / "observations" / f"{bundle['observation_card']['observation_id']}.yaml",
    }
    _write_yaml(paths["candidate"], bundle)
    _write_yaml(paths["source"], bundle["source_document"])
    _write_yaml(paths["observation"], bundle["observation_card"])
    return {key: str(path) for key, path in paths.items()}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Knowledge asset ingestion")
    subparsers = parser.add_subparsers(dest="command", required=True)
    ingest = subparsers.add_parser("ingest")
    ingest.add_argument("source_path")
    ingest.add_argument("--asset-root", default=str(ASSET_ROOT))
    args = parser.parse_args(argv)

    if args.command == "ingest":
        bundle = build_heytea_cultural_motif_candidate(Path(args.source_path))
        paths = write_candidate_bundle(bundle, Path(args.asset_root))
        print(f"candidate_written: {paths['candidate']}")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
