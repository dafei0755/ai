// frontend-nextjs/types/advisor.ts

export type AdvisorModule =
  | 'project_base'
  | 'floor_plan'
  | 'scheme_canvas'
  | 'resource_radar'
  | 'silicon_avatar'
  | 'knowledge_hub';

export type AdvisorObjectType =
  | 'project'
  | 'space'
  | 'brief'
  | 'spg'
  | 'floor_plan_pack'
  | 'layout_variant'
  | 'concept_canvas'
  | 'placement_canvas'
  | 'resource_candidate'
  | 'decision_log'
  | 'preference_rule';

export interface SceneRef {
  projectId: string;
  sessionId: string;
  module: AdvisorModule;
  view?: string;
  objectId?: string;
  objectType?: AdvisorObjectType;
  userAction: 'view' | 'edit' | 'select' | 'navigate_in' | 'ask' | 'confirm' | 'upload';
  dispatchLevel: 'L0' | 'L1' | 'L2' | 'L3';
}

export type ActionChip =
  | { type: 'ask';      label: string; isPrimary: boolean; payload: { question: string } }
  | { type: 'navigate'; label: string; isPrimary: boolean; payload: { target: AdvisorModule; objectId?: string } }
  | { type: 'fill';     label: string; isPrimary: boolean; payload: { formId: string; fieldId?: string } }
  | { type: 'freeze';   label: string; isPrimary: boolean; payload: { draftId: string } }
  | { type: 'backfill'; label: string; isPrimary: boolean; payload: { sourceObjectId: string; targetModule: AdvisorModule } }
  | { type: 'compare';  label: string; isPrimary: boolean; payload: { objectIdA: string; objectIdB: string } };

export interface CarriedConstraint {
  sourceObjectId: string;
  sourceObjectType: string;
  targetModule: AdvisorModule;
  constraints: {
    label: string;
    value: string;
    strength: 'hard' | 'soft' | 'hint';
    source: 'brief' | 'spg' | 'ontology' | 'methodology' | 'user_confirmed';
  }[];
}

export interface EvidenceMetadata {
  evidenceClass:
    | 'none'
    | 'internal_reasoning'
    | 'knowledge_base'
    | 'case_validated'
    | 'standard_verified';
  verificationState:
    | 'unverified'
    | 'pending_registry'
    | 'registered'
    | 'expert_confirmed';
}

export interface AdvisorJudgment {
  content: string;
  confidence: 'high' | 'medium' | 'low';
  evidence: EvidenceMetadata;
  sourceParts: {
    ontology?: string;
    methodology?: string;
    knowledge?: string;
    userHistory?: string;
  };
  cannotDo?: { reason: string; blockedChipTypes?: ActionChip['type'][] }[];
}

export interface ActivatedCapability {
  type: 'ontology' | 'methodology' | 'knowledge' | 'evidence' | 'user_history';
  name: string;
  status: 'active' | 'pending' | 'unavailable' | 'placeholder';
  summary: string;
  sourceId?: string;
}

export interface AdvisorViewModel {
  traceId: string;
  generatedAt: string;
  sceneContext: SceneRef;
  boundObjectId?: string;
  objectState?: 'draft' | 'pending_confirmation' | 'frozen' | 'stale' | 'forked' | 'archived';
  objectVersion?: string;
  judgment: AdvisorJudgment;
  evidenceStatus: 'none' | 'internal_hint' | 'verified';
  activatedCapabilities: ActivatedCapability[];
  actionChips: ActionChip[];
  carriedConstraints?: CarriedConstraint[];
}
