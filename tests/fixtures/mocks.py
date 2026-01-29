"""
统一Mock对象管理模块
提供常用的Mock对象和辅助函数，确保测试的一致性和可维护性
"""

import json
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock

# ============================================================================
# LLM Mock Objects
# ============================================================================


class MockLLMResponse:
    """Mock LLM响应对象"""

    def __init__(self, content: str, **kwargs):
        self.content = content
        self.additional_kwargs = kwargs

    def __str__(self):
        return self.content


class MockAsyncLLM:
    """Mock异步LLM，支持ainvoke/astream"""

    def __init__(self, responses: Optional[List[str]] = None):
        """
        Args:
            responses: 预设的响应列表，按顺序返回
        """
        self.responses = responses or ["Mock LLM Response"]
        self.call_count = 0
        self.call_history = []

    async def ainvoke(self, prompt: Any, **kwargs) -> MockLLMResponse:
        """Mock ainvoke调用"""
        self.call_history.append({"method": "ainvoke", "prompt": prompt, "kwargs": kwargs})
        response = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1
        return MockLLMResponse(response)

    async def astream(self, prompt: Any, **kwargs):
        """Mock astream调用，返回异步生成器"""
        self.call_history.append({"method": "astream", "prompt": prompt, "kwargs": kwargs})
        response = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1

        # 模拟流式返回
        for chunk in response.split():
            yield MockLLMResponse(chunk + " ")

    def invoke(self, prompt: Any, **kwargs) -> MockLLMResponse:
        """Mock同步invoke调用"""
        self.call_history.append({"method": "invoke", "prompt": prompt, "kwargs": kwargs})
        response = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1
        return MockLLMResponse(response)

    def reset(self):
        """重置mock状态"""
        self.call_count = 0
        self.call_history.clear()


def create_mock_llm(responses: Optional[List[str]] = None) -> MockAsyncLLM:
    """
    创建Mock LLM对象

    Args:
        responses: 预设的响应列表

    Returns:
        MockAsyncLLM实例
    """
    return MockAsyncLLM(responses)


def create_structured_llm_response(data: Dict[str, Any]) -> str:
    """
    创建结构化的LLM响应（JSON格式）

    Args:
        data: 要返回的数据字典

    Returns:
        JSON字符串
    """
    return json.dumps(data, ensure_ascii=False, indent=2)


# ============================================================================
# Redis Mock Objects
# ============================================================================


class MockRedisClient:
    """Mock Redis客户端，模拟内存存储"""

    def __init__(self):
        self.data = {}
        self.connected = True

    async def get(self, key: str) -> Optional[bytes]:
        """获取键值"""
        value = self.data.get(key)
        if value is not None and isinstance(value, str):
            return value.encode("utf-8")
        return value

    async def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """设置键值"""
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        self.data[key] = value
        return True

    async def delete(self, *keys: str) -> int:
        """删除键"""
        deleted = 0
        for key in keys:
            if key in self.data:
                del self.data[key]
                deleted += 1
        return deleted

    async def exists(self, *keys: str) -> int:
        """检查键是否存在"""
        return sum(1 for key in keys if key in self.data)

    async def keys(self, pattern: str = "*") -> List[str]:
        """获取匹配的键列表"""
        # 简单实现，仅支持 * 通配符
        if pattern == "*":
            return list(self.data.keys())
        # 简化处理，实际可以用fnmatch
        prefix = pattern.replace("*", "")
        return [k for k in self.data.keys() if k.startswith(prefix)]

    async def expire(self, key: str, seconds: int) -> bool:
        """设置过期时间（mock中不实际过期）"""
        return key in self.data

    async def ping(self) -> bool:
        """Ping检查"""
        return self.connected

    async def close(self):
        """关闭连接"""
        self.connected = False

    def reset(self):
        """重置所有数据"""
        self.data.clear()


def create_mock_redis() -> MockRedisClient:
    """创建Mock Redis客户端"""
    return MockRedisClient()


# ============================================================================
# Workflow Mock Objects
# ============================================================================


class MockWorkflowState:
    """Mock LangGraph状态对象"""

    def __init__(self, initial_state: Optional[Dict[str, Any]] = None):
        self.state = initial_state or {}
        self.updates = []

    def get(self, key: str, default=None):
        """获取状态值"""
        return self.state.get(key, default)

    def update(self, updates: Dict[str, Any]):
        """更新状态"""
        self.state.update(updates)
        self.updates.append(updates.copy())

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.state.copy()


