"""
🔥 v7.18 升级1 - Prompt 模板系统

预构建静态 Prompt 部分（约80%内容），减少每次执行时的重复拼接开销

核心优化:
1. 静态部分只在类初始化时构建一次（自主性协议、输出格式、约束条件）
2. 动态部分每次执行时构建（TaskInstruction、项目上下文）
3. 使用单例模式，为每种角色类型创建唯一模板实例

预期收益:
- Prompt 构建时间减少 80%
- 内存开销 ~2MB (10个角色模板缓存)
- 每个项目节省 1-2 秒
"""

from functools import lru_cache
from typing import Any, Dict, List

from loguru import logger


class ExpertPromptTemplate:
    """
    专家Prompt模板（静态部分预构建）

    ✅ 升级1优化：预构建80%的静态内容，减少拼接开销
    """

    def __init__(self, role_type: str, base_system_prompt: str, autonomy_protocol: Dict[str, Any]):
        """
        初始化模板（只在首次创建时执行）

        Args:
            role_type: 角色类型（如 "V2", "V3", "V4"）
            base_system_prompt: 角色的基础 system prompt
            autonomy_protocol: 自主性协议（全局共享）
        """
        self.role_type = role_type
        self.base_system_prompt = base_system_prompt

        # 🔥 预构建静态部分（只执行一次）
        self.static_sections = self._build_static_sections(autonomy_protocol)

        logger.debug(f"✅ [升级1] 为角色类型 {role_type} 预构建了 Prompt 静态部分")

    def _build_static_sections(self, autonomy_protocol: Dict[str, Any]) -> Dict[str, str]:
        """
        构建静态部分（80%的内容）

        这些内容对所有同类型角色都相同，预构建可避免重复拼接

        Returns:
            静态部分字典
        """
        return {
            "autonomy_section": f"""
# 🔄 专家自主性协议 v{autonomy_protocol.get('version', '4.0')}
{autonomy_protocol.get('protocol_content', '')}
""",
            "output_format_section": """
# 📊 严格输出要求

**你必须返回JSON格式的TaskOrientedExpertOutput，包含以下三个必填部分：**

```json
{{
  "task_execution_report": {{
    "deliverable_outputs": [
      {{
        "deliverable_name": "交付物名称（与任务指令中的交付物对应）",
        "content": "具体分析内容（详细完整，不要省略）",
        "completion_status": "completed",
        "completion_rate": 0.95,
        "notes": "补充说明或备注",
        "quality_self_assessment": 0.9
      }}
    ],
    "task_completion_summary": "任务完成情况总结（2-3句话）",
    "additional_insights": ["执行过程中的额外洞察（可选）"],
    "execution_challenges": ["遇到的挑战或限制（可选）"]
  }},
  "protocol_execution": {{
    "protocol_status": "complied",
    "compliance_confirmation": "确认接受需求分析师的洞察并按指令执行",
    "challenge_details": null,
    "reinterpretation": null
  }},
  "execution_metadata": {{
    "confidence": 0.9,
    "completion_rate": 1.0,
    "execution_time_estimate": "约X分钟",
    "execution_notes": "执行过程备注",
    "dependencies_satisfied": true
  }}
}}
```

# ⚠️ 关键要求

1. **严格围绕TaskInstruction**：只输出分配的交付物，不要添加其他内容
2. **JSON格式要求**：输出必须是有效的JSON，不要有额外的解释文字
3. **三个必填部分**：task_execution_report、protocol_execution、execution_metadata 缺一不可
4. **protocol_status**：必须是 "complied"、"challenged" 或 "reinterpreted" 之一
5. **内容完整性**：每个deliverable的content要详细完整，不要简化
6. **专业标准**：所有分析要符合你的专业领域标准
7. **🔥 v7.10.1: 中文字段名要求**：
   - 如果content是JSON对象（如用户画像、案例库等），所有字段名必须使用中文
   - ✅ 正确："案例名称"、"设计依据"、"视角"、"建议"
   - ❌ 错误："case_name"、"design_rationale"、"perspective"、"suggestions"
   - 内容中的专业术语可以使用英文，但字段名必须是中文

# 🚫 禁止事项

- 不要输出TaskInstruction之外的任何分析
- 不要在JSON前后添加解释性文字
- 不要省略或简化任何必需的字段
- 不要添加额外的建议或观察
- 不要使用markdown代码块包裹JSON
- 不要使用旧格式字段如 expert_summary、task_results、validation_checklist
- 🔥 v7.10.1: **不要输出图片占位符字段**（如"图片": ["image_1_url", "image_2_url"]）
  - 系统不支持专家生成图片，请专注于文本分析内容
  - 如需引用视觉元素，在文字内容中描述即可

**记住：你的输出将被严格验证，必须包含 task_execution_report、protocol_execution 和 execution_metadata 三个必填字段。**
""",
        }

    def render(
        self,
        dynamic_role_name: str,
        task_instruction: Dict[str, Any],
        context: str,
        state: Dict[str, Any],
        creative_mode_note: str = "",
        search_queries_hint: str = "",  # 🆕 v7.122: 搜索查询提示
    ) -> Dict[str, str]:
        """
        渲染完整Prompt（只构建动态部分20%）

        Args:
            dynamic_role_name: 动态角色名称
            task_instruction: 任务指令
            context: 项目上下文
            state: 当前状态
            creative_mode_note: 创意叙事模式说明（可选）
            search_queries_hint: 🆕 v7.122 预生成的搜索查询提示（可选）

        Returns:
            包含 system_prompt 和 user_prompt 的字典
        """
        # 🔥 构建动态的 TaskInstruction 部分（20%的内容）
        task_instruction_section = self._build_task_instruction_section(task_instruction)

        # 🆕 构建任务优先级提示（如果有confirmed_core_tasks）
        task_priority_section = self._build_task_priority_section(state)

        # 🆕 v7.154: 构建角色差异化指令（防止V4/V5输出同质化）
        role_differentiation_section = self._build_role_differentiation_section()

        # 🔥 拼接预构建的静态部分（80%）+ 动态部分（20%）
        system_prompt = f"""
{self.base_system_prompt}

# 🎯 动态角色定义
你在本次分析中的具体角色：{dynamic_role_name}
{creative_mode_note}
{role_differentiation_section}
# 📋 TaskInstruction - 你的明确任务指令

{task_instruction_section}

{task_priority_section}
{search_queries_hint}
{self.static_sections['autonomy_section']}
{self.static_sections['output_format_section']}
"""

        # 构建用户提示词
        # 🔥 v7.19: 添加输出质量引导
        # 🆕 v7.65: 增加搜索工具使用指引

        # 检查是否有require_search=true的交付物
        required_search_deliverables = [
            d.get("name") for d in task_instruction.get("deliverables", []) if d.get("require_search", False)
        ]

        search_guidance = ""
        if required_search_deliverables:
            search_guidance = f"""

# 🔍 搜索工具使用指引 (v7.65)

⚠️ **强制搜索要求**: 以下交付物已标记require_search=true，**必须**使用搜索工具获取外部资料：
{chr(10).join([f'- **{name}**' for name in required_search_deliverables])}

📚 **搜索工具使用规则**:
1. **MUST搜索** - 强制场景：
   - require_search=true的交付物（如上所列）
   - 需要2023年后的最新数据、趋势
   - 案例库、best practices、行业标杆
   - 学术理论依据、研究方法论

2. **SHOULD搜索** - 建议场景：
   - 提到具体行业、品牌、技术时
   - 需要具体数据支撑时（如尺寸、成本）
   - 跨领域知识（如商业+心理学）

3. **MAY搜索** - 可选场景：
   - 需要扩展视野、增加灵感
   - 验证已有判断的准确性

⛔ **禁止自行编造**: 当需要外部数据时，必须使用搜索工具获取，不得自行虚构案例、数据或趋势。
"""

        user_prompt = f"""
# 📂 项目上下文
{context}

# 📊 当前项目状态
- 项目阶段: {state.get('current_phase', '分析阶段')}
- 已完成分析: {len(state.get('expert_analyses', {}))}个专家
{search_guidance}
# 🎯 执行指令

请严格按照上述TaskInstruction执行你的专业分析任务，并以JSON格式返回TaskOrientedExpertOutput结构。

**关键要求：**
1. 只围绕分配的交付物进行分析
2. 确保protocol_execution部分完整填写
3. 所有内容必须符合成功标准
4. 返回格式必须是有效JSON
5. 不要有任何额外输出

# 📏 输出质量标准 (v7.19)

**内容深度要求：**
- 每个交付物的 content 字段应包含 **300-800字** 的详细分析
- 必须包含 **具体数据、案例或专业依据**，禁止空泛描述
- 使用 **分点结构**（如1. 2. 3.）组织复杂内容
- 结论必须 **可操作、可验证**

**高质量示例：**
✅ "根据人因工程标准(GB/T 14774)，走廊宽度应≥1.2m，当前设计1.5m满足双向通行需求。建议在转角处增加200mm缓冲区。"
❌ "走廊宽度合适，符合标准。"（太简短，无依据）

开始执行你的专业分析任务：
"""

        return {"system_prompt": system_prompt, "user_prompt": user_prompt}

    def _build_task_instruction_section(self, task_instruction: Dict[str, Any]) -> str:
        """
        构建 TaskInstruction 部分（动态内容）

        Args:
            task_instruction: 任务指令字典

        Returns:
            格式化的 TaskInstruction 文本
        """
        sections = []

        # 核心目标
        sections.append(
            f"""
## 核心目标
{task_instruction.get('objective', '基于专业领域提供深度分析')}
"""
        )

        # 交付物要求
        sections.append("## 交付物要求\n")
        deliverables = task_instruction.get("deliverables", [])
        if deliverables:
            for i, deliverable in enumerate(deliverables, 1):
                require_search_mark = "🔍必须搜索" if deliverable.get("require_search", False) else ""
                sections.append(
                    f"""
**交付物 {i}: {deliverable.get('name', f'交付物{i}')}** {require_search_mark}
- 描述: {deliverable.get('description', '')}
- 格式: {deliverable.get('format', 'analysis')}
- 优先级: {deliverable.get('priority', 'medium')}
- 成功标准: {', '.join(deliverable.get('success_criteria', []))}
"""
                )
                if deliverable.get("require_search", False):
                    sections.append("⚠️ **此交付物必须使用搜索工具获取外部资料**\n")

        # 整体成功标准
        sections.append(
            f"""
## 整体成功标准
{', '.join(task_instruction.get('success_criteria', ['输出符合专业标准']))}
"""
        )

        # 约束条件
        sections.append(
            f"""
## 约束条件
{', '.join(task_instruction.get('constraints', ['无特殊约束']))}
"""
        )

        # 上下文要求
        sections.append(
            f"""
## 上下文要求
{', '.join(task_instruction.get('context_requirements', ['无特殊上下文要求']))}
"""
        )

        return "\n".join(sections)

    def _build_task_priority_section(self, state: Dict[str, Any]) -> str:
        """
        构建任务优先级提示部分（基于问卷确认的核心任务）

        当用户通过问卷确认了核心任务后，此方法会生成一个优先级指引，
        提示专家优先关注这些核心任务相关的工作。

        Args:
            state: 工作流状态，包含 confirmed_core_tasks

        Returns:
            格式化的任务优先级提示文本，如果无确认任务则返回空字符串
        """
        confirmed_tasks = state.get("confirmed_core_tasks", [])

        # 边界情况：无问卷数据或用户未确认核心任务
        if not confirmed_tasks:
            return ""

        sections = []
        sections.append("\n## 📌 任务优先级指引")
        sections.append("\n用户在问卷中确认了以下核心任务，这些是项目的重点关注方向：\n")

        # 格式化核心任务列表
        for i, task in enumerate(confirmed_tasks, 1):
            task_title = task.get("title", f"任务{i}")
            task_desc = task.get("description", "")

            sections.append(f"**{i}. {task_title}**")
            if task_desc:
                sections.append(f"   - {task_desc}")
            sections.append("")  # 空行分隔

        # 添加优先级说明
        sections.append("**执行建议：**")
        sections.append("- 在分析时，优先围绕这些核心任务展开")
        sections.append("- 如果你的交付物与这些任务相关，应重点关注")
        sections.append("- 衍生任务虽然重要，但应在核心任务满足后再深化")

        return "\n".join(sections)

    def _build_role_differentiation_section(self) -> str:
        """
        🆕 v7.154: 构建角色差异化指令

        防止V4和V5输出内容同质化，明确各角色的独特视角和分析焦点

        Returns:
            角色差异化指令文本，如果不是V4/V5则返回空字符串
        """
        if self.role_type == "V4":
            return """
# 🎯 角色差异化指令 (v7.154)

**你是V4设计研究员，你的独特视角是：**
- 📊 **数据驱动分析**：用数据和统计支撑观点，而非主观描述
- 🌍 **国际视野**：优先引用国际案例、全球趋势、跨文化对比
- 📈 **趋势研判**：关注行业发展方向、新兴技术、未来预测
- 🔬 **方法论严谨**：使用学术研究方法、引用权威来源

**⚠️ 差异化要求（避免与V5重复）：**
- ❌ 不要过多描述本地场景适配和用户行为细节（这是V5的职责）
- ❌ 不要罗列大量本地案例（应聚焦国际标杆和数据对比）
- ✅ 应该提供：数据对比表、趋势图表描述、国际案例分析、研究方法论
"""
        elif self.role_type == "V5":
            return """
# 🎯 角色差异化指令 (v7.154)

**你是V5场景行业专家，你的独特视角是：**
- 🏠 **本地化适配**：关注本地市场、文化习惯、法规标准
- 👥 **用户行为洞察**：深入分析用户动线、使用习惯、痛点需求
- 🎬 **场景模拟**：描述具体使用场景、时间节奏、功能分区
- 💡 **实操建议**：提供可落地的具体建议，而非理论分析

**⚠️ 差异化要求（避免与V4重复）：**
- ❌ 不要过多引用国际案例和数据趋势（这是V4的职责）
- ❌ 不要进行宏观的行业分析和方法论探讨
- ✅ 应该提供：用户旅程图、场景描述、功能分区建议、本地化适配方案
"""
        else:
            return ""


# 🔥 全局模板缓存（单例模式）
_template_cache: Dict[str, ExpertPromptTemplate] = {}


def get_expert_template(
    role_type: str, base_system_prompt: str, autonomy_protocol: Dict[str, Any]
) -> ExpertPromptTemplate:
    """
    获取或创建专家模板（单例模式）

    ✅ 升级1优化：每种角色类型只创建一次模板

    Args:
        role_type: 角色类型（如 "V2", "V3"）
        base_system_prompt: 基础 system prompt
        autonomy_protocol: 自主性协议

    Returns:
        缓存的模板实例
    """
    if role_type not in _template_cache:
        logger.info(f"🔧 [升级1] 首次创建 {role_type} 的 Prompt 模板，将缓存于内存")
        _template_cache[role_type] = ExpertPromptTemplate(role_type, base_system_prompt, autonomy_protocol)
    else:
        logger.debug(f"✅ [升级1] 使用缓存的 {role_type} Prompt 模板")

    return _template_cache[role_type]


def clear_template_cache():
    """清除模板缓存（用于测试或重新加载）"""
    global _template_cache
    _template_cache.clear()
    logger.info("🔧 [升级1] 已清除 Prompt 模板缓存")
