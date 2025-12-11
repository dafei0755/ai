// lib/fieldTranslation.ts
// 智能字段翻译服务

// 🔤 基础字段映射（保留核心映射）
const CORE_FIELD_LABELS: Record<string, string> = {
  // 任务执行相关 - 移除冗余标签，直接显示内容
  // 'task_execution_report': '',  // 不显示
  // 'deliverable_outputs': '',     // 不显示 
  // 'deliverable_name': '',        // 不显示
  'task_completion_summary': '任务完成概述',
  'additional_insights': '额外洞察',
  'execution_challenges': '执行挑战',
  // 'completion_status': '',       // 隐藏技术性字段
  // 'quality_self_assessment': '', // 隐藏技术性字段
  
  // 设计相关字段
  'design_rationale': '设计理念',
  'project_vision_summary': '项目愿景概述',
  'spatial_requirements': '空间需求',
  'material_recommendations': '材料建议',
  'technical_considerations': '技术考虑',
  'budget_implications': '预算影响',
  'implementation_strategy': '实施策略',
  
  // 专家分析字段
  'expert_analysis': '专家分析',
  'recommendations': '建议',
  'risk_assessment': '风险评估',
  'feasibility_study': '可行性研究',
  'market_analysis': '市场分析',
  'user_experience_insights': '用户体验洞察',
  
  // 通用字段
  'analysis': '分析',
  'summary': '概要',
  'description': '描述',
  'requirements': '需求',
  'objectives': '目标',
  'challenges': '挑战',
  'opportunities': '机会',
  'conclusion': '结论',
  'next_steps': '下一步',
  'priority': '优先级',
  'timeline': '时间线',
  'resources': '资源',
  'stakeholders': '利益相关者',
};

