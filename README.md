# Final Year Project

Produce transport coordination platform built with Django. Farmers create transport bookings from a map, transporters accept matching jobs, the system tracks delivery progress, and staff/admin users manage transport pricing from an in-app dashboard.

## Core Features

- Farmers choose pickup and dropoff points from a map or place search.
- The system calculates route distance and duration using map services.
- Farmers pay quoted transport charges through M-Pesa STK Push at booking time.
- Transporter discovery is automatic and expands from nearby drivers outward.
- Farmers can delete incorrect pending bookings and create a new one.
- Transporters can edit vehicle details, accept jobs, mark pickup and delivery at the correct location, and share live location.
- Booking status changes trigger farmer popups for pickup, in-transit, and delivery.
- Staff/admin users manage vehicle-type transport rates outside Django admin.
- Email verification and password reset are supported through SMTP/Brevo-ready email delivery.
- The Docker app container runs database migrations automatically on startup.

## Business Rules

- Farmers do not choose a transporter search radius.
- The system automatically searches outward from nearby drivers to farther matching drivers.
- Farmers cannot edit bookings. Wrong pending bookings must be deleted and recreated.
- Farmers can delete only `pending_payment` bookings.
- Drivers can only mark `picked_up` after arriving at pickup.
- Drivers can only mark `delivered` after arriving at dropoff.
- `in_transit` is automatic after the driver leaves pickup with the goods.
- Farmer live driver tracking becomes visible only after pickup starts.
- Admin controls transport pricing by vehicle type.
- Daraja sandbox payments use application-level escrow simulation:
  farmer pays first, payment is held in system records, and it is released to the transporter only after delivery is marked complete.

## User Roles

- `farmer`
  Creates bookings, views bookings, tracks live transport, and deletes only pending bookings.
- `driver`
  Maintains vehicle details, accepts matching bookings, shares live location, marks pickup, and marks delivery.
- `admin`
  Staff user with access to the in-app admin dashboard and Django admin.

## Booking Lifecycle

1. Farmer selects pickup and dropoff on the map.
2. System creates the booking and calculates quote and route.
3. Farmer completes M-Pesa STK Push for the quoted amount.
4. System marks the booking `CONFIRMED` and holds the payment in application escrow.
5. Matching transporters see the booking in their dashboard.
6. A driver accepts the booking.
7. Driver marks `picked_up` only after arriving at pickup.
8. System switches the booking to `in_transit` automatically once the driver leaves pickup.
9. Driver marks `delivered` only after arriving at dropoff.
10. System releases the held payment to the transporter in internal payout records.
11. Farmer receives status popups and can track the route live.

## Authentication And Security

- Browser and API access use Django session authentication.
- Public sign-up is limited to `farmer` and `driver` accounts.
- Non-staff users must verify their email before signing in.
- Changing an account email address triggers re-verification.
- API access is protected by authenticated role checks and DRF throttling.
- Production security flags are environment-driven in `backend/core/settings.py`.

## Pricing

Transport rates are controlled by admin per vehicle type.

Default seeded rates:

- Motorbike: `KES 100/km`
- Pickup: `KES 200/km`
- Van: `KES 250/km`
- Truck: `KES 350/km`

Rates can be updated in the app at:

- `/accounts/admin-dashboard/`

## Main Pages

- `/`
  Home entry point. Redirects by role.
- `/accounts/login/`
  Login page using phone number and password.
- `/accounts/signup/`
  User registration for farmer or driver.
- `/accounts/verification-sent/`
  Email verification notice page after signup or email change.
- `/accounts/resend-verification/`
  Resend verification link.
- `/accounts/admin-dashboard/`
  Staff/admin dashboard for rates and revenue.
- `/accounts/password_reset/`
  Password reset request page.
- `/api/payments/stk-push/`
  Initiate M-Pesa STK Push for a booking.
- `/admin/`
  Django admin site for staff users.

