"""
测试复杂度评估算法的准确性

基于85个真实测试问题，验证P0优化后的准确率提升
"""
import pytest
from intelligent_project_analyzer.security.domain_classifier import DomainClassifier


class TestComplexityAssessment:
    """复杂度评估测试类"""

    @pytest.fixture
    def classifier(self):
        """创建分类器实例"""
        return DomainClassifier(llm_model=None)  # 复杂度评估不需要LLM

    # ========== 简单任务测试（应判定为simple）==========

    def test_naming_task_with_culture(self, classifier):
        """测试#22: 命名任务即使含"文化"也应判simple（P0.2优化）"""
        user_input = "中餐包房8间，以苏东坡的诗词命名，4个字，传递生活态度和价值观"
        result = classifier.assess_task_complexity(user_input)

        assert result["complexity"] == "simple", f"期望simple，实际{result['complexity']}"
        assert result["confidence"] >= 0.85, f"置信度过低: {result['confidence']}"
        assert "命名类任务" in result["reasoning"]

    def test_naming_task_door_plate(self, classifier):
        """测试#23: 门牌命名任务（P0.2优化）"""
        user_input = "设计总监的办公室门牌，用苏东坡的诗词中抽取3个字"
        result = classifier.assess_task_complexity(user_input)

        assert result["complexity"] == "simple"
        assert "V3_叙事与体验专家_3-2" in result["suggested_experts"]

    def test_recommendation_task(self, classifier):
        """测试#17: 推荐类任务"""
        user_input = "成都麓湖地产样板房，需要10个概念主题，给出建议"
        result = classifier.assess_task_complexity(user_input)

        assert result["complexity"] == "simple"
        assert result["suggested_workflow"] == "quick_response"

    def test_poetic_concept_long_description(self, classifier):
        """测试#32: 诗意概念即使描述详细>300字也不应误判complex（P0.3优化）"""
        user_input = """
        一位诗人客户，要求他的书房设计概念是"月亮落在结冰的湖面上"。
        他希望空间能营造出宁静、冷冽、诗意的氛围，仿佛置身于冬夜的湖畔。
        光线的运用至关重要，要模拟月光在冰面上的反射效果。
        色彩以冷色调为主，白、灰、浅蓝，材质要有冰的质感。
        家具要极简，不能破坏整体的意境。
        """ * 2  # 故意重复使其>300字

        result = classifier.assess_task_complexity(user_input)

        # 即使>300字，也不应直接判complex
        assert result["complexity"] in ["simple", "medium"], \
            f"诗意书房应为simple/medium，但判定为{result['complexity']}"

    # ========== 中等任务测试（应判定为medium）==========

    def test_single_space_with_special_needs(self, classifier):
        """测试#26: 单一空间但有特殊需求"""
        user_input = "一对刚刚经历婚姻危机并决定复合的夫妻，希望重新设计他们的主卧室，预算有限"
        result = classifier.assess_task_complexity(user_input)

        assert result["complexity"] in ["medium", "complex"]
        # P0.1优化: "婚姻.*危机"应触发"特殊用户群体"

    def test_single_functional_space(self, classifier):
        """测试#25: 单一功能空间但技术要求高"""
        user_input = "一位职业电竞选手，15平米卧室改造，兼具直播、训练和休息功能，要求绝对隔音和专业级灯光"
        result = classifier.assess_task_complexity(user_input)

        # P0.1优化: "绝对隔音"触发"特殊技术工艺"
        # 但因为也命中了medium特征（卧室+改造），判定为medium也合理
        assert result["complexity"] in ["medium", "complex"]

    # ========== 复杂任务测试（应判定为complex）==========

    def test_large_area_market(self, classifier):
        """测试#7: 大面积菜市场更新（P0.1优化：大型项目面积）"""
        user_input = "深圳蛇口20000平米菜市场更新，对标苏州黄桥菜市场，融入蛇口渔村传统文化，成为城市更新标杆"
        result = classifier.assess_task_complexity(user_input)

        assert result["complexity"] == "complex", \
            f"20000平米项目应为complex，实际{result['complexity']}"
        assert result["confidence"] >= 0.85

    def test_competition_bidding(self, classifier):
        """测试#24: 竞标项目（P0.1优化：商业竞争）"""
        user_input = "成都文华东方酒店室内设计方案竞标，对手有HBA、CCD郑中设计、杨邦胜设计、刘波设计"
        result = classifier.assess_task_complexity(user_input)

        assert result["complexity"] == "complex"
        # P0.1优化: "竞标"应触发"商业竞争"

    def test_special_craft_dolby(self, classifier):
        """测试#45: 特殊工艺（P0.1优化：杜比全景声）"""
        user_input = "一位电影混音师，需要在家中搭建符合杜比全景声标准的家庭影院和工作室，声学效果优先"
        result = classifier.assess_task_complexity(user_input)

        assert result["complexity"] == "complex"
        # P0.1优化: "杜比"应触发"特殊技术工艺"

    def test_special_user_autism(self, classifier):
        """测试#6: 特殊用户（P0.1优化：自闭症儿童）"""
        user_input = "深圳前海160平米住宅，35岁程序员，孩子7岁自闭症，外公外婆每年来住3个月"
        result = classifier.assess_task_complexity(user_input)

        assert result["complexity"] == "complex"
        # P0.1优化: "自闭症"应触发"特殊用户群体"

    def test_style_conflict_fusion(self, classifier):
        """测试#28: 风格冲突融合（P0.1优化）"""
        user_input = "北京四合院，内部要实现纽约Loft的开放、极简和派对功能"
        result = classifier.assess_task_complexity(user_input)

        assert result["complexity"] == "complex"
        # P0.1优化: "四合院.*Loft"应触发"风格冲突融合"

    def test_budget_constraint(self, classifier):
        """测试#76: 预算约束（P0.1优化）"""
        user_input = "上海老弄堂120平米老房翻新，业主想要杂志级效果，但全包预算限制在50万"
        result = classifier.assess_task_complexity(user_input)

        # P0.1优化: "预算.*限制"应触发"严格约束条件"
        assert result["complexity"] in ["medium", "complex"]

    def test_extreme_environment(self, classifier):
        """测试#84: 极端环境（P0.1优化）"""
        user_input = "西藏林芝海拔3800米悬崖边精品民宿，极寒条件下的低能耗供暖，室内弥散式供氧系统"
        result = classifier.assess_task_complexity(user_input)

        assert result["complexity"] == "complex"
        # P0.1优化: "海拔.*3800"应触发"特殊技术工艺"

    def test_multi_function_complex(self, classifier):
        """测试#15: 多功能复合（P0.1优化）"""
        user_input = "安徽合肥50000平米中国书法大酒店，250间客房，能展览、能住宿、能会议、能交流的综合主题酒店"
        result = classifier.assess_task_complexity(user_input)

        assert result["complexity"] == "complex"
        # P0.1优化: "综合"应触发"多功能复合"

    def test_blended_family(self, classifier):
        """测试#49: 再婚家庭（P0.1优化）"""
        user_input = "再婚家庭，男方带16岁儿子，女方带10岁女儿，需要为两个没有血缘关系的孩子创造既有公共交流区又有绝对隐私的空间"
        result = classifier.assess_task_complexity(user_input)

        assert result["complexity"] == "complex"
        # P0.1优化: "再婚.*家庭"应触发"特殊用户群体"

    def test_length_independence_simple(self, classifier):
        """测试：简单任务不受描述长度影响"""
        # 简短版本（30字）
        short = "成都麓湖样板房，需要10个概念主题"
        # 详细版本（150字）
        long = """成都麓湖片区的地产样板房项目，需要10个设计概念主题。
        项目位于成都麓湖生态城，目标客群为高净值人群，希望通过多元化的设计概念
        吸引不同审美偏好的客户。需要涵盖现代、中式、自然等多种风格方向，
        每个主题需要有明确的设计定位和目标客群描述。"""

        result_short = classifier.assess_task_complexity(short)
        result_long = classifier.assess_task_complexity(long)

        # 核心断言：无论描述长短，复杂度应一致
        assert result_short["complexity"] == result_long["complexity"], \
            f"简短版判定为{result_short['complexity']}，详细版判定为{result_long['complexity']}，违反了'复杂度与长度无关'原则"
        assert result_short["complexity"] == "simple", "推荐类任务应判定为simple"

    def test_length_independence_complex(self, classifier):
        """测试：复杂任务不受描述长度影响"""
        # 简短版本（25字）
        short = "深圳蛇口20000平米菜市场更新"
        # 详细版本（180字）
        long = """深圳蛇口菜市场更新改造项目，总面积20000平方米，
        需要对标苏州黄桥菜市场的成功经验，融入蛇口渔村的传统文化元素。
        项目需要兼顾蛇口老居民街坊的日常需求、香港访客的消费习惯、
        蛇口特色外籍客群的多元需求，以及周边社区居民的便利性。
        业主希望将其打造为深圳城市更新的标杆项目，具有示范意义。"""

        result_short = classifier.assess_task_complexity(short)
        result_long = classifier.assess_task_complexity(long)

        # 核心断言：无论描述长短，复杂度应一致
        assert result_short["complexity"] == result_long["complexity"], \
            f"简短版判定为{result_short['complexity']}，详细版判定为{result_long['complexity']}，违反了'复杂度与长度无关'原则"
        assert result_short["complexity"] == "complex", "大型项目应判定为complex"


