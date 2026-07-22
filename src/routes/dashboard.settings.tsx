import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
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
import { Copy, Loader2, Stethoscope, Upload } from "lucide-react";
import { toast } from "sonner";
import { WeeklySchedule, defaultWeeklyHours, type WeeklyHours } from "@/components/WeeklySchedule";

export const Route = createFileRoute("/dashboard/settings")({
  component: SettingsPage,
});

function SettingsPage() {
  const [name, setName] = useState("Dr. Rafael Silva");
  const [specialty, setSpecialty] = useState("Cardiologia");
  const [bio, setBio] = useState("Cardiologista há 12 anos. Atendimento humanizado.");
  const [hours, setHours] = useState<WeeklyHours>(defaultWeeklyHours());
  const [autoConfirm, setAutoConfirm] = useState(true);
  const [duration, setDuration] = useState("30");
  const [horizon, setHorizon] = useState("30");
  const [saving, setSaving] = useState(false);
  const slug = "dr-silva";
  const link = `doctflow.com/d/${slug}`;

  const save = () => {
    setSaving(true);
    setTimeout(() => {
      setSaving(false);
      toast.success("Alterações salvas!");
    }, 600);
  };

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
              <Upload className="h-4 w-4 mr-1.5" /> Enviar foto
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
            <Label htmlFor="bio">Bio</Label>
            <Textarea id="bio" value={bio} onChange={(e) => setBio(e.target.value)} rows={3} />
          </div>
        </Section>

        {/* Seu link */}
        <Section title="Seu link público">
          <div className="flex items-center gap-2 rounded-lg border border-border bg-secondary p-3">
            <code className="flex-1 text-sm text-foreground truncate">{link}</code>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                navigator.clipboard?.writeText(link);
                toast.success("Link copiado!");
              }}
            >
              <Copy className="h-4 w-4" />
            </Button>
          </div>
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

          <div className="grid sm:grid-cols-2 gap-4">
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
          </div>
        </Section>

        <div className="flex justify-end">
          <Button className="h-11 px-6" onClick={save} disabled={saving}>
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : "Salvar alterações"}
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
