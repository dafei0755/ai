# -*- coding: utf-8 -*-
"""
v7.234 Analysis Quality Evaluation Test Suite

Test Coverage:
1. Unit tests - Individual method testing
2. Integration tests - Method collaboration testing
3. End-to-end tests - Full flow testing
4. Regression tests - Ensure existing functionality works
"""

import asyncio
import json
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import AsyncMock, MagicMock, patch

# ==================== Test Data ====================

HIGH_QUALITY_ANALYSIS_DATA = {
    "user_profile": {
        "location": "Sichuan Emeishan Qiliping",
        "occupation": "B&B Owner/Designer",
        "identity_tags": ["Design aesthetics pursuer", "Nordic style lover"],
        "explicit_need": "HAY-style B&B interior design concept",
        "implicit_needs": ["Differentiated competitiveness", "Attract high-end guests"],
    },
    "analysis": {
        "l1_facts": {
            "brand_entities": [
                {
                    "name": "HAY",
                    "product_lines": ["Palissade", "Mags", "About A Chair", "Colour Crate"],
                    "designers": ["Ronan Bouroullec", "Stefan Diez", "Thomas Bentzen"],
                    "color_system": ["Pastel Pink", "Soft Yellow", "Sky Blue", "Olive Green"],
                    "materials": ["Powder-coated steel", "Recycled plastic", "Natural oak"],
                }
            ],
            "location_entities": [
                {
                    "name": "Sichuan Emeishan Qiliping",
                    "climate": "Subtropical humid climate",
                    "altitude": "1300-1500m",
                    "local_materials": ["Bamboo", "Fir wood", "Blue stone"],
                    "architecture_style": "Western Sichuan residential",
                }
            ],
            "competitor_entities": [
                {"name": "Songtsam", "positioning": "Tibetan luxury", "differentiator": "Local culture depth"},
                {"name": "Jixiashan", "positioning": "Minimalist aesthetics", "differentiator": "Mountain experience"},
                {"name": "Aman", "positioning": "Oriental ultimate", "differentiator": "Service and privacy"},
            ],
            "style_entities": ["Nordic minimalism", "Danish design", "Functionalism"],
            "person_entities": [
                {"name": "Rolf Hay", "role": "Founder", "works": ["HAY brand"]},
                {"name": "Ronan Bouroullec", "role": "Designer", "works": ["Palissade series"]},
            ],
        },
        "l2_models": {
            "selected_perspectives": ["Psychology", "Sociology", "Aesthetics"],
            "psychological": "Create urban quality sense with HAY Palissade outdoor furniture",
            "sociological": "Convey cultural capital through Nordic design knowledge",
            "aesthetic": "HAY pastel colors and rounded geometry vs bamboo and stone textures",
        },
        "l3_tension": {
            "formula": "[HAY industrial precision] vs [Western Sichuan craftsmanship warmth]",
            "description": "Tension between Nordic standardized production and local artisan handcraft",
            "resolution_strategy": "Use HAY Palissade outdoor furniture with local bamboo weaving",
        },
        "l4_jtbd": "When operating a B&B in scenic Qiliping, I want to inject HAY brand refined urban quality, to create a distinctive premium vacation space attracting design and nature lovers",
        "l5_sharpness": {
            "score": 85,
            "specificity": "Yes, this analysis is specific to HAY+Qiliping fusion",
            "actionability": "Yes, can directly guide product selection: Palissade series + local bamboo weaving + HAY color system",
            "depth": "Yes, touches user's deep pursuit of design travel and social identity",
        },
    },
    "search_framework": {
        "core_question": "How to fuse HAY design with Qiliping local environment",
        "answer_goal": "Provide HAY style and Western Sichuan style fusion design concept framework",
        "boundary": "Do not search: 1.HAY corporate history 2.Nordic design history 3.Emeishan travel guide",
        "targets": [
            {
                "id": "T1",
                "name": "HAY Product Features",
                "description": "Search HAY core product line design features",
                "purpose": "Establish brand design language cognition",
                "priority": 1,
                "category": "Basic",
                "preset_keywords": [
                    "HAY Palissade outdoor furniture powder-coated steel color matching courtyard design real case",
                    "HAY Mags modular sofa wool fabric B&B living room soft decoration Nordic minimalism",
                ],
                "quality_criteria": ["Contains specific product images", "Color system description"],
                "expected_info": ["Product features", "Color system", "Material description"],
            },
            {
                "id": "T2",
                "name": "Competitor Cases",
                "description": "Search similar positioned mountain B&B design cases",
                "purpose": "Obtain fusion design success experience",
                "priority": 2,
                "category": "Case",
                "preset_keywords": [
                    "Songtsam Jixiashan mountain B&B interior design local materials bamboo structure design case",
                    "Qiliping Emeishan boutique B&B Western Sichuan style modern design fusion case",
                ],
                "quality_criteria": ["Has real scene photos", "Design concept description"],
                "expected_info": ["Design methods", "Material selection", "Space layout"],
            },
        ],
    },
}


