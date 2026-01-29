/**
 * 深度分析展示卡片组件
 *
 * 🆕 v7.280: 展示完整的 L1-L5 分析维度和人性化维度
 *
 * 设计原则：
 * 1. 扁平化展示 - 所有维度默认展开，无需折叠
 * 2. 配置驱动 - 维度定义来自后端配置
 * 3. 完整呈现 - 不丢失任何分析维度
 */

'use client';

import React from 'react';
import {
  Layers,
  Eye,
  Zap,
  Target,
  Gauge,
  Heart,
  Building2,
  MapPin,
  User,
  Package,
  Calendar,
  Lightbulb,
  Sparkles,
  Shield,
  Clock,
  Bookmark,
  ChevronRight,
} from 'lucide-react';
import type {
  DeepAnalysisResult,
  L1FactsLayer,
  PerspectiveAnalysis,
  CoreTension,
  UserTask,
  SharpnessAssessment,
  HumanDimensions,
} from '@/types';

interface DeepAnalysisCardProps {
  analysis: DeepAnalysisResult | null;
  isExpanded?: boolean;
  onToggle?: () => void;
}

/**
 * L1 事实层展示组件
 */
const L1FactsSection: React.FC<{ facts: L1FactsLayer }> = ({ facts }) => {
  const entitySections = [
    { key: 'brands', label: '品牌', icon: Building2, color: 'blue', data: facts.brands },
    { key: 'locations', label: '地点', icon: MapPin, color: 'green', data: facts.locations },
    { key: 'persons', label: '人物', icon: User, color: 'purple', data: facts.persons },
    { key: 'items', label: '物品', icon: Package, color: 'orange', data: facts.items },
    { key: 'events', label: '事件', icon: Calendar, color: 'pink', data: facts.events },
    { key: 'concepts', label: '概念', icon: Lightbulb, color: 'cyan', data: facts.concepts },
  ];

  const hasAnyData = entitySections.some(s => s.data && s.data.length > 0);
  if (!hasAnyData) return null;

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Layers className="w-4 h-4 text-blue-500" />
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">L1 事实层</span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {entitySections.map(section => {
          if (!section.data || section.data.length === 0) return null;
          const IconComponent = section.icon;
          return (
            <div
              key={section.key}
              className={`bg-${section.color}-50 dark:bg-${section.color}-900/10 rounded-lg p-3 border border-${section.color}-200 dark:border-${section.color}-800`}
            >
              <div className="flex items-center gap-2 mb-2">
                <IconComponent className={`w-4 h-4 text-${section.color}-600 dark:text-${section.color}-400`} />
                <span className={`text-xs font-medium text-${section.color}-700 dark:text-${section.color}-300`}>
                  {section.label} ({section.data.length})
                </span>
              </div>
              <div className="space-y-2">
                {section.data.map((entity: any, idx: number) => (
                  <div key={idx} className="text-xs text-gray-600 dark:text-gray-400">
                    <span className="font-medium text-gray-800 dark:text-gray-200">
                      {entity.name}
                    </span>
                    {entity.positioning && (
                      <span className="ml-1 text-gray-500">- {entity.positioning}</span>
                    )}
                    {entity.type && (
                      <span className="ml-1 text-gray-500">({entity.type})</span>
                    )}
                    {entity.role && (
                      <span className="ml-1 text-gray-500">- {entity.role}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

/**
 * L2 多视角分析展示组件
 */
const L2PerspectivesSection: React.FC<{ perspectives: PerspectiveAnalysis[] }> = ({ perspectives }) => {
  if (!perspectives || perspectives.length === 0) return null;

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Eye className="w-4 h-4 text-indigo-500" />
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">L2 多视角分析</span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {perspectives.map((perspective, idx) => (
          <div
            key={idx}
            className="bg-indigo-50 dark:bg-indigo-900/10 rounded-lg p-3 border border-indigo-200 dark:border-indigo-800"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-indigo-700 dark:text-indigo-300">
                {perspective.perspective_name}
              </span>
              <span className="text-xs bg-indigo-100 dark:bg-indigo-800 text-indigo-600 dark:text-indigo-300 px-2 py-0.5 rounded">
                权重: {(perspective.weight * 100).toFixed(0)}%
              </span>
            </div>
            <p className="text-xs text-gray-600 dark:text-gray-400 mb-2">
              {perspective.analysis}
            </p>
            {perspective.key_considerations && perspective.key_considerations.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {perspective.key_considerations.slice(0, 3).map((consideration, i) => (
                  <span
                    key={i}
                    className="text-xs bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 px-2 py-0.5 rounded border border-gray-200 dark:border-gray-700"
                  >
                    {consideration}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

/**
 * L3 核心张力展示组件
 */
const L3TensionSection: React.FC<{ tension: CoreTension }> = ({ tension }) => {
  if (!tension || !tension.tension_statement) return null;

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Zap className="w-4 h-4 text-amber-500" />
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">L3 核心张力</span>
      </div>
      <div className="bg-amber-50 dark:bg-amber-900/10 rounded-lg p-4 border border-amber-200 dark:border-amber-800">
        <p className="text-sm text-amber-800 dark:text-amber-200 font-medium mb-3">
          {tension.tension_statement}
        </p>
        {tension.conflicting_goals && tension.conflicting_goals.length > 0 && (
          <div className="mb-3">
            <span className="text-xs text-amber-600 dark:text-amber-400 font-medium">冲突目标:</span>
            <div className="flex flex-wrap gap-1 mt-1">
              {tension.conflicting_goals.map((goal, idx) => (
                <span
                  key={idx}
                  className="text-xs bg-amber-100 dark:bg-amber-800 text-amber-700 dark:text-amber-300 px-2 py-0.5 rounded"
                >
                  {goal}
                </span>
              ))}
            </div>
          </div>
        )}
        {tension.resolution_strategy && (
          <div>
            <span className="text-xs text-amber-600 dark:text-amber-400 font-medium">解决策略:</span>
            <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
              {tension.resolution_strategy}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * L4 用户任务展示组件
 */
const L4TaskSection: React.FC<{ task: UserTask }> = ({ task }) => {
  if (!task || !task.jtbd_statement) return null;

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Target className="w-4 h-4 text-emerald-500" />
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">L4 用户任务 (JTBD)</span>
      </div>
      <div className="bg-emerald-50 dark:bg-emerald-900/10 rounded-lg p-4 border border-emerald-200 dark:border-emerald-800">
        <p className="text-sm text-emerald-800 dark:text-emerald-200 font-medium mb-3">
          {task.jtbd_statement}
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {task.functional_job && (
            <div className="bg-white dark:bg-gray-800 rounded p-2 border border-emerald-200 dark:border-emerald-700">
              <span className="text-xs text-emerald-600 dark:text-emerald-400 font-medium block mb-1">功能任务</span>
              <span className="text-xs text-gray-600 dark:text-gray-400">{task.functional_job}</span>
            </div>
          )}
          {task.emotional_job && (
            <div className="bg-white dark:bg-gray-800 rounded p-2 border border-emerald-200 dark:border-emerald-700">
              <span className="text-xs text-emerald-600 dark:text-emerald-400 font-medium block mb-1">情感任务</span>
              <span className="text-xs text-gray-600 dark:text-gray-400">{task.emotional_job}</span>
            </div>
          )}
          {task.social_job && (
            <div className="bg-white dark:bg-gray-800 rounded p-2 border border-emerald-200 dark:border-emerald-700">
              <span className="text-xs text-emerald-600 dark:text-emerald-400 font-medium block mb-1">社会任务</span>
              <span className="text-xs text-gray-600 dark:text-gray-400">{task.social_job}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

/**
 * L5 锐度评估展示组件
 */
const L5SharpnessSection: React.FC<{ sharpness: SharpnessAssessment }> = ({ sharpness }) => {
  if (!sharpness || sharpness.score === undefined) return null;

  // 锐度评分颜色
  const getScoreColor = (score: number) => {
    if (score >= 8) return 'text-emerald-600 bg-emerald-100 dark:text-emerald-400 dark:bg-emerald-900/30';
    if (score >= 6) return 'text-blue-600 bg-blue-100 dark:text-blue-400 dark:bg-blue-900/30';
    if (score >= 4) return 'text-amber-600 bg-amber-100 dark:text-amber-400 dark:bg-amber-900/30';
    return 'text-red-600 bg-red-100 dark:text-red-400 dark:bg-red-900/30';
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Gauge className="w-4 h-4 text-purple-500" />
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">L5 锐度评估</span>
      </div>
      <div className="bg-purple-50 dark:bg-purple-900/10 rounded-lg p-4 border border-purple-200 dark:border-purple-800">
        <div className="flex items-center gap-4 mb-3">
          <div className={`text-2xl font-bold px-3 py-1 rounded-lg ${getScoreColor(sharpness.score)}`}>
            {sharpness.score.toFixed(1)}
          </div>
          <div className="text-sm text-gray-600 dark:text-gray-400">
            / 10 分
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {sharpness.specificity && (
            <div className="bg-white dark:bg-gray-800 rounded p-2 border border-purple-200 dark:border-purple-700">
              <span className="text-xs text-purple-600 dark:text-purple-400 font-medium block mb-1">具体性</span>
              <span className="text-xs text-gray-600 dark:text-gray-400">{sharpness.specificity}</span>
            </div>
          )}
          {sharpness.actionability && (
            <div className="bg-white dark:bg-gray-800 rounded p-2 border border-purple-200 dark:border-purple-700">
              <span className="text-xs text-purple-600 dark:text-purple-400 font-medium block mb-1">可操作性</span>
              <span className="text-xs text-gray-600 dark:text-gray-400">{sharpness.actionability}</span>
            </div>
          )}
          {sharpness.depth && (
            <div className="bg-white dark:bg-gray-800 rounded p-2 border border-purple-200 dark:border-purple-700">
              <span className="text-xs text-purple-600 dark:text-purple-400 font-medium block mb-1">深度</span>
              <span className="text-xs text-gray-600 dark:text-gray-400">{sharpness.depth}</span>
            </div>
          )}
        </div>
        {sharpness.improvement_suggestions && sharpness.improvement_suggestions.length > 0 && (
          <div className="mt-3 pt-3 border-t border-purple-200 dark:border-purple-700">
            <span className="text-xs text-purple-600 dark:text-purple-400 font-medium">改进建议:</span>
            <ul className="mt-1 space-y-1">
              {sharpness.improvement_suggestions.map((suggestion, idx) => (
                <li key={idx} className="text-xs text-gray-600 dark:text-gray-400 flex items-start gap-1">
                  <span className="text-purple-400">•</span>
                  {suggestion}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * 人性化维度展示组件
 */
const HumanDimensionsSection: React.FC<{ dimensions: HumanDimensions }> = ({ dimensions }) => {
  if (!dimensions) return null;

  const hasAnyData = dimensions.emotion_map || dimensions.spiritual_pursuit ||
    dimensions.psychological_safety || dimensions.ritual_behaviors || dimensions.memory_anchors;

  if (!hasAnyData) return null;

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Heart className="w-4 h-4 text-rose-500" />
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">人性化维度</span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {/* 情感地图 */}
        {dimensions.emotion_map && (
          <div className="bg-rose-50 dark:bg-rose-900/10 rounded-lg p-3 border border-rose-200 dark:border-rose-800">
            <div className="flex items-center gap-2 mb-2">
              <Sparkles className="w-4 h-4 text-rose-500" />
              <span className="text-xs font-medium text-rose-700 dark:text-rose-300">情感地图</span>
            </div>
            <div className="space-y-2">
              {dimensions.emotion_map.primary_emotions && (
                <div>
                  <span className="text-xs text-rose-600 dark:text-rose-400">主要情绪:</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {dimensions.emotion_map.primary_emotions.map((e, i) => (
                      <span key={i} className="text-xs bg-rose-100 dark:bg-rose-800 text-rose-700 dark:text-rose-300 px-1.5 py-0.5 rounded">
                        {e}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* 精神追求 */}
        {dimensions.spiritual_pursuit && (
          <div className="bg-violet-50 dark:bg-violet-900/10 rounded-lg p-3 border border-violet-200 dark:border-violet-800">
            <div className="flex items-center gap-2 mb-2">
              <Lightbulb className="w-4 h-4 text-violet-500" />
              <span className="text-xs font-medium text-violet-700 dark:text-violet-300">精神追求</span>
            </div>
            <div className="space-y-2">
              {dimensions.spiritual_pursuit.core_values && (
                <div>
                  <span className="text-xs text-violet-600 dark:text-violet-400">核心价值观:</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {dimensions.spiritual_pursuit.core_values.map((v, i) => (
                      <span key={i} className="text-xs bg-violet-100 dark:bg-violet-800 text-violet-700 dark:text-violet-300 px-1.5 py-0.5 rounded">
                        {v}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* 心理安全 */}
        {dimensions.psychological_safety && (
          <div className="bg-sky-50 dark:bg-sky-900/10 rounded-lg p-3 border border-sky-200 dark:border-sky-800">
            <div className="flex items-center gap-2 mb-2">
              <Shield className="w-4 h-4 text-sky-500" />
              <span className="text-xs font-medium text-sky-700 dark:text-sky-300">心理安全</span>
            </div>
            <div className="space-y-2">
              {dimensions.psychological_safety.safety_needs && (
                <div>
                  <span className="text-xs text-sky-600 dark:text-sky-400">安全需求:</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {dimensions.psychological_safety.safety_needs.map((n, i) => (
                      <span key={i} className="text-xs bg-sky-100 dark:bg-sky-800 text-sky-700 dark:text-sky-300 px-1.5 py-0.5 rounded">
                        {n}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* 仪式行为 */}
        {dimensions.ritual_behaviors && (
          <div className="bg-teal-50 dark:bg-teal-900/10 rounded-lg p-3 border border-teal-200 dark:border-teal-800">
            <div className="flex items-center gap-2 mb-2">
              <Clock className="w-4 h-4 text-teal-500" />
              <span className="text-xs font-medium text-teal-700 dark:text-teal-300">仪式行为</span>
            </div>
            <div className="space-y-2">
              {dimensions.ritual_behaviors.daily_rituals && (
                <div>
                  <span className="text-xs text-teal-600 dark:text-teal-400">日常仪式:</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {dimensions.ritual_behaviors.daily_rituals.map((r, i) => (
                      <span key={i} className="text-xs bg-teal-100 dark:bg-teal-800 text-teal-700 dark:text-teal-300 px-1.5 py-0.5 rounded">
                        {r}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* 记忆锚点 */}
        {dimensions.memory_anchors && (
          <div className="bg-amber-50 dark:bg-amber-900/10 rounded-lg p-3 border border-amber-200 dark:border-amber-800">
            <div className="flex items-center gap-2 mb-2">
              <Bookmark className="w-4 h-4 text-amber-500" />
              <span className="text-xs font-medium text-amber-700 dark:text-amber-300">记忆锚点</span>
            </div>
            <div className="space-y-2">
              {dimensions.memory_anchors.key_memories && (
                <div>
                  <span className="text-xs text-amber-600 dark:text-amber-400">关键记忆:</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {dimensions.memory_anchors.key_memories.map((m, i) => (
                      <span key={i} className="text-xs bg-amber-100 dark:bg-amber-800 text-amber-700 dark:text-amber-300 px-1.5 py-0.5 rounded">
                        {m}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * 深度分析卡片主组件
 */
const DeepAnalysisCard: React.FC<DeepAnalysisCardProps> = ({
  analysis,
  isExpanded = true,
  onToggle,
}) => {
  if (!analysis) return null;

  return (
    <div className="ucppt-card">
      {/* 标题栏 */}
      <div
        className={`ucppt-card-header ${isExpanded ? 'ucppt-card-header-expanded' : 'ucppt-card-header-collapsed'}`}
        onClick={onToggle}
      >
        <div className="flex items-center gap-3">
          <div className="ucppt-icon-circle ucppt-icon-indigo">
            <Layers className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
          </div>
          <div>
            <span className="ucppt-title-indigo">深度分析洞察</span>
            {analysis.motivation_type && (
              <span className="ml-2 text-xs bg-indigo-100 dark:bg-indigo-800 text-indigo-600 dark:text-indigo-300 px-2 py-0.5 rounded">
                动机: {analysis.motivation_type}
              </span>
            )}
          </div>
        </div>
        {onToggle && (
          <ChevronRight
            className={`w-5 h-5 text-gray-400 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
          />
        )}
      </div>

      {/* 内容区域 */}
      {isExpanded && (
        <div className="ucppt-card-content space-y-6">
          {/* L1 事实层 */}
          {analysis.l1_facts && <L1FactsSection facts={analysis.l1_facts} />}

          {/* L2 多视角分析 */}
          {analysis.l2_perspectives && <L2PerspectivesSection perspectives={analysis.l2_perspectives} />}

          {/* L3 核心张力 */}
          {analysis.l3_core_tension && <L3TensionSection tension={analysis.l3_core_tension} />}

          {/* L4 用户任务 */}
          {analysis.l4_user_task && <L4TaskSection task={analysis.l4_user_task} />}

          {/* L5 锐度评估 */}
          {analysis.l5_sharpness && <L5SharpnessSection sharpness={analysis.l5_sharpness} />}

          {/* 人性化维度 */}
          {analysis.human_dimensions && <HumanDimensionsSection dimensions={analysis.human_dimensions} />}
        </div>
      )}
    </div>
  );
};

export default DeepAnalysisCard;
