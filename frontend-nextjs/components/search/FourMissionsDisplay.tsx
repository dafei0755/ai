'use client';

import React, { useState } from 'react';
import {
  FourMissions,
  Mission1UserProblemAnalysis,
  Mission2ClearObjectives,
  Mission3TaskDimensions,
  Mission4ExecutionRequirements,
  DeliverableItem,
  KeyStep,
  BreakthroughPoint
} from '@/types';
import {
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
  User,
  Target,
  Lightbulb,
  AlertTriangle,
  MapPin,
  Ruler,
  Tag,
  Lock,
  Heart,
  Zap,
  Package,
  CheckCircle,
  Users,
  Layers,
  TrendingUp,
  Shield,
  XCircle,
  AlertCircle,
  Wrench
} from 'lucide-react';

interface FourMissionsDisplayProps {
  missions: FourMissions;
  className?: string;
}

interface MissionCardProps {
  title: string;
  description: string;
  icon: React.ReactNode;
  color: string;
  children: React.ReactNode;
  defaultExpanded?: boolean;
}

const MissionCard: React.FC<MissionCardProps> = ({
  title,
  description,
  icon,
  color,
  children,
  defaultExpanded = true
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  return (
    <div className={`border rounded-lg overflow-hidden ${color} bg-white shadow-sm`}>
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${color.replace('border-l-4', 'bg-opacity-10')}`}>
            {icon}
          </div>
          <div className="text-left">
            <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
            <p className="text-sm text-gray-600">{description}</p>
          </div>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-5 h-5 text-gray-400" />
        ) : (
          <ChevronDown className="w-5 h-5 text-gray-400" />
        )}
      </button>

      {isExpanded && (
        <div className="px-6 py-4 border-t bg-gray-50">
          {children}
        </div>
      )}
    </div>
  );
};

const InfoItem: React.FC<{
  icon: React.ReactNode;
  label: string;
  value: string | string[];
  color?: string;
}> = ({ icon, label, value, color = 'text-blue-600' }) => {
  const displayValue = Array.isArray(value) ? value.join(', ') : value;

  return (
    <div className="flex items-start gap-3 mb-3">
      <div className={`mt-0.5 ${color}`}>{icon}</div>
      <div className="flex-1">
        <span className="text-sm font-medium text-gray-700">{label}:</span>
        <p className="text-sm text-gray-900 mt-1">{displayValue}</p>
      </div>
    </div>
  );
};

export const FourMissionsDisplay: React.FC<FourMissionsDisplayProps> = ({
  missions,
  className = ''
}) => {
  const [copiedSection, setCopiedSection] = useState<string | null>(null);

  const copyToClipboard = (text: string, section: string) => {
    navigator.clipboard.writeText(text);
    setCopiedSection(section);
    setTimeout(() => setCopiedSection(null), 2000);
  };

  const formatMission1Text = (mission: Mission1UserProblemAnalysis): string => {
    const { content } = mission;
    return `
【使命1：用户问题分析】

用户身份: ${content.user_identity}
项目类型: ${content.project_type}
项目地点: ${content.project_location}
项目规模: ${content.project_scale}
核心主题: ${content.core_theme}
关键约束: ${content.key_constraints.join(', ')}
用户动机: ${content.user_motivation}
核心矛盾: ${content.core_tension}
    `.trim();
  };

  const formatMission2Text = (mission: Mission2ClearObjectives): string => {
    const { content } = mission;
    const deliverables = content.key_deliverables
      .map((d, i) => `${i + 1}. [${d.id}] ${d.name}: ${d.description} (${d.priority})`)
      .join('\n');
    const criteria = content.success_criteria
      .map((c, i) => `${i + 1}. ${c}`)
      .join('\n');

    return `
【使命2：明确目标】

交付物类型: ${content.final_deliverable_type}
输出格式: ${content.output_format}
目标受众: ${content.target_audience}

关键交付物:
${deliverables}

成功标准:
${criteria}
    `.trim();
  };

  const formatMission3Text = (mission: Mission3TaskDimensions): string => {
    const { content } = mission;
    const steps = content.key_steps
      .map((s, i) => `${i + 1}. [${s.step_id}] ${s.action}\n   目的: ${s.purpose}\n   预期输出: ${s.expected_output}`)
      .join('\n\n');
    const breakthroughs = content.breakthrough_points
      .map((b, i) => `${i + 1}. ${b.point}\n   关键原因: ${b.why_key}\n   利用方式: ${b.how_to_leverage}`)
      .join('\n\n');

    return `
【使命3：任务维度】

任务类型: ${content.task_type}
复杂度: ${content.complexity_level}
解题方法论: ${content.solution_approach}
所需专业: ${content.required_expertise.join(', ')}

关键步骤:
${steps}

突破点:
${breakthroughs}
    `.trim();
  };

  const formatMission4Text = (mission: Mission4ExecutionRequirements): string => {
    const { content } = mission;
    const standards = content.quality_standards.map((s, i) => `${i + 1}. ${s}`).join('\n');
    const constraints = content.constraints_to_respect.map((c, i) => `${i + 1}. ${c}`).join('\n');
    const antiPatterns = content.anti_patterns.map((a, i) => `${i + 1}. ${a}`).join('\n');
    const risks = content.risk_alerts.map((r, i) => `${i + 1}. ${r}`).join('\n');
    const tools = content.recommended_tools.map((t, i) => `${i + 1}. ${t}`).join('\n');

    return `
【使命4：执行要求】

质量标准:
${standards}

必须遵守的约束:
${constraints}

应避免的做法:
${antiPatterns}

潜在风险:
${risks}

推荐工具:
${tools}
    `.trim();
  };

  const formatAllMissions = (): string => {
    return `
${missions.creation_command}

${formatMission1Text(missions.mission_1_user_problem_analysis)}

${formatMission2Text(missions.mission_2_clear_objectives)}

${formatMission3Text(missions.mission_3_task_dimensions)}

${formatMission4Text(missions.mission_4_execution_requirements)}

---
分析质量:
- L5锐度评分: ${missions.metadata.analysis_quality.l5_sharpness_score}
- 交付物验证评分: ${missions.metadata.analysis_quality.deliverables_validation_score}
- 整体置信度: ${missions.metadata.analysis_quality.overall_confidence}
    `.trim();
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {/* 创作指令 */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <h2 className="text-sm font-medium text-blue-900 mb-2">创作指令</h2>
            <p className="text-lg font-semibold text-blue-900">{missions.creation_command}</p>
          </div>
          <button
            onClick={() => copyToClipboard(formatAllMissions(), 'all')}
            className="flex items-center gap-2 px-3 py-2 text-sm bg-white border border-blue-300 rounded-lg hover:bg-blue-50 transition-colors"
          >
            {copiedSection === 'all' ? (
              <>
                <Check className="w-4 h-4 text-green-600" />
                <span className="text-green-600">已复制</span>
              </>
            ) : (
              <>
                <Copy className="w-4 h-4 text-blue-600" />
                <span className="text-blue-600">复制全部</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* 使命1：用户问题分析 */}
      <MissionCard
        title="使命1：用户问题分析"
        description="结构化梳理用户信息"
        icon={<User className="w-5 h-5 text-blue-600" />}
        color="border-l-4 border-blue-500"
      >
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <InfoItem
              icon={<User className="w-4 h-4" />}
              label="用户身份"
              value={missions.mission_1_user_problem_analysis.content.user_identity}
              color="text-blue-600"
            />
            <InfoItem
              icon={<Layers className="w-4 h-4" />}
              label="项目类型"
              value={missions.mission_1_user_problem_analysis.content.project_type}
              color="text-purple-600"
            />
            <InfoItem
              icon={<MapPin className="w-4 h-4" />}
              label="项目地点"
              value={missions.mission_1_user_problem_analysis.content.project_location}
              color="text-green-600"
            />
            <InfoItem
              icon={<Ruler className="w-4 h-4" />}
              label="项目规模"
              value={missions.mission_1_user_problem_analysis.content.project_scale}
              color="text-orange-600"
            />
          </div>

          <InfoItem
            icon={<Tag className="w-4 h-4" />}
            label="核心主题"
            value={missions.mission_1_user_problem_analysis.content.core_theme}
            color="text-pink-600"
          />

          <InfoItem
            icon={<Lock className="w-4 h-4" />}
            label="关键约束"
            value={missions.mission_1_user_problem_analysis.content.key_constraints}
            color="text-red-600"
          />

          <InfoItem
            icon={<Heart className="w-4 h-4" />}
            label="用户动机"
            value={missions.mission_1_user_problem_analysis.content.user_motivation}
            color="text-rose-600"
          />

          <InfoItem
            icon={<Zap className="w-4 h-4" />}
            label="核心矛盾"
            value={missions.mission_1_user_problem_analysis.content.core_tension}
            color="text-yellow-600"
          />

          <button
            onClick={() => copyToClipboard(formatMission1Text(missions.mission_1_user_problem_analysis), 'mission1')}
            className="mt-4 flex items-center gap-2 px-3 py-2 text-sm bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 transition-colors"
          >
            {copiedSection === 'mission1' ? (
              <>
                <Check className="w-4 h-4 text-green-600" />
                <span className="text-green-600">已复制</span>
              </>
            ) : (
              <>
                <Copy className="w-4 h-4 text-blue-600" />
                <span className="text-blue-600">复制使命1</span>
              </>
            )}
          </button>
        </div>
      </MissionCard>

      {/* 使命2：明确目标 */}
      <MissionCard
        title="使命2：明确目标"
        description="用户最后要的是什么"
        icon={<Target className="w-5 h-5 text-green-600" />}
        color="border-l-4 border-green-500"
      >
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <InfoItem
              icon={<Package className="w-4 h-4" />}
              label="交付物类型"
              value={missions.mission_2_clear_objectives.content.final_deliverable_type}
              color="text-green-600"
            />
            <InfoItem
              icon={<Layers className="w-4 h-4" />}
              label="输出格式"
              value={missions.mission_2_clear_objectives.content.output_format}
              color="text-blue-600"
            />
            <InfoItem
              icon={<Users className="w-4 h-4" />}
              label="目标受众"
              value={missions.mission_2_clear_objectives.content.target_audience}
              color="text-purple-600"
            />
          </div>

          {/* 关键交付物 */}
          <div className="mt-4">
            <h4 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-green-600" />
              关键交付物 ({missions.mission_2_clear_objectives.content.key_deliverables.length}项)
            </h4>
            <div className="space-y-2">
              {missions.mission_2_clear_objectives.content.key_deliverables.map((deliverable, index) => (
                <div
                  key={deliverable.id}
                  className="bg-white border border-gray-200 rounded-lg p-3 hover:border-green-300 transition-colors"
                >
                  <div className="flex items-start gap-3">
                    <span className="flex-shrink-0 w-6 h-6 bg-green-100 text-green-700 rounded-full flex items-center justify-center text-xs font-semibold">
                      {index + 1}
                    </span>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-medium text-gray-900">{deliverable.name}</span>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${
                          deliverable.priority === 'MUST_HAVE'
                            ? 'bg-red-100 text-red-700'
                            : 'bg-blue-100 text-blue-700'
                        }`}>
                          {deliverable.priority === 'MUST_HAVE' ? '必需' : '可选'}
                        </span>
                      </div>
                      <p className="text-sm text-gray-600">{deliverable.description}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 成功标准 */}
          <div className="mt-4">
            <h4 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-green-600" />
              成功标准
            </h4>
            <ul className="space-y-2">
              {missions.mission_2_clear_objectives.content.success_criteria.map((criterion, index) => (
                <li key={index} className="flex items-start gap-2 text-sm text-gray-700">
                  <CheckCircle className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                  <span>{criterion}</span>
                </li>
              ))}
            </ul>
          </div>

          <button
            onClick={() => copyToClipboard(formatMission2Text(missions.mission_2_clear_objectives), 'mission2')}
            className="mt-4 flex items-center gap-2 px-3 py-2 text-sm bg-green-50 border border-green-200 rounded-lg hover:bg-green-100 transition-colors"
          >
            {copiedSection === 'mission2' ? (
              <>
                <Check className="w-4 h-4 text-green-600" />
                <span className="text-green-600">已复制</span>
              </>
            ) : (
              <>
                <Copy className="w-4 h-4 text-green-600" />
                <span className="text-green-600">复制使命2</span>
              </>
            )}
          </button>
        </div>
      </MissionCard>

      {/* 使命3：任务维度 */}
      <MissionCard
        title="使命3：任务维度"
        description="解题思路"
        icon={<Lightbulb className="w-5 h-5 text-yellow-600" />}
        color="border-l-4 border-yellow-500"
      >
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <InfoItem
              icon={<Layers className="w-4 h-4" />}
              label="任务类型"
              value={missions.mission_3_task_dimensions.content.task_type}
              color="text-yellow-600"
            />
            <InfoItem
              icon={<TrendingUp className="w-4 h-4" />}
              label="复杂度"
              value={missions.mission_3_task_dimensions.content.complexity_level}
              color="text-orange-600"
            />
          </div>

          <InfoItem
            icon={<Lightbulb className="w-4 h-4" />}
            label="解题方法论"
            value={missions.mission_3_task_dimensions.content.solution_approach}
            color="text-purple-600"
          />

          <InfoItem
            icon={<Users className="w-4 h-4" />}
            label="所需专业"
            value={missions.mission_3_task_dimensions.content.required_expertise}
            color="text-blue-600"
          />

          {/* 关键步骤 */}
          <div className="mt-4">
            <h4 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <Layers className="w-4 h-4 text-yellow-600" />
              关键步骤 ({missions.mission_3_task_dimensions.content.key_steps.length}个)
            </h4>
            <div className="space-y-3">
              {missions.mission_3_task_dimensions.content.key_steps.map((step, index) => (
                <div
                  key={step.step_id}
                  className="bg-white border border-gray-200 rounded-lg p-4 hover:border-yellow-300 transition-colors"
                >
                  <div className="flex items-start gap-3">
                    <span className="flex-shrink-0 w-8 h-8 bg-yellow-100 text-yellow-700 rounded-full flex items-center justify-center text-sm font-semibold">
                      {index + 1}
                    </span>
                    <div className="flex-1 space-y-2">
                      <p className="text-sm font-medium text-gray-900">{step.action}</p>
                      <div className="text-xs text-gray-600 space-y-1">
                        <p><span className="font-medium">目的:</span> {step.purpose}</p>
                        <p><span className="font-medium">预期输出:</span> {step.expected_output}</p>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 突破点 */}
          <div className="mt-4">
            <h4 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <Zap className="w-4 h-4 text-yellow-600" />
              突破点
            </h4>
            <div className="space-y-3">
              {missions.mission_3_task_dimensions.content.breakthrough_points.map((bp, index) => (
                <div
                  key={index}
                  className="bg-gradient-to-r from-yellow-50 to-orange-50 border border-yellow-200 rounded-lg p-4"
                >
                  <p className="text-sm font-medium text-gray-900 mb-2">{bp.point}</p>
                  <div className="text-xs text-gray-600 space-y-1">
                    <p><span className="font-medium">关键原因:</span> {bp.why_key}</p>
                    <p><span className="font-medium">利用方式:</span> {bp.how_to_leverage}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <button
            onClick={() => copyToClipboard(formatMission3Text(missions.mission_3_task_dimensions), 'mission3')}
            className="mt-4 flex items-center gap-2 px-3 py-2 text-sm bg-yellow-50 border border-yellow-200 rounded-lg hover:bg-yellow-100 transition-colors"
          >
            {copiedSection === 'mission3' ? (
              <>
                <Check className="w-4 h-4 text-green-600" />
                <span className="text-green-600">已复制</span>
              </>
            ) : (
              <>
                <Copy className="w-4 h-4 text-yellow-600" />
                <span className="text-yellow-600">复制使命3</span>
              </>
            )}
          </button>
        </div>
      </MissionCard>

      {/* 使命4：执行要求 */}
      <MissionCard
        title="使命4：执行要求"
        description="注意事项"
        icon={<AlertTriangle className="w-5 h-5 text-red-600" />}
        color="border-l-4 border-red-500"
      >
        <div className="space-y-4">
          {/* 质量标准 */}
          <div>
            <h4 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <Shield className="w-4 h-4 text-green-600" />
              质量标准
            </h4>
            <ul className="space-y-2">
              {missions.mission_4_execution_requirements.content.quality_standards.map((standard, index) => (
                <li key={index} className="flex items-start gap-2 text-sm text-gray-700">
                  <CheckCircle className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                  <span>{standard}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* 必须遵守的约束 */}
          <div>
            <h4 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <Lock className="w-4 h-4 text-blue-600" />
              必须遵守的约束
            </h4>
            <ul className="space-y-2">
              {missions.mission_4_execution_requirements.content.constraints_to_respect.map((constraint, index) => (
                <li key={index} className="flex items-start gap-2 text-sm text-gray-700">
                  <AlertCircle className="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" />
                  <span>{constraint}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* 应避免的做法 */}
          <div>
            <h4 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <XCircle className="w-4 h-4 text-red-600" />
              应避免的做法
            </h4>
            <ul className="space-y-2">
              {missions.mission_4_execution_requirements.content.anti_patterns.map((pattern, index) => (
                <li key={index} className="flex items-start gap-2 text-sm text-gray-700">
                  <XCircle className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
                  <span>{pattern}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* 潜在风险 */}
          <div>
            <h4 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-orange-600" />
              潜在风险
            </h4>
            <ul className="space-y-2">
              {missions.mission_4_execution_requirements.content.risk_alerts.map((risk, index) => (
                <li key={index} className="flex items-start gap-2 text-sm text-gray-700">
                  <AlertTriangle className="w-4 h-4 text-orange-500 mt-0.5 flex-shrink-0" />
                  <span>{risk}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* 推荐工具 */}
          <div>
            <h4 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <Wrench className="w-4 h-4 text-purple-600" />
              推荐工具
            </h4>
            <ul className="space-y-2">
              {missions.mission_4_execution_requirements.content.recommended_tools.map((tool, index) => (
                <li key={index} className="flex items-start gap-2 text-sm text-gray-700">
                  <Wrench className="w-4 h-4 text-purple-500 mt-0.5 flex-shrink-0" />
                  <span>{tool}</span>
                </li>
              ))}
            </ul>
          </div>

          <button
            onClick={() => copyToClipboard(formatMission4Text(missions.mission_4_execution_requirements), 'mission4')}
            className="mt-4 flex items-center gap-2 px-3 py-2 text-sm bg-red-50 border border-red-200 rounded-lg hover:bg-red-100 transition-colors"
          >
            {copiedSection === 'mission4' ? (
              <>
                <Check className="w-4 h-4 text-green-600" />
                <span className="text-green-600">已复制</span>
              </>
            ) : (
              <>
                <Copy className="w-4 h-4 text-red-600" />
                <span className="text-red-600">复制使命4</span>
              </>
            )}
          </button>
        </div>
      </MissionCard>

      {/* 分析质量指标 */}
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">分析质量指标</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white rounded-lg p-3 border border-gray-200">
            <p className="text-xs text-gray-600 mb-1">L5锐度评分</p>
            <p className="text-2xl font-bold text-blue-600">
              {missions.metadata.analysis_quality.l5_sharpness_score}
            </p>
          </div>
          <div className="bg-white rounded-lg p-3 border border-gray-200">
            <p className="text-xs text-gray-600 mb-1">交付物验证评分</p>
            <p className="text-2xl font-bold text-green-600">
              {missions.metadata.analysis_quality.deliverables_validation_score}
            </p>
          </div>
          <div className="bg-white rounded-lg p-3 border border-gray-200">
            <p className="text-xs text-gray-600 mb-1">整体置信度</p>
            <p className="text-2xl font-bold text-purple-600">
              {(missions.metadata.analysis_quality.overall_confidence * 100).toFixed(0)}%
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FourMissionsDisplay;
