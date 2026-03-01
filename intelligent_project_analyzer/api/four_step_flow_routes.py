"""
4步骤搜索流程 API 路由

提供4步骤搜索流程的HTTP API接口
- POST /api/search/four-step/stream - 流式执行4步骤搜索
- GET /api/search/four-step/status/{session_id} - 查询执行状态

Author: AI Assistant
Created: 2026-02-01
Version: 1.0
"""

import json
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel, Field

from intelligent_project_analyzer.core.four_step_flow_types import SearchExecutionConfig
from intelligent_project_analyzer.services.four_step_flow_orchestrator import (
    get_four_step_flow_orchestrator,
)

router = APIRouter(prefix="/api/search/four-step", tags=["Four-Step Search Flow"])


# ============================================================================
# 请求/响应模型
# ============================================================================


class FourStepSearchRequest(BaseModel):
    """4步骤搜索请求"""

    user_input: str = Field(..., description="用户输入的搜索问题")
    config: Optional[dict] = Field(None, description="搜索执行配置（可选）")


class FourStepSearchResponse(BaseModel):
    """4步骤搜索响应"""

    session_id: str = Field(..., description="会话ID")
    status: str = Field(..., description="执行状态")
    message: str = Field(..., description="状态消息")


# ============================================================================
# 辅助函数
# ============================================================================


async def optional_auth(request: Request) -> Optional[dict]:
    """可选认证依赖函数"""
    auth_header = request.headers.get("Authorization", "")

    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    # TODO: 实现JWT验证
    return None


def get_user_identifier(current_user: Optional[dict]) -> Optional[str]:
    """获取用户标识符"""
    if not current_user:
        return None
    return current_user.get("username") or str(current_user.get("user_id", ""))


# ============================================================================
# API 端点
# ============================================================================


@router.post("/stream", response_model=FourStepSearchResponse)
async def four_step_search_stream(
    request: FourStepSearchRequest,
    current_user: Optional[dict] = Depends(optional_auth),
):
    """
    流式执行4步骤搜索流程

    ## 流程说明

    1. **Step 1: 深度分析** - 理解用户需求，生成输出框架
    2. **Step 2: 搜索任务分解** - 将框架转化为具体搜索查询
    3. **Step 3: 智能搜索执行** - 执行搜索，动态增补查询
    4. **Step 4: 总结生成** - 生成最终报告

    ## SSE 事件类型

    ### Step 1 事件
    - `step1_dialogue_chunk` - 深度分析对话内容（流式）
    - `step1_extracting_structure` - 正在提取结构化数据
    - `step1_completed` - Step 1完成

    ### Step 2 事件
    - `step2_task_list_chunk` - 搜索任务清单内容（流式）
    - `step2_extracting_structure` - 正在提取结构化数据
    - `step2_completed` - Step 2完成

    ### Step 3 事件
    - `step3_query_start` - 开始执行某个查询
    - `step3_query_completed` - 查询完成
    - `step3_supplementary_added` - 添加补充查询
    - `step3_completed` - Step 3完成

    ### Step 4 事件
    - `step4_summary_chunk` - 总结内容（流式）
    - `step4_extracting_metadata` - 正在提取元数据
    - `step4_completed` - Step 4完成

    ### 流程控制事件
    - `flow_step_start` - 步骤开始
    - `flow_waiting_user_confirmation` - 等待用户确认
    - `flow_completed` - 流程完成
    - `flow_error` - 流程错误

    ## 示例

    ```bash
    curl -X POST "http://localhost:8000/api/search/four-step/stream" \\
      -H "Content-Type: application/json" \\
      -d '{
        "user_input": "深圳南山，38岁独立女性，200平米大平层，Audrey Hepburn风格"
      }'
    ```
    """
    session_id = str(uuid.uuid4())
    user_identifier = get_user_identifier(current_user)

    logger.info(
        f" [4-Step Flow] 新会话: {session_id}, " f"用户: {user_identifier or '未登录'}, " f"输入: {request.user_input[:50]}..."
    )

    # 解析配置
    config = None
    if request.config:
        try:
            config = SearchExecutionConfig(**request.config)
        except Exception as e:
            logger.warning(f"️ 配置解析失败，使用默认配置: {e}")

    # 创建编排器
    orchestrator = get_four_step_flow_orchestrator()

    async def event_generator():
        """SSE事件生成器"""
        try:
            # 发送会话开始事件
            yield "event: session_start\n"
            yield f"data: {json.dumps({'session_id': session_id, 'timestamp': datetime.now().isoformat()})}\n\n"

            # 执行4步骤流程
            async for event in orchestrator.execute_flow(request.user_input, config):
                event_type = event.get("event", "unknown")
                event_data = event.get("data", {})

                # 发送SSE事件
                yield f"event: {event_type}\n"
                yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"

                # 如果是错误事件，记录日志
                if event_type.endswith("_error"):
                    logger.error(f" [4-Step Flow] {session_id}: {event_data.get('error')}")

            # 发送会话结束事件
            yield "event: session_end\n"
            yield f"data: {json.dumps({'session_id': session_id, 'timestamp': datetime.now().isoformat()})}\n\n"

            logger.info(f" [4-Step Flow] 会话完成: {session_id}")

        except Exception as e:
            logger.error(f" [4-Step Flow] 会话异常 {session_id}: {e}")
            error_data = {"error": str(e), "session_id": session_id}
            yield "event: flow_error\n"
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用Nginx缓冲
        },
    )


@router.get("/status/{session_id}")
async def get_four_step_status(
    session_id: str,
    current_user: Optional[dict] = Depends(optional_auth),
):
    """
    查询4步骤搜索流程的执行状态

    ## 参数
    - `session_id`: 会话ID

    ## 返回
    - `status`: 执行状态（running/completed/error）
    - `current_step`: 当前步骤（1-4）
    - `progress`: 进度信息

    ## 示例

    ```bash
    curl "http://localhost:8000/api/search/four-step/status/abc-123"
    ```
    """
    # TODO: 实现状态查询（需要状态存储）
    return {
        "session_id": session_id,
        "status": "not_implemented",
        "message": "状态查询功能待实现",
    }


@router.post("/test")
async def test_four_step_flow():
    """
    测试4步骤流程（开发用）

    使用预设的测试输入执行完整流程
    """
    test_input = "深圳南山，38岁独立女性，英国海归，不婚主义，200平米大平层，" "对Audrey Hepburn赫本的经典优雅情有独钟，希望融入现代极简室内设计"

    orchestrator = get_four_step_flow_orchestrator()

    results = []
    async for event in orchestrator.execute_flow(test_input):
        results.append(event)

    return {
        "test_input": test_input,
        "total_events": len(results),
        "events": results[:10],  # 只返回前10个事件
        "message": "测试完成",
    }
