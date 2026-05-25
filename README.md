# FreshHaul

FreshHaul is a Django-based produce transport coordination platform. Farmers create map-based bookings, pay through M-Pesa STK Push, drivers accept matching jobs, and staff users manage pricing and operational reporting from in-app dashboards.

## What The System Does

- Farmers create bookings with pickup and dropoff locations selected from map/place data.
- The backend calculates route distance, duration, required vehicle class, and quoted price.
- Payments are initiated with Safaricom Daraja STK Push.
- Paid bookings become visible to matching drivers.
- Drivers maintain profile, location, and vehicle data.
- Drivers accept jobs, update trip progress, and send tracking updates.
- Staff users manage transport pricing bands and review booking and revenue dashboards.
- Email verification, resend verification, and password reset flows are included.

## Roles

- `farmer`
  Can create, view, track, and delete unpaid bookings.
- `driver`
  Can manage transporter profile and vehicles, accept matching bookings, update live location, and complete delivery actions.
- `admin`
  Staff account with access to the in-app admin dashboard and Django admin.

## Core Booking Flow

1. A farmer creates a booking with produce details and map-selected endpoints.
2. The system computes route data and determines the required vehicle type from booking weight.
3. The booking is created in `pending_payment`.
4. The farmer initiates STK Push payment.
5. On successful callback, booking payment becomes `paid` and status becomes `confirmed`.
6. Matching drivers see the booking in their open jobs list.
7. A driver accepts the booking with one of their available vehicles.
8. The driver can mark `picked_up` only when physically near the pickup point.
9. The system moves the trip to `in_transit` after pickup progression logic.
10. The driver can mark `delivered` only when near the dropoff point.
11. Payment release and payout records are updated after delivery completion logic runs.

## Booking And Payment Statuses

Booking statuses:

- `pending_payment`
- `confirmed`
- `accepted`
- `declined`
- `picked_up`
- `in_transit`
- `delivered`
- `completed`
- `cancelled`

Booking payment statuses:

- `unpaid`
- `pending`
- `paid`

Payment statuses:

- `pending`
- `stk_push_sent`
- `paid_held`
- `failed`
- `cancelled`
- `released`

Payout statuses:

- `pending_release`
- `released`
- `failed`

## Business Rules Enforced In Code

- Public signup is limited to `farmer` and `driver`.
- Non-staff users must verify email before login.
- Bookings can only be created by farmers.
- The required vehicle class is derived from booking weight and configured pricing bands.
- Farmers can only delete bookings still in `pending_payment`.
- Drivers can only accept bookings already in `confirmed` and already marked as paid.
- Drivers must choose an available vehicle that matches the booking vehicle type and capacity.
- Pickup and delivery status changes are location-gated using the driver profile location.
- Driver-facing open jobs are filtered by available vehicle types and progressive transporter matching.

## Vehicle Pricing Defaults

Default seeded pricing rules:

- `motorbike`: `KES 100/km`, `0kg < weight <= 200kg`
- `van`: `KES 250/km`, `200kg < weight <= 1000kg`
- `pickup`: `KES 200/km`, `1000kg < weight <= 3000kg`
- `truck`: `KES 350/km`, `10000kg < weight <= 30000kg`

Staff users can change pricing bands in the admin dashboard at `/accounts/admin-dashboard/`.

## Tech Stack

- Python 3.12
- Django 6
- Django REST Framework
- PostgreSQL in Docker deployments
- SQLite fallback for local development when PostgreSQL env vars are absent
- Leaflet with OpenStreetMap/Nominatim/OSRM integrations
- Safaricom Daraja sandbox for M-Pesa

## Project Structure

