"""
对话界面组件

提供分析完成后的自由对话功能
"""

import streamlit as st
import time
from typing import List, Dict, Any
from datetime import datetime


def render_conversation_interface():
    """
    渲染对话界面
    
    布局：
    - 顶部：报告摘要卡片
    - 中部：对话历史（聊天式）
    - 底部：输入框 + 快捷按钮
    """
    st.markdown("## 💬 智能对话助手")
    st.info("✅ 分析报告已生成！您可以继续提问或开始新的分析。")
    
    # ========== 报告摘要卡片 ==========
    with st.expander("📊 分析报告摘要", expanded=False):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            # 尝试从session_state获取报告信息
            report = st.session_state.get("final_report", {})
            sections_count = len(report.get("sections", {})) if isinstance(report, dict) else 0
            st.metric("📄 报告章节", f"{sections_count}章")
        with col2:
            st.metric("👥 分析专家", "6位")
        with col3:
            # 计算分析时长
            start_time = st.session_state.get('start_time', time.time())
            elapsed = int(time.time() - start_time)
            minutes, seconds = divmod(elapsed, 60)
            st.metric("⏱️ 分析时长", f"{minutes}分{seconds}秒")
        with col4:
            pdf_path = st.session_state.get("pdf_path")
            if pdf_path:
                try:
                    with open(pdf_path, "rb") as f:
                        st.download_button(
                            "📥 下载PDF",
                            data=f,
                            file_name=f"analysis_{datetime.now().strftime('%Y%m%d')}.pdf",
                            mime="application/pdf"
                        )
                except:
                    st.caption("PDF文件不可用")
            else:
                st.caption("PDF生成中...")
    
    st.markdown("---")
    
    # ========== 对话历史显示 ==========
    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = []
    
    # 使用聊天式UI显示历史
    if st.session_state.conversation_history:
        st.markdown("### 📝 对话记录")
        
        for i, turn in enumerate(st.session_state.conversation_history):
            # 用户问题
            with st.chat_message("user", avatar="🙋"):
                st.write(turn["question"])
            
            # AI回答
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(turn["answer"])
                
                # 引用章节标签
                if turn.get("referenced_sections"):
                    refs = ", ".join([f"`{ref}`" for ref in turn["referenced_sections"]])
                    st.caption(f"📖 引用章节：{refs}")
                
                # 时间戳
                timestamp = turn.get('timestamp', '')
                if timestamp:
                    try:
                        dt = datetime.fromisoformat(timestamp)
                        time_str = dt.strftime("%H:%M:%S")
                        st.caption(f"⏰ {time_str}")
                    except:
                        st.caption(f"⏰ {timestamp}")
    
    else:
        st.info("""
        👋 您好！我是设计知外 AI 助手。
        
        分析报告已经生成完毕，您可以：
        - 🔍 深入了解某个章节的内容
        - 💡 咨询具体的实施建议
        - 📊 要求补充数据和案例
        - ❓ 提出任何相关问题
        
        请在下方输入您的问题开始对话！
        """)
    
    st.markdown("---")
    
    # ========== 快捷问题按钮 ==========
    st.markdown("#### 💡 快捷问题")
    
    col1, col2, col3 = st.columns(3)
    
    quick_questions = [
        ("📖 核心建议", "请总结一下核心设计建议是什么？"),
        ("⚠️ 风险分析", "这个方案的主要实施风险有哪些？"),
        ("💰 成本预估", "大概需要多少预算和资源投入？"),
        ("📊 案例参考", "有没有类似的成功案例可以参考？"),
        ("🎯 优先级", "哪些是最应该优先实施的部分？"),
        ("🔧 技术选型", "推荐的技术栈是什么？为什么？")
    ]
    
    # 处理快捷问题按钮点击
    quick_question_clicked = None
    for i, (label, question) in enumerate(quick_questions[:3]):
        with [col1, col2, col3][i]:
            if st.button(label, key=f"quick_{i}", use_container_width=True):
                quick_question_clicked = question
    
    # ========== 用户输入区 ==========
    st.markdown("#### ✍️ 输入您的问题")
    
    user_question = st.text_area(
        "问题：",
        value="",
        height=100,
        placeholder="例如：能详细解释一下第3章的设计方案吗？",
        key="conversation_input"
    )
    
    # 按钮组
    col1, col2, col3, col4 = st.columns([2, 2, 2, 4])
    
    with col1:
        send_button = st.button(
            "📤 发送",
            type="primary",
            use_container_width=True
        )
    
    with col2:
        if st.button("🔄 清空历史", use_container_width=True):
            st.session_state.conversation_history = []
            st.rerun()
    
    with col3:
        if st.button("🆕 新分析", use_container_width=True):
            # 重置状态
            st.session_state.analysis_complete = False
            st.session_state.analysis_started = False
            st.session_state.session_id = None
            st.session_state.conversation_history = []
            st.session_state.user_input = ""
            st.rerun()
    
    # ========== 处理发送 ==========
    # 判断是快捷问题还是用户手动输入
    question_to_send = quick_question_clicked or (user_question if send_button else None)
    
    if question_to_send:
        with st.spinner("🤔 思考中..."):
            try:
                # 调用对话API
                response = st.session_state.api_client.ask_question(
                    session_id=st.session_state.session_id,
                    question=question_to_send
                )
                
                # 添加到历史
                st.session_state.conversation_history.append({
                    "question": question_to_send,
                    "answer": response["answer"],
                    "intent": response["intent"],
                    "referenced_sections": response.get("references", []),
                    "timestamp": datetime.now().isoformat()
                })
                
                # 显示后续建议
                if response.get("suggestions"):
                    with st.expander("💡 您还可以问：", expanded=True):
                        for suggestion in response["suggestions"][:3]:
                            st.write(f"- {suggestion}")
                
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ 对话失败：{str(e)}")
                st.exception(e)
    
    # ========== 侧边栏统计 ==========
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 📊 对话统计")
        st.metric("对话轮次", len(st.session_state.conversation_history))
        
        if st.button("👋 结束对话", type="secondary", use_container_width=True):
            try:
                st.session_state.api_client.end_conversation(st.session_state.session_id)
                st.sidebar.success("对话已结束！")
                time.sleep(1)
                # 重置状态
                st.session_state.analysis_complete = False
                st.session_state.analysis_started = False
                st.session_state.conversation_history = []
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"结束失败：{str(e)}")
