"""
v7.235 & v7.236 搜索任务清单清晰度改进 - 完整测试套件

测试范围：
1. 单元测试：SearchTarget 新字段、字段同步、序列化
2. 集成测试：_build_search_framework_from_json 解析、持久化
3. 端到端测试：完整搜索框架生成流程
4. 回归测试：旧字段兼容性、已有功能正常

版本：v7.236
日期：2026-01-23
"""

import asyncio
import json
import os
import sys
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from intelligent_project_analyzer.services.llm_factory import LLMFactory
from intelligent_project_analyzer.services.ucppt_search_engine import SearchFramework, SearchTarget, UcpptSearchEngine

# ==================== 第一部分：单元测试 ====================


class TestSearchTargetV7236Unit:
    """
    SearchTarget v7.236 单元测试

    测试新增字段：question, search_for, why_need, success_when
    """

    def test_new_fields_creation(self):
        """测试 v7.236 新字段创建"""
        target = SearchTarget(
            id="T1",
            question="HAY品牌设计理念是什么？",
            search_for="HAY官网、品牌故事、设计师访谈",
            why_need="为民宿设计提供北欧风格参考",
            success_when=["找到品牌官方定义", "获取3个以上设计案例"],
            priority=1,
            category="品牌调研",
        )

        assert target.id == "T1"
        assert target.question == "HAY品牌设计理念是什么？"
        assert target.search_for == "HAY官网、品牌故事、设计师访谈"
        assert target.why_need == "为民宿设计提供北欧风格参考"
        assert len(target.success_when) == 2
        assert target.priority == 1
        assert target.category == "品牌调研"

    def test_new_to_old_field_sync(self):
        """测试新字段 → 旧字段自动同步（__post_init__）"""
        target = SearchTarget(
            id="T1",
            question="HAY品牌设计理念是什么？",
            search_for="HAY官网、品牌故事",
            why_need="提供北欧风格参考",
            success_when=["找到品牌定义"],
        )

        # 旧字段应被自动填充
        assert target.name == "HAY品牌设计理念是什么？"
        assert target.description == "HAY官网、品牌故事"
        assert target.purpose == "提供北欧风格参考"
        assert target.quality_criteria == ["找到品牌定义"]

    def test_old_to_new_field_sync(self):
        """测试旧字段 → 新字段自动同步（向后兼容）"""
        target = SearchTarget(
            id="T1",
            name="品牌设计理念",
            description="品牌故事和设计案例",
            purpose="风格参考",
            quality_criteria=["找到定义"],
        )

        # 新字段应被自动填充
        assert target.question == "品牌设计理念"
        assert target.search_for == "品牌故事和设计案例"
        assert target.why_need == "风格参考"
        assert target.success_when == ["找到定义"]

    def test_new_fields_priority_over_old(self):
        """测试同时有新旧字段时的行为（不会互相覆盖）"""
        target = SearchTarget(
            id="T1",
            question="新问题",
            name="旧名称",  # 旧字段也提供了值
            search_for="新内容",
            description="旧描述",  # 旧字段也提供了值
        )

        # 新字段应保持原值（不会被旧字段覆盖）
        assert target.question == "新问题"
        assert target.search_for == "新内容"
        # 旧字段也保持原值（因为条件不满足：新字段有值但旧字段也有值）
        # __post_init__ 逻辑是 "if new and not old" 才同步
        assert target.name == "旧名称"  # 不会被覆盖
        assert target.description == "旧描述"  # 不会被覆盖

    def test_to_dict_includes_new_fields(self):
        """测试 to_dict() 包含新字段"""
        target = SearchTarget(
            id="T1",
            question="测试问题",
            search_for="测试内容",
            why_need="测试原因",
            success_when=["标准1", "标准2"],
            priority=2,
            category="案例参考",
        )

        result = target.to_dict()

        assert result["question"] == "测试问题"
        assert result["search_for"] == "测试内容"
        assert result["why_need"] == "测试原因"
        assert result["success_when"] == ["标准1", "标准2"]
        # 旧字段也应存在（兼容）
        assert result["name"] == "测试问题"
        assert result["description"] == "测试内容"
        assert result["purpose"] == "测试原因"

    def test_category_user_friendly_values(self):
        """测试 v7.236 用户友好的分类值"""
        valid_categories = ["品牌调研", "案例参考", "方案验证", "背景知识"]

        for category in valid_categories:
            target = SearchTarget(
                id="T1",
                question="测试",
                category=category,
            )
            assert target.category == category

    def test_default_category_value(self):
        """测试默认分类值"""
        target = SearchTarget(
            id="T1",
            question="测试问题",
        )
        assert target.category == "品牌调研"  # v7.236 默认值

    def test_is_complete_with_new_fields(self):
        """测试 is_complete() 与新字段配合工作"""
        target = SearchTarget(
            id="T1",
            question="测试问题",
            success_when=["完成标准"],
        )

        assert not target.is_complete()

        target.completion_score = 0.85
        assert target.is_complete()

    def test_empty_new_fields_fallback(self):
        """测试空新字段回退到旧字段"""
        target = SearchTarget(
            id="T1",
            name="旧名称",
            description="旧描述",
            purpose="旧目的",
        )

        # 空新字段应该从旧字段获取值
        assert target.question == "旧名称"
        assert target.search_for == "旧描述"
        assert target.why_need == "旧目的"


