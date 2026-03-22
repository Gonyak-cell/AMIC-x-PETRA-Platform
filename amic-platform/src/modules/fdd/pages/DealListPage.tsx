import { useState, useMemo, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Briefcase, CheckCircle, FileEdit, Archive, Plus, ChevronDown } from "lucide-react";
import { toast } from "sonner";
import { useDeals, useCreateDeal } from "@/modules/fdd/hooks/useDeals";
import type {
  DealCreate,
  DealType,
  DealStructure,
  InvestmentType,
  SellerType,
  Deal,
} from "@/modules/fdd/types/deal";
import type { IndustryType } from "@/modules/fdd/types/deal";
import { INDUSTRY_LIST, FDD_INDUSTRY_OPTIONS } from "@/types/industry";
import {
  Button,
  Card,
  KpiCard,
  DataTable,
  Modal,
  Input,
  Select,
  Badge,
  getStatusVariant,
  EmptyState,
  PageHero,
} from "@/components/ui";
import type { Column } from "@/components/ui";
import { formatDate } from "@/lib/format";
import { useScrollReveal } from "@/hooks/useScrollReveal";
import { TeamAvatars } from "@/components/collaboration/TeamAvatars";
import { useTeamMembers } from "@/hooks/useTeamMembers";
import {
  DEAL_TYPE_OPTIONS,
  CURRENCY_OPTIONS,
  DEAL_STRUCTURE_OPTIONS,
  INVESTMENT_TYPE_OPTIONS,
  SELLER_TYPE_OPTIONS,
} from "@/modules/fdd/constants";
import heroImg from "@/assets/images/heroes/hero-arch-silver.jpg";

const INITIAL_FORM: DealCreate = {
  name: "",
  target_company_name: "",
};

