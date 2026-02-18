import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  Play,
  Pause,
  XCircle,
  Users,
  UserPlus,
  FileText,
  Calendar,
  AlertTriangle,
  CheckCircle,
  Shield,
  DollarSign,
  ClipboardCheck,
  Plus,
  Trash2,
} from "lucide-react";

import {
  useTransaction,
  usePhaseCompletion,
  useAdvancePhase,
  useChangeStatus,
  useEngagements,
  useCreateEngagement,
  useWorkingGroup,
  useAddMember,
  useConflictCheck,
  useBuyers,
  useAddBuyer,
  useTimeline,
} from "@/modules/ma/hooks/useTransactions";
import type { Transaction } from "@/modules/ma/types/transaction";
import type { EngagementCreate } from "@/modules/ma/types/engagement";
import type { WorkingGroupMemberCreate } from "@/modules/ma/types/engagement";
import type { BuyerCandidateCreate } from "@/modules/ma/types/buyer";
import { useNdas, useNdaSummary, useCreateNda, useUpdateNda, useDeleteNda } from "@/modules/ma/hooks/useNdas";
import { useBids, useBidComparison, useCreateBid, useUpdateBid, useDeleteBid } from "@/modules/ma/hooks/useBids";
import { useDDChecklist, useDDChecklistSummary, useCreateDDChecklistItem, useUpdateDDChecklistItem, useDeleteDDChecklistItem } from "@/modules/ma/hooks/useDDChecklist";
import type { NDACreate, NdaStatus } from "@/modules/ma/types/nda";
import type { BidCreate, BidType, BidStatus as BidStatusType, ValuationMethod } from "@/modules/ma/types/bid";
import type { DDChecklistCreate, DDWorkstream, DDChecklistStatus as DDStatusType } from "@/modules/ma/types/dd_checklist";
import {
  PHASE_CONFIG,
  ENGAGEMENT_TYPE_OPTIONS,
  WORKING_GROUP_ROLE_OPTIONS,
  BUYER_TYPE_OPTIONS,
  BUYER_STATUS_OPTIONS,
  NDA_TYPE_OPTIONS,
  NDA_STATUS_OPTIONS,
  BID_TYPE_OPTIONS,
  BID_STATUS_OPTIONS,
  VALUATION_METHOD_OPTIONS,
  DD_WORKSTREAM_OPTIONS,
  DD_STATUS_OPTIONS,
} from "@/modules/ma/constants";

import {
  Badge,
  Breadcrumbs,
  Button,
  Card,
  DataTable,
  EmptyState,
  Input,
  KpiCard,
  Modal,
  PageHero,
  Select,
  Spinner,
  Tabs,
} from "@/components/ui";
import type { Column, TabItem } from "@/components/ui";

// ── 상수/유틸 ──────────────────────────────────────────
const STATUS_VARIANT: Record<string, "success" | "warning" | "error" | "info" | "neutral"> = {
  DRAFT: "neutral",
  ACTIVE: "success",
  ON_HOLD: "warning",
  COMPLETED: "info",
  TERMINATED: "error",
};

const BUYER_STATUS_VARIANT: Record<string, "success" | "warning" | "error" | "info" | "neutral"> = {
  IDENTIFIED: "neutral",
  CONTACTED: "neutral",
  NDA_SENT: "info",
  NDA_SIGNED: "info",
  CIM_SENT: "info",
  INTEREST_CONFIRMED: "warning",
  IOI_RECEIVED: "warning",
  IOI_ACCEPTED: "success",
  DD_GRANTED: "success",
  DD_IN_PROGRESS: "success",
  LOI_RECEIVED: "warning",
  LOI_ACCEPTED: "success",
  SELECTED: "success",
  REJECTED: "error",
};

const NDA_STATUS_VARIANT: Record<string, "success" | "warning" | "error" | "info" | "neutral"> = {
  DRAFT: "neutral",
  SENT: "info",
  SIGNED: "success",
  EXPIRED: "warning",
  REJECTED: "error",
};

const BID_STATUS_VARIANT: Record<string, "success" | "warning" | "error" | "info" | "neutral"> = {
  SUBMITTED: "info",
  UNDER_REVIEW: "warning",
  ACCEPTED: "success",
  REJECTED: "error",
  WITHDRAWN: "neutral",
  EXPIRED: "warning",
};

const DD_STATUS_VARIANT: Record<string, "success" | "warning" | "error" | "info" | "neutral"> = {
  NOT_STARTED: "neutral",
  IN_PROGRESS: "info",
  COMPLETED: "success",
  NOT_APPLICABLE: "neutral",
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("ko-KR");
}

function formatAmount(amount: number | null): string {
  if (amount == null) return "-";
  if (amount >= 1_0000_0000) return `${(amount / 1_0000_0000).toLocaleString()}억`;
  return amount.toLocaleString();
}

