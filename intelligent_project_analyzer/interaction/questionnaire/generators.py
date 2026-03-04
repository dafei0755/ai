"""
问卷生成器模块

提供各类问卷问题的生成逻辑，从 calibration_questionnaire.py 中提取。

v7.4 更新：
- FallbackQuestionGenerator：支持从用户输入提取关键词生成定制问题
- DomainSpecificQuestionGenerator：基于领域生成专业问题
- ConflictQuestionGenerator：冲突问题需由用户约束激活
"""

import re
from typing import Any, Dict, List

from loguru import logger

from .context import KeywordExtractor


class FallbackQuestionGenerator:
    """
    兜底问题生成器

    在缺失问卷时构建兜底问题集，确保问卷流程不会被跳过。
    应用智能补齐机制，确保生成 7-10个问题（而非旧版的4个）。

    v7.4 优化：
    - 支持从用户输入提取关键词生成定制问题
    - 支持领域识别，生成领域专业问题
    - 核心矛盾从用户输入中智能提取，而非使用通用模板

    原始位置: calibration_questionnaire.py L17-263
    """

    @staticmethod
    def generate(structured_data: Dict[str, Any], user_input: str = "", extracted_info: Dict | None = None) -> List[Dict[str, Any]]:
        """
        在缺失问卷时构建兜底问题集，确保问卷流程不会被跳过

         v7.4优化：
        - 支持从用户输入提取关键词生成定制问题
        - 核心矛盾从用户输入中智能提取
        - 领域专业问题优先于通用问题

        Args:
            structured_data: 需求分析师的结构化输出
            user_input: 用户原始输入（用于关键词提取）
            extracted_info: 预提取的关键信息（可选，避免重复提取）
        """

        #  v7.4: 智能提取关键信息
        if extracted_info is None and user_input:
            extracted_info = KeywordExtractor.extract(user_input, structured_data)
        elif extracted_info is None:
            extracted_info = KeywordExtractor._empty_result()

        # 获取提取的信息
        domain = extracted_info.get("domain", {})
        core_concepts = extracted_info.get("core_concepts", [])
        keywords = extracted_info.get("keywords", [])
        question_focus = extracted_info.get("question_focus", [])

        project_task = str(structured_data.get("project_task", "")).strip()
        character_narrative = str(structured_data.get("character_narrative", "")).strip()
        design_challenge = str(structured_data.get("design_challenge", "")).strip()
        core_tension = str(structured_data.get("core_tension", "")).strip()
        resource_constraints = str(structured_data.get("resource_constraints", "")).strip()
        project_type = str(structured_data.get("project_type", "")).strip()

        short_task = (
            project_task[:120] + ("..." if len(project_task) > 120 else "")
            if project_task else "当前项目"
        )
        tension_hint = (
            core_tension[:120] + ("..." if len(core_tension) > 120 else "")
            if core_tension else "展示与体验、功能与情绪之间的权衡"
        )

        #  v7.4: 使用领域标签
        domain_label = domain.get("label", "空间")
        type_label = {
            "personal_residential": "住宅空间",
            "hybrid_residential_commercial": "混合型空间",
            "commercial_enterprise": "商业项目"
        }.get(project_type or "", domain_label)

        #  v7.4优化：智能提取核心矛盾
        # 优先从用户输入的核心概念中提取，而非使用通用模板
        tension_a = ""
        tension_b = ""

        #  v7.4.4: 过滤无效的核心概念（系统生成的标题等）
        valid_concepts = [c for c in core_concepts if c and c not in {
            "用户需求描述", "附件材料", "附件", "说明", "摘要", "内容", 
            "背景资料", "参考信息", "明确要求", "背景信息", "项目背景"
        }]

        # 方法1: 从核心概念中提取对立面
        if len(valid_concepts) >= 2:
            # 尝试识别对立概念
            tension_a = valid_concepts[0]
            tension_b = valid_concepts[1]
            logger.info(f"[Fallback补齐] 从核心概念提取矛盾: \"{tension_a}\" vs \"{tension_b}\"")

        # 方法2: 从design_challenge中提取（原有逻辑）
        if not tension_a or not tension_b:
            if design_challenge:
                # 模式1: "A"...与..."B" 格式（中文双引号）
                match = re.search(r'"([^"]{2,30})"[^"]{0,50}与[^"]{0,50}"([^"]{2,30})"', design_challenge)
                if match:
                    tension_a = match.group(1).strip()
                    tension_b = match.group(2).strip()
                    logger.info(f"[Fallback补齐] 从design_challenge提取核心矛盾(双引号): \"{tension_a}\" vs \"{tension_b}\"")
                else:
                    #  模式1b: 'A'...与...'B' 格式（中文单引号/英文单引号）
                    match = re.search(r"'([^']{2,30})'[^']{0,50}与[^']{0,50}'([^']{2,30})'", design_challenge)
                    if match:
                        tension_a = match.group(1).strip()
                        tension_b = match.group(2).strip()
                        logger.info(f"[Fallback补齐] 从design_challenge提取核心矛盾(单引号): \"{tension_a}\" vs \"{tension_b}\"")
                    else:
                        # 模式2: A vs B 或 A与其对B 格式
                        match = re.search(r'(.{5,30}?)[的需求]*(?:vs|与其对)(.{5,30}?)[的需求]*', design_challenge)
                        if match:
                            tension_a = match.group(1).strip()
                            tension_b = match.group(2).strip()
                            logger.info(f"[Fallback补齐] 提取核心矛盾(模式2): {tension_a} vs {tension_b}")

        # 方法3: 从用户输入中提取引号内容
        if not tension_a or not tension_b:
            if user_input:
                #  v7.4.4: 支持多种引号格式
                # 优先尝试中文双引号
                quoted_matches = re.findall(r'"([^"]{2,20})"', user_input)
                # 如果没有，尝试单引号
                if len(quoted_matches) < 2:
                    single_matches = re.findall(r"'([^']{2,20})'", user_input)
                    quoted_matches.extend(single_matches)
                
                if len(quoted_matches) >= 2:
                    tension_a = quoted_matches[0]
                    tension_b = quoted_matches[1]
                    logger.info(f"[Fallback补齐] 从用户输入引号提取: \"{tension_a}\" vs \"{tension_b}\"")
                elif len(quoted_matches) == 1:
                    tension_a = quoted_matches[0]
                    logger.info(f"[Fallback补齐] 从用户输入提取单个概念: \"{tension_a}\"")

        # 方法4: 兜底使用通用矛盾（但尽量避免）
        if not tension_a:
            tension_a = "功能性需求"
        if not tension_b:
            tension_b = "情感化需求"
            logger.warning("[Fallback补齐] ️ 使用通用矛盾模板，建议优化用户输入解析")

        # 提取时间线索（从character_narrative中）
        time_hint = "一天"
        if character_narrative:
            if "早晨" in character_narrative or "清晨" in character_narrative:
                time_hint = "清晨"
            elif "夜晚" in character_narrative or "夜间" in character_narrative:
                time_hint = "夜晚"

        is_residential = "residential" in project_type
        is_commercial = "commercial" in project_type

        #  v7.4: 基于领域识别
        is_tech = domain.get("type") == "tech_innovation"
        is_hospitality = domain.get("type") == "hospitality"
        is_office = domain.get("type") == "office"

        #  生成完整的7-10个问题（按照YAML要求）
        questions = []

        # === 单选题部分（2-3个）===

        #  v7.4: 科技创新领域专用问题
        if is_tech and valid_concepts:
            # 科技领域：核心概念实现路径
            primary_concept = valid_concepts[0] if valid_concepts else "核心功能"
            questions.append({
                "id": "tech_core_concept",
                "question": f"对于'{primary_concept}'的实现，您更看重？(单选)",
                "context": f"这是{domain_label}项目的核心技术决策，将影响整体架构。",
                "type": "single_choice",
                "options": [
                    f"技术先进性：采用最前沿的方案实现'{primary_concept}'",
                    "成本可控性：选择成熟稳定的解决方案",
                    "可扩展性：预留未来升级和迭代空间",
                    "用户体验：优先保证使用者的直观感受"
                ]
            })

            # 如果有"迭代"、"数据"等关键词，生成专用问题
            keyword_names = [k[0] for k in keywords]
            if any(kw in keyword_names for kw in ["迭代", "敏捷", "模块化"]):
                questions.append({
                    "id": "tech_iteration_cycle",
                    "question": "关于空间的'可迭代'调整，您期望的响应周期是？(单选)",
                    "context": "这决定了模块化程度和技术复杂度的权衡。",
                    "type": "single_choice",
                    "options": [
                        "实时响应（分钟级）：空间能即时响应使用变化",
                        "日度调整（每天优化）：根据前一天数据优化布局",
                        "周期性重组（月度/季度）：定期大规模调整",
                        "按需触发：仅在特定事件时调整"
                    ]
                })

            if any(kw in keyword_names for kw in ["数据", "热力图", "传感器", "行为"]):
                questions.append({
                    "id": "tech_data_collection",
                    "question": "关于员工行为数据的采集方式，您倾向于？(单选)",
                    "context": "数据采集方式影响隐私保护和数据精度的平衡。",
                    "type": "single_choice",
                    "options": [
                        "被动采集：摄像头+AI视觉分析（高精度，需隐私保护）",
                        "环境感知：工位传感器+物联网（中等精度，低侵入）",
                        "主动反馈：员工APP/系统主动上报（低精度，高隐私）",
                        "混合方案：结合多种方式，分区域差异化采集"
                    ]
                })

        # 单选题1: 核心矛盾优先级（从用户输入提取）
        elif tension_a and tension_b and tension_a != "功能性需求":
            # 只有当提取到真正的核心矛盾时才使用
            questions.append({
                "id": "core_tension_priority",
                "question": f"当'{tension_a}'与'{tension_b}'产生冲突时，您更倾向于？(单选)",
                "context": "这是本项目最核心的战略选择，将决定设计的根本方向。",
                "type": "single_choice",
                "options": [
                    f"优先保证'{tension_a}'，可以在'{tension_b}'上做出妥协",
                    f"优先保证'{tension_b}'，'{tension_a}'可以通过其他方式补偿",
                    "寻求平衡点，通过创新设计同时满足两者"
                ]
            })
        else:
            #  v7.5: 优化兜底问题，使用更具体的设计维度
            # 根据项目类型选择不同的核心问题
            if is_residential:
                questions.append({
                    "id": "residential_priority",
                    "question": f"在这个{type_label}项目中，您更看重哪个方面？(单选)",
                    "context": "帮助我们确定设计的核心出发点：实用功能还是生活氛围。",
                    "type": "single_choice",
                    "options": [
                        "功能实用性：收纳充足、动线合理、使用便捷",
                        "生活氛围感：光影变化、空间层次、情感温度",
                        "两者平衡：在实用基础上追求氛围感"
                    ]
                })
            elif is_commercial:
                questions.append({
                    "id": "commercial_priority",
                    "question": f"在这个{type_label}项目中，您更看重哪个方面？(单选)",
                    "context": "帮助我们确定设计的核心出发点：运营效率还是品牌体验。",
                    "type": "single_choice",
                    "options": [
                        "运营效率：坪效最大化、动线优化、维护便捷",
                        "品牌体验：第一印象、情感连接、记忆点塑造",
                        "两者平衡：在保证效率基础上打造独特体验"
                    ]
                })
            else:
                questions.append({
                    "id": "general_priority",
                    "question": f"在这个{type_label}项目中，您更看重哪个方面？(单选)",
                    "context": "帮助我们确定设计的核心出发点：功能需求还是空间体验。",
                    "type": "single_choice",
                    "options": [
                        "功能优先：满足所有使用需求，确保空间效率",
                        "体验优先：打造独特的空间感受和氛围",
                        "两者平衡：在满足功能基础上追求体验升级"
                    ]
                })

        # 单选题2: 资源分配策略（基于resource_constraints）
        if resource_constraints:
            questions.append({
                "id": "resource_allocation",
                "question": f"面对{resource_constraints}的限制，您的取舍策略是？(单选)",
                "context": "帮助我们在资源有限时做出明智的优先级决策。",
                "type": "single_choice",
                "options": [
                    "集中资源打造核心体验区，其他区域从简",
                    "平均分配，确保整体协调统一",
                    "先满足基本功能，预留后期升级空间"
                ]
            })
        else:
            # 兜底：长期适应性问题
            questions.append({
                "id": "long_term_adaptability",
                "question": "关于空间的长期适应性，您更看重？(单选)",
                "context": "这关乎设计的灵活性与稳定性，帮助我们确定空间的可变性程度。",
                "type": "single_choice",
                "options": [
                    "灵活可变：随着生活变化而调整",
                    "稳定固定：一次设计到位，长期不变",
                    "模块化：核心固定，局部可调"
                ]
            })

        # === 多选题部分（2-3个）===

        #  v7.4: 科技创新领域专用多选题
        if is_tech:
            keyword_names = [k[0] for k in keywords] if keywords else []

            # 科技公司文化/空间特质
            questions.append({
                "id": "tech_culture_traits",
                "question": f"作为{domain_label}项目，以下哪些空间特质最能体现企业文化？(多选)",
                "context": "这将指导空间的功能分区和氛围营造。",
                "type": "multiple_choice",
                "options": [
                    "开放协作：无固定工位，随时组队讨论",
                    "深度专注：隔音舱/专注区，支持沉浸式工作",
                    "快速迭代：白板墙/原型区，支持快速验证想法",
                    "数据可视化：大屏展示区，实时呈现业务数据",
                    "休闲放松：游戏区/休息区，缓解工作压力",
                    "学习成长：图书角/培训室，支持持续学习"
                ]
            })

            # 如果涉及模块化/可迭代
            if any(kw in keyword_names for kw in ["模块化", "迭代", "重组", "调整"]):
                questions.append({
                    "id": "tech_modular_elements",
                    "question": "在'模块化设计系统'中，以下哪些元素需要支持快速重组？(多选)",
                    "context": "这决定了模块化设计的范围和复杂度。",
                    "type": "multiple_choice",
                    "options": [
                        "工位布局：支持团队规模变化",
                        "会议空间：支持不同规模会议需求",
                        "隔断系统：支持开放/封闭切换",
                        "家具配置：支持功能场景切换",
                        "照明系统：支持不同工作模式",
                        "声学环境：支持安静/协作切换"
                    ]
                })

        # 多选题1: 感官体验偏好（基于项目类型定制）
        elif is_residential:
            questions.append({
                "id": "sensory_experience",
                "question": "在日常使用中，以下哪些体验对您最重要？(多选)",
                "context": "这决定了我们在材质、光线、声音等方面的侧重点。",
                "type": "multiple_choice",
                "options": [
                    "视觉：光影变化和空间美感",
                    "触觉：材质的温润感和舒适度",
                    "听觉：安静或特定的声音氛围",
                    "嗅觉：自然或特定香氛",
                    "温度：恒温或季节变化"
                ]
            })
        elif is_commercial:
            questions.append({
                "id": "commercial_experience",
                "question": "在日常运营中，以下哪些体验对您最重要？(多选)",
                "context": "这直接影响商业空间的核心竞争力和运营效率。",
                "type": "multiple_choice",
                "options": [
                    "视觉冲击力：第一印象和品牌展示",
                    "动线流畅度：客户体验路径优化",
                    "功能灵活性：多场景适配能力",
                    "运营效率：坪效和服务响应速度",
                    "品牌氛围：情感连接和记忆点"
                ]
            })
        else:
            #  v7.5: 优化通用多选题，使用更具体的功能维度
            questions.append({
                "id": "general_experience",
                "question": "在日常使用中，以下哪些体验对您最重要？(多选)",
                "context": "帮助我们确定设计在感官和功能层面的侧重点。",
                "type": "multiple_choice",
                "options": [
                    "采光与通风：自然光充足、空气流通",
                    "视觉舒适度：色彩搭配、材质质感",
                    "声学环境：安静或适度的背景音",
                    "空间灵活性：可适应不同使用场景",
                    "易维护性：清洁方便、耐用持久"
                ]
            })

        # 多选题2: 功能配置优先级（基于项目类型定制）
        if is_residential:
            questions.append({
                "id": "functional_priority",
                "question": "在空间功能配置上，以下哪些是您不可妥协的？(多选)",
                "context": "帮助我们识别核心功能需求，确保关键体验不受影响。",
                "type": "multiple_choice",
                "options": [
                    "充足的储物空间",
                    "独立的工作区域",
                    "舒适的休息空间",
                    "社交接待功能",
                    "个人兴趣爱好空间"
                ]
            })
        elif is_commercial:
            questions.append({
                "id": "commercial_functional_priority",
                "question": "在空间功能配置上，以下哪些是您不可妥协的？(多选)",
                "context": "帮助我们识别核心功能需求，确保运营效率和客户体验。",
                "type": "multiple_choice",
                "options": [
                    "客户展示/体验区",
                    "核心功能操作区",
                    "员工支持服务区",
                    "储物/后勤保障区",
                    "品牌形象展示区"
                ]
            })
        else:
            #  v7.5: 优化通用功能优先级题，使用更具体的表达
            questions.append({
                "id": "space_allocation",
                "question": "在空间分配上，以下哪些区域是必须保证的？(多选)",
                "context": "帮助我们理解空间使用的核心需求，确保关键功能不被压缩。",
                "type": "multiple_choice",
                "options": [
                    "主要活动区：日常使用最频繁的核心空间",
                    "储物收纳区：保证物品有处可放",
                    "工作/学习区：需要专注的独立空间",
                    "休息放松区：身心恢复的舒适空间",
                    "社交接待区：可以招待朋友/客户的场所"
                ]
            })

        # 多选题3: 美学风格偏好（第三个多选题，确保问题数达到7-10）
        questions.append({
            "id": "aesthetic_preference",
            "question": "以下哪些美学特质最能代表您的理想空间？(多选)",
            "context": "帮助我们把握空间的整体风格方向和氛围营造。",
            "type": "multiple_choice",
            "options": [
                "简洁利落：少即是多的克制美学",
                "温润自然：材质和光线的柔和融合",
                "艺术张力：独特造型和视觉冲击",
                "精致细腻：细节打磨和品质感",
                "自由随性：不拘一格的个性表达"
            ]
        })

        # === 开放题部分（2个）===

        #  v7.4: 科技领域专用开放题
        if is_tech and valid_concepts:
            primary_concept = valid_concepts[0] if valid_concepts else "核心功能"
            questions.append({
                "id": "tech_ideal_scenario",
                "question": f"描述一个理想的'{primary_concept}'应用场景：什么触发了空间调整？调整了什么？员工感受如何？(开放题)",
                "context": "这将成为设计验证的'黄金标准'场景。",
                "type": "open_ended",
                "placeholder": "例如：周一早会后，系统检测到A组需要协作，自动将相邻工位合并为讨论区..."
            })

            questions.append({
                "id": "tech_success_criteria",
                "question": "如果这个空间设计成功，一年后您希望看到什么变化？(开放题)",
                "context": "明确成功标准，指导设计决策的优先级。",
                "type": "open_ended",
                "placeholder": "例如：员工满意度提升、协作效率提高、空间利用率优化..."
            })
        else:
            # 开放题1: 理想场景描述（基于时间线索定制）
            questions.append({
                "id": "signature_moment",
                "question": f"描述您理想中{time_hint}的生活场景：在哪、做什么、感受什么？(开放题)",
                "context": "这将成为设计的'黄金标准'场景，指导空间氛围和功能布局。",
                "type": "open_ended",
                "placeholder": f"例如：{time_hint}，在窗边的阅读角落，手捧一本书，感受阳光洒落..."
            })

            # 开放题2: 精神追求与灵感参考
            questions.append({
                "id": "inspiration_reference",
                "question": "有没有某个空间/场所/作品让您印象深刻或特别向往？请描述它打动您的特质。(开放题)",
                "context": "提取您对空间体验的精神追求，作为设计的灵感参考。",
                "type": "open_ended",
                "placeholder": "例如：某个咖啡馆、酒店、展览空间，或者电影/书籍中的场景..."
            })

        # 统计日志
        domain_info = f"领域({domain.get('label', '通用')})" if domain else "领域(通用)"
        logger.info(f"[Fallback补齐]  智能生成 {len(questions)} 个问题（单选:{sum(1 for q in questions if q['type']=='single_choice')} + 多选:{sum(1 for q in questions if q['type']=='multiple_choice')} + 开放:{sum(1 for q in questions if q['type']=='open_ended')}）")
        logger.info(f"[Fallback补齐]  提取策略: {domain_info}, 核心概念({core_concepts[:3]}), 项目类型({project_type})")

        return questions


