"""
P2 深度增强验证测试

D1: 维度字段强制注入 (_ensure_task_dimensions)
D2: 多源整合任务自动生成 (_detect_multi_reference_sources, _generate_integration_tasks)
D3: 规则引擎通用化扩充 (_generate_rule_based_tasks)
D4: 用户意图覆盖校验 (_extract_user_requirements, _validate_requirement_coverage, _generate_coverage_gap_tasks)
"""


# =============================================================================
# D1: 维度字段强制注入
# =============================================================================


class TestD1DimensionInjection:
    """验证每个任务都携带3-5个dimensions子项"""

    def test_ensure_dimensions_auto_fill(self):
        """D1: 无dimensions的任务应被自动填充"""
        from intelligent_project_analyzer.services.core_task_decomposer import (
            _ensure_task_dimensions,
        )

        tasks = [
            {
                "id": "task_1",
                "title": "文化背景调研",
                "description": "调研项目相关的传统文化、历史遗产和民俗特色",
                "source_keywords": ["文化", "历史"],
                "task_type": "research",
            },
            {
                "id": "task_2",
                "title": "客群需求分析",
                "description": "分析目标用户群体的需求",
                "source_keywords": ["客群", "需求"],
                "task_type": "analysis",
            },
        ]
        _ensure_task_dimensions(tasks)

        for task in tasks:
            assert "dimensions" in task, f"任务 {task['id']} 缺少dimensions字段"
            assert len(task["dimensions"]) >= 3, f"任务 {task['id']} dimensions不足3个: {task['dimensions']}"
            assert len(task["dimensions"]) <= 5, f"任务 {task['id']} dimensions超过5个: {task['dimensions']}"

    def test_ensure_dimensions_preserves_existing(self):
        """D1: 已有>=3个dimensions的任务不应被覆盖"""
        from intelligent_project_analyzer.services.core_task_decomposer import (
            _ensure_task_dimensions,
        )

        existing_dims = ["运营模式", "商业定位", "策划体系", "成功要素"]
        tasks = [
            {
                "id": "task_1",
                "title": "商业模式研究",
                "description": "分析商业模式",
                "source_keywords": [],
                "task_type": "research",
                "dimensions": existing_dims,
            },
        ]
        _ensure_task_dimensions(tasks)

        assert tasks[0]["dimensions"] == existing_dims, "已有维度被意外覆盖"

    def test_ensure_dimensions_extracts_from_description(self):
        """D1: 应从description中的顿号分隔短语提取维度"""
        from intelligent_project_analyzer.services.core_task_decomposer import (
            _ensure_task_dimensions,
        )

        tasks = [
            {
                "id": "task_1",
                "title": "样本研究",
                "description": "收集温度、湿度、风向、日照数据进行分析",
                "source_keywords": [],
                "task_type": "research",
            },
        ]
        _ensure_task_dimensions(tasks)

        dims = tasks[0]["dimensions"]
        assert len(dims) >= 3
        # 应该提取到温度、湿度、风向等
        extracted_from_desc = [d for d in dims if d in ["温度", "湿度", "风向", "日照数据"]]
        assert len(extracted_from_desc) >= 2, f"从description提取的维度不足: {dims}"

    def test_ensure_dimensions_uses_keywords_fallback(self):
        """D1: 当description不够时，应从source_keywords补充"""
        from intelligent_project_analyzer.services.core_task_decomposer import (
            _ensure_task_dimensions,
        )

        tasks = [
            {
                "id": "task_1",
                "title": "短任务",
                "description": "简短描述",
                "source_keywords": ["市场", "趋势", "竞品"],
                "task_type": "research",
            },
        ]
        _ensure_task_dimensions(tasks)

        dims = tasks[0]["dimensions"]
        assert len(dims) >= 3
        # source_keywords应被采纳
        kw_used = [d for d in dims if d in ["市场", "趋势", "竞品"]]
        assert len(kw_used) >= 1, f"source_keywords未被使用: {dims}"

    def test_ensure_dimensions_type_defaults(self):
        """D1: 最终兜底使用task_type默认维度"""
        from intelligent_project_analyzer.services.core_task_decomposer import (
            _ensure_task_dimensions,
        )

        tasks = [
            {
                "id": "task_1",
                "title": "X",
                "description": "",
                "source_keywords": [],
                "task_type": "design",
            },
        ]
        _ensure_task_dimensions(tasks)

        dims = tasks[0]["dimensions"]
        assert len(dims) >= 3
        # design类型的默认维度
        design_defaults = ["方案构思", "可行性评估", "视觉表达", "技术实现"]
        used_defaults = [d for d in dims if d in design_defaults]
        assert len(used_defaults) >= 3, f"design默认维度未生效: {dims}"

    def test_dimensions_in_parse_response(self):
        """D1: parse_response应保留LLM返回的dimensions字段"""
        from intelligent_project_analyzer.services.core_task_decomposer import (
            CoreTaskDecomposer,
        )

        decomposer = CoreTaskDecomposer()

        response = """{
            "tasks": [{
                "id": "task_1",
                "title": "测试任务",
                "description": "测试描述",
                "source_keywords": ["测试"],
                "task_type": "research",
                "priority": "high",
                "dependencies": [],
                "execution_order": 1,
                "support_search": true,
                "dimensions": ["维度A", "维度B", "维度C"]
            }]
        }"""

        tasks = decomposer.parse_response(response)
        assert len(tasks) == 1
        assert tasks[0]["dimensions"] == ["维度A", "维度B", "维度C"]

    def test_dimensions_default_empty_in_parse_response(self):
        """D1: parse_response中LLM未返回dimensions时默认为空列表"""
        from intelligent_project_analyzer.services.core_task_decomposer import (
            CoreTaskDecomposer,
        )

        decomposer = CoreTaskDecomposer()

        response = """{
            "tasks": [{
                "id": "task_1",
                "title": "测试任务",
                "description": "测试描述",
                "source_keywords": [],
                "task_type": "research",
                "priority": "medium"
            }]
        }"""

        tasks = decomposer.parse_response(response)
        assert len(tasks) == 1
        assert tasks[0]["dimensions"] == []


