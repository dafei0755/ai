import type { CandidateCardData, CandidateCardResponse } from '@/components/ConversationMode/CandidateCard';

export type MessageRole = 'user' | 'assistant' | 'system';

export interface GuidanceCardOptionData {
  id: string;
  label: string;
  description: string;
  consequence_hint?: string;
  recommended?: boolean;
}

export interface GuidanceCardPage {
  page_title?: string;
  prompt_text: string;
  options: GuidanceCardOptionData[];
  allow_freetext?: boolean;
  response_mode?: 'single_select' | 'multi_select' | 'priority_pick' | 'confirmation_status' | 'fact_status';
  max_select?: number;
  helper_text?: string;
  source?: string;
  missing_slot_action?: 'certainty_ceiling' | 'branch_answer_plus_followup' | 'option_menu' | string;
  missing_slot_names?: string[];
}

export interface GuidanceCardStructuredResponse {
  pages: Array<{
    page_index: number;
    page_title: string;
    response_mode: GuidanceCardPage['response_mode'] | 'single_select';
    selected_option_id?: string;
    selected_option_ids?: string[];
    selected_options?: Array<{
      id: string;
      label: string;
      priority?: number;
    }>;
    freetext?: string;
  }>;
}

export interface SchemeVersionCardData {
  id: 'basic' | 'standard' | 'professional' | string;
  name: string;
  subtitle: string;
  price_label?: string;
  accent?: 'blue' | 'cyan' | 'violet' | string;
  recommended?: boolean;
  includes?: string[];
  directory_preview?: string[];
}

export interface GuidanceCardSectionData {
  title: string;
  body?: string;
  items?: string[];
  emphasis?: 'high' | 'medium' | 'low' | string;
}

export interface GuidanceCardData {
  card_id: string;
  card_type:
    | 'mirror'
    | 'fork'
    | 'gap'
    | 'hypothesis'
    | 'candidate'
    | 'demand_reconstruction_blueprint'
    | 'scheme_round_1'
    | 'scheme_round_2'
    | 'scheme_stage_conclusion'
    | 'scheme_version_selection';
  title?: string;
  prompt_text: string;
  options: GuidanceCardOptionData[];
  allow_freetext?: boolean;
  pages?: GuidanceCardPage[];
  source_turns?: string[];
  candidate_fields?: CandidateCardData['candidate_fields'];
  card_status?: CandidateCardData['card_status'];
  gap_round?: boolean;
  summary?: Record<string, unknown>;
  display_label?: string;
  artifact_name?: string;
  reconstruction_type?: string;
  sections?: GuidanceCardSectionData[];
  version_cards?: SchemeVersionCardData[];
  recommended_version?: string;
  maturity_note?: string;
}

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: string;
  has_draft?: boolean;
  draft_type?: string;
  guidance_card?: GuidanceCardData;
  card_responded?: boolean;
  card_selection_label?: string;
}

export interface AdvisorSceneContext {
  key: string;
  label: string;
  suggestion: string;
  sceneRef: string;
}

export interface ConversationChatProps {
  sessionId: string;
  messages: ChatMessage[];
  activeExpertPerspective?: string;
  expertPerspectiveOptions?: readonly string[];
  onExpertPerspectiveChange?: (next: string) => void;
  summonOptions?: readonly string[];
  onSummonExpert?: (target: string) => void;
  visualBriefContext?: {
    space: string;
    status: string;
    summary: string;
    visualPrompt: string;
    appliedTags: string[];
    lockedTags: string[];
    negativeConstraints: string[];
    customNote?: string;
    sourceTitles: string[];
  } | null;
  onVisualBriefPromptChange?: (prompt: string) => void;
  onVisualBriefNoteChange?: (note: string) => void;
  advisorSceneContext?: AdvisorSceneContext | null;
  onSendMessage: (text: string) => void;
  loading?: boolean;
  placeholder?: string;
  showUpgradeBanner?: boolean;
  onUpgradeConfirm?: () => void;
  onUpgradeDismiss?: () => void;
  onCardResponse?: (
    cardId: string,
    optionId?: string,
    freetext?: string,
    structuredResponse?: GuidanceCardStructuredResponse,
  ) => void | Promise<void>;
  onCandidateCardResponse?: (response: CandidateCardResponse) => void;
  prefillHint?: { id: number; text: string } | null;
  className?: string;
}
