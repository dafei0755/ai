"""
智能项目分析系统 - Streamlit前端应用

完整的多智能体协作项目分析平台前端界面

启动命令:
    streamlit run intelligent_project_analyzer/frontend/app.py
"""

import json
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st

# ✅ 不再需要load_dotenv() - Pydantic Settings会自动处理

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import requests

from intelligent_project_analyzer.api.client import AnalysisAPIClient
from intelligent_project_analyzer.settings import settings

# 页面配置
st.set_page_config(page_title="设计知外 Design Beyond", page_icon="🎨", layout="wide", initial_sidebar_state="expanded")

# 导入自定义样式和组件
try:
    from frontend_components import (
        apply_custom_css,
        render_agent_card,
        render_analysis_results,
        render_header,
        render_progress_tracker,
        render_sidebar,
    )
except ImportError:
    # 如果从当前目录导入失败，尝试从完整路径导入
    from intelligent_project_analyzer.frontend.frontend_components import (
        apply_custom_css,
        render_agent_card,
        render_analysis_results,
        render_header,
        render_sidebar,
    )


def initialize_session_state():
    """初始化session state"""
    # 基本状态
    if "session_id" not in st.session_state:
        st.session_state.session_id = None
    if "analysis_started" not in st.session_state:
        st.session_state.analysis_started = False
    if "analysis_complete" not in st.session_state:
        st.session_state.analysis_complete = False
    if "user_input" not in st.session_state:
        st.session_state.user_input = ""
    if "mode" not in st.session_state:
        st.session_state.mode = "fixed"
    if "interrupt_data" not in st.session_state:
        st.session_state.interrupt_data = None
    if "waiting_for_user" not in st.session_state:
        st.session_state.waiting_for_user = False
    if "current_status" not in st.session_state:
        st.session_state.current_status = None
    if "just_submitted" not in st.session_state:
        st.session_state.just_submitted = False

    # API 客户端 - 每次都重新创建以确保可用
    # ✅ 使用统一配置
    api_base_url = settings.api_base_url
    st.session_state.api_client = AnalysisAPIClient(api_base_url)


def run_workflow_with_api():
    """使用 API 执行工作流"""
    if not st.session_state.user_input:
        return

    try:
        # 检查后端连接
        try:
            health = st.session_state.api_client.health_check()
            if health.get("status") != "healthy":
                st.error("❌ 后端服务器未就绪，请先启动后端服务器")
                st.info("💡 运行命令: `python intelligent_project_analyzer/api/server.py`")
                st.session_state.analysis_started = False
                return
        except requests.exceptions.ConnectionError as ce:
            st.error("❌ 无法连接到后端服务器，请确保后端正在运行")
            st.info("💡 运行命令: `python intelligent_project_analyzer/api/server.py`")
            st.code(f"连接错误: {ce}")
            st.session_state.analysis_started = False
            return
        except requests.exceptions.HTTPError as he:
            st.error(f"❌ 后端服务器返回错误: {he}")
            st.info("💡 请检查后端服务器日志")
            st.code(f"HTTP 错误: {he}")
            st.session_state.analysis_started = False
            return

        # 发起分析请求
        response = st.session_state.api_client.start_analysis(
            user_input=st.session_state.user_input, mode=st.session_state.mode
        )

        st.session_state.session_id = response["session_id"]
        st.session_state.thread_id = response["session_id"]

        st.success(f"✅ 分析已启动，会话ID: {response['session_id']}")

    except Exception as e:
        st.error(f"❌ 启动分析失败: {e}")
        import traceback

        st.code(traceback.format_exc())
        st.session_state.analysis_started = False


