import { createFileRoute, Link } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { addDays, format, isBefore, startOfDay } from "date-fns";
import { ptBR } from "date-fns/locale";
import { Calendar } from "@/components/ui/calendar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { TimeSlotGrid } from "@/components/TimeSlotGrid";
import { PhoneInput, isValidPhone } from "@/components/PhoneInput";
import { EmptyState } from "@/components/EmptyState";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { CalendarPlus, CheckCircle2, Loader2, Mail, Stethoscope, Sun, Moon, SearchX } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { getErrorMessage } from "@/lib/api-client";
import { toBrasiliaDisplayDate } from "@/lib/timezone";
import { weekdaysWithoutHours } from "@/lib/schedule-mapping";
import { usePublicDoctor } from "@/hooks/use-doctor";
import { useAvailability } from "@/hooks/use-availability";
import { useCreatePublicAppointment } from "@/hooks/use-appointments";
import type { Appointment, AvailabilitySlot, DoctorPublic } from "@/lib/api-types";

export const Route = createFileRoute("/d/$slug")({
  head: ({ params }) => ({
    meta: [
      { title: `Agendar consulta — ${params.slug}` },
      { name: "description", content: "Agende sua consulta em 30 segundos." },
    ],
  }),
  component: BookingPage,
});

type Step = "pick" | "form" | "success";

function groupSlotsByPeriod(slots: AvailabilitySlot[]) {
  const morning: AvailabilitySlot[] = [];
  const afternoon: AvailabilitySlot[] = [];
  for (const slot of slots) {
    const hour = toBrasiliaDisplayDate(slot.start_time).getHours();
    (hour < 12 ? morning : afternoon).push(slot);
  }
  return { morning, afternoon };
}

function isDayDisabled(day: Date, doctor: DoctorPublic): boolean {
  if (isBefore(day, startOfDay(new Date()))) return true;
  const maxDate = addDays(startOfDay(new Date()), doctor.config_json.advance_booking_days);
  if (day > maxDate) return true;
  return weekdaysWithoutHours(doctor.config_json.working_hours).includes(day.getDay());
}

