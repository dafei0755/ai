// components/report/ReportSectionCard.tsx
// 报告章节卡片组件

'use client';

import React, { FC, useState, useMemo } from 'react';
import { ChevronDown, ChevronUp, BarChart3, List, FileText, Code2 } from 'lucide-react';
import { ReportSection } from '@/types';
import MarkdownRenderer from './MarkdownRenderer';
import { translateFieldName } from '@/lib/fieldTranslation';

interface ReportSectionCardProps {
  section: ReportSection;
  defaultExpanded?: boolean;
}

// 🔗 目录项接口
interface TocItem {
  id: string;
  text: string;
  level: number;
  index: number;
}

// 📑 目录组件
const TableOfContents: FC<{ items: TocItem[]; onItemClick: (id: string) => void }> = ({ items, onItemClick }) => {
  const [tocExpanded, setTocExpanded] = useState(false);
  
  if (items.length === 0) return null;
  
  return (
    <div className="mb-4 bg-slate-800/30 border border-slate-700/50 rounded-lg overflow-hidden">
      <button
        onClick={() => setTocExpanded(!tocExpanded)}
        className="w-full px-3 py-2 flex items-center justify-between text-sm hover:bg-slate-700/30 transition-colors"
      >
        <div className="flex items-center gap-2">
          <List className="w-4 h-4 text-blue-400" />
          <span className="text-blue-300 font-medium">目录导航</span>
          <span className="text-gray-400">({items.length}项)</span>
        </div>
        {tocExpanded ? (
          <ChevronUp className="w-4 h-4 text-gray-400" />
        ) : (
          <ChevronDown className="w-4 h-4 text-gray-400" />
        )}
      </button>
      
      {tocExpanded && (
        <div className="px-3 pb-3 max-h-48 overflow-y-auto">
          <ul className="space-y-1">
            {items.map((item) => (
              <li key={item.id}>
                <button
                  onClick={() => onItemClick(item.id)}
                  className={`
                    w-full text-left px-2 py-1 rounded text-sm hover:bg-slate-700/50 transition-colors
                    ${item.level === 1 ? 'text-white font-medium' : 
                      item.level === 2 ? 'text-gray-200 pl-4' :
                      item.level === 3 ? 'text-gray-300 pl-6' :
                      'text-gray-400 pl-8'}
                  `}
                  title={item.text}
                >
                  <span className="block truncate">{item.text}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

interface ReportSectionCardProps {
  section: ReportSection;
  defaultExpanded?: boolean;
}

const ReportSectionCard: FC<ReportSectionCardProps> = ({ section, defaultExpanded = false }) => {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [renderMode, setRenderMode] = useState<'enhanced' | 'markdown'>('enhanced'); // 渲染模式

  // 置信度颜色
  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-400 bg-green-400/20';
    if (confidence >= 0.6) return 'text-yellow-400 bg-yellow-400/20';
    return 'text-red-400 bg-red-400/20';
  };

  // 🔥 嵌套模型类型识别器
  const identifyNestedModelType = (obj: any): string | null => {
    if (!obj || typeof obj !== 'object') return null;
    const fields = Object.keys(obj);

    // TouchpointScript: touchpoint_name + emotional_goal + sensory_script
    if (fields.includes('touchpoint_name') && fields.includes('emotional_goal') && fields.includes('sensory_script')) {
      return 'TouchpointScript';
    }

    // FamilyMemberProfile: member + daily_routine + spatial_needs + storage_needs
    if (fields.includes('member') && fields.includes('spatial_needs') && fields.includes('storage_needs')) {
      return 'FamilyMemberProfile';
    }

    // RetailKPI: metric + target + spatial_strategy
    if (fields.includes('metric') && fields.includes('target') && fields.includes('spatial_strategy')) {
      return 'RetailKPI';
    }

    // DesignChallenge: challenge + context + constraints
    if (fields.includes('challenge') && fields.includes('context') && fields.includes('constraints')) {
      return 'DesignChallenge';
    }

    // SubprojectBrief: subproject_name + key_requirements + design_priority
    if (fields.includes('subproject_name') && fields.includes('key_requirements') && fields.includes('design_priority')) {
      return 'SubprojectBrief';
    }

    // TechnicalOption: option_name + advantages + disadvantages + estimated_cost_level
    if (fields.includes('option_name') && fields.includes('advantages') && fields.includes('disadvantages') && fields.includes('estimated_cost_level')) {
      return 'TechnicalOption';
    }

    // KeyNodeAnalysis: node_name + challenge + proposed_solution
    if (fields.includes('node_name') && fields.includes('challenge') && fields.includes('proposed_solution')) {
      return 'KeyNodeAnalysis';
    }

    // SystemSolution: system_name + recommended_solution + reasoning + impact_on_architecture
    if (fields.includes('system_name') && fields.includes('recommended_solution') && fields.includes('reasoning')) {
      return 'SystemSolution';
    }

    // SmartScenario: scenario_name + description + triggered_systems
    if (fields.includes('scenario_name') && fields.includes('description') && fields.includes('triggered_systems')) {
      return 'SmartScenario';
    }

    // MaterialSpec: material_name + application_area + key_specifications + reasoning
    if (fields.includes('material_name') && fields.includes('application_area') && fields.includes('key_specifications')) {
      return 'MaterialSpec';
    }

    // NodeDetail: node_name + challenge + proposed_solution (similar to KeyNodeAnalysis, but used in V6-3 context)
    // Already covered by KeyNodeAnalysis check above

    // CostBreakdown: category + percentage + cost_drivers
    if (fields.includes('category') && fields.includes('percentage') && fields.includes('cost_drivers')) {
      return 'CostBreakdown';
    }

    // VEOption: area + original_scheme + proposed_option + impact_analysis
    if (fields.includes('area') && fields.includes('original_scheme') && fields.includes('proposed_option') && fields.includes('impact_analysis')) {
      return 'VEOption';
    }

    return null;
  };

  // 🔥 嵌套模型特殊渲染器
  const renderNestedModel = (data: any, modelType: string, index: number): React.ReactNode => {
    const baseClasses = "bg-slate-800/50 border border-slate-700/50 rounded-lg p-4";

    switch (modelType) {
      case 'TouchpointScript':
        return (
          <div key={index} className={`${baseClasses} border-l-4 border-purple-500/50`}>
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 bg-purple-500/20 rounded-full flex items-center justify-center flex-shrink-0">
                <span className="text-purple-400 text-lg">✨</span>
              </div>
              <div className="flex-1 space-y-2">
                <h5 className="text-base font-semibold text-purple-300">{data.touchpoint_name}</h5>
                <div className="text-sm text-gray-300">
                  <span className="text-purple-400 font-medium">情感目标：</span>
                  {data.emotional_goal}
                </div>
                <div className="text-sm text-gray-400">
                  <span className="text-purple-400 font-medium">感官脚本：</span>
                  {data.sensory_script}
                </div>
              </div>
            </div>
          </div>
        );

      case 'FamilyMemberProfile':
        return (
          <div key={index} className={`${baseClasses} border-l-4 border-green-500/50`}>
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 bg-green-500/20 rounded-full flex items-center justify-center flex-shrink-0">
                <span className="text-green-400 text-lg">👤</span>
              </div>
              <div className="flex-1 space-y-2">
                <h5 className="text-base font-semibold text-green-300">{data.member}</h5>
                <div className="text-sm text-gray-300">{data.daily_routine}</div>
                <div className="grid grid-cols-2 gap-3 mt-2">
                  <div>
                    <div className="text-xs text-green-400 font-medium mb-1">空间需求</div>
                    <ul className="text-sm text-gray-400 space-y-0.5 list-none pl-0">
                      {data.spatial_needs?.map((need: string, i: number) => (
                        <li key={i}>{need}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <div className="text-xs text-green-400 font-medium mb-1">储物需求</div>
                    <ul className="text-sm text-gray-400 space-y-0.5 list-none pl-0">
                      {data.storage_needs?.map((need: string, i: number) => (
                        <li key={i}>{need}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </div>
        );

      case 'RetailKPI':
        return (
          <div key={index} className={`${baseClasses} border-l-4 border-blue-500/50`}>
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-blue-500/20 rounded-lg flex items-center justify-center flex-shrink-0">
                <span className="text-2xl font-bold text-blue-400">📊</span>
              </div>
              <div className="flex-1 space-y-1">
                <h5 className="text-base font-semibold text-blue-300">{data.metric}</h5>
                <div className="text-lg font-mono text-blue-400">{data.target}</div>
                <div className="text-sm text-gray-400">{data.spatial_strategy}</div>
              </div>
            </div>
          </div>
        );

      case 'DesignChallenge':
        return (
          <div key={index} className={`${baseClasses} border-l-4 border-orange-500/50`}>
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span className="text-orange-400 text-lg">⚠️</span>
                <h5 className="text-base font-semibold text-orange-300">{data.challenge}</h5>
              </div>
              <div className="text-sm text-gray-300">{data.context}</div>
              <div className="text-sm">
                <span className="text-orange-400 font-medium">约束条件：</span>
                <span className="text-gray-400">{Array.isArray(data.constraints) ? data.constraints.join('、') : data.constraints}</span>
              </div>
            </div>
          </div>
        );

      case 'SubprojectBrief':
        return (
          <div key={index} className={`${baseClasses} border-l-4 border-cyan-500/50`}>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h5 className="text-base font-semibold text-cyan-300">{data.subproject_name}</h5>
                {data.area_sqm && (
                  <span className="text-sm bg-cyan-500/20 text-cyan-300 px-2 py-0.5 rounded">
                    {data.area_sqm}㎡
                  </span>
                )}
              </div>
              <div className="text-sm">
                <span className="text-cyan-400 font-medium">核心需求：</span>
                <span className="text-gray-300">{Array.isArray(data.key_requirements) ? data.key_requirements.join('、') : data.key_requirements}</span>
              </div>
              <div className="text-sm">
                <span className="text-cyan-400 font-medium">优先级：</span>
                <span className={`font-medium ${data.design_priority === '高' ? 'text-red-400' : data.design_priority === '中' ? 'text-yellow-400' : 'text-gray-400'}`}>
                  {data.design_priority}
                </span>
              </div>
            </div>
          </div>
        );

      case 'TechnicalOption':
      case 'KeyNodeAnalysis':
        return (
          <div key={index} className={`${baseClasses} border-l-4 border-indigo-500/50`}>
            <div className="space-y-2">
              <h5 className="text-base font-semibold text-indigo-300">
                {data.option_name || data.node_name}
              </h5>
              {data.advantages && (
                <div className="text-sm">
                  <span className="text-green-400 font-medium">优势：</span>
                  <span className="text-gray-300">{Array.isArray(data.advantages) ? data.advantages.join('、') : data.advantages}</span>
                </div>
              )}
              {data.disadvantages && (
                <div className="text-sm">
                  <span className="text-red-400 font-medium">劣势：</span>
                  <span className="text-gray-300">{Array.isArray(data.disadvantages) ? data.disadvantages.join('、') : data.disadvantages}</span>
                </div>
              )}
              {data.challenge && (
                <div className="text-sm">
                  <span className="text-orange-400 font-medium">挑战：</span>
                  <span className="text-gray-300">{data.challenge}</span>
                </div>
              )}
              {data.proposed_solution && (
                <div className="text-sm">
                  <span className="text-indigo-400 font-medium">方案：</span>
                  <span className="text-gray-300">{data.proposed_solution}</span>
                </div>
              )}
              {data.estimated_cost_level && (
                <span className="inline-block text-xs bg-indigo-500/20 text-indigo-300 px-2 py-0.5 rounded">
                  成本：{data.estimated_cost_level}
                </span>
              )}
            </div>
          </div>
        );

      case 'SystemSolution':
        return (
          <div key={index} className={`${baseClasses} border-l-4 border-teal-500/50`}>
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span className="text-teal-400 text-lg">⚙️</span>
                <h5 className="text-base font-semibold text-teal-300">{data.system_name}</h5>
              </div>
              <div className="text-sm">
                <span className="text-teal-400 font-medium">推荐方案：</span>
                <span className="text-gray-300">{data.recommended_solution}</span>
              </div>
              <div className="text-sm text-gray-400">{data.reasoning}</div>
              {data.impact_on_architecture && (
                <div className="text-sm text-gray-500 italic">→ {data.impact_on_architecture}</div>
              )}
            </div>
          </div>
        );

      case 'SmartScenario':
        return (
          <div key={index} className={`${baseClasses} border-l-4 border-violet-500/50`}>
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span className="text-violet-400 text-lg">🤖</span>
                <h5 className="text-base font-semibold text-violet-300">{data.scenario_name}</h5>
              </div>
              <div className="text-sm text-gray-300">{data.description}</div>
              {data.triggered_systems && (
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {data.triggered_systems.map((system: string, i: number) => (
                    <span key={i} className="text-xs bg-violet-500/20 text-violet-300 px-2 py-0.5 rounded">
                      {system}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        );

      case 'MaterialSpec':
        return (
          <div key={index} className={`${baseClasses} border-l-4 border-amber-500/50`}>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h5 className="text-base font-semibold text-amber-300">{data.material_name}</h5>
                <span className="text-xs bg-amber-500/20 text-amber-300 px-2 py-0.5 rounded">
                  {data.application_area}
                </span>
              </div>
              {data.key_specifications && (
                <ul className="text-sm text-gray-300 space-y-0.5 list-none pl-0">
                  {data.key_specifications.map((spec: string, i: number) => (
                    <li key={i}>{spec}</li>
                  ))}
                </ul>
              )}
              <div className="text-sm text-gray-400 italic">{data.reasoning}</div>
            </div>
          </div>
        );

      case 'CostBreakdown':
        return (
          <div key={index} className={`${baseClasses} border-l-4 border-emerald-500/50`}>
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 bg-emerald-500/20 rounded-lg flex items-center justify-center flex-shrink-0">
                <span className="text-2xl font-bold text-emerald-400">{data.percentage}%</span>
              </div>
              <div className="flex-1 space-y-1">
                <h5 className="text-base font-semibold text-emerald-300">{data.category}</h5>
                <ul className="text-sm text-gray-400 space-y-0.5 list-none pl-0">
                  {data.cost_drivers?.map((driver: string, i: number) => (
                    <li key={i}>{driver}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        );

      case 'VEOption':
        return (
          <div key={index} className={`${baseClasses} border-l-4 border-lime-500/50`}>
            <div className="space-y-2">
              <h5 className="text-base font-semibold text-lime-300">{data.area}</h5>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <div className="text-xs text-gray-500 mb-1">原方案</div>
                  <div className="text-sm text-gray-300">{data.original_scheme}</div>
                </div>
                <div>
                  <div className="text-xs text-lime-400 mb-1">建议方案</div>
                  <div className="text-sm text-lime-300 font-medium">{data.proposed_option}</div>
                </div>
              </div>
              <div className="text-sm bg-lime-500/10 text-lime-300 p-2 rounded">
                💡 {data.impact_analysis}
              </div>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  // 🔥 智能渲染JSON数据
  const renderJsonContent = (data: any, depth: number = 0): React.ReactNode => {
    if (data === null || data === undefined) return null;
    
    // 基础类型
    if (typeof data === 'string') {
      // 长文本分段显示
      if (data.length > 100) {
        return (
          <p className="text-sm text-gray-300 leading-relaxed whitespace-pre-wrap">
            {data}
          </p>
        );
      }
      return <span className="text-gray-300">{data}</span>;
    }
    
    if (typeof data === 'number' || typeof data === 'boolean') {
      return <span className="text-blue-400">{String(data)}</span>;
    }
    
    // 数组
    if (Array.isArray(data)) {
      if (data.length === 0) return null;
      
      // 检查是否是简单字符串数组
      if (data.every(item => typeof item === 'string')) {
        return (
          <ul className="space-y-1.5 my-2 list-none pl-0">
            {data.map((item, idx) => (
              <li key={idx} className="text-sm text-gray-300">
                {item}
              </li>
            ))}
          </ul>
        );
      }
      
      // 复杂对象数组 - 先检查是否为嵌套模型数组
      const firstItem = data[0];
      if (typeof firstItem === 'object') {
        const nestedModelType = identifyNestedModelType(firstItem);
        if (nestedModelType) {
          return (
            <div className="space-y-3">
              {data.map((item, idx) => renderNestedModel(item, nestedModelType, idx))}
            </div>
          );
        }
      }

      // 普通复杂对象数组
      return (
        <div className="space-y-3">
          {data.map((item, idx) => (
            <div key={idx} className="pl-3 border-l-2 border-blue-500/30">
              {renderJsonContent(item, depth + 1)}
            </div>
          ))}
        </div>
      );
    }

    // 对象
    if (typeof data === 'object') {
      // 🚫 过滤掉黑名单字段和空值（只过滤技术元数据）
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
      
      const entries = Object.entries(data).filter(([key, v]) => {
        // 过滤空值
        if (v === null || v === undefined || v === '') return false;
        // 过滤黑名单字段
        if (fieldBlacklist.has(key) || fieldBlacklist.has(key.toLowerCase())) return false;
        return true;
      });
      
      if (entries.length === 0) return null;

      // 检查是否为单个嵌套模型
      const nestedModelType = identifyNestedModelType(data);
      if (nestedModelType) {
        return renderNestedModel(data, nestedModelType, 0);
      }
      
      // 字段名映射为更友好的中文
      const fieldLabels: Record<string, string> = {
        // ===== 通用字段 =====
        'project_task': '项目任务',
        'character_narrative': '角色叙事',
        'physical_context': '物理环境',
        'resource_constraints': '资源约束',
        'regulatory_requirements': '法规要求',
        'inspiration_references': '灵感参考',
        'experience_behavior': '体验行为',
        'design_challenge': '设计挑战',
        'primary_deliverables': '核心交付物',
        'project_overview': '项目概述',
        'core_objectives': '核心目标',
        'target_users': '目标用户',
        'constraints': '约束条件',
        'calibration_questionnaire': '校准问卷',
        'expert_handoff': '专家交接',
        'custom_analysis': '定制分析',
        'confidence': '置信度',
        'structured_data': '结构化内容',
        'narrative_summary': '文字摘要',
        'raw_text': '原始文本',
        'raw_content': '原始内容',
        'validation_warnings': '校验提醒',

        // ===== 灵活输出架构字段 (Phase 2-3) =====
        'output_mode': '输出模式',
        'user_question_focus': '用户问题焦点',
        'design_rationale': '设计原理',
        'decision_rationale': '决策依据',
        'targeted_analysis': '针对性分析',
        'expert_handoff_response': '专家交接响应',
        'challenge_flags': '挑战标记',

        // ===== V6工程师系列 =====
        // V6-1: 结构与幕墙专家
        'feasibility_assessment': '可行性评估',
        'structural_system_options': '结构体系选项',
        'facade_system_options': '幕墙体系选项',
        'key_technical_nodes': '关键技术节点',
        'risk_analysis_and_recommendations': '风险分析与建议',

        // V6-2: 机电与智能化专家
        'mep_overall_strategy': '机电整体策略',
        'system_solutions': '系统方案',
        'smart_building_scenarios': '智慧建筑场景',
        'coordination_and_clash_points': '协调与碰撞点',
        'sustainability_and_energy_saving': '可持续与节能',

        // V6-3: 室内工艺与材料专家
        'craftsmanship_strategy': '工艺策略',
        'key_material_specifications': '关键材料规格',
        'critical_node_details': '关键节点详情',
        'quality_control_and_mockup': '质控与样板',
        'risk_analysis': '风险分析',

        // V6-4: 成本与价值工程师
        'cost_estimation_summary': '成本估算摘要',
        'cost_breakdown_analysis': '成本拆解分析',
        'value_engineering_options': '价值工程选项',
        'budget_control_strategy': '预算控制策略',
        'cost_overrun_risk_analysis': '成本超支风险分析',

        // ===== V5场景专家系列 =====
        // V5-0: 通用场景策略师
        'scenario_deconstruction': '场景拆解',
        'operational_logic': '运营逻辑',
        'stakeholder_analysis': '利益相关方分析',
        'design_challenges_for_v2': 'V2设计挑战',

        // V5-1: 居住场景专家
        'family_profile_and_needs': '家庭画像与需求',

        // V5-2: 商业零售运营专家
        'business_goal_analysis': '商业目标分析',

        // V5-3: 企业办公策略专家
        'organizational_analysis': '组织分析',
        'collaboration_model': '协作模式',
        'workspace_strategy': '工作空间策略',

        // V5-4: 酒店餐饮运营专家
        'service_process_analysis': '服务流程分析',
        'operational_efficiency': '运营效率',
        'guest_experience_blueprint': '宾客体验蓝图',

        // V5-5: 文化教育场景专家
        'visitor_journey_analysis': '访客旅程分析',
        'educational_model': '教育模式',
        'public_service_strategy': '公共服务策略',

        // V5-6: 医疗康养场景专家
        'healthcare_process_analysis': '医疗流程分析',
        'patient_experience_blueprint': '患者体验蓝图',
        'wellness_strategy': '康养策略',

        // ===== V2设计总监系列 =====
        // V2-0: 项目设计总监
        'master_plan_strategy': '总体规划策略',
        'spatial_zoning_concept': '空间分区概念',
        'circulation_integration': '动线整合',
        'subproject_coordination': '子项目协调',
        'design_unity_and_variation': '设计统一性与变化',

        // V2-1: 居住空间设计总监
        'project_vision_summary': '项目愿景摘要',
        'spatial_concept': '空间概念',
        'narrative_translation': '叙事转译',
        'aesthetic_framework': '美学框架',
        'functional_planning': '功能规划',
        'material_palette': '材料选择',
        'implementation_guidance': '实施指导',

        // V2-2: 商业空间设计总监
        'business_strategy_translation': '商业策略转译',

        // V2-3: 办公空间设计总监
        'workspace_vision': '工作空间愿景',
        'spatial_strategy': '空间策略',
        'collaboration_and_focus_balance': '协作与专注平衡',
        'brand_and_culture_expression': '品牌与文化表达',

        // V2-4: 酒店餐饮空间设计总监
        'experiential_vision': '体验愿景',
        'sensory_design_framework': '感官设计框架',
        'guest_journey_design': '宾客旅程设计',
        'guest_experience_journey': '宾客体验旅程',
        'ambience_design_strategy': '氛围设计策略',
        'functional_zoning_and_flow': '功能分区与动线',

        // V2-5: 文化与公共建筑设计总监
        'public_vision': '公共愿景',
        'spatial_accessibility': '空间可达性',
        'community_engagement': '社区参与',
        'cultural_expression': '文化表达',
        'cultural_theme_and_spirit': '文化主题与精神',
        'symbolic_system': '符号系统',

        // V2-6: 建筑及景观设计总监
        'architectural_concept': '建筑概念',
        'facade_and_envelope': '立面与围护',
        'landscape_integration': '景观整合',
        'indoor_outdoor_relationship': '室内外关系',

        // ===== V3叙事专家系列 =====
        // V3-1: 个体叙事与心理洞察专家
        'individual_narrative_core': '个体叙事核心',
        'psychological_profile': '心理画像',
        'lifestyle_blueprint': '生活方式蓝图',
        'key_spatial_moments': '关键空间时刻',
        'narrative_guidelines_for_v2': '叙事指南',

        // V3-2: 品牌叙事与顾客体验专家
        'brand_narrative_core': '品牌叙事核心',
        'customer_archetype': '顾客原型',
        'emotional_journey_map': '情感旅程地图',
        'key_touchpoint_scripts': '关键触点脚本',

        // V3-3: 空间叙事与情感体验专家
        'spatial_narrative_concept': '空间叙事概念',
        'sensory_experience_design': '感官体验设计',

        // ===== V4研究者系列 =====
        // V4-1: 设计研究者
        'research_focus': '研究焦点',
        'methodology': '研究方法',
        'key_findings': '核心发现',
        'design_implications': '设计启示',
        'evidence_base': '证据基础',

        // V4-2: 趋势研究与未来洞察专家
        'trend_analysis': '趋势分析',
        'future_scenarios': '未来场景',
        'opportunity_identification': '机会识别',
        'risk_assessment': '风险评估',

        // ===== 其他现有字段 =====
        'interdisciplinary_insights': '跨学科洞察',
        'scene_storyboard': '场景脚本',
        'case_studies_deep_dive': '案例深度研究',
        'competitive_analysis': '竞争分析',
        'reusable_design_patterns': '可复用设计模式',
        'key_success_factors': '关键成功因素',
        'operational_blueprint': '运营蓝图',
        'journey_maps': '旅程地图',
        'key_performance_indicators': 'KPI指标',
        'technical_requirements_for_v6': 'V6技术需求',
      };
      
      return (
        <div className={`space-y-4 ${depth > 0 ? 'mt-2' : ''}`}>
          {entries.map(([key, value]) => {
            const label = fieldLabels[key] || key.replace(/_/g, ' ');

            // 跳过一些不需要显示的字段
            if (['content', 'challenge_flags', 'expert_handoff_response'].includes(key)) {
              return null;
            }

            // 🎯 Targeted模式特殊渲染：targeted_analysis字段
            if (key === 'targeted_analysis') {
              return (
                <div key={key} className="bg-blue-500/10 border-l-4 border-blue-500 p-4 rounded-r-lg my-4">
                  <div className="flex items-center gap-2 mb-3">
                    <svg className="w-5 h-5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <h4 className="text-base font-semibold text-blue-400">{label}</h4>
                  </div>
                  <div className="space-y-3 pl-2">
                    {renderJsonContent(value, depth + 1)}
                  </div>
                </div>
              );
            }

            return (
              <div key={key} className="space-y-1">
                <h4 className="text-sm font-medium text-blue-400 capitalize">{label}</h4>
                <div className="pl-2">
                  {renderJsonContent(value, depth + 1)}
                </div>
              </div>
            );
          })}
        </div>
      );
    }
    
    return null;
  };

  // 🔍 提取标题生成目录
  const extractHeadings = (content: string): TocItem[] => {
    if (!content) return [];
    
    const headings: TocItem[] = [];
    const lines = content.split('\n');
    
    lines.forEach((line, index) => {
      const trimmed = line.trim();
      if (trimmed.startsWith('#')) {
        const match = trimmed.match(/^(#{1,6})\s+(.+)$/);
        if (match) {
          const [, hashes, text] = match;
          const level = hashes.length;
          const id = `heading-${index}-${text.replace(/[^\w\u4e00-\u9fa5]/g, '-').toLowerCase()}`;
          
          headings.push({
            id,
            text: text.trim(),
            level,
            index
          });
        }
      }
    });
    
    return headings;
  };

  // 🎯 滚动到指定标题
  const scrollToHeading = (headingId: string) => {
    const element = document.getElementById(headingId);
    if (element) {
      element.scrollIntoView({ 
        behavior: 'smooth', 
        block: 'start',
        inline: 'nearest'
      });
      // 添加短暂的高亮效果
      element.classList.add('highlight-flash');
      setTimeout(() => {
        element.classList.remove('highlight-flash');
      }, 2000);
    }
  };

  // 📝 使用useMemo缓存标题提取结果
  const tocItems = useMemo(() => extractHeadings(section.content || ''), [section.content]);
  
  const formatContent = (content: string) => {
    if (!content) return null;
    
    // 🚨 强制测试标记
    console.log('🚨🚨🚨 FORMAT CONTENT FUNCTION CALLED! 🚨🚨🚨');
    alert('测试：formatContent函数已执行！');
    
    // 🔍 调试信息
    console.log('🔍 formatContent 输入:', {
      contentType: typeof content,
      contentLength: content.length,
      firstChars: content.substring(0, 100),
      hasLineBreaks: content.includes('\n'),
      hasDoubleLineBreaks: content.includes('\n\n')
    });
    
    // 🔥 尝试解析JSON，如果是JSON则智能渲染
    let isJsonContent = false;
    try {
      const jsonData = JSON.parse(content);
      console.log('✅ 检测到 JSON 数据，使用 renderJsonContent');
      isJsonContent = true;
      return (
        <div>
          {tocItems.length > 0 && <TableOfContents items={tocItems} onItemClick={scrollToHeading} />}
          {renderJsonContent(jsonData)}
        </div>
      );
    } catch {
      console.log('ℹ️ 非 JSON 数据，使用文本处理');
      // 不是JSON，按渲染模式处理文本
    }
    
    // 🎯 根据渲染模式选择处理方式
    if (renderMode === 'markdown') {
      return (
        <div>
          {/* 添加模式切换按钮 */}
          <div className="flex justify-end mb-3">
            <button
              onClick={() => setRenderMode('enhanced')}
              className="text-xs text-gray-400 hover:text-blue-400 transition-colors flex items-center gap-1"
            >
              <Code2 className="w-3 h-3" />
              切换到增强模式
            </button>
          </div>
          <MarkdownRenderer content={content} />
        </div>
      );
    }
    
    // 🚀 超级强化文本预处理：确保长文本必须分段
    console.log('🛠️ 开始文本预处理...');
    
    let processed = content
      // 1. 标准化换行符
      .replace(/\r\n/g, '\n')
      .replace(/\r/g, '\n')
      
      // 2. 处理转义字符
      .replace(/\\n\\n/g, '\n\n')
      .replace(/\\n/g, '\n')
      .replace(/\\t/g, '\t')
      
      // 3. 🔥 激进的中文句号分段 - 确保每句话后都分段
      .replace(/([。！？])(?!\s*$)/g, '$1\n\n')
      
      // 4. 🎯 数字和重要词汇前分段
      .replace(/([。！？])\s*([一二三四五六七八九十][\d]*[、\.。])/g, '$1\n\n$2')
      .replace(/([。！？])\s*([１２３４５６７８９])/g, '$1\n\n$2')
      .replace(/([。！？])\s*(主要|核心|重要|关键|首先|其次|另外|此外|同时)/g, '$1\n\n$2')
      
      // 5. 🔥 长句在逗号处强制分行
      .replace(/([，、])(?=.{20,}[。！？])/g, '$1\n  ')
      
      // 6. 清理多余换行
      .replace(/\n{3,}/g, '\n\n')
      .replace(/^\s+|\s+$/g, '');
    
    console.log('📝 文本预处理结果:', {
      originalLength: content.length,
      processedLength: processed.length,
      paragraphCount: processed.split('\n\n').length,
      hasParagraphs: processed.includes('\n\n')
    });
    
    // 🔥 如果处理后仍然没有分段效果，强制按长度分段
    if (!processed.includes('\n\n') && processed.length > 200) {
      console.log('⚠️ 未检测到分段，执行强制分段逻辑');
      
      // 按句号分割，然后重新组合
      const sentences = processed.split(/([。！？])/).reduce((acc, part, idx) => {
        if (idx % 2 === 0 && part.trim()) {
          acc.push(part.trim());
        } else if (idx % 2 === 1) {
          acc[acc.length - 1] += part;
        }
        return acc;
      }, []);
      
      // 每2个句子组成一段
      const paragraphGroups = [];
      for (let i = 0; i < sentences.length; i += 2) {
        const group = sentences.slice(i, i + 2).join(' ');
        if (group.trim()) paragraphGroups.push(group.trim());
      }
      
      processed = paragraphGroups.join('\n\n');
      
      console.log('🔧 强制分段结果:', {
        sentenceCount: sentences.length,
        paragraphCount: paragraphGroups.length,
        finalText: processed.substring(0, 200) + '...'
      });
    }
    
    // 按双换行分割成段落
    let paragraphs = processed.split(/\n\n+/).filter(p => p.trim());
    
    // 🔥 最后的保险：如果段落太少且很长，强制分段
    if (paragraphs.length < 3 && processed.length > 300) {
      console.log('🚨 最后保险分段逻辑执行');
      
      paragraphs = processed.split(/([。！？])/).reduce((acc, part, idx) => {
        if (idx % 2 === 0 && part.trim()) {
          acc.push(part.trim());
        } else if (idx % 2 === 1 && acc.length > 0) {
          acc[acc.length - 1] += part;
        }
        return acc;
      }, []).filter(p => p.trim() && p.length > 5);
    }
    
    console.log('✅ 最终段落处理结果:', {
      totalParagraphs: paragraphs.length,
      paragraphLengths: paragraphs.map(p => p.length),
      firstParagraph: paragraphs[0]?.substring(0, 100) + '...'
    });
    
    return (
      <div className="space-y-4 text-content-optimized">
        {/* 调试信息 - 仅开发环境显示 */}
        {process.env.NODE_ENV === 'development' && (
          <div className="bg-yellow-900/20 border border-yellow-700/50 rounded p-2 text-xs text-yellow-300">
            <div>调试信息：共 {paragraphs.length} 个段落</div>
            <div>原始长度：{content.length} | 处理后：{processed.length}</div>
            <div>分段检测：{processed.includes('\n\n') ? '✅ 有分段' : '❌ 无分段'}</div>
          </div>
        )}
        
        {/* 模式切换和目录导航 */}
        <div className="flex justify-between items-start">
          <div className="flex-1">
            {tocItems.length > 0 && <TableOfContents items={tocItems} onItemClick={scrollToHeading} />}
          </div>
          <div className="ml-3">
            <button
              onClick={() => setRenderMode('markdown')}
              className="text-xs text-gray-400 hover:text-blue-400 transition-colors flex items-center gap-1"
            >
              <FileText className="w-3 h-3" />
              Markdown模式
            </button>
          </div>
        </div>
        
        {/* 段落渲染 - 强制视觉分隔 */}
        {paragraphs.map((para, index) => {
          const trimmedPara = para.trim();
          if (!trimmedPara) return null;
          
          return (
            <div 
              key={index} 
              className="paragraph-container"
              style={{
                marginBottom: '1.5rem',
                paddingBottom: '1rem',
                borderBottom: process.env.NODE_ENV === 'development' ? '1px dashed rgba(255,255,255,0.1)' : 'none'
              }}
            >
              {/* 段落索引（仅开发环境） */}
              {process.env.NODE_ENV === 'development' && (
                <div className="text-xs text-gray-500 mb-1">段落 {index + 1}</div>
              )}
              
              {/* 内容渲染 */}
              {(() => {
          
          // 🎯 增强标题识别和渲染（支持H1-H6层级）- 添加ID支持
          const generateHeadingId = (text: string, index: number) => 
            `heading-${index}-${text.replace(/[^\w\u4e00-\u9fa5]/g, '-').toLowerCase()}`;
          
          if (trimmedPara.startsWith('###### ')) {
            const text = trimmedPara.replace('###### ', '');
            return (
              <h6 key={index} id={generateHeadingId(text, index)} className="text-xs font-medium text-gray-400 mt-2 mb-1 uppercase tracking-wider">
                {text}
              </h6>
            );
          }
          if (trimmedPara.startsWith('##### ')) {
            const text = trimmedPara.replace('##### ', '');
            return (
              <h5 key={index} id={generateHeadingId(text, index)} className="text-sm font-medium text-gray-300 mt-2 mb-2">
                {text}
              </h5>
            );
          }
          if (trimmedPara.startsWith('#### ')) {
            const text = trimmedPara.replace('#### ', '');
            return (
              <h4 key={index} id={generateHeadingId(text, index)} className="text-base font-medium text-gray-200 mt-3 mb-2 border-l-2 border-gray-500 pl-3">
                {text}
              </h4>
            );
          }
          if (trimmedPara.startsWith('### ')) {
            const text = trimmedPara.replace('### ', '');
            return (
              <h4 key={index} id={generateHeadingId(text, index)} className="text-lg font-semibold text-white mt-4 mb-3 border-l-4 border-blue-500 pl-4 bg-blue-500/5 py-2 rounded-r">
                {text}
              </h4>
            );
          }
          if (trimmedPara.startsWith('## ')) {
            const text = trimmedPara.replace('## ', '');
            return (
              <h3 key={index} id={generateHeadingId(text, index)} className="text-xl font-semibold text-gray-100 mt-5 mb-3 border-b border-gray-600 pb-2">
                {text}
              </h3>
            );
          }
          if (trimmedPara.startsWith('# ')) {
            const text = trimmedPara.replace('# ', '');
            return (
              <h2 key={index} id={generateHeadingId(text, index)} className="text-2xl font-bold text-white mt-6 mb-4 border-b-2 border-blue-500 pb-3">
                {text}
              </h2>
            );
          }
          
          // ✂️ 智能长段落分段处理 - 针对中文连续文本优化
          const sentences = trimmedPara.split(/(?<=[。！？.!?])\s*/);
          
          // 🔥 特别处理超长连续文本 - 如果段落超长且句子很少，进行强制智能分段
          if (trimmedPara.length > 300 && sentences.length <= 3) {
            // 按语义关键词分段
            const keywordBreaks = [
              '主要功能', '核心区域', '设计要求', '建筑特点', '空间布局', '功能分区',
              '设计原则', '主要特色', '重要节点', '关键要素', '核心功能', '主要内容',
              '基本要求', '设计理念', '空间特征', '功能需求', '设计目标', '主要方向'
            ];
            
            let segmented = trimmedPara;
            keywordBreaks.forEach(keyword => {
              segmented = segmented.replace(
                new RegExp(`([。！？])(?=.*?${keyword})`, 'g'), 
                '$1\n\n'
              );
            });
            
            // 如果还是太长，按逗号进行更细致的分段
            if (segmented.length > 200) {
              segmented = segmented.replace(/([，、])(?=.{30,}[。！？])/g, '$1\n');
            }
            
            const segments = segmented.split(/\n\n+/).filter(seg => seg.trim());
            
            return (
              <div key={index} className="space-y-4">
                {segments.map((segment, segIdx) => (
                  <p key={segIdx} className="text-sm text-gray-300 leading-[1.8] text-justify indent-2">
                    {segment.trim()}
                  </p>
                ))}
              </div>
            );
          }
          
          // 如果段落很长（超过150字符）且有多个句子，进行常规智能分段
          if (trimmedPara.length > 150 && sentences.length > 2) {
            // 按句子逻辑分组，保持意思连贯
            const groups: string[] = [];
            let currentGroup = '';
            let charCount = 0;
            
            sentences.forEach((sentence, sIdx) => {
              const sentenceLength = sentence.trim().length;
              
              // 如果当前组已经有内容且加上新句子会超过120字符，或已有2个完整句子
              if (currentGroup && (charCount + sentenceLength > 120 || currentGroup.split(/[。！？.!?]/).length >= 3)) {
                if (currentGroup.trim()) {
                  groups.push(currentGroup.trim());
                }
                currentGroup = sentence;
                charCount = sentenceLength;
              } else {
                currentGroup += (currentGroup ? ' ' : '') + sentence;
                charCount += sentenceLength;
              }
            });
            
            // 添加剩余内容
            if (currentGroup.trim()) {
              groups.push(currentGroup.trim());
            }
            
            return (
              <div key={index} className="space-y-3">
                {groups.map((group, gIdx) => (
                  <p key={gIdx} className="text-sm text-gray-300 leading-[1.8] text-justify indent-2">
                    {group}
                  </p>
                ))}
              </div>
            );
          }
          
          // 🎨 增强列表检测和渲染
          const lines = trimmedPara.split('\n');
          const isListItem = lines.every(line => 
            line.trim().startsWith('- ') || 
            line.trim().startsWith('• ') || 
            line.trim().startsWith('* ') ||
            line.trim().startsWith('+ ') ||
            line.trim().startsWith('· ') ||
            /^\d+[.、)]\s/.test(line.trim()) ||
            /^[a-zA-Z][.、)]\s/.test(line.trim()) ||  // a. b. c. 格式
            line.trim() === ''
          );
          
          if (isListItem && lines.length > 1) {
            return (
              <ul key={index} className="space-y-2 my-4 pl-1">
                {lines.filter(line => line.trim()).map((line, lineIndex) => {
                  const cleanLine = line.replace(/^[-•*+·]\s*/, '').replace(/^\d+[.、)]\s*/, '').replace(/^[a-zA-Z][.、)]\s*/, '');
                  return (
                    <li key={lineIndex} className="text-sm text-gray-300 flex items-start gap-3 leading-relaxed">
                      <span className="text-blue-400 mt-1.5 flex-shrink-0 w-2 h-2 bg-blue-400 rounded-full"></span>
                      <span className="flex-1">{cleanLine}</span>
                    </li>
                  );
                })}
              </ul>
            );
          }
          
                // 📝 普通段落渲染优化
                return (
                  <p className="text-sm text-gray-300 leading-[1.8] mb-4 text-justify indent-2 block">
                    {trimmedPara}
                  </p>
                );
              })()} 
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div 
      id={`section-${section.section_id}`}
      className="bg-[var(--card-bg)] border border-[var(--border-color)] rounded-xl overflow-hidden"
    >
      {/* 章节头部 */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-5 py-4 flex items-center justify-between hover:bg-[var(--sidebar-bg)] transition-colors"
      >
        <div className="flex items-center gap-3">
          <BarChart3 className="w-5 h-5 text-blue-400" />
          <h3 className="text-base font-medium text-white">{section.title}</h3>
        </div>
        <div className="flex items-center gap-3">
          {/* 置信度指示器 */}
          <span className={`text-xs px-2 py-1 rounded-full ${getConfidenceColor(section.confidence)}`}>
            {Math.round(section.confidence * 100)}% 置信度
          </span>
          {expanded ? (
            <ChevronUp className="w-5 h-5 text-gray-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-gray-400" />
          )}
        </div>
      </button>

      {/* 章节内容 */}
      {expanded && (
        <div className="px-5 pb-5 border-t border-[var(--border-color)]">
          <div className="pt-4">
            {formatContent(section.content)}
          </div>
        </div>
      )}
    </div>
  );
};

export default ReportSectionCard;
