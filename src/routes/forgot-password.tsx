import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2, MailCheck } from "lucide-react";
import { toast } from "sonner";
import { useForgotPassword } from "@/hooks/use-auth";
import { getErrorMessage } from "@/lib/api-client";

export const Route = createFileRoute("/forgot-password")({
  head: () => ({
    meta: [
      { title: "Esqueci minha senha — DoctFlow" },
      { name: "description", content: "Recupere o acesso à sua conta DoctFlow." },
    ],
  }),
  component: ForgotPasswordPage,
});

function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const forgotPassword = useForgotPassword();

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) {
      toast.error("Informe seu email.");
      return;
    }
    forgotPassword.mutate(email, {
      // O backend sempre responde com sucesso genérico (não revela se o email
      // existe), então aqui só tratamos falha de rede/servidor como erro real.
      onSuccess: () => setSent(true),
      onError: (error) => toast.error(getErrorMessage(error)),
    });
  };

  return (
    <div className="min-h-screen bg-secondary flex flex-col">
      <header className="px-4 py-4">
        <Link to="/" className="inline-flex items-center gap-2">
          <img src="/logo-mark.svg" alt="DoctFlow" className="h-8 w-8 rounded-lg" />
          <span className="font-bold text-lg text-foreground">DoctFlow</span>
        </Link>
      </header>

      <main className="flex-1 flex items-center justify-center px-4 pb-8">
        <div className="w-full max-w-sm bg-background border border-border rounded-2xl p-6 shadow-sm">
          {sent ? (
            <div className="text-center py-2">
              <div className="mx-auto h-14 w-14 rounded-full bg-success/10 grid place-items-center mb-4">
                <MailCheck className="h-7 w-7 text-success" />
              </div>
              <h1 className="text-xl font-bold text-foreground">Verifique seu email</h1>
              <p className="mt-2 text-sm text-muted-foreground">
                Se houver uma conta com o email <strong className="text-foreground">{email}</strong>, enviamos um
                link para redefinir sua senha.
              </p>
              <Link to="/login" className="mt-6 inline-block text-sm text-primary hover:underline">
                ← Voltar para o login
              </Link>
            </div>
          ) : (
            <>
              <h1 className="text-2xl font-bold text-foreground">Esqueci minha senha</h1>
              <p className="mt-1 text-sm text-muted-foreground">
                Informe seu email e enviaremos um link de redefinição.
              </p>

              <form onSubmit={submit} className="mt-6 space-y-4">
                <div className="space-y-1.5">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="voce@email.com"
                    autoComplete="email"
                  />
                </div>
                <Button type="submit" className="w-full h-11" disabled={forgotPassword.isPending}>
                  {forgotPassword.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Enviar link"}
                </Button>
              </form>

              <p className="mt-6 text-center text-xs text-muted-foreground">
                <Link to="/login" className="hover:text-foreground">← Voltar para o login</Link>
              </p>
            </>
          )}
        </div>
      </main>
    </div>
  );
}