function BookingPage() {
  const { slug } = Route.useParams();
  const doctorQuery = usePublicDoctor(slug);
  const doctor = doctorQuery.data;

  const [date, setDate] = useState<Date | undefined>(new Date());
  const dateStr = date ? format(date, "yyyy-MM-dd") : "";
  const availabilityQuery = useAvailability(slug, dateStr);

  const [selectedSlot, setSelectedSlot] = useState<AvailabilitySlot | null>(null);
  const [step, setStep] = useState<Step>("pick");
  const [modalOpen, setModalOpen] = useState(false);
  const [createdAppointment, setCreatedAppointment] = useState<Appointment | null>(null);

  const slots = useMemo(() => availabilityQuery.data?.slots ?? [], [availabilityQuery.data]);
  const { morning, afternoon } = useMemo(() => groupSlotsByPeriod(slots), [slots]);
  const hasSlots = morning.length + afternoon.length > 0;

  const handleDateChange = (d: Date | undefined) => {
    setDate(d);
    setSelectedSlot(null);
  };

  const handleSlotSelect = (slot: AvailabilitySlot) => {
    setSelectedSlot(slot);
    setModalOpen(true);
    setStep("form");
  };

  const handleConfirmed = (appointment: Appointment) => {
    setCreatedAppointment(appointment);
    setStep("success");
  };

  if (doctorQuery.isLoading) {
    return (
      <div className="min-h-screen bg-secondary flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (doctorQuery.isError || !doctor) {
    return (
      <div className="min-h-screen bg-secondary flex items-center justify-center px-4">
        <EmptyState icon={SearchX} title="Médico não encontrado" description="Verifique se o link está correto." />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-secondary">
      {/* Header do médico */}
      <div className="bg-background border-b border-border">
        <div className="mx-auto max-w-2xl px-4 py-6 flex items-center gap-4">
          <Avatar className="h-16 w-16 border-2 border-primary/20">
            <AvatarFallback className="bg-primary/10 text-primary text-xl">
              <Stethoscope />
            </AvatarFallback>
          </Avatar>
          <div className="min-w-0">
            <h1 className="text-xl font-bold text-foreground truncate">{doctor.full_name}</h1>
            <p className="text-sm text-primary font-medium">{doctor.specialty}</p>
            {doctor.bio && <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{doctor.bio}</p>}
          </div>
        </div>
      </div>

      <main className="mx-auto max-w-2xl px-4 py-6 space-y-6">
        {/* Calendário */}
        <section className="bg-background rounded-xl border border-border p-4">
          <h2 className="text-sm font-semibold text-foreground mb-3">
            <CalendarPlus className="inline h-4 w-4 mr-1.5 text-primary" />
            Escolha uma data
          </h2>
          <Calendar
            mode="single"
            selected={date}
            onSelect={handleDateChange}
            disabled={(d) => isDayDisabled(d, doctor)}
            locale={ptBR}
            className={cn("p-0 pointer-events-auto w-full")}
          />
        </section>

        {/* Slots */}
        {date && (
          <section className="bg-background rounded-xl border border-border p-4">
            <h2 className="text-sm font-semibold text-foreground mb-3">
              Horários em {format(date, "dd 'de' MMMM", { locale: ptBR })}
            </h2>
            {availabilityQuery.isLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-primary" />
              </div>
            ) : !hasSlots ? (
              <EmptyState
                title="Sem horários disponíveis"
                description={`${doctor.full_name} não possui horários disponíveis nesta data. Tente outra data.`}
              />
            ) : (
              <div className="space-y-4">
                {morning.length > 0 && (
                  <div>
                    <div className="flex items-center gap-1.5 mb-2 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                      <Sun className="h-3.5 w-3.5" /> Manhã
                    </div>
                    <SlotGrid slots={morning} selected={selectedSlot} onSelect={handleSlotSelect} />
                  </div>
                )}
                {afternoon.length > 0 && (
                  <div>
                    <div className="flex items-center gap-1.5 mb-2 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                      <Moon className="h-3.5 w-3.5" /> Tarde
                    </div>
                    <SlotGrid slots={afternoon} selected={selectedSlot} onSelect={handleSlotSelect} />
                  </div>
                )}
              </div>
            )}
          </section>
        )}
      </main>

      {/* Modal de confirmação */}
      <Dialog
        open={modalOpen}
        onOpenChange={(o) => {
          setModalOpen(o);
          if (!o) setStep("pick");
        }}
      >
        <DialogContent className="sm:max-w-md">
          {step === "form" && selectedSlot && (
            <BookingForm slot={selectedSlot} doctorSlug={slug} doctorName={doctor.full_name} onSuccess={handleConfirmed} />
          )}
          {step === "success" && selectedSlot && createdAppointment && (
            <SuccessScreen
              slot={selectedSlot}
              appointment={createdAppointment}
              doctorName={doctor.full_name}
              onClose={() => {
                setModalOpen(false);
                setStep("pick");
                setSelectedSlot(null);
              }}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

// Adapta AvailabilitySlot (start_time ISO) para o componente TimeSlotGrid, que
// trabalha com Date de exibição — sem tocar no ISO original, que segue junto
// no `slot` selecionado para ser enviado à API sem reconstrução.
function SlotGrid({
  slots,
  selected,
  onSelect,
}: {
  slots: AvailabilitySlot[];
  selected: AvailabilitySlot | null;
  onSelect: (slot: AvailabilitySlot) => void;
}) {
  const displayDates = slots.map((slot) => toBrasiliaDisplayDate(slot.start_time));
  const selectedDisplay = selected ? toBrasiliaDisplayDate(selected.start_time) : null;
  return (
    <TimeSlotGrid
      slots={displayDates}
      selected={selectedDisplay}
      onSelect={(displayDate) => {
        const index = displayDates.findIndex((d) => d.getTime() === displayDate.getTime());
        if (index >= 0) onSelect(slots[index]);
      }}
    />
  );
}

function BookingForm({
  slot,
  doctorSlug,
  doctorName,
  onSuccess,
}: {
  slot: AvailabilitySlot;
  doctorSlug: string;
  doctorName: string;
  onSuccess: (appointment: Appointment) => void;
}) {
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [errors, setErrors] = useState<{ name?: string; phone?: string }>({});
  const createAppointment = useCreatePublicAppointment();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const errs: typeof errors = {};
    if (name.trim().length < 3) errs.name = "Informe seu nome completo.";
    if (!isValidPhone(phone)) errs.phone = "Telefone inválido. Use (DD) 99999-9999.";
    setErrors(errs);
    if (Object.keys(errs).length > 0) return;

    createAppointment.mutate(
      {
        doctor_slug: doctorSlug,
        patient_name: name,
        patient_phone: phone,
        patient_email: email || undefined,
        desired_datetime: slot.start_time,
      },
      {
        onSuccess: (appointment) => {
          toast.success("Consulta agendada com sucesso!");
          onSuccess(appointment);
        },
        onError: (error) => toast.error(getErrorMessage(error)),
      },
    );
  };

  return (
    <form onSubmit={handleSubmit}>
      <DialogHeader>
        <DialogTitle>Confirmar agendamento</DialogTitle>
        <DialogDescription>
          {doctorName} · {format(toBrasiliaDisplayDate(slot.start_time), "dd/MM/yyyy 'às' HH:mm", { locale: ptBR })}
        </DialogDescription>
      </DialogHeader>
      <div className="space-y-4 py-4">
        <div className="space-y-1.5">
          <Label htmlFor="name">Nome completo</Label>
          <Input
            id="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Seu nome"
            aria-invalid={!!errors.name}
          />
          {errors.name && <p className="text-xs text-destructive">{errors.name}</p>}
        </div>
        <PhoneInput label="WhatsApp" value={phone} onChange={setPhone} error={errors.phone} />
        <div className="space-y-1.5">
          <Label htmlFor="email">Email (opcional)</Label>
          <Input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="voce@email.com"
          />
        </div>
      </div>
      <DialogFooter>
        <Button
          type="submit"
          disabled={createAppointment.isPending}
          className="w-full bg-accent text-accent-foreground hover:bg-accent/90 h-11"
        >
          {createAppointment.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Confirmar agendamento"}
        </Button>
      </DialogFooter>
    </form>
  );
}

// "2026-08-24T13:00:00Z" -> "20260824T130000Z", formato exigido pelo parâmetro
// `dates` do link de criação de evento do Google Calendar.
function toGoogleCalendarStamp(iso: string): string {
  return new Date(iso).toISOString().replace(/[-:]/g, "").split(".")[0] + "Z";
}

function buildGoogleCalendarUrl(appointment: Appointment, doctorName: string): string {
  const start = new Date(appointment.scheduled_at);
  const end = new Date(start.getTime() + appointment.duration_minutes * 60_000);
  const params = new URLSearchParams({
    action: "TEMPLATE",
    text: `Consulta com ${doctorName}`,
    dates: `${toGoogleCalendarStamp(start.toISOString())}/${toGoogleCalendarStamp(end.toISOString())}`,
    details: "Agendado pelo DoctFlow.",
  });
  return `https://calendar.google.com/calendar/render?${params.toString()}`;
}

function SuccessScreen({
  slot,
  appointment,
  doctorName,
  onClose,
}: {
  slot: AvailabilitySlot;
  appointment: Appointment;
  doctorName: string;
  onClose: () => void;
}) {
  // Código curto só para referência visual — o id completo (UUID) é o que
  // realmente identifica a consulta nos links e na API.
  const shortCode = appointment.id.slice(0, 8).toUpperCase();
  const patientEmail = appointment.patient?.email;

  return (
    <div className="text-center py-4">
      <div className="mx-auto h-16 w-16 rounded-full bg-success/10 grid place-items-center mb-4">
        <CheckCircle2 className="h-9 w-9 text-success" />
      </div>
      <h2 className="text-xl font-bold text-foreground">Consulta confirmada! ✅</h2>
      <p className="mt-2 text-sm text-foreground font-medium">{doctorName}</p>
      <p className="text-sm text-muted-foreground">
        {format(toBrasiliaDisplayDate(slot.start_time), "EEEE, dd 'de' MMMM 'às' HH:mm", { locale: ptBR })}
      </p>
      <p className="mt-1 text-xs text-muted-foreground">Código da consulta: #{shortCode}</p>
      <div className="mt-6 flex items-center gap-2 rounded-lg bg-secondary p-3 text-sm text-foreground">
        <Mail className="h-5 w-5 text-primary shrink-0" />
        <span className="text-left">
          {patientEmail ? (
            <>
              Se o email chegar, a confirmação vai para <strong>{patientEmail}</strong>. De qualquer forma, guarde
              o link abaixo.
            </>
          ) : (
            "Você não informou email, então não vai receber confirmação por nenhum canal — guarde o código acima ou o link abaixo."
          )}
        </span>
      </div>
      <div className="mt-4 flex flex-col gap-2">
        <a
          href={buildGoogleCalendarUrl(appointment, doctorName)}
          target="_blank"
          rel="noopener noreferrer"
          className="w-full"
        >
          <Button variant="outline" className="w-full">
            <CalendarPlus className="h-4 w-4 mr-1.5" />
            Adicionar ao meu calendário
          </Button>
        </a>
        <Link to="/appointment/$id" params={{ id: appointment.id }} className="w-full">
          <Button variant="outline" className="w-full">
            Ver ou cancelar minha consulta
          </Button>
        </Link>
        <p className="text-xs text-muted-foreground">
          Salve este link — é por ele que você acompanha ou cancela a consulta, com ou sem email.
        </p>
        <Button className="w-full" onClick={onClose}>Fechar</Button>
      </div>
    </div>
  );
}
