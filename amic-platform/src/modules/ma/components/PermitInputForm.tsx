import { useState } from "react";
import { Plus, Trash2, Search } from "lucide-react";
import { Button, CheckboxGroup, Input } from "@/components/ui";
import type { ExistingPermit, IndustryOption } from "@/modules/ma/types/permit";

// KB sub_category 코드 → 한글 라벨 매핑
const SUB_CATEGORY_LABELS: Record<string, string> = {
  FINANCE_BANK: "은행",
  FINANCE_INSURANCE: "보험",
  FINANCE_SECURITIES: "증권",
  FINANCE_CREDIT: "여신전문",
  TELECOM_BASIC: "기간통신",
  TELECOM_VALUE_ADDED: "부가통신",
  CONSTRUCTION_GENERAL: "일반건설",
  HEALTHCARE_HOSPITAL: "병원",
  HEALTHCARE_PHARMACY: "약국/의약품",
  FOOD_MANUFACTURING: "식품제조",
  FOOD_RESTAURANT: "외식업",
  ENVIRONMENT_WASTE: "폐기물",
  ENVIRONMENT_WATER: "수질",
  ENERGY_POWER: "발전",
  ENERGY_GAS: "가스",
  BROADCASTING_TV: "TV/종편",
  BROADCASTING_CABLE: "케이블/IPTV",
  TRANSPORT_FREIGHT: "화물",
  TRANSPORT_PASSENGER: "여객",
  EDUCATION_SCHOOL: "학교",
  EDUCATION_ACADEMY: "학원",
  MANUFACTURING_GENERAL: "일반제조",
  IT_GENERAL: "일반",
};

interface PermitInputFormProps {
  industries: IndustryOption[];
  onSubmit: (businessTypes: string[], existingPermits: ExistingPermit[]) => void;
  isPending: boolean;
}

export default function PermitInputForm({
  industries,
  onSubmit,
  isPending,
}: PermitInputFormProps) {
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  const [existingPermits, setExistingPermits] = useState<ExistingPermit[]>([]);
  const [search, setSearch] = useState("");

  const addExistingPermit = () => {
    setExistingPermits((prev) => [
      ...prev,
      { name: "", issuer: "", reg_number: "" },
    ]);
  };

  const updatePermit = (
    idx: number,
    field: keyof ExistingPermit,
    value: string,
  ) => {
    setExistingPermits((prev) =>
      prev.map((p, i) => (i === idx ? { ...p, [field]: value } : p)),
    );
  };

  const removePermit = (idx: number) => {
    setExistingPermits((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleSubmit = () => {
    if (selectedTypes.length === 0) return;
    const cleaned = existingPermits.filter((p) => p.name.trim());
    onSubmit(selectedTypes, cleaned);
  };

  // Build flat options from industries + sub_categories
  const options = industries.flatMap((ind) => {
    if (!ind.sub_categories?.length) {
      return [{ value: ind.code, label: ind.label }];
    }
    return ind.sub_categories.map((sub) => ({
      value: sub,
      label: `${ind.label} — ${SUB_CATEGORY_LABELS[sub] ?? sub}`,
    }));
  });

  const filtered = search
    ? options.filter(
        (o) =>
          o.label.toLowerCase().includes(search.toLowerCase()) ||
          o.value.toLowerCase().includes(search.toLowerCase()),
      )
    : options;

  return (
    <div className="space-y-5">
      {/* 업종 선택 */}
      <div>
        <label className="block text-sm font-medium text-text-body mb-2">
          대상기업 업종 (복수 선택 가능)
        </label>
        <div className="relative mb-2">
          <Search
            size={14}
            className="absolute left-2.5 top-1/2 -translate-y-1/2 text-text-muted"
          />
          <input
            type="text"
            placeholder="업종 검색..."
            className="w-full pl-8 pr-3 py-1.5 text-sm border border-gray-border rounded-dr-sm focus:ring-2 focus:ring-accent/30 focus:outline-none bg-bg-base"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="max-h-48 overflow-y-auto border border-gray-border rounded-dr-sm p-3 bg-bg-base">
          <CheckboxGroup
            label=""
            options={filtered}
            selected={selectedTypes}
            onChange={setSelectedTypes}
            layout="vertical"
          />
          {filtered.length === 0 && (
            <p className="text-xs text-text-muted py-2">
              검색 결과가 없습니다.
            </p>
          )}
        </div>
        {selectedTypes.length > 0 && (
          <p className="mt-1 text-xs text-text-muted">
            {selectedTypes.length}개 업종 선택됨
          </p>
        )}
      </div>

      {/* 기존 보유 인허가 */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-sm font-medium text-text-body">
            기존 보유 인허가 (선택)
          </label>
          <button
            type="button"
            onClick={addExistingPermit}
            className="flex items-center gap-1 text-xs text-accent hover:text-amic-700 transition-colors"
          >
            <Plus size={12} />
            추가
          </button>
        </div>
        {existingPermits.length === 0 ? (
          <p className="text-xs text-text-muted">
            기존 보유 인허가가 없으면 비워두셔도 됩니다.
          </p>
        ) : (
          <div className="space-y-2">
            {existingPermits.map((permit, idx) => (
              <div key={idx} className="flex items-center gap-2">
                <Input
                  label=""
                  placeholder="인허가명"
                  value={permit.name}
                  onChange={(e) => updatePermit(idx, "name", e.target.value)}
                  className="flex-1"
                />
                <Input
                  label=""
                  placeholder="발급기관"
                  value={permit.issuer}
                  onChange={(e) => updatePermit(idx, "issuer", e.target.value)}
                  className="flex-1"
                />
                <Input
                  label=""
                  placeholder="등록번호 (선택)"
                  value={permit.reg_number ?? ""}
                  onChange={(e) =>
                    updatePermit(idx, "reg_number", e.target.value)
                  }
                  className="flex-1"
                />
                <button
                  type="button"
                  onClick={() => removePermit(idx)}
                  className="p-1.5 text-text-muted hover:text-negative rounded transition-colors"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 분석 실행 */}
      <Button
        onClick={handleSubmit}
        disabled={selectedTypes.length === 0 || isPending}
        className="w-full"
      >
        {isPending ? "분석 중..." : "인허가 분석 실행"}
      </Button>
    </div>
  );
}
