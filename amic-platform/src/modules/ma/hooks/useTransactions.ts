import { useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { maApi } from "@/api/maClient";
import { PHASE_CONFIG } from "@/modules/ma/constants";
import type {
  Transaction,
  TransactionCreate,
  TransactionUpdate,
  TransactionListParams,
  TransactionListResponse,
} from "@/modules/ma/types/transaction";
import type { PhaseCompletionStatus } from "@/modules/ma/types/workflow";
import type { DashboardStats } from "@/modules/ma/types/dashboard";
import type {
  Engagement,
  EngagementCreate,
  WorkingGroupMember,
  WorkingGroupMemberCreate,
} from "@/modules/ma/types/engagement";
import type {
  BuyerCandidate,
  BuyerCandidateCreate,
  BuyerCandidateUpdate,
  BuyerPipelineSummary,
} from "@/modules/ma/types/buyer";
import type {
  TimelineResponse,
  MilestoneCreate,
  GanttResponse,
} from "@/modules/ma/types/timeline";

// ── Transaction CRUD ───────────────────────────────────
export function useTransactions(params?: TransactionListParams) {
  return useQuery<TransactionListResponse>({
    queryKey: ["ma", "transactions", params],
    queryFn: async () => {
      const { data } = await maApi.get("/transactions", { params });
      return data;
    },
    staleTime: 30_000,
  });
}

export function useTransaction(txnId: string) {
  return useQuery<Transaction>({
    queryKey: ["ma", "transactions", txnId],
    queryFn: async () => {
      const { data } = await maApi.get(`/transactions/${txnId}`);
      return data;
    },
    enabled: !!txnId,
  });
}

export function useCreateTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: TransactionCreate) => {
      const { data } = await maApi.post("/transactions", body);
      return data as Transaction;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ma", "transactions"] });
      toast.success("거래가 성공적으로 생성되었습니다.");
    },
    onError: () => {
      toast.error("거래 생성 중 오류가 발생했습니다.");
    },
  });
}

export function useUpdateTransaction(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: TransactionUpdate) => {
      const { data } = await maApi.patch(`/transactions/${txnId}`, body);
      return data as Transaction;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ma", "transactions"] });
      qc.invalidateQueries({ queryKey: ["ma", "transactions", txnId] });
      toast.success("거래가 수정되었습니다.");
    },
    onError: () => {
      toast.error("거래 수정 중 오류가 발생했습니다.");
    },
  });
}

export function useDeleteTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (txnId: string) => {
      await maApi.delete(`/transactions/${txnId}`);
    },
    onMutate: async (txnId) => {
      // 삭제 시작 시 관련 쿼리 즉시 취소 → refetch 방지
      await qc.cancelQueries({ queryKey: ["ma", "transactions", txnId] });
    },
    onSuccess: (_data, txnId) => {
      // removeQueries 의도적 미호출: 컴포넌트 마운트 상태에서
      // removeQueries → observer 재생성 → refetch → 404 유발
      // navigate 후 unmount 시 React Query GC가 자동 정리

      // 삭제된 거래의 하위 쿼리를 제외하고 목록/대시보드만 갱신
      qc.invalidateQueries({
        predicate: (query) => {
          const k = query.queryKey;
          if (k[0] !== "ma") return false;
          if (k[1] === "dashboard") return true;
          if (k[1] === "transactions") return k[2] !== txnId;
          return false;
        },
      });
      toast.success("거래가 삭제되었습니다.");
    },
    onError: (_err, txnId) => {
      // 실패 시 취소된 쿼리 다시 활성화
      qc.invalidateQueries({ queryKey: ["ma", "transactions", txnId] });
      toast.error("거래 삭제 중 오류가 발생했습니다.");
    },
  });
}

// ── Workflow ────────────────────────────────────────────
export function usePhaseCompletion(txnId: string) {
  return useQuery<PhaseCompletionStatus>({
    queryKey: ["ma", "transactions", txnId, "phase-status"],
    queryFn: async () => {
      const { data } = await maApi.get(
        `/transactions/${txnId}/workflow/phase-status`,
      );
      return data;
    },
    enabled: !!txnId,
  });
}

export function useAdvancePhase(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { to_phase: string; notes?: string }) => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/workflow/advance`,
        body,
      );
      return data as Transaction;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ma", "transactions", txnId] });
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "phase-status"],
      });
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "timeline"],
      });
      toast.success("단계가 전환되었습니다.");
    },
    onError: (err: Error) => {
      toast.error(err.message || "단계 전환에 실패했습니다.");
    },
  });
}

export function useAutoAdvanceNotification(txnId: string) {
  const prevCanAdvance = useRef<boolean | null>(null);
  const { data: phaseStatus } = usePhaseCompletion(txnId);
  const advancePhase = useAdvancePhase(txnId);
  const advanceRef = useRef(advancePhase);
  advanceRef.current = advancePhase;

  useEffect(() => {
    if (!phaseStatus) return;

    // 초기 로드 시에는 알림하지 않음 (이전 값이 null)
    if (prevCanAdvance.current === null) {
      prevCanAdvance.current = phaseStatus.can_advance;
      return;
    }

    // can_advance가 false → true로 전환된 시점에만 알림
    if (
      phaseStatus.can_advance &&
      !prevCanAdvance.current &&
      phaseStatus.next_phase
    ) {
      const nextLabel =
        PHASE_CONFIG.find((p) => p.phase === phaseStatus.next_phase)?.label ??
        phaseStatus.next_phase;

      toast.success(`모든 조건 충족! ${nextLabel} 단계로 진행할 수 있습니다`, {
        action: {
          label: "진행하기",
          onClick: () =>
            advanceRef.current.mutate({
              to_phase: phaseStatus.next_phase!,
            }),
        },
        duration: 10000,
      });
    }

    prevCanAdvance.current = phaseStatus.can_advance;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phaseStatus?.can_advance, phaseStatus?.next_phase]);
}

export function useChangeStatus(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { to_status: string; reason?: string }) => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/workflow/status`,
        body,
      );
      return data as Transaction;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ma", "transactions", txnId] });
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "timeline"],
      });
      toast.success("상태가 변경되었습니다.");
    },
    onError: (err: Error) => {
      toast.error(err.message || "상태 변경에 실패했습니다.");
    },
  });
}

