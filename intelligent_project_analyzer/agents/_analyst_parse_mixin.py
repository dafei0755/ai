"""
需求分析师 解析/结构化 Mixin
由 scripts/refactor/_split_mt14_analyst.py 自动生成 (MT-14)
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from langchain_core.runnables import RunnableConfig
    from langgraph.store.base import BaseStore
    from ..workflow.state import ProjectAnalysisState


class AnalystParseMixin:
    """Mixin — 需求分析师 解析/结构化 Mixin"""
    def _parse_requirements(self, llm_response: str) -> Dict[str, Any]:
        """解析LLM响应中的结构化需求 - 支持v1.0格式 - v3.6修复JSON解析"""
        try:
            #  v3.6优化：使用多种方法提取JSON，防止内容截断
            json_str = None

            # 方法1: 尝试提取JSON代码块（支持markdown code fence）
            import re
            json_pattern = r'```json\s*\n(.*?)\n```'
            match = re.search(json_pattern, llm_response, re.DOTALL)
            if match:
                json_str = match.group(1)
                logger.info("[JSON解析]  使用code fence提取")

            # 方法2: 尝试提取 ```{ ... }``` 格式（无json标记）
            if not json_str:
                code_block_pattern = r'```\s*\n(\{.*?\})\n```'
                match = re.search(code_block_pattern, llm_response, re.DOTALL)
                if match:
                    json_str = match.group(1)
                    logger.info("[JSON解析]  使用无标记代码块提取")

            # 方法3: 使用栈匹配法找到完整JSON（平衡大括号）
            if not json_str:
                json_str = self._extract_balanced_json(llm_response)
                if json_str:
                    logger.info("[JSON解析]  使用平衡括号提取")

            # 方法4:  尝试查找最大的JSON对象（从第一个{到最后一个}）
            if not json_str:
                first_brace = llm_response.find('{')
                last_brace = llm_response.rfind('}')
                if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
                    json_candidate = llm_response[first_brace:last_brace+1]
                    # 尝试解析验证
                    try:
                        json.loads(json_candidate)
                        json_str = json_candidate
                        logger.info("[JSON解析]  使用首尾括号提取并验证成功")
                    except Exception:
                        logger.warning("[JSON解析] ️ 首尾括号提取验证失败")

            # 如果所有方法都失败
            if not json_str:
                logger.warning("[JSON解析] ️ 所有提取方法失败，使用fallback")
                logger.debug(f"[JSON解析] LLM响应前200字符: {llm_response[:200]}")
                logger.debug(f"[JSON解析] LLM响应后200字符: {llm_response[-200:]}")
                #  v3.6调试：保存完整响应以便分析
                try:
                    import os
                    from datetime import datetime
                    debug_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "debug")
                    os.makedirs(debug_dir, exist_ok=True)
                    debug_file = os.path.join(debug_dir, f"llm_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(llm_response)
                    logger.info(f"[JSON解析] 完整LLM响应已保存到: {debug_file}")
                except Exception as save_error:
                    logger.warning(f"[JSON解析] 无法保存调试文件: {save_error}")

            if json_str:
                structured_data = json.loads(json_str)
                logger.info(f"[JSON解析]  成功解析，包含 {len(structured_data)} 个字段")
            else:
                # 如果没有找到JSON，创建基础结构
                structured_data = self._create_fallback_structure(llm_response)

            # 验证新格式的必需字段
            new_format_fields = [
                "project_task", "character_narrative", "space_constraints",
                "inspiration_references", "experience_behavior", "core_tension"
            ]

            # 检查是否是新格式
            is_new_format = any(field in structured_data for field in new_format_fields)

            if is_new_format:
                # 新格式（v2.0）：验证并填充缺失字段
                for field in new_format_fields:
                    if field not in structured_data:
                        structured_data[field] = "待进一步分析"

                #  v7.3: 问卷生成已分离，此处不再验证和修正问卷
                # 原因：问卷应在深度分析完成后，由专门节点基于分析结果动态生成
                # 旧逻辑（_validate_and_fix_questionnaire）已弃用，问卷生成移至 calibration_questionnaire.py

                # 向后兼容：如果存在旧问卷字段，保留但标记
                if "calibration_questionnaire" in structured_data:
                    logger.info("ℹ️ 检测到旧问卷字段，将由专门节点重新生成")
                    structured_data["calibration_questionnaire"]["source"] = "to_be_regenerated"

                #  v7.2: 构建完整的6字段数据结构（用于前端展示）
                # 从旧字段映射到新字段，确保前端能正确显示所有内容
                project_task = structured_data.get("project_task", "")
                character_narrative = structured_data.get("character_narrative", "")
                physical_context = structured_data.get("physical_context", "")
                resource_constraints = structured_data.get("resource_constraints", "")
                regulatory_requirements = structured_data.get("regulatory_requirements", "")
                
                # 1. project_overview: 项目概览（直接使用 project_task）
                structured_data["project_overview"] = project_task
                
                # 2. core_objectives: 核心目标（从 project_task 提取，或使用 design_goals）
                design_goals = structured_data.get("design_goals", "")
                if design_goals and len(design_goals) > 20:
                    # 如果有 design_goals，按句号分割为列表
                    goals_list = [g.strip() for g in design_goals.split('。') if g.strip() and len(g.strip()) > 5]
                    structured_data["core_objectives"] = goals_list[:5]  # 最多5个目标
                elif project_task and len(project_task) > 50:
                    # 从 project_task 提取核心目标
                    core_obj = project_task[:80].strip()
                    if '，' in core_obj or '。' in core_obj:
                        core_obj = core_obj.split('，')[0].split('。')[0]
                    structured_data["core_objectives"] = [core_obj]
                else:
                    structured_data["core_objectives"] = [project_task] if project_task else []
                
                # 3. project_tasks: 项目任务（从 project_task 提取关键词，或使用 functional_requirements）
                functional_req = structured_data.get("functional_requirements", "")
                if functional_req and len(functional_req) > 20:
                    # 按句号/分号分割功能需求为任务列表
                    tasks_list = [t.strip() for t in functional_req.replace('；', '。').split('。') if t.strip() and len(t.strip()) > 5]
                    structured_data["project_tasks"] = tasks_list[:8]  # 最多8个任务
                else:
                    # 默认从 project_task 提取一个任务
                    structured_data["project_tasks"] = [project_task] if project_task else []
                
                # 4. narrative_characters: 叙事角色（从 character_narrative 分段提取）
                if character_narrative and len(character_narrative) > 20:
                    # 按 "→" 或 "、" 分割人物叙事
                    if '→' in character_narrative:
                        char_list = [c.strip() for c in character_narrative.split('→') if c.strip()]
                        structured_data["narrative_characters"] = char_list[:6]  # 最多6个阶段
                    elif '、' in character_narrative:
                        char_list = [c.strip() for c in character_narrative.split('、') if c.strip()]
                        structured_data["narrative_characters"] = char_list[:6]
                    else:
                        # 整段作为一个角色描述
                        structured_data["narrative_characters"] = [character_narrative]
                else:
                    structured_data["narrative_characters"] = [character_narrative] if character_narrative else []
                
                # 5. physical_contexts: 物理环境（从 physical_context 分句提取）
                if physical_context and len(physical_context) > 20:
                    # 按逗号/句号分割物理环境
                    context_list = [c.strip() for c in physical_context.replace('，', '。').split('。') if c.strip() and len(c.strip()) > 5]
                    structured_data["physical_contexts"] = context_list[:6]  # 最多6个环境
                else:
                    structured_data["physical_contexts"] = [physical_context] if physical_context else []
                
                # 6. constraints_opportunities: 约束与机遇（结构化对象）
                space_constraints = structured_data.get("space_constraints", "")
                core_tension = structured_data.get("core_tension", "")
                design_challenge = structured_data.get("design_challenge", "")
                inspiration_refs = structured_data.get("inspiration_references", "")
                
                # 约束类字段（按重要性分句）
                constraints_parts = []
                if resource_constraints:
                    constraints_parts.append(f"资源约束：{resource_constraints}")
                if regulatory_requirements:
                    constraints_parts.append(f"规范要求：{regulatory_requirements}")
                if space_constraints:
                    constraints_parts.append(f"空间约束：{space_constraints}")
                if core_tension:
                    constraints_parts.append(f"核心矛盾：{core_tension}")
                
                # 机遇类字段
                opportunities_parts = []
                if design_challenge:
                    opportunities_parts.append(f"设计挑战：{design_challenge}")
                if inspiration_refs:
                    opportunities_parts.append(f"灵感参考：{inspiration_refs}")
                
                structured_data["constraints_opportunities"] = {
                    "constraints": constraints_parts if constraints_parts else ["暂无明确约束"],
                    "opportunities": opportunities_parts if opportunities_parts else ["待发掘机遇"]
                }
                
                # 兼容旧格式：保留旧字段（用于其他可能依赖旧字段的模块）
                structured_data["target_users"] = character_narrative[:100].strip() if character_narrative else ""
                physical = physical_context
                resource = resource_constraints
                regulatory = regulatory_requirements
                combined_constraints = f"{physical} {resource} {regulatory}".strip()
                structured_data["constraints"] = {"description": combined_constraints}
            else:
                # 旧格式：验证旧字段
                old_format_fields = [
                    "project_overview", "core_objectives", "functional_requirements",
                    "target_users", "constraints"
                ]

                for field in old_format_fields:
                    if field not in structured_data:
                        structured_data[field] = "待进一步分析"

            self._normalize_jtbd_fields(structured_data)
            
            #  推断项目类型（用于本体论注入）
            project_type = self._infer_project_type(structured_data)
            structured_data["project_type"] = project_type
            
            return structured_data

        except json.JSONDecodeError as e:
            logger.error(f"[JSON解析]  JSONDecodeError: {str(e)}")
            logger.error(f"[JSON解析] 问题位置: line {e.lineno}, col {e.colno}")
            if json_str:
                # 显示错误前后的文本片段
                error_pos = getattr(e, 'pos', 0)
                start_pos = max(0, error_pos - 50)
                end_pos = min(len(json_str), error_pos + 50)
                logger.error(f"[JSON解析] 前后文本: ...{json_str[start_pos:end_pos]}...")
            logger.warning("[JSON解析] 使用fallback结构")
            return self._create_fallback_structure(llm_response)
        except Exception as e:
            logger.error(f"[JSON解析]  未知错误: {str(e)}")
            logger.warning("[JSON解析] 使用fallback结构")
            return self._create_fallback_structure(llm_response)

    def _extract_balanced_json(self, text: str) -> str | None:
        """
        使用栈匹配法提取完整的JSON对象

         v3.6新增：防止简单的find('{')和rfind('}')在遇到嵌套JSON或字符串中的大括号时失败

        Args:
            text: 包含JSON的文本

        Returns:
            完整的JSON字符串，如果未找到则返回None
        """
        start_idx = text.find('{')
        if start_idx == -1:
            return None

        stack = []
        in_string = False
        escape = False

        for i in range(start_idx, len(text)):
            ch = text[i]

            # 处理转义字符
            if escape:
                escape = False
                continue
            if ch == '\\':
                escape = True
                continue

            # 处理字符串状态（只在双引号时切换）
            if ch == '"':
                in_string = not in_string
                continue

            # 只在非字符串状态下处理括号
            if not in_string:
                if ch == '{':
                    stack.append(ch)
                elif ch == '}':
                    if stack:
                        stack.pop()
                    if not stack:  # 栈空，找到完整JSON
                        json_candidate = text[start_idx:i+1]
                        logger.info(f"[JSON解析] 平衡括号提取成功，长度: {len(json_candidate)} 字符")
                        return json_candidate

        logger.warning("[JSON解析] 未找到平衡的JSON结构")
        return None

    def _create_fallback_structure(self, content: str) -> Dict[str, Any]:
        """创建备用的结构化数据 - 支持新格式"""
        return {
            # 新格式字段
            "project_task": content[:500] + "..." if len(content) > 500 else content,
            "character_narrative": "待进一步分析核心人物特征",
            "physical_context": "待明确物理环境条件",
            "resource_constraints": "待明确资源限制",
            "regulatory_requirements": "待明确规范要求",
            "inspiration_references": "【待后续专家补齐】V4设计研究员将提供国际案例参考，V5场景专家将结合行业趋势补充灵感来源",
            "experience_behavior": "【待后续专家补齐】V3叙事专家将构建完整用户旅程，V5场景专家将细化典型使用场景",
            "design_challenge": "待识别设计挑战",
            "calibration_questionnaire": {
                "introduction": "以下问题旨在精准捕捉您在战术执行和美学表达层面的个人偏好",
                "questions": []
            },
            # 兼容旧格式字段
            "project_overview": content[:500] + "..." if len(content) > 500 else content,
            "core_objectives": ["基于用户描述的项目目标"],
            "functional_requirements": ["待详细分析"],
            "non_functional_requirements": {"performance": "待定义", "security": "待定义"},
            "target_users": "待识别",
            "use_cases": ["主要使用场景待分析"],
            "constraints": {"budget": "未明确", "timeline": "未明确", "technology": "未明确"},
            "assumptions": ["基于当前信息的假设"],
            "risks": ["待识别潜在风险"],
            "success_criteria": ["待定义成功标准"],
            "raw_analysis": content
        }

    def _normalize_jtbd_fields(self, structured_data: Dict[str, Any]) -> None:
        """将 JTBD 相关字段转换为自然语言，避免在 UI 中出现公式术语"""
        if not structured_data:
            return

        for field in ["project_task", "project_overview"]:
            value = structured_data.get(field)
            if isinstance(value, str):
                structured_data[field] = transform_jtbd_to_natural_language(value)

        core_objectives = structured_data.get("core_objectives")
        if isinstance(core_objectives, list):
            structured_data["core_objectives"] = [
                transform_jtbd_to_natural_language(obj) if isinstance(obj, str) else obj
                for obj in core_objectives
            ]

    def _infer_project_type(self, structured_data: Dict[str, Any]) -> str:
        """
        推断项目类型（用于本体论注入）
        
        根据需求内容中的关键词匹配，识别项目类型：
        - personal_residential: 个人/家庭住宅类项目
        - hybrid_residential_commercial: 混合型（住宅+商业）
        - commercial_enterprise: 纯商业/企业级项目
        
        Returns:
            项目类型标识字符串
        """
        # 提取所有文本内容进行关键词匹配
        all_text = " ".join([
            str(structured_data.get("project_task", "")),
            str(structured_data.get("character_narrative", "")),
            str(structured_data.get("project_overview", "")),
            str(structured_data.get("target_users", "")),
        ]).lower()
        
        # 定义关键词集合（按优先级）
        personal_keywords = [
            "住宅", "家", "公寓", "别墅", "房子", "居住", "卧室", "客厅", 
            "家庭", "个人", "私宅", "家居", "户型", "住房", "民宿"
        ]
        
        commercial_keywords = [
            # 办公类
            "办公", "商业", "企业", "公司", "写字楼", "工作室", "创意园", "产业园", "厂房", "仓储", "品牌", "连锁",
            # 零售/展示类
            "店铺", "商店", "展厅", "零售", "购物", "商场", "专卖店", "旗舰店", "体验店",
            # 餐饮类
            "餐厅", "餐饮", "中餐", "西餐", "日料", "包房", "包间", "宴会厅", "食堂", "茶餐厅",
            "咖啡", "咖啡厅", "咖啡馆", "茶室", "茶馆", "酒吧", "清吧",
            # 住宿/会所类
            "酒店", "宾馆", "民宿", "会所", "俱乐部", "会议室",
            #  公共/市政类（城市更新、菜市场等）
            "菜市场", "市场", "农贸市场", "集市", "城市更新", "旧改", "改造", "公共空间",
            "社区中心", "文化中心", "活动中心", "体育馆", "图书馆", "博物馆", "美术馆",
            "标杆", "示范", "地标", "城市名片",
            #  文化/体验类
            "文化", "传统", "渔村", "历史", "遗产", "非遗", "民俗", "在地文化",
            #  教育/医疗/健康类
            "学校", "教育", "培训", "幼儿园", "早教", "托育",
            "医院", "诊所", "医疗", "养老院", "康养", "健康中心", "体检中心", "康复中心",
            "健康管理", "健康", "医美", "理疗", "养生", "保健",
            #  商业运营类（强烈表明是商业项目）
            "经营", "运营", "市场营销", "营销", "用户体验", "商业模式", "盈利"
        ]
        
        # 统计关键词命中数
        personal_score = sum(1 for kw in personal_keywords if kw in all_text)
        commercial_score = sum(1 for kw in commercial_keywords if kw in all_text)
        
        logger.info(f"[项目类型推断] 个人/住宅得分: {personal_score}, 商业/企业得分: {commercial_score}")
        
        # 判定逻辑
        if personal_score > 0 and commercial_score > 0:
            # 同时包含住宅和商业关键词
            logger.info("[项目类型推断] 识别为混合型项目 (hybrid_residential_commercial)")
            return "hybrid_residential_commercial"
        elif personal_score > commercial_score:
            # 主要是住宅类关键词
            logger.info("[项目类型推断] 识别为个人/住宅项目 (personal_residential)")
            return "personal_residential"
        elif commercial_score > personal_score:
            # 主要是商业类关键词
            logger.info("[项目类型推断] 识别为商业/企业项目 (commercial_enterprise)")
            return "commercial_enterprise"
        else:
            # 未命中任何关键词，返回 None（将触发 meta_framework）
            logger.warning("[项目类型推断] 无法识别项目类型，将使用通用框架 (meta_framework)")
            return None
    
    def _calculate_confidence(self, structured_data: Dict[str, Any]) -> float:
        """计算分析结果的置信度"""
        confidence_factors = []
        
        # 检查关键字段的完整性
        key_fields = ["project_overview", "core_objectives", "functional_requirements"]
        for field in key_fields:
            value = structured_data.get(field, "")
            if isinstance(value, str) and len(value) > 20:
                confidence_factors.append(0.3)
            elif isinstance(value, list) and len(value) > 0:
                confidence_factors.append(0.3)
            else:
                confidence_factors.append(0.1)
        
        # 检查详细程度
        total_content_length = sum(
            len(str(v)) for v in structured_data.values()
        )
        if total_content_length > 1000:
            confidence_factors.append(0.1)
        
        return min(sum(confidence_factors), 1.0)
    
    def _retrieve_user_preferences(self, store: BaseStore, config: RunnableConfig) -> str:
        """检索用户历史偏好"""
        try:
            user_id = config["configurable"]["user_id"]
            namespace = ("user_preferences", user_id)
            
            # 搜索相关的用户偏好
            memories = store.search(namespace, limit=5)
            
            if memories:
                preferences = []
                for memory in memories:
                    if "preference" in memory.value:
                        preferences.append(memory.value["preference"])
                
                return "\n".join(preferences) if preferences else ""
            
            return ""
            
        except Exception as e:
            logger.warning(f"Failed to retrieve user preferences: {str(e)}")
            return ""
    
    def _save_user_preferences(
        self,
        store: BaseStore,
        config: RunnableConfig,
        structured_requirements: Dict[str, Any]
    ):
        """保存用户偏好"""
        try:
            user_id = config["configurable"]["user_id"]
            namespace = ("user_preferences", user_id)
            
            # 提取可能的偏好信息
            preferences = []
            
            # 从目标用户中提取偏好
            target_users = structured_requirements.get("target_users", "")
            if target_users and len(target_users) > 10:
                preferences.append(f"目标用户偏好: {target_users}")
            
            # 从约束条件中提取偏好
            constraints = structured_requirements.get("constraints", {})
            if isinstance(constraints, dict):
                for key, value in constraints.items():
                    if value and value != "未明确" and value != "待定义":
                        preferences.append(f"{key}偏好: {value}")
            
            # 保存偏好
            for i, preference in enumerate(preferences):
                memory_id = f"req_analysis_{int(time.time())}_{i}"
                store.put(namespace, memory_id, {
                    "preference": preference,
                    "source": "requirements_analysis",
                    "timestamp": time.time()
                })
            
        except Exception as e:
            logger.warning(f"Failed to save user preferences: {str(e)}")

    # ═══════════════════════════════════════════════════════════════════════════
    #  v7.17 P1: 两阶段执行架构
    # Phase1: 快速定性 + 交付物识别 (~1.5s)
    # Phase2: 深度分析 + 专家接口构建 (~3s)
    # ═══════════════════════════════════════════════════════════════════════════

