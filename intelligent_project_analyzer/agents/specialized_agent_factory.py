"""
专业智能体工厂 - Specialized Agent Factory

根据角色配置动态创建专业智能体。
Dynamically creates specialized agents based on role configurations.
"""

from typing import Dict, Any, Callable
try:
    from langgraph.prebuilt import create_react_agent
except ImportError:
    # 尝试处理 langgraph 命名空间包问题
    import sys
    from loguru import logger
    logger.warning("Failed to import langgraph.prebuilt directly. Attempting workarounds...")
    try:
        # 尝试先导入 langgraph
        import langgraph
        from langgraph.prebuilt import create_react_agent
    except ImportError as e:
        logger.error(f"Failed to import create_react_agent: {e}")
        # 打印调试信息
        try:
            import langgraph
            logger.error(f"langgraph path: {getattr(langgraph, '__path__', 'unknown')}")
        except:
            pass
        raise

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage  # 🆕 N3优化：添加重试消息类型
from intelligent_project_analyzer.core.role_manager import RoleManager


class SpecializedAgentFactory:
    """
    专业智能体工厂

    功能:
    1. 根据角色配置动态创建智能体节点
    2. 加载客户自定义的 system_prompt
    3. 动态构建包含项目需求和其他专家结果的完整上下文
    4. 支持 Dynamic Mode 的并行执行

    主要方法:
    - create_simple_agent_node: 创建轻量级智能体节点（当前使用）
    - create_agent: 创建 ReAct 智能体（保留用于未来扩展）
    """
    
    @staticmethod
    def create_agent(
        role_id: str,
        role_config: Dict[str, Any],
        llm_model,
        tools: list = None
    ):
        """
        创建专业智能体
        
        Args:
            role_id: 角色ID
            role_config: 角色配置
            llm_model: LLM模型实例
            tools: 可用工具列表
        
        Returns:
            创建的ReAct智能体
        """
        # 获取system_prompt
        system_prompt = role_config.get("system_prompt", "你是一位专业的智能体助手。")
        
        # 创建ReAct智能体
        agent = create_react_agent(
            llm_model,
            tools or [],
            state_modifier=system_prompt
        )
        
        return agent
    
    @staticmethod
    def create_simple_agent_node(
        role_id: str,
        role_config: Dict[str, Any],
        llm_model
    ) -> Callable:
        """
        创建简单的智能体节点(不使用工具)
        
        Args:
            role_id: 角色ID
            role_config: 角色配置
            llm_model: LLM模型实例
        
        Returns:
            智能体节点函数
        """
        # 获取system_prompt
        system_prompt = role_config.get("system_prompt", "你是一位专业的智能体助手。")
        
        # 定义节点函数
        def simple_agent_node(state: Dict) -> Dict:
            """
            简单智能体节点函数

            Args:
                state: 图状态

            Returns:
                状态更新
            """
            import json
            from loguru import logger

            # ✅ 获取完整的项目信息
            requirements = state.get("structured_requirements", {})
            task_description = state.get("task_description", "")
            agent_results = state.get("agent_results", {})
            messages = state.get("messages", [])
            
            # ✅ 检查是否为重新执行并获取审核反馈
            is_rerun = state.get("is_rerun", False)
            review_feedback_for_agent = state.get("review_feedback_for_agent", {})

            # 🔧 替换提示词中的占位符 {user_specific_request}
            # 优先使用角色特定任务，否则使用通用任务描述
            role_specific_task = state.get(f"{role_id}_task", "")  # 如果有角色特定任务
            user_specific_request = role_specific_task or task_description or "完成您所擅长领域的专业分析"
            
            # 替换占位符
            processed_prompt = system_prompt.replace("{user_specific_request}", user_specific_request)

            # ✅ 构建包含项目需求的提示词
            prompt_parts = [processed_prompt]

            # 添加项目需求信息
            if requirements:
                prompt_parts.append("\n---\n\n## 项目需求信息\n\n")
                prompt_parts.append(json.dumps(requirements, ensure_ascii=False, indent=2))

            # 添加任务描述
            if task_description:
                prompt_parts.append("\n---\n\n## 你的任务\n\n")
                prompt_parts.append(task_description)

            # 添加其他专家的分析结果
            if agent_results:
                prompt_parts.append("\n---\n\n## 其他专家的分析结果（供参考）\n\n")
                for aid, result in agent_results.items():
                    analysis = result.get("analysis", "")
                    if analysis:
                        # 只显示前200个字符，避免提示词过长
                        prompt_parts.append(f"\n### {aid}\n{analysis[:200]}...\n")
            
            # ✅ 新增：如果是重新执行，附加审核反馈
            if is_rerun and review_feedback_for_agent:
                specific_tasks = review_feedback_for_agent.get("specific_tasks", [])
                iteration_context = review_feedback_for_agent.get("iteration_context", {})
                avoid_changes_to = review_feedback_for_agent.get("avoid_changes_to", [])
                
                if specific_tasks or iteration_context:
                    logger.info(f"📝 {role_id} 收到审核反馈：{len(specific_tasks)} 个改进任务")
                    
                    prompt_parts.append("\n" + "="*60 + "\n")
                    prompt_parts.append("⚠️ 这是重新执行轮次 - 请根据审核反馈改进\n")
                    prompt_parts.append("="*60 + "\n\n")
                    
                    # 添加迭代上下文
                    if iteration_context:
                        round_num = iteration_context.get("round", 1)
                        prompt_parts.append(f"## 迭代轮次：第 {round_num} 轮\n\n")
                        
                        previous_summary = iteration_context.get("previous_output_summary", "")
                        if previous_summary:
                            prompt_parts.append(f"### 上一轮输出摘要\n{previous_summary}\n\n")
                        
                        what_worked = iteration_context.get("what_worked_well", [])
                        if what_worked:
                            prompt_parts.append("### ✅ 上一轮做得好的方面（保持）\n")
                            for item in what_worked:
                                prompt_parts.append(f"- {item}\n")
                            prompt_parts.append("\n")
                        
                        what_needs_improvement = iteration_context.get("what_needs_improvement", [])
                        if what_needs_improvement:
                            prompt_parts.append("### ⚠️ 需要改进的方面\n")
                            for item in what_needs_improvement:
                                prompt_parts.append(f"- {item}\n")
                            prompt_parts.append("\n")
                    
                    # 添加具体改进任务
                    if specific_tasks:
                        prompt_parts.append("## 🎯 具体改进任务清单\n\n")
                        prompt_parts.append("请逐一解决以下问题，确保本次输出质量显著提升：\n\n")
                        
                        for task in specific_tasks:
                            task_id = task.get("task_id", "")
                            priority = task.get("priority", "medium")
                            instruction = task.get("instruction", "")
                            example = task.get("example", "")
                            validation = task.get("validation", "")
                            
                            priority_icon = "🔴" if priority == "high" else "🟡" if priority == "medium" else "🟢"
                            
                            prompt_parts.append(f"### {priority_icon} 任务 {task_id} ({priority.upper()})\n\n")
                            prompt_parts.append(f"**要求**: {instruction}\n\n")
                            if example:
                                prompt_parts.append(f"**示例**: {example}\n\n")
                            if validation:
                                prompt_parts.append(f"**验证**: {validation}\n\n")
                            prompt_parts.append("---\n\n")
                    
                    # 添加保持不变的内容
                    if avoid_changes_to:
                        prompt_parts.append("## 🔒 以下方面已经良好，无需改动\n\n")
                        for item in avoid_changes_to:
                            prompt_parts.append(f"- {item}\n")
                        prompt_parts.append("\n")
                    
                    prompt_parts.append("="*60 + "\n")
                    prompt_parts.append("🎯 本次分析要求：针对上述改进任务逐一解决，提供更高质量的分析结果\n")
                    prompt_parts.append("="*60 + "\n\n")

            prompt_parts.append("\n---\n")
            
            # 🔧 N3优化：强化v3.5协议说明，醒目提示必填字段
            prompt_parts.append("\n" + "="*80 + "\n")
            prompt_parts.append("🚨 **CRITICAL v3.5 EXPERT AUTONOMY PROTOCOL** 🚨\n")
            prompt_parts.append("="*80 + "\n\n")
            
            prompt_parts.append("📋 **MANDATORY JSON FIELDS** (failure = automatic retry):\n\n")
            prompt_parts.append("1. ✅ expert_handoff_response (REQUIRED):\n")
            prompt_parts.append("   {\n")
            prompt_parts.append('     "critical_questions_responses": {"q1_...": "your answer", ...},\n')
            prompt_parts.append('     "chosen_design_stance": "your choice"\n')
            prompt_parts.append("   }\n\n")
            
            prompt_parts.append("2. ✅ design_rationale OR decision_rationale (REQUIRED):\n")
            prompt_parts.append("   Explain WHY you made your design decisions\n\n")
            
            prompt_parts.append("3. ✅ challenge_flags (REQUIRED):\n")
            prompt_parts.append("   - If you disagree with requirements analyst: provide challenges\n")
            prompt_parts.append("   - If you agree: use empty array []\n\n")
            
            prompt_parts.append("🔧 **OUTPUT FORMAT REQUIREMENTS**:\n")
            prompt_parts.append("- DO NOT use markdown code fences (no ```json or ```).\n")
            prompt_parts.append("- START with { and END with }\n")
            prompt_parts.append("- Include ALL 3 mandatory fields above\n\n")
            
            # 🌐 v3.5.1: 添加中文输出要求
            prompt_parts.append("🌐 **OUTPUT LANGUAGE REQUIREMENTS (CRITICAL)**:\n")
            prompt_parts.append("- 所有字段值（JSON value）必须使用简体中文\n")
            prompt_parts.append("- 分析内容、建议、描述、名称等必须全部用中文撰写\n")
            prompt_parts.append("- 专业术语可保留英文，但需附带中文解释（如：Wabi-Sabi/侘寂）\n")
            prompt_parts.append("- ❌ 禁止输出英文分析内容\n")
            prompt_parts.append("- ❌ 禁止输出未翻译的英文策略或建议\n\n")
            
            prompt_parts.append("⚠️ Non-compliant outputs trigger automatic retry (max 1 retry).\n")
            prompt_parts.append("="*80 + "\n\n")

            complete_prompt = "".join(prompt_parts)

            # 构建消息
            full_messages = [SystemMessage(content=complete_prompt)] + messages

            # 调用LLM
            response = llm_model.invoke(full_messages)
            
            # ✅ v3.5: 验证专家主动性协议执行情况
            result_content = response.content
            
            # 🔧 N3优化：增加协议遵守率检查，支持自动重试
            import json
            parsed_result = {}
            json_parse_failed = False
            protocol_violations = []
            retry_count = state.get(f"protocol_retry_{role_id}", 0)  # 🆕 协议重试计数
            max_protocol_retries = 1  # 最多重试1次
            
            try:
                # 查找 JSON 块
                if "```json" in result_content:
                    json_start = result_content.find("```json") + 7
                    json_end = result_content.find("""`""", json_start)
                    json_str = result_content[json_start:json_end].strip()
                elif "{" in result_content and "}" in result_content:
                    json_str = result_content[result_content.find("{"):result_content.rfind("}")+1]
                else:
                    logger.error(f"❌ [v3.5 PROTOCOL VIOLATION] {role_id} 输出不包含JSON对象")
                    json_parse_failed = True
                    json_str = "{}"
                
                if not json_parse_failed:
                    parsed_result = json.loads(json_str)
                    logger.info(f"✅ [v3.5 Protocol] {role_id} JSON解析成功")
                
                # 🔧 P2修复：统计协议遵守情况
                protocol_violations = []
                
                # 检查1: expert_handoff_response（回应 critical_questions）
                if "expert_handoff_response" in parsed_result:
                    handoff_response = parsed_result["expert_handoff_response"]
                    if isinstance(handoff_response, dict) and handoff_response:
                        # 检查是否真正回答了问题
                        has_responses = any(key in handoff_response for key in [
                            "critical_questions_responses", "answered_questions", "chosen_design_stance"
                        ])
                        if has_responses:
                            logger.info(f"✅ [v3.5 Protocol] {role_id} 包含有效的 expert_handoff_response")
                        else:
                            protocol_violations.append("expert_handoff_response字段存在但内容为空")
                            logger.warning(f"⚠️ [v3.5 VIOLATION] {role_id} 的 expert_handoff_response 无有效内容")
                    else:
                        protocol_violations.append("expert_handoff_response字段无效")
                        logger.warning(f"⚠️ [v3.5 VIOLATION] {role_id} 的 expert_handoff_response 为空或无效")
                else:
                    protocol_violations.append("缺少expert_handoff_response字段")
                    logger.error(f"❌ [v3.5 VIOLATION] {role_id} 未包含 expert_handoff_response 字段")
                
                # 检查2: challenge_flags（专家挑战）
                if "challenge_flags" in parsed_result:
                    challenge_flags = parsed_result["challenge_flags"]
                    if isinstance(challenge_flags, list) and challenge_flags:
                        logger.warning(f"🔥 [v3.5 Protocol] {role_id} 提出了 {len(challenge_flags)} 个挑战标记")
                        for i, challenge in enumerate(challenge_flags, 1):
                            # 🔧 P0修复: 检查challenge是否为字典类型
                            if isinstance(challenge, dict):
                                challenged_item = challenge.get("challenged_item", "未知项目")
                                logger.warning(f"   🔥 挑战 {i}: {challenged_item}")
                            elif isinstance(challenge, str):
                                # 如果是字符串，直接使用字符串内容
                                logger.warning(f"   🔥 挑战 {i}: {challenge}")
                            else:
                                # 其他类型，转为字符串
                                logger.warning(f"   🔥 挑战 {i}: {str(challenge)}")
                    else:
                        logger.debug(f"ℹ️ [v3.5 Protocol] {role_id} 接受需求分析师的洞察（无挑战）")
                else:
                    logger.debug(f"ℹ️ [v3.5 Protocol] {role_id} 未包含 challenge_flags 字段（默认接受）")
                
                # 检查3: design_rationale/decision_rationale（设计立场解释）
                has_rationale = any(key in parsed_result for key in [
                    "design_rationale", "decision_rationale", "decision_logic"
                ])
                if not has_rationale:
                    protocol_violations.append("缺少design_rationale字段")
                    logger.error(f"❌ [v3.5 VIOLATION] {role_id} 未明确解释设计立场（缺少 design_rationale/decision_rationale）")
                
                # 🔧 P2修复：汇总违规情况
                if protocol_violations:
                    logger.error(f"\n📊 [v3.5 COMPLIANCE] {role_id} 协议遵守率: {len(protocol_violations)} 个违规项")
                    for i, violation in enumerate(protocol_violations, 1):
                        logger.error(f"   {i}. {violation}")
                    
                    # 🆕 N3优化: 如果违规且未达到重试上限，触发重试
                    if retry_count < max_protocol_retries:
                        logger.warning(f"🔄 [v3.5 RETRY] {role_id} 触发协议遵守重试 ({retry_count + 1}/{max_protocol_retries})")
                        
                        # 构建重试提示
                        retry_prompt = f"""
🚨 CRITICAL: Your previous response violated the v3.5 Expert Autonomy Protocol.

Missing fields:
{chr(10).join(f'  - {v}' for v in protocol_violations)}

YOU MUST include these fields in your JSON response:
1. expert_handoff_response: {{
     "critical_questions_responses": {{"q1_...": "your answer", ...}},
     "chosen_design_stance": "your choice"
   }}
2. design_rationale or decision_rationale: "explain your design decisions"
3. challenge_flags: [] (empty array if you accept requirements analyst's insights)

Please regenerate your complete response with ALL required fields.
Start directly with the JSON object (no markdown, no explanations).
"""
                        
                        # 添加重试提示到messages
                        retry_messages = full_messages + [
                            AIMessage(content=result_content),
                            HumanMessage(content=retry_prompt)
                        ]
                        
                        # 更新重试计数
                        state[f"protocol_retry_{role_id}"] = retry_count + 1
                        
                        # 重新调用LLM
                        logger.info(f"🔄 重新调用LLM进行协议修正...")
                        response = llm_model.invoke(retry_messages)
                        result_content = response.content
                        
                        # 重新解析
                        try:
                            if "```json" in result_content:
                                json_start = result_content.find("```json") + 7
                                json_end = result_content.find("```", json_start)
                                json_str = result_content[json_start:json_end].strip()
                            elif "{" in result_content and "}" in result_content:
                                json_str = result_content[result_content.find("{"):result_content.rfind("}")+1]
                            else:
                                json_str = "{}"
                            
                            parsed_result = json.loads(json_str)
                            logger.info(f"✅ [v3.5 RETRY] {role_id} 重试后JSON解析成功")
                            
                            # 重新检查协议（简化版）
                            retry_violations = []
                            if "expert_handoff_response" not in parsed_result:
                                retry_violations.append("expert_handoff_response")
                            if not any(k in parsed_result for k in ["design_rationale", "decision_rationale", "decision_logic"]):
                                retry_violations.append("design_rationale")
                            
                            if retry_violations:
                                logger.error(f"❌ [v3.5 RETRY] {role_id} 重试后仍违规: {retry_violations}")
                            else:
                                logger.info(f"✅ [v3.5 RETRY] {role_id} 重试成功，协议完全遵守！")
                        except Exception as retry_error:
                            logger.error(f"❌ [v3.5 RETRY] {role_id} 重试解析失败: {retry_error}")
                else:
                    logger.info(f"✅ [v3.5 COMPLIANCE] {role_id} 完全遵守v3.5专家主动性协议")
                    
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                logger.error(f"❌ [v3.5 PROTOCOL VIOLATION] {role_id} JSON解析失败: {e}")
                logger.error(f"   输出预览: {result_content[:200]}...")
                json_parse_failed = True
                parsed_result = {}  # 解析失败时使用空字典

            # 🔧 P0修复：返回parsed_result供挑战检测使用
            return {
                "messages": [response],
                "role_results": [{
                    "role_id": role_id,
                    "role_name": role_config.get("name", "未知角色"),
                    "result": response.content,
                    "parsed_result": parsed_result  # 🆕 保存解析后的结构化数据
                }]
            }
        
        return simple_agent_node


# 使用示例
if __name__ == "__main__":
    from langchain_openai import ChatOpenAI
    from intelligent_project_analyzer.core.role_manager import RoleManager
    import os

    # 初始化 - 使用 OpenAI Official API
    llm = ChatOpenAI(
        model="gpt-4.1",
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    role_manager = RoleManager()
    
    # 获取一个角色配置
    role_config = role_manager.get_role_config("V2_设计总监", "2-1")
    
    if role_config:
        # 创建智能体节点
        agent_node = SpecializedAgentFactory.create_simple_agent_node(
            "V2_设计总监_2-1",
            role_config,
            llm
        )
        
        # 测试节点
        test_state = {
            "messages": [
                {"role": "user", "content": "请分析这个建筑设计项目的空间规划"}
            ]
        }
        
        result = agent_node(test_state)
        print("智能体响应:")
        print(result["role_results"][0]["result"])