// ── Engagement ─────────────────────────────────────────
export function useEngagements(txnId: string) {
  return useQuery<Engagement[]>({
    queryKey: ["ma", "transactions", txnId, "engagements"],
    queryFn: async () => {
      const { data } = await maApi.get(`/transactions/${txnId}/engagements`);
      return data;
    },
    enabled: !!txnId,
    staleTime: 60_000,
  });
}

export function useCreateEngagement(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: EngagementCreate) => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/engagements`,
        body,
      );
      return data as Engagement;
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "engagements"],
      });
      toast.success("수임계약이 등록되었습니다.");
    },
    onError: () => {
      toast.error("수임계약 등록에 실패했습니다.");
    },
  });
}

// ── Working Group ──────────────────────────────────────
export function useWorkingGroup(txnId: string) {
  return useQuery<WorkingGroupMember[]>({
    queryKey: ["ma", "transactions", txnId, "members"],
    queryFn: async () => {
      const { data } = await maApi.get(`/transactions/${txnId}/members`);
      return data;
    },
    enabled: !!txnId,
  });
}

export function useAddMember(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: WorkingGroupMemberCreate) => {
      const { data } = await maApi.post(`/transactions/${txnId}/members`, body);
      return data as WorkingGroupMember;
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "members"],
      });
      toast.success("멤버가 추가되었습니다.");
    },
    onError: () => {
      toast.error("멤버 추가에 실패했습니다.");
    },
  });
}

// ── Buyers ─────────────────────────────────────────────
export function useBuyers(txnId: string) {
  return useQuery<BuyerCandidate[]>({
    queryKey: ["ma", "transactions", txnId, "buyers"],
    queryFn: async () => {
      const { data } = await maApi.get(`/transactions/${txnId}/buyers`);
      return data;
    },
    enabled: !!txnId,
    staleTime: 60_000,
  });
}

export function useBuyerSummary(txnId: string, active = true) {
  return useQuery<BuyerPipelineSummary>({
    queryKey: ["ma", "transactions", txnId, "buyers", "summary"],
    queryFn: async () => {
      const { data } = await maApi.get(`/transactions/${txnId}/buyers/summary`);
      return data;
    },
    enabled: !!txnId && active,
    staleTime: 60_000,
  });
}

export function useAddBuyer(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: BuyerCandidateCreate) => {
      const { data } = await maApi.post(`/transactions/${txnId}/buyers`, body);
      return data as BuyerCandidate;
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "buyers"],
      });
      toast.success("매수자 후보가 추가되었습니다.");
    },
    onError: () => {
      toast.error("매수자 추가에 실패했습니다.");
    },
  });
}

export function useUpdateBuyer(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      buyerId,
      body,
    }: {
      buyerId: string;
      body: BuyerCandidateUpdate;
    }) => {
      const { data } = await maApi.patch(
        `/transactions/${txnId}/buyers/${buyerId}`,
        body,
      );
      return data as BuyerCandidate;
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "buyers"],
      });
      toast.success("매수자 정보가 수정되었습니다.");
    },
    onError: () => {
      toast.error("매수자 정보 수정에 실패했습니다.");
    },
  });
}

export function useExportBuyerExcel(txnId: string) {
  return useMutation({
    mutationFn: async () => {
      const { data } = await maApi.get(
        `/transactions/${txnId}/buyers/export-excel`,
        { responseType: "blob" },
      );
      return data as Blob;
    },
    onSuccess: (blob) => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Long-List_${txnId}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("엑셀 파일이 다운로드되었습니다.");
    },
    onError: () => {
      toast.error("엑셀 다운로드에 실패했습니다.");
    },
  });
}

// ── Timeline ───────────────────────────────────────────
export function useTimeline(txnId: string) {
  return useQuery<TimelineResponse>({
    queryKey: ["ma", "transactions", txnId, "timeline"],
    queryFn: async () => {
      const { data } = await maApi.get(`/transactions/${txnId}/timeline`);
      return data;
    },
    enabled: !!txnId,
    staleTime: 60_000,
  });
}

export function useGanttTimeline(txnId: string, active = true) {
  return useQuery<GanttResponse>({
    queryKey: ["ma", "transactions", txnId, "timeline", "gantt"],
    queryFn: async () => {
      const { data } = await maApi.get(`/transactions/${txnId}/timeline/gantt`);
      return data;
    },
    enabled: !!txnId && active,
    staleTime: 60_000,
  });
}

export function useAddTimelineEvent(txnId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: MilestoneCreate) => {
      const { data } = await maApi.post(
        `/transactions/${txnId}/timeline`,
        body,
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "timeline"],
      });
      toast.success("이벤트가 추가되었습니다.");
    },
    onError: () => {
      toast.error("이벤트 추가에 실패했습니다.");
    },
  });
}

// ── Dashboard Stats ────────────────────────────────────
export function useMaStats() {
  return useQuery<DashboardStats>({
    queryKey: ["ma", "dashboard", "stats"],
    queryFn: async () => {
      const { data } = await maApi.get<DashboardStats>("/dashboard/stats");
      return data;
    },
  });
}
