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
  MOCK_ADVISOR_VIEW_MODEL,
  type ViewKey,
  type CapabilityStatus,
} from '@/components/project-cockpit/mock/mockData';
import type { AdvisorViewModel, SceneRef, ActionChip, AdvisorModule } from '@/types/advisor';

// 底盘页内模块：页内切换 activeCapability，不跳页
const COCKPIT_MODULES = new Set<CapabilityStatus['key']>([
  'project_base',
  'floor_plan',
  'scheme_canvas',
]);

export default function ProjectCockpitPage() {
  const params    = useParams();
  const router    = useRouter();
  const projectId = params.projectId as string;

  const [isActivated, setIsActivated]           = useState(projectId !== 'new');
  const [activeView, setActiveView]             = useState<ViewKey>('overview');
  const [activeCapability, setActiveCapability] = useState<CapabilityStatus['key']>('project_base');
  const [prefillMessage, setPrefillMessage]     = useState<string | undefined>(undefined);
  // Phase A2 接入点：_sceneRef 将作为 POST /v1/advisor/intents 的请求体传入
  const [_sceneRef, setSceneRef]                = useState<SceneRef>({
    projectId,
    sessionId: 'local-session',
    module: 'project_base',
    userAction: 'view',
    dispatchLevel: 'L1',
  });
  // Phase A2: const [viewModel, setViewModel] = useState<AdvisorViewModel>(MOCK_ADVISOR_VIEW_MODEL);
  // 届时 handleAsk 调用 setViewModel(response) 替换 mock
  const viewModel: AdvisorViewModel = MOCK_ADVISOR_VIEW_MODEL;

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

  const handleChipAction = (chip: ActionChip) => {
    if (chip.type === 'navigate') {
      const { target } = chip.payload;
      if (COCKPIT_MODULES.has(target as CapabilityStatus['key'])) {
        // L0：页内切换，不发后端请求
        setActiveCapability(target as CapabilityStatus['key']);
        // navigate_in 到达 → 触发 L2（Phase A2 替换为 POST /v1/advisor/intents）
        setSceneRef(prev => ({
          ...prev,
          module: target,
          userAction: 'navigate_in',
          dispatchLevel: 'L2',
        }));
      } else {
        router.push(`/analysis/${projectId}?module=${target}`);
      }
    } else if (chip.type === 'fill') {
      console.log('[mock] fill chip:', chip.payload);
      // Phase A2: 打开对应表单
    }
  };

  const handleAsk = (text: string) => {
    console.log('[mock] advisor ask:', text);
    setSceneRef(prev => ({ ...prev, userAction: 'ask', dispatchLevel: 'L3' }));
    setPrefillMessage(undefined);
    // Phase A2: POST /v1/advisor/intents → setViewModel(response)
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
      viewModel={viewModel}
      prefillMessage={prefillMessage}
      onChipAction={handleChipAction}
      onAsk={handleAsk}
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
