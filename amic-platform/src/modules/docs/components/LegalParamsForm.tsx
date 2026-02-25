/**
 * 법률 문서 타입별 파라미터 입력 폼
 * SPA / SHA / BTA / SSA / MOU 각각 서브폼으로 분기
 *
 * 접근성: 모든 label + input 쌍을 htmlFor/id로 연결, aria-label 추가
 * 타입 안전성: 각 서브폼이 구체적 파라미터 인터페이스를 사용
 */
import { Plus, Trash2 } from "lucide-react";
import type {
  LegalDocType,
  SPAParameters,
  SHAParameters,
  BTAParameters,
  SSAParameters,
  MOUParameters,
  ShareholderEntry,
  BoardSeatEntry,
} from "@/modules/docs/types/legal_document";

const inputCls =
  "w-full rounded-lg border border-border bg-white px-3 py-2 text-sm text-text-primary " +
  "placeholder:text-text-placeholder focus:border-accent-primary focus:outline-none focus:ring-1 focus:ring-accent-primary";

// 접근성이 있는 label + input 조합 — label과 input을 htmlFor/id로 연결
function LabeledInput({
  label,
  required,
  ...inputProps
}: {
  label: string;
  required?: boolean;
} & React.InputHTMLAttributes<HTMLInputElement>) {
  // 렌더 당 stable한 ID 생성 (key prefix + label)
  const id = `lf-${label.replace(/[^a-z0-9]/gi, "_").toLowerCase()}-${Math.random().toString(36).slice(2, 6)}`;
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-xs font-medium text-text-secondary">
        {label}
        {required && (
          <span className="ml-0.5 text-negative" aria-label="필수">
            *
          </span>
        )}
      </label>
      <input id={id} className={inputCls} aria-required={required} {...inputProps} />
    </div>
  );
}

function LabeledTextarea({
  label,
  required,
  ...props
}: {
  label: string;
  required?: boolean;
} & React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const id = `lf-${label.replace(/[^a-z0-9]/gi, "_").toLowerCase()}-${Math.random().toString(36).slice(2, 6)}`;
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-xs font-medium text-text-secondary">
        {label}
        {required && (
          <span className="ml-0.5 text-negative" aria-label="필수">
            *
          </span>
        )}
      </label>
      <textarea
        id={id}
        className={`${inputCls} min-h-[80px] resize-none`}
        aria-required={required}
        {...props}
      />
    </div>
  );
}

// ── SPA 폼 ────────────────────────────────────────────────────────────────────

function SPAForm({
  params,
  onChange,
}: {
  params: Partial<SPAParameters>;
  onChange: (p: Partial<SPAParameters>) => void;
}) {
  const p = params;
  const str = (k: keyof SPAParameters, def = "") =>
    String(p[k] !== undefined ? p[k] : def);
  const num = (k: keyof SPAParameters, def = 0) =>
    Number(p[k] !== undefined ? p[k] : def);
  const set =
    (k: keyof SPAParameters) => (e: React.ChangeEvent<HTMLInputElement>) =>
      onChange({ ...p, [k]: e.target.value });
  const setNum =
    (k: keyof SPAParameters) => (e: React.ChangeEvent<HTMLInputElement>) =>
      onChange({ ...p, [k]: Number(e.target.value) });

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <LabeledInput label="매도인명" required value={str("seller_name")} onChange={set("seller_name")} placeholder="주식회사 ABC" />
      <LabeledInput label="매도인 대표이사" required value={str("seller_representative")} onChange={set("seller_representative")} placeholder="홍길동" />
      <LabeledInput label="매수인명" required value={str("buyer_name")} onChange={set("buyer_name")} placeholder="주식회사 XYZ" />
      <LabeledInput label="매수인 대표이사" required value={str("buyer_representative")} onChange={set("buyer_representative")} placeholder="김철수" />
      <LabeledInput label="대상회사명" required value={str("target_company_name")} onChange={set("target_company_name")} placeholder="주식회사 대상" />
      <LabeledInput label="법인등록번호" value={str("target_corp_reg_no")} onChange={set("target_corp_reg_no")} placeholder="110111-0000000" />
      <LabeledInput label="발행주식 총수" type="number" min={0} value={num("total_shares")} onChange={setNum("total_shares")} />
      <LabeledInput label="양도 주식 수" type="number" min={0} value={num("transfer_shares")} onChange={setNum("transfer_shares")} />
      <LabeledInput label="주당 양도가격 (원)" type="number" min={0} value={num("share_price_per")} onChange={setNum("share_price_per")} />
      <LabeledInput label="총 양도대금 (원)" type="number" min={0} value={num("total_purchase_price")} onChange={setNum("total_purchase_price")} />
      <LabeledInput label="계약 체결일" type="date" value={str("signing_date")} onChange={set("signing_date")} />
      <LabeledInput label="거래 종결일" type="date" value={str("closing_date")} onChange={set("closing_date")} />
      <LabeledInput label="진술보장 기간 (개월)" type="number" min={0} value={num("warranty_period_months", 24)} onChange={setNum("warranty_period_months")} />
      <LabeledInput label="에스크로 금액 (원)" type="number" min={0} value={num("escrow_amount")} onChange={setNum("escrow_amount")} />
      <LabeledInput label="에스크로 기간 (개월)" type="number" min={0} value={num("escrow_period_months", 18)} onChange={setNum("escrow_period_months")} />
      <LabeledInput label="준거법" value={str("governing_law", "대한민국")} onChange={set("governing_law")} />
    </div>
  );
}

