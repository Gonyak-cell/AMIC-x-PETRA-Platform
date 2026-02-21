import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  Play,
  Pause,
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
  Scale,
  Flag,
  Sparkles,
  MessageSquare,
  Pin,
  Clock,
  Check,
  X,
  Send,
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
import type { EngagementCreate } from "@/modules/ma/types/engagement";
import type { WorkingGroupMemberCreate } from "@/modules/ma/types/engagement";
import type { BuyerCandidateCreate } from "@/modules/ma/types/buyer";
import { useNdas, useNdaSummary, useCreateNda, useUpdateNda, useDeleteNda } from "@/modules/ma/hooks/useNdas";
import { useBids, useBidComparison, useCreateBid, useUpdateBid, useDeleteBid } from "@/modules/ma/hooks/useBids";
import { useDDChecklist, useDDChecklistSummary, useCreateDDChecklistItem, useUpdateDDChecklistItem, useDeleteDDChecklistItem } from "@/modules/ma/hooks/useDDChecklist";
import { useContracts, useContractSummary, useCreateContract, useUpdateContract, useDeleteContract, useAnalyzeContract } from "@/modules/ma/hooks/useContracts";
import { useClosingChecklist, useClosingSummary, useCreateClosingItem, useUpdateClosingItem, useDeleteClosingItem } from "@/modules/ma/hooks/useClosing";
import { usePMITasks, usePMISummary, useCreatePMITask, useUpdatePMITask, useDeletePMITask } from "@/modules/ma/hooks/usePMI";
import { useEarnoutMilestones, useEarnoutSummary, useCreateEarnout, useUpdateEarnout, useDeleteEarnout } from "@/modules/ma/hooks/useEarnout";
import { useNotes, useCreateNote, useDeleteNote } from "@/modules/ma/hooks/useNotes";
import { useApprovals, useApprovalSummary, useCreateApproval, useDecideApproval, useCancelApproval } from "@/modules/ma/hooks/useApprovals";
import type { NoteCreate, NoteType } from "@/modules/ma/types/note";
import type { ApprovalCreate, ApprovalType as AppType, ApprovalStatus as AppStatus } from "@/modules/ma/types/approval";
import type { NDACreate, NdaStatus } from "@/modules/ma/types/nda";
import type { BidCreate, BidType, BidStatus as BidStatusType, ValuationMethod } from "@/modules/ma/types/bid";
import type { DDChecklistCreate, DDWorkstream, DDChecklistStatus as DDStatusType } from "@/modules/ma/types/dd_checklist";
import type { ContractCreate, ContractStatus, SignatureStatus as SigStatus } from "@/modules/ma/types/contract";
import type { ClosingChecklistCreate, ClosingCategory, ClosingConditionStatus } from "@/modules/ma/types/closing";
import type { PMITask, PMITaskCreate, PMICategory, PMITaskStatus, PMIPriority } from "@/modules/ma/types/pmi";
import type { EarnoutCreate, EarnoutStatus, EarnoutMetric } from "@/modules/ma/types/earnout";
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
  CONTRACT_TYPE_OPTIONS,
  CONTRACT_STATUS_OPTIONS,
  SIGNATURE_STATUS_OPTIONS,
  CLOSING_CATEGORY_OPTIONS,
  CLOSING_CONDITION_STATUS_OPTIONS,
  PMI_CATEGORY_OPTIONS,
  PMI_STATUS_OPTIONS,
  PMI_PRIORITY_OPTIONS,
  EARNOUT_STATUS_OPTIONS,
  EARNOUT_METRIC_OPTIONS,
  NOTE_TYPE_OPTIONS,
  APPROVAL_TYPE_OPTIONS,
  APPROVAL_STATUS_OPTIONS,
} from "@/modules/ma/constants";

import {
  Badge,
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

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("ko-KR");
}

function formatAmount(amount: number | null): string {
  if (amount == null) return "-";
  if (amount >= 1_0000_0000) return `${(amount / 1_0000_0000).toLocaleString()}억`;
  return amount.toLocaleString();
}

