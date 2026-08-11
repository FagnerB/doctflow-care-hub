// Hooks de consultas: agenda do médico logado e fluxo público (criar / ver status).
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { doctorsApi, appointmentsApi } from "@/lib/api";
import { hasAccessToken, isBrowser } from "@/lib/auth-storage";
import type { AppointmentCreatePayload, AppointmentStatus } from "@/lib/api-types";
import { doctorKeys } from "./use-doctor";

export const appointmentKeys = {
  mine: ["appointments", "me"] as const,
  publicStatus: (id: string) => ["appointments", "public", id] as const,
};

/**
 * Agenda completa do médico logado. Sem filtros de data — no volume de um
 * MVP (um profissional solo) buscar tudo de uma vez e filtrar no cliente é
 * mais simples e evita refetch a cada troca de mês no calendário.
 *
 * `refetchInterval` opcional liga o polling usado para o badge de "nova consulta".
 */
export function useDoctorAppointments(options?: { refetchInterval?: number }) {
  return useQuery({
    queryKey: appointmentKeys.mine,
    queryFn: () => doctorsApi.getMyAppointments(),
    enabled: isBrowser() && hasAccessToken(),
    refetchInterval: options?.refetchInterval,
  });
}

export function useUpdateAppointmentStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status, notes }: { id: string; status: AppointmentStatus; notes?: string }) =>
      doctorsApi.updateAppointmentStatus(id, status, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: appointmentKeys.mine });
      queryClient.invalidateQueries({ queryKey: doctorKeys.stats() });
    },
  });
}

export function useCreatePublicAppointment() {
  return useMutation({
    mutationFn: (payload: AppointmentCreatePayload) => appointmentsApi.create(payload),
  });
}

export function usePublicAppointmentStatus(appointmentId: string | undefined) {
  return useQuery({
    queryKey: appointmentKeys.publicStatus(appointmentId ?? ""),
    queryFn: () => appointmentsApi.getPublicStatus(appointmentId as string),
    enabled: !!appointmentId,
    retry: false,
  });
}
