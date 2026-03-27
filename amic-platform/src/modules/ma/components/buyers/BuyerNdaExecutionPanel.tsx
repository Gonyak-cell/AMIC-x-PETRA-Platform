import { useEffect, useId, useMemo, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  Download,
  FileText,
  PenLine,
  Trash2,
  Upload,
} from "lucide-react";
import { extractApiError } from "@/api/errors";
import { maApi } from "@/api/maClient";
import { FUNNEL_NDA_AND_AFTER } from "@/modules/ma/constants";
import { useCreateNda, useUpdateNda } from "@/modules/ma/hooks/useNdas";
import {
  getNdaMarkupDownloadUrl,
  useDeleteNdaMarkup,
  useNdaMarkups,
} from "@/modules/ma/hooks/useNdaMarkups";
import type { BuyerCandidate } from "@/modules/ma/types/buyer";
import type { NDA } from "@/modules/ma/types/nda";
import type {
  NdaMarkup,
  NdaMarkupListResponse,
} from "@/modules/ma/types/nda_markup";
import { formatFileSize } from "@/modules/ma/utils/format";
import { cn } from "@/lib/cn";
import { toast } from "sonner";
import { Badge, Button, Card, EmptyState, SlidePanel } from "@/components/ui";

const ACCEPT_EXTENSIONS =
  ".docx,.doc,.pdf,.hwp,.hwpx,.xlsx,.xls,.pptx,.ppt,.txt";

