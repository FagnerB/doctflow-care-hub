import { createFileRoute, Link } from "@tanstack/react-router";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/EmptyState";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { CalendarCheck, Loader2, MessageCircle, SearchX, Stethoscope } from "lucide-react";
import { maskPhoneForPublic } from "@/lib/phone";
import { toBrasiliaDisplayDate } from "@/lib/timezone";
import { usePublicAppointmentStatus } from "@/hooks/use-appointments";
import type { AppointmentStatus } from "@/lib/api-types";

const ACTIVE_STATUSES: AppointmentStatus[] = ["pending", "confirmed"];

// Página pública de status da consulta — o paciente não precisa de conta,
// o próprio UUID do agendamento funciona como "token" de acesso ao link.
export const Route = createFileRoute("/appointment/$id")({
  head: () => ({
    meta: [{ title: "Minha consulta — DoctFlow" }],
  }),
  component: AppointmentStatusPage,
});

const statusLabels: Record<AppointmentStatus, string> = {
  pending: "Pendente",
  confirmed: "Confirmada",
  completed: "Concluída",
  cancelled_by_patient: "Cancelada",
  cancelled_by_doctor: "Cancelada pelo consultório",
  no_show: "Não compareceu",
};

const statusColor: Record<AppointmentStatus, string> = {
  pending: "bg-warning text-warning-foreground",
  confirmed: "bg-primary text-primary-foreground",
  completed: "bg-success text-success-foreground",
  cancelled_by_patient: "bg-destructive text-destructive-foreground",
  cancelled_by_doctor: "bg-destructive text-destructive-foreground",
  no_show: "bg-muted text-muted-foreground",
};

function AppointmentStatusPage() {
  const { id } = Route.useParams();
  const statusQuery = usePublicAppointmentStatus(id);

  return (
    <div className="min-h-screen bg-secondary flex flex-col">
      <header className="px-4 py-4">
        <Link to="/" className="inline-flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-primary grid place-items-center">
            <Stethoscope className="h-5 w-5 text-primary-foreground" />
          </div>
          <span className="font-bold text-lg text-foreground">DoctFlow</span>
        </Link>
      </header>

      <main className="flex-1 flex items-center justify-center px-4 pb-8">
        <div className="w-full max-w-sm bg-background border border-border rounded-2xl p-6 shadow-sm">
          {statusQuery.isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
            </div>
          ) : statusQuery.isError || !statusQuery.data ? (
            <EmptyState icon={SearchX} title="Consulta não encontrada" description="Verifique se o link está correto." />
          ) : (
            <>
              <div className="text-center">
                <div className="mx-auto h-14 w-14 rounded-full bg-primary/10 grid place-items-center mb-3">
                  <CalendarCheck className="h-7 w-7 text-primary" />
                </div>
                <h1 className="text-xl font-bold text-foreground">Consulta com {statusQuery.data.doctor_full_name}</h1>
                <Badge className={`${statusColor[statusQuery.data.status]} mt-2`}>
                  {statusLabels[statusQuery.data.status]}
                </Badge>
              </div>

              <div className="mt-6 space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Paciente</span>
                  <span className="text-foreground font-medium">{statusQuery.data.patient_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Telefone</span>
                  <span className="text-foreground font-medium">{maskPhoneForPublic(statusQuery.data.patient_phone)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Data</span>
                  <span className="text-foreground font-medium">
                    {format(toBrasiliaDisplayDate(statusQuery.data.scheduled_at), "dd 'de' MMMM 'de' yyyy", {
                      locale: ptBR,
                    })}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Horário</span>
                  <span className="text-foreground font-medium">
                    {format(toBrasiliaDisplayDate(statusQuery.data.scheduled_at), "HH:mm")}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Duração</span>
                  <span className="text-foreground font-medium">{statusQuery.data.duration_minutes} min</span>
                </div>
              </div>

              {/* Sem endpoint público de cancelamento por id no backend — o único
                  caminho real é responder CANCELAR no WhatsApp. Só faz sentido
                  mostrar esse aviso enquanto a consulta ainda está ativa. */}
              {ACTIVE_STATUSES.includes(statusQuery.data.status) && (
                <div className="mt-6 flex items-start gap-2 rounded-lg bg-secondary p-3 text-sm text-foreground">
                  <MessageCircle className="h-5 w-5 text-primary shrink-0 mt-0.5" />
                  <span className="text-left">
                    Para cancelar, responda <strong>CANCELAR</strong> na conversa do WhatsApp que você recebeu.
                  </span>
                </div>
              )}

              <Link to="/" className="mt-6 block">
                <Button variant="outline" className="w-full">Voltar ao início</Button>
              </Link>
            </>
          )}
        </div>
      </main>
    </div>
  );
}
