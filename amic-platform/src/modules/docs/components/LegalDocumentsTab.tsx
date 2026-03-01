import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Plus,
  Download,
  Trash2,
  RefreshCw,
  FileText,
  AlertCircle,
  Sparkles,
} from "lucide-react";
import {
  useLegalDocuments,
  useDeleteLegalDocument,
  useRegenerateLegalDocument,
  getLegalDocDownloadUrl,
  formatFileSize,
} from "@/modules/docs/hooks/useLegalDocuments";
import type {
  LegalDocument,
  LegalDocType,
} from "@/modules/docs/types/legal_document";
import { LEGAL_DOC_META } from "@/modules/docs/types/legal_document";

const STATUS_BADGE: Record<string, string> = {
  DRAFT: "bg-gray-100 text-gray-600",
  GENERATING: "bg-yellow-100 text-yellow-700 animate-pulse",
  READY: "bg-emerald-100 text-emerald-700",
  FAILED: "bg-negative-light text-negative",
};

const STATUS_LABEL: Record<string, string> = {
  DRAFT: "초안",
  GENERATING: "생성 중",
  READY: "완료",
  FAILED: "실패",
};

const DOC_TYPE_BADGE: Record<LegalDocType, string> = {
  SPA: "bg-info-light text-info",
  SHA: "bg-violet-100 text-violet-700",
  BTA: "bg-emerald-100 text-emerald-700",
  SSA: "bg-orange-100 text-orange-700",
  MOU: "bg-sky-100 text-sky-700",
};

interface LegalDocumentsTabProps {
  txnId: string;
}

export default function LegalDocumentsTab({ txnId }: LegalDocumentsTabProps) {
  const navigate = useNavigate();
  const { data: docs, isLoading } = useLegalDocuments(txnId);
  const deleteMut = useDeleteLegalDocument(txnId);
  const regenMut = useRegenerateLegalDocument(txnId);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const handleNew = (type?: LegalDocType) => {
    const params = new URLSearchParams({ txn_id: txnId });
    if (type) params.set("type", type);
    navigate(`/docs/legal/new?${params.toString()}`);
  };

  const handleRegenerate = (doc: LegalDocument) => {
    regenMut.mutate({
      docId: doc.id,
      body: {
        doc_type: doc.doc_type,
        title: doc.title,
        parameters: doc.parameters ?? {},
      },
    });
  };

  const handleDelete = async (docId: string) => {
    if (confirmDeleteId === docId) {
      await deleteMut.mutateAsync(docId);
      setConfirmDeleteId(null);
    } else {
      setConfirmDeleteId(docId);
    }
  };

  if (isLoading) {
    return (
      <div className="flex h-40 items-center justify-center">
        <RefreshCw className="h-5 w-5 animate-spin text-text-tertiary" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-text-primary">법률 문서</h3>
          <p className="text-xs text-text-secondary">
            SPA, SHA, BTA, SSA 생성 및 다운로드
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => navigate(`/docs/legal/generate?txn_id=${txnId}`)}
            className="flex items-center gap-1.5 rounded-lg border border-accent-primary px-3 py-1.5 text-xs font-medium text-accent-primary hover:bg-accent-primary/5"
          >
            <Sparkles className="h-3.5 w-3.5" />
            AI 계약서 생성
          </button>
          <button
            type="button"
            onClick={() => handleNew()}
            className="flex items-center gap-1.5 rounded-lg bg-accent-primary px-3 py-1.5 text-xs font-medium text-white hover:bg-accent-primary/90"
          >
            <Plus className="h-3.5 w-3.5" />새 법률 문서
          </button>
        </div>
      </div>

      {/* 빠른 생성 버튼 */}
      <div className="flex flex-wrap gap-2">
        {(["SPA", "SHA", "BTA", "SSA"] as LegalDocType[]).map((type) => (
          <button
            key={type}
            type="button"
            onClick={() => handleNew(type)}
            className="rounded-full border border-border px-3 py-1 text-xs text-text-secondary hover:border-accent-primary hover:text-accent-primary"
          >
            {type} 생성
          </button>
        ))}
      </div>

      {/* 문서 목록 */}
      {!docs || docs.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-border py-12 text-center">
          <FileText className="h-8 w-8 text-text-tertiary" />
          <div>
            <p className="text-sm font-medium text-text-secondary">
              생성된 법률 문서가 없습니다
            </p>
            <p className="text-xs text-text-tertiary">
              위 버튼으로 SPA, SHA 등 법률 문서를 생성하세요
            </p>
          </div>
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-border">
          <table className="w-full text-sm">
            <thead className="bg-white">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-text-tertiary">
                  유형
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-text-tertiary">
                  제목
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-text-tertiary">
                  상태
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-text-tertiary">
                  크기
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-text-tertiary">
                  생성일
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-text-tertiary">
                  작업
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {docs.map((doc: LegalDocument) => (
                <tr key={doc.id} className="hover:bg-white-elevated/50">
                  <td className="px-4 py-3">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium ${DOC_TYPE_BADGE[doc.doc_type]}`}
                    >
                      {doc.doc_type}
                    </span>
                  </td>
                  <td className="max-w-[200px] px-4 py-3">
                    <p className="truncate text-sm font-medium text-text-primary">
                      {doc.title}
                    </p>
                    <p className="text-xs text-text-tertiary">
                      {LEGAL_DOC_META[doc.doc_type].labelKo}
                    </p>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_BADGE[doc.status]}`}
                    >
                      {STATUS_LABEL[doc.status]}
                    </span>
                    {doc.status === "FAILED" && doc.error_message && (
                      <div className="mt-1 flex items-center gap-1 text-xs text-negative">
                        <AlertCircle className="h-3 w-3" />
                        <span
                          className="truncate max-w-[120px]"
                          title={doc.error_message}
                        >
                          오류 발생
                        </span>
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-xs text-text-tertiary">
                    {formatFileSize(doc.file_size_bytes)}
                  </td>
                  <td className="px-4 py-3 text-xs text-text-tertiary">
                    {new Date(doc.created_at).toLocaleDateString("ko-KR")}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      {doc.status === "READY" && (
                        <a
                          href={getLegalDocDownloadUrl(txnId, doc.id)}
                          download={
                            doc.file_name ?? `${doc.doc_type}_${doc.id}.docx`
                          }
                          className="flex items-center gap-1 rounded-md p-1.5 text-text-secondary hover:bg-white hover:text-accent-primary"
                          title="다운로드"
                        >
                          <Download className="h-4 w-4" />
                        </a>
                      )}
                      {(doc.status === "READY" || doc.status === "FAILED") && (
                        <button
                          type="button"
                          onClick={() => handleRegenerate(doc)}
                          disabled={regenMut.isPending}
                          className="rounded-md p-1.5 text-text-tertiary hover:bg-white hover:text-accent-primary disabled:opacity-40"
                          title="재생성"
                        >
                          <RefreshCw
                            className={`h-4 w-4 ${regenMut.isPending ? "animate-spin" : ""}`}
                          />
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => handleDelete(doc.id)}
                        className={`rounded-md p-1.5 hover:bg-white ${
                          confirmDeleteId === doc.id
                            ? "text-negative"
                            : "text-text-tertiary hover:text-negative"
                        }`}
                        title={
                          confirmDeleteId === doc.id
                            ? "다시 클릭하면 삭제됩니다"
                            : "삭제"
                        }
                        disabled={deleteMut.isPending}
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
