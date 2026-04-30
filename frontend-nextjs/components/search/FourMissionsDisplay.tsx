'use client';

import React, { useState } from 'react';
import {
  FourMissions,
} from '@/types';
import {
  Copy,
  Check,
  Target,
  User,
  Lightbulb,
  Wrench,
} from 'lucide-react';
import {
  formatAllMissionsToNaturalLanguage
} from '@/utils/missionFormatter';

interface FourMissionsDisplayProps {
  missions: FourMissions;
  className?: string;
}

export const FourMissionsDisplay: React.FC<FourMissionsDisplayProps> = ({
  missions,
  className = ''
}) => {
  const [copied, setCopied] = useState(false);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formattedContent = formatAllMissionsToNaturalLanguage(missions);

  // v7.302.10: 检查是否有内容 - 支持两种数据结构：
  // 1. missions.mission_x.content（嵌套结构）
  // 2. missions.mission_x 直接包含字段（扁平结构）
  const getMissionContent = (mission: any) => {
    if (!mission) return null;
    // 如果有 content 字段，返回 content
    if (mission.content && Object.keys(mission.content).length > 0) {
      return mission.content;
    }
    // 否则，mission 本身就是内容（扁平结构）
    // 检查是否有实际内容字段（排除 title 和 description）
    const contentKeys = Object.keys(mission).filter(k => k !== 'title' && k !== 'description');
    if (contentKeys.length > 0) {
      return mission;
    }
    return null;
  };

  const mission1Content = getMissionContent(missions.mission_1_user_problem_analysis);
  const mission2Content = getMissionContent(missions.mission_2_clear_objectives);
  const mission3Content = getMissionContent(missions.mission_3_task_dimensions);
  const mission4Content = getMissionContent(missions.mission_4_execution_requirements);

  const hasMission1 = !!mission1Content;
  const hasMission2 = !!mission2Content;
  const hasMission3 = !!mission3Content;
  const hasMission4 = !!mission4Content;

  return (
    <div className={`${className}`}>
      {/* 统一卡片：需求理解与深度分析 - v7.302.6 扁平化样式 */}
      <div className="ucppt-card">
        {/* 卡片头部 */}
        <div className="ucppt-card-header ucppt-card-header-expanded">
          <div className="flex items-center gap-3">
            <div className="ucppt-icon-circle ucppt-icon-blue">
              <Target className="w-4 h-4 text-blue-600 dark:text-blue-400" />
            </div>
            <div className="flex-1">
              <span className="ucppt-title-blue">需求理解与深度分析</span>
              {missions.creation_command && (
                <p className="text-xs text-gray-500 dark:text-gray-600 mt-0.5">
                  {missions.creation_command}
                </p>
              )}
            </div>
          </div>
          <button
            onClick={() => copyToClipboard(formattedContent)}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs bg-gray-100 dark:bg-gray-100 border border-gray-200 dark:border-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-200 transition-colors"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-green-600 dark:text-green-400" />
                <span className="text-green-600 dark:text-green-400">已复制</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5 text-gray-600 dark:text-gray-700" />
                <span className="text-gray-600 dark:text-gray-700">复制</span>
              </>
            )}
          </button>
        </div>

        {/* 4条使命内容 - 扁平化列表样式 */}
        <div className="ucppt-card-content">
          <div className="space-y-4">
            {/* 使命1: 用户问题分析 */}
            {hasMission1 && (
              <MissionSection
                icon={<User className="w-4 h-4" />}
                title="我的理解"
                colorClass="text-blue-600 dark:text-blue-400"
                bgClass="bg-blue-50 dark:bg-blue-900/20"
              >
                <MissionContent mission={missions.mission_1_user_problem_analysis} type="mission1" />
              </MissionSection>
            )}

            {/* 使命2: 明确目标 */}
            {hasMission2 && (
              <MissionSection
                icon={<Target className="w-4 h-4" />}
                title="项目目标"
                colorClass="text-emerald-600 dark:text-emerald-400"
                bgClass="bg-emerald-50 dark:bg-emerald-900/20"
              >
                <MissionContent mission={missions.mission_2_clear_objectives} type="mission2" />
              </MissionSection>
            )}

            {/* 使命3: 任务维度 */}
            {hasMission3 && (
              <MissionSection
                icon={<Lightbulb className="w-4 h-4" />}
                title="解题思路"
                colorClass="text-amber-600 dark:text-amber-400"
                bgClass="bg-amber-50 dark:bg-amber-900/20"
              >
                <MissionContent mission={missions.mission_3_task_dimensions} type="mission3" />
              </MissionSection>
            )}

            {/* 使命4: 执行要求 */}
            {hasMission4 && (
              <MissionSection
                icon={<Wrench className="w-4 h-4" />}
                title="执行计划"
                colorClass="text-purple-600 dark:text-purple-400"
                bgClass="bg-purple-50 dark:bg-purple-900/20"
              >
                <MissionContent mission={missions.mission_4_execution_requirements} type="mission4" />
              </MissionSection>
            )}

            {/* 无内容时显示加载状态 */}
            {!hasMission1 && !hasMission2 && !hasMission3 && !hasMission4 && (
              <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400 text-sm py-4">
                <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                <span>正在分析您的需求...</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// 使命区块组件
const MissionSection: React.FC<{
  icon: React.ReactNode;
  title: string;
  colorClass: string;
  bgClass: string;
  children: React.ReactNode;
}> = ({ icon, title, colorClass, bgClass, children }) => (
  <div className="space-y-2">
    <div className="flex items-center gap-2">
      <div className={`w-6 h-6 rounded-md flex items-center justify-center ${bgClass} ${colorClass}`}>
        {icon}
      </div>
      <h4 className={`text-sm font-medium ${colorClass}`}>{title}</h4>
    </div>
    <div className="pl-8 text-sm text-gray-900 dark:text-gray-100 leading-relaxed">
      {children}
    </div>
  </div>
);

// 使命内容渲染组件
const MissionContent: React.FC<{
  mission: any;
  type: 'mission1' | 'mission2' | 'mission3' | 'mission4';
}> = ({ mission, type }) => {
  // v7.302.10: 支持两种数据结构
  // 1. mission.content（嵌套结构）
  // 2. mission 本身包含字段（扁平结构）
  const getContent = () => {
    if (!mission) return null;
    if (mission.content && typeof mission.content === 'object') {
      return mission.content;
    }
    // 扁平结构：mission 本身就是内容
    return mission;
  };

  const content = getContent();
  if (!content) return null;

  switch (type) {
    case 'mission1':
      return (
        <div className="space-y-1.5">
          {content.user_identity && (
            <p>根据您的描述，我理解您可能是<strong>{content.user_identity}</strong>，正在进行<strong>{content.project_type || '项目'}</strong>设计。</p>
          )}
          {content.project_location && (
            <p><strong>地点</strong>：{content.project_location}{content.project_scale ? `，${content.project_scale}` : ''}</p>
          )}
          {content.core_theme && (
            <p><strong>核心主题</strong>：{content.core_theme}</p>
          )}
          {content.core_tension && (
            <p className="text-amber-700 dark:text-amber-400"><strong>设计挑战</strong>：{content.core_tension}</p>
          )}
          {content.key_constraints && content.key_constraints.length > 0 && (
            <p><strong>关键约束</strong>：{content.key_constraints.join('、')}</p>
          )}
        </div>
      );

    case 'mission2':
      return (
        <div className="space-y-1.5">
          {content.final_deliverable_type && (
            <p><strong>交付物类型</strong>：{content.final_deliverable_type}</p>
          )}
          {content.key_deliverables && content.key_deliverables.length > 0 && (
            <div>
              <p className="font-medium mb-1">核心交付物：</p>
              <ul className="list-disc list-inside space-y-0.5 text-gray-600 dark:text-gray-400">
                {content.key_deliverables.map((d: any, i: number) => (
                  <li key={i}>{d.name}：{d.description}</li>
                ))}
              </ul>
            </div>
          )}
          {content.success_criteria && content.success_criteria.length > 0 && (
            <p><strong>成功标准</strong>：{content.success_criteria.join('、')}</p>
          )}
        </div>
      );

    case 'mission3':
      return (
        <div className="space-y-1.5">
          {content.task_type && (
            <p><strong>任务类型</strong>：{content.task_type}（复杂度：{content.complexity_level || '中等'}）</p>
          )}
          {content.solution_approach && (
            <p><strong>解题方法</strong>：{content.solution_approach}</p>
          )}
          {content.required_expertise && content.required_expertise.length > 0 && (
            <p><strong>所需专业</strong>：{content.required_expertise.join('、')}</p>
          )}
          {content.key_steps && content.key_steps.length > 0 && (
            <div>
              <p className="font-medium mb-1">关键步骤：</p>
              <ol className="list-decimal list-inside space-y-0.5 text-gray-600 dark:text-gray-400">
                {content.key_steps.slice(0, 4).map((s: any, i: number) => (
                  <li key={i}>{s.action}</li>
                ))}
              </ol>
            </div>
          )}
        </div>
      );

    case 'mission4':
      return (
        <div className="space-y-1.5">
          {content.execution_strategy && (
            <p><strong>执行策略</strong>：{content.execution_strategy}</p>
          )}
          {content.quality_requirements && content.quality_requirements.length > 0 && (
            <p><strong>质量要求</strong>：{content.quality_requirements.join('、')}</p>
          )}
          {content.breakthrough_points && content.breakthrough_points.length > 0 && (
            <div>
              <p className="font-medium mb-1">突破点：</p>
              <ul className="list-disc list-inside space-y-0.5 text-gray-600 dark:text-gray-400">
                {content.breakthrough_points.slice(0, 3).map((b: any, i: number) => (
                  <li key={i}>{b.point}：{b.approach}</li>
                ))}
              </ul>
            </div>
          )}
          {content.risk_mitigation && content.risk_mitigation.length > 0 && (
            <p className="text-amber-700 dark:text-amber-400">
              <strong>风险控制</strong>：{content.risk_mitigation.slice(0, 2).join('、')}
            </p>
          )}
        </div>
      );

    default:
      return null;
  }
};

export default FourMissionsDisplay;
