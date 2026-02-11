import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useMemo } from "react";
import { toast } from "sonner";
import api from "@/api/client";
import type { AdminUser } from "@/types/admin";
import type { TeamMember, TeamAssignmentData } from "@/types/collaboration";

export function useTeamMembers() {
  const { data: users = [], isLoading } = useQuery<AdminUser[]>({
    queryKey: ["admin", "users"],
    queryFn: async () => {
      try {
        const { data } = await api.get<AdminUser[]>("/auth/users");
        return data;
      } catch {
        return [];
      }
    },
    staleTime: 60_000,
  });

  const members: TeamMember[] = useMemo(
    () =>
      users
        .filter((u) => u.is_active)
        .map((u) => ({
          user_id: u.id,
          display_name: u.display_name,
          role: u.role,
          email: u.email,
        })),
    [users],
  );

  const partners = useMemo(
    () => members.filter((m) => m.role === "ADMIN" || m.role === "MANAGER"),
    [members],
  );

  const managers = useMemo(
    () => members.filter((m) => m.role === "MANAGER" || m.role === "ADMIN"),
    [members],
  );

  const analysts = useMemo(
    () => members.filter((m) => m.role === "ANALYST"),
    [members],
  );

  return { members, partners, managers, analysts, isLoading };
}

export function useUpdateTeamAssignment(dealId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (assignment: Partial<TeamAssignmentData>) => {
      const { data } = await api.put(`/deals/${dealId}`, {
        team_partner_id: assignment.partner_id,
        team_manager_id: assignment.manager_id,
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["deals"] });
      queryClient.invalidateQueries({ queryKey: ["deal", dealId] });
      toast.success("Team assignment updated");
    },
    onError: () => {
      toast.error("Failed to update team assignment");
    },
  });
}
