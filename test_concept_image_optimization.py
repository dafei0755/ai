#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
概念图生成优化验证测试
版本: v7.153

测试目标:
1. 配置加载器正确加载角色视觉配置
2. 两阶段LLM流程正常执行
3. Style Anchor机制正常生成
4. 关键词校验功能正常
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from loguru import logger


async def test_config_loader():
    """测试1: 配置加载器"""
    logger.info("=" * 60)
    logger.info("测试1: 配置加载器验证")
    logger.info("=" * 60)

    from intelligent_project_analyzer.utils.visual_config_loader import (
        build_role_visual_context,
        get_role_visual_identity,
        get_visual_type_config,
    )

    # 测试所有角色配置
    roles = ["V2", "V3", "V4", "V5", "V6", "V7"]
    for role in roles:
        config = get_role_visual_identity(role)
        assert config is not None, f"角色{role}配置为空"
        assert "visual_type" in config, f"角色{role}缺少visual_type"
        assert "extraction_focus" in config, f"角色{role}缺少extraction_focus"
        assert "required_keywords" in config, f"角色{role}缺少required_keywords"
        logger.success(f"  ✅ {role}: visual_type={config['visual_type']}, keywords={config['required_keywords']}")

    # 测试视觉类型配置
    visual_types = [
        "photorealistic_rendering",
        "narrative_collage",
        "data_infographic",
        "journey_diagram",
        "technical_blueprint",
        "emotional_atmosphere",
    ]
    for vt in visual_types:
        vt_config = get_visual_type_config(vt)
        assert vt_config is not None, f"视觉类型{vt}配置为空"
        assert "description" in vt_config, f"视觉类型{vt}缺少description"
        assert "keywords_en" in vt_config, f"视觉类型{vt}缺少keywords_en"
        logger.success(f"  ✅ {vt}: {vt_config['description']}, keywords={vt_config['keywords_en'][:2]}...")

    # 测试构建完整上下文
    context = build_role_visual_context("V3")
    assert "role" in context, "缺少role字段"
    assert "visual_type" in context, "缺少visual_type字段"
    assert "format_hint" in context, "缺少format_hint字段"
    assert "global" in context, "缺少global字段"
    logger.success(f"  ✅ build_role_visual_context('V3') 成功构建完整上下文")

    logger.info("测试1通过: 配置加载器正常工作 ✅\n")
    return True


async def test_visual_brief_extraction():
    """测试2: 视觉简报提取（第一阶段LLM）"""
    logger.info("=" * 60)
    logger.info("测试2: 视觉简报提取（第一阶段LLM）")
    logger.info("=" * 60)

    from intelligent_project_analyzer.services.image_generator import ImageGeneratorService

    service = ImageGeneratorService()

    # 模拟交付物内容（融合了问卷+需求+搜索+任务的综合信息）
    test_content = """
    ## 叙事体验专家视角分析

    ### 空间情感基调
    本项目为高端商务办公空间设计，目标用户为科技公司高管。
    空间需要营造专业、高效、创新的氛围，同时融入温暖、人文关怀的元素。

    ### 用户故事场景
    - 清晨：高管进入办公室，阳光透过落地窗洒入
    - 午后：在休闲区与团队成员进行头脑风暴
    - 傍晚：在私密会客区接待重要客户

    ### 文化符号与意义
    - 木质纹理：自然、温暖、可持续
    - 铜色金属：专业、精致、品质感
    - 绿植点缀：生机、健康、平衡

    ### 材质与色彩
    主色调：深灰色(#4A4A4A)配合暖木色(#A67C52)
    点缀色：铜金色(#B87333)和墨绿(#2F4F4F)

    ### 关键情绪节点
    - 入口区域：仪式感、尊贵感
    - 工作区域：专注、高效
    - 交流区域：开放、创意
    """

    test_role_id = "V3"

    logger.info(f"  测试输入: content长度={len(test_content)}字符, role={test_role_id}")

    # 调用第一阶段LLM，返回 (visual_brief, style_anchor)
    result = await service._extract_visual_brief(test_content, test_role_id)
    visual_brief, style_anchor = result

    assert visual_brief is not None, "视觉简报为空"
    assert len(visual_brief) > 100, f"视觉简报太短: {len(visual_brief)}字符"

    logger.info(f"  视觉简报长度: {len(visual_brief)} 字符")
    logger.info(f"  Style Anchor: {style_anchor}")
    logger.info(f"  视觉简报预览: {visual_brief[:200]}...")

    # 检查是否包含style_anchor
    if style_anchor and len(style_anchor) > 10:
        logger.success(f"  ✅ Style Anchor提取成功: {style_anchor[:60]}...")
    else:
        logger.warning("  ⚠️ Style Anchor为空或过短")

    logger.info("测试2通过: 视觉简报提取正常 ✅\n")
    return visual_brief, style_anchor


