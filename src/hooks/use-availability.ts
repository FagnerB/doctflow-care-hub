// Slots disponíveis de um médico numa data — usado na página pública /d/:slug.
import { useQuery } from "@tanstack/react-query";
import { doctorsApi } from "@/lib/api";

export function useAvailability(slug: string, dateStr: string) {
  return useQuery({
    queryKey: ["availability", slug, dateStr],
    queryFn: () => doctorsApi.getAvailability(slug, dateStr),
    enabled: !!slug && !!dateStr,
  });
}
