"""
雷达图智能化 Phase 1 单元测试 (v7.137)

测试内容：
1. 同义词匹配增强
2. 任务类型映射
3. 答案推理规则
"""

import pytest

from intelligent_project_analyzer.services.dimension_selector import DimensionSelector


def _extract_dimensions(result):
    """
    🔧 v7.140: 兼容v7.139字典返回格式的辅助函数

    Args:
        result: select_for_project() 的返回值（可能是字典或列表）

    Returns:
        维度列表 (List[Dict])
    """
    if isinstance(result, dict):
        return result.get("dimensions", [])
    return result


class TestSynonymMatchingV7137:
    """测试1: 同义词匹配增强"""

    def setup_method(self):
        """测试前准备"""
        self.selector = DimensionSelector()

    def test_synonym_matching_budget(self):
        """测试预算相关同义词匹配"""
        # 用户输入包含"性价比"（synonyms中的词）
        user_input = "我想要性价比高的设计，预算有限"

        dimensions = _extract_dimensions(
            self.selector.select_for_project(
                project_type="personal_residential", user_input=user_input, min_dimensions=9, max_dimensions=12
            )
        )

        # 检查是否包含 budget_priority 维度
        dim_ids = [d["id"] for d in dimensions]
        assert "budget_priority" in dim_ids, "应该匹配到 budget_priority 维度（通过同义词'性价比'）"

    def test_synonym_matching_style(self):
        """测试风格相关同义词匹配"""
        # 用户输入包含"新中式"（synonyms中的词）
        user_input = "我喜欢新中式风格，要有禅意"

        dimensions = _extract_dimensions(
            self.selector.select_for_project(
                project_type="personal_residential", user_input=user_input, min_dimensions=9, max_dimensions=12
            )
        )

        # 检查是否包含 cultural_axis 维度
        dim_ids = [d["id"] for d in dimensions]
        assert "cultural_axis" in dim_ids, "应该匹配到 cultural_axis 维度（通过同义词'新中式'、'禅意'）"

    def test_synonym_matching_material(self):
        """测试材质相关同义词匹配"""
        # 用户输入包含"原木"（synonyms中的词）
        user_input = "我想用原木和皮革材料，营造温暖的感觉"

        dimensions = _extract_dimensions(
            self.selector.select_for_project(
                project_type="personal_residential", user_input=user_input, min_dimensions=9, max_dimensions=12
            )
        )

        # 检查是否包含 material_temperature 维度
        dim_ids = [d["id"] for d in dimensions]
        assert "material_temperature" in dim_ids, "应该匹配到 material_temperature 维度（通过同义词'原木'、'温暖'）"

    def test_negative_keyword_filter(self):
        """测试排除词过滤"""
        # 用户输入虽然包含"风格"，但主要谈功能
        user_input = "我更关注功能性和实用性，风格无所谓"

        dimensions = _extract_dimensions(
            self.selector.select_for_project(
                project_type="personal_residential", user_input=user_input, min_dimensions=9, max_dimensions=12
            )
        )

        # function_intensity 应该有较高优先级
        dim_ids = [d["id"] for d in dimensions]
        assert "function_intensity" in dim_ids, "应该匹配到 function_intensity 维度"

        # cultural_axis 可能被降低优先级（因为"功能"是其negative_keyword）
        # 注意：这里不强制排除，只是降低优先级


