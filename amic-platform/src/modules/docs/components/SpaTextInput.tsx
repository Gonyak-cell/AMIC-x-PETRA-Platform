/** 계약서 원문 텍스트 입력 — Step 0 (SPA/SHA/BTA/SSA/MOU) */

import { useState } from "react";
import { FileText } from "lucide-react";
import type { DocType } from "@/modules/docs/types/spa_analysis";
import { DOC_TYPES, DOC_TYPE_LABELS } from "@/modules/docs/types/spa_analysis";

interface SpaTextInputProps {
  onSubmit: (
    text: string,
    languageHint: "ko" | "en" | null,
    docTypeHint: DocType | null,
  ) => void;
  isPending: boolean;
  /** P3-2: 이전 입력값 복원 (실패 시 텍스트 보존) */
  initialText?: string;
}

const MIN_CHARS = 100;
const MAX_CHARS = 500_000;

export default function SpaTextInput({
  onSubmit,
  isPending,
  initialText = "",
}: SpaTextInputProps) {
  const [text, setText] = useState(initialText);
  const [languageHint, setLanguageHint] = useState<"ko" | "en" | null>(null);
  const [docTypeHint, setDocTypeHint] = useState<DocType | null>(null);

  const charCount = text.length;
  const isValid = charCount >= MIN_CHARS && charCount <= MAX_CHARS;

  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-sm font-semibold text-text-primary">
        계약서 원문을 붙여넣으세요
      </h2>

      {/* 텍스트 입력 */}
      <div className="rounded-xl border border-border p-4">
        <label
          htmlFor="spa-raw-text"
          className="mb-1 block text-xs font-medium text-text-secondary"
        >
          계약서 원문 <span className="text-negative">*</span>
        </label>
        <textarea
          id="spa-raw-text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={16}
          className="w-full rounded-lg border border-border bg-white px-3 py-2 text-sm text-text-primary placeholder:text-text-tertiary focus:border-accent-primary focus:outline-none focus:ring-1 focus:ring-accent-primary font-mono leading-relaxed"
          placeholder="계약서 원문 전체를 붙여넣으세요 (최소 100자)..."
          disabled={isPending}
        />
        <div
          className="mt-1 flex items-center justify-between text-xs"
          aria-live="polite"
        >
          <span
            className={
              charCount < MIN_CHARS
                ? "text-negative"
                : charCount > MAX_CHARS
                  ? "text-negative"
                  : "text-text-tertiary"
            }
          >
            {charCount.toLocaleString()} / {MIN_CHARS.toLocaleString()}~
            {MAX_CHARS.toLocaleString()}자
          </span>
          {charCount > 0 && charCount < MIN_CHARS && (
            <span className="text-negative">
              {(MIN_CHARS - charCount).toLocaleString()}자 더 필요합니다
            </span>
          )}
        </div>
      </div>

      {/* 힌트 옵션 + 분석 버튼 */}
      <div className="flex items-center justify-between rounded-xl border border-border p-4">
        <div className="flex items-center gap-3 flex-wrap">
          <label
            htmlFor="doc-type-hint"
            className="text-xs font-medium text-text-secondary"
          >
            문서 유형
          </label>
          <select
            id="doc-type-hint"
            value={docTypeHint ?? ""}
            onChange={(e) =>
              setDocTypeHint((e.target.value as DocType) || null)
            }
            className="rounded-lg border border-border bg-white px-2 py-1 text-xs text-text-primary focus:border-accent-primary focus:outline-none focus:ring-1 focus:ring-accent-primary"
          >
            <option value="">자동 감지</option>
            {DOC_TYPES.map((dt) => (
              <option key={dt} value={dt}>
                {DOC_TYPE_LABELS[dt]}
              </option>
            ))}
          </select>
          <label
            htmlFor="lang-hint"
            className="text-xs font-medium text-text-secondary"
          >
            언어 힌트
          </label>
          <select
            id="lang-hint"
            value={languageHint ?? ""}
            onChange={(e) =>
              setLanguageHint((e.target.value as "ko" | "en") || null)
            }
            className="rounded-lg border border-border bg-white px-2 py-1 text-xs text-text-primary focus:border-accent-primary focus:outline-none focus:ring-1 focus:ring-accent-primary"
          >
            <option value="">자동 감지</option>
            <option value="ko">한국어</option>
            <option value="en">영어</option>
          </select>
        </div>

        <button
          type="button"
          onClick={() => onSubmit(text, languageHint, docTypeHint)}
          disabled={!isValid || isPending}
          className="flex items-center gap-1.5 rounded-lg bg-accent-primary px-4 py-2 text-sm font-medium text-white hover:bg-accent-primary/90 disabled:opacity-40"
        >
          <FileText className="h-4 w-4" />
          {isPending ? "분석 중..." : "변수 추출 시작"}
        </button>
      </div>
    </div>
  );
}