def poll_analysis_status():
    """轮询分析状态"""
    if not st.session_state.session_id:
        return

    try:
        # 获取状态
        status = st.session_state.api_client.get_status(st.session_state.session_id)

        # 调试信息
        print(f"[DEBUG] poll_analysis_status - status type: {type(status)}")
        print(f"[DEBUG] poll_analysis_status - status content: {status}")

        st.session_state.current_status = status["status"]

        # 检查状态
        if status["status"] == "waiting_for_input":
            # 需要用户输入
            interrupt_data = status.get("interrupt_data", {})
            print(f"[DEBUG] interrupt_data type: {type(interrupt_data)}")
            print(f"[DEBUG] interrupt_data content: {interrupt_data}")

            st.session_state.interrupt_data = interrupt_data
            st.session_state.waiting_for_user = True
            # 不需要继续轮询，等待用户确认
            return

        elif status["status"] == "completed":
            # 分析完成
            st.session_state.analysis_complete = True
            st.session_state.analysis_started = False  # 🔧 停止分析状态
            st.rerun()  # 🔧 修复: 刷新界面以显示结果

        elif status["status"] == "failed":
            # 分析失败
            st.error(f"❌ 分析失败: {status.get('error', '未知错误')}")

            # 显示详细的traceback用于调试
            if status.get("traceback"):
                with st.expander("🔍 查看详细错误信息（调试用）", expanded=True):
                    st.code(status["traceback"], language="python")

            st.session_state.analysis_started = False

        elif status["status"] in ["initializing", "running"]:
            # 继续轮询（延迟后刷新，避免频繁请求）
            time.sleep(1)  # 减少到1秒，提升响应速度
            st.rerun()
        else:
            # 未知状态，显示警告并停止
            st.warning(f"⚠️ 未知状态: {status['status']}")
            st.session_state.analysis_started = False

    except Exception as e:
        st.error(f"❌ 获取状态失败: {e}")
        import traceback

        st.code(traceback.format_exc())


def main():
    """主函数"""
    initialize_session_state()

    # 应用自定义CSS
    apply_custom_css()

    # 渲染头部
    render_header()

    # 渲染侧边栏
    mode_changed = render_sidebar()

    # 如果模式改变，重置状态
    if mode_changed:
        st.session_state.analysis_started = False
        st.session_state.analysis_complete = False
        st.session_state.session_id = None

    # 主内容区
    if st.session_state.analysis_complete:
        # 🆕 分析完成 → 进入对话模式
        from conversation_ui import render_conversation_interface

        render_conversation_interface()
    elif st.session_state.waiting_for_user:
        # 人机交互界面
        render_interaction_interface()
    elif st.session_state.analysis_started:
        # 分析进行中界面（动态进度）
        render_analysis_interface()
    else:
        # 需求输入界面
        render_input_interface()


def render_input_interface():
    """渲染需求输入界面"""
    st.markdown("## 📝 项目需求输入")

    # 示例需求
    with st.expander("💡 查看示例需求"):
        st.markdown(
            """
        **示例1: 深圳南山独立女性住宅设计**
        ```
        项目需求: 深圳南山，38岁独立女性，英国海归，不婚主义，200平米大平层，
        对Audrey Hepburn赫本情有独钟，基于此给出室内设计建议。
        ```

        **示例2: 农耕文化与城市化的室内设计影响**
        ```
        项目需求: 农耕文化与城市化进程对于室内设计概念的影响
        ```

        **示例3: 铜锣湾广场商业综合体设计**
        ```
        项目需求: 给出室内设计概念思路
        项目: 铜锣湾广场
        地点: 南充嘉陵区
        面积: 50000平米，两层商业街区
        项目定位: 综合商业，餐饮，购物，娱乐
        面临的对手: 300米以内的王府井商场
        ```

        **示例4: 中餐包房命名设计**
        ```
        项目需求: 中餐包房，8间房，以苏东坡的诗词命名，4个字，
        传递生活态度和价值观，要求不落俗套
        ```

        **示例5: 深圳蛇口菜市场更新改造**
        ```
        项目需求: 深圳蛇口，20000平米，菜市场更新，对标苏州黄桥菜市场，
        希望融入蛇口渔村传统文化。给出室内改造框架。
        兼顾蛇口老居民街坊，香港访客，蛇口特色外籍客群，和社区居民。
        希望能成为深圳城市更新的标杆。
        ```
        """
        )

    # 需求输入
    user_input = st.text_area(
        "请详细描述您的设计项目需求",
        height=250,
        placeholder="请输入设计项目需求，包括：\n- 项目类型（住宅/商业/办公等）\n- 空间面积和位置\n- 目标用户画像\n- 核心设计诉求\n- 预算和时间要求\n- 特殊需求或限制条件...",
        help="详细的需求描述将帮助系统提供更专业、更精准的设计分析",
        key="input_text",
    )

    # 开始分析按钮
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🎨 开始专业设计分析", type="primary", use_container_width=True):
            if not user_input.strip():
                st.warning("⚠️ 请先输入项目需求")
            else:
                # 保存用户输入
                st.session_state.user_input = user_input
                st.session_state.analysis_started = True

                # 使用 API 启动分析
                with st.spinner("正在启动分析..."):
                    run_workflow_with_api()

                # 如果启动成功，标记为刚提交（避免立即轮询）
                if st.session_state.session_id:
                    st.session_state.just_submitted = True
                    st.rerun()