class MockCheckpointer:
    """Mock LangGraph Checkpointer"""

    def __init__(self):
        self.checkpoints = {}

    async def aput(self, config: Dict[str, Any], checkpoint: Dict[str, Any]):
        """保存检查点"""
        session_id = config.get("configurable", {}).get("thread_id", "default")
        if session_id not in self.checkpoints:
            self.checkpoints[session_id] = []
        self.checkpoints[session_id].append(checkpoint)

    async def aget(self, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """获取最新检查点"""
        session_id = config.get("configurable", {}).get("thread_id", "default")
        checkpoints = self.checkpoints.get(session_id, [])
        return checkpoints[-1] if checkpoints else None

    async def alist(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """列出所有检查点"""
        session_id = config.get("configurable", {}).get("thread_id", "default")
        return self.checkpoints.get(session_id, [])

    def reset(self):
        """重置所有检查点"""
        self.checkpoints.clear()


class MockStore:
    """Mock LangGraph Store"""

    def __init__(self):
        self.data = {}

    async def aput(self, namespace: str, key: str, value: Any):
        """存储数据"""
        if namespace not in self.data:
            self.data[namespace] = {}
        self.data[namespace][key] = value

    async def aget(self, namespace: str, key: str) -> Optional[Any]:
        """获取数据"""
        return self.data.get(namespace, {}).get(key)

    async def adelete(self, namespace: str, key: str) -> bool:
        """删除数据"""
        if namespace in self.data and key in self.data[namespace]:
            del self.data[namespace][key]
            return True
        return False

    def reset(self):
        """重置所有数据"""
        self.data.clear()


def create_mock_workflow_components():
    """
    创建完整的Mock工作流组件集

    Returns:
        Dict包含state、checkpointer、store
    """
    return {"state": MockWorkflowState(), "checkpointer": MockCheckpointer(), "store": MockStore()}


# ============================================================================
# File/Upload Mock Objects
# ============================================================================


class MockUploadFile:
    """Mock FastAPI UploadFile对象"""

    def __init__(self, filename: str, content: bytes, content_type: str = "application/octet-stream"):
        self.filename = filename
        self.content = content
        self.content_type = content_type
        self._position = 0

    async def read(self, size: int = -1) -> bytes:
        """读取内容"""
        if size == -1:
            data = self.content[self._position :]
            self._position = len(self.content)
        else:
            data = self.content[self._position : self._position + size]
            self._position += len(data)
        return data

    async def seek(self, offset: int):
        """移动文件指针"""
        self._position = offset

    async def close(self):
        """关闭文件"""
        pass


def create_mock_upload_file(filename: str, content: str, content_type: str = "text/plain") -> MockUploadFile:
    """
    创建Mock上传文件

    Args:
        filename: 文件名
        content: 文件内容（字符串）
        content_type: MIME类型

    Returns:
        MockUploadFile实例
    """
    return MockUploadFile(filename, content.encode("utf-8"), content_type)


# ============================================================================
# API Mock Objects
# ============================================================================


class MockAPIResponse:
    """Mock API响应对象"""

    def __init__(self, status_code: int = 200, json_data: Optional[Dict] = None, text: str = ""):
        self.status_code = status_code
        self._json_data = json_data
        self.text = text

    def json(self) -> Dict:
        """返回JSON数据"""
        return self._json_data or {}

    def raise_for_status(self):
        """检查HTTP状态"""
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


def create_mock_api_response(status_code: int = 200, data: Optional[Dict] = None) -> MockAPIResponse:
    """
    创建Mock API响应

    Args:
        status_code: HTTP状态码
        data: 响应数据

    Returns:
        MockAPIResponse实例
    """
    return MockAPIResponse(status_code, data)


# ============================================================================
# WebSocket Mock Objects
# ============================================================================


class MockWebSocket:
    """Mock WebSocket连接"""

    def __init__(self):
        self.sent_messages = []
        self.closed = False

    async def send_text(self, data: str):
        """发送文本消息"""
        if not self.closed:
            self.sent_messages.append(data)

    async def send_json(self, data: Dict):
        """发送JSON消息"""
        if not self.closed:
            self.sent_messages.append(json.dumps(data))

    async def close(self):
        """关闭连接"""
        self.closed = True

    def reset(self):
        """重置状态"""
        self.sent_messages.clear()
        self.closed = False


def create_mock_websocket() -> MockWebSocket:
    """创建Mock WebSocket"""
    return MockWebSocket()


# ============================================================================
# Helper Functions
# ============================================================================


def create_mock_state(user_input: str = "测试需求", session_id: str = "test-session-id") -> Dict[str, Any]:
    """
    创建标准的Mock ProjectAnalysisState

    Args:
        user_input: 用户输入
        session_id: 会话ID

    Returns:
        状态字典
    """
    return {
        "user_input": user_input,
        "session_id": session_id,
        "current_phase": "initial",
        "expert_pool": [],
        "analysis_results": {},
        "report_generated": False,
        "error": None,
        "workflow_flags": {},
        "messages": [],
    }


def assert_mock_called_with_pattern(mock_obj: Mock, pattern: str):
    """
    断言Mock被调用时参数包含特定模式

    Args:
        mock_obj: Mock对象
        pattern: 要匹配的字符串模式
    """
    for call in mock_obj.call_args_list:
        args_str = str(call)
        if pattern in args_str:
            return True
    raise AssertionError(f"Pattern '{pattern}' not found in any call to {mock_obj}")


def get_mock_call_args(mock_obj: Mock, call_index: int = 0) -> tuple:
    """
    获取Mock对象指定调用的参数

    Args:
        mock_obj: Mock对象
        call_index: 调用索引（0为第一次调用）

    Returns:
        (args, kwargs) 元组
    """
    if not mock_obj.call_args_list:
        raise AssertionError(f"{mock_obj} was never called")
    if call_index >= len(mock_obj.call_args_list):
        raise AssertionError(
            f"Call index {call_index} out of range " f"(only {len(mock_obj.call_args_list)} calls made)"
        )
    call = mock_obj.call_args_list[call_index]
    return call[0], call[1]


# ============================================================================
# OpenRouter API Mock (for Image Generation)
# ============================================================================


class MockOpenRouterClient:
    """Mock OpenRouter API客户端（用于图像生成测试）"""

    def __init__(self, response_mode: str = "success"):
        """
        Args:
            response_mode: 响应模式
                - "success": 成功返回图像URL
                - "base64": 返回Base64编码图像
                - "timeout": 模拟超时
                - "rate_limit": 模拟限流
                - "token_limit": 模拟Token耗尽
                - "error": 返回错误响应
        """
        self.response_mode = response_mode
        self.call_count = 0
        self.call_history = []

    async def post(self, url: str, json: Dict[str, Any], **kwargs) -> "MockOpenRouterResponse":
        """Mock POST请求"""
        self.call_count += 1
        self.call_history.append({"url": url, "json": json, "kwargs": kwargs})

        if self.response_mode == "timeout":
            raise TimeoutError("Request timeout")
        elif self.response_mode == "rate_limit":
            return MockOpenRouterResponse(
                status=429, json_data={"error": {"message": "Rate limit exceeded", "code": "rate_limit_exceeded"}}
            )
        elif self.response_mode == "error":
            return MockOpenRouterResponse(
                status=500, json_data={"error": {"message": "Internal server error", "code": "internal_error"}}
            )
        elif self.response_mode == "token_limit":
            return MockOpenRouterResponse(
                status=200,
                json_data={
                    "choices": [{"finish_reason": "length", "message": {"content": "Truncated"}}],
                    "usage": {"prompt_tokens": 100, "completion_tokens": 4096},
                },
            )
        elif self.response_mode == "base64":
            return MockOpenRouterResponse(
                status=200,
                json_data={
                    "choices": [
                        {
                            "message": {
                                "content": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
                            }
                        }
                    ],
                    "usage": {"prompt_tokens": 50, "completion_tokens": 100},
                },
            )
        else:  # success
            return MockOpenRouterResponse(
                status=200,
                json_data={
                    "choices": [
                        {"message": {"images": ["https://example.com/image1.png", "https://example.com/image2.png"]}}
                    ],
                    "usage": {"prompt_tokens": 50, "completion_tokens": 100},
                },
            )

    def reset(self):
        """重置mock状态"""
        self.call_count = 0
        self.call_history.clear()


class MockOpenRouterResponse:
    """Mock OpenRouter响应"""

    def __init__(self, status: int, json_data: Dict[str, Any]):
        self.status = status
        self.status_code = status
        self._json_data = json_data

    async def json(self) -> Dict[str, Any]:
        """返回JSON数据"""
        return self._json_data

    def raise_for_status(self):
        """检查状态码"""
        if self.status >= 400:
            raise Exception(f"HTTP {self.status}: {self._json_data.get('error', {}).get('message', 'Unknown error')}")


# ============================================================================
# File System Mock (for File Processor)
# ============================================================================


class MockFileSystem:
    """Mock文件系统，支持异步文件操作"""

    def __init__(self):
        self.files: Dict[str, bytes] = {}
        self.write_history = []
        self.read_history = []

    async def write(self, path: str, content: bytes):
        """Mock异步文件写入"""
        self.files[path] = content
        self.write_history.append({"path": path, "size": len(content)})

    async def read(self, path: str) -> bytes:
        """Mock异步文件读取"""
        self.read_history.append({"path": path})
        if path not in self.files:
            raise FileNotFoundError(f"File not found: {path}")
        return self.files[path]

    def exists(self, path: str) -> bool:
        """检查文件是否存在"""
        return path in self.files

    def reset(self):
        """重置mock状态"""
        self.files.clear()
        self.write_history.clear()
        self.read_history.clear()


class MockAsyncFile:
    """Mock异步文件对象（用于aiofiles）"""

    def __init__(self, content: bytes = b""):
        self.content = content
        self.position = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def write(self, data: bytes):
        """写入数据"""
        self.content += data

    async def read(self) -> bytes:
        """读取所有数据"""
        return self.content

    async def seek(self, position: int):
        """移动文件指针"""
        self.position = position


def create_mock_aiofiles(content: bytes = b""):
    """
    创建mock aiofiles.open上下文管理器

    Args:
        content: 文件内容

    Returns:
        Mock对象
    """
    mock_file = MockAsyncFile(content)
    mock_open = AsyncMock(return_value=mock_file)
    return mock_open


# ============================================================================
# Tencent Cloud API Mock (for Security Module)
# ============================================================================


class MockTencentCloudAPI:
    """Mock腾讯云内容安全API"""

    def __init__(self, detection_result: str = "safe"):
        """
        Args:
            detection_result: 检测结果
                - "safe": 安全内容
                - "risky": 高风险内容
                - "review": 需要人工审核
                - "error": API错误
        """
        self.detection_result = detection_result
        self.call_count = 0
        self.call_history = []

    async def text_moderation(self, content: str) -> Dict[str, Any]:
        """Mock文本审核接口"""
        self.call_count += 1
        self.call_history.append({"content": content})

        if self.detection_result == "error":
            raise Exception("Tencent Cloud API Error")
        elif self.detection_result == "risky":
            return {"Suggestion": "Block", "Label": "Porn", "Score": 95, "Keywords": ["敏感词1", "敏感词2"]}
        elif self.detection_result == "review":
            return {"Suggestion": "Review", "Label": "Politics", "Score": 70, "Keywords": ["需审核"]}
        else:  # safe
            return {"Suggestion": "Pass", "Label": "", "Score": 0, "Keywords": []}

    def reset(self):
        """重置mock状态"""
        self.call_count = 0
        self.call_history.clear()


class MockChardet:
    """Mock chardet编码检测"""

    @staticmethod
    def detect(data: bytes) -> Dict[str, Any]:
        """检测编码"""
        # 简单判断：如果包含中文UTF-8字节序列，返回UTF-8，否则返回GBK
        try:
            data.decode("utf-8")
            return {"encoding": "utf-8", "confidence": 0.99}
        except:
            return {"encoding": "gbk", "confidence": 0.85}


# ============================================================================
# P2 Agent System Mock Objects
# ============================================================================


class MockPromptManager:
    """Mock PromptManager - 用于Agent任务描述加载"""

    def __init__(self, default_task: str = "执行专业分析"):
        self.default_task = default_task
        self.call_history = []
        self.task_templates = {
            "requirements_analyst": "分析用户需求，提取结构化信息",
            "project_director": "制定战略计划，选择专家团队",
            "expert": "执行专业领域深度分析",
        }

    def get_task_description(self, role_type: str, **kwargs) -> str:
        """获取任务描述"""
        self.call_history.append({"role_type": role_type, "kwargs": kwargs})
        return self.task_templates.get(role_type, self.default_task)

    def load_prompt(self, prompt_name: str) -> str:
        """加载提示词模板"""
        self.call_history.append({"prompt_name": prompt_name})
        return f"Mock prompt template for {prompt_name}"


class MockCapabilityDetector:
    """Mock CapabilityDetector - 用于能力边界检测"""

    def __init__(self, capability_result: str = "within_boundary"):
        """
        Args:
            capability_result: "within_boundary" | "outside_boundary" | "needs_clarification"
        """
        self.capability_result = capability_result
        self.call_history = []

    def check_capability(self, user_input: str) -> Dict[str, Any]:
        """检查用户需求是否在能力边界内"""
        self.call_history.append({"user_input": user_input})

        if self.capability_result == "outside_boundary":
            return {
                "is_within_boundary": False,
                "blocked_deliverables": ["CAD施工图", "精确工程量清单"],
                "reason": "需求超出设计能力范围",
                "suggestions": ["调整为概念设计方案", "移除精确施工要求"],
            }
        elif self.capability_result == "needs_clarification":
            return {"is_within_boundary": True, "warning": "部分需求需要用户澄清", "clarification_needed": ["项目规模", "预算范围"]}
        else:
            return {
                "is_within_boundary": True,
                "confidence": 0.95,
                "supported_deliverables": ["概念方案", "设计手册", "用户体验报告"],
            }


class MockBaseStore:
    """Mock BaseStore - 用于用户偏好持久化"""

    def __init__(self):
        self.storage = {}
        self.call_history = []

    def get(self, namespace: str, key: str) -> Optional[Any]:
        """获取存储值"""
        self.call_history.append({"action": "get", "namespace": namespace, "key": key})
        return self.storage.get(f"{namespace}:{key}")

    def put(self, namespace: str, key: str, value: Any) -> None:
        """存储值"""
        self.call_history.append({"action": "put", "namespace": namespace, "key": key, "value": value})
        self.storage[f"{namespace}:{key}"] = value

    def delete(self, namespace: str, key: str) -> None:
        """删除值"""
        self.call_history.append({"action": "delete", "namespace": namespace, "key": key})
        self.storage.pop(f"{namespace}:{key}", None)


class MockKeywordExtractor:
    """Mock KeywordExtractor - 用于问卷系统关键词提取"""

    @staticmethod
    def extract(user_input: str, structured_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        提取关键词和核心概念

        Returns:
            {
                "keywords": List[str],
                "project_type": str,
                "core_concepts": List[str],
                "domain": str
            }
        """
        # 简单规则提取
        keywords = []
        if "办公" in user_input or "office" in user_input.lower():
            keywords.extend(["办公空间", "协作", "灵活布局"])
            domain = "commercial_office"
        elif "住宅" in user_input or "家" in user_input:
            keywords.extend(["居住体验", "温馨", "功能分区"])
            domain = "residential"
        else:
            keywords.extend(["空间设计", "用户体验"])
            domain = "general"

        return {
            "keywords": keywords,
            "project_type": structured_data.get("project_type", "未知"),
            "core_concepts": keywords[:2],
            "domain": domain,
        }

    @staticmethod
    def _empty_result() -> Dict[str, Any]:
        """空结果（提取失败时使用）"""
        return {"keywords": [], "project_type": "未知", "core_concepts": [], "domain": "general"}


class MockRoleManager:
    """Mock RoleManager - 用于角色配置管理"""

    def __init__(self):
        self.available_roles = [
            {"role_id": "V2", "name": "设计总监", "category": "design_director"},
            {"role_id": "V3", "name": "叙事专家", "category": "narrative_specialist"},
            {"role_id": "V4", "name": "设计研究员", "category": "research_analyst"},
            {"role_id": "V5", "name": "场景专家", "category": "scenario_planner"},
            {"role_id": "V6", "name": "实施规划师", "category": "implementation_planner"},
        ]
        self.call_history = []

    def get_available_roles(self) -> List[Dict[str, Any]]:
        """获取可用角色列表"""
        self.call_history.append({"action": "get_available_roles"})
        return self.available_roles

    def get_role_config(self, base_type: str, rid: str) -> Dict[str, Any]:
        """获取角色配置"""
        self.call_history.append({"action": "get_role_config", "base_type": base_type, "rid": rid})
        return {
            "role_id": f"{base_type}_{rid}",
            "name": f"{base_type}角色",
            "description": f"这是{base_type}角色的配置",
            "capabilities": ["分析", "设计", "规划"],
        }

    def parse_full_role_id(self, full_role_id: str) -> tuple:
        """解析完整角色ID -> (base_type, rid)"""
        self.call_history.append({"action": "parse_full_role_id", "full_role_id": full_role_id})
        # 示例: "V3_叙事专家_3-1" -> ("V3", "3-1")
        parts = full_role_id.split("_")
        if len(parts) >= 3:
            return (parts[0], parts[2])
        return (parts[0], "1-1")
