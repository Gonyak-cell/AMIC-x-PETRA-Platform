/** Step 1: 템플릿 변수 기반 동적 폼 */

import { useMemo } from "react";
import type { TemplateVariable } from "@/modules/docs/types/contract_generation";
import { formatAmount } from "@/lib/format";

interface DynamicVariableFormProps {
  variables: TemplateVariable[];
  values: Record<string, unknown>;
  onChange: (key: string, value: unknown) => void;
}

/** 조건식을 평가한다 (프론트엔드용).
 *
 * 지원 패턴:
 *  - key == True / key == False  (불리언)
 *  - not key                     (불리언 부정)
 *  - key == "문자열"             (문자열 동등)
 *  - key > 123 / key >= / < / <= (숫자 비교)
 *  - key in ["v1", "v2"]        (멤버십 검사)
 *  - key not in ["v1", "v2"]    (비멤버십 검사)
 *  - expr1 and expr2 / expr1 or expr2 (논리 조합)
 *
 * ⚠️ and가 or보다 우선순위 높음 (Python 동일)
 *
 * 🔗 BE 동기화 필수: deal-mgmt/app/services/contract_generation_service.py
 *    `evaluate_condition()` 함수와 동일한 패턴을 지원해야 한다.
 *    BE에 새 연산자를 추가하면 여기에도 반드시 반영할 것.
 */
function evalCondition(
  expr: string | null,
  vars: Record<string, unknown>,
): boolean {
  if (!expr) return true;

  // OR 분리 (낮은 우선순위)
  if (/\bor\b/i.test(expr)) {
    return expr
      .split(/\bor\b/i)
      .some((part) => evalAndGroup(part.trim(), vars));
  }

  return evalAndGroup(expr, vars);
}

/** and로 연결된 그룹을 평가한다. */
function evalAndGroup(expr: string, vars: Record<string, unknown>): boolean {
  if (/\band\b/i.test(expr)) {
    return expr
      .split(/\band\b/i)
      .every((part) => evalSingle(part.trim(), vars));
  }
  return evalSingle(expr, vars);
}

function evalSingle(expr: string, vars: Record<string, unknown>): boolean {
  // not 연산자: not key
  const notMatch = expr.match(/^not\s+(\w+)$/i);
  if (notMatch) {
    const val = vars[notMatch[1]];
    return !val || val === "false" || val === "False";
  }

  // 불리언: key == True / key == False
  const boolMatch = expr.match(/^(\w+)\s*==\s*(True|False)$/);
  if (boolMatch) {
    const val = vars[boolMatch[1]];
    const expected = boolMatch[2] === "True";
    return val === expected || val === String(expected).toLowerCase();
  }

  // 문자열 동등: key == "value"
  const strMatch = expr.match(/^(\w+)\s*==\s*"([^"]*)"$/);
  if (strMatch) {
    return String(vars[strMatch[1]] ?? "") === strMatch[2];
  }

  // 숫자 비교: key (>|>=|<|<=|==|!=) number
  const numMatch = expr.match(/^(\w+)\s*(>=|<=|!=|>|<|==)\s*(\d+(?:\.\d+)?)$/);
  if (numMatch) {
    const val = Number(vars[numMatch[1]]);
    const op = numMatch[2];
    const num = Number(numMatch[3]);
    if (Number.isNaN(val)) return false;
    switch (op) {
      case ">":
        return val > num;
      case ">=":
        return val >= num;
      case "<":
        return val < num;
      case "<=":
        return val <= num;
      case "==":
        return val === num;
      case "!=":
        return val !== num;
      default:
        return false;
    }
  }

  // in 연산자: key in ["val1", "val2"]
  const inMatch = expr.match(/^(\w+)\s+in\s+\[([^\]]*)\]$/);
  if (inMatch) {
    const raw = inMatch[2].trim();
    if (!raw) return false; // 빈 리스트 → Python과 동일하게 false
    const val = String(vars[inMatch[1]] ?? "");
    const items = raw
      .split(",")
      .map((s) => s.trim().replace(/^"|"$/g, "").replace(/^'|'$/g, ""));
    return items.includes(val);
  }

  // not in 연산자: key not in ["val1", "val2"]
  const notInMatch = expr.match(/^(\w+)\s+not\s+in\s+\[([^\]]*)\]$/);
  if (notInMatch) {
    const raw = notInMatch[2].trim();
    if (!raw) return true; // 빈 리스트 → Python과 동일하게 true
    const val = String(vars[notInMatch[1]] ?? "");
    const items = raw
      .split(",")
      .map((s) => s.trim().replace(/^"|"$/g, "").replace(/^'|'$/g, ""));
    return !items.includes(val);
  }

  // 인식 불가 패턴 → 숨김 (BE와 동일하게 false)
  if (import.meta.env.DEV) {
    console.warn(`[evalCondition] 인식할 수 없는 조건식: "${expr}"`);
  }
  return false;
}

export default function DynamicVariableForm({
  variables,
  values,
  onChange,
}: DynamicVariableFormProps) {
  // 그룹별로 분류
  const grouped = useMemo(() => {
    const map = new Map<string, TemplateVariable[]>();
    const sorted = [...variables].sort(
      (a, b) => a.display_order - b.display_order,
    );
    for (const v of sorted) {
      const group = v.group_name ?? "기타";
      if (!map.has(group)) map.set(group, []);
      map.get(group)!.push(v);
    }
    return map;
  }, [variables]);

  return (
    <div className="flex flex-col gap-6">
      {Array.from(grouped.entries()).map(([groupName, vars]) => (
        <fieldset
          key={groupName}
          className="rounded-xl border border-border p-4"
        >
          <legend className="px-2 text-xs font-semibold text-text-secondary">
            {groupName}
          </legend>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {vars.map((v) => {
              if (!evalCondition(v.visible_condition, values)) return null;
              return (
                <VariableInput
                  key={v.id}
                  variable={v}
                  value={values[v.variable_key]}
                  onChange={(val) => onChange(v.variable_key, val)}
                />
              );
            })}
          </div>
        </fieldset>
      ))}
    </div>
  );
}

