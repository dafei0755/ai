"""
前端组件模块

提供可复用的UI组件
"""

import streamlit as st
from typing import Dict, List, Any, Optional
from datetime import datetime
import os

#  导入统一配置
from intelligent_project_analyzer.settings import settings


def apply_custom_css():
    """应用自定义CSS样式"""
    st.markdown("""
    <style>
        /* 主标题样式 */
        .main-header {
            font-size: 2.8rem;
            font-weight: bold;
            background: linear-gradient(120deg, #1f77b4, #2ca02c);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-align: center;
            margin-bottom: 2rem;
            padding: 1rem 0;
        }
        
        /* 副标题样式 */
        .sub-header {
            font-size: 1.8rem;
            font-weight: bold;
            color: #2c3e50;
            margin-top: 2rem;
            margin-bottom: 1rem;
            border-bottom: 3px solid #1f77b4;
            padding-bottom: 0.5rem;
        }
        
        /* 信息框样式 */
        .info-box {
            background: linear-gradient(135deg, #e8f4f8 0%, #d4e9f7 100%);
            padding: 1.5rem;
            border-radius: 10px;
            border-left: 5px solid #1f77b4;
            margin: 1rem 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .success-box {
            background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
            padding: 1.5rem;
            border-radius: 10px;
            border-left: 5px solid #28a745;
            margin: 1rem 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .warning-box {
            background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
            padding: 1.5rem;
            border-radius: 10px;
            border-left: 5px solid #ffc107;
            margin: 1rem 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .error-box {
            background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
            padding: 1.5rem;
            border-radius: 10px;
            border-left: 5px solid #dc3545;
            margin: 1rem 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        /* 智能体卡片样式 */
        .agent-card {
            background: white;
            padding: 1.5rem;
            border-radius: 10px;
            border: 2px solid #e0e0e0;
            margin: 1rem 0;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .agent-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        }
        
        .agent-card-header {
            font-size: 1.3rem;
            font-weight: bold;
            color: #1f77b4;
            margin-bottom: 0.5rem;
        }
        
        .agent-card-status {
            display: inline-block;
            padding: 0.3rem 0.8rem;
            border-radius: 20px;
            font-size: 0.9rem;
            font-weight: bold;
            margin-top: 0.5rem;
        }
        
        .status-running {
            background-color: #fff3cd;
            color: #856404;
        }
        
        .status-complete {
            background-color: #d4edda;
            color: #155724;
        }
        
        .status-pending {
            background-color: #e8f4f8;
            color: #004085;
        }
        
        /* 进度条容器 */
        .progress-container {
            background-color: #f8f9fa;
            padding: 1.5rem;
            border-radius: 10px;
            margin: 1rem 0;
        }
        
        /* 时间轴样式 */
        .timeline-item {
            position: relative;
            padding-left: 2rem;
            padding-bottom: 1.5rem;
            border-left: 2px solid #1f77b4;
        }
        
        .timeline-item:last-child {
            border-left: none;
        }
        
        .timeline-dot {
            position: absolute;
            left: -6px;
            top: 0;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background-color: #1f77b4;
        }
        
        .timeline-content {
            background-color: white;
            padding: 1rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        /* 按钮样式增强 */
        .stButton > button {
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.3s;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }
    </style>
    """, unsafe_allow_html=True)


def render_header():
    """渲染页面头部"""
    st.markdown("""
    <div class="main-header">
         设计知外 Design Beyond
    </div>
    <div style="text-align: center; color: #666; margin-bottom: 2rem;">
        <p style="font-size: 1.1rem;">专业室内设计/空间设计智能咨询系统</p>
        <p style="font-size: 0.9rem;">基于第一性原理的多维度设计分析 | Powered by Claude 4.5 Sonnet</p>
    </div>
    """, unsafe_allow_html=True)