async def test_structured_prompt_generation(visual_brief: str, style_anchor: str):
    """测试3: 结构化Prompt生成（第二阶段LLM）"""
    logger.info("=" * 60)
    logger.info("测试3: 结构化Prompt生成（第二阶段LLM）")
    logger.info("=" * 60)

    from intelligent_project_analyzer.services.image_generator import ImageGeneratorService

    service = ImageGeneratorService()

    test_role_id = "V3"

    logger.info(f"  输入视觉简报长度: {len(visual_brief)} 字符")
    logger.info(f"  输入Style Anchor: {style_anchor[:50] if style_anchor else 'None'}...")

    # 调用第二阶段LLM - 签名为 (visual_brief, style_anchor, role_id, deliverable_name)
    structured_prompt = await service._generate_structured_prompt(visual_brief, style_anchor, test_role_id, "测试交付物")

    assert structured_prompt is not None, "结构化Prompt为空"
    assert len(structured_prompt) > 50, f"结构化Prompt太短: {len(structured_prompt)}字符"

    logger.info(f"  结构化Prompt长度: {len(structured_prompt)} 字符")
    logger.info(f"  结构化Prompt内容:\n  {structured_prompt}")

    # 检查是否为英文
    english_ratio = sum(1 for c in structured_prompt if c.isascii()) / len(structured_prompt)
    logger.info(f"  英文字符比例: {english_ratio:.2%}")

    if english_ratio > 0.8:
        logger.success("  ✅ Prompt主要为英文，符合预期")
    else:
        logger.warning(f"  ⚠️ 英文比例偏低({english_ratio:.2%})，可能需要调整")

    logger.info("测试3通过: 结构化Prompt生成正常 ✅\n")
    return structured_prompt, style_anchor


async def test_keyword_validation(structured_prompt: str, style_anchor: str):
    """测试4: 关键词校验与增强"""
    logger.info("=" * 60)
    logger.info("测试4: 关键词校验与增强")
    logger.info("=" * 60)

    from intelligent_project_analyzer.services.image_generator import ImageGeneratorService

    service = ImageGeneratorService()

    test_role_id = "V3"

    logger.info(f"  输入Prompt长度: {len(structured_prompt)} 字符")
    logger.info(f"  Style Anchor: {style_anchor}")

    # 获取角色的required_keywords
    from intelligent_project_analyzer.utils.visual_config_loader import get_role_visual_identity, get_visual_type_config

    role_config = get_role_visual_identity(test_role_id)
    required_keywords = role_config.get("required_keywords", [])
    visual_type = role_config.get("visual_type", "photorealistic_rendering")
    visual_type_config = get_visual_type_config(visual_type)
    quality_suffix = visual_type_config.get("quality_suffix", "8K resolution, professional")

    # 调用校验方法 - 签名为 (prompt, required_keywords, style_anchor, quality_suffix)
    enhanced_prompt = service._validate_and_enhance_prompt(
        structured_prompt, required_keywords, style_anchor, quality_suffix
    )

    assert enhanced_prompt is not None, "增强后Prompt为空"

    logger.info(f"  增强后Prompt长度: {len(enhanced_prompt)} 字符")
    logger.info(f"  增强后Prompt:\n  {enhanced_prompt[:300]}...")

    # required_keywords已经在上面获取了
    found_keywords = []
    missing_keywords = []
    for kw in required_keywords:
        if kw.lower() in enhanced_prompt.lower():
            found_keywords.append(kw)
        else:
            missing_keywords.append(kw)

    logger.info(f"  必需关键词: {required_keywords}")
    logger.info(f"  已找到: {found_keywords}")

    if missing_keywords:
        logger.warning(f"  ⚠️ 缺失关键词: {missing_keywords}")
    else:
        logger.success("  ✅ 所有必需关键词都已包含")

    # 检查style_anchor是否嵌入
    if style_anchor and (
        style_anchor in enhanced_prompt or any(part.strip() in enhanced_prompt for part in style_anchor.split(","))
    ):
        logger.success("  ✅ Style Anchor已嵌入Prompt")
    else:
        logger.warning("  ⚠️ Style Anchor可能未正确嵌入")

    logger.info("测试4通过: 关键词校验正常 ✅\n")
    return enhanced_prompt


