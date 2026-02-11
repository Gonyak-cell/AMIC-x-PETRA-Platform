import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import api from "@/api/client";
import type { AuthUser } from "@/types/auth";
import type { PasswordChangeRequest } from "@/types/settings";

export function useUpdateProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      userId,
      displayName,
    }: {
      userId: string;
      displayName: string;
    }) => {
      const { data } = await api.put(`/auth/users/${userId}`, {
        display_name: displayName,
      });
      return data as AuthUser;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      toast.success("Profile updated successfully");
    },
    onError: () => {
      toast.error("Failed to update profile");
    },
  });
}

export function useChangePassword() {
  return useMutation({
    mutationFn: async (body: PasswordChangeRequest) => {
      const { data } = await api.post("/auth/change-password", {
        current_password: body.current_password,
        new_password: body.new_password,
      });
      return data;
    },
    onSuccess: () => {
      toast.success("Password changed successfully");
    },
    onError: () => {
      toast.error("Failed to change password. Please check your current password.");
    },
  });
}
