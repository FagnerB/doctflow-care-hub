import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Copy, Info, Loader2, Stethoscope } from "lucide-react";
import { toast } from "sonner";
import { WeeklySchedule, defaultWeeklyHours, type WeeklyHours } from "@/components/WeeklySchedule";
import { useDoctorProfile, useUpdateDoctorProfile } from "@/hooks/use-doctor";
import { getErrorMessage } from "@/lib/api-client";
import { weeklyHoursToWorkingHours, workingHoursToWeeklyHours } from "@/lib/schedule-mapping";

export const Route = createFileRoute("/dashboard/settings")({
  component: SettingsPage,
});

function SettingsPage() {
  const profileQuery = useDoctorProfile();
  const updateProfile = useUpdateDoctorProfile();
  const profile = profileQuery.data;

  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [specialty, setSpecialty] = useState("");
  const [bio, setBio] = useState("");
  const [hours, setHours] = useState<WeeklyHours>(defaultWeeklyHours());
  const [autoConfirm, setAutoConfirm] = useState(true);
  const [duration, setDuration] = useState("30");
  const [horizon, setHorizon] = useState("30");
  const [cancellationHours, setCancellationHours] = useState("24");

  // Preenche o formulário quando o perfil chega da API (só uma vez por carregamento).
  useEffect(() => {
    if (!profile) return;
    setName(profile.user.full_name);
    setPhone(profile.user.phone);
    setSpecialty(profile.specialty);
    setBio(profile.bio ?? "");
    setHours(workingHoursToWeeklyHours(profile.config_json.working_hours));
    setAutoConfirm(profile.config_json.auto_confirm);
    setDuration(String(profile.config_json.consultation_duration_minutes));
    setHorizon(String(profile.config_json.advance_booking_days));
    setCancellationHours(String(profile.config_json.cancellation_policy_hours));
  }, [profile]);

  // Em dev local o link real ainda não existe (o médico não vai divulgar
  // "localhost"). Isso se resolve sozinho assim que o deploy do frontend
  // (Lovable) publica num domínio de verdade — window.location.origin já
  // reflete o host certo automaticamente, sem precisar mudar nada aqui.
  const isLocalPreview = typeof window !== "undefined" && window.location.hostname === "localhost";
  const publicLink =
    typeof window !== "undefined" && profile ? `${window.location.origin}/d/${profile.slug}` : "";

  const save = () => {
    if (!profile) return;
    updateProfile.mutate(
      {
        full_name: name,
        phone,
        specialty,
        bio,
        config_json: {
          consultation_duration_minutes: Number(duration),
          advance_booking_days: Number(horizon),
          auto_confirm: autoConfirm,
          cancellation_policy_hours: Number(cancellationHours),
          working_hours: weeklyHoursToWorkingHours(hours),
        },
      },
      {
        onSuccess: () => toast.success("Alterações salvas!"),
        onError: (error) => toast.error(getErrorMessage(error)),
      },
    );
  };

  if (profileQuery.isLoading) {
    return (
      <div className="p-4 md:p-6 flex items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6 max-w-3xl">
      <h1 className="text-2xl font-bold text-foreground">Configurações</h1>
      <p className="text-sm text-muted-foreground">Personalize seu perfil e agenda.</p>

      <div className="mt-6 space-y-6">
        {/* Perfil */}
        <Section title="Perfil">
          <div className="flex items-center gap-4">
            <Avatar className="h-16 w-16">
              <AvatarFallback className="bg-primary/10 text-primary">
                <Stethoscope />
              </AvatarFallback>
            </Avatar>
            <Button variant="outline" size="sm" onClick={() => toast.info("Em breve: upload de avatar")}>
              Enviar foto
            </Button>
          </div>
          <div className="grid sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label htmlFor="name">Nome</Label>
              <Input id="name" value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="specialty">Especialidade</Label>
              <Input id="specialty" value={specialty} onChange={(e) => setSpecialty(e.target.value)} />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="phone">Telefone (WhatsApp)</Label>
            <Input id="phone" value={phone} onChange={(e) => setPhone(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="bio">Bio</Label>
            <Textarea id="bio" value={bio} onChange={(e) => setBio(e.target.value)} rows={3} />
          </div>
        </Section>

        {/* Seu link */}
        <Section title="Seu link público">
          {isLocalPreview && (
            <p className="text-xs text-muted-foreground flex items-center gap-1.5">
              <Info className="h-3.5 w-3.5 shrink-0" />
              Preview local — quando o site for publicado, o link abaixo já mostra o domínio real automaticamente.
            </p>
          )}
          <TooltipProvider>
            <div className="flex items-center gap-2 rounded-lg border border-border bg-secondary p-3">
              <code className="flex-1 text-sm text-foreground truncate">{publicLink}</code>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => {
                      navigator.clipboard?.writeText(publicLink);
                      toast.success("Link copiado!");
                    }}
                  >
                    <Copy className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Copie este link e cole na bio do seu Instagram</TooltipContent>
              </Tooltip>
            </div>
          </TooltipProvider>
        </Section>

        {/* Horários */}
        <Section title="Horários de atendimento">
          <WeeklySchedule value={hours} onChange={setHours} />
        </Section>

        {/* Preferências */}
        <Section title="Preferências">
          <div className="flex items-center justify-between gap-4 p-3 rounded-lg border border-border">
            <div>
              <div className="text-sm font-medium text-foreground">Confirmação automática</div>
              <div className="text-xs text-muted-foreground">
                Novos agendamentos ficam confirmados automaticamente.
              </div>
            </div>
            <Switch checked={autoConfirm} onCheckedChange={setAutoConfirm} />
          </div>

          <div className="grid sm:grid-cols-3 gap-4">
            <div className="space-y-1.5">
              <Label>Duração da consulta</Label>
              <Select value={duration} onValueChange={setDuration}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="15">15 minutos</SelectItem>
                  <SelectItem value="30">30 minutos</SelectItem>
                  <SelectItem value="45">45 minutos</SelectItem>
                  <SelectItem value="60">60 minutos</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>Antecedência máxima</Label>
              <Select value={horizon} onValueChange={setHorizon}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="7">7 dias</SelectItem>
                  <SelectItem value="14">14 dias</SelectItem>
                  <SelectItem value="30">30 dias</SelectItem>
                  <SelectItem value="60">60 dias</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>Cancelamento até</Label>
              <Select value={cancellationHours} onValueChange={setCancellationHours}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="0">Sem prazo mínimo</SelectItem>
                  <SelectItem value="6">6 horas antes</SelectItem>
                  <SelectItem value="12">12 horas antes</SelectItem>
                  <SelectItem value="24">24 horas antes</SelectItem>
                  <SelectItem value="48">48 horas antes</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </Section>

        <div className="flex justify-end">
          <Button className="h-11 px-6" onClick={save} disabled={updateProfile.isPending}>
            {updateProfile.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Salvar alterações"}
          </Button>
        </div>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="bg-background border border-border rounded-xl p-5 space-y-4">
      <h2 className="text-base font-semibold text-foreground">{title}</h2>
      {children}
    </section>
  );
}