def render_sidebar() -> bool:
    """
    渲染侧边栏
    
    Returns:
        bool: 模式是否改变
    """
    mode_changed = False
    
    with st.sidebar:
        st.markdown("### ️ 系统配置")
        
        # 默认使用 Dynamic Mode（Fixed Mode 已移除）
        selected_mode = "dynamic"
        selected_mode_label = "Dynamic 动态模式"
        st.session_state.mode = selected_mode

        # 模式说明
        st.info("""
        **Dynamic模式特点:**
        -  智能选择3-8个最合适的角色
        -  根据需求定制分析团队
        -  适合特定领域深度分析
        -  灵活度更高

        注：Fixed模式已移除，系统现在仅支持Dynamic模式
        """)
        
        st.markdown("---")
        
        # API配置检查
        st.markdown("###  API配置")
        #  从统一配置读取
        api_key = settings.llm.api_key
        api_base = settings.llm.api_base

        if api_key:
            st.success(" API密钥已加载")
            if api_base:
                st.info(f" API Base: {api_base[:30]}...")
            else:
                st.info(" 使用 OpenAI 官方地址")
        else:
            st.error(" 未配置 API 密钥")
            st.warning("请在 .env 文件中设置 OPENAI_API_KEY")
        
        st.markdown("---")
        
        # 系统信息
        st.markdown("###  系统状态")
        
        status_color = "" if not st.session_state.get('analysis_started', False) else ""
        status_text = "就绪" if not st.session_state.get('analysis_started', False) else "分析中"
        
        st.markdown(f"""
        **运行模式:** {selected_mode_label}  
        **LLM模型:** gpt-4o-mini  
        **系统状态:** {status_color} {status_text}
        """)
        
        if st.session_state.get('thread_id'):
            st.markdown(f"**会话ID:** `{st.session_state.thread_id[:16]}...`")
        
        st.markdown("---")
        
        # 帮助信息
        with st.expander(" 使用指南"):
            st.markdown("""
            **快速开始:**
            1. 选择运行模式（Fixed/Dynamic）
            2. 输入详细的项目需求
            3. 点击"开始智能分析"
            4. 等待多智能体协作完成
            5. 查看分析结果和建议
            
            **提示:**
            - 需求描述越详细，分析越准确
            - Fixed模式适合标准项目
            - Dynamic模式适合特殊需求
            - 分析过程中可能需要确认
            """)
        
        with st.expander("ℹ️ 关于系统"):
            st.markdown("""
            **设计知外 Design Beyond v3.0**

            专业的室内设计/空间设计智能咨询系统，
            基于第一性原理的多维度设计分析方法。

            **核心特性:**
            -  专业设计分析（V2-V6专家团队）
            -  智能查询分类（深度/广度/直接）
            -  自适应报告生成
            -  三层分析协议（L1→L2→L3）
            -  核心张力判定

            **专家团队:**
            - V2 设计总监（首席空间产品官）
            - V3 人物及叙事专家（定魂之人）
            - V4 设计研究员（知识架构师）
            - V5 场景与用户生态专家（情境解码器）
            - V6 专业总工程师（现实守护者）

            **技术栈:**
            - LangGraph + LangChain
            - Claude 4.5 Sonnet
            - Streamlit
            """)
    
    return mode_changed


def render_analysis_results(events: List[Dict[str, Any]]):
    """
    渲染分析结果
    
    Args:
        events: 事件列表
    """
    st.markdown("###  分析结果")
    
    # 提取各智能体的结果
    agent_results = {}
    
    for event_data in events:
        event = event_data['event']
        for node_name, node_output in event.items():
            if isinstance(node_output, dict):
                if 'agent_results' in node_output:
                    agent_results.update(node_output['agent_results'])
    
    # 显示结果
    if agent_results:
        tabs = st.tabs([f" {agent}" for agent in agent_results.keys()])
        
        for tab, (agent_name, result) in zip(tabs, agent_results.items()):
            with tab:
                render_agent_result(agent_name, result)
    else:
        st.info("暂无分析结果")


def render_agent_result(agent_name: str, result: Dict[str, Any]):
    """
    渲染单个智能体的结果
    
    Args:
        agent_name: 智能体名称
        result: 分析结果
    """
    st.markdown(f"#### {agent_name}")
    
    # 显示置信度
    if 'confidence' in result:
        confidence = result['confidence']
        st.metric("置信度", f"{confidence:.1%}")
    
    # 显示内容
    if 'content' in result:
        st.markdown("**分析内容:**")
        st.markdown(result['content'])
    
    # 显示结构化数据
    if 'structured_data' in result:
        with st.expander(" 查看结构化数据"):
            st.json(result['structured_data'])


def render_agent_card(
    agent_name: str,
    status: str = "pending",
    description: str = "",
    result: Optional[Dict[str, Any]] = None
):
    """
    渲染智能体卡片
    
    Args:
        agent_name: 智能体名称
        status: 状态 (pending/running/complete)
        description: 描述
        result: 分析结果
    """
    status_class = f"status-{status}"
    status_text = {
        "pending": " 等待中",
        "running": " 执行中",
        "complete": " 已完成"
    }.get(status, " 未知")
    
    st.markdown(f"""
    <div class="agent-card">
        <div class="agent-card-header">{agent_name}</div>
        <p style="color: #666; margin: 0.5rem 0;">{description}</p>
        <span class="agent-card-status {status_class}">{status_text}</span>
    </div>
    """, unsafe_allow_html=True)
    
    if result and status == "complete":
        with st.expander(f"查看 {agent_name} 的分析结果"):
            st.json(result)

