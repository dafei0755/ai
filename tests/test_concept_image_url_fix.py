"""
概念图URL修复相关测试

测试覆盖：
1. result_aggregator中的字段映射（url -> image_url）
2. generated_images_by_expert数据结构
3. 端到端的概念图数据流

Author: Claude Code
Version: v7.120
"""

from unittest.mock import Mock

import pytest

from intelligent_project_analyzer.report.result_aggregator import ResultAggregatorAgent


class TestConceptImageURLMapping:
    """测试概念图URL字段映射"""

    @pytest.fixture
    def aggregator(self):
        """创建ResultAggregatorAgent实例用于测试"""
        mock_llm = Mock()
        return ResultAggregatorAgent(llm_model=mock_llm)

    def test_extract_generated_images_by_expert_basic(self, aggregator):
        """测试基本的概念图提取和字段映射"""

        # 模拟state数据
        state = {
            "agent_results": {
                "2-1": {
                    "role_id": "2-1",
                    "role_name": "V2 设计总监",
                    "expert_name": "V2 设计总监",
                    "concept_images": [
                        {
                            "id": "2-1_1_143022_abc",
                            "url": "/generated_images/session_123/concept_1.png",  # 注意：后端使用url
                            "prompt": "现代简约风格客厅设计",
                            "aspect_ratio": "16:9",
                            "style_type": "interior",
                            "deliverable_id": "2-1_1_143022_abc",
                        }
                    ],
                },
                "3-1": {
                    "role_id": "3-1",
                    "expert_name": "V3 叙事专家",
                    "concept_images": [
                        {
                            "id": "3-1_1_143025_xyz",
                            "url": "/generated_images/session_123/concept_2.png",
                            "prompt": "空间叙事流线图",
                            "aspect_ratio": "16:9",
                            "style_type": "narrative",
                        }
                    ],
                },
            }
        }

        # 调用提取方法
        result = aggregator._extract_generated_images_by_expert(state)

        # 验证结果结构
        assert "2-1" in result
        assert "3-1" in result

        # 验证V2专家的概念图
        v2_data = result["2-1"]
        assert v2_data["expert_name"] == "V2 设计总监"
        assert len(v2_data["images"]) == 1

        # 🔥 关键验证：url字段已转换为image_url
        image = v2_data["images"][0]
        assert "image_url" in image
        assert "url" not in image  # url字段应被移除
        assert image["image_url"] == "/generated_images/session_123/concept_1.png"
        assert image["id"] == "2-1_1_143022_abc"
        assert image["prompt"] == "现代简约风格客厅设计"

        # 验证V3专家的概念图
        v3_data = result["3-1"]
        assert len(v3_data["images"]) == 1
        assert "image_url" in v3_data["images"][0]
        assert "url" not in v3_data["images"][0]

    def test_extract_generated_images_skip_requirements_analyst(self, aggregator):
        """测试跳过需求分析师的概念图"""

        state = {
            "agent_results": {
                "requirements_analyst": {
                    "role_id": "requirements_analyst",
                    "concept_images": [{"url": "/some/image.png"}],
                },
                "project_director": {"role_id": "project_director", "concept_images": [{"url": "/another/image.png"}]},
                "2-1": {
                    "expert_name": "V2 设计总监",
                    "concept_images": [{"id": "test-1", "url": "/generated_images/test.png", "prompt": "测试图"}],
                },
            }
        }

        result = aggregator._extract_generated_images_by_expert(state)

        # 验证：需求分析师和项目总监不应出现在结果中
        assert "requirements_analyst" not in result
        assert "project_director" not in result

        # 验证：专家角色应正常提取
        assert "2-1" in result
        assert len(result["2-1"]["images"]) == 1

    def test_extract_generated_images_empty_concept_images(self, aggregator):
        """测试concept_images为空的情况"""

        state = {
            "agent_results": {
                "2-1": {"expert_name": "V2 设计总监", "concept_images": []},  # 空数组
                "3-1": {
                    "expert_name": "V3 叙事专家",
                    # 没有concept_images字段
                },
            }
        }

        result = aggregator._extract_generated_images_by_expert(state)

        # 验证：空的concept_images应被跳过
        assert "2-1" not in result
        assert "3-1" not in result
        assert result == {}

    def test_extract_generated_images_with_deliverable_id_fallback(self, aggregator):
        """测试当缺少id字段时使用deliverable_id作为备选"""

        state = {
            "agent_results": {
                "2-1": {
                    "expert_name": "V2 设计总监",
                    "concept_images": [
                        {
                            # 没有id字段
                            "deliverable_id": "fallback-id-123",
                            "url": "/generated_images/test.png",
                            "prompt": "测试",
                        }
                    ],
                }
            }
        }

        result = aggregator._extract_generated_images_by_expert(state)

        # 验证：应该使用deliverable_id作为id
        image = result["2-1"]["images"][0]
        assert image["id"] == "fallback-id-123"

    def test_extract_generated_images_multiple_images_per_expert(self, aggregator):
        """测试一个专家有多张概念图的情况"""

        state = {
            "agent_results": {
                "2-1": {
                    "expert_name": "V2 设计总监",
                    "concept_images": [
                        {"id": "img-1", "url": "/generated_images/session_123/img1.png", "prompt": "概念图1"},
                        {"id": "img-2", "url": "/generated_images/session_123/img2.png", "prompt": "概念图2"},
                        {"id": "img-3", "url": "/generated_images/session_123/img3.png", "prompt": "概念图3"},
                    ],
                }
            }
        }

        result = aggregator._extract_generated_images_by_expert(state)

        # 验证：所有图片都应正确提取和转换
        assert len(result["2-1"]["images"]) == 3
        for i, image in enumerate(result["2-1"]["images"], 1):
            assert "image_url" in image
            assert "url" not in image
            assert image["id"] == f"img-{i}"
            assert image["prompt"] == f"概念图{i}"


class TestConceptImageURLFormat:
    """测试概念图URL格式"""

    @pytest.fixture
    def aggregator(self):
        """创建ResultAggregatorAgent实例用于测试"""
        mock_llm = Mock()
        return ResultAggregatorAgent(llm_model=mock_llm)

    def test_relative_url_format(self, aggregator):
        """测试相对路径URL格式"""
        test_cases = [
            "/generated_images/session_123/concept_1.png",
            "/followup_images/session_456/followup_1.png",
            "/archived_images/old_session/archive_1.png",
        ]

        for test_url in test_cases:
            state = {
                "agent_results": {
                    "2-1": {"expert_name": "测试专家", "concept_images": [{"id": "test", "url": test_url, "prompt": "测试"}]}
                }
            }

            result = aggregator._extract_generated_images_by_expert(state)

            # 验证：相对路径应保持不变（在Next.js代理方案下）
            assert result["2-1"]["images"][0]["image_url"] == test_url
            # 验证：应以/开头
            assert result["2-1"]["images"][0]["image_url"].startswith("/")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
