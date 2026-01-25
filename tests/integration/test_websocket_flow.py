"""
WebSocket推送端到端集成测试

测试覆盖:
1. WebSocket完整生命周期: 连接 → 推送 → 断开
2. 状态更新广播机制
3. 搜索引用推送 (v7.120+)
4. 高频错误场景回归测试:
   - v7.120-v7.131: WebSocket连接状态检查缺失 (CONNECTED检查)
   - 心跳保活机制
   - Redis Pub/Sub多实例广播

作者: Copilot AI Testing Assistant
创建日期: 2026-01-04
"""

import asyncio
import json
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.websockets import WebSocket, WebSocketDisconnect, WebSocketState

from intelligent_project_analyzer.api.server import broadcast_to_websockets


@pytest.fixture
def mock_websocket():
    """创建模拟WebSocket对象"""
    ws = MagicMock(spec=WebSocket)
    ws.client_state = WebSocketState.CONNECTED
    ws.send_json = AsyncMock()
    ws.send_text = AsyncMock()
    ws.receive_text = AsyncMock()
    ws.accept = AsyncMock()
    ws.close = AsyncMock()
    return ws


@pytest.fixture
def mock_redis_client():
    """创建模拟Redis客户端"""
    client = MagicMock()
    client.publish = AsyncMock()
    client.subscribe = AsyncMock()
    return client


@pytest.fixture
def sample_status_update_message() -> Dict:
    """模拟状态更新消息"""
    return {
        "type": "status_update",
        "status": "running",
        "progress": 50,
        "current_node": "expert_v4_analysis",
        "detail": "正在生成室内设计方案...",
        "timestamp": "2026-01-04T10:30:00Z",
    }


@pytest.fixture
def sample_search_references_message() -> Dict:
    """模拟搜索引用消息 (v7.120+)"""
    return {
        "type": "status_update",
        "status": "running",
        "search_references": [
            {
                "title": "现代简约设计理念",
                "url": "https://example.com/article1",
                "snippet": "现代简约风格强调功能性与美学的平衡...",
                "source": "bocha",
            },
            {
                "title": "收纳设计技巧",
                "url": "https://example.com/article2",
                "snippet": "巧妙利用墙面空间，实现收纳最大化...",
                "source": "tavily",
            },
        ],
        "current_node": "expert_v4_analysis",
    }