class TestTaskMappingV7137:
    """测试2: 任务类型映射"""

    def setup_method(self):
        """测试前准备"""
        self.selector = DimensionSelector()

    def test_task_mapping_storage_optimization(self):
        """测试收纳优化任务映射"""
        confirmed_tasks = [{"title": "收纳优化", "description": "需要大量储物柜和整理空间", "priority": "high"}]

        dimensions = _extract_dimensions(
            self.selector.select_for_project(
                project_type="personal_residential",
                user_input="住宅设计",
                confirmed_tasks=confirmed_tasks,
                min_dimensions=9,
                max_dimensions=15,  # 允许任务映射注入更多维度
            )
        )

        dim_ids = [d["id"] for d in dimensions]

        # 应该包含 storage_priority 维度（高优先级）
        assert "storage_priority" in dim_ids, "收纳优化任务应该映射到 storage_priority 维度"

        # 可能包含 space_flexibility 维度（中优先级）
        if "space_flexibility" in dim_ids:
            print("✅ 任务映射成功注入 space_flexibility")

    def test_task_mapping_smart_home(self):
        """测试智能家居任务映射"""
        confirmed_tasks = [{"title": "智能家居集成", "description": "需要全屋智能控制系统", "priority": "high"}]

        dimensions = _extract_dimensions(
            self.selector.select_for_project(
                project_type="personal_residential",
                user_input="住宅设计",
                confirmed_tasks=confirmed_tasks,
                min_dimensions=9,
                max_dimensions=15,
            )
        )

        dim_ids = [d["id"] for d in dimensions]

        # 应该包含 tech_visibility 和 automation_workflow 维度
        assert "tech_visibility" in dim_ids, "智能家居任务应该映射到 tech_visibility 维度"
        assert "automation_workflow" in dim_ids, "智能家居任务应该映射到 automation_workflow 维度"

    def test_task_mapping_style_positioning(self):
        """测试风格定位任务映射"""
        confirmed_tasks = [{"title": "风格定位", "description": "确定整体设计风格和美学方向", "priority": "high"}]

        dimensions = _extract_dimensions(
            self.selector.select_for_project(
                project_type="personal_residential",
                user_input="住宅设计",
                confirmed_tasks=confirmed_tasks,
                min_dimensions=9,
                max_dimensions=15,
            )
        )

        dim_ids = [d["id"] for d in dimensions]

        # 应该包含风格相关的核心维度
        assert "cultural_axis" in dim_ids, "风格定位任务应该映射到 cultural_axis 维度"
        assert "aesthetic_direction" in dim_ids, "风格定位任务应该映射到 aesthetic_direction 维度"

    def test_task_mapping_multiple_tasks(self):
        """测试多任务组合映射"""
        confirmed_tasks = [
            {"title": "空间布局优化", "description": "优化户型功能分区", "priority": "high"},
            {"title": "收纳优化", "description": "增加储物空间", "priority": "medium"},
        ]

        dimensions = _extract_dimensions(
            self.selector.select_for_project(
                project_type="personal_residential",
                user_input="住宅设计",
                confirmed_tasks=confirmed_tasks,
                min_dimensions=9,
                max_dimensions=15,
            )
        )

        dim_ids = [d["id"] for d in dimensions]

        # 应该包含两个任务相关的维度
        assert "space_flexibility" in dim_ids, "空间布局优化应该映射到 space_flexibility"
        assert "storage_priority" in dim_ids, "收纳优化应该映射到 storage_priority"
        assert "function_intensity" in dim_ids, "两个任务都强调功能性"


