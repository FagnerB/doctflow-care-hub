import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { Input } from "@/components/ui/input";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Search, User } from "lucide-react";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { mockAppointments, mockPatients, statusLabels, type Patient } from "@/lib/mock-data";
import { EmptyState } from "@/components/EmptyState";

export const Route = createFileRoute("/dashboard/patients")({
  component: PatientsPage,
});

function PatientsPage() {
  const [q, setQ] = useState("");
  const [selected, setSelected] = useState<Patient | null>(null);

  const filtered = useMemo(() => {
    const term = q.toLowerCase().trim();
    if (!term) return mockPatients;
    return mockPatients.filter(
      (p) =>
        p.name.toLowerCase().includes(term) || p.phone.replace(/\D/g, "").includes(term.replace(/\D/g, "")),
    );
  }, [q]);

  const historyOf = (patient: Patient) =>
    mockAppointments
      .filter((a) => a.patientName === patient.name)
      .sort((a, b) => +b.start - +a.start);

  return (
    <div className="p-4 md:p-6">
      <h1 className="text-2xl font-bold text-foreground">Pacientes</h1>
      <p className="text-sm text-muted-foreground">
        {mockPatients.length} pacientes cadastrados
      </p>

      <div className="mt-4 relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Buscar por nome ou telefone"
          className="pl-9 h-11"
        />
      </div>

      <div className="mt-4 bg-background border border-border rounded-xl overflow-hidden">
        {filtered.length === 0 ? (
          <EmptyState icon={User} title="Nenhum paciente encontrado" />
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nome</TableHead>
                  <TableHead>Telefone</TableHead>
                  <TableHead>Última consulta</TableHead>
                  <TableHead className="text-right">Total</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((p) => (
                  <TableRow
                    key={p.id}
                    className="cursor-pointer"
                    onClick={() => setSelected(p)}
                  >
                    <TableCell className="font-medium text-foreground">{p.name}</TableCell>
                    <TableCell className="text-muted-foreground">{p.phone}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {p.lastVisit ? format(p.lastVisit, "dd/MM/yyyy") : "—"}
                    </TableCell>
                    <TableCell className="text-right">
                      <Badge variant="secondary">{p.totalVisits}</Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </div>

      <Sheet open={!!selected} onOpenChange={(o) => !o && setSelected(null)}>
        <SheetContent className="w-full sm:max-w-md overflow-y-auto">
          {selected && (
            <>
              <SheetHeader>
                <SheetTitle>{selected.name}</SheetTitle>
                <SheetDescription>{selected.phone}</SheetDescription>
              </SheetHeader>
              <div className="mt-6">
                <h3 className="text-sm font-semibold text-foreground mb-2">Histórico</h3>
                {historyOf(selected).length === 0 ? (
                  <p className="text-sm text-muted-foreground">Sem consultas registradas.</p>
                ) : (
                  <ul className="space-y-2">
                    {historyOf(selected).map((a) => (
                      <li
                        key={a.id}
                        className="rounded-lg border border-border p-3 flex items-center justify-between"
                      >
                        <div>
                          <div className="text-sm font-medium text-foreground">
                            {format(a.start, "dd 'de' MMM yyyy", { locale: ptBR })}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {format(a.start, "HH:mm")}
                          </div>
                        </div>
                        <Badge variant="outline">{statusLabels[a.status]}</Badge>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}