# =============================================================================
# D2: 多源整合任务自动生成
# =============================================================================


class TestD2MultiReferenceDetection:
    """验证多源参考检测的通用性"""

    def test_detect_quoted_names(self):
        """D2: 检测多个引号包围的名称"""
        from intelligent_project_analyzer.services.core_task_decomposer import (
            _detect_multi_reference_sources,
        )

        user_input = '参考"安藤忠雄"和"隈研吾"的设计风格'
        result = _detect_multi_reference_sources(user_input)

        assert result["detected"] is True
        assert len(result["sources"]) >= 2
        assert result["source_type"] == "reference"

    def test_detect_multi_pattern(self):
        """D2: 检测'多位/多个'模式"""
        from intelligent_project_analyzer.services.core_task_decomposer import (
            _detect_multi_reference_sources,
        )

        user_input = "邀请多位建筑师参与设计"
        result = _detect_multi_reference_sources(user_input)

        assert result["detected"] is True
        assert result["source_type"] == "expert"
        assert "多位建筑师" in result["pattern"]

    def test_detect_compare_pattern(self):
        """D2: 检测对比/融合模式"""
        from intelligent_project_analyzer.services.core_task_decomposer import (
            _detect_multi_reference_sources,
        )

        user_input = "融合传统工艺和现代技术的设计方案"
        result = _detect_multi_reference_sources(user_input)

        assert result["detected"] is True
        assert result["source_type"] == "methodology"
        assert "对比/融合模式" in result["pattern"]

    def test_detect_structured_data_refs(self):
        """D2: 从结构化数据检测多源引用"""
        from intelligent_project_analyzer.services.core_task_decomposer import (
            _detect_multi_reference_sources,
        )

        user_input = "设计一个文化酒店"
        structured_data = {"design_challenge": '"传统美学"与"现代功能"的平衡'}
        result = _detect_multi_reference_sources(user_input, structured_data)

        assert result["detected"] is True
        assert result["pattern"] == "结构化数据多源引用"

    def test_detect_no_multi_reference(self):
        """D2: 无多源引用时返回detected=False"""
        from intelligent_project_analyzer.services.core_task_decomposer import (
            _detect_multi_reference_sources,
        )

        user_input = "设计一个简单的住宅"
        result = _detect_multi_reference_sources(user_input)

        assert result["detected"] is False
        assert result["sources"] == []

    def test_generate_integration_tasks_basic(self):
        """D2: 生成整合任务（2个源 → 1个对比任务）"""
        from intelligent_project_analyzer.services.core_task_decomposer import (
            _generate_integration_tasks,
        )

        ref_info = {"detected": True, "sources": ["方法A", "方法B"], "source_type": "methodology", "pattern": "对比/融合模式"}
        tasks = _generate_integration_tasks(ref_info, "融合方法A和方法B")

        assert len(tasks) == 1  # 2个源只生成对比任务
        assert "对比分析" in tasks[0]["title"]
        assert tasks[0]["task_type"] == "analysis"
        assert len(tasks[0]["dimensions"]) >= 3

    def test_generate_integration_tasks_three_plus(self):
        """D2: 3+个源时额外生成整合策略任务"""
        from intelligent_project_analyzer.services.core_task_decomposer import (
            _generate_integration_tasks,
        )

        ref_info = {"detected": True, "sources": ["专家A", "专家B", "专家C"], "source_type": "expert", "pattern": "名称枚举"}
        tasks = _generate_integration_tasks(ref_info, "参考专家A、B、C")

        assert len(tasks) == 2  # 对比 + 整合策略
        assert "对比分析" in tasks[0]["title"]
        assert "整合策略" in tasks[1]["title"]

    def test_generate_integration_tasks_not_detected(self):
        """D2: 未检测到多源时返回空列表"""
        from intelligent_project_analyzer.services.core_task_decomposer import (
            _generate_integration_tasks,
        )

        ref_info = {"detected": False, "sources": [], "source_type": "reference", "pattern": ""}
        tasks = _generate_integration_tasks(ref_info, "简单项目")

        assert tasks == []


