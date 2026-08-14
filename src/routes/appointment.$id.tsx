import { createFileRoute, Link } from "@tanstack/react-router";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/EmptyState";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { CalendarCheck, CircleX, Loader2, SearchX, Stethoscope } from "lucide-react";
import { getErrorMessage } from "@/lib/api-client";
import { maskPhoneForPublic } from "@/lib/phone";
import { toBrasiliaDisplayDate } from "@/lib/timezone";
import { useCancelPublicAppointment, usePublicAppointmentStatus } from "@/hooks/use-appointments";
import type { AppointmentStatus } from "@/lib/api-types";
import { toast } from "sonner";

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
  const cancelMutation = useCancelPublicAppointment();

  const handleCancel = () => {
    if (!id) return;
    cancelMutation.mutate(id, {
      onError: (error) => toast.error(getErrorMessage(error)),
    });
  };

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

              {ACTIVE_STATUSES.includes(statusQuery.data.status) && (
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button
                      variant="outline"
                      className="mt-6 w-full text-destructive hover:text-destructive"
                      disabled={cancelMutation.isPending}
                    >
                      {cancelMutation.isPending ? (
                        <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
                      ) : (
                        <CircleX className="h-4 w-4 mr-1.5" />
                      )}
                      Cancelar consulta
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>Cancelar esta consulta?</AlertDialogTitle>
                      <AlertDialogDescription>
                        O horário fica livre para outro paciente. Essa ação não pode ser desfeita — pra remarcar,
                        você vai precisar agendar de novo.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>Voltar</AlertDialogCancel>
                      <AlertDialogAction onClick={handleCancel}>Cancelar consulta</AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              )}

              <Link to="/" className="mt-3 block">
                <Button variant="ghost" className="w-full">Voltar ao início</Button>
              </Link>
            </>
          )}
        </div>
      </main>
    </div>
  );
}
