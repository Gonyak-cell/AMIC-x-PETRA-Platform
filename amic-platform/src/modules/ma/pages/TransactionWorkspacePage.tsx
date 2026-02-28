import { useState, useMemo, useEffect } from "react";
import {
  useParams,
  useNavigate,
  useSearchParams,
  Navigate,
} from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
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
  Check,
  X,
  Send,
  BarChart2,
  BookOpen,
  Building2,
  FileSignature,
  ExternalLink,
  CircleCheck,
  CircleDashed,
  ChevronRight,
  ChevronDown,
  Handshake,
  Download,
  FileSpreadsheet,
} from "lucide-react";
import { cn } from "@/lib/cn";

import {
  useTransaction,
  useUpdateTransaction,
  useDeleteTransaction,
  usePhaseCompletion,
  useAdvancePhase,
  useAutoAdvanceNotification,
  useChangeStatus,
  useEngagements,
  useCreateEngagement,
  useWorkingGroup,
  useAddMember,
  useConflictCheck,
  useBuyers,
  useAddBuyer,
  useUpdateBuyer,
  useExportBuyerExcel,
  useTimeline,
  useGanttTimeline,
} from "@/modules/ma/hooks/useTransactions";
import type { EngagementCreate } from "@/modules/ma/types/engagement";
import type { WorkingGroupMemberCreate } from "@/modules/ma/types/engagement";
import type {
  BuyerCandidate,
  BuyerCandidateCreate,
  BuyerTier,
  DealRole,
} from "@/modules/ma/types/buyer";
import type {
  TransactionPhase,
  TransactionSide,
  Currency,
  DealStructure,
  InvestmentType,
  SaleProcess,
  ControlTransfer,
  ValuationBasis,
  CrossBorder,
} from "@/modules/ma/types/transaction";
import { useShortListOverview } from "@/modules/ma/hooks/useMarketingLogs";
import BuyerTierBadge from "@/modules/ma/components/buyers/BuyerTierBadge";
import DealRoleBadge from "@/modules/ma/components/buyers/DealRoleBadge";
import ConsortiumPanel from "@/modules/ma/components/buyers/ConsortiumPanel";
import ShortListOverview from "@/modules/ma/components/buyers/ShortListOverview";
import {
  useNdas,
  useNdaSummary,
  useCreateNda,
  useUpdateNda,
  useDeleteNda,
} from "@/modules/ma/hooks/useNdas";
import {
  useBids,
  useBidComparison,
  useCreateBid,
  useUpdateBid,
  useDeleteBid,
} from "@/modules/ma/hooks/useBids";
import {
  useDDChecklist,
  useDDChecklistSummary,
  useCreateDDChecklistItem,
  useUpdateDDChecklistItem,
  useDeleteDDChecklistItem,
} from "@/modules/ma/hooks/useDDChecklist";
import {
  useContracts,
  useContractSummary,
  useCreateContract,
  useUpdateContract,
  useDeleteContract,
  useAnalyzeContract,
} from "@/modules/ma/hooks/useContracts";
import {
  useClosingChecklist,
  useClosingSummary,
  useCreateClosingItem,
  useUpdateClosingItem,
  useDeleteClosingItem,
} from "@/modules/ma/hooks/useClosing";
import {
  usePMITasks,
  usePMISummary,
  useCreatePMITask,
  useUpdatePMITask,
  useDeletePMITask,
} from "@/modules/ma/hooks/usePMI";
import {
  useEarnoutMilestones,
  useEarnoutSummary,
  useCreateEarnout,
  useUpdateEarnout,
  useDeleteEarnout,
} from "@/modules/ma/hooks/useEarnout";
import {
  useNotes,
  useCreateNote,
  useDeleteNote,
} from "@/modules/ma/hooks/useNotes";
import {
  useApprovals,
  useApprovalSummary,
  useCreateApproval,
  useDecideApproval,
  useCancelApproval,
} from "@/modules/ma/hooks/useApprovals";
import {
  useRisks,
  useRiskSummary,
  useCreateRisk,
  useUpdateRisk,
  useDeleteRisk,
} from "@/modules/ma/hooks/useRisks";
import {
  useCompliance,
  useComplianceSummary,
  useCreateCompliance,
  useUpdateCompliance,
  useDeleteCompliance,
} from "@/modules/ma/hooks/useCompliance";
import { useLegalDocuments } from "@/modules/docs/hooks/useLegalDocuments";
import type { NoteCreate, NoteType } from "@/modules/ma/types/note";
import type {
  ApprovalCreate,
  ApprovalType as AppType,
} from "@/modules/ma/types/approval";
import type {
  RiskItemCreate,
  RiskCategory,
  RiskSeverity,
  RiskLikelihood,
  RiskStatus,
} from "@/modules/ma/types/risk";
import type {
  ComplianceItemCreate,
  ComplianceCategory as CompCat,
  ComplianceStatus,
} from "@/modules/ma/types/compliance";
import type { NDACreate, NdaStatus } from "@/modules/ma/types/nda";
import type {
  BidCreate,
  BidType,
  BidStatus as BidStatusType,
  ValuationMethod,
} from "@/modules/ma/types/bid";
import type {
  DDChecklistCreate,
  DDWorkstream,
  DDChecklistStatus as DDStatusType,
} from "@/modules/ma/types/dd_checklist";
import type {
  ContractCreate,
  ContractStatus,
  SignatureStatus as SigStatus,
} from "@/modules/ma/types/contract";
import type {
  ClosingChecklistCreate,
  ClosingCategory,
  ClosingConditionStatus,
} from "@/modules/ma/types/closing";
import type {
  PMITask,
  PMITaskCreate,
  PMICategory,
  PMITaskStatus,
  PMIPriority,
} from "@/modules/ma/types/pmi";
import type {
  EarnoutCreate,
  EarnoutStatus,
  EarnoutMetric,
} from "@/modules/ma/types/earnout";
import CompanyInfoCard from "@/modules/ma/components/overview/CompanyInfoCard";
import EngagementDocUpload from "@/modules/ma/components/overview/EngagementDocUpload";
import PipelineFlow from "@/modules/ma/components/PipelineFlow";
import PhaseActionPanel from "@/modules/ma/components/PhaseActionPanel";
import {
  PHASE_CONFIG,
  PHASE_TAB_MAP,
  PHASE_VISIBLE_TABS,
  ENGAGEMENT_TYPE_OPTIONS,
  WORKING_GROUP_ROLE_OPTIONS,
  BUYER_TYPE_OPTIONS,
  BUYER_STATUS_OPTIONS,
  BUYER_TIER_OPTIONS,
  DEAL_ROLE_OPTIONS,
  NDA_TYPE_OPTIONS,
  NDA_STATUS_OPTIONS,
  BID_TYPE_OPTIONS,
  BID_STATUS_OPTIONS,
  VALUATION_METHOD_OPTIONS,
  DD_WORKSTREAM_OPTIONS,
  DD_WORKSTREAM_HIERARCHY,
  DD_SUB_LABELS,
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
  RISK_CATEGORY_OPTIONS,
  RISK_SEVERITY_OPTIONS,
  RISK_LIKELIHOOD_OPTIONS,
  RISK_STATUS_OPTIONS,
  COMPLIANCE_CATEGORY_OPTIONS,
  COMPLIANCE_STATUS_OPTIONS,
  TRANSACTION_SIDE_OPTIONS,
  DEAL_STRUCTURE_OPTIONS,
  INVESTMENT_TYPE_OPTIONS,
  CURRENCY_OPTIONS,
  SALE_PROCESS_OPTIONS,
  CONTROL_TRANSFER_OPTIONS,
  VALUATION_BASIS_OPTIONS,
  CROSS_BORDER_OPTIONS,
  TARGET_BUYER_TYPE_OPTIONS,
  TEAM_MEMBERS,
} from "@/modules/ma/constants";

import FileUploadZone from "@/modules/ma/components/FileUploadZone";
import ClientPortalDashboard from "@/modules/ma/components/ClientPortalDashboard";
import { GanttTimeline } from "@/modules/ma/components/GanttTimeline";
import MeetingLogsTab from "@/modules/ma/components/meetings/MeetingLogsTab";
import LegalDocumentsTab from "@/modules/docs/components/LegalDocumentsTab";
import DDReportSection from "@/modules/ma/components/DDReportSection";
import VdrTab from "@/modules/ma/components/vdr/VdrTab";
import RFIPanel from "@/modules/ma/components/rfi/RFIPanel";
import PermitAnalysisPanel from "@/modules/ma/components/PermitAnalysisPanel";
import RalphLoopProgress from "@/modules/docs/components/RalphLoopProgress";
import QualityDashboard from "@/modules/docs/components/QualityDashboard";
import {
  useRalphSessions,
  useCreateRalphSession,
} from "@/modules/docs/hooks/useRalphLoop";
import type { RalphSession } from "@/modules/docs/hooks/useRalphLoop";
import {
  useMarketingMaterials,
  useCreateMarketingMaterial,
  useDeleteMarketingMaterial,
  useUpdateDistribution,
  getDownloadUrl,
} from "@/modules/ma/hooks/useMarketingMaterials";
import type { MarketingMaterial } from "@/modules/ma/types/marketing_material";
import { MARKETING_STATUS_LABELS } from "@/modules/ma/types/marketing_material";
import {
  useFinancialModels,
  useCreateFinancialModel,
  useDeleteFinancialModel,
  getFMDownloadUrl,
} from "@/modules/ma/hooks/useFinancialModels";
import type { FinancialModel } from "@/modules/ma/types/financial_model";
import {
  FM_MODEL_TYPE_LABELS,
  FM_STATUS_LABELS,
  FM_STATUS_COLORS,
} from "@/modules/ma/types/financial_model";
import FMChecklistReview from "@/modules/ma/components/fm/FMChecklistReview";
import { ContractNegotiationWorkspace } from "@/modules/ma/components/negotiation/ContractNegotiationWorkspace";
import SIMappingPanel from "@/modules/ma/components/si-mapping/SIMappingPanel";

import {
  Badge,
  Button,
  Card,
  DataTable,
  EmptyState,
  InlineSelect,
  InlineCombobox,
  INLINE_INPUT_CLS,
  Input,
  KpiCard,
  Modal,
  PageHero,
  Select,
  Spinner,
  Tabs,
} from "@/components/ui";
import type { Column, TabItem } from "@/components/ui";
import heroImg from "@/assets/images/heroes/hero-arch-dark-round.jpg";

// ── 상수/유틸 ──────────────────────────────────────────
const VALID_PHASES = PHASE_CONFIG.map((p) => p.phase);

const STATUS_VARIANT: Record<
  string,
  "success" | "warning" | "error" | "info" | "neutral"
> = {
  DRAFT: "neutral",
  ACTIVE: "success",
  ON_HOLD: "warning",
  COMPLETED: "info",
  TERMINATED: "error",
};

const BUYER_STATUS_VARIANT: Record<
  string,
  "success" | "warning" | "error" | "info" | "neutral"
> = {
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
  if (amount >= 1_0000_0000)
    return `${(amount / 1_0000_0000).toLocaleString()}억`;
  return amount.toLocaleString();
}

// INLINE_INPUT_CLS는 @/components/ui에서 import

// PipelineFlow + PhaseActionPanel imported from components

