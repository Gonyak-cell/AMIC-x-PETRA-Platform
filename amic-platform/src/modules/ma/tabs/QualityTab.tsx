import { useState } from "react";
import { ArrowRight, Sparkles } from "lucide-react";
import {
  useRalphSessions,
  useCreateRalphSession,
} from "@/modules/docs/hooks/useRalphLoop";
import type { RalphSession } from "@/modules/docs/hooks/useRalphLoop";
import RalphLoopProgress from "@/modules/docs/components/RalphLoopProgress";
import QualityDashboard from "@/modules/docs/components/QualityDashboard";

import { Button, Card, EmptyState } from "@/components/ui";

import { formatISODate as formatDate } from "@/modules/ma/utils/format";

interface QualityTabProps {
  txnId: string;
  canWrite: boolean;
}

export default function QualityTab({ txnId, canWrite }: QualityTabProps) {
  const { data: ralphSessions } = useRalphSessions(txnId);
  const createRalphSession = useCreateRalphSession(txnId);
  const [selectedRalphSession, setSelectedRalphSession] =
    useState<RalphSession | null>(null);

  return (
    <div className="space-y-6">
      {/* 세션 목록 */}
      <Card
        title="Ralph Loop 세션"
        headerBar
        actions={
          canWrite ? (
            <Button
              size="sm"
              icon={Sparkles}
              loading={createRalphSession.isPending}
              onClick={() =>
                createRalphSession.mutate({ doc_type: "ldd_full" })
              }
            >
              새 세션 시작
            </Button>
          ) : undefined
        }
      >
        {!ralphSessions?.length ? (
          <EmptyState
            icon={Sparkles}
            title="Ralph Loop 세션 없음"
            description="AI Quality 세션을 시작하면 문서 품질을 자동으로 검증합니다."
          />
        ) : (
          <div className="divide-y">
            {ralphSessions.map((session) => {
              const statusColor = {
                pending: "bg-gray-100 text-gray-600",
                running: "bg-blue-50 text-blue-700",
                completed: "bg-green-100 text-green-700",
                failed: "bg-red-50 text-red-700",
              }[session.status];

              return (
                <div
                  key={session.id}
                  className="flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-gray-50"
                  onClick={() => setSelectedRalphSession(session)}
                >
                  <div className="flex items-center gap-3">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusColor}`}
                    >
                      {session.status.toUpperCase()}
                    </span>
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        {session.doc_type}
                      </p>
                      <p className="text-xs text-gray-500">
                        {formatDate(session.created_at)} · 반복{" "}
                        {session.total_iterations}회
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    {session.final_score != null && (
                      <span
                        className={`text-sm font-semibold ${
                          session.final_score >= 4.0
                            ? "text-positive"
                            : session.final_score >= 3.0
                              ? "text-amber-600"
                              : "text-negative"
                        }`}
                      >
                        {session.final_score.toFixed(1)}/5.0
                      </span>
                    )}
                    <ArrowRight size={14} className="text-gray-400" />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </Card>

      {/* 선택된 세션 상세 */}
      {selectedRalphSession && (
        <Card>
          <QualityDashboard session={selectedRalphSession} />
          {selectedRalphSession.status === "running" && (
            <div className="mt-4">
              <RalphLoopProgress sessionId={selectedRalphSession.id} />
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