const INLINE_CLS =
  "text-xs border border-gray-200 rounded px-1.5 py-0.5 bg-transparent hover:bg-white focus:bg-white focus:ring-2 focus:ring-accent/30 focus:border-amic transition-colors";

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
  const VALID_TABS = ["engagement", "team", "buyers", "timeline", "ndas", "bids", "dd-checklist", "contracts", "closing", "pmi", "earnout", "notes-approvals"];
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

  // 데이터 로드 — Phase 3
  const { data: contracts } = useContracts(id);
  const { data: contractSummary } = useContractSummary(id);
  const { data: closingItems } = useClosingChecklist(id);
  const { data: closingSummary } = useClosingSummary(id);

  // 데이터 로드 — Phase 4
  const { data: pmiTasks } = usePMITasks(id);
  const { data: pmiSummary } = usePMISummary(id);
  const { data: earnoutMilestones } = useEarnoutMilestones(id);
  const { data: earnoutSummary } = useEarnoutSummary(id);

  // 데이터 로드 — Phase 5A
  const { data: notesData } = useNotes(id);
  const { data: approvalsData } = useApprovals(id);
  const { data: approvalSummary } = useApprovalSummary(id);

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

  // Mutations — Phase 3
  const createContract = useCreateContract(id);
  const updateContract = useUpdateContract(id);
  const deleteContract = useDeleteContract(id);
  const analyzeContract = useAnalyzeContract(id);
  const createClosingItem = useCreateClosingItem(id);
  const updateClosingItem = useUpdateClosingItem(id);
  const deleteClosingItem = useDeleteClosingItem(id);

  // Mutations — Phase 4
  const createPMITask = useCreatePMITask(id);
  const updatePMITask = useUpdatePMITask(id);
  const deletePMITask = useDeletePMITask(id);
  const createEarnout = useCreateEarnout(id);
  const updateEarnout = useUpdateEarnout(id);
  const deleteEarnout = useDeleteEarnout(id);

  // Mutations — Phase 5A
  const createNote = useCreateNote(id);
  const deleteNote = useDeleteNote(id);
  const createApproval = useCreateApproval(id);
  const decideApproval = useDecideApproval();
  const cancelApproval = useCancelApproval();

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

  // UI State — Phase 3
  const [showContractModal, setShowContractModal] = useState(false);
  const [showClosingModal, setShowClosingModal] = useState(false);

  // UI State — Phase 4
  const [showPMIModal, setShowPMIModal] = useState(false);
  const [showEarnoutModal, setShowEarnoutModal] = useState(false);

  // UI State — Phase 5A
  const [showNoteModal, setShowNoteModal] = useState(false);
  const [showApprovalModal, setShowApprovalModal] = useState(false);

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

  // Form state — Phase 3
  const [contractForm, setContractForm] = useState<ContractCreate>({ title: "" });
  const [closingForm, setClosingForm] = useState<ClosingChecklistCreate>({
    category: "REGULATORY" as ClosingCategory,
    title: "",
  });

  // Form state — Phase 4
  const [pmiForm, setPmiForm] = useState<PMITaskCreate>({
    category: "INTEGRATION_PLAN" as PMICategory,
    title: "",
  });
  const [earnoutForm, setEarnoutForm] = useState<EarnoutCreate>({
    title: "",
    metric: "REVENUE" as EarnoutMetric,
    target_value: 0,
  });

  // Form state — Phase 5A
  const [noteForm, setNoteForm] = useState<NoteCreate>({
    content: "",
    note_type: "COMMENT",
  });
  const [approvalForm, setApprovalForm] = useState<ApprovalCreate>({
    approval_type: "PHASE_ADVANCE",
    title: "",
    approvers: [{ email: "", role: "승인자" }],
  });

  // Note type 필터
  const [noteTypeFilter, setNoteTypeFilter] = useState<string>("ALL");
  const filteredNotes =
    noteTypeFilter === "ALL"
      ? notesData?.items
      : notesData?.items.filter((n) => n.note_type === noteTypeFilter);

  // DD 워크스트림 필터
  const [ddWorkstreamFilter, setDdWorkstreamFilter] = useState<string>("ALL");
  const filteredDDItems =
    ddWorkstreamFilter === "ALL"
      ? ddItems
      : ddItems?.filter((item) => item.workstream === ddWorkstreamFilter);

  // 클로징 카테고리 필터
  const [closingCategoryFilter, setClosingCategoryFilter] = useState<string>("ALL");
  const filteredClosingItems =
    closingCategoryFilter === "ALL"
      ? closingItems
      : closingItems?.filter((item) => item.category === closingCategoryFilter);

  // PMI 카테고리 필터
  const [pmiCategoryFilter, setPmiCategoryFilter] = useState<string>("ALL");
  const filteredPmiTasks =
    pmiCategoryFilter === "ALL"
      ? pmiTasks
      : pmiTasks?.filter((t) => t.category === pmiCategoryFilter);

  const tabs: TabItem[] = [
    { id: "overview", label: "Overview" },
    { id: "engagement", label: "수임", badge: engagements?.length },
    { id: "team", label: "팀", badge: members?.length },
    { id: "buyers", label: "매수자", badge: buyers?.length },
    { id: "ndas", label: "NDA", badge: ndas?.length },
    { id: "bids", label: "입찰", badge: bids?.length },
    { id: "dd-checklist", label: "DD 체크리스트", badge: ddItems?.length },
    { id: "contracts", label: "계약/SPA", badge: contracts?.length },
    { id: "closing", label: "클로징", badge: closingItems?.length },
    { id: "pmi", label: "PMI", badge: pmiTasks?.length },
    { id: "earnout", label: "어닝아웃", badge: earnoutMilestones?.length },
    { id: "notes-approvals", label: "노트/승인", badge: (notesData?.total ?? 0) + (approvalsData?.total ?? 0) || undefined },
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
              <KpiCard label="전체" value={String(ndaSummary.total)} />
              <KpiCard label="체결 완료" value={String(ndaSummary.signed_count)} variant="positive" />
              <KpiCard label="대기 중" value={String(ndaSummary.pending_count)} variant="default" />
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
                      <Select
                        options={NDA_STATUS_OPTIONS}
                        value={r.status}
                        onChange={(e) =>
                          updateNda.mutate({
                            ndaId: r.id,
                            body: { status: e.target.value as NdaStatus },
                          })
                        }
                        className="!py-0.5 !px-1.5 !text-xs"
                      />
                    ),
                  },
                  {
                    key: "sent_at",
                    header: "발송일",
                    render: (r) => (
                      <input
                        key={`${r.id}-sent-${r.sent_at}`}
                        type="date"
                        className={`${INLINE_CLS} w-32`}
                        defaultValue={r.sent_at ?? ""}
                        onChange={(e) =>
                          updateNda.mutate({ ndaId: r.id, body: { sent_at: e.target.value || undefined } })
                        }
                      />
                    ),
                  },
                  {
                    key: "signed_at",
                    header: "체결일",
                    render: (r) => (
                      <input
                        key={`${r.id}-signed-${r.signed_at}`}
                        type="date"
                        className={`${INLINE_CLS} w-32`}
                        defaultValue={r.signed_at ?? ""}
                        onChange={(e) =>
                          updateNda.mutate({ ndaId: r.id, body: { signed_at: e.target.value || undefined } })
                        }
                      />
                    ),
                  },
                  {
                    key: "expires_at",
                    header: "만료일",
                    render: (r) => (
                      <input
                        key={`${r.id}-expires-${r.expires_at}`}
                        type="date"
                        className={`${INLINE_CLS} w-32`}
                        defaultValue={r.expires_at ?? ""}
                        onChange={(e) =>
                          updateNda.mutate({ ndaId: r.id, body: { expires_at: e.target.value || undefined } })
                        }
                      />
                    ),
                  },
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
                    render: (r) => (
                      <input
                        key={`${r.id}-amount-${r.amount}`}
                        type="number"
                        className={`${INLINE_CLS} w-28 text-right font-mono`}
                        defaultValue={r.amount ?? ""}
                        placeholder="금액"
                        onBlur={(e) => {
                          const v = e.target.value ? Number(e.target.value) : undefined;
                          if (v !== (r.amount ?? undefined)) {
                            updateBid.mutate({ bidId: r.id, body: { amount: v } });
                          }
                        }}
                      />
                    ),
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
                      <Select
                        options={BID_STATUS_OPTIONS}
                        value={r.status}
                        onChange={(e) =>
                          updateBid.mutate({
                            bidId: r.id,
                            body: { status: e.target.value as BidStatusType },
                          })
                        }
                        className="!py-0.5 !px-1.5 !text-xs"
                      />
                    ),
                  },
                  {
                    key: "submitted_at",
                    header: "제출일",
                    render: (r) => (
                      <input
                        key={`${r.id}-submitted-${r.submitted_at}`}
                        type="date"
                        className={`${INLINE_CLS} w-32`}
                        defaultValue={r.submitted_at ?? ""}
                        onChange={(e) =>
                          updateBid.mutate({ bidId: r.id, body: { submitted_at: e.target.value || undefined } })
                        }
                      />
                    ),
                  },
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
                <KpiCard label="전체 항목" value={String(ddSummary.total)} />
                <KpiCard
                  label="완료율"
                  value={`${Math.round(ddSummary.overall_completion_pct)}%`}
                  variant={ddSummary.overall_completion_pct >= 80 ? "positive" : "default"}
                />
                <KpiCard
                  label="진행 중"
                  value={String(ddSummary.by_workstream.reduce((s, w) => s + w.in_progress, 0))}
                />
                <KpiCard
                  label="미시작"
                  value={String(ddSummary.by_workstream.reduce((s, w) => s + w.not_started, 0))}
                  variant={ddSummary.by_workstream.reduce((s, w) => s + w.not_started, 0) > 0 ? "negative" : "default"}
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

          {/* 워크스트림 필터 */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-medium text-text-muted">워크스트림:</span>
            {[{ value: "ALL", label: "전체" }, ...DD_WORKSTREAM_OPTIONS].map((opt) => (
              <button
                key={opt.value}
                type="button"
                className={`px-3 py-1 text-xs font-medium rounded-full transition-colors ${
                  ddWorkstreamFilter === opt.value
                    ? "bg-accent text-white"
                    : "bg-gray-100 text-text-secondary hover:bg-gray-200"
                }`}
                onClick={() => setDdWorkstreamFilter(opt.value)}
              >
                {opt.label}
              </button>
            ))}
          </div>

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
            ) : !filteredDDItems?.length ? (
              <div className="p-8 text-center text-text-muted text-sm">
                선택한 워크스트림에 해당하는 항목이 없습니다.
              </div>
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
                      <Select
                        options={DD_STATUS_OPTIONS}
                        value={r.status}
                        onChange={(e) =>
                          updateDDItem.mutate({
                            itemId: r.id,
                            body: { status: e.target.value as DDStatusType },
                          })
                        }
                        className="!py-0.5 !px-1.5 !text-xs"
                      />
                    ),
                  },
                  {
                    key: "assignee_email",
                    header: "담당자",
                    render: (r) => (
                      <input
                        key={`${r.id}-assignee-${r.assignee_email}`}
                        type="email"
                        className={`${INLINE_CLS} w-36`}
                        defaultValue={r.assignee_email ?? ""}
                        placeholder="이메일"
                        onBlur={(e) => {
                          const v = e.target.value || undefined;
                          if (v !== (r.assignee_email ?? undefined)) {
                            updateDDItem.mutate({ itemId: r.id, body: { assignee_email: v } });
                          }
                        }}
                      />
                    ),
                  },
                  {
                    key: "due_date",
                    header: "기한",
                    render: (r) => (
                      <input
                        key={`${r.id}-due-${r.due_date}`}
                        type="date"
                        className={`${INLINE_CLS} w-32`}
                        defaultValue={r.due_date ?? ""}
                        onChange={(e) =>
                          updateDDItem.mutate({ itemId: r.id, body: { due_date: e.target.value || undefined } })
                        }
                      />
                    ),
                  },
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
                data={filteredDDItems ?? []}
                keyField="id"
              />
            )}
          </Card>
        </div>
      )}

      {/* ── 계약/SPA 탭 ───────────────────────────────── */}
      {activeTab === "contracts" && (
        <div className="space-y-4">
          {/* 계약 요약 KPI */}
          {contractSummary && contractSummary.total > 0 && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <KpiCard label="전체 계약" value={String(contractSummary.total)} />
              <KpiCard
                label="서명 대기"
                value={String(contractSummary.pending_signatures)}
                variant={contractSummary.pending_signatures > 0 ? "caution" : "default"}
              />
              <KpiCard label="체결 완료" value={String(contractSummary.fully_executed)} variant="positive" />
              <KpiCard
                label="유형별"
                value={String(Object.keys(contractSummary.by_type).length)}
              />
            </div>
          )}

          {/* 계약 목록 */}
          <Card
            title="계약서 목록"
            headerBar
            padding="none"
            actions={
              <Button icon={Plus} onClick={() => setShowContractModal(true)} variant="ghost">
                계약서 추가
              </Button>
            }
          >
            {!contracts?.length ? (
              <EmptyState
                icon={Scale}
                title="계약서 없음"
                description="SPA, SHA 등 계약서를 등록하세요."
                actionLabel="계약서 추가"
                onAction={() => setShowContractModal(true)}
              />
            ) : (
              <DataTable
                columns={[
                  { key: "title", header: "제목" },
                  {
                    key: "contract_type",
                    header: "유형",
                    render: (r) => (
                      <Badge variant="neutral">
                        {CONTRACT_TYPE_OPTIONS.find((o) => o.value === r.contract_type)?.label ?? r.contract_type}
                      </Badge>
                    ),
                  },
                  {
                    key: "status",
                    header: "상태",
                    render: (r) => (
                      <Select
                        options={CONTRACT_STATUS_OPTIONS}
                        value={r.status}
                        onChange={(e) =>
                          updateContract.mutate({
                            contractId: r.id,
                            body: { status: e.target.value as ContractStatus },
                          })
                        }
                        className="!py-0.5 !px-1.5 !text-xs"
                      />
                    ),
                  },
                  {
                    key: "counterparty_name",
                    header: "상대방",
                    render: (r) => r.counterparty_name ?? "-",
                  },
                  {
                    key: "current_version",
                    header: "버전",
                    align: "right",
                    render: (r) => `v${r.current_version}`,
                  },
                  {
                    key: "seller_signature",
                    header: "매도측 서명",
                    render: (r) => (
                      <Select
                        options={SIGNATURE_STATUS_OPTIONS}
                        value={r.seller_signature}
                        onChange={(e) =>
                          updateContract.mutate({
                            contractId: r.id,
                            body: { seller_signature: e.target.value as SigStatus },
                          })
                        }
                        className="!py-0.5 !px-1.5 !text-xs"
                      />
                    ),
                  },
                  {
                    key: "buyer_signature",
                    header: "매수측 서명",
                    render: (r) => (
                      <Select
                        options={SIGNATURE_STATUS_OPTIONS}
                        value={r.buyer_signature}
                        onChange={(e) =>
                          updateContract.mutate({
                            contractId: r.id,
                            body: { buyer_signature: e.target.value as SigStatus },
                          })
                        }
                        className="!py-0.5 !px-1.5 !text-xs"
                      />
                    ),
                  },
                  {
                    key: "effective_date",
                    header: "효력일",
                    render: (r) => (
                      <input
                        key={`${r.id}-eff-${r.effective_date}`}
                        type="date"
                        className={`${INLINE_CLS} w-32`}
                        defaultValue={r.effective_date ?? ""}
                        onChange={(e) =>
                          updateContract.mutate({
                            contractId: r.id,
                            body: { effective_date: e.target.value || undefined },
                          })
                        }
                      />
                    ),
                  },
                  {
                    key: "ai_actions",
                    header: "",
                    width: "70px",
                    render: (r) => (
                      <div className="flex items-center gap-1">
                        <button
                          className="text-text-muted hover:text-accent p-1 rounded transition-colors"
                          title="AI 분석"
                          onClick={() => analyzeContract.mutate(r.id)}
                        >
                          <Sparkles size={14} />
                        </button>
                        <button
                          className="text-text-muted hover:text-negative p-1 rounded transition-colors"
                          title="삭제"
                          onClick={() => {
                            if (confirm("이 계약서를 삭제하시겠습니까?")) {
                              deleteContract.mutate(r.id);
                            }
                          }}
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    ),
                  },
                ] as Column<(typeof contracts)[number]>[]}
                data={contracts}
                keyField="id"
              />
            )}
          </Card>
        </div>
      )}

      {/* ── 클로징 탭 ─────────────────────────────────── */}
      {activeTab === "closing" && (
        <div className="space-y-4">
          {/* 클로징 요약 KPI */}
          {closingSummary && closingSummary.total > 0 && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <KpiCard label="전체 항목" value={String(closingSummary.total)} />
              <KpiCard
                label="완료율"
                value={`${Math.round(closingSummary.completion_rate * 100)}%`}
                variant={closingSummary.completion_rate >= 0.8 ? "positive" : "default"}
              />
              <KpiCard
                label="진행 중"
                value={String(closingSummary.by_status["IN_PROGRESS"] ?? 0)}
              />
              <KpiCard
                label="대기"
                value={String(closingSummary.by_status["PENDING"] ?? 0)}
                variant={(closingSummary.by_status["PENDING"] ?? 0) > 0 ? "caution" : "default"}
              />
            </div>
          )}

          {/* 카테고리 필터 */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-medium text-text-muted">카테고리:</span>
            {[{ value: "ALL", label: "전체" }, ...CLOSING_CATEGORY_OPTIONS].map((opt) => (
              <button
                key={opt.value}
                type="button"
                className={`px-3 py-1 text-xs font-medium rounded-full transition-colors ${
                  closingCategoryFilter === opt.value
                    ? "bg-accent text-white"
                    : "bg-gray-100 text-text-secondary hover:bg-gray-200"
                }`}
                onClick={() => setClosingCategoryFilter(opt.value)}
              >
                {opt.label}
              </button>
            ))}
          </div>

          {/* 체크리스트 */}
          <Card
            title="클로징 체크리스트"
            headerBar
            padding="none"
            actions={
              <Button icon={Plus} onClick={() => setShowClosingModal(true)} variant="ghost">
                항목 추가
              </Button>
            }
          >
            {!closingItems?.length ? (
              <EmptyState
                icon={Flag}
                title="클로징 항목 없음"
                description="선행조건, 인허가 등 클로징 체크리스트를 추가하세요."
                actionLabel="항목 추가"
                onAction={() => setShowClosingModal(true)}
              />
            ) : !filteredClosingItems?.length ? (
              <div className="p-8 text-center text-text-muted text-sm">
                선택한 카테고리에 해당하는 항목이 없습니다.
              </div>
            ) : (
              <DataTable
                columns={[
                  {
                    key: "category",
                    header: "카테고리",
                    render: (r) => (
                      <Badge variant="neutral">
                        {CLOSING_CATEGORY_OPTIONS.find((o) => o.value === r.category)?.label ?? r.category}
                      </Badge>
                    ),
                  },
                  { key: "title", header: "항목" },
                  {
                    key: "status",
                    header: "상태",
                    render: (r) => (
                      <Select
                        options={CLOSING_CONDITION_STATUS_OPTIONS}
                        value={r.status}
                        onChange={(e) =>
                          updateClosingItem.mutate({
                            itemId: r.id,
                            body: { status: e.target.value as ClosingConditionStatus },
                          })
                        }
                        className="!py-0.5 !px-1.5 !text-xs"
                      />
                    ),
                  },
                  {
                    key: "responsible_party",
                    header: "담당",
                    render: (r) => (
                      <input
                        key={`${r.id}-resp-${r.responsible_party}`}
                        type="text"
                        className={`${INLINE_CLS} w-28`}
                        defaultValue={r.responsible_party ?? ""}
                        placeholder="담당자"
                        onBlur={(e) => {
                          const v = e.target.value || undefined;
                          if (v !== (r.responsible_party ?? undefined)) {
                            updateClosingItem.mutate({ itemId: r.id, body: { responsible_party: v } });
                          }
                        }}
                      />
                    ),
                  },
                  {
                    key: "due_date",
                    header: "기한",
                    render: (r) => (
                      <input
                        key={`${r.id}-due-${r.due_date}`}
                        type="date"
                        className={`${INLINE_CLS} w-32`}
                        defaultValue={r.due_date ?? ""}
                        onChange={(e) =>
                          updateClosingItem.mutate({ itemId: r.id, body: { due_date: e.target.value || undefined } })
                        }
                      />
                    ),
                  },
                  {
                    key: "completed_date",
                    header: "완료일",
                    render: (r) => (
                      <input
                        key={`${r.id}-comp-${r.completed_date}`}
                        type="date"
                        className={`${INLINE_CLS} w-32`}
                        defaultValue={r.completed_date ?? ""}
                        onChange={(e) =>
                          updateClosingItem.mutate({ itemId: r.id, body: { completed_date: e.target.value || undefined } })
                        }
                      />
                    ),
                  },
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
                            deleteClosingItem.mutate(r.id);
                          }
                        }}
                      >
                        <Trash2 size={14} />
                      </button>
                    ),
                  },
                ] as Column<(typeof closingItems)[number]>[]}
                data={filteredClosingItems ?? []}
                keyField="id"
              />
            )}
          </Card>
        </div>
      )}

      {/* ── PMI 탭 ──────────────────────────────────── */}
      {activeTab === "pmi" && (
        <div className="space-y-4">
          {/* KPI 요약 */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <KpiCard label="총 태스크" value={String(pmiSummary?.total ?? 0)} />
            <KpiCard
              label="완료율"
              value={`${Math.round((pmiSummary?.completion_rate ?? 0) * 100)}%`}
              variant={
                (pmiSummary?.completion_rate ?? 0) >= 0.8
                  ? "positive"
                  : (pmiSummary?.completion_rate ?? 0) >= 0.5
                    ? "caution"
                    : "default"
              }
            />
            <KpiCard
              label="진행 중"
              value={String(pmiSummary?.by_status?.IN_PROGRESS ?? 0)}
              variant="caution"
            />
            <KpiCard
              label="차단됨"
              value={String(pmiSummary?.by_status?.BLOCKED ?? 0)}
              variant={(pmiSummary?.by_status?.BLOCKED ?? 0) > 0 ? "negative" : "default"}
            />
          </div>

          {/* 카테고리 필터 칩 */}
          <div className="flex flex-wrap gap-2">
            <button
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${pmiCategoryFilter === "ALL" ? "bg-accent text-white" : "bg-gray-100 text-text-muted hover:bg-gray-200"}`}
              onClick={() => setPmiCategoryFilter("ALL")}
            >
              전체
            </button>
            {PMI_CATEGORY_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${pmiCategoryFilter === opt.value ? "bg-accent text-white" : "bg-gray-100 text-text-muted hover:bg-gray-200"}`}
                onClick={() => setPmiCategoryFilter(opt.value)}
              >
                {opt.label}
              </button>
            ))}
          </div>

          <Card
            title="PMI 태스크"
            headerBar
            actions={
              <Button size="sm" icon={Plus} onClick={() => setShowPMIModal(true)}>
                태스크 추가
              </Button>
            }
          >
            {!filteredPmiTasks?.length ? (
              <EmptyState icon={Flag} title="PMI 태스크 없음" description="인수 후 통합 태스크를 추가하세요." />
            ) : (
              <DataTable
                columns={[
                  { key: "title", header: "태스크명" },
                  {
                    key: "category",
                    header: "카테고리",
                    render: (t) => <Badge variant="info">{PMI_CATEGORY_OPTIONS.find((o) => o.value === t.category)?.label ?? t.category}</Badge>,
                  },
                  {
                    key: "priority",
                    header: "우선순위",
                    render: (t) => (
                      <select
                        className={INLINE_CLS}
                        value={t.priority}
                        onChange={(e) => updatePMITask.mutate({ taskId: t.id, body: { priority: e.target.value as PMIPriority } })}
                      >
                        {PMI_PRIORITY_OPTIONS.map((o) => (
                          <option key={o.value} value={o.value}>{o.label}</option>
                        ))}
                      </select>
                    ),
                  },
                  {
                    key: "status",
                    header: "상태",
                    render: (t) => (
                      <select
                        className={INLINE_CLS}
                        value={t.status}
                        onChange={(e) => updatePMITask.mutate({ taskId: t.id, body: { status: e.target.value as PMITaskStatus } })}
                      >
                        {PMI_STATUS_OPTIONS.map((o) => (
                          <option key={o.value} value={o.value}>{o.label}</option>
                        ))}
                      </select>
                    ),
                  },
                  { key: "assignee_name", header: "담당자", render: (t) => t.assignee_name ?? "-" },
                  { key: "due_date", header: "마감일", render: (t) => t.due_date ?? "-" },
                  {
                    key: "actions",
                    header: "",
                    render: (t) => (
                      <button
                        className="text-red-400 hover:text-red-600"
                        onClick={() => { if (confirm("삭제하시겠습니까?")) deletePMITask.mutate(t.id); }}
                      >
                        <Trash2 size={14} />
                      </button>
                    ),
                  },
                ] as Column<PMITask>[]}
                data={filteredPmiTasks ?? []}
                keyField="id"
              />
            )}
          </Card>
        </div>
      )}

      {/* ── Earnout 탭 ───────────────────────────────── */}
      {activeTab === "earnout" && (
        <div className="space-y-4">
          {/* KPI 요약 */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <KpiCard label="총 마일스톤" value={String(earnoutSummary?.total ?? 0)} />
            <KpiCard
              label="목표 합계"
              value={formatAmount(earnoutSummary?.total_target ?? 0)}
            />
            <KpiCard
              label="실적 합계"
              value={formatAmount(earnoutSummary?.total_actual ?? 0)}
              variant={
                (earnoutSummary?.total_actual ?? 0) >= (earnoutSummary?.total_target ?? 1)
                  ? "positive"
                  : "caution"
              }
            />
            <KpiCard
              label="지급 합계"
              value={formatAmount(earnoutSummary?.total_payment ?? 0)}
            />
          </div>

          <Card
            title="어닝아웃 마일스톤"
            headerBar
            actions={
              <Button size="sm" icon={Plus} onClick={() => setShowEarnoutModal(true)}>
                마일스톤 추가
              </Button>
            }
          >
            {!earnoutMilestones?.length ? (
              <EmptyState icon={DollarSign} title="어닝아웃 없음" description="어닝아웃 마일스톤을 추가하세요." />
            ) : (
              <DataTable
                columns={[
                  { key: "title", header: "마일스톤" },
                  {
                    key: "metric",
                    header: "지표",
                    render: (m) => EARNOUT_METRIC_OPTIONS.find((o) => o.value === m.metric)?.label ?? m.metric,
                  },
                  {
                    key: "target_value",
                    header: "목표",
                    render: (m) => `${formatAmount(m.target_value)} ${m.currency}`,
                  },
                  {
                    key: "actual_value",
                    header: "실적",
                    render: (m) => m.actual_value != null ? `${formatAmount(m.actual_value)} ${m.currency}` : "-",
                  },
                  {
                    key: "status",
                    header: "상태",
                    render: (m) => (
                      <select
                        className={INLINE_CLS}
                        value={m.status}
                        onChange={(e) => updateEarnout.mutate({ milestoneId: m.id, body: { status: e.target.value as EarnoutStatus } })}
                      >
                        {EARNOUT_STATUS_OPTIONS.map((o) => (
                          <option key={o.value} value={o.value}>{o.label}</option>
                        ))}
                      </select>
                    ),
                  },
                  {
                    key: "period",
                    header: "측정 기간",
                    render: (m) => m.measurement_start && m.measurement_end ? `${m.measurement_start} ~ ${m.measurement_end}` : "-",
                  },
                  {
                    key: "payment_amount",
                    header: "지급액",
                    render: (m) => m.payment_amount != null ? formatAmount(m.payment_amount) : "-",
                  },
                  {
                    key: "actions",
                    header: "",
                    render: (m) => (
                      <button
                        className="text-red-400 hover:text-red-600"
                        onClick={() => { if (confirm("삭제하시겠습니까?")) deleteEarnout.mutate(m.id); }}
                      >
                        <Trash2 size={14} />
                      </button>
                    ),
                  },
                ] as Column<(typeof earnoutMilestones)[number]>[]}
                data={earnoutMilestones ?? []}
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

      {/* ── Notes & Approvals 탭 ──────────────────────── */}
      {activeTab === "notes-approvals" && (
        <div className="space-y-6">
          {/* 승인 요약 KPI */}
          {approvalSummary && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <KpiCard label="전체 승인" value={approvalSummary.total} />
              <KpiCard label="대기 중" value={approvalSummary.pending} variant={approvalSummary.pending > 0 ? "warning" : undefined} />
              <KpiCard label="승인됨" value={approvalSummary.approved} variant="good" />
              <KpiCard label="거절됨" value={approvalSummary.rejected} variant={approvalSummary.rejected > 0 ? "bad" : undefined} />
            </div>
          )}

          {/* 승인 요청 목록 */}
          <Card
            title="승인 요청"
            headerBar
            actions={
              <Button size="sm" icon={Plus} onClick={() => setShowApprovalModal(true)}>
                승인 요청
              </Button>
            }
          >
            {!approvalsData?.items.length ? (
              <EmptyState
                icon={Shield}
                title="승인 요청 없음"
                description="단계 전환이나 계약 체결 시 승인 요청을 생성하세요."
              />
            ) : (
              <div className="space-y-3 p-1">
                {approvalsData.items.map((approval) => (
                  <div
                    key={approval.id}
                    className="border rounded-lg p-4 space-y-2 hover:border-accent/30 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-sm">{approval.title}</span>
                        <Badge
                          variant={
                            approval.status === "APPROVED"
                              ? "success"
                              : approval.status === "REJECTED"
                                ? "error"
                                : approval.status === "CANCELLED"
                                  ? "neutral"
                                  : "warning"
                          }
                          pill
                        >
                          {APPROVAL_STATUS_OPTIONS.find((o) => o.value === approval.status)?.label ?? approval.status}
                        </Badge>
                        <Badge variant="info" pill>
                          {APPROVAL_TYPE_OPTIONS.find((o) => o.value === approval.approval_type)?.label ?? approval.approval_type}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-1">
                        {approval.status === "PENDING" && (
                          <>
                            <Button
                              size="sm"
                              variant="ghost"
                              icon={Check}
                              onClick={() =>
                                decideApproval.mutate({
                                  approvalId: approval.id,
                                  body: { email: approval.approvers[0]?.email ?? "", decision: "APPROVED" },
                                })
                              }
                            >
                              승인
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              icon={X}
                              onClick={() =>
                                decideApproval.mutate({
                                  approvalId: approval.id,
                                  body: { email: approval.approvers[0]?.email ?? "", decision: "REJECTED" },
                                })
                              }
                            >
                              거절
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => cancelApproval.mutate(approval.id)}
                            >
                              취소
                            </Button>
                          </>
                        )}
                      </div>
                    </div>
                    {approval.description && (
                      <p className="text-xs text-text-muted">{approval.description}</p>
                    )}
                    <div className="flex items-center gap-4 text-xs text-text-muted">
                      <span>요청자: {approval.requester_email}</span>
                      {approval.deadline && <span>기한: {approval.deadline}</span>}
                      <span>{formatDate(approval.created_at)}</span>
                    </div>
                    {approval.approvers.length > 0 && (
                      <div className="flex flex-wrap gap-2 pt-1">
                        {approval.approvers.map((a, i) => (
                          <Badge
                            key={i}
                            variant={
                              a.status === "APPROVED"
                                ? "success"
                                : a.status === "REJECTED"
                                  ? "error"
                                  : "neutral"
                            }
                            pill
                          >
                            {a.email} ({a.role})
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* 노트/코멘트 */}
          <Card
            title="내부 노트"
            headerBar
            actions={
              <div className="flex items-center gap-2">
                <Select
                  options={[{ value: "ALL", label: "전체" }, ...NOTE_TYPE_OPTIONS]}
                  value={noteTypeFilter}
                  onChange={(e) => setNoteTypeFilter(e.target.value)}
                />
                <Button size="sm" icon={Plus} onClick={() => setShowNoteModal(true)}>
                  노트 추가
                </Button>
              </div>
            }
          >
            {!filteredNotes?.length ? (
              <EmptyState
                icon={MessageSquare}
                title="노트 없음"
                description="내부 의사결정, 질문, 메모를 기록하세요."
              />
            ) : (
              <div className="space-y-3 p-1">
                {filteredNotes.map((note) => (
                  <div
                    key={note.id}
                    className={`border rounded-lg p-4 space-y-2 ${note.is_pinned ? "border-accent/40 bg-accent/5" : ""}`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {note.is_pinned && <Pin size={14} className="text-accent" />}
                        <Badge variant="info" pill>
                          {NOTE_TYPE_OPTIONS.find((o) => o.value === note.note_type)?.label ?? note.note_type}
                        </Badge>
                        <span className="text-xs text-text-muted">{note.author_email}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <span className="text-xs text-text-muted">{formatDate(note.created_at)}</span>
                        <Button
                          size="sm"
                          variant="ghost"
                          icon={Trash2}
                          onClick={() => {
                            if (confirm("이 노트를 삭제하시겠습니까?")) deleteNote.mutate(note.id);
                          }}
                        />
                      </div>
                    </div>
                    <p className="text-sm whitespace-pre-wrap">{note.content}</p>
                    {note.mentions && note.mentions.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {note.mentions.map((m) => (
                          <Badge key={m} variant="neutral" pill>@{m}</Badge>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
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

      {/* 계약서 추가 모달 */}
      <Modal
        open={showContractModal}
        onClose={() => setShowContractModal(false)}
        title="계약서 추가"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createContract.mutate(contractForm, {
              onSuccess: () => {
                setShowContractModal(false);
                setContractForm({ title: "" });
              },
            });
          }}
          className="space-y-4"
        >
          <Input
            label="제목"
            required
            value={contractForm.title}
            onChange={(e) => setContractForm({ ...contractForm, title: e.target.value })}
            placeholder="예: 주식매매계약(SPA)"
          />
          <Select
            label="계약 유형"
            options={CONTRACT_TYPE_OPTIONS.filter((o) => o.value !== "")}
            value={contractForm.contract_type ?? "SPA"}
            onChange={(e) =>
              setContractForm({ ...contractForm, contract_type: (e.target.value || undefined) as ContractCreate["contract_type"] })
            }
          />
          <Input
            label="상대방"
            value={contractForm.counterparty_name ?? ""}
            onChange={(e) =>
              setContractForm({ ...contractForm, counterparty_name: e.target.value || undefined })
            }
            placeholder="계약 상대방"
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="효력일"
              type="date"
              value={contractForm.effective_date ?? ""}
              onChange={(e) =>
                setContractForm({ ...contractForm, effective_date: e.target.value || undefined })
              }
            />
            <Input
              label="만료일"
              type="date"
              value={contractForm.expiry_date ?? ""}
              onChange={(e) =>
                setContractForm({ ...contractForm, expiry_date: e.target.value || undefined })
              }
            />
          </div>
          <Input
            label="설명 / 비고"
            value={contractForm.description ?? ""}
            onChange={(e) =>
              setContractForm({ ...contractForm, description: e.target.value || undefined })
            }
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="ghost" type="button" onClick={() => setShowContractModal(false)}>
              취소
            </Button>
            <Button type="submit" loading={createContract.isPending}>
              등록
            </Button>
          </div>
        </form>
      </Modal>

      {/* 클로징 체크리스트 추가 모달 */}
      <Modal
        open={showClosingModal}
        onClose={() => setShowClosingModal(false)}
        title="클로징 체크리스트 항목 추가"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createClosingItem.mutate(closingForm, {
              onSuccess: () => {
                setShowClosingModal(false);
                setClosingForm({ category: "REGULATORY", title: "" });
              },
            });
          }}
          className="space-y-4"
        >
          <Select
            label="카테고리"
            options={CLOSING_CATEGORY_OPTIONS}
            value={closingForm.category}
            onChange={(e) =>
              setClosingForm({ ...closingForm, category: e.target.value as ClosingCategory })
            }
          />
          <Input
            label="항목명"
            required
            value={closingForm.title}
            onChange={(e) => setClosingForm({ ...closingForm, title: e.target.value })}
            placeholder="예: 공정거래위원회 기업결합신고"
          />
          <Input
            label="설명"
            value={closingForm.description ?? ""}
            onChange={(e) =>
              setClosingForm({ ...closingForm, description: e.target.value || undefined })
            }
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="담당자"
              value={closingForm.responsible_party ?? ""}
              onChange={(e) =>
                setClosingForm({ ...closingForm, responsible_party: e.target.value || undefined })
              }
            />
            <Input
              label="담당자 이메일"
              type="email"
              value={closingForm.responsible_email ?? ""}
              onChange={(e) =>
                setClosingForm({ ...closingForm, responsible_email: e.target.value || undefined })
              }
            />
          </div>
          <Input
            label="기한"
            type="date"
            value={closingForm.due_date ?? ""}
            onChange={(e) =>
              setClosingForm({ ...closingForm, due_date: e.target.value || undefined })
            }
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="ghost" type="button" onClick={() => setShowClosingModal(false)}>
              취소
            </Button>
            <Button type="submit" loading={createClosingItem.isPending}>
              추가
            </Button>
          </div>
        </form>
      </Modal>

      {/* PMI 태스크 추가 모달 */}
      <Modal
        open={showPMIModal}
        onClose={() => setShowPMIModal(false)}
        title="PMI 태스크 추가"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createPMITask.mutate(pmiForm, {
              onSuccess: () => {
                setShowPMIModal(false);
                setPmiForm({ category: "INTEGRATION_PLAN", title: "" });
              },
            });
          }}
          className="space-y-4"
        >
          <Select
            label="카테고리"
            options={PMI_CATEGORY_OPTIONS}
            value={pmiForm.category}
            onChange={(e) =>
              setPmiForm({ ...pmiForm, category: e.target.value as PMICategory })
            }
          />
          <Input
            label="태스크명"
            required
            value={pmiForm.title}
            onChange={(e) => setPmiForm({ ...pmiForm, title: e.target.value })}
            placeholder="예: IT 시스템 통합 계획 수립"
          />
          <Input
            label="설명"
            value={pmiForm.description ?? ""}
            onChange={(e) =>
              setPmiForm({ ...pmiForm, description: e.target.value || undefined })
            }
          />
          <Select
            label="우선순위"
            options={PMI_PRIORITY_OPTIONS}
            value={pmiForm.priority ?? "MEDIUM"}
            onChange={(e) =>
              setPmiForm({ ...pmiForm, priority: e.target.value as PMIPriority })
            }
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="담당자"
              value={pmiForm.assignee_name ?? ""}
              onChange={(e) =>
                setPmiForm({ ...pmiForm, assignee_name: e.target.value || undefined })
              }
            />
            <Input
              label="담당자 이메일"
              type="email"
              value={pmiForm.assignee_email ?? ""}
              onChange={(e) =>
                setPmiForm({ ...pmiForm, assignee_email: e.target.value || undefined })
              }
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="시작일"
              type="date"
              value={pmiForm.start_date ?? ""}
              onChange={(e) =>
                setPmiForm({ ...pmiForm, start_date: e.target.value || undefined })
              }
            />
            <Input
              label="마감일"
              type="date"
              value={pmiForm.due_date ?? ""}
              onChange={(e) =>
                setPmiForm({ ...pmiForm, due_date: e.target.value || undefined })
              }
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="ghost" type="button" onClick={() => setShowPMIModal(false)}>
              취소
            </Button>
            <Button type="submit" loading={createPMITask.isPending}>
              추가
            </Button>
          </div>
        </form>
      </Modal>

      {/* 어닝아웃 마일스톤 추가 모달 */}
      <Modal
        open={showEarnoutModal}
        onClose={() => setShowEarnoutModal(false)}
        title="어닝아웃 마일스톤 추가"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createEarnout.mutate(earnoutForm, {
              onSuccess: () => {
                setShowEarnoutModal(false);
                setEarnoutForm({ title: "", metric: "REVENUE", target_value: 0 });
              },
            });
          }}
          className="space-y-4"
        >
          <Input
            label="마일스톤명"
            required
            value={earnoutForm.title}
            onChange={(e) => setEarnoutForm({ ...earnoutForm, title: e.target.value })}
            placeholder="예: 2026년 매출 달성 조건"
          />
          <Input
            label="설명"
            value={earnoutForm.description ?? ""}
            onChange={(e) =>
              setEarnoutForm({ ...earnoutForm, description: e.target.value || undefined })
            }
          />
          <Select
            label="지표"
            options={EARNOUT_METRIC_OPTIONS}
            value={earnoutForm.metric}
            onChange={(e) =>
              setEarnoutForm({ ...earnoutForm, metric: e.target.value as EarnoutMetric })
            }
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="목표 금액"
              type="number"
              required
              value={earnoutForm.target_value.toString()}
              onChange={(e) =>
                setEarnoutForm({ ...earnoutForm, target_value: Number(e.target.value) || 0 })
              }
            />
            <Select
              label="통화"
              options={[
                { value: "KRW", label: "KRW (원)" },
                { value: "USD", label: "USD ($)" },
                { value: "EUR", label: "EUR (€)" },
              ]}
              value={earnoutForm.currency ?? "KRW"}
              onChange={(e) =>
                setEarnoutForm({ ...earnoutForm, currency: e.target.value })
              }
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="측정 시작일"
              type="date"
              value={earnoutForm.measurement_start ?? ""}
              onChange={(e) =>
                setEarnoutForm({ ...earnoutForm, measurement_start: e.target.value || undefined })
              }
            />
            <Input
              label="측정 종료일"
              type="date"
              value={earnoutForm.measurement_end ?? ""}
              onChange={(e) =>
                setEarnoutForm({ ...earnoutForm, measurement_end: e.target.value || undefined })
              }
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="ghost" type="button" onClick={() => setShowEarnoutModal(false)}>
              취소
            </Button>
            <Button type="submit" loading={createEarnout.isPending}>
              추가
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

      {/* 노트 추가 모달 */}
      <Modal
        open={showNoteModal}
        onClose={() => setShowNoteModal(false)}
        title="노트 추가"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createNote.mutate(noteForm, {
              onSuccess: () => {
                setShowNoteModal(false);
                setNoteForm({ content: "", note_type: "COMMENT" });
              },
            });
          }}
          className="space-y-4"
        >
          <Select
            label="유형"
            options={NOTE_TYPE_OPTIONS}
            value={noteForm.note_type ?? "COMMENT"}
            onChange={(e) =>
              setNoteForm({ ...noteForm, note_type: e.target.value as NoteType })
            }
          />
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-1">
              내용
            </label>
            <textarea
              required
              rows={4}
              className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm shadow-sm focus:border-accent focus:ring-2 focus:ring-accent/30"
              value={noteForm.content}
              onChange={(e) => setNoteForm({ ...noteForm, content: e.target.value })}
              placeholder="의사결정, 질문, 메모 등을 기록하세요..."
            />
          </div>
          <Input
            label="멘션 (이메일, 쉼표 구분)"
            value={noteForm.mentions?.join(", ") ?? ""}
            onChange={(e) =>
              setNoteForm({
                ...noteForm,
                mentions: e.target.value
                  ? e.target.value.split(",").map((s) => s.trim())
                  : undefined,
              })
            }
            placeholder="user@example.com, user2@example.com"
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="ghost" type="button" onClick={() => setShowNoteModal(false)}>
              취소
            </Button>
            <Button type="submit" loading={createNote.isPending} icon={Send}>
              작성
            </Button>
          </div>
        </form>
      </Modal>

      {/* 승인 요청 모달 */}
      <Modal
        open={showApprovalModal}
        onClose={() => setShowApprovalModal(false)}
        title="승인 요청 생성"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createApproval.mutate(approvalForm, {
              onSuccess: () => {
                setShowApprovalModal(false);
                setApprovalForm({
                  approval_type: "PHASE_ADVANCE",
                  title: "",
                  approvers: [{ email: "", role: "승인자" }],
                });
              },
            });
          }}
          className="space-y-4"
        >
          <Select
            label="승인 유형"
            options={APPROVAL_TYPE_OPTIONS}
            value={approvalForm.approval_type}
            onChange={(e) =>
              setApprovalForm({ ...approvalForm, approval_type: e.target.value as AppType })
            }
          />
          <Input
            label="제목"
            required
            value={approvalForm.title}
            onChange={(e) => setApprovalForm({ ...approvalForm, title: e.target.value })}
            placeholder="예: 마케팅 단계 전환 승인 요청"
          />
          <Input
            label="설명"
            value={approvalForm.description ?? ""}
            onChange={(e) =>
              setApprovalForm({ ...approvalForm, description: e.target.value || undefined })
            }
          />
          <Input
            label="승인자 이메일"
            required
            type="email"
            value={approvalForm.approvers[0]?.email ?? ""}
            onChange={(e) =>
              setApprovalForm({
                ...approvalForm,
                approvers: [{ email: e.target.value, role: "승인자" }],
              })
            }
            placeholder="approver@example.com"
          />
          <Input
            label="기한"
            type="date"
            value={approvalForm.deadline ?? ""}
            onChange={(e) =>
              setApprovalForm({ ...approvalForm, deadline: e.target.value || undefined })
            }
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="ghost" type="button" onClick={() => setShowApprovalModal(false)}>
              취소
            </Button>
            <Button type="submit" loading={createApproval.isPending}>
              요청
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
