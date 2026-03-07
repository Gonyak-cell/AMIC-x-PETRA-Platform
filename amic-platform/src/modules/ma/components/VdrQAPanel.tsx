/**
 * VDR Q&A 패널 — Deal Room AI Assistant 채팅 UI.
 *
 * Gemini File API 기반으로 VDR 문서에 대한 자연어 질문/답변 인터페이스.
 */
import { useState, useRef, useEffect, useCallback } from "react";
import { Button, Card } from "@/components/ui";
import { MessageSquare, Send, Trash2, FileText, Loader2 } from "lucide-react";
import { useVdrQA } from "@/modules/ma/hooks/useVdrQA";
import type { VdrQAMessage, VdrQASource } from "@/modules/ma/types/vdr";
import { PanelHeader, PanelEmptyState } from "./PanelShared";

interface VdrQAPanelProps {
  txnId: string;
}

// ── 메시지 버블 ──

function MessageBubble({ message }: { message: VdrQAMessage }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`}>
      <div
        className={`max-w-[85%] rounded-lg px-4 py-2.5 text-sm leading-relaxed ${
          isUser
            ? "bg-accent text-white rounded-br-sm"
            : "bg-surface-secondary text-text-dark rounded-bl-sm"
        }`}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>

        {/* 참조 문서 */}
        {message.sources && message.sources.length > 0 && (
          <SourceList sources={message.sources} />
        )}

        <span
          className={`block text-[10px] mt-1.5 ${
            isUser ? "text-white/60" : "text-text-muted"
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

// ── 로딩 인디케이터 ──

function TypingIndicator() {
  return (
    <div className="flex justify-start mb-3">
      <div className="bg-surface-secondary rounded-lg px-4 py-3 rounded-bl-sm">
        <div className="flex items-center gap-1.5">
          <Loader2 className="h-3.5 w-3.5 animate-spin text-text-muted" />
          <span className="text-xs text-text-muted">답변 생성 중...</span>
        </div>
      </div>
    </div>
  );
}

// ── 메인 패널 ──

export default function VdrQAPanel({ txnId }: VdrQAPanelProps) {
  const { messages, ask, isLoading, clearHistory } = useVdrQA(txnId);
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // 메시지 추가 시 스크롤 하단으로
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  const handleSend = useCallback(() => {
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;
    ask(trimmed);
    setInput("");
    inputRef.current?.focus();
  }, [input, isLoading, ask]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

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
              disabled={isLoading}
            >
              <Trash2 className="h-3.5 w-3.5 mr-1" />
              초기화
            </Button>
          ) : undefined
        }
      />

      {/* 메시지 영역 */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-1 min-h-0">
        {messages.length === 0 && !isLoading ? (
          <PanelEmptyState
            icon={MessageSquare}
            title="VDR 문서에 대해 질문해 보세요"
            description="업로드된 문서를 기반으로 AI가 답변합니다. 예: '대상 기업 매출 추이는?'"
          />
        ) : (
          <>
            {messages.map((msg, idx) => (
              <MessageBubble key={idx} message={msg} />
            ))}
            {isLoading && <TypingIndicator />}
          </>
        )}
      </div>

      {/* 입력 영역 */}
      <div className="border-t border-border pt-3 mt-2">
        <div className="flex items-end gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="질문을 입력하세요... (Shift+Enter: 줄바꿈)"
            rows={1}
            className="flex-1 resize-none rounded-lg border border-border bg-surface px-3 py-2 text-sm placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-accent"
            disabled={isLoading}
          />
          <Button
            variant="primary"
            size="sm"
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </Card>
  );
}