## Project Structure

```text
final_year_project/
├── README.md
└── backend/
    ├── accounts/        # custom user model, auth views, admin dashboard
    ├── booking/         # booking flow, status lifecycle, tracking
    ├── maps/            # place search, reverse geocoding, route preview
    ├── transporters/    # driver vehicle setup, live location, pricing
    ├── templates/       # farmer, transporter, auth, and admin UI
    ├── core/            # Django settings and URL configuration
    ├── Dockerfile
    ├── docker-compose.yml
    └── manage.py
```

## Main API Routes

### Bookings

- `GET /api/bookings/`
  Farmer booking list.
- `POST /api/bookings/`
  Create booking in `PENDING_PAYMENT`.
- `GET /api/bookings/<id>/`
  Booking detail.
- `DELETE /api/bookings/<id>/`
  Delete unpaid booking as farmer.
- `GET /api/bookings/<id>/payment-status/`
  Booking and payment status snapshot.
- `POST /api/bookings/<id>/mark-delivered/`
  Driver delivery action alias that also triggers payout release logic.
- `GET /api/bookings/<id>/tracking/`
  Booking tracking detail for farmer or assigned driver.
- `POST /api/bookings/<id>/status/`
  Driver marks pickup or delivery.
- `POST /api/bookings/<id>/tracking-updates/`
  Driver live location update for a booking.
- `GET /api/bookings/driver/open/`
  Open bookings visible to a driver.
- `GET /api/bookings/driver/assigned/`
  Accepted bookings for a driver.
- `POST /api/bookings/driver/decision/`
  Driver accepts a booking.

### Maps

- `GET /api/maps/places/search/`
- `GET /api/maps/places/reverse/`
- `GET /api/maps/places/lookup/`
- `POST /api/maps/routes/preview/`

### Transporters

- `GET /api/transporters/me/`
  Driver vehicle/profile setup.
- `POST /api/transporters/me/`
  Save driver vehicle/profile setup.
- `PATCH /api/transporters/me/location/`
  Update live location.

### Payments

- `POST /api/payments/stk-push/`
  Start M-Pesa STK Push for a booking using the booking quote amount.
- `POST /api/payments/mpesa/callback/`
  Daraja callback endpoint.
- `GET /api/payments/<id>/`
  Payment detail for the related farmer, transporter, or admin.
- `GET /api/payments/bookings/<booking_id>/status/`
  Payment snapshot for a booking.

## Example API Payloads

### Create Booking

`POST /api/bookings/`

```json
{
  "produce_name": "Tomatoes",
  "produce_description": "Fresh tomatoes for market",
  "weight_kg": "800.00",
  "pickup_place": {
    "place_id": "11",
    "source": "nominatim",
    "osm_type": "W",
    "osm_id": "11",
    "name": "Farm Gate",
    "address": "Farm Gate, Kiambu",
    "latitude": "-1.292100",
    "longitude": "36.821900"
  },
  "dropoff_place": {
    "place_id": "22",
    "source": "nominatim",
    "osm_type": "W",
    "osm_id": "22",
    "name": "City Market",
    "address": "City Market, Nairobi",
    "latitude": "-1.300000",
    "longitude": "36.800000"
  }
}
```

After booking creation, the farmer completes payment from the dashboard payment modal. The booking remains `pending_payment` until the Daraja callback confirms payment.

### Driver Accept Booking

`POST /api/bookings/driver/decision/`

```json
{
  "booking_id": 12,
  "vehicle_id": 4,
  "action": "accept"
}
```

### Start Booking Payment

`POST /api/payments/stk-push/`

```json
{
  "booking_id": 12,
  "phone_number": "0712345678"
}
```

### Mark Picked Up

`POST /api/bookings/<id>/status/`

```json
{
  "status": "picked_up"
}
```

### Mark Delivered

`POST /api/bookings/<id>/status/`