// 🚫 字段黑名单（不显示的技术元数据字段）
const FIELD_BLACKLIST = new Set([
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

// 🔤 扩展词汇翻译（常见英文词汇到中文的映射）
const WORD_TRANSLATIONS: Record<string, string> = {
  // 动词
  'create': '创建', 'design': '设计', 'implement': '实施', 'analyze': '分析',
  'evaluate': '评估', 'optimize': '优化', 'integrate': '整合', 'develop': '开发',
  'execute': '执行', 'deliver': '交付', 'manage': '管理', 'coordinate': '协调',
  
  // 名词
  'strategy': '策略', 'approach': '方法', 'solution': '解决方案', 'framework': '框架',
  'methodology': '方法论', 'process': '流程', 'workflow': '工作流', 'timeline': '时间线',
  'milestone': '里程碑', 'deliverable': '交付物', 'outcome': '结果', 'impact': '影响',
  'insight': '洞察', 'feedback': '反馈', 'iteration': '迭代', 'validation': '验证',
  
  // 形容词
  'comprehensive': '全面的', 'detailed': '详细的', 'strategic': '战略的', 'tactical': '战术的',
  'innovative': '创新的', 'efficient': '高效的', 'effective': '有效的', 'scalable': '可扩展的',
  'sustainable': '可持续的', 'flexible': '灵活的', 'robust': '稳健的', 'agile': '敏捷的',
  
  // 专业术语
  'assessment': '评估', 'benchmark': '基准', 'specification': '规格', 'requirement': '需求',
  'constraint': '约束', 'criterion': '标准', 'parameter': '参数', 'metric': '指标',
  'threshold': '阈值', 'baseline': '基线', 'target': '目标', 'variance': '差异',
  'compliance': '合规', 'governance': '治理', 'standard': '标准', 'protocol': '协议',
};

// 🧠 翻译缓存
const translationCache = new Map<string, string>();

// 🎯 智能字段名翻译器
export class IntelligentFieldTranslator {
  private static instance: IntelligentFieldTranslator;
  
  public static getInstance(): IntelligentFieldTranslator {
    if (!IntelligentFieldTranslator.instance) {
      IntelligentFieldTranslator.instance = new IntelligentFieldTranslator();
    }
    return IntelligentFieldTranslator.instance;
  }

  /**
   * 翻译字段名
   * @param fieldKey 英文字段名
   * @returns 中文字段名
   */
  public translateField(fieldKey: string): string {
    if (!fieldKey || typeof fieldKey !== 'string') return fieldKey;
    
    // 0. 检查黑名单（返回空字符串表示不显示）
    const lowerKey = fieldKey.toLowerCase();
    if (FIELD_BLACKLIST.has(lowerKey) || FIELD_BLACKLIST.has(fieldKey)) {
      return ''; // 返回空字符串，前端可过滤
    }
    
    // 1. 检查缓存
    const cacheKey = lowerKey;
    if (translationCache.has(cacheKey)) {
      return translationCache.get(cacheKey)!;
    }
    
    // 2. 直接映射匹配
    const directMatch = this.findDirectMatch(fieldKey);
    if (directMatch) {
      translationCache.set(cacheKey, directMatch);
      return directMatch;
    }
    
    // 3. 智能分词翻译
    const smartTranslation = this.smartTranslate(fieldKey);
    if (smartTranslation !== fieldKey) {
      translationCache.set(cacheKey, smartTranslation);
      return smartTranslation;
    }
    
    // 4. 格式化英文字段名作为后备
    const formattedField = this.formatFieldName(fieldKey);
    translationCache.set(cacheKey, formattedField);
    return formattedField;
  }

  /**
   * 查找直接映射
   */
  private findDirectMatch(fieldKey: string): string | null {
    const lowerKey = fieldKey.toLowerCase();
    
    // 核心字段映射
    if (CORE_FIELD_LABELS[lowerKey]) return CORE_FIELD_LABELS[lowerKey];
    if (CORE_FIELD_LABELS[fieldKey]) return CORE_FIELD_LABELS[fieldKey];
    
    return null;
  }

  /**
   * 智能分词翻译
   */
  private smartTranslate(fieldKey: string): string {
    // 处理下划线分隔
    const words = fieldKey
      .replace(/([a-z])([A-Z])/g, '$1_$2') // 驼峰转下划线
      .toLowerCase()
      .split(/[_\-\s]+/)
      .filter(word => word.length > 0);
    
    // 翻译每个词
    const translatedWords = words.map(word => {
      // 查找词汇翻译
      if (WORD_TRANSLATIONS[word]) {
        return WORD_TRANSLATIONS[word];
      }
      
      // 处理常见后缀
      if (word.endsWith('ing')) {
        const base = word.slice(0, -3);
        if (WORD_TRANSLATIONS[base]) {
          return WORD_TRANSLATIONS[base];
        }
      }
      
      if (word.endsWith('ed')) {
        const base = word.slice(0, -2);
        if (WORD_TRANSLATIONS[base]) {
          return WORD_TRANSLATIONS[base] + '的';
        }
      }
      
      if (word.endsWith('er') || word.endsWith('or')) {
        const base = word.slice(0, -2);
        if (WORD_TRANSLATIONS[base]) {
          return WORD_TRANSLATIONS[base] + '者';
        }
      }
      
      // 保持原词
      return word;
    });
    
    // 组合翻译结果
    const hasChineseWords = translatedWords.some(word => /[\u4e00-\u9fa5]/.test(word));
    
    if (hasChineseWords) {
      // 有中文翻译，组合为中文短语
      return translatedWords
        .map(word => /[\u4e00-\u9fa5]/.test(word) ? word : this.formatEnglishWord(word))
        .join('');
    } else {
      // 没有中文翻译，返回原始格式化字段名
      return this.formatFieldName(fieldKey);
    }
  }

  /**
   * 格式化英文单词
   */
  private formatEnglishWord(word: string): string {
    return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
  }

  /**
   * 格式化字段名（后备方案）
   */
  private formatFieldName(fieldKey: string): string {
    return fieldKey
      .replace(/([a-z])([A-Z])/g, '$1 $2') // 驼峰转空格
      .replace(/[_-]/g, ' ') // 下划线和连字符转空格
      .replace(/\b\w/g, letter => letter.toUpperCase()) // 首字母大写
      .trim();
  }

  /**
   * 批量翻译字段
   */
  public translateFields(fields: Record<string, any>): Record<string, any> {
    const translated: Record<string, any> = {};
    
    for (const [key, value] of Object.entries(fields)) {
      const translatedKey = this.translateField(key);
      translated[translatedKey] = value;
    }
    
    return translated;
  }

  /**
   * 清除翻译缓存
   */
  public clearCache(): void {
    translationCache.clear();
  }

  /**
   * 获取缓存统计
   */
  public getCacheStats(): { size: number; keys: string[] } {
    return {
      size: translationCache.size,
      keys: Array.from(translationCache.keys())
    };
  }
}

// 导出单例实例
export const fieldTranslator = IntelligentFieldTranslator.getInstance();

// 导出便捷函数
export function translateFieldName(fieldKey: string): string {
  return fieldTranslator.translateField(fieldKey);
}

export function translateFields(fields: Record<string, any>): Record<string, any> {
  return fieldTranslator.translateFields(fields);
}