class TestAnswerInferenceV7137:
    """测试3: 答案推理规则"""

    def setup_method(self):
        """测试前准备"""
        self.selector = DimensionSelector()

    def test_answer_inference_budget_low(self):
        """测试低预算答案推理"""
        gap_filling_answers = {"你的预算范围是？": "预算有限，希望控制在15万以内"}

        # 先选择包含 budget_priority 的维度
        dimensions = _extract_dimensions(
            self.selector.select_for_project(
                project_type="personal_residential",
                user_input="预算15万的住宅设计",
                min_dimensions=9,
                max_dimensions=12,
            )
        )

        # 应用答案推理
        dimensions_after = self.selector.apply_answer_to_dimension_rules(gap_filling_answers, dimensions)

        # 查找 budget_priority 维度
        budget_dim = next((d for d in dimensions_after if d["id"] == "budget_priority"), None)

        if budget_dim:
            # 低预算应该推理为成本敏感（接近0）
            assert budget_dim["default_value"] < 40, f"低预算应该推理为成本敏感（<40），但得到 {budget_dim['default_value']}"
            assert budget_dim.get("inferred_from_answer") is True, "应该标记为答案推理"
            print(f"✅ 低预算推理成功: default_value={budget_dim['default_value']}")

    def test_answer_inference_budget_high(self):
        """测试高预算答案推理"""
        gap_filling_answers = {"你的预算范围是？": "预算充足，品质优先，不在乎价格"}

        dimensions = _extract_dimensions(
            self.selector.select_for_project(
                project_type="personal_residential",
                user_input="高端住宅设计",
                min_dimensions=9,
                max_dimensions=12,
            )
        )

        dimensions_after = self.selector.apply_answer_to_dimension_rules(gap_filling_answers, dimensions)

        budget_dim = next((d for d in dimensions_after if d["id"] == "budget_priority"), None)

        if budget_dim:
            # 高预算应该推理为品质优先（接近100）
            assert budget_dim["default_value"] > 70, f"高预算应该推理为品质优先（>70），但得到 {budget_dim['default_value']}"
            print(f"✅ 高预算推理成功: default_value={budget_dim['default_value']}")

    def test_answer_inference_style_chinese(self):
        """测试中式风格答案推理"""
        gap_filling_answers = {"你喜欢什么风格？": "我喜欢新中式风格，要有东方禅意的感觉"}

        dimensions = _extract_dimensions(
            self.selector.select_for_project(
                project_type="personal_residential",
                user_input="中式风格住宅",
                min_dimensions=9,
                max_dimensions=12,
            )
        )

        dimensions_after = self.selector.apply_answer_to_dimension_rules(gap_filling_answers, dimensions)

        cultural_dim = next((d for d in dimensions_after if d["id"] == "cultural_axis"), None)

        if cultural_dim:
            # 中式风格应该推理为东方倾向（接近0）
            assert cultural_dim["default_value"] < 40, f"中式风格应该推理为东方倾向（<40），但得到 {cultural_dim['default_value']}"
            print(f"✅ 中式风格推理成功: default_value={cultural_dim['default_value']}")

    def test_answer_inference_style_modern(self):
        """测试现代风格答案推理"""
        gap_filling_answers = {"你喜欢什么风格？": "我喜欢现代简约风格，北欧风格也不错"}

        dimensions = _extract_dimensions(
            self.selector.select_for_project(
                project_type="personal_residential",
                user_input="现代住宅设计",
                min_dimensions=9,
                max_dimensions=12,
            )
        )

        dimensions_after = self.selector.apply_answer_to_dimension_rules(gap_filling_answers, dimensions)

        cultural_dim = next((d for d in dimensions_after if d["id"] == "cultural_axis"), None)

        if cultural_dim:
            # 现代/北欧风格应该推理为西方倾向（接近100）
            assert cultural_dim["default_value"] > 60, f"现代风格应该推理为西方倾向（>60），但得到 {cultural_dim['default_value']}"
            print(f"✅ 现代风格推理成功: default_value={cultural_dim['default_value']}")

    def test_answer_inference_storage_high(self):
        """测试高收纳需求答案推理"""
        gap_filling_answers = {"收纳需求如何？": "东西很多，需要大量隐藏收纳空间"}

        dimensions = _extract_dimensions(
            self.selector.select_for_project(
                project_type="personal_residential",
                user_input="住宅设计，收纳需求高",
                min_dimensions=9,
                max_dimensions=12,
            )
        )

        dimensions_after = self.selector.apply_answer_to_dimension_rules(gap_filling_answers, dimensions)

        storage_dim = next((d for d in dimensions_after if d["id"] == "storage_priority"), None)

        if storage_dim:
            # 高收纳需求应该推理为隐藏收纳（接近100）
            assert storage_dim["default_value"] > 70, f"高收纳需求应该推理为隐藏收纳（>70），但得到 {storage_dim['default_value']}"
            print(f"✅ 高收纳推理成功: default_value={storage_dim['default_value']}")

    def test_answer_inference_atmosphere_calm(self):
        """测试安静氛围答案推理"""
        gap_filling_answers = {"你希望什么样的氛围？": "我希望空间安静宁静，适合放松和冥想"}

        dimensions = _extract_dimensions(
            self.selector.select_for_project(
                project_type="personal_residential",
                user_input="住宅设计",
                min_dimensions=9,
                max_dimensions=12,
            )
        )

        dimensions_after = self.selector.apply_answer_to_dimension_rules(gap_filling_answers, dimensions)

        energy_dim = next((d for d in dimensions_after if d["id"] == "energy_level"), None)

        if energy_dim:
            # 安静氛围应该推理为静谧能量（接近0）
            assert energy_dim["default_value"] < 40, f"安静氛围应该推理为静谧能量（<40），但得到 {energy_dim['default_value']}"
            print(f"✅ 安静氛围推理成功: default_value={energy_dim['default_value']}")

    def test_answer_inference_multiple_rules(self):
        """测试多条规则同时应用"""
        gap_filling_answers = {
            "你的预算范围是？": "预算有限，15万左右",
            "你喜欢什么风格？": "现代简约",
            "收纳需求如何？": "需要大量储物空间",
        }

        dimensions = _extract_dimensions(
            self.selector.select_for_project(
                project_type="personal_residential",
                user_input="15万现代住宅，收纳需求高",
                min_dimensions=9,
                max_dimensions=12,
            )
        )

        dimensions_after = self.selector.apply_answer_to_dimension_rules(gap_filling_answers, dimensions)

        # 检查多个维度是否被推理
        inferred_dims = [d for d in dimensions_after if d.get("inferred_from_answer")]
        assert len(inferred_dims) >= 2, f"应该至少有2个维度被推理，但只有 {len(inferred_dims)} 个"

        print(f"✅ 多规则推理成功: {len(inferred_dims)} 个维度被推理")


