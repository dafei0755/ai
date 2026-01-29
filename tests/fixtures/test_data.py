"""
测试数据目录
存放常用的测试样本文件和数据
"""

# 样本PDF内容（用于测试文件处理）
SAMPLE_PDF_TEXT = """
项目需求文档

1. 项目概述
   设计一个150平米的现代简约风格住宅

2. 功能需求
   - 三室两厅
   - 注重收纳空间
   - 采光良好

3. 预算
   总预算：30万元
"""

# 样本Word文档内容
SAMPLE_WORD_TEXT = """
设计需求说明

客户信息：张先生
项目类型：住宅室内设计
风格偏好：现代简约、北欧风格
特殊要求：家有老人和小孩，需要考虑安全性
"""

# 样本用户输入
SAMPLE_USER_INPUTS = {
    "simple": "我想设计一个咖啡店",
    "detailed": "我需要设计一个150平米的现代简约风格住宅，三室两厅，预算30万，希望注重收纳和采光",
    "with_files": "请根据附件中的需求文档进行设计分析",
    "commercial": "设计一个200平米的精品咖啡店，位于商业区，目标客户是年轻白领",
    "renovation": "老房翻新，80平米两室一厅，想改造成北欧风格",
}

# 样本问卷数据
SAMPLE_QUESTIONNAIRE = {
    "questions": [
        {"id": "q1", "text": "您的项目主要使用场景是什么？", "type": "choice", "options": ["居住", "办公", "商业"]},
        {"id": "q2", "text": "您对设计风格有具体偏好吗？", "type": "text"},
        {"id": "q3", "text": "项目预算范围是多少？", "type": "number"},
    ]
}

# 样本问卷回答
SAMPLE_QUESTIONNAIRE_ANSWERS = {"q1": "居住", "q2": "现代简约、北欧风格", "q3": "30万"}

# 样本专家池数据
SAMPLE_EXPERT_POOL = [
    {"id": "expert_v3_001", "role": "V3_空间规划师", "name": "空间布局专家", "expertise": ["空间规划", "动线设计", "功能分区"], "priority": 1},
    {"id": "expert_v4_001", "role": "V4_风格定义师", "name": "风格设计专家", "expertise": ["风格定义", "色彩搭配", "材料选择"], "priority": 2},
    {"id": "expert_v5_001", "role": "V5_预算分析师", "name": "成本控制专家", "expertise": ["预算规划", "成本优化", "材料采购"], "priority": 3},
]

# 样本分析结果
SAMPLE_ANALYSIS_RESULTS = {
    "expert_v3_001": {
        "expert_name": "空间布局专家",
        "analysis": "基于150平米的空间，建议采用开放式布局...",
        "recommendations": ["客厅与餐厅采用开放式设计", "主卧套房设计，独立卫浴", "次卧预留儿童房功能"],
        "search_references": [{"title": "现代住宅空间规划指南", "url": "https://example.com/article1", "snippet": "开放式布局的优势..."}],
    },
    "expert_v4_001": {
        "expert_name": "风格设计专家",
        "analysis": "现代简约风格强调简洁、实用...",
        "recommendations": ["色彩以白色、灰色为主", "家具选择简洁线条", "适当加入木质元素"],
        "search_references": [],
    },
}

# 样本LLM响应
SAMPLE_LLM_RESPONSES = {
    "requirements_analysis": """
    {
        "core_requirements": [
            "150平米住宅设计",
            "现代简约风格",
            "三室两厅布局"
        ],
        "constraints": [
            "预算30万",
            "注重收纳",
            "采光良好"
        ],
        "implicit_needs": [
            "家庭居住",
            "实用功能优先"
        ]
    }
    """,
    "expert_analysis": """
    {
        "analysis": "基于项目需求，建议采用开放式布局设计，以增强空间感和采光效果。",
        "recommendations": [
            "客厅与餐厅开放式设计",
            "主卧套房配独立卫浴",
            "多功能收纳系统"
        ],
        "challenges": [
            "预算有限需要材料优化",
            "收纳空间需要精心规划"
        ]
    }
    """,
    "questionnaire_generation": """
    {
        "questions": [
            {
                "id": "q1",
                "text": "家庭成员构成如何？",
                "type": "text",
                "priority": "high"
            },
            {
                "id": "q2",
                "text": "是否有特殊生活习惯需要考虑？",
                "type": "text",
                "priority": "medium"
            }
        ]
    }
    """,
}

# 样本搜索结果
SAMPLE_SEARCH_RESULTS = {
    "tavily": {
        "results": [
            {
                "title": "现代简约风格设计指南",
                "url": "https://example.com/modern-design",
                "content": "现代简约风格的核心特征是简洁、实用...",
                "score": 0.95,
            },
            {
                "title": "150平米户型设计案例",
                "url": "https://example.com/150sqm-case",
                "content": "150平米三室两厅户型设计要点...",
                "score": 0.88,
            },
        ]
    },
    "arxiv": {
        "results": [
            {
                "title": "Sustainable Interior Design: A Systematic Review",
                "authors": ["Zhang, L.", "Wang, H."],
                "published": "2023-05-15",
                "abstract": "This paper reviews sustainable design practices...",
                "pdf_url": "https://arxiv.org/pdf/2305.12345",
            }
        ]
    },
}

# 样本图片生成提示词
SAMPLE_IMAGE_PROMPTS = {
    "concept_image": "A modern minimalist living room with open layout, "
    "featuring white walls, wooden floors, and natural lighting. "
    "Include a comfortable sofa, coffee table, and large windows.",
    "followup_image": "Close-up view of a custom storage solution in modern style, "
    "showing built-in cabinets with clean lines and hidden storage compartments.",
}

# 样本配置数据
SAMPLE_CONFIG = {
    "analysis_mode": {
        "mode": "comprehensive",
        "enable_search": True,
        "enable_image_generation": True,
        "max_experts": 10,
    },
    "search_filters": {
        "blacklist": ["lowquality.com", "spam-site.com"],
        "whitelist": ["authoritative-source.com", "research-journal.org"],
    },
    "capability_boundary": {
        "supported_deliverables": ["设计策略文档", "空间概念描述", "材料选择指导"],
        "unsupported_deliverables": ["CAD施工图", "3D效果图", "精确材料清单"],
    },
}

# 样本会话数据
SAMPLE_SESSION_DATA = {
    "session_id": "test-session-123",
    "user_id": "test-user-456",
    "created_at": "2026-01-06T10:00:00Z",
    "state": {
        "user_input": SAMPLE_USER_INPUTS["detailed"],
        "current_phase": "expert_collaboration",
        "expert_pool": SAMPLE_EXPERT_POOL,
        "analysis_results": SAMPLE_ANALYSIS_RESULTS,
    },
}