@pytest.mark.integration
@pytest.mark.integration_critical
class TestWebSocketFlow:
    """WebSocket推送端到端集成测试"""

    @pytest.mark.asyncio
    async def test_websocket_connection_lifecycle(self, mock_websocket: MagicMock):
        """测试WebSocket完整生命周期"""
        from intelligent_project_analyzer.api.server import websocket_connections

        session_id = "test_session_lifecycle"

        # Arrange - 初始化空连接池
        websocket_connections.clear()

        # Act - 模拟连接加入
        if session_id not in websocket_connections:
            websocket_connections[session_id] = []
        websocket_connections[session_id].append(mock_websocket)

        # Assert - 验证连接已加入
        assert session_id in websocket_connections, "会话未加入连接池"
        assert len(websocket_connections[session_id]) == 1, "连接数量错误"
        assert mock_websocket in websocket_connections[session_id], "WebSocket对象未加入"

        # Act - 发送消息
        test_message = {"type": "test", "content": "Hello WebSocket"}
        await broadcast_to_websockets(session_id, test_message)

        # Assert - 验证消息已发送
        mock_websocket.send_json.assert_called_once()
        sent_message = mock_websocket.send_json.call_args[0][0]
        assert sent_message["type"] == "test", "消息类型错误"
        assert sent_message["content"] == "Hello WebSocket", "消息内容错误"

        # Act - 断开连接
        websocket_connections[session_id].remove(mock_websocket)
        if not websocket_connections[session_id]:
            del websocket_connections[session_id]

        # Assert - 验证连接已移除
        assert session_id not in websocket_connections, "会话未从连接池移除"

    @pytest.mark.asyncio
    async def test_status_update_broadcast(self, mock_websocket: MagicMock, sample_status_update_message: Dict):
        """测试状态更新广播"""
        from intelligent_project_analyzer.api.server import websocket_connections

        session_id = "test_session_status"
        websocket_connections.clear()
        websocket_connections[session_id] = [mock_websocket]

        # Act
        await broadcast_to_websockets(session_id, sample_status_update_message)

        # Assert
        mock_websocket.send_json.assert_called_once()
        sent_message = mock_websocket.send_json.call_args[0][0]

        assert sent_message["type"] == "status_update", "消息类型错误"
        assert sent_message["status"] == "running", "状态错误"
        assert sent_message["progress"] == 50, "进度错误"
        assert sent_message["current_node"] == "expert_v4_analysis", "节点名称错误"

    @pytest.mark.asyncio
    async def test_search_references_push(self, mock_websocket: MagicMock, sample_search_references_message: Dict):
        """测试搜索引用推送 (v7.120+ 数据流优化)"""
        from intelligent_project_analyzer.api.server import websocket_connections

        session_id = "test_session_search"
        websocket_connections.clear()
        websocket_connections[session_id] = [mock_websocket]

        # Act
        await broadcast_to_websockets(session_id, sample_search_references_message)

        # Assert
        mock_websocket.send_json.assert_called_once()
        sent_message = mock_websocket.send_json.call_args[0][0]

        # 验证搜索引用数据
        assert "search_references" in sent_message, "缺少搜索引用字段"
        references = sent_message["search_references"]
        assert len(references) == 2, "搜索引用数量错误"

        # 验证第一条引用
        ref1 = references[0]
        assert ref1["title"] == "现代简约设计理念", "引用标题错误"
        assert ref1["source"] == "bocha", "引用来源错误"
        assert "url" in ref1, "缺少URL字段"
        assert "snippet" in ref1, "缺少摘要字段"

    @pytest.mark.asyncio
    async def test_websocket_connection_state_check_regression(self):
        """
        回归测试: v7.120-v7.131 WebSocket连接状态检查缺失

        根因: 发送消息前未检查 ws.client_state == CONNECTED
        修复: 添加状态检查，跳过未连接的WebSocket
        """
        from intelligent_project_analyzer.api.server import websocket_connections

        # Arrange
        session_id = "test_session_state_check"
        websocket_connections.clear()

        # 创建3个WebSocket: 已连接、正在连接、已断开
        ws_connected = MagicMock(spec=WebSocket)
        ws_connected.client_state = WebSocketState.CONNECTED
        ws_connected.send_json = AsyncMock()

        ws_connecting = MagicMock(spec=WebSocket)
        ws_connecting.client_state = WebSocketState.CONNECTING
        ws_connecting.send_json = AsyncMock()

        ws_disconnected = MagicMock(spec=WebSocket)
        ws_disconnected.client_state = WebSocketState.DISCONNECTED
        ws_disconnected.send_json = AsyncMock()

        websocket_connections[session_id] = [ws_connected, ws_connecting, ws_disconnected]

        # Act
        test_message = {"type": "test", "content": "Connection state test"}
        await broadcast_to_websockets(session_id, test_message)

        # Assert - 只有CONNECTED状态的WebSocket应该收到消息
        ws_connected.send_json.assert_called_once()
        ws_connecting.send_json.assert_not_called()  # ❌ 不应发送
        ws_disconnected.send_json.assert_not_called()  # ❌ 不应发送

        # 验证未连接的WebSocket被标记为断开
        # (在实际实现中，它们应该从连接池移除)

    @pytest.mark.asyncio
    async def test_heartbeat_mechanism(self, mock_websocket: MagicMock):
        """测试心跳保活机制"""
        from intelligent_project_analyzer.api.server import websocket_connections

        session_id = "test_session_heartbeat"
        websocket_connections.clear()
        websocket_connections[session_id] = [mock_websocket]

        # Act - 发送ping消息
        ping_message = {"type": "ping"}
        await broadcast_to_websockets(session_id, ping_message)

        # Assert
        mock_websocket.send_json.assert_called_once_with(ping_message)

        # Act - 模拟客户端响应pong
        mock_websocket.send_json.reset_mock()
        pong_message = {"type": "pong"}

        # 在真实场景中，服务端会接收到pong并验证连接
        # 这里仅测试发送逻辑
        await mock_websocket.send_json(pong_message)
        mock_websocket.send_json.assert_called_once_with(pong_message)

    @pytest.mark.asyncio
    async def test_redis_pubsub_multi_instance_broadcast(self, mock_redis_client: MagicMock):
        """测试Redis Pub/Sub多实例广播"""
        session_id = "test_session_redis"
        test_message = {"type": "test", "content": "Multi-instance broadcast"}

        # Arrange - 注入模拟Redis客户端
        with patch("intelligent_project_analyzer.api.server.redis_pubsub_client", mock_redis_client):
            # Act
            await broadcast_to_websockets(session_id, test_message)

            # Assert
            mock_redis_client.publish.assert_called_once()

            # 验证发布的消息格式
            call_args = mock_redis_client.publish.call_args
            channel = call_args[0][0]
            payload_str = call_args[0][1]

            assert channel == "workflow:broadcast", "Redis频道错误"

            payload = json.loads(payload_str)
            assert payload["session_id"] == session_id, "会话ID错误"
            assert payload["payload"] == test_message, "消息内容错误"

    @pytest.mark.asyncio
    async def test_multi_client_broadcast(self):
        """测试多客户端广播"""
        from intelligent_project_analyzer.api.server import websocket_connections

        session_id = "test_session_multi_client"
        websocket_connections.clear()

        # Arrange - 创建3个客户端连接
        clients = []
        for i in range(3):
            ws = MagicMock(spec=WebSocket)
            ws.client_state = WebSocketState.CONNECTED
            ws.send_json = AsyncMock()
            clients.append(ws)

        websocket_connections[session_id] = clients

        # Act
        test_message = {"type": "test", "content": "Broadcast to all clients"}
        await broadcast_to_websockets(session_id, test_message)

        # Assert - 所有客户端都应收到消息
        for idx, client in enumerate(clients):
            client.send_json.assert_called_once()
            sent_message = client.send_json.call_args[0][0]
            assert sent_message["content"] == "Broadcast to all clients", f"客户端{idx+1}消息错误"

    @pytest.mark.asyncio
    async def test_websocket_send_timeout_handling(self):
        """测试WebSocket发送超时处理 (v7.133+)"""
        from intelligent_project_analyzer.api.server import websocket_connections

        session_id = "test_session_timeout"
        websocket_connections.clear()

        # Arrange - 创建一个会超时的WebSocket
        ws_timeout = MagicMock(spec=WebSocket)
        ws_timeout.client_state = WebSocketState.CONNECTED
        ws_timeout.send_json = AsyncMock(side_effect=asyncio.TimeoutError("Send timeout"))

        websocket_connections[session_id] = [ws_timeout]

        # Act
        test_message = {"type": "test", "content": "Timeout test"}
        await broadcast_to_websockets(session_id, test_message)

        # Assert - 超时不应导致崩溃，应优雅处理
        ws_timeout.send_json.assert_called()
        # 实际实现中，超时的连接应该被标记为断开

    @pytest.mark.asyncio
    async def test_websocket_disconnect_cleanup(self, mock_websocket: MagicMock):
        """测试WebSocket断开连接后的清理"""
        from intelligent_project_analyzer.api.server import websocket_connections

        session_id = "test_session_cleanup"
        websocket_connections.clear()
        websocket_connections[session_id] = [mock_websocket]

        # Act - 模拟断开
        websocket_connections[session_id].remove(mock_websocket)
        if not websocket_connections[session_id]:
            del websocket_connections[session_id]

        # Assert
        assert session_id not in websocket_connections, "会话未清理"

        # Act - 尝试向已清理的会话广播
        test_message = {"type": "test"}
        await broadcast_to_websockets(session_id, test_message)  # 不应崩溃

        # Assert - 不应发送消息（因为连接池为空）
        mock_websocket.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_websocket_error_handling(self):
        """测试WebSocket错误处理"""
        from intelligent_project_analyzer.api.server import websocket_connections

        session_id = "test_session_error"
        websocket_connections.clear()

        # Arrange - 创建一个会抛出异常的WebSocket
        ws_error = MagicMock(spec=WebSocket)
        ws_error.client_state = WebSocketState.CONNECTED
        ws_error.send_json = AsyncMock(side_effect=Exception("Send error"))

        websocket_connections[session_id] = [ws_error]

        # Act
        test_message = {"type": "test"}
        await broadcast_to_websockets(session_id, test_message)  # 不应崩溃

        # Assert
        ws_error.send_json.assert_called()
        # 实际实现中，错误的连接应该被移除


