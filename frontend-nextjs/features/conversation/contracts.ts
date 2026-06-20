export const CONVERSATION_ANALYSIS_UI_MODULE_CONTRACT = {
  moduleId: 'conversation-analysis-ui',
  currentVersion: 'v0.1-feature-boundary-contract',
  ownedPaths: [
    'frontend-nextjs/features/conversation/contracts.ts',
    'frontend-nextjs/app/analysis/[sessionId]/page.tsx',
    'frontend-nextjs/components/ConversationMode/ConversationChat.tsx',
    'frontend-nextjs/components/ConversationMode/GuidanceCard.tsx',
    'frontend-nextjs/lib/api.ts',
    'frontend-nextjs/types/',
  ],
  entrypoints: [
    'frontend-nextjs/app/analysis/[sessionId]/page.tsx',
    'ConversationChat',
    'GuidanceCardWidget',
  ],
  dependencies: [
    'demand-reconstruction',
    'scheme-advisor-entry',
    'frontend api client',
  ],
  requiredGuidanceCardTypes: [
    'demand_reconstruction_blueprint',
    'scheme_round_1',
    'scheme_round_2',
    'scheme_stage_conclusion',
    'scheme_version_selection',
  ],
  protectedTestCases: [
    'renders demand reconstruction cards without formal intake wording',
    'renders dynamic demand reconstruction blueprint sections',
    'renders user-facing labels for context packet missing-slot pages',
    'submits multi-page scheme answers as structured selections',
    'renders backend configured version names and price labels verbatim',
    'confirms the selected version without navigating to checkout',
  ],
  publicContractRules: [
    'analysis page composes session loading, layout, and feature entrypoints',
    'conversation chat remains the composition shell for message interactions',
    'guidance, candidate, and version cards remain independently testable',
    'frontend labels must translate internal backend signals into user-facing language',
  ],
  nextRefactorTargets: [
    'extract conversation types from ConversationChat',
    'extract card renderer from ConversationChat',
    'extract conversation hooks from analysis page',
  ],
} as const;

export type ConversationGuidanceCardType =
  (typeof CONVERSATION_ANALYSIS_UI_MODULE_CONTRACT.requiredGuidanceCardTypes)[number];
