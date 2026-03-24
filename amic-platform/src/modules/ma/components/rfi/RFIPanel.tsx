import { type ChangeEvent, useRef, useState } from "react";
import { toast } from "sonner";
import {
  Download,
  Paperclip,
  Plus,
  Sparkles,
  Trash2,
  Upload,
} from "lucide-react";

import { Badge, Button, Card, Modal } from "@/components/ui";
import {
  openAttachmentFilePicker,
  validateAttachmentFile,
} from "@/modules/ma/components/attachmentUploadUtils";
import {
  useDeleteAttachment as useDeleteRFIAttachment,
  useExportRFI,
  useGenerateRFI,
  useImportRFI,
  useRFIAttachments,
  useUploadAttachments,
} from "@/modules/ma/hooks/useRFI";
import type { RFIAttachment, RFIAutoGenerateRequest } from "@/modules/ma/types/rfi";
import { formatISODate } from "@/modules/ma/utils/format";

import RFIDashboard from "./RFIDashboard";
import RFIItemDetail from "./RFIItemDetail";
import RFIItemList from "./RFIItemList";
import RFICreateModal from "./RFICreateModal";

interface RFIPanelProps {
  txnId: string;
}

type TabType = "dashboard" | "list";

function getRFIAttachmentDownloadUrl(txnId: string, attachmentId: string) {
  return `/api/ma/transactions/${txnId}/rfi/attachments/${attachmentId}/download`;
}

function getAttachmentStatusLabel(attachment: RFIAttachment) {
  return attachment.is_mapped ? "매핑됨" : "미매핑";
}

