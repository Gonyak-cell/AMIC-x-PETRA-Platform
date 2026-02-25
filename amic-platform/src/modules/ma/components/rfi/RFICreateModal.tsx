import { useState } from "react";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { useCreateRFI } from "@/modules/ma/hooks/useRFI";
import type { RFICreate } from "@/modules/ma/types/rfi";

interface RFICreateModalProps {
  txnId: string;
  open: boolean;
  onClose: () => void;
}

const INITIAL_FORM: RFICreate = {
  title: "",
  round_number: 1,
  description: "",
  recipient_name: "",
  recipient_email: "",
  recipient_company: "",
  due_date: "",
  notes: "",
};

export default function RFICreateModal({ txnId, open, onClose }: RFICreateModalProps) {
  const createRFI = useCreateRFI(txnId);
  const [form, setForm] = useState<RFICreate>({ ...INITIAL_FORM });

  const handleSubmit = () => {
    if (!form.title.trim()) return;
    const body: RFICreate = {
      ...form,
      description: form.description || undefined,
      recipient_name: form.recipient_name || undefined,
      recipient_email: form.recipient_email || undefined,
      recipient_company: form.recipient_company || undefined,
      due_date: form.due_date || undefined,
      notes: form.notes || undefined,
    };
    createRFI.mutate(body, {
      onSuccess: () => {
        onClose();
        setForm({ ...INITIAL_FORM });
      },
    });
  };

  return (
    <Modal open={open} onClose={onClose} title="RFI 생성">
      <div className="space-y-4">
        <div>
          <label htmlFor="rfi-title" className="block text-sm font-medium text-gray-700 mb-1">제목 *</label>
          <input
            id="rfi-title"
            type="text"
            className="w-full border rounded px-3 py-2 text-sm"
            placeholder="예: 1차 RFI — 재무/법률"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="rfi-round" className="block text-sm font-medium text-gray-700 mb-1">라운드</label>
            <input
              id="rfi-round"
              type="number"
              min={1}
              className="w-full border rounded px-3 py-2 text-sm"
              value={form.round_number}
              onChange={(e) => setForm({ ...form, round_number: Number(e.target.value) })}
            />
          </div>
          <div>
            <label htmlFor="rfi-due-date" className="block text-sm font-medium text-gray-700 mb-1">마감일</label>
            <input
              id="rfi-due-date"
              type="date"
              className="w-full border rounded px-3 py-2 text-sm"
              value={form.due_date}
              onChange={(e) => setForm({ ...form, due_date: e.target.value })}
            />
          </div>
        </div>

        <div>
          <label htmlFor="rfi-description" className="block text-sm font-medium text-gray-700 mb-1">설명</label>
          <textarea
            id="rfi-description"
            className="w-full border rounded px-3 py-2 text-sm"
            rows={2}
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
          />
        </div>

        <div className="border-t pt-4">
          <p className="text-sm font-medium text-gray-700 mb-2">수신자 정보</p>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="rfi-recipient-name" className="block text-xs text-gray-500 mb-1">담당자명</label>
              <input
                id="rfi-recipient-name"
                type="text"
                className="w-full border rounded px-3 py-2 text-sm"
                value={form.recipient_name}
                onChange={(e) => setForm({ ...form, recipient_name: e.target.value })}
              />
            </div>
            <div>
              <label htmlFor="rfi-recipient-email" className="block text-xs text-gray-500 mb-1">이메일</label>
              <input
                id="rfi-recipient-email"
                type="email"
                className="w-full border rounded px-3 py-2 text-sm"
                value={form.recipient_email}
                onChange={(e) => setForm({ ...form, recipient_email: e.target.value })}
              />
            </div>
          </div>
          <div className="mt-2">
            <label htmlFor="rfi-recipient-company" className="block text-xs text-gray-500 mb-1">회사명</label>
            <input
              id="rfi-recipient-company"
              type="text"
              className="w-full border rounded px-3 py-2 text-sm"
              value={form.recipient_company}
              onChange={(e) => setForm({ ...form, recipient_company: e.target.value })}
            />
          </div>
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" onClick={onClose}>
            취소
          </Button>
          <Button onClick={handleSubmit} disabled={!form.title.trim() || createRFI.isPending}>
            {createRFI.isPending ? "생성 중..." : "RFI 생성"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