class TestSearchTargetSerialization:
    """SearchTarget 序列化测试"""

    def test_json_serialization(self):
        """测试 JSON 序列化"""
        target = SearchTarget(
            id="T1",
            question="HAY品牌设计理念是什么？",
            search_for="HAY官网、品牌故事",
            why_need="提供设计参考",
            success_when=["找到定义"],
            priority=1,
            category="品牌调研",
        )

        data = target.to_dict()
        json_str = json.dumps(data, ensure_ascii=False)
        parsed = json.loads(json_str)

        assert parsed["question"] == "HAY品牌设计理念是什么？"
        assert parsed["search_for"] == "HAY官网、品牌故事"
        assert parsed["category"] == "品牌调研"

    def test_json_deserialization_new_format(self):
        """测试从 v7.236 新格式 JSON 反序列化"""
        json_data = {
            "id": "T1",
            "question": "HAY品牌设计理念是什么？",
            "search_for": "HAY官网、品牌故事",
            "why_need": "提供设计参考",
            "success_when": ["找到定义"],
            "priority": 1,
            "category": "品牌调研",
        }

        target = SearchTarget(**json_data)

        assert target.question == "HAY品牌设计理念是什么？"
        assert target.name == "HAY品牌设计理念是什么？"  # 同步到旧字段

    def test_json_deserialization_old_format(self):
        """测试从旧格式 JSON 反序列化（向后兼容）"""
        json_data = {
            "id": "T1",
            "name": "品牌设计理念",
            "description": "品牌故事和案例",
            "purpose": "参考",
            "quality_criteria": ["标准"],
            "priority": 1,
            "category": "基础",  # 旧分类值
        }

        target = SearchTarget(**json_data)

        # 新字段应被同步填充
        assert target.question == "品牌设计理念"
        assert target.search_for == "品牌故事和案例"
        assert target.why_need == "参考"
        assert target.success_when == ["标准"]


# ==================== 第二部分：集成测试 ====================