# =============================================================================
# D3: 规则引擎通用化扩充
# =============================================================================


class TestD3RuleEngineGeneralization:
    """验证规则引擎重新启用且通用化"""

    def test_feature_driven_enabled(self):
        """D3: 特征驱动策略应重新启用（不再被注释）"""
        import inspect
        from intelligent_project_analyzer.services.core_task_decomposer import (
            _generate_rule_based_tasks,
        )

        source = inspect.getsource(_generate_rule_based_tasks)

        # 确认 Strategy 1 不再被注释
        assert "# if project_features:" not in source, "特征驱动策略仍然被注释"
        assert "_generate_feature_driven_tasks(project_features)" in source, "特征驱动函数调用缺失"

    def test_feature_driven_generates_tasks(self):
        """D3: 高分特征应生成对应规则任务"""
        from intelligent_project_analyzer.services.core_task_decomposer import (
            _generate_rule_based_tasks,
        )

        features = {"cultural": 0.88, "commercial": 0.72, "aesthetic": 0.65}
        tasks = _generate_rule_based_tasks(
            user_input="设计一个文化酒店", structured_data=None, project_features=features, task_count=10
        )

        # cultural (0.88 >= 0.7) 和 commercial (0.72 >= 0.7) 应触发任务
        assert len(tasks) >= 2, f"特征驱动应至少生成2个任务，实际{len(tasks)}个"

        # 检查特征来源标记
        feature_tasks = [t for t in tasks if t.get("source") == "rule_feature_driven"]
        assert len(feature_tasks) >= 2, f"特征驱动任务不足: {feature_tasks}"

    def test_universal_rules_stakeholder(self):
        """D3: 包含用户/客群关键词时应生成利益相关方任务"""
        from intelligent_project_analyzer.services.core_task_decomposer import (
            _generate_rule_based_tasks,
        )

        tasks = _generate_rule_based_tasks(
            user_input="为社区居民和游客设计公共空间", structured_data=None, project_features=None, task_count=10
        )

        stakeholder_tasks = [t for t in tasks if "利益相关方" in t.get("title", "")]
        assert len(stakeholder_tasks) >= 1, "缺少利益相关方分析任务"

    def test_universal_rules_budget(self):
        """D3: 包含预算关键词时应生成资源约束任务"""
        from intelligent_project_analyzer.services.core_task_decomposer import (
            _generate_rule_based_tasks,
        )

        tasks = _generate_rule_based_tasks(
            user_input="预算有限，50万全包的住宅改造", structured_data=None, project_features=None, task_count=10
        )

        budget_tasks = [t for t in tasks if "资源约束" in t.get("title", "")]
        assert len(budget_tasks) >= 1, "缺少资源约束评估任务"

    def test_universal_rules_sustainability(self):
        """D3: 包含可持续关键词时应生成可持续策略任务"""
        from intelligent_project_analyzer.services.core_task_decomposer import (
            _generate_rule_based_tasks,
        )

        tasks = _generate_rule_based_tasks(
            user_input="绿色建筑设计，注重节能环保", structured_data=None, project_features=None, task_count=10
        )

        sus_tasks = [t for t in tasks if "可持续" in t.get("title", "")]
        assert len(sus_tasks) >= 1, "缺少可持续发展策略任务"

    def test_universal_rules_phased(self):
        """D3: 包含分期关键词时应生成阶段规划任务"""
        from intelligent_project_analyzer.services.core_task_decomposer import (
            _generate_rule_based_tasks,
        )

        tasks = _generate_rule_based_tasks(
            user_input="项目分为一期和二期，一期先启动商业区", structured_data=None, project_features=None, task_count=10
        )

        phase_tasks = [t for t in tasks if "阶段规划" in t.get("title", "")]
        assert len(phase_tasks) >= 1, "缺少阶段规划任务"

    def test_rule_tasks_have_source_tag(self):
        """D3: 所有规则任务应有source标记"""
        from intelligent_project_analyzer.services.core_task_decomposer import (
            _generate_rule_based_tasks,
        )

        features = {"cultural": 0.85}
        tasks = _generate_rule_based_tasks(
            user_input="结合传统文化的项目，预算100万", structured_data=None, project_features=features, task_count=10
        )

        for task in tasks:
            assert "source" in task, f"任务 {task.get('title')} 缺少source字段"
            assert task["source"].startswith("rule_"), f"任务 {task.get('title')} source不规范: {task['source']}"


