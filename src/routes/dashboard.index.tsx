import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { Calendar } from "@/components/ui/calendar";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
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
import { CalendarOff, CheckCircle2, Clock, XCircle } from "lucide-react";
import {
  mockAppointments,
  statusLabels,
  type Appointment,
  type AppointmentStatus,
} from "@/lib/mock-data";
import { toast } from "sonner";
import { EmptyState } from "@/components/EmptyState";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/dashboard/")({
  component: AgendaPage,
});

const statusColor: Record<AppointmentStatus, string> = {
  confirmed: "bg-primary text-primary-foreground",
  completed: "bg-success text-success-foreground",
  cancelled: "bg-destructive text-destructive-foreground",
  pending: "bg-warning text-warning-foreground",
};

function AgendaPage() {
  const [appointments, setAppointments] = useState<Appointment[]>(mockAppointments);
  const [date, setDate] = useState<Date>(new Date());
  const [selected, setSelected] = useState<Appointment | null>(null);

  const dayAppointments = useMemo(
    () => appointments.filter((a) => isSameDay(a.start, date)).sort((a, b) => +a.start - +b.start),
    [appointments, date],
  );

  const bookedDates = useMemo(() => appointments.map((a) => a.start), [appointments]);

  const updateStatus = (id: string, status: AppointmentStatus) => {
    setAppointments((prev) => prev.map((a) => (a.id === id ? { ...a, status } : a)));
    setSelected(null);
    toast.success(`Consulta ${statusLabels[status].toLowerCase()}.`);
  };

  const blockDay = () => {
    toast.success(`Dia ${format(date, "dd/MM")} bloqueado.`);
  };

  return (
    <div className="p-4 md:p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Agenda</h1>
          <p className="text-sm text-muted-foreground">
            {format(date, "EEEE, dd 'de' MMMM", { locale: ptBR })}
          </p>
        </div>
        <Button variant="outline" onClick={blockDay}>
          <CalendarOff className="h-4 w-4 mr-1.5" />
          Bloquear dia
        </Button>
      </div>

      <div className="grid lg:grid-cols-[1fr_320px] gap-4">
        {/* Calendário */}
        <div className="bg-background border border-border rounded-xl p-3">
          <Calendar
            mode="single"
            selected={date}
            onSelect={(d) => d && setDate(d)}
            locale={ptBR}
            modifiers={{ booked: bookedDates }}
            modifiersClassNames={{
              booked: "relative after:content-[''] after:absolute after:bottom-1 after:left-1/2 after:-translate-x-1/2 after:h-1 after:w-1 after:rounded-full after:bg-primary",
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
          {dayAppointments.length === 0 ? (
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
                        {a.patientName}
                      </span>
                      <Badge className={cn("shrink-0 text-[10px]", statusColor[a.status])}>
                        {statusLabels[a.status]}
                      </Badge>
                    </div>
                    <div className="mt-1 text-xs text-muted-foreground flex items-center gap-1">
                      <Clock className="h-3 w-3" /> {format(a.start, "HH:mm")} — {format(a.end, "HH:mm")}
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
                <DialogTitle>{selected.patientName}</DialogTitle>
                <DialogDescription>
                  {format(selected.start, "EEEE, dd/MM 'às' HH:mm", { locale: ptBR })}
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-2 text-sm py-2">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Telefone</span>
                  <span className="text-foreground">{selected.patientPhone}</span>
                </div>
                {selected.patientEmail && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Email</span>
                    <span className="text-foreground">{selected.patientEmail}</span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Status</span>
                  <Badge className={cn(statusColor[selected.status])}>
                    {statusLabels[selected.status]}
                  </Badge>
                </div>
              </div>
              <DialogFooter className="flex-col sm:flex-row gap-2">
                {selected.status !== "confirmed" && (
                  <Button className="w-full" onClick={() => updateStatus(selected.id, "confirmed")}>
                    <CheckCircle2 className="h-4 w-4 mr-1.5" /> Confirmar
                  </Button>
                )}
                {selected.status !== "completed" && (
                  <Button
                    className="w-full bg-success text-success-foreground hover:bg-success/90"
                    onClick={() => updateStatus(selected.id, "completed")}
                  >
                    Concluída
                  </Button>
                )}
                {selected.status !== "cancelled" && (
                  <Button
                    variant="destructive"
                    className="w-full"
                    onClick={() => updateStatus(selected.id, "cancelled")}
                  >
                    <XCircle className="h-4 w-4 mr-1.5" /> Cancelar
                  </Button>
                )}
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
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
