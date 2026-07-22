// Dados mockados para desenvolvimento do frontend antes da integração com a API.
import { addDays, addMinutes, format, setHours, setMinutes, startOfDay } from "date-fns";

export type AppointmentStatus = "pending" | "confirmed" | "completed" | "cancelled";

export interface Appointment {
  id: string;
  patientName: string;
  patientPhone: string;
  patientEmail?: string;
  start: Date;
  end: Date;
  status: AppointmentStatus;
  notes?: string;
}

export interface Patient {
  id: string;
  name: string;
  phone: string;
  email?: string;
  lastVisit?: Date;
  totalVisits: number;
}

export interface DoctorProfile {
  slug: string;
  name: string;
  specialty: string;
  bio: string;
  avatarUrl?: string;
}

export const mockDoctor: DoctorProfile = {
  slug: "dr-silva",
  name: "Dr. Rafael Silva",
  specialty: "Cardiologia",
  bio: "Cardiologista há 12 anos. Atendimento humanizado e focado em prevenção.",
};

// Gera horários disponíveis (mock) para uma data
export function getAvailableSlots(date: Date): { morning: Date[]; afternoon: Date[] } {
  const day = startOfDay(date);
  const morning: Date[] = [];
  const afternoon: Date[] = [];
  // Manhã: 08:00 - 12:00
  for (let h = 8; h < 12; h++) {
    for (const m of [0, 30]) {
      morning.push(setMinutes(setHours(day, h), m));
    }
  }
  // Tarde: 14:00 - 18:00
  for (let h = 14; h < 18; h++) {
    for (const m of [0, 30]) {
      afternoon.push(setMinutes(setHours(day, h), m));
    }
  }
  // Remove slots pseudo-aleatórios para parecer real
  const seed = date.getDate();
  return {
    morning: morning.filter((_, i) => (i + seed) % 3 !== 0),
    afternoon: afternoon.filter((_, i) => (i + seed) % 4 !== 0),
  };
}

// Consultas mockadas
const today = startOfDay(new Date());
export const mockAppointments: Appointment[] = [
  {
    id: "a1",
    patientName: "Maria Santos",
    patientPhone: "(11) 98765-4321",
    patientEmail: "maria@example.com",
    start: setMinutes(setHours(today, 9), 0),
    end: setMinutes(setHours(today, 9), 30),
    status: "confirmed",
  },
  {
    id: "a2",
    patientName: "João Pereira",
    patientPhone: "(11) 91234-5678",
    start: setMinutes(setHours(today, 10), 30),
    end: setMinutes(setHours(today, 11), 0),
    status: "pending",
  },
  {
    id: "a3",
    patientName: "Ana Costa",
    patientPhone: "(21) 99876-5432",
    start: setMinutes(setHours(addDays(today, 1), 14), 0),
    end: setMinutes(setHours(addDays(today, 1), 14), 30),
    status: "confirmed",
  },
  {
    id: "a4",
    patientName: "Pedro Lima",
    patientPhone: "(11) 98888-7777",
    start: setMinutes(setHours(addDays(today, -3), 15), 0),
    end: setMinutes(setHours(addDays(today, -3), 15), 30),
    status: "completed",
  },
  {
    id: "a5",
    patientName: "Carla Souza",
    patientPhone: "(11) 97777-6666",
    start: setMinutes(setHours(addDays(today, -5), 11), 0),
    end: setMinutes(setHours(addDays(today, -5), 11), 30),
    status: "cancelled",
  },
];

export const mockPatients: Patient[] = [
  {
    id: "p1",
    name: "Maria Santos",
    phone: "(11) 98765-4321",
    email: "maria@example.com",
    lastVisit: today,
    totalVisits: 4,
  },
  {
    id: "p2",
    name: "João Pereira",
    phone: "(11) 91234-5678",
    lastVisit: today,
    totalVisits: 2,
  },
  {
    id: "p3",
    name: "Ana Costa",
    phone: "(21) 99876-5432",
    lastVisit: addDays(today, 1),
    totalVisits: 1,
  },
  {
    id: "p4",
    name: "Pedro Lima",
    phone: "(11) 98888-7777",
    lastVisit: addDays(today, -3),
    totalVisits: 6,
  },
  {
    id: "p5",
    name: "Carla Souza",
    phone: "(11) 97777-6666",
    lastVisit: addDays(today, -5),
    totalVisits: 3,
  },
];

export const statusLabels: Record<AppointmentStatus, string> = {
  pending: "Pendente",
  confirmed: "Confirmado",
  completed: "Concluído",
  cancelled: "Cancelado",
};

export function formatDateTime(d: Date) {
  return format(d, "dd/MM/yyyy 'às' HH:mm");
}

export function slotDuration(start: Date, minutes = 30) {
  return addMinutes(start, minutes);
}