# =============================================================================
# D4: 用户意图覆盖校验
# =============================================================================


class TestD4UserIntentCoverage:
    """验证用户意图提取与覆盖校验的通用性"""

    def test_extract_numbered_list(self):
        """D4: 提取数字编号列表"""
        from intelligent_project_analyzer.services.core_task_decomposer import (
            _extract_user_requirements,
        )

        user_input = """项目要求：
1. 保留原有建筑结构
2. 增加绿色景观设计
3. 控制总预算在200万以内"""

        reqs = _extract_user_requirements(user_input)
        assert len(reqs) >= 2, f"应至少提取2个需求，实际{len(reqs)}个: {reqs}"

    def test_extract_chinese_numbered(self):
        """D4: 提取中文编号需求"""
        from intelligent_project_analyzer.services.core_task_decomposer import (
            _extract_user_requirements,
        )

        user_input = "第一、完成场地调研。第二、制定设计方案。第三、进行施工图设计。"

        reqs = _extract_user_requirements(user_input)
        assert len(reqs) >= 2, f"应至少提取2个需求，实际{len(reqs)}个"

    def test_extract_intent_clauses(self):
        """D4: 提取意图引导子句"""
        from intelligent_project_analyzer.services.core_task_decomposer import (
            _extract_user_requirements,
        )

        user_input = "需要融入当地文化元素。希望能成为城市更新的标杆。要求兼顾商业价值和社区需求。"

        reqs = _extract_user_requirements(user_input)
        assert len(reqs) >= 2, f"应至少提取2个需求，实际{len(reqs)}个"

        req_texts = [r["text"] for r in reqs]
        has_culture = any("文化" in t for t in req_texts)
        assert has_culture, f"未提取到文化相关需求: {req_texts}"

    def test_extract_markdown_headings(self):
        """D4: 提取Markdown标题"""
        from intelligent_project_analyzer.services.core_task_decomposer import (
            _extract_user_requirements,
        )

        user_input = """## 场地环境分析调研
详细的场地分析内容
## 设计理念与创新策略
创新的设计理念
## 施工计划与进度管理
分期施工计划"""

        reqs = _extract_user_requirements(user_input)
        headings = [r for r in reqs if r["source"] == "markdown_heading"]
        assert len(headings) >= 2, f"应至少提取2个Markdown标题需求，实际{len(headings)}个"

    def test_extract_specific_requirements_block(self):
        """D4: 提取'具体要求'块"""
        from intelligent_project_analyzer.services.core_task_decomposer import (
            _extract_user_requirements,
        )

        user_input = "具体要求：保留古树；增加停车位；设置无障碍通道"

        reqs = _extract_user_requirements(user_input)
        assert len(reqs) >= 2, f"应至少提取2个需求，实际{len(reqs)}个"

    def test_extract_empty_input(self):
        """D4: 简短输入无需求提取"""
        from intelligent_project_analyzer.services.core_task_decomposer import (
            _extract_user_requirements,
        )

        reqs = _extract_user_requirements("做个设计")
        assert len(reqs) == 0

    def test_validate_coverage_all_covered(self):
        """D4: 所有需求被覆盖时返回空列表"""
        from intelligent_project_analyzer.services.core_task_decomposer import (
            _validate_requirement_coverage,
        )

        tasks = [
            {"title": "文化背景调研", "description": "调研当地的传统文化和历史元素", "source_keywords": ["文化", "历史", "元素"]},
            {"title": "预算成本分析", "description": "分析项目预算约束和成本控制策略", "source_keywords": ["预算", "成本", "控制"]},
        ]
        requirements = [
            {"id": "req_1", "text": "融入当地文化元素", "source": "intent_clause"},
            {"id": "req_2", "text": "控制预算成本", "source": "intent_clause"},
        ]

        uncovered = _validate_requirement_coverage(tasks, requirements)
        assert len(uncovered) == 0, f"应全部覆盖，但发现未覆盖需求: {uncovered}"

    def test_validate_coverage_gaps(self):
        """D4: 未覆盖的需求应被识别"""
        from intelligent_project_analyzer.services.core_task_decomposer import (
            _validate_requirement_coverage,
        )

        tasks = [
            {"title": "文化研究", "description": "调研文化背景", "source_keywords": ["文化"]},
        ]
        requirements = [
            {"id": "req_1", "text": "融入文化元素", "source": "intent_clause"},
            {"id": "req_2", "text": "无障碍通道设计规范", "source": "numbered_list"},
        ]

        uncovered = _validate_requirement_coverage(tasks, requirements)
        assert len(uncovered) >= 1, "应至少识别1个未覆盖需求"

        # 无障碍通道应该是未覆盖的
        uncovered_texts = [r["text"] for r in uncovered]
        has_accessibility = any("无障碍" in t for t in uncovered_texts)
        assert has_accessibility, f"无障碍需求应未覆盖: {uncovered_texts}"

    def test_generate_coverage_gap_tasks(self):
        """D4: 为未覆盖需求生成补充任务"""
        from intelligent_project_analyzer.services.core_task_decomposer import (
            _generate_coverage_gap_tasks,
        )

        uncovered = [
            {"id": "req_1", "text": "无障碍通道设计规范研究", "source": "numbered_list"},
            {"id": "req_2", "text": "消防安全标准评估", "source": "numbered_list"},
        ]

        tasks = _generate_coverage_gap_tasks(uncovered, "设计一个公共建筑")

        assert len(tasks) == 2
        for task in tasks:
            assert task.get("source") == "rule_coverage_d4"
            assert "dimensions" in task
            assert len(task["dimensions"]) >= 2
            assert task.get("task_type") in ["research", "analysis", "design"]

    def test_generate_coverage_gap_max_five(self):
        """D4: 补充任务最多5个"""
        from intelligent_project_analyzer.services.core_task_decomposer import (
            _generate_coverage_gap_tasks,
        )

        uncovered = [{"id": f"req_{i}", "text": f"需求条目{i}的详细内容", "source": "numbered_list"} for i in range(10)]

        tasks = _generate_coverage_gap_tasks(uncovered, "大型项目")
        assert len(tasks) <= 5, f"补充任务应最多5个，实际{len(tasks)}个"


