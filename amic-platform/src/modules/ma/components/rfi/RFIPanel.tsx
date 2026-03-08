import { useRef, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Plus, Download, Upload, Sparkles } from "lucide-react";
import {
  useExportRFI,
  useImportRFI,
  useGenerateRFI,
} from "@/modules/ma/hooks/useRFI";
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
  const [activeTab, setActiveTab] = useState<TabType>("list");

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
          <h2 className="text-lg font-semibold text-gray-900">RFI 관리</h2>

          {/* Tab buttons */}
          <div className="flex items-center gap-1 ml-4">
            <Button
              size="sm"
              variant={activeTab === "dashboard" ? "primary" : "secondary"}
              onClick={() => setActiveTab("dashboard")}
            >
              대시보드
            </Button>
            <Button
              size="sm"
              variant={activeTab === "list" ? "primary" : "secondary"}
              onClick={() => setActiveTab("list")}
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
            onClick={() => generateRFI.mutate({})}
            loading={generateRFI.isPending}
          >
            AI 생성
          </Button>
        </div>
      </div>

      {/* Main content */}
      {activeTab === "dashboard" ? (
        <RFIDashboard txnId={txnId} />
      ) : (
        <RFIItemList txnId={txnId} onSelectItem={setSelectedItemId} />
      )}

      {/* Hidden file input for Excel import */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".xlsx,.xls"
        className="hidden"
        onChange={handleFileChange}
      />

      {/* Create modal */}
      <RFICreateModal
        txnId={txnId}
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
      />
    </div>
  );
}
