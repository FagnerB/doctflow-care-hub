// Pacientes do médico logado, derivados das consultas — o backend não tem
// endpoint de listagem dedicada (só GET /patients/{id} por id específico),
// mas cada consulta já traz o paciente embutido. Compartilhado entre a lista
// de pacientes (dashboard.patients.tsx) e a busca do modal de novo agendamento.
import { useMemo } from "react";
import type { Appointment, Patient } from "@/lib/api-types";
import { useDoctorAppointments } from "./use-appointments";

export interface PatientSummary {
  patient: Patient;
  lastVisit: string;
  totalVisits: number;
}

function derivePatients(appointments: Appointment[]): PatientSummary[] {
  const byId = new Map<string, PatientSummary>();
  for (const appointment of appointments) {
    if (!appointment.patient) continue;
    const existing = byId.get(appointment.patient.id);
    if (!existing) {
      byId.set(appointment.patient.id, {
        patient: appointment.patient,
        lastVisit: appointment.scheduled_at,
        totalVisits: 1,
      });
    } else {
      existing.totalVisits += 1;
      if (new Date(appointment.scheduled_at) > new Date(existing.lastVisit)) {
        existing.lastVisit = appointment.scheduled_at;
      }
    }
  }
  return Array.from(byId.values()).sort((a, b) => +new Date(b.lastVisit) - +new Date(a.lastVisit));
}

export function usePatients() {
  const appointmentsQuery = useDoctorAppointments();
  const appointments = useMemo(() => appointmentsQuery.data ?? [], [appointmentsQuery.data]);
  const patients = useMemo(() => derivePatients(appointments), [appointments]);
  return { ...appointmentsQuery, patients, appointments };
}

/** Filtra por nome ou telefone (dígitos), para a busca "enquanto digito". */
export function filterPatients(patients: PatientSummary[], term: string): PatientSummary[] {
  const clean = term.toLowerCase().trim();
  if (!clean) return patients;
  const digits = clean.replace(/\D/g, "");
  return patients.filter(
    (p) =>
      p.patient.name.toLowerCase().includes(clean) || (digits && p.patient.phone.replace(/\D/g, "").includes(digits)),
  );
}
