import { useState, useMemo, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import {
  ArrowLeft,
  User,
  Calendar,
  FileText,
  Paperclip,
  XCircle,
  Send,
} from "lucide-react";
import {
  useRFIItem,
  useCreateThread,
  useCloseRFIItem,
} from "@/modules/ma/hooks/useRFI";
import type { RFIThread, RFIAttachment } from "@/modules/ma/types/rfi";
import {
  RFI_ITEM_STATUS_LABELS,
  RFI_CATEGORY_LABELS,
  RFI_PRIORITY_LABELS,
  RFI_ITEM_STATUS_VARIANT,
} from "@/modules/ma/constants";

/* ------------------------------------------------------------------ */
/*  Props                                                              */
/* ------------------------------------------------------------------ */

interface RFIItemDetailProps {
  txnId: string;
  itemId: string;
  onBack: () => void;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}



function isSafeUrl(url: string): boolean {
  try {
    const parsed = new URL(url, window.location.origin);
    return parsed.protocol === "https:" || parsed.protocol === "http:";
  } catch {
    return false;
  }
}
/* ------------------------------------------------------------------ */
/*  Sub-components                                                     */
/* ------------------------------------------------------------------ */

function ThreadBubble({
  thread,
  attachments,
}: {
  thread: RFIThread;
  attachments: RFIAttachment[];
}) {
  const isAdvisor = thread.author_role === "ADVISOR";
  const linkedAttachments = attachments.filter(
    (a) => a.thread_id === thread.id,
  );

  return (
    <div className={`flex ${isAdvisor ? "justify-start" : "justify-end"}`}>
      <div
        className={`max-w-[75%] rounded-lg p-4 ${
          isAdvisor
            ? "bg-teal-50 border-l-4 border-teal-400"
            : "bg-blue-50 border-l-4 border-blue-400 ml-auto"
        }`}
      >
        {/* Author info */}
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xs font-semibold text-text-body">
            {thread.author_email}
          </span>
          <Badge variant={isAdvisor ? "success" : "info"} pill>
            {isAdvisor ? "Advisor" : "Target"}
          </Badge>
          <span className="text-xs text-text-muted">
            Round {thread.round_num}
          </span>
          {!thread.is_published && (
            <span className="text-xs text-amber-600 font-medium">(비공개)</span>
          )}
        </div>

        {/* Content */}
        <p className="text-sm text-text-dark whitespace-pre-wrap leading-relaxed">
          {thread.content_text}
        </p>

        {/* Linked attachments */}
        {linkedAttachments.length > 0 && (
          <div className="mt-2 space-y-1">
            {linkedAttachments.filter((att) => isSafeUrl(att.file_url)).map((att) => (
              <a
                key={att.id}
                href={att.file_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 text-xs text-blue-600 hover:underline"
              >
                <Paperclip className="h-3 w-3" />
                {att.file_name}
              </a>
            ))}
          </div>
        )}

        {/* Timestamp */}
        <p className="text-[11px] text-text-muted mt-2 text-right">
          {formatDateTime(thread.created_at)}
        </p>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */

export default function RFIItemDetail({
  txnId,
  itemId,
  onBack,
}: RFIItemDetailProps) {
  const { data: item, isLoading, isError } = useRFIItem(txnId, itemId);
  const createThread = useCreateThread(txnId, itemId);
  const closeItem = useCloseRFIItem(txnId);

  const [replyText, setReplyText] = useState("");

  const sortedThreads = useMemo(() => {
    if (!item?.threads) return [];
    return [...item.threads].sort(
      (a, b) =>
        new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
    );
  }, [item?.threads]);

  const itemAttachments = useMemo(() => {
    if (!item?.attachments) return [];
    return item.attachments.filter((a) => a.item_id === item.id);
  }, [item?.attachments, item?.id]);

  const isClosed = item?.current_status === "CLOSED";

  function handleSubmitReply(e: FormEvent) {
    e.preventDefault();
    const trimmed = replyText.trim();
    if (!trimmed) return;
    createThread.mutate(
      { content_text: trimmed, is_published: true },
      { onSuccess: () => setReplyText("") },
    );
  }

  function handleClose() {
    if (!item) return;
    closeItem.mutate({ itemId, version: item.version });
  }

  /* ── Loading ──────────────────────────────────────────── */

  if (isError) {
    return (
      <div className="text-center py-12 text-red-600">
        <p className="text-sm">데이터를 불러오는 중 오류가 발생했습니다.</p>
        <Button
          variant="ghost"
          icon={ArrowLeft}
          onClick={onBack}
          size="sm"
          className="mt-4"
        >
          목록으로
        </Button>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!item) {
    return (
      <div className="text-center py-12 text-text-secondary">
        <p>RFI 항목을 찾을 수 없습니다.</p>
        <Button
          variant="ghost"
          icon={ArrowLeft}
          onClick={onBack}
          size="sm"
          className="mt-4"
        >
          목록으로
        </Button>
      </div>
    );
  }

  /* ── Render ───────────────────────────────────────────── */

  return (
    <div className="space-y-5">
      {/* ── Header ───────────────────────────────────────── */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" icon={ArrowLeft} onClick={onBack} size="sm">
          목록
        </Button>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-lg font-bold text-text-dark">
              {item.item_number}
            </h3>
            <Badge variant={RFI_ITEM_STATUS_VARIANT[item.current_status]} pill>
              {RFI_ITEM_STATUS_LABELS[item.current_status]}
            </Badge>
            <span className="text-xs text-text-secondary">
              {RFI_PRIORITY_LABELS[item.priority]}
            </span>
          </div>
        </div>

        {!isClosed && (
          <Button
            variant="danger"
            size="sm"
            icon={XCircle}
            onClick={handleClose}
            loading={closeItem.isPending}
          >
            마감
          </Button>
        )}
      </div>

      {/* ── Question card ────────────────────────────────── */}
      <Card padding="md">
        <p className="text-sm font-semibold text-text-secondary mb-1">질의 내용</p>
        <p className="text-base text-text-dark whitespace-pre-wrap leading-relaxed">
          {item.question_text}
        </p>
      </Card>

      {/* ── Meta info ────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-3 text-xs text-text-body">
        <Badge variant="neutral">{RFI_CATEGORY_LABELS[item.category]}</Badge>

        {item.assignee_email && (
          <span className="flex items-center gap-1">
            <User className="h-3.5 w-3.5 text-text-muted" />
            {item.assignee_email}
          </span>
        )}

        {item.due_date && (
          <span className="flex items-center gap-1">
            <Calendar className="h-3.5 w-3.5 text-text-muted" />
            {formatDate(item.due_date)}
          </span>
        )}

        {item.target_doc && (
          <span className="flex items-center gap-1">
            <FileText className="h-3.5 w-3.5 text-text-muted" />
            {item.target_doc}
          </span>
        )}

        <span className="text-text-muted">{formatDateTime(item.created_at)}</span>
      </div>

      {/* ── Internal memo (ADVISOR only) ─────────────────── */}
      {item.internal_memo && (
        <div className="rounded-lg bg-amber-50 border border-amber-200 p-4">
          <p className="text-xs font-semibold text-amber-700 mb-1">
            Internal Memo
          </p>
          <p className="text-sm text-amber-900 whitespace-pre-wrap">
            {item.internal_memo}
          </p>
        </div>
      )}

      {/* ── Thread timeline ──────────────────────────────── */}
      <div>
        <h4 className="text-sm font-semibold text-text-body mb-3">
          Thread ({sortedThreads.length})
        </h4>

        {sortedThreads.length === 0 ? (
          <Card padding="md">
            <p className="text-center text-sm text-text-muted py-4">
              아직 답변이 없습니다.
            </p>
          </Card>
        ) : (
          <div className="space-y-3">
            {sortedThreads.map((thread) => (
              <ThreadBubble
                key={thread.id}
                thread={thread}
                attachments={item.attachments}
              />
            ))}
          </div>
        )}
      </div>

      {/* ── Reply form ───────────────────────────────────── */}
      {!isClosed && (
        <form onSubmit={handleSubmitReply} className="space-y-2">
          <textarea
            className="w-full rounded-lg border border-gray-border px-4 py-3 text-sm placeholder-text-muted focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none resize-y min-h-[80px]"
            aria-label="답변 내용"
            placeholder="답변을 입력하세요..."
            value={replyText}
            onChange={(e) => setReplyText(e.target.value)}
            rows={3}
          />
          <div className="flex justify-end">
            <Button
              type="submit"
              size="sm"
              icon={Send}
              disabled={!replyText.trim()}
              loading={createThread.isPending}
            >
              답변 등록
            </Button>
          </div>
        </form>
      )}

      {/* ── Attachments ──────────────────────────────────── */}
      {itemAttachments.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-text-body mb-2">
            첨부파일 ({itemAttachments.length})
          </h4>
          <div className="space-y-1">
            {itemAttachments.filter((att) => isSafeUrl(att.file_url)).map((att) => (
              <a
                key={att.id}
                href={att.file_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 rounded-md border border-gray-border px-3 py-2 text-sm text-text-body hover:bg-bg-cool/50 transition-colors"
              >
                <Paperclip className="h-4 w-4 text-text-muted shrink-0" />
                <span className="truncate">{att.file_name}</span>
                {att.vdr_index && (
                  <span className="ml-auto text-xs text-text-muted shrink-0">
                    VDR {att.vdr_index}
                  </span>
                )}
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