class TestAccuracyMetrics:
    """准确率统计测试"""

    @pytest.fixture
    def classifier(self):
        return DomainClassifier(llm_model=None)

    def test_sample_accuracy(self, classifier):
        """测试样本准确率"""
        test_cases = [
            # (输入, 预期复杂度)
            ("中餐包房8间命名，苏东坡诗词", "simple"),
            ("门牌3个字命名", "simple"),
            ("成都麓湖样板房10个概念主题", "simple"),
            ("深圳蛇口20000平米菜市场更新", "complex"),
            ("成都文华东方酒店竞标", "complex"),
            ("杜比全景声家庭影院工作室", "complex"),
            ("自闭症儿童家庭160平米住宅", "complex"),
            ("四合院+Loft风格融合", "complex"),
            ("海拔3800米极寒民宿", "complex"),
        ]

        correct = 0
        total = len(test_cases)

        for user_input, expected in test_cases:
            result = classifier.assess_task_complexity(user_input)
            if result["complexity"] == expected:
                correct += 1
            else:
                print(f"误判: '{user_input[:30]}...'")
                print(f"   预期={expected}, 实际={result['complexity']}")
                print(f"   reasoning={result['reasoning']}")

        accuracy = correct / total
        print(f"\n准确率: {correct}/{total} = {accuracy*100:.1f}%")
        print(f"目标: 85%")

        assert accuracy >= 0.85, f"准确率{accuracy*100:.1f}%低于85%目标"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
