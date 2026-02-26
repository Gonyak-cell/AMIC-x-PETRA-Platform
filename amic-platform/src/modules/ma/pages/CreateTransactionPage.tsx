import { useState } from "react";
import { useNavigate, Navigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { ArrowLeft, ChevronDown } from "lucide-react";

import { useCreateTransaction } from "@/modules/ma/hooks/useTransactions";
import type { TransactionCreate, DealStructure, InvestmentType } from "@/modules/ma/types/transaction";
import {
  TRANSACTION_SIDE_OPTIONS,
  CURRENCY_OPTIONS,
  DEAL_STRUCTURE_OPTIONS,
  INVESTMENT_TYPE_OPTIONS,
} from "@/modules/ma/constants";

import { Button, Card, Input, Select, PageHero } from "@/components/ui";
import heroImg from "@/assets/images/heroes/hero-arch-blue-wave.jpg";

const SIDE_OPTIONS = TRANSACTION_SIDE_OPTIONS.filter((o) => o.value !== "");

const INITIAL: TransactionCreate = {
  name: "",
  code_name: "",
  side: "SELL",
  target_company_name: "",
  client_name: "",
  lead_advisor_email: "",
};

export default function CreateTransactionPage() {
  const navigate = useNavigate();
  const { isClient } = useAuth();
  const createTxn = useCreateTransaction();
  const [form, setForm] = useState<TransactionCreate>(INITIAL);
  const [showOptional, setShowOptional] = useState(false);

  if (isClient) return <Navigate to="/ma/transactions" replace />;

  const set = <K extends keyof TransactionCreate>(
    key: K,
    val: TransactionCreate[K],
  ) => setForm((prev) => ({ ...prev, [key]: val }));

  const canSubmit =
    form.name.trim() &&
    form.code_name.trim() &&
    form.target_company_name.trim() &&
    form.client_name.trim() &&
    form.lead_advisor_email.trim();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    createTxn.mutate(form, {
      onSuccess: (txn) => navigate(`/ma/transactions/${txn.id}`),
    });
  };

  return (
    <div className="space-y-6">
      <PageHero title="New Transaction" subtitle="새 M&A 거래 생성" backgroundImage={heroImg} backgroundOpacity={0.18} compact />

      <div className="max-w-2xl mx-auto">
        <Button
          variant="ghost"
          icon={ArrowLeft}
          onClick={() => navigate("/ma/transactions")}
          className="mb-4"
        >
          목록으로
        </Button>

        <Card title="기본 정보" headerBar>
          <form
            id="create-txn"
            onSubmit={handleSubmit}
            className="space-y-5 p-1"
          >
            {/* 필수 필드 */}
            <fieldset className="space-y-4">
              <legend className="text-xs font-semibold uppercase tracking-wider text-text-muted mb-1">
                Required
              </legend>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Input
                  label="거래명"
                  required
                  value={form.name}
                  onChange={(e) => set("name", e.target.value)}
                  placeholder="프로젝트 명칭"
                />
                <Input
                  label="코드네임"
                  required
                  value={form.code_name}
                  onChange={(e) => set("code_name", e.target.value)}
                  placeholder="보안 코드 (예: Project Phoenix)"
                />
              </div>

              <Select
                label="자문 유형"
                options={SIDE_OPTIONS}
                value={form.side}
                onChange={(e) => set("side", e.target.value as TransactionCreate["side"])}
              />

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Input
                  label="대상 기업"
                  required
                  value={form.target_company_name}
                  onChange={(e) => set("target_company_name", e.target.value)}
                  placeholder="인수/매각 대상 기업명"
                />
                <Input
                  label="클라이언트"
                  required
                  value={form.client_name}
                  onChange={(e) => set("client_name", e.target.value)}
                  placeholder="의뢰인 명칭"
                />
              </div>

              <Input
                label="리드 어드바이저 이메일"
                type="email"
                required
                value={form.lead_advisor_email}
                onChange={(e) => set("lead_advisor_email", e.target.value)}
                placeholder="advisor@company.com"
              />
            </fieldset>

            {/* 선택 필드 토글 */}
            <button
              type="button"
              aria-expanded={showOptional}
              onClick={() => setShowOptional(!showOptional)}
              className="flex items-center gap-1.5 text-sm font-medium text-accent hover:text-accent/80 transition-colors"
            >
              <ChevronDown
                size={16}
                className={`transition-transform ${showOptional ? "rotate-180" : ""}`}
              />
              {showOptional ? "옵션 접기" : "추가 정보 입력"}
            </button>

            {showOptional && (
              <fieldset className="space-y-4 animate-fade-in">
                <legend className="text-xs font-semibold uppercase tracking-wider text-text-muted mb-1">
                  Optional
                </legend>

                <Input
                  label="DART Corp Code"
                  value={form.target_corp_code ?? ""}
                  onChange={(e) =>
                    set("target_corp_code", e.target.value || undefined)
                  }
                  placeholder="8자리 기업 코드"
                />

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Select
                    label="딜 구조"
                    options={DEAL_STRUCTURE_OPTIONS}
                    value={form.deal_structure ?? ""}
                    onChange={(e) =>
                      set("deal_structure", (e.target.value || undefined) as DealStructure | undefined)
                    }
                  />
                  <Select
                    label="투자 유형"
                    options={INVESTMENT_TYPE_OPTIONS}
                    value={form.investment_type ?? ""}
                    onChange={(e) =>
                      set("investment_type", (e.target.value || undefined) as InvestmentType | undefined)
                    }
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Input
                    label="예상 거래 금액"
                    type="number"
                    value={
                      form.estimated_deal_value != null
                        ? String(form.estimated_deal_value)
                        : ""
                    }
                    onChange={(e) =>
                      set(
                        "estimated_deal_value",
                        e.target.value ? Number(e.target.value) : undefined,
                      )
                    }
                    placeholder="0"
                  />
                  <Select
                    label="통화"
                    options={CURRENCY_OPTIONS}
                    value={form.currency ?? "KRW"}
                    onChange={(e) => set("currency", e.target.value as TransactionCreate["currency"])}
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Input
                    label="산업"
                    value={form.industry ?? ""}
                    onChange={(e) =>
                      set("industry", e.target.value || undefined)
                    }
                    placeholder="산업 분류"
                  />
                  <Input
                    label="목표 종결일"
                    type="date"
                    value={form.target_close_date ?? ""}
                    onChange={(e) =>
                      set("target_close_date", e.target.value || undefined)
                    }
                  />
                </div>

                <Input
                  label="딜 캡틴 이메일"
                  type="email"
                  value={form.deal_captain_email ?? ""}
                  onChange={(e) =>
                    set("deal_captain_email", e.target.value || undefined)
                  }
                  placeholder="captain@company.com"
                />
              </fieldset>
            )}

            {/* 제출 */}
            <div className="flex justify-end gap-3 pt-4 border-t">
              <Button
                variant="ghost"
                type="button"
                onClick={() => navigate("/ma/transactions")}
              >
                취소
              </Button>
              <Button
                type="submit"
                disabled={!canSubmit}
                loading={createTxn.isPending}
              >
                거래 생성
              </Button>
            </div>
          </form>
        </Card>
      </div>
    </div>
  );
}
