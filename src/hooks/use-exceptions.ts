// Hooks de bloqueio de agenda (schedule_exceptions) — usados na Agenda e em /dashboard/exceptions.
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { doctorsApi } from "@/lib/api";
import { hasAccessToken, isBrowser } from "@/lib/auth-storage";
import type { ScheduleExceptionCreatePayload } from "@/lib/api-types";

export const exceptionKeys = {
  mine: ["exceptions", "me"] as const,
};

export function useExceptions() {
  return useQuery({
    queryKey: exceptionKeys.mine,
    queryFn: doctorsApi.listExceptions,
    enabled: isBrowser() && hasAccessToken(),
  });
}

export function useCreateException() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ScheduleExceptionCreatePayload) => doctorsApi.createException(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: exceptionKeys.mine });
      // Bloqueio muda a disponibilidade de qualquer data já cacheada.
      queryClient.invalidateQueries({ queryKey: ["availability"] });
    },
  });
}

export function useDeleteException() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (exceptionId: string) => doctorsApi.deleteException(exceptionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: exceptionKeys.mine });
      queryClient.invalidateQueries({ queryKey: ["availability"] });
    },
  });
}