export default function RFIPanel({ txnId }: RFIPanelProps) {
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showGenerateModal, setShowGenerateModal] = useState(false);
  const [activeTab, setActiveTab] = useState<TabType>("list");
  const [genIndustry, setGenIndustry] = useState("");
  const [genPurpose, setGenPurpose] = useState("");
  const [genFocusAreas, setGenFocusAreas] = useState("");

  const excelFileInputRef = useRef<HTMLInputElement>(null);
  const rfiUploadInputRef = useRef<HTMLInputElement>(null);

  const exportRFI = useExportRFI(txnId);
  const importRFI = useImportRFI(txnId);
  const generateRFI = useGenerateRFI(txnId);
  const uploadRFI = useUploadAttachments(txnId);
  const deleteRFIAttachment = useDeleteRFIAttachment(txnId);
  const { data: uploadedRFIAttachments } = useRFIAttachments(txnId);

  const rfiAttachments = uploadedRFIAttachments ?? [];

  const handleImportClick = () => {
    openAttachmentFilePicker(excelFileInputRef);
  };

  const handleUploadClick = () => {
    openAttachmentFilePicker(rfiUploadInputRef);
  };

  const handleExcelFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    importRFI.mutate(file);
    event.target.value = "";
  };

  const handleRFIUploadChange = (event: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? []);
    const validFiles = files.filter((file) => {
      const error = validateAttachmentFile(file);
      if (error) {
        toast.error(error);
        return false;
      }
      return true;
    });

    if (validFiles.length > 0) {
      uploadRFI.mutate(validFiles);
    }

    event.target.value = "";
  };

  const handleGenerateSubmit = () => {
    if (!genIndustry.trim() || !genPurpose.trim()) return;

    const payload: RFIAutoGenerateRequest = {
      industry: genIndustry.trim(),
      deal_purpose: genPurpose.trim(),
      focus_areas: genFocusAreas
        .split(",")
        .map((value) => value.trim())
        .filter(Boolean),
    };

    generateRFI.mutate(payload, {
      onSuccess: () => {
        setShowGenerateModal(false);
        setGenIndustry("");
        setGenPurpose("");
        setGenFocusAreas("");
      },
    });
  };

  const handleDeleteAttachment = (attachmentId: string) => {
    if (!window.confirm("업로드한 RFI 파일을 삭제하시겠습니까?")) {
      return;
    }

    deleteRFIAttachment.mutate(attachmentId);
  };

  if (selectedItemId) {
    return (
      <RFIItemDetail
        txnId={txnId}
        itemId={selectedItemId}
        onBack={() => setSelectedItemId(null)}
      />
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
          <h2 className="text-lg font-semibold text-text-dark">RFI 관리</h2>

          <div className="flex items-center gap-1 lg:ml-4" role="tablist">
            <Button
              size="sm"
              variant={activeTab === "dashboard" ? "primary" : "secondary"}
              onClick={() => setActiveTab("dashboard")}
              role="tab"
              id="rfi-tab-dashboard"
              aria-selected={activeTab === "dashboard"}
              aria-controls="rfi-tabpanel-dashboard"
            >
              대시보드
            </Button>
            <Button
              size="sm"
              variant={activeTab === "list" ? "primary" : "secondary"}
              onClick={() => setActiveTab("list")}
              role="tab"
              id="rfi-tab-list"
              aria-selected={activeTab === "list"}
              aria-controls="rfi-tabpanel-list"
            >
              목록
            </Button>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 xl:justify-end">
          <Button
            size="sm"
            variant="primary"
            icon={Plus}
            onClick={() => setShowCreateModal(true)}
          >
            질의 추가
          </Button>
          <Button
            size="sm"
            variant="secondary"
            icon={Download}
            onClick={() => exportRFI.mutate(undefined)}
            loading={exportRFI.isPending}
          >
            Excel 내보내기
          </Button>
          <Button
            size="sm"
            variant="secondary"
            icon={Upload}
            onClick={handleImportClick}
            loading={importRFI.isPending}
          >
            Excel 가져오기
          </Button>
          <Button
            size="sm"
            variant="secondary"
            icon={Paperclip}
            onClick={handleUploadClick}
            loading={uploadRFI.isPending}
          >
            RFI 업로드
          </Button>
          <Button
            size="sm"
            variant="accent"
            icon={Sparkles}
            onClick={() => setShowGenerateModal(true)}
            loading={generateRFI.isPending}
          >
            AI 생성
          </Button>
        </div>
      </div>

      {rfiAttachments.length > 0 ? (
        <Card title={`업로드한 RFI 파일 (${rfiAttachments.length}건)`} padding="none">
          <div className="divide-y divide-gray-border">
            {rfiAttachments.map((attachment) => (
              <div
                key={attachment.id}
                className="flex flex-col gap-3 px-4 py-3 lg:flex-row lg:items-center lg:justify-between"
              >
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <Paperclip className="h-4 w-4 text-text-muted" />
                    <p className="truncate text-sm font-medium text-text-dark">
                      {attachment.file_name}
                    </p>
                    <Badge
                      variant={attachment.is_mapped ? "info" : "neutral"}
                      pill
                    >
                      {getAttachmentStatusLabel(attachment)}
                    </Badge>
                  </div>
                  <p className="mt-1 text-xs text-text-secondary">
                    업로드일 {formatISODate(attachment.created_at)}
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="ghost"
                    icon={Download}
                    onClick={() =>
                      window.open(
                        getRFIAttachmentDownloadUrl(txnId, attachment.id),
                        "_blank",
                        "noopener,noreferrer",
                      )
                    }
                  >
                    다운로드
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    icon={Trash2}
                    onClick={() => handleDeleteAttachment(attachment.id)}
                    disabled={deleteRFIAttachment.isPending}
                    aria-label={`${attachment.file_name} 삭제`}
                  >
                    삭제
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </Card>
      ) : null}

      <div
        role="tabpanel"
        id={`rfi-tabpanel-${activeTab}`}
        aria-labelledby={`rfi-tab-${activeTab}`}
      >
        {activeTab === "dashboard" ? (
          <RFIDashboard txnId={txnId} />
        ) : (
          <RFIItemList txnId={txnId} onSelectItem={setSelectedItemId} />
        )}
      </div>

      <input
        ref={excelFileInputRef}
        type="file"
        accept=".xlsx,.xls"
        className="hidden"
        aria-label="Excel 파일 선택"
        onChange={handleExcelFileChange}
      />
      <input
        ref={rfiUploadInputRef}
        type="file"
        className="hidden"
        multiple
        aria-label="RFI 파일 선택"
        onChange={handleRFIUploadChange}
      />

      <RFICreateModal
        txnId={txnId}
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
      />

      <Modal
        open={showGenerateModal}
        onClose={() => {
          if (!generateRFI.isPending) setShowGenerateModal(false);
        }}
        title="AI RFI 자동 생성"
        size="md"
      >
        <div className="space-y-4">
          <div>
            <label
              htmlFor="gen-industry"
              className="mb-1 block text-sm font-medium text-text-body"
            >
              산업군 <span className="text-red-500">*</span>
            </label>
            <input
              id="gen-industry"
              type="text"
              value={genIndustry}
              onChange={(event) => setGenIndustry(event.target.value)}
              placeholder="예: 제조업, IT/소프트웨어, 유통"
              className="w-full rounded-md border border-gray-border px-3 py-2 text-sm focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/40"
            />
          </div>
          <div>
            <label
              htmlFor="gen-purpose"
              className="mb-1 block text-sm font-medium text-text-body"
            >
              거래 목적 <span className="text-red-500">*</span>
            </label>
            <input
              id="gen-purpose"
              type="text"
              value={genPurpose}
              onChange={(event) => setGenPurpose(event.target.value)}
              placeholder="예: 경영권 인수, 지분 투자, 합병"
              className="w-full rounded-md border border-gray-border px-3 py-2 text-sm focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/40"
            />
          </div>
          <div>
            <label
              htmlFor="gen-focus"
              className="mb-1 block text-sm font-medium text-text-body"
            >
              중점 분야 (쉼표 구분)
            </label>
            <input
              id="gen-focus"
              type="text"
              value={genFocusAreas}
              onChange={(event) => setGenFocusAreas(event.target.value)}
              placeholder="예: 재무, 법무, 인사, IT"
              className="w-full rounded-md border border-gray-border px-3 py-2 text-sm focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/40"
            />
          </div>
        </div>
        <div className="mt-4 flex justify-end gap-2 border-t border-gray-border pt-4">
          <Button
            size="sm"
            variant="secondary"
            onClick={() => setShowGenerateModal(false)}
          >
            취소
          </Button>
          <Button
            size="sm"
            variant="accent"
            icon={Sparkles}
            onClick={handleGenerateSubmit}
            loading={generateRFI.isPending}
            disabled={!genIndustry.trim() || !genPurpose.trim()}
          >
            생성
          </Button>
        </div>
      </Modal>
    </div>
  );
}
