import { useParams } from "react-router-dom";
import { User, Building2, Activity, GitBranch } from "lucide-react";
import { useDeal } from "@/hooks/useDeals";
import { Card, KpiCard, Spinner } from "@/components/ui";
import { WorkflowStepper } from "@/components/workflow";
import type { DealPhase } from "@/types/deal";

const NEXT_STEPS: Record<DealPhase, { title: string; items: string[] }> = {
  MOU: {
    title: "MoU 체결 단계",
    items: [
      "딜 기본 정보를 확인하세요",
      "Client 및 Target 정보를 입력하세요",
      "팀 구성을 완료하세요",
      "FDD Scope를 설정하세요",
    ],
  },
  VDR_SETUP: {
    title: "VDR 개설 단계",
    items: [
      "VDR 폴더 구조를 초기화하세요",
      "필요한 폴더를 추가하거나 수정하세요",
      "Client에게 VDR 접근 정보를 공유하세요",
    ],
  },
  DATA_UPLOAD: {
    title: "자료 업로드 단계",
    items: [
      "재무제표 (TB, GL) 파일을 업로드하세요",
      "매출채권 / 매입채무 데이터를 업로드하세요",
      "부채 및 리스 관련 자료를 업로드하세요",
      "업로드된 파일의 검증 결과를 확인하세요",
    ],
  },
  ANALYSIS: {
    title: "자료 검토 단계",
    items: [
      "계정과목 매핑을 검토하세요",
      "QoE 분석 결과를 확인하세요",
      "NWC 분석을 실행하세요",
      "Net Debt 분류를 완료하세요",
      "이슈 사항을 정리하세요",
    ],
  },
  REPORTING: {
    title: "보고서 작성 단계",
    items: [
      "보고서 포함 항목을 선택하세요",
      "보고서 미리보기를 확인하세요",
      "최종 보고서를 생성하세요",
      "버전을 확정(Finalize)하세요",
    ],
  },
};

export default function WorkflowOverviewPage() {
  const { dealId } = useParams<{ dealId: string }>();
  const { data: deal, isLoading } = useDeal(dealId!);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!deal) return null;

  const phase = deal.current_phase ?? "MOU";
  const nextSteps = NEXT_STEPS[phase];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-heading font-bold text-text-dark">
          {deal.name}
        </h1>
        <p className="text-text-secondary mt-1">Workflow Overview</p>
      </div>

      {/* Workflow Stepper */}
      <Card>
        <WorkflowStepper currentPhase={phase} className="py-2" />
      </Card>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="Client"
          value={deal.client_name || "-"}
          icon={User}
        />
        <KpiCard
          label="Target"
          value={deal.target_company_name || "-"}
          icon={Building2}
        />
        <KpiCard
          label="Status"
          value={deal.status}
          icon={Activity}
        />
        <KpiCard
          label="Phase"
          value={phase.replace(/_/g, " ")}
          icon={GitBranch}
        />
      </div>

      {/* Next Steps */}
      <Card title={nextSteps.title} headerBar>
        <ul className="space-y-3">
          {nextSteps.items.map((item, index) => (
            <li key={index} className="flex items-start gap-3 text-sm text-text-body">
              <span className="flex-shrink-0 w-6 h-6 bg-bg-cool rounded-full flex items-center justify-center text-xs text-text-secondary font-medium">
                {index + 1}
              </span>
              {item}
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
