import { format } from "date-fns";
import { cn } from "@/lib/utils";

interface Props {
  slots: Date[];
  selected?: Date | null;
  onSelect: (d: Date) => void;
  disabled?: Date[];
}

// Grid de horários com estados selected / disabled. Touch-friendly (min 44px).
export function TimeSlotGrid({ slots, selected, onSelect, disabled = [] }: Props) {
  if (slots.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-2">Nenhum horário disponível.</p>
    );
  }

  return (
    <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
      {slots.map((slot) => {
        const isSelected = selected?.getTime() === slot.getTime();
        const isDisabled = disabled.some((d) => d.getTime() === slot.getTime());
        return (
          <button
            key={slot.toISOString()}
            type="button"
            disabled={isDisabled}
            onClick={() => onSelect(slot)}
            className={cn(
              "h-11 rounded-lg border text-sm font-medium transition-colors",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              isSelected
                ? "bg-primary text-primary-foreground border-primary"
                : "bg-background hover:bg-secondary border-border text-foreground",
              isDisabled && "opacity-40 cursor-not-allowed hover:bg-background",
            )}
            aria-label={`Horário ${format(slot, "HH:mm")}`}
            aria-pressed={isSelected}
          >
            {format(slot, "HH:mm")}
          </button>
        );
      })}
    </div>
  );
}
