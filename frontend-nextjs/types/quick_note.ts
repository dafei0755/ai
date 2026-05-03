export type QuickNoteSource = 'web' | 'qclaw_wechat' | 'mobile';
export type QuickNoteStatus = 'raw' | 'tagged' | 'suggested' | 'routed' | 'archived';

export interface QuickNote {
  quicknote_id: string;
  raw_text: string;
  created_at: string;
  source: QuickNoteSource;
  status: QuickNoteStatus;
}

export interface CreateQuickNoteRequest {
  raw_text: string;
  source?: QuickNoteSource;
}

export interface ListQuickNotesResponse {
  items: QuickNote[];
}