def render_interaction_interface():
    """渲染人机交互界面"""
    st.markdown("## 💬 需要您的确认")

    if st.session_state.interrupt_data:
        interrupt_data = st.session_state.interrupt_data
        interaction_type = interrupt_data.get("interaction_type")

        # 根据交互类型渲染不同界面
        # 🆕 v7.151: requirements_confirmation 已合并到 questionnaire_summary
        if interaction_type == "calibration_questionnaire":
            render_questionnaire_form(interrupt_data)
        elif interaction_type == "role_and_task_unified_review":
            render_role_task_review(interrupt_data)
        else:
            # 兜底：显示JSON + 确认/修改按钮
            st.info("系统需要您的确认才能继续")
            st.json(interrupt_data)

            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ 确认", type="primary", use_container_width=True):
                    try:
                        st.session_state.api_client.resume_analysis(st.session_state.session_id, "approve")
                        st.session_state.waiting_for_user = False
                        st.session_state.interrupt_data = None
                        st.success("✅ 已确认，继续分析...")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 恢复分析失败: {e}")

            with col2:
                if st.button("❌ 修改", use_container_width=True):
                    try:
                        st.session_state.api_client.resume_analysis(st.session_state.session_id, "revise")
                        st.session_state.waiting_for_user = False
                        st.session_state.interrupt_data = None
                        st.info("🔄 返回需求分析...")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 恢复分析失败: {e}")


# 🆕 v7.151: render_requirements_confirmation 已移除
# 需求确认功能已合并到 questionnaire_summary（需求洞察）节点


def render_questionnaire_form(interrupt_data):
    """渲染战略校准问卷表单（真实表单）"""
    questionnaire = interrupt_data.get("questionnaire", {})
    introduction = questionnaire.get("introduction", "")
    questions = questionnaire.get("questions", [])

    if not questions:
        st.warning("⚠️ 未生成战略校准问卷")
        if st.button("⏭️ 跳过问卷"):
            try:
                st.session_state.api_client.resume_analysis(st.session_state.session_id, "skip")
                st.session_state.waiting_for_user = False
                st.session_state.interrupt_data = None
                st.rerun()
            except Exception as e:
                st.error(f"❌ 操作失败: {e}")
        return

    st.markdown("### 📋 战略校准问卷")
    st.info(introduction)

    # 初始化答案存储
    if "questionnaire_answers" not in st.session_state:
        st.session_state.questionnaire_answers = {}

    # 渲染每个问题
    for i, q in enumerate(questions, 1):
        question_text = q.get("question", "")
        context = q.get("context", "")
        question_type = q.get("type", "open_ended")
        options = q.get("options", [])

        st.markdown(f"#### Q{i}. {question_text}")
        if context:
            st.caption(context)

        # 根据题型渲染不同组件
        if question_type == "single_choice":
            answer = st.radio(label="请选择：", options=options, key=f"q{i}", label_visibility="collapsed")
            st.session_state.questionnaire_answers[f"q{i}"] = answer

        elif question_type == "multiple_choice":
            answer = st.multiselect(label="请选择（可多选）：", options=options, key=f"q{i}", label_visibility="collapsed")
            st.session_state.questionnaire_answers[f"q{i}"] = answer

        elif question_type == "open_ended":
            answer = st.text_area(label="请输入：", height=100, key=f"q{i}", label_visibility="collapsed")
            st.session_state.questionnaire_answers[f"q{i}"] = answer

        st.markdown("---")

    # 提交按钮
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ 提交问卷答案", type="primary", use_container_width=True):
            # 验证必填项
            unanswered = []
            for i, q in enumerate(questions, 1):
                if q.get("type") in ["single_choice", "open_ended"]:
                    answer = st.session_state.questionnaire_answers.get(f"q{i}")
                    if not answer:
                        unanswered.append(i)

            if unanswered:
                st.error(f"⚠️ 请回答问题: {', '.join(map(str, unanswered))}")
            else:
                try:
                    response = requests.post(
                        f"{st.session_state.api_client.base_url}/api/analysis/resume",
                        json={
                            "session_id": st.session_state.session_id,
                            "resume_value": {"intent": "submit", "answers": st.session_state.questionnaire_answers},
                        },
                    )
                    response.raise_for_status()

                    st.session_state.waiting_for_user = False
                    st.session_state.interrupt_data = None
                    st.session_state.questionnaire_answers = {}
                    st.success("✅ 问卷已提交，继续分析...")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 提交失败: {e}")

    with col2:
        if st.button("⏭️ 跳过问卷", use_container_width=True):
            try:
                response = requests.post(
                    f"{st.session_state.api_client.base_url}/api/analysis/resume",
                    json={"session_id": st.session_state.session_id, "resume_value": {"intent": "skip"}},
                )
                response.raise_for_status()
                st.session_state.waiting_for_user = False
                st.session_state.interrupt_data = None
                st.session_state.questionnaire_answers = {}
                st.info("⏭️ 已跳过问卷...")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"❌ 操作失败: {e}")


