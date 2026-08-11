// Hooks do perfil do médico logado (/doctors/me) e do perfil público (/doctors/{slug}).
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { doctorsApi } from "@/lib/api";
import { hasAccessToken, isBrowser } from "@/lib/auth-storage";
import type { DoctorUpdatePayload } from "@/lib/api-types";

export const doctorKeys = {
  me: ["doctor", "me"] as const,
  stats: (month?: string) => ["doctor", "stats", month ?? "current"] as const,
  public: (slug: string) => ["doctor", "public", slug] as const,
};

export function useDoctorProfile() {
  return useQuery({
    queryKey: doctorKeys.me,
    queryFn: doctorsApi.getMe,
    enabled: isBrowser() && hasAccessToken(),
  });
}

export function useUpdateDoctorProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: DoctorUpdatePayload) => doctorsApi.updateMe(payload),
    onSuccess: (doctor) => {
      queryClient.setQueryData(doctorKeys.me, doctor);
    },
  });
}

export function useDoctorStats(referenceMonth?: string) {
  return useQuery({
    queryKey: doctorKeys.stats(referenceMonth),
    queryFn: () => doctorsApi.getMyStats(referenceMonth),
    enabled: isBrowser() && hasAccessToken(),
  });
}

export function usePublicDoctor(slug: string) {
  return useQuery({
    queryKey: doctorKeys.public(slug),
    queryFn: () => doctorsApi.getPublic(slug),
    enabled: !!slug,
    retry: false,
  });
}