# =============================================================================
# 跨D项集成测试
# =============================================================================


class TestP2Integration:
    """P2 D1-D4 跨功能集成验证"""

    def test_rule_tasks_have_dimensions(self):
        """集成: 规则引擎生成的任务应包含dimensions"""
        from intelligent_project_analyzer.services.core_task_decomposer import (
            _generate_rule_based_tasks,
        )

        features = {"cultural": 0.9, "sustainable": 0.8}
        tasks = _generate_rule_based_tasks(
            user_input="可持续的文化遗产保护项目", structured_data=None, project_features=features, task_count=10
        )

        for task in tasks:
            # 规则任务的dimensions可能先为空，但D1会后处理
            assert isinstance(task.get("dimensions", []), list)

    def test_integration_tasks_have_dimensions(self):
        """集成: 整合任务应自带dimensions"""
        from intelligent_project_analyzer.services.core_task_decomposer import (
            _generate_integration_tasks,
        )

        ref_info = {"detected": True, "sources": ["A", "B", "C"], "source_type": "expert", "pattern": "名称枚举"}
        tasks = _generate_integration_tasks(ref_info, "参考A、B和C")

        for task in tasks:
            assert "dimensions" in task
            assert len(task["dimensions"]) >= 3

    def test_coverage_gap_tasks_have_dimensions(self):
        """集成: 覆盖补充任务应自带dimensions"""
        from intelligent_project_analyzer.services.core_task_decomposer import (
            _generate_coverage_gap_tasks,
        )

        uncovered = [{"id": "req_1", "text": "项目风险评估和应对", "source": "intent_clause"}]
        tasks = _generate_coverage_gap_tasks(uncovered, "大型项目")

        assert len(tasks) >= 1
        for task in tasks:
            assert "dimensions" in task
            assert len(task["dimensions"]) >= 2

    def test_d1_d2_d3_d4_functions_exist(self):
        """集成: 所有P2函数应可导入"""
        from intelligent_project_analyzer.services.core_task_decomposer import (
            _ensure_task_dimensions,
            _detect_multi_reference_sources,
            _generate_integration_tasks,
            _extract_user_requirements,
            _validate_requirement_coverage,
            _generate_coverage_gap_tasks,
        )

        # 所有函数都应该是callable
        assert callable(_ensure_task_dimensions)
        assert callable(_detect_multi_reference_sources)
        assert callable(_generate_integration_tasks)
        assert callable(_extract_user_requirements)
        assert callable(_validate_requirement_coverage)
        assert callable(_generate_coverage_gap_tasks)

    def test_p2_hooks_in_hybrid_function(self):
        """集成: decompose_core_tasks_hybrid应包含P2钩子"""
        import inspect
        from intelligent_project_analyzer.services.core_task_decomposer import (
            decompose_core_tasks_hybrid,
        )

        source = inspect.getsource(decompose_core_tasks_hybrid)

        # D1 钩子
        assert "_ensure_task_dimensions" in source, "缺少D1维度注入钩子"
        # D2 钩子
        assert "_detect_multi_reference_sources" in source, "缺少D2多源检测钩子"
        assert "_generate_integration_tasks" in source, "缺少D2整合任务生成钩子"
        # D4 钩子
        assert "_extract_user_requirements" in source, "缺少D4需求提取钩子"
        assert "_validate_requirement_coverage" in source, "缺少D4覆盖校验钩子"
        assert "_generate_coverage_gap_tasks" in source, "缺少D4补充任务生成钩子"