// ── 개별 입력 필드 ──────────────────────────────────────────────────────

interface VariableInputProps {
  variable: TemplateVariable;
  value: unknown;
  onChange: (value: unknown) => void;
}

function VariableInput({ variable: v, value, onChange }: VariableInputProps) {
  const id = `var-${v.variable_key}`;
  const strVal = value != null ? String(value) : "";
  const baseInput =
    "w-full rounded-lg border border-border bg-white px-3 py-2 text-sm text-text-primary placeholder:text-text-tertiary focus:border-accent-primary focus:outline-none focus:ring-1 focus:ring-accent-primary";

  const label = (
    <label
      htmlFor={id}
      className="mb-1.5 block text-xs font-medium text-text-secondary"
    >
      {v.question_label}
      {v.is_required && <span className="ml-0.5 text-negative">*</span>}
    </label>
  );

  const desc = v.description ? (
    <p className="mt-0.5 text-xs text-text-tertiary">{v.description}</p>
  ) : null;

  switch (v.input_type) {
    case "BOOLEAN": {
      const checked = value === true || value === "true";
      return (
        <div className="flex flex-col">
          <span className="mb-1.5 block text-xs font-medium text-text-secondary">
            {v.question_label}
            {v.is_required && <span className="ml-0.5 text-negative">*</span>}
          </span>
          <div className="flex items-center gap-3">
            <button
              id={id}
              type="button"
              role="switch"
              aria-checked={checked}
              aria-label={v.question_label}
              onClick={() => onChange(!checked)}
              className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-accent-primary focus:ring-offset-2 ${
                checked ? "bg-accent-primary" : "bg-gray-300"
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  checked ? "translate-x-6" : "translate-x-1"
                }`}
              />
            </button>
            <span className="text-sm text-text-primary">
              {checked ? "예" : "아니오"}
            </span>
          </div>
          {desc}
        </div>
      );
    }

    case "TEXTAREA":
      return (
        <div className="col-span-full flex flex-col">
          {label}
          <textarea
            id={id}
            value={strVal}
            onChange={(e) => onChange(e.target.value)}
            rows={3}
            className={baseInput}
            placeholder={v.default_value ?? ""}
            required={v.is_required}
          />
          {desc}
        </div>
      );

    case "SELECT":
      return (
        <div className="flex flex-col">
          {label}
          <select
            id={id}
            value={strVal}
            onChange={(e) => onChange(e.target.value)}
            className={baseInput}
            required={v.is_required}
            aria-required={v.is_required}
          >
            <option value="" disabled>
              선택하세요
            </option>
            {v.select_options &&
              Object.entries(v.select_options).map(([key, displayLabel]) => (
                <option key={key} value={key}>
                  {displayLabel}
                </option>
              ))}
          </select>
          {desc}
        </div>
      );

    case "DATE":
      return (
        <div className="flex flex-col">
          {label}
          <input
            id={id}
            type="date"
            value={strVal}
            onChange={(e) => onChange(e.target.value)}
            className={baseInput}
            required={v.is_required}
          />
          {desc}
        </div>
      );

    case "CURRENCY": {
      const numVal = strVal ? Number(strVal) : 0;
      return (
        <div className="flex flex-col">
          {label}
          <div className="relative">
            <input
              id={id}
              type="number"
              value={strVal}
              onChange={(e) =>
                onChange(e.target.value ? Number(e.target.value) : null)
              }
              className={baseInput + " pr-8"}
              placeholder={v.default_value ?? ""}
              required={v.is_required}
            />
            <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-xs text-text-tertiary">
              원
            </span>
          </div>
          {numVal > 0 && (
            <p className="mt-0.5 text-xs text-text-tertiary">
              {formatAmount(numVal, "KRW")}원
            </p>
          )}
          {desc}
        </div>
      );
    }

    case "PERCENTAGE":
      return (
        <div className="flex flex-col">
          {label}
          <div className="relative">
            <input
              id={id}
              type="number"
              step="0.01"
              value={strVal}
              onChange={(e) =>
                onChange(e.target.value ? Number(e.target.value) : null)
              }
              className={baseInput + " pr-8"}
              placeholder={v.default_value ?? ""}
              required={v.is_required}
            />
            <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-xs text-text-tertiary">
              %
            </span>
          </div>
          {desc}
        </div>
      );

    case "NUMBER":
      return (
        <div className="flex flex-col">
          {label}
          <input
            id={id}
            type="number"
            value={strVal}
            onChange={(e) =>
              onChange(e.target.value ? Number(e.target.value) : null)
            }
            className={baseInput}
            placeholder={v.default_value ?? ""}
            required={v.is_required}
          />
          {desc}
        </div>
      );

    default:
      return (
        <div className="flex flex-col">
          {label}
          <input
            id={id}
            type="text"
            value={strVal}
            onChange={(e) => onChange(e.target.value)}
            className={baseInput}
            placeholder={v.default_value ?? ""}
            required={v.is_required}
          />
          {desc}
        </div>
      );
  }
}
