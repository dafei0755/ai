"""
v12.0 智能约束识别系统 — 端到端测试

测试范围：
E1: 完整链路 — 用户输入+上传图片 → 约束检测 → interrupt payload → 用户确认 → 下游节点可读取
E2: 约束信封端到端格式校验 — 从原始约束 → 组装 → 注入 → 在 prompt 中可读
E3: 多图多区域端到端 — 多张图片分属不同区域，最终正确汇总
"""

import asyncio
import os
import sys
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from typing import Any, Dict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

pytestmark = [pytest.mark.integration]  # e2e 但不需要真实 LLM


# ==============================================================================
# 公共工具
# ==============================================================================


def _full_state_with_images() -> Dict[str, Any]:
    """模拟用户上传了3张图片（1张平面图、1张现场照片、1张风格参考）的 state"""
    from intelligent_project_analyzer.core.state import StateManager

    sm = StateManager()
    state = sm.create_initial_state("三层别墅设计，1楼客厅餐厅厨房，2楼主卧书房，地下室车库", "test-v12-e2e")
    state.update(
        {
            "agent_results": {
                "requirements_analyst": {
                    "structured_data": {
                        "project_task": "三层别墅设计",
                        "project_overview": "150平米三层别墅",
                        "core_objectives": ["现代简约"],
                        "functional_requirements": ["客厅", "餐厅", "厨房", "主卧", "书房"],
                        "constraints": {"budget": "100万"},
                        "confidence_score": 0.9,
                    }
                }
            },
            "structured_requirements": {
                "project_overview": "150平米三层别墅",
                "core_objectives": ["现代简约"],
                "functional_requirements": ["客厅", "餐厅", "厨房", "主卧", "书房"],
                "constraints": {"budget": "100万"},
            },
            "detected_design_modes": [],
            "project_type": "personal_residential",
            "uploaded_visual_references": [
                {
                    "file_path": "/tmp/floor_plan_1f.png",
                    "structured_features": {
                        "image_type": "constraint_source",
                        "image_subtype": "floor_plan",
                        "spatial_zone_guess": "1F",
                        "style_keywords": [],
                    },
                },
                {
                    "file_path": "/tmp/site_photo_2f.jpg",
                    "structured_features": {
                        "image_type": "constraint_source",
                        "image_subtype": "site_photo",
                        "spatial_zone_guess": "2F",
                        "style_keywords": [],
                    },
                },
                {
                    "file_path": "/tmp/style_ref.jpg",
                    "structured_features": {
                        "image_type": "style_reference",
                        "image_subtype": "style_reference",
                        "spatial_zone_guess": "整体",
                        "style_keywords": ["侘寂风", "原木色", "低饱和度"],
                    },
                },
            ],
        }
    )
    return state


def _mock_extract_floor_plan():
    """模拟平面图提取结果"""
    return {
        "spatial_zone": "1F",
        "constraints": [
            {"level": "immutable", "description": "客厅与餐厅之间有承重墙", "source": "floor_plan"},
            {"level": "immutable", "description": "管井位于厨房东北角", "source": "floor_plan"},
            {"level": "baseline", "description": "标准层高2.8m", "source": "floor_plan"},
            {"level": "opportunity", "description": "南向大面积开窗，采光极佳", "source": "floor_plan"},
        ],
        "spatial_topology": {"rooms": 5, "total_area": "约55㎡", "main_axis": "南北向"},
        "existing_conditions": None,
    }


def _mock_extract_site_photo():
    """模拟现场照片提取结果"""
    return {
        "spatial_zone": "2F",
        "constraints": [
            {"level": "baseline", "description": "现有地板为实木复合，状态良好", "source": "site_photo"},
            {"level": "opportunity", "description": "主卧阳台可改造为休闲区", "source": "site_photo"},
        ],
        "spatial_topology": None,
        "existing_conditions": {
            "floor": "实木复合地板",
            "ceiling": "白色乳胶漆",
            "issues": ["墙面有轻微开裂"],
        },
    }


# ==============================================================================
# E1: 完整链路端到端
# ==============================================================================


class TestE1FullPipelineE2E:
    """从上传图片到约束在 Command.update 中可见的完整链路"""

    def test_full_flow_with_mock_vision(self):
        """E1.1: 多图上传 → 约束检测 → interrupt → 确认 → Command 包含完整约束"""
        from intelligent_project_analyzer.interaction.nodes.output_intent_detection import (
            output_intent_detection_node,
        )

        state = _full_state_with_images()

        # 根据 image_subtype 路由返回不同 mock
        async def mock_extract(file_path, image_subtype, spatial_zone):
            if image_subtype == "floor_plan":
                return _mock_extract_floor_plan()
            else:
                return _mock_extract_site_photo()

        with patch(
            "intelligent_project_analyzer.interaction.nodes.output_intent_detection.interrupt",
            return_value={"selected_deliveries": ["design_professional"], "selected_modes": []},
        ):
            with patch("intelligent_project_analyzer.services.file_processor.ConstraintSourceExtractor") as MockCls:
                mock_extractor = MagicMock()
                mock_extractor.extract_constraint_source_details = AsyncMock(side_effect=mock_extract)
                MockCls.return_value = mock_extractor

                from langgraph.types import Command

                cmd = output_intent_detection_node(state)

        # 验证 Command 结构
        assert isinstance(cmd, Command)

        # 验证约束字段存在
        vc = cmd.update.get("visual_constraints")
        assert vc is not None, "visual_constraints 不应为 None"

        # 验证约束按区域汇总
        cbz = vc.get("constraints_by_zone", {})
        assert "1F" in cbz, f"应包含 1F 区域约束，实际: {list(cbz.keys())}"
        assert "2F" in cbz, f"应包含 2F 区域约束，实际: {list(cbz.keys())}"

        # 验证约束计数
        all_constraints = sum(len(v) for v in cbz.values())
        assert all_constraints >= 4, f"应至少有4条约束，实际: {all_constraints}"

        # 验证信封非空
        envelope = vc.get("constraint_envelope", "")
        assert len(envelope) > 0, "约束信封不应为空"
        assert "设计参照系" in envelope

        # 验证风格倾向
        st = vc.get("style_tendencies", {})
        assert "侘寂风" in st.get("prefer", [])

        # 验证空间区域
        esz = cmd.update.get("extracted_spatial_zones")
        assert esz is not None
        zone_ids = {z["id"] for z in esz}
        assert "overall" in zone_ids
        assert "1f" in zone_ids  # 从 user_input "1楼" 提取
        assert "2f" in zone_ids  # 从 user_input "2楼" 提取


