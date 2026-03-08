import { useRef, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Plus, Download, Upload, Sparkles } from "lucide-react";
import { Modal } from "@/components/ui/Modal";
import {
  useExportRFI,
  useImportRFI,
  useGenerateRFI,
} from "@/modules/ma/hooks/useRFI";
import type { RFIAutoGenerateRequest } from "@/modules/ma/types/rfi";
import RFIDashboard from "./RFIDashboard";
import RFIItemList from "./RFIItemList";
import RFIItemDetail from "./RFIItemDetail";
import RFICreateModal from "./RFICreateModal";

interface RFIPanelProps {
  txnId: string;
}

type TabType = "dashboard" | "list";

export default function RFIPanel({ txnId }: RFIPanelProps) {
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showGenerateModal, setShowGenerateModal] = useState(false);
  const [activeTab, setActiveTab] = useState<TabType>("list");

  // AI generate form state
  const [genIndustry, setGenIndustry] = useState("");
  const [genPurpose, setGenPurpose] = useState("");
  const [genFocusAreas, setGenFocusAreas] = useState("");

  const fileInputRef = useRef<HTMLInputElement>(null);

  const exportRFI = useExportRFI(txnId);
  const importRFI = useImportRFI(txnId);
  const generateRFI = useGenerateRFI(txnId);

  const handleImportClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    importRFI.mutate(file);
    // Reset input so the same file can be re-selected
    e.target.value = "";
  };

  const handleGenerateSubmit = () => {
    if (!genIndustry.trim() || !genPurpose.trim()) return;
    const payload: RFIAutoGenerateRequest = {
      industry: genIndustry.trim(),
      deal_purpose: genPurpose.trim(),
      focus_areas: genFocusAreas
        .split(",")
        .map((s) => s.trim())
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

  // Detail view takes over the entire panel
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
      {/* Top bar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold text-text-dark">RFI 관리</h2>

          {/* Tab buttons */}
          <div className="flex items-center gap-1 ml-4" role="tablist">
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

        {/* Action buttons */}
        <div className="flex items-center gap-2">
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
            variant="accent"
            icon={Sparkles}
            onClick={() => setShowGenerateModal(true)}
            loading={generateRFI.isPending}
          >
            AI 생성
          </Button>
        </div>
      </div>

      {/* Main content */}
      <div
        role="tabpanel"
        id={"rfi-tabpanel-" + activeTab}
        aria-labelledby={"rfi-tab-" + activeTab}
      >
        {activeTab === "dashboard" ? (
          <RFIDashboard txnId={txnId} />
        ) : (
          <RFIItemList txnId={txnId} onSelectItem={setSelectedItemId} />
        )}
      </div>

      {/* Hidden file input for Excel import */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".xlsx,.xls"
        className="hidden"
        aria-label="Excel 파일 선택"
        onChange={handleFileChange}
      />

      {/* Create modal */}
      <RFICreateModal
        txnId={txnId}
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
      />

      {/* AI Generate modal */}
      <Modal
        open={showGenerateModal}
        onClose={() => { if (!generateRFI.isPending) setShowGenerateModal(false); }}
        title="AI RFI 자동 생성"
        size="md"
      >
        <div className="space-y-4">
          <div>
            <label
              htmlFor="gen-industry"
              className="block text-sm font-medium text-text-body mb-1"
            >
              산업군 <span className="text-red-500">*</span>
            </label>
            <input
              id="gen-industry"
              type="text"
              value={genIndustry}
              onChange={(e) => setGenIndustry(e.target.value)}
              placeholder="예: 제조업, IT/소프트웨어, 유통"
              className="w-full rounded-md border border-gray-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent"
            />
          </div>
          <div>
            <label
              htmlFor="gen-purpose"
              className="block text-sm font-medium text-text-body mb-1"
            >
              거래 목적 <span className="text-red-500">*</span>
            </label>
            <input
              id="gen-purpose"
              type="text"
              value={genPurpose}
              onChange={(e) => setGenPurpose(e.target.value)}
              placeholder="예: 경영권 인수, 지분 투자, 합병"
              className="w-full rounded-md border border-gray-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent"
            />
          </div>
          <div>
            <label
              htmlFor="gen-focus"
              className="block text-sm font-medium text-text-body mb-1"
            >
              중점 분야 (쉼표 구분)
            </label>
            <input
              id="gen-focus"
              type="text"
              value={genFocusAreas}
              onChange={(e) => setGenFocusAreas(e.target.value)}
              placeholder="예: 재무, 법률, 인사, IT"
              className="w-full rounded-md border border-gray-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent"
            />
          </div>
        </div>
        <div className="flex justify-end gap-2 pt-4 mt-4 border-t border-gray-border">
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
