import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import {
  Plus,
  FileText,
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
  DollarSign,
  Scale,
} from "lucide-react";
import { cn } from "@/lib/cn";

import { useUpdateTransaction } from "@/modules/ma/hooks/useTransactions";
import type {
  Currency,
  DealType,
  DealStructure,
  InvestmentType,
  SaleProcess,
  ControlTransfer,
  ValuationBasis,
  CrossBorder,
} from "@/modules/ma/types/transaction";
import type { Transaction } from "@/modules/ma/types/transaction";
import {
  PHASE_CONFIG,
  DEAL_TYPE_OPTIONS,
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
import CompanyInfoCard from "@/modules/ma/components/overview/CompanyInfoCard";

import {
  Badge,
  Button,
  Card,
  InlineSelect,
  InlineCombobox,
  INLINE_INPUT_CLS,
} from "@/components/ui";
import { formatISODate as formatDate } from "@/modules/ma/utils/format";

// ── Types ──────────────────────────────────────────────
interface TransactionOverviewTabProps {
  txnId: string;
  txn: Transaction;
  /** Legal docs — only doc_type is used (MOU existence check) */
  legalDocs?: Array<{ doc_type: string }>;
  onTabChange: (tab: string) => void;
}

// ── 서비스 연동 아코디언 phase-group 매핑 ────────────
const PHASE_TO_SVC_GROUP: Record<string, string> = {
  ENGAGEMENT: "PREPARATION",
  PREPARATION: "PREPARATION",
  MARKETING: "MARKETING",
  BIDDING: "BIDDING",
  MOU_SIGNED: "MAIN_DUE_DILIGENCE",
  MAIN_DUE_DILIGENCE: "MAIN_DUE_DILIGENCE",
  NEGOTIATION: "NEGOTIATION",
  CLOSING: "CLOSING",
  POST_CLOSING: "CLOSING",
};

// ── 메인 컴포넌트 ──────────────────────────────────────
export default function TransactionOverviewTab({
  txnId,
  txn,
  legalDocs,
  onTabChange,
}: TransactionOverviewTabProps) {
  const { canWrite } = useAuth();
  const navigate = useNavigate();
  const updateTxn = useUpdateTransaction(txnId);

  // 서비스 연동 아코디언 상태
  const [openSvcGroups, setOpenSvcGroups] = useState<Set<string>>(
    () => new Set(["PREPARATION"]),
  );
  useEffect(() => {
    if (txn.phase) {
      const g = PHASE_TO_SVC_GROUP[txn.phase] ?? "PREPARATION";
      setOpenSvcGroups(new Set([g]));
    }
  }, [txn.phase]);
  const toggleSvcGroup = (key: string) =>
    setOpenSvcGroups((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });

  const id = txnId;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* 거래 정보 — 2-Column */}
      <Card
        title="거래 정보"
        headerBar
        className="lg:col-span-2"
        data-onboarding="deal-info"
      >
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
              <span className="font-mono text-sm font-medium text-accent select-all">
                {txn.code_name}
              </span>
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
            <dt className="text-text-muted">딜 구조</dt>
            <dd>
              <InlineSelect
                options={DEAL_TYPE_OPTIONS}
                value={txn.deal_type}
                onChange={(v) =>
                  updateTxn.mutate({
                    deal_type: (v || "SE") as DealType,
                  })
                }
                disabled={!canWrite()}
              />
            </dd>
            <dt className="text-text-muted">세부 거래 구조</dt>
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
                className={cn(INLINE_INPUT_CLS, "w-32 text-right font-mono")}
                defaultValue={txn.estimated_deal_value ?? ""}
                onBlur={(e) => {
                  const v = e.target.value || null;
                  if (v !== txn.estimated_deal_value)
                    updateTxn.mutate({ estimated_deal_value: v });
                }}
                disabled={!canWrite()}
                placeholder="-"
              />
              <InlineSelect
                options={CURRENCY_OPTIONS}
                value={txn.currency}
                onChange={(v) => updateTxn.mutate({ currency: v as Currency })}
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
                className={cn(INLINE_INPUT_CLS, "w-20 text-right font-mono")}
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
                className={cn(INLINE_INPUT_CLS, "w-16 text-right font-mono")}
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
                className={cn(INLINE_INPUT_CLS, "w-16 text-right font-mono")}
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
      <div className="lg:col-span-2" data-onboarding="company-info">
        <CompanyInfoCard txn={txn} canWrite={canWrite()} />
      </div>

      {/* 서비스 연동 — 전체 너비 */}
      <div className="lg:col-span-2" data-onboarding="service-integration">
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
                      connected: !!legalDocs?.some((d) => d.doc_type === "MOU"),
                      createUrl: `/docs/legal/new?txn_id=${id}&type=MOU&return_url=${enc(`/ma/transactions/${id}`)}`,
                    },
                  ],
                },
                {
                  key: "BIDDING",
                  phase: "BIDDING" as const,
                  label: "입찰",
                  items: [],
                },
                {
                  key: "MAIN_DUE_DILIGENCE",
                  phase: "MAIN_DUE_DILIGENCE" as const,
                  label: "본실사",
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
                    <button
                      type="button"
                      className="flex items-center gap-2 w-full px-3 py-2.5 text-left"
                      onClick={() =>
                        isLeaf
                          ? onTabChange("closing")
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
                                        onClick={() => navigate(svc.createUrl!)}
                                      >
                                        생성
                                      </Button>
                                    )}
                                  {svc.tab && (
                                    <button
                                      type="button"
                                      onClick={() => onTabChange(svc.tab)}
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
  );
}
