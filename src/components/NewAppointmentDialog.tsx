// Modal de agendamento manual pelo médico (telefone, balcão, encaixe).
// Objetivo do produto: cadastrar um paciente novo e agendar para ele em
// menos de 30 segundos, sem sair do modal.
import { useEffect, useMemo, useState } from "react";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { AlertTriangle, Loader2, Search, UserPlus, X } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { PhoneInput, isValidPhone } from "@/components/PhoneInput";
import { getErrorMessage } from "@/lib/api-client";
import { buildBrasiliaIso, toBrasiliaDisplayDate } from "@/lib/timezone";
import { workingHoursToWeeklyHours } from "@/lib/schedule-mapping";
import { cn } from "@/lib/utils";
import { useCreateDoctorAppointment, useDoctorAppointments } from "@/hooks/use-appointments";
import { useAvailability } from "@/hooks/use-availability";
import { filterPatients, usePatients, type PatientSummary } from "@/hooks/use-patients";
import type { Appointment, Doctor } from "@/lib/api-types";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  doctor: Doctor;
  defaultDate?: Date;
}

const CANCELLED_STATUSES = ["cancelled_by_patient", "cancelled_by_doctor"];

// Compara "HH:mm" convertendo para minutos — mais seguro que comparação de
// string quando os formatos podem variar em zero à esquerda.
function toMinutes(hhmm: string): number {
  const [h, m] = hhmm.split(":").map(Number);
  return h * 60 + m;
}

function isOutsideWorkingHours(doctor: Doctor, date: Date, timeStr: string): boolean {
  if (!timeStr) return false;
  const weeklyHours = workingHoursToWeeklyHours(doctor.config_json.working_hours);
  const windows = weeklyHours[date.getDay()] ?? [];
  const minutes = toMinutes(timeStr);
  return !windows.some((w) => minutes >= toMinutes(w.start) && minutes < toMinutes(w.end));
}

// Índice único do banco só pega horário IDÊNTICO — duas consultas às 09:00 e
// 09:15 com 30min de duração se sobrepõem sem colidir no índice. Isso aqui é
// só aviso (o próprio índice já bloqueia o caso de colisão exata; encaixe
// sobreposto é prática legítima e não pode ser proibido pelo sistema).
function findOverlap(
  appointments: Appointment[],
  date: Date,
  timeStr: string,
  durationMinutes: number,
): Appointment | null {
  if (!timeStr) return null;
  const start = new Date(buildBrasiliaIso(date, timeStr)).getTime();
  const end = start + durationMinutes * 60_000;

  for (const appointment of appointments) {
    if (CANCELLED_STATUSES.includes(appointment.status)) continue;
    const otherStart = new Date(appointment.scheduled_at).getTime();
    const otherEnd = otherStart + appointment.duration_minutes * 60_000;
    if (start < otherEnd && end > otherStart) return appointment;
  }
  return null;
}

