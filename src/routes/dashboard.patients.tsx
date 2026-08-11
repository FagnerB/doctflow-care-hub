import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { Input } from "@/components/ui/input";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Loader2, Search, User } from "lucide-react";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { EmptyState } from "@/components/EmptyState";
import { toBrasiliaDisplayDate } from "@/lib/timezone";
import { useDoctorAppointments } from "@/hooks/use-appointments";
import type { Appointment, Patient } from "@/lib/api-types";

export const Route = createFileRoute("/dashboard/patients")({
  component: PatientsPage,
});

const statusLabels: Record<string, string> = {
  pending: "Pendente",
  confirmed: "Confirmado",
  completed: "Concluído",
  cancelled_by_patient: "Cancelado (paciente)",
  cancelled_by_doctor: "Cancelado (médico)",
  no_show: "Não compareceu",
};

interface PatientSummary {
  patient: Patient;
  lastVisit: string;
  totalVisits: number;
}

// O backend não tem um endpoint "listar pacientes" — só GET /patients/{id}
// (por id específico). Como cada consulta já vem com o paciente embutido
// (AppointmentRead.patient), derivamos a lista aqui: é exatamente o mesmo
// conjunto de pacientes que um endpoint dedicado devolveria, sem precisar de
// uma rota nova no backend.
function derivePatients(appointments: Appointment[]): PatientSummary[] {
  const byId = new Map<string, PatientSummary>();
  for (const appointment of appointments) {
    if (!appointment.patient) continue;
    const existing = byId.get(appointment.patient.id);
    if (!existing) {
      byId.set(appointment.patient.id, {
        patient: appointment.patient,
        lastVisit: appointment.scheduled_at,
        totalVisits: 1,
      });
    } else {
      existing.totalVisits += 1;
      if (new Date(appointment.scheduled_at) > new Date(existing.lastVisit)) {
        existing.lastVisit = appointment.scheduled_at;
      }
    }
  }
  return Array.from(byId.values()).sort((a, b) => +new Date(b.lastVisit) - +new Date(a.lastVisit));
}

function PatientsPage() {
  const appointmentsQuery = useDoctorAppointments();
  const [q, setQ] = useState("");
  const [selected, setSelected] = useState<PatientSummary | null>(null);

  const appointments = useMemo(() => appointmentsQuery.data ?? [], [appointmentsQuery.data]);
  const patients = useMemo(() => derivePatients(appointments), [appointments]);

  const filtered = useMemo(() => {
    const term = q.toLowerCase().trim();
    if (!term) return patients;
    const digits = term.replace(/\D/g, "");
    return patients.filter(
      (p) =>
        p.patient.name.toLowerCase().includes(term) ||
        (digits && p.patient.phone.replace(/\D/g, "").includes(digits)),
    );
  }, [q, patients]);

  const historyOf = (patientId: string) =>
    appointments
      .filter((a) => a.patient_id === patientId)
      .sort((a, b) => +new Date(b.scheduled_at) - +new Date(a.scheduled_at));

  return (
    <div className="p-4 md:p-6">
      <h1 className="text-2xl font-bold text-foreground">Pacientes</h1>
      <p className="text-sm text-muted-foreground">
        {appointmentsQuery.isLoading ? "Carregando..." : `${patients.length} pacientes cadastrados`}
      </p>

      <div className="mt-4 relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Buscar por nome ou telefone"
          className="pl-9 h-11"
        />
      </div>

      <div className="mt-4 bg-background border border-border rounded-xl overflow-hidden">
        {appointmentsQuery.isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState icon={User} title="Nenhum paciente encontrado" />
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nome</TableHead>
                  <TableHead>Telefone</TableHead>
                  <TableHead>Última consulta</TableHead>
                  <TableHead className="text-right">Total</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((p) => (
                  <TableRow key={p.patient.id} className="cursor-pointer" onClick={() => setSelected(p)}>
                    <TableCell className="font-medium text-foreground">{p.patient.name}</TableCell>
                    <TableCell className="text-muted-foreground">{p.patient.phone}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {format(toBrasiliaDisplayDate(p.lastVisit), "dd/MM/yyyy")}
                    </TableCell>
                    <TableCell className="text-right">
                      <Badge variant="secondary">{p.totalVisits}</Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </div>

      <Sheet open={!!selected} onOpenChange={(o) => !o && setSelected(null)}>
        <SheetContent className="w-full sm:max-w-md overflow-y-auto">
          {selected && (
            <>
              <SheetHeader>
                <SheetTitle>{selected.patient.name}</SheetTitle>
                <SheetDescription>{selected.patient.phone}</SheetDescription>
              </SheetHeader>
              <div className="mt-6 px-4">
                <h3 className="text-sm font-semibold text-foreground mb-2">Histórico</h3>
                <ul className="space-y-2">
                  {historyOf(selected.patient.id).map((a) => (
                    <li key={a.id} className="rounded-lg border border-border p-3 flex items-center justify-between">
                      <div>
                        <div className="text-sm font-medium text-foreground">
                          {format(toBrasiliaDisplayDate(a.scheduled_at), "dd 'de' MMM yyyy", { locale: ptBR })}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {format(toBrasiliaDisplayDate(a.scheduled_at), "HH:mm")}
                        </div>
                      </div>
                      <Badge variant="outline">{statusLabels[a.status]}</Badge>
                    </li>
                  ))}
                </ul>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}
