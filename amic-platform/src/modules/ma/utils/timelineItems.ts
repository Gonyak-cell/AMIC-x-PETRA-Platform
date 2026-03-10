import type { MarketingStage } from "@/modules/ma/types/marketing_log";
import type { MeetingLog } from "@/modules/ma/types/meeting_log";

export type TimelineItem =
  | { type: "stage"; stage: MarketingStage; date: string; elapsed: number | null }
  | { type: "meeting"; log: MeetingLog };

/** 두 날짜(YYYY-MM-DD) 사이 일수 차이. 유효하지 않은 날짜면 null. */
export function daysBetween(a: string, b: string): number | null {
  const da = new Date(a);
  const db = new Date(b);
  if (isNaN(da.getTime()) || isNaN(db.getTime())) return null;
  return Math.round((db.getTime() - da.getTime()) / (1000 * 60 * 60 * 24));
}

/**
 * 완료된 마케팅 단계와 미팅 로그를 날짜 기준 오름차순으로 병합한다.
 * 같은 날짜면 stage가 meeting보다 먼저 배치된다.
 *
 * @param completedStages - 완료된 단계 배열. date는 YYYY-MM-DD 형식
 * @param meetingLogs - 미팅 로그 배열. buyer_id가 null인 항목은 제외됨
 */
export function buildTimelineItems(
  completedStages: { stage: MarketingStage; date: string }[],
  meetingLogs: MeetingLog[],
): TimelineItem[] {
  const sortedStages = [...completedStages].sort((a, b) =>
    a.date < b.date ? -1 : a.date > b.date ? 1 : 0,
  );

  const stageItems: TimelineItem[] = sortedStages.map((s, idx) => ({
    type: "stage" as const,
    stage: s.stage,
    date: s.date,
    elapsed: idx > 0 ? daysBetween(sortedStages[idx - 1].date, s.date) : null,
  }));

  const meetingItems: TimelineItem[] = meetingLogs
    .filter((log) => log.buyer_id != null)
    .map((log) => ({ type: "meeting" as const, log }));

  const merged = [...stageItems, ...meetingItems];

  merged.sort((a, b) => {
    const dateA = a.type === "stage" ? a.date : a.log.meeting_date;
    const dateB = b.type === "stage" ? b.date : b.log.meeting_date;
    if (dateA < dateB) return -1;
    if (dateA > dateB) return 1;
    if (a.type === "stage" && b.type === "meeting") return -1;
    if (a.type === "meeting" && b.type === "stage") return 1;
    return 0;
  });

  return merged;
}
