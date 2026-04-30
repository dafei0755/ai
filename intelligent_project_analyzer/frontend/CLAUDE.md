# 前端界面模块 - AI 协作文档

> 📍 **路径导航**: [根目录](../../CLAUDE.md) > [intelligent_project_analyzer](../) > **frontend**

---

## 📋 模块职责

**Streamlit 前端界面 (Web UI)**

本模块提供完整的 Web 用户界面，支持需求输入、实时进度跟踪、人机交互和结果展示。

### 核心功能
- 🎨 **美观界面**: 自定义 CSS 样式
- 📝 **需求输入**: 多种示例需求模板
- 📊 **进度跟踪**: 实时显示分析进度
- 💬 **人机交互**: 处理需求确认、角色审核等
- 📄 **结果展示**: 分章节展示分析结果
- 🔄 **状态同步**: 自动轮询后端状态

---

## 📁 文件结构

```
frontend/
├── app.py                    # Streamlit 主应用
├── frontend_components.py    # 可复用UI组件
└── run_frontend.py          # 启动脚本
```

---

## 🔑 核心界面

### 1. 需求输入界面

**功能**:
- 提供示例需求模板
- 支持自由文本输入
- 启动分析按钮

**示例需求**:
```
示例1: 深圳南山独立女性住宅设计
项目需求: 深圳南山，38岁独立女性，英国海归，不婚主义，200平米大平层，
对Audrey Hepburn赫本情有独钟，基于此给出室内设计建议。

示例2: 铜锣湾广场商业综合体设计
项目需求: 给出室内设计概念思路
项目: 铜锣湾广场
地点: 南充嘉陵区
面积: 50000平米，两层商业街区
```

---

### 2. 进度跟踪界面

**功能**:
- 显示当前阶段
- 进度条显示完成度
- 实时日志输出

**进度指示器**:
```python
st.progress(st.session_state.progress, text=f"分析进度: {st.session_state.progress:.0%}")
```

---

### 3. 人机交互界面

**功能**:
- 展示 interrupt_data（需求确认、角色审核等）
- 提供交互选项（批准/拒绝/修改）
- 支持自然语言输入

**交互示例**:
```python
if st.session_state.waiting_for_user:
    interrupt_data = st.session_state.interrupt_data
    interaction_type = interrupt_data.get("interaction_type")

    if interaction_type == "requirements_confirmation":
        # 显示需求摘要
        st.write(interrupt_data["message"])
        # 提供确认/拒绝按钮
        if st.button("确认需求"):
            api_client.resume_analysis(session_id, "approve")
```

---

### 4. 结果展示界面

**功能**:
- 分章节展示分析结果
- 支持折叠/展开
- 下载 PDF 报告

**结果卡片**:
```python
for section in final_report["sections"]:
    with st.expander(f"📄 {section['title']} (置信度: {section['confidence']:.0%})"):
        st.markdown(section['content'])
```

---

## 🎨 自定义样式

**CSS 组件**:
- `.main-header`: 渐变色主标题
- `.agent-card`: 智能体卡片（悬停效果）
- `.info-box`: 信息提示框
- `.timeline-item`: 时间轴样式

**应用样式**:
```python
from frontend_components import apply_custom_css
apply_custom_css()
```

---

## 🔄 状态管理

**Session State 字段**:
```python
st.session_state.session_id          # 会话ID
st.session_state.analysis_started     # 是否开始分析
st.session_state.analysis_complete    # 是否完成
st.session_state.waiting_for_user     # 是否等待用户输入
st.session_state.interrupt_data       # interrupt数据
st.session_state.progress             # 进度(0.0-1.0)
st.session_state.api_client           # API客户端实例
```

---

## 🧪 启动方式

**方法1: 直接运行**
```bash
streamlit run intelligent_project_analyzer/frontend/app.py
```

**方法2: 使用启动脚本**
```bash
python intelligent_project_analyzer/frontend/run_frontend.py
```

**访问界面**:
- 前端: http://localhost:8501
- 后端API: http://localhost:8000

---

## 📚 相关资源

- [API 服务](../api/CLAUDE.md)
- [人机交互节点](../interaction/CLAUDE.md)
- [Streamlit 官方文档](https://docs.streamlit.io/)

---

**最后更新**: 2025-11-16
**覆盖率**: 90%
**文档版本**: 1.0.0