// ── WorkflowStepper ────────────────────────────────────
function WorkflowStepper({ current }: { current: string }) {
  const currentIdx = PHASE_CONFIG.findIndex((p) => p.phase === current);
  return (
    <div className="flex items-center gap-1 overflow-x-auto py-2">
      {PHASE_CONFIG.map((p, i) => {
        const done = i < currentIdx;
        const active = i === currentIdx;
        return (
          <div key={p.phase} className="flex items-center">
            <div
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap ${
                active
                  ? "bg-accent text-white"
                  : done
                    ? "bg-accent/10 text-accent"
                    : "bg-gray-100 text-text-muted"
              }`}
            >
              {done && <CheckCircle size={12} />}
              <span>
                {p.order}. {p.label}
              </span>
            </div>
            {i < PHASE_CONFIG.length - 1 && (
              <div
                className={`w-4 h-px mx-0.5 ${done ? "bg-accent" : "bg-gray-200"}`}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── 메인 컴포넌트 ──────────────────────────────────────
export default function TransactionWorkspacePage() {
  const { txnId, "*": splat } = useParams<{ txnId: string; "*": string }>();
  const navigate = useNavigate();
  const id = txnId!;

  // URL 기반 탭 결정
  const VALID_TABS = ["engagement", "team", "buyers", "timeline", "ndas", "bids", "dd-checklist"];
  const activeTab = VALID_TABS.includes(splat ?? "") ? splat! : "overview";

  // 데이터 로드 — Phase 1
  const { data: txn, isLoading } = useTransaction(id);
  const { data: phaseStatus } = usePhaseCompletion(id);
  const { data: engagements } = useEngagements(id);
  const { data: members } = useWorkingGroup(id);
  const { data: conflicts } = useConflictCheck(id);
  const { data: buyers } = useBuyers(id);
  const { data: timeline } = useTimeline(id);

  // 데이터 로드 — Phase 2
  const { data: ndas } = useNdas(id);
  const { data: ndaSummary } = useNdaSummary(id);
  const { data: bids } = useBids(id);
  const { data: bidComparison } = useBidComparison(id);
  const { data: ddItems } = useDDChecklist(id);
  const { data: ddSummary } = useDDChecklistSummary(id);

  // Mutations — Phase 1
  const advancePhase = useAdvancePhase(id);
  const changeStatus = useChangeStatus(id);
  const createEngagement = useCreateEngagement(id);
  const addMember = useAddMember(id);
  const addBuyer = useAddBuyer(id);

  // Mutations — Phase 2
  const createNda = useCreateNda(id);
  const updateNda = useUpdateNda(id);
  const deleteNda = useDeleteNda(id);
  const createBid = useCreateBid(id);
  const updateBid = useUpdateBid(id);
  const deleteBid = useDeleteBid(id);
  const createDDItem = useCreateDDChecklistItem(id);
  const updateDDItem = useUpdateDDChecklistItem(id);
  const deleteDDItem = useDeleteDDChecklistItem(id);

  // URL 기반 탭 전환
  const handleTabChange = (tab: string) => {
    if (tab === "overview") {
      navigate(`/ma/transactions/${id}`);
    } else {
      navigate(`/ma/transactions/${id}/${tab}`);
    }
  };

  // UI State — Phase 1
  const [showEngModal, setShowEngModal] = useState(false);
  const [showMemberModal, setShowMemberModal] = useState(false);
  const [showBuyerModal, setShowBuyerModal] = useState(false);

  // UI State — Phase 2
  const [showNdaModal, setShowNdaModal] = useState(false);
  const [showBidModal, setShowBidModal] = useState(false);
  const [showDDModal, setShowDDModal] = useState(false);

  // Form state — Phase 1
  const [engForm, setEngForm] = useState<EngagementCreate>({ type: "EXCLUSIVE" });
  const [memberForm, setMemberForm] = useState<WorkingGroupMemberCreate>({
    name: "",
    email: "",
    role: "LEAD_ADVISOR",
  });
  const [buyerForm, setBuyerForm] = useState<BuyerCandidateCreate>({
    company_name: "",
    buyer_type: "STRATEGIC",
  });

  // Form state — Phase 2
  const [ndaForm, setNdaForm] = useState<NDACreate>({
    buyer_candidate_id: "",
    nda_type: "MUTUAL",
  });
  const [bidForm, setBidForm] = useState<BidCreate>({
    buyer_candidate_id: "",
    bid_type: "IOI" as BidType,
  });
  const [ddForm, setDDForm] = useState<DDChecklistCreate>({
    workstream: "FINANCIAL" as DDWorkstream,
    title: "",
  });

  const tabs: TabItem[] = [
    { id: "overview", label: "Overview" },
    { id: "engagement", label: "수임", badge: engagements?.length },
    { id: "team", label: "팀", badge: members?.length },
    { id: "buyers", label: "매수자", badge: buyers?.length },
    { id: "ndas", label: "NDA", badge: ndas?.length },
    { id: "bids", label: "입찰", badge: bids?.length },
    { id: "dd-checklist", label: "DD 체크리스트", badge: ddItems?.length },
    { id: "timeline", label: "타임라인", badge: timeline?.total },
  ];

  if (isLoading) return <Spinner size="lg" />;
  if (!txn)
    return (
      <div className="text-center py-20 text-text-muted">
        거래를 찾을 수 없습니다
      </div>
    );

  const phaseLabel =
    PHASE_CONFIG.find((p) => p.phase === txn.phase)?.label ?? txn.phase;

  return (
    <div className="space-y-6">
      {/* Hero */}
      <PageHero
        title={txn.name}
        subtitle={`${txn.code_name} | ${txn.target_company_name} | ${txn.client_name}`}
        compact
        actions={
          <div className="flex flex-wrap gap-2">
            <Button
              variant="ghost"
              icon={ArrowLeft}
              onClick={() => navigate("/ma/transactions")}
            >
              목록
            </Button>
            {txn.status === "DRAFT" && (
              <Button
                icon={Play}
                onClick={() =>
                  changeStatus.mutate({ to_status: "ACTIVE" })
                }
                loading={changeStatus.isPending}
              >
                시작
              </Button>
            )}
            {txn.status === "ACTIVE" && (
              <>
                {phaseStatus?.can_advance && phaseStatus.next_phase && (
                  <Button
                    icon={ArrowRight}
                    onClick={() =>
                      advancePhase.mutate({
                        to_phase: phaseStatus.next_phase!,
                      })
                    }
                    loading={advancePhase.isPending}
                  >
                    {PHASE_CONFIG.find(
                      (p) => p.phase === phaseStatus.next_phase,
                    )?.label ?? "다음"}{" "}
                    단계로
                  </Button>
                )}
                <Button
                  variant="ghost"
                  icon={Pause}
                  onClick={() =>
                    changeStatus.mutate({ to_status: "ON_HOLD" })
                  }
                >
                  보류
                </Button>
              </>
            )}
            {txn.status === "ON_HOLD" && (
              <Button
                icon={Play}
                onClick={() =>
                  changeStatus.mutate({ to_status: "ACTIVE" })
                }
              >
                재개
              </Button>
            )}
          </div>
        }
      />

      {/* Workflow Stepper */}
      <Card padding="md">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-3">
            <Badge variant={STATUS_VARIANT[txn.status]}>{txn.status}</Badge>
            <span className="text-sm text-text-muted">
              현재: <strong>{phaseLabel}</strong>
            </span>
          </div>
        </div>
        <WorkflowStepper current={txn.phase} />

        {/* 전제 조건 */}
        {phaseStatus && !phaseStatus.all_met && (
          <div className="mt-3 p-3 bg-caution/10 rounded-dr-sm text-sm">
            <div className="flex items-center gap-1.5 font-medium text-caution mb-1">
              <AlertTriangle size={14} />
              다음 단계 전환 요건 미충족
            </div>
            <ul className="space-y-1 ml-5">
              {phaseStatus.prerequisites
                .filter((p) => !p.satisfied)
                .map((p) => (
                  <li key={p.field} className="text-text-secondary">
                    {p.label}
                  </li>
                ))}
            </ul>
          </div>
        )}
      </Card>

      {/* 이해충돌 경고 */}
      {conflicts?.has_conflicts && (
        <Card padding="md" variant="accent-left">
          <div className="flex items-center gap-2 text-negative font-medium mb-2">
            <AlertTriangle size={16} />
            이해충돌 감지
          </div>
          {conflicts.conflicts.map((c, i) => (
            <div key={i} className="text-sm text-text-secondary">
              <Badge
                variant={c.severity === "CRITICAL" ? "error" : "warning"}
                pill
              >
                {c.severity}
              </Badge>{" "}
              {c.message}
            </div>
          ))}
        </Card>
      )}

      {/* 탭 */}
      <Tabs
        tabs={tabs}
        activeTab={activeTab}
        onTabChange={handleTabChange}
        variant="underline"
      />

      {/* ── Overview 탭 ───────────────────────────────── */}
      {activeTab === "overview" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card title="거래 정보" headerBar>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm p-1">
              <dt className="text-text-muted">유형</dt>
              <dd>{txn.side}</dd>
              <dt className="text-text-muted">딜 구조</dt>
              <dd>{txn.deal_structure ?? "-"}</dd>
              <dt className="text-text-muted">투자 유형</dt>
              <dd>{txn.investment_type ?? "-"}</dd>
              <dt className="text-text-muted">산업</dt>
              <dd>{txn.industry ?? "-"}</dd>
              <dt className="text-text-muted">예상 금액</dt>
              <dd className="font-mono">
                {txn.estimated_deal_value != null
                  ? `${txn.estimated_deal_value.toLocaleString()} ${txn.currency}`
                  : "-"}
              </dd>
              <dt className="text-text-muted">목표 종결일</dt>
              <dd>{txn.target_close_date ?? "-"}</dd>
              <dt className="text-text-muted">리드 어드바이저</dt>
              <dd>{txn.lead_advisor_email}</dd>
              <dt className="text-text-muted">딜 캡틴</dt>
              <dd>{txn.deal_captain_email ?? "-"}</dd>
            </dl>
          </Card>
          <Card title="서비스 연동" headerBar>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm p-1">
              <dt className="text-text-muted">FDD Deal</dt>
              <dd className="font-mono text-xs">
                {txn.fdd_deal_id ?? "미연동"}
              </dd>
              <dt className="text-text-muted">IM Document</dt>
              <dd className="font-mono text-xs">
                {txn.im_document_id ?? "미연동"}
              </dd>
              <dt className="text-text-muted">DART Corp Code</dt>
              <dd className="font-mono text-xs">
                {txn.target_corp_code ?? "-"}
              </dd>
              <dt className="text-text-muted">생성일</dt>
              <dd>{formatDate(txn.created_at)}</dd>
              <dt className="text-text-muted">수정일</dt>
              <dd>{formatDate(txn.updated_at)}</dd>
            </dl>
          </Card>
        </div>
      )}

      {/* ── Engagement 탭 ─────────────────────────────── */}
      {activeTab === "engagement" && (
        <Card
          title="수임계약"
          headerBar
          padding="none"
          actions={
            <Button
              icon={FileText}
              onClick={() => setShowEngModal(true)}
              variant="ghost"
            >
              추가
            </Button>
          }
        >
          {!engagements?.length ? (
            <EmptyState
              icon={FileText}
              title="수임계약 없음"
              description="수임계약을 등록하세요."
              actionLabel="수임계약 추가"
              onAction={() => setShowEngModal(true)}
            />
          ) : (
            <DataTable
              columns={[
                {
                  key: "type",
                  header: "유형",
                  render: (r) => (
                    <Badge variant="info">
                      {ENGAGEMENT_TYPE_OPTIONS.find(
                        (o) => o.value === r.type,
                      )?.label ?? r.type}
                    </Badge>
                  ),
                },
                { key: "signed_at", header: "체결일" },
                { key: "expires_at", header: "만료일" },
                { key: "notes", header: "비고" },
              ]}
              data={engagements}
              keyField="id"
            />
          )}
        </Card>
      )}

      {/* ── Team 탭 ───────────────────────────────────── */}
      {activeTab === "team" && (
        <Card
          title="워킹그룹"
          headerBar
          padding="none"
          actions={
            <Button
              icon={UserPlus}
              onClick={() => setShowMemberModal(true)}
              variant="ghost"
            >
              멤버 추가
            </Button>
          }
        >
          {!members?.length ? (
            <EmptyState
              icon={Users}
              title="멤버 없음"
              description="워킹그룹 멤버를 추가하세요."
              actionLabel="멤버 추가"
              onAction={() => setShowMemberModal(true)}
            />
          ) : (
            <DataTable
              columns={[
                { key: "name", header: "이름" },
                { key: "email", header: "이메일" },
                { key: "organization", header: "소속" },
                {
                  key: "role",
                  header: "역할",
                  render: (r) => (
                    <Badge variant="neutral">
                      {WORKING_GROUP_ROLE_OPTIONS.find(
                        (o) => o.value === r.role,
                      )?.label ?? r.role}
                    </Badge>
                  ),
                },
                {
                  key: "is_active",
                  header: "상태",
                  render: (r) => (
                    <Badge variant={r.is_active ? "success" : "neutral"}>
                      {r.is_active ? "Active" : "Inactive"}
                    </Badge>
                  ),
                },
              ]}
              data={members}
              keyField="id"
            />
          )}
        </Card>
      )}

      {/* ── Buyers 탭 ─────────────────────────────────── */}
      {activeTab === "buyers" && (
        <Card
          title="매수자 후보"
          headerBar
          padding="none"
          actions={
            <Button
              icon={UserPlus}
              onClick={() => setShowBuyerModal(true)}
              variant="ghost"
            >
              후보 추가
            </Button>
          }
        >
          {!buyers?.length ? (
            <EmptyState
              icon={Users}
              title="매수자 후보 없음"
              description="잠재 매수자를 추가하세요."
              actionLabel="후보 추가"
              onAction={() => setShowBuyerModal(true)}
            />
          ) : (
            <DataTable
              columns={[
                {
                  key: "company_name",
                  header: "회사명",
                  render: (r) => (
                    <div>
                      <span className="font-medium">{r.company_name}</span>
                      {r.contact_name && (
                        <span className="block text-xs text-text-muted">
                          {r.contact_name}
                        </span>
                      )}
                    </div>
                  ),
                },
                {
                  key: "buyer_type",
                  header: "유형",
                  render: (r) => (
                    <Badge variant="neutral">
                      {BUYER_TYPE_OPTIONS.find((o) => o.value === r.buyer_type)
                        ?.label ?? r.buyer_type}
                    </Badge>
                  ),
                },
                {
                  key: "status",
                  header: "상태",
                  render: (r) => (
                    <Badge variant={BUYER_STATUS_VARIANT[r.status] ?? "neutral"}>
                      {BUYER_STATUS_OPTIONS.find((o) => o.value === r.status)
                        ?.label ?? r.status}
                    </Badge>
                  ),
                },
                {
                  key: "ioi_value",
                  header: "IOI",
                  align: "right",
                  mono: true,
                  render: (r) =>
                    r.ioi_value != null
                      ? r.ioi_value.toLocaleString()
                      : "-",
                },
                {
                  key: "loi_value",
                  header: "LOI",
                  align: "right",
                  mono: true,
                  render: (r) =>
                    r.loi_value != null
                      ? r.loi_value.toLocaleString()
                      : "-",
                },
              ]}
              data={buyers}
              keyField="id"
            />
          )}
        </Card>
      )}

      {/* ── NDA 탭 ──────────────────────────────────────── */}
      {activeTab === "ndas" && (
        <div className="space-y-4">
          {/* NDA 요약 */}
          {ndaSummary && ndaSummary.total > 0 && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <KpiCard label="전체" value={ndaSummary.total} />
              <KpiCard label="체결 완료" value={ndaSummary.signed_count} variant="positive" />
              <KpiCard label="대기 중" value={ndaSummary.pending_count} variant="neutral" />
              <KpiCard
                label="체결률"
                value={ndaSummary.total > 0 ? `${Math.round((ndaSummary.signed_count / ndaSummary.total) * 100)}%` : "-"}
              />
            </div>
          )}
          <Card
            title="NDA 목록"
            headerBar
            padding="none"
            actions={
              <Button icon={Plus} onClick={() => setShowNdaModal(true)} variant="ghost">
                NDA 추가
              </Button>
            }
          >
            {!ndas?.length ? (
              <EmptyState
                icon={Shield}
                title="NDA 없음"
                description="매수 후보와의 NDA를 등록하세요."
                actionLabel="NDA 추가"
                onAction={() => setShowNdaModal(true)}
              />
            ) : (
              <DataTable
                columns={[
                  {
                    key: "buyer_candidate_id",
                    header: "매수자",
                    render: (r) => {
                      const buyer = buyers?.find((b) => b.id === r.buyer_candidate_id);
                      return buyer?.company_name ?? r.buyer_candidate_id.slice(0, 8);
                    },
                  },
                  {
                    key: "nda_type",
                    header: "유형",
                    render: (r) => (
                      <Badge variant="neutral">
                        {NDA_TYPE_OPTIONS.find((o) => o.value === r.nda_type)?.label ?? r.nda_type}
                      </Badge>
                    ),
                  },
                  {
                    key: "status",
                    header: "상태",
                    render: (r) => (
                      <select
                        className="text-xs border rounded px-1.5 py-0.5 bg-white"
                        value={r.status}
                        onChange={(e) =>
                          updateNda.mutate({
                            ndaId: r.id,
                            body: { status: e.target.value as NdaStatus },
                          })
                        }
                      >
                        {NDA_STATUS_OPTIONS.map((o) => (
                          <option key={o.value} value={o.value}>
                            {o.label}
                          </option>
                        ))}
                      </select>
                    ),
                  },
                  { key: "sent_at", header: "발송일", render: (r) => r.sent_at ?? "-" },
                  { key: "signed_at", header: "체결일", render: (r) => r.signed_at ?? "-" },
                  { key: "expires_at", header: "만료일", render: (r) => r.expires_at ?? "-" },
                  {
                    key: "actions",
                    header: "",
                    width: "40px",
                    render: (r) => (
                      <button
                        className="text-text-muted hover:text-negative p-1 rounded transition-colors"
                        title="삭제"
                        onClick={() => {
                          if (confirm("이 NDA를 삭제하시겠습니까?")) {
                            deleteNda.mutate(r.id);
                          }
                        }}
                      >
                        <Trash2 size={14} />
                      </button>
                    ),
                  },
                ]}
                data={ndas}
                keyField="id"
              />
            )}
          </Card>
        </div>
      )}

      {/* ── Bids 탭 ─────────────────────────────────────── */}
      {activeTab === "bids" && (
        <div className="space-y-4">
          {/* 비교 매트릭스 */}
          {bidComparison && bidComparison.length > 0 && (
            <Card title="입찰 비교 매트릭스" headerBar padding="none">
              <DataTable
                columns={[
                  { key: "buyer_name", header: "매수자" },
                  {
                    key: "buyer_type",
                    header: "유형",
                    render: (r) => (
                      <Badge variant="neutral">
                        {BUYER_TYPE_OPTIONS.find((o) => o.value === r.buyer_type)?.label ?? r.buyer_type}
                      </Badge>
                    ),
                  },
                  {
                    key: "ioi",
                    header: "IOI",
                    align: "right",
                    mono: true,
                    render: (r) => r.ioi ? formatAmount(r.ioi.amount) : "-",
                  },
                  {
                    key: "loi",
                    header: "LOI",
                    align: "right",
                    mono: true,
                    render: (r) => r.loi ? formatAmount(r.loi.amount) : "-",
                  },
                  {
                    key: "final_offer",
                    header: "최종 제안",
                    align: "right",
                    mono: true,
                    render: (r) => r.final_offer ? formatAmount(r.final_offer.amount) : "-",
                  },
                ]}
                data={bidComparison}
                keyField="buyer_id"
              />
            </Card>
          )}

          {/* 전체 입찰 목록 */}
          <Card
            title="입찰 이력"
            headerBar
            padding="none"
            actions={
              <Button icon={Plus} onClick={() => setShowBidModal(true)} variant="ghost">
                입찰 추가
              </Button>
            }
          >
            {!bids?.length ? (
              <EmptyState
                icon={DollarSign}
                title="입찰 없음"
                description="IOI/LOI/최종 제안을 등록하세요."
                actionLabel="입찰 추가"
                onAction={() => setShowBidModal(true)}
              />
            ) : (
              <DataTable
                columns={[
                  {
                    key: "buyer_candidate_id",
                    header: "매수자",
                    render: (r) => {
                      const buyer = buyers?.find((b) => b.id === r.buyer_candidate_id);
                      return buyer?.company_name ?? r.buyer_candidate_id.slice(0, 8);
                    },
                  },
                  {
                    key: "bid_type",
                    header: "유형",
                    render: (r) => (
                      <Badge variant="info">
                        {BID_TYPE_OPTIONS.find((o) => o.value === r.bid_type)?.label ?? r.bid_type}
                      </Badge>
                    ),
                  },
                  {
                    key: "amount",
                    header: "금액",
                    align: "right",
                    mono: true,
                    render: (r) => formatAmount(r.amount),
                  },
                  {
                    key: "valuation_method",
                    header: "밸류에이션",
                    render: (r) =>
                      r.valuation_method
                        ? (VALUATION_METHOD_OPTIONS.find((o) => o.value === r.valuation_method)?.label ?? r.valuation_method)
                        : "-",
                  },
                  {
                    key: "multiple",
                    header: "배수",
                    align: "right",
                    mono: true,
                    render: (r) => (r.multiple != null ? `${r.multiple}x` : "-"),
                  },
                  {
                    key: "status",
                    header: "상태",
                    render: (r) => (
                      <select
                        className="text-xs border rounded px-1.5 py-0.5 bg-white"
                        value={r.status}
                        onChange={(e) =>
                          updateBid.mutate({
                            bidId: r.id,
                            body: { status: e.target.value as BidStatusType },
                          })
                        }
                      >
                        {BID_STATUS_OPTIONS.map((o) => (
                          <option key={o.value} value={o.value}>
                            {o.label}
                          </option>
                        ))}
                      </select>
                    ),
                  },
                  { key: "submitted_at", header: "제출일", render: (r) => r.submitted_at ?? "-" },
                  {
                    key: "actions",
                    header: "",
                    width: "40px",
                    render: (r) => (
                      <button
                        className="text-text-muted hover:text-negative p-1 rounded transition-colors"
                        title="삭제"
                        onClick={() => {
                          if (confirm("이 입찰을 삭제하시겠습니까?")) {
                            deleteBid.mutate(r.id);
                          }
                        }}
                      >
                        <Trash2 size={14} />
                      </button>
                    ),
                  },
                ]}
                data={bids}
                keyField="id"
              />
            )}
          </Card>
        </div>
      )}

      {/* ── DD 체크리스트 탭 ─────────────────────────────── */}
      {activeTab === "dd-checklist" && (
        <div className="space-y-4">
          {/* DD 진행 요약 */}
          {ddSummary && ddSummary.total > 0 && (
            <div className="space-y-3">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <KpiCard label="전체 항목" value={ddSummary.total} />
                <KpiCard
                  label="완료율"
                  value={`${Math.round(ddSummary.overall_completion_pct)}%`}
                  variant={ddSummary.overall_completion_pct >= 80 ? "positive" : "neutral"}
                />
                <KpiCard
                  label="진행 중"
                  value={ddSummary.by_workstream.reduce((s, w) => s + w.in_progress, 0)}
                />
                <KpiCard
                  label="미시작"
                  value={ddSummary.by_workstream.reduce((s, w) => s + w.not_started, 0)}
                  variant={ddSummary.by_workstream.reduce((s, w) => s + w.not_started, 0) > 0 ? "negative" : "neutral"}
                />
              </div>
              {/* 워크스트림별 진행률 바 */}
              <Card padding="md">
                <div className="space-y-2">
                  {ddSummary.by_workstream.map((ws) => {
                    const pct = ws.total > 0 ? Math.round((ws.completed / ws.total) * 100) : 0;
                    return (
                      <div key={ws.workstream} className="flex items-center gap-3">
                        <span className="text-xs font-medium w-20 truncate">
                          {DD_WORKSTREAM_OPTIONS.find((o) => o.value === ws.workstream)?.label ?? ws.workstream}
                        </span>
                        <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-accent rounded-full transition-all"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                        <span className="text-xs text-text-muted w-16 text-right">
                          {ws.completed}/{ws.total}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </Card>
            </div>
          )}

          {/* 체크리스트 목록 */}
          <Card
            title="DD 체크리스트"
            headerBar
            padding="none"
            actions={
              <Button icon={Plus} onClick={() => setShowDDModal(true)} variant="ghost">
                항목 추가
              </Button>
            }
          >
            {!ddItems?.length ? (
              <EmptyState
                icon={ClipboardCheck}
                title="체크리스트 없음"
                description="실사 체크리스트 항목을 추가하세요."
                actionLabel="항목 추가"
                onAction={() => setShowDDModal(true)}
              />
            ) : (
              <DataTable
                columns={[
                  {
                    key: "workstream",
                    header: "워크스트림",
                    render: (r) => (
                      <Badge variant="neutral">
                        {DD_WORKSTREAM_OPTIONS.find((o) => o.value === r.workstream)?.label ?? r.workstream}
                      </Badge>
                    ),
                  },
                  { key: "title", header: "항목" },
                  {
                    key: "status",
                    header: "상태",
                    render: (r) => (
                      <select
                        className="text-xs border rounded px-1.5 py-0.5 bg-white"
                        value={r.status}
                        onChange={(e) =>
                          updateDDItem.mutate({
                            itemId: r.id,
                            body: { status: e.target.value as DDStatusType },
                          })
                        }
                      >
                        {DD_STATUS_OPTIONS.map((o) => (
                          <option key={o.value} value={o.value}>
                            {o.label}
                          </option>
                        ))}
                      </select>
                    ),
                  },
                  { key: "assignee_email", header: "담당자", render: (r) => r.assignee_email ?? "-" },
                  { key: "due_date", header: "기한", render: (r) => r.due_date ?? "-" },
                  {
                    key: "actions",
                    header: "",
                    width: "40px",
                    render: (r) => (
                      <button
                        className="text-text-muted hover:text-negative p-1 rounded transition-colors"
                        title="삭제"
                        onClick={() => {
                          if (confirm("이 체크리스트 항목을 삭제하시겠습니까?")) {
                            deleteDDItem.mutate(r.id);
                          }
                        }}
                      >
                        <Trash2 size={14} />
                      </button>
                    ),
                  },
                ]}
                data={ddItems}
                keyField="id"
              />
            )}
          </Card>
        </div>
      )}

      {/* ── Timeline 탭 ───────────────────────────────── */}
      {activeTab === "timeline" && (
        <Card title="타임라인" headerBar>
          {!timeline?.items.length ? (
            <EmptyState
              icon={Calendar}
              title="이벤트 없음"
              description="거래 활동이 시작되면 자동으로 기록됩니다."
            />
          ) : (
            <div className="space-y-3 p-1">
              {timeline.items.map((event) => (
                <div
                  key={event.id}
                  className="flex gap-3 items-start border-l-2 border-accent/20 pl-4 py-1"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">
                        {event.title}
                      </span>
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
          )}
        </Card>
      )}

      {/* ── Modals ────────────────────────────────────── */}

      {/* Engagement 추가 모달 */}
      <Modal
        open={showEngModal}
        onClose={() => setShowEngModal(false)}
        title="수임계약 추가"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createEngagement.mutate(engForm, {
              onSuccess: () => {
                setShowEngModal(false);
                setEngForm({ type: "EXCLUSIVE" });
              },
            });
          }}
          className="space-y-4"
        >
          <Select
            label="유형"
            options={ENGAGEMENT_TYPE_OPTIONS}
            value={engForm.type}
            onChange={(e) =>
              setEngForm({ ...engForm, type: e.target.value as EngagementCreate["type"] })
            }
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="체결일"
              type="date"
              value={engForm.signed_at ?? ""}
              onChange={(e) =>
                setEngForm({ ...engForm, signed_at: e.target.value || undefined })
              }
            />
            <Input
              label="만료일"
              type="date"
              value={engForm.expires_at ?? ""}
              onChange={(e) =>
                setEngForm({ ...engForm, expires_at: e.target.value || undefined })
              }
            />
          </div>
          <Input
            label="비고"
            value={engForm.notes ?? ""}
            onChange={(e) =>
              setEngForm({ ...engForm, notes: e.target.value || undefined })
            }
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="ghost"
              type="button"
              onClick={() => setShowEngModal(false)}
            >
              취소
            </Button>
            <Button type="submit" loading={createEngagement.isPending}>
              등록
            </Button>
          </div>
        </form>
      </Modal>

      {/* Member 추가 모달 */}
      <Modal
        open={showMemberModal}
        onClose={() => setShowMemberModal(false)}
        title="멤버 추가"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            addMember.mutate(memberForm, {
              onSuccess: () => {
                setShowMemberModal(false);
                setMemberForm({ name: "", email: "", role: "LEAD_ADVISOR" });
              },
            });
          }}
          className="space-y-4"
        >
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="이름"
              required
              value={memberForm.name}
              onChange={(e) =>
                setMemberForm({ ...memberForm, name: e.target.value })
              }
            />
            <Input
              label="이메일"
              type="email"
              required
              value={memberForm.email}
              onChange={(e) =>
                setMemberForm({ ...memberForm, email: e.target.value })
              }
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="소속"
              value={memberForm.organization ?? ""}
              onChange={(e) =>
                setMemberForm({
                  ...memberForm,
                  organization: e.target.value || undefined,
                })
              }
            />
            <Select
              label="역할"
              options={WORKING_GROUP_ROLE_OPTIONS}
              value={memberForm.role}
              onChange={(e) =>
                setMemberForm({
                  ...memberForm,
                  role: e.target.value as WorkingGroupMemberCreate["role"],
                })
              }
            />
          </div>
          <Input
            label="전화"
            value={memberForm.phone ?? ""}
            onChange={(e) =>
              setMemberForm({
                ...memberForm,
                phone: e.target.value || undefined,
              })
            }
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="ghost"
              type="button"
              onClick={() => setShowMemberModal(false)}
            >
              취소
            </Button>
            <Button type="submit" loading={addMember.isPending}>
              추가
            </Button>
          </div>
        </form>
      </Modal>

      {/* Buyer 추가 모달 */}
      <Modal
        open={showBuyerModal}
        onClose={() => setShowBuyerModal(false)}
        title="매수자 후보 추가"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            addBuyer.mutate(buyerForm, {
              onSuccess: () => {
                setShowBuyerModal(false);
                setBuyerForm({ company_name: "", buyer_type: "STRATEGIC" });
              },
            });
          }}
          className="space-y-4"
        >
          <Input
            label="회사명"
            required
            value={buyerForm.company_name}
            onChange={(e) =>
              setBuyerForm({ ...buyerForm, company_name: e.target.value })
            }
            placeholder="매수 후보 기업명"
          />
          <Select
            label="유형"
            options={BUYER_TYPE_OPTIONS.filter((o) => o.value !== "")}
            value={buyerForm.buyer_type}
            onChange={(e) =>
              setBuyerForm({
                ...buyerForm,
                buyer_type: e.target.value as BuyerCandidateCreate["buyer_type"],
              })
            }
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="담당자"
              value={buyerForm.contact_name ?? ""}
              onChange={(e) =>
                setBuyerForm({
                  ...buyerForm,
                  contact_name: e.target.value || undefined,
                })
              }
            />
            <Input
              label="이메일"
              type="email"
              value={buyerForm.contact_email ?? ""}
              onChange={(e) =>
                setBuyerForm({
                  ...buyerForm,
                  contact_email: e.target.value || undefined,
                })
              }
            />
          </div>
          <Input
            label="비고"
            value={buyerForm.notes ?? ""}
            onChange={(e) =>
              setBuyerForm({
                ...buyerForm,
                notes: e.target.value || undefined,
              })
            }
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="ghost"
              type="button"
              onClick={() => setShowBuyerModal(false)}
            >
              취소
            </Button>
            <Button type="submit" loading={addBuyer.isPending}>
              추가
            </Button>
          </div>
        </form>
      </Modal>

      {/* NDA 추가 모달 */}
      <Modal
        open={showNdaModal}
        onClose={() => setShowNdaModal(false)}
        title="NDA 추가"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createNda.mutate(ndaForm, {
              onSuccess: () => {
                setShowNdaModal(false);
                setNdaForm({ buyer_candidate_id: "", nda_type: "MUTUAL" });
              },
            });
          }}
          className="space-y-4"
        >
          <Select
            label="매수자"
            options={(buyers ?? []).map((b) => ({ value: b.id, label: b.company_name }))}
            value={ndaForm.buyer_candidate_id}
            onChange={(e) =>
              setNdaForm({ ...ndaForm, buyer_candidate_id: e.target.value })
            }
          />
          <Select
            label="NDA 유형"
            options={NDA_TYPE_OPTIONS}
            value={ndaForm.nda_type ?? "MUTUAL"}
            onChange={(e) =>
              setNdaForm({ ...ndaForm, nda_type: e.target.value as NDACreate["nda_type"] })
            }
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="발송일"
              type="date"
              value={ndaForm.sent_at ?? ""}
              onChange={(e) =>
                setNdaForm({ ...ndaForm, sent_at: e.target.value || undefined })
              }
            />
            <Input
              label="만료일"
              type="date"
              value={ndaForm.expires_at ?? ""}
              onChange={(e) =>
                setNdaForm({ ...ndaForm, expires_at: e.target.value || undefined })
              }
            />
          </div>
          <Input
            label="비고"
            value={ndaForm.notes ?? ""}
            onChange={(e) =>
              setNdaForm({ ...ndaForm, notes: e.target.value || undefined })
            }
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="ghost" type="button" onClick={() => setShowNdaModal(false)}>
              취소
            </Button>
            <Button type="submit" loading={createNda.isPending}>
              등록
            </Button>
          </div>
        </form>
      </Modal>

      {/* Bid 추가 모달 */}
      <Modal
        open={showBidModal}
        onClose={() => setShowBidModal(false)}
        title="입찰 등록"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createBid.mutate(bidForm, {
              onSuccess: () => {
                setShowBidModal(false);
                setBidForm({ buyer_candidate_id: "", bid_type: "IOI" });
              },
            });
          }}
          className="space-y-4"
        >
          <Select
            label="매수자"
            options={(buyers ?? []).map((b) => ({ value: b.id, label: b.company_name }))}
            value={bidForm.buyer_candidate_id}
            onChange={(e) =>
              setBidForm({ ...bidForm, buyer_candidate_id: e.target.value })
            }
          />
          <div className="grid grid-cols-2 gap-4">
            <Select
              label="입찰 유형"
              options={BID_TYPE_OPTIONS}
              value={bidForm.bid_type}
              onChange={(e) =>
                setBidForm({ ...bidForm, bid_type: e.target.value as BidType })
              }
            />
            <Input
              label="금액 (원)"
              type="number"
              value={bidForm.amount ?? ""}
              onChange={(e) =>
                setBidForm({ ...bidForm, amount: e.target.value ? Number(e.target.value) : undefined })
              }
              placeholder="50000000000"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Select
              label="밸류에이션"
              options={VALUATION_METHOD_OPTIONS}
              value={bidForm.valuation_method ?? ""}
              onChange={(e) =>
                setBidForm({ ...bidForm, valuation_method: (e.target.value || undefined) as ValuationMethod | undefined })
              }
            />
            <Input
              label="배수"
              type="number"
              step="0.1"
              value={bidForm.multiple ?? ""}
              onChange={(e) =>
                setBidForm({ ...bidForm, multiple: e.target.value ? Number(e.target.value) : undefined })
              }
              placeholder="8.5"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="제출일"
              type="date"
              value={bidForm.submitted_at ?? ""}
              onChange={(e) =>
                setBidForm({ ...bidForm, submitted_at: e.target.value || undefined })
              }
            />
            <Input
              label="유효기간"
              type="date"
              value={bidForm.valid_until ?? ""}
              onChange={(e) =>
                setBidForm({ ...bidForm, valid_until: e.target.value || undefined })
              }
            />
          </div>
          <Input
            label="조건 / 비고"
            value={bidForm.conditions ?? ""}
            onChange={(e) =>
              setBidForm({ ...bidForm, conditions: e.target.value || undefined })
            }
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="ghost" type="button" onClick={() => setShowBidModal(false)}>
              취소
            </Button>
            <Button type="submit" loading={createBid.isPending}>
              등록
            </Button>
          </div>
        </form>
      </Modal>

      {/* DD 체크리스트 추가 모달 */}
      <Modal
        open={showDDModal}
        onClose={() => setShowDDModal(false)}
        title="DD 체크리스트 항목 추가"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createDDItem.mutate(ddForm, {
              onSuccess: () => {
                setShowDDModal(false);
                setDDForm({ workstream: "FINANCIAL", title: "" });
              },
            });
          }}
          className="space-y-4"
        >
          <Select
            label="워크스트림"
            options={DD_WORKSTREAM_OPTIONS}
            value={ddForm.workstream}
            onChange={(e) =>
              setDDForm({ ...ddForm, workstream: e.target.value as DDWorkstream })
            }
          />
          <Input
            label="항목명"
            required
            value={ddForm.title}
            onChange={(e) => setDDForm({ ...ddForm, title: e.target.value })}
            placeholder="예: 최근 3개년 재무제표 수집"
          />
          <Input
            label="설명"
            value={ddForm.description ?? ""}
            onChange={(e) =>
              setDDForm({ ...ddForm, description: e.target.value || undefined })
            }
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="담당자 이메일"
              type="email"
              value={ddForm.assignee_email ?? ""}
              onChange={(e) =>
                setDDForm({ ...ddForm, assignee_email: e.target.value || undefined })
              }
            />
            <Input
              label="기한"
              type="date"
              value={ddForm.due_date ?? ""}
              onChange={(e) =>
                setDDForm({ ...ddForm, due_date: e.target.value || undefined })
              }
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="ghost" type="button" onClick={() => setShowDDModal(false)}>
              취소
            </Button>
            <Button type="submit" loading={createDDItem.isPending}>
              추가
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