```json
{
  "status": "delivered"
}
```

### Send Tracking Update

`POST /api/bookings/<id>/tracking-updates/`

```json
{
  "latitude": "-1.295500",
  "longitude": "36.815000",
  "speed_kph": "45.00",
  "notes": "Automatic live location update"
}
```

## Tech Stack

- Django
- Django REST Framework
- PostgreSQL
- Leaflet
- OpenStreetMap / Nominatim / OSRM
- Safaricom Daraja sandbox
- SMTP / Brevo-ready email delivery

## Email And Auth Flow

1. User signs up as `farmer` or `driver`.
2. The system sends an email verification link.
3. Non-staff users must verify their email before signing in.
4. Password reset is available through the email-based reset flow.
5. If a user changes their email address from the dashboard, verification is required again.

## Payment Flow

1. Farmer creates a booking from the map.
2. The system calculates the route and quote.
3. Farmer starts M-Pesa STK Push from the farmer dashboard.
4. Successful callback marks payment as held and booking as `confirmed`.
5. Matching drivers can then see and accept the booking.
6. When delivery is completed, the held payment is released in system payout records.

- Django 6
- Django REST Framework
- SQLite by default, PostgreSQL supported through environment variables
- Leaflet for map UI
- OpenStreetMap tiles
- Nominatim for place search and reverse geocoding
- OSRM for route previews

## External Services

The application relies on public mapping services by default:

- OpenStreetMap tile server for map display
- Nominatim for place search and reverse geocoding
- OSRM for route distance and geometry

These are configurable through environment variables if you want to swap providers or self-host them.

## Local Setup

### Prerequisites

- Python 3
- Virtual environment with project dependencies installed

### Environment

Start from:

- `backend/.env.example`

Create your local file:

```bash
cp backend/.env.example backend/.env
```

Required:

- `DJANGO_SECRET_KEY`

Common optional groups:

- PostgreSQL: `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`
- Maps: `MAPS_USER_AGENT`, `MAPS_TIMEOUT_SECONDS`, `NOMINATIM_SEARCH_URL`, `NOMINATIM_LOOKUP_URL`, `NOMINATIM_REVERSE_URL`, `OSRM_BASE_URL`
- Email: `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL`
- Security: `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `USE_SECURE_COOKIES`, `SECURE_SSL_REDIRECT`, `ENABLE_HSTS`
- Daraja: `MPESA_ENV`, `MPESA_CONSUMER_KEY`, `MPESA_CONSUMER_SECRET`, `MPESA_SHORTCODE`, `MPESA_PASSKEY`, `MPESA_CALLBACK_URL`

## Run Locally

```bash
cd backend
DJANGO_SECRET_KEY=dev-secret-key ../.venv/bin/python manage.py runserver
```

Open:

- App: `http://127.0.0.1:8000/`
- Django admin: `http://127.0.0.1:8000/admin/`

## Run With Docker

From `backend/`:

```bash
docker compose up --build
```

Services:

- Django app: `http://127.0.0.1:8000/`
- PostgreSQL: `localhost:5432`
- Adminer: `http://127.0.0.1:8080/`

Make sure `backend/.env` exists because `docker-compose.yml` reads environment variables from it.
The Docker `web` service now runs migrations automatically before starting the Django server.

## Deployment Notes

- Set a strong production `DJANGO_SECRET_KEY`.
- Set `DEBUG=False` in production.
- Configure `ALLOWED_HOSTS` correctly.
- Set `CSRF_TRUSTED_ORIGINS` for your HTTPS domains.
- Enable `USE_SECURE_COOKIES=True`.
- Enable `SECURE_SSL_REDIRECT=True` once HTTPS is active.
- Enable `ENABLE_HSTS=True` only after HTTPS is confirmed working correctly.
- Prefer PostgreSQL over SQLite in production.
- Use a production WSGI/ASGI server instead of Django `runserver`.
- If map usage grows, consider self-hosting or replacing public Nominatim/OSRM endpoints.
- Serve static files through a proper web server or static file pipeline.
- Use a verified Brevo sender/domain before enabling real email delivery.
- Use Daraja sandbox credentials and a reachable callback URL when testing payments.

