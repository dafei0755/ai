export type QuickNoteSource = 'web' | 'qclaw_wechat' | 'mobile';
export type QuickNoteStatus = 'raw' | 'tagged' | 'suggested' | 'routed' | 'archived';
export type QuickNoteTargetPage = '草池' | '沉淀' | '作品' | '我';
export type QuickNoteReviewStatus = 'unreviewed' | 'manual_review_required' | 'reviewed';
export type QuickNotePromotionStatus = 'not_promoted' | 'candidate_routed' | 'promoted';

export interface QuickNote {
  quicknote_id: string;
  raw_text: string;
  created_at: string;
  updated_at?: string;
  source: QuickNoteSource;
  status: QuickNoteStatus;
  target_page?: QuickNoteTargetPage;
  category?: string;
  original_preserved?: boolean;
  review_status?: QuickNoteReviewStatus;
  promotion_status?: QuickNotePromotionStatus;
  promoted_object_id?: string | null;
}

export interface CreateQuickNoteRequest {
  raw_text: string;
  source?: QuickNoteSource;
}

export interface UpdateQuickNoteRequest {
  quicknote_id: string;
  raw_text?: string;
  target_page?: QuickNoteTargetPage;
  category?: string;
}

export interface ListQuickNotesResponse {
  items: QuickNote[];
}
