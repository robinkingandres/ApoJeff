# APO Care Appointment System

A full-stack appointment scheduler for a traditional healing/community care service.

## Stack

- `frontend`: React 19 + TypeScript + Vite
- `backend`: Django 5 + Django REST Framework + SimpleJWT
- Database: PostgreSQL in deployment; SQLite is used only when `DATABASE_URL` is not configured for local smoke tests
- Email: Django email backend with environment-based SMTP settings

## Run locally

1. Start PostgreSQL: `docker compose up -d postgres`
2. Copy `backend/.env.example` to `backend/.env` and set the email credentials.
3. In `backend`, run `python -m pip install -r requirements.txt`, then `python manage.py migrate`.
4. Create an admin account with `python manage.py createsuperuser`.
5. Start the API with `python manage.py runserver`.
6. In `frontend`, run `npm install` and `npm run dev`.

The patient booking page is served by Vite. Staff can use Django Admin at `http://localhost:8000/admin/` or the staff sign-in link in the patient page.

## API

- `GET /api/availability/?date=YYYY-MM-DD`: public slot counts
- `POST /api/appointments/`: public booking; validates email, date, time, and capacity transactionally
- `GET /api/appointments/lookup/<reference>/`: public appointment lookup by reference
- `POST /api/auth/token/`: admin JWT login
- `POST /api/auth/token/refresh/`: refresh JWT
- `GET /api/admin/appointments/`: admin appointment list with `search`, `status`, and `date` filters
- `GET /api/admin/appointments/stats/`: admin dashboard counts
- `PATCH /api/admin/appointments/<id>/update_status/`: admin status update
- `DELETE /api/admin/appointments/<id>/`: staff-only permanent appointment deletion

## Reminders

The command `python manage.py send_reminders` finds confirmed appointments scheduled for tomorrow, sends one reminder per appointment, and records `reminder_sent_at` plus an `EmailEvent`. Run it once daily using Windows Task Scheduler, cron, or a container scheduler. Example cron entry:

```text
0 8 * * * /path/to/python /path/to/backend/manage.py send_reminders
```

Confirmation email failures do not discard a successful booking. Email event timestamps are visible in Django Admin.
