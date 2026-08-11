// Conversão entre a forma que o backend usa para working_hours (chave = nome
// do dia em inglês, ex. "monday") e a forma que o componente WeeklySchedule
// já usa no frontend (chave = índice numérico, 0 = domingo).
import type { TimeRange, WeeklyHours } from "@/components/WeeklySchedule";
import type { DayName, TimeWindow } from "./api-types";

// Índice (getDay()) -> nome do dia no backend.
const DAY_NAME_BY_INDEX: Record<number, DayName> = {
  0: "sunday",
  1: "monday",
  2: "tuesday",
  3: "wednesday",
  4: "thursday",
  5: "friday",
  6: "saturday",
};

const ALL_DAY_NAMES: DayName[] = [
  "monday",
  "tuesday",
  "wednesday",
  "thursday",
  "friday",
  "saturday",
  "sunday",
];

export function workingHoursToWeeklyHours(workingHours: Record<DayName, TimeWindow[]>): WeeklyHours {
  const result: WeeklyHours = {};
  for (const [indexStr, dayName] of Object.entries(DAY_NAME_BY_INDEX)) {
    result[Number(indexStr)] = (workingHours[dayName] ?? []).map((w) => ({ start: w.start, end: w.end }));
  }
  return result;
}

export function weeklyHoursToWorkingHours(weeklyHours: WeeklyHours): Record<DayName, TimeWindow[]> {
  const result = {} as Record<DayName, TimeWindow[]>;
  for (const dayName of ALL_DAY_NAMES) {
    result[dayName] = [];
  }
  for (const [indexStr, ranges] of Object.entries(weeklyHours)) {
    const dayName = DAY_NAME_BY_INDEX[Number(indexStr)];
    if (dayName) result[dayName] = ranges.map((r: TimeRange) => ({ start: r.start, end: r.end }));
  }
  return result;
}

/** Índices de dia da semana (0=domingo) em que o médico não atende nenhum horário. */
export function weekdaysWithoutHours(workingHours: Record<DayName, TimeWindow[]>): number[] {
  const withoutHours: number[] = [];
  for (const [indexStr, dayName] of Object.entries(DAY_NAME_BY_INDEX)) {
    if ((workingHours[dayName] ?? []).length === 0) withoutHours.push(Number(indexStr));
  }
  return withoutHours;
}