LOW_QUALITY_ANALYSIS_DATA = {
    "user_profile": {
        "location": "Sichuan",
        "occupation": "Owner",
        "identity_tags": ["Design lover"],
        "explicit_need": "B&B design",
        "implicit_needs": [],
    },
    "analysis": {
        "l1_facts": ["HAY is Nordic brand", "Qiliping is resort area", "Need B&B design"],
        "l2_models": {
            "psychological": "User needs belonging",
            "sociological": "Show taste",
            "aesthetic": "Modern and traditional fusion",
        },
        "l3_tension": "Modern vs Traditional",
        "l4_jtbd": "Design a beautiful B&B",
        "l5_sharpness": {"score": 40, "specificity": "", "actionability": "", "depth": ""},
    },
    "search_framework": {
        "core_question": "B&B design",
        "answer_goal": "Provide design solution",
        "boundary": "",
        "targets": [
            {
                "id": "T1",
                "name": "HAY Design",
                "description": "Search HAY design concept",
                "purpose": "Understand brand",
                "priority": 1,
                "category": "Basic",
                "preset_keywords": ["HAY design concept", "Nordic style features"],
                "quality_criteria": [],
                "expected_info": [],
            }
        ],
    },
}


# ==================== Unit Tests ====================


class TestCalculateProperNounRatio:
    """Test proper noun ratio calculation"""

    @pytest.fixture
    def search_engine(self):
        """Create search engine instance"""
        from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine

        engine = UcpptSearchEngine()
        return engine

    def test_high_proper_noun_ratio(self, search_engine):
        """Test text with high proper noun ratio"""
        text = "HAY Palissade outdoor furniture powder-coated steel courtyard color matching"
        ratio = search_engine._calculate_proper_noun_ratio(text)
        # HAY and Palissade are proper nouns, ~22% is reasonable for mixed English text
        assert ratio >= 0.15, f"High proper noun text should be >=15%, actual={ratio:.1%}"
        print(f"[PASS] High quality keyword proper noun ratio: {ratio:.1%}")

    def test_low_proper_noun_ratio(self, search_engine):
        """Test text with low proper noun ratio"""
        text = "design concept aesthetic features style concept"
        ratio = search_engine._calculate_proper_noun_ratio(text)
        assert ratio < 0.4, f"Low proper noun text should be <40%, actual={ratio:.1%}"
        print(f"[PASS] Low quality keyword proper noun ratio: {ratio:.1%}")

    def test_mixed_text(self, search_engine):
        """Test mixed text"""
        text = "Songtsam Jixiashan mountain B&B local materials bamboo structure design case"
        ratio = search_engine._calculate_proper_noun_ratio(text)
        assert 0.2 <= ratio <= 0.9, f"Mixed text should be in reasonable range, actual={ratio:.1%}"
        print(f"[PASS] Mixed text proper noun ratio: {ratio:.1%}")

    def test_empty_text(self, search_engine):
        """Test empty text"""
        ratio = search_engine._calculate_proper_noun_ratio("")
        assert ratio == 0.0
        print("[PASS] Empty text handled correctly")

    def test_english_proper_nouns(self, search_engine):
        """Test English proper noun recognition"""
        text = "Ronan Bouroullec designed Palissade for HAY"
        ratio = search_engine._calculate_proper_noun_ratio(text)
        assert ratio >= 0.2, f"English proper nouns should be recognized, actual={ratio:.1%}"
        print(f"[PASS] English proper noun ratio: {ratio:.1%}")


class TestEvaluateAnalysisQuality:
    """Test analysis quality evaluation"""

    @pytest.fixture
    def search_engine(self):
        from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine

        return UcpptSearchEngine()

    def test_high_quality_analysis(self, search_engine):
        """Test high quality analysis scoring"""
        result = search_engine._evaluate_analysis_quality_v234(HIGH_QUALITY_ANALYSIS_DATA)

        assert result["score"] >= 55, f"High quality analysis should be >=55, actual={result['score']}"
        assert result["pass"] is True, "High quality analysis should pass"
        assert result["grade"] in ["A", "B"], f"Grade should be A or B, actual={result['grade']}"

        print(f"[PASS] High quality analysis score: {result['score']}/100 grade={result['grade']}")
        print(f"   Breakdown: {result['breakdown']}")

    def test_low_quality_analysis(self, search_engine):
        """Test low quality analysis scoring"""
        result = search_engine._evaluate_analysis_quality_v234(LOW_QUALITY_ANALYSIS_DATA)

        assert result["score"] < 55, f"Low quality analysis should be <55, actual={result['score']}"
        assert result["pass"] is False, "Low quality analysis should not pass"
        assert result["grade"] == "C", f"Grade should be C, actual={result['grade']}"
        assert len(result["issues"]) > 0, "Should have issue list"

        print(f"[PASS] Low quality analysis score: {result['score']}/100 grade={result['grade']}")
        print(f"   Issues: {result['issues'][:3]}")

    def test_breakdown_dimensions(self, search_engine):
        """Test scoring dimension completeness"""
        result = search_engine._evaluate_analysis_quality_v234(HIGH_QUALITY_ANALYSIS_DATA)

        expected_dims = [
            "entity_coverage",
            "entity_specificity",
            "keyword_density",
            "tension_actionability",
            "sharpness",
        ]
        for dim in expected_dims:
            assert dim in result["breakdown"], f"Missing dimension: {dim}"

        print(f"[PASS] Scoring dimensions complete: {list(result['breakdown'].keys())}")


