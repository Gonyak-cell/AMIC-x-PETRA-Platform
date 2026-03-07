/**
 * VDR Q&A 패널 — Deal Room AI Assistant 채팅 UI.
 *
 * SSE 스트리밍 + 문서 선택적 참조 지원.
 */
import { useState, useRef, useEffect, useCallback } from "react";
import { Button, Card } from "@/components/ui";
import { MessageSquare, Send, Trash2, FileText, Paperclip, X } from "lucide-react";
import { useVdrQA } from "@/modules/ma/hooks/useVdrQA";
import type { VdrQAMessage, VdrQASource } from "@/modules/ma/types/vdr";
import { PanelHeader, PanelEmptyState } from "./PanelShared";
import VdrDocumentSelector from "./VdrDocumentSelector";

interface VdrQAPanelProps {
  txnId: string;
}

// ── 메시지 버블 ──

function MessageBubble({ message, isStreaming }: { message: VdrQAMessage; isStreaming?: boolean }) {
  const isUser = message.role === "user";
  const isError = message.isError;

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`}>
      <div
        className={`max-w-[85%] rounded-lg px-4 py-2.5 text-sm leading-relaxed ${
          isUser
            ? "bg-accent text-white rounded-br-sm"
            : isError
              ? "bg-red-50 text-red-700 border border-red-200 rounded-bl-sm"
              : "bg-surface-secondary text-text-dark rounded-bl-sm"
        }`}
        {...(isError ? { role: "alert" } : {})}
      >
        <p className="whitespace-pre-wrap">
          {message.content}
          {isStreaming && !isUser && (
            <span className="inline-block w-1.5 h-4 bg-accent/70 ml-0.5 animate-pulse" aria-hidden="true" />
          )}
        </p>

        {/* 참조 문서 */}
        {message.sources && message.sources.length > 0 && (
          <SourceList sources={message.sources} />
        )}

        <span
          className={`block text-[10px] mt-1.5 ${
            isUser ? "text-white/60" : isError ? "text-red-400" : "text-text-muted"
          }`}
        >
          {new Date(message.timestamp).toLocaleTimeString("ko-KR", {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </span>
      </div>
    </div>
  );
}

// ── 참조 문서 목록 ──

function SourceList({ sources }: { sources: VdrQASource[] }) {
  return (
    <div className="mt-2 pt-2 border-t border-black/10">
      <p className="text-[10px] font-medium text-text-muted mb-1">참조 문서</p>
      <div className="flex flex-wrap gap-1">
        {sources.map((s) => (
          <span
            key={s.document_id}
            className="inline-flex items-center gap-1 text-[10px] bg-black/5 rounded px-1.5 py-0.5"
          >
            <FileText className="h-2.5 w-2.5" />
            {s.document_name}
          </span>
        ))}
      </div>
    </div>
  );
}

// ── 메인 패널 ──

export default function VdrQAPanel({ txnId }: VdrQAPanelProps) {
  const { messages, ask, isStreaming, clearHistory } = useVdrQA(txnId);
  const [input, setInput] = useState("");
  const [showDocSelector, setShowDocSelector] = useState(false);
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const userScrolledUpRef = useRef(false);

  // 사용자 스크롤 위치 감지 — 하단에서 벗어나면 자동 스크롤 중단
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;

    const handleScroll = () => {
      const threshold = 40;
      const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < threshold;
      userScrolledUpRef.current = !atBottom;
    };

    el.addEventListener("scroll", handleScroll, { passive: true });
    return () => el.removeEventListener("scroll", handleScroll);
  }, []);

  // 메시지 추가/스트리밍 시 스크롤 하단으로 (사용자가 위로 스크롤한 경우 제외)
  useEffect(() => {
    if (scrollRef.current && !userScrolledUpRef.current) {
      requestAnimationFrame(() => {
        if (scrollRef.current) {
          scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
      });
    }
  }, [messages, isStreaming]);

  const handleSend = useCallback(() => {
    const trimmed = input.trim();
    if (!trimmed || isStreaming) return;
    const docIds = selectedDocIds.length > 0 ? selectedDocIds : undefined;
    ask(trimmed, docIds);
    setInput("");
    userScrolledUpRef.current = false;
    inputRef.current?.focus();
  }, [input, isStreaming, ask, selectedDocIds]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  const selectedLabel =
    selectedDocIds.length === 0
      ? null
      : `${selectedDocIds.length}개 문서 선택됨`;

  return (
    <Card className="flex flex-col h-full">
      {/* 헤더 */}
      <PanelHeader
        title="Deal Room AI Assistant"
        count={messages.length}
        actions={
          messages.length > 0 ? (
            <Button
              variant="ghost"
              size="sm"
              onClick={clearHistory}
              disabled={isStreaming}
            >
              <Trash2 className="h-3.5 w-3.5 mr-1" />
              초기화
            </Button>
          ) : undefined
        }
      />

      {/* 메시지 영역 */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-1 min-h-0" aria-live="polite" aria-label="채팅 메시지">
        {messages.length === 0 && !isStreaming ? (
          <PanelEmptyState
            icon={MessageSquare}
            title="VDR 문서에 대해 질문해 보세요"
            description="업로드된 문서를 기반으로 AI가 답변합니다. 예: '대상 기업 매출 추이는?'"
          />
        ) : (
          <>
            {messages.map((msg, idx) => (
              <MessageBubble
                key={`${msg.role}-${msg.timestamp}-${idx}`}
                message={msg}
                isStreaming={isStreaming && idx === messages.length - 1 && msg.role === "assistant"}
              />
            ))}
          </>
        )}
      </div>

      {/* 문서 선택기 */}
      {showDocSelector && (
        <div className="border-t border-border px-3 py-2">
          <VdrDocumentSelector
            txnId={txnId}
            selectedDocumentIds={selectedDocIds}
            onSelectionChange={setSelectedDocIds}
          />
        </div>
      )}

      {/* 선택 요약 칩 */}
      {selectedLabel && (
        <div className="px-3 pb-1">
          <span className="inline-flex items-center gap-1 text-[10px] bg-accent/10 text-accent rounded-full px-2 py-0.5">
            <Paperclip className="h-2.5 w-2.5" />
            {selectedLabel}
            <button
              type="button"
              onClick={() => setSelectedDocIds([])}
              className="ml-0.5 hover:text-accent/70"
              aria-label="문서 선택 해제"
            >
              <X className="h-2.5 w-2.5" />
            </button>
          </span>
        </div>
      )}

      {/* 입력 영역 */}
      <div className="border-t border-border pt-3 mt-2">
        <div className="flex items-end gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowDocSelector((v) => !v)}
            className={showDocSelector ? "text-accent" : "text-text-muted"}
            aria-label="참조 문서 선택"
          >
            <Paperclip className="h-4 w-4" />
          </Button>
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            aria-label="질문 입력"
            placeholder="질문을 입력하세요... (Shift+Enter: 줄바꿈)"
            rows={1}
            className="flex-1 resize-none rounded-lg border border-border bg-surface px-3 py-2 text-sm placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-accent"
            disabled={isStreaming}
          />
          <Button
            variant="primary"
            size="sm"
            onClick={handleSend}
            disabled={!input.trim() || isStreaming}
            aria-label="질문 전송"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </Card>
  );
}
