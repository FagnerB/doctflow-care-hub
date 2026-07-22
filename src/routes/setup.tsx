import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { toast } from "sonner";
import { Check, Copy, Loader2, Stethoscope } from "lucide-react";
import { WeeklySchedule, type WeeklyHours, defaultWeeklyHours } from "@/components/WeeklySchedule";

export const Route = createFileRoute("/setup")({
  head: () => ({
    meta: [
      { title: "Primeiro acesso — DoctFlow" },
      { name: "description", content: "Configure sua conta em 3 passos." },
    ],
  }),
  component: SetupPage,
});

function SetupPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [password, setPassword] = useState("");
  const [password2, setPassword2] = useState("");
  const [hours, setHours] = useState<WeeklyHours>(defaultWeeklyHours());
  const [loading, setLoading] = useState(false);
  const slug = "seu-slug";

  const goNext = () => {
    if (step === 1) {
      if (password.length < 6) return toast.error("Senha muito curta.");
      if (password !== password2) return toast.error("As senhas não conferem.");
    }
    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      setStep((s) => s + 1);
    }, 400);
  };

  return (
    <div className="min-h-screen bg-secondary">
      <header className="px-4 py-4 border-b border-border bg-background">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-primary grid place-items-center">
            <Stethoscope className="h-5 w-5 text-primary-foreground" />
          </div>
          <span className="font-bold text-lg text-foreground">DoctFlow</span>
        </div>
      </header>

      <main className="mx-auto max-w-lg px-4 py-8">
        <div className="mb-6">
          <div className="flex justify-between text-xs text-muted-foreground mb-2">
            <span>Passo {step} de 3</span>
            <span>{Math.round((step / 3) * 100)}%</span>
          </div>
          <Progress value={(step / 3) * 100} className="h-2" />
        </div>

        <div className="bg-background border border-border rounded-2xl p-6">
          {step === 1 && (
            <>
              <h1 className="text-xl font-bold text-foreground">Defina sua senha</h1>
              <p className="mt-1 text-sm text-muted-foreground">
                Escolha uma senha segura para acessar sua conta.
              </p>
              <div className="mt-5 space-y-4">
                <div className="space-y-1.5">
                  <Label htmlFor="pw">Nova senha</Label>
                  <Input id="pw" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="pw2">Confirme a senha</Label>
                  <Input id="pw2" type="password" value={password2} onChange={(e) => setPassword2(e.target.value)} />
                </div>
              </div>
            </>
          )}

          {step === 2 && (
            <>
              <h1 className="text-xl font-bold text-foreground">Horários de atendimento</h1>
              <p className="mt-1 text-sm text-muted-foreground">
                Configure os períodos de cada dia. Você pode ajustar depois.
              </p>
              <div className="mt-5">
                <WeeklySchedule value={hours} onChange={setHours} />
              </div>
            </>
          )}

          {step === 3 && (
            <>
              <div className="text-center py-4">
                <div className="mx-auto h-16 w-16 rounded-full bg-success/10 grid place-items-center mb-3">
                  <Check className="h-9 w-9 text-success" />
                </div>
                <h1 className="text-xl font-bold text-foreground">Tudo pronto!</h1>
                <p className="mt-2 text-sm text-muted-foreground">
                  Compartilhe seu link para começar a receber agendamentos.
                </p>
              </div>
              <div className="mt-4 flex items-center gap-2 rounded-lg border border-border bg-secondary p-3">
                <code className="flex-1 text-sm text-foreground truncate">doctflow.com/d/{slug}</code>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => {
                    navigator.clipboard?.writeText(`doctflow.com/d/${slug}`);
                    toast.success("Link copiado!");
                  }}
                >
                  <Copy className="h-4 w-4" />
                </Button>
              </div>
            </>
          )}

          <div className="mt-6 flex gap-2">
            {step > 1 && step < 3 && (
              <Button variant="outline" onClick={() => setStep((s) => s - 1)}>
                Voltar
              </Button>
            )}
            {step < 3 && (
              <Button className="flex-1 h-11" onClick={goNext} disabled={loading}>
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Continuar"}
              </Button>
            )}
            {step === 3 && (
              <Button
                className="w-full h-11 bg-accent text-accent-foreground hover:bg-accent/90"
                onClick={() => navigate({ to: "/dashboard" })}
              >
                Ir para o dashboard
              </Button>
            )}
          </div>
        </div>

        <p className="text-center mt-6">
          <Link to="/login" className="text-xs text-muted-foreground hover:text-foreground">
            ← Voltar para o login
          </Link>
        </p>
      </main>
    </div>
  );
}