// ── SHA 폼 ────────────────────────────────────────────────────────────────────

function SHAForm({
  params,
  onChange,
}: {
  params: Partial<SHAParameters>;
  onChange: (p: Partial<SHAParameters>) => void;
}) {
  const p = params;
  const str = (k: keyof SHAParameters, def = "") =>
    String(p[k] !== undefined ? p[k] : def);
  const num = (k: keyof SHAParameters, def = 0) =>
    Number(p[k] !== undefined ? p[k] : def);
  const set =
    (k: keyof SHAParameters) => (e: React.ChangeEvent<HTMLInputElement>) =>
      onChange({ ...p, [k]: e.target.value });
  const setNum =
    (k: keyof SHAParameters) => (e: React.ChangeEvent<HTMLInputElement>) =>
      onChange({ ...p, [k]: Number(e.target.value) });
  const setBool =
    (k: keyof SHAParameters) => (e: React.ChangeEvent<HTMLInputElement>) =>
      onChange({ ...p, [k]: e.target.checked });

  const shareholders: ShareholderEntry[] = (p.shareholders as ShareholderEntry[] | undefined) ?? [];
  const boardSeats: BoardSeatEntry[] = (p.board_seats_by_shareholder as BoardSeatEntry[] | undefined) ?? [];

  const addShareholder = () =>
    onChange({ ...p, shareholders: [...shareholders, { name: "", shares: 0, pct: 0 }] });
  const removeShareholder = (i: number) =>
    onChange({ ...p, shareholders: shareholders.filter((_, idx) => idx !== i) });
  const updateShareholder = (i: number, field: keyof ShareholderEntry, val: string | number) =>
    onChange({
      ...p,
      shareholders: shareholders.map((s, idx) => (idx === i ? { ...s, [field]: val } : s)),
    });

  const addBoardSeat = () =>
    onChange({ ...p, board_seats_by_shareholder: [...boardSeats, { shareholder: "", seats: 1 }] });
  const removeBoardSeat = (i: number) =>
    onChange({ ...p, board_seats_by_shareholder: boardSeats.filter((_, idx) => idx !== i) });
  const updateBoardSeat = (i: number, field: keyof BoardSeatEntry, val: string | number) =>
    onChange({
      ...p,
      board_seats_by_shareholder: boardSeats.map((b, idx) => (idx === i ? { ...b, [field]: val } : b)),
    });

  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <LabeledInput label="회사명" required value={str("company_name")} onChange={set("company_name")} placeholder="주식회사 대상" />
        <LabeledInput label="이사회 총 의석수" type="number" min={1} value={num("board_seats_total", 3)} onChange={setNum("board_seats_total")} />
        <LabeledInput label="락업 기간 (개월)" type="number" min={0} value={num("lock_up_months", 24)} onChange={setNum("lock_up_months")} />
        <LabeledInput label="경업금지 기간 (개월)" type="number" min={0} value={num("non_compete_months", 36)} onChange={setNum("non_compete_months")} />
        <LabeledInput label="계약 체결일" type="date" value={str("signing_date")} onChange={set("signing_date")} />
      </div>

      {/* 조항 포함 여부 */}
      <fieldset>
        <legend className="mb-2 text-xs font-medium text-text-secondary">포함 조항</legend>
        <div className="flex flex-wrap gap-5">
          {[
            { key: "rofr_included" as keyof SHAParameters, label: "우선매수권 (ROFR)" },
            { key: "drag_along_included" as keyof SHAParameters, label: "동반매각권 (Drag-Along)" },
            { key: "tag_along_included" as keyof SHAParameters, label: "동반참여권 (Tag-Along)" },
          ].map(({ key, label }) => {
            const checkId = `sha-${key}`;
            return (
              <label
                key={key}
                htmlFor={checkId}
                className="flex items-center gap-2 text-sm text-text-primary cursor-pointer"
              >
                <input
                  id={checkId}
                  type="checkbox"
                  checked={Boolean(p[key] !== undefined ? p[key] : true)}
                  onChange={setBool(key)}
                  className="h-4 w-4 rounded"
                />
                {label}
              </label>
            );
          })}
        </div>
      </fieldset>

      {/* 주주 목록 */}
      <fieldset>
        <div className="mb-2 flex items-center justify-between">
          <legend className="text-xs font-medium text-text-secondary">주주 목록</legend>
          <button
            type="button"
            onClick={addShareholder}
            className="flex items-center gap-1 text-xs text-accent-primary hover:underline"
            aria-label="주주 추가"
          >
            <Plus className="h-3 w-3" aria-hidden="true" /> 추가
          </button>
        </div>
        {shareholders.map((s, i) => (
          <div key={i} className="mb-2 grid grid-cols-4 gap-2">
            <input className={`col-span-2 ${inputCls}`} placeholder="주주명" value={s.name}
              onChange={(e) => updateShareholder(i, "name", e.target.value)}
              aria-label={`주주 ${i + 1} 이름`} />
            <input type="number" min={0} className={inputCls} placeholder="주식 수" value={s.shares}
              onChange={(e) => updateShareholder(i, "shares", Number(e.target.value))}
              aria-label={`주주 ${i + 1} 주식 수`} />
            <div className="flex gap-1">
              <input type="number" min={0} max={100} className={inputCls} placeholder="%" value={s.pct}
                onChange={(e) => updateShareholder(i, "pct", Number(e.target.value))}
                aria-label={`주주 ${i + 1} 지분율`} />
              <button type="button" onClick={() => removeShareholder(i)}
                className="text-red-400 hover:text-negative" aria-label={`주주 ${i + 1} 삭제`}>
                <Trash2 className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
          </div>
        ))}
      </fieldset>

      {/* 이사 지명권 */}
      <fieldset>
        <div className="mb-2 flex items-center justify-between">
          <legend className="text-xs font-medium text-text-secondary">주주별 이사 지명권</legend>
          <button
            type="button"
            onClick={addBoardSeat}
            className="flex items-center gap-1 text-xs text-accent-primary hover:underline"
            aria-label="이사 지명권 추가"
          >
            <Plus className="h-3 w-3" aria-hidden="true" /> 추가
          </button>
        </div>
        {boardSeats.map((b, i) => (
          <div key={i} className="mb-2 grid grid-cols-4 gap-2">
            <input className={`col-span-2 ${inputCls}`} placeholder="주주명" value={b.shareholder}
              onChange={(e) => updateBoardSeat(i, "shareholder", e.target.value)}
              aria-label={`이사 지명권 ${i + 1} 주주명`} />
            <div className="flex col-span-2 gap-1">
              <input type="number" min={0} className={inputCls} placeholder="의석수" value={b.seats}
                onChange={(e) => updateBoardSeat(i, "seats", Number(e.target.value))}
                aria-label={`이사 지명권 ${i + 1} 의석수`} />
              <button type="button" onClick={() => removeBoardSeat(i)}
                className="text-red-400 hover:text-negative" aria-label={`이사 지명권 ${i + 1} 삭제`}>
                <Trash2 className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
          </div>
        ))}
      </fieldset>
    </div>
  );
}