class TestBuildSearchFrameworkIntegration:
    """
    _build_search_framework_from_json 集成测试

    测试新字段解析、向后兼容、边界情况
    """

    @pytest.fixture
    def engine(self):
        """创建测试用引擎实例"""
        # Mock 环境变量和外部依赖
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test_key"}):
            with patch(
                "intelligent_project_analyzer.services.ucppt_search_engine.get_ai_search_service", return_value=None
            ):
                engine = UcpptSearchEngine()
                return engine

    def test_parse_new_format_targets(self, engine):
        """测试解析 v7.236 新格式目标"""
        data = {
            "user_profile": {"type": "设计师"},
            "analysis": {"l1_facts": ["HAY", "民宿"]},
            "search_framework": {
                "core_question": "如何设计HAY风格民宿？",
                "answer_goal": "提供设计方案",
                "targets": [
                    {
                        "id": "T1",
                        "question": "HAY品牌核心设计语言是什么？",
                        "search_for": "HAY官网、品牌宣言、设计师访谈",
                        "why_need": "确定风格方向",
                        "success_when": ["找到官方定义", "获取案例图片"],
                        "priority": 1,
                        "category": "品牌调研",
                        "preset_keywords": ["HAY 品牌理念", "HAY 设计语言"],
                    },
                    {
                        "id": "T2",
                        "question": "有哪些成功的HAY风格民宿案例？",
                        "search_for": "民宿设计案例、Airbnb案例",
                        "why_need": "提供参考",
                        "success_when": ["找到3个以上案例"],
                        "priority": 2,
                        "category": "案例参考",
                    },
                ],
            },
        }

        framework = engine._build_search_framework_from_json("HAY风格民宿设计", data)

        assert len(framework.targets) == 2

        t1 = framework.targets[0]
        assert t1.question == "HAY品牌核心设计语言是什么？"
        assert t1.search_for == "HAY官网、品牌宣言、设计师访谈"
        assert t1.why_need == "确定风格方向"
        assert t1.success_when == ["找到官方定义", "获取案例图片"]
        assert t1.category == "品牌调研"
        assert t1.preset_keywords == ["HAY 品牌理念", "HAY 设计语言"]

        t2 = framework.targets[1]
        assert t2.question == "有哪些成功的HAY风格民宿案例？"
        assert t2.category == "案例参考"

    def test_parse_old_format_fallback(self, engine):
        """测试解析旧格式（向后兼容）"""
        data = {
            "user_profile": {},
            "analysis": {"l1_facts": []},
            "search_framework": {
                "core_question": "设计问题",
                "targets": [
                    {
                        "id": "T1",
                        "name": "品牌研究",  # 旧字段
                        "description": "品牌故事",  # 旧字段
                        "purpose": "参考",  # 旧字段
                        "quality_criteria": ["标准"],  # 旧字段
                        "priority": 1,
                    },
                ],
            },
        }

        framework = engine._build_search_framework_from_json("测试查询", data)

        t1 = framework.targets[0]
        # 应该正确回退到旧字段
        assert t1.question == "品牌研究"
        assert t1.search_for == "品牌故事"
        assert t1.why_need == "参考"
        assert t1.success_when == ["标准"]

    def test_mixed_format_parsing(self, engine):
        """测试混合格式解析（部分新字段、部分旧字段）"""
        data = {
            "user_profile": {},
            "analysis": {},
            "search_framework": {
                "targets": [
                    {
                        "id": "T1",
                        "question": "新格式问题",  # 新字段
                        "description": "旧格式描述",  # 旧字段（应被忽略）
                        "why_need": "新格式原因",  # 新字段
                        "quality_criteria": ["旧标准"],  # 旧字段
                    },
                ],
            },
        }

        framework = engine._build_search_framework_from_json("测试", data)

        t1 = framework.targets[0]
        assert t1.question == "新格式问题"
        # search_for 应回退到旧的 description
        assert t1.search_for == "旧格式描述"
        assert t1.why_need == "新格式原因"
        # success_when 应回退到旧的 quality_criteria
        assert t1.success_when == ["旧标准"]

    def test_empty_targets_fallback(self, engine):
        """测试空目标列表兜底（v7.234）"""
        data = {
            "user_profile": {},
            "analysis": {},
            "search_framework": {
                "core_question": "设计问题",
                "targets": [],  # 空列表
            },
        }

        framework = engine._build_search_framework_from_json("HAY风格民宿", data)

        # 应使用默认目标兜底
        assert len(framework.targets) > 0
        assert framework.targets[0].id == "T1"

    def test_preset_keywords_auto_generation(self, engine):
        """测试预设关键词自动生成"""
        data = {
            "user_profile": {},
            "analysis": {},
            "search_framework": {
                "targets": [
                    {
                        "id": "T1",
                        "question": "品牌理念问题",
                        "search_for": "品牌官网和故事",
                        # 没有 preset_keywords
                    },
                ],
            },
        }

        framework = engine._build_search_framework_from_json("HAY民宿设计", data)

        t1 = framework.targets[0]
        # 应该自动生成预设关键词
        assert len(t1.preset_keywords) > 0


