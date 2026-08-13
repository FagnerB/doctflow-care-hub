// Tipos TypeScript espelhando os schemas Pydantic do backend (app/schemas/*.py).
// Nomes de campo em snake_case propositalmente, iguais ao JSON da API — evita
// uma camada de tradução que só criaria oportunidade de dessincronizar.

export type UserRole = "owner" | "doctor" | "patient";

export type AppointmentStatus =
  | "pending"
  | "confirmed"
  | "completed"
  | "cancelled_by_patient"
  | "cancelled_by_doctor"
  | "no_show";

export type DayName =
  | "monday"
  | "tuesday"
  | "wednesday"
  | "thursday"
  | "friday"
  | "saturday"
  | "sunday";

export interface TimeWindow {
  start: string; // "HH:mm"
  end: string; // "HH:mm"
}

export interface DoctorConfig {
  consultation_duration_minutes: number;
  advance_booking_days: number;
  auto_confirm: boolean;
  cancellation_policy_hours: number;
  working_hours: Record<DayName, TimeWindow[]>;
}

export interface User {
  id: string;
  email: string;
  role: UserRole;
  full_name: string;
  phone: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Doctor {
  id: string;
  slug: string;
  specialty: string;
  bio: string | null;
  avatar_url: string | null;
  is_verified: boolean;
  config_json: DoctorConfig;
  created_at: string;
  updated_at: string;
  user: User;
}

export interface DoctorPublic {
  slug: string;
  full_name: string;
  specialty: string;
  bio: string | null;
  avatar_url: string | null;
  is_verified: boolean;
  config_json: DoctorConfig;
}

export interface DoctorUpdatePayload {
  full_name?: string;
  phone?: string;
  specialty?: string;
  bio?: string | null;
  avatar_url?: string | null;
  config_json?: DoctorConfig;
}

export interface Patient {
  id: string;
  name: string;
  phone: string;
  email: string | null;
  cpf: string | null;
  created_at: string;
}

export interface Appointment {
  id: string;
  doctor_id: string;
  patient_id: string;
  scheduled_at: string; // ISO com offset de America/Sao_Paulo
  duration_minutes: number;
  status: AppointmentStatus;
  notes: string | null;
  created_at: string;
  updated_at: string;
  confirmation_sent_at: string | null;
  reminder_sent_at: string | null;
  patient: Patient | null;
}

export interface AppointmentPublicStatus {
  id: string;
  status: AppointmentStatus;
  scheduled_at: string;
  duration_minutes: number;
  confirmation_sent_at: string | null;
  reminder_sent_at: string | null;
  doctor_full_name: string;
  patient_name: string;
  patient_phone: string;
}

export interface AvailabilitySlot {
  start_time: string; // ISO com offset de America/Sao_Paulo
  end_time: string;
  is_available: boolean;
}

export interface AvailabilityResponse {
  doctor_slug: string;
  date: string;
  slots: AvailabilitySlot[];
}

export interface ScheduleException {
  id: string;
  doctor_id: string;
  exception_date: string; // "YYYY-MM-DD"
  start_time: string | null; // "HH:mm:ss"
  end_time: string | null;
  reason: string | null;
  created_at: string;
}

export interface ScheduleExceptionCreatePayload {
  exception_date: string;
  start_time?: string | null;
  end_time?: string | null;
  reason?: string | null;
}

export interface UpcomingAppointmentSummary {
  id: string;
  patient_name: string;
  patient_phone: string;
  scheduled_at: string;
  duration_minutes: number;
  status: AppointmentStatus;
}

export interface DoctorStats {
  month: string;
  total_appointments: number;
  confirmed: number;
  completed: number;
  no_show: number;
  cancelled: number;
  attendance_rate: number;
  upcoming: UpcomingAppointmentSummary[];
}

export interface TokenPair {
  token_type: string;
  access_token: string;
  refresh_token: string;
  expires_in: number;
  user: User;
}

export interface AppointmentCreatePayload {
  doctor_slug: string;
  patient_name: string;
  patient_phone: string;
  patient_email?: string | null;
  patient_cpf?: string | null;
  desired_datetime: string; // ISO
  notes?: string | null;
}

export interface ResetPasswordPayload {
  new_password: string;
  access_token?: string;
  token_hash?: string;
  type?: string;
}

// Envelope de erro padronizado (app/main.py: exception handlers).
export interface ApiErrorBody {
  success: false;
  error: string;
  code: string;
  details?: unknown;
}
