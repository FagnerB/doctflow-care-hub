// Funções de endpoint, agrupadas por domínio — espelham 1:1 os routers do
// backend (app/routers/*.py). Os hooks em src/hooks/ chamam só isto aqui,
// nunca apiGet/apiPost diretamente.
import { apiDelete, apiGet, apiPost, apiPut } from "./api-client";
import type {
  Appointment,
  AppointmentCreateByDoctorPayload,
  AppointmentCreatePayload,
  AppointmentPublicStatus,
  AppointmentStatus,
  AvailabilityResponse,
  Doctor,
  DoctorPublic,
  DoctorStats,
  DoctorUpdatePayload,
  ResetPasswordPayload,
  ScheduleException,
  ScheduleExceptionCreatePayload,
  TokenPair,
  User,
} from "./api-types";

export const authApi = {
  login: (email: string, password: string) =>
    apiPost<TokenPair>("/api/auth/login", { email, password }, false),

  me: () => apiGet<{ user: User }>("/api/auth/me"),

  forgotPassword: (email: string) =>
    apiPost<{ success: boolean; message: string }>("/api/auth/forgot-password", { email }, false),

  resetPassword: (payload: ResetPasswordPayload) =>
    apiPost<{ success: boolean; message: string }>("/api/auth/reset-password", payload, false),
};

export const doctorsApi = {
  getPublic: (slug: string) => apiGet<DoctorPublic>(`/api/doctors/${encodeURIComponent(slug)}`, undefined, false),

  getAvailability: (slug: string, dateStr: string) =>
    apiGet<AvailabilityResponse>(`/api/doctors/${encodeURIComponent(slug)}/availability`, { date: dateStr }, false),

  getMe: () => apiGet<Doctor>("/api/doctors/me"),

  updateMe: (payload: DoctorUpdatePayload) => apiPut<Doctor>("/api/doctors/me", payload),

  getMyAppointments: (params?: { date_from?: string; date_to?: string; status?: AppointmentStatus }) =>
    apiGet<Appointment[]>("/api/doctors/me/appointments", params),

  createMyAppointment: (payload: AppointmentCreateByDoctorPayload) =>
    apiPost<Appointment>("/api/doctors/me/appointments", payload),

  getMyStats: (referenceMonth?: string) =>
    apiGet<DoctorStats>("/api/doctors/me/stats", { reference_month: referenceMonth }),

  updateAppointmentStatus: (appointmentId: string, status: AppointmentStatus, notes?: string) =>
    apiPut<Appointment>(`/api/doctors/me/appointments/${appointmentId}/status`, { status, notes }),

  listExceptions: () => apiGet<ScheduleException[]>("/api/doctors/me/exceptions"),

  createException: (payload: ScheduleExceptionCreatePayload) =>
    apiPost<ScheduleException>("/api/doctors/me/exceptions", payload),

  deleteException: (exceptionId: string) =>
    apiDelete<{ success: boolean }>(`/api/doctors/me/exceptions/${exceptionId}`),
};

export const appointmentsApi = {
  create: (payload: AppointmentCreatePayload) => apiPost<Appointment>("/api/appointments", payload, false),

  getPublicStatus: (appointmentId: string) =>
    apiGet<AppointmentPublicStatus>(`/api/appointments/${appointmentId}/status`, undefined, false),

  cancelPublic: (appointmentId: string) =>
    apiPost<AppointmentPublicStatus>(`/api/appointments/${appointmentId}/cancel`, undefined, false),
};
