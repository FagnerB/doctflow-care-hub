import { createFileRoute, Link } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  CalendarCheck,
  Instagram,
  Link2,
  MessageCircle,
  Check,
  Sparkles,
  Stethoscope,
} from "lucide-react";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "DoctFlow — Seu consultório, online." },
      {
        name: "description",
        content:
          "Agendamento médico que converte seguidores em pacientes. Pacientes agendam em 30 segundos pelo link da sua bio.",
      },
      { property: "og:title", content: "DoctFlow — Seu consultório, online." },
      {
        property: "og:description",
        content: "Pacientes agendam em 30 segundos direto do Instagram.",
      },
    ],
  }),
  component: Landing,
});

function Landing() {
  return (
    <div className="min-h-screen bg-background">
      {/* Nav */}
      <header className="border-b border-border bg-background/80 backdrop-blur sticky top-0 z-30">
        <div className="mx-auto max-w-6xl px-4 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-primary grid place-items-center">
              <Stethoscope className="h-5 w-5 text-primary-foreground" />
            </div>
            <span className="font-bold text-lg text-foreground">DoctFlow</span>
          </Link>
          <nav className="flex items-center gap-2">
            <Link to="/login">
              <Button variant="ghost" size="sm">Entrar</Button>
            </Link>
            <Link to="/login">
              <Button size="sm" className="bg-accent text-accent-foreground hover:bg-accent/90">
                Começar grátis
              </Button>
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section className="mx-auto max-w-6xl px-4 py-12 md:py-20 grid md:grid-cols-2 gap-10 items-center">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full bg-secondary px-3 py-1 text-xs font-medium text-primary mb-4">
            <Sparkles className="h-3.5 w-3.5" /> Novo · 30 dias grátis
          </div>
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-foreground leading-tight">
            Agendamento médico que <span className="text-primary">converte seguidores</span> em pacientes.
          </h1>
          <p className="mt-4 text-lg text-muted-foreground">
            Médicos usam o DoctFlow no link da bio do Instagram.
            Pacientes agendam em 30 segundos, sem baixar app.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link to="/login">
              <Button size="lg" className="bg-accent text-accent-foreground hover:bg-accent/90 h-12 px-6 text-base">
                Começar grátis por 30 dias
              </Button>
            </Link>
            <Link to="/d/$slug" params={{ slug: "dr-silva" }}>
              <Button size="lg" variant="outline" className="h-12 px-6 text-base">
                Ver demo
              </Button>
            </Link>
          </div>
          <ul className="mt-6 flex flex-wrap gap-x-6 gap-y-2 text-sm text-muted-foreground">
            <li className="flex items-center gap-1.5"><Check className="h-4 w-4 text-success" /> Sem cartão de crédito</li>
            <li className="flex items-center gap-1.5"><Check className="h-4 w-4 text-success" /> Lembretes por WhatsApp</li>
            <li className="flex items-center gap-1.5"><Check className="h-4 w-4 text-success" /> Cancele quando quiser</li>
          </ul>
        </div>

        {/* Mockup do celular */}
        <div className="flex justify-center">
          <PhoneMockup />
        </div>
      </section>

      {/* Como funciona */}
      <section className="bg-secondary py-16 md:py-20">
        <div className="mx-auto max-w-6xl px-4">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-foreground">Como funciona</h2>
            <p className="mt-2 text-muted-foreground">Em 3 passos você já está recebendo agendamentos.</p>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            <Step n={1} icon={CalendarCheck} title="Médico configura horários" desc="Defina os dias e horários que quer atender. Leva 2 minutos." />
            <Step n={2} icon={Instagram} title="Coloca o link na bio" desc="Um link único (doctflow.com/d/seu-nome) direto para agendamento." />
            <Step n={3} icon={MessageCircle} title="Paciente agenda sozinho" desc="Sem ligação, sem WhatsApp travando. Confirmação instantânea." />
          </div>
        </div>
      </section>

      {/* Fase beta — nada de depoimento ou número inventado aqui */}
      <section className="py-16 md:py-20">
        <div className="mx-auto max-w-3xl px-4 text-center">
          <div className="mx-auto h-16 w-16 rounded-full bg-primary/10 grid place-items-center mb-6">
            <Sparkles className="h-7 w-7 text-primary" />
          </div>
          <h2 className="text-2xl md:text-3xl font-medium text-foreground leading-snug">
            Estamos em fase beta
          </h2>
          <p className="mt-4 text-muted-foreground max-w-xl mx-auto">
            O DoctFlow está sendo construído junto com os primeiros profissionais que topam testar.
            Ainda não temos números de resultado pra mostrar — preferimos isso a inventar um.
          </p>
        </div>
      </section>

      {/* Preços */}
      <section className="bg-secondary py-16 md:py-20">
        <div className="mx-auto max-w-5xl px-4">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-foreground">Planos simples</h2>
            <p className="mt-2 text-muted-foreground">Cancele quando quiser. Sem taxas escondidas.</p>
          </div>
          <div className="grid md:grid-cols-2 gap-6 max-w-3xl mx-auto">
            <PricingCard
              name="Básico"
              price="49"
              features={["Agendamentos ilimitados", "Link personalizado", "Lembretes por email", "1 profissional"]}
            />
            <PricingCard
              name="Pro"
              price="99"
              highlight
              features={[
                "Tudo do Básico",
                "Lembretes por WhatsApp",
                "Confirmação automática",
                "Relatórios e histórico",
                "Suporte prioritário",
              ]}
            />
          </div>
        </div>
      </section>

      {/* CTA final */}
      <section className="py-16 md:py-20">
        <div className="mx-auto max-w-3xl px-4 text-center">
          <h2 className="text-3xl md:text-4xl font-bold text-foreground">
            Pronto para lotar sua agenda?
          </h2>
          <p className="mt-3 text-muted-foreground">
            Comece grátis. Sem cartão de crédito.
          </p>
          <div className="mt-6">
            <Link to="/login">
              <Button size="lg" className="bg-accent text-accent-foreground hover:bg-accent/90 h-12 px-8 text-base">
                Começar grátis por 30 dias
              </Button>
            </Link>
          </div>
        </div>
      </section>

      <footer className="border-t border-border py-8">
        <div className="mx-auto max-w-6xl px-4 flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-muted-foreground">
          <div className="flex items-center gap-2">
            <div className="h-6 w-6 rounded-md bg-primary grid place-items-center">
              <Stethoscope className="h-4 w-4 text-primary-foreground" />
            </div>
            <span>© {new Date().getFullYear()} DoctFlow</span>
          </div>
          <div className="flex gap-6">
            <a href="#" className="hover:text-foreground">Termos</a>
            <a href="#" className="hover:text-foreground">Privacidade</a>
            <a href="#" className="hover:text-foreground">Contato</a>
          </div>
        </div>
      </footer>
    </div>
  );
}

