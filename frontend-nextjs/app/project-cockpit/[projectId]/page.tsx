'use client';

/**
 * 项目底盘页 — 方案高参核心决策视图
 *
 * 路由：
 *   /project-cockpit/new       → 空状态激活入口
 *   /project-cockpit/[id]      → 已激活项目决策视图
 */

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { PageLayout } from '@/components/project-cockpit/PageLayout';
import { EmptyStateInvitation, type EntryType } from '@/components/project-cockpit/EmptyStateInvitation';
import { DecisionView } from '@/components/project-cockpit/DecisionView';
import { LeftNavWithStatus } from '@/components/project-cockpit/LeftNavWithStatus';
import { AdvisorPanel } from '@/components/project-cockpit/AdvisorPanel';
import {
  MOCK_PROJECT_OVERVIEW,
  MOCK_STAGES,
  type ViewKey,
  type CapabilityStatus,
} from '@/components/project-cockpit/mock/mockData';

const ADVISOR_OUTPUT = {
  focus: '整个项目 · HAY 气质七里坪山地民宿',
  stage: '项目底盘草案',
  judgment: '品牌气质和地点约束已明确；主要缺口是面积分布、房间数量和平面图。补齐后平面推演可正式启动。',
  suggestion: '补充面积 / 房间数量 / 平面图，或先保存项目方向草案。',
};

const INPUT_PLACEHOLDERS: Record<string, string> = {
  global: '问我这个项目下一步怎么推进，或让我解释当前判断...',
  space:  '围绕空间动线、接待、功能关系继续深化...',
  card:   '围绕这张卡追问、改写、补证据或生成下一步动作...',
};

export default function ProjectCockpitPage() {
  const params    = useParams();
  const router    = useRouter();
  const projectId = params.projectId as string;

  const [isActivated, setIsActivated]   = useState(projectId !== 'new');
  const [activeView, setActiveView]     = useState<ViewKey>('overview');
  const [activeCapability, setActiveCapability] = useState<CapabilityStatus['key']>('project_base');
  const [advisorFocus]                  = useState<'global' | 'space' | 'card'>('global');
  const [prefillMessage, setPrefillMessage] = useState<string | undefined>(undefined);

  const handleEntry = (type: EntryType) => {
    console.log('[mock] activation entry:', type);
    setIsActivated(true);
    if (projectId === 'new') {
      router.push('/project-cockpit/hay-demo');
    }
  };

  const handleAction = (actionLabel: string) => {
    console.log('[mock] action:', actionLabel);
  };

  const handleCapabilityClick = (key: CapabilityStatus['key']) => {
    setActiveCapability(key);
  };

  const handleAdvisorSend = (text: string) => {
    console.log('[mock] advisor send:', text);
    setPrefillMessage(undefined);
  };

  const handleAdvisorPrefill = (text: string) => {
    setPrefillMessage(text);
  };

  const leftNav = (
    <LeftNavWithStatus
      capabilities={MOCK_PROJECT_OVERVIEW.capabilities}
      activeKey={activeCapability}
      onCapabilityClick={handleCapabilityClick}
    />
  );

  const mainContent = !isActivated ? (
    <EmptyStateInvitation onEntry={handleEntry} />
  ) : (
    <DecisionView
      overview={MOCK_PROJECT_OVERVIEW}
      stages={MOCK_STAGES}
      activeView={activeView}
      onViewChange={setActiveView}
      onAction={handleAction}
      onCapabilityClick={handleCapabilityClick}
      onAdvisorPrefill={handleAdvisorPrefill}
    />
  );

  const advisorPanel = (
    <AdvisorPanel
      advisorFocus={advisorFocus}
      output={ADVISOR_OUTPUT}
      inputPlaceholder={INPUT_PLACEHOLDERS[advisorFocus]}
      prefillMessage={prefillMessage}
      onSend={handleAdvisorSend}
    />
  );

  return (
    <PageLayout
      leftNav={leftNav}
      mainContent={mainContent}
      advisorPanel={advisorPanel}
    />
  );
}
