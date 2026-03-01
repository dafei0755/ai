"""
项目类型自动检测器 — 单一权威注册表 (Single Source of Truth)
v7.200: 统一分类定义、中文标签映射、关键词推断、LLM Prompt 类型列表

所有与项目类型相关的设置，只在此文件中维护：
  - PROJECT_TYPE_REGISTRY：类型定义（ID、标签、优先级、关键词）
  - LEGACY_TYPE_ALIASES  ：旧 ID → 新 ID 向后兼容映射
  - get_type_label()      ：ID → 中文标签（全局唯一出处）
  - get_all_type_ids()    ：返回全部类型 ID 列表（供 YAML/Prompt 注入）

规则：
  - 新增/修改分类 → 只改本文件 PROJECT_TYPE_REGISTRY
  - 下游代码 shared_agent_utils / query_builder / requirements_analyst
    等均从本模块读取，禁止自行维护字典
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

# 扩展类型文件路径（管理员审批后由 project_type_expansion.py 写入）
_EXTENSIONS_FILE = Path(__file__).parent.parent.parent / "data" / "project_type_extensions.json"


def _load_extension_registry() -> Dict[str, Any]:
    """从 data/project_type_extensions.json 加载管理员审批的扩展类型"""
    if not _EXTENSIONS_FILE.exists():
        return {}
    try:
        import json

        with open(_EXTENSIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("types", {})
    except Exception as e:
        logger.warning(f"[TypeRegistry] 加载扩展类型失败，忽略: {e}")
        return {}


# =============================================================================
# 项目类型权威注册表
# 字段说明：
#   name        : 中文显示标签（唯一出处，其他文件不得另建映射）
#   name_en     : 英文检索上下文（供 query_builder 使用）
#   keywords    : 主关键词，命中权重 ×2
#   secondary_keywords: 次要关键词，命中权重 ×1
#   priority    : 类型区分优先级（越高越优先），范围 1-15
#   min_secondary_hits: 当 primary hits=0 时，次要命中需达到此阈值才触发（0=不限制）
#   include_in_prompt : True → 写入 LLM prompt 的可用类型列表
# =============================================================================
PROJECT_TYPE_REGISTRY: Dict[str, Dict[str, Any]] = {
    # ══════════════════════════════════════════════════════════════════════════
    # 优先级 15 — 乡建/新农村（强优先，防止被住宅/酒店关键词稀释）
    # ══════════════════════════════════════════════════════════════════════════
    "rural_construction": {
        "name": "乡建/新农村建设",
        "name_en": "rural construction village regeneration agricultural tourism",
        "keywords": [
            "新农村",
            "乡村振兴",
            "乡建",
            "农文旅",
            "村建",
            "村落改造",
            "乡村建设",
            "农村建设",
            "乡居",
            "村庄改造",
            "美丽乡村",
        ],
        "secondary_keywords": [
            "民宿集群",
            "在地农耕",
            "农耕文化",
            "乡村经济",
            "村子",
            "村庄",
            "村民",
            "农村",
            "乡村",
            "田园",
            "山村",
            "聚落",
            "振兴",
        ],
        "priority": 15,
        "min_secondary_hits": 3,
        "include_in_prompt": True,
    },
    # ══════════════════════════════════════════════════════════════════════════
    # 优先级 10 — 城市更新
    # ══════════════════════════════════════════════════════════════════════════
    "urban_renewal_market": {
        "name": "城市更新/公共市场",
        "name_en": "urban renewal public market regeneration",
        "keywords": [
            "城市更新",
            "菜市场",
            "农贸市场",
            "市场改造",
            "活化",
            "再生",
            "旧改",
            "老旧改造",
        ],
        "secondary_keywords": ["标杆", "示范", "渔村", "老街", "历史街区", "公共市场", "集市"],
        "priority": 10,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },
    "urban_renewal_heritage": {
        "name": "城市更新/历史建筑活化",
        "name_en": "urban renewal heritage conservation adaptive reuse renovation restoration addition",
        "keywords": [
            "历史街区",
            "老建筑",
            "文物保护",
            "历史保护",
            "古建筑",
            "老城区",
            "遗址保护",
            "遗产保护",
            "适应性改造",
            "适应性利用",
            "加建改造",
            "建筑修复",
        ],
        "secondary_keywords": [
            "修缮",
            "修复",
            "保护",
            "传承",
            "非遗",
            "传统建筑",
            "加建",
            "扩建",
            "立面改造",
            "历史风貌",
        ],
        "priority": 10,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },
    # ══════════════════════════════════════════════════════════════════════════
    # 优先级 9 — 高辨识度专项类型
    # ══════════════════════════════════════════════════════════════════════════
    "real_estate_showcase": {
        "name": "地产样板房/售楼展示",
        "name_en": "real estate model room showflat sales center developer",
        "keywords": ["样板房", "样板间", "售楼处", "展示中心", "地产营销", "销售中心"],
        "secondary_keywords": ["楼盘", "开发商", "竞标", "开盘", "地产项目", "地标建筑", "超高层"],
        "priority": 9,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },
    "industrial_conversion": {
        "name": "工业/生产设施/厂房改造",
        "name_en": "industrial conversion factory warehouse winery barn brewery adaptive reuse",
        "keywords": [
            "厂房",
            "工厂",
            "仓库",
            "工业遗存",
            "工业建筑",
            "粮仓",
            "车间",
            "工业遗址",
            "酒庄",
            "酿酒厂",
            "啤酒厂",
            "谷仓",
        ],
        "secondary_keywords": [
            "改造",
            "旧厂区",
            "工业风",
            "loft",
            "创意园区",
            "马厩",
            "温室",
            "能源工厂",
            "库房",
            "物流仓储",
        ],
        "priority": 9,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },
    "educational_facility": {
        "name": "教育建筑/校园",
        "name_en": "educational school campus university kindergarten library research daycare",
        "keywords": [
            "学校",
            "校园",
            "幼儿园",
            "小学",
            "中学",
            "高中",
            "大学",
            "高校",
            "教学楼",
            "图书馆",
            "科研楼",
            "实验楼",
            "书院",
            "学院",
            "日托中心",
            "研究所",
            "学生大厅",
        ],
        "secondary_keywords": [
            "教育",
            "教室",
            "课室",
            "培训",
            "研究院",
            "科研中心",
            "学生宿舍",
            "学生公寓",
            "食堂",
            "操场",
            "研学",
            "青少年",
            "职业学校",
            "培训学校",
            "研学基地",
        ],
        "priority": 9,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },
    "religious_spiritual": {
        "name": "宗教/仪式/殡葬空间",
        "name_en": "religious spiritual church temple mosque shrine chapel memorial cemetery",
        "keywords": [
            "教堂",
            "寺庙",
            "清真寺",
            "礼拜堂",
            "祠堂",
            "庙宇",
            "佛堂",
            "寺院",
            "道观",
            "神殿",
            "宗教建筑",
            "修道院",
            "大教堂",
            "小教堂",
            "祈告室",
            "犹太教堂",
        ],
        "secondary_keywords": [
            "礼拜",
            "冥想",
            "禅",
            "精神",
            "信仰",
            "纪念堂",
            "坛庙",
            "圣地",
            "庄严",
            "神圣",
            # 殡葬建筑（纪念中心/火葬场/公墓/陵墓）
            "火葬场",
            "公墓",
            "陵墓",
            "殡仪馆",
            "墓园",
            "纪念馆",
        ],
        "priority": 9,
        "min_secondary_hits": 1,
        "include_in_prompt": True,
    },
    # ══════════════════════════════════════════════════════════════════════════
    # 优先级 8 — 主流场所类型
    # ══════════════════════════════════════════════════════════════════════════
    "commercial_hospitality": {
        "name": "酒店民宿/度假",
        "name_en": "hospitality hotel boutique inn resort spa hostel holiday cabin glamping treehouse container hotspring",
        "keywords": [
            "酒店",
            "民宿",
            "度假村",
            "客栈",
            "旅馆",
            "会所",
            "度假小屋",
            "青年旅舍",
            "精品酒店",
            # 新型度假场所
            "泡汤",
            "日归温泉",
            "汤屋",
            "山顶营地",
            "树屋民宿",
            "露营基地",
            "集装箱民宿",
            "帐篷酒店",
            "荠野形",
            "帐篷度假",
        ],
        "secondary_keywords": [
            "resort",
            "住宿",
            "客房",
            "大堂吧",
            "度假",
            "宾馆",
            "旅游景点",
            "主题公园",
            "度假区",
            "旅游配套",
            "野外",
            "自然",
            "山里",
            "乡村住宿",
        ],
        "priority": 8,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },
    "commercial_dining": {
        "name": "餐饮/夜生活空间",
        "name_en": "restaurant dining cafe food beverage bar tea nightclub buffet hotpot barbecue",
        "keywords": [
            "餐厅",
            "餐饮",
            "咏噌馆",
            "茶室",
            "酒吧",
            "食堂",
            "快餐店",
            "夜店",
            "夜总会",
            # 特色餐饮形式
            "自助餐",
            "自助火锅",
            "自助宿",
            "无限畅吃",
            "烧烤店",
            "火锅店",
            "火锅",
            "串串",
            "凒菜",
            "小龙艶",
            "居酒屋",
            "大排档改造",
            "夹股",
        ],
        "secondary_keywords": [
            "咏噌",
            "茶馆",
            "酒楼",
            "美食",
            "用餐",
            "中餐",
            "西餐",
            "日料",
            "包房",
            "小酒馆",
            "清吧",
            "酒廈",
            "lounge",
            "娱乐餐饮",
            "夜宵摘",
            "外卓",
        ],
        "priority": 8,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },
    "performing_arts": {
        "name": "演艺/剧场空间",
        "name_en": "performing arts theater concert hall opera auditorium stage cinema ballroom",
        "keywords": [
            "剧院",
            "剧场",
            "音乐厅",
            "演艺中心",
            "歌剧院",
            "音乐会场",
            "露天剧场",
            "礼堂",
            "演出中心",
            "大剧院",
            "电影院",
            "舞厅",
            "音乐俱乐部",
        ],
        "secondary_keywords": [
            "舞台",
            "演出",
            "表演",
            "观演",
            "戏剧",
            "排演",
            "影院",
            "多厅影城",
            "放映厅",
        ],
        "priority": 8,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },
    "public_cultural": {
        "name": "文化展陈/科教场馆",
        "name_en": "cultural museum exhibition gallery art center science visitor aquarium zoo planetarium",
        "keywords": [
            # 展陈建筑
            "博物馆",
            "美术馆",
            "展览馆",
            "展览中心",
            "展馆",
            "展厅",
            "文化中心",
            "艺术馆",
            "艺术中心",
            "视觉艺术中心",
            "图书馆",
            # 科教建筑
            "科学中心",
            "游客中心",
            "动物园",
            "水族馆",
            "天文馆",
            "解说中心",
            "青年活动中心",
        ],
        "secondary_keywords": [
            "展览",
            "展示",
            "画廊",
            "书屋",
            "艺术空间",
            "文物",
            "文化遗址",
            "传统建筑展",
            # 展陈装置/临时装置
            "展陈装置",
            "临时装置",
            "装置艺术",
            # 瞭望塔/自然博物馆（科教建筑周边）
            "瞭望塔",
            "自然博物馆",
            "昆曲",
        ],
        "priority": 8,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },
    "landscape_outdoor": {
        "name": "景观/公共户外空间",
        "name_en": "landscape architecture outdoor public space park plaza waterfront urban garden",
        "keywords": [
            "景观设计",
            "城市公园",
            "公共广场",
            "滨水景观",
            "花园设计",
            "公共绿地",
            "景观装置",
            "口袋公园",
            "屋顶花园",
            "庭院设计",
        ],
        "secondary_keywords": [
            "景观",
            "园林",
            "户外",
            "广场",
            "公园",
            "步道",
            "滨水",
            "绿化",
            "植被",
            "水景",
            "铺装",
            "人行道",
            "林荫",
            "生态",
        ],
        "priority": 8,
        "min_secondary_hits": 1,
        "include_in_prompt": True,
    },
    "community_public": {
        "name": "社区/公共服务空间",
        "name_en": "community public service center civic shared space neighborhood memorial senior station elderly",
        "keywords": [
            "社区活动中心",
            "公共服务中心",
            "市民中心",
            "社区图书馆",
            "社区书屋",
            "社区服务中心",
            "居委会",
            "邻里中心",
            "社区食堂",
            "社区公园",
            "社区中心",
            # 城市新型社区设施
            "长者食堂",
            "銀发驿站",
            "老年活动室",
            "共享洗衣房",
            "社区健身角",
            "无障碍改造社区",
        ],
        "secondary_keywords": [
            "社区",
            "公益空间",
            "共享厨房",
            "避难所",
            "公共客厅",
            "社会服务",
            "社区改造",
            "留守儿童",
            "社区图书角",
            "公共活动",
            "绪念碑",
            "绪念广场",
            "城市绪念",
            "銀发服务",
            "居家养老",
            "互助养老",
        ],
        "priority": 8,
        "min_secondary_hits": 1,
        "include_in_prompt": True,
    },
    # ══════════════════════════════════════════════════════════════════════════
    # 优先级 7 — 商业/办公/专业类
    # ══════════════════════════════════════════════════════════════════════════
    "commercial_retail": {
        "name": "商业零售/综合体",
        "name_en": "retail commercial shop brand store mall shopping complex",
        "keywords": ["商场", "综合体", "购物中心", "专卖店", "买手店", "百货"],
        "secondary_keywords": ["零售", "店铺", "品牌", "门店", "旗舰店", "购物", "商业街区"],
        "priority": 7,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },
    "brand_experience": {
        "name": "品牌旗舰/体验店",
        "name_en": "brand flagship experience store showroom concept store immersive",
        "keywords": ["旗舰店", "品牌体验店", "概念店", "体验店", "品牌展示馆"],
        "secondary_keywords": ["品牌旗舰", "香薰品牌", "生活方式品牌", "展示空间", "品牌叙事"],
        "priority": 7,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },
    "commercial_office": {
        "name": "办公/联合办公",
        "name_en": "office coworking workspace studio research center corporate incubator makerspace accelerator creator",
        "keywords": [
            "办公室",
            "写字楼",
            "联合办公",
            "工作室",
            "研发中心",
            "总部大楼",
            # 新型工作场所
            "孵化器",
            "加速器",
            "众创空间",
            "创客空间",
            "makerspace",
            "电商仓储办公",
            "直播办公（办公性质）",
        ],
        "secondary_keywords": [
            "办公",
            "会议室",
            "工位",
            "共享办公",
            "创意园",
            "产业园",
            "数据中心",
            "创业团队",
            "起步世界",
            "创立者社区",
        ],
        "priority": 7,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },
    "commercial_enterprise": {
        "name": "企业空间/品牌展厅",
        "name_en": "corporate enterprise brand showroom experience center headquarters",
        "keywords": ["企业总部", "展厅", "接待中心", "企业展示", "体验中心"],
        "secondary_keywords": [
            "企业文化",
            "员工空间",
            "运营",
            "商业模式",
            "坪效",
            "俱乐部",
        ],
        "priority": 7,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },
    "healthcare_wellness": {
        "name": "医疗/康养/养老",
        "name_en": "healthcare wellness senior living medical clinic spa rehabilitation veterinary TCM elderly adaptive",
        "keywords": [
            "医院",
            "诊所",
            "养老院",
            "康养中心",
            "月子中心",
            "体检中心",
            "保健中心",
            "牙科诊所",
            "水痗中心",
            "温泉",
            "桑拿",
            # 适老化
            "适老化改造",
            "适老化",
            "无障碍设计",
            "老人房",
            "銀发站",
            "老年住宅改造",
            "针对老人的设计",
            # 中医馆/心理
            "中医馆",
            "针灸推拿",
            "心理和询室",
            "正念空间",
            "冥想山",
            # 医美（与 beauty_personal_care 共丫，主词赋余正规医疗语境）
            "医疗美容",
            "整形外科",
            "整形诊所",
        ],
        "secondary_keywords": [
            "护理",
            "康复",
            "老年",
            "养生",
            "医疗",
            "痗养",
            "健康",
            "宁静病房",
            "临终关怀",
            "心理干预",
            "水痗",
            "spa",
            "澡堂",
            "汗蒸",
            "药浴",
            "兽医",
            "动物医院",
            "医学实验室",
            "药疗设施",
            # 适老化次要
            "老人",
            "老年人",
            "扁扇手扶",
            "坎坡",
            "轮椅",
            "坛板",
        ],
        "priority": 7,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },
    "sports_entertainment_arts": {
        "name": "体育/健身/运动场馆",
        "name_en": "sports fitness arena stadium aquatics gymnasium track field skating frisbee paddle surf climbing trampoline",
        "keywords": [
            "体育馆",
            "体育场",
            "运动场",
            "游泳馆",
            "游泳池",
            "健身房",
            "球场",
            "足球场",
            "篮球场",
            "檪榄球场",
            "跡马场",
            "健身俱乐部",
            "滑板公园",
            "滑雪中心",
            "冰场",
            # 新兴运动项目
            "电竞馆",
            "电竞中心",
            "污遢环",
            "飞爹卢环",
            "攀岩馆",
            "屋内攀岩",
            "蹦寭公园",
            "蹦寭场",
            "室内滑雪",
            "高尔夫练习场",
            "台球应允容",
            "刑棒馆",
            "膙弓馆",
        ],
        "secondary_keywords": [
            "运动",
            "健身",
            "竞技",
            "训练",
            "马术",
            "射击",
            "攀岩",
            "游乐设施",
            "娱乐",
            "活动课",
            "星期训练",
        ],
        "priority": 7,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },
    "transportation_civic": {
        "name": "交通/市政/公共行政",
        "name_en": "transportation civic infrastructure airport metro station government courthouse embassy",
        "keywords": [
            # 交通建筑
            "交通枢纽",
            "地铁站",
            "机场",
            "火车站",
            "高铁站",
            "港口",
            "码头",
            "停车场",
            "公交站",
            "交通中心",
            "游船码头",
            "船坞",
            # 行政/公共建筑
            "市政厅",
            "市政建筑",
            "政府大楼",
            "行政中心",
            "法院",
            "大使馆",
            # 安保建筑
            "消防站",
            "警察局",
            "紧急服务",
        ],
        "secondary_keywords": [
            "交通",
            "枢纽",
            "公共交通",
            "基础设施",
            "桥梁",
            "人行桥",
            "公路桥",
            "能源站",
            "变电站",
            "水务",
            "物流中心",
            "部门建筑",
            "行政楼",
            "办事处",
            "司法",
        ],
        "priority": 7,
        "min_secondary_hits": 1,
        "include_in_prompt": True,
    },
    # ══════════════════════════════════════════════════════════════════════════
    # 优先级 8 补充 — 休闲娱乐/婚宴庆典/亲子早教/存量住宅改造（v8.0 新增）
    # ══════════════════════════════════════════════════════════════════════════
    "leisure_entertainment": {
        "name": "休闲娱乐/水会棋牌KTV",
        "name_en": "leisure entertainment KTV karaoke spa bathhouse billiards escape room board game mahjong",
        "keywords": [
            "ktv",
            "量贩ktv",
            "一声ktv",
            "棋牌室",
            "麻将馆",
            "棋牌",
            "水会",
            "洗浴中心",
            "澡堂子",
            "男宾女宾",
            "洗浴",
            "密室逃脱",
            "剧本杀",
            "密室",
            "沉浸式密室",
            "桌游馆",
            "轰趴馆",
            "轰趴",
            "真人cs",
            "激光枪战",
            "电玩城",
            "游戏厅",
            "娱乐城",
        ],
        "secondary_keywords": [
            "包厢",
            "娱乐",
            "会员卡",
            "大厅",
            "休闲",
            "台球厅",
            "棋牌文化",
            "休闲服务",
            "娱乐空间",
            "消费场所",
        ],
        "priority": 8,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },
    "wedding_banquet": {
        "name": "婚庆宴会/庆典空间",
        "name_en": "wedding banquet ceremony hall celebration event venue bridal",
        "keywords": [
            "婚宴",
            "婚礼堂",
            "婚礼会所",
            "婚礼场地",
            "婚庆公司",
            "宴会厅",
            "宴请厅",
            "宴会中心",
            "宴请空间",
            "庆典会所",
            "答谢宴",
            "颁奖典礼场地",
            "婚宴酒楼",
            "宴会楼",
            "满月宴",
            "升学宴",
            "寿宴厅",
        ],
        "secondary_keywords": [
            "婚礼",
            "庆典",
            "仪式感",
            "酒席",
            "席面",
            "摆席",
            "宴席",
            "堂食大厅",
            "主题婚礼",
            "婚礼策划",
        ],
        "priority": 8,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },
    "children_family": {
        "name": "亲子/早教/儿童空间",
        "name_en": "children family early education daycare toddler playground parenting center baby gym",
        "keywords": [
            "早教中心",
            "早教",
            "亲子乐园",
            "儿童乐园",
            "儿童游乐场",
            "绘本馆",
            "亲子餐厅",
            "宝宝",
            "托育",
            "托育中心",
            "蒙台梭利",
            "感统训练室",
            "感统",
            "baby gym",
            "亲子主题",
            "儿童主题",
            "儿童活动中心",
        ],
        "secondary_keywords": [
            "儿童",
            "小朋友",
            "幼儿",
            "亲子",
            "家长",
            "育儿",
            "安全",
            "圆角",
            "低甲醛",
            "无毒",
            "启蒙",
            "启智",
        ],
        "priority": 8,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },
    "residential_renovation": {
        "name": "存量住宅改造/二手房翻新",
        "name_en": "renovation existing residential second-hand house renovation remodel old apartment makeover",
        "keywords": [
            "二手房",
            "二手房改造",
            "旧房翻新",
            "老房改造",
            "老旧住宅",
            "重新装修",
            "格局改造",
            "格局重整",
            "老破小",
            "回迁房",
            "翻新改造",
            "老宅改造",
            "原有户型",
            "房龄",
        ],
        "secondary_keywords": [
            "翻新",
            "改造",
            "重装",
            "拆改",
            "承重",
            "原来",
            "之前",
            "住了多年",
            "原房东",
            "原有格局",
            "局部改造",
        ],
        "priority": 8,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },
    # ══════════════════════════════════════════════════════════════════════════
    # 优先级 7 补充 — 美容美发/汽车展厅/直播媒体/快闪临时（v8.0 新增）
    # ══════════════════════════════════════════════════════════════════════════
    "beauty_personal_care": {
        "name": "美容美发/生活美学门店",
        "name_en": "beauty salon hair studio nail spa lash brow tattoo aesthetic clinic personal care",
        "keywords": [
            "美发沙龙",
            "发型工作室",
            "美发店",
            "理发店",
            "剪发",
            "美容院",
            "美容工作室",
            "美甲店",
            "美睫",
            "纹身馆",
            "轻医美",
            "医美诊所",
            "皮肤管理",
            "无创美容",
            "造型工作室",
            "整体形象",
            "香薰spa工作室",
        ],
        "secondary_keywords": [
            "美容",
            "美发",
            "护肤",
            "发色",
            "烫发",
            "染发",
            "造型",
            "顾客",
            "师傅",
            "操作台",
            "洗剪吹",
        ],
        "priority": 7,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },
    "automotive_showroom": {
        "name": "汽车展厅/4S店/改装",
        "name_en": "automotive showroom 4S car dealership EV experience center auto modification supercar club",
        "keywords": [
            "4s店",
            "4s店展厅",
            "汽车展厅",
            "汽车展示中心",
            "新能源汽车体验店",
            "汽车体验中心",
            "汽车改装店",
            "改装车",
            "试驾中心",
            "超跑俱乐部",
            "汽车美容",
            "洗车房",
            "汽车主题",
        ],
        "secondary_keywords": [
            "汽车",
            "车",
            "售车",
            "购车",
            "看车",
            "品牌店",
            "展车",
            "试驾",
            "交车区",
            "维修区",
        ],
        "priority": 8,
        "min_secondary_hits": 1,
        "include_in_prompt": True,
    },
    "digital_media_studio": {
        "name": "直播/拍摄/媒体基地",
        "name_en": "live streaming studio MCN filming base media production creator photography commercial shoot",
        "keywords": [
            "直播基地",
            "直播间",
            "直播间设计",
            "拍摄基地",
            "拍摄场地",
            "mcn机构",
            "影棚",
            "商业摄影棚",
            "摄影基地",
            "短视频基地",
            "内容创作基地",
            "录播室",
        ],
        "secondary_keywords": [
            "直播",
            "带货",
            "主播",
            "博主",
            "kol",
            "up主",
            "内容创作",
            "摄影",
            "拍摄",
            "录制",
            "布景",
        ],
        "priority": 7,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },
    "popup_temporary": {
        "name": "快闪/临时装置空间",
        "name_en": "pop-up temporary installation flash store limited event space immersive experience",
        "keywords": [
            "快闪店",
            "快闪",
            "pop-up",
            "popup",
            "限时体验店",
            "快闪餐厅",
            "限时店",
            "期间限定",
            "快闪空间",
            "发布空间",
            "新品发布场地",
        ],
        "secondary_keywords": [
            "临时",
            "限时",
            "短期",
            "拆除",
            "可拆卸",
            "快速搭建",
            "模块化",
            "装置",
            "互动体验",
        ],
        "priority": 7,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },
    # ══════════════════════════════════════════════════════════════════════════
    # 优先级 6 — 细分/兜底类型
    # ══════════════════════════════════════════════════════════════════════════
    "special_function": {
        "name": "专项功能空间",
        "name_en": "specialty functional space home theater studio piano wine cellar cigar meditation yoga recording lab",
        "keywords": [
            "影音室",
            "家庭影院",
            "茶室",
            "书房",
            "衣帽间",
            "收藏室",
            # 新增专项空间类型
            "鈢琴室",
            "乐器房",
            "红酒窖",
            "雪茄室",
            "私人图书室",
            "冥想室",
            "瑜伽房",
            "家用瑜伽",
            "第二书房",
        ],
        "secondary_keywords": [
            "隔音",
            "声学",
            "冥想空间",
            "实验室",
            "工坊",
            "训练室",
            "拍摄间",
            "录音室",
            "专业灯光",
        ],
        "priority": 6,
        "min_secondary_hits": 2,
        "include_in_prompt": True,
    },
    "residential_collective": {
        "name": "集合住宅/公共住房",
        "name_en": "collective housing affordable apartment complex social housing co-living loft",
        "keywords": [
            "公租房",
            "保障房",
            "集合住宅",
            "住宅楼",
            "公寓楼",
            "居住综合体",
            "住宅小区",
            "人才公寓",
            "廉租房",
            "社会住房",
            "共享生活",
            "共居公寓",
        ],
        "secondary_keywords": [
            "集合",
            "多层",
            "高层住宅",
            "居住区",
            "住宅区",
            "宿舍楼",
            "学生公寓",
            "员工宿舍",
            "共居",
            "loft公寓",
            "阁楼公寓",
            "联排住宅",
        ],
        "priority": 6,
        "min_secondary_hits": 1,
        "include_in_prompt": True,
    },
    "hybrid_residential_commercial": {
        "name": "住商混合",
        "name_en": "hybrid residential commercial mixed use",
        "keywords": [],
        "secondary_keywords": [],
        "priority": 6,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },
    # ══════════════════════════════════════════════════════════════════════════
    # 优先级 5 — 个人住宅（默认兜底）
    # ══════════════════════════════════════════════════════════════════════════
    "personal_residential": {
        "name": "个人住宅",
        "name_en": "residential apartment villa home interior private house villa duplex penthouse loft studio flat",
        "keywords": [
            "住宅",
            "公寓",
            "别墅",
            "房子",
            "新房",
            "私宅",
            "住房",
            "自住",
            # 户型规格
            "三房",
            "两房",
            "四房",
            "三居室",
            "两居室",
            "一居室",
            "五居室",
            "大平层",
            "小平层",
            "平层",
            # 楼型/产品形态
            "独栋别墅",
            "独栋",
            "联排别墅",
            "联排",
            "叠拼别墅",
            "叠拼",
            "洋房",
            "花园洋房",
            "豪宅",
            "豪宅公寓",
            "复式",
            "跃层",
            "顶层复式",
            "顶层",
            "loft户型",
            "阁楼",
            # 小户型
            "小户型",
            "迎为公寓",
            "微户型",
            "单间",
            # 持有/病态
            "婚房",
            "首套房",
            "改善型住宅",
            "度假屋",
            "度假宅",
            "自建房",
        ],
        "secondary_keywords": [
            "卧室",
            "客厅",
            "厨房",
            "卫生间",
            "装修",
            "家装",
            "家居",
            "户型",
            # 延伸（次要）
            "主卧",
            "次卧",
            "儿童房",
            "玄关",
            "过道",
            "阳台",
            "书房",
            "餐厅",
            "客餐一体",
            "开放式厨房",
        ],
        "priority": 5,
        "min_secondary_hits": 0,
        "include_in_prompt": True,
    },
}

# =============================================================================
# 向后兼容别名 — 旧 ID → 新 ID
# 已有数据库/状态中存储了旧 ID 的，可通过此表规范化到当前 ID
# =============================================================================
LEGACY_TYPE_ALIASES: Dict[str, str] = {
    # 旧 ontology 体系 ID → 新 detector 体系 ID
    "cultural_educational": "public_cultural",  # v3.0 → v3.2
    "office_coworking": "commercial_office",
    "hospitality_tourism": "commercial_hospitality",
    "commercial_enterprise": "commercial_enterprise",  # 保持，部分含义不同但沿用
    "urban_renewal": "urban_renewal_market",
    "heritage_conservation": "urban_renewal_heritage",
    # v3.2 新增：ontology.yaml 框架重命名产生的旧别名
    "industrial_manufacturing": "industrial_conversion",
    "education_research": "educational_facility",
    "transportation_infrastructure": "transportation_civic",
    # v8.0 新增：8 个新分类的备用别名（预留向前兼容）
    "entertainment_leisure": "leisure_entertainment",
    "bathhouse_ktv": "leisure_entertainment",
    "wedding_hall": "wedding_banquet",
    "banquet_hall": "wedding_banquet",
    "early_education": "children_family",
    "kids_space": "children_family",
    "house_renovation": "residential_renovation",
    "old_house_renovation": "residential_renovation",
    "hair_salon": "beauty_personal_care",
    "beauty_salon": "beauty_personal_care",
    "car_showroom": "automotive_showroom",
    "live_streaming": "digital_media_studio",
    "flash_store": "popup_temporary",
}


# =============================================================================
# 公用工具函数 — 全局唯一出处，下游直接 import 使用
# =============================================================================


def get_type_label(type_id: str, fallback: str = "") -> str:
    """
    根据项目类型 ID 返回中文显示标签。

    这是全局唯一的 ID→标签 映射出处，所有模块必须调用此函数，
    禁止在其他文件中自行维护字典。

    Args:
        type_id: 项目类型 ID（支持旧别名自动转换）
        fallback: 找不到时的默认值，默认返回 type_id 本身

    Returns:
        中文标签字符串
    """
    # 合并注册表：静态 + 扩展
    merged = {**PROJECT_TYPE_REGISTRY, **_load_extension_registry()}
    canonical_id = LEGACY_TYPE_ALIASES.get(type_id, type_id)
    entry = merged.get(canonical_id)
    if entry:
        return entry["name"]
    return fallback if fallback is not None else type_id


def get_type_name_en(type_id: str) -> str:
    """返回英文检索上下文（供 query_builder 使用，含扩展类型）。"""
    merged = {**PROJECT_TYPE_REGISTRY, **_load_extension_registry()}
    canonical_id = LEGACY_TYPE_ALIASES.get(type_id, type_id)
    entry = merged.get(canonical_id)
    if entry:
        return entry.get("name_en", type_id)
    return type_id


def get_all_type_ids(include_in_prompt_only: bool = False) -> List[str]:
    """
    返回全部项目类型 ID 列表（静态注册表 + 已审批扩展）。

    Args:
        include_in_prompt_only: True → 仅返回 include_in_prompt=True 的类型
    """
    merged = {**PROJECT_TYPE_REGISTRY, **_load_extension_registry()}
    if include_in_prompt_only:
        return [tid for tid, cfg in merged.items() if cfg.get("include_in_prompt", True)]
    return list(merged.keys())


def normalize_type_id(type_id: str) -> str:
    """将旧别名 ID 规范化为当前注册表中的标准 ID。"""
    return LEGACY_TYPE_ALIASES.get(type_id, type_id)


# =============================================================================
# 业态父分类映射（Steps 9-12 两阶段检测）
# type_id → parent_type（宽泛业态桶，供两阶段检测的第一阶段使用）
# =============================================================================
PARENT_TYPE_MAP: Dict[str, str] = {
    # 住宅
    "personal_residential": "residential",
    "residential_renovation": "residential",
    # 商业餐饮/酒店
    "commercial_dining": "hospitality",
    "commercial_hospitality": "hospitality",
    "wedding_banquet": "hospitality",
    # 办公
    "commercial_office": "office",
    "digital_media_studio": "office",
    # 零售
    "commercial_retail": "retail",
    "beauty_personal_care": "retail",
    "automotive_showroom": "retail",
    "popup_temporary": "retail",
    # 休闲娱乐
    "leisure_entertainment": "leisure",
    "sports_entertainment_arts": "leisure",
    "performing_arts": "leisure",
    # 教育/亲子
    "children_family": "education",
    "educational_facility": "education",
    # 医疗/康养
    "healthcare_wellness": "healthcare",
    # 公共/社区
    "community_public": "public",
    "public_cultural": "public",
    "transportation_civic": "public",
    "rural_construction": "public",
    # 工业更新
    "industrial_conversion": "industrial",
    "urban_renewal_market": "urban_renewal",
    "urban_renewal_heritage": "urban_renewal",
    # 特殊
    "landscape_outdoor": "outdoor",
    "religious_spiritual": "special",
    "special_function": "special",
}

# =============================================================================
# 专项标签映射（Steps 9-12）
# (触发关键词, specialty_tag) — 按精确度降序（长词优先）
# =============================================================================
SPECIALTY_TAG_MAP: List[Tuple[str, str]] = [
    # 餐饮细分
    ("自助餐", "buffet"),
    ("烧烤", "bbq"),
    ("火锅", "hotpot"),
    ("咖啡馆", "cafe"),
    ("茶饮店", "tea_bar"),
    # 住宅细分
    ("大平层", "flat_luxury"),
    ("独栋别墅", "detached_villa"),
    ("叠拼", "stacked_mansion"),
    ("loft", "loft"),
    ("跃层", "duplex"),
    ("复式", "duplex"),
    ("别墅", "villa"),
    ("公寓", "apartment"),
    # 酒店细分
    ("精品酒店", "boutique_hotel"),
    ("树屋民宿", "treehouse"),
    ("胶囊酒店", "capsule_hotel"),
    ("民宿", "b_and_b"),
    # 办公细分
    ("共享办公", "co_working"),
    ("孵化器", "incubator"),
    ("makerspace", "makerspace"),
    # 娱乐细分
    ("ktv", "ktv"),
    ("密室", "escape_room"),
    ("棋牌", "mahjong_room"),
    ("水会", "spa_club"),
    # 医疗细分
    ("牙科", "dental"),
    ("中医", "tcm"),
    ("适老", "age_friendly"),
    ("养老", "elderly_care"),
    ("医美", "aesthetic_medicine"),
    # 教育细分
    ("幼儿园", "kindergarten"),
    ("早教", "early_childhood"),
    # 汽车细分
    ("4s店展厅", "auto_4s_showroom"),
    ("汽车展厅", "auto_showroom"),
    # 直播细分
    ("直播间", "live_studio"),
    ("mcn", "mcn_studio"),
    # 快闪
    ("快闪", "popup"),
    # 婚宴细分
    ("婚宴", "wedding_banquet_hall"),
    ("宴会厅", "banquet_hall"),
]


def _build_exclusivity_weights(registry: Dict[str, Any]) -> Dict[str, float]:
    """
    计算关键词排他性权重（Step 14）。

    - 仅出现在 1 个类型中 → 1.5（独占关键词，命中更可靠）
    - 出现在 2 个类型中   → 1.2（稀有词，小幅加成）
    - 出现在 3+ 个类型中  → 1.0（通用词，不加成）
    """
    keyword_freq: Dict[str, int] = {}
    for cfg in registry.values():
        for kw in cfg.get("keywords", []) + cfg.get("secondary_keywords", []):
            keyword_freq[kw] = keyword_freq.get(kw, 0) + 1
    weights: Dict[str, float] = {}
    for kw, freq in keyword_freq.items():
        if freq == 1:
            weights[kw] = 1.5
        elif freq == 2:
            weights[kw] = 1.2
        else:
            weights[kw] = 1.0
    return weights


# 保持向后兼容 — 旧代码直接引用 PROJECT_TYPE_KEYWORDS 的地方仍可访问
PROJECT_TYPE_KEYWORDS = PROJECT_TYPE_REGISTRY


class ProjectTypeDetector:
    """
    项目类型自动检测器 — 所有关键词逻辑从 PROJECT_TYPE_REGISTRY 读取。

    v7.200: 统一注册表驱动，消除重复逻辑
    v7.210: 支持扩展类型热重载（data/project_type_extensions.json）
    """

    # 类级别合并注册表（静态 + 扩展）
    _merged_registry: Optional[Dict[str, Any]] = None

    def __init__(self):
        self.registry = self._get_registry()
        # Step 14: 预计算排他性权重（基于合并注册表）
        self._excl_weights = _build_exclusivity_weights(self.registry)
        logger.info(
            "[v8.1] 项目类型检测器初始化，共 {} 种类型（含 {} 个扩展）".format(
                len(self.registry), len(self.registry) - len(PROJECT_TYPE_REGISTRY)
            )
        )

    @classmethod
    def _get_registry(cls) -> Dict[str, Any]:
        """获取合并注册表（静态 + 扩展），带缓存"""
        if cls._merged_registry is None:
            cls._merged_registry = {**PROJECT_TYPE_REGISTRY, **_load_extension_registry()}
        return cls._merged_registry

    @classmethod
    def reload_extensions(cls) -> int:
        """
        热重载扩展类型（管理员审批新类型后调用）。

        Returns:
            当前扩展类型数量
        """
        extensions = _load_extension_registry()
        cls._merged_registry = {**PROJECT_TYPE_REGISTRY, **extensions}
        logger.info(f"[TypeRegistry] 热重载完成，共 {len(cls._merged_registry)} 种类型，{len(extensions)} 个扩展")
        return len(extensions)

    @staticmethod
    def _get_specialty_tag(combined_text: str) -> Optional[str]:
        """Step 11: 从合并文本中提取最精确的专项标签（SPECIALTY_TAG_MAP 按序首次命中）"""
        for trigger, tag in SPECIALTY_TAG_MAP:
            if trigger in combined_text:
                return tag
        return None

    @staticmethod
    def _get_parent_type(type_id: str) -> Optional[str]:
        """Step 9: 返回 type_id 对应的宽泛业态父分类"""
        return PARENT_TYPE_MAP.get(type_id)

    def detect(
        self,
        user_input: str,
        confirmed_tasks: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[Optional[str], float, str]:
        """
        检测项目类型。

        Args:
            user_input: 用户原始输入（或预处理后的合并文本）
            confirmed_tasks: 确认的任务列表（可选）

        Returns:
            (project_type, confidence, reason)
            - project_type : 类型 ID；若完全无匹配，返回 None（触发通用框架）
            - confidence   : 0.0–1.0
            - reason       : 人类可读的匹配说明
        """
        # ── Step 6: 别名预处理 ─────────────────────────────────────────────
        try:
            from .type_alias_normalizer import normalize_input

            preprocessed = normalize_input(user_input)
        except Exception:
            preprocessed = user_input

        # 合并文本
        combined_text = preprocessed.lower()
        if confirmed_tasks:
            for task in confirmed_tasks:
                combined_text += " " + task.get("title", "").lower()
                combined_text += " " + task.get("description", "").lower()

        # ── Step 13: 预计算否定区间 ───────────────────────────────────────────
        try:
            from .type_alias_normalizer import extract_negated_spans, is_negated

            negated_spans = extract_negated_spans(combined_text)
        except Exception:
            negated_spans = []
            is_negated = lambda kw, txt, spans: False  # noqa: E731

        scores: Dict[str, Dict[str, Any]] = {}

        for type_id, config in self.registry.items():
            # hybrid_residential_commercial 只在外部逻辑合成，不参与关键词匹配
            if not config.get("keywords"):
                continue

            # ── Step 13: 否定词过滤 ───────────────────────────────────────────
            def _hits_with_negation(keywords: List[str]) -> Tuple[int, float, List[str]]:
                """返回 (命中数, 加权分, 命中词列表)，否定词语境下的命中不计"""
                count = 0
                weighted = 0.0
                matched: List[str] = []
                for kw in keywords:
                    if kw not in combined_text:
                        continue
                    if negated_spans and is_negated(kw, combined_text, negated_spans):
                        continue  # 否定语境，跳过
                    # ── Step 14: 排他性权重 ───────────────────────────────────
                    w = self._excl_weights.get(kw, 1.0)
                    count += 1
                    weighted += w
                    matched.append(kw)
                return count, weighted, matched

            primary_count, primary_weighted, primary_matched = _hits_with_negation(config["keywords"])
            secondary_count, secondary_weighted, secondary_matched = _hits_with_negation(
                config.get("secondary_keywords", [])
            )

            # min_secondary_hits：primary=0 时的次要命中阈值
            min_sec = config.get("min_secondary_hits", 0)
            if primary_count == 0:
                if min_sec > 0 and secondary_count < min_sec:
                    continue
                elif min_sec == 0 and secondary_count == 0:
                    continue

            # ── Step 14: 带权重的得分（排他性关键词贡献更高）────────────────
            score = primary_weighted * 2 + secondary_weighted

            scores[type_id] = {
                "score": score,
                "priority": config["priority"],
                "primary_hits": primary_count,
                "secondary_hits": secondary_count,
                "matched": primary_matched + secondary_matched,
                "name": config["name"],
            }

        if not scores:
            # 完全无匹配 → 返回 None，上层可决定走通用框架
            logger.info("[v8.1] 项目类型未匹配，建议触发通用框架")
            return None, 0.0, "无关键词命中"

        # 按 score × priority 降序
        sorted_types = sorted(
            scores.items(),
            key=lambda x: x[1]["score"] * x[1]["priority"],
            reverse=True,
        )

        best_type_id, best_info = sorted_types[0]
        confidence = min(0.95, 0.4 + best_info["score"] * 0.1)
        reason = "匹配关键词: " + ", ".join(best_info["matched"][:4])

        # ── Step 15: top-2 融合提示 ───────────────────────────────────────────
        if len(sorted_types) >= 2:
            second_type_id, second_info = sorted_types[1]
            best_score_val = best_info["score"] * best_info["priority"]
            second_score_val = second_info["score"] * second_info["priority"]
            if best_score_val > 0 and second_score_val / best_score_val >= 0.8:
                # 第二名得分 ≥80% 第一名 → 附加弱提示（不影响主结果）
                reason += f" | 次选: {second_info['name']} ({second_type_id})"

        logger.info(f"[v8.1] 检测结果: {best_info['name']} ({best_type_id}), " f"置信度: {confidence:.0%}, {reason}")
        return best_type_id, confidence, reason

    def detect_with_details(
        self,
        user_input: str,
        confirmed_tasks: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        检测项目类型（返回详细信息）。

        v8.1 新增字段：
          parent_type   : 宽泛业态桶（Steps 9-10）
          specialty_tag : 细粒度子类型（Steps 11-12）
          secondary_type: 第二候选类型（Step 15），得分差 ≤20% 时非空
          is_ambiguous  : True 表示主次候选得分接近，建议追问确认
        """
        project_type, confidence, reason = self.detect(user_input, confirmed_tasks)

        # ── Step 10: 提取 parent_type ─────────────────────────────────────────
        parent_type = self._get_parent_type(project_type) if project_type else None

        # ── Step 11: 提取 specialty_tag ──────────────────────────────────────
        try:
            from .type_alias_normalizer import normalize_input

            combined = normalize_input(user_input).lower()
        except Exception:
            combined = user_input.lower()
        if confirmed_tasks:
            for t in confirmed_tasks:
                combined += " " + t.get("title", "").lower()
        specialty_tag = self._get_specialty_tag(combined)

        # ── Step 15: 解析 reason 中的次选 ────────────────────────────────────
        secondary_type: Optional[str] = None
        secondary_name: Optional[str] = None
        is_ambiguous = False
        if " | 次选: " in reason:
            try:
                secondary_part = reason.split(" | 次选: ")[1]
                # 格式: "名称 (type_id)"
                secondary_type = secondary_part.split("(")[1].rstrip(")")
                secondary_name = secondary_part.split("(")[0].strip()
                is_ambiguous = True
            except Exception:
                pass

        if project_type is None:
            return {
                "project_type": None,
                "project_type_name": "未识别",
                "confidence": 0.0,
                "reason": reason,
                "parent_type": None,
                "specialty_tag": specialty_tag,
                "secondary_type": None,
                "secondary_type_name": None,
                "is_ambiguous": False,
                "all_matches": [],
            }

        return {
            "project_type": project_type,
            "project_type_name": get_type_label(project_type),
            "confidence": confidence,
            "reason": reason,
            "parent_type": parent_type,
            "specialty_tag": specialty_tag,
            "secondary_type": secondary_type,
            "secondary_type_name": secondary_name,
            "is_ambiguous": is_ambiguous,
            "all_matches": [],
        }


# =============================================================================
# 便捷函数
# =============================================================================


def detect_project_type(
    user_input: str,
    confirmed_tasks: Optional[List[Dict[str, Any]]] = None,
    default: str = "personal_residential",
) -> str:
    """
    便捷函数：检测项目类型，无匹配时返回 default。

    Args:
        user_input: 用户原始输入
        confirmed_tasks: 确认的任务列表（可选）
        default: 无匹配时的默认类型 ID

    Returns:
        项目类型 ID
    """
    detector = ProjectTypeDetector()
    project_type, _, _ = detector.detect(user_input, confirmed_tasks)
    return project_type if project_type is not None else default


def detect_project_type_with_confidence(
    user_input: str,
    confirmed_tasks: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[Optional[str], float]:
    """
    便捷函数：检测项目类型（带置信度）。

    Returns:
        (项目类型ID或None, 置信度)
    """
    detector = ProjectTypeDetector()
    project_type, confidence, _ = detector.detect(user_input, confirmed_tasks)
    return project_type, confidence
