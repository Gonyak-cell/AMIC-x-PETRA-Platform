import {
  Building2,
  Calendar,
  FileText,
  HelpCircle,
  Mail,
  MessageSquare,
  Users,
} from "lucide-react";
import { Badge, Card, EmptyState, KpiCard, Spinner } from "@/components/ui";
import {
  CLIENT_OVERVIEW_STEPS,
  OnboardingOverlay,
  useOnboarding,
} from "@/components/onboarding";
import { useAuth } from "@/hooks/useAuth";
import { useClientDashboard } from "@/modules/ma/hooks/useClientPortal";
import type {
  BuyerSummaryForClient,
  MaterialDistributionForClient,
  UpcomingMeetingForClient,
} from "@/modules/ma/types/client_portal";

const DOC_BADGE_VARIANT: Record<string, "info" | "warning" | "success"> = {
  TM: "info",
  DM: "warning",
  IM: "success",
};

const REACTION_LABEL: Record<string, string> = {
  VERY_POSITIVE: "매우 긍정",
  POSITIVE: "긍정",
  NEUTRAL: "중립",
  NEGATIVE: "부정",
  VERY_NEGATIVE: "매우 부정",
};

const REACTION_VARIANT: Record<
  string,
  "success" | "warning" | "error" | "neutral"
> = {
  VERY_POSITIVE: "success",
  POSITIVE: "success",
  NEUTRAL: "neutral",
  NEGATIVE: "warning",
  VERY_NEGATIVE: "error",
};

const CONDITION_LABEL: Record<string, string> = {
  FULL_MATCH: "조건 일치",
  PARTIAL_MATCH: "부분 일치",
  MISMATCH: "불일치",
  NOT_ASSESSED: "미평가",
};

const CONDITION_VARIANT: Record<
  string,
  "success" | "warning" | "error" | "neutral"
> = {
  FULL_MATCH: "success",
  PARTIAL_MATCH: "warning",
  MISMATCH: "error",
  NOT_ASSESSED: "neutral",
};

interface Props {
  txnId: string;
}