class TestMergeAnalysisData:
    """Test analysis data merging"""

    @pytest.fixture
    def search_engine(self):
        from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine

        return UcpptSearchEngine()

    def test_merge_l1_facts(self, search_engine):
        """Test L1 entity merging"""
        original = {"analysis": {"l1_facts": {"brand_entities": [{"name": "HAY", "product_lines": ["Palissade"]}]}}}
        supplement = {
            "analysis": {
                "l1_facts": {
                    "brand_entities": [{"name": "HAY", "product_lines": ["Mags", "About A Chair"]}],
                    "competitor_entities": [{"name": "Songtsam", "positioning": "Tibetan luxury"}],
                }
            }
        }

        merged = search_engine._merge_analysis_data(original, supplement)

        assert "competitor_entities" in merged["analysis"]["l1_facts"]
        print(f"[PASS] L1 entity merge successful: {list(merged['analysis']['l1_facts'].keys())}")

    def test_merge_keywords(self, search_engine):
        """Test search keyword merging"""
        original = {"search_framework": {"targets": [{"id": "T1", "preset_keywords": ["original keyword 1"]}]}}
        supplement = {
            "search_framework": {"targets": [{"id": "T1", "preset_keywords": ["new keyword 1", "new keyword 2"]}]}
        }

        merged = search_engine._merge_analysis_data(original, supplement)

        keywords = merged["search_framework"]["targets"][0]["preset_keywords"]
        assert len(keywords) >= 2, "Keywords should be merged"
        print(f"[PASS] Keyword merge successful: {keywords}")


# ==================== Integration Tests ====================


