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

from typing import Dict, Any, List
from loguru import logger
from functools import lru_cache


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
"""
        }

    def render(
        self,
        dynamic_role_name: str,
        task_instruction: Dict[str, Any],
        context: str,
        state: Dict[str, Any],
        creative_mode_note: str = ""
    ) -> Dict[str, str]:
        """
        渲染完整Prompt（只构建动态部分20%）

        Args:
            dynamic_role_name: 动态角色名称
            task_instruction: 任务指令
            context: 项目上下文
            state: 当前状态
            creative_mode_note: 创意叙事模式说明（可选）

        Returns:
            包含 system_prompt 和 user_prompt 的字典
        """
        # 🔥 构建动态的 TaskInstruction 部分（20%的内容）
        task_instruction_section = self._build_task_instruction_section(task_instruction)

        # 🔥 拼接预构建的静态部分（80%）+ 动态部分（20%）
        system_prompt = f"""
{self.base_system_prompt}

# 🎯 动态角色定义
你在本次分析中的具体角色：{dynamic_role_name}
{creative_mode_note}
# 📋 TaskInstruction - 你的明确任务指令

{task_instruction_section}

{self.static_sections['autonomy_section']}
{self.static_sections['output_format_section']}
"""

        # 构建用户提示词
        # 🔥 v7.19: 添加输出质量引导
        user_prompt = f"""
# 📂 项目上下文
{context}

# 📊 当前项目状态
- 项目阶段: {state.get('current_phase', '分析阶段')}
- 已完成分析: {len(state.get('expert_analyses', {}))}个专家

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

        return {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt
        }

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
        sections.append(f"""
## 核心目标
{task_instruction.get('objective', '基于专业领域提供深度分析')}
""")

        # 交付物要求
        sections.append("## 交付物要求\n")
        deliverables = task_instruction.get('deliverables', [])
        if deliverables:
            for i, deliverable in enumerate(deliverables, 1):
                sections.append(f"""
**交付物 {i}: {deliverable.get('name', f'交付物{i}')}**
- 描述: {deliverable.get('description', '')}
- 格式: {deliverable.get('format', 'analysis')}
- 优先级: {deliverable.get('priority', 'medium')}
- 成功标准: {', '.join(deliverable.get('success_criteria', []))}
""")

        # 整体成功标准
        sections.append(f"""
## 整体成功标准
{', '.join(task_instruction.get('success_criteria', ['输出符合专业标准']))}
""")

        # 约束条件
        sections.append(f"""
## 约束条件
{', '.join(task_instruction.get('constraints', ['无特殊约束']))}
""")

        # 上下文要求
        sections.append(f"""
## 上下文要求
{', '.join(task_instruction.get('context_requirements', ['无特殊上下文要求']))}
""")

        return "\n".join(sections)


# 🔥 全局模板缓存（单例模式）
_template_cache: Dict[str, ExpertPromptTemplate] = {}


def get_expert_template(
    role_type: str,
    base_system_prompt: str,
    autonomy_protocol: Dict[str, Any]
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