// ── BTA 폼 ────────────────────────────────────────────────────────────────────

function BTAForm({
  params,
  onChange,
}: {
  params: Partial<BTAParameters>;
  onChange: (p: Partial<BTAParameters>) => void;
}) {
  const p = params;
  const str = (k: keyof BTAParameters, def = "") =>
    String(p[k] !== undefined ? p[k] : def);
  const num = (k: keyof BTAParameters, def = 0) =>
    Number(p[k] !== undefined ? p[k] : def);
  const set =
    (k: keyof BTAParameters) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
      onChange({ ...p, [k]: e.target.value });
  const setNum =
    (k: keyof BTAParameters) => (e: React.ChangeEvent<HTMLInputElement>) =>
      onChange({ ...p, [k]: Number(e.target.value) });
  const setBool =
    (k: keyof BTAParameters) => (e: React.ChangeEvent<HTMLInputElement>) =>
      onChange({ ...p, [k]: e.target.checked });

  const assets: string[] = (p.transferred_assets as string[] | undefined) ?? [];
  const excl: string[] = (p.excluded_assets as string[] | undefined) ?? [];

  const addItem = (key: keyof BTAParameters, arr: string[]) => () =>
    onChange({ ...p, [key]: [...arr, ""] });
  const removeItem = (key: keyof BTAParameters, arr: string[], i: number) => () =>
    onChange({ ...p, [key]: arr.filter((_, idx) => idx !== i) });
  const updateItem = (key: keyof BTAParameters, arr: string[], i: number, val: string) =>
    onChange({ ...p, [key]: arr.map((a, idx) => (idx === i ? val : a)) });

  const checkId = "bta-employee_transfer";

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <LabeledInput label="양도인명" required value={str("transferor_name")} onChange={set("transferor_name")} />
        <LabeledInput label="양도인 대표이사" value={str("transferor_representative")} onChange={set("transferor_representative")} />
        <LabeledInput label="양수인명" required value={str("transferee_name")} onChange={set("transferee_name")} />
        <LabeledInput label="양수인 대표이사" value={str("transferee_representative")} onChange={set("transferee_representative")} />
        <LabeledInput label="양도 대금 (원)" type="number" min={0} value={num("total_consideration")} onChange={setNum("total_consideration")} />
        <LabeledInput label="이전 직원 수" type="number" min={0} value={num("employee_count")} onChange={setNum("employee_count")} />
        <LabeledInput label="계약 체결일" type="date" value={str("signing_date")} onChange={set("signing_date")} />
        <LabeledInput label="양도 실행일" type="date" value={str("closing_date")} onChange={set("closing_date")} />
      </div>

      <LabeledTextarea
        label="양도대상 사업 내용"
        required
        value={str("business_description")}
        onChange={set("business_description")}
      />

      <label htmlFor={checkId} className="flex items-center gap-2 text-sm text-text-primary cursor-pointer">
        <input
          id={checkId}
          type="checkbox"
          checked={Boolean(p.employee_transfer !== undefined ? p.employee_transfer : true)}
          onChange={setBool("employee_transfer")}
          className="h-4 w-4 rounded"
        />
        직원 이전 포함
      </label>

      {/* 이전 자산 */}
      <fieldset>
        <div className="mb-2 flex items-center justify-between">
          <legend className="text-xs font-medium text-text-secondary">이전 자산 목록</legend>
          <button type="button" onClick={addItem("transferred_assets", assets)}
            className="text-xs text-accent-primary hover:underline" aria-label="이전 자산 추가">
            + 추가
          </button>
        </div>
        {assets.map((a, i) => (
          <div key={i} className="mb-1 flex gap-2">
            <input className={inputCls} value={a}
              onChange={(e) => updateItem("transferred_assets", assets, i, e.target.value)}
              placeholder="자산명" aria-label={`이전 자산 ${i + 1}`} />
            <button type="button" onClick={removeItem("transferred_assets", assets, i)}
              className="text-red-400" aria-label={`이전 자산 ${i + 1} 삭제`}>
              <Trash2 className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
        ))}
      </fieldset>

      {/* 제외 자산 */}
      <fieldset>
        <div className="mb-2 flex items-center justify-between">
          <legend className="text-xs font-medium text-text-secondary">제외 자산 목록</legend>
          <button type="button" onClick={addItem("excluded_assets", excl)}
            className="text-xs text-accent-primary hover:underline" aria-label="제외 자산 추가">
            + 추가
          </button>
        </div>
        {excl.map((a, i) => (
          <div key={i} className="mb-1 flex gap-2">
            <input className={inputCls} value={a}
              onChange={(e) => updateItem("excluded_assets", excl, i, e.target.value)}
              placeholder="자산명" aria-label={`제외 자산 ${i + 1}`} />
            <button type="button" onClick={removeItem("excluded_assets", excl, i)}
              className="text-red-400" aria-label={`제외 자산 ${i + 1} 삭제`}>
              <Trash2 className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
        ))}
      </fieldset>
    </div>
  );
}

