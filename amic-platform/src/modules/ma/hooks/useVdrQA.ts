import { useCallback, useRef, useState } from "react";
import { toast } from "sonner";

import { maApi } from "@/api/maClient";
import { refreshAuth } from "@/api/client";
import { emitForceLogout } from "@/lib/auth-events";
import type {
  VdrQAErrorEvent,
  VdrQAMessage,
  VdrQASource,
  VdrQASourcesEvent,
  VdrQATokenEvent,
} from "@/modules/ma/types/vdr";

/** JSON.parse 래퍼 — malformed SSE 데이터에 대한 런타임 크래시 방지 */
function safeParse<T>(raw: string): T | null {
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

/**
 * SSE 텍스트 스트림에서 이벤트를 파싱한다.
 * text/event-stream 형식: "event: xxx\ndata: {...}\n\n"
 */
function parseSSEEvents(text: string): { event: string; data: string }[] {
  const events: { event: string; data: string }[] = [];
  const blocks = text.split("\n\n");

  for (const block of blocks) {
    if (!block.trim()) continue;

    let event = "";
    const dataLines: string[] = [];
    for (const line of block.split("\n")) {
      if (line.startsWith("event: ")) event = line.slice(7);
      else if (line.startsWith("data: ")) dataLines.push(line.slice(6));
    }
    const data = dataLines.join("\n");
    if (event && data) events.push({ event, data });
  }

  return events;
}

/**
 * VDR Q&A 훅 — SSE 스트리밍 기반 Deal Room AI Assistant.
 *
 * 사용법:
 *   const { messages, ask, isStreaming, clearHistory } = useVdrQA(txnId);
 *   ask("대상 기업 매출 추이는?");
 */
export function useVdrQA(txnId: string) {
  const [messages, setMessages] = useState<VdrQAMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const conversationIdRef = useRef<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const isStreamingRef = useRef(false);
  const abortRef = useRef<AbortController | null>(null);

  const ask = useCallback(
    async (question: string, documentIds?: string[]) => {
      if (isStreamingRef.current) return;

      // 사용자 메시지 추가
      setMessages((prev) => [
        ...prev,
        {
          role: "user",
          content: question,
          timestamp: new Date().toISOString(),
        },
      ]);

      // 빈 assistant 메시지 추가 (스트리밍 대상)
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "", timestamp: new Date().toISOString() },
      ]);

      setIsStreaming(true);
      isStreamingRef.current = true;
      const controller = new AbortController();
      abortRef.current = controller;

      // rAF 기반 토큰 배칭 — 프레임당 1회 업데이트로 리렌더 최소화
      const pendingTokens: string[] = [];
      let rafId: number | null = null;

      function flushTokens() {
        if (pendingTokens.length === 0) return;
        const text = pendingTokens.join("");
        pendingTokens.length = 0;
        rafId = null;
        setMessages((prev) => {
          const lastIdx = prev.length - 1;
          const last = prev[lastIdx];
          if (last?.role === "assistant") {
            const updated = prev.slice();
            updated[lastIdx] = { ...last, content: last.content + text };
            return updated;
          }
          return prev;
        });
      }

      let receivedDone = false;

      try {
        const body = JSON.stringify({
          question,
          document_ids: documentIds,
          conversation_id: conversationIdRef.current ?? undefined,
        });

        const baseURL = maApi.defaults.baseURL ?? "/api/ma";
        const fetchHeaders: Record<string, string> = {
          "Content-Type": "application/json",
        };
        const authHeader =
          maApi.defaults.headers.common?.["Authorization"] ??
          maApi.defaults.headers?.["Authorization"];
        if (typeof authHeader === "string") {
          fetchHeaders["Authorization"] = authHeader;
        }

        const sseUrl = `${baseURL}/transactions/${txnId}/vdr/qa/stream`;
        const fetchOpts: RequestInit = {
          method: "POST",
          headers: fetchHeaders,
          credentials: "include",
          body,
          signal: controller.signal,
        };

        let response = await fetch(sseUrl, fetchOpts);

        // 401 → 토큰 갱신 후 1회 재시도
        if (response.status === 401) {
          const refreshed = await refreshAuth();
          if (refreshed) {
            // refreshAuth 대기 중 abort된 경우 불필요한 재시도 방지
            if (controller.signal.aborted) return;
            // 재시도 시 Authorization 헤더 갱신 (쿠키 기반이므로 헤더는 보조적)
            const freshAuthHeader =
              maApi.defaults.headers.common?.["Authorization"] ??
              maApi.defaults.headers?.["Authorization"];
            if (typeof freshAuthHeader === "string") {
              fetchHeaders["Authorization"] = freshAuthHeader;
            }
            response = await fetch(sseUrl, {
              ...fetchOpts,
              headers: fetchHeaders,
            });
          } else {
            emitForceLogout();
            throw new Error("인증이 만료되었습니다. 다시 로그인해 주세요.");
          }
        }

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const reader = response.body?.getReader();
        if (!reader) throw new Error("ReadableStream 미지원");

        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // 완전한 블록만 파싱 — 불완전한 마지막 블록 보존
          const lastDoubleNewline = buffer.lastIndexOf("\n\n");
          if (lastDoubleNewline === -1) continue;

          const completePart = buffer.slice(0, lastDoubleNewline + 2);
          buffer = buffer.slice(lastDoubleNewline + 2);
          const events = parseSSEEvents(completePart);

          for (const { event, data } of events) {
            if (event === "token") {
              const parsed = safeParse<VdrQATokenEvent>(data);
              if (!parsed) continue;
              pendingTokens.push(parsed.text);
              if (rafId === null) {
                rafId = requestAnimationFrame(flushTokens);
              }
            } else if (event === "sources") {
              // 남은 토큰 즉시 플러시
              if (rafId !== null) cancelAnimationFrame(rafId);
              flushTokens();

              const parsed = safeParse<VdrQASourcesEvent>(data);
              if (!parsed) continue;
              setConversationId(parsed.conversation_id);
              conversationIdRef.current = parsed.conversation_id;
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last?.role === "assistant") {
                  updated[updated.length - 1] = {
                    ...last,
                    // final_content가 있으면 sanitized 텍스트로 교체
                    ...(parsed.final_content != null
                      ? { content: parsed.final_content }
                      : {}),
                    sources: parsed.sources as VdrQASource[],
                  };
                }
                return updated;
              });
            } else if (event === "error") {
              const parsed = safeParse<VdrQAErrorEvent>(data);
              if (!parsed) continue;
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last?.role === "assistant") {
                  updated[updated.length - 1] = {
                    ...last,
                    content: parsed.message,
                    isError: true,
                  };
                }
                return updated;
              });
            } else if (event === "info") {
              // 정보성 안내 (인사 등) — 에러가 아니므로 회색 스타일 적용
              const parsed = safeParse<VdrQAErrorEvent>(data);
              if (!parsed) continue;
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last?.role === "assistant") {
                  updated[updated.length - 1] = {
                    ...last,
                    content: parsed.message,
                  };
                }
                return updated;
              });
            } else if (event === "done") {
              receivedDone = true;
            }
          }
        }

        // 스트림 종료 후 잔여 토큰 플러시
        if (rafId !== null) cancelAnimationFrame(rafId);
        flushTokens();

        // done 이벤트 없이 스트림이 끊긴 경우 — 부분 응답 표시
        if (!receivedDone) {
          toast.error("Q&A 오류", {
            description: "응답이 완료되지 않았습니다. 다시 시도해 주세요.",
          });
          setMessages((prev) => {
            const lastIdx = prev.length - 1;
            const last = prev[lastIdx];
            if (last?.role === "assistant" && last.content) {
              const updated = prev.slice();
              updated[lastIdx] = { ...last, isIncomplete: true };
              return updated;
            }
            return prev;
          });
        }
      } catch (err) {
        if (rafId !== null) cancelAnimationFrame(rafId);
        flushTokens(); // 에러 시에도 수신된 부분 토큰 UI 반영
        if ((err as Error).name === "AbortError") {
          // 빈 assistant 메시지 정리
          setMessages((prev) => {
            const last = prev[prev.length - 1];
            if (last?.role === "assistant" && !last.content) {
              return prev.slice(0, -1);
            }
            return prev;
          });
          return;
        }

        toast.error("Q&A 오류", {
          description: (err as Error).message || "답변 생성에 실패했습니다.",
        });
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last?.role === "assistant" && !last.content) {
            updated[updated.length - 1] = {
              ...last,
              content:
                "답변 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
              isError: true,
            };
          }
          return updated;
        });
      } finally {
        setIsStreaming(false);
        isStreamingRef.current = false;
        abortRef.current = null;
      }
    },
    [txnId],
  );

  const cancelStream = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const clearHistory = useCallback(() => {
    cancelStream();
    setMessages([]);
    setConversationId(null);
    conversationIdRef.current = null;
  }, [cancelStream]);

  return {
    messages,
    ask,
    isStreaming,
    clearHistory,
    cancelStream,
    conversationId,
  };
}