function Step({ n, icon: Icon, title, desc }: { n: number; icon: typeof CalendarCheck; title: string; desc: string }) {
  return (
    <Card className="border-border">
      <CardContent className="pt-6">
        <div className="flex items-start gap-4">
          <div className="shrink-0 h-11 w-11 rounded-lg bg-primary text-primary-foreground grid place-items-center font-bold">
            {n}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <Icon className="h-5 w-5 text-primary" />
              <h3 className="font-semibold text-foreground">{title}</h3>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">{desc}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function PricingCard({
  name,
  price,
  features,
  highlight,
}: {
  name: string;
  price: string;
  features: string[];
  highlight?: boolean;
}) {
  return (
    <div
      className={
        "rounded-2xl border p-6 bg-background " +
        (highlight ? "border-primary ring-2 ring-primary/20 shadow-lg relative" : "border-border")
      }
    >
      {highlight && (
        <span className="absolute -top-3 left-6 rounded-full bg-accent text-accent-foreground text-xs font-semibold px-3 py-1">
          Mais popular
        </span>
      )}
      <h3 className="text-lg font-semibold text-foreground">{name}</h3>
      <div className="mt-3 flex items-baseline gap-1">
        <span className="text-4xl font-bold text-foreground">R${price}</span>
        <span className="text-muted-foreground">/mês</span>
      </div>
      <ul className="mt-6 space-y-3">
        {features.map((f) => (
          <li key={f} className="flex items-start gap-2 text-sm">
            <Check className="h-4 w-4 text-success mt-0.5 shrink-0" />
            <span className="text-foreground">{f}</span>
          </li>
        ))}
      </ul>
      <Link to="/login" className="block mt-6">
        <Button
          className={
            "w-full " +
            (highlight
              ? "bg-accent text-accent-foreground hover:bg-accent/90"
              : "")
          }
          variant={highlight ? "default" : "outline"}
        >
          Começar grátis
        </Button>
      </Link>
    </div>
  );
}

function PhoneMockup() {
  return (
    <div className="relative">
      <div className="w-[280px] h-[560px] rounded-[2.5rem] bg-foreground p-3 shadow-2xl">
        <div className="w-full h-full rounded-[2rem] bg-background overflow-hidden relative">
          <div className="absolute top-0 inset-x-0 h-6 flex justify-center">
            <div className="w-24 h-5 bg-foreground rounded-b-2xl" />
          </div>
          <div className="pt-10 px-4 pb-4 h-full flex flex-col">
            <div className="flex items-center gap-3">
              <div className="h-12 w-12 rounded-full bg-primary/20 grid place-items-center text-2xl">🩺</div>
              <div>
                <div className="text-sm font-semibold text-foreground">Dr. Rafael Silva</div>
                <div className="text-[11px] text-muted-foreground">Cardiologia</div>
              </div>
            </div>
            <div className="mt-4 text-xs font-semibold text-foreground">Escolha um horário</div>
            <div className="mt-2 grid grid-cols-3 gap-1.5">
              {["08:00", "08:30", "09:00", "09:30", "10:00", "10:30"].map((h, i) => (
                <div
                  key={h}
                  className={
                    "h-8 rounded-md text-[11px] font-medium grid place-items-center " +
                    (i === 2
                      ? "bg-primary text-primary-foreground"
                      : "bg-secondary text-foreground")
                  }
                >
                  {h}
                </div>
              ))}
            </div>
            <div className="mt-auto">
              <div className="h-10 rounded-lg bg-accent text-accent-foreground grid place-items-center text-xs font-semibold">
                Confirmar agendamento
              </div>
            </div>
          </div>
        </div>
      </div>
      <div className="absolute -bottom-4 -right-4 bg-background border border-border rounded-xl p-3 shadow-lg flex items-center gap-2">
        <Link2 className="h-4 w-4 text-primary" />
        <span className="text-xs font-medium text-foreground">doctflow.com/d/dr-silva</span>
      </div>
    </div>
  );
}