export function NewAppointmentDialog({ open, onOpenChange, doctor, defaultDate }: Props) {
  const { patients } = usePatients();
  const appointmentsQuery = useDoctorAppointments();
  const createAppointment = useCreateDoctorAppointment();

  const [search, setSearch] = useState("");
  const [selectedPatient, setSelectedPatient] = useState<PatientSummary | null>(null);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [date, setDate] = useState<Date | undefined>(defaultDate ?? new Date());
  const [timeStr, setTimeStr] = useState("");
  const [notes, setNotes] = useState("");
  const [notifyPatient, setNotifyPatient] = useState(true);
  const [errors, setErrors] = useState<{ name?: string; phone?: string; time?: string }>({});

  const dateStr = date ? format(date, "yyyy-MM-dd") : "";
  const availabilityQuery = useAvailability(doctor.slug, dateStr);
  const freeSlots = availabilityQuery.data?.slots ?? [];

  const suggestions = useMemo(
    () => (search.trim() && !selectedPatient ? filterPatients(patients, search).slice(0, 5) : []),
    [search, patients, selectedPatient],
  );

  const outsideHours = date ? isOutsideWorkingHours(doctor, date, timeStr) : false;
  const overlap = useMemo(
    () =>
      date
        ? findOverlap(appointmentsQuery.data ?? [], date, timeStr, doctor.config_json.consultation_duration_minutes)
        : null,
    [appointmentsQuery.data, date, timeStr, doctor.config_json.consultation_duration_minutes],
  );

  // Reseta o formulário toda vez que o modal abre — não deixa lixo da última
  // vez visível quando o médico abre de novo.
  useEffect(() => {
    if (!open) return;
    setSearch("");
    setSelectedPatient(null);
    setName("");
    setPhone("");
    setDate(defaultDate ?? new Date());
    setTimeStr("");
    setNotes("");
    setNotifyPatient(true);
    setErrors({});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const pickPatient = (p: PatientSummary) => {
    setSelectedPatient(p);
    setName(p.patient.name);
    setPhone(p.patient.phone.replace(/^\+55/, "").replace(/(\d{2})(\d{5})(\d{4})/, "($1) $2-$3"));
    setSearch("");
  };

  const clearPatientSelection = () => {
    setSelectedPatient(null);
    setName("");
    setPhone("");
  };

  const pickSlot = (iso: string) => {
    setTimeStr(format(toBrasiliaDisplayDate(iso), "HH:mm"));
  };

  const submit = () => {
    const errs: typeof errors = {};
    if (name.trim().length < 3) errs.name = "Informe o nome completo.";
    if (!isValidPhone(phone)) errs.phone = "Telefone inválido. Use (DD) 99999-9999.";
    if (!date || !timeStr) errs.time = "Escolha data e horário.";
    setErrors(errs);
    if (Object.keys(errs).length > 0 || !date) return;

    createAppointment.mutate(
      {
        patient_name: name,
        patient_phone: phone,
        scheduled_at: buildBrasiliaIso(date, timeStr),
        notes: notes || undefined,
        notify_patient: notifyPatient,
      },
      {
        onSuccess: () => {
          toast.success("Consulta agendada.");
          onOpenChange(false);
        },
        onError: (error) => {
          // 409 (conflito de horário) fica no modal — o médico escolhe outro
          // horário sem perder o que já preencheu. Erro genérico também não
          // fecha, para não perder o preenchimento à toa.
          toast.error(getErrorMessage(error));
        },
      },
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Novo agendamento</DialogTitle>
          <DialogDescription>Cadastre o paciente na hora, se precisar, e marque a consulta.</DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Paciente */}
          <div className="space-y-1.5">
            <Label>Paciente</Label>
            {selectedPatient ? (
              <div className="flex items-center justify-between gap-2 rounded-lg border border-border bg-secondary p-2.5">
                <span className="text-sm text-foreground truncate">
                  {selectedPatient.patient.name} · {selectedPatient.patient.phone}
                </span>
                <Button size="sm" variant="ghost" onClick={clearPatientSelection} aria-label="Trocar paciente">
                  <X className="h-4 w-4" />
                </Button>
              </div>
            ) : (
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Buscar paciente por nome ou telefone"
                  className="pl-9"
                />
                {suggestions.length > 0 && (
                  <div className="absolute z-10 mt-1 w-full rounded-lg border border-border bg-background shadow-md overflow-hidden">
                    {suggestions.map((p) => (
                      <button
                        key={p.patient.id}
                        type="button"
                        onClick={() => pickPatient(p)}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-secondary transition-colors"
                      >
                        <div className="text-foreground font-medium">{p.patient.name}</div>
                        <div className="text-xs text-muted-foreground">{p.patient.phone}</div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Novo paciente (ou edição dos dados do selecionado) */}
          {!selectedPatient && (
            <div className="grid sm:grid-cols-2 gap-3 rounded-lg border border-dashed border-border p-3">
              <div className="sm:col-span-2 flex items-center gap-1.5 text-xs text-muted-foreground">
                <UserPlus className="h-3.5 w-3.5" />
                Não encontrou? Preencha para cadastrar um paciente novo.
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="patient-name">Nome completo</Label>
                <Input id="patient-name" value={name} onChange={(e) => setName(e.target.value)} aria-invalid={!!errors.name} />
                {errors.name && <p className="text-xs text-destructive">{errors.name}</p>}
              </div>
              <PhoneInput label="WhatsApp" value={phone} onChange={setPhone} error={errors.phone} id="patient-phone" />
            </div>
          )}

          {/* Data */}
          <div className="space-y-1.5">
            <Label>Data</Label>
            <Calendar
              mode="single"
              selected={date}
              onSelect={(d) => {
                setDate(d);
                setTimeStr("");
              }}
              locale={ptBR}
              className="p-0 pointer-events-auto rounded-lg border border-border"
            />
          </div>

          {/* Horário */}
          <div className="space-y-1.5">
            <Label>Horário</Label>
            {availabilityQuery.isLoading ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground py-2">
                <Loader2 className="h-4 w-4 animate-spin" /> Carregando horários livres...
              </div>
            ) : freeSlots.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {freeSlots.map((slot) => {
                  const label = format(toBrasiliaDisplayDate(slot.start_time), "HH:mm");
                  const active = timeStr === label;
                  return (
                    <button
                      key={slot.start_time}
                      type="button"
                      onClick={() => pickSlot(slot.start_time)}
                      className={cn(
                        "h-9 px-3 rounded-lg border text-sm font-medium transition-colors",
                        active
                          ? "bg-primary text-primary-foreground border-primary"
                          : "bg-background hover:bg-secondary border-border text-foreground",
                      )}
                    >
                      {label}
                    </button>
                  );
                })}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">Sem horários livres configurados nesse dia — digite o horário do encaixe abaixo.</p>
            )}
            <div className="flex items-center gap-2 pt-1">
              <Input
                type="time"
                value={timeStr}
                onChange={(e) => setTimeStr(e.target.value)}
                className="w-32"
                aria-invalid={!!errors.time}
              />
              <span className="text-xs text-muted-foreground">ou digite outro horário (encaixe)</span>
            </div>
            {errors.time && <p className="text-xs text-destructive">{errors.time}</p>}
            {outsideHours && (
              <div className="flex items-center gap-1.5 rounded-md bg-warning/15 text-warning-foreground px-2.5 py-1.5 text-xs">
                <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-warning" />
                Fora do expediente configurado — o agendamento é permitido mesmo assim.
              </div>
            )}
            {overlap && (
              <div className="flex items-center gap-1.5 rounded-md bg-warning/15 text-warning-foreground px-2.5 py-1.5 text-xs">
                <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-warning" />
                Se sobrepõe com {overlap.patient?.name ?? "outra consulta"} às{" "}
                {format(toBrasiliaDisplayDate(overlap.scheduled_at), "HH:mm")} ({overlap.duration_minutes}min) —
                agendamento permitido mesmo assim.
              </div>
            )}
          </div>

          {/* Observação */}
          <div className="space-y-1.5">
            <Label htmlFor="notes">Observação (opcional)</Label>
            <Textarea id="notes" value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} placeholder="Ex.: encaixe pedido por telefone" />
          </div>

          {/* Notificar paciente */}
          <div className="flex items-center justify-between gap-4 rounded-lg border border-border p-3">
            <div>
              <div className="text-sm font-medium text-foreground">Avisar o paciente pelo WhatsApp</div>
              <div className="text-xs text-muted-foreground">
                Desligue ao importar consultas que o paciente já sabe que tem — evita confirmação retroativa indevida.
              </div>
            </div>
            <Switch checked={notifyPatient} onCheckedChange={setNotifyPatient} />
          </div>
        </div>

        <DialogFooter>
          <Button className="w-full h-11" onClick={submit} disabled={createAppointment.isPending}>
            {createAppointment.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Agendar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
