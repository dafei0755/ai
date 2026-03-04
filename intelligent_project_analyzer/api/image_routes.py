"""
MT-1 (2026-03-01): 图像生成与管理路由

从 api/server.py 提取的图像相关端点。
外部状态通过 _server 惰性代理访问（避免循环导入）。
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query
from loguru import logger
from pydantic import BaseModel

from intelligent_project_analyzer.settings import settings  # 直接导入，无循环依赖

router = APIRouter(tags=["Images"])
from intelligent_project_analyzer.api._server_proxy import server_proxy as _server


#  v7.40.1: 图像重新生成 API
#  v7.41: 扩展支持多图、参数控制、保存副本
class RegenerateImageRequest(BaseModel):
    expert_name: str
    new_prompt: str
    #  v7.41: 新增字段
    save_as_copy: bool = False  # 是否保存为副本（默认覆盖）
    image_id: str | None = None  # 要替换的图像ID（多图模式）
    aspect_ratio: str | None = "16:9"  # 宽高比
    style_type: str | None = None  # 风格类型


class AddImageRequest(BaseModel):
    """v7.41: 新增概念图请求"""

    expert_name: str
    prompt: str
    aspect_ratio: str | None = "16:9"
    style_type: str | None = None


class DeleteImageRequest(BaseModel):
    """v7.41: 删除概念图请求"""

    expert_name: str
    image_id: str | None = None  # 如果为空，删除该专家的所有图像


@router.post("/api/analysis/regenerate-image/{session_id}")
async def regenerate_expert_image(session_id: str, request: RegenerateImageRequest):
    """
    重新生成专家概念图像

     v7.40.1: 允许用户编辑提示词后重新生成图像
     v7.41: 支持保存为副本、参数控制
    """
    try:
        # 获取会话
        session = await _server.session_manager.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")

        logger.info(f" 开始重新生成图像: session={session_id}, expert={request.expert_name}")
        logger.info(f" 新提示词: {request.new_prompt[:100]}...")
        logger.info(
            f"️ 参数: aspect_ratio={request.aspect_ratio}, style_type={request.style_type}, save_as_copy={request.save_as_copy}"
        )

        # 检查图像生成是否启用
        if not settings.image_generation.enabled:
            raise HTTPException(status_code=400, detail="图像生成功能未启用")

        # 导入图像生成服务
        from intelligent_project_analyzer.services.image_generator import ImageGeneratorService

        image_service = ImageGeneratorService()

        #  v7.60.4: 修复参数名称和类型（style_type→style, string→enum）
        result = await image_service.generate_image(
            prompt=request.new_prompt,
            aspect_ratio=_server._parse_aspect_ratio(request.aspect_ratio),
            style=request.style_type,
        )

        if not result.success:
            logger.error(f" 图像生成失败: {result.error}")
            return {"success": False, "error": result.error or "图像生成失败"}

        #  v7.60.5: 累加图像生成Token到会话metadata
        if result.total_tokens > 0:
            from intelligent_project_analyzer.utils.token_utils import update_session_tokens

            token_data = {
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.completion_tokens,
                "total_tokens": result.total_tokens,
            }
            success = await update_session_tokens(
                _server.session_manager, session_id, token_data, agent_name="image_generation"
            )
            if success:
                logger.info(f" [图像Token] 已累加 {result.total_tokens} tokens 到会话 {session_id}")

        logger.info(f" 图像重新生成成功: expert={request.expert_name}")

        #  v7.41: 生成唯一ID
        import uuid

        new_image_id = str(uuid.uuid4())[:8]

        new_image_data = {
            "expert_name": request.expert_name,
            "image_url": result.image_url,
            "prompt": request.new_prompt,
            "id": new_image_id,
            "aspect_ratio": request.aspect_ratio,
            "style_type": request.style_type,
            "created_at": datetime.now().isoformat(),
        }

        # 更新会话中的图像数据
        final_report = session.get("final_report", {})
        if isinstance(final_report, dict):
            generated_images_by_expert = final_report.get("generated_images_by_expert", {})

            #  v7.41: 多图支持
            if request.expert_name in generated_images_by_expert:
                existing = generated_images_by_expert[request.expert_name]

                # 兼容旧格式（单图对象 -> 数组）
                if isinstance(existing, dict) and "images" not in existing:
                    existing = {"expert_name": request.expert_name, "images": [existing]}
                elif isinstance(existing, dict) and "images" in existing:
                    pass  # 已经是新格式
                else:
                    existing = {"expert_name": request.expert_name, "images": []}

                images = existing.get("images", [])

                if request.save_as_copy:
                    # 保存为副本（最多3张）
                    if len(images) >= 3:
                        logger.warning(f"️ 专家 {request.expert_name} 已有3张图像，无法添加更多")
                        return {"success": False, "error": "已达到最大图像数量（3张）"}
                    images.append(new_image_data)
                else:
                    # 覆盖：替换指定图像或第一张
                    if request.image_id:
                        for i, img in enumerate(images):
                            if img.get("id") == request.image_id:
                                images[i] = new_image_data
                                break
                        else:
                            # 未找到指定ID，追加
                            if len(images) < 3:
                                images.append(new_image_data)
                    elif images:
                        images[0] = new_image_data
                    else:
                        images.append(new_image_data)

                existing["images"] = images
                generated_images_by_expert[request.expert_name] = existing
            else:
                # 新专家，创建新条目
                generated_images_by_expert[request.expert_name] = {
                    "expert_name": request.expert_name,
                    "images": [new_image_data],
                }

            final_report["generated_images_by_expert"] = generated_images_by_expert
            session["final_report"] = final_report
            await _server.session_manager.update(session_id, session)
            logger.info(" 已更新会话中的图像数据")

        return {
            "success": True,
            "image_url": result.image_url,
            "prompt": request.new_prompt,
            "expert_name": request.expert_name,
            "image_id": new_image_id,
            "aspect_ratio": request.aspect_ratio,
            "style_type": request.style_type,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f" 重新生成图像失败: {e}")
        import traceback

        traceback.print_exc()
        return {"success": False, "error": str(e)}


#  v7.41: 新增概念图 API
@router.post("/api/analysis/add-image/{session_id}")
async def add_expert_image(session_id: str, request: AddImageRequest):
    """
    为专家新增概念图（最多3张）
    """
    try:
        session = await _server.session_manager.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")

        logger.info(f" 新增概念图: session={session_id}, expert={request.expert_name}")

        if not settings.image_generation.enabled:
            raise HTTPException(status_code=400, detail="图像生成功能未启用")

        # 检查是否已达到上限
        final_report = session.get("final_report", {})
        generated_images_by_expert = final_report.get("generated_images_by_expert", {})

        if request.expert_name in generated_images_by_expert:
            existing = generated_images_by_expert[request.expert_name]
            # 兼容旧格式
            if isinstance(existing, dict) and "images" not in existing:
                images = [existing]
            elif isinstance(existing, dict) and "images" in existing:
                images = existing.get("images", [])
            else:
                images = []

            if len(images) >= 3:
                return {"success": False, "error": "已达到最大图像数量（3张）"}

        from intelligent_project_analyzer.services.image_generator import ImageGeneratorService

        image_service = ImageGeneratorService()
        #  v7.60.4: 修复参数名称和类型（style_type→style, string→enum）
        result = await image_service.generate_image(
            prompt=request.prompt,
            aspect_ratio=_server._parse_aspect_ratio(request.aspect_ratio),
            style=request.style_type,
        )

        if not result.success:
            return {"success": False, "error": result.error or "图像生成失败"}

        #  v7.60.5: 累加图像生成Token到会话metadata
        if result.total_tokens > 0:
            from intelligent_project_analyzer.utils.token_utils import update_session_tokens

            token_data = {
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.completion_tokens,
                "total_tokens": result.total_tokens,
            }
            success = await update_session_tokens(
                _server.session_manager, session_id, token_data, agent_name="image_generation"
            )
            if success:
                logger.info(f" [图像Token] 已累加 {result.total_tokens} tokens 到会话 {session_id}")

        import uuid

        new_image_id = str(uuid.uuid4())[:8]

        new_image_data = {
            "expert_name": request.expert_name,
            "image_url": result.image_url,
            "prompt": request.prompt,
            "id": new_image_id,
            "aspect_ratio": request.aspect_ratio,
            "style_type": request.style_type,
            "created_at": datetime.now().isoformat(),
        }

        # 更新会话
        if request.expert_name in generated_images_by_expert:
            existing = generated_images_by_expert[request.expert_name]
            if isinstance(existing, dict) and "images" not in existing:
                existing = {"expert_name": request.expert_name, "images": [existing]}
            existing["images"].append(new_image_data)
            generated_images_by_expert[request.expert_name] = existing
        else:
            generated_images_by_expert[request.expert_name] = {
                "expert_name": request.expert_name,
                "images": [new_image_data],
            }

        final_report["generated_images_by_expert"] = generated_images_by_expert
        session["final_report"] = final_report
        await _server.session_manager.update(session_id, session)

        logger.info(f" 新增概念图成功: id={new_image_id}")

        return {"success": True, "image": new_image_data}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f" 新增概念图失败: {e}")
        return {"success": False, "error": str(e)}


#  v7.41: 删除概念图 API
@router.delete("/api/analysis/delete-image/{session_id}")
async def delete_expert_image(session_id: str, request: DeleteImageRequest):
    """
    删除专家概念图
    """
    try:
        session = await _server.session_manager.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")

        logger.info(f"️ 删除概念图: session={session_id}, expert={request.expert_name}, image_id={request.image_id}")

        final_report = session.get("final_report", {})
        generated_images_by_expert = final_report.get("generated_images_by_expert", {})

        if request.expert_name not in generated_images_by_expert:
            return {"success": False, "error": "未找到该专家的概念图"}

        existing = generated_images_by_expert[request.expert_name]

        if request.image_id:
            # 删除指定图像
            if isinstance(existing, dict) and "images" in existing:
                images = existing.get("images", [])
                images = [img for img in images if img.get("id") != request.image_id]
                if images:
                    existing["images"] = images
                    generated_images_by_expert[request.expert_name] = existing
                else:
                    del generated_images_by_expert[request.expert_name]
            else:
                # 旧格式单图，直接删除
                del generated_images_by_expert[request.expert_name]
        else:
            # 删除该专家的所有图像
            del generated_images_by_expert[request.expert_name]

        final_report["generated_images_by_expert"] = generated_images_by_expert
        session["final_report"] = final_report
        await _server.session_manager.update(session_id, session)

        logger.info(" 删除概念图成功")

        return {"success": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f" 删除概念图失败: {e}")
        return {"success": False, "error": str(e)}


#  v7.41: 智能推荐提示词 API
@router.get("/api/analysis/suggest-prompts/{session_id}/{expert_name}")
async def suggest_image_prompts(session_id: str, expert_name: str):
    """
    基于专家报告关键词生成3个推荐提示词

    策略：从专家报告中提取关键概念，组合成可视化提示词
    """
    try:
        session = await _server.session_manager.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")

        logger.info(f" 生成推荐提示词: session={session_id}, expert={expert_name}")

        final_report = session.get("final_report", {})
        expert_reports = final_report.get("expert_reports", {})

        # 查找专家报告
        expert_content = None
        expert_dynamic_name = expert_name

        for key, value in expert_reports.items():
            # 匹配专家名称（支持多种格式）
            if expert_name in key or key in expert_name:
                expert_content = value
                expert_dynamic_name = key
                break

        if not expert_content:
            # 尝试从 agent_results 获取
            agent_results = session.get("agent_results", {})
            for key, value in agent_results.items():
                if expert_name in key or key in expert_name:
                    if isinstance(value, dict):
                        expert_content = value.get("content", "")
                    else:
                        expert_content = str(value)
                    break

        if not expert_content:
            logger.warning(f"️ 未找到专家报告: {expert_name}")
            # 返回默认推荐
            return {
                "success": True,
                "suggestions": [
                    {
                        "label": "现代室内设计",
                        "prompt": f"A modern interior design concept for {expert_name}, featuring clean lines and warm lighting",
                        "keywords": ["modern", "interior", "design"],
                        "confidence": 0.6,
                    },
                    {
                        "label": "空间材质可视化",
                        "prompt": "An architectural visualization showing spatial arrangement and material textures",
                        "keywords": ["architecture", "spatial", "materials"],
                        "confidence": 0.5,
                    },
                    {
                        "label": "概念风格展板",
                        "prompt": "A conceptual design mood board with color palette and style references",
                        "keywords": ["concept", "mood board", "style"],
                        "confidence": 0.5,
                    },
                ],
            }

        # 从专家报告中提取关键词
        import re

        import jieba

        # 清理内容
        if isinstance(expert_content, dict):
            content_text = json.dumps(expert_content, ensure_ascii=False)
        else:
            content_text = str(expert_content)

        # 提取中文关键词
        words = list(jieba.cut(content_text))

        # 过滤常见词和短词
        stop_words = {
            "的",
            "是",
            "在",
            "和",
            "与",
            "了",
            "将",
            "对",
            "为",
            "等",
            "中",
            "以",
            "及",
            "到",
            "从",
            "有",
            "这",
            "个",
            "人",
            "我",
            "们",
            "你",
            "他",
            "她",
            "它",
        }
        keywords = [w for w in words if len(w) >= 2 and w not in stop_words]

        # 统计词频
        from collections import Counter

        word_freq = Counter(keywords)
        top_keywords = [word for word, _ in word_freq.most_common(30)]

        # 提取设计相关关键词
        design_keywords = []
        design_patterns = [
            r"(空间|布局|风格|材质|色彩|灯光|家具|装饰|功能区|动线)",
            r"(现代|简约|奢华|自然|工业|北欧|日式|中式|美式)",
            r"(客厅|卧室|厨房|书房|阳台|玄关|餐厅|卫生间)",
            r"(木质|石材|金属|玻璃|皮革|织物|大理石)",
            r"(温馨|舒适|明亮|开放|私密|层次|对比)",
        ]

        for pattern in design_patterns:
            matches = re.findall(pattern, content_text)
            design_keywords.extend(matches)

        # 合并关键词
        all_keywords = list(set(design_keywords + top_keywords[:15]))[:20]

        # 生成推荐提示词
        suggestions = []

        # 提示词模板（包含中文标签）
        templates = [
            {
                "label": "空间氛围渲染",
                "template": "A {style} interior design concept featuring {material} elements, {lighting} lighting, and {mood} atmosphere, professional architectural visualization, 8K",
                "defaults": {
                    "style": "modern minimalist",
                    "material": "natural wood and marble",
                    "lighting": "warm ambient",
                    "mood": "serene and inviting",
                },
            },
            {
                "label": "功能区规划",
                "template": "Spatial visualization of {space} with {feature} design, {color} color palette, {style} aesthetic, photorealistic rendering",
                "defaults": {
                    "space": "open living area",
                    "feature": "flowing",
                    "color": "neutral earth tone",
                    "style": "contemporary",
                },
            },
            {
                "label": "设计概念图",
                "template": "Conceptual design for {function} space, emphasizing {quality} and {element}, {style} style, architectural photography",
                "defaults": {
                    "function": "multi-functional",
                    "quality": "natural light flow",
                    "element": "spatial hierarchy",
                    "style": "Scandinavian",
                },
            },
        ]

        # 根据关键词填充模板
        for i, template_info in enumerate(templates):
            template = template_info["template"]
            defaults = template_info["defaults"]

            # 尝试用提取的关键词替换默认值
            filled = template
            used_keywords = []

            for key, default_value in defaults.items():
                # 查找相关关键词
                relevant = [kw for kw in all_keywords if kw not in used_keywords]
                if relevant and i < len(all_keywords):
                    # 选择一个关键词
                    keyword = relevant[i % len(relevant)]
                    used_keywords.append(keyword)
                    filled = filled.replace(
                        f"{{{key}}}",
                        f"{keyword} {default_value.split()[0]}" if len(default_value.split()) > 1 else keyword,
                    )
                else:
                    filled = filled.replace(f"{{{key}}}", default_value)

            suggestions.append(
                {
                    "label": template_info["label"],
                    "prompt": filled,
                    "keywords": used_keywords[:5] if used_keywords else list(defaults.values())[:3],
                    "confidence": 0.8 - (i * 0.1),
                }
            )

        logger.info(f" 生成了 {len(suggestions)} 个推荐提示词")

        return {"success": True, "suggestions": suggestions, "extracted_keywords": all_keywords[:10]}

    except Exception as e:
        logger.error(f" 生成推荐提示词失败: {e}")
        import traceback

        traceback.print_exc()
        return {"success": False, "error": str(e), "suggestions": []}


# ============================================================================
#  v7.48: 图像对话历史 API（Google AI Studio 风格）
# ============================================================================


class ImageChatTurnModel(BaseModel):
    """单轮对话模型"""

    turn_id: str
    type: str  # 'user' | 'assistant'
    timestamp: str
    prompt: str | None = None
    aspect_ratio: str | None = None
    style_type: str | None = None
    reference_image_url: str | None = None
    image: Dict[str, Any] | None = None  # ExpertGeneratedImage
    error: str | None = None


class ImageChatHistoryRequest(BaseModel):
    """保存对话历史请求"""

    turns: List[ImageChatTurnModel]


class RegenerateImageWithContextRequest(BaseModel):
    """带上下文的图像生成请求"""

    expert_name: str
    prompt: str
    aspect_ratio: str | None = "16:9"
    style_type: str | None = None
    reference_image: str | None = None
    context: str | None = None  # 多轮对话上下文
    #  v7.61: Vision 分析参数
    use_vision_analysis: bool | None = True
    vision_focus: str | None = "comprehensive"
    #  v7.62: Inpainting 图像编辑参数
    mask_image: str | None = None  # Mask 图像 Base64（黑色=保留，透明=编辑）
    edit_mode: bool | None = False  # 是否为编辑模式（有mask时自动为True）


@router.get("/api/analysis/image-chat-history/{session_id}/{expert_name}")
async def get_image_chat_history(session_id: str, expert_name: str):
    """
    获取专家的图像对话历史

     v7.48: 支持 Google AI Studio 风格的图像生成对话
    """
    try:
        session = await _server.session_manager.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")

        logger.info(f" 获取图像对话历史: session={session_id}, expert={expert_name}")

        # 从 session 中获取对话历史
        image_chat_histories = session.get("image_chat_histories", {})
        expert_history = image_chat_histories.get(expert_name, {})

        if not expert_history:
            # 返回空历史
            return {
                "success": True,
                "history": {
                    "expert_name": expert_name,
                    "session_id": session_id,
                    "turns": [],
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                },
            }

        return {"success": True, "history": expert_history}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f" 获取图像对话历史失败: {e}")
        return {"success": False, "error": str(e)}


@router.post("/api/analysis/image-chat-history/{session_id}/{expert_name}")
async def save_image_chat_history(session_id: str, expert_name: str, request: ImageChatHistoryRequest):
    """
    保存专家的图像对话历史

     v7.48: 对话历史持久化，支持删除整条对话记录
    """
    try:
        session = await _server.session_manager.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")

        logger.info(f" 保存图像对话历史: session={session_id}, expert={expert_name}, turns={len(request.turns)}")

        # 获取或初始化对话历史存储
        if "image_chat_histories" not in session:
            session["image_chat_histories"] = {}

        # 转换 turns 为字典格式存储
        turns_data = [turn.dict() for turn in request.turns]

        # 保存对话历史
        session["image_chat_histories"][expert_name] = {
            "expert_name": expert_name,
            "session_id": session_id,
            "turns": turns_data,
            "created_at": session["image_chat_histories"]
            .get(expert_name, {})
            .get("created_at", datetime.now().isoformat()),
            "updated_at": datetime.now().isoformat(),
        }

        await _server.session_manager.update(session_id, session)

        logger.info(" 图像对话历史已保存")

        return {"success": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f" 保存图像对话历史失败: {e}")
        return {"success": False, "error": str(e)}


@router.post("/api/analysis/regenerate-image-with-context/{session_id}")
async def regenerate_image_with_context(session_id: str, request: RegenerateImageWithContextRequest):
    """
    带多轮对话上下文的图像生成

     v7.48: 支持多轮对话上下文传递给 LLM，实现更连贯的图像生成

    上下文格式：将之前的 prompts 拼接为字符串，帮助 LLM 理解用户意图演变
    """
    try:
        session = await _server.session_manager.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")

        logger.info(f" 带上下文生成图像: session={session_id}, expert={request.expert_name}")
        logger.info(f"   提示词: {request.prompt[:100]}...")
        if request.context:
            logger.info(f"   上下文: {request.context[:200]}...")

        if not settings.image_generation.enabled:
            raise HTTPException(status_code=400, detail="图像生成功能未启用")

        from intelligent_project_analyzer.services.image_generator import ImageGeneratorService

        image_service = ImageGeneratorService()

        def _build_top_constraints(session_data: Dict[str, Any]) -> str:
            """自动从项目类型与需求分析提取顶层约束，用于统一图像风格。"""
            final_report = session_data.get("final_report", {}) if isinstance(session_data, dict) else {}
            req = {}
            if isinstance(final_report, dict):
                req = final_report.get("requirements_analysis", {}) or final_report.get("structured_data", {}) or {}

            def _pick_str(*vals: Any) -> str:
                for v in vals:
                    if isinstance(v, str) and v.strip():
                        return v.strip()
                return ""

            def _pick_list(val: Any) -> str:
                if isinstance(val, list):
                    cleaned = [str(x).strip() for x in val if str(x).strip()]
                    if cleaned:
                        return "；".join(cleaned[:4])
                return ""

            project_type = _pick_str(
                session_data.get("project_type") if isinstance(session_data, dict) else "",
                req.get("project_type") if isinstance(req, dict) else "",
                final_report.get("project_type") if isinstance(final_report, dict) else "",
            )
            overview = _pick_str(
                req.get("project_overview") if isinstance(req, dict) else "",
                req.get("project_task") if isinstance(req, dict) else "",
                req.get("project_tasks") if isinstance(req, dict) else "",
            )
            objectives = _pick_list(req.get("core_objectives") if isinstance(req, dict) else [])
            constraints = _pick_str(req.get("constraints_opportunities") if isinstance(req, dict) else "")
            user_input = _pick_str(
                session_data.get("user_input") if isinstance(session_data, dict) else "",
                final_report.get("user_input") if isinstance(final_report, dict) else "",
            )

            pieces: List[str] = []
            if project_type:
                pieces.append(f"Project type: {project_type}")
            if overview:
                pieces.append(f"Overview: {overview}")
            if objectives:
                pieces.append(f"Objectives: {objectives}")
            if constraints:
                pieces.append(f"Constraints: {constraints}")
            if user_input and len(pieces) < 3:
                pieces.append(f"User intent: {user_input[:200]}")

            text = "\n".join(pieces)
            if len(text) > 600:
                text = text[:600]
            return text

        def _get_expert_context(session_data: Dict[str, Any], expert_name: str) -> str:
            """v7.50: 获取专家报告上下文用于 LLM 增强"""
            final_report = session_data.get("final_report", {}) if isinstance(session_data, dict) else {}
            expert_reports = final_report.get("expert_reports", {}) if isinstance(final_report, dict) else {}

            expert_content = expert_reports.get(expert_name, "")
            if isinstance(expert_content, dict):
                # 提取关键字段
                parts = []
                for key in ["structured_data", "content", "narrative_summary"]:
                    if key in expert_content:
                        val = expert_content[key]
                        if isinstance(val, str):
                            parts.append(val[:400])
                        elif isinstance(val, dict):
                            parts.append(json.dumps(val, ensure_ascii=False)[:400])
                return " ".join(parts)[:1000]
            elif isinstance(expert_content, str):
                return expert_content[:1000]
            return ""

        #  v7.50: 使用 LLM 增强用户输入的提示词
        constraint_text = _build_top_constraints(session)
        expert_context = _get_expert_context(session, request.expert_name)

        #  v7.61: Vision 分析集成 (如果有参考图且启用 Vision)
        vision_analysis_text = None
        if request.reference_image and request.use_vision_analysis:
            try:
                from intelligent_project_analyzer.services.vision_service import get_vision_service

                logger.info(" [v7.61] 开始 Vision 分析参考图...")
                vision_service = get_vision_service()

                vision_result = await vision_service.analyze_design_image(
                    image_data=request.reference_image, analysis_type=request.vision_focus or "comprehensive"
                )

                if vision_result.success:
                    logger.info(f" Vision 分析成功: {len(vision_result.features or {})} 个特征")
                    vision_analysis_text = vision_result.analysis

                    # 添加结构化特征
                    features = vision_result.features or {}
                    if features.get("colors"):
                        vision_analysis_text += f"\n主色调: {', '.join(features['colors'][:3])}"
                    if features.get("styles"):
                        vision_analysis_text += f"\n风格: {', '.join(features['styles'][:3])}"
                    if features.get("materials"):
                        vision_analysis_text += f"\n材质: {', '.join(features['materials'][:3])}"
                else:
                    logger.warning(f"️ Vision 分析失败: {vision_result.error}")

            except Exception as e:
                logger.error(f" Vision 分析异常: {e}")
                # 优雅降级：继续使用纯文本模式

        #  v7.62: Inpainting 编辑模式路由（双模式架构）
        if request.mask_image:
            logger.info(" [v7.62 Dual-Mode] 检测到 Mask，路由到编辑模式")

            try:
                from intelligent_project_analyzer.services.inpainting_service import (
                    get_inpainting_service,
                )

                # 获取 Inpainting 服务（需要 OPENAI_API_KEY）
                openai_key = os.getenv("OPENAI_API_KEY")
                inpainting_service = get_inpainting_service(api_key=openai_key)

                if not inpainting_service.is_available():
                    logger.warning("️ Inpainting 服务不可用（缺少 OPENAI_API_KEY），回退到生成模式")
                else:
                    # 调用双模式方法（会自动使用 Inpainting 或回退）
                    result = await image_service.edit_image_with_mask(
                        original_image=request.reference_image,
                        mask_image=request.mask_image,
                        prompt=request.prompt,
                        aspect_ratio=_server._parse_aspect_ratio(request.aspect_ratio),
                        style=request.style_type,
                        inpainting_service=inpainting_service,
                    )

                    # 如果成功，直接返回结果（跳过后续 LLM 增强）
                    if result.success:
                        import uuid

                        new_image_id = str(uuid.uuid4())[:8]

                        new_image_data = {
                            "expert_name": request.expert_name,
                            "image_url": result.image_url,
                            "prompt": request.prompt,
                            "prompt_used": result.revised_prompt or request.prompt,
                            "id": new_image_id,
                            "aspect_ratio": request.aspect_ratio,
                            "style_type": request.style_type,
                            "created_at": datetime.now().isoformat(),
                            "edit_mode": True,  #  v7.62: 标记为编辑模式
                            "model_used": result.model_used,
                        }

                        # 更新 session
                        final_report = session.get("final_report", {})
                        generated_images_by_expert = final_report.get("generated_images_by_expert", {})

                        if request.expert_name in generated_images_by_expert:
                            existing = generated_images_by_expert[request.expert_name]
                            if isinstance(existing, dict) and "images" not in existing:
                                existing = {"expert_name": request.expert_name, "images": [existing]}
                            if "images" not in existing:
                                existing["images"] = []
                            existing["images"].append(new_image_data)
                            generated_images_by_expert[request.expert_name] = existing
                        else:
                            generated_images_by_expert[request.expert_name] = {
                                "expert_name": request.expert_name,
                                "images": [new_image_data],
                            }

                        final_report["generated_images_by_expert"] = generated_images_by_expert
                        session["final_report"] = final_report
                        await _server.session_manager.update(session_id, session)

                        logger.info(f" [Inpainting Mode] 图像编辑成功: id={new_image_id}")

                        return {
                            "success": True,
                            "image_url": result.image_url,
                            "image_id": new_image_id,
                            "image_data": new_image_data,
                            "mode": "inpainting",  #  标记模式
                        }

            except ImportError:
                logger.warning("️ InpaintingService 未安装，回退到生成模式")
            except Exception as e:
                logger.error(f" Inpainting 模式异常: {e}")
                logger.warning(" 回退到生成模式")

        # 如果没有 Mask 或 Inpainting 失败，继续使用生成模式（原有逻辑）

        # 调用 LLM 增强方法（包含 Vision 特征）
        enhanced_prompt = await image_service._enhance_prompt_with_user_input(
            user_prompt=request.prompt,
            expert_context=expert_context,
            conversation_history=request.context or "",
            project_constraints=constraint_text,
            vision_analysis=vision_analysis_text,
        )

        logger.info(f" [v7.50] 提示词增强: {len(request.prompt)} → {len(enhanced_prompt)} 字符")
        logger.debug(f" 增强后提示词: {enhanced_prompt[:200]}...")

        #  v7.60.4: 修复参数名称和类型（style_type→style, string→enum）
        result = await image_service.generate_image(
            prompt=enhanced_prompt,
            aspect_ratio=_server._parse_aspect_ratio(request.aspect_ratio),
            style=request.style_type,
        )

        if not result.success:
            return {"success": False, "error": result.error or "图像生成失败"}

        #  v7.60.5: 累加图像生成Token到会话metadata（后置Token追踪）
        if result.total_tokens > 0:
            from intelligent_project_analyzer.utils.token_utils import update_session_tokens

            token_data = {
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.completion_tokens,
                "total_tokens": result.total_tokens,
            }
            success = await update_session_tokens(
                _server.session_manager, session_id, token_data, agent_name="image_generation"
            )
            if success:
                logger.info(f" [图像Token-带上下文] 已累加 {result.total_tokens} tokens 到会话 {session_id}")

        import uuid

        new_image_id = str(uuid.uuid4())[:8]

        new_image_data = {
            "expert_name": request.expert_name,
            "image_url": result.image_url,
            "prompt": request.prompt,  # 用户原始输入
            "prompt_used": enhanced_prompt,  #  v7.50: 实际使用的增强后提示词
            "id": new_image_id,
            "aspect_ratio": request.aspect_ratio,
            "style_type": request.style_type,
            "created_at": datetime.now().isoformat(),
            "has_context": bool(request.context),  # 标记是否使用了上下文
            "llm_enhanced": len(enhanced_prompt) > len(request.prompt),  #  v7.50: 标记是否经过 LLM 增强
        }

        # 同时更新到 generated_images_by_expert（保持兼容性）
        final_report = session.get("final_report", {})
        generated_images_by_expert = final_report.get("generated_images_by_expert", {})

        if request.expert_name in generated_images_by_expert:
            existing = generated_images_by_expert[request.expert_name]
            if isinstance(existing, dict) and "images" not in existing:
                existing = {"expert_name": request.expert_name, "images": [existing]}
            if "images" not in existing:
                existing["images"] = []
            existing["images"].append(new_image_data)
            generated_images_by_expert[request.expert_name] = existing
        else:
            generated_images_by_expert[request.expert_name] = {
                "expert_name": request.expert_name,
                "images": [new_image_data],
            }

        final_report["generated_images_by_expert"] = generated_images_by_expert
        session["final_report"] = final_report
        await _server.session_manager.update(session_id, session)

        logger.info(f" 带上下文图像生成成功: id={new_image_id}")

        return {"success": True, "image_url": result.image_url, "image_id": new_image_id, "image_data": new_image_data}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f" 带上下文图像生成失败: {e}")
        import traceback

        traceback.print_exc()
        return {"success": False, "error": str(e)}


@router.post("/api/images/regenerate")
async def regenerate_concept_image(
    session_id: str = Query(..., description="会话ID"),
    deliverable_id: str = Query(..., description="交付物ID"),
    aspect_ratio: str = Query(default="16:9", description="宽高比（16:9, 9:16, 1:1）"),
):
    """
    重新生成指定交付物的概念图

    Args:
        session_id: 会话ID
        deliverable_id: 交付物ID
        aspect_ratio: 宽高比（16:9, 9:16, 1:1）

    Returns:
        新生成的图片元数据
    """
    try:
        from intelligent_project_analyzer.services.image_generator import ImageGeneratorService
        from intelligent_project_analyzer.services.image_storage_manager import ImageStorageManager
        from intelligent_project_analyzer.services.redis_session_manager import RedisSessionManager

        # 获取会话状态
        session_manager = RedisSessionManager()
        state = _server.session_manager.get_state(session_id)

        if not state:
            raise HTTPException(status_code=404, detail="会话不存在")

        deliverable_metadata = state.get("deliverable_metadata", {}).get(deliverable_id)
        if not deliverable_metadata:
            raise HTTPException(status_code=404, detail="交付物不存在")

        # 获取专家分析（从agent_results中）
        owner_role = deliverable_metadata.get("owner_role")
        agent_results = state.get("agent_results", {})
        expert_result = agent_results.get(owner_role, {})
        expert_analysis = expert_result.get("analysis", "")[:500]

        # 删除旧图片
        await ImageStorageManager.delete_image(session_id, deliverable_id)

        # 重新生成
        image_generator = ImageGeneratorService()
        new_image = await image_generator.generate_deliverable_image(
            deliverable_metadata=deliverable_metadata,
            expert_analysis=expert_analysis,
            session_id=session_id,
            project_type=state.get("project_type", "interior"),
            aspect_ratio=aspect_ratio,
        )

        #  Phase 0优化: 排除None和默认值以减少响应大小
        return {"status": "success", "image": new_image.model_dump(exclude_none=True, exclude_defaults=True)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f" 重新生成概念图失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/images/{session_id}/{deliverable_id}")
async def delete_concept_image(session_id: str, deliverable_id: str):
    """删除指定交付物的概念图"""
    try:
        from intelligent_project_analyzer.services.image_storage_manager import ImageStorageManager

        success = await ImageStorageManager.delete_image(session_id, deliverable_id)

        if not success:
            raise HTTPException(status_code=404, detail="图片不存在")

        return {"status": "success", "message": "图片已删除"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f" 删除概念图失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/images/{session_id}")
async def list_session_images(session_id: str):
    """获取会话的所有概念图列表"""
    try:
        from intelligent_project_analyzer.services.image_storage_manager import ImageStorageManager

        images = await ImageStorageManager.get_session_images(session_id)

        return {"session_id": session_id, "total": len(images), "images": images}

    except Exception as e:
        logger.error(f" 获取图片列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
