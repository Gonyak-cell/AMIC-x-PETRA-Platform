export type NoteType = "COMMENT" | "DECISION" | "QUESTION" | "ACTION_ITEM";

export interface DealNote {
  id: string;
  transaction_id: string;
  author_email: string;
  content: string;
  note_type: NoteType;
  parent_id: string | null;
  is_pinned: boolean;
  mentions: string[] | null;
  attachments: { name: string; url: string; size: number }[] | null;
  created_at: string;
  updated_at: string;
}

export interface NoteCreate {
  content: string;
  note_type?: NoteType;
  parent_id?: string;
  is_pinned?: boolean;
  mentions?: string[];
  attachments?: { name: string; url: string; size: number }[];
}

export interface NoteUpdate {
  content?: string;
  note_type?: NoteType;
  is_pinned?: boolean;
  mentions?: string[];
  attachments?: { name: string; url: string; size: number }[];
}

export interface NoteListResponse {
  items: DealNote[];
  total: number;
}
