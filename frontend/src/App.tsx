import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import AdminDashboard from './AdminDashboard'
import { createAppointment, getAvailability, getDailyQueue } from './services/api'
import type { Appointment, QueueEntry } from './services/api'
import './App.css'

const emptyForm = {
  full_name: '', address: '',
}

function App() {
  const [form, setForm] = useState(emptyForm)
  const [memberNames, setMemberNames] = useState<string[]>([])
  const [appointment, setAppointment] = useState<Appointment | null>(null)
  const [queueDate, setQueueDate] = useState('')
  const [queue, setQueue] = useState<QueueEntry[] | null>(null)
  const [queuePage, setQueuePage] = useState(1)
  const [queueError, setQueueError] = useState('')
  const [queueLoading, setQueueLoading] = useState(true)
  const [dateOpen, setDateOpen] = useState(false)
  const [bookingDate, setBookingDate] = useState('')
  const [bookingNote, setBookingNote] = useState('Loading booking availability...')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    setError('')
    const refresh = () => getAvailability()
      .then((data) => { if (active) { setDateOpen(data.is_open); setBookingDate(data.date); setBookingNote(data.note) } })
      .catch(() => { if (active) { setDateOpen(false); setBookingNote('Unable to load booking availability. Please try again shortly.') } })
    void refresh()
    const timer = window.setInterval(refresh, 30000)
    return () => { active = false; window.clearInterval(timer) }
  }, [appointment])

  useEffect(() => {
    let active = true
    setQueuePage(1)
    setQueueLoading(true)
    setQueueError('')
    const refresh = () => getDailyQueue()
      .then((data) => { if (active) {
        setQueue(data.queue)
        setQueueDate(data.date)
        setQueueError('')
        setQueuePage((page) => Math.min(page, Math.max(1, Math.ceil(data.queue.length / 5))))
      } })
      .catch((err) => { if (active) setQueueError(err instanceof Error ? err.message : 'Unable to load the queue.') })
      .finally(() => { if (active) setQueueLoading(false) })
    void refresh()
    const timer = window.setInterval(refresh, 30000)
    return () => { active = false; window.clearInterval(timer) }
  }, [appointment])

  const update = (key: keyof typeof form, value: string) => setForm((current) => ({ ...current, [key]: value }))
  const addMember = () => setMemberNames((current) => [...current, ''])
  const updateMember = (index: number, value: string) => setMemberNames((current) => current.map((name, itemIndex) => itemIndex === index ? value : name))
  const removeMember = (index: number) => setMemberNames((current) => current.filter((_, itemIndex) => itemIndex !== index))
  const queuePageCount = Math.ceil((queue?.length ?? 0) / 5)
  const visibleQueue = queue?.slice((queuePage - 1) * 5, queuePage * 5) ?? []

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    setLoading(true)
    try {
      const created = await createAppointment({ ...form, additional_names: memberNames.map((name) => name.trim()).filter(Boolean) })
      setAppointment(created)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to create appointment.')
    } finally {
      setLoading(false)
    }
  }

  if (window.location.search.includes('admin=1')) return <AdminDashboard />
  if (appointment) return <Confirmation appointment={appointment} onNew={() => { setAppointment(null); setForm(emptyForm); setMemberNames([]) }} />

  return (
    <main className="shell">
      <header className="topbar">
        <img className="brand-mark" src="/apo-logo.jpg" alt="APO Care logo" />
        <div><strong>APO JEFF THE HEALER</strong></div>
        <a className="admin-link" href="/?admin=1">Staff sign in</a>
      </header>
      <section className="hero">
        <div><p className="eyebrow">WELCOME TO APO JEFF THE HEALER ONLINE APPOINTMENT REGISTRATION</p><p className="hero-copy">You can now book your appointment online.</p></div>
      </section>
      <section className="booking-layout">
        <form className="booking-card" onSubmit={submit}>
          <div className="section-heading"><span className="step">01</span><div><p className="eyebrow">TELL US ABOUT YOU</p><h2>Primary member details</h2></div></div>
          <div className="form-grid">
            <label>Full name<input required value={form.full_name} onChange={(event) => update('full_name', event.target.value)} placeholder="Juan Dela Cruz" /></label>
            <label className="wide">Address<textarea required rows={2} value={form.address} onChange={(event) => update('address', event.target.value)} placeholder="Your home address" /></label>
          </div>
          <div className="members-section">
            <div><p className="eyebrow">GROUP BOOKING</p><h3>Additional members</h3><p>Add names for people joining this appointment. You only need to complete the details above once.</p></div>
            {memberNames.map((name, index) => <div className="member-row" key={index}><input aria-label={`Additional member ${index + 1} name`} required value={name} onChange={(event) => updateMember(index, event.target.value)} placeholder={`Member ${index + 1} full name`} /><button type="button" className="remove-member" onClick={() => removeMember(index)} aria-label={`Remove member ${index + 1}`}>×</button></div>)}
            <button type="button" className="add-member" onClick={addMember}>+ Add another name</button>
          </div>
          <p className="booking-date-info">Bookings made today are scheduled for tomorrow. Booking is closed on Sundays.</p>
          {bookingDate && <p className="booking-date-info">Appointment date: <strong>{new Date(`${bookingDate}T00:00:00`).toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}</strong></p>}
          {!dateOpen && <p className="date-closed">{bookingNote || 'Appointments are closed for tomorrow. Please return on an open booking day.'}</p>}
          {error && <p className="error">{error}</p>}
          <button className="primary-action" disabled={loading || !dateOpen}>{loading ? 'Submitting appointment...' : 'Book Appoinment'} <span>→</span></button>
          <p className="privacy">Your information is kept private and used only to manage your appointment.</p>
        </form>
        <aside className="side-column"><div className="lookup-card"><p className="eyebrow">DAILY LINEUP</p><h2>Queue Dashboard</h2><p>Bookers and reference numbers, shown in queue order.</p><p className="selected-queue-date">Today's queue: {queueDate && new Date(`${queueDate}T00:00:00`).toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}</p>{queueError && <p className="lookup-error" role="alert">{queueError}</p>}{queueLoading && <p className="queue-empty" role="status">Loading queue...</p>}{!queueLoading && queue && <div className="queue-list" role="status">{queue.length ? visibleQueue.map((entry) => <div className="queue-entry" key={entry.reference_number}><span className="queue-number">#{entry.queue_position}</span><div><strong>{entry.booker_name}</strong><span>{entry.reference_number}</span><span className="queue-members">Additional members: {entry.additional_names.length ? entry.additional_names.join(', ') : 'None'}</span></div></div>) : <p className="queue-empty">No active bookings for this date yet.</p>}</div>}{!queueLoading && queuePageCount > 1 && <nav className="queue-pagination" aria-label="Queue pages"><button type="button" disabled={queuePage === 1} onClick={() => setQueuePage((page) => page - 1)}>Previous</button><span>Page {queuePage} of {queuePageCount}</span><button type="button" disabled={queuePage === queuePageCount} onClick={() => setQueuePage((page) => page + 1)}>Next</button></nav>}<div className="aside-note"><span>✦</span><p>Queue order follows booking time. Cancelled bookings are not included.</p></div></div><div className="info-card"><p className="eyebrow">LOCATION NG GAMUTAN</p><strong>DAANG CALAYO BRGY. LOOC, NASUGBU, BATANGAS</strong><p>Near ALFAMART LOOC</p><a href="https://www.google.com/maps/search/?api=1&query=GAMUTAN+NI+APO+JEFF" target="_blank" rel="noreferrer">Search GAMUTAN NI APO JEFF on Google Maps ↗</a></div><div className="info-card"><p className="eyebrow">ARAW NG GAMUTAN</p><strong>TUESDAY TO SUNDAY</strong><p>8:00 AM - 6:00 PM</p><strong>WALANG GAMUTAN SA MONDAY</strong></div></aside>
      </section>
      <footer><span>APO Jeff 2026</span><span>Developed by: Russel Guevarra ♡</span></footer>
    </main>
  )
}

function Confirmation({ appointment, onNew }: { appointment: Appointment; onNew: () => void }) {
  return <main className="confirmation-page"><div className="confirmation-panel"><div className="success-icon">✓</div><p className="eyebrow">YOU'RE ALL SET</p><h1>Appointment<br /><em>confirmed.</em></h1><p className="hero-copy">Your booking is confirmed. Keep your reference number to check your place in the queue.</p><div className="reference"><span>REFERENCE NUMBER</span><strong>{appointment.reference_number}</strong></div><div className="details"><div><span>Primary member</span><strong>{appointment.patient.full_name}</strong></div><div><span>Date</span><strong>{appointment.appointment_date}</strong></div><div><span>Additional members</span><strong>{appointment.additional_names?.length ? appointment.additional_names.join(', ') : 'None'}</strong></div><div><span>Status</span><strong className="confirmed">{appointment.status_label}</strong></div></div><button className="primary-action" onClick={() => window.print()}>Print confirmation <span>↗</span></button><button className="text-action" onClick={onNew}>Book another appointment</button></div></main>
}

export default App
