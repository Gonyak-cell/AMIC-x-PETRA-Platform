/** SPA 분석 리뷰 패널 — 변수/조항 테이블 (편집·삭제·추가) */

import { Fragment, useCallback, useMemo, useState } from "react";
import {
  ChevronDown,
  ChevronUp,
  Plus,
  Trash2,
  Eye,
  EyeOff,
} from "lucide-react";

/** LLM 생성 HTML에서 위험 요소를 제거한다. */
function sanitizeHtml(html: string): string {
  const doc = new DOMParser().parseFromString(html, "text/html");
  doc
    .querySelectorAll("script,style,iframe,object,embed,link")
    .forEach((el) => el.remove());
  doc.querySelectorAll("*").forEach((el) => {
    for (const attr of [...el.attributes]) {
      if (
        attr.name.startsWith("on") ||
        attr.value.trim().toLowerCase().startsWith("javascript:")
      ) {
        el.removeAttribute(attr.name);
      }
    }
  });
  return doc.body.innerHTML;
}
import type {
  ExtractedVariable,
  AnalyzedClause,
  IndustryType,
  ShaType,
  ExitStrategy,
  BtaScope,
  SeverancePayHandling,
  SsaSecurityType,
  SsaTransactionContext,
  MouTransactionType,
  MouDepositHandling,
} from "@/modules/docs/types/spa_analysis";
import {
  DEAL_STRUCTURES,
  DEAL_STRUCTURE_LABELS,
  INDUSTRY_TYPES,
  INDUSTRY_TYPE_LABELS,
  SHA_TYPES,
  SHA_TYPE_LABELS,
  EXIT_STRATEGIES,
  EXIT_STRATEGY_LABELS,
  BTA_SCOPES,
  BTA_SCOPE_LABELS,
  SEVERANCE_PAY_HANDLING,
  SEVERANCE_PAY_LABELS,
  SSA_SECURITY_TYPES,
  SSA_SECURITY_TYPE_LABELS,
  SSA_TRANSACTION_CONTEXTS,
  SSA_TRANSACTION_CONTEXT_LABELS,
  MOU_TRANSACTION_TYPES,
  MOU_TRANSACTION_TYPE_LABELS,
  MOU_DEPOSIT_HANDLING,
  MOU_DEPOSIT_HANDLING_LABELS,
} from "@/modules/docs/types/spa_analysis";

// ── 변수 리뷰 ─────────────────────────────────────────────────────────────

interface VariableReviewProps {
  variables: ExtractedVariable[];
  dealStructure: string; // DealStructure | ShaType
  industryType: IndustryType;
  onVariablesChange: (vars: ExtractedVariable[]) => void;
  onDealStructureChange: (v: string) => void;
  onIndustryTypeChange: (v: IndustryType) => void;
  /** SHA 모드일 때 분류 섹션을 숨긴다 (ShaClassificationPanel 사용 시) */
  hideClassification?: boolean;
}