// ── SSA 폼 ────────────────────────────────────────────────────────────────────

function SSAForm({
  params,
  onChange,
}: {
  params: Partial<SSAParameters>;
  onChange: (p: Partial<SSAParameters>) => void;
}) {
  const p = params;
  const str = (k: keyof SSAParameters, def = "") =>
    String(p[k] !== undefined ? p[k] : def);
  const num = (k: keyof SSAParameters, def = 0) =>
    Number(p[k] !== undefined ? p[k] : def);
  const set =
    (k: keyof SSAParameters) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
      onChange({ ...p, [k]: e.target.value });
  const setNum =
    (k: keyof SSAParameters) => (e: React.ChangeEvent<HTMLInputElement>) =>
      onChange({ ...p, [k]: Number(e.target.value) });

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <LabeledInput label="발행 회사명" required value={str("company_name")} onChange={set("company_name")} />
      <LabeledInput label="회사 대표이사" value={str("company_representative")} onChange={set("company_representative")} />
      <LabeledInput label="인수인명" required value={str("investor_name")} onChange={set("investor_name")} />
      <LabeledInput label="인수인 대표이사" value={str("investor_representative")} onChange={set("investor_representative")} />
      <LabeledInput label="발행 신주 수" type="number" min={0} value={num("new_shares_count")} onChange={setNum("new_shares_count")} />
      <LabeledInput label="주당 인수가액 (원)" type="number" min={0} value={num("subscription_price_per")} onChange={setNum("subscription_price_per")} />
      <LabeledInput label="총 인수대금 (원)" type="number" min={0} value={num("total_investment")} onChange={setNum("total_investment")} />
      <LabeledInput label="주식 종류" value={str("share_class", "보통주")} onChange={set("share_class")} placeholder="보통주 / 우선주" />
      <LabeledInput label="Pre-money 기업가치 (원)" type="number" min={0} value={num("pre_money_valuation")} onChange={setNum("pre_money_valuation")} />
      <LabeledInput label="Post-money 기업가치 (원)" type="number" min={0} value={num("post_money_valuation")} onChange={setNum("post_money_valuation")} />
      <LabeledInput label="청산우선권 배수 (x)" type="number" step={0.1} min={0} value={num("liquidation_preference_x", 1)} onChange={setNum("liquidation_preference_x")} />
      <LabeledInput label="이사 지명권 수" type="number" min={0} value={num("board_seats", 1)} onChange={setNum("board_seats")} />
      <LabeledInput label="계약 체결일" type="date" value={str("signing_date")} onChange={set("signing_date")} />
      <LabeledInput label="납입 기일" type="date" value={str("investment_date")} onChange={set("investment_date")} />
      <div className="col-span-full">
        <LabeledTextarea
          label="자금 사용 목적"
          value={str("use_of_proceeds")}
          onChange={set("use_of_proceeds")}
          placeholder="자금 사용 목적을 입력하세요"
        />
      </div>
    </div>
  );
}