def render_analysis_interface():
    """渲染分析进度界面（增强版：阶段展示 + 详细进度）"""
    st.markdown("## 🔄 智能分析进行中")

    # 显示用户输入的需求摘要
    with st.expander("📝 查看需求摘要", expanded=False):
        st.markdown(st.session_state.user_input)

    # 获取当前状态
    if st.session_state.session_id:
        try:
            status = st.session_state.api_client.get_status(st.session_state.session_id)
            current_stage = status.get("current_stage", "初始化中")
            detail = status.get("detail", "")

            # 更新 session_state
            st.session_state.current_status = status["status"]

        except Exception as e:
            current_stage = st.session_state.current_status or "初始化中"
            detail = ""

    else:
        current_stage = "初始化中"
        detail = ""

    # ========== 阶段展示区域 ==========
    st.markdown("### 📊 分析进度")

    # 定义所有阶段（优化关键词匹配）
    stages = [
        {"name": "需求分析", "keywords": ["requirements", "analyst", "需求"], "icon": "📋"},
        {"name": "战略校准", "keywords": ["calibration", "questionnaire", "校准", "问卷"], "icon": "🎯"},
        {"name": "角色选择", "keywords": ["director", "strategic", "role", "总监", "选角"], "icon": "👥"},
        {"name": "批次执行", "keywords": ["batch", "executor", "批次", "执行"], "icon": "⚙️"},
        {"name": "多视角审核", "keywords": ["review", "审核"], "icon": "🔍"},
        {"name": "报告生成", "keywords": ["result", "aggregat", "report", "报告", "pdf"], "icon": "📄"},
    ]

    # 判断当前阶段（使用关键词匹配）
    current_stage_lower = current_stage.lower() if current_stage else ""
    current_stage_index = 0

    for idx, stage in enumerate(stages):
        if any(keyword in current_stage_lower for keyword in stage["keywords"]):
            current_stage_index = idx
            break

    # 渲染阶段列表
    for idx, stage in enumerate(stages):
        stage_name = stage["name"]
        stage_icon = stage["icon"]

        # 判断阶段状态
        if idx == current_stage_index:
            # 当前阶段
            st.info(f"🔄 **{stage_icon} {stage_name}** - 进行中...")
            if detail:
                st.caption(f"    💬 {detail}")
        elif idx < current_stage_index:
            # 已完成阶段
            st.success(f"✅ {stage_icon} {stage_name}")
        else:
            # 待执行阶段
            st.text(f"⏳ {stage_icon} {stage_name}")

    st.markdown("---")

    # ========== 分析状态提示 ==========
    st.info("⏳ 智能分析进行中，请耐心等待...")

    # ========== 详细状态信息 ==========
    col1, col2 = st.columns(2)
    with col1:
        st.metric("当前阶段", current_stage)
    with col2:
        elapsed_time = int((time.time() - st.session_state.get("start_time", time.time())))
        minutes, seconds = divmod(elapsed_time, 60)
        st.metric("已用时", f"{minutes}分{seconds}秒")

    # ========== 分析小贴士 ==========
    st.info("💡 系统正在进行多维度分析，包括需求理解、战略规划、专家协作等环节")

    # ========== 会话信息（折叠） ==========
    with st.expander("🔍 会话详情", expanded=False):
        st.code(f"会话ID: {st.session_state.session_id}")
        st.code(f"状态: {st.session_state.current_status}")
        st.code(f"当前阶段: {current_stage}")

    # ========== 轮询状态 ==========
    # 保存开始时间
    if "start_time" not in st.session_state:
        st.session_state.start_time = time.time()

    # 🔥 如果刚提交，延迟轮询，让用户看到进度界面
    if st.session_state.get("just_submitted"):
        st.session_state.just_submitted = False
        st.info("⏳ 正在连接分析引擎...")
        time.sleep(2)  # 给后端2秒启动时间

    # 开始轮询状态
    poll_analysis_status()

    # 如果检测到需要用户输入，重新运行以显示确认界面
    if st.session_state.waiting_for_user:
        st.rerun()