export default function ClientPortalDashboard({ txnId }: Props) {
  const { data, isLoading, isError } = useClientDashboard(txnId);
  const { user } = useAuth();
  const onboarding = useOnboarding(user?.id, txnId, CLIENT_OVERVIEW_STEPS);

  if (isLoading) return <Spinner size="lg" />;
  if (isError || !data) {
    return (
      <EmptyState
        title="데이터를 불러올 수 없습니다"
        description="네트워크 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <button
          onClick={onboarding.restart}
          className="flex items-center gap-1.5 text-sm text-text-muted hover:text-primary-500 transition-colors"
          title="가이드 다시보기"
        >
          <HelpCircle className="w-4 h-4" />
          가이드
        </button>
      </div>

      {/* 1. 프로젝트 요약 */}
      <Card className="p-5" data-onboarding="project-summary">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-lg font-heading font-semibold text-text-dark">
              {data.transaction_name}
            </h2>
            <p className="text-sm text-text-muted mt-0.5">{data.codename}</p>
          </div>
          <Badge variant="info" className="text-sm">
            {data.phase_label}
          </Badge>
        </div>

        {data.team_contacts.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-3">
            {data.team_contacts.map((c) => (
              <div
                key={c.email}
                className="flex items-center gap-2 rounded-lg border border-gray-border px-3 py-2"
              >
                <Mail className="w-4 h-4 text-text-muted" />
                <div className="text-sm">
                  <span className="font-medium">{c.name}</span>
                  <span className="text-text-muted ml-1">({c.role})</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* KPI 요약 */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <KpiCard
          label="활성 매수자"
          value={String(data.buyer_summaries.length)}
        />
        <KpiCard label="배포 문서" value={String(data.materials.length)} />
        <KpiCard
          label="예정 미팅"
          value={String(data.upcoming_meetings.length)}
          variant="warning"
        />
        <KpiCard
          label="최근 활동"
          value={String(data.recent_activity.length)}
        />
      </div>

      {/* 2. 문서 배포 현황 */}
      <Card title="문서 배포 현황" headerBar data-onboarding="doc-distribution">
        {data.materials.length === 0 ? (
          <EmptyState
            icon={FileText}
            title="배포된 문서가 없습니다"
            description="아직 마케팅 자료가 배포되지 않았습니다."
          />
        ) : (
          <div className="divide-y divide-gray-border">
            {data.materials.map((m) => (
              <MaterialRow key={m.id} material={m} />
            ))}
          </div>
        )}
      </Card>

      {/* 3. 매수자별 현황 */}
      <Card title="매수자별 현황" headerBar data-onboarding="buyer-status">
        {data.buyer_summaries.length === 0 ? (
          <EmptyState
            icon={Users}
            title="등록된 매수자가 없습니다"
            description="아직 매수자 후보가 등록되지 않았습니다."
          />
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 p-4">
            {data.buyer_summaries.map((b) => (
              <BuyerCard key={b.buyer_id} buyer={b} />
            ))}
          </div>
        )}
      </Card>

      {/* 4. 다음 미팅 일정 */}
      <Card
        title="다음 미팅 일정"
        headerBar
        data-onboarding="upcoming-meetings"
      >
        {data.upcoming_meetings.length === 0 ? (
          <EmptyState
            icon={Calendar}
            title="예정된 미팅이 없습니다"
            description="현재 예정된 미팅이 없습니다."
          />
        ) : (
          <div className="divide-y divide-gray-border">
            {data.upcoming_meetings.map((m) => (
              <MeetingRow key={m.id} meeting={m} />
            ))}
          </div>
        )}
      </Card>

      {/* 5. 최근 활동 */}
      {data.recent_activity.length > 0 && (
        <Card title="최근 활동" headerBar data-onboarding="recent-activity">
          <div className="divide-y divide-gray-border">
            {data.recent_activity.map((a, i) => (
              <div key={i} className="flex items-center gap-3 px-4 py-3">
                <div className="flex-shrink-0">
                  {a.event_type === "MEETING_COMPLETED" ? (
                    <MessageSquare className="w-4 h-4 text-primary-500" />
                  ) : (
                    <FileText className="w-4 h-4 text-accent-green" />
                  )}
                </div>
                <span className="text-sm flex-1">{a.description}</span>
                <span className="text-xs text-text-muted whitespace-nowrap">
                  {a.timestamp}
                </span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {onboarding.isActive && onboarding.step && (
        <OnboardingOverlay
          step={onboarding.step}
          currentIndex={onboarding.currentStep}
          totalSteps={onboarding.totalSteps}
          onNext={onboarding.next}
          onPrev={onboarding.prev}
          onSkip={onboarding.skip}
        />
      )}
    </div>
  );
}

/* ── 서브 컴포넌트 ────────────────────────────────────── */

function MaterialRow({
  material: m,
}: {
  material: MaterialDistributionForClient;
}) {
  const count = m.distributed_to?.length ?? 0;
  return (
    <div className="flex items-center gap-3 px-4 py-3">
      <Badge variant={DOC_BADGE_VARIANT[m.doc_type] ?? "neutral"}>
        {m.doc_type}
      </Badge>
      <span className="text-sm font-medium flex-1 truncate">{m.title}</span>
      <span className="text-xs text-text-muted">
        {count > 0 ? `${count}곳 배포` : "미배포"}
      </span>
      {m.distributed_at && (
        <span className="text-xs text-text-muted">
          {m.distributed_at.slice(0, 10)}
        </span>
      )}
    </div>
  );
}

function BuyerCard({ buyer: b }: { buyer: BuyerSummaryForClient }) {
  return (
    <div className="rounded-lg border border-gray-border p-4 space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Building2 className="w-4 h-4 text-text-muted" />
          <span className="text-sm font-semibold">{b.company_name}</span>
        </div>
        <Badge variant="neutral" className="text-xs">
          {b.status_label}
        </Badge>
      </div>

      <div className="flex flex-wrap gap-2">
        {b.latest_reaction && (
          <Badge
            variant={REACTION_VARIANT[b.latest_reaction] ?? "neutral"}
            className="text-xs"
          >
            {REACTION_LABEL[b.latest_reaction] ?? b.latest_reaction}
          </Badge>
        )}
        {b.condition_match && (
          <Badge
            variant={CONDITION_VARIANT[b.condition_match] ?? "neutral"}
            className="text-xs"
          >
            {CONDITION_LABEL[b.condition_match] ?? b.condition_match}
          </Badge>
        )}
      </div>

      {b.condition_notes && (
        <p className="text-xs text-text-muted line-clamp-2">
          {b.condition_notes}
        </p>
      )}

      <div className="flex items-center justify-between text-xs text-text-muted">
        <span>미팅 {b.meeting_count}회</span>
        {b.next_meeting_date ? (
          <span className="text-primary-600 font-medium">
            다음: {b.next_meeting_date}
          </span>
        ) : (
          <span>예정 없음</span>
        )}
      </div>
    </div>
  );
}

function MeetingRow({ meeting: m }: { meeting: UpcomingMeetingForClient }) {
  return (
    <div className="flex items-center gap-3 px-4 py-3">
      <Calendar className="w-4 h-4 text-warning-500 flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <span className="text-sm font-medium block truncate">{m.title}</span>
        <span className="text-xs text-text-muted">
          {m.meeting_date}
          {m.meeting_time && ` ${m.meeting_time}`}
          {m.location && ` · ${m.location}`}
        </span>
      </div>
      <Badge variant="neutral" className="text-xs">
        {m.channel}
      </Badge>
      {m.attendee_count > 0 && (
        <span className="text-xs text-text-muted">{m.attendee_count}명</span>
      )}
    </div>
  );
}