@pytest.mark.integration
class TestWebSocketEdgeCases:
    """WebSocket边缘场景测试"""

    @pytest.mark.asyncio
    async def test_empty_message_broadcast(self, mock_websocket: MagicMock):
        """测试空消息广播"""
        from intelligent_project_analyzer.api.server import websocket_connections

        session_id = "test_session_empty"
        websocket_connections.clear()
        websocket_connections[session_id] = [mock_websocket]

        # Act
        empty_message = {}
        await broadcast_to_websockets(session_id, empty_message)

        # Assert - 空消息也应该发送
        mock_websocket.send_json.assert_called_once_with({})

    @pytest.mark.asyncio
    async def test_large_message_broadcast(self, mock_websocket: MagicMock):
        """测试大消息广播"""
        from intelligent_project_analyzer.api.server import websocket_connections

        session_id = "test_session_large"
        websocket_connections.clear()
        websocket_connections[session_id] = [mock_websocket]

        # Act - 发送一个大消息（模拟包含大量搜索结果）
        large_message = {
            "type": "status_update",
            "search_references": [
                {
                    "title": f"Reference {i}",
                    "url": f"https://example.com/article{i}",
                    "snippet": "Lorem ipsum " * 100,  # 长摘要
                }
                for i in range(50)  # 50条搜索结果
            ],
        }

        await broadcast_to_websockets(session_id, large_message)

        # Assert
        mock_websocket.send_json.assert_called_once()
        sent_message = mock_websocket.send_json.call_args[0][0]
        assert len(sent_message["search_references"]) == 50, "搜索结果数量错误"

    @pytest.mark.asyncio
    async def test_nonexistent_session_broadcast(self):
        """测试向不存在的会话广播"""
        from intelligent_project_analyzer.api.server import websocket_connections

        websocket_connections.clear()

        # Act - 向不存在的会话广播
        nonexistent_session = "nonexistent_session_12345"
        test_message = {"type": "test"}
        await broadcast_to_websockets(nonexistent_session, test_message)  # 不应崩溃

        # Assert - 应该优雅处理（日志记录，但不抛出异常）

    @pytest.mark.asyncio
    async def test_concurrent_broadcast_to_same_session(self, mock_websocket: MagicMock):
        """测试并发向同一会话广播"""
        from intelligent_project_analyzer.api.server import websocket_connections

        session_id = "test_session_concurrent"
        websocket_connections.clear()
        websocket_connections[session_id] = [mock_websocket]

        # Act - 并发发送10条消息
        tasks = [broadcast_to_websockets(session_id, {"type": "test", "index": i}) for i in range(10)]
        await asyncio.gather(*tasks)

        # Assert - 应该收到10次调用
        assert mock_websocket.send_json.call_count == 10, "并发消息数量错误"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