```text
final_year_project/
├── README.md
├── API.md
├── project.mmd
└── backend/
    ├── ARCHITECTURE.md
    ├── Dockerfile
    ├── docker-compose.yml
    ├── entrypoint.sh
    ├── requirements.txt
    ├── manage.py
    ├── core/            # settings and root URL configuration
    ├── accounts/        # custom auth, dashboards, verification, reports
    ├── booking/         # booking lifecycle, matching, tracking
    ├── maps/            # place lookup, reverse geocoding, route preview
    ├── payments/        # STK Push, callbacks, payment and payout records
    ├── transporters/    # driver profiles, vehicles, pricing
    └── templates/       # web UI templates
```

## Main Web Routes

- `/`
  Public landing page for anonymous users, role-based dashboard for authenticated users.
- `/accounts/signup/`
  Public registration.
- `/accounts/login/`
  Login using phone number and password.
- `/accounts/profile/`
  Profile update endpoint/page.
- `/accounts/verification-sent/`
  Email verification notice.
- `/accounts/verify-email/`
  Code-based email verification page.
- `/accounts/resend-verification/`
  Resend verification code.
- `/accounts/admin-dashboard/`
  Staff pricing, reporting, and booking management dashboard.
- `/admin/`
  Django admin.

## API Areas

- `/api/bookings/`
  Booking CRUD, tracking, and driver actions.
- `/api/maps/`
  Search, lookup, reverse geocoding, and route preview.
- `/api/payments/`
  STK Push initiation, callback, payment detail, and booking payment status.
- `/api/transporters/`
  Driver profile/vehicle setup and live location updates.

Full endpoint documentation lives in [API.md](./API.md).

## Local Development

### 1. Create a virtual environment

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Set environment variables

At minimum:

```bash
export DJANGO_SECRET_KEY='change-me'
export DEBUG=1
```

Optional database variables for PostgreSQL:

- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST`
- `POSTGRES_PORT`

If these are not set, the project uses SQLite at `backend/db.sqlite3`.

### 3. Run migrations and start the server

```bash
python manage.py migrate
python manage.py runserver
```

## Docker Development

The backend container runs migrations automatically from `entrypoint.sh`.

```bash
cd backend
docker compose up --build
```

Default exposed services:

- Django app: `http://127.0.0.1:8000`
- Adminer: `http://127.0.0.1:8080`
- PostgreSQL: `localhost:5432`

## Environment Variables

Important settings used by the project:

- `DJANGO_SECRET_KEY`
- `DEBUG`
- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`
- `USE_SECURE_COOKIES`
- `SECURE_SSL_REDIRECT`
- `ENABLE_HSTS`
- `DRF_THROTTLE_ANON`
- `DRF_THROTTLE_USER`
- `MAPS_USER_AGENT`
- `MAPS_TIMEOUT_SECONDS`
- `NOMINATIM_SEARCH_URL`
- `NOMINATIM_LOOKUP_URL`
- `NOMINATIM_REVERSE_URL`
- `OSRM_BASE_URL`
- `EMAIL_BACKEND`
- `EMAIL_HOST`
- `EMAIL_PORT`
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`
- `EMAIL_USE_TLS`
- `EMAIL_USE_SSL`
- `DEFAULT_FROM_EMAIL`
- `SERVER_EMAIL`
- `MPESA_ENV`
- `MPESA_CONSUMER_KEY`
- `MPESA_CONSUMER_SECRET`
- `MPESA_SHORTCODE`
- `MPESA_PASSKEY`
- `MPESA_CALLBACK_URL`
- `MPESA_INITIATOR_NAME`
- `MPESA_TIMEOUT_SECONDS`
- `PUBLIC_BASE_URL`
- `SITE_NAME`
- `SITE_SUPPORT_EMAIL`
- `SITE_SUPPORT_PHONE`
- `SITE_TAGLINE`

## Notes

- API authentication is session-based.
- DRF throttling is enabled for anonymous and authenticated traffic.
- The project currently includes `drf-spectacular` in dependencies, but no schema or Swagger route is wired in `core/urls.py`.
- The current shell in this workspace does not have Django installed, so runtime verification requires installing dependencies first.
