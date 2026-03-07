import { useMutation } from "@tanstack/react-query";
import { useCallback, useState } from "react";
import { toast } from "sonner";

import { maApi } from "@/api/maClient";
import type {
  VdrQAMessage,
  VdrQARequest,
  VdrQAResponse,
} from "@/modules/ma/types/vdr";

/**
 * VDR Q&A 훅 — Gemini File API 기반 Deal Room AI Assistant.
 *
 * 사용법:
 *   const { messages, ask, isLoading, clearHistory } = useVdrQA(txnId);
 *   ask("대상 기업 매출 추이는?");
 */
export function useVdrQA(txnId: string) {
  const [messages, setMessages] = useState<VdrQAMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);

  const mutation = useMutation<VdrQAResponse, Error, VdrQARequest>({
    mutationFn: async (req) => {
      const { data } = await maApi.post<VdrQAResponse>(
        `/transactions/${txnId}/vdr/qa`,
        req,
      );
      return data;
    },
    onSuccess: (data) => {
      setConversationId(data.conversation_id);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.answer,
          sources: data.sources,
          timestamp: new Date().toISOString(),
        },
      ]);
    },
    onError: (err) => {
      toast.error("Q&A 오류", {
        description: err.message || "답변 생성에 실패했습니다.",
      });
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "답변 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
          timestamp: new Date().toISOString(),
        },
      ]);
    },
  });

  const ask = useCallback(
    (question: string, documentIds?: string[]) => {
      // 사용자 메시지 추가
      setMessages((prev) => [
        ...prev,
        {
          role: "user",
          content: question,
          timestamp: new Date().toISOString(),
        },
      ]);

      // API 호출
      mutation.mutate({
        question,
        document_ids: documentIds,
        conversation_id: conversationId ?? undefined,
      });
    },
    [conversationId, mutation],
  );

  const clearHistory = useCallback(() => {
    setMessages([]);
    setConversationId(null);
  }, []);

  return {
    messages,
    ask,
    isLoading: mutation.isPending,
    clearHistory,
    conversationId,
  };
}