function getLocalDateString(): string {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function getNextVersionLabel(markups: NdaMarkup[]): string {
  const nextVersion =
    Math.max(0, ...markups.map((markup) => markup.version_number)) + 1;
  return `v${nextVersion}`;
}

interface BuyerNdaExecutionPanelProps {
  open: boolean;
  onClose: () => void;
  txnId: string;
  buyer: BuyerCandidate | null;
  nda: NDA | null;
  canWrite: boolean;
}

function hasDraggedFiles(event: React.DragEvent<HTMLDivElement>) {
  const types = Array.from(event.dataTransfer.types ?? []);
  return types.includes("Files") || event.dataTransfer.files.length > 0;
}

export default function BuyerNdaExecutionPanel({
  open,
  onClose,
  txnId,
  buyer,
  nda,
  canWrite,
}: BuyerNdaExecutionPanelProps) {
  const queryClient = useQueryClient();
  const fileInputId = useId();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [workingNdaId, setWorkingNdaId] = useState<string | null>(nda?.id ?? null);
  const [selectedMarkupId, setSelectedMarkupId] = useState<string | null>(null);
  const [isDragActive, setIsDragActive] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  const effectiveNdaId = workingNdaId ?? nda?.id ?? "";
  const currentNda = nda ?? (workingNdaId ? { status: "DRAFT" as const } : null);
  const createNda = useCreateNda(txnId);
  const updateNda = useUpdateNda(txnId);
  const deleteMarkup = useDeleteNdaMarkup(txnId, effectiveNdaId);
  const { data, isLoading, isError } = useNdaMarkups(txnId, effectiveNdaId);
  const markups = data?.items;

  const sortedMarkups = useMemo(
    () => [...(markups ?? [])].sort((a, b) => b.version_number - a.version_number),
    [markups],
  );
  const selectedMarkup =
    sortedMarkups.find((markup) => markup.id === selectedMarkupId) ??
    sortedMarkups[0] ??
    null;
  const isSigned =
    currentNda?.status === "SIGNED" ||
    (buyer ? FUNNEL_NDA_AND_AFTER.has(buyer.status) : false);

  useEffect(() => {
    setWorkingNdaId(nda?.id ?? null);
    setSelectedMarkupId(null);
    setIsDragActive(false);
  }, [buyer?.id, nda?.id, open]);

  useEffect(() => {
    if (!selectedMarkupId && sortedMarkups[0]) {
      setSelectedMarkupId(sortedMarkups[0].id);
      return;
    }

    if (
      selectedMarkupId &&
      sortedMarkups.every((markup) => markup.id !== selectedMarkupId)
    ) {
      setSelectedMarkupId(sortedMarkups[0]?.id ?? null);
    }
  }, [selectedMarkupId, sortedMarkups]);

  async function ensureNdaId() {
    if (!buyer) {
      throw new Error("NDA 대상을 찾을 수 없습니다.");
    }

    if (effectiveNdaId) {
      return effectiveNdaId;
    }

    const createdNda = await createNda.mutateAsync({
      party_type: "BUYER",
      buyer_candidate_id: buyer.id,
      counterparty_name: buyer.company_name,
      nda_type: "MUTUAL",
    });
    setWorkingNdaId(createdNda.id);
    return createdNda.id;
  }

  function syncMarkupCache(ndaId: string, markup: NdaMarkup) {
    const queryKey = ["ma", "transactions", txnId, "ndas", ndaId, "markups"];
    queryClient.setQueryData<NdaMarkupListResponse | undefined>(queryKey, (current) => {
      if (!current) {
        return {
          items: [markup],
          total: 1,
          limit: 50,
          offset: 0,
        };
      }

      return {
        ...current,
        items: [...current.items.filter((item) => item.id !== markup.id), markup],
        total: current.items.some((item) => item.id === markup.id)
          ? current.total
          : current.total + 1,
      };
    });
  }

  function syncNdaStatusCache(updatedNda: NDA) {
    const ndaQueries = queryClient.getQueriesData<NDA[]>({
      queryKey: ["ma", "transactions", txnId, "ndas"],
    });

    for (const [queryKey, current] of ndaQueries) {
      if (!Array.isArray(current)) {
        continue;
      }

      queryClient.setQueryData<NDA[]>(queryKey, (items) => {
        if (!items) {
          return items;
        }

        return items.map((item) =>
          item.id === updatedNda.id ? { ...item, ...updatedNda } : item,
        );
      });
    }
  }

  function syncBuyerStatusCache(updatedNda: NDA) {
    if (updatedNda.status !== "SIGNED" || !updatedNda.buyer_candidate_id) {
      return;
    }

    queryClient.setQueryData<BuyerCandidate[]>(
      ["ma", "transactions", txnId, "buyers"],
      (current) =>
        current?.map((candidate) =>
          candidate.id === updatedNda.buyer_candidate_id
            ? {
                ...candidate,
                status: "NDA_SIGNED",
                updated_at: updatedNda.updated_at,
              }
            : candidate,
        ),
    );
  }

  async function handleUploadFile(file: File) {
    if (!buyer || !canWrite) return;

    try {
      setIsUploading(true);
      const nextNdaId = await ensureNdaId();
      const formData = new FormData();
      formData.append("file", file);
      formData.append("version_label", getNextVersionLabel(sortedMarkups));
      formData.append("version_date", getLocalDateString());

      const { data: uploaded } = await maApi.post<NdaMarkup>(
        `/transactions/${txnId}/ndas/${nextNdaId}/markups`,
        formData,
        {
          headers: { "Content-Type": "multipart/form-data" },
        },
      );

      syncMarkupCache(nextNdaId, uploaded);
      setSelectedMarkupId(uploaded.id);
      queryClient.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "ndas"],
      });
      toast.success("NDA 버전이 업로드되었습니다.");
    } catch (error) {
      toast.error(extractApiError(error, "NDA 업로드에 실패했습니다."));
    } finally {
      setIsUploading(false);
      setIsDragActive(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  }

  async function handleSign() {
    if (!canWrite || !buyer || !effectiveNdaId || sortedMarkups.length === 0) {
      return;
    }

    const updatedNda = await updateNda.mutateAsync({
      ndaId: effectiveNdaId,
      body: {
        status: "SIGNED",
        signed_at: getLocalDateString(),
      },
    });

    syncNdaStatusCache(updatedNda);
    syncBuyerStatusCache(updatedNda);

    await Promise.all([
      queryClient.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "ndas"],
      }),
      queryClient.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "buyers"],
      }),
      queryClient.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "short-list", "overview"],
      }),
      queryClient.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "workspace-summary"],
      }),
    ]);

    onClose();
  }

  async function handleDeleteMarkup(markupId: string) {
    if (!canWrite) return;
    deleteMarkup.mutate(markupId);
  }

  if (!buyer) {
    return null;
  }

  return (
    <SlidePanel
      open={open}
      onClose={onClose}
      title={`${buyer.company_name} NDA`}
      subtitle="NDA 버전 관리 및 날인"
      width="lg"
      headerActions={
        isSigned ? (
          <Badge variant="success">SIGNED</Badge>
        ) : canWrite ? (
          <Button
            size="sm"
            variant="accent"
            icon={PenLine}
            disabled={sortedMarkups.length === 0}
            loading={updateNda.isPending}
            onClick={() => {
              void handleSign();
            }}
          >
            날인
          </Button>
        ) : undefined
      }
    >
      <div className="space-y-4">
        <Card className="border-accent/20 bg-accent/5" padding="sm">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-amic">{buyer.company_name}</p>
              <p className="mt-1 text-xs text-text-secondary">
                {buyer.contact_name ?? "담당자 미등록"}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant={isSigned ? "success" : "neutral"}>
                {isSigned ? "SIGNED" : currentNda?.status ?? "READY"}
              </Badge>
              <Badge variant="info">{sortedMarkups.length} version(s)</Badge>
            </div>
          </div>
        </Card>

        <input
          id={fileInputId}
          ref={fileInputRef}
          type="file"
          className="sr-only"
          accept={ACCEPT_EXTENSIONS}
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) {
              void handleUploadFile(file);
            }
          }}
        />

        {sortedMarkups.length === 0 ? (
          <div
            className={cn(
              "rounded-dr border border-dashed p-8 text-center transition-colors",
              isDragActive
                ? "border-accent bg-accent/5"
                : "border-gray-border bg-white",
            )}
            onDragOver={(event) => {
              if (!canWrite) return;
              if (!hasDraggedFiles(event)) return;
              event.preventDefault();
              event.stopPropagation();
              event.dataTransfer.dropEffect = "copy";
              setIsDragActive(true);
            }}
            onDragLeave={(event) => {
              if (!canWrite) return;
              if (!hasDraggedFiles(event)) return;
              event.preventDefault();
              event.stopPropagation();
              setIsDragActive(false);
            }}
            onDrop={(event) => {
              if (!canWrite) return;
              if (!hasDraggedFiles(event)) return;
              event.preventDefault();
              event.stopPropagation();
              setIsDragActive(false);
              const file = event.dataTransfer.files?.[0];
              if (file) {
                void handleUploadFile(file);
              }
            }}
          >
            <EmptyState
              icon={FileText}
              title="업로드된 NDA가 없습니다"
              description="여기에 파일을 드래그하거나 업로드 버튼으로 v1 NDA를 등록하세요."
            />
            {canWrite ? (
              <div className="mt-4 flex justify-center">
                <Button
                  variant="secondary"
                  icon={Upload}
                  loading={isUploading || createNda.isPending}
                  onClick={() => fileInputRef.current?.click()}
                >
                  NDA 업로드
                </Button>
              </div>
            ) : null}
          </div>
        ) : (
          <>
            <Card padding="sm">
              <div className="flex flex-wrap items-center gap-2">
                {sortedMarkups.map((markup) => {
                  const isActive = markup.id === selectedMarkup?.id;

                  return (
                    <button
                      key={markup.id}
                      type="button"
                      onClick={() => setSelectedMarkupId(markup.id)}
                      className={cn(
                        "rounded-full border px-3 py-1 text-sm transition-colors",
                        isActive
                          ? "border-accent bg-accent text-white"
                          : "border-gray-border bg-white text-text-secondary hover:border-accent hover:text-accent",
                      )}
                    >
                      {markup.version_label}
                    </button>
                  );
                })}
                {canWrite ? (
                  <Button
                    size="sm"
                    variant="ghost"
                    icon={Upload}
                    loading={isUploading}
                    onClick={() => fileInputRef.current?.click()}
                  >
                    새 버전 업로드
                  </Button>
                ) : null}
              </div>
            </Card>

            {selectedMarkup ? (
              <Card padding="md">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="font-heading text-lg font-semibold text-text-dark">
                        {selectedMarkup.version_label}
                      </h3>
                      <Badge variant="neutral">{selectedMarkup.version_date}</Badge>
                    </div>
                    <p className="mt-2 text-sm text-text-secondary">
                      {selectedMarkup.file_name ?? "첨부 파일"}
                    </p>
                    <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-text-muted">
                      {selectedMarkup.file_size_bytes != null ? (
                        <span>{formatFileSize(selectedMarkup.file_size_bytes)}</span>
                      ) : null}
                      <span>
                        업로드 {new Date(selectedMarkup.created_at).toLocaleDateString("ko-KR")}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {selectedMarkup.has_file ? (
                      <a
                        href={getNdaMarkupDownloadUrl(
                          txnId,
                          effectiveNdaId,
                          selectedMarkup.id,
                        )}
                        className="inline-flex items-center gap-2 rounded-dr-sm border border-gray-border px-3 py-1.5 text-sm font-medium text-text-secondary transition-colors hover:border-accent hover:text-accent"
                      >
                        <Download className="h-4 w-4" />
                        다운로드
                      </a>
                    ) : null}
                    {canWrite ? (
                      <button
                        type="button"
                        className="inline-flex items-center gap-2 rounded-dr-sm border border-red-100 px-3 py-1.5 text-sm font-medium text-red-500 transition-colors hover:border-red-200 hover:bg-red-50"
                        onClick={() => {
                          void handleDeleteMarkup(selectedMarkup.id);
                        }}
                      >
                        <Trash2 className="h-4 w-4" />
                        삭제
                      </button>
                    ) : null}
                  </div>
                </div>

                {selectedMarkup.changes_summary ? (
                  <div className="mt-4 rounded-dr bg-bg-cool px-4 py-3 text-sm text-text-secondary">
                    {selectedMarkup.changes_summary}
                  </div>
                ) : (
                  <div className="mt-4 rounded-dr border border-dashed border-gray-border px-4 py-3 text-sm text-text-muted">
                    이 버전에 등록된 변경 요약이 없습니다. 파일명을 통해 버전을 확인하세요.
                  </div>
                )}
              </Card>
            ) : null}
          </>
        )}

        {isError ? (
          <div className="flex items-center gap-2 rounded-dr border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-600">
            <AlertCircle className="h-4 w-4" />
            NDA 버전 정보를 불러오지 못했습니다.
          </div>
        ) : null}

        {isLoading && effectiveNdaId ? (
          <div className="rounded-dr border border-gray-border bg-white px-4 py-3 text-sm text-text-secondary">
            NDA 버전을 불러오는 중입니다.
          </div>
        ) : null}
      </div>
    </SlidePanel>
  );
}
