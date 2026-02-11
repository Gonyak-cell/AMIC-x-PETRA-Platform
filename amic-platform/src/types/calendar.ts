export type CalendarEventModule = "fdd" | "kiis" | "im";

export type CalendarEventType =
  | "deal_start"
  | "deal_end"
  | "deal_reference"
  | "deal_created"
  | "audit_date"
  | "portfolio_check"
  | "document_created"
  | "document_completed";

export interface CalendarEvent {
  id: string;
  module: CalendarEventModule;
  type: CalendarEventType;
  title: string;
  date: string;
  endDate?: string;
  entityId: string;
  entityPath: string;
}

export interface CalendarFilter {
  modules: CalendarEventModule[];
  month: number;
  year: number;
}

export interface GanttItem {
  id: string;
  label: string;
  module: CalendarEventModule;
  startDate: string;
  endDate: string;
  entityPath: string;
  progress?: number;
}

export type CalendarViewMode = "calendar" | "gantt";
