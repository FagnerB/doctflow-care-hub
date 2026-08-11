import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Calendar } from "@/components/ui/calendar";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { CalendarOff, Loader2, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { EmptyState } from "@/components/EmptyState";
import { getErrorMessage } from "@/lib/api-client";
import { useCreateException, useDeleteException, useExceptions } from "@/hooks/use-exceptions";

export const Route = createFileRoute("/dashboard/exceptions")({
  head: () => ({
    meta: [{ title: "Bloqueios — DoctFlow" }],
  }),
  component: ExceptionsPage,
});

function ExceptionsPage() {
  const exceptionsQuery = useExceptions();
  const createException = useCreateException();
  const deleteException = useDeleteException();

  const [open, setOpen] = useState(false);
  const [date, setDate] = useState<Date | undefined>(new Date());
  const [fullDay, setFullDay] = useState(true);
  const [startTime, setStartTime] = useState("09:00");
  const [endTime, setEndTime] = useState("12:00");
  const [reason, setReason] = useState("");

  const exceptions = exceptionsQuery.data ?? [];

  const submit = () => {
    if (!date) return toast.error("Escolha uma data.");
    if (!fullDay && startTime >= endTime) return toast.error("O horário final precisa ser depois do inicial.");

    createException.mutate(
      {
        exception_date: format(date, "yyyy-MM-dd"),
        start_time: fullDay ? undefined : `${startTime}:00`,
        end_time: fullDay ? undefined : `${endTime}:00`,
        reason: reason || undefined,
      },
      {
        onSuccess: () => {
          toast.success("Bloqueio criado.");
          setOpen(false);
          setReason("");
        },
        onError: (error) => toast.error(getErrorMessage(error)),
      },
    );
  };

  const remove = (id: string) => {
    deleteException.mutate(id, {
      onSuccess: () => toast.success("Bloqueio removido."),
      onError: (error) => toast.error(getErrorMessage(error)),
    });
  };

  return (
    <div className="p-4 md:p-6 max-w-3xl">
      <div className="flex items-center justify-between gap-2">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Bloqueios de agenda</h1>
          <p className="text-sm text-muted-foreground">Férias, feriados ou compromissos — dia inteiro ou só um período.</p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-1.5" /> Novo bloqueio
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Novo bloqueio</DialogTitle>
              <DialogDescription>Pacientes não conseguirão agendar neste período.</DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <Calendar
                mode="single"
                selected={date}
                onSelect={setDate}
                locale={ptBR}
                disabled={(d) => d < new Date(new Date().setHours(0, 0, 0, 0))}
                className="p-0 pointer-events-auto mx-auto"
              />
              <div className="flex items-center justify-between gap-4 p-3 rounded-lg border border-border">
                <div>
                  <div className="text-sm font-medium text-foreground">Dia inteiro</div>
                  <div className="text-xs text-muted-foreground">Desligue para bloquear só um horário.</div>
                </div>
                <Switch checked={fullDay} onCheckedChange={setFullDay} />
              </div>
              {!fullDay && (
                <div className="flex items-center gap-2">
                  <Input type="time" value={startTime} onChange={(e) => setStartTime(e.target.value)} className="h-10" />
                  <span className="text-muted-foreground text-sm">—</span>
                  <Input type="time" value={endTime} onChange={(e) => setEndTime(e.target.value)} className="h-10" />
                </div>
              )}
              <div className="space-y-1.5">
                <Label htmlFor="reason">Motivo (opcional)</Label>
                <Textarea id="reason" value={reason} onChange={(e) => setReason(e.target.value)} rows={2} placeholder="Férias, feriado..." />
              </div>
            </div>
            <DialogFooter>
              <Button className="w-full" onClick={submit} disabled={createException.isPending}>
                {createException.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Bloquear"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <div className="mt-6 bg-background border border-border rounded-xl">
        {exceptionsQuery.isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
          </div>
        ) : exceptions.length === 0 ? (
          <EmptyState icon={CalendarOff} title="Nenhum bloqueio cadastrado" description="Sua agenda está livre para os pacientes agendarem." />
        ) : (
          <ul className="divide-y divide-border">
            {exceptions.map((exception) => (
              <li key={exception.id} className="flex items-center justify-between gap-4 p-4">
                <div>
                  <div className="text-sm font-medium text-foreground">
                    {format(new Date(`${exception.exception_date}T00:00:00`), "dd 'de' MMMM 'de' yyyy", { locale: ptBR })}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {exception.start_time && exception.end_time
                      ? `${exception.start_time.slice(0, 5)} — ${exception.end_time.slice(0, 5)}`
                      : "Dia inteiro"}
                    {exception.reason ? ` · ${exception.reason}` : ""}
                  </div>
                </div>
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button size="icon" variant="ghost" aria-label="Remover bloqueio">
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>Remover este bloqueio?</AlertDialogTitle>
                      <AlertDialogDescription>
                        O horário volta a ficar disponível para agendamento imediatamente.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>Cancelar</AlertDialogCancel>
                      <AlertDialogAction onClick={() => remove(exception.id)}>Remover</AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
