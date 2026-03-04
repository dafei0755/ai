"""
ResultAggregator 交付物答案 Mixin
由 scripts/refactor/_split_mt12_result_aggregator.py 自动生成 (MT-12)
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from ..workflow.state import ProjectAnalysisState


class AggregatorDeliverableMixin:
    """Mixin — ResultAggregator 交付物答案 Mixin"""
    def _extract_deliverable_answers(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        """
         v7.0: 从责任者输出中提取交付物答案

        核心逻辑：
        1. 从 deliverable_metadata 获取每个交付物的 owner
        2. 从 agent_results[owner] 中提取该专家的输出
        3. 直接使用专家输出作为答案，不做LLM二次综合

        Returns:
            {
                "deliverable_answers": [...],  # 各交付物的责任者答案
                "expert_support_chain": [...], # 专家支撑链
                "question": str,               # 用户核心问题
                "answer": str,                 # 综合摘要（向后兼容）
                "deliverables": [...],         # 交付物清单（向后兼容）
                "timeline": str,
                "budget_range": str
            }
        """
        deliverable_metadata = state.get("deliverable_metadata") or {}
        deliverable_owner_map = state.get("deliverable_owner_map") or {}
        agent_results = state.get("agent_results") or {}
        structured_requirements = state.get("structured_requirements") or {}
        user_input = state.get("user_input", "")

        logger.info(f" [v7.0] 开始提取交付物答案: {len(deliverable_metadata)} 个交付物")
        logger.debug(f"deliverable_owner_map: {deliverable_owner_map}")
        logger.debug(f"agent_results keys: {list(agent_results.keys())}")

        deliverable_answers = []
        expert_support_chain = []
        owners_set = set()  # 记录已作为owner的专家
        seen_names = {}  #  v7.154: 用于交付物名称去重

        #  v7.283: 数据验证 - 过滤异常ID（防止搜索结果混入）
        import re

        valid_deliverable_pattern = re.compile(r"^\d+-\d+_\d+_\d+_[a-z]{3}$")  # 正确格式：2-1_1_143022_abc
        invalid_count = 0

        for deliverable_id in list(deliverable_metadata.keys()):
            if not valid_deliverable_pattern.match(deliverable_id):
                logger.error(f" [v7.283] 检测到异常交付物ID格式: {deliverable_id}，已过滤")
                logger.error(f"   交付物名称: {deliverable_metadata[deliverable_id].get('name', 'N/A')}")
                logger.error("   正确格式应为: role_id_sequence_timestamp_hash (如 2-1_1_143022_abc)")
                deliverable_metadata.pop(deliverable_id)
                invalid_count += 1

        if invalid_count > 0:
            logger.warning(f"️ [v7.283] 已过滤 {invalid_count} 个异常交付物ID（可能是搜索结果数据混入）")

        # 1. 提取每个交付物的责任者答案
        for deliverable_id, metadata in deliverable_metadata.items():
            owner_role = metadata.get("owner") or deliverable_owner_map.get(deliverable_id)

            if not owner_role:
                logger.warning(f"️ 交付物 {deliverable_id} 无责任者，跳过")
                continue

            owners_set.add(owner_role)

            # 在 agent_results 中查找匹配的专家输出
            # owner_role 格式可能是 "V2_设计总监_室内策略方向" 这样的完整ID
            # agent_results 的 key 可能是 "V2_设计总监_2-1" 这样的格式
            owner_result = self._find_owner_result(agent_results, owner_role)

            if not owner_result:
                logger.warning(f"️ 未找到责任者 {owner_role} 的输出")
                owner_answer = f"（{owner_role} 的输出待生成）"
                answer_summary = owner_answer
                quality_score = None
            else:
                owner_answer = self._extract_owner_deliverable_output(owner_result, deliverable_id)
                answer_summary = self._generate_answer_summary(owner_answer)
                quality_score = self._extract_quality_score(owner_result)

            #  v7.108: 提取概念图
            #  v7.154: 增强概念图关联逻辑
            concept_images = []
            if owner_result:
                concept_images_data = owner_result.get("concept_images", [])
                # 过滤出属于该交付物的概念图
                for img_data in concept_images_data:
                    img_deliverable_id = img_data.get("deliverable_id", "")
                    # 精确匹配
                    if img_deliverable_id == deliverable_id:
                        concept_images.append(img_data)
                    #  v7.154: 如果是主交付物（如 D1），关联该专家的所有概念图
                    elif deliverable_id.startswith("D") and deliverable_id[1:].isdigit():
                        # D1, D2 等主交付物，关联该专家的所有概念图
                        concept_images.append(img_data)
                        logger.debug(f"️ [v7.154] 主交付物 {deliverable_id} 关联概念图: {img_deliverable_id}")

            #  v7.154: 交付物名称去重
            deliverable_name = metadata.get("name", deliverable_id)
            if deliverable_name in seen_names:
                # 名称重复，添加后缀区分
                seen_names[deliverable_name] += 1
                # 从 owner_role 中提取专家标识作为后缀
                import re

                suffix_match = re.search(r"(\d+-\d+)$", owner_role)
                if suffix_match:
                    deliverable_name = f"{deliverable_name} ({suffix_match.group(1)})"
                else:
                    deliverable_name = f"{deliverable_name} ({seen_names[deliverable_name]})"
                logger.debug(f" [v7.154] 交付物名称去重: {metadata.get('name')} -> {deliverable_name}")
            else:
                seen_names[deliverable_name] = 1

            deliverable_answer = {
                "deliverable_id": deliverable_id,
                "deliverable_name": deliverable_name,
                "deliverable_type": metadata.get("type", "unknown"),
                "owner_role": owner_role,
                "owner_answer": owner_answer,
                "answer_summary": answer_summary,
                "supporters": metadata.get("supporters", []),
                "quality_score": quality_score,
                "concept_images": concept_images,  #  v7.108: 关联概念图
            }

            deliverable_answers.append(deliverable_answer)
            logger.info(f" 提取 {deliverable_id} 答案: owner={owner_role}, 长度={len(owner_answer)}")

        # 2. 构建专家支撑链（非owner专家的贡献）
        state.get("active_agents", [])
        for role_id in agent_results.keys():
            # 跳过需求分析师、项目总监和已作为owner的专家
            if role_id in ["requirements_analyst", "project_director"]:
                continue
            if role_id in owners_set:
                continue
            if not any(role_id.startswith(prefix) for prefix in ["V2_", "V3_", "V4_", "V5_", "V6_"]):
                continue

            agent_result = agent_results.get(role_id, {})
            if not agent_result:
                continue

            # 提取贡献信息
            contribution = self._extract_supporter_contribution(role_id, agent_result, deliverable_metadata)
            if contribution:
                expert_support_chain.append(contribution)

        # 3. 按依赖顺序排序支撑链（V4 → V3 → V5 → V6 → V2）
        tier_order = {"V4_": 1, "V3_": 2, "V5_": 3, "V6_": 4, "V2_": 5}
        expert_support_chain.sort(
            key=lambda x: min(
                (tier_order.get(prefix, 99) for prefix in tier_order if x.get("role_id", "").startswith(prefix)),
                default=99,
            )
        )

        # 4. 生成向后兼容字段
        question = structured_requirements.get("project_task") or user_input[:200] if user_input else "待定"
        deliverables_list = [d.get("deliverable_name", d.get("deliverable_id")) for d in deliverable_answers]
        answer_summary = self._generate_combined_summary(deliverable_answers)

        #  v7.154: 增强 timeline 和 budget 提取逻辑
        # 优先级：顶层字段 > constraints 子字段 > 默认值
        timeline = structured_requirements.get("timeline")
        if not timeline or timeline == "待定":
            constraints = structured_requirements.get("constraints", {})
            if isinstance(constraints, dict):
                timeline = constraints.get("timeline") or constraints.get("project_timeline")
        if not timeline or timeline in ["待定", "未明确", "N/A", None]:
            timeline = "请参考专家报告中的实施规划"

        budget_range = structured_requirements.get("budget_range")
        if not budget_range or budget_range == "待定":
            constraints = structured_requirements.get("constraints", {})
            if isinstance(constraints, dict):
                budget_range = constraints.get("budget") or constraints.get("budget_range")
        if not budget_range or budget_range in ["待定", "未明确", "N/A", None]:
            budget_range = "请参考专家报告中的成本估算"

        result = {
            "deliverable_answers": deliverable_answers,
            "expert_support_chain": expert_support_chain,
            "question": question,
            "answer": answer_summary,
            "deliverables": deliverables_list,
            "timeline": timeline if isinstance(timeline, str) else "请参考专家报告中的实施规划",
            "budget_range": budget_range if isinstance(budget_range, str) else "请参考专家报告中的成本估算",
        }

        logger.info(f" [v7.0] 提取完成: {len(deliverable_answers)} 个交付物答案, {len(expert_support_chain)} 个支撑专家")
        return result


    def _find_owner_result(self, agent_results: Dict[str, Any], owner_role: str) -> Dict[str, Any] | None:
        """
        在 agent_results 中查找匹配的专家输出

        owner_role 可能是完整描述如 "V2_高净值住宅空间与个性化设计总规划师_2-1"
        agent_results key 可能是 "V2_设计总监_2-1"

        匹配策略（按优先级）：
        1. 精确匹配
        2. 后缀匹配（如 "2-1"）- 最可靠，因为后缀是唯一标识符
        3. 前缀匹配（如 "V2_"）- 作为兜底

         v7.154: 增强匹配逻辑，支持动态角色名称与简化角色名称的匹配
        """
        import re

        # 1. 精确匹配
        if owner_role in agent_results:
            return agent_results[owner_role]

        # 2. 后缀匹配（提取 "2-1" 这样的后缀）
        # owner_role 格式: "V2_高净值住宅空间与个性化设计总规划师_2-1"
        # agent_results key 格式: "V2_设计总监_2-1"
        suffix_match = re.search(r"(\d+-\d+)$", owner_role)
        if suffix_match:
            suffix = suffix_match.group(1)  # 如 "2-1"
            tier_prefix = owner_role.split("_")[0] if "_" in owner_role else ""  # 如 "V2"

            for key in agent_results.keys():
                # 检查 key 是否以相同后缀结尾，且前缀匹配
                if key.endswith(f"_{suffix}") or key.endswith(f"-{suffix}"):
                    # 确保层级前缀也匹配（V2 匹配 V2，不匹配 V3）
                    key_prefix = key.split("_")[0] if "_" in key else ""
                    if tier_prefix and key_prefix == tier_prefix:
                        logger.debug(f" [v7.154] 后缀匹配成功: {owner_role} -> {key} (suffix={suffix})")
                        return agent_results[key]

        # 3. 前缀匹配（如 V2_）- 作为兜底
        parts = owner_role.split("_")
        if len(parts) >= 1:
            tier_prefix = parts[0]  # V2, V3, V4 等

            # 查找以此前缀开头的专家
            for key in agent_results.keys():
                if key.startswith(f"{tier_prefix}_"):
                    logger.debug(f" [v7.154] 前缀匹配成功: {owner_role} -> {key} (prefix={tier_prefix})")
                    return agent_results[key]

        logger.warning(f"️ [v7.154] 未找到匹配的专家: {owner_role}")
        return None


    def _extract_owner_deliverable_output(self, owner_result: Dict[str, Any], deliverable_id: str) -> str:
        """
        从责任者输出中提取针对特定交付物的答案

        优先顺序：
        1. structured_data.task_execution_report.deliverable_outputs 中匹配的内容
        2. structured_output.task_results 中匹配 deliverable_id 的内容
        3. structured_data 中的主要内容
        4. analysis 或 content 字段

         v7.6: 增强处理嵌套 JSON 字符串和重复内容
        """
        if not owner_result:
            return "暂无输出"

        #  v7.6: 优先从 structured_data.task_execution_report.deliverable_outputs 提取
        structured_data = owner_result.get("structured_data", {})
        if structured_data and isinstance(structured_data, dict):
            task_execution_report = structured_data.get("task_execution_report", {})
            if task_execution_report and isinstance(task_execution_report, dict):
                deliverable_outputs = task_execution_report.get("deliverable_outputs", [])
                if deliverable_outputs and isinstance(deliverable_outputs, list):
                    for output in deliverable_outputs:
                        if not isinstance(output, dict):
                            continue
                        output_name = output.get("deliverable_name", "")
                        content = output.get("content", "")

                        if content:
                            #  处理嵌套 JSON 字符串（LLM 可能返回 markdown 代码块）
                            cleaned_content = self._clean_nested_json_content(content)
                            if cleaned_content:
                                logger.debug(f" 从 deliverable_outputs 提取内容: {output_name[:30]}")
                                return cleaned_content

        # 尝试从 TaskOrientedExpertOutput 结构中提取
        structured_output = owner_result.get("structured_output", {})
        if structured_output and isinstance(structured_output, dict):
            task_results = structured_output.get("task_results", [])
            for task in task_results:
                if task.get("deliverable_id") == deliverable_id:
                    content = task.get("content", "")
                    if content:
                        return self._clean_nested_json_content(content)

            # 如果没有匹配的 deliverable_id，返回第一个 task 的内容
            if task_results:
                first_task = task_results[0]
                content = first_task.get("content", "")
                if content:
                    return self._clean_nested_json_content(content)

        # 从 structured_data 中提取核心输出字段
        if structured_data and isinstance(structured_data, dict):
            # 尝试提取核心输出字段
            for key in ["core_output", "deliverable_output", "main_content", "analysis_result", "recommendation"]:
                if key in structured_data:
                    value = structured_data[key]
                    if isinstance(value, str) and value:
                        return self._clean_nested_json_content(value)
                    elif isinstance(value, dict):
                        return self._format_dict_as_readable(value)

            #  v7.6: 不再将整个 structured_data 作为 JSON 返回
            # 而是尝试提取有意义的内容
            # 跳过元数据字段
            skip_keys = {"protocol_execution", "execution_metadata", "task_completion_summary", "content"}
            meaningful_data = {k: v for k, v in structured_data.items() if k not in skip_keys and v}
            if meaningful_data:
                return self._format_dict_as_readable(meaningful_data)

        # 回退到 analysis 或 content 字段
        analysis = owner_result.get("analysis", "")
        if analysis:
            return self._clean_nested_json_content(analysis)

        content = owner_result.get("content", "")
        if content:
            return self._clean_nested_json_content(content)

        return "暂无输出"


    def _clean_nested_json_content(self, content: Any) -> str:
        """
        清理嵌套的 JSON 内容

        处理 LLM 返回的 markdown 代码块包裹的 JSON，
        提取实际有意义的内容而不是原始 JSON 字符串
        """
        if not content:
            return ""

        # 如果是字典或列表，转换为可读格式
        if isinstance(content, dict | list):
            return self._format_dict_as_readable(content)

        # 如果是字符串
        if isinstance(content, str):
            text = content.strip()

            # 移除 markdown 代码块包裹
            if text.startswith("```json"):
                text = text[7:]
            elif text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            # 尝试解析为 JSON
            if text.startswith("{") or text.startswith("["):
                try:
                    parsed = json.loads(text)
                    # 如果解析成功，检查是否包含嵌套的 task_execution_report
                    if isinstance(parsed, dict):
                        # 提取有意义的内容
                        if "task_execution_report" in parsed:
                            ter = parsed["task_execution_report"]
                            if isinstance(ter, dict) and "deliverable_outputs" in ter:
                                outputs = ter["deliverable_outputs"]
                                if outputs and isinstance(outputs, list):
                                    # 递归提取第一个交付物的内容
                                    first_output = outputs[0]
                                    if isinstance(first_output, dict):
                                        inner_content = first_output.get("content", "")
                                        if inner_content:
                                            return self._clean_nested_json_content(inner_content)
                        # 格式化为可读内容
                        return self._format_dict_as_readable(parsed)
                    elif isinstance(parsed, list):
                        return self._format_dict_as_readable(parsed)
                except json.JSONDecodeError:
                    pass

            # 返回清理后的文本
            return text

        return str(content)


    def _format_dict_as_readable(self, data: Any, indent: int = 0) -> str:
        """
        将字典/列表格式化为人类可读的 Markdown 格式
        而不是原始 JSON
        """
        if data is None:
            return ""

        lines = []
        prefix = "  " * indent

        if isinstance(data, dict):
            for key, value in data.items():
                # 跳过元数据字段
                if key in {
                    "completion_status",
                    "completion_rate",
                    "quality_self_assessment",
                    "notes",
                    "protocol_status",
                    "compliance_confirmation",
                    "challenge_details",
                    "reinterpretation",
                    "confidence",
                    "execution_time_estimate",
                    "execution_notes",
                    "dependencies_satisfied",
                }:
                    continue

                # 格式化键名
                readable_key = key.replace("_", " ").title()

                if isinstance(value, dict):
                    lines.append(f"{prefix}**{readable_key}**:")
                    lines.append(self._format_dict_as_readable(value, indent + 1))
                elif isinstance(value, list):
                    lines.append(f"{prefix}**{readable_key}**:")
                    for item in value:
                        if isinstance(item, dict):
                            lines.append(self._format_dict_as_readable(item, indent + 1))
                        else:
                            lines.append(f"{prefix}  - {item}")
                elif value:
                    lines.append(f"{prefix}**{readable_key}**: {value}")
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    lines.append(self._format_dict_as_readable(item, indent))
                    lines.append("")  # 空行分隔
                else:
                    lines.append(f"{prefix}- {item}")
        else:
            lines.append(f"{prefix}{data}")

        return "\n".join(lines)


    def _extract_quality_score(self, owner_result: Dict[str, Any]) -> float | None:
        """从专家输出中提取质量分数"""
        if not owner_result:
            return None

        # 从 structured_output 提取
        structured_output = owner_result.get("structured_output", {})
        if structured_output and isinstance(structured_output, dict):
            # 从 protocol_execution 提取
            protocol_execution = structured_output.get("protocol_execution", {})
            if protocol_execution:
                confidence = protocol_execution.get("confidence_level")
                if confidence is not None:
                    try:
                        return float(confidence) * 100  # 转换为百分制
                    except (TypeError, ValueError):
                        pass

            # 从 task_results 提取
            task_results = structured_output.get("task_results", [])
            if task_results:
                completeness_scores = [
                    t.get("completeness_score", 0)
                    for t in task_results
                    if isinstance(t.get("completeness_score"), int | float)
                ]
                if completeness_scores:
                    return sum(completeness_scores) / len(completeness_scores) * 100

        # 从 confidence 字段提取
        confidence = owner_result.get("confidence")
        if confidence is not None:
            try:
                return float(confidence) * 100
            except (TypeError, ValueError):
                pass

        return None


    def _generate_answer_summary(self, full_answer: str) -> str:
        """生成答案摘要（200字以内）"""
        if not full_answer or full_answer == "暂无输出":
            return "暂无摘要"

        # 简单截取前200字
        if len(full_answer) <= 200:
            return full_answer

        # 尝试在句子边界截断
        truncated = full_answer[:200]
        last_period = max(truncated.rfind("。"), truncated.rfind("！"), truncated.rfind("？"))
        if last_period > 100:
            return truncated[: last_period + 1]

        return truncated + "..."


    def _generate_combined_summary(self, deliverable_answers: List[Dict[str, Any]]) -> str:
        """生成多交付物的综合摘要（向后兼容用）"""
        if not deliverable_answers:
            return "暂无核心答案"

        summaries = []
        for da in deliverable_answers:
            name = da.get("deliverable_name", da.get("deliverable_id", "未知"))
            summary = da.get("answer_summary", "")
            if summary:
                summaries.append(f"【{name}】{summary}")

        if not summaries:
            return "暂无核心答案"

        return " ".join(summaries)


    def _extract_supporter_contribution(
        self, role_id: str, agent_result: Dict[str, Any], deliverable_metadata: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        """提取支撑专家的贡献信息"""
        if not agent_result:
            return None

        # 确定角色名称
        role_name = agent_result.get("role_name", role_id)

        # 提取贡献摘要
        analysis = agent_result.get("analysis", "")
        content = agent_result.get("content", "")
        contribution_text = analysis or content or ""

        if not contribution_text:
            structured_data = agent_result.get("structured_data", {})
            if structured_data:
                contribution_text = json.dumps(structured_data, ensure_ascii=False)[:500]

        if not contribution_text:
            return None

        # 生成摘要
        contribution_summary = contribution_text[:200] + "..." if len(contribution_text) > 200 else contribution_text

        # 确定关联的交付物
        related_deliverables = []
        for d_id, d_meta in deliverable_metadata.items():
            supporters = d_meta.get("supporters", [])
            if any(
                role_id.startswith(s.split("_")[0] + "_" + s.split("_")[1]) if len(s.split("_")) >= 2 else s == role_id
                for s in supporters
            ):
                related_deliverables.append(d_id)

        return {
            "role_id": role_id,
            "role_name": role_name,
            "contribution_type": "support",
            "contribution_summary": contribution_summary,
            "related_deliverables": related_deliverables,
        }


    def _consolidate_search_references(self, state: ProjectAnalysisState) -> List[Dict[str, Any]]:
        """
         v7.122: 统一处理搜索引用，确保数据完整性和一致性

        功能：
        1. 从 state 中提取 search_references
        2. 容错处理（处理 None 或空列表）
        3. 去重（基于 title + url）
        4. 按质量分数排序
        5. 验证必需字段

        Args:
            state: 项目分析状态

        Returns:
            处理后的搜索引用列表
        """
        # 1. 提取搜索引用（容错处理）
        raw_references = state.get("search_references") or []

        if not raw_references:
            logger.debug("ℹ️ [v7.122] 无搜索引用数据")
            return []

        if not isinstance(raw_references, list):
            logger.warning(f"️ [v7.122] search_references 类型错误: {type(raw_references)}")
            return []

        logger.info(f" [v7.122] 开始处理 {len(raw_references)} 条原始搜索引用")

        # 2. 去重（基于 title + url）
        unique_references = []
        seen = set()

        for ref in raw_references:
            if not isinstance(ref, dict):
                logger.warning(f"️ [v7.122] 跳过非字典引用: {type(ref)}")
                continue

            # 验证必需字段
            if not ref.get("title"):
                logger.warning("️ [v7.122] 跳过缺少标题的引用")
                continue

            # 去重键
            title = ref.get("title", "")
            url = ref.get("url", "")
            key = (title, url)

            if key in seen:
                logger.debug(f"️ [v7.122] 跳过重复引用: {title}")
                continue

            seen.add(key)
            unique_references.append(ref)

        logger.info(f" [v7.122] 去重后: {len(unique_references)} 条唯一引用")

        # 3. 按质量分数排序（如果有）
        def get_quality_score(ref: Dict[str, Any]) -> float:
            """提取质量分数，支持多种格式"""
            # 优先使用 quality_score
            if "quality_score" in ref and ref["quality_score"] is not None:
                try:
                    return float(ref["quality_score"])
                except (TypeError, ValueError):
                    pass

            # 次选 relevance_score
            if "relevance_score" in ref and ref["relevance_score"] is not None:
                try:
                    return float(ref["relevance_score"]) * 100  # 转换为 0-100 范围
                except (TypeError, ValueError):
                    pass

            # 默认分数
            return 50.0

        try:
            sorted_references = sorted(unique_references, key=get_quality_score, reverse=True)  # 高分在前
            logger.debug(" [v7.122] 已按质量分数排序")
        except Exception as e:
            logger.warning(f"️ [v7.122] 排序失败，保持原顺序: {e}")
            sorted_references = unique_references

        # 4. 添加引用编号（如果没有）
        for idx, ref in enumerate(sorted_references, 1):
            if "reference_number" not in ref:
                ref["reference_number"] = idx

        logger.info(f" [v7.122] 搜索引用处理完成: {len(sorted_references)} 条")

        return sorted_references