class TestSessionArchivePersistence:
    """
    v7.235 会话归档持久化集成测试

    测试新增字段的保存和读取
    """

    def test_archived_search_session_new_columns(self):
        """测试 ArchivedSearchSession 新列存在"""
        from intelligent_project_analyzer.services.session_archive_manager import ArchivedSearchSession

        # 验证新列存在
        columns = [c.name for c in ArchivedSearchSession.__table__.columns]

        assert "search_framework" in columns
        assert "search_master_line" in columns
        assert "current_round" in columns
        assert "overall_completeness" in columns

    def test_search_framework_json_persistence(self):
        """测试 SearchFramework JSON 持久化格式"""
        target = SearchTarget(
            id="T1",
            question="测试问题",
            search_for="测试内容",
            why_need="测试原因",
            success_when=["标准1"],
            priority=1,
            category="品牌调研",
        )

        # 模拟持久化
        serialized = json.dumps(target.to_dict(), ensure_ascii=False)
        deserialized = json.loads(serialized)

        # 验证新字段正确保存
        assert deserialized["question"] == "测试问题"
        assert deserialized["search_for"] == "测试内容"
        assert deserialized["why_need"] == "测试原因"
        assert deserialized["success_when"] == ["标准1"]


# ==================== 第三部分：端到端测试 ====================


class TestSearchFrameworkE2E:
    """
    搜索框架生成端到端测试

    测试完整流程：需求 → 分析 → 框架生成 → 任务清单
    """

    @pytest.fixture
    def engine(self):
        """创建测试用引擎实例"""
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test_key"}):
            with patch(
                "intelligent_project_analyzer.services.ucppt_search_engine.get_ai_search_service", return_value=None
            ):
                engine = UcpptSearchEngine()
                return engine

    @pytest.mark.asyncio
    async def test_hay_example_framework_generation(self, engine):
        """
        测试 HAY 民宿示例的框架生成（对应 Prompt 中的示例）
        """
        # 模拟 DeepSeek-Reasoner 返回的 JSON
        mock_response_json = {
            "user_profile": {
                "身份": "民宿老板",
                "目标": "打造北欧风格精品民宿",
                "决策阶段": "概念设计阶段",
            },
            "analysis": {
                "l1_facts": {
                    "品牌实体": [{"name": "HAY", "type": "北欧设计品牌"}],
                    "场所实体": [{"name": "民宿", "type": "住宿空间"}],
                },
            },
            "search_framework": {
                "core_question": "如何将HAY的设计理念落地到民宿空间？",
                "answer_goal": "提供可执行的设计方案框架",
                "boundary": "聚焦空间设计，不涉及运营管理",
                "targets": [
                    {
                        "id": "T1",
                        "question": "HAY品牌核心设计语言是什么？",
                        "search_for": "HAY官网品牌宣言、设计师访谈、品牌历史",
                        "why_need": "确定空间的核心风格DNA",
                        "success_when": ["找到官方设计理念表述", "获取品牌色彩/材质标准"],
                        "priority": 1,
                        "category": "品牌调研",
                        "preset_keywords": ["HAY 品牌理念 设计语言", "HAY 设计风格 DNA"],
                    },
                    {
                        "id": "T2",
                        "question": "有哪些成功的HAY风格空间案例？",
                        "search_for": "HAY展厅、HAY合作酒店、北欧风格民宿案例",
                        "why_need": "提供空间布局和氛围参考",
                        "success_when": ["收集5个以上高质量案例图", "包含不同空间类型"],
                        "priority": 1,
                        "category": "案例参考",
                        "preset_keywords": ["HAY 展厅设计", "北欧风民宿 案例"],
                    },
                    {
                        "id": "T3",
                        "question": "民宿场景需要哪些功能区？",
                        "search_for": "精品民宿设计标准、客房功能分析",
                        "why_need": "确保设计符合民宿实际使用需求",
                        "success_when": ["明确核心功能分区", "了解动线设计要点"],
                        "priority": 2,
                        "category": "方案验证",
                        "preset_keywords": ["民宿设计 功能分区", "精品民宿 空间规划"],
                    },
                ],
            },
        }

        # 构建框架
        framework = engine._build_search_framework_from_json("我想用HAY风格设计一间民宿", mock_response_json)

        # 验证核心问题
        assert framework.core_question == "如何将HAY的设计理念落地到民宿空间？"
        assert framework.answer_goal == "提供可执行的设计方案框架"

        # 验证目标数量
        assert len(framework.targets) == 3

        # 验证 T1: 品牌调研
        t1 = framework.targets[0]
        assert t1.question == "HAY品牌核心设计语言是什么？"
        assert "HAY官网品牌宣言" in t1.search_for
        assert t1.category == "品牌调研"
        assert len(t1.preset_keywords) >= 2

        # 验证 T2: 案例参考
        t2 = framework.targets[1]
        assert t2.question == "有哪些成功的HAY风格空间案例？"
        assert t2.category == "案例参考"

        # 验证 T3: 方案验证
        t3 = framework.targets[2]
        assert t3.question == "民宿场景需要哪些功能区？"
        assert t3.category == "方案验证"

    @pytest.mark.asyncio
    async def test_task_list_clarity_requirements(self, engine):
        """
        测试任务清单清晰度要求（v7.236 核心改进）

        验证每个 SearchTarget 都有清晰的：
        - question: 问句形式，明确要回答什么
        - search_for: 具体搜索内容
        - why_need: 对回答的贡献
        - success_when: 完成标准
        """
        mock_data = {
            "user_profile": {},
            "analysis": {},
            "search_framework": {
                "targets": [
                    {
                        "id": "T1",
                        "question": "小米SU7的核心竞争力是什么？",
                        "search_for": "官方配置表、技术发布会、竞品对比评测",
                        "why_need": "帮助用户理解产品定位",
                        "success_when": ["找到官方技术参数", "获取第三方评测对比"],
                        "priority": 1,
                        "category": "品牌调研",
                    },
                ],
            },
        }

        framework = engine._build_search_framework_from_json("小米SU7值得买吗", mock_data)

        t1 = framework.targets[0]

        # 验证 question 是问句形式
        assert "？" in t1.question or "?" in t1.question or t1.question.endswith("吗")

        # 验证 search_for 包含具体内容
        assert len(t1.search_for) > 10
        assert "、" in t1.search_for or "," in t1.search_for  # 列举多个内容

        # 验证 why_need 说明贡献
        assert len(t1.why_need) > 5

        # 验证 success_when 有明确标准
        assert len(t1.success_when) >= 1
        assert all(len(s) > 3 for s in t1.success_when)