export function VariableReviewPanel({
  variables,
  dealStructure,
  industryType,
  onVariablesChange,
  onDealStructureChange,
  onIndustryTypeChange,
  hideClassification = false,
}: VariableReviewProps) {
  const [editingIdx, setEditingIdx] = useState<number | null>(null);

  // P3-3: 중복 variable_key 감지
  const duplicateKeys = useMemo(() => {
    const counts = new Map<string, number>();
    for (const v of variables) {
      counts.set(v.variable_key, (counts.get(v.variable_key) ?? 0) + 1);
    }
    return new Set(
      [...counts.entries()].filter(([, c]) => c > 1).map(([k]) => k),
    );
  }, [variables]);

  const updateVar = useCallback(
    (idx: number, patch: Partial<ExtractedVariable>) => {
      const next = [...variables];
      next[idx] = { ...next[idx], ...patch };
      onVariablesChange(next);
    },
    [variables, onVariablesChange],
  );

  const removeVar = useCallback(
    (idx: number) => {
      onVariablesChange(variables.filter((_, i) => i !== idx));
    },
    [variables, onVariablesChange],
  );

  const addVar = useCallback(() => {
    const newVar: ExtractedVariable = {
      variable_key: `custom_${Date.now()}`,
      input_type: "TEXT",
      question_label: "새 변수",
      description: null,
      extracted_value: null,
      default_value: null,
      is_required: false,
      select_options: null,
      display_order: variables.length,
      group_name: "사용자 추가",
      visible_condition: null,
      confidence: 1.0,
    };
    onVariablesChange([...variables, newVar]);
    setEditingIdx(variables.length);
  }, [variables, onVariablesChange]);

  return (
    <div className="flex flex-col gap-4">
      {/* 분류 선택 (SHA 모드에서는 ShaClassificationPanel 사용) */}
      {!hideClassification && (
        <div className="flex items-center gap-4 rounded-xl border border-border p-4">
          <div className="flex flex-col gap-1">
            <label
              htmlFor="deal-structure"
              className="text-xs font-medium text-text-secondary"
            >
              딜 구조
            </label>
            <select
              id="deal-structure"
              value={dealStructure}
              onChange={(e) => onDealStructureChange(e.target.value)}
              className="rounded-lg border border-border bg-white px-2 py-1 text-sm text-text-primary focus:border-accent-primary focus:outline-none focus:ring-1 focus:ring-accent-primary"
            >
              {DEAL_STRUCTURES.map((ds) => (
                <option key={ds} value={ds}>
                  {DEAL_STRUCTURE_LABELS[ds]}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label
              htmlFor="industry-type"
              className="text-xs font-medium text-text-secondary"
            >
              산업 유형
            </label>
            <select
              id="industry-type"
              value={industryType}
              onChange={(e) =>
                onIndustryTypeChange(e.target.value as IndustryType)
              }
              className="rounded-lg border border-border bg-white px-2 py-1 text-sm text-text-primary focus:border-accent-primary focus:outline-none focus:ring-1 focus:ring-accent-primary"
            >
              {INDUSTRY_TYPES.map((it) => (
                <option key={it} value={it}>
                  {INDUSTRY_TYPE_LABELS[it]}
                </option>
              ))}
            </select>
          </div>
          <div className="ml-auto text-xs text-text-tertiary">
            {variables.length}개 변수
          </div>
        </div>
      )}

      {/* 변수 테이블 */}
      <div className="overflow-x-auto rounded-xl border border-border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-white-elevated text-left text-xs font-medium text-text-secondary">
              <th className="px-3 py-2">#</th>
              <th className="px-3 py-2">변수 키</th>
              <th className="px-3 py-2">라벨</th>
              <th className="px-3 py-2">타입</th>
              <th className="px-3 py-2">추출값</th>
              <th className="px-3 py-2">신뢰도</th>
              <th className="px-3 py-2 text-right">작업</th>
            </tr>
          </thead>
          <tbody>
            {variables.map((v, idx) => (
              <Fragment key={`${v.variable_key}-${idx}`}>
                <tr className="border-b border-border last:border-b-0 hover:bg-white-elevated/50">
                  <td className="px-3 py-2 text-text-tertiary">{idx + 1}</td>
                  <td className="px-3 py-2 font-mono text-xs">
                    {editingIdx === idx ? (
                      <div className="flex flex-col gap-0.5">
                        <input
                          id={`var-key-${idx}`}
                          type="text"
                          aria-label="변수 키"
                          aria-invalid={duplicateKeys.has(v.variable_key)}
                          aria-describedby={
                            duplicateKeys.has(v.variable_key)
                              ? `var-key-dup-${idx}`
                              : undefined
                          }
                          value={v.variable_key}
                          onChange={(e) =>
                            updateVar(idx, { variable_key: e.target.value })
                          }
                          className={`w-full rounded border px-1 py-0.5 text-xs ${duplicateKeys.has(v.variable_key) ? "border-negative" : "border-border"}`}
                        />
                        {duplicateKeys.has(v.variable_key) && (
                          <span
                            id={`var-key-dup-${idx}`}
                            className="text-[10px] text-negative"
                          >
                            중복 키
                          </span>
                        )}
                      </div>
                    ) : (
                      <span
                        className={
                          duplicateKeys.has(v.variable_key)
                            ? "text-negative"
                            : ""
                        }
                      >
                        {v.variable_key}
                        {duplicateKeys.has(v.variable_key) && " ⚠"}
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2">
                    {editingIdx === idx ? (
                      <input
                        type="text"
                        aria-label="질문 라벨"
                        value={v.question_label}
                        onChange={(e) =>
                          updateVar(idx, { question_label: e.target.value })
                        }
                        className="w-full rounded border border-border px-1 py-0.5 text-xs"
                      />
                    ) : (
                      <span className="text-text-primary">
                        {v.question_label}
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2">
                    {editingIdx === idx ? (
                      <select
                        aria-label="입력 타입"
                        value={v.input_type}
                        onChange={(e) =>
                          updateVar(idx, {
                            input_type: e.target
                              .value as ExtractedVariable["input_type"],
                          })
                        }
                        className="rounded border border-border px-1 py-0.5 text-xs"
                      >
                        {[
                          "TEXT",
                          "TEXTAREA",
                          "NUMBER",
                          "DATE",
                          "SELECT",
                          "BOOLEAN",
                          "CURRENCY",
                          "PERCENTAGE",
                        ].map((t) => (
                          <option key={t} value={t}>
                            {t}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <span className="rounded bg-white-elevated px-1.5 py-0.5 text-xs text-text-secondary">
                        {v.input_type}
                      </span>
                    )}
                  </td>
                  <td className="max-w-[200px] truncate px-3 py-2 text-xs text-text-secondary">
                    {editingIdx === idx ? (
                      <input
                        type="text"
                        aria-label="추출 값"
                        value={v.extracted_value ?? ""}
                        onChange={(e) =>
                          updateVar(idx, {
                            extracted_value: e.target.value || null,
                          })
                        }
                        className="w-full rounded border border-border px-1 py-0.5 text-xs"
                      />
                    ) : (
                      (v.extracted_value ?? "—")
                    )}
                  </td>
                  <td className="px-3 py-2">
                    <ConfidenceBadge value={v.confidence} />
                  </td>
                  <td className="px-3 py-2 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        type="button"
                        onClick={() =>
                          setEditingIdx(editingIdx === idx ? null : idx)
                        }
                        className="rounded p-1 text-text-tertiary hover:bg-white-elevated hover:text-text-primary"
                        title={editingIdx === idx ? "편집 완료" : "편집"}
                        aria-label={`${v.variable_key} 변수 ${editingIdx === idx ? "편집 완료" : "편집"}`}
                      >
                        {editingIdx === idx ? (
                          <Eye className="h-3.5 w-3.5" />
                        ) : (
                          <EyeOff className="h-3.5 w-3.5" />
                        )}
                      </button>
                      <button
                        type="button"
                        onClick={() => removeVar(idx)}
                        className="rounded p-1 text-text-tertiary hover:bg-red-50 hover:text-negative"
                        title="삭제"
                        aria-label={`${v.variable_key} 변수 삭제`}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
                {/* 고급 편집 (편집 모드 시 확장) */}
                {editingIdx === idx && (
                  <tr className="border-b border-border bg-blue-50/20">
                    <td colSpan={7} className="px-3 py-3">
                      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                        <div className="flex flex-col gap-1">
                          <label
                            htmlFor={`var-desc-${idx}`}
                            className="text-[10px] font-medium text-text-tertiary"
                          >
                            설명
                          </label>
                          <input
                            id={`var-desc-${idx}`}
                            type="text"
                            value={v.description ?? ""}
                            onChange={(e) =>
                              updateVar(idx, {
                                description: e.target.value || null,
                              })
                            }
                            className="w-full rounded border border-border px-2 py-1 text-xs"
                            placeholder="변수에 대한 설명"
                          />
                        </div>
                        <div className="flex flex-col gap-1">
                          <label
                            htmlFor={`var-default-${idx}`}
                            className="text-[10px] font-medium text-text-tertiary"
                          >
                            기본값
                          </label>
                          <input
                            id={`var-default-${idx}`}
                            type="text"
                            value={v.default_value ?? ""}
                            onChange={(e) =>
                              updateVar(idx, {
                                default_value: e.target.value || null,
                              })
                            }
                            className="w-full rounded border border-border px-2 py-1 text-xs"
                            placeholder="기본값"
                          />
                        </div>
                        <div className="flex flex-col gap-1">
                          <label
                            htmlFor={`var-cond-${idx}`}
                            className="text-[10px] font-medium text-text-tertiary"
                          >
                            표시 조건
                          </label>
                          <input
                            id={`var-cond-${idx}`}
                            type="text"
                            value={v.visible_condition ?? ""}
                            onChange={(e) =>
                              updateVar(idx, {
                                visible_condition: e.target.value || null,
                              })
                            }
                            className="w-full rounded border border-border px-2 py-1 text-xs font-mono"
                            placeholder="escrow_included == True"
                          />
                        </div>
                        <div className="flex items-end gap-2 pb-1">
                          <label className="flex items-center gap-1.5 text-xs text-text-secondary">
                            <input
                              type="checkbox"
                              checked={v.is_required}
                              onChange={(e) =>
                                updateVar(idx, {
                                  is_required: e.target.checked,
                                })
                              }
                              className="h-3.5 w-3.5 rounded border-border text-accent-primary focus:ring-accent-primary"
                            />
                            필수 항목
                          </label>
                        </div>
                        {v.input_type === "SELECT" && (
                          <div className="col-span-2 sm:col-span-4">
                            <SelectOptionsEditor
                              value={v.select_options}
                              onChange={(opts) =>
                                updateVar(idx, { select_options: opts })
                              }
                            />
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>

      {/* 추가 버튼 */}
      <button
        type="button"
        onClick={addVar}
        className="flex items-center gap-1.5 self-start rounded-lg border border-dashed border-border px-3 py-1.5 text-xs font-medium text-text-secondary hover:border-accent-primary hover:text-accent-primary"
      >
        <Plus className="h-3.5 w-3.5" />
        변수 추가
      </button>
    </div>
  );
}

// ── 조항 리뷰 ─────────────────────────────────────────────────────────────

interface ClauseReviewProps {
  clauses: AnalyzedClause[];
  onClausesChange: (clauses: AnalyzedClause[]) => void;
}

export function ClauseReviewPanel({
  clauses,
  onClausesChange,
}: ClauseReviewProps) {
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);

  const updateClause = useCallback(
    (idx: number, patch: Partial<AnalyzedClause>) => {
      const next = [...clauses];
      next[idx] = { ...next[idx], ...patch };
      onClausesChange(next);
    },
    [clauses, onClausesChange],
  );

  const removeClause = useCallback(
    (idx: number) => {
      onClausesChange(
        clauses
          .filter((_, i) => i !== idx)
          .map((c, i) => ({ ...c, clause_order: i })),
      );
    },
    [clauses, onClausesChange],
  );

  const moveClause = useCallback(
    (idx: number, direction: -1 | 1) => {
      const target = idx + direction;
      if (target < 0 || target >= clauses.length) return;
      const next = [...clauses];
      [next[idx], next[target]] = [next[target], next[idx]];
      onClausesChange(next.map((c, i) => ({ ...c, clause_order: i })));
      setExpandedIdx(target);
    },
    [clauses, onClausesChange],
  );

  return (
    <div className="flex flex-col gap-3">
      <div className="text-xs text-text-tertiary">
        {clauses.length}개 조항 · 클릭하여 원문/템플릿 비교
      </div>

      {clauses.map((c, idx) => (
        <div
          key={c.clause_order}
          className="rounded-xl border border-border overflow-hidden"
        >
          {/* 조항 헤더 */}
          <button
            type="button"
            onClick={() => setExpandedIdx(expandedIdx === idx ? null : idx)}
            className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-white-elevated/50"
          >
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent-primary/10 text-xs font-medium text-accent-primary">
              {idx + 1}
            </span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-text-primary truncate">
                  {c.title}
                </span>
                {c.is_boilerplate && (
                  <span className="shrink-0 rounded bg-blue-50 px-1.5 py-0.5 text-[10px] font-medium text-blue-600">
                    표준
                  </span>
                )}
                <ConfidenceBadge value={c.confidence} />
              </div>
              {c.condition_expression && (
                <span className="text-xs text-text-tertiary font-mono">
                  조건: {c.condition_expression}
                </span>
              )}
            </div>
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  moveClause(idx, -1);
                }}
                disabled={idx === 0}
                className="rounded p-1 text-text-tertiary hover:bg-white-elevated disabled:opacity-30"
                title="위로 이동"
                aria-label={`${c.title} 조항 위로 이동`}
              >
                <ChevronUp className="h-3.5 w-3.5" />
              </button>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  moveClause(idx, 1);
                }}
                disabled={idx === clauses.length - 1}
                className="rounded p-1 text-text-tertiary hover:bg-white-elevated disabled:opacity-30"
                title="아래로 이동"
                aria-label={`${c.title} 조항 아래로 이동`}
              >
                <ChevronDown className="h-3.5 w-3.5" />
              </button>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  removeClause(idx);
                }}
                className="rounded p-1 text-text-tertiary hover:bg-red-50 hover:text-negative"
                title="삭제"
                aria-label={`${c.title} 조항 삭제`}
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          </button>

          {/* 확장 영역: 원문 vs 템플릿 비교 */}
          {expandedIdx === idx && (
            <div className="border-t border-border px-4 py-3">
              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                {/* 원문 */}
                <div className="flex flex-col gap-1">
                  <span className="text-xs font-medium text-text-secondary">
                    원문
                  </span>
                  <SafeHtml
                    html={c.original_content}
                    className="rounded-lg border border-border bg-white-elevated p-3 text-xs text-text-primary leading-relaxed max-h-60 overflow-y-auto"
                  />
                </div>
                {/* Jinja2 템플릿 */}
                <div className="flex flex-col gap-1">
                  <span className="text-xs font-medium text-text-secondary">
                    Jinja2 템플릿
                  </span>
                  <SafeHtml
                    html={c.content}
                    className="rounded-lg border border-border bg-white-elevated p-3 text-xs text-text-primary leading-relaxed max-h-60 overflow-y-auto font-mono"
                  />
                </div>
              </div>

              {/* 조건식 편집 */}
              <div className="mt-3 flex items-center gap-3">
                <label
                  htmlFor={`cond-${idx}`}
                  className="text-xs font-medium text-text-secondary"
                >
                  조건식
                </label>
                <input
                  id={`cond-${idx}`}
                  type="text"
                  value={c.condition_expression ?? ""}
                  onChange={(e) =>
                    updateClause(idx, {
                      condition_expression: e.target.value || null,
                    })
                  }
                  placeholder="예: has_escrow == True"
                  className="flex-1 rounded-lg border border-border bg-white px-2 py-1 text-xs font-mono text-text-primary focus:border-accent-primary focus:outline-none focus:ring-1 focus:ring-accent-primary"
                />
                <label className="flex items-center gap-1.5 text-xs text-text-secondary">
                  <input
                    type="checkbox"
                    checked={c.is_boilerplate}
                    onChange={(e) =>
                      updateClause(idx, {
                        is_boilerplate: e.target.checked,
                      })
                    }
                    className="h-3.5 w-3.5 rounded border-border text-accent-primary focus:ring-accent-primary"
                  />
                  표준 조항
                </label>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// ── SELECT 옵션 편집 ──────────────────────────────────────────────────────

function SelectOptionsEditor({
  value,
  onChange,
}: {
  value: Record<string, string> | null;
  onChange: (v: Record<string, string> | null) => void;
}) {
  const [text, setText] = useState(value ? JSON.stringify(value, null, 2) : "");
  const [valid, setValid] = useState(true);

  return (
    <div className="flex flex-col gap-1">
      <label
        htmlFor="select-opts-editor"
        className="text-[10px] font-medium text-text-tertiary"
      >
        선택 옵션 (JSON)
      </label>
      <textarea
        id="select-opts-editor"
        aria-invalid={!valid}
        aria-describedby={!valid ? "select-opts-error" : undefined}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onBlur={() => {
          try {
            const parsed = text.trim()
              ? (JSON.parse(text) as Record<string, string>)
              : null;
            onChange(parsed);
            setValid(true);
          } catch {
            setValid(false);
          }
        }}
        rows={2}
        className={`w-full rounded border px-2 py-1 text-xs font-mono ${
          valid ? "border-border" : "border-negative"
        }`}
        placeholder={'{"KEY": "표시값", "KEY2": "표시값2"}'}
      />
      {!valid && (
        <span id="select-opts-error" className="text-[10px] text-negative">
          유효한 JSON이 아닙니다
        </span>
      )}
    </div>
  );
}

// ── 안전한 HTML 렌더링 ──────────────────────────────────────────────────

function SafeHtml({ html, className }: { html: string; className?: string }) {
  const clean = useMemo(() => sanitizeHtml(html), [html]);
  return (
    <div className={className} dangerouslySetInnerHTML={{ __html: clean }} />
  );
}

// ── SHA 분류 패널 ────────────────────────────────────────────────────────

interface ShaClassificationProps {
  shaType: ShaType;
  exitStrategy: ExitStrategy;
  industryType: IndustryType;
  onShaTypeChange: (v: ShaType) => void;
  onExitStrategyChange: (v: ExitStrategy) => void;
  onIndustryTypeChange: (v: IndustryType) => void;
  variableCount: number;
}

export function ShaClassificationPanel({
  shaType,
  exitStrategy,
  industryType,
  onShaTypeChange,
  onExitStrategyChange,
  onIndustryTypeChange,
  variableCount,
}: ShaClassificationProps) {
  return (
    <div className="flex items-center gap-4 rounded-xl border border-border p-4 flex-wrap">
      <div className="flex flex-col gap-1">
        <label
          htmlFor="sha-type"
          className="text-xs font-medium text-text-secondary"
        >
          SHA 유형
        </label>
        <select
          id="sha-type"
          value={shaType}
          onChange={(e) => onShaTypeChange(e.target.value as ShaType)}
          className="rounded-lg border border-border bg-white px-2 py-1 text-sm text-text-primary focus:border-accent-primary focus:outline-none focus:ring-1 focus:ring-accent-primary"
        >
          {SHA_TYPES.map((st) => (
            <option key={st} value={st}>
              {SHA_TYPE_LABELS[st]}
            </option>
          ))}
        </select>
      </div>
      <div className="flex flex-col gap-1">
        <label
          htmlFor="exit-strategy"
          className="text-xs font-medium text-text-secondary"
        >
          Exit 전략
        </label>
        <select
          id="exit-strategy"
          value={exitStrategy}
          onChange={(e) => onExitStrategyChange(e.target.value as ExitStrategy)}
          className="rounded-lg border border-border bg-white px-2 py-1 text-sm text-text-primary focus:border-accent-primary focus:outline-none focus:ring-1 focus:ring-accent-primary"
        >
          {EXIT_STRATEGIES.map((es) => (
            <option key={es} value={es}>
              {EXIT_STRATEGY_LABELS[es]}
            </option>
          ))}
        </select>
      </div>
      <div className="flex flex-col gap-1">
        <label
          htmlFor="sha-industry-type"
          className="text-xs font-medium text-text-secondary"
        >
          산업 유형
        </label>
        <select
          id="sha-industry-type"
          value={industryType}
          onChange={(e) => onIndustryTypeChange(e.target.value as IndustryType)}
          className="rounded-lg border border-border bg-white px-2 py-1 text-sm text-text-primary focus:border-accent-primary focus:outline-none focus:ring-1 focus:ring-accent-primary"
        >
          {INDUSTRY_TYPES.map((it) => (
            <option key={it} value={it}>
              {INDUSTRY_TYPE_LABELS[it]}
            </option>
          ))}
        </select>
      </div>
      <div className="ml-auto text-xs text-text-tertiary">
        {variableCount}개 변수
      </div>
    </div>
  );
}

// ── BTA 분류 패널 ────────────────────────────────────────────────────────

interface BtaClassificationProps {
  btaScope: BtaScope;
  severancePayHandling: SeverancePayHandling;
  industryType: IndustryType;
  onBtaScopeChange: (v: BtaScope) => void;
  onSeverancePayChange: (v: SeverancePayHandling) => void;
  onIndustryTypeChange: (v: IndustryType) => void;
  variableCount: number;
}

export function BtaClassificationPanel({
  btaScope,
  severancePayHandling,
  industryType,
  onBtaScopeChange,
  onSeverancePayChange,
  onIndustryTypeChange,
  variableCount,
}: BtaClassificationProps) {
  return (
    <div className="flex items-center gap-4 rounded-xl border border-border p-4 flex-wrap">
      <div className="flex flex-col gap-1">
        <label
          htmlFor="bta-scope"
          className="text-xs font-medium text-text-secondary"
        >
          양도 범위
        </label>
        <select
          id="bta-scope"
          value={btaScope}
          onChange={(e) => onBtaScopeChange(e.target.value as BtaScope)}
          className="rounded-lg border border-border bg-white px-2 py-1 text-sm text-text-primary focus:border-accent-primary focus:outline-none focus:ring-1 focus:ring-accent-primary"
        >
          {BTA_SCOPES.map((s) => (
            <option key={s} value={s}>
              {BTA_SCOPE_LABELS[s]}
            </option>
          ))}
        </select>
      </div>
      <div className="flex flex-col gap-1">
        <label
          htmlFor="severance-pay"
          className="text-xs font-medium text-text-secondary"
        >
          퇴직금 처리
        </label>
        <select
          id="severance-pay"
          value={severancePayHandling}
          onChange={(e) =>
            onSeverancePayChange(e.target.value as SeverancePayHandling)
          }
          className="rounded-lg border border-border bg-white px-2 py-1 text-sm text-text-primary focus:border-accent-primary focus:outline-none focus:ring-1 focus:ring-accent-primary"
        >
          {SEVERANCE_PAY_HANDLING.map((s) => (
            <option key={s} value={s}>
              {SEVERANCE_PAY_LABELS[s]}
            </option>
          ))}
        </select>
      </div>
      <div className="flex flex-col gap-1">
        <label
          htmlFor="bta-industry-type"
          className="text-xs font-medium text-text-secondary"
        >
          산업 유형
        </label>
        <select
          id="bta-industry-type"
          value={industryType}
          onChange={(e) => onIndustryTypeChange(e.target.value as IndustryType)}
          className="rounded-lg border border-border bg-white px-2 py-1 text-sm text-text-primary focus:border-accent-primary focus:outline-none focus:ring-1 focus:ring-accent-primary"
        >
          {INDUSTRY_TYPES.map((it) => (
            <option key={it} value={it}>
              {INDUSTRY_TYPE_LABELS[it]}
            </option>
          ))}
        </select>
      </div>
      <div className="ml-auto text-xs text-text-tertiary">
        {variableCount}개 변수
      </div>
    </div>
  );
}

// ── SSA 분류 패널 ─────────────────────────────────────────────────────────

interface SsaClassificationProps {
  securityType: SsaSecurityType;
  transactionContext: SsaTransactionContext;
  industryType: IndustryType;
  onSecurityTypeChange: (v: SsaSecurityType) => void;
  onTransactionContextChange: (v: SsaTransactionContext) => void;
  onIndustryTypeChange: (v: IndustryType) => void;
  variableCount: number;
}

export function SsaClassificationPanel({
  securityType,
  transactionContext,
  industryType,
  onSecurityTypeChange,
  onTransactionContextChange,
  onIndustryTypeChange,
  variableCount,
}: SsaClassificationProps) {
  return (
    <div className="flex items-center gap-4 rounded-xl border border-border p-4 flex-wrap">
      <div className="flex flex-col gap-1">
        <label
          htmlFor="ssa-security-type"
          className="text-sm font-medium text-text-secondary whitespace-nowrap"
        >
          증권 종류
        </label>
        <select
          id="ssa-security-type"
          className="rounded-lg border border-border bg-white px-3 py-1.5 text-sm focus:ring-2 focus:ring-accent-primary"
          value={securityType}
          onChange={(e) =>
            onSecurityTypeChange(e.target.value as SsaSecurityType)
          }
        >
          {SSA_SECURITY_TYPES.map((st) => (
            <option key={st} value={st}>
              {SSA_SECURITY_TYPE_LABELS[st]}
            </option>
          ))}
        </select>
      </div>
      <div className="flex flex-col gap-1">
        <label
          htmlFor="ssa-transaction-context"
          className="text-sm font-medium text-text-secondary whitespace-nowrap"
        >
          거래 맥락
        </label>
        <select
          id="ssa-transaction-context"
          className="rounded-lg border border-border bg-white px-3 py-1.5 text-sm focus:ring-2 focus:ring-accent-primary"
          value={transactionContext}
          onChange={(e) =>
            onTransactionContextChange(e.target.value as SsaTransactionContext)
          }
        >
          {SSA_TRANSACTION_CONTEXTS.map((tc) => (
            <option key={tc} value={tc}>
              {SSA_TRANSACTION_CONTEXT_LABELS[tc]}
            </option>
          ))}
        </select>
      </div>
      <div className="flex flex-col gap-1">
        <label
          htmlFor="ssa-industry-type"
          className="text-sm font-medium text-text-secondary whitespace-nowrap"
        >
          산업 유형
        </label>
        <select
          id="ssa-industry-type"
          className="rounded-lg border border-border bg-white px-3 py-1.5 text-sm focus:ring-2 focus:ring-accent-primary"
          value={industryType}
          onChange={(e) => onIndustryTypeChange(e.target.value as IndustryType)}
        >
          {INDUSTRY_TYPES.map((it) => (
            <option key={it} value={it}>
              {INDUSTRY_TYPE_LABELS[it]}
            </option>
          ))}
        </select>
      </div>
      <div className="ml-auto text-xs text-text-tertiary">
        {variableCount}개 변수
      </div>
    </div>
  );
}

// ── MOU 분류 패널 ─────────────────────────────────────────────────────────

interface MouClassificationProps {
  mouTransactionType: MouTransactionType;
  depositHandling: MouDepositHandling;
  industryType: IndustryType;
  onMouTransactionTypeChange: (v: MouTransactionType) => void;
  onDepositHandlingChange: (v: MouDepositHandling) => void;
  onIndustryTypeChange: (v: IndustryType) => void;
  variableCount: number;
}

export function MouClassificationPanel({
  mouTransactionType,
  depositHandling,
  industryType,
  onMouTransactionTypeChange,
  onDepositHandlingChange,
  onIndustryTypeChange,
  variableCount,
}: MouClassificationProps) {
  return (
    <div className="flex items-center gap-4 rounded-xl border border-border p-4 flex-wrap">
      <div className="flex flex-col gap-1">
        <label
          htmlFor="mou-transaction-type"
          className="text-sm font-medium text-text-secondary whitespace-nowrap"
        >
          거래 유형
        </label>
        <select
          id="mou-transaction-type"
          className="rounded-lg border border-border bg-white px-3 py-1.5 text-sm focus:ring-2 focus:ring-accent-primary"
          value={mouTransactionType}
          onChange={(e) =>
            onMouTransactionTypeChange(e.target.value as MouTransactionType)
          }
        >
          {MOU_TRANSACTION_TYPES.map((mt) => (
            <option key={mt} value={mt}>
              {MOU_TRANSACTION_TYPE_LABELS[mt]}
            </option>
          ))}
        </select>
      </div>
      <div className="flex flex-col gap-1">
        <label
          htmlFor="mou-deposit-handling"
          className="text-sm font-medium text-text-secondary whitespace-nowrap"
        >
          보증금 처리
        </label>
        <select
          id="mou-deposit-handling"
          className="rounded-lg border border-border bg-white px-3 py-1.5 text-sm focus:ring-2 focus:ring-accent-primary"
          value={depositHandling}
          onChange={(e) =>
            onDepositHandlingChange(e.target.value as MouDepositHandling)
          }
        >
          {MOU_DEPOSIT_HANDLING.map((dh) => (
            <option key={dh} value={dh}>
              {MOU_DEPOSIT_HANDLING_LABELS[dh]}
            </option>
          ))}
        </select>
      </div>
      <div className="flex flex-col gap-1">
        <label
          htmlFor="mou-industry-type"
          className="text-sm font-medium text-text-secondary whitespace-nowrap"
        >
          산업 유형
        </label>
        <select
          id="mou-industry-type"
          className="rounded-lg border border-border bg-white px-3 py-1.5 text-sm focus:ring-2 focus:ring-accent-primary"
          value={industryType}
          onChange={(e) => onIndustryTypeChange(e.target.value as IndustryType)}
        >
          {INDUSTRY_TYPES.map((it) => (
            <option key={it} value={it}>
              {INDUSTRY_TYPE_LABELS[it]}
            </option>
          ))}
        </select>
      </div>
      <div className="ml-auto text-xs text-text-tertiary">
        {variableCount}개 변수
      </div>
    </div>
  );
}

// ── 신뢰도 배지 ─────────────────────────────────────────────────────────

function ConfidenceBadge({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color =
    pct >= 80
      ? "bg-emerald-50 text-emerald-700"
      : pct >= 50
        ? "bg-amber-50 text-amber-700"
        : "bg-red-50 text-negative";
  return (
    <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${color}`}>
      {pct}%
    </span>
  );
}
