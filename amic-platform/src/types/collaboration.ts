export type CommentEntityType = "deal" | "issue" | "document";

export interface Comment {
  id: string;
  entity_type: CommentEntityType;
  entity_id: string;
  author_id: string;
  author_name: string;
  content: string;
  mentions: string[];
  created_at: string;
  updated_at: string | null;
  is_edited: boolean;
}

export interface CommentCreate {
  content: string;
  mentions: string[];
}

export interface TeamMember {
  user_id: string;
  display_name: string;
  role: string;
  email: string;
}

export interface TeamAssignmentData {
  partner_id: string | null;
  manager_id: string | null;
  analysts: string[];
}
