import { createFileRoute, Link, Outlet, useRouterState, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { Calendar, CalendarOff, Users, Settings, LogOut, Stethoscope } from "lucide-react";
import { cn } from "@/lib/utils";
import { useLogout } from "@/hooks/use-auth";
import { hasAccessToken } from "@/lib/auth-storage";
import { useDoctorAppointments } from "@/hooks/use-appointments";
import { useUnseenAppointmentsCount } from "@/hooks/use-unseen-appointments";

export const Route = createFileRoute("/dashboard")({
  head: () => ({
    meta: [
      { title: "Dashboard — DoctFlow" },
      { name: "description", content: "Gerencie sua agenda e pacientes." },
    ],
  }),
  component: DashboardLayout,
});

function DashboardLayout() {
  const navigate = useNavigate();
  const logout = useLogout();
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  // Guarda de sessão client-side: sem token, não há por que renderizar o
  // dashboard (toda chamada à API voltaria 401). Roda em efeito porque
  // localStorage não existe durante o SSR — no servidor esta verificação
  // sempre passaria batido, e é o cliente, após montar, quem redireciona.
  useEffect(() => {
    if (!hasAccessToken()) navigate({ to: "/login" });
  }, [navigate]);

  // Badge de "nova consulta": consulta a agenda periodicamente e compara com
  // a quantidade já vista pelo médico (persistida em localStorage).
  const appointmentsQuery = useDoctorAppointments({ refetchInterval: 30_000 });
  const unseenCount = useUnseenAppointmentsCount(appointmentsQuery.data);

  const navItems = [
    { to: "/dashboard", label: "Agenda", icon: Calendar, exact: true, badge: unseenCount },
    { to: "/dashboard/patients", label: "Pacientes", icon: Users },
    { to: "/dashboard/exceptions", label: "Bloqueios", icon: CalendarOff },
    { to: "/dashboard/settings", label: "Configurações", icon: Settings },
  ] as const;

  const isActive = (to: string, exact?: boolean) =>
    exact ? pathname === to : pathname.startsWith(to);

  return (
    <div className="min-h-screen bg-secondary flex flex-col md:flex-row">
      {/* Sidebar desktop */}
      <aside className="hidden md:flex md:w-64 flex-col bg-background border-r border-border">
        <div className="h-16 flex items-center gap-2 px-6 border-b border-border">
          <div className="h-8 w-8 rounded-lg bg-primary grid place-items-center">
            <Stethoscope className="h-5 w-5 text-primary-foreground" />
          </div>
          <span className="font-bold text-lg text-foreground">DoctFlow</span>
        </div>
        <nav className="flex-1 p-3 space-y-1">
          {navItems.map((item) => {
            const active = isActive(item.to, "exact" in item ? item.exact : false);
            return (
              <Link
                key={item.to}
                to={item.to}
                className={cn(
                  "flex items-center justify-between gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                  active
                    ? "bg-primary text-primary-foreground"
                    : "text-foreground hover:bg-secondary",
                )}
              >
                <span className="flex items-center gap-3">
                  <item.icon className="h-4 w-4" />
                  {item.label}
                </span>
                {"badge" in item && item.badge > 0 && (
                  <span className="min-w-5 h-5 px-1.5 rounded-full bg-accent text-accent-foreground text-[11px] font-bold grid place-items-center">
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>
        <div className="p-3 border-t border-border">
          <button
            onClick={logout}
            className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-foreground hover:bg-secondary w-full"
          >
            <LogOut className="h-4 w-4" /> Sair
          </button>
        </div>
      </aside>

      {/* Header mobile */}
      <header className="md:hidden h-14 bg-background border-b border-border flex items-center justify-between px-4">
        <div className="flex items-center gap-2">
          <div className="h-7 w-7 rounded-md bg-primary grid place-items-center">
            <Stethoscope className="h-4 w-4 text-primary-foreground" />
          </div>
          <span className="font-bold text-foreground">DoctFlow</span>
        </div>
        <button onClick={logout} aria-label="Sair" className="p-2 -mr-2 text-muted-foreground">
          <LogOut className="h-5 w-5" />
        </button>
      </header>

      {/* Conteúdo */}
      <main className="flex-1 pb-20 md:pb-0 min-w-0">
        <Outlet />
      </main>

      {/* Bottom nav mobile */}
      <nav className="md:hidden fixed bottom-0 inset-x-0 bg-background border-t border-border z-20">
        <div className="grid grid-cols-4">
          {navItems.map((item) => {
            const active = isActive(item.to, "exact" in item ? item.exact : false);
            return (
              <Link
                key={item.to}
                to={item.to}
                className={cn(
                  "relative flex flex-col items-center justify-center gap-1 py-2.5 text-xs font-medium",
                  active ? "text-primary" : "text-muted-foreground",
                )}
              >
                <item.icon className="h-5 w-5" />
                {item.label}
                {"badge" in item && item.badge > 0 && (
                  <span className="absolute top-1 right-1/4 min-w-4 h-4 px-1 rounded-full bg-accent text-accent-foreground text-[10px] font-bold grid place-items-center">
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </div>
      </nav>
    </div>
  );
}
