// components/report/ExpertReportAccordion.tsx
// 专家报告手风琴组件

'use client';

import { FC, useState } from 'react';
import { ChevronDown, ChevronUp, User, Briefcase, Download, Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import ReactDOMServer from 'react-dom/server';

interface ExpertReportAccordionProps {
  expertReports: Record<string, string>;
  userInput?: string;
  sessionId?: string;  // 用于后端 PDF 下载 API
}

// 专家角色颜色映射
const EXPERT_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  'V2': { bg: 'bg-purple-500/20', text: 'text-purple-400', border: 'border-purple-500/30' },
  'V3': { bg: 'bg-blue-500/20', text: 'text-blue-400', border: 'border-blue-500/30' },
  'V4': { bg: 'bg-green-500/20', text: 'text-green-400', border: 'border-green-500/30' },
  'V5': { bg: 'bg-yellow-500/20', text: 'text-yellow-400', border: 'border-yellow-500/30' },
  'V6': { bg: 'bg-red-500/20', text: 'text-red-400', border: 'border-red-500/30' },
};

// 字段名称中文映射 - 常见字段
const FIELD_LABELS: Record<string, string> = {
  // 🚫 黑名单字段（映射为空字符串，不显示技术元数据）
  'protocol_status': '',
  'protocol执行': '',
  'protocol状态': '',
  'complianceconfirmation': '',
  'compliance_confirmation': '',
  'execution_metadata': '',
  'executionmetadata': '',
  'confidence': '',
  '置信度': '',
  'completion_status': '',
  'completion记录': '',
  'completion_ratio': '',
  'quality_self_assessment': '',
  'dependencies_satisfied': '',
  
  // 核心字段
  'project_vision_summary': '项目愿景概述',
  'design_rationale': '设计理念',
  'spatial_concept': '空间概念',
  'structured_data': '结构化内容',
  'narrative_summary': '文字摘要',
  'raw_text': '原始文本',
  'validation_warnings': '校验提醒',
  'customer_journey_design': '客户旅程设计',
  'visual_merchandising_strategy': '视觉陈列策略',
  'brand_identity_integration': '品牌识别整合',
  'material_and_finish_direction': '材质与饰面方向',
  'lighting_strategy': '灯光策略',
  'sustainability_considerations': '可持续性考量',
  'implementation_priorities': '实施优先级',
  'expert_handoff_response': '专家交接响应',
  'challenge_flags': '挑战标记',
  'confidence': '置信度',
  
  // 截图中出现的字段
  'pattern_name': '模式名称',
  'description': '描述',
  'desc': '描述',
  'key_success_factors': '关键成功因素',
  'key_performance_indicators': '关键绩效指标',
  'metric': '指标',
  'target': '目标',
  'spatial_strategy': '空间策略',
  'custom_analysis': '定制分析',
  'missing_inspiration_warning': '缺失灵感警告',
  'master_work_deconstruction': '大师作品解构',
  'master_work_deconstruction_nendo': 'Nendo大师作品解构',
  'master': '大师',
  'philosophy': '设计哲学',
  'signature_methods': '标志性手法',
  'application_to_project': '项目应用',
  'business_goal_analysis': '商业目标分析',
  'operational_blueprint': '运营蓝图',
  'critical_questions_responses': '关键问题回应',
  'chosen_design_stance': '设计立场选择',
  'interpretation_framework': '解读框架',
};

