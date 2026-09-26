import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import AdminDashboard from './AdminDashboard'
import { createAppointment, getAvailability, lookupAppointment } from './services/api'
import type { Appointment } from './services/api'
import './App.css'

const today = (() => {
  const date = new Date()
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 10)
})()

const minimumAppointmentDate = (() => {
  const date = new Date(`${today}T00:00:00`)
  date.setDate(date.getDate() + 1)
  while (date.getDay() === 1) date.setDate(date.getDate() + 1)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
})()

const emptyForm = {
  full_name: '', email: '', contact_number: '', address: '', age: '', gender: '', appointment_date: minimumAppointmentDate,
}

function App() {
  const [form, setForm] = useState(emptyForm)
  const [memberNames, setMemberNames] = useState<string[]>([])
  const [appointment, setAppointment] = useState<Appointment | null>(null)
  const [lookup, setLookup] = useState('')
  const [lookupResult, setLookupResult] = useState<Appointment | null>(null)
  const [dateOpen, setDateOpen] = useState(true)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    setError('')
    getAvailability(form.appointment_date)
      .then((data) => setDateOpen(data.is_open))
      .catch(() => setDateOpen(true))
  }, [form.appointment_date])

  const update = (key: keyof typeof form, value: string) => setForm((current) => ({ ...current, [key]: value }))
  const addMember = () => setMemberNames((current) => [...current, ''])
  const updateMember = (index: number, value: string) => setMemberNames((current) => current.map((name, itemIndex) => itemIndex === index ? value : name))
  const removeMember = (index: number) => setMemberNames((current) => current.filter((_, itemIndex) => itemIndex !== index))

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    setLoading(true)
    try {
      const created = await createAppointment({ ...form, age: Number(form.age), additional_names: memberNames.map((name) => name.trim()).filter(Boolean) })
      setAppointment(created)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to create appointment.')
    } finally {
      setLoading(false)
    }
  }

  const findAppointment = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    try { setLookupResult(await lookupAppointment(lookup.trim())) }
    catch (err) { setError(err instanceof Error ? err.message : 'Appointment not found.') }
  }

  if (window.location.search.includes('admin=1')) return <AdminDashboard />
  if (appointment) return <Confirmation appointment={appointment} onNew={() => { setAppointment(null); setForm(emptyForm); setMemberNames([]) }} />

  return (
    <main className="shell">
      <header className="topbar">
        <img className="brand-mark" src="/apo-logo.jpg" alt="APO Care logo" />
        <div><strong>APO JEFF THE HEALER</strong><span>Community appointment desk</span></div>
        <a className="admin-link" href="/?admin=1">Staff sign in</a>
      </header>
      <section className="hero">
        <div><p className="eyebrow">WELCOME TO APO JEFF THE HEALER ONLINE APPOINTMENT REGISTRATION</p><p className="hero-copy">You can now book your appointment online. Anytime. Anywhere.</p></div>
      </section>
      <section className="booking-layout">
        <form className="booking-card" onSubmit={submit}>
          <div className="section-heading"><span className="step">01</span><div><p className="eyebrow">TELL US ABOUT YOU</p><h2>Primary member details</h2></div></div>
          <div className="form-grid">
            <label>Full name<input required value={form.full_name} onChange={(event) => update('full_name', event.target.value)} placeholder="Juan Dela Cruz" /></label>
            <label>Email address<input required type="email" value={form.email} onChange={(event) => update('email', event.target.value)} placeholder="example@gmail.com" /></label>
            <label>Contact number<input required value={form.contact_number} onChange={(event) => update('contact_number', event.target.value)} placeholder="09XX XXX XXXX" /></label>
            <label>Age<input required type="number" min="1" max="120" value={form.age} onChange={(event) => update('age', event.target.value)} placeholder="Your age" /></label>
            <label>Gender<select required value={form.gender} onChange={(event) => update('gender', event.target.value)}><option value="">Select one</option><option value="female">Female</option><option value="male">Male</option><option value="other">Other</option><option value="prefer_not">Prefer not to say</option></select></label>
            <label className="wide">Address<textarea required rows={2} value={form.address} onChange={(event) => update('address', event.target.value)} placeholder="Your home address" /></label>
          </div>
          <div className="members-section">
            <div><p className="eyebrow">GROUP BOOKING</p><h3>Additional members</h3><p>Add names for people joining this appointment. You only need to complete the details above once.</p></div>
            {memberNames.map((name, index) => <div className="member-row" key={index}><input aria-label={`Additional member ${index + 1} name`} required value={name} onChange={(event) => updateMember(index, event.target.value)} placeholder={`Member ${index + 1} full name`} /><button type="button" className="remove-member" onClick={() => removeMember(index)} aria-label={`Remove member ${index + 1}`}>×</button></div>)}
            <button type="button" className="add-member" onClick={addMember}>+ Add another name</button>
          </div>
          <div className="section-heading schedule-heading"><span className="step">02</span><div><p className="eyebrow">CHOOSE A DATE</p><h2>When can we see you?</h2></div></div>
          <label className="date-label">Appointment date<input required type="date" min={minimumAppointmentDate} value={form.appointment_date} onChange={(event) => update('appointment_date', event.target.value)} /></label>
          <p className="booking-notice">Appointments must be booked at least 24 hours in advance.</p>
          {!dateOpen && <p className="date-closed">Appointments are closed for this date. Please select another date.</p>}
          {error && <p className="error">{error}</p>}
          <button className="primary-action" disabled={loading || !dateOpen}>{loading ? 'Submitting appointment...' : 'Confirm appointment'} <span>→</span></button>
          <p className="privacy">Your information is kept private and used only to manage your appointment.</p>
        </form>
        <aside className="side-column"><div className="lookup-card"><p className="eyebrow">ALREADY BOOKED?</p><h2>Find your appointment</h2><p>Enter your reference number to view your booking details.</p><form onSubmit={findAppointment}><label className="sr-only" htmlFor="reference">Reference number</label><input id="reference" value={lookup} onChange={(event) => setLookup(event.target.value)} placeholder="APPT-2026-0001" required /><button className="secondary-action">Look up <span>↗</span></button></form>{lookupResult && <div className="lookup-result"><span className="status-dot"></span><strong>{lookupResult.status_label}</strong><p>{lookupResult.patient.full_name}<br />{lookupResult.appointment_date}</p></div>}<div className="aside-note"><span>✦</span><p>Appointments are confirmed by email. Please arrive a few minutes before your scheduled date.</p></div></div><div className="info-card"><p className="eyebrow">LOCATION NG GAMUTAN</p><strong>DAANG CALAYO BRGY. LOOC, NASUGBU, BATANGAS</strong><p>Near ALFAMART LOOC</p><a href="https://www.google.com/maps/search/?api=1&query=GAMUTAN+NI+APO+JEFF" target="_blank" rel="noreferrer">Search GAMUTAN NI APO JEFF on Google Maps ↗</a></div><div className="info-card"><p className="eyebrow">ARAW NG GAMUTAN</p><strong>TUESDAY TO SUNDAY</strong><p>8:00 AM - 6:00 PM</p><strong>WALANG GAMUTAN NG MONDAY</strong></div></aside>
      </section>
      <footer><span>APO Jeff 2026</span><span>Developed by: Russel Guevarra ♡</span></footer>
    </main>
  )
}

function Confirmation({ appointment, onNew }: { appointment: Appointment; onNew: () => void }) {
  return <main className="confirmation-page"><div className="confirmation-panel"><div className="success-icon">✓</div><p className="eyebrow">YOU'RE ALL SET</p><h1>Appointment<br /><em>confirmed.</em></h1><p className="hero-copy">A confirmation has been sent to {appointment.patient.email}.</p><div className="reference"><span>REFERENCE NUMBER</span><strong>{appointment.reference_number}</strong></div><div className="details"><div><span>Primary member</span><strong>{appointment.patient.full_name}</strong></div><div><span>Date</span><strong>{appointment.appointment_date}</strong></div><div><span>Additional members</span><strong>{appointment.additional_names?.length ? appointment.additional_names.join(', ') : 'None'}</strong></div><div><span>Status</span><strong className="confirmed">{appointment.status_label}</strong></div></div><button className="primary-action" onClick={() => window.print()}>Print confirmation <span>↗</span></button><button className="text-action" onClick={onNew}>Book another appointment</button></div></main>
}

export default App