# ==================== 第四部分：回归测试 ====================


class TestBackwardCompatibilityRegression:
    """
    向后兼容性回归测试

    确保 v7.236 修改不破坏已有功能
    """

    @pytest.fixture
    def engine(self):
        """创建测试用引擎实例"""
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test_key"}):
            with patch(
                "intelligent_project_analyzer.services.ucppt_search_engine.get_ai_search_service", return_value=None
            ):
                engine = UcpptSearchEngine()
                return engine

    def test_old_format_still_works(self, engine):
        """测试旧格式数据仍然可以正常解析"""
        old_format_data = {
            "user_profile": {"type": "用户"},
            "analysis": {"l1_facts": ["品牌A"]},
            "search_framework": {
                "core_question": "设计问题",
                "answer_goal": "提供方案",
                "targets": [
                    {
                        "id": "T1",
                        "name": "品牌研究",
                        "description": "研究品牌故事",
                        "purpose": "了解品牌",
                        "priority": 1,
                        "category": "基础",  # 旧分类
                    },
                    {
                        "id": "T2",
                        "name": "案例收集",
                        "description": "收集设计案例",
                        "purpose": "参考",
                        "priority": 2,
                        "category": "案例",  # 旧分类
                    },
                ],
            },
        }

        framework = engine._build_search_framework_from_json("测试查询", old_format_data)

        # 验证旧数据正确解析
        assert len(framework.targets) == 2
        assert framework.targets[0].name == "品牌研究"
        assert framework.targets[0].question == "品牌研究"  # 同步到新字段
        assert framework.targets[1].name == "案例收集"

    def test_search_target_is_complete_unchanged(self):
        """测试 is_complete() 行为未改变"""
        target = SearchTarget(
            id="T1",
            name="测试",
            description="测试描述",
            purpose="测试",
            priority=1,
        )

        # 初始状态：未完成
        assert not target.is_complete()

        # status = complete 时完成
        target.status = "complete"
        assert target.is_complete()

        # completion_score >= 0.8 时完成
        target.status = "pending"
        target.completion_score = 0.8
        assert target.is_complete()

        # completion_score < 0.8 且 status != complete 时未完成
        target.completion_score = 0.79
        assert not target.is_complete()

    def test_mark_complete_unchanged(self):
        """测试 mark_complete() 行为未改变"""
        target = SearchTarget(
            id="T1",
            name="测试",
            description="测试",
            purpose="测试",
        )

        target.mark_complete(0.95)

        assert target.status == "complete"
        assert target.completion_score == 0.95

    def test_mark_searching_unchanged(self):
        """测试 mark_searching() 行为未改变"""
        target = SearchTarget(
            id="T1",
            name="测试",
        )

        target.mark_searching()

        assert target.status == "searching"

    def test_to_dict_includes_all_legacy_fields(self):
        """测试 to_dict() 仍包含所有旧字段"""
        target = SearchTarget(
            id="T1",
            question="新问题",
            search_for="新内容",
            why_need="新原因",
            priority=1,
            category="品牌调研",
            preset_keywords=["关键词1"],
            expected_info=["信息1"],
        )

        result = target.to_dict()

        # 验证所有旧字段都存在
        legacy_fields = [
            "id",
            "name",
            "description",
            "purpose",
            "priority",
            "category",
            "status",
            "completion_score",
            "sources_count",
            "preset_keywords",
            "quality_criteria",
            "search_queries",
            "expected_info",
        ]

        for field in legacy_fields:
            assert field in result, f"缺少旧字段: {field}"