export default function DealListPage() {
  const navigate = useNavigate();
  const { data: deals, isLoading } = useDeals();
  const createDeal = useCreateDeal();
  const { members } = useTeamMembers();
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState<DealCreate>(INITIAL_FORM);
  const [showOptional, setShowOptional] = useState(false);
  const kpiRef = useRef<HTMLDivElement>(null);
  useScrollReveal(kpiRef, { stagger: 0.06, y: 20 });

  // KPI 계산
  const kpis = useMemo(() => {
    if (!deals) return { total: 0, active: 0, draft: 0, archived: 0 };
    return {
      total: deals.length,
      active: deals.filter((d) => d.status === "ACTIVE").length,
      draft: deals.filter((d) => d.status === "DRAFT").length,
      archived: deals.filter((d) => d.status === "ARCHIVED").length,
    };
  }, [deals]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // 필수 필드만 포함, 나머지는 값이 있을 때만 추가
    const payload: DealCreate = {
      name: form.name,
      target_company_name: form.target_company_name,
    };
    if (form.deal_type) payload.deal_type = form.deal_type;
    if (form.base_currency) payload.base_currency = form.base_currency;
    if (form.industry) payload.industry = form.industry;
    if (form.client_name) payload.client_name = form.client_name;
    if (form.client_contact_email)
      payload.client_contact_email = form.client_contact_email;
    if (form.deal_structure) payload.deal_structure = form.deal_structure;
    if (form.investment_type) payload.investment_type = form.investment_type;
    if (form.seller_type) payload.seller_type = form.seller_type;
    if (form.reference_date) payload.reference_date = form.reference_date;
    if (form.period_start) payload.period_start = form.period_start;
    if (form.period_end) payload.period_end = form.period_end;

    createDeal.mutate(payload, {
      onSuccess: () => {
        toast.success("딜이 성공적으로 생성되었습니다.");
        setForm(INITIAL_FORM);
        setShowOptional(false);
        setShowModal(false);
      },
      onError: () => {
        toast.error("딜 생성에 실패했습니다.");
      },
    });
  };

  const handleRowClick = (deal: Deal) => {
    navigate(`/fdd/deals/${deal.id}`);
  };

  const tbd = <span className="text-text-muted italic text-xs">선택 안함</span>;

  // DataTable 컬럼 정의
  const columns: Column<Deal>[] = [
    {
      key: "name",
      header: "딜 이름",
      render: (row) => (
        <div>
          <span className="font-medium text-text-dark">{row.name}</span>
          <span className="block text-xs text-text-muted">
            {row.target_company_name || "선택 안함"}
          </span>
        </div>
      ),
    },
    {
      key: "deal_type",
      header: "가격조정 방식",
      width: "160px",
      render: (row) => (
        <span>
          {row.deal_type === "COMPLETION_ACCOUNTS"
            ? "가격조정"
            : "잠금박스"}
        </span>
      ),
    },
    {
      key: "industry",
      header: "업종",
      width: "140px",
      render: (row) => {
        const ind = INDUSTRY_LIST.find((i) => i.id === row.industry);
        return (
          <Badge variant={row.industry === "general" ? "neutral" : "info"}>
            {ind?.name_en ?? "General"}
          </Badge>
        );
      },
    },
    {
      key: "deal_structure",
      header: "거래구조",
      width: "120px",
      render: (row) => {
        if (!row.deal_structure) return tbd;
        const opt = DEAL_STRUCTURE_OPTIONS.find((o) => o.value === row.deal_structure);
        return <span>{opt?.label ?? row.deal_structure}</span>;
      },
    },
    {
      key: "reference_date",
      header: "기준일",
      align: "center",
      width: "120px",
      render: (row) =>
        row.reference_date ? formatDate(row.reference_date, "month") : tbd,
    },
    {
      key: "team_partner_id",
      header: "팀",
      width: "120px",
      render: (row) => {
        const teamIds = [row.team_partner_id, row.team_manager_id].filter(
          Boolean,
        ) as string[];
        if (teamIds.length === 0) return tbd;
        const teamMembers = teamIds
          .map((id) => members.find((m) => m.user_id === id))
          .filter(Boolean) as typeof members;
        return <TeamAvatars members={teamMembers} max={3} />;
      },
    },
    {
      key: "status",
      header: "상태",
      align: "center",
      width: "100px",
      render: (row) => (
        <Badge variant={getStatusVariant(row.status)}>{row.status}</Badge>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHero
        title="Deals"
        subtitle="Financial Due Diligence 딜 관리"
        compact
        backgroundImage={heroImg}
        backgroundOpacity={0.18}
        actions={
          <Button variant="accent" icon={Plus} onClick={() => setShowModal(true)}>
            새 딜 생성
          </Button>
        }
      />

      {/* KPI Cards */}
      <div ref={kpiRef} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="전체 딜"
          value={String(kpis.total)}
          icon={Briefcase}
        />
        <KpiCard
          label="진행 중"
          value={String(kpis.active)}
          icon={CheckCircle}
          variant="positive"
        />
        <KpiCard
          label="초안"
          value={String(kpis.draft)}
          icon={FileEdit}
          variant="caution"
        />
        <KpiCard
          label="보관"
          value={String(kpis.archived)}
          icon={Archive}
        />
      </div>

      {/* Deal Table */}
      <Card title="전체 딜 목록" headerBar padding="none">
        {!isLoading && (!deals || deals.length === 0) ? (
          <EmptyState
            icon={Briefcase}
            title="아직 딜이 없습니다"
            description="새 딜을 생성하여 FDD 분석을 시작하세요."
          />
        ) : (
          <DataTable
            columns={columns}
            data={deals || []}
            keyField="id"
            loading={isLoading}
            onRowClick={handleRowClick}
            striped
          />
        )}
      </Card>

      {/* Create Deal Modal */}
      <Modal
        open={showModal}
        onClose={() => setShowModal(false)}
        title="새 딜 생성"
        size="lg"
        footer={
          <>
            <Button variant="ghost" onClick={() => setShowModal(false)}>
              취소
            </Button>
            <Button
              variant="accent"
              type="submit"
              form="create-deal-form"
              loading={createDeal.isPending}
            >
              생성
            </Button>
          </>
        }
      >
        <form id="create-deal-form" onSubmit={handleSubmit} className="space-y-5">
          {/* ─── 필수 정보 ─── */}
          <fieldset className="space-y-3">
            <legend className="text-xs font-semibold uppercase tracking-wider text-text-muted mb-1">
              기본 정보
            </legend>
            <Input
              label="딜 이름"
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="예: Project Alpha"
            />
            <Input
              label="대상회사명"
              required
              value={form.target_company_name}
              onChange={(e) =>
                setForm({ ...form, target_company_name: e.target.value })
              }
              placeholder="예: (주)대상기업"
            />
          </fieldset>

          <p className="text-xs text-text-muted">
            위 두 항목만 입력하면 바로 생성됩니다. 나머지는 나중에 설정할 수 있습니다.
          </p>

          {/* ─── 추가 정보 토글 ─── */}
          <button
            type="button"
            className="flex items-center gap-1.5 text-sm font-medium text-accent hover:text-accent/80 transition-colors"
            onClick={() => setShowOptional(!showOptional)}
          >
            <ChevronDown
              size={16}
              className={`transition-transform ${showOptional ? "rotate-180" : ""}`}
            />
            추가 정보 {showOptional ? "접기" : "펼치기"}
          </button>

          {showOptional && (
            <div className="space-y-5 animate-fade-in">
              {/* ─── 의뢰인 정보 ─── */}
              <fieldset className="space-y-3">
                <legend className="text-xs font-semibold uppercase tracking-wider text-text-muted mb-1">
                  의뢰인 정보
                </legend>
                <div className="grid grid-cols-2 gap-4">
                  <Input
                    label="의뢰인명"
                    value={form.client_name ?? ""}
                    onChange={(e) =>
                      setForm({ ...form, client_name: e.target.value })
                    }
                    placeholder="선택 안함"
                  />
                  <Input
                    label="의뢰인 이메일"
                    type="email"
                    value={form.client_contact_email ?? ""}
                    onChange={(e) =>
                      setForm({ ...form, client_contact_email: e.target.value })
                    }
                    placeholder="선택 안함"
                  />
                </div>
              </fieldset>

              {/* ─── 거래 분류 ─── */}
              <fieldset className="space-y-3">
                <legend className="text-xs font-semibold uppercase tracking-wider text-text-muted mb-1">
                  거래 분류
                </legend>
                <div className="grid grid-cols-2 gap-4">
                  <Select
                    label="거래구조"
                    options={DEAL_STRUCTURE_OPTIONS}
                    value={form.deal_structure ?? ""}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        deal_structure: (e.target.value || undefined) as
                          | DealStructure
                          | undefined,
                      })
                    }
                  />
                  <Select
                    label="투자 유형"
                    options={INVESTMENT_TYPE_OPTIONS}
                    value={form.investment_type ?? ""}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        investment_type: (e.target.value || undefined) as
                          | InvestmentType
                          | undefined,
                      })
                    }
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <Select
                    label="매도인 유형"
                    options={SELLER_TYPE_OPTIONS}
                    value={form.seller_type ?? ""}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        seller_type: (e.target.value || undefined) as
                          | SellerType
                          | undefined,
                      })
                    }
                  />
                  <Select
                    label="가격조정 방식"
                    options={DEAL_TYPE_OPTIONS}
                    value={form.deal_type ?? ""}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        deal_type: (e.target.value || undefined) as
                          | DealType
                          | undefined,
                      })
                    }
                  />
                </div>
              </fieldset>

              {/* ─── 분석 설정 ─── */}
              <fieldset className="space-y-3">
                <legend className="text-xs font-semibold uppercase tracking-wider text-text-muted mb-1">
                  분석 설정
                </legend>
                <div className="grid grid-cols-2 gap-4">
                  <Select
                    label="업종"
                    options={FDD_INDUSTRY_OPTIONS}
                    value={form.industry ?? ""}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        industry: (e.target.value || undefined) as
                          | IndustryType
                          | undefined,
                      })
                    }
                  />
                  <Select
                    label="통화"
                    options={CURRENCY_OPTIONS}
                    value={form.base_currency ?? ""}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        base_currency: e.target.value || undefined,
                      })
                    }
                  />
                </div>

                <Input
                  label="기준일"
                  type="date"
                  value={form.reference_date ?? ""}
                  onChange={(e) =>
                    setForm({ ...form, reference_date: e.target.value || undefined })
                  }
                />

                <div className="grid grid-cols-2 gap-4">
                  <Input
                    label="분석기간 시작"
                    type="date"
                    value={form.period_start ?? ""}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        period_start: e.target.value || undefined,
                      })
                    }
                  />
                  <Input
                    label="분석기간 종료"
                    type="date"
                    value={form.period_end ?? ""}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        period_end: e.target.value || undefined,
                      })
                    }
                  />
                </div>
              </fieldset>
            </div>
          )}
        </form>
      </Modal>
    </div>
  );
}