## Create Admin User

```bash
cd backend
DJANGO_SECRET_KEY=dev-secret-key ../.venv/bin/python manage.py createsuperuser
```

Login uses:

- `phone_number`
- `password`

Admin users should have:

- `is_staff=True`
- `is_superuser=True`
- role `admin`

## Tests

Run all tests:

```bash
cd backend
DJANGO_SECRET_KEY=test-secret-key ../.venv/bin/python manage.py test
```

Run a specific app:

```bash
cd backend
DJANGO_SECRET_KEY=test-secret-key ../.venv/bin/python manage.py test booking.tests
```

## Example User Flows

### Farmer Flow

1. Log in as a farmer.
2. Verify email first if this is a new account.
3. Select pickup and dropoff on the map.
4. Enter produce details and M-Pesa phone number.
5. Create the booking and complete the STK push.
6. Wait for a driver to accept.
7. Use `Track live` to follow the delivery route.
8. If an unpaid booking is wrong, delete it and create a new one.

### Driver Flow

1. Log in as a driver.
2. Verify email first if this is a new account.
3. Configure vehicle details from the `Vehicle Profile` modal.
4. Allow browser location access.
5. Accept an open booking that matches the vehicle.
6. Travel to the pickup point and tap `Picked up`.
7. Move away from pickup so the system switches to `In transit`.
8. Reach dropoff and tap `Delivered`.

### Admin Flow

1. Log in with a staff/superuser account.
2. Open `/accounts/admin-dashboard/`.
3. Update transport rates by vehicle type.
4. Review booking counts and revenue summaries.

## Current Limitations

- Background location tracking is not available once the browser is closed.
- Driver tracking depends on browser GPS permission.
- Public map providers may rate-limit heavy traffic if left on default hosted endpoints.
- The UI is designed for operational use and intentionally hides low-level tracking/status internals from users.
- Real email delivery depends on valid SMTP credentials and a verified sender/domain.
- Daraja sandbox does not implement true escrow. Release is simulated in application records when delivery is completed.

## Troubleshooting

- `The DJANGO_SECRET_KEY environment variable is not set.`
  Set `DJANGO_SECRET_KEY` before running the backend.
- Verification or password-reset emails do not arrive.
  Check SMTP/Brevo env vars, use a verified sender domain, and inspect Brevo transactional logs.
- STK push does not arrive on the phone.
  Check Daraja sandbox credentials, callback URL, phone format, and application logs for token or STK push errors.
- Admin user cannot be created or cannot log in.
  Run migrations first, then create the admin using `createsuperuser`.
- `column accounts_customuser.is_email_verified does not exist`
  Run migrations or restart the Docker app so startup migrations are applied.
- Driver cannot see new bookings.
  Check browser location permission, vehicle availability, vehicle type, and vehicle capacity.
- Driver cannot mark `picked_up`.
  The driver must first arrive at the pickup point.
- Driver cannot mark `delivered`.
  The driver must first arrive at the delivery point.
- Farmer cannot see live driver movement.
  Tracking becomes visible only after pickup starts and depends on driver location sharing.
- Map search or route preview fails.
  Check internet access and configured map service URLs.

## Suggested Screenshots

If you are preparing documentation or a project report, useful screenshots would be:

- Farmer map booking page
- Driver open bookings dashboard
- Driver live route tracking map
- Farmer live tracking map
- Admin pricing and revenue dashboard

## Notes

- Driver live tracking depends on browser location permission.
- Farmer live tracking becomes visible after pickup starts.
- The UI intentionally hides raw technical tracking/status data from farmers and drivers.