def render_results_interface():
    """渲染结果展示界面"""
    st.markdown("## 🎉 设计分析完成")

    st.success("✅ 专业设计分析已完成！")

    # 获取分析结果
    if st.session_state.session_id:
        try:
            # 🔥 修复：先检查状态，避免在未完成时调用 get_result()
            status = st.session_state.api_client.get_status(st.session_state.session_id)

            if status.get("status") != "completed":
                st.warning(f"⚠️ 分析尚未完成，当前状态: {status.get('status')}")
                st.info("💡 请等待分析完成或返回继续交互")

                if st.button("🔄 刷新状态"):
                    st.rerun()

                if st.button("⬅️ 返回分析界面"):
                    st.session_state.analysis_complete = False
                    st.rerun()
                return

            result = st.session_state.api_client.get_result(st.session_state.session_id)

            # 显示查询类型（如果有）
            if "strategic_analysis" in result and result["strategic_analysis"]:
                strategic = result["strategic_analysis"]
                if "query_type" in strategic:
                    query_type = strategic["query_type"]
                    query_type_emoji = {"深度优先探询": "🔍", "广度优先探询": "📊", "直接探询": "💡"}
                    emoji = query_type_emoji.get(query_type, "🎯")
                    st.info(f"{emoji} **查询类型**: {query_type}")

            # 显示最终报告
            if "final_report" in result:
                st.markdown("### 📊 设计分析报告")
                st.markdown(result["final_report"])

            # 🆕 显示审核反馈章节
            if "review_feedback" in result and result["review_feedback"]:
                with st.expander("🔍 审核反馈与迭代改进", expanded=True):
                    st.markdown("#### 多视角审核过程")
                    review_data = result["review_feedback"]

                    # 创建标签页
                    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 迭代总结", "🔴 红队质疑", "🔵 蓝队验证", "⚖️ 评委裁决", "👔 甲方决策"])

                    with tab1:
                        st.markdown(review_data.get("iteration_summary", "暂无总结"))

                    with tab2:
                        challenges = review_data.get("red_team_challenges", [])
                        if challenges:
                            for item in challenges:
                                col1, col2, col3 = st.columns([2, 1, 1])
                                with col1:
                                    st.markdown(f"**{item.get('issue_id')}**: {item.get('description', '')}")
                                with col2:
                                    priority_color = {"high": "🔴", "medium": "🟡", "low": "🟢"}
                                    st.markdown(
                                        f"{priority_color.get(item.get('priority', 'medium'), '⚪')} {item.get('priority', 'medium')}"
                                    )
                                with col3:
                                    status_color = {"已修复": "✅", "进行中": "🔄", "待处理": "⏳"}
                                    st.markdown(
                                        f"{status_color.get(item.get('status', '待处理'), '❓')} {item.get('status', '待处理')}"
                                    )
                                st.markdown(f"**响应措施**: {item.get('response', '无')}")
                                st.markdown("---")
                        else:
                            st.info("无红队质疑点")

                    with tab3:
                        validations = review_data.get("blue_team_validations", [])
                        if validations:
                            for item in validations:
                                st.markdown(f"**{item.get('issue_id')}**: {item.get('description', '')}")
                                st.markdown(f"**价值增强**: {item.get('response', '')}")
                                st.markdown("---")
                        else:
                            st.info("无蓝队验证记录")

                    with tab4:
                        rulings = review_data.get("judge_rulings", [])
                        if rulings:
                            for item in rulings:
                                st.markdown(f"**{item.get('issue_id')}**: {item.get('description', '')}")
                                st.markdown(f"**裁决方案**: {item.get('response', '')}")
                                st.markdown(f"**状态**: {item.get('status', '待定')}")
                                st.markdown("---")
                        else:
                            st.info("无评委裁决记录")

                    with tab5:
                        decisions = review_data.get("client_decisions", [])
                        if decisions:
                            for item in decisions:
                                st.markdown(f"**{item.get('issue_id')}**: {item.get('description', '')}")
                                st.markdown(f"**实施计划**: {item.get('response', '')}")
                                st.markdown("---")
                        else:
                            st.info("无甲方决策记录")

            # 🆕 显示用户访谈记录
            if "questionnaire_responses" in result and result["questionnaire_responses"]:
                with st.expander("📝 用户访谈记录（校准问卷）", expanded=False):
                    qr_data = result["questionnaire_responses"]
                    st.markdown(f"**提交时间**: {qr_data.get('timestamp', '未知')}")
                    st.markdown("---")

                    responses = qr_data.get("responses", [])
                    for resp in responses:
                        st.markdown(f"**Q{resp.get('question_id', '?')}**: {resp.get('question', '')}")
                        st.markdown(f"> {resp.get('answer', '未回答')}")
                        if resp.get("context"):
                            st.caption(f"上下文: {resp['context']}")
                        st.markdown("---")

                    # 显示洞察分析
                    if qr_data.get("analysis_insights"):
                        st.markdown("#### 关键洞察")
                        st.markdown(qr_data["analysis_insights"])

            # 🆕 显示多轮审核可视化
            if "review_visualization" in result and result["review_visualization"]:
                with st.expander("📊 多轮审核可视化", expanded=False):
                    viz_data = result["review_visualization"]

                    st.markdown(f"**总审核轮次**: {viz_data.get('total_rounds', 0)}轮")
                    st.markdown(f"**最终决策**: {viz_data.get('final_decision', '未知')}")
                    st.markdown(f"**改进率**: {viz_data.get('improvement_rate', 0)*100:.1f}%")
                    st.markdown("---")

                    rounds = viz_data.get("rounds", [])
                    if rounds:
                        # 创建评分趋势表格
                        import pandas as pd

                        df = pd.DataFrame(
                            [
                                {
                                    "轮次": r.get("round_number", 0),
                                    "红队评分": r.get("red_score", 0),
                                    "蓝队评分": r.get("blue_score", 0),
                                    "评委评分": r.get("judge_score", 0),
                                    "发现问题": r.get("issues_found", 0),
                                    "解决问题": r.get("issues_resolved", 0),
                                }
                                for r in rounds
                            ]
                        )

                        st.dataframe(df, use_container_width=True)

                        # 简单的柱状图
                        st.markdown("#### 评分趋势")
                        st.bar_chart(df.set_index("轮次")[["红队评分", "蓝队评分", "评委评分"]])

            # 显示专家原始报告（如果有）
            if "expert_reports" in result and result["expert_reports"]:
                with st.expander("👥 查看专家原始报告", expanded=False):
                    for expert_id, report in result["expert_reports"].items():
                        st.markdown(f"#### {expert_id}")
                        st.markdown(report)
                        st.markdown("---")

            # 显示详细结果
            with st.expander("🔍 查看完整数据", expanded=False):
                st.json(result)

        except Exception as e:
            st.error(f"❌ 获取结果失败: {e}")

    # 重新分析按钮
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔄 开始新的设计分析", type="primary", use_container_width=True):
            # 重置状态
            st.session_state.analysis_started = False
            st.session_state.analysis_complete = False
            st.session_state.session_id = None
            st.session_state.user_input = ""
            st.session_state.current_status = None
            st.session_state.progress = 0.0
            st.rerun()


