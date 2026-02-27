import { X, Sparkles, AlertCircle, Scale, Lightbulb } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";

interface AIInsightCardProps {
  issueTitle: string;
  clauseReference: string | null;
  aiSuggestion: string | null;
  aiRationale: string | null;
  isLoading: boolean;
  onClose: () => void;
}

export function AIInsightCard({
  issueTitle,
  clauseReference,
  aiSuggestion,
  aiRationale,
  isLoading,
  onClose,
}: AIInsightCardProps) {
  return (
    <div className="absolute right-4 top-4 z-50 w-80 rounded-xl border border-gray-border bg-white shadow-xl">
      {/* 헤더 */}
      <div className="flex items-center justify-between border-b border-gray-border px-4 py-3">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-primary-600" />
          <h4 className="text-sm font-heading font-semibold text-text-dark">AI 분석</h4>
        </div>
        <button onClick={onClose} className="rounded p-0.5 hover:bg-gray-100">
          <X className="h-4 w-4 text-text-muted" />
        </button>
      </div>

      {/* 콘텐츠 */}
      <div className="max-h-[400px] overflow-y-auto p-4">
        {isLoading ? (
          <div className="space-y-3">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-16 w-full" />
          </div>
        ) : (
          <div className="space-y-4">
            {/* 주요 쟁점 */}
            <Section icon={AlertCircle} title="주요 쟁점" color="text-red-600">
              <p className="text-xs text-text-dark font-medium">{issueTitle}</p>
              {clauseReference && (
                <span className="mt-1 inline-block rounded bg-gray-100 px-1.5 py-0.5 text-[10px] text-text-muted">
                  {clauseReference}
                </span>
              )}
            </Section>

            {/* M&A 표준 관행 */}
            <Section icon={Scale} title="M&A 표준 관행" color="text-blue-600">
              {aiSuggestion ? (
                <p className="text-xs text-text-secondary whitespace-pre-wrap">{aiSuggestion}</p>
              ) : (
                <p className="text-xs text-text-muted italic">
                  LLM 연동 예정 — AI 분석 요청 시 해당 조항에 대한 M&A 표준 관행을 제시합니다.
                </p>
              )}
            </Section>

            {/* 리스크 평가 */}
            <Section icon={AlertCircle} title="리스크 평가" color="text-amber-600">
              {aiRationale ? (
                <p className="text-xs text-text-secondary whitespace-pre-wrap">{aiRationale}</p>
              ) : (
                <p className="text-xs text-text-muted italic">
                  LLM 연동 예정 — 해당 조항의 리스크를 평가합니다.
                </p>
              )}
            </Section>

            {/* 권장 대응 */}
            <Section icon={Lightbulb} title="권장 대응" color="text-green-600">
              {aiSuggestion ? (
                <div className="space-y-1.5">
                  <ActionPill label="수용" description="상대측 제안을 현 상태로 수용" />
                  <ActionPill label="대안 제시" description="AI 수정안 기반 역제안" />
                  <ActionPill label="거절" description="현 조항 유지, 추가 협의 요청" />
                </div>
              ) : (
                <p className="text-xs text-text-muted italic">
                  LLM 연동 예정 — 수용/거절/대안 옵션을 제시합니다.
                </p>
              )}
            </Section>
          </div>
        )}
      </div>

      {/* 푸터 */}
      <div className="border-t border-gray-border px-4 py-2">
        <p className="text-[10px] text-text-muted text-center">
          AI 분석은 참고용이며, 최종 판단은 법률 전문가의 검토가 필요합니다.
        </p>
      </div>
    </div>
  );
}

function Section({
  icon: Icon,
  title,
  color,
  children,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  color: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="mb-1.5 flex items-center gap-1.5">
        <Icon className={`h-3.5 w-3.5 ${color}`} />
        <p className="text-xs font-semibold text-text-dark">{title}</p>
      </div>
      <div className="ml-5">{children}</div>
    </div>
  );
}

function ActionPill({ label, description }: { label: string; description: string }) {
  return (
    <div className="flex items-center gap-2 rounded border border-gray-200 bg-gray-50 px-2 py-1.5">
      <span className="text-xs font-medium text-text-dark">{label}</span>
      <span className="text-[10px] text-text-muted">{description}</span>
    </div>
  );
}