class TestQualityEvaluationIntegration:
    """Test quality evaluation and optimization integration"""

    @pytest.fixture
    def search_engine(self):
        from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine

        return UcpptSearchEngine()

    @pytest.mark.asyncio
    async def test_refine_low_quality_analysis(self, search_engine):
        """Test low quality analysis refinement flow"""
        query = "HAY-style B&B interior design concept, Sichuan Emeishan Qiliping"

        quality = search_engine._evaluate_analysis_quality_v234(LOW_QUALITY_ANALYSIS_DATA)
        assert not quality["pass"], "Low quality data should not pass"

        print(f"[PASS] Initial score: {quality['score']}/100 (not passed)")

        with patch.object(search_engine, "_call_deepseek", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = json.dumps(
                {
                    "analysis": {
                        "l1_facts": {
                            "brand_entities": [
                                {"name": "HAY", "product_lines": ["Palissade", "Mags"], "designers": ["Bouroullec"]}
                            ],
                            "competitor_entities": [
                                {"name": "Songtsam", "positioning": "Tibetan luxury", "differentiator": "Local culture"}
                            ],
                        },
                        "l3_tension": {
                            "formula": "[HAY industrial precision] vs [Western Sichuan craftsmanship warmth]",
                            "resolution_strategy": "HAY color system + local bamboo weaving material",
                        },
                    },
                    "search_framework": {
                        "targets": [
                            {
                                "id": "T1",
                                "preset_keywords": [
                                    "HAY Palissade outdoor furniture powder-coated steel B&B courtyard color matching"
                                ],
                            }
                        ]
                    },
                }
            )

            refined_data, refined_quality = await search_engine._refine_analysis_v234(
                query, LOW_QUALITY_ANALYSIS_DATA, quality
            )

            print(f"[PASS] Refined score: {refined_quality['score']}/100")
            assert refined_quality["score"] > quality["score"], "Refined score should improve"


class TestPromptGeneration:
    """Test Prompt generation quality"""

    @pytest.fixture
    def search_engine(self):
        from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine

        return UcpptSearchEngine()

    def test_prompt_contains_entity_extraction(self, search_engine):
        """Test Prompt contains entity extraction instructions"""
        query = "HAY style B&B design"
        prompt = search_engine._build_unified_analysis_prompt(query)

        # Check v7.234 new content - check for entity-related content
        has_entity_content = "brand" in prompt.lower() or "entity" in prompt.lower() or "location" in prompt.lower()
        assert has_entity_content, "Prompt should contain entity extraction instructions"

        print("[PASS] Prompt contains entity extraction instructions")

    def test_prompt_contains_quality_standards(self, search_engine):
        """Test Prompt contains keyword quality standards"""
        query = "Test question"
        prompt = search_engine._build_unified_analysis_prompt(query)

        # Check for keyword-related content
        has_keyword_content = "keyword" in prompt.lower() or "search" in prompt.lower()
        assert has_keyword_content, "Should contain keyword standards"

        print("[PASS] Prompt contains keyword quality standards")


# ==================== Regression Tests ====================


class TestRegressionV7220:
    """Regression tests - Ensure v7.220 functionality unaffected"""

    @pytest.fixture
    def search_engine(self):
        from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine

        return UcpptSearchEngine()

    def test_build_search_framework_from_json(self, search_engine):
        """Test SearchFramework building still works"""
        framework = search_engine._build_search_framework_from_json("Test question", HIGH_QUALITY_ANALYSIS_DATA)

        assert framework is not None
        assert framework.original_query == "Test question"
        assert len(framework.targets) > 0
        assert framework.targets[0].preset_keywords, "Should have preset keywords"

        print(f"[PASS] SearchFramework build normal: {len(framework.targets)} targets")

    def test_build_simple_search_framework(self, search_engine):
        """Test simple SearchFramework fallback"""
        framework = search_engine._build_simple_search_framework("Test fallback solution")

        assert framework is not None
        assert len(framework.targets) >= 2

        print(f"[PASS] Fallback solution normal: {len(framework.targets)} default targets")

    def test_safe_parse_json(self, search_engine):
        """Test JSON parsing still works"""
        valid_json = '{"key": "value", "number": 42}'
        result = search_engine._safe_parse_json(valid_json, "test")

        assert result is not None
        assert result["key"] == "value"

        invalid_json = "not a json"
        result = search_engine._safe_parse_json(invalid_json, "test")
        assert result is None

        print("[PASS] JSON parsing normal")


class TestRegressionSearchTarget:
    """Regression tests - SearchTarget data structure"""

    @pytest.fixture
    def search_engine(self):
        from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine

        return UcpptSearchEngine()

    def test_search_target_to_dict(self, search_engine):
        """Test SearchTarget serialization"""
        from intelligent_project_analyzer.services.ucppt_search_engine import SearchTarget

        target = SearchTarget(
            id="T1",
            name="Test target",
            description="Test description",
            purpose="Test purpose",
            priority=1,
            category="Basic",
            preset_keywords=["keyword1", "keyword2"],
            quality_criteria=["criteria1"],
            expected_info=["info1"],
        )

        result = target.to_dict()

        assert result["id"] == "T1"
        assert result["preset_keywords"] == ["keyword1", "keyword2"]

        print("[PASS] SearchTarget serialization normal")


# ==================== Performance Tests ====================


class TestPerformance:
    """Performance tests"""

    @pytest.fixture
    def search_engine(self):
        from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine

        return UcpptSearchEngine()

    def test_quality_evaluation_speed(self, search_engine):
        """Test quality evaluation speed"""
        import time

        start = time.time()
        for _ in range(100):
            search_engine._evaluate_analysis_quality_v234(HIGH_QUALITY_ANALYSIS_DATA)
        elapsed = time.time() - start

        avg_ms = elapsed / 100 * 1000
        assert avg_ms < 100, f"Evaluation should be <100ms, actual={avg_ms:.2f}ms"

        print(f"[PASS] Quality evaluation avg time: {avg_ms:.2f}ms")

    def test_proper_noun_ratio_speed(self, search_engine):
        """Test proper noun calculation speed"""
        import time

        text = "HAY Palissade outdoor furniture powder-coated steel B&B courtyard color matching Songtsam Jixiashan mountain B&B"

        start = time.time()
        for _ in range(1000):
            search_engine._calculate_proper_noun_ratio(text)
        elapsed = time.time() - start

        avg_us = elapsed / 1000 * 1000000
        assert avg_us < 5000, f"Calculation should be <5ms, actual={avg_us:.2f}us"

        print(f"[PASS] Proper noun calculation avg time: {avg_us:.2f}us")


# ==================== Run Entry ====================

if __name__ == "__main__":
    print("=" * 60)
    print("v7.234 Analysis Quality Evaluation Test Suite")
    print("=" * 60)

    pytest.main(
        [
            __file__,
            "-v",
            "--tb=short",
        ]
    )
