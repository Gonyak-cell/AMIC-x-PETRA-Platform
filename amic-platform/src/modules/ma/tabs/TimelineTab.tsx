import { Calendar } from "lucide-react";
import {
  useTimeline,
  useGanttTimeline,
} from "@/modules/ma/hooks/useTransactions";
import { GanttTimeline } from "@/modules/ma/components/GanttTimeline";

import { Badge, Card, EmptyState } from "@/components/ui";

interface TimelineTabProps {
  txnId: string;
}

export default function TimelineTab({ txnId }: TimelineTabProps) {
  const { data: timeline } = useTimeline(txnId);
  const { data: ganttData } = useGanttTimeline(txnId);

  return (
    <div className="space-y-6">
      {/* 간트 타임라인 */}
      <Card title="딜 타임라인" headerBar>
        {ganttData ? (
          <GanttTimeline data={ganttData} />
        ) : (
          <EmptyState
            icon={Calendar}
            title="타임라인 데이터 없음"
            description="거래 활동이 시작되면 자동으로 기록됩니다."
          />
        )}
      </Card>

      {/* 활동 로그 (접을 수 있는 섹션) */}
      {timeline?.items && timeline.items.length > 0 && (
        <details className="group">
          <summary className="cursor-pointer text-sm font-medium text-text-muted hover:text-text-primary transition-colors">
            활동 로그 ({timeline.total}건)
          </summary>
          <Card className="mt-2">
            <div className="space-y-3 p-1">
              {timeline.items.map((event) => (
                <div
                  key={event.id}
                  className="flex gap-3 items-start border-l-2 border-accent/20 pl-4 py-1"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">{event.title}</span>
                      {event.is_auto_generated && (
                        <Badge variant="neutral" pill>
                          자동
                        </Badge>
                      )}
                    </div>
                    {event.description && (
                      <p className="text-xs text-text-muted mt-0.5">
                        {event.description}
                      </p>
                    )}
                  </div>
                  <span className="text-xs text-text-muted whitespace-nowrap">
                    {event.event_date}
                  </span>
                </div>
              ))}
            </div>
          </Card>
        </details>
      )}
    </div>
  );
}