// ── MOU 폼 ────────────────────────────────────────────────────────────────────

function MOUForm({
  params,
  onChange,
}: {
  params: Partial<MOUParameters>;
  onChange: (p: Partial<MOUParameters>) => void;
}) {
  const p = params;
  const str = (k: keyof MOUParameters, def = "") =>
    String(p[k] !== undefined ? p[k] : def);
  const num = (k: keyof MOUParameters, def = 0) =>
    Number(p[k] !== undefined ? p[k] : def);
  const set =
    (k: keyof MOUParameters) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
      onChange({ ...p, [k]: e.target.value });
  const setNum =
    (k: keyof MOUParameters) => (e: React.ChangeEvent<HTMLInputElement>) =>
      onChange({ ...p, [k]: Number(e.target.value) });

  const bindingArr: string[] = (p.binding_provisions as string[] | undefined) ?? ["비밀유지", "독점협상"];
  const nonBindingArr: string[] = (p.non_binding_provisions as string[] | undefined) ?? ["가격협상", "거래구조"];

  const addItem = (key: keyof MOUParameters, arr: string[]) => () =>
    onChange({ ...p, [key]: [...arr, ""] });
  const removeItem = (key: keyof MOUParameters, arr: string[], i: number) => () =>
    onChange({ ...p, [key]: arr.filter((_, idx) => idx !== i) });
  const updateItem = (key: keyof MOUParameters, arr: string[], i: number, val: string) =>
    onChange({ ...p, [key]: arr.map((a, idx) => (idx === i ? val : a)) });

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <LabeledInput label="당사자 갑 (회사명)" required value={str("party_a_name")} onChange={set("party_a_name")} />
        <LabeledInput label="갑 대표이사" value={str("party_a_representative")} onChange={set("party_a_representative")} />
        <LabeledInput label="당사자 을 (회사명)" required value={str("party_b_name")} onChange={set("party_b_name")} />
        <LabeledInput label="을 대표이사" value={str("party_b_representative")} onChange={set("party_b_representative")} />
        <LabeledInput label="독점협상기간 (일)" type="number" min={0} value={num("exclusivity_period_days", 90)} onChange={setNum("exclusivity_period_days")} />
        <LabeledInput label="독점협상 시작일" type="date" value={str("exclusivity_start_date")} onChange={set("exclusivity_start_date")} />
        <LabeledInput label="비밀유지 기간 (개월)" type="number" min={0} value={num("confidentiality_period_months", 24)} onChange={setNum("confidentiality_period_months")} />
        <LabeledInput label="체결일" type="date" value={str("signing_date")} onChange={set("signing_date")} />
      </div>

      <LabeledTextarea
        label="목적"
        required
        value={str("purpose")}
        onChange={set("purpose")}
        placeholder="양해각서 목적을 입력하세요"
      />

      {/* 구속력 있는 조항 */}
      <fieldset>
        <div className="mb-2 flex items-center justify-between">
          <legend className="text-xs font-medium text-text-secondary">구속력 있는 조항</legend>
          <button type="button" onClick={addItem("binding_provisions", bindingArr)}
            className="text-xs text-accent-primary hover:underline" aria-label="구속 조항 추가">
            + 추가
          </button>
        </div>
        {bindingArr.map((a, i) => (
          <div key={i} className="mb-1 flex gap-2">
            <input className={inputCls} value={a}
              onChange={(e) => updateItem("binding_provisions", bindingArr, i, e.target.value)}
              placeholder="조항명" aria-label={`구속 조항 ${i + 1}`} />
            <button type="button" onClick={removeItem("binding_provisions", bindingArr, i)}
              className="text-red-400" aria-label={`구속 조항 ${i + 1} 삭제`}>
              <Trash2 className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
        ))}
      </fieldset>

      {/* 비구속적 조항 */}
      <fieldset>
        <div className="mb-2 flex items-center justify-between">
          <legend className="text-xs font-medium text-text-secondary">비구속적 조항</legend>
          <button type="button" onClick={addItem("non_binding_provisions", nonBindingArr)}
            className="text-xs text-accent-primary hover:underline" aria-label="비구속 조항 추가">
            + 추가
          </button>
        </div>
        {nonBindingArr.map((a, i) => (
          <div key={i} className="mb-1 flex gap-2">
            <input className={inputCls} value={a}
              onChange={(e) => updateItem("non_binding_provisions", nonBindingArr, i, e.target.value)}
              placeholder="조항명" aria-label={`비구속 조항 ${i + 1}`} />
            <button type="button" onClick={removeItem("non_binding_provisions", nonBindingArr, i)}
              className="text-red-400" aria-label={`비구속 조항 ${i + 1} 삭제`}>
              <Trash2 className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
        ))}
      </fieldset>
    </div>
  );
}

