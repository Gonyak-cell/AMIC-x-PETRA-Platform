/** CLIENT 역할 전용 대시보드 타입. */

export interface TeamContactForClient {
  name: string;
  email: string;
  role: string;
}

export interface MaterialDistributionForClient {
  id: string;
  doc_type: "TM" | "DM" | "IM";
  title: string;
  status: string;
  distributed_to: string[] | null;
  distributed_at: string | null;
}

export interface BuyerSummaryForClient {
  buyer_id: string;
  company_name: string;
  status: string;
  status_label: string;
  latest_reaction: string | null;
  latest_reaction_comments: string | null;
  condition_match: string | null;
  condition_notes: string | null;
  next_meeting_date: string | null;
  next_meeting_title: string | null;
  meeting_count: number;
}

export interface UpcomingMeetingForClient {
  id: string;
  title: string;
  meeting_date: string;
  meeting_time: string | null;
  location: string | null;
  channel: string;
  attendee_count: number;
}

export interface RecentActivityForClient {
  event_type: "MEETING_COMPLETED" | "DOCUMENT_DISTRIBUTED" | "STATUS_CHANGED";
  description: string;
  timestamp: string;
}

export interface ClientPortalDashboard {
  transaction_name: string;
  codename: string;
  current_phase: string;
  phase_label: string;
  team_contacts: TeamContactForClient[];
  materials: MaterialDistributionForClient[];
  buyer_summaries: BuyerSummaryForClient[];
  upcoming_meetings: UpcomingMeetingForClient[];
  recent_activity: RecentActivityForClient[];
}
