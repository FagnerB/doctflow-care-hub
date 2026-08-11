import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { toast } from "sonner";
import { Check, Copy, Loader2, ShieldAlert, Stethoscope } from "lucide-react";
import { WeeklySchedule, type WeeklyHours, defaultWeeklyHours } from "@/components/WeeklySchedule";
import { useLogin, useResetPassword } from "@/hooks/use-auth";
import { useDoctorProfile, useUpdateDoctorProfile } from "@/hooks/use-doctor";
import { getErrorMessage } from "@/lib/api-client";
import { decodeJwtPayload, parseRecoveryTokenFromLocation } from "@/lib/auth-storage";
import { weeklyHoursToWorkingHours, workingHoursToWeeklyHours } from "@/lib/schedule-mapping";

export const Route = createFileRoute("/setup")({
  head: () => ({
    meta: [
      { title: "Primeiro acesso — DoctFlow" },
      { name: "description", content: "Configure sua conta em 3 passos." },
    ],
  }),
  component: SetupPage,
});

// Fluxo: o médico chega aqui pelo link de convite do e-mail (mesmo mecanismo
// do "esqueci minha senha" — access_token/token_hash na URL, type=invite).
// Passo 1 define a senha nova no Supabase e, com ela, faz login na NOSSA API
// (o access_token do Supabase não serve de Bearer para os endpoints do
// DoctFlow — só o JWT emitido por /auth/login serve). A partir daí os passos
// 2 e 3 já podem chamar /doctors/me normalmente.

function SetupPage() {
  const navigate = useNavigate();
  const resetPassword = useResetPassword();
  const login = useLogin();
  const doctorProfile = useDoctorProfile();
  const updateProfile = useUpdateDoctorProfile();

  const [step, setStep] = useState(1);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [password2, setPassword2] = useState("");
  const [hours, setHours] = useState<WeeklyHours>(defaultWeeklyHours());
  const [slug, setSlug] = useState("");
  const [token, setToken] = useState<ReturnType<typeof parseRecoveryTokenFromLocation> | null | undefined>(
    undefined,
  );

  useEffect(() => {
    const found = parseRecoveryTokenFromLocation();
    setToken(found);
    if (found?.accessToken) {
      const claims = decodeJwtPayload(found.accessToken);
      const claimEmail = claims?.email;
      if (typeof claimEmail === "string") setEmail(claimEmail);
    }
  }, []);

  const submitStep1 = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return toast.error("Informe seu email.");
    if (password.length < 8) return toast.error("A senha precisa ter no mínimo 8 caracteres.");
    if (password !== password2) return toast.error("As senhas não conferem.");
    if (!token) return;

    resetPassword.mutate(
      { new_password: password, access_token: token.accessToken, token_hash: token.tokenHash, type: token.type },
      {
        onSuccess: () => {
          login.mutate(
            { email, password },
            {
              onSuccess: async () => {
                const profile = await doctorProfile.refetch();
                if (profile.data) {
                  setHours(workingHoursToWeeklyHours(profile.data.config_json.working_hours));
                  setSlug(profile.data.slug);
                }
                setStep(2);
              },
              onError: (error) =>
                toast.error(`Senha definida, mas o login falhou: ${getErrorMessage(error)}. Tente entrar manualmente.`),
            },
          );
        },
        onError: (error) => toast.error(getErrorMessage(error)),
      },
    );
  };

  const submitStep2 = () => {
    if (!doctorProfile.data) return;
    updateProfile.mutate(
      { config_json: { ...doctorProfile.data.config_json, working_hours: weeklyHoursToWorkingHours(hours) } },
      {
        onSuccess: () => setStep(3),
        onError: (error) => toast.error(getErrorMessage(error)),
      },
    );
  };

  const publicLink = typeof window !== "undefined" ? `${window.location.origin}/d/${slug}` : `/d/${slug}`;

  if (token === null) {
    return (
      <div className="min-h-screen bg-secondary flex items-center justify-center px-4">
        <div className="w-full max-w-sm bg-background border border-border rounded-2xl p-6 text-center">
          <div className="mx-auto h-14 w-14 rounded-full bg-destructive/10 grid place-items-center mb-4">
            <ShieldAlert className="h-7 w-7 text-destructive" />
          </div>
          <h1 className="text-xl font-bold text-foreground">Link de convite inválido ou expirado</h1>
          <p className="mt-2 text-sm text-muted-foreground">Fale com quem administra sua conta para receber um novo convite.</p>
          <Link to="/login" className="mt-6 inline-block text-sm text-primary hover:underline">
            ← Voltar para o login
          </Link>
        </div>
      </div>
    );
  }

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
            <form onSubmit={submitStep1}>
              <h1 className="text-xl font-bold text-foreground">Confirme seu email e defina sua senha</h1>
              <p className="mt-1 text-sm text-muted-foreground">
                Escolha uma senha segura para acessar sua conta.
              </p>
              <div className="mt-5 space-y-4">
                <div className="space-y-1.5">
                  <Label htmlFor="email">Email</Label>
                  <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="pw">Nova senha</Label>
                  <Input id="pw" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="pw2">Confirme a senha</Label>
                  <Input id="pw2" type="password" value={password2} onChange={(e) => setPassword2(e.target.value)} />
                </div>
              </div>
              <Button
                type="submit"
                className="w-full h-11 mt-6"
                disabled={resetPassword.isPending || login.isPending || doctorProfile.isFetching}
              >
                {resetPassword.isPending || login.isPending || doctorProfile.isFetching ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  "Continuar"
                )}
              </Button>
            </form>
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
              <div className="mt-6 flex gap-2">
                <Button variant="outline" onClick={() => setStep(1)}>Voltar</Button>
                <Button className="flex-1 h-11" onClick={submitStep2} disabled={updateProfile.isPending}>
                  {updateProfile.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Continuar"}
                </Button>
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
                <code className="flex-1 text-sm text-foreground truncate">{publicLink}</code>
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
              </div>
              <Button
                className="w-full h-11 mt-6 bg-accent text-accent-foreground hover:bg-accent/90"
                onClick={() => navigate({ to: "/dashboard" })}
              >
                Ir para o dashboard
              </Button>
            </>
          )}
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