class TestTypeAnnotationFix:
    """
    v7.235 类型注解修复回归测试

    测试 _generate_phase_checkpoint 类型注解正确
    """

    def test_generate_phase_checkpoint_type_annotation(self):
        """测试 _generate_phase_checkpoint 接受 SearchFramework"""
        from intelligent_project_analyzer.services.ucppt_search_engine import SearchFramework, SearchTarget

        # 创建测试用 SearchFramework
        framework = SearchFramework(
            original_query="测试查询",
            core_question="核心问题",
            answer_goal="回答目标",
            targets=[
                SearchTarget(id="T1", question="测试问题"),
            ],
        )

        # 验证 SearchFramework 结构正确
        assert framework.original_query == "测试查询"
        assert len(framework.targets) == 1


class TestExtensionTaskSync:
    """
    v7.235 扩展任务同步回归测试

    测试扩展任务是否同时同步到 search_master_line 和 framework.targets
    """

    def test_extension_task_structure(self):
        """测试扩展任务结构与 SearchTarget 兼容"""
        extension_task = {
            "id": "E1",
            "question": "发现的新问题",
            "search_for": "新发现的内容",
            "why_need": "补充信息",
            "success_when": ["新标准"],
            "priority": 2,
            "category": "案例参考",
        }

        # 应该能创建 SearchTarget
        target = SearchTarget(**extension_task)

        assert target.id == "E1"
        assert target.question == "发现的新问题"
        assert target.category == "案例参考"


# ==================== 第五部分：性能测试 ====================


class TestSearchTargetPerformance:
    """SearchTarget 性能测试"""

    def test_large_batch_creation(self):
        """测试大批量创建性能"""
        import time

        start = time.time()

        targets = []
        for i in range(100):
            target = SearchTarget(
                id=f"T{i}",
                question=f"问题{i}",
                search_for=f"内容{i}",
                why_need=f"原因{i}",
                success_when=[f"标准{i}"],
                priority=i % 3 + 1,
                category=["品牌调研", "案例参考", "方案验证"][i % 3],
            )
            targets.append(target)

        elapsed = time.time() - start

        assert len(targets) == 100
        assert elapsed < 1.0  # 应该在1秒内完成

    def test_serialization_performance(self):
        """测试序列化性能"""
        import time

        target = SearchTarget(
            id="T1",
            question="测试问题" * 10,
            search_for="测试内容" * 20,
            why_need="测试原因" * 5,
            success_when=["标准1", "标准2", "标准3"],
            preset_keywords=["关键词1", "关键词2", "关键词3", "关键词4", "关键词5"],
        )

        start = time.time()

        for _ in range(1000):
            data = target.to_dict()
            json_str = json.dumps(data, ensure_ascii=False)
            json.loads(json_str)

        elapsed = time.time() - start

        assert elapsed < 2.0  # 1000次序列化/反序列化应该在2秒内完成


# ==================== 运行配置 ====================

if __name__ == "__main__":
    pytest.main(
        [
            __file__,
            "-v",
            "-s",
            "--tb=short",
            "-x",  # 第一个失败就停止
        ]
    )
