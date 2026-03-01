/** Step 1: 템플릿 변수 기반 동적 폼 */

import { useMemo } from "react";
import type { TemplateVariable } from "@/modules/docs/types/contract_generation";

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

  // 인식 불가 패턴 → 숨김 (BE와 동일하게 false)
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
      className="mb-1 block text-xs font-medium text-text-secondary"
    >
      {v.question_label}
      {v.is_required && <span className="ml-0.5 text-negative">*</span>}
    </label>
  );

  const desc = v.description ? (
    <p className="mt-0.5 text-xs text-text-tertiary">{v.description}</p>
  ) : null;

  switch (v.input_type) {
    case "BOOLEAN":
      return (
        <div className="flex flex-col">
          <span className="mb-1 block text-xs font-medium text-text-secondary">
            {v.question_label}
            {v.is_required && <span className="ml-0.5 text-negative">*</span>}
          </span>
          <label
            htmlFor={id}
            className="flex items-center gap-2 cursor-pointer"
          >
            <input
              id={id}
              type="checkbox"
              checked={value === true || value === "true"}
              onChange={(e) => onChange(e.target.checked)}
              className="h-4 w-4 rounded border-border text-accent-primary focus:ring-accent-primary"
            />
            <span className="text-sm text-text-primary">예</span>
          </label>
          {desc}
        </div>
      );

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
            <option value="">선택하세요</option>
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

    case "NUMBER":
    case "CURRENCY":
    case "PERCENTAGE":
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
