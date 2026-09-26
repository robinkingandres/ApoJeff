import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { getAdminAppointments, getAdminStats, getScheduleDate, staffLogin, updateAppointmentStatus, updateScheduleDate } from './services/api'
import type { AdminStats, Appointment, ScheduleDate } from './services/api'

const localToday = (() => {
  const now = new Date()
  return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 10)
})()

export default function AdminDashboard() {
  const [loggedIn, setLoggedIn] = useState(Boolean(localStorage.getItem('apo_staff_token')))
  return loggedIn ? <Dashboard onLogout={() => { localStorage.removeItem('apo_staff_token'); setLoggedIn(false) }} /> : <Login onLoggedIn={() => setLoggedIn(true)} />
}

function Login({ onLoggedIn }: { onLoggedIn: () => void }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (event: FormEvent) => {
    event.preventDefault(); setLoading(true); setError('')
    try {
      const tokens = await staffLogin(username, password)
      localStorage.setItem('apo_staff_token', tokens.access)
      onLoggedIn()
    } catch (err) { setError(err instanceof Error ? err.message : 'Unable to sign in.') }
    finally { setLoading(false) }
  }

  return <main className="admin-page"><form className="admin-login" onSubmit={submit}><p className="eyebrow">APO JEFF THE HEALER</p><h1>Staff sign in</h1><p>Manage appointments and schedule availability.</p><label>Username<input required value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" /></label><label>Password<input required type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" /></label>{error && <p className="admin-error">{error}</p>}<button className="primary-action" disabled={loading}>{loading ? 'Signing in...' : 'Sign in'} <span>→</span></button><a className="back-link" href="/">Back to public booking</a></form></main>
}

function Dashboard({ onLogout }: { onLogout: () => void }) {
  const [appointments, setAppointments] = useState<Appointment[]>([])
  const [stats, setStats] = useState<AdminStats>({ today: 0, upcoming: 0, completed: 0, cancelled: 0 })
  const [schedule, setSchedule] = useState<ScheduleDate>({ date: localToday, is_open: true, note: '' })
  const [filters, setFilters] = useState({ search: '', status: '', date: '' })
  const [error, setError] = useState('')

  const refresh = async () => {
    try {
      const query = new URLSearchParams(Object.entries(filters).filter(([, value]) => value)).toString()
      const [records, counts] = await Promise.all([getAdminAppointments(query ? `?${query}` : ''), getAdminStats()])
      setAppointments(records); setStats(counts); setError('')
    } catch (err) { setError(err instanceof Error ? err.message : 'Unable to load dashboard data.') }
  }

  useEffect(() => { refresh() }, [filters.status, filters.date])
  useEffect(() => { getScheduleDate(localToday).then(setSchedule).catch(() => undefined) }, [])

  const changeStatus = async (appointment: Appointment, status: string) => {
    try { await updateAppointmentStatus(String(appointment.id), status); await refresh() } catch (err) { setError(err instanceof Error ? err.message : 'Unable to update status.') }
  }

  const changeDate = async (date: string) => {
    setSchedule({ date, is_open: true, note: '' })
    try { setSchedule(await getScheduleDate(date)) } catch { setError('Unable to load that schedule date.') }
  }

  const toggleDate = async () => {
    try { setSchedule(await updateScheduleDate(schedule.date, !schedule.is_open, schedule.note)) } catch (err) { setError(err instanceof Error ? err.message : 'Unable to update schedule.') }
  }

  return <main className="admin-page dashboard-page"><header className="dashboard-header"><div><p className="eyebrow">APO JEFF THE HEALER</p><h1>Appointment dashboard</h1></div><div className="dashboard-actions"><button className="print-button" onClick={() => window.print()}>Print / Save PDF</button><button className="logout-button" onClick={onLogout}>Sign out</button></div></header>{error && <p className="admin-error">{error}</p>}<section className="stat-grid"><Stat label="Today's appointments" value={stats.today} /><Stat label="Upcoming" value={stats.upcoming} /><Stat label="Completed" value={stats.completed} /><Stat label="Cancelled" value={stats.cancelled} /></section><section className="schedule-control"><div><p className="eyebrow">SCHEDULE CONTROL</p><h2>Open or close a date</h2><p>Closed dates stop new public bookings immediately.</p></div><div className="schedule-fields"><label>Date<input type="date" value={schedule.date} min={localToday} onChange={(event) => changeDate(event.target.value)} /></label><label>Note<input value={schedule.note} onChange={(event) => setSchedule({ ...schedule, note: event.target.value })} placeholder="Optional reason" /></label><button className={schedule.is_open ? 'close-date' : 'open-date'} onClick={toggleDate}>{schedule.is_open ? 'Close date' : 'Open date'}</button></div><strong className={schedule.is_open ? 'open-label' : 'closed-label'}>{schedule.is_open ? 'OPEN FOR BOOKINGS' : 'CLOSED FOR BOOKINGS'}</strong></section><section className="appointment-panel"><div className="panel-heading"><div><p className="eyebrow">PATIENT RECORDS</p><h2>All appointments</h2></div><button className="refresh-button" onClick={refresh}>Refresh</button></div><div className="filters"><input placeholder="Search name, email, reference" value={filters.search} onChange={(event) => setFilters({ ...filters, search: event.target.value })} onKeyDown={(event) => event.key === 'Enter' && refresh()} /><input type="date" value={filters.date} onChange={(event) => setFilters({ ...filters, date: event.target.value })} /><select value={filters.status} onChange={(event) => setFilters({ ...filters, status: event.target.value })}><option value="">All statuses</option><option value="pending">Pending</option><option value="confirmed">Confirmed</option><option value="completed">Completed</option><option value="cancelled">Cancelled</option></select></div><div className="appointment-table">{appointments.length === 0 ? <p className="empty-state">No appointments match these filters.</p> : appointments.map((appointment) => <article className="appointment-row" key={appointment.id}><div className="appointment-main"><strong>{appointment.patient.full_name}</strong><span>{appointment.reference_number} · {appointment.appointment_date} at {appointment.appointment_time}</span></div><div className="patient-detail"><span>{appointment.patient.email}</span><span>{appointment.patient.contact_number}</span><span>{appointment.patient.address}</span></div><div className="row-actions"><span className={`status-badge ${appointment.status}`}>{appointment.status_label}</span><select value={appointment.status} onChange={(event) => changeStatus(appointment, event.target.value)}><option value="pending">Pending</option><option value="confirmed">Confirmed</option><option value="completed">Completed</option><option value="cancelled">Cancelled</option></select></div></article>)}</div></section></main>
}

function Stat({ label, value }: { label: string; value: number }) { return <div className="stat-card"><span>{label}</span><strong>{value}</strong></div> }
