import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { format, isBefore, startOfDay } from "date-fns";
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
import { getAvailableSlots, mockDoctor } from "@/lib/mock-data";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { CalendarPlus, CheckCircle2, Loader2, MessageCircle, Stethoscope, Sun, Moon } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/d/$slug")({
  head: ({ params }) => ({
    meta: [
      { title: `Agendar consulta — ${mockDoctor.name}` },
      {
        name: "description",
        content: `Agende sua consulta com ${mockDoctor.name} (${mockDoctor.specialty}) em 30 segundos.`,
      },
      { property: "og:title", content: `Agendar com ${mockDoctor.name}` },
      { property: "og:description", content: `Agendamento online — /${params.slug}` },
    ],
  }),
  component: BookingPage,
});

type Step = "pick" | "form" | "success";

function BookingPage() {
  const [date, setDate] = useState<Date | undefined>(new Date());
  const [selectedSlot, setSelectedSlot] = useState<Date | null>(null);
  const [step, setStep] = useState<Step>("pick");
  const [modalOpen, setModalOpen] = useState(false);
  const [loadingSlots, setLoadingSlots] = useState(false);

  const doctor = mockDoctor;
  const slots = date ? getAvailableSlots(date) : { morning: [], afternoon: [] };
  const hasSlots = slots.morning.length + slots.afternoon.length > 0;

  const handleDateChange = (d: Date | undefined) => {
    setDate(d);
    setSelectedSlot(null);
    if (d) {
      setLoadingSlots(true);
      setTimeout(() => setLoadingSlots(false), 300);
    }
  };

  const handleSlotSelect = (slot: Date) => {
    setSelectedSlot(slot);
    setModalOpen(true);
    setStep("form");
  };

  const handleConfirmed = () => {
    setStep("success");
  };

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
            <h1 className="text-xl font-bold text-foreground truncate">{doctor.name}</h1>
            <p className="text-sm text-primary font-medium">{doctor.specialty}</p>
            <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{doctor.bio}</p>
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
            disabled={(d) => isBefore(d, startOfDay(new Date()))}
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
            {loadingSlots ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-primary" />
              </div>
            ) : !hasSlots ? (
              <EmptyState
                title="Sem horários disponíveis"
                description={`${doctor.name} não possui horários disponíveis nesta data. Tente outra data.`}
              />
            ) : (
              <div className="space-y-4">
                {slots.morning.length > 0 && (
                  <div>
                    <div className="flex items-center gap-1.5 mb-2 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                      <Sun className="h-3.5 w-3.5" /> Manhã
                    </div>
                    <TimeSlotGrid slots={slots.morning} selected={selectedSlot} onSelect={handleSlotSelect} />
                  </div>
                )}
                {slots.afternoon.length > 0 && (
                  <div>
                    <div className="flex items-center gap-1.5 mb-2 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                      <Moon className="h-3.5 w-3.5" /> Tarde
                    </div>
                    <TimeSlotGrid slots={slots.afternoon} selected={selectedSlot} onSelect={handleSlotSelect} />
                  </div>
                )}
              </div>
            )}
          </section>
        )}
      </main>

      {/* Modal de confirmação */}
      <Dialog open={modalOpen} onOpenChange={(o) => { setModalOpen(o); if (!o) setStep("pick"); }}>
        <DialogContent className="sm:max-w-md">
          {step === "form" && selectedSlot && (
            <BookingForm
              slot={selectedSlot}
              doctorName={doctor.name}
              onSuccess={handleConfirmed}
            />
          )}
          {step === "success" && selectedSlot && (
            <SuccessScreen
              slot={selectedSlot}
              onClose={() => { setModalOpen(false); setStep("pick"); setSelectedSlot(null); }}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

function BookingForm({
  slot,
  doctorName,
  onSuccess,
}: {
  slot: Date;
  doctorName: string;
  onSuccess: () => void;
}) {
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [errors, setErrors] = useState<{ name?: string; phone?: string }>({});
  const [loading, setLoading] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const errs: typeof errors = {};
    if (name.trim().length < 3) errs.name = "Informe seu nome completo.";
    if (!isValidPhone(phone)) errs.phone = "Telefone inválido. Use (DD) 99999-9999.";
    setErrors(errs);
    if (Object.keys(errs).length > 0) return;

    setLoading(true);
    // Simula chamada de API
    setTimeout(() => {
      setLoading(false);
      toast.success("Consulta agendada com sucesso!");
      onSuccess();
    }, 800);
  };

  return (
    <form onSubmit={handleSubmit}>
      <DialogHeader>
        <DialogTitle>Confirmar agendamento</DialogTitle>
        <DialogDescription>
          {doctorName} · {format(slot, "dd/MM/yyyy 'às' HH:mm", { locale: ptBR })}
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
        <PhoneInput
          label="WhatsApp"
          value={phone}
          onChange={setPhone}
          error={errors.phone}
        />
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
          disabled={loading}
          className="w-full bg-accent text-accent-foreground hover:bg-accent/90 h-11"
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Confirmar agendamento"}
        </Button>
      </DialogFooter>
    </form>
  );
}

function SuccessScreen({ slot, onClose }: { slot: Date; onClose: () => void }) {
  return (
    <div className="text-center py-4">
      <div className="mx-auto h-16 w-16 rounded-full bg-success/10 grid place-items-center mb-4">
        <CheckCircle2 className="h-9 w-9 text-success" />
      </div>
      <h2 className="text-xl font-bold text-foreground">Consulta confirmada! ✅</h2>
      <p className="mt-2 text-sm text-muted-foreground">
        {format(slot, "EEEE, dd 'de' MMMM 'às' HH:mm", { locale: ptBR })}
      </p>
      <div className="mt-6 flex items-center gap-2 rounded-lg bg-secondary p-3 text-sm text-foreground">
        <MessageCircle className="h-5 w-5 text-primary shrink-0" />
        <span className="text-left">Você receberá lembretes pelo WhatsApp.</span>
      </div>
      <div className="mt-4 flex flex-col gap-2">
        <Button variant="outline" className="w-full" onClick={() => toast.info("Em breve: integração com Google Calendar")}>
          <CalendarPlus className="h-4 w-4 mr-1.5" />
          Adicionar ao Google Calendar
        </Button>
        <Button className="w-full" onClick={onClose}>Fechar</Button>
      </div>
    </div>
  );
}
