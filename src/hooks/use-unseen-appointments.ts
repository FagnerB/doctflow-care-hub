// Badge de "nova consulta" no nav da Agenda. Sem push/WebSocket no backend,
// a implementação é a mais simples que funciona: comparar a quantidade total
// de consultas com a quantidade que o médico já viu (persistida localmente).
// Consultas nunca são apagadas (só trocam de status), então a contagem total
// só cresce quando chega algo novo — comparar tamanhos é seguro.
import type { Appointment } from "@/lib/api-types";
import { isBrowser } from "@/lib/auth-storage";

const LAST_SEEN_KEY = "doctflow.last_seen_appointments_count";

function getLastSeenCount(): number {
  if (!isBrowser()) return 0;
  const raw = window.localStorage.getItem(LAST_SEEN_KEY);
  const parsed = raw ? Number(raw) : 0;
  return Number.isFinite(parsed) ? parsed : 0;
}

export function markAppointmentsAsSeen(count: number): void {
  if (!isBrowser()) return;
  window.localStorage.setItem(LAST_SEEN_KEY, String(count));
}

export function useUnseenAppointmentsCount(appointments: Appointment[] | undefined): number {
  if (!appointments) return 0;
  return Math.max(0, appointments.length - getLastSeenCount());
}
