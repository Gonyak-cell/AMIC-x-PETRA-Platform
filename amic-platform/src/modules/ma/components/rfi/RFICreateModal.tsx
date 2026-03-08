import { useState } from "react";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { useCreateRFIItem } from "@/modules/ma/hooks/useRFI";
import {
  RFI_CATEGORY_OPTIONS,
  RFI_PRIORITY_OPTIONS,
} from "@/modules/ma/constants";
import type {
  RFIItemCreate,
  RFICategoryV2,
  RFIPriority,
} from "@/modules/ma/types/rfi";

interface RFICreateModalProps {
  txnId: string;
  isOpen: boolean;
  onClose: () => void;
}

interface FormState {
  category: RFICategoryV2 | "";
  question_text: string;
  priority: RFIPriority;
  target_doc: string;
  assignee_email: string;
  due_date: string;
  internal_memo: string;
  report_section_tag: string;
}

const INITIAL_FORM: FormState = {
  category: "",
  question_text: "",
  priority: "MEDIUM",
  target_doc: "",
  assignee_email: "",
  due_date: "",
  internal_memo: "",
  report_section_tag: "",
};

const categoryOptions = RFI_CATEGORY_OPTIONS.filter((opt) => opt.value !== "");
const priorityOptions = RFI_PRIORITY_OPTIONS.filter((opt) => opt.value !== "");

export default function RFICreateModal({
  txnId,
  isOpen,
  onClose,
}: RFICreateModalProps) {
  const createRFIItem = useCreateRFIItem(txnId);
  const [form, setForm] = useState<FormState>({ ...INITIAL_FORM });

  const canSubmit = form.category !== "" && form.question_text.trim() !== "";

  const handleClose = () => {
    setForm({ ...INITIAL_FORM });
    onClose();
  };

  const handleSubmit = () => {
    if (!canSubmit) return;

    if (form.category === "") return;
    const body: RFIItemCreate = {
      category: form.category,
      question_text: form.question_text.trim(),
      priority: form.priority || undefined,
      target_doc: form.target_doc.trim() || undefined,
      assignee_email: form.assignee_email.trim() || undefined,
      due_date: form.due_date || undefined,
      internal_memo: form.internal_memo.trim() || undefined,
      report_section_tag: form.report_section_tag.trim() || undefined,
    };

    createRFIItem.mutate(body, {
      onSuccess: () => {
        handleClose();
      },
    });
  };

  const update = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <Modal open={isOpen} onClose={handleClose} title="질의 추가" size="lg">
      <div className="space-y-5">
        {/* Row 1: 카테고리 + 우선순위 */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label
              htmlFor="rfi-category"
              className="block text-sm font-medium text-text-body mb-1"
            >
              카테고리 <span className="text-red-500">*</span>
            </label>
            <select
              id="rfi-category"
              className="w-full border border-gray-border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent"
              value={form.category}
              onChange={(e) => update("category", e.target.value as RFICategoryV2 | "")}
            >
              <option value="">선택하세요</option>
              {categoryOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label
              htmlFor="rfi-priority"
              className="block text-sm font-medium text-text-body mb-1"
            >
              우선순위
            </label>
            <select
              id="rfi-priority"
              className="w-full border border-gray-border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent"
              value={form.priority}
              onChange={(e) => update("priority", e.target.value as RFIPriority)}
            >
              {priorityOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Row 2: 질의 내용 (full-width textarea) */}
        <div>
          <label
            htmlFor="rfi-question"
            className="block text-sm font-medium text-text-body mb-1"
          >
            질의 내용 <span className="text-red-500">*</span>
          </label>
          <textarea
            id="rfi-question"
            className="w-full border border-gray-border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent"
            rows={4}
            placeholder="질의 내용을 입력하세요"
            value={form.question_text}
            onChange={(e) => update("question_text", e.target.value)}
          />
        </div>

        {/* Row 3: 대상 문서 + 담당자 이메일 */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label
              htmlFor="rfi-target-doc"
              className="block text-sm font-medium text-text-body mb-1"
            >
              대상 문서
            </label>
            <input
              id="rfi-target-doc"
              type="text"
              className="w-full border border-gray-border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent"
              placeholder="예: 재무제표, 계약서"
              value={form.target_doc}
              onChange={(e) => update("target_doc", e.target.value)}
            />
          </div>

          <div>
            <label
              htmlFor="rfi-assignee"
              className="block text-sm font-medium text-text-body mb-1"
            >
              담당자 이메일
            </label>
            <input
              id="rfi-assignee"
              type="email"
              className="w-full border border-gray-border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent"
              placeholder="example@company.com"
              value={form.assignee_email}
              onChange={(e) => update("assignee_email", e.target.value)}
            />
          </div>
        </div>

        {/* Row 4: 마감일 + 리포트 섹션 태그 */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label
              htmlFor="rfi-due-date"
              className="block text-sm font-medium text-text-body mb-1"
            >
              마감일
            </label>
            <input
              id="rfi-due-date"
              type="date"
              className="w-full border border-gray-border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent"
              value={form.due_date}
              onChange={(e) => update("due_date", e.target.value)}
            />
          </div>

          <div>
            <label
              htmlFor="rfi-section-tag"
              className="block text-sm font-medium text-text-body mb-1"
            >
              리포트 섹션 태그
            </label>
            <input
              id="rfi-section-tag"
              type="text"
              className="w-full border border-gray-border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent"
              placeholder="예: 3.1 재무분석"
              value={form.report_section_tag}
              onChange={(e) => update("report_section_tag", e.target.value)}
            />
          </div>
        </div>

        {/* Row 5: 내부 메모 (full-width textarea) */}
        <div>
          <label
            htmlFor="rfi-memo"
            className="block text-sm font-medium text-text-body mb-1"
          >
            내부 메모
          </label>
          <textarea
            id="rfi-memo"
            className="w-full border border-gray-border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent"
            rows={2}
            placeholder="내부 참고용 메모 (대상에게 표시되지 않음)"
            value={form.internal_memo}
            onChange={(e) => update("internal_memo", e.target.value)}
          />
        </div>

        {/* Footer buttons */}
        <div className="flex justify-end gap-2 pt-2 border-t border-gray-border">
          <Button variant="secondary" onClick={handleClose}>
            취소
          </Button>
          <Button
            variant="primary"
            onClick={handleSubmit}
            disabled={!canSubmit || createRFIItem.isPending}
          >
            {createRFIItem.isPending ? "생성 중..." : "질의 추가"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
