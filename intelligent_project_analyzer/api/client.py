"""
API 客户端

用于前端调用后端 API
"""

import requests
from typing import Dict, Any, Optional
from datetime import datetime


class AnalysisAPIClient:
    """分析 API 客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        初始化客户端
        
        Args:
            base_url: API 服务器地址
        """
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
    
    def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        
        Returns:
            健康状态
        """
        response = self.session.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    def start_analysis(
        self,
        user_input: str,
        mode: str = "fixed"
    ) -> Dict[str, Any]:
        """
        开始分析
        
        Args:
            user_input: 用户输入的需求
            mode: 运行模式 (fixed 或 dynamic)
            
        Returns:
            会话信息
        """
        response = self.session.post(
            f"{self.base_url}/api/analysis/start",
            json={
                "user_input": user_input,
                "mode": mode
            }
        )
        response.raise_for_status()
        return response.json()
    
    def get_status(self, session_id: str) -> Dict[str, Any]:
        """
        获取分析状态
        
        Args:
            session_id: 会话 ID
            
        Returns:
            状态信息
        """
        response = self.session.get(
            f"{self.base_url}/api/analysis/status/{session_id}"
        )
        response.raise_for_status()
        return response.json()
    
    def resume_analysis(
        self,
        session_id: str,
        resume_value: Any
    ) -> Dict[str, Any]:
        """
        恢复分析
        
        Args:
            session_id: 会话 ID
            resume_value: 恢复值（用户输入）
            
        Returns:
            恢复结果
        """
        response = self.session.post(
            f"{self.base_url}/api/analysis/resume",
            json={
                "session_id": session_id,
                "resume_value": resume_value
            }
        )
        response.raise_for_status()
        return response.json()
    
    def get_result(self, session_id: str) -> Dict[str, Any]:
        """
        获取分析结果
        
        Args:
            session_id: 会话 ID
            
        Returns:
            分析结果
        """
        response = self.session.get(
            f"{self.base_url}/api/analysis/result/{session_id}"
        )
        response.raise_for_status()
        return response.json()
    
    def list_sessions(self) -> Dict[str, Any]:
        """
        列出所有会话
        
        Returns:
            会话列表
        """
        response = self.session.get(f"{self.base_url}/api/sessions")
        response.raise_for_status()
        return response.json()
    
    # 🆕 对话相关方法
    
    def ask_question(
        self,
        session_id: str,
        question: str,
        context_hint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        对话模式提问
        
        Args:
            session_id: 会话ID
            question: 用户问题
            context_hint: 可选上下文提示
        
        Returns:
            对话响应
        """
        response = self.session.post(
            f"{self.base_url}/api/conversation/ask",
            json={
                "session_id": session_id,
                "question": question,
                "context_hint": context_hint
            }
        )
        response.raise_for_status()
        return response.json()
    
    def get_conversation_history(self, session_id: str) -> Dict[str, Any]:
        """
        获取对话历史
        
        Args:
            session_id: 会话ID
        
        Returns:
            对话历史
        """
        response = self.session.get(
            f"{self.base_url}/api/conversation/history/{session_id}"
        )
        response.raise_for_status()
        return response.json()
    
    def end_conversation(self, session_id: str) -> Dict[str, Any]:
        """
        结束对话
        
        Args:
            session_id: 会话ID
        
        Returns:
            结束确认
        """
        response = self.session.post(
            f"{self.base_url}/api/conversation/end",
            params={"session_id": session_id}
        )
        response.raise_for_status()
        return response.json()