def render_role_task_review(interrupt_data):
    """渲染角色与任务统一审核界面（可编辑）"""
    st.info("📋 请审核项目总监选择的角色和任务分配。您可以直接修改任务内容后提交。")

    message = interrupt_data.get("message", "")
    if message:
        st.markdown(message)

    role_selection = interrupt_data.get("role_selection", {})
    selected_roles = role_selection.get("selected_roles", [])

    # 初始化编辑状态
    if "role_task_edits" not in st.session_state:
        st.session_state.role_task_edits = {}

    # 检测数据变化，重置编辑状态
    current_data_hash = str(selected_roles)
    if "last_role_task_hash" not in st.session_state or st.session_state.last_role_task_hash != current_data_hash:
        st.session_state.role_task_edits = {}
        st.session_state.last_role_task_hash = current_data_hash
        st.session_state.role_task_version = st.session_state.get("role_task_version", 0) + 1

    version = st.session_state.get("role_task_version", 0)

    if not selected_roles:
        st.warning("⚠️ 未找到选择的角色")
        return

    # 渲染每个角色的任务
    for idx, role in enumerate(selected_roles):
        role_id = role.get("role_id", "")
        role_name = role.get("role_name", "")
        dynamic_role_name = role.get("dynamic_role_name", role_name)
        tasks = role.get("tasks", [])
        focus_areas = role.get("focus_areas", [])
        expected_output = role.get("expected_output", "")
        dependencies = role.get("dependencies", [])

        with st.expander(f"🎭 {dynamic_role_name} ({role_id})", expanded=idx < 3):
            # 显示基本信息
            st.markdown(f"**基础角色**: {role_name}")
            if focus_areas:
                st.markdown(f"**关注领域**: {', '.join(focus_areas)}")
            if dependencies:
                st.markdown(f"**依赖角色**: {', '.join(dependencies)}")
            if expected_output:
                st.markdown(f"**预期产出**: {expected_output}")

            # 任务列表（可编辑）
            st.markdown("#### 📝 任务清单")
            for task_idx, task in enumerate(tasks):
                task_key = f"{role_id}_task_{task_idx}"
                default_value = st.session_state.role_task_edits.get(task_key, task)

                edited_task = st.text_area(
                    f"任务 {task_idx + 1}",
                    value=default_value,
                    height=80,
                    key=f"edit_{task_key}_v{version}",
                    help="您可以直接修改任务内容",
                )

                # 保存编辑
                st.session_state.role_task_edits[task_key] = edited_task

    # 提交按钮
    st.markdown("---")
    if st.button("✅ 提交角色与任务审核", type="primary", use_container_width=True):
        # 检测是否有修改
        has_modifications = False
        modifications = {}

        for idx, role in enumerate(selected_roles):
            role_id = role.get("role_id", "")
            tasks = role.get("tasks", [])
            modified_tasks = []

            for task_idx, original_task in enumerate(tasks):
                task_key = f"{role_id}_task_{task_idx}"
                edited_task = st.session_state.role_task_edits.get(task_key, original_task)

                # 检查是否有真实修改
                if edited_task.strip() != original_task.strip():
                    has_modifications = True

                modified_tasks.append(edited_task)

            if has_modifications:
                modifications[role_id] = modified_tasks

        # 构建响应
        resume_value = {"action": "approve"}

        if has_modifications:
            resume_value["modifications"] = modifications

        # 提交
        try:
            st.session_state.api_client.resume_analysis(st.session_state.session_id, resume_value)

            st.session_state.waiting_for_user = False
            st.session_state.interrupt_data = None
            st.session_state.role_task_edits = {}
            st.session_state.just_submitted = True  # 🔥 标记刚提交，避免立即轮询
            st.success("✅ 提交成功，继续分析...")
            time.sleep(2)  # 给后端2秒处理时间
            st.rerun()
        except Exception as e:
            st.error(f"❌ 提交失败: {e}")


if __name__ == "__main__":
    main()
