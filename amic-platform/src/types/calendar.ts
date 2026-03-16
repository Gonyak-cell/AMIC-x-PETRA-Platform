export type CalendarEventModule = "ma";

export type CalendarEventType =
  | "transaction_created"
  | "target_close"
  | "phase_current";

export interface CalendarEvent {
  id: string;
  module: CalendarEventModule;
  type: CalendarEventType;
  title: string;
  date: string;
  endDate?: string;
  entityId: string;
  entityPath: string;
  phase?: string;
  phaseLabel?: string;
  phaseOrder?: number;
}

export interface CalendarFilter {
  /** 0-based month (0 = January, 11 = December). Matches `Date.getMonth()`. */
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
