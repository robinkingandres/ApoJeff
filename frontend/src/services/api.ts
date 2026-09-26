const API_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000/api'

export type Slot = { time: string; label: string; booked: number; capacity: number; available: number; is_full: boolean }
export type Appointment = { id: number; reference_number: string; patient: { full_name: string; email: string; contact_number: string; address: string; age: number; gender: string }; additional_names: string[]; appointment_date: string; appointment_time: string | null; status: string; status_label: string; created_at: string; confirmation_sent_at: string | null; reminder_sent_at: string | null }
export type AdminStats = { today: number; upcoming: number; completed: number; cancelled: number }
export type ScheduleDate = { date: string; is_open: boolean; note: string; updated_at?: string }
export type QueueEntry = { queue_position: number; booker_name: string; reference_number: string; additional_names: string[] }

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem('apo_staff_token')
  const response = await fetch(`${API_URL}${path}`, { headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(options?.headers ?? {}) }, ...options })
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail ?? 'Something went wrong. Please try again.')
  return data
}

export const getAvailability = (date: string) => request<{ date: string; is_open: boolean; note: string; booked_count: number; slots?: Slot[] }>(`/availability/?date=${date}`)
export const createAppointment = (payload: Record<string, unknown>) => request<Appointment>('/appointments/', { method: 'POST', body: JSON.stringify(payload) })
export const lookupAppointment = (reference: string) => request<Appointment>(`/appointments/lookup/${encodeURIComponent(reference)}/`)
export const getDailyQueue = (date: string) => request<{ date: string; queue: QueueEntry[] }>(`/queue/?date=${date}`)
export const staffLogin = (username: string, password: string) => request<{ access: string; refresh: string }>('/auth/token/', { method: 'POST', body: JSON.stringify({ username, password }) })
export const getAdminAppointments = (filters = '') => request<Appointment[]>(`/admin/appointments/${filters}`)
export const getAdminStats = () => request<AdminStats>('/admin/appointments/stats/')
export const updateAppointmentStatus = (id: string, status: string) => request<Appointment>(`/admin/appointments/${id}/update_status/`, { method: 'PATCH', body: JSON.stringify({ status }) })
export const getScheduleDate = (date: string) => request<ScheduleDate>(`/admin/schedule/?date=${date}`)
export const updateScheduleDate = (date: string, is_open: boolean, note: string) => request<ScheduleDate>('/admin/schedule/', { method: 'PATCH', body: JSON.stringify({ date, is_open, note }) })
