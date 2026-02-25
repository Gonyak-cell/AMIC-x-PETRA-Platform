import { useState, useMemo, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import {
  FileText,
  FolderOpen,
  Check,
  ArrowRight,
  ArrowLeft,
  CheckCircle,
  Loader2,
  Building2,
} from "lucide-react";
import {
  Button,
  Card,
  Input,
  Select,
  PageHero,
  Spinner,
  EmptyState,
} from "@/components/ui";
import { useTransactions } from "@/modules/ma/hooks/useTransactions";
import {
  useTransactionVdrFolders,
  useTransactionVdrDocuments,
  useCreateFromVdr,
} from "@/modules/im/hooks/useVdrDocumentSelector";
import { formatBytes } from "@/lib/format";
import type { IMStyle, IndustryId } from "@/modules/im/types/document";
import { isIMStyle } from "@/modules/im/types/document";
import { INDUSTRY_OPTIONS, isIndustryId } from "@/types/industry";
import type { VdrDocument, VdrFolder } from "@/modules/ma/types/vdr";
import { MIME_TYPE_LABELS } from "@/modules/ma/types/vdr";
import heroImg from "@/assets/images/heroes/hero-arch-mono.jpg";

// ── Step titles ──────────────────────────────────────────────

const STEP_TITLES = [
  "Select Transaction & VDR Documents",
  "IM Settings",
  "Review & Start",
];

const STYLE_OPTIONS = [
  { value: "TITAN", label: "Titan - Concise Summary" },
  { value: "COVENANT", label: "Covenant - Financial Focus" },
  { value: "FULL", label: "Full - Comprehensive" },
  { value: "TEASER", label: "Teaser - One-pager" },
];

// ── Helper: flatten folder tree to get all folders ───────────

function flattenFolders(folders: VdrFolder[]): VdrFolder[] {
  const result: VdrFolder[] = [];
  for (const f of folders) {
    result.push(f);
    if (f.children?.length) {
      result.push(...flattenFolders(f.children));
    }
  }
  return result;
}

// ── Main Component ──────────────────────────────────────────

export default function CreateFromVdrPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);

  // Step 0 state
  const [selectedTxnId, setSelectedTxnId] = useState("");
  const [activeFolderId, setActiveFolderId] = useState<string | null>(null);
  const [selectedDocIds, setSelectedDocIds] = useState<Set<string>>(new Set());
  const [selectedDocNames, setSelectedDocNames] = useState<Map<string, string>>(new Map());

  // Step 1 state
  const [companyName, setCompanyName] = useState("");
  const [projectName, setProjectName] = useState("");
  const [imStyle, setImStyle] = useState<IMStyle>("FULL");
  const [industry, setIndustry] = useState<IndustryId>("general");

  // Queries
  const { data: txnData, isLoading: txnLoading } = useTransactions({
    limit: 100,
    status: "ACTIVE",
  });
  const transactions = useMemo(() => txnData?.items ?? [], [txnData]);

  const { data: folders, isLoading: foldersLoading } =
    useTransactionVdrFolders(selectedTxnId);
  const flatFolders = useMemo(
    () => (folders ? flattenFolders(folders) : []),
    [folders],
  );

  const { data: folderDocs, isLoading: docsLoading } =
    useTransactionVdrDocuments(selectedTxnId, activeFolderId ?? "");

  const createFromVdr = useCreateFromVdr();

  // ── Transaction selection ──────────────────────────────────

  const selectedTxn = useMemo(
    () => transactions.find((t) => t.id === selectedTxnId),
    [transactions, selectedTxnId],
  );

  const handleTxnChange = useCallback(
    (txnId: string) => {
      setSelectedTxnId(txnId);
      setActiveFolderId(null);
      setSelectedDocIds(new Set());
      setSelectedDocNames(new Map());

      const txn = transactions.find((t) => t.id === txnId);
      if (txn) {
        setCompanyName(txn.target_company_name);
        setProjectName(txn.code_name);
        if (txn.industry && isIndustryId(txn.industry)) {
          setIndustry(txn.industry);
        }
      }
    },
    [transactions],
  );

  // ── Document selection ─────────────────────────────────────

  const toggleDoc = useCallback(
    (doc: VdrDocument) => {
      setSelectedDocIds((prev) => {
        const next = new Set(prev);
        if (next.has(doc.id)) {
          next.delete(doc.id);
        } else {
          next.add(doc.id);
        }
        return next;
      });
      setSelectedDocNames((prev) => {
        const next = new Map(prev);
        if (next.has(doc.id)) {
          next.delete(doc.id);
        } else {
          next.set(doc.id, doc.original_name);
        }
        return next;
      });
    },
    [],
  );

  const selectAllInFolder = useCallback(() => {
    if (!folderDocs) return;
    const allSelected = folderDocs.every((d) => selectedDocIds.has(d.id));
    if (allSelected) {
      // Deselect all in this folder
      setSelectedDocIds((prev) => {
        const next = new Set(prev);
        folderDocs.forEach((d) => next.delete(d.id));
        return next;
      });
      setSelectedDocNames((prev) => {
        const next = new Map(prev);
        folderDocs.forEach((d) => next.delete(d.id));
        return next;
      });
    } else {
      // Select all in this folder
      setSelectedDocIds((prev) => {
        const next = new Set(prev);
        folderDocs.forEach((d) => next.add(d.id));
        return next;
      });
      setSelectedDocNames((prev) => {
        const next = new Map(prev);
        folderDocs.forEach((d) => next.set(d.id, d.original_name));
        return next;
      });
    }
  }, [folderDocs, selectedDocIds]);

  // ── Navigation ─────────────────────────────────────────────

  const canProceedStep0 = selectedTxnId && selectedDocIds.size > 0;
  const canProceedStep1 =
    companyName.trim().length > 0 && projectName.trim().length > 0;

  const handleNext = () => setStep((s) => Math.min(s + 1, 2));
  const handleBack = () => setStep((s) => Math.max(s - 1, 0));

  // ── Submit ─────────────────────────────────────────────────

  const handleSubmit = async () => {
    try {
      const result = await createFromVdr.mutateAsync({
        transaction_id: selectedTxnId,
        vdr_document_ids: Array.from(selectedDocIds),
        company_name: companyName,
        project_name: projectName,
        im_style: imStyle,
        industry,
      });
      toast.success("VDR extraction started");
      navigate(`/im/documents/${result.document_id}/checklist`);
    } catch {
      toast.error("Failed to start VDR extraction");
    }
  };

  // ── Render ─────────────────────────────────────────────────

  return (
    <div className="space-y-6">
      <PageHero
        title="Create IM from VDR"
        subtitle="Extract data from Virtual Data Room documents to populate your IM"
        backgroundImage={heroImg}
        backgroundOpacity={0.18}
        compact
      />

      <Card>
        {/* Step indicator */}
        <ol
          className="flex items-center gap-2 mb-6 list-none p-0 m-0"
          aria-label="Creation steps"
        >
          {STEP_TITLES.map((title, i) => (
            <li
              key={title}
              className="flex items-center gap-2"
              aria-current={i === step ? "step" : undefined}
            >
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                  i === step
                    ? "bg-amic text-white"
                    : i < step
                      ? "bg-positive text-white"
                      : "bg-gray-100 text-text-secondary"
                }`}
                aria-label={`Step ${i + 1}: ${title}${i < step ? " (completed)" : i === step ? " (current)" : ""}`}
              >
                {i < step ? <Check className="h-4 w-4" /> : i + 1}
              </div>
              <span
                className={`text-sm hidden sm:inline ${
                  i === step
                    ? "text-text-dark font-medium"
                    : "text-text-secondary"
                }`}
              >
                {title}
              </span>
              {i < STEP_TITLES.length - 1 && (
                <div
                  className="w-8 h-px bg-gray-200 hidden sm:block"
                  aria-hidden="true"
                />
              )}
            </li>
          ))}
        </ol>

        {/* ── Step 0: Transaction & VDR Documents ── */}
        {step === 0 && (
          <div className="space-y-5">
            {/* Transaction Selector */}
            <div>
              <label className="block text-sm font-medium text-text-dark mb-2">
                Select Transaction
              </label>
              {txnLoading ? (
                <Spinner size="sm" />
              ) : transactions.length === 0 ? (
                <EmptyState
                  icon={Building2}
                  title="No active transactions"
                  description="Create an M&A transaction first to use VDR-based IM creation."
                />
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  {transactions.map((txn) => (
                    <button
                      key={txn.id}
                      type="button"
                      onClick={() => handleTxnChange(txn.id)}
                      className={`text-left p-3 rounded-lg border transition-colors ${
                        selectedTxnId === txn.id
                          ? "border-accent bg-accent/5 ring-1 ring-accent"
                          : "border-gray-border bg-white hover:border-amic/30"
                      }`}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <Building2 className="h-4 w-4 text-amic flex-shrink-0" />
                        <span className="font-medium text-sm text-text-dark truncate">
                          {txn.code_name}
                        </span>
                      </div>
                      <p className="text-xs text-text-secondary truncate">
                        {txn.target_company_name}
                      </p>
                      <div className="flex items-center gap-2 mt-1.5">
                        <span className="px-1.5 py-0.5 text-[10px] bg-gray-100 rounded text-text-secondary">
                          {txn.phase}
                        </span>
                        <span className="px-1.5 py-0.5 text-[10px] bg-gray-100 rounded text-text-secondary">
                          {txn.side}
                        </span>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* VDR Document Selection */}
            {selectedTxnId && (
              <div className="space-y-3">
                <label className="block text-sm font-medium text-text-dark">
                  Select VDR Documents
                </label>
                <div className="border border-gray-border rounded-lg overflow-hidden">
                  <div className="grid grid-cols-1 sm:grid-cols-[240px_1fr]">
                    {/* Folder sidebar */}
                    <div className="border-b sm:border-b-0 sm:border-r border-gray-border bg-bg-cool p-2 overflow-y-auto max-h-[400px]">
                      {foldersLoading ? (
                        <div className="flex items-center justify-center py-8">
                          <Spinner size="sm" />
                        </div>
                      ) : flatFolders.length === 0 ? (
                        <p className="text-xs text-text-secondary text-center py-4">
                          No VDR folders. Initialize VDR first.
                        </p>
                      ) : (
                        <ul className="space-y-0.5">
                          {flatFolders.map((folder) => (
                            <li key={folder.id}>
                              <button
                                type="button"
                                onClick={() =>
                                  setActiveFolderId(folder.id)
                                }
                                className={`w-full text-left px-3 py-2 rounded text-sm flex items-center gap-2 transition-colors ${
                                  activeFolderId === folder.id
                                    ? "bg-accent/10 text-accent font-medium"
                                    : "text-text-secondary hover:bg-white"
                                }`}
                              >
                                <FolderOpen className="h-3.5 w-3.5 flex-shrink-0" />
                                <span className="truncate">{folder.name}</span>
                                {folder.document_count > 0 && (
                                  <span className="ml-auto text-[10px] text-text-secondary bg-white rounded-full px-1.5">
                                    {folder.document_count}
                                  </span>
                                )}
                              </button>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>

                    {/* Document list */}
                    <div className="p-3 overflow-y-auto max-h-[400px]">
                      {!activeFolderId ? (
                        <p className="text-sm text-text-secondary text-center py-8">
                          Select a folder to view documents
                        </p>
                      ) : docsLoading ? (
                        <div className="flex items-center justify-center py-8">
                          <Spinner size="sm" />
                        </div>
                      ) : !folderDocs || folderDocs.length === 0 ? (
                        <p className="text-sm text-text-secondary text-center py-8">
                          No documents in this folder
                        </p>
                      ) : (
                        <div className="space-y-2">
                          {/* Select all toggle */}
                          <div className="flex items-center justify-between pb-2 border-b border-gray-border">
                            <span className="text-xs text-text-secondary">
                              {folderDocs.length} document(s)
                            </span>
                            <button
                              type="button"
                              onClick={selectAllInFolder}
                              className="text-xs text-accent hover:underline"
                            >
                              {folderDocs.every((d) =>
                                selectedDocIds.has(d.id),
                              )
                                ? "Deselect All"
                                : "Select All"}
                            </button>
                          </div>

                          {folderDocs.map((doc) => {
                            const isSelected = selectedDocIds.has(doc.id);
                            const mimeLabel =
                              MIME_TYPE_LABELS[doc.mime_type] ??
                              doc.mime_type.split("/").pop();
                            return (
                              <button
                                key={doc.id}
                                type="button"
                                onClick={() => toggleDoc(doc)}
                                className={`w-full text-left px-3 py-2 rounded-lg border flex items-center gap-3 transition-colors ${
                                  isSelected
                                    ? "border-accent bg-accent/5"
                                    : "border-gray-border bg-white hover:border-amic/30"
                                }`}
                              >
                                <div
                                  className={`w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 ${
                                    isSelected
                                      ? "bg-accent border-accent"
                                      : "border-gray-300 bg-white"
                                  }`}
                                >
                                  {isSelected && (
                                    <Check className="h-3 w-3 text-white" />
                                  )}
                                </div>
                                <FileText className="h-4 w-4 text-text-secondary flex-shrink-0" />
                                <div className="flex-1 min-w-0">
                                  <p className="text-sm text-text-dark truncate">
                                    {doc.original_name}
                                  </p>
                                  <p className="text-[10px] text-text-secondary">
                                    {mimeLabel} &middot;{" "}
                                    {formatBytes(doc.file_size_bytes)}
                                  </p>
                                </div>
                              </button>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Selected count */}
                {selectedDocIds.size > 0 && (
                  <div className="flex items-center gap-2 text-sm text-accent font-medium">
                    <CheckCircle className="h-4 w-4" />
                    {selectedDocIds.size} document(s) selected
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ── Step 1: IM Settings ── */}
        {step === 1 && (
          <div className="space-y-5">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="Company Name *"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                placeholder="e.g. Target Corp"
              />
              <Input
                label="Project Name *"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                placeholder="e.g. Project TITAN"
              />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Select
                label="IM Style"
                options={STYLE_OPTIONS}
                value={imStyle}
                onChange={(e) => {
                  const v = e.target.value;
                  if (isIMStyle(v)) setImStyle(v);
                }}
              />
              <Select
                label="Industry"
                options={INDUSTRY_OPTIONS}
                value={industry}
                onChange={(e) => {
                  const v = e.target.value;
                  if (isIndustryId(v)) setIndustry(v);
                }}
              />
            </div>
          </div>
        )}

        {/* ── Step 2: Review & Confirm ── */}
        {step === 2 && (
          <div className="space-y-5">
            <h4 className="text-sm font-heading font-semibold text-text-dark">
              Review & Confirm
            </h4>
            <div className="bg-bg-cool rounded-lg p-4 space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-text-secondary">Transaction</span>
                <span className="text-text-dark font-medium">
                  {selectedTxn?.code_name ?? "--"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">
                  Target Company
                </span>
                <span className="text-text-dark font-medium">
                  {companyName}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">Project Name</span>
                <span className="text-text-dark font-medium">
                  {projectName}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">IM Style</span>
                <span className="text-text-dark">{imStyle}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">Industry</span>
                <span className="text-text-dark">{industry}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">VDR Documents</span>
                <span className="text-text-dark font-medium">
                  {selectedDocIds.size} selected
                </span>
              </div>
              {/* Selected documents list */}
              <div className="border-t border-gray-border pt-2 mt-2">
                <span className="text-xs text-text-secondary block mb-1.5">
                  Selected Documents:
                </span>
                <ul className="space-y-1">
                  {Array.from(selectedDocNames.entries()).map(
                    ([id, name]) => (
                      <li
                        key={id}
                        className="flex items-center gap-2 text-xs text-text-dark"
                      >
                        <FileText className="h-3 w-3 text-text-secondary flex-shrink-0" />
                        <span className="truncate">{name}</span>
                      </li>
                    ),
                  )}
                </ul>
              </div>
            </div>

            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
              <p className="text-sm text-amber-800">
                <strong>Note:</strong> After starting extraction, the system
                will analyze the selected VDR documents and populate the IM
                checklist. You will be able to review and confirm each data
                point before generating the final IM.
              </p>
            </div>
          </div>
        )}

        {/* Navigation */}
        <div className="flex justify-between mt-8 pt-4 border-t border-gray-border">
          <Button
            variant="ghost"
            icon={ArrowLeft}
            onClick={step === 0 ? () => navigate("/im") : handleBack}
          >
            {step === 0 ? "Cancel" : "Back"}
          </Button>
          {step < 2 ? (
            <Button
              variant="primary"
              icon={ArrowRight}
              iconPosition="right"
              onClick={handleNext}
              disabled={
                (step === 0 && !canProceedStep0) ||
                (step === 1 && !canProceedStep1)
              }
            >
              Next
            </Button>
          ) : (
            <Button
              variant="accent"
              icon={Loader2}
              onClick={handleSubmit}
              loading={createFromVdr.isPending}
            >
              Start Extraction
            </Button>
          )}
        </div>
      </Card>
    </div>
  );
}
