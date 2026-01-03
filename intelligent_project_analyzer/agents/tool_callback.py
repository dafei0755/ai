"""
Tool Call Recorder (v7.64)

使用LangChain回调机制自动记录工具调用，并转换为SearchReference格式
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

try:
    from langchain_core.callbacks import BaseCallbackHandler
    from langchain_core.outputs import LLMResult
except ImportError:
    logger.warning("LangChain callbacks not available")
    BaseCallbackHandler = object


class ToolCallRecorder(BaseCallbackHandler):
    """
    工具调用记录器（LangChain回调）

    核心功能：
    1. 拦截LLM的工具调用（on_tool_start, on_tool_end）
    2. 记录工具名称、输入、输出
    3. 解析搜索结果并转换为SearchReference格式
    4. 提供方法将记录添加到state

    使用方法：
        recorder = ToolCallRecorder(role_id="4-1")
        llm = llm.bind_tools(tools, callbacks=[recorder])
        # ... 执行后
        references = recorder.get_search_references()
    """

    def __init__(self, role_id: str, deliverable_id: Optional[str] = None, enable_recording: bool = True):
        """
        初始化工具调用记录器

        Args:
            role_id: 角色ID（如"4-1"）
            deliverable_id: 关联的交付物ID（可选）
            enable_recording: 是否启用记录（默认True）
        """
        super().__init__()
        self.role_id = role_id
        self.deliverable_id = deliverable_id or f"{role_id}_unknown"
        self.enable_recording = enable_recording

        # 工具调用记录列表
        self.tool_calls: List[Dict[str, Any]] = []

        # 当前正在执行的工具调用（用于关联start和end）
        self.active_tool_call: Optional[Dict[str, Any]] = None

        # 工具调用日志文件路径
        self.log_file = Path("logs/tool_calls.jsonl")
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"✅ ToolCallRecorder initialized for role={role_id}, "
            f"deliverable={deliverable_id}, recording={enable_recording}"
        )

    def _write_to_jsonl(self, tool_call: Dict[str, Any]) -> None:
        """
        将工具调用记录写入JSONL文件

        Args:
            tool_call: 工具调用记录
        """
        try:
            # 准备日志条目（移除冗长的输出字段）
            log_entry = {
                "timestamp": tool_call["start_time"],
                "tool_name": tool_call["tool_name"],
                "role_id": tool_call["role_id"],
                "deliverable_id": tool_call["deliverable_id"],
                "input_query": tool_call["input"][:200] if tool_call.get("input") else None,
                "output_length": len(tool_call.get("output", "")),
                "duration_ms": tool_call.get("duration_ms", 0),
                "status": tool_call["status"],
                "error": tool_call.get("error"),
            }

            # 追加写入JSONL文件
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

        except Exception as e:
            logger.error(f"❌ Failed to write tool call to JSONL: {e}")

    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs: Any) -> None:
        """
        工具调用开始时的回调

        Args:
            serialized: 工具的序列化表示
            input_str: 工具输入字符串
            **kwargs: 其他参数
        """
        if not self.enable_recording:
            return

        tool_name = serialized.get("name", "unknown_tool")

        # 创建新的工具调用记录
        self.active_tool_call = {
            "tool_name": tool_name,
            "input": input_str,
            "status": "started",
            "start_time": datetime.now().isoformat(),
            "role_id": self.role_id,
            "deliverable_id": self.deliverable_id,
        }

        logger.debug(f"🔧 Tool started: {tool_name}")

        # 🔥 v7.120: 增强日志 - 显示工具调用开始
        logger.info(f"🔧 [ToolCallRecorder] Tool START: {tool_name}")
        logger.info(f"   Role: {self.role_id}, Deliverable: {self.deliverable_id}")
        logger.info(f"   Input: {input_str[:100]}...")

    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """
        工具调用结束时的回调

        Args:
            output: 工具输出字符串
            **kwargs: 其他参数
        """
        if not self.enable_recording or not self.active_tool_call:
            return

        # 计算执行时长
        start_time = datetime.fromisoformat(self.active_tool_call["start_time"])
        end_time = datetime.now()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        # 更新当前工具调用记录
        self.active_tool_call["status"] = "completed"
        self.active_tool_call["output"] = output
        self.active_tool_call["end_time"] = end_time.isoformat()
        self.active_tool_call["duration_ms"] = duration_ms

        # 添加到记录列表
        self.tool_calls.append(self.active_tool_call.copy())

        logger.debug(f"✅ Tool completed: {self.active_tool_call['tool_name']}, " f"output_length={len(output)}")

        # 🔥 v7.120: 增强日志 - 显示工具调用完成
        logger.info(
            f"✅ [ToolCallRecorder] Tool END: {self.active_tool_call['tool_name']}, "
            f"output_length={len(output)} chars, duration={duration_ms}ms"
        )
        logger.info(f"   Total calls recorded: {len(self.tool_calls)}")

        # 🔥 v7.130: 持久化工具调用记录到JSONL
        self._write_to_jsonl(self.active_tool_call)

        # 清空当前工具调用
        self.active_tool_call = None

    def on_tool_error(self, error: Exception, **kwargs: Any) -> None:
        """
        工具调用出错时的回调

        Args:
            error: 错误异常
            **kwargs: 其他参数
        """
        if not self.enable_recording or not self.active_tool_call:
            return

        # 计算执行时长
        start_time = datetime.fromisoformat(self.active_tool_call["start_time"])
        end_time = datetime.now()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        # 更新当前工具调用记录
        self.active_tool_call["status"] = "failed"
        self.active_tool_call["error"] = str(error)
        self.active_tool_call["end_time"] = end_time.isoformat()
        self.active_tool_call["duration_ms"] = duration_ms

        # 添加到记录列表
        self.tool_calls.append(self.active_tool_call.copy())

        logger.warning(f"❌ Tool failed: {self.active_tool_call['tool_name']}, " f"error={str(error)[:100]}")

        # 🔥 v7.130: 持久化工具调用记录到JSONL
        self._write_to_jsonl(self.active_tool_call)

        # 清空当前工具调用
        self.active_tool_call = None

    def get_tool_calls(self) -> List[Dict[str, Any]]:
        """
        获取所有工具调用记录

        Returns:
            工具调用记录列表
        """
        return self.tool_calls

    def get_search_references(self, deliverable_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        从工具调用记录中提取搜索引用

        Args:
            deliverable_id: 指定交付物ID（可选，默认使用初始化时的ID）

        Returns:
            SearchReference字典列表
        """
        references = []
        target_deliverable_id = deliverable_id or self.deliverable_id

        for tool_call in self.tool_calls:
            # 只处理成功完成的工具调用
            if tool_call.get("status") != "completed":
                continue

            # 只处理搜索工具
            tool_name = tool_call.get("tool_name", "")
            if not self._is_search_tool(tool_name):
                continue

            # 解析工具输出
            try:
                output_data = json.loads(tool_call.get("output", "{}"))
            except json.JSONDecodeError:
                logger.warning(f"⚠️ Failed to parse tool output for {tool_name}")
                continue

            # 提取搜索结果
            search_results = output_data.get("results", [])
            query = output_data.get("query", "") or output_data.get("precise_query", "")

            # 转换为SearchReference格式
            for result in search_results:
                reference = self._convert_to_search_reference(
                    result=result,
                    tool_name=tool_name,
                    query=query,
                    deliverable_id=target_deliverable_id,
                    timestamp=tool_call.get("end_time", ""),
                )
                if reference:
                    references.append(reference)

        logger.info(f"📚 Extracted {len(references)} search references from " f"{len(self.tool_calls)} tool calls")

        return references

    def _is_search_tool(self, tool_name: str) -> bool:
        """
        判断是否为搜索工具

        Args:
            tool_name: 工具名称

        Returns:
            是否为搜索工具
        """
        search_tools = ["tavily_search", "arxiv_search", "ragflow_kb", "ragflow_kb_tool", "bocha_search"]
        return any(st in tool_name.lower() for st in search_tools)

    def _convert_to_search_reference(
        self, result: Dict[str, Any], tool_name: str, query: str, deliverable_id: str, timestamp: str
    ) -> Optional[Dict[str, Any]]:
        """
        将搜索结果转换为SearchReference格式

        Args:
            result: 搜索结果字典
            tool_name: 工具名称
            query: 搜索查询
            deliverable_id: 交付物ID
            timestamp: 时间戳

        Returns:
            SearchReference字典，如果转换失败则返回None
        """
        try:
            # 映射工具名称到标准格式
            source_tool = self._normalize_tool_name(tool_name)

            # 提取必需字段
            title = result.get("title", "Untitled")
            snippet = result.get("snippet", "") or result.get("content", "")[:300]

            # 确保snippet不为空
            if not snippet or len(snippet.strip()) < 10:
                logger.debug(f"⚠️ Skipping result with empty snippet: {title}")
                return None

            # 构建SearchReference字典
            reference = {
                "source_tool": source_tool,
                "title": title,
                "url": result.get("url"),
                "snippet": snippet[:300],  # 限制300字符
                "relevance_score": result.get("relevance_score", 0.7),
                "quality_score": result.get("quality_score"),
                "content_complete": result.get("content_complete", True),
                "source_credibility": result.get("source_credibility", "unknown"),
                "deliverable_id": deliverable_id,
                "query": query,
                "timestamp": timestamp,
                "llm_relevance_score": result.get("llm_relevance_score"),
                "llm_scoring_reason": result.get("llm_scoring_reason"),
            }

            return reference

        except Exception as e:
            logger.warning(f"⚠️ Failed to convert search result to reference: {e}")
            return None

    def _normalize_tool_name(self, tool_name: str) -> str:
        """
        规范化工具名称到标准格式

        Args:
            tool_name: 原始工具名称

        Returns:
            标准工具名称: "tavily" | "arxiv" | "ragflow" | "bocha"
        """
        tool_name_lower = tool_name.lower()

        if "tavily" in tool_name_lower:
            return "tavily"
        elif "arxiv" in tool_name_lower:
            return "arxiv"
        elif "ragflow" in tool_name_lower:
            return "ragflow"
        elif "bocha" in tool_name_lower:
            return "bocha"
        else:
            logger.warning(f"⚠️ Unknown tool name: {tool_name}, defaulting to 'tavily'")
            return "tavily"

    def reset(self):
        """重置记录器（清空所有记录）"""
        self.tool_calls = []
        self.active_tool_call = None
        logger.debug(f"🔄 ToolCallRecorder reset for role={self.role_id}")

    def get_summary(self) -> Dict[str, Any]:
        """
        获取记录摘要

        Returns:
            摘要字典
        """
        total_calls = len(self.tool_calls)
        completed = sum(1 for c in self.tool_calls if c.get("status") == "completed")
        failed = sum(1 for c in self.tool_calls if c.get("status") == "failed")

        tool_counts = {}
        for call in self.tool_calls:
            tool_name = call.get("tool_name", "unknown")
            tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1

        return {
            "role_id": self.role_id,
            "total_calls": total_calls,
            "completed": completed,
            "failed": failed,
            "tool_counts": tool_counts,
            "has_active_call": self.active_tool_call is not None,
        }


# ============================================================================
# 辅助函数：集成到State
# ============================================================================


def add_references_to_state(
    state: Dict[str, Any], recorder: ToolCallRecorder, deliverable_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    将ToolCallRecorder的搜索引用添加到state

    Args:
        state: ProjectAnalysisState字典
        recorder: ToolCallRecorder实例
        deliverable_id: 指定交付物ID（可选）

    Returns:
        更新后的state字典
    """
    # 提取搜索引用
    new_references = recorder.get_search_references(deliverable_id)

    if not new_references:
        logger.debug("ℹ️ No search references to add to state")
        return state

    # 获取现有引用
    existing_references = state.get("search_references", [])

    # 合并引用（避免重复）
    merged_references = existing_references + new_references

    # 去重（基于title + url）
    unique_references = []
    seen = set()
    for ref in merged_references:
        key = (ref.get("title", ""), ref.get("url", ""))
        if key not in seen:
            unique_references.append(ref)
            seen.add(key)

    # 更新state
    state["search_references"] = unique_references

    logger.info(f"✅ Added {len(new_references)} new references to state " f"(total: {len(unique_references)})")

    return state