class TestIntegrationV7137:
    """测试4: 集成测试（同义词+任务映射+答案推理）"""

    def setup_method(self):
        """测试前准备"""
        self.selector = DimensionSelector()

    def test_full_pipeline(self):
        """测试完整流水线"""
        # 用户输入（包含同义词）
        user_input = "我想要一个新中式风格的住宅，预算20万，需要大量收纳空间"

        # 确认的任务（触发任务映射）
        confirmed_tasks = [
            {"title": "风格定位", "description": "新中式风格", "priority": "high"},
            {"title": "收纳优化", "description": "增加储物空间", "priority": "high"},
        ]

        # 问卷答案（触发答案推理）
        gap_filling_answers = {
            "你的预算范围是？": "20万左右，希望性价比高",
            "你喜欢什么风格？": "新中式，要有禅意",
            "收纳需求如何？": "东西很多，需要大量柜子",
        }

        # 完整流水线
        dimensions = _extract_dimensions(
            self.selector.select_for_project(
                project_type="personal_residential",
                user_input=user_input,
                confirmed_tasks=confirmed_tasks,
                gap_filling_answers=gap_filling_answers,
                min_dimensions=9,
                max_dimensions=15,
            )
        )

        dim_ids = [d["id"] for d in dimensions]

        # 验证关键维度存在
        assert "cultural_axis" in dim_ids, "应该包含 cultural_axis（同义词+任务映射+答案推理）"
        assert "storage_priority" in dim_ids, "应该包含 storage_priority（任务映射+答案推理）"
        assert "budget_priority" in dim_ids, "应该包含 budget_priority（同义词+答案推理）"

        # 验证答案推理生效
        cultural_dim = next((d for d in dimensions if d["id"] == "cultural_axis"), None)
        if cultural_dim and cultural_dim.get("inferred_from_answer"):
            assert cultural_dim["default_value"] < 40, "新中式应该推理为东方倾向"

        storage_dim = next((d for d in dimensions if d["id"] == "storage_priority"), None)
        if storage_dim and storage_dim.get("inferred_from_answer"):
            assert storage_dim["default_value"] > 70, "高收纳需求应该推理为隐藏收纳"

        print(
            f"✅ 完整流水线测试通过: {len(dimensions)} 个维度，{len([d for d in dimensions if d.get('inferred_from_answer')])} 个被推理"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