class BiddingStrategyGenerator:
    """
    竞标策略问题生成器
    
    为竞标策略场景生成专用问题。
    核心逻辑：提取竞争对手信息，生成差异化优势、对手分析、品牌定位等战略问题。
    
    原始位置: calibration_questionnaire.py L266-391
    """
    
    @staticmethod
    def generate(user_input: str, structured_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
         P1优化：为竞标策略场景生成专用问题

        核心逻辑：
        - 提取竞争对手信息
        - 生成差异化优势、对手分析、品牌定位等战略问题
        - 问题聚焦于"如何在重量级对手中突围"

        Args:
            user_input: 用户原始输入
            structured_data: V1需求分析结果

        Returns:
            竞标策略专用问题列表
        """

        questions = []

        # 提取竞争对手信息
        competitors = []
        # 常见设计公司名称
        known_competitors = ["HBA", "CCD", "郑中设计", "杨邦胜", "刘波设计", "季裕棠", "琚斌", "YABU", "AB Concept"]
        for comp in known_competitors:
            if comp.lower() in user_input.lower():
                competitors.append(comp)

        # 提取项目名称
        project_name = ""
        project_match = re.search(r'([\u4e00-\u9fa5]+酒店|[\u4e00-\u9fa5]+项目)', user_input)
        if project_match:
            project_name = project_match.group(1)

        # 提取地点
        location = ""
        location_match = re.search(r'(成都|北京|上海|深圳|广州|杭州|南京|武汉|西安|重庆)', user_input)
        if location_match:
            location = location_match.group(1)

        logger.info(f" [P1] 竞标策略问题生成: 竞争对手={competitors}, 项目={project_name}, 地点={location}")

        # 问题1：差异化优势选择（单选）
        competitor_str = "、".join(competitors[:3]) if competitors else "重量级对手"
        questions.append({
            "id": "bidding_competitive_advantage",
            "question": f"面对{competitor_str}等重量级对手，您认为最有可能形成差异化优势的是？(单选)",
            "context": "这是竞标策略的核心选择，将决定方案的整体方向。",
            "type": "single_choice",
            "options": [
                "品牌叙事创新：讲一个对手没讲过的故事",
                f"在地文化深度：比对手更懂{location or '本地'}",
                "体验设计突破：创造独特的客户旅程",
                "可持续创新：ESG战略差异化",
                "技术赋能：智能化体验领先"
            ],
            "source": "p1_bidding_strategy",
            "priority": "high"
        })

        # 问题2：对手弱点识别（多选）
        questions.append({
            "id": "bidding_opponent_weakness",
            "question": "您认为这些大牌设计团队最可能的弱点是什么？(多选)",
            "context": "识别对手弱点是制定突围策略的关键。",
            "type": "multiple_choice",
            "options": [
                "过于依赖成功案例套路，缺乏创新",
                "国际视角强但在地文化理解不足",
                "设计精美但运营落地性考虑不够",
                "品牌调性高但成本控制能力弱",
                "团队规模大但响应速度慢",
                "其它（请补充）"
            ],
            "source": "p1_bidding_strategy",
            "priority": "high"
        })

        # 问题3：品牌定位倾向（单选）
        if project_name:
            questions.append({
                "id": "bidding_brand_positioning",
                "question": f"{project_name}的品牌定位，您倾向于？(单选)",
                "context": "品牌定位决定了设计语言和空间叙事的基调。",
                "type": "single_choice",
                "options": [
                    f"强调国际奢华标准，{location or '本地'}元素点缀",
                    f"深度融合{location or '本地'}文化，重新定义品牌",
                    f"创造全新品类：'新{location or '本地'}奢华'",
                    "其它（请详细说明）"
                ],
                "source": "p1_bidding_strategy",
                "priority": "high"
            })

        # 问题4：评委打动点（多选）
        questions.append({
            "id": "bidding_winning_factors",
            "question": "竞标评审中，您认为最能打动评委的是？(多选)",
            "context": "明确评委关注点，有助于聚焦方案表达。",
            "type": "multiple_choice",
            "options": [
                "设计创新突破：前所未见的空间体验",
                "战略洞察深刻：对市场和客户的深度理解",
                "落地可行性强：成本、工期、运营的周全考虑",
                "视觉呈现震撼：方案表达的专业度和感染力",
                "团队实力展示：过往案例和执行能力",
                "其它（请补充）"
            ],
            "source": "p1_bidding_strategy",
            "priority": "medium"
        })

        # 问题5：开放题 - 竞标故事
        questions.append({
            "id": "bidding_story_vision",
            "question": f"描述您理想中的'{project_name or '本项目'}故事'：如果用一句话打动评委，您会说什么？(开放题)",
            "context": "这将成为方案的核心叙事线索。",
            "type": "open_ended",
            "placeholder": "例如：让每一位入住者都能感受到成都的慢生活哲学...",
            "source": "p1_bidding_strategy",
            "priority": "medium"
        })

        logger.info(f" [P1] 竞标策略问题生成完成: {len(questions)} 个问题")
        return questions


class PhilosophyQuestionGenerator:
    """
    理念探索问题生成器
    
    基于V1战略洞察生成理念探索问题（理念维度增强）。
    问题关注为什么和如何理解，而非怎么做。
    
    原始位置: calibration_questionnaire.py L394-531
    """
    
    @staticmethod
    def generate(structured_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        基于V1战略洞察生成理念探索问题（ 理念维度增强）

        核心逻辑：
        - 基于design_challenge提取核心矛盾，生成理念选择问题
        - 基于expert_handoff.design_challenge_spectrum生成方案倾向问题
        - 基于project_task生成目标理念问题
        - 问题关注"为什么"和"如何理解"，而非"怎么做"

        Args:
            structured_data: V1需求分析师的输出

        Returns:
            理念探索问题列表（单选题+开放题）
        """
        
        logger.debug(" [TRACE] _build_philosophy_questions 开始执行")
        philosophy_questions = []

        # 提取V1的战略洞察数据
        design_challenge = structured_data.get("design_challenge", "")
        project_task = structured_data.get("project_task", "")
        expert_handoff = structured_data.get("expert_handoff", {})
        logger.debug(f" [TRACE] 数据提取完成: design_challenge长度={len(design_challenge)}, project_task长度={len(project_task)}")

        # 1. 基于design_challenge生成理念问题
        if design_challenge:
            logger.debug(" [TRACE] 处理 design_challenge...")
            # 提取核心矛盾 (格式: 作为[身份]的[需求A]与[需求B]的对立)
            # 限制正则匹配的字符串长度，避免潜在的性能问题
            safe_challenge = design_challenge[:500] if len(design_challenge) > 500 else design_challenge
            #  修复: 使用更简单的正则，避免灾难性回溯
            #  紧急修复: 改用贪婪匹配 + 更短的限制，避免挂起
            match = re.search(r'作为\[([^\]]{1,30})\]的\[([^\]]{1,30})\]与\[([^\]]{1,30})\]', safe_challenge)
            logger.debug(f" [TRACE] 正则匹配完成: match={bool(match)}")
            if match:
                identity = match.group(1)
                need_a = match.group(2)
                need_b = match.group(3)

                philosophy_questions.append({
                    "id": "v1_design_philosophy",
                    "question": f" 在'{need_a}'与'{need_b}'的矛盾中，您更认同哪种设计理念？(单选)",
                    "context": f"这个问题关乎您作为'{identity}'的核心价值取向，将深刻影响设计的精神内核。",
                    "type": "single_choice",
                    "options": [
                        f"优先{need_a}，这是我的根本追求",
                        f"优先{need_b}，这更符合实际需要",
                        "两者同等重要，寻求创新方案平衡",
                        "我还不确定，希望看到更多可能性"
                    ],
                    "source": "v1_strategic_insight",
                    "dimension": "philosophy"
                })

                logger.info(f" 基于design_challenge生成理念问题: {need_a} vs {need_b}")

        # 2. 基于expert_handoff.design_challenge_spectrum生成方案倾向问题
        design_spectrum = expert_handoff.get("design_challenge_spectrum", {})
        if design_spectrum:
            极端A = design_spectrum.get("极端A", {}).get("标签", "")
            极端B = design_spectrum.get("极端B", {}).get("标签", "")
            中间立场 = design_spectrum.get("中间立场", [])

            if 极端A and 极端B:
                # 构建选项（包含极端A、极端B和中间立场）
                options = [
                    f"倾向极端A：{极端A}",
                    f"倾向极端B：{极端B}"
                ]

                # 添加中间立场选项（最多2个）
                for stance in 中间立场[:2]:
                    if isinstance(stance, dict):
                        label = stance.get("标签", "")
                        if label:
                            options.append(f"中间立场：{label}")

                philosophy_questions.append({
                    "id": "v1_approach_spectrum",
                    "question": " 在设计方案的光谱上，您的理想立场是？(单选)",
                    "context": f"从'{极端A}'到'{极端B}'之间存在多种可能性，您的选择将决定方案的整体调性。",
                    "type": "single_choice",
                    "options": options,
                    "source": "v1_strategic_insight",
                    "dimension": "approach"
                })

                logger.info(f" 基于design_challenge_spectrum生成方案倾向问题: {极端A} ↔ {极端B}")

        # 3. 基于project_task生成目标理念问题
        if project_task:
            logger.debug(" [TRACE] 处理 project_task...")
            # 提取"雇佣空间完成[X]与[Y]"部分
            safe_task = project_task[:2000] if len(project_task) > 2000 else project_task
            #  修复: 使用非贪婪匹配和长度限制，避免灾难性回溯
            match = re.search(r'雇佣空间完成\[([^\]]{1,50}?)\]与\[([^\]]{1,50}?)\]', safe_task)
            logger.debug(f" [TRACE] project_task 正则匹配完成: match={bool(match)}")
            if match:
                goal_x = match.group(1)
                goal_y = match.group(2)

                philosophy_questions.append({
                    "id": "v1_goal_philosophy",
                    "question": " 对于这个项目，您更看重哪个层面的成功？(单选)",
                    "context": f"V1分析显示您希望空间完成'{goal_x}'与'{goal_y}'，但在实际决策中往往需要确定主次。",
                    "type": "single_choice",
                    "options": [
                        f"{goal_x} - 这是核心目标",
                        f"{goal_y} - 这是核心目标",
                        "两者缺一不可，必须同时实现",
                        "还有更重要的目标（请在补充说明中描述）"
                    ],
                    "source": "v1_strategic_insight",
                    "dimension": "goal"
                })

                logger.info(f" 基于project_task生成目标理念问题: {goal_x} vs {goal_y}")

        # 4. 基于expert_handoff.critical_questions_for_experts生成开放探索问题
        critical_questions_raw = expert_handoff.get("critical_questions_for_experts", [])
        
        #  v7.3修复：兼容处理Dict格式（按角色分组）和List格式
        if isinstance(critical_questions_raw, dict):
            # 将所有角色的问题合并为一个列表
            critical_questions = []
            for questions in critical_questions_raw.values():
                if isinstance(questions, list):
                    critical_questions.extend(questions)
                elif isinstance(questions, str):
                    critical_questions.append(questions)
            logger.debug(f" critical_questions_for_experts 是Dict格式，已扁平化为 {len(critical_questions)} 个问题")
        else:
            critical_questions = critical_questions_raw if isinstance(critical_questions_raw, list) else []
        
        if critical_questions and len(critical_questions) > 0:
            # 选择第1个critical question作为开放题
            first_question = critical_questions[0]

            philosophy_questions.append({
                "id": "v1_critical_exploration",
                "question": f" {first_question}",
                "context": "V1分析师识别出这是项目的关键决策点，您的思考将帮助专家团队更好地理解您的深层需求。",
                "type": "open_ended",
                "placeholder": "请分享您的想法、担忧或不确定的地方...",
                "source": "v1_strategic_insight",
                "dimension": "exploration"
            })

            logger.info(" 基于critical_questions生成开放探索问题")

        logger.debug(f" [TRACE] _build_philosophy_questions 完成，生成 {len(philosophy_questions)} 个问题")
        return philosophy_questions


class ConflictQuestionGenerator:
    """
    资源冲突问题生成器

    基于V1.5可行性分析结果生成针对性问题（价值体现点1 - 资源维度）。
    当检测到critical级别冲突时，生成单选题要求用户明确优先级。

    v7.4 优化：
    - 冲突问题必须由用户约束激活，避免突兀出现
    - 只有当用户在输入中提及相关约束（预算/工期/空间）时才生成对应问题

    原始位置: calibration_questionnaire.py L742-861
    """

    @staticmethod
    def generate(
        feasibility: Dict[str, Any],
        scenario_type: str = "unknown",
        user_mentioned_constraints: List[str] | None = None
    ) -> List[Dict[str, Any]]:
        """
        基于V1.5可行性分析结果生成针对性问题（ 价值体现点1 - 资源维度）

         v7.4优化：冲突问题必须由用户约束激活

        核心逻辑：
        - 当检测到critical级别冲突时，生成单选题要求用户明确优先级
        - 针对预算/时间/空间三类冲突，分别生成不同的问题
        -  v7.4: 只有当用户提及相关约束时才生成对应问题
        -  根据场景类型过滤：竞标策略场景跳过施工相关冲突
        - 问题插入到问卷开头，确保用户优先回答

        Args:
            feasibility: V1.5可行性分析结果
            scenario_type: 场景类型
            user_mentioned_constraints: 用户提及的约束类型列表 (budget/timeline/space/regulation)

        Returns:
            冲突问题列表（单选题）
        """
        conflict_questions = []

        #  P0优化：竞标策略场景跳过施工相关冲突问题
        if scenario_type == "bidding_strategy":
            logger.info(" 竞标策略场景：跳过施工相关冲突问题（预算、工期、空间）")
            return []

        #  v7.4: 初始化用户约束列表
        if user_mentioned_constraints is None:
            user_mentioned_constraints = []

        # 提取冲突检测结果
        conflicts = feasibility.get("conflict_detection", {})

        # 1. 预算冲突问题
        #  v7.4: 只有当用户提及预算约束时才生成
        budget_mentioned = "budget" in user_mentioned_constraints
        budget_conflicts = conflicts.get("budget_conflicts", [])

        if budget_conflicts and budget_conflicts[0].get("detected"):
            conflict = budget_conflicts[0]
            severity = conflict.get("severity", "unknown")

            # 仅针对critical和high级别的冲突生成问题
            if severity in ["critical", "high"]:
                if not budget_mentioned:
                    #  v7.4: 用户未提及预算，跳过此问题
                    logger.info(f"️ [v7.4] 用户未提及预算约束，跳过预算冲突问题（severity={severity}）")
                else:
                    description = conflict.get("description", "预算约束")
                    details = conflict.get("details", {})
                    gap = details.get("gap", 0)
                    gap_percentage = details.get("gap_percentage", 0)

                    # 构建问题选项
                    options = [
                        f"增加预算至可行范围（需额外投入约{gap//10000}万元）",
                        "削减部分需求，优先保留核心功能",
                        "寻求替代方案（降低材料等级、分期实施等）"
                    ]

                    conflict_questions.append({
                        "id": "v15_budget_conflict",
                        "question": f"️ 可行性分析发现：{description}。您倾向于如何调整？(单选)",
                        "context": f"V1.5检测到预算缺口约{gap_percentage}%，这是项目推进的关键决策点。",
                        "type": "single_choice",
                        "options": options,
                        "source": "v15_feasibility_conflict",
                        "severity": severity
                    })

                    logger.info(f" V1.5预算冲突问题生成：severity={severity}, gap={gap}, gap_percentage={gap_percentage}%")

        # 2. 时间冲突问题
        #  v7.4: 只有当用户提及工期约束时才生成
        timeline_mentioned = "timeline" in user_mentioned_constraints
        timeline_conflicts = conflicts.get("timeline_conflicts", [])

        if timeline_conflicts and timeline_conflicts[0].get("detected"):
            conflict = timeline_conflicts[0]
            severity = conflict.get("severity", "unknown")

            if severity in ["critical", "high", "medium"]:
                if not timeline_mentioned:
                    #  v7.4: 用户未提及工期，跳过此问题
                    logger.info(f"️ [v7.4] 用户未提及工期约束，跳过时间冲突问题（severity={severity}）")
                else:
                    description = conflict.get("description", "工期约束")
                    details = conflict.get("details", {})
                    gap = details.get("gap", 0)

                    options = [
                        f"延长工期（需额外{gap}天左右），确保质量标准",
                        "维持工期，调整质量预期至'优良'等级",
                        "优化施工方案，在质量和时间之间寻求平衡"
                    ]

                    conflict_questions.append({
                        "id": "v15_timeline_conflict",
                        "question": f"️ 可行性分析发现：{description}。您倾向于如何调整？(单选)",
                        "context": "V1.5检测到工期紧张可能影响质量标准，需要明确时间与质量的优先级。",
                        "type": "single_choice",
                        "options": options,
                        "source": "v15_feasibility_conflict",
                        "severity": severity
                    })

                    logger.info(f" V1.5时间冲突问题生成：severity={severity}, gap={gap}天")

        # 3. 空间冲突问题
        #  v7.4: 只有当用户提及空间约束时才生成
        space_mentioned = "space" in user_mentioned_constraints
        space_conflicts = conflicts.get("space_conflicts", [])

        if space_conflicts and space_conflicts[0].get("detected"):
            conflict = space_conflicts[0]
            severity = conflict.get("severity", "unknown")

            if severity in ["critical", "high"]:
                if not space_mentioned:
                    #  v7.4: 用户未提及空间，跳过此问题
                    logger.info(f"️ [v7.4] 用户未提及空间约束，跳过空间冲突问题（severity={severity}）")
                else:
                    description = conflict.get("description", "空间约束")
                    details = conflict.get("details", {})
                    gap = details.get("gap", 0)

                    options = [
                        "调整户型配置，减少房间数量或面积",
                        "采用多功能房设计，提升空间灵活性",
                        "优化空间布局，通过设计创新解决约束"
                    ]

                    conflict_questions.append({
                        "id": "v15_space_conflict",
                        "question": f"️ 可行性分析发现：{description}。您倾向于如何调整？(单选)",
                        "context": f"V1.5检测到空间缺口约{gap}㎡，需要重新权衡功能配置。",
                        "type": "single_choice",
                        "options": options,
                        "source": "v15_feasibility_conflict",
                        "severity": severity
                    })

                    logger.info(f" V1.5空间冲突问题生成：severity={severity}, gap={gap}㎡")

        #  v7.4: 统计日志
        if not conflict_questions and conflicts:
            logger.info(f"️ [v7.4] 检测到冲突但用户未提及相关约束，跳过所有冲突问题（用户约束: {user_mentioned_constraints}）")

        return conflict_questions


class DomainSpecificQuestionGenerator:
    """
    领域专业问题生成器

    v7.4 新增：基于识别的领域生成专业问题，替代通用模板问题。

    支持的领域：
    - tech_innovation: 科技创新（AI、数据、迭代、模块化等）
    - hospitality: 酒店餐饮
    - office: 办公空间
    - retail: 零售商业
    - residential: 住宅空间
    - cultural_educational: 文化教育
    - healthcare: 医疗健康
    """

    # 领域专业问题模板
    DOMAIN_QUESTION_TEMPLATES = {
        "tech_innovation": {
            "single_choice": [
                {
                    "id": "tech_flexibility_vs_stability",
                    "question": "在空间设计中，'灵活可变'与'稳定高效'如何权衡？(单选)",
                    "context": "这决定了空间的基础架构和技术复杂度。",
                    "options": [
                        "高度灵活：空间能随时响应变化，接受一定的效率损失",
                        "稳定优先：固定高效的布局，仅保留必要的调整能力",
                        "分区策略：核心区稳定，边缘区灵活"
                    ]
                },
                {
                    "id": "tech_automation_level",
                    "question": "空间调整的自动化程度，您期望达到？(单选)",
                    "context": "自动化程度影响技术投入和用户体验。",
                    "options": [
                        "全自动：系统自主决策和执行调整",
                        "半自动：系统建议，人工确认后执行",
                        "手动触发：人工发起，系统辅助执行",
                        "纯手动：传统方式，无需技术介入"
                    ]
                }
            ],
            "multiple_choice": [
                {
                    "id": "tech_data_sources",
                    "question": "空间优化应该参考哪些数据源？(多选)",
                    "context": "数据源决定了优化决策的依据和精度。",
                    "options": [
                        "空间占用率：哪些区域被使用/闲置",
                        "人员流动热力图：动线和聚集点",
                        "环境数据：温度、光照、噪音",
                        "预约/日程数据：会议室、工位预订",
                        "员工反馈：满意度调查、建议",
                        "业务数据：项目进度、团队规模变化"
                    ]
                }
            ],
            "open_ended": [
                {
                    "id": "tech_innovation_vision",
                    "question": "描述您理想中的'智能空间'一天：从员工到达到离开，空间如何响应？(开放题)",
                    "context": "这将成为设计的愿景蓝图。",
                    "placeholder": "例如：员工刷卡进入，系统自动调整其常用工位的灯光和温度..."
                }
            ]
        },
        "hospitality": {
            "single_choice": [
                {
                    "id": "hospitality_experience_focus",
                    "question": "在客户体验中，最核心的差异化要素是？(单选)",
                    "context": "这决定了设计资源的投入重点。",
                    "options": [
                        "视觉震撼：第一印象和拍照打卡点",
                        "服务动线：高效贴心的服务体验",
                        "私密舒适：安静放松的个人空间",
                        "文化叙事：独特的品牌故事和在地文化"
                    ]
                }
            ],
            "multiple_choice": [
                {
                    "id": "hospitality_key_touchpoints",
                    "question": "以下哪些客户触点需要重点设计？(多选)",
                    "context": "触点设计决定了客户体验的关键时刻。",
                    "options": [
                        "入口/大堂：第一印象",
                        "前台/接待：服务起点",
                        "走廊/过渡：空间叙事",
                        "核心功能区：主要体验",
                        "休息/等候区：舒适感知",
                        "出口/告别：最后印象"
                    ]
                }
            ]
        },
        "office": {
            "single_choice": [
                {
                    "id": "office_work_mode",
                    "question": "团队的主要工作模式是？(单选)",
                    "context": "工作模式决定了空间的基本布局逻辑。",
                    "options": [
                        "独立专注型：大部分时间独立工作，偶尔协作",
                        "频繁协作型：团队讨论和协作是常态",
                        "混合模式：根据项目阶段切换工作方式",
                        "远程优先：办公室主要用于特定活动"
                    ]
                }
            ],
            "multiple_choice": [
                {
                    "id": "office_space_types",
                    "question": "以下哪些空间类型是必须的？(多选)",
                    "context": "空间类型配置决定了功能分区。",
                    "options": [
                        "开放工位区",
                        "独立办公室",
                        "会议室（大/中/小）",
                        "电话亭/专注舱",
                        "休闲/茶水区",
                        "培训/多功能厅"
                    ]
                }
            ]
        }
    }

    @classmethod
    def generate(
        cls,
        domain_type: str,
        core_concepts: List[str] = None,
        keywords: List[tuple] = None,
        max_questions: int = 4
    ) -> List[Dict[str, Any]]:
        """
        基于领域生成专业问题

        Args:
            domain_type: 领域类型 (tech_innovation/hospitality/office/...)
            core_concepts: 核心概念列表
            keywords: 关键词列表 [(keyword, weight), ...]
            max_questions: 最大问题数量

        Returns:
            领域专业问题列表
        """
        questions = []

        # 获取领域模板
        templates = cls.DOMAIN_QUESTION_TEMPLATES.get(domain_type, {})
        if not templates:
            logger.info(f"️ [DomainSpecific] 领域 {domain_type} 无专用模板，跳过")
            return []

        # 按题型顺序生成问题
        for q_type in ["single_choice", "multiple_choice", "open_ended"]:
            type_templates = templates.get(q_type, [])
            for template in type_templates:
                if len(questions) >= max_questions:
                    break

                question = template.copy()
                question["type"] = q_type
                question["source"] = "domain_specific"
                question["domain"] = domain_type

                # 如果有核心概念，尝试个性化问题
                if core_concepts and "{concept}" in question.get("question", ""):
                    question["question"] = question["question"].format(
                        concept=core_concepts[0]
                    )

                questions.append(question)

        logger.info(f" [DomainSpecific] 为领域 {domain_type} 生成 {len(questions)} 个专业问题")
        return questions