// ── 메인 분기 컴포넌트 ─────────────────────────────────────────────────────────

interface LegalParamsFormProps {
  docType: LegalDocType;
  params: Record<string, unknown>;
  onChange: (params: Record<string, unknown>) => void;
}

// 외부 인터페이스는 Record<string, unknown>을 유지하고, 내부에서 타입별로 캐스팅한다
export default function LegalParamsForm({ docType, params, onChange }: LegalParamsFormProps) {
  switch (docType) {
    case "SPA":
      return (
        <SPAForm
          params={params as Partial<SPAParameters>}
          onChange={onChange as (p: Partial<SPAParameters>) => void}
        />
      );
    case "SHA":
      return (
        <SHAForm
          params={params as Partial<SHAParameters>}
          onChange={onChange as (p: Partial<SHAParameters>) => void}
        />
      );
    case "BTA":
      return (
        <BTAForm
          params={params as Partial<BTAParameters>}
          onChange={onChange as (p: Partial<BTAParameters>) => void}
        />
      );
    case "SSA":
      return (
        <SSAForm
          params={params as Partial<SSAParameters>}
          onChange={onChange as (p: Partial<SSAParameters>) => void}
        />
      );
    case "MOU":
      return (
        <MOUForm
          params={params as Partial<MOUParameters>}
          onChange={onChange as (p: Partial<MOUParameters>) => void}
        />
      );
  }
}