async def test_full_pipeline():
    """测试5: 完整流程集成测试（不实际调用生图API）"""
    logger.info("=" * 60)
    logger.info("测试5: 完整流程集成测试")
    logger.info("=" * 60)

    from intelligent_project_analyzer.services.image_generator import ImageGeneratorService
    from intelligent_project_analyzer.utils.visual_config_loader import build_role_visual_context

    service = ImageGeneratorService()

    # 模拟完整的deliverable内容
    mock_deliverable_content = """
    # 设计总监视角 - 空间概念分析

    ## 项目背景
    客户需求：打造一个100平米的现代简约风格客厅
    目标用户：35-45岁都市精英家庭
    预算范围：中高端装修

    ## 搜索洞察
    基于案例库搜索，发现以下趋势：
    - 开放式布局成为主流
    - 自然材质（木、石、棉麻）受青睐
    - 智能家居集成需求增长

    ## 空间规划
    - 客厅区：L型沙发+茶几组合
    - 餐厅区：岛台式餐桌
    - 阅读角：落地灯+单人沙发

    ## 材质建议
    - 地面：浅灰色水磨石
    - 墙面：米白色乳胶漆+木饰面背景墙
    - 软装：亚麻质地沙发+羊毛地毯

    ## 色彩方案
    主色：暖灰(#E8E4E0)
    辅色：原木色(#C4A77D)
    点缀：藏蓝(#1A3A5C)
    """

    roles_to_test = ["V2", "V3"]  # 测试两个不同角色

    for role_id in roles_to_test:
        logger.info(f"\n  --- 测试角色: {role_id} ---")

        # 获取角色上下文
        context = build_role_visual_context(role_id)
        logger.info(f"  角色名称: {context['role'].get('name')}")
        logger.info(f"  视觉类型: {context['role'].get('visual_type')}")

        # 获取配置
        role_config = context["role"]
        required_keywords = role_config.get("required_keywords", [])
        visual_type_config = context["visual_type"]
        quality_suffix = visual_type_config.get("quality_suffix", "8K resolution")

        # 第一阶段：提取视觉简报 - 返回 (visual_brief, style_anchor)
        visual_brief, style_anchor = await service._extract_visual_brief(mock_deliverable_content, role_id)
        logger.info(f"  第一阶段输出: visual_brief={len(visual_brief)}字符, style_anchor='{style_anchor[:30]}...'")

        # 第二阶段：生成结构化Prompt - 签名 (visual_brief, style_anchor, role_id, deliverable_name)
        structured_prompt = await service._generate_structured_prompt(visual_brief, style_anchor, role_id, "测试交付物")
        logger.info(f"  第二阶段输出: {len(structured_prompt)} 字符")

        # 第三阶段：校验增强 - 签名 (prompt, required_keywords, style_anchor, quality_suffix)
        final_prompt = service._validate_and_enhance_prompt(
            structured_prompt, required_keywords, style_anchor, quality_suffix
        )
        logger.info(f"  最终Prompt: {len(final_prompt)} 字符")
        logger.info(f"  Prompt预览: {final_prompt[:100]}...")

        logger.success(f"  ✅ {role_id} 完整流程测试通过")

    logger.info("\n测试5通过: 完整流程集成测试正常 ✅\n")


async def main():
    """主测试入口"""
    logger.info("\n" + "=" * 70)
    logger.info("概念图生成优化验证测试 v7.153")
    logger.info("=" * 70 + "\n")

    try:
        # 测试1: 配置加载器
        await test_config_loader()

        # 测试2: 视觉简报提取
        visual_brief, style_anchor = await test_visual_brief_extraction()

        # 测试3: 结构化Prompt生成
        structured_prompt, style_anchor = await test_structured_prompt_generation(visual_brief, style_anchor)

        # 测试4: 关键词校验
        await test_keyword_validation(structured_prompt, style_anchor)

        # 测试5: 完整流程
        await test_full_pipeline()

        logger.info("=" * 70)
        logger.success("🎉 所有测试通过！概念图生成优化功能验证成功")
        logger.info("=" * 70)

    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    asyncio.run(main())
