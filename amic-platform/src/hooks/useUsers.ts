import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import api from "@/api/client";
import { extractApiError } from "@/api/errors";
import type { AdminUser, UserCreate, UserUpdate } from "@/types/admin";

export function useUsers() {
  return useQuery<AdminUser[]>({
    queryKey: ["admin", "users"],
    queryFn: async () => {
      const { data } = await api.get("/auth/users");
      return data;
    },
  });
}

export function useCreateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: UserCreate) => {
      const { data } = await api.post("/auth/users", body);
      return data as AdminUser;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      toast.success("User created successfully");
    },
    onError: (err) => {
      toast.error(extractApiError(err, "Failed to create user"));
    },
  });
}

export function useUpdateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      userId,
      body,
    }: {
      userId: string;
      body: UserUpdate;
    }) => {
      const { data } = await api.put(`/auth/users/${userId}`, body);
      return data as AdminUser;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      toast.success("User updated successfully");
    },
    onError: (err) => {
      toast.error(extractApiError(err, "Failed to update user"));
    },
  });
}

export function useDeleteUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (userId: string) => {
      await api.delete(`/auth/users/${userId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      toast.success("User deleted successfully");
    },
    onError: (err) => {
      toast.error(extractApiError(err, "Failed to delete user"));
    },
  });
}

export function useDeactivateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (userId: string) => {
      const { data } = await api.put(`/auth/users/${userId}`, {
        is_active: false,
      });
      return data as AdminUser;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      toast.success("User deactivated");
    },
    onError: (err) => {
      toast.error(extractApiError(err, "Failed to deactivate user"));
    },
  });
}