// 英文单词到中文的映射（无重复，按字母顺序整理）
const WORD_TRANSLATIONS: Record<string, string> = {
  // A
  'acceleration': '加速度', 'accelerations': '加速度',
  'acoustic': '声学', 'acoustics': '声学',
  'action': '行动', 'actions': '行动',
  'activity': '活动', 'activities': '活动',
  'adaptable': '适应', 'advantage': '优点', 'advantages': '优点',
  'affecting': '影响中', 'affects': '影响到',
  'alert': '警报', 'alerts': '警报',
  'amplitude': '振幅', 'amplitudes': '振幅',
  'analyses': '分析', 'analysis': '分析',
  'answer': '答案', 'answers': '答案',
  'api': '接口', 'apis': '接口',
  'appendices': '附录', 'appendix': '附录',
  'application': '应用', 'applications': '应用',
  'approach': '方法', 'approaches': '方法',
  'architecture': '架构',
  'area': '区域', 'areas': '区域',
  'arg': '参数', 'args': '参数', 'argument': '参数', 'arguments': '参数',
  'array': '数组', 'arrays': '数组',
  'assessment': '评估', 'assessments': '评估',
  'asset': '资产', 'assets': '资产',
  'assistance': '协助',
  'atmosphere': '氛围',
  'attribute': '属性', 'attributes': '属性',
  'audio': '音频', 'audios': '音频',
  'average': '平均', 'avg': '平均',
  
  // B
  'background': '背景',
  'bad': '不良',
  'basic': '基本',
  'benchmark': '基准', 'benchmarking': '对标', 'benchmarks': '基准',
  'benefit': '收益', 'benefits': '收益',
  'best': '最佳',
  'blue': '蓝队',
  'blueprint': '蓝图', 'blueprints': '蓝图',
  'brand': '品牌', 'brands': '品牌',
  'budget': '预算', 'budgets': '预算',
  'bug': '缺陷', 'bugs': '缺陷',
  'business': '商业',
  'button': '按钮', 'buttons': '按钮',
  
  // C
  'capability': '能力', 'capabilities': '能力',
  'case': '案例', 'cases': '案例',
  'categories': '类别', 'category': '类别',
  'cell': '单元格', 'cells': '单元格',
  'challenge': '挑战', 'challenges': '挑战',
  'change': '变化', 'changes': '变化',
  'chapter': '章节', 'chapters': '章节',
  'check': '检查', 'checks': '检查',
  'choice': '选择', 'choices': '选择',
  'chosen': '选定',
  'clash': '冲突', 'clashpoints': '冲突点',
  'class': '类别', 'classes': '类别',
  'client': '客户', 'clients': '客户',
  'cluster': '集群', 'clusters': '集群',
  'collaboration': '协作',
  'collection': '集合', 'collections': '集合',
  'color': '颜色', 'colors': '颜色',
  'column': '列', 'columns': '列',
  'comment': '评论', 'comments': '评论',
  'common': '常见',
  'communication': '沟通', 'communications': '沟通',
  'competitive': '竞争', 'competition': '竞争', 'competitor': '竞争对手', 'competitors': '竞争对手',
  'complete': '完整',
  'component': '组件', 'components': '组件',
  'comprehensive': '综合',
  'concept': '概念', 'concepts': '概念',
  'conclusion': '结论', 'conclusions': '结论',
  'consideration': '考量', 'considerations': '考量',
  'constraint': '约束', 'constraints': '约束条件',
  'content': '内容', 'contents': '内容',
  'context': '背景', 'contexts': '背景',
  'control': '控件', 'controls': '控件',
  'coordination': '协调',
  'core': '核心',
  'cost': '成本', 'costs': '成本',
  'count': '计数', 'counts': '计数',
  'craft': '工艺', 'craftsmanship': '工艺',
  'creative': '创意', 'creativity': '创意',
  'criteria': '标准', 'criterion': '标准',
  'critical': '关键', 'crucial': '关键',
  'current': '当前',
  'custom': '定制', 'customer': '客户', 'customers': '客户',
  'cycle': '周期', 'cycles': '周期',
  
  // D
  'data': '数据',
  'date': '日期', 'dates': '日期',
  'day': '日', 'days': '日',
  'decision': '决策', 'decisions': '决策',
  'deconstruction': '解构', 'deconstructed': '解构',
  'deep': '深度', 'deepdive': '深度分析',
  'delay': '延迟', 'delays': '延迟',
  'deliverable': '交付物', 'deliverables': '交付物',
  'density': '密度', 'densities': '密度',
  'depth': '深度', 'depths': '深度',
  'desc': '描述', 'description': '描述', 'descriptions': '描述',
  'design': '设计', 'designs': '设计',
  'detail': '详情', 'detailed': '详细', 'details': '详情',
  'development': '开发',
  'dialog': '对话框', 'dialogs': '对话框',
  'digital': '数字',
  'direction': '方向', 'directions': '方向',
  'directory': '目录', 'directories': '目录',
  'display': '展示', 'displays': '展示',
  'dive': '分析',
  'duration': '持续时间', 'durations': '持续时间',
  
  // E
  'effect': '效果', 'effects': '效果',
  'effective': '有效',
  'efficiency': '效率', 'efficient': '高效',
  'electrical': '电气',
  'element': '元素', 'elements': '元素',
  'emotion': '情感', 'emotions': '情感',
  'energies': '能量', 'energy': '能源', 'energysaving': '节能',
  'engagement': '参与',
  'enhancement': '增强', 'enhancements': '增强',
  'entity': '实体', 'entities': '实体',
  'environment': '环境', 'environments': '环境',
  'error': '错误', 'errors': '错误',
  'essential': '必要',
  'evaluation': '评估', 'evaluations': '评估',
  'example': '示例', 'examples': '示例',
  'excellent': '优秀',
  'exceptional': '特殊',
  'execution': '执行',
  'existing': '现有',
  'expansion': '扩展',
  'expense': '费用', 'expenses': '费用',
  'experience': '体验', 'experiences': '体验',
  'expert': '专家', 'experts': '专家',
  'exploration': '探索',
  'extent': '程度', 'extents': '程度',
  'external': '外部',
  
  // F
  'factor': '因素', 'factors': '因素',
  'feasible': '可行',
  'feature': '特性', 'features': '特性',
  'feedback': '反馈', 'feedbacks': '反馈',
  'feeling': '感觉', 'feelings': '感觉',
  'field': '领域', 'fields': '字段',
  'file': '文件', 'files': '文件',
  'filter': '筛选', 'filters': '筛选',
  'final': '最终',
  'finding': '发现', 'findings': '发现',
  'finish': '饰面', 'finishes': '饰面',
  'fire': '消防',
  'first': '首要',
  'fix': '修复', 'fixes': '修复',
  'flag': '标记', 'flags': '标记',
  'flexible': '灵活',
  'flow': '流程', 'flows': '流程',
  'folder': '文件夹', 'folders': '文件夹',
  'footer': '页脚', 'footers': '页脚',
  'force': '力', 'forces': '力',
  'format': '格式', 'formats': '格式',
  'found': '发现',
  'framework': '框架', 'frameworks': '框架',
  'frequency': '频率', 'frequencies': '频率',
  'full': '完整',
  'function': '功能', 'functional': '功能', 'functions': '功能',
  'fundamental': '基础',
  'future': '未来',
  
  // G
  'general': '通用',
  'global': '全局',
  'goal': '目标', 'goals': '目标',
  'good': '良好',
  'group': '组', 'groups': '组',
  'growth': '增长',
  'guidance': '指导', 'guide': '指南', 'guideline': '指南', 'guidelines': '指南', 'guides': '指南',
  
  // H
  'handoff': '交接', 'handoffs': '交接',
  'header': '页眉', 'headers': '页眉',
  'height': '高度', 'heights': '高度',
  'helper': '辅助', 'helpers': '辅助',
  'high': '高',
  'history': '历史',
  'hour': '小时', 'hours': '小时',
  'how': '如何',
  'humidity': '湿度', 'humidities': '湿度',
  'hvac': '暖通空调',
  
  // I
  'icon': '图标', 'icons': '图标',
  'id': '标识', 'ids': '标识',
  'idea': '想法', 'ideal': '理想', 'ideas': '想法',
  'identity': '标识',
  'image': '形象', 'images': '图片',
  'impact': '影响', 'impacts': '影响',
  'implement': '实施', 'implementation': '实施', 'implementations': '实施',
  'important': '重要',
  'improvement': '改进', 'improvements': '改进',
  'indicator': '指标', 'indicators': '指标',
  'industry': '行业', 'industries': '行业',
  'info': '信息', 'information': '信息',
  'infrastructure': '基础设施',
  'initial': '初始',
  'inner': '内部',
  'innovation': '创新', 'innovations': '创新', 'innovative': '创新',
  'input': '输入', 'inputs': '输入',
  'insight': '洞察', 'insights': '洞察',
  'inspiration': '灵感', 'inspired': '灵感',
  'instance': '实例', 'instances': '实例',
  'integrated': '整合', 'integration': '整合', 'integrations': '整合',
  'interaction': '交互', 'interactions': '交互',
  'interface': '接口', 'interfaces': '接口',
  'internal': '内部',
  'interpret': '解读', 'interpretation': '解读',
  'interval': '间隔', 'intervals': '间隔',
  'intro': '简介', 'introduction': '介绍',
  'investigation': '调查', 'investigations': '调查',
  'issue': '问题', 'issues': '问题',
  'item': '项', 'items': '项目',
  'iteration': '迭代', 'iterations': '迭代', 'iteration_summary': '迭代改进总结',
  
  // J
  'journey': '旅程', 'journeys': '旅程',
  'judge': '评委', 'judges': '评委',
  
  // K
  'key': '关键', 'keys': '键',
  'kind': '种类', 'kinds': '种类',
  'kpi': '关键绩效指标', 'kpis': '关键绩效指标',
  
  // L
  'label': '标签', 'labels': '标签',
  'last': '最后',
  'layout': '布局', 'layouts': '布局',
  'length': '长度', 'lengths': '长度',
  'level': '层级', 'levels': '层级',
  'light': '灯光', 'lighting': '照明', 'lights': '灯光',
  'limit': '限制', 'limits': '限制',
  'link': '链接', 'links': '链接',
  'list': '列表', 'listing': '清单', 'lists': '列表',
  'local': '本地',
  'location': '位置', 'locations': '位置',
  'long': '长期',
  'low': '低',
  
  // M
  'main': '主要',
  'maintenance': '维护',
  'major': '主要',
  'management': '管理',
  'map': '映射', 'maps': '映射',
  'market': '市场', 'markets': '市场',
  'mass': '质量', 'masses': '质量',
  'master': '大师', 'masters': '大师',
  'material': '材料', 'materials': '材料',
  'max': '最大',
  'mechanical': '机械',
  'media': '媒体',
  'medium': '中等',
  'member': '成员', 'members': '成员',
  'menu': '菜单', 'menus': '菜单',
  'merchandising': '陈列',
  'message': '信息', 'messages': '信息',
  'method': '方法', 'methodology': '方法论', 'methods': '手法',
  'metric': '指标', 'metrics': '指标',
  'might': '可能',
  'milestone': '里程碑', 'milestones': '里程碑',
  'min': '最小',
  'minor': '次要',
  'minute': '分钟', 'minutes': '分钟',
  'mission': '使命',
  'missing': '缺失',
  'modal': '弹窗', 'modals': '弹窗',
  'mode': '模式', 'modes': '模式',
  'model': '模型', 'models': '模型',
  'module': '模块', 'modules': '模块',
  'month': '月', 'months': '月',
  'mood': '氛围',
  'multimedia': '多媒体',
  
  // N
  'name': '名称', 'names': '名称',
  'narrative': '叙事',
  'national': '国家',
  'nav': '导航', 'navigation': '导航',
  'negative': '消极',
  'nendo': 'Nendo',
  'new': '新',
  'next': '下一',
  'normal': '正常',
  'note': '备注', 'notes': '备注',
  
  // O
  'object': '对象', 'objects': '对象',
  'objective': '目标', 'objectives': '目标',
  'offset': '偏移', 'offsets': '偏移',
  'old': '旧',
  'operation': '运营', 'operational': '运营', 'operations': '运营',
  'opportunity': '机会', 'opportunities': '机会',
  'optimal': '最优',
  'optimization': '优化', 'optimizations': '优化',
  'option': '选项', 'options': '选项',
  'order': '顺序', 'orders': '顺序',
  'outcome': '成果', 'outcomes': '成果',
  'outer': '外部',
  'output': '输出', 'outputs': '输出',
  'overall': '整体',
  'overview': '概述', 'overviews': '概述',
  
  // P
  'page': '页面', 'pages': '页面',
  'pair': '对', 'pairs': '对',
  'panel': '面板', 'panels': '面板',
  'param': '参数', 'parameter': '参数', 'parameters': '参数', 'params': '参数',
  'part': '部分', 'parts': '部分',
  'patch': '补丁', 'patches': '补丁',
  'path': '路径', 'paths': '路径',
  'pattern': '模式', 'patterns': '模式',
  'pending': '待处理',
  'perfect': '完美',
  'performance': '绩效', 'performances': '绩效',
  'period': '周期', 'periods': '周期',
  'phase': '阶段', 'phases': '阶段',
  'philosophies': '哲学', 'philosophy': '哲学',
  'photo': '照片', 'photos': '照片',
  'physical': '物理',
  'place': '地点', 'places': '地点',
  'plan': '计划', 'plans': '计划',
  'platform': '平台', 'platforms': '平台',
  'plumbing': '给排水',
  'point': '要点', 'points': '要点',
  'policies': '政策', 'policy': '政策',
  'popup': '弹出', 'popups': '弹出',
  'position': '立场', 'positions': '立场',
  'positive': '积极',
  'possible': '可能',
  'potential': '潜在',
  'power': '功率', 'powers': '功率',
  'practice': '实践', 'practices': '实践',
  'preferred': '首选',
  'present': '现有',
  'pressure': '压力', 'pressures': '压力',
  'previous': '之前',
  'price': '价格', 'prices': '价格',
  'primary': '主要',
  'principle': '原则', 'principles': '原则',
  'priorities': '优先级', 'priority': '优先级',
  'private': '私有',
  'problem': '问题', 'problems': '问题',
  'procedure': '程序', 'procedures': '程序',
  'process': '流程', 'processes': '流程',
  'product': '产品', 'products': '产品',
  'professional': '专业',
  'project': '项目', 'projects': '项目',
  'property': '属性', 'properties': '属性',
  'protection': '防护',
  'public': '公开',
  
  // Q
  'quality': '质量',
  'queries': '查询', 'query': '查询',
  'question': '问题', 'questions': '问题',
  'quick': '快速',
  
  // R
  'range': '范围', 'ranges': '范围',
  'rare': '罕见',
  'rate': '比率', 'rates': '比率',
  'rationale': '理由',
  'reason': '原因', 'reasoning': '推理依据', 'reasons': '原因',
  'recommendation': '建议', 'recommendations': '建议', 'recommended': '推荐',
  'red': '红队',
  'reference': '参考', 'references': '参考',
  'region': '区域', 'regional': '区域', 'regions': '区域',
  'release': '发布', 'releases': '发布',
  'reliability': '可靠性',
  'request': '请求', 'requests': '请求',
  'requirement': '需求', 'requirements': '需求',
  'research': '研究',
  'resolved': '已解决',
  'resource': '资源', 'resources': '资源',
  'response': '响应', 'responses': '回应',
  'result': '结果', 'results': '结果',
  'return': '返回', 'returns': '返回',
  'reusable': '可复用', 'reuse': '复用',
  'review': '审核', 'reviews': '审核',
  'risk': '风险', 'risks': '风险',
  'roadmap': '路线图', 'roadmaps': '路线图',
  'role': '角色', 'roles': '角色',
  'round': '轮次', 'rounds': '审核轮次',
  'row': '行', 'rows': '行',
  'rule': '规则', 'rules': '规则',
  'ruling': '裁决', 'rulings': '裁决',
  
  // S
  'safety': '安全',
  'sample': '样本', 'samples': '样本',
  'saving': '节约', 'savings': '节约',
  'scalable': '可扩展',
  'scale': '规模', 'scales': '规模',
  'scenario': '场景', 'scenarios': '场景',
  'schedule': '日程', 'schedules': '日程',
  'scope': '范围', 'scopes': '范围',
  'score': '评分', 'scores': '评分',
  'screen': '屏幕', 'screens': '屏幕',
  'search': '搜索', 'searches': '搜索',
  'second': '秒', 'seconds': '秒',
  'section': '章节', 'sections': '章节',
  'sector': '领域', 'sectors': '领域',
  'security': '安全',
  'selected': '选择',
  'senior': '高级',
  'service': '服务', 'services': '服务',
  'session': '会话', 'sessions': '会话',
  'set': '集合', 'sets': '集合',
  'short': '短期',
  'sidebar': '侧边栏', 'sidebars': '侧边栏',
  'signature': '标志性',
  'significant': '重要',
  'site': '现场', 'sites': '现场',
  'situation': '情况', 'situations': '情况',
  'size': '大小', 'sizes': '大小',
  'slow': '缓慢',
  'solution': '解决方案', 'solutions': '解决方案',
  'sort': '排序', 'sorts': '排序',
  'sound': '声音', 'sounds': '声音',
  'source': '来源', 'sources': '来源',
  'space': '空间', 'spaces': '空间', 'spatial': '空间',
  'spec': '规格', 'special': '特殊', 'specification': '规格', 'specifications': '规格', 'specs': '规格', 'specific': '具体',
  'speed': '速度', 'speeds': '速度',
  'stage': '阶段', 'stages': '阶段',
  'stakeholder': '利益相关者', 'stakeholders': '利益相关者',
  'stance': '立场',
  'standard': '标准', 'standardized': '标准化', 'standards': '标准',
  'state': '状态', 'states': '状态',
  'status': '状态',
  'step': '步骤', 'steps': '步骤',
  'stories': '故事', 'story': '故事',
  'strategic': '战略', 'strategies': '策略', 'strategy': '策略',
  'strength': '优势', 'strengths': '优势',
  'structural': '结构', 'structure': '结构', 'structures': '结构',
  'studies': '研究', 'study': '研究',
  'style': '风格', 'styles': '风格',
  'subsystem': '子系统', 'subsystems': '子系统',
  'success': '成功', 'successful': '成功',
  'sum': '求和', 'summaries': '摘要', 'summary': '摘要', 'sums': '求和',
  'support': '支持', 'supports': '支持',
  'sustainability': '可持续性', 'sustainable': '可持续',
  'system': '系统', 'systems': '系统',
  
  // T
  'tab': '标签', 'table': '表格', 'tables': '表格', 'tabs': '标签',
  'tag': '标签', 'tags': '标签',
  'takeaway': '要点', 'takeaways': '要点',
  'target': '目标', 'targets': '目标',
  'task': '任务', 'tasks': '任务',
  'team': '团队', 'teams': '团队',
  'technical': '技术', 'technique': '技术', 'techniques': '技术', 'technologies': '技术', 'technology': '技术',
  'temperature': '温度', 'temperatures': '温度',
  'template': '模板', 'templates': '模板',
  'test': '测试', 'tests': '测试',
  'texture': '纹理', 'textures': '纹理',
  'threat': '威胁', 'threats': '威胁',
  'time': '时间', 'timeline': '时间线', 'timelines': '时间线', 'timeout': '超时', 'timeouts': '超时', 'times': '时间', 'timestamp': '时间戳', 'timestamps': '时间戳',
  'tip': '提示', 'tips': '提示',
  'title': '标题', 'titles': '标题',
  'tool': '工具', 'toolbar': '工具栏', 'toolbars': '工具栏', 'toolkit': '工具包', 'tools': '工具',
  'total': '总计', 'totals': '总计',
  'touchpoint': '触点', 'touchpoints': '触点',
  'transformation': '转型', 'transformations': '转型',
  'trend': '趋势', 'trends': '趋势',
  'triggered': '触发',
  'type': '类型', 'types': '类型', 'typical': '典型',
  
  // U
  'unique': '独特',
  'unusual': '异常',
  'update': '更新', 'updates': '更新',
  'upgrade': '升级', 'upgrades': '升级',
  'uri': '标识符', 'uris': '标识符',
  'url': '链接', 'urls': '链接',
  'usage': '使用',
  'user': '用户', 'users': '用户',
  'utilities': '实用工具', 'utility': '实用工具',
  
  // V
  'validation': '验证', 'validations': '验证',
  'value': '价值', 'values': '价值',
  'velocity': '速度', 'velocities': '速度',
  'verification': '验证', 'verifications': '验证',
  'version': '版本', 'versions': '版本',
  'viable': '可行的',
  'video': '视频', 'videos': '视频',
  'view': '视图', 'views': '视图',
  'virtual': '虚拟',
  'vision': '愿景', 'visions': '愿景',
  'visual': '视觉',
  'volume': '体积', 'volumes': '体积',
  
  // W
  'warning': '警告', 'warnings': '警告',
  'wavelength': '波长', 'wavelengths': '波长',
  'we': '我们',
  'weakness': '劣势', 'weaknesses': '劣势',
  'week': '周', 'weeks': '周',
  'weight': '重量', 'weights': '权重',
  'widget': '部件', 'widgets': '部件',
  'width': '宽度', 'widths': '宽度',
  'window': '窗口', 'windows': '窗口',
  'work': '工作', 'workflow': '工作流', 'workflows': '工作流', 'works': '作品',
  
  // Y
  'year': '年', 'years': '年',
  
  // Z
  'zone': '区域', 'zones': '区域',
};

