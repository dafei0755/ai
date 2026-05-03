'use client';

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

const COCKPIT_MODULES = new Set<AdvisorModule>([
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
  const [sceneRef, setSceneRef]                 = useState<SceneRef>({
    projectId,
    sessionId: 'local-session',
    module: 'project_base',
    userAction: 'view',
    dispatchLevel: 'L1',
  });
  const [viewModel, setViewModel] = useState<AdvisorViewModel>(MOCK_ADVISOR_VIEW_MODEL);

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
      if (COCKPIT_MODULES.has(target)) {
        setActiveCapability(target as CapabilityStatus['key']);
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
    }
  };

  const handleAsk = (text: string) => {
    console.log('[mock] advisor ask:', text);
    setSceneRef(prev => ({ ...prev, userAction: 'ask', dispatchLevel: 'L3' }));
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
