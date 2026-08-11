import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2, ShieldAlert, Stethoscope } from "lucide-react";
import { toast } from "sonner";
import { useResetPassword } from "@/hooks/use-auth";
import { getErrorMessage } from "@/lib/api-client";
import { parseRecoveryTokenFromLocation } from "@/lib/auth-storage";

export const Route = createFileRoute("/reset-password")({
  head: () => ({
    meta: [
      { title: "Redefinir senha — DoctFlow" },
      { name: "description", content: "Defina uma nova senha para sua conta DoctFlow." },
    ],
  }),
  component: ResetPasswordPage,
});

function ResetPasswordPage() {
  const navigate = useNavigate();
  const resetPassword = useResetPassword();
  const [password, setPassword] = useState("");
  const [password2, setPassword2] = useState("");
  // undefined = ainda não verificou; null = verificou e não achou token.
  const [token, setToken] = useState<ReturnType<typeof parseRecoveryTokenFromLocation> | null | undefined>(
    undefined,
  );

  useEffect(() => {
    // Só roda no cliente: o link do Supabase chega como fragmento/query da URL,
    // que não existe durante o SSR.
    setToken(parseRecoveryTokenFromLocation());
  }, []);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (password.length < 8) {
      toast.error("A senha precisa ter no mínimo 8 caracteres.");
      return;
    }
    if (password !== password2) {
      toast.error("As senhas não conferem.");
      return;
    }
    if (!token) return;

    resetPassword.mutate(
      {
        new_password: password,
        access_token: token.accessToken,
        token_hash: token.tokenHash,
        type: token.type,
      },
      {
        onSuccess: () => {
          toast.success("Senha redefinida! Faça login com a nova senha.");
          navigate({ to: "/login" });
        },
        onError: (error) => toast.error(getErrorMessage(error)),
      },
    );
  };

  return (
    <div className="min-h-screen bg-secondary flex flex-col">
      <header className="px-4 py-4">
        <Link to="/" className="inline-flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-primary grid place-items-center">
            <Stethoscope className="h-5 w-5 text-primary-foreground" />
          </div>
          <span className="font-bold text-lg text-foreground">DoctFlow</span>
        </Link>
      </header>

      <main className="flex-1 flex items-center justify-center px-4 pb-8">
        <div className="w-full max-w-sm bg-background border border-border rounded-2xl p-6 shadow-sm">
          {token === null ? (
            <div className="text-center py-2">
              <div className="mx-auto h-14 w-14 rounded-full bg-destructive/10 grid place-items-center mb-4">
                <ShieldAlert className="h-7 w-7 text-destructive" />
              </div>
              <h1 className="text-xl font-bold text-foreground">Link inválido ou expirado</h1>
              <p className="mt-2 text-sm text-muted-foreground">
                Solicite um novo link de redefinição de senha.
              </p>
              <Link to="/forgot-password" className="mt-6 inline-block text-sm text-primary hover:underline">
                Solicitar novo link
              </Link>
            </div>
          ) : (
            <>
              <h1 className="text-2xl font-bold text-foreground">Nova senha</h1>
              <p className="mt-1 text-sm text-muted-foreground">Escolha uma senha com no mínimo 8 caracteres.</p>

              <form onSubmit={submit} className="mt-6 space-y-4">
                <div className="space-y-1.5">
                  <Label htmlFor="password">Nova senha</Label>
                  <Input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="new-password"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="password2">Confirme a senha</Label>
                  <Input
                    id="password2"
                    type="password"
                    value={password2}
                    onChange={(e) => setPassword2(e.target.value)}
                    autoComplete="new-password"
                  />
                </div>
                <Button type="submit" className="w-full h-11" disabled={resetPassword.isPending || token === undefined}>
                  {resetPassword.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Redefinir senha"}
                </Button>
              </form>
            </>
          )}
        </div>
      </main>
    </div>
  );
}