# ==============================================================================
# E2: 约束信封格式端到端校验
# ==============================================================================


class TestE2ConstraintEnvelopeFormat:
    """验证约束信封文本的标准格式"""

    def test_envelope_format_multi_zone(self):
        """E2.1: 多区域信封包含完整的层级标签和区域标题"""
        from intelligent_project_analyzer.interaction.nodes.output_intent_detection import (
            _build_constraint_envelope,
            _extract_spatial_zones,
        )

        zones = _extract_spatial_zones({}, "三层别墅，1楼客厅，2楼卧室")

        constraints = {
            "overall": [
                {"level": "immutable", "description": "建筑红线不可超越"},
            ],
            "1f": [
                {"level": "baseline", "description": "层高2.8m"},
                {"level": "opportunity", "description": "南向采光好"},
            ],
            "2f": [
                {"level": "immutable", "description": "管井位置固定"},
            ],
        }
        style = {"prefer": ["现代简约", "原木色"], "avoid": ["欧式", "大理石"]}

        envelope = _build_constraint_envelope(constraints, zones, style)

        # 结构校验
        assert envelope.startswith("=== 设计参照系")
        assert envelope.rstrip().endswith("=== END ===")

        # 层级标签
        assert "L1 不可变" in envelope
        assert "L2 基准" in envelope
        assert "L3 机会" in envelope

        # 区域标题
        assert "## 整体" in envelope
        assert "## 1F" in envelope
        assert "## 2F" in envelope

        # 风格
        assert "风格偏好" in envelope
        assert "现代简约" in envelope

        # 内容
        assert "建筑红线" in envelope
        assert "南向采光" in envelope

    def test_envelope_single_zone_no_zone_headers(self):
        """E2.2: 单区域（仅 overall）信封不显示区域标题"""
        from intelligent_project_analyzer.interaction.nodes.output_intent_detection import (
            _build_constraint_envelope,
        )

        zones = [{"id": "overall", "label": "整体", "source": "preset"}]
        constraints = {
            "overall": [
                {"level": "baseline", "description": "层高3.0m"},
            ],
        }

        envelope = _build_constraint_envelope(constraints, zones)

        # 单区域不应有 ## 整体 标题
        assert "## 整体" not in envelope
        # 但内容应在
        assert "层高3.0m" in envelope


# ==============================================================================
# E3: 多图多区域端到端
# ==============================================================================


class TestE3MultiImageMultiZone:
    """多张图片分属不同区域的端到端汇总测试"""

    def test_four_images_three_zones(self):
        """E3.1: 4张图片 → 3个区域 → 约束正确归属"""
        from intelligent_project_analyzer.interaction.nodes.output_intent_detection import (
            _run_constraint_pipeline,
        )

        state = _full_state_with_images()
        # 添加第4张图片（地下室平面图）
        state["uploaded_visual_references"].append(
            {
                "file_path": "/tmp/floor_plan_basement.png",
                "structured_features": {
                    "image_type": "constraint_source",
                    "image_subtype": "floor_plan",
                    "spatial_zone_guess": "地下室",
                    "style_keywords": [],
                },
            }
        )
        state["extracted_spatial_zones"] = [
            {"id": "overall", "label": "整体", "source": "preset"},
            {"id": "1f", "label": "1F", "source": "extracted"},
            {"id": "2f", "label": "2F", "source": "extracted"},
            {"id": "basement", "label": "地下室", "source": "extracted"},
        ]

        async def mock_extract(file_path, image_subtype, spatial_zone):
            return {
                "spatial_zone": spatial_zone,
                "constraints": [
                    {"level": "baseline", "description": f"{spatial_zone}的约束条目", "source": image_subtype},
                ],
                "spatial_topology": {"zone": spatial_zone},
                "existing_conditions": None,
            }

        with patch("intelligent_project_analyzer.services.file_processor.ConstraintSourceExtractor") as MockCls:
            mock_extractor = MagicMock()
            mock_extractor.extract_constraint_source_details = AsyncMock(side_effect=mock_extract)
            MockCls.return_value = mock_extractor

            result = asyncio.run(_run_constraint_pipeline(state))

        assert result is not None
        cbz = result["constraints_by_zone"]

        # 3个约束源图片 → 3个区域各有约束
        assert "1F" in cbz
        assert "2F" in cbz
        assert "地下室" in cbz

        # 每个区域至少1条
        for zone, constraints in cbz.items():
            assert len(constraints) >= 1, f"区域 {zone} 应至少有1条约束"

        # 拓扑也按区域汇总
        assert len(result["spatial_topologies"]) >= 2
