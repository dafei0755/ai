"""
搜索查询生成节点 (v7.109)

在deliverable_id_generator之后、role_task_review之前执行，
为每个交付物生成搜索查询和概念图配置供用户审批。

Author: Claude Code
Created: 2025-12-31
Version: v1.0
"""

from typing import Any, Dict

from loguru import logger

from ...agents.search_strategy import SearchStrategyGenerator
from ...services.llm_factory import LLMFactory
from ...utils.mode_config import get_concept_image_config


def search_query_generator_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    为所有交付物生成搜索查询和概念图配置

    执行时机: deliverable_id_generator → **search_query_generator** → role_task_review

    输入state字段:
    - deliverable_metadata: Dict[str, Dict] - 交付物元数据（来自deliverable_id_generator_node）
    - analysis_mode: str - "normal" 或 "deep_thinking"
    - user_input: str - 用户输入（用于LLM上下文）
    - structured_requirements: Dict - 结构化需求（提供项目背景）

    输出state字段（更新）:
    - deliverable_metadata: 每个deliverable添加:
        - search_queries: List[str] - 2-5个搜索查询
        - concept_image_config: Dict - {count, editable, max_count}
    - project_image_aspect_ratio: str - 项目级宽高比（默认"16:9"）

    概念图配置规则:
    - 普通模式: count=1, editable=False, max_count=1
    - 深度思考模式: count=3, editable=True, max_count=10
    """

    logger.info("🔍 [搜索查询生成] 开始为交付物生成搜索查询和概念图配置...")

    # 1. 提取必要信息
    deliverable_metadata = state.get("deliverable_metadata", {})
    analysis_mode = state.get("analysis_mode", "normal")
    user_input = state.get("user_input", "")
    structured_requirements = state.get("structured_requirements", {})

    if not deliverable_metadata:
        logger.warning("⚠️ [搜索查询生成] 未找到deliverable_metadata，跳过搜索查询生成")
        return {"detail": "未找到交付物元数据", "project_image_aspect_ratio": "16:9"}  # 设置默认值

    logger.info(f"📋 [搜索查询生成] 分析模式: {analysis_mode}")
    logger.info(f"📋 [搜索查询生成] 交付物数量: {len(deliverable_metadata)}")

    # 2. 初始化搜索策略生成器
    try:
        llm_factory = LLMFactory()
        llm = llm_factory.create_llm(provider="openrouter", model_name="gpt-4o-mini", temperature=0.5)  # 使用轻量模型生成搜索查询
        search_generator = SearchStrategyGenerator(llm_model=llm)
        logger.debug("✅ [搜索查询生成] SearchStrategyGenerator已初始化（使用LLM）")
    except Exception as e:
        logger.warning(f"⚠️ [搜索查询生成] LLM初始化失败: {e}，使用降级方案（无LLM）")
        search_generator = SearchStrategyGenerator(llm_model=None)

    # 3. 获取项目任务背景（用于LLM上下文）
    project_task = structured_requirements.get("project_task", user_input[:500])

    # 🔥 v7.121: 提取问卷摘要和用户输入
    questionnaire_summary = state.get("questionnaire_summary", {})
    user_input_full = state.get("user_input", "")

    logger.debug(f"📋 [搜索查询生成] 可用数据:")
    logger.debug(f"   - 用户输入长度: {len(user_input_full)} 字符")
    logger.debug(f"   - 问卷摘要: {bool(questionnaire_summary)}")
    if questionnaire_summary:
        logger.debug(f"   - 问卷内容: {list(questionnaire_summary.keys())}")

    # 4. 为每个交付物生成搜索查询和概念图配置
    processed_count = 0
    for deliv_id, metadata in deliverable_metadata.items():
        try:
            # 4.1 生成搜索查询
            deliverable_name = metadata.get("name", "交付物")
            deliverable_description = metadata.get("description", "")
            keywords = metadata.get("keywords", [])
            constraints = metadata.get("constraints", {})

            logger.debug(f"  🔍 处理交付物: {deliverable_name} ({deliv_id})")

            # 🔥 v7.121: 传递完整数据（包含用户输入和问卷摘要）
            search_queries = search_generator.generate_deliverable_queries(
                deliverable_name=deliverable_name,
                deliverable_description=deliverable_description,
                keywords=keywords,
                constraints=constraints,
                project_task=project_task,
                user_input=user_input_full,  # 🔥 传递完整用户输入
                questionnaire_summary=questionnaire_summary,  # 🔥 传递问卷摘要
                num_queries=3,  # 每个交付物生成3个查询
            )

            metadata["search_queries"] = search_queries
            logger.debug(f"    ✅ 生成了 {len(search_queries)} 个搜索查询")

            # 4.2 设置概念图配置（使用工具函数）
            image_config = get_concept_image_config(analysis_mode)
            metadata["concept_image_config"] = {
                "count": image_config["count"],
                "editable": image_config["editable"],
                "max_count": image_config["max_count"],
            }

            # 追踪日志
            logger.info(
                f"🎨 [模式追踪] {analysis_mode} → {deliv_id}: "
                f"{image_config['count']}张概念图 "
                f"({'可调整' if image_config['editable'] else '固定'})"
            )
            logger.debug(
                f"    📷 概念图配置: {image_config['count']}张 "
                f"({image_config['mode_name']}，"
                f"{'可修改' if image_config['editable'] else '不可修改'}，"
                f"上限{image_config['max_count']}张)"
            )

            processed_count += 1

        except Exception as e:
            logger.error(f"❌ [搜索查询生成] 处理交付物 {deliv_id} 失败: {e}")
            # 设置降级配置
            metadata["search_queries"] = [
                f"{metadata.get('name', '交付物')} 设计案例 2024",
                f"{' '.join(metadata.get('keywords', [])[:2])} best practices",
                f"{metadata.get('name', '交付物')} 研究资料",
            ]
            # 使用工具函数获取降级配置
            fallback_config = get_concept_image_config(analysis_mode)
            metadata["concept_image_config"] = {
                "count": fallback_config["count"],
                "editable": fallback_config["editable"],
                "max_count": fallback_config["max_count"],
            }
            logger.warning(f"⚠️ [降级方案] 使用默认配置: {fallback_config['count']}张概念图")
            processed_count += 1

    logger.info(f"✅ [搜索查询生成] 完成！共处理 {processed_count}/{len(deliverable_metadata)} 个交付物")

    # 5. 设置项目级aspect_ratio（默认16:9横向）
    project_aspect_ratio = "16:9"

    # 调试输出：显示每个交付物的搜索查询
    for deliv_id, metadata in deliverable_metadata.items():
        logger.debug(f"  📋 {metadata.get('name')}: {len(metadata.get('search_queries', []))} 个查询")
        for i, query in enumerate(metadata.get("search_queries", [])[:2], 1):  # 只显示前2个
            logger.debug(f"    {i}. {query}")

    return {
        "deliverable_metadata": deliverable_metadata,
        "project_image_aspect_ratio": project_aspect_ratio,
        "detail": f"已为 {processed_count} 个交付物生成搜索查询和概念图配置",
    }