const ExpertReportAccordion: FC<ExpertReportAccordionProps> = ({ expertReports, userInput, sessionId }) => {
  const [expandedExpert, setExpandedExpert] = useState<string | null>(null);
  const [isDownloading, setIsDownloading] = useState(false);

  // 调试日志
  console.log('ExpertReportAccordion 渲染, sessionId:', sessionId);

  if (!expertReports || Object.keys(expertReports).length === 0) {
    return null;
  }



  // 生成全部专家报告的打印 HTML
  const generateAllPrintHTML = (): string => {
    const styles = `
      <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans SC", sans-serif;
          line-height: 1.6;
          color: #333;
          padding: 40px;
          max-width: 800px;
          margin: 0 auto;
        }
        h1 { font-size: 24px; margin-bottom: 20px; color: #111; border-bottom: 2px solid #f97316; padding-bottom: 10px; }
        h2 { font-size: 20px; margin: 30px 0 15px; color: #111; border-left: 4px solid #f97316; padding-left: 10px; background: #fff7ed; padding: 8px 12px; border-radius: 4px; }
        h2.expert-title { page-break-before: always; margin-top: 0; }
        h3 { font-size: 16px; margin: 20px 0 10px; color: #333; font-weight: 600; }
        h4 { font-size: 15px; margin: 15px 0 8px; color: #444; font-weight: 600; }
        p { margin: 10px 0; text-align: justify; line-height: 1.8; }
        ul, ol { margin: 10px 0 10px 20px; padding-left: 0; }
        li { margin: 6px 0; padding-left: 5px; }
        
        /* 移除 Tailwind 的 prose 样式影响，强制使用打印样式 */
        .prose { max-width: none !important; color: #333 !important; }
        
        /* 列表样式修正 */
        ul { list-style-type: disc; }
        ul ul { list-style-type: circle; }
        ul ul ul { list-style-type: square; }
        ol { list-style-type: decimal; }
        
        strong { color: #000; font-weight: 700; }
        blockquote { border-left: 4px solid #e5e7eb; padding-left: 15px; color: #666; margin: 15px 0; font-style: italic; }
        
        .meta { color: #666; font-size: 12px; margin-bottom: 30px; text-align: right; }
        .divider { border-top: 1px solid #eee; margin: 30px 0; }
        .user-input { background: #f9fafb; padding: 20px; border-radius: 8px; margin: 20px 0 40px; border: 1px solid #e5e7eb; }
        
        @media print {
          body { padding: 0; margin: 0; }
          h2.expert-title { page-break-before: always; }
          .no-print { display: none; }
        }
      </style>
    `;

    const userInputSection = userInput ? `
      <h2>用户原始需求</h2>
      <div class="user-input">${userInput}</div>
      <div class="divider"></div>
    ` : '';

    let content = '';
    Object.entries(expertReports).forEach(([expertName, expertContent]) => {
      // 使用 ReactDOMServer 渲染 MarkdownContent 组件
      // 这将复用 UI 中使用的所有文本处理逻辑（processMarkdownText）
      const expertHtml = ReactDOMServer.renderToStaticMarkup(
        <MarkdownContent content={expertContent} />
      );
      
      content += `<div class="expert-section">
        <h2 class="expert-title">${expertName}</h2>
        <div class="expert-content">${expertHtml}</div>
      </div>`;
    });

    return `<!DOCTYPE html><html><head><meta charset="UTF-8"><title>全部专家报告汇总</title>${styles}</head><body>
      <h1>全部专家报告汇总</h1>
      <p class="meta">生成时间: ${new Date().toLocaleString('zh-CN')} | 专家数量: ${Object.keys(expertReports).length}</p>
      ${userInputSection}
      ${content}
    </body></html>`;
  };

  // 通用的 iframe 打印方法
  const printWithIframe = (htmlContent: string) => {
    const iframe = document.createElement('iframe');
    iframe.style.position = 'fixed';
    iframe.style.right = '0';
    iframe.style.bottom = '0';
    iframe.style.width = '0';
    iframe.style.height = '0';
    iframe.style.border = 'none';
    document.body.appendChild(iframe);

    const iframeDoc = iframe.contentWindow?.document;
    if (iframeDoc) {
      iframeDoc.open();
      iframeDoc.write(htmlContent);
      iframeDoc.close();

      iframe.onload = () => {
        setTimeout(() => {
          iframe.contentWindow?.print();
          setTimeout(() => {
            document.body.removeChild(iframe);
          }, 1000);
        }, 300);
      };
    }
  };

  // 下载全部专家报告
  // v7.1.3: 恢复使用后端 API 下载 PDF，因为后端已升级为高速生成模式
  const handleDownloadAll = async () => {
    if (!sessionId) {
      console.error('sessionId 未设置，无法下载全部专家报告');
      return;
    }

    setIsDownloading(true);

    try {
      console.log('开始下载全部专家报告 PDF, sessionId:', sessionId);
      
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/analysis/report/${sessionId}/download-all-experts-pdf`
      );

      if (!response.ok) {
        const errorText = await response.text();
        console.error('下载全部专家报告 PDF 失败:', response.status, errorText);
        throw new Error(`下载失败: ${response.status}`);
      }

      // 获取文件名
      const contentDisposition = response.headers.get('Content-Disposition');
      let filename = `all_expert_reports_${sessionId}.pdf`;
      if (contentDisposition) {
        const match = contentDisposition.match(/filename\*?=(?:UTF-8'')?([^;\n]*)/i);
        if (match) {
          filename = decodeURIComponent(match[1].replace(/['"]/g, ''));
        }
      }

      // 下载文件
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      console.log('全部专家报告 PDF 下载成功:', filename);
    } catch (error) {
      console.error('下载全部专家报告 PDF 出错:', error);
      // 如果后端失败，降级为前端 HTML 下载
      try {
        const printHTML = generateAllPrintHTML();
        const blob = new Blob([printHTML], { type: 'text/html;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `专家报告汇总_${new Date().toISOString().split('T')[0]}.html`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
      } catch (e) {
        console.error('降级下载也失败:', e);
      }
    } finally {
      setIsDownloading(false);
    }
  };

  const getExpertColor = (expertName: string) => {
    const match = expertName.match(/V(\d)/);
    if (match) {
      return EXPERT_COLORS[`V${match[1]}`] || EXPERT_COLORS['V2'];
    }
    return EXPERT_COLORS['V2'];
  };

  // 获取字段的中文标签 - 智能翻译
  const getFieldLabel = (key: string): string => {
    // 1. 直接匹配完整键名
    const lowerKey = key.toLowerCase();
    // 如果映射为空字符串，说明是黑名单字段
    if (FIELD_LABELS.hasOwnProperty(lowerKey)) return FIELD_LABELS[lowerKey];
    if (FIELD_LABELS.hasOwnProperty(key)) return FIELD_LABELS[key];
    
    // 2. 预处理：处理 camelCase 中的 "and" 连接词
    let processedKey = key
      .replace(/([a-z])And([A-Z])/g, '$1_and_$2')  // coordinationAndClashPoints -> coordination_and_ClashPoints
      .replace(/([a-z])On([A-Z])/g, '$1_on_$2')    // impactOnArchitecture -> impact_on_Architecture
      .replace(/([a-z])For([A-Z])/g, '$1_for_$2')  // designForManufacturing -> design_for_Manufacturing
      .replace(/([a-z])In([A-Z])/g, '$1_in_$2')    // errorInProcess -> error_in_Process
      .replace(/([a-z])To([A-Z])/g, '$1_to_$2');   // applicationToProject -> application_to_Project
    
    // 3. 将 snake_case 或 camelCase 拆分为单词
    const words = processedKey
      .replace(/_/g, ' ')
      .replace(/([a-z])([A-Z])/g, '$1 $2')
      .toLowerCase()
      .split(/\s+/)
      .filter(w => w.length > 0);
    
    // 4. 翻译每个单词
    const translatedWords = words.map(word => {
      // 跳过介词
      if (['and', 'or', 'on', 'in', 'for', 'to', 'of', 'with', 'by'].includes(word)) {
        return '';
      }
      return WORD_TRANSLATIONS[word] || word;
    }).filter(w => w.length > 0);
    
    // 5. 组合返回
    return translatedWords.join('');
  };

  // 提取公共的 Markdown 处理逻辑
  const processMarkdownText = (content: string): string => {
    if (!content) return '';
    
    let text = content
      // 1. 基础清理：处理转义换行符
      .replace(/\\n\\n/g, '\n\n')
      .replace(/\\n/g, '\n')
      .replace(/\r\n/g, '\n')
      .replace(/\r/g, '\n')
      // 1.1 符号标准化：将各种奇形怪状的列表符号统一为标准 Markdown 列表符
      // 扩展：包含标准圆点 • 和中间点 ·，确保它们也被统一处理
      .replace(/^[ \t]*[●○■□▪▫⁃◦•·]\s*/gm, '- ');

    // 1.5 深度列表重构：使用逐行扫描算法代替正则，彻底解决列表断行问题
    const lines = text.split('\n');
    const reconstructedLines: string[] = [];
    
    // 列表标记正则 - 扩展支持更多符号
    // 注意：前面的标准化已经处理了大部分特殊符号，这里主要保留对数字序号和中文序号的支持
    // 同时保留 - 和 * 以防万一
    const listMarkerRegex = /^\s*([-*]|\d+\.|[一二三四五六七八九十]+、|\(\d+\)|（\d+）)\s*$/;
    
    for (let i = 0; i < lines.length; i++) {
      const currentLine = lines[i];
      const trimmedLine = currentLine.trim();
      
      // 检查当前行是否是孤立的列表标记
      if (listMarkerRegex.test(trimmedLine)) {
        // 这是一个孤立的标记，需要寻找下一个非空行
        let nextContentIndex = i + 1;
        while (nextContentIndex < lines.length && !lines[nextContentIndex].trim()) {
          nextContentIndex++;
        }
        
        if (nextContentIndex < lines.length) {
          // 找到了内容行，合并
          const marker = trimmedLine;
          const content = lines[nextContentIndex].trim();
          reconstructedLines.push(`${marker} ${content}`);
          
          // 跳过已处理的行
          i = nextContentIndex;
        } else {
          // 后面没有内容了，保留原样
          reconstructedLines.push(currentLine);
        }
      } else {
        // 普通行，保留
        reconstructedLines.push(currentLine);
      }
    }
    
    text = reconstructedLines.join('\n');

    // 2. 智能分段：针对 "一、" "1." "(1)" "- " 等列表/标题特征进行强制换行
    // 这一步是为了解决 LLM 输出时可能将结构化内容挤在一行的问题
    const patterns = [
      /([^\n])\s*([一二三四五六七八九十]+、)/g,   // 中文序号：一、二、
      /([^\n])\s*(\d+\.\s)/g,                     // 数字序号：1. 2. (带空格)
      /([^\n])\s*(\(\d+\)|（\d+）)/g,             // 括号序号：(1) （1）
      /([^\n])\s*([-•·*]\s)/g,                    // 列表符号：- • · *
      /([^\n])\s*(###?\s)/g                       // Markdown 标题：## ###
    ];

    patterns.forEach(pattern => {
      text = text.replace(pattern, '$1\n\n$2');
    });

    // 3. 句末优化：中文句号后如果紧跟文字，增加分段（避免长文不换行）
    // 排除引号结尾的情况
    text = text.replace(/([。！？])\s*(?=[^\n”’"'\)）])/g, '$1\n\n');

    // 4. 确保 Markdown 列表生效（列表项前必须有空行）
    text = text.replace(/([^\n])\n([-•]|\d+\.\s)/g, '$1\n\n$2');

    // 5. 清理多余换行
    text = text.replace(/\n{3,}/g, '\n\n');

    return text;
  };

  // Markdown 渲染组件
  const MarkdownContent = ({ content }: { content: string }) => {
    // 增强的分段逻辑处理
    const processedContent = processMarkdownText(content);

    return (
      <div className="prose prose-invert max-w-none text-sm text-gray-300">
        <ReactMarkdown 
          remarkPlugins={[remarkGfm]}
          components={{
          h1: ({node, ...props}) => <h1 className="text-xl font-bold text-white mt-4 mb-2" {...props} />,
          h2: ({node, ...props}) => <h2 className="text-lg font-semibold text-white mt-4 mb-2" {...props} />,
          h3: ({node, ...props}) => <h3 className="text-base font-semibold text-white mt-3 mb-1" {...props} />,
          h4: ({node, ...props}) => <h4 className="text-sm font-semibold text-white mt-2 mb-1" {...props} />,
          p: ({node, ...props}) => <p className="leading-relaxed mb-2 text-gray-300" {...props} />,
          ul: ({node, ...props}) => <ul className="list-disc pl-5 space-y-1 my-2" {...props} />,
          ol: ({node, ...props}) => <ol className="list-decimal pl-5 space-y-1 my-2" {...props} />,
          li: ({node, ...props}) => <li className="text-gray-300 pl-1" {...props} />,
          blockquote: ({node, ...props}) => <blockquote className="border-l-4 border-gray-600 pl-4 italic my-2 text-gray-400" {...props} />,
          code: ({node, inline, className, children, ...props}: any) => {
            return inline ? (
              <code className="bg-gray-800 px-1 py-0.5 rounded text-xs font-mono text-orange-300" {...props}>{children}</code>
            ) : (
              <pre className="bg-gray-800 p-3 rounded-lg overflow-x-auto my-2 text-xs font-mono text-gray-300" {...props}>
                <code>{children}</code>
              </pre>
            );
          },
          table: ({node, ...props}) => <div className="overflow-x-auto my-4"><table className="min-w-full divide-y divide-gray-700" {...props} /></div>,
          thead: ({node, ...props}) => <thead className="bg-gray-800" {...props} />,
          tbody: ({node, ...props}) => <tbody className="divide-y divide-gray-700" {...props} />,
          tr: ({node, ...props}) => <tr {...props} />,
          th: ({node, ...props}) => <th className="px-3 py-2 text-left text-xs font-medium text-gray-300 uppercase tracking-wider" {...props} />,
          td: ({node, ...props}) => <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-300" {...props} />,
        }}
      >
        {processedContent}
      </ReactMarkdown>
      </div>
    );
  };

  // 解析并渲染专家内容
  const renderExpertContent = (content: string) => {
    // 尝试解析为 JSON
    let parsedContent: Record<string, any> | null = null;
    
    try {
      // 处理可能的 JSON 字符串
      if (content.trim().startsWith('{')) {
        parsedContent = JSON.parse(content);
      }
    } catch {
      // 不是有效的 JSON，按普通文本处理
    }

    // 如果成功解析为 JSON 对象
    if (parsedContent && typeof parsedContent === 'object') {
      return renderStructuredContent(parsedContent);
    }

    // 普通文本渲染
    return renderTextContent(content);
  };

  // 渲染结构化内容（JSON 对象）
  const renderStructuredContent = (obj: Record<string, any>, depth: number = 0) => {
    // 🚫 字段黑名单（只过滤技术元数据，保留主要交付内容）
    const fieldBlacklist = new Set([
      'protocol_status',
      'protocol执行',
      'protocol状态',
      'complianceconfirmation',
      'compliance_confirmation',
      'execution_metadata',
      'executionmetadata',
      'confidence',
      '置信度',
      'completion_status',
      'completion记录',
      'completion_ratio',
      'quality_self_assessment',
      'dependencies_satisfied',
    ]);
    
    return (
      <div className={`space-y-4 ${depth > 0 ? 'ml-4 pl-4 border-l border-[var(--border-color)]' : ''}`}>
        {Object.entries(obj).map(([key, value]) => {
          // 🚫 跳过黑名单字段
          if (fieldBlacklist.has(key) || fieldBlacklist.has(key.toLowerCase())) {
            return null;
          }
          
          // 跳过空值
          if (value === null || value === undefined || value === '') return null;

          const label = getFieldLabel(key);
          
          // 处理嵌套对象
          if (typeof value === 'object' && !Array.isArray(value)) {
            return (
              <div key={key} className="space-y-2">
                <h4 className="text-sm font-semibold text-blue-400">{label}</h4>
                {renderStructuredContent(value, depth + 1)}
              </div>
            );
          }
          
          // 处理数组
          if (Array.isArray(value)) {
            if (value.length === 0) return null;
            return (
              <div key={key} className="space-y-2">
                <h4 className="text-sm font-semibold text-blue-400">{label}</h4>
                <div className="space-y-3">
                  {value.map((item, index) => {
                    // 如果数组项是对象，递归渲染
                    if (typeof item === 'object' && item !== null) {
                      return (
                        <div key={index} className="bg-[var(--sidebar-bg)]/50 rounded-lg p-3 border border-[var(--border-color)]">
                          {renderArrayItemObject(item, index)}
                        </div>
                      );
                    }
                    // 基本类型直接显示
                    return (
                      <div key={index} className="text-sm text-gray-300 flex items-start gap-2">
                        <span className="text-gray-500 mt-0.5">•</span>
                        <span>{String(item)}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          }
          
          // 处理字符串 - 检查是否是 JSON 字符串
          if (typeof value === 'string') {
            const trimmed = value.trim();
            if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
              try {
                const parsed = JSON.parse(trimmed);
                if (typeof parsed === 'object') {
                  return (
                    <div key={key} className="space-y-2">
                      <h4 className="text-sm font-semibold text-blue-400">{label}</h4>
                      {Array.isArray(parsed) ? (
                        <div className="space-y-3">
                          {parsed.map((item, index) => (
                            <div key={index} className="bg-[var(--sidebar-bg)]/50 rounded-lg p-3 border border-[var(--border-color)]">
                              {typeof item === 'object' ? renderArrayItemObject(item, index) : <span className="text-sm text-gray-300">{String(item)}</span>}
                            </div>
                          ))}
                        </div>
                      ) : (
                        renderStructuredContent(parsed, depth + 1)
                      )}
                    </div>
                  );
                }
              } catch {
                // 不是有效 JSON，继续普通处理
              }
            }
          }
          
          // 处理字符串/数字等基本类型
          const stringValue = String(value);
          
          return (
            <div key={key} className="space-y-1">
              <h4 className="text-sm font-semibold text-blue-400">{label}</h4>
              <MarkdownContent content={stringValue} />
            </div>
          );
        })}
      </div>
    );
  };

  // 渲染数组项中的对象
  const renderArrayItemObject = (item: Record<string, any>, index: number) => {
    return (
      <div className="space-y-2">
        {Object.entries(item).map(([itemKey, itemValue]) => {
          if (itemValue === null || itemValue === undefined || itemValue === '') return null;
          
          const itemLabel = getFieldLabel(itemKey);
          
          // 嵌套对象递归
          if (typeof itemValue === 'object' && !Array.isArray(itemValue)) {
            return (
              <div key={itemKey} className="space-y-1">
                <span className="text-xs font-medium text-purple-400">{itemLabel}：</span>
                <div className="ml-3">
                  {renderArrayItemObject(itemValue, 0)}
                </div>
              </div>
            );
          }
          
          // 嵌套数组
          if (Array.isArray(itemValue)) {
            return (
              <div key={itemKey} className="space-y-1">
                <span className="text-xs font-medium text-purple-400">{itemLabel}：</span>
                <ul className="ml-3 space-y-1">
                  {itemValue.map((subItem, subIndex) => (
                    <li key={subIndex} className="text-sm text-gray-300 flex items-start gap-1">
                      <span className="text-gray-500">-</span>
                      <span>{typeof subItem === 'object' ? JSON.stringify(subItem) : String(subItem)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            );
          }
          
          return (
            <div key={itemKey} className="flex items-start gap-2">
              <span className="text-xs font-medium text-purple-400 whitespace-nowrap">{itemLabel}：</span>
              <div className="flex-1">
                <MarkdownContent content={String(itemValue)} />
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  // 渲染普通文本内容
  const renderTextContent = (content: string) => {
    if (!content) return null;
    return <MarkdownContent content={content} />;
  };

  return (
    <div className="bg-[var(--card-bg)] border border-[var(--border-color)] rounded-2xl overflow-hidden">
      {/* 标题 */}
      <div className="px-6 py-4 border-b border-[var(--border-color)] flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-orange-500/20 rounded-lg flex items-center justify-center">
            <Briefcase className="w-5 h-5 text-orange-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">专家原始报告</h2>
            <p className="text-sm text-gray-400">点击展开查看各专家的详细分析</p>
          </div>
        </div>
        <button
          onClick={handleDownloadAll}
          disabled={isDownloading}
          className="flex items-center gap-2 px-3 py-2 bg-orange-500/20 hover:bg-orange-500/30 text-orange-400 rounded-lg transition-colors text-sm disabled:opacity-50 disabled:cursor-not-allowed"
          title="下载全部专家报告"
        >
          {isDownloading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Download className="w-4 h-4" />
          )}
          <span>{isDownloading ? '准备中...' : '下载全部'}</span>
        </button>
      </div>

      {/* 专家列表 */}
      <div className="divide-y divide-[var(--border-color)]">
        {Object.entries(expertReports).map(([expertName, content]) => {
          const colors = getExpertColor(expertName);
          const isExpanded = expandedExpert === expertName;
          
          // 计算内容长度提示
          let contentLength = '';
          try {
            const parsed = JSON.parse(content);
            const fieldCount = Object.keys(parsed).length;
            contentLength = `${fieldCount} 个分析维度`;
          } catch {
            contentLength = content.length > 1000 
              ? `${Math.round(content.length / 1000)}k 字符` 
              : `${content.length} 字符`;
          }

          return (
            <div key={expertName}>
              <div className="w-full px-6 py-4 flex items-center justify-between hover:bg-[var(--sidebar-bg)] transition-colors">
                <button
                  onClick={() => setExpandedExpert(isExpanded ? null : expertName)}
                  className="flex items-center gap-3 flex-1"
                >
                  <div className={`w-8 h-8 rounded-full ${colors.bg} flex items-center justify-center`}>
                    <User className={`w-4 h-4 ${colors.text}`} />
                  </div>
                  <span className="text-sm font-medium text-white">{expertName}</span>
                </button>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-gray-500">{contentLength}</span>
                  <button
                    onClick={() => setExpandedExpert(isExpanded ? null : expertName)}
                  >
                    {isExpanded ? (
                      <ChevronUp className="w-5 h-5 text-gray-400" />
                    ) : (
                      <ChevronDown className="w-5 h-5 text-gray-400" />
                    )}
                  </button>
                </div>
              </div>

              {isExpanded && (
                <div className={`px-6 pb-6 border-l-4 ${colors.border} ml-6 mr-6 mb-4`}>
                  <div className="pl-4 pt-4 max-h-[600px] overflow-y-auto">
                    {renderExpertContent(content)}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default ExpertReportAccordion;
