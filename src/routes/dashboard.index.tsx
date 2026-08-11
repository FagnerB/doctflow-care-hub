import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { Calendar } from "@/components/ui/calendar";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { format, isSameDay } from "date-fns";
import { ptBR } from "date-fns/locale";
import { CalendarOff, CheckCircle2, Clock, Loader2, XCircle } from "lucide-react";
import { toast } from "sonner";
import { EmptyState } from "@/components/EmptyState";
import { cn } from "@/lib/utils";
import { getErrorMessage } from "@/lib/api-client";
import { toBrasiliaDisplayDate } from "@/lib/timezone";
import { useDoctorAppointments, useUpdateAppointmentStatus } from "@/hooks/use-appointments";
import { useDoctorStats } from "@/hooks/use-doctor";
import { useCreateException, useExceptions } from "@/hooks/use-exceptions";
import { markAppointmentsAsSeen } from "@/hooks/use-unseen-appointments";
import type { Appointment, AppointmentStatus } from "@/lib/api-types";

export const Route = createFileRoute("/dashboard/")({
  component: AgendaPage,
});

const statusLabels: Record<AppointmentStatus, string> = {
  pending: "Pendente",
  confirmed: "Confirmado",
  completed: "Concluído",
  cancelled_by_patient: "Cancelado (paciente)",
  cancelled_by_doctor: "Cancelado (médico)",
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

const CANCELLED: AppointmentStatus[] = ["cancelled_by_patient", "cancelled_by_doctor"];

function AgendaPage() {
  const appointmentsQuery = useDoctorAppointments();
  const statsQuery = useDoctorStats();
  const exceptionsQuery = useExceptions();
  const updateStatus = useUpdateAppointmentStatus();
  const createException = useCreateException();

  const [date, setDate] = useState<Date>(new Date());
  const [selected, setSelected] = useState<Appointment | null>(null);
  const [confirmBlock, setConfirmBlock] = useState(false);

  const appointments = useMemo(() => appointmentsQuery.data ?? [], [appointmentsQuery.data]);
  const exceptions = useMemo(() => exceptionsQuery.data ?? [], [exceptionsQuery.data]);

  // Assim que a agenda carrega, marca como "vistas" — some o badge no nav.
  useEffect(() => {
    if (appointmentsQuery.data) markAppointmentsAsSeen(appointmentsQuery.data.length);
  }, [appointmentsQuery.data]);

  const dayAppointments = useMemo(
    () =>
      appointments
        .filter((a) => isSameDay(toBrasiliaDisplayDate(a.scheduled_at), date))
        .sort((a, b) => +new Date(a.scheduled_at) - +new Date(b.scheduled_at)),
    [appointments, date],
  );

  const bookedDates = useMemo(() => appointments.map((a) => toBrasiliaDisplayDate(a.scheduled_at)), [appointments]);
  const blockedDates = useMemo(
    () => exceptions.filter((e) => !e.start_time).map((e) => new Date(`${e.exception_date}T00:00:00`)),
    [exceptions],
  );

  const isDayFullyBlocked = exceptions.some(
    (e) => !e.start_time && isSameDay(new Date(`${e.exception_date}T00:00:00`), date),
  );

  const updateAppointmentStatus = (id: string, status: AppointmentStatus) => {
    updateStatus.mutate(
      { id, status },
      {
        onSuccess: () => {
          setSelected(null);
          toast.success(`Consulta ${statusLabels[status].toLowerCase()}.`);
        },
        onError: (error) => toast.error(getErrorMessage(error)),
      },
    );
  };

  const blockDay = () => {
    createException.mutate(
      { exception_date: format(date, "yyyy-MM-dd"), reason: "Bloqueado pelo médico" },
      {
        onSuccess: () => {
          setConfirmBlock(false);
          toast.success(`Dia ${format(date, "dd/MM")} bloqueado.`);
        },
        onError: (error) => {
          setConfirmBlock(false);
          toast.error(getErrorMessage(error));
        },
      },
    );
  };

  return (
    <div className="p-4 md:p-6">
      <div className="flex items-center justify-between mb-4 gap-2">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Agenda</h1>
          <p className="text-sm text-muted-foreground">
            {format(date, "EEEE, dd 'de' MMMM", { locale: ptBR })}
          </p>
        </div>
        <Button variant="outline" disabled={isDayFullyBlocked} onClick={() => setConfirmBlock(true)}>
          <CalendarOff className="h-4 w-4 mr-1.5" />
          {isDayFullyBlocked ? "Dia já bloqueado" : "Bloquear dia"}
        </Button>
      </div>

      {/* Cards de estatísticas do mês */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <StatCard
          label="Consultas no mês"
          value={statsQuery.data?.total_appointments}
          loading={statsQuery.isLoading}
        />
        <StatCard
          label="Comparecimento"
          value={statsQuery.data ? `${statsQuery.data.attendance_rate}%` : undefined}
          loading={statsQuery.isLoading}
        />
        <StatCard label="Faltas" value={statsQuery.data?.no_show} loading={statsQuery.isLoading} />
        <StatCard label="Canceladas" value={statsQuery.data?.cancelled} loading={statsQuery.isLoading} />
      </div>

      <div className="grid lg:grid-cols-[1fr_320px] gap-4">
        {/* Calendário */}
        <div className="bg-background border border-border rounded-xl p-3">
          <Calendar
            mode="single"
            selected={date}
            onSelect={(d) => d && setDate(d)}
            locale={ptBR}
            modifiers={{ booked: bookedDates, blocked: blockedDates }}
            modifiersClassNames={{
              booked:
                "relative after:content-[''] after:absolute after:bottom-1 after:left-1/2 after:-translate-x-1/2 after:h-1 after:w-1 after:rounded-full after:bg-primary",
              blocked: "line-through opacity-50",
            }}
            className={cn("p-0 pointer-events-auto w-full")}
          />
          <div className="mt-4 flex flex-wrap gap-3 text-xs">
            <LegendDot color="bg-primary" label="Confirmado" />
            <LegendDot color="bg-success" label="Concluído" />
            <LegendDot color="bg-warning" label="Pendente" />
            <LegendDot color="bg-destructive" label="Cancelado" />
          </div>
        </div>

        {/* Lista do dia */}
        <div className="bg-background border border-border rounded-xl p-4">
          <h2 className="text-sm font-semibold text-foreground mb-3">
            Consultas de {format(date, "dd/MM")}
          </h2>
          {appointmentsQuery.isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
            </div>
          ) : dayAppointments.length === 0 ? (
            <EmptyState
              icon={Clock}
              title="Nenhuma consulta"
              description="Não há consultas agendadas para este dia."
            />
          ) : (
            <ul className="space-y-2">
              {dayAppointments.map((a) => (
                <li key={a.id}>
                  <button
                    onClick={() => setSelected(a)}
                    className="w-full text-left rounded-lg border border-border p-3 hover:bg-secondary transition-colors"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-semibold text-foreground truncate">
                        {a.patient?.name ?? "—"}
                      </span>
                      <Badge className={cn("shrink-0 text-[10px]", statusColor[a.status])}>
                        {statusLabels[a.status]}
                      </Badge>
                    </div>
                    <div className="mt-1 text-xs text-muted-foreground flex items-center gap-1">
                      <Clock className="h-3 w-3" /> {format(toBrasiliaDisplayDate(a.scheduled_at), "HH:mm")}
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Modal detalhes */}
      <Dialog open={!!selected} onOpenChange={(o) => !o && setSelected(null)}>
        <DialogContent className="sm:max-w-md">
          {selected && (
            <>
              <DialogHeader>
                <DialogTitle>{selected.patient?.name ?? "Paciente"}</DialogTitle>
                <DialogDescription>
                  {format(toBrasiliaDisplayDate(selected.scheduled_at), "EEEE, dd/MM 'às' HH:mm", { locale: ptBR })}
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-2 text-sm py-2">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Telefone</span>
                  <span className="text-foreground">{selected.patient?.phone ?? "—"}</span>
                </div>
                {selected.patient?.email && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Email</span>
                    <span className="text-foreground">{selected.patient.email}</span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Status</span>
                  <Badge className={cn(statusColor[selected.status])}>{statusLabels[selected.status]}</Badge>
                </div>
              </div>
              <DialogFooter className="flex-col sm:flex-row gap-2">
                {selected.status !== "confirmed" && !CANCELLED.includes(selected.status) && (
                  <Button
                    className="w-full"
                    disabled={updateStatus.isPending}
                    onClick={() => updateAppointmentStatus(selected.id, "confirmed")}
                  >
                    <CheckCircle2 className="h-4 w-4 mr-1.5" /> Confirmar
                  </Button>
                )}
                {selected.status !== "completed" && !CANCELLED.includes(selected.status) && (
                  <Button
                    className="w-full bg-success text-success-foreground hover:bg-success/90"
                    disabled={updateStatus.isPending}
                    onClick={() => updateAppointmentStatus(selected.id, "completed")}
                  >
                    Concluída
                  </Button>
                )}
                {!CANCELLED.includes(selected.status) && (
                  <Button
                    variant="destructive"
                    className="w-full"
                    disabled={updateStatus.isPending}
                    onClick={() => updateAppointmentStatus(selected.id, "cancelled_by_doctor")}
                  >
                    <XCircle className="h-4 w-4 mr-1.5" /> Cancelar
                  </Button>
                )}
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>

      {/* Confirmação de bloqueio de dia */}
      <AlertDialog open={confirmBlock} onOpenChange={setConfirmBlock}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Bloquear {format(date, "dd/MM/yyyy")}?</AlertDialogTitle>
            <AlertDialogDescription>
              Nenhum paciente poderá agendar horários neste dia. Se já houver consultas ativas, o bloqueio será
              recusado — cancele ou remarque antes.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={blockDay} disabled={createException.isPending}>
              {createException.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Bloquear"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

function StatCard({
  label,
  value,
  loading,
}: {
  label: string;
  value: string | number | undefined;
  loading: boolean;
}) {
  return (
    <Card>
      <CardContent className="p-3 md:p-4">
        <div className="text-xs text-muted-foreground truncate">{label}</div>
        <div className="mt-1 text-xl md:text-2xl font-bold text-foreground">
          {loading ? <Loader2 className="h-5 w-5 animate-spin text-primary" /> : value ?? "—"}
        </div>
      </CardContent>
    </Card>
  );
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-1.5 text-muted-foreground">
      <span className={cn("h-2.5 w-2.5 rounded-full", color)} />
      {label}
    </div>
  );
}
