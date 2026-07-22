import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Plus, Trash2 } from "lucide-react";

// Horários por dia da semana (0 = domingo … 6 = sábado)
export interface TimeRange {
  start: string; // "HH:mm"
  end: string;
}
export type WeeklyHours = Record<number, TimeRange[]>;

const dayLabels: Record<number, string> = {
  0: "Domingo",
  1: "Segunda",
  2: "Terça",
  3: "Quarta",
  4: "Quinta",
  5: "Sexta",
  6: "Sábado",
};

export function defaultWeeklyHours(): WeeklyHours {
  const wh: WeeklyHours = {};
  for (let d = 0; d < 7; d++) {
    wh[d] = d >= 1 && d <= 5 ? [{ start: "08:00", end: "12:00" }, { start: "14:00", end: "18:00" }] : [];
  }
  return wh;
}

interface Props {
  value: WeeklyHours;
  onChange: (v: WeeklyHours) => void;
}

export function WeeklySchedule({ value, onChange }: Props) {
  const update = (day: number, ranges: TimeRange[]) => {
    onChange({ ...value, [day]: ranges });
  };

  return (
    <div className="space-y-4">
      {[1, 2, 3, 4, 5, 6, 0].map((day) => {
        const ranges = value[day] ?? [];
        return (
          <div key={day} className="border border-border rounded-lg p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-semibold text-foreground">{dayLabels[day]}</span>
              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={() => update(day, [...ranges, { start: "09:00", end: "12:00" }])}
              >
                <Plus className="h-4 w-4 mr-1" /> Adicionar período
              </Button>
            </div>
            {ranges.length === 0 ? (
              <p className="text-xs text-muted-foreground">Sem atendimento neste dia.</p>
            ) : (
              <div className="space-y-2">
                {ranges.map((r, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <Input
                      type="time"
                      value={r.start}
                      onChange={(e) => {
                        const nr = [...ranges];
                        nr[i] = { ...r, start: e.target.value };
                        update(day, nr);
                      }}
                      className="h-10"
                    />
                    <span className="text-muted-foreground text-sm">—</span>
                    <Input
                      type="time"
                      value={r.end}
                      onChange={(e) => {
                        const nr = [...ranges];
                        nr[i] = { ...r, end: e.target.value };
                        update(day, nr);
                      }}
                      className="h-10"
                    />
                    <Button
                      type="button"
                      size="icon"
                      variant="ghost"
                      onClick={() => update(day, ranges.filter((_, idx) => idx !== i))}
                      aria-label="Remover período"
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