// ── 메인 컴포넌트 ──────────────────────────────────────
export default function TransactionWorkspacePage() {
  const { txnId, "*": splat } = useParams<{ txnId: string; "*": string }>();
  const navigate = useNavigate();
  const { canWrite, isClient } = useAuth();
  const id = txnId ?? "";

  // URL 기반 탭 결정
  const VALID_TABS = [
    "engagement",
    "buyers",
    "timeline",
    "marketing-materials",
    "models",
    "ndas",
    "vdr",
    "bids",
    "dd-checklist",
    "contracts",
    "closing",
    "pmi",
    "earnout",
    "risks",
    "compliance",
    "notes-approvals",
    "marketing-logs",
    "negotiation-logs",
    "rfi",
  ];
  const activeTab = VALID_TABS.includes(splat ?? "") ? splat! : "overview";

  // 파이프라인에서 클릭한 단계 (URL search param 기반, 리마운트 안전)
  const [searchParams, setSearchParams] = useSearchParams();
  const viewedPhase: TransactionPhase | null = (() => {
    const raw = searchParams.get("viewPhase");
    return raw && VALID_PHASES.includes(raw as TransactionPhase)
      ? (raw as TransactionPhase)
      : null;
  })();

  // 매수자 필터 (buyers 탭에서 클릭 시 전달)
  const buyerIdParam = searchParams.get("buyerId") || undefined;

  // DD/Checklist 서브탭 (체크리스트 vs DD 리포트)
  const [ddSubTab, setDdSubTab] = useState<"checklist" | "reports">(
    "checklist",
  );

  // 계약/SPA 서브탭 (계약 vs 법률 문서)
  const [contractSubTab, setContractSubTab] = useState<
    "negotiation-workspace" | "contracts" | "legal-docs"
  >("negotiation-workspace");

  // 매수자 서브탭 (Long List vs Short List)
  const [buyerSubTab, setBuyerSubTab] = useState<"long-list" | "short-list">(
    "long-list",
  );
  const [showSIMappingModal, setShowSIMappingModal] = useState(false);

  // URL 호환성: 삭제된 탭 → 통합 탭으로 리다이렉트 (viewPhase 보존)
  useEffect(() => {
    const qs = viewedPhase ? `?viewPhase=${viewedPhase}` : "";
    if (splat === "ldd") {
      navigate(`/ma/transactions/${id}/dd-checklist${qs}`, { replace: true });
      setDdSubTab("reports");
    }
    if (splat === "legal_docs") {
      navigate(`/ma/transactions/${id}/contracts${qs}`, { replace: true });
      setContractSubTab("legal-docs");
    }
  }, [splat, id, navigate, viewedPhase]);

  // 데이터 로드 — Phase 1
  const { data: txn, isLoading } = useTransaction(id);
  const { data: phaseStatus } = usePhaseCompletion(id);
  useAutoAdvanceNotification(id);
  const { data: engagements } = useEngagements(id);
  useWorkingGroup(id);
  const { data: conflicts } = useConflictCheck(id);
  const { data: buyers } = useBuyers(id);
  const { data: timeline } = useTimeline(id);
  const { data: ganttData } = useGanttTimeline(id);

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

  // 데이터 로드 — 마케팅 자료
  const { data: marketingMaterials } = useMarketingMaterials(id);
  const createMarketingMaterial = useCreateMarketingMaterial(id);
  const deleteMarketingMaterial = useDeleteMarketingMaterial(id);
  useUpdateDistribution(id); // 향후 배포 관리 UI에서 사용 예정

  // 데이터 로드 — 재무모델
  const { data: financialModels } = useFinancialModels(id);
  const createFinancialModel = useCreateFinancialModel(id);
  const deleteFinancialModel = useDeleteFinancialModel(id);
  const [selectedFMId, setSelectedFMId] = useState<string | null>(null);

  // 데이터 로드 — Phase 5B
  const { data: risks } = useRisks(id);
  const { data: riskSummary } = useRiskSummary(id);
  const { data: complianceItems } = useCompliance(id);
  const { data: complianceSummary } = useComplianceSummary(id);

  // 데이터 로드 — Legal Documents (MOU 연결 상태 확인용)
  const { data: legalDocs } = useLegalDocuments(id);

  // 데이터 로드 — Ralph Loop (AI Quality)
  const { data: ralphSessions } = useRalphSessions(id);
  const createRalphSession = useCreateRalphSession(id);
  const [selectedRalphSession, setSelectedRalphSession] =
    useState<RalphSession | null>(null);

  // Mutations — Transaction 기본 정보
  const updateTxn = useUpdateTransaction(id);
  const deleteTxn = useDeleteTransaction();

  // Mutations — Phase 1
  const advancePhase = useAdvancePhase(id);
  const changeStatus = useChangeStatus(id);
  const createEngagement = useCreateEngagement(id);
  const addMember = useAddMember(id);
  const addBuyer = useAddBuyer(id);
  const updateBuyer = useUpdateBuyer(id);
  const exportExcel = useExportBuyerExcel(id);
  const { data: shortListOverview } = useShortListOverview(id);

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

  // Mutations — Phase 5B
  const createRisk = useCreateRisk(id);
  const updateRisk = useUpdateRisk(id);
  const deleteRisk = useDeleteRisk(id);
  const createCompliance = useCreateCompliance(id);
  const updateCompliance = useUpdateCompliance(id);
  const deleteCompliance = useDeleteCompliance(id);

  // URL 기반 탭 전환 (viewPhase search param 유지하여 탭 필터링 보존)
  const handleTabChange = (tab: string) => {
    const qs = viewedPhase ? `?viewPhase=${viewedPhase}` : "";
    if (tab === "overview") {
      navigate(`/ma/transactions/${id}${qs}`);
    } else {
      navigate(`/ma/transactions/${id}/${tab}${qs}`);
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

  // UI State — Phase 5B
  const [showRiskModal, setShowRiskModal] = useState(false);
  const [showComplianceModal, setShowComplianceModal] = useState(false);

  // Form state — Phase 1
  const [engForm, setEngForm] = useState<EngagementCreate>({
    type: "EXCLUSIVE",
  });
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
    workstream: "FDD_FINANCIAL_STATEMENTS" as DDWorkstream,
    title: "",
  });

  // Form state — Phase 3
  const [contractForm, setContractForm] = useState<ContractCreate>({
    title: "",
  });
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

  // Form state — Phase 5B
  const [riskForm, setRiskForm] = useState<RiskItemCreate>({
    category: "REGULATORY" as RiskCategory,
    title: "",
    severity: "MEDIUM" as RiskSeverity,
    likelihood: "MEDIUM" as RiskLikelihood,
  });
  const [complianceForm, setComplianceForm] = useState<ComplianceItemCreate>({
    category: "ANTITRUST" as CompCat,
    requirement: "",
  });

  // Note type 필터
  const [noteTypeFilter, setNoteTypeFilter] = useState<string>("ALL");
  const filteredNotes =
    noteTypeFilter === "ALL"
      ? notesData?.items
      : notesData?.items.filter((n) => n.note_type === noteTypeFilter);

  // DD 워크스트림 필터 (2단 계층: 그룹 → 서브)
  const [ddGroupFilter, setDdGroupFilter] = useState<string>("ALL");
  const [ddSubFilter, setDdSubFilter] = useState<string | null>(null);
  const activeGroup = DD_WORKSTREAM_HIERARCHY.find(
    (g) => g.key === ddGroupFilter,
  );
  const filteredDDItems = useMemo(() => {
    if (!ddItems) return [];
    if (ddGroupFilter === "ALL") return ddItems;
    if (!activeGroup) return ddItems;
    if (ddSubFilter)
      return ddItems.filter((item) => item.workstream === ddSubFilter);
    return ddItems.filter((item) =>
      activeGroup.children.includes(item.workstream),
    );
  }, [ddItems, ddGroupFilter, ddSubFilter, activeGroup]);

  // 서비스 연동 아코디언 상태
  const PHASE_TO_SVC_GROUP: Record<string, string> = {
    ENGAGEMENT: "PREPARATION",
    PREPARATION: "PREPARATION",
    MARKETING: "MARKETING",
    BIDDING_DD: "BIDDING_DD",
    NEGOTIATION: "NEGOTIATION",
    CLOSING: "CLOSING",
    POST_CLOSING: "CLOSING",
  };
  const [openSvcGroups, setOpenSvcGroups] = useState<Set<string>>(
    () => new Set(["PREPARATION"]),
  );
  useEffect(() => {
    if (txn?.phase) {
      const g = PHASE_TO_SVC_GROUP[txn.phase] ?? "PREPARATION";
      setOpenSvcGroups(new Set([g]));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [txn?.phase]);
  const toggleSvcGroup = (key: string) =>
    setOpenSvcGroups((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });

  // Closing 카테고리 필터
  const [closingCategoryFilter, setClosingCategoryFilter] =
    useState<string>("ALL");
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

  // Risk 카테고리 필터
  const [riskCategoryFilter, setRiskCategoryFilter] = useState<string>("ALL");
  const filteredRisks =
    riskCategoryFilter === "ALL"
      ? risks
      : risks?.filter((r) => r.category === riskCategoryFilter);

  // Compliance 카테고리 필터
  const [complianceCategoryFilter, setComplianceCategoryFilter] =
    useState<string>("ALL");
  const filteredComplianceItems =
    complianceCategoryFilter === "ALL"
      ? complianceItems
      : complianceItems?.filter((c) => c.category === complianceCategoryFilter);

  const allTabs: TabItem[] = [
    { id: "overview", label: "Overview" },
    { id: "engagement", label: "수임", badge: engagements?.length },
    { id: "buyers", label: "매수자", badge: buyers?.length },
    { id: "timeline", label: "타임라인", badge: timeline?.total },
    {
      id: "marketing-materials",
      label: "마케팅 자료",
      badge: marketingMaterials?.length,
    },
    { id: "models", label: "재무모델", badge: financialModels?.length },
    { id: "ndas", label: "NDA", badge: ndas?.length },
    { id: "bids", label: "입찰", badge: bids?.length },
    { id: "dd-checklist", label: "DD/Checklist", badge: ddItems?.length },
    { id: "contracts", label: "계약/SPA", badge: contracts?.length },
    { id: "closing", label: "Closing", badge: closingItems?.length },
    { id: "pmi", label: "PMI", badge: pmiTasks?.length },
    { id: "earnout", label: "어닝아웃", badge: earnoutMilestones?.length },
    { id: "marketing-logs", label: "마케팅 로그" },
    { id: "negotiation-logs", label: "협상 로그" },
    { id: "vdr", label: "VDR" },
    { id: "rfi", label: "RFI" },
  ];

  // 탭 필터링: viewedPhase가 있으면 해당 단계 탭, 없으면 현재 단계 탭
  const effectivePhase = (viewedPhase ?? txn?.phase) as
    | TransactionPhase
    | undefined;
  const visibleTabIds = effectivePhase
    ? PHASE_VISIBLE_TABS[effectivePhase]
    : allTabs.map((t) => t.id);
  const tabs = isClient
    ? [{ id: "overview", label: "대시보드" }]
    : allTabs.filter((t) => visibleTabIds.includes(t.id));

  // 사이드바 Tools에서만 접근하는 탭 (파이프라인 탭 바에는 미표시)
  const SIDEBAR_ONLY_TABS = [
    "risks",
    "compliance",
    "notes-approvals",
    "timeline",
  ];

  // activeTab이 현재 보이는 탭에 없으면 PHASE_TAB_MAP 폴백 (useEffect 없이 렌더 시점 계산)
  const safeActiveTab =
    activeTab === "overview" ||
    visibleTabIds.includes(activeTab) ||
    SIDEBAR_ONLY_TABS.includes(activeTab)
      ? activeTab
      : viewedPhase
        ? (PHASE_TAB_MAP[viewedPhase] ?? "overview")
        : "overview";

  if (!txnId) return <Navigate to="/ma/transactions" replace />;
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
        backgroundImage={heroImg}
        backgroundOpacity={0.18}
        compact
        actions={
          <div className="flex flex-wrap gap-2">
            <Button
              variant="ghost"
              icon={ArrowLeft}
              onClick={() => navigate("/ma/transactions")}
              className="!text-white/80 hover:!text-white hover:!bg-white/10"
            >
              목록
            </Button>
            {canWrite() && txn.status === "DRAFT" && (
              <Button
                icon={Play}
                onClick={() => changeStatus.mutate({ to_status: "ACTIVE" })}
                loading={changeStatus.isPending}
              >
                시작
              </Button>
            )}
            {canWrite() && txn.status === "ACTIVE" && (
              <>
                {phaseStatus?.previous_phase && (
                  <Button
                    variant="ghost"
                    icon={ArrowLeft}
                    onClick={() =>
                      advancePhase.mutate({
                        to_phase: phaseStatus.previous_phase!,
                      })
                    }
                    loading={advancePhase.isPending}
                    className="!text-white/80 hover:!text-white hover:!bg-white/10"
                  >
                    {PHASE_CONFIG.find(
                      (p) => p.phase === phaseStatus.previous_phase,
                    )?.label ?? "이전"}{" "}
                    단계로
                  </Button>
                )}
                {phaseStatus?.can_advance && phaseStatus.next_phase && (
                  <div className="flex items-center gap-2">
                    {phaseStatus.has_warnings && (
                      <span className="flex items-center gap-1 text-xs text-caution">
                        <AlertTriangle size={12} />
                        권장 항목 미완료
                      </span>
                    )}
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
                  </div>
                )}
                <Button
                  variant="ghost"
                  icon={Pause}
                  onClick={() => changeStatus.mutate({ to_status: "ON_HOLD" })}
                  className="!text-white/80 hover:!text-white hover:!bg-white/10"
                >
                  보류
                </Button>
              </>
            )}
            {canWrite() && txn.status === "ON_HOLD" && (
              <Button
                icon={Play}
                onClick={() => changeStatus.mutate({ to_status: "ACTIVE" })}
              >
                재개
              </Button>
            )}
            {canWrite() && !isClient && (
              <Button
                variant="ghost"
                icon={Trash2}
                onClick={() => {
                  if (confirm("이 거래를 삭제하시겠습니까?")) {
                    deleteTxn.mutate(id, {
                      onSuccess: () => navigate("/ma/transactions"),
                    });
                  }
                }}
                loading={deleteTxn.isPending}
                className="!text-white/60 hover:!text-negative hover:!bg-white/10"
              >
                삭제
              </Button>
            )}
          </div>
        }
      />

      {/* Pipeline Flow */}
      <Card padding="md">
        <div className="flex items-center gap-3 mb-3">
          <Badge variant={STATUS_VARIANT[txn.status]}>{txn.status}</Badge>
          <span className="text-sm text-text-muted">
            현재: <strong>{phaseLabel}</strong>
          </span>
        </div>
        <PipelineFlow
          currentPhase={txn.phase}
          onPhaseClick={(phase) => {
            const currentIdx = PHASE_CONFIG.findIndex(
              (p) => p.phase === txn.phase,
            );
            const clickedIdx = PHASE_CONFIG.findIndex((p) => p.phase === phase);
            if (clickedIdx > currentIdx) return; // 미래 단계 무시
            if (phase === viewedPhase) return; // 같은 단계 재클릭 무시
            const defaultTab = PHASE_TAB_MAP[phase];
            const tabPath = defaultTab === "overview" ? "" : `/${defaultTab}`;
            navigate(`/ma/transactions/${id}${tabPath}?viewPhase=${phase}`);
          }}
        />
      </Card>

      {/* Phase Action Panel */}
      <PhaseActionPanel txnId={id} />

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
        activeTab={safeActiveTab}
        onTabChange={handleTabChange}
        variant="underline"
      />

      {/* ── Overview 탭 ───────────────────────────────── */}
      {safeActiveTab === "overview" && isClient && (
        <ClientPortalDashboard txnId={id} />
      )}
      {safeActiveTab === "overview" && !isClient && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* 거래 정보 — 2-Column */}
          <Card title="거래 정보" headerBar className="lg:col-span-2">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-0 p-1 md:items-start">
              {/* ── 좌측 열: 기본 딜 정보 ── */}
              <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-3 text-sm items-center">
                <dt className="text-text-muted">거래명</dt>
                <dd>
                  <input
                    key={`name-${txn.updated_at}`}
                    type="text"
                    className={cn(INLINE_INPUT_CLS, "w-64")}
                    defaultValue={txn.name}
                    onBlur={(e) => {
                      const v = e.target.value.trim();
                      if (v && v !== txn.name) updateTxn.mutate({ name: v });
                    }}
                    disabled={!canWrite()}
                  />
                </dd>
                <dt className="text-text-muted">코드네임</dt>
                <dd>
                  <input
                    key={`codename-${txn.updated_at}`}
                    type="text"
                    className={cn(INLINE_INPUT_CLS, "w-40 font-mono")}
                    defaultValue={txn.code_name}
                    onBlur={(e) => {
                      const v = e.target.value.trim();
                      if (v && v !== txn.code_name)
                        updateTxn.mutate({ code_name: v });
                    }}
                    disabled={!canWrite()}
                  />
                </dd>
                <dt className="text-text-muted">대상기업</dt>
                <dd>
                  <input
                    key={`target-${txn.updated_at}`}
                    type="text"
                    className={cn(INLINE_INPUT_CLS, "w-48")}
                    defaultValue={txn.target_company_name}
                    onBlur={(e) => {
                      const v = e.target.value.trim();
                      if (v && v !== txn.target_company_name)
                        updateTxn.mutate({ target_company_name: v });
                    }}
                    disabled={!canWrite()}
                  />
                </dd>
                <dt className="text-text-muted">클라이언트</dt>
                <dd>
                  <input
                    key={`client-${txn.updated_at}`}
                    type="text"
                    className={cn(INLINE_INPUT_CLS, "w-48")}
                    defaultValue={txn.client_name}
                    onBlur={(e) => {
                      const v = e.target.value.trim();
                      if (v && v !== txn.client_name)
                        updateTxn.mutate({ client_name: v });
                    }}
                    disabled={!canWrite()}
                  />
                </dd>
                <dt className="text-text-muted">유형</dt>
                <dd>
                  <InlineSelect
                    options={TRANSACTION_SIDE_OPTIONS.filter(
                      (o) => o.value !== "",
                    )}
                    value={txn.side}
                    onChange={(v) =>
                      updateTxn.mutate({ side: v as TransactionSide })
                    }
                    disabled={!canWrite()}
                  />
                </dd>
                <dt className="text-text-muted">딜 구조</dt>
                <dd>
                  <InlineSelect
                    options={DEAL_STRUCTURE_OPTIONS}
                    value={txn.deal_structure ?? ""}
                    onChange={(v) =>
                      updateTxn.mutate({
                        deal_structure: (v || null) as DealStructure | null,
                      })
                    }
                    disabled={!canWrite()}
                  />
                </dd>
                <dt className="text-text-muted">투자 유형</dt>
                <dd>
                  <InlineSelect
                    options={INVESTMENT_TYPE_OPTIONS}
                    value={txn.investment_type ?? ""}
                    onChange={(v) =>
                      updateTxn.mutate({
                        investment_type: (v || null) as InvestmentType | null,
                      })
                    }
                    disabled={!canWrite()}
                  />
                </dd>
                <dt className="text-text-muted">산업</dt>
                <dd>
                  <input
                    key={`industry-${txn.updated_at}`}
                    type="text"
                    className={cn(INLINE_INPUT_CLS, "w-40")}
                    defaultValue={txn.industry ?? ""}
                    onBlur={(e) => {
                      const v = e.target.value.trim();
                      if (v !== (txn.industry ?? ""))
                        updateTxn.mutate({ industry: v || null });
                    }}
                    disabled={!canWrite()}
                    placeholder="-"
                  />
                </dd>
                <dt className="text-text-muted">예상 금액</dt>
                <dd className="flex items-center gap-1">
                  <input
                    key={`deal-val-${txn.updated_at}`}
                    type="number"
                    className={cn(
                      INLINE_INPUT_CLS,
                      "w-32 text-right font-mono",
                    )}
                    defaultValue={txn.estimated_deal_value ?? ""}
                    onBlur={(e) => {
                      const v = e.target.value ? Number(e.target.value) : null;
                      if (v !== txn.estimated_deal_value)
                        updateTxn.mutate({ estimated_deal_value: v });
                    }}
                    disabled={!canWrite()}
                    placeholder="-"
                  />
                  <InlineSelect
                    options={CURRENCY_OPTIONS}
                    value={txn.currency}
                    onChange={(v) =>
                      updateTxn.mutate({ currency: v as Currency })
                    }
                    disabled={!canWrite()}
                  />
                </dd>
                <dt className="text-text-muted">목표 종결일</dt>
                <dd>
                  <input
                    type="date"
                    className={cn(INLINE_INPUT_CLS, "w-36")}
                    value={txn.target_close_date ?? ""}
                    onChange={(e) =>
                      updateTxn.mutate({
                        target_close_date: e.target.value || null,
                      })
                    }
                    disabled={!canWrite()}
                  />
                </dd>
                <dt className="text-text-muted">리드 어드바이저</dt>
                <dd>
                  <InlineCombobox
                    options={TEAM_MEMBERS.map((m) => ({
                      value: m.email,
                      label: `${m.name} (${m.title})`,
                      description: m.email,
                    }))}
                    value={txn.lead_advisor_email}
                    onChange={(v) => {
                      if (v && v !== txn.lead_advisor_email)
                        updateTxn.mutate({ lead_advisor_email: v });
                    }}
                    disabled={!canWrite()}
                    placeholder="담당자 검색..."
                    clearable={false}
                  />
                </dd>
                <dt className="text-text-muted">딜 캡틴</dt>
                <dd>
                  <InlineCombobox
                    options={TEAM_MEMBERS.map((m) => ({
                      value: m.email,
                      label: `${m.name} (${m.title})`,
                      description: m.email,
                    }))}
                    value={txn.deal_captain_email ?? ""}
                    onChange={(v) => {
                      if (v !== (txn.deal_captain_email ?? ""))
                        updateTxn.mutate({ deal_captain_email: v || null });
                    }}
                    disabled={!canWrite()}
                    placeholder="담당자 검색..."
                  />
                </dd>
              </dl>

              {/* ── 우측 열: 딜 상세 구조 ── */}
              <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-3 text-sm items-center">
                <dt className="text-text-muted">매각 방식</dt>
                <dd>
                  <InlineSelect
                    options={SALE_PROCESS_OPTIONS}
                    value={txn.sale_process ?? ""}
                    onChange={(v) =>
                      updateTxn.mutate({
                        sale_process: (v || null) as SaleProcess | null,
                      })
                    }
                    disabled={!canWrite()}
                  />
                </dd>
                <dt className="text-text-muted">경영권</dt>
                <dd>
                  <InlineSelect
                    options={CONTROL_TRANSFER_OPTIONS}
                    value={txn.control_transfer ?? ""}
                    onChange={(v) =>
                      updateTxn.mutate({
                        control_transfer: (v || null) as ControlTransfer | null,
                      })
                    }
                    disabled={!canWrite()}
                  />
                </dd>
                <dt className="text-text-muted">대상 지분율</dt>
                <dd className="flex items-center gap-1">
                  <input
                    key={`stake-${txn.updated_at}`}
                    type="number"
                    className={cn(
                      INLINE_INPUT_CLS,
                      "w-20 text-right font-mono",
                    )}
                    defaultValue={txn.target_stake ?? ""}
                    min={0}
                    max={100}
                    step={0.01}
                    onBlur={(e) => {
                      const v = e.target.value ? Number(e.target.value) : null;
                      if (v !== txn.target_stake)
                        updateTxn.mutate({ target_stake: v });
                    }}
                    disabled={!canWrite()}
                    placeholder="-"
                  />
                  <span className="text-xs text-text-muted">%</span>
                </dd>
                <dt className="text-text-muted">신주/구주</dt>
                <dd className="flex items-center gap-1">
                  <input
                    key={`new-share-${txn.updated_at}`}
                    type="number"
                    className={cn(
                      INLINE_INPUT_CLS,
                      "w-16 text-right font-mono",
                    )}
                    defaultValue={txn.new_share_ratio ?? ""}
                    min={0}
                    max={100}
                    step={0.01}
                    onBlur={(e) => {
                      const v = e.target.value ? Number(e.target.value) : null;
                      if (v !== txn.new_share_ratio)
                        updateTxn.mutate({ new_share_ratio: v });
                    }}
                    disabled={!canWrite()}
                    placeholder="신주"
                  />
                  <span className="text-xs text-text-muted">/</span>
                  <input
                    key={`old-share-${txn.updated_at}`}
                    type="number"
                    className={cn(
                      INLINE_INPUT_CLS,
                      "w-16 text-right font-mono",
                    )}
                    defaultValue={txn.old_share_ratio ?? ""}
                    min={0}
                    max={100}
                    step={0.01}
                    onBlur={(e) => {
                      const v = e.target.value ? Number(e.target.value) : null;
                      if (v !== txn.old_share_ratio)
                        updateTxn.mutate({ old_share_ratio: v });
                    }}
                    disabled={!canWrite()}
                    placeholder="구주"
                  />
                  <span className="text-xs text-text-muted">%</span>
                </dd>
                <dt className="text-text-muted">밸류에이션 기준</dt>
                <dd>
                  <InlineSelect
                    options={VALUATION_BASIS_OPTIONS}
                    value={txn.valuation_basis ?? ""}
                    onChange={(v) =>
                      updateTxn.mutate({
                        valuation_basis: (v || null) as ValuationBasis | null,
                      })
                    }
                    disabled={!canWrite()}
                  />
                </dd>
                <dt className="text-text-muted">Cross-border</dt>
                <dd>
                  <InlineSelect
                    options={CROSS_BORDER_OPTIONS}
                    value={txn.cross_border ?? ""}
                    onChange={(v) =>
                      updateTxn.mutate({
                        cross_border: (v || null) as CrossBorder | null,
                      })
                    }
                    disabled={!canWrite()}
                  />
                </dd>
                <dt className="text-text-muted">타겟 매수자</dt>
                <dd className="flex items-center gap-1.5 flex-wrap">
                  {TARGET_BUYER_TYPE_OPTIONS.map((opt) => {
                    const selected = (txn.target_buyer_types ?? []).includes(
                      opt.value as "STRATEGIC" | "FINANCIAL_SPONSOR",
                    );
                    return (
                      <button
                        key={opt.value}
                        type="button"
                        disabled={!canWrite()}
                        className={cn(
                          "px-2 py-0.5 rounded-full text-xs border transition-colors",
                          selected
                            ? "bg-amic/10 border-amic text-amic font-medium"
                            : "bg-transparent border-gray-border text-text-secondary hover:border-amic/50",
                        )}
                        onClick={() => {
                          const current = txn.target_buyer_types ?? [];
                          const next = selected
                            ? current.filter((v) => v !== opt.value)
                            : [
                                ...current,
                                opt.value as "STRATEGIC" | "FINANCIAL_SPONSOR",
                              ];
                          updateTxn.mutate({
                            target_buyer_types: next.length > 0 ? next : null,
                          });
                        }}
                      >
                        {opt.label}
                      </button>
                    );
                  })}
                </dd>
                <dt className="text-text-muted">배타적 협상권</dt>
                <dd className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={txn.exclusivity ?? false}
                    onChange={(e) => {
                      const checked = e.target.checked;
                      updateTxn.mutate({
                        exclusivity: checked,
                        ...(checked ? {} : { exclusivity_deadline: null }),
                      });
                    }}
                    disabled={!canWrite()}
                    className="h-3.5 w-3.5 rounded border-gray-border accent-amic"
                  />
                  {txn.exclusivity && (
                    <input
                      type="date"
                      className={cn(INLINE_INPUT_CLS, "w-36")}
                      value={txn.exclusivity_deadline ?? ""}
                      onChange={(e) =>
                        updateTxn.mutate({
                          exclusivity_deadline: e.target.value || null,
                        })
                      }
                      disabled={!canWrite()}
                    />
                  )}
                </dd>
              </dl>
            </div>
          </Card>
          {/* 회사 정보 — 전체 너비 */}
          <div className="lg:col-span-2">
            {txn.corporate_info ? (
              <CompanyInfoCard txn={txn} />
            ) : (
              <Card title="회사 정보" headerBar>
                <EngagementDocUpload
                  txnId={id}
                  docCategoryHint="CORPORATE_DOCS"
                />
              </Card>
            )}
          </div>

          {/* 서비스 연동 — 전체 너비 */}
          <div className="lg:col-span-2">
            <Card title="서비스 연동" headerBar>
              <div className="space-y-1.5 p-1">
                {(() => {
                  const enc = encodeURIComponent;
                  interface SvcItem {
                    key: string;
                    label: string;
                    icon: typeof Building2;
                    tab: string;
                    connected?: boolean;
                    viewUrl?: string;
                    createUrl?: string;
                    placeholder?: boolean;
                  }
                  const svcGroups: {
                    key: string;
                    phase: (typeof PHASE_CONFIG)[number]["phase"];
                    label: string;
                    items: SvcItem[];
                  }[] = [
                    {
                      key: "PREPARATION",
                      phase: "PREPARATION" as const,
                      label: "준비",
                      items: [
                        {
                          key: "kiis",
                          label: "KIIS 기업 인텔리전스",
                          icon: Building2,
                          tab: "",
                          connected: !!txn.target_corp_code,
                          viewUrl: txn.target_corp_code
                            ? `/kiis/companies/${txn.target_corp_code}`
                            : undefined,
                        },
                        {
                          key: "nda",
                          label: "NDA",
                          icon: FileText,
                          tab: "",
                          placeholder: true,
                        },
                      ],
                    },
                    {
                      key: "MARKETING",
                      phase: "MARKETING" as const,
                      label: "마케팅",
                      items: [
                        {
                          key: "tm",
                          label: "Teaser Memo (TM)",
                          icon: FileText,
                          tab: "marketing-materials",
                          createUrl: `/docs/new?type=teaser&txn_id=${id}&company=${enc(txn.target_company_name)}&project=${enc(txn.code_name)}&industry=${enc(txn.industry ?? "")}&return_url=${enc(`/ma/transactions/${id}`)}`,
                        },
                        {
                          key: "dm",
                          label: "Discussion Memo (DM)",
                          icon: FileText,
                          tab: "marketing-materials",
                          createUrl: `/docs/new?type=dm&txn_id=${id}&company=${enc(txn.target_company_name)}&project=${enc(txn.code_name)}&industry=${enc(txn.industry ?? "")}&return_url=${enc(`/ma/transactions/${id}`)}`,
                        },
                        {
                          key: "im",
                          label: "Information Memo (IM)",
                          icon: BookOpen,
                          tab: "marketing-materials",
                          connected: !!txn.im_document_id,
                          viewUrl: txn.im_document_id
                            ? `/docs/documents/${txn.im_document_id}`
                            : undefined,
                          createUrl: `/docs/new?type=im&txn_id=${id}&company=${enc(txn.target_company_name)}&project=${enc(txn.code_name)}&industry=${enc(txn.industry ?? "")}&return_url=${enc(`/ma/transactions/${id}`)}`,
                        },
                      ],
                    },
                    {
                      key: "MOU",
                      phase: "MARKETING" as const,
                      label: "MOU",
                      items: [
                        {
                          key: "mou",
                          label: "양해각서 (MOU)",
                          icon: Handshake,
                          tab: "contracts",
                          connected: !!legalDocs?.some(
                            (d) => d.doc_type === "MOU",
                          ),
                          createUrl: `/docs/legal/new?txn_id=${id}&type=MOU&return_url=${enc(`/ma/transactions/${id}`)}`,
                        },
                      ],
                    },
                    {
                      key: "BIDDING_DD",
                      phase: "BIDDING_DD" as const,
                      label: "DD",
                      items: [
                        {
                          key: "fdd",
                          label: "재무실사 (FDD)",
                          icon: BarChart2,
                          tab: "dd-checklist",
                          connected: !!txn.fdd_deal_id,
                          viewUrl: txn.fdd_deal_id
                            ? `/fdd/deals/${txn.fdd_deal_id}`
                            : undefined,
                          createUrl: `/docs/new?type=fdd&txn_id=${id}&company=${enc(txn.target_company_name)}&project=${enc(txn.code_name)}&return_url=${enc(`/ma/transactions/${id}`)}`,
                        },
                        {
                          key: "ldd",
                          label: "법률실사 (LDD)",
                          icon: Scale,
                          tab: "ldd",
                          createUrl: `/docs/ldd/new?txn_id=${id}&company=${enc(txn.target_company_name)}&return_url=${enc(`/ma/transactions/${id}`)}`,
                        },
                        {
                          key: "tdd",
                          label: "세무실사 (TDD)",
                          icon: DollarSign,
                          tab: "dd-checklist",
                        },
                      ],
                    },
                    {
                      key: "NEGOTIATION",
                      phase: "NEGOTIATION" as const,
                      label: "계약/협상",
                      items: [
                        {
                          key: "legal",
                          label: "법률 문서",
                          icon: FileSignature,
                          tab: "legal_docs",
                          createUrl: `/docs/legal/new?txn_id=${id}&return_url=${enc(`/ma/transactions/${id}`)}`,
                        },
                      ],
                    },
                    {
                      key: "CLOSING",
                      phase: "CLOSING" as const,
                      label: "Closing",
                      items: [],
                    },
                  ];

                  const currentIdx = PHASE_CONFIG.findIndex(
                    (p) => p.phase === txn.phase,
                  );

                  return svcGroups.map((group) => {
                    const groupIdx = PHASE_CONFIG.findIndex(
                      (p) => p.phase === group.phase,
                    );
                    const isCurrent = groupIdx === currentIdx;
                    const isPast = groupIdx < currentIdx;
                    const isOpen = openSvcGroups.has(group.key);
                    const isLeaf = group.items.length === 0;
                    const connectedCount = group.items.filter(
                      (s) => s.connected,
                    ).length;

                    return (
                      <div
                        key={group.key}
                        className={cn(
                          "rounded-lg border transition-all",
                          isCurrent &&
                            "border-accent bg-accent/[0.03] ring-1 ring-accent/20",
                          isPast && !isCurrent && "border-gray-border",
                          !isPast &&
                            !isCurrent &&
                            "border-dashed border-gray-border/60",
                        )}
                      >
                        {/* 그룹 헤더 */}
                        <button
                          type="button"
                          className="flex items-center gap-2 w-full px-3 py-2.5 text-left"
                          onClick={() =>
                            isLeaf
                              ? handleTabChange("closing")
                              : toggleSvcGroup(group.key)
                          }
                        >
                          {isPast && (
                            <CircleCheck
                              size={14}
                              className="text-accent shrink-0"
                            />
                          )}
                          {isCurrent && (
                            <span className="relative flex h-2 w-2 shrink-0">
                              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent/60" />
                              <span className="relative inline-flex h-2 w-2 rounded-full bg-accent" />
                            </span>
                          )}
                          {!isPast && !isCurrent && (
                            <CircleDashed
                              size={14}
                              className="text-text-muted/40 shrink-0"
                            />
                          )}
                          <span
                            className={cn(
                              "text-xs font-semibold uppercase tracking-wide flex-1",
                              isCurrent
                                ? "text-accent"
                                : isPast
                                  ? "text-text-secondary"
                                  : "text-text-muted",
                            )}
                          >
                            {group.label}
                          </span>
                          {isCurrent && (
                            <Badge variant="success" pill>
                              현재
                            </Badge>
                          )}
                          {!isLeaf && group.items.length > 0 && (
                            <span className="text-[10px] text-text-muted tabular-nums">
                              {connectedCount}/{group.items.length}
                            </span>
                          )}
                          {isLeaf ? (
                            <ChevronRight
                              size={14}
                              className="text-text-muted shrink-0"
                            />
                          ) : (
                            <ChevronDown
                              size={14}
                              className={cn(
                                "text-text-muted shrink-0 transition-transform duration-200",
                                !isOpen && "-rotate-90",
                              )}
                            />
                          )}
                        </button>

                        {/* 접이식 콘텐츠 */}
                        {!isLeaf && (
                          <div
                            className={cn(
                              "grid transition-all duration-200",
                              isOpen
                                ? "grid-rows-[1fr] opacity-100"
                                : "grid-rows-[0fr] opacity-0",
                            )}
                          >
                            <div className="overflow-hidden">
                              <div className="space-y-1.5 px-3 pb-2.5">
                                {group.items.map((svc) => (
                                  <div
                                    key={svc.key}
                                    className="flex items-center gap-2.5"
                                  >
                                    <div
                                      className={cn(
                                        "flex items-center justify-center w-7 h-7 rounded-md shrink-0",
                                        svc.connected
                                          ? "bg-accent/10 text-accent"
                                          : "bg-bg-cool text-text-muted",
                                      )}
                                    >
                                      <svc.icon size={14} />
                                    </div>
                                    <span className="text-sm font-medium truncate flex-1 min-w-0">
                                      {svc.label}
                                    </span>
                                    <div className="flex items-center gap-1 shrink-0">
                                      {svc.placeholder && (
                                        <span className="text-[10px] text-text-muted">
                                          준비 중
                                        </span>
                                      )}
                                      {svc.connected && (
                                        <Badge variant="success" pill>
                                          연결됨
                                        </Badge>
                                      )}
                                      {svc.connected && svc.viewUrl && (
                                        <Button
                                          variant="ghost"
                                          size="sm"
                                          icon={ExternalLink}
                                          onClick={() => navigate(svc.viewUrl!)}
                                        >
                                          열기
                                        </Button>
                                      )}
                                      {canWrite() &&
                                        !svc.connected &&
                                        !svc.placeholder &&
                                        svc.createUrl && (
                                          <Button
                                            variant="ghost"
                                            size="sm"
                                            icon={Plus}
                                            onClick={() =>
                                              navigate(svc.createUrl!)
                                            }
                                          >
                                            생성
                                          </Button>
                                        )}
                                      {svc.tab && (
                                        <button
                                          type="button"
                                          onClick={() =>
                                            handleTabChange(svc.tab)
                                          }
                                          className="p-1 rounded hover:bg-bg-cool text-text-muted hover:text-text-secondary transition-colors"
                                        >
                                          <ChevronRight size={12} />
                                        </button>
                                      )}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  });
                })()}

                {/* Metadata */}
                <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm pt-2 border-t border-gray-border">
                  <dt className="text-text-muted">DART Corp Code</dt>
                  <dd className="font-mono text-xs">
                    {txn.target_corp_code ?? "-"}
                  </dd>
                  <dt className="text-text-muted">생성일</dt>
                  <dd>{formatDate(txn.created_at)}</dd>
                  <dt className="text-text-muted">수정일</dt>
                  <dd>{formatDate(txn.updated_at)}</dd>
                </dl>
              </div>
            </Card>
          </div>
        </div>
      )}

      {/* ── Engagement 탭 ─────────────────────────────── */}
      {safeActiveTab === "engagement" && (
        <Card
          title="수임계약"
          headerBar
          padding="none"
          actions={
            canWrite() ? (
              <Button
                icon={FileText}
                onClick={() => setShowEngModal(true)}
                variant="ghost"
              >
                추가
              </Button>
            ) : undefined
          }
        >
          {!engagements?.length ? (
            <EmptyState
              icon={FileText}
              title="수임계약 없음"
              description="수임계약을 등록하세요."
              actionLabel={canWrite() ? "수임계약 추가" : undefined}
              onAction={canWrite() ? () => setShowEngModal(true) : undefined}
            />
          ) : (
            <DataTable
              columns={[
                {
                  key: "type",
                  header: "유형",
                  render: (r) => (
                    <Badge variant="info">
                      {ENGAGEMENT_TYPE_OPTIONS.find((o) => o.value === r.type)
                        ?.label ?? r.type}
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

      {/* Team 탭 삭제됨 */}

      {/* ── Buyers 탭 (Long List / Short List) ─────────── */}
      {safeActiveTab === "buyers" &&
        (() => {
          const tierOptions = BUYER_TIER_OPTIONS.filter((o) => o.value !== "");

          const buyerColumns: Column<BuyerCandidate>[] = [
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
              key: "tier",
              header: "Tier",
              render: (r) =>
                canWrite() ? (
                  <InlineSelect
                    options={[{ value: "", label: "-" }, ...tierOptions]}
                    value={r.tier ?? ""}
                    onChange={(val) =>
                      updateBuyer.mutate({
                        buyerId: r.id,
                        body: { tier: (val || null) as BuyerTier | null },
                      })
                    }
                  />
                ) : (
                  <BuyerTierBadge tier={r.tier} />
                ),
            },
            {
              key: "deal_role",
              header: "역할",
              render: (r) => {
                const roleOptions = DEAL_ROLE_OPTIONS.filter(
                  (o) => o.value !== "",
                );
                return canWrite() ? (
                  <InlineSelect
                    options={[{ value: "", label: "-" }, ...roleOptions]}
                    value={r.deal_role ?? ""}
                    onChange={(val) =>
                      updateBuyer.mutate({
                        buyerId: r.id,
                        body: {
                          deal_role: (val || null) as DealRole | null,
                        },
                      })
                    }
                  />
                ) : (
                  <DealRoleBadge role={r.deal_role} />
                );
              },
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
              align: "right" as const,
              mono: true,
              render: (r) =>
                r.ioi_value != null ? r.ioi_value.toLocaleString() : "-",
            },
            {
              key: "loi_value",
              header: "LOI",
              align: "right" as const,
              mono: true,
              render: (r) =>
                r.loi_value != null ? r.loi_value.toLocaleString() : "-",
            },
          ];

          const allBuyers = buyers ?? [];
          const shortListBuyers = allBuyers.filter(
            (b) => b.tier && b.tier !== "NOT_TARGET",
          );

          return (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <Tabs
                  tabs={[
                    {
                      id: "long-list",
                      label: "Long List",
                      badge: allBuyers.length || undefined,
                    },
                    {
                      id: "short-list",
                      label: "Short List",
                      badge: shortListBuyers.length || undefined,
                    },
                  ]}
                  activeTab={buyerSubTab}
                  onTabChange={(tab) =>
                    setBuyerSubTab(tab as "long-list" | "short-list")
                  }
                  variant="pill"
                  size="sm"
                />
                <div className="flex items-center gap-2">
                  {buyerSubTab === "long-list" && (
                    <Button
                      icon={Download}
                      onClick={() => exportExcel.mutate()}
                      variant="ghost"
                      size="sm"
                      loading={exportExcel.isPending}
                    >
                      Excel
                    </Button>
                  )}
                  {canWrite() && (
                    <Button
                      icon={UserPlus}
                      onClick={() => setShowBuyerModal(true)}
                      variant="ghost"
                    >
                      후보 추가
                    </Button>
                  )}
                </div>
              </div>

              {buyerSubTab === "long-list" && (
                <>
                  <div className="mb-3 flex justify-end">
                    <Button
                      icon={Sparkles}
                      onClick={() => setShowSIMappingModal(true)}
                      variant="secondary"
                      size="sm"
                    >
                      SI 자동 매핑
                    </Button>
                  </div>
                  <Card title="Long List" headerBar padding="none">
                    {!allBuyers.length ? (
                      <EmptyState
                        icon={Users}
                        title="Long List 후보 없음"
                        description="잠재 매수자를 추가하세요."
                        actionLabel={canWrite() ? "후보 추가" : undefined}
                        onAction={
                          canWrite() ? () => setShowBuyerModal(true) : undefined
                        }
                      />
                    ) : (
                      <DataTable
                        columns={buyerColumns}
                        data={allBuyers}
                        keyField="id"
                      />
                    )}
                  </Card>
                  {showSIMappingModal && (
                    <SIMappingPanel
                      txnId={id!}
                      onClose={() => setShowSIMappingModal(false)}
                    />
                  )}
                </>
              )}

              {buyerSubTab === "short-list" && (
                <>
                  <ShortListOverview
                    txnId={id}
                    buyers={allBuyers}
                    overviewData={shortListOverview ?? []}
                    canWrite={canWrite()}
                  />
                  <ConsortiumPanel
                    txnId={id}
                    buyers={allBuyers}
                    canWrite={canWrite()}
                  />
                </>
              )}
            </div>
          );
        })()}

      {/* ── VDR 탭 ────────────────────────────────────────── */}
      {safeActiveTab === "vdr" && <VdrTab txnId={id} />}

      {/* ── RFI 탭 ────────────────────────────────────────── */}
      {safeActiveTab === "rfi" && <RFIPanel txnId={id} />}

      {/* ── NDA 탭 ──────────────────────────────────────── */}
      {safeActiveTab === "ndas" && (
        <div className="space-y-4">
          {/* NDA 요약 */}
          {ndaSummary && ndaSummary.total > 0 && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <KpiCard label="전체" value={String(ndaSummary.total)} />
              <KpiCard
                label="체결 완료"
                value={String(ndaSummary.signed_count)}
                variant="positive"
              />
              <KpiCard
                label="대기 중"
                value={String(ndaSummary.pending_count)}
                variant="default"
              />
              <KpiCard
                label="체결률"
                value={
                  ndaSummary.total > 0
                    ? `${Math.round((ndaSummary.signed_count / ndaSummary.total) * 100)}%`
                    : "-"
                }
              />
            </div>
          )}
          <Card
            title="NDA 목록"
            headerBar
            padding="none"
            actions={
              canWrite() ? (
                <Button
                  icon={Plus}
                  onClick={() => setShowNdaModal(true)}
                  variant="ghost"
                >
                  NDA 추가
                </Button>
              ) : undefined
            }
          >
            {!ndas?.length ? (
              <EmptyState
                icon={Shield}
                title="NDA 없음"
                description="매수 후보와의 NDA를 등록하세요."
                actionLabel={canWrite() ? "NDA 추가" : undefined}
                onAction={canWrite() ? () => setShowNdaModal(true) : undefined}
              />
            ) : (
              <DataTable
                columns={[
                  {
                    key: "buyer_candidate_id",
                    header: "매수자",
                    render: (r) => {
                      const buyer = buyers?.find(
                        (b) => b.id === r.buyer_candidate_id,
                      );
                      return (
                        buyer?.company_name ?? r.buyer_candidate_id.slice(0, 8)
                      );
                    },
                  },
                  {
                    key: "nda_type",
                    header: "유형",
                    render: (r) => (
                      <Badge variant="neutral">
                        {NDA_TYPE_OPTIONS.find((o) => o.value === r.nda_type)
                          ?.label ?? r.nda_type}
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
                        disabled={!canWrite()}
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
                        className={`${INLINE_INPUT_CLS} w-32`}
                        defaultValue={r.sent_at ?? ""}
                        onChange={(e) =>
                          updateNda.mutate({
                            ndaId: r.id,
                            body: { sent_at: e.target.value || undefined },
                          })
                        }
                        disabled={!canWrite()}
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
                        className={`${INLINE_INPUT_CLS} w-32`}
                        defaultValue={r.signed_at ?? ""}
                        onChange={(e) =>
                          updateNda.mutate({
                            ndaId: r.id,
                            body: { signed_at: e.target.value || undefined },
                          })
                        }
                        disabled={!canWrite()}
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
                        className={`${INLINE_INPUT_CLS} w-32`}
                        defaultValue={r.expires_at ?? ""}
                        onChange={(e) =>
                          updateNda.mutate({
                            ndaId: r.id,
                            body: { expires_at: e.target.value || undefined },
                          })
                        }
                        disabled={!canWrite()}
                      />
                    ),
                  },
                  {
                    key: "actions",
                    header: "",
                    width: "40px",
                    render: (r) =>
                      canWrite() ? (
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
                      ) : null,
                  },
                ]}
                data={ndas}
                keyField="id"
              />
            )}
            <FileUploadZone txnId={id} entityType="NDA" embedded />
          </Card>
        </div>
      )}

      {/* ── Bids 탭 ─────────────────────────────────────── */}
      {safeActiveTab === "bids" && (
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
                        {BUYER_TYPE_OPTIONS.find(
                          (o) => o.value === r.buyer_type,
                        )?.label ?? r.buyer_type}
                      </Badge>
                    ),
                  },
                  {
                    key: "ioi",
                    header: "IOI",
                    align: "right",
                    mono: true,
                    render: (r) => (r.ioi ? formatAmount(r.ioi.amount) : "-"),
                  },
                  {
                    key: "loi",
                    header: "LOI",
                    align: "right",
                    mono: true,
                    render: (r) => (r.loi ? formatAmount(r.loi.amount) : "-"),
                  },
                  {
                    key: "final_offer",
                    header: "최종 제안",
                    align: "right",
                    mono: true,
                    render: (r) =>
                      r.final_offer ? formatAmount(r.final_offer.amount) : "-",
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
              canWrite() ? (
                <Button
                  icon={Plus}
                  onClick={() => setShowBidModal(true)}
                  variant="ghost"
                >
                  입찰 추가
                </Button>
              ) : undefined
            }
          >
            {!bids?.length ? (
              <EmptyState
                icon={DollarSign}
                title="입찰 없음"
                description="IOI/LOI/최종 제안을 등록하세요."
                actionLabel={canWrite() ? "입찰 추가" : undefined}
                onAction={canWrite() ? () => setShowBidModal(true) : undefined}
              />
            ) : (
              <DataTable
                columns={[
                  {
                    key: "buyer_candidate_id",
                    header: "매수자",
                    render: (r) => {
                      const buyer = buyers?.find(
                        (b) => b.id === r.buyer_candidate_id,
                      );
                      return (
                        buyer?.company_name ?? r.buyer_candidate_id.slice(0, 8)
                      );
                    },
                  },
                  {
                    key: "bid_type",
                    header: "유형",
                    render: (r) => (
                      <Badge variant="info">
                        {BID_TYPE_OPTIONS.find((o) => o.value === r.bid_type)
                          ?.label ?? r.bid_type}
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
                        className={`${INLINE_INPUT_CLS} w-28 text-right font-mono`}
                        defaultValue={r.amount ?? ""}
                        placeholder="금액"
                        onBlur={(e) => {
                          const v = e.target.value
                            ? Number(e.target.value)
                            : undefined;
                          if (v !== (r.amount ?? undefined)) {
                            updateBid.mutate({
                              bidId: r.id,
                              body: { amount: v },
                            });
                          }
                        }}
                        disabled={!canWrite()}
                      />
                    ),
                  },
                  {
                    key: "valuation_method",
                    header: "밸류에이션",
                    render: (r) =>
                      r.valuation_method
                        ? (VALUATION_METHOD_OPTIONS.find(
                            (o) => o.value === r.valuation_method,
                          )?.label ?? r.valuation_method)
                        : "-",
                  },
                  {
                    key: "multiple",
                    header: "배수",
                    align: "right",
                    mono: true,
                    render: (r) =>
                      r.multiple != null ? `${r.multiple}x` : "-",
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
                        disabled={!canWrite()}
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
                        className={`${INLINE_INPUT_CLS} w-32`}
                        defaultValue={r.submitted_at ?? ""}
                        onChange={(e) =>
                          updateBid.mutate({
                            bidId: r.id,
                            body: { submitted_at: e.target.value || undefined },
                          })
                        }
                        disabled={!canWrite()}
                      />
                    ),
                  },
                  {
                    key: "actions",
                    header: "",
                    width: "40px",
                    render: (r) =>
                      canWrite() ? (
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
                      ) : null,
                  },
                ]}
                data={bids}
                keyField="id"
              />
            )}
            <FileUploadZone txnId={id} entityType="BID" embedded />
          </Card>
        </div>
      )}

      {/* ── DD/Checklist 탭 ─────────────────────────────── */}
      {safeActiveTab === "dd-checklist" && (
        <div className="space-y-4">
          {/* 서브탭: 체크리스트 / DD 리포트 */}
          <Tabs
            tabs={[
              { id: "checklist", label: "체크리스트" },
              { id: "reports", label: "DD 리포트" },
            ]}
            activeTab={ddSubTab}
            onTabChange={(tab) => setDdSubTab(tab as "checklist" | "reports")}
            variant="pill"
            size="sm"
          />

          {/* DD 리포트 서브탭 */}
          {ddSubTab === "reports" && <DDReportSection txnId={id} />}

          {/* 체크리스트 서브탭 */}
          {ddSubTab === "checklist" && (
            <>
              {/* DD 진행 요약 */}
              {ddSummary && ddSummary.total > 0 && (
                <div className="space-y-3">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <KpiCard
                      label="전체 항목"
                      value={String(ddSummary.total)}
                    />
                    <KpiCard
                      label="완료율"
                      value={`${Math.round(ddSummary.overall_completion_pct)}%`}
                      variant={
                        ddSummary.overall_completion_pct >= 80
                          ? "positive"
                          : "default"
                      }
                    />
                    <KpiCard
                      label="진행 중"
                      value={String(
                        ddSummary.by_workstream.reduce(
                          (s, w) => s + w.in_progress,
                          0,
                        ),
                      )}
                    />
                    <KpiCard
                      label="미시작"
                      value={String(
                        ddSummary.by_workstream.reduce(
                          (s, w) => s + w.not_started,
                          0,
                        ),
                      )}
                      variant={
                        ddSummary.by_workstream.reduce(
                          (s, w) => s + w.not_started,
                          0,
                        ) > 0
                          ? "negative"
                          : "default"
                      }
                    />
                  </div>
                  {/* 워크스트림별 진행률 바 (그룹화) */}
                  <Card padding="md">
                    <div className="space-y-2">
                      {DD_WORKSTREAM_HIERARCHY.map((group) => {
                        const childStats = ddSummary.by_workstream.filter(
                          (ws) => group.children.includes(ws.workstream),
                        );
                        const total = childStats.reduce(
                          (s, w) => s + w.total,
                          0,
                        );
                        const completed = childStats.reduce(
                          (s, w) => s + w.completed,
                          0,
                        );
                        const pct =
                          total > 0 ? Math.round((completed / total) * 100) : 0;
                        return (
                          <div key={group.key}>
                            <div className="flex items-center gap-3">
                              <span className="text-xs font-medium w-24 truncate">
                                {group.label}
                              </span>
                              <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                                <div
                                  className="h-full bg-accent rounded-full transition-all"
                                  style={{ width: `${pct}%` }}
                                />
                              </div>
                              <span className="text-xs text-text-muted w-16 text-right">
                                {completed}/{total}
                              </span>
                            </div>
                            {group.children.length > 1 &&
                              childStats.map((ws) => {
                                const subPct =
                                  ws.total > 0
                                    ? Math.round(
                                        (ws.completed / ws.total) * 100,
                                      )
                                    : 0;
                                return (
                                  <div
                                    key={ws.workstream}
                                    className="flex items-center gap-3 ml-6 mt-1"
                                  >
                                    <span className="text-[10px] text-text-muted w-18 truncate">
                                      {DD_SUB_LABELS[ws.workstream] ??
                                        ws.workstream}
                                    </span>
                                    <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                                      <div
                                        className="h-full bg-accent/60 rounded-full transition-all"
                                        style={{ width: `${subPct}%` }}
                                      />
                                    </div>
                                    <span className="text-[10px] text-text-muted w-12 text-right">
                                      {ws.completed}/{ws.total}
                                    </span>
                                  </div>
                                );
                              })}
                          </div>
                        );
                      })}
                    </div>
                  </Card>
                </div>
              )}

              {/* 워크스트림 필터 — 1단: 메인 그룹 */}
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs font-medium text-text-muted">
                  워크스트림:
                </span>
                <button
                  type="button"
                  className={`px-3 py-1 text-xs font-medium rounded-dr-sm transition-colors ${
                    ddGroupFilter === "ALL"
                      ? "bg-accent text-white"
                      : "bg-bg-cool text-text-muted hover:bg-gray-border"
                  }`}
                  onClick={() => {
                    setDdGroupFilter("ALL");
                    setDdSubFilter(null);
                  }}
                >
                  전체
                </button>
                {DD_WORKSTREAM_HIERARCHY.map((g) => (
                  <button
                    key={g.key}
                    type="button"
                    className={`px-3 py-1 text-xs font-medium rounded-dr-sm transition-colors ${
                      ddGroupFilter === g.key
                        ? "bg-accent text-white"
                        : "bg-bg-cool text-text-muted hover:bg-gray-border"
                    }`}
                    onClick={() => {
                      setDdGroupFilter(g.key);
                      setDdSubFilter(null);
                    }}
                  >
                    {g.label}
                    {g.children.length > 1 ? " ▾" : ""}
                  </button>
                ))}
              </div>
              {/* 워크스트림 필터 — 2단: 서브 필터 (하위 항목이 있는 그룹만) */}
              {activeGroup && activeGroup.children.length > 1 && (
                <div className="flex flex-wrap items-center gap-2 ml-4">
                  <span className="text-xs text-text-muted">하위:</span>
                  <button
                    type="button"
                    className={`px-2.5 py-0.5 text-[11px] font-medium rounded-dr-sm transition-colors ${
                      !ddSubFilter
                        ? "bg-accent/80 text-white"
                        : "bg-bg-cool text-text-muted hover:bg-gray-border"
                    }`}
                    onClick={() => setDdSubFilter(null)}
                  >
                    전체
                  </button>
                  {activeGroup.children.map((ws) => (
                    <button
                      key={ws}
                      type="button"
                      className={`px-2.5 py-0.5 text-[11px] font-medium rounded-dr-sm transition-colors ${
                        ddSubFilter === ws
                          ? "bg-accent/80 text-white"
                          : "bg-bg-cool text-text-muted hover:bg-gray-border"
                      }`}
                      onClick={() => setDdSubFilter(ws)}
                    >
                      {DD_SUB_LABELS[ws] ?? ws}
                    </button>
                  ))}
                </div>
              )}

              {/* 체크리스트 목록 */}
              <Card
                title="DD 체크리스트"
                headerBar
                padding="none"
                actions={
                  canWrite() ? (
                    <Button
                      icon={Plus}
                      onClick={() => setShowDDModal(true)}
                      variant="ghost"
                    >
                      항목 추가
                    </Button>
                  ) : undefined
                }
              >
                {!ddItems?.length ? (
                  <EmptyState
                    icon={ClipboardCheck}
                    title="체크리스트 없음"
                    description="실사 체크리스트 항목을 추가하세요."
                    actionLabel={canWrite() ? "항목 추가" : undefined}
                    onAction={
                      canWrite() ? () => setShowDDModal(true) : undefined
                    }
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
                        render: (r) => {
                          const group = DD_WORKSTREAM_HIERARCHY.find((g) =>
                            g.children.includes(r.workstream),
                          );
                          const groupLabel = group?.label.split(" ")[0] ?? "";
                          return (
                            <div className="flex items-center gap-1">
                              {group && group.children.length > 1 && (
                                <Badge
                                  variant="neutral"
                                  className="text-[10px] opacity-60"
                                >
                                  {groupLabel}
                                </Badge>
                              )}
                              <Badge variant="neutral">
                                {DD_SUB_LABELS[r.workstream] ??
                                  DD_WORKSTREAM_OPTIONS.find(
                                    (o) => o.value === r.workstream,
                                  )?.label ??
                                  r.workstream}
                              </Badge>
                            </div>
                          );
                        },
                      },
                      { key: "title", header: "항목" },
                      {
                        key: "status",
                        header: "상태",
                        render: (r) => (
                          <InlineSelect
                            options={DD_STATUS_OPTIONS}
                            value={r.status}
                            onChange={(v) =>
                              updateDDItem.mutate({
                                itemId: r.id,
                                body: { status: v as DDStatusType },
                              })
                            }
                            disabled={!canWrite()}
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
                            className={`${INLINE_INPUT_CLS} w-36`}
                            defaultValue={r.assignee_email ?? ""}
                            placeholder="이메일"
                            onBlur={(e) => {
                              const v = e.target.value || undefined;
                              if (v !== (r.assignee_email ?? undefined)) {
                                updateDDItem.mutate({
                                  itemId: r.id,
                                  body: { assignee_email: v },
                                });
                              }
                            }}
                            disabled={!canWrite()}
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
                            className={`${INLINE_INPUT_CLS} w-32`}
                            defaultValue={r.due_date ?? ""}
                            onChange={(e) =>
                              updateDDItem.mutate({
                                itemId: r.id,
                                body: { due_date: e.target.value || undefined },
                              })
                            }
                            disabled={!canWrite()}
                          />
                        ),
                      },
                      {
                        key: "actions",
                        header: "",
                        width: "40px",
                        render: (r) =>
                          canWrite() ? (
                            <button
                              className="text-text-muted hover:text-negative p-1 rounded transition-colors"
                              title="삭제"
                              onClick={() => {
                                if (
                                  confirm(
                                    "이 체크리스트 항목을 삭제하시겠습니까?",
                                  )
                                ) {
                                  deleteDDItem.mutate(r.id);
                                }
                              }}
                            >
                              <Trash2 size={14} />
                            </button>
                          ) : null,
                      },
                    ]}
                    data={filteredDDItems ?? []}
                    keyField="id"
                  />
                )}
                <FileUploadZone txnId={id} entityType="DD_CHECKLIST" embedded />
              </Card>
            </>
          )}
        </div>
      )}

      {/* ── 계약/SPA 탭 ───────────────────────────────── */}
      {safeActiveTab === "contracts" && (
        <div className="space-y-4">
          {/* 서브탭: 계약 / 법률 문서 */}
          <Tabs
            tabs={[
              { id: "negotiation-workspace", label: "협상 워크스페이스" },
              { id: "contracts", label: "계약 목록" },
              { id: "legal-docs", label: "법률 문서" },
            ]}
            activeTab={contractSubTab}
            onTabChange={(tab) =>
              setContractSubTab(
                tab as "negotiation-workspace" | "contracts" | "legal-docs",
              )
            }
            variant="pill"
            size="sm"
          />

          {/* 협상 워크스페이스 서브탭 */}
          {contractSubTab === "negotiation-workspace" && (
            <ContractNegotiationWorkspace txnId={id} />
          )}

          {/* 법률 문서 서브탭 */}
          {contractSubTab === "legal-docs" && <LegalDocumentsTab txnId={id} />}

          {/* 계약 서브탭 */}
          {contractSubTab === "contracts" && (
            <>
              {/* 계약 요약 KPI */}
              {contractSummary && contractSummary.total > 0 && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <KpiCard
                    label="전체 계약"
                    value={String(contractSummary.total)}
                  />
                  <KpiCard
                    label="서명 대기"
                    value={String(contractSummary.pending_signatures)}
                    variant={
                      contractSummary.pending_signatures > 0
                        ? "caution"
                        : "default"
                    }
                  />
                  <KpiCard
                    label="체결 완료"
                    value={String(contractSummary.fully_executed)}
                    variant="positive"
                  />
                  <KpiCard
                    label="유형별"
                    value={String(Object.keys(contractSummary.by_type).length)}
                  />
                </div>
              )}

              {/* 계약 목록 */}
              <Card title="계약서 목록" headerBar padding="none">
                {!contracts?.length ? (
                  <EmptyState
                    icon={Scale}
                    title="계약서 없음"
                    description="SPA, SHA 등 계약서를 등록하세요."
                    actionLabel={canWrite() ? "계약서 추가" : undefined}
                    onAction={
                      canWrite() ? () => setShowContractModal(true) : undefined
                    }
                  />
                ) : (
                  <DataTable
                    columns={
                      [
                        { key: "title", header: "제목" },
                        {
                          key: "contract_type",
                          header: "유형",
                          render: (r) => (
                            <Badge variant="neutral">
                              {CONTRACT_TYPE_OPTIONS.find(
                                (o) => o.value === r.contract_type,
                              )?.label ?? r.contract_type}
                            </Badge>
                          ),
                        },
                        {
                          key: "status",
                          header: "상태",
                          render: (r) => (
                            <InlineSelect
                              options={CONTRACT_STATUS_OPTIONS}
                              value={r.status}
                              onChange={(v) =>
                                updateContract.mutate({
                                  contractId: r.id,
                                  body: { status: v as ContractStatus },
                                })
                              }
                              disabled={!canWrite()}
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
                            <InlineSelect
                              options={SIGNATURE_STATUS_OPTIONS}
                              value={r.seller_signature}
                              onChange={(v) =>
                                updateContract.mutate({
                                  contractId: r.id,
                                  body: { seller_signature: v as SigStatus },
                                })
                              }
                              disabled={!canWrite()}
                            />
                          ),
                        },
                        {
                          key: "buyer_signature",
                          header: "매수측 서명",
                          render: (r) => (
                            <InlineSelect
                              options={SIGNATURE_STATUS_OPTIONS}
                              value={r.buyer_signature}
                              onChange={(v) =>
                                updateContract.mutate({
                                  contractId: r.id,
                                  body: { buyer_signature: v as SigStatus },
                                })
                              }
                              disabled={!canWrite()}
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
                              className={`${INLINE_INPUT_CLS} w-32`}
                              defaultValue={r.effective_date ?? ""}
                              onChange={(e) =>
                                updateContract.mutate({
                                  contractId: r.id,
                                  body: {
                                    effective_date: e.target.value || undefined,
                                  },
                                })
                              }
                              disabled={!canWrite()}
                            />
                          ),
                        },
                        {
                          key: "ai_actions",
                          header: "",
                          width: "70px",
                          render: (r) =>
                            canWrite() ? (
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
                                    if (
                                      confirm("이 계약서를 삭제하시겠습니까?")
                                    ) {
                                      deleteContract.mutate(r.id);
                                    }
                                  }}
                                >
                                  <Trash2 size={14} />
                                </button>
                              </div>
                            ) : null,
                        },
                      ] as Column<(typeof contracts)[number]>[]
                    }
                    data={contracts}
                    keyField="id"
                  />
                )}
                <FileUploadZone txnId={id} entityType="CONTRACT" embedded />
              </Card>
            </>
          )}
        </div>
      )}

      {/* ── Closing 탭 ─────────────────────────────────── */}
      {safeActiveTab === "closing" && (
        <div className="space-y-4">
          {/* Closing 요약 KPI */}
          {closingSummary && closingSummary.total > 0 && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <KpiCard label="전체 항목" value={String(closingSummary.total)} />
              <KpiCard
                label="완료율"
                value={`${Math.round(closingSummary.completion_rate * 100)}%`}
                variant={
                  closingSummary.completion_rate >= 0.8 ? "positive" : "default"
                }
              />
              <KpiCard
                label="진행 중"
                value={String(closingSummary.by_status["IN_PROGRESS"] ?? 0)}
              />
              <KpiCard
                label="대기"
                value={String(closingSummary.by_status["PENDING"] ?? 0)}
                variant={
                  (closingSummary.by_status["PENDING"] ?? 0) > 0
                    ? "caution"
                    : "default"
                }
              />
            </div>
          )}

          {/* 카테고리 필터 */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-medium text-text-muted">
              카테고리:
            </span>
            {[{ value: "ALL", label: "전체" }, ...CLOSING_CATEGORY_OPTIONS].map(
              (opt) => (
                <button
                  key={opt.value}
                  type="button"
                  className={`px-3 py-1 text-xs font-medium rounded-dr-sm transition-colors ${
                    closingCategoryFilter === opt.value
                      ? "bg-accent text-white"
                      : "bg-bg-cool text-text-muted hover:bg-gray-border"
                  }`}
                  onClick={() => setClosingCategoryFilter(opt.value)}
                >
                  {opt.label}
                </button>
              ),
            )}
          </div>

          {/* 체크리스트 */}
          <Card
            title="Closing 체크리스트"
            headerBar
            padding="none"
            actions={
              canWrite() ? (
                <Button
                  icon={Plus}
                  onClick={() => setShowClosingModal(true)}
                  variant="ghost"
                >
                  항목 추가
                </Button>
              ) : undefined
            }
          >
            {!closingItems?.length ? (
              <EmptyState
                icon={Flag}
                title="Closing 항목 없음"
                description="선행조건, 인허가 등 Closing 체크리스트를 추가하세요."
                actionLabel={canWrite() ? "항목 추가" : undefined}
                onAction={
                  canWrite() ? () => setShowClosingModal(true) : undefined
                }
              />
            ) : !filteredClosingItems?.length ? (
              <div className="p-8 text-center text-text-muted text-sm">
                선택한 카테고리에 해당하는 항목이 없습니다.
              </div>
            ) : (
              <DataTable
                columns={
                  [
                    {
                      key: "category",
                      header: "카테고리",
                      render: (r) => (
                        <Badge variant="neutral">
                          {CLOSING_CATEGORY_OPTIONS.find(
                            (o) => o.value === r.category,
                          )?.label ?? r.category}
                        </Badge>
                      ),
                    },
                    { key: "title", header: "항목" },
                    {
                      key: "status",
                      header: "상태",
                      render: (r) => (
                        <InlineSelect
                          options={CLOSING_CONDITION_STATUS_OPTIONS}
                          value={r.status}
                          onChange={(v) =>
                            updateClosingItem.mutate({
                              itemId: r.id,
                              body: { status: v as ClosingConditionStatus },
                            })
                          }
                          disabled={!canWrite()}
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
                          className={`${INLINE_INPUT_CLS} w-28`}
                          defaultValue={r.responsible_party ?? ""}
                          placeholder="담당자"
                          onBlur={(e) => {
                            const v = e.target.value || undefined;
                            if (v !== (r.responsible_party ?? undefined)) {
                              updateClosingItem.mutate({
                                itemId: r.id,
                                body: { responsible_party: v },
                              });
                            }
                          }}
                          disabled={!canWrite()}
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
                          className={`${INLINE_INPUT_CLS} w-32`}
                          defaultValue={r.due_date ?? ""}
                          onChange={(e) =>
                            updateClosingItem.mutate({
                              itemId: r.id,
                              body: { due_date: e.target.value || undefined },
                            })
                          }
                          disabled={!canWrite()}
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
                          className={`${INLINE_INPUT_CLS} w-32`}
                          defaultValue={r.completed_date ?? ""}
                          onChange={(e) =>
                            updateClosingItem.mutate({
                              itemId: r.id,
                              body: {
                                completed_date: e.target.value || undefined,
                              },
                            })
                          }
                          disabled={!canWrite()}
                        />
                      ),
                    },
                    {
                      key: "actions",
                      header: "",
                      width: "40px",
                      render: (r) =>
                        canWrite() ? (
                          <button
                            className="text-text-muted hover:text-negative p-1 rounded transition-colors"
                            title="삭제"
                            onClick={() => {
                              if (
                                confirm(
                                  "이 체크리스트 항목을 삭제하시겠습니까?",
                                )
                              ) {
                                deleteClosingItem.mutate(r.id);
                              }
                            }}
                          >
                            <Trash2 size={14} />
                          </button>
                        ) : null,
                    },
                  ] as Column<(typeof closingItems)[number]>[]
                }
                data={filteredClosingItems ?? []}
                keyField="id"
              />
            )}
            <FileUploadZone txnId={id} entityType="CLOSING" embedded />
          </Card>
        </div>
      )}

      {/* ── PMI 탭 ──────────────────────────────────── */}
      {safeActiveTab === "pmi" && (
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
              variant={
                (pmiSummary?.by_status?.BLOCKED ?? 0) > 0
                  ? "negative"
                  : "default"
              }
            />
          </div>

          {/* 카테고리 필터 칩 */}
          <div className="flex flex-wrap gap-2">
            <button
              className={`px-3 py-1 rounded-dr-sm text-xs font-medium transition-colors ${pmiCategoryFilter === "ALL" ? "bg-accent text-white" : "bg-bg-cool text-text-muted hover:bg-gray-border"}`}
              onClick={() => setPmiCategoryFilter("ALL")}
            >
              전체
            </button>
            {PMI_CATEGORY_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                className={`px-3 py-1 rounded-dr-sm text-xs font-medium transition-colors ${pmiCategoryFilter === opt.value ? "bg-accent text-white" : "bg-bg-cool text-text-muted hover:bg-gray-border"}`}
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
              canWrite() ? (
                <Button
                  size="sm"
                  icon={Plus}
                  onClick={() => setShowPMIModal(true)}
                >
                  태스크 추가
                </Button>
              ) : undefined
            }
          >
            {!filteredPmiTasks?.length ? (
              <EmptyState
                icon={Flag}
                title="PMI 태스크 없음"
                description="인수 후 통합 태스크를 추가하세요."
              />
            ) : (
              <DataTable
                columns={
                  [
                    { key: "title", header: "태스크명" },
                    {
                      key: "category",
                      header: "카테고리",
                      render: (t) => (
                        <Badge variant="info">
                          {PMI_CATEGORY_OPTIONS.find(
                            (o) => o.value === t.category,
                          )?.label ?? t.category}
                        </Badge>
                      ),
                    },
                    {
                      key: "priority",
                      header: "우선순위",
                      render: (t) => (
                        <InlineSelect
                          options={PMI_PRIORITY_OPTIONS}
                          value={t.priority}
                          onChange={(v) =>
                            updatePMITask.mutate({
                              taskId: t.id,
                              body: { priority: v as PMIPriority },
                            })
                          }
                          disabled={!canWrite()}
                        />
                      ),
                    },
                    {
                      key: "status",
                      header: "상태",
                      render: (t) => (
                        <InlineSelect
                          options={PMI_STATUS_OPTIONS}
                          value={t.status}
                          onChange={(v) =>
                            updatePMITask.mutate({
                              taskId: t.id,
                              body: { status: v as PMITaskStatus },
                            })
                          }
                          disabled={!canWrite()}
                        />
                      ),
                    },
                    {
                      key: "assignee_name",
                      header: "담당자",
                      render: (t) => (
                        <input
                          key={`${t.id}-assignee`}
                          type="text"
                          className={`${INLINE_INPUT_CLS} w-28`}
                          defaultValue={t.assignee_name ?? ""}
                          placeholder="-"
                          onBlur={(e) => {
                            if (
                              e.target.value.trim() !== (t.assignee_name ?? "")
                            )
                              updatePMITask.mutate({
                                taskId: t.id,
                                body: {
                                  assignee_name:
                                    e.target.value.trim() || undefined,
                                },
                              });
                          }}
                          disabled={!canWrite()}
                        />
                      ),
                    },
                    {
                      key: "due_date",
                      header: "마감일",
                      render: (t) => (
                        <input
                          type="date"
                          className={`${INLINE_INPUT_CLS} w-32`}
                          defaultValue={t.due_date ?? ""}
                          onChange={(e) =>
                            updatePMITask.mutate({
                              taskId: t.id,
                              body: { due_date: e.target.value || undefined },
                            })
                          }
                          disabled={!canWrite()}
                        />
                      ),
                    },
                    {
                      key: "actions",
                      header: "",
                      render: (t) =>
                        canWrite() ? (
                          <button
                            className="text-text-muted hover:text-negative p-1 rounded transition-colors"
                            onClick={() => {
                              if (confirm("삭제하시겠습니까?"))
                                deletePMITask.mutate(t.id);
                            }}
                          >
                            <Trash2 size={14} />
                          </button>
                        ) : null,
                    },
                  ] as Column<PMITask>[]
                }
                data={filteredPmiTasks ?? []}
                keyField="id"
              />
            )}
            <FileUploadZone txnId={id} entityType="PMI" embedded />
          </Card>
        </div>
      )}

      {/* ── Earnout 탭 ───────────────────────────────── */}
      {safeActiveTab === "earnout" && (
        <div className="space-y-4">
          {/* KPI 요약 */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <KpiCard
              label="총 마일스톤"
              value={String(earnoutSummary?.total ?? 0)}
            />
            <KpiCard
              label="목표 합계"
              value={formatAmount(earnoutSummary?.total_target ?? 0)}
            />
            <KpiCard
              label="실적 합계"
              value={formatAmount(earnoutSummary?.total_actual ?? 0)}
              variant={
                (earnoutSummary?.total_actual ?? 0) >=
                (earnoutSummary?.total_target ?? 1)
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
              canWrite() ? (
                <Button
                  size="sm"
                  icon={Plus}
                  onClick={() => setShowEarnoutModal(true)}
                >
                  마일스톤 추가
                </Button>
              ) : undefined
            }
          >
            {!earnoutMilestones?.length ? (
              <EmptyState
                icon={DollarSign}
                title="어닝아웃 없음"
                description="어닝아웃 마일스톤을 추가하세요."
              />
            ) : (
              <DataTable
                columns={
                  [
                    { key: "title", header: "마일스톤" },
                    {
                      key: "metric",
                      header: "지표",
                      render: (m) =>
                        EARNOUT_METRIC_OPTIONS.find((o) => o.value === m.metric)
                          ?.label ?? m.metric,
                    },
                    {
                      key: "target_value",
                      header: "목표",
                      render: (m) =>
                        `${formatAmount(m.target_value)} ${m.currency}`,
                    },
                    {
                      key: "actual_value",
                      header: "실적",
                      render: (m) => (
                        <input
                          key={`${m.id}-actual`}
                          type="number"
                          className={`${INLINE_INPUT_CLS} w-24 text-right`}
                          defaultValue={m.actual_value ?? ""}
                          placeholder="-"
                          onBlur={(e) => {
                            const v =
                              e.target.value === ""
                                ? undefined
                                : Number(e.target.value);
                            if (v !== m.actual_value)
                              updateEarnout.mutate({
                                milestoneId: m.id,
                                body: { actual_value: v },
                              });
                          }}
                          disabled={!canWrite()}
                        />
                      ),
                    },
                    {
                      key: "status",
                      header: "상태",
                      render: (m) => (
                        <InlineSelect
                          options={EARNOUT_STATUS_OPTIONS}
                          value={m.status}
                          onChange={(v) =>
                            updateEarnout.mutate({
                              milestoneId: m.id,
                              body: { status: v as EarnoutStatus },
                            })
                          }
                          disabled={!canWrite()}
                        />
                      ),
                    },
                    {
                      key: "period",
                      header: "측정 기간",
                      render: (m) =>
                        m.measurement_start && m.measurement_end
                          ? `${m.measurement_start} ~ ${m.measurement_end}`
                          : "-",
                    },
                    {
                      key: "payment_amount",
                      header: "지급액",
                      render: (m) => (
                        <input
                          key={`${m.id}-payment`}
                          type="number"
                          className={`${INLINE_INPUT_CLS} w-24 text-right`}
                          defaultValue={m.payment_amount ?? ""}
                          placeholder="-"
                          onBlur={(e) => {
                            const v =
                              e.target.value === ""
                                ? undefined
                                : Number(e.target.value);
                            if (v !== m.payment_amount)
                              updateEarnout.mutate({
                                milestoneId: m.id,
                                body: { payment_amount: v },
                              });
                          }}
                          disabled={!canWrite()}
                        />
                      ),
                    },
                    {
                      key: "actions",
                      header: "",
                      render: (m) =>
                        canWrite() ? (
                          <button
                            className="text-text-muted hover:text-negative p-1 rounded transition-colors"
                            onClick={() => {
                              if (confirm("삭제하시겠습니까?"))
                                deleteEarnout.mutate(m.id);
                            }}
                          >
                            <Trash2 size={14} />
                          </button>
                        ) : null,
                    },
                  ] as Column<(typeof earnoutMilestones)[number]>[]
                }
                data={earnoutMilestones ?? []}
                keyField="id"
              />
            )}
            <FileUploadZone txnId={id} entityType="EARNOUT" embedded />
          </Card>
        </div>
      )}

      {/* ── Risk 탭 (Phase 5B) ─────────────────────────── */}
      {safeActiveTab === "risks" && (
        <div className="space-y-4">
          {/* KPI 요약 */}
          {riskSummary && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <KpiCard label="총 리스크" value={String(riskSummary.total)} />
              <KpiCard
                label="미완화 Critical"
                value={String(riskSummary.unmitigated_critical)}
                variant={
                  riskSummary.unmitigated_critical > 0 ? "danger" : "default"
                }
              />
              <KpiCard
                label="평균 점수"
                value={String(riskSummary.avg_risk_score)}
                subtitle="/20"
              />
              <KpiCard
                label="카테고리"
                value={String(riskSummary.by_category.length)}
              />
            </div>
          )}

          <Card
            title="리스크 레지스터"
            headerBar
            actions={
              canWrite() ? (
                <Button size="sm" onClick={() => setShowRiskModal(true)}>
                  <Plus size={14} className="mr-1" />
                  리스크 추가
                </Button>
              ) : undefined
            }
          >
            {/* 카테고리 필터 */}
            <div className="flex flex-wrap items-center gap-2 mb-4">
              <span className="text-xs font-medium text-text-muted">
                카테고리:
              </span>
              {[{ value: "ALL", label: "전체" }, ...RISK_CATEGORY_OPTIONS].map(
                (opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    className={`px-3 py-1 text-xs font-medium rounded-dr-sm transition-colors ${
                      riskCategoryFilter === opt.value
                        ? "bg-accent text-white"
                        : "bg-bg-cool text-text-muted hover:bg-gray-border"
                    }`}
                    onClick={() => setRiskCategoryFilter(opt.value)}
                  >
                    {opt.label}
                  </button>
                ),
              )}
            </div>

            {!filteredRisks?.length ? (
              <EmptyState
                title="리스크 없음"
                description="리스크 항목을 추가하세요."
              />
            ) : (
              <DataTable
                columns={
                  [
                    {
                      key: "title",
                      header: "제목",
                      render: (risk) => (
                        <span className="font-medium">{risk.title}</span>
                      ),
                    },
                    {
                      key: "category",
                      header: "카테고리",
                      render: (risk) => (
                        <Badge variant="neutral">
                          {RISK_CATEGORY_OPTIONS.find(
                            (o) => o.value === risk.category,
                          )?.label ?? risk.category}
                        </Badge>
                      ),
                    },
                    {
                      key: "severity",
                      header: "심각도",
                      render: (risk) => (
                        <InlineSelect
                          options={RISK_SEVERITY_OPTIONS}
                          value={risk.severity}
                          onChange={(v) =>
                            updateRisk.mutate({
                              itemId: risk.id,
                              body: { severity: v as RiskSeverity },
                            })
                          }
                          disabled={!canWrite()}
                        />
                      ),
                    },
                    {
                      key: "likelihood",
                      header: "발생확률",
                      render: (risk) => (
                        <InlineSelect
                          options={RISK_LIKELIHOOD_OPTIONS}
                          value={risk.likelihood}
                          onChange={(v) =>
                            updateRisk.mutate({
                              itemId: risk.id,
                              body: { likelihood: v as RiskLikelihood },
                            })
                          }
                          disabled={!canWrite()}
                        />
                      ),
                    },
                    {
                      key: "risk_score",
                      header: "점수",
                      render: (risk) => (
                        <span
                          className={`font-mono font-bold ${(risk.risk_score ?? 0) >= 12 ? "text-negative" : (risk.risk_score ?? 0) >= 6 ? "text-caution" : "text-positive"}`}
                        >
                          {risk.risk_score ?? "-"}
                        </span>
                      ),
                    },
                    {
                      key: "status",
                      header: "상태",
                      render: (risk) => (
                        <InlineSelect
                          options={RISK_STATUS_OPTIONS}
                          value={risk.status}
                          onChange={(v) =>
                            updateRisk.mutate({
                              itemId: risk.id,
                              body: { status: v as RiskStatus },
                            })
                          }
                          disabled={!canWrite()}
                        />
                      ),
                    },
                    {
                      key: "owner_email",
                      header: "담당",
                      render: (risk) => (
                        <input
                          key={`${risk.id}-owner`}
                          type="text"
                          className={`${INLINE_INPUT_CLS} w-36`}
                          defaultValue={risk.owner_email ?? ""}
                          placeholder="-"
                          onBlur={(e) => {
                            if (
                              e.target.value.trim() !== (risk.owner_email ?? "")
                            )
                              updateRisk.mutate({
                                itemId: risk.id,
                                body: {
                                  owner_email:
                                    e.target.value.trim() || undefined,
                                },
                              });
                          }}
                          disabled={!canWrite()}
                        />
                      ),
                    },
                    {
                      key: "actions",
                      header: "",
                      width: "40px",
                      render: (risk) =>
                        canWrite() ? (
                          <button
                            className="text-text-muted hover:text-negative p-1 rounded transition-colors"
                            onClick={() => {
                              if (confirm("삭제하시겠습니까?"))
                                deleteRisk.mutate(risk.id);
                            }}
                          >
                            <Trash2 size={14} />
                          </button>
                        ) : null,
                    },
                  ] as Column<(typeof filteredRisks)[number]>[]
                }
                data={filteredRisks ?? []}
                keyField="id"
              />
            )}
          </Card>

          {/* 리스크 추가 모달 */}
          <Modal
            open={showRiskModal}
            onClose={() => setShowRiskModal(false)}
            title="리스크 추가"
          >
            <div className="space-y-3">
              <Select
                label="카테고리"
                options={RISK_CATEGORY_OPTIONS}
                value={riskForm.category}
                onChange={(e) =>
                  setRiskForm((f) => ({
                    ...f,
                    category: e.target.value as RiskCategory,
                  }))
                }
              />
              <Input
                label="제목"
                value={riskForm.title}
                onChange={(e) =>
                  setRiskForm((f) => ({ ...f, title: e.target.value }))
                }
                required
              />
              <Input
                label="설명"
                value={riskForm.description ?? ""}
                onChange={(e) =>
                  setRiskForm((f) => ({ ...f, description: e.target.value }))
                }
              />
              <div className="grid grid-cols-2 gap-3">
                <Select
                  label="심각도"
                  options={RISK_SEVERITY_OPTIONS}
                  value={riskForm.severity ?? "MEDIUM"}
                  onChange={(e) =>
                    setRiskForm((f) => ({
                      ...f,
                      severity: e.target.value as RiskSeverity,
                    }))
                  }
                />
                <Select
                  label="발생확률"
                  options={RISK_LIKELIHOOD_OPTIONS}
                  value={riskForm.likelihood ?? "MEDIUM"}
                  onChange={(e) =>
                    setRiskForm((f) => ({
                      ...f,
                      likelihood: e.target.value as RiskLikelihood,
                    }))
                  }
                />
              </div>
              <Input
                label="완화 전략"
                value={riskForm.mitigation_strategy ?? ""}
                onChange={(e) =>
                  setRiskForm((f) => ({
                    ...f,
                    mitigation_strategy: e.target.value,
                  }))
                }
              />
              <Input
                label="담당자 이메일"
                value={riskForm.owner_email ?? ""}
                onChange={(e) =>
                  setRiskForm((f) => ({ ...f, owner_email: e.target.value }))
                }
              />
              <Input
                label="기한"
                type="date"
                value={riskForm.due_date ?? ""}
                onChange={(e) =>
                  setRiskForm((f) => ({ ...f, due_date: e.target.value }))
                }
              />
              <Button
                disabled={!riskForm.title}
                onClick={() => {
                  createRisk.mutate(riskForm);
                  setShowRiskModal(false);
                  setRiskForm({
                    category: "REGULATORY",
                    title: "",
                    severity: "MEDIUM",
                    likelihood: "MEDIUM",
                  });
                }}
              >
                추가
              </Button>
            </div>
          </Modal>
        </div>
      )}

      {/* ── Compliance 탭 (Phase 5B) ───────────────────── */}
      {safeActiveTab === "compliance" && (
        <div className="space-y-4">
          {/* KPI 요약 */}
          {complianceSummary && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <KpiCard
                label="총 항목"
                value={String(complianceSummary.total)}
              />
              <KpiCard
                label="준수율"
                value={`${complianceSummary.compliance_rate}%`}
              />
              <KpiCard
                label="주의/미준수"
                value={String(complianceSummary.flagged_count)}
                variant={
                  complianceSummary.flagged_count > 0 ? "danger" : "default"
                }
              />
              <KpiCard
                label="기한 초과"
                value={String(complianceSummary.overdue_count)}
                variant={
                  complianceSummary.overdue_count > 0 ? "danger" : "default"
                }
              />
            </div>
          )}

          <Card
            title="컴플라이언스 체크리스트"
            headerBar
            actions={
              canWrite() ? (
                <Button size="sm" onClick={() => setShowComplianceModal(true)}>
                  <Plus size={14} className="mr-1" />
                  항목 추가
                </Button>
              ) : undefined
            }
          >
            {/* 카테고리 필터 */}
            <div className="flex flex-wrap items-center gap-2 mb-4">
              <span className="text-xs font-medium text-text-muted">
                카테고리:
              </span>
              {[
                { value: "ALL", label: "전체" },
                ...COMPLIANCE_CATEGORY_OPTIONS,
              ].map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  className={`px-3 py-1 text-xs font-medium rounded-dr-sm transition-colors ${
                    complianceCategoryFilter === opt.value
                      ? "bg-accent text-white"
                      : "bg-bg-cool text-text-muted hover:bg-gray-border"
                  }`}
                  onClick={() => setComplianceCategoryFilter(opt.value)}
                >
                  {opt.label}
                </button>
              ))}
            </div>

            {!filteredComplianceItems?.length ? (
              <EmptyState
                title="컴플라이언스 항목 없음"
                description="규제 요건을 추가하세요."
              />
            ) : (
              <DataTable
                columns={
                  [
                    {
                      key: "requirement",
                      header: "요건",
                      render: (item) => (
                        <span className="font-medium">{item.requirement}</span>
                      ),
                    },
                    {
                      key: "category",
                      header: "카테고리",
                      render: (item) => (
                        <Badge variant="neutral">
                          {COMPLIANCE_CATEGORY_OPTIONS.find(
                            (o) => o.value === item.category,
                          )?.label ?? item.category}
                        </Badge>
                      ),
                    },
                    {
                      key: "jurisdiction",
                      header: "관할",
                      render: (item) => (
                        <span className="text-xs">
                          {item.jurisdiction ?? "-"}
                        </span>
                      ),
                    },
                    {
                      key: "regulatory_body",
                      header: "규제 기관",
                      render: (item) => (
                        <span className="text-xs">
                          {item.regulatory_body ?? "-"}
                        </span>
                      ),
                    },
                    {
                      key: "status",
                      header: "상태",
                      render: (item) => (
                        <InlineSelect
                          options={COMPLIANCE_STATUS_OPTIONS}
                          value={item.status}
                          onChange={(v) =>
                            updateCompliance.mutate({
                              itemId: item.id,
                              body: { status: v as ComplianceStatus },
                            })
                          }
                          disabled={!canWrite()}
                        />
                      ),
                    },
                    {
                      key: "due_date",
                      header: "기한",
                      render: (item) => (
                        <input
                          type="date"
                          className={`${INLINE_INPUT_CLS} w-32`}
                          defaultValue={item.due_date ?? ""}
                          onChange={(e) =>
                            updateCompliance.mutate({
                              itemId: item.id,
                              body: { due_date: e.target.value || undefined },
                            })
                          }
                          disabled={!canWrite()}
                        />
                      ),
                    },
                    {
                      key: "assignee_email",
                      header: "담당",
                      render: (item) => (
                        <input
                          key={`${item.id}-assignee`}
                          type="text"
                          className={`${INLINE_INPUT_CLS} w-36`}
                          defaultValue={item.assignee_email ?? ""}
                          placeholder="-"
                          onBlur={(e) => {
                            if (
                              e.target.value.trim() !==
                              (item.assignee_email ?? "")
                            )
                              updateCompliance.mutate({
                                itemId: item.id,
                                body: {
                                  assignee_email:
                                    e.target.value.trim() || undefined,
                                },
                              });
                          }}
                          disabled={!canWrite()}
                        />
                      ),
                    },
                    {
                      key: "actions",
                      header: "",
                      width: "40px",
                      render: (item) =>
                        canWrite() ? (
                          <button
                            className="text-text-muted hover:text-negative p-1 rounded transition-colors"
                            onClick={() => {
                              if (confirm("삭제하시겠습니까?"))
                                deleteCompliance.mutate(item.id);
                            }}
                          >
                            <Trash2 size={14} />
                          </button>
                        ) : null,
                    },
                  ] as Column<(typeof filteredComplianceItems)[number]>[]
                }
                data={filteredComplianceItems ?? []}
                keyField="id"
              />
            )}
          </Card>

          {/* 컴플라이언스 추가 모달 */}
          <Modal
            open={showComplianceModal}
            onClose={() => setShowComplianceModal(false)}
            title="컴플라이언스 항목 추가"
          >
            <div className="space-y-3">
              <Select
                label="카테고리"
                options={COMPLIANCE_CATEGORY_OPTIONS}
                value={complianceForm.category}
                onChange={(e) =>
                  setComplianceForm((f) => ({
                    ...f,
                    category: e.target.value as CompCat,
                  }))
                }
              />
              <Input
                label="규제 요건"
                value={complianceForm.requirement}
                onChange={(e) =>
                  setComplianceForm((f) => ({
                    ...f,
                    requirement: e.target.value,
                  }))
                }
                required
              />
              <Input
                label="설명"
                value={complianceForm.description ?? ""}
                onChange={(e) =>
                  setComplianceForm((f) => ({
                    ...f,
                    description: e.target.value,
                  }))
                }
              />
              <div className="grid grid-cols-2 gap-3">
                <Input
                  label="관할권"
                  value={complianceForm.jurisdiction ?? ""}
                  onChange={(e) =>
                    setComplianceForm((f) => ({
                      ...f,
                      jurisdiction: e.target.value,
                    }))
                  }
                  placeholder="예: 대한민국"
                />
                <Input
                  label="규제 기관"
                  value={complianceForm.regulatory_body ?? ""}
                  onChange={(e) =>
                    setComplianceForm((f) => ({
                      ...f,
                      regulatory_body: e.target.value,
                    }))
                  }
                  placeholder="예: 공정거래위원회"
                />
              </div>
              <Input
                label="담당자 이메일"
                value={complianceForm.assignee_email ?? ""}
                onChange={(e) =>
                  setComplianceForm((f) => ({
                    ...f,
                    assignee_email: e.target.value,
                  }))
                }
              />
              <Input
                label="기한"
                type="date"
                value={complianceForm.due_date ?? ""}
                onChange={(e) =>
                  setComplianceForm((f) => ({ ...f, due_date: e.target.value }))
                }
              />
              <Button
                disabled={!complianceForm.requirement}
                onClick={() => {
                  createCompliance.mutate(complianceForm);
                  setShowComplianceModal(false);
                  setComplianceForm({ category: "ANTITRUST", requirement: "" });
                }}
              >
                추가
              </Button>
            </div>
          </Modal>

          {/* 인허가 분석 패널 */}
          <PermitAnalysisPanel txnId={id} canWrite={canWrite()} />
        </div>
      )}

      {/* ── 마케팅 자료 탭 (TM / DM / IM) ─────────────── */}
      {safeActiveTab === "marketing-materials" && (
        <div className="space-y-4">
          <Card
            title="마케팅 자료"
            headerBar
            actions={
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() =>
                    createMarketingMaterial.mutate({
                      doc_type: "TM",
                      title: `${txn?.code_name ?? "Project"} — Teaser Memo`,
                      project_code: txn?.code_name ?? undefined,
                    })
                  }
                >
                  + Teaser (TM)
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() =>
                    createMarketingMaterial.mutate({
                      doc_type: "DM",
                      title: `${txn?.code_name ?? "Project"} — Discussion Memo`,
                      project_code: txn?.code_name ?? undefined,
                    })
                  }
                >
                  + Discussion (DM)
                </Button>
                <Button
                  size="sm"
                  onClick={() =>
                    createMarketingMaterial.mutate({
                      doc_type: "IM",
                      title: `${txn?.code_name ?? "Project"} — Information Memo`,
                      project_code: txn?.code_name ?? undefined,
                    })
                  }
                >
                  + Information (IM)
                </Button>
              </div>
            }
          >
            {!marketingMaterials?.length ? (
              <EmptyState
                icon={FileText}
                title="마케팅 자료 없음"
                description="TM, DM, IM 자료를 생성하여 매수자에게 배포하세요."
              />
            ) : (
              <DataTable<MarketingMaterial>
                columns={[
                  {
                    key: "doc_type",
                    label: "유형",
                    render: (row) => (
                      <Badge
                        variant={
                          row.doc_type === "TM"
                            ? "info"
                            : row.doc_type === "DM"
                              ? "warning"
                              : "success"
                        }
                        pill
                      >
                        {row.doc_type}
                      </Badge>
                    ),
                  },
                  { key: "title", label: "제목" },
                  {
                    key: "status",
                    label: "상태",
                    render: (row) => (
                      <Badge
                        variant={
                          row.status === "READY"
                            ? "success"
                            : row.status === "GENERATING"
                              ? "warning"
                              : row.status === "FAILED"
                                ? "error"
                                : "neutral"
                        }
                        pill
                      >
                        {MARKETING_STATUS_LABELS[row.status] ?? row.status}
                      </Badge>
                    ),
                  },
                  {
                    key: "distributed_to",
                    label: "배포",
                    render: (row) =>
                      row.distributed_to?.length
                        ? `${row.distributed_to.length}곳`
                        : "미배포",
                  },
                  {
                    key: "file_size_bytes",
                    label: "크기",
                    render: (row) =>
                      row.file_size_bytes
                        ? `${Math.round(row.file_size_bytes / 1024)} KB`
                        : "—",
                  },
                  {
                    key: "id",
                    label: "작업",
                    render: (row) => (
                      <div className="flex gap-2">
                        {row.status === "READY" && (
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() =>
                              window.open(getDownloadUrl(id, row.id), "_blank")
                            }
                          >
                            다운로드
                          </Button>
                        )}
                        {canWrite() && (
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => {
                              if (
                                window.confirm(
                                  "마케팅 자료를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.",
                                )
                              ) {
                                deleteMarketingMaterial.mutate(row.id);
                              }
                            }}
                          >
                            <Trash2 size={14} />
                          </Button>
                        )}
                      </div>
                    ),
                  },
                ]}
                data={marketingMaterials}
                keyField="id"
              />
            )}
            <FileUploadZone
              txnId={id}
              entityType="MARKETING_MATERIAL"
              embedded
            />
          </Card>
        </div>
      )}

      {/* ── 재무모델 (Models) 탭 ─────────────────────── */}
      {safeActiveTab === "models" && (
        <div className="space-y-4">
          {selectedFMId ? (
            // 체크리스트 리뷰 뷰
            <div>
              <Button
                variant="ghost"
                size="sm"
                icon={ArrowLeft}
                onClick={() => setSelectedFMId(null)}
                className="mb-4"
              >
                모델 목록으로
              </Button>
              <FMChecklistReview txnId={id} fmId={selectedFMId} />
            </div>
          ) : (
            // 모델 목록 뷰
            <Card
              title="재무모델"
              headerBar
              actions={
                canWrite() ? (
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() =>
                        createFinancialModel.mutate({
                          model_type: "DCF",
                          title: `${txn?.code_name ?? "Project"} — DCF Valuation`,
                        })
                      }
                    >
                      + DCF
                    </Button>
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() =>
                        createFinancialModel.mutate({
                          model_type: "COMPS",
                          title: `${txn?.code_name ?? "Project"} — 비교기업 분석`,
                        })
                      }
                    >
                      + COMPS
                    </Button>
                    <Button
                      size="sm"
                      onClick={() =>
                        createFinancialModel.mutate({
                          model_type: "FULL",
                          title: `${txn?.code_name ?? "Project"} — Full Financial Model`,
                        })
                      }
                    >
                      + Full Model
                    </Button>
                  </div>
                ) : undefined
              }
            >
              {!financialModels?.length ? (
                <EmptyState
                  icon={FileSpreadsheet}
                  title="재무모델 없음"
                  description="DCF, LBO, COMPS 등 재무모델을 생성하면 VDR 자료에서 가정값을 자동 추출하여 Excel을 생성합니다."
                />
              ) : (
                <DataTable<FinancialModel>
                  columns={[
                    {
                      key: "model_type",
                      header: "유형",
                      render: (row) => (
                        <span className="text-sm font-medium">
                          {FM_MODEL_TYPE_LABELS[row.model_type]}
                        </span>
                      ),
                    },
                    {
                      key: "title",
                      header: "제목",
                      render: (row) => (
                        <button
                          type="button"
                          onClick={() => {
                            if (
                              row.status === "PENDING_REVIEW" ||
                              row.status === "READY" ||
                              row.status === "FAILED"
                            ) {
                              setSelectedFMId(row.id);
                            }
                          }}
                          className="text-sm text-amic hover:underline text-left"
                        >
                          {row.title}
                        </button>
                      ),
                    },
                    {
                      key: "status",
                      header: "상태",
                      render: (row) => (
                        <span
                          className={cn(
                            "inline-flex px-2 py-0.5 text-xs font-semibold rounded-full",
                            FM_STATUS_COLORS[row.status],
                          )}
                        >
                          {FM_STATUS_LABELS[row.status]}
                        </span>
                      ),
                    },
                    {
                      key: "version",
                      header: "버전",
                      render: (row) => (
                        <span className="text-xs">v{row.version}</span>
                      ),
                    },
                    {
                      key: "ralph_score",
                      header: "Ralph 점수",
                      render: (row) =>
                        row.ralph_score != null ? (
                          <span className="text-xs font-medium">
                            {row.ralph_score.toFixed(1)}
                          </span>
                        ) : (
                          <span className="text-xs text-text-secondary">
                            --
                          </span>
                        ),
                    },
                    {
                      key: "actions" as keyof FinancialModel,
                      header: "",
                      render: (row) => (
                        <div className="flex items-center gap-1">
                          {row.status === "READY" && (
                            <Button
                              variant="ghost"
                              size="sm"
                              icon={Download}
                              onClick={() =>
                                window.open(
                                  getFMDownloadUrl(id, row.id),
                                  "_blank",
                                )
                              }
                            >
                              다운로드
                            </Button>
                          )}
                          {canWrite() && (
                            <Button
                              variant="ghost"
                              size="sm"
                              icon={Trash2}
                              onClick={() =>
                                deleteFinancialModel.mutate(row.id)
                              }
                              className="text-negative hover:bg-negative/10"
                            />
                          )}
                        </div>
                      ),
                    },
                  ]}
                  data={financialModels}
                  keyField="id"
                />
              )}
              <FileUploadZone
                txnId={id}
                entityType="FINANCIAL_MODEL"
                embedded
              />
            </Card>
          )}
        </div>
      )}

      {/* ── Timeline 탭 ───────────────────────────────── */}

      {/* ── AI Quality (Ralph Loop) 탭 ───────────────── */}
      {safeActiveTab === "ai-quality" && (
        <div className="space-y-6">
          {/* 세션 목록 */}
          <Card
            title="Ralph Loop 세션"
            headerBar
            actions={
              canWrite() ? (
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
      )}

      {safeActiveTab === "timeline" && (
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
              </Card>
            </details>
          )}
        </div>
      )}

      {/* ── 마케팅 로그 탭 ──────────────────────────────── */}
      {safeActiveTab === "marketing-logs" && (
        <MeetingLogsTab
          txnId={id}
          meetingPhase="MARKETING"
          buyerId={buyerIdParam}
          buyerName={
            buyerIdParam
              ? buyers?.find((b) => b.id === buyerIdParam)?.company_name
              : undefined
          }
          onClearBuyerFilter={() => {
            const next = new URLSearchParams(searchParams);
            next.delete("buyerId");
            setSearchParams(next, { replace: true });
          }}
        />
      )}

      {/* ── 협상 로그 탭 ──────────────────────────────── */}
      {safeActiveTab === "negotiation-logs" && (
        <MeetingLogsTab txnId={id} meetingPhase="NEGOTIATION" />
      )}

      {/* ── Notes & Approvals 탭 ──────────────────────── */}
      {safeActiveTab === "notes-approvals" && (
        <div className="space-y-6">
          {/* 승인 요약 KPI */}
          {approvalSummary && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <KpiCard
                label="전체 승인"
                value={String(approvalSummary.total)}
              />
              <KpiCard
                label="대기 중"
                value={String(approvalSummary.pending)}
                variant={approvalSummary.pending > 0 ? "warning" : undefined}
              />
              <KpiCard
                label="승인됨"
                value={String(approvalSummary.approved)}
                variant="good"
              />
              <KpiCard
                label="거절됨"
                value={String(approvalSummary.rejected)}
                variant={approvalSummary.rejected > 0 ? "bad" : undefined}
              />
            </div>
          )}

          {/* 승인 요청 목록 */}
          <Card
            title="승인 요청"
            headerBar
            actions={
              canWrite() ? (
                <Button
                  size="sm"
                  icon={Plus}
                  onClick={() => setShowApprovalModal(true)}
                >
                  승인 요청
                </Button>
              ) : undefined
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
                        <span className="font-medium text-sm">
                          {approval.title}
                        </span>
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
                          {APPROVAL_STATUS_OPTIONS.find(
                            (o) => o.value === approval.status,
                          )?.label ?? approval.status}
                        </Badge>
                        <Badge variant="info" pill>
                          {APPROVAL_TYPE_OPTIONS.find(
                            (o) => o.value === approval.approval_type,
                          )?.label ?? approval.approval_type}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-1">
                        {canWrite() && approval.status === "PENDING" && (
                          <>
                            <Button
                              size="sm"
                              variant="ghost"
                              icon={Check}
                              onClick={() =>
                                decideApproval.mutate({
                                  approvalId: approval.id,
                                  body: {
                                    email: approval.approvers[0]?.email ?? "",
                                    decision: "APPROVED",
                                  },
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
                                  body: {
                                    email: approval.approvers[0]?.email ?? "",
                                    decision: "REJECTED",
                                  },
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
                      <p className="text-xs text-text-muted">
                        {approval.description}
                      </p>
                    )}
                    <div className="flex items-center gap-4 text-xs text-text-muted">
                      <span>요청자: {approval.requester_email}</span>
                      {approval.deadline && (
                        <span>기한: {approval.deadline}</span>
                      )}
                      <span>{formatDate(approval.created_at)}</span>
                    </div>
                    {approval.approvers.length > 0 && (
                      <div className="flex flex-wrap gap-2 pt-1">
                        {approval.approvers.map((a) => (
                          <Badge
                            key={a.email}
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

          {/* 노트 타입 필터 */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-medium text-text-muted">타입:</span>
            {[{ value: "ALL", label: "전체" }, ...NOTE_TYPE_OPTIONS].map(
              (opt) => (
                <button
                  key={opt.value}
                  type="button"
                  className={`px-3 py-1 text-xs font-medium rounded-dr-sm transition-colors ${
                    noteTypeFilter === opt.value
                      ? "bg-accent text-white"
                      : "bg-bg-cool text-text-muted hover:bg-gray-border"
                  }`}
                  onClick={() => setNoteTypeFilter(opt.value)}
                >
                  {opt.label}
                </button>
              ),
            )}
          </div>

          {/* 노트/코멘트 */}
          <Card
            title="내부 노트"
            headerBar
            actions={
              canWrite() ? (
                <Button
                  size="sm"
                  icon={Plus}
                  onClick={() => setShowNoteModal(true)}
                >
                  노트 추가
                </Button>
              ) : undefined
            }
          >
            {!filteredNotes?.length ? (
              <EmptyState
                icon={MessageSquare}
                title="노트 없음"
                description={
                  canWrite()
                    ? "내부 의사결정, 질문, 메모를 기록하세요."
                    : "등록된 노트가 없습니다."
                }
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
                        {note.is_pinned && (
                          <Pin size={14} className="text-accent" />
                        )}
                        <Badge variant="info" pill>
                          {NOTE_TYPE_OPTIONS.find(
                            (o) => o.value === note.note_type,
                          )?.label ?? note.note_type}
                        </Badge>
                        <span className="text-xs text-text-muted">
                          {note.author_email}
                        </span>
                      </div>
                      <div className="flex items-center gap-1">
                        <span className="text-xs text-text-muted">
                          {formatDate(note.created_at)}
                        </span>
                        {canWrite() && (
                          <Button
                            size="sm"
                            variant="ghost"
                            icon={Trash2}
                            onClick={() => {
                              if (confirm("이 노트를 삭제하시겠습니까?"))
                                deleteNote.mutate(note.id);
                            }}
                          />
                        )}
                      </div>
                    </div>
                    <p className="text-sm whitespace-pre-wrap">
                      {note.content}
                    </p>
                    {note.mentions && note.mentions.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {note.mentions.map((m) => (
                          <Badge key={m} variant="neutral" pill>
                            @{m}
                          </Badge>
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
              setEngForm({
                ...engForm,
                type: e.target.value as EngagementCreate["type"],
              })
            }
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="체결일"
              type="date"
              value={engForm.signed_at ?? ""}
              onChange={(e) =>
                setEngForm({
                  ...engForm,
                  signed_at: e.target.value || undefined,
                })
              }
            />
            <Input
              label="만료일"
              type="date"
              value={engForm.expires_at ?? ""}
              onChange={(e) =>
                setEngForm({
                  ...engForm,
                  expires_at: e.target.value || undefined,
                })
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
                buyer_type: e.target
                  .value as BuyerCandidateCreate["buyer_type"],
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
            options={(buyers ?? []).map((b) => ({
              value: b.id,
              label: b.company_name,
            }))}
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
              setNdaForm({
                ...ndaForm,
                nda_type: e.target.value as NDACreate["nda_type"],
              })
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
                setNdaForm({
                  ...ndaForm,
                  expires_at: e.target.value || undefined,
                })
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
            <Button
              variant="ghost"
              type="button"
              onClick={() => {
                setShowNdaModal(false);
                setNdaForm({ buyer_candidate_id: "", nda_type: "MUTUAL" });
              }}
            >
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
            options={(buyers ?? []).map((b) => ({
              value: b.id,
              label: b.company_name,
            }))}
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
                setBidForm({
                  ...bidForm,
                  amount: e.target.value ? Number(e.target.value) : undefined,
                })
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
                setBidForm({
                  ...bidForm,
                  valuation_method: (e.target.value || undefined) as
                    | ValuationMethod
                    | undefined,
                })
              }
            />
            <Input
              label="배수"
              type="number"
              step="0.1"
              value={bidForm.multiple ?? ""}
              onChange={(e) =>
                setBidForm({
                  ...bidForm,
                  multiple: e.target.value ? Number(e.target.value) : undefined,
                })
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
                setBidForm({
                  ...bidForm,
                  submitted_at: e.target.value || undefined,
                })
              }
            />
            <Input
              label="유효기간"
              type="date"
              value={bidForm.valid_until ?? ""}
              onChange={(e) =>
                setBidForm({
                  ...bidForm,
                  valid_until: e.target.value || undefined,
                })
              }
            />
          </div>
          <Input
            label="조건 / 비고"
            value={bidForm.conditions ?? ""}
            onChange={(e) =>
              setBidForm({
                ...bidForm,
                conditions: e.target.value || undefined,
              })
            }
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="ghost"
              type="button"
              onClick={() => setShowBidModal(false)}
            >
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
            onChange={(e) =>
              setContractForm({ ...contractForm, title: e.target.value })
            }
            placeholder="예: 주식매매계약(SPA)"
          />
          <Select
            label="계약 유형"
            options={CONTRACT_TYPE_OPTIONS.filter((o) => o.value !== "")}
            value={contractForm.contract_type ?? "SPA"}
            onChange={(e) =>
              setContractForm({
                ...contractForm,
                contract_type: (e.target.value ||
                  undefined) as ContractCreate["contract_type"],
              })
            }
          />
          <Input
            label="상대방"
            value={contractForm.counterparty_name ?? ""}
            onChange={(e) =>
              setContractForm({
                ...contractForm,
                counterparty_name: e.target.value || undefined,
              })
            }
            placeholder="계약 상대방"
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="효력일"
              type="date"
              value={contractForm.effective_date ?? ""}
              onChange={(e) =>
                setContractForm({
                  ...contractForm,
                  effective_date: e.target.value || undefined,
                })
              }
            />
            <Input
              label="만료일"
              type="date"
              value={contractForm.expiry_date ?? ""}
              onChange={(e) =>
                setContractForm({
                  ...contractForm,
                  expiry_date: e.target.value || undefined,
                })
              }
            />
          </div>
          <Input
            label="설명 / 비고"
            value={contractForm.description ?? ""}
            onChange={(e) =>
              setContractForm({
                ...contractForm,
                description: e.target.value || undefined,
              })
            }
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="ghost"
              type="button"
              onClick={() => setShowContractModal(false)}
            >
              취소
            </Button>
            <Button type="submit" loading={createContract.isPending}>
              등록
            </Button>
          </div>
        </form>
      </Modal>

      {/* Closing 체크리스트 추가 모달 */}
      <Modal
        open={showClosingModal}
        onClose={() => setShowClosingModal(false)}
        title="Closing 체크리스트 항목 추가"
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
              setClosingForm({
                ...closingForm,
                category: e.target.value as ClosingCategory,
              })
            }
          />
          <Input
            label="항목명"
            required
            value={closingForm.title}
            onChange={(e) =>
              setClosingForm({ ...closingForm, title: e.target.value })
            }
            placeholder="예: 공정거래위원회 기업결합신고"
          />
          <Input
            label="설명"
            value={closingForm.description ?? ""}
            onChange={(e) =>
              setClosingForm({
                ...closingForm,
                description: e.target.value || undefined,
              })
            }
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="담당자"
              value={closingForm.responsible_party ?? ""}
              onChange={(e) =>
                setClosingForm({
                  ...closingForm,
                  responsible_party: e.target.value || undefined,
                })
              }
            />
            <Input
              label="담당자 이메일"
              type="email"
              value={closingForm.responsible_email ?? ""}
              onChange={(e) =>
                setClosingForm({
                  ...closingForm,
                  responsible_email: e.target.value || undefined,
                })
              }
            />
          </div>
          <Input
            label="기한"
            type="date"
            value={closingForm.due_date ?? ""}
            onChange={(e) =>
              setClosingForm({
                ...closingForm,
                due_date: e.target.value || undefined,
              })
            }
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="ghost"
              type="button"
              onClick={() => setShowClosingModal(false)}
            >
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
              setPmiForm({
                ...pmiForm,
                category: e.target.value as PMICategory,
              })
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
              setPmiForm({
                ...pmiForm,
                description: e.target.value || undefined,
              })
            }
          />
          <Select
            label="우선순위"
            options={PMI_PRIORITY_OPTIONS}
            value={pmiForm.priority ?? "MEDIUM"}
            onChange={(e) =>
              setPmiForm({
                ...pmiForm,
                priority: e.target.value as PMIPriority,
              })
            }
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="담당자"
              value={pmiForm.assignee_name ?? ""}
              onChange={(e) =>
                setPmiForm({
                  ...pmiForm,
                  assignee_name: e.target.value || undefined,
                })
              }
            />
            <Input
              label="담당자 이메일"
              type="email"
              value={pmiForm.assignee_email ?? ""}
              onChange={(e) =>
                setPmiForm({
                  ...pmiForm,
                  assignee_email: e.target.value || undefined,
                })
              }
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="시작일"
              type="date"
              value={pmiForm.start_date ?? ""}
              onChange={(e) =>
                setPmiForm({
                  ...pmiForm,
                  start_date: e.target.value || undefined,
                })
              }
            />
            <Input
              label="마감일"
              type="date"
              value={pmiForm.due_date ?? ""}
              onChange={(e) =>
                setPmiForm({
                  ...pmiForm,
                  due_date: e.target.value || undefined,
                })
              }
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="ghost"
              type="button"
              onClick={() => setShowPMIModal(false)}
            >
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
                setEarnoutForm({
                  title: "",
                  metric: "REVENUE",
                  target_value: 0,
                });
              },
            });
          }}
          className="space-y-4"
        >
          <Input
            label="마일스톤명"
            required
            value={earnoutForm.title}
            onChange={(e) =>
              setEarnoutForm({ ...earnoutForm, title: e.target.value })
            }
            placeholder="예: 2026년 매출 달성 조건"
          />
          <Input
            label="설명"
            value={earnoutForm.description ?? ""}
            onChange={(e) =>
              setEarnoutForm({
                ...earnoutForm,
                description: e.target.value || undefined,
              })
            }
          />
          <Select
            label="지표"
            options={EARNOUT_METRIC_OPTIONS}
            value={earnoutForm.metric}
            onChange={(e) =>
              setEarnoutForm({
                ...earnoutForm,
                metric: e.target.value as EarnoutMetric,
              })
            }
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="목표 금액"
              type="number"
              required
              value={earnoutForm.target_value.toString()}
              onChange={(e) =>
                setEarnoutForm({
                  ...earnoutForm,
                  target_value: Number(e.target.value) || 0,
                })
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
                setEarnoutForm({
                  ...earnoutForm,
                  measurement_start: e.target.value || undefined,
                })
              }
            />
            <Input
              label="측정 종료일"
              type="date"
              value={earnoutForm.measurement_end ?? ""}
              onChange={(e) =>
                setEarnoutForm({
                  ...earnoutForm,
                  measurement_end: e.target.value || undefined,
                })
              }
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="ghost"
              type="button"
              onClick={() => setShowEarnoutModal(false)}
            >
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
                setDDForm({
                  workstream: "FDD_FINANCIAL_STATEMENTS",
                  title: "",
                });
              },
            });
          }}
          className="space-y-4"
        >
          <div className="w-full">
            <label className="block text-sm font-medium text-text-body mb-1.5">
              워크스트림
            </label>
            <div className="relative">
              <select
                className="w-full px-3 py-2 text-sm rounded-dr-sm border transition-colors appearance-none shadow-sm bg-white text-text-body pr-10 focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-amic border-gray-border hover:border-amic-400"
                value={ddForm.workstream}
                onChange={(e) =>
                  setDDForm({
                    ...ddForm,
                    workstream: e.target.value as DDWorkstream,
                  })
                }
              >
                {DD_WORKSTREAM_HIERARCHY.map((g) =>
                  g.children.length === 1 ? (
                    <option key={g.key} value={g.children[0]}>
                      {g.label}
                    </option>
                  ) : (
                    <optgroup key={g.key} label={g.label}>
                      {g.children.map((ws) => (
                        <option key={ws} value={ws}>
                          {DD_SUB_LABELS[ws] ?? ws}
                        </option>
                      ))}
                    </optgroup>
                  ),
                )}
              </select>
            </div>
          </div>
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
                setDDForm({
                  ...ddForm,
                  assignee_email: e.target.value || undefined,
                })
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
            <Button
              variant="ghost"
              type="button"
              onClick={() => setShowDDModal(false)}
            >
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
              setNoteForm({
                ...noteForm,
                note_type: e.target.value as NoteType,
              })
            }
          />
          <div>
            <label className="block text-sm font-medium text-text-body mb-1.5">
              내용
            </label>
            <textarea
              required
              rows={4}
              className="w-full px-3 py-2 text-sm rounded-dr-sm border border-gray-border shadow-sm bg-white text-text-body placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-amic hover:border-amic-400 transition-colors"
              value={noteForm.content}
              onChange={(e) =>
                setNoteForm({ ...noteForm, content: e.target.value })
              }
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
            <Button
              variant="ghost"
              type="button"
              onClick={() => setShowNoteModal(false)}
            >
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
              setApprovalForm({
                ...approvalForm,
                approval_type: e.target.value as AppType,
              })
            }
          />
          <Input
            label="제목"
            required
            value={approvalForm.title}
            onChange={(e) =>
              setApprovalForm({ ...approvalForm, title: e.target.value })
            }
            placeholder="예: 마케팅 단계 전환 승인 요청"
          />
          <Input
            label="설명"
            value={approvalForm.description ?? ""}
            onChange={(e) =>
              setApprovalForm({
                ...approvalForm,
                description: e.target.value || undefined,
              })
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
              setApprovalForm({
                ...approvalForm,
                deadline: e.target.value || undefined,
              })
            }
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="ghost"
              type="button"
              onClick={() => setShowApprovalModal(false)}
            >
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
