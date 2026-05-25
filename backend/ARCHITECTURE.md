# Architecture Document

## 1. Overview

FreshHaul is a server-rendered Django application with REST API endpoints for booking, mapping, payment, and transporter workflows. The system connects farmers with drivers for produce delivery, calculates route-based pricing, and uses M-Pesa STK Push for payment initiation.

The implementation combines:

- Django templates for the main web UI
- Django REST Framework for same-origin API endpoints
- relational persistence through Django ORM
- third-party map and payment integrations

## 2. Architectural Goals

- Keep authentication, booking, payments, and transporter logic separated by app boundary.
- Support map-assisted booking with deterministic backend pricing.
- Enforce role-based access and booking lifecycle rules in server-side code.
- Keep the web application deployable in both local and containerized environments.
- Maintain a structure that can later support async workers, richer notifications, and mobile clients.

## 3. High-Level Architecture

FreshHaul follows a layered client-server architecture.

### Presentation Layer

- Django templates under `backend/templates/`
- role-specific dashboards for farmers, drivers, and admins
- browser-side JavaScript for map rendering, polling, and UI state

### Application Layer

- Django app views for page rendering and form flows
- DRF views for booking, payment, mapping, and transporter APIs
- domain rules in serializers, models, utilities, and services

### Data Layer

- Django ORM models
- SQLite fallback for local development
- PostgreSQL when PostgreSQL environment variables are supplied

### Integration Layer

- Nominatim search, lookup, and reverse geocoding
- OSRM route calculation
- OpenStreetMap tile usage in the frontend
- Safaricom Daraja STK Push and callback handling
- SMTP email delivery for verification and password reset flows

## 4. Runtime Topology

```text
Browser
  |
  | HTTPS / session-authenticated requests
  v
Django templates + DRF views
  |
  | ORM
  v
SQLite or PostgreSQL
  |
  +--> Nominatim / OSRM
  +--> Daraja API
  +--> SMTP provider
```

In Docker development, the stack also includes:

- a `web` container for Django
- a `db` container for PostgreSQL
- an optional `adminer` container for database inspection

## 5. Django App Boundaries

### `accounts`

Responsibilities:

- custom user model
- login and signup
- email verification
- profile updates
- role-based home/dashboard routing
- admin dashboard and CSV report exports

Key types:

- `CustomUser`
- `HomeView`
- `AdminDashboardView`

### `booking`

Responsibilities:

- booking entity and lifecycle
- driver matching
- status history
- tracking updates
- role-constrained booking API endpoints

Key types:

- `Booking`
- `BookingStatus`
- `BookingCreateSerializer`
- `BookingDecisionView`
- `BookingStatusUpdateView`

### `transporters`

Responsibilities:

- transporter profile
- vehicle management
- transport pricing rules and weight bands
- driver location updates

Key types:

- `TransporterProfile`
- `Vehicle`
- `TransportPricing`

### `payments`

Responsibilities:

- STK Push initiation
- Daraja callback handling
- payment status history
- held payment and release tracking
- payout records for drivers

Key types:

- `Payment`
- `TransporterPayout`
- `StkPushInitiateView`
- `MpesaCallbackView`

### `maps`

Responsibilities:

- place search
- place lookup
- reverse geocoding
- route preview abstraction

## 6. Core Domain Model

### Users

The system uses a custom auth model where:

- `phone_number` is the login username
- `email` is unique and verification-backed
- `role` is one of `farmer`, `driver`, or `admin`

### Bookings

Each booking stores:

- farmer
- optional assigned transporter
- optional assigned vehicle
- produce details
- pickup and dropoff place identifiers and coordinates
- route distance, duration, and geometry
- derived vehicle type requirement
- quoted price
- booking status and booking payment status

### Driver Assets

Driver operations are split into:

- `TransporterProfile` for company and current location
- `Vehicle` for registration, type, capacity, and availability

### Payments

Payment tracking is separated into:

- `Payment` for STK Push, callback, receipt, held, and released state
- `TransporterPayout` for delivery-linked payout release state
- `PaymentStatusHistory` for auditability

## 7. Main Request Flows

### Public Landing Flow

1. Anonymous user loads `/`.
2. `HomeView` returns `accounts/landing.html`.
3. Landing metrics are built from bookings and registered driver counts.

### Farmer Booking Flow

1. Farmer creates booking through dashboard UI.
2. Frontend calls `/api/maps/...` and `/api/bookings/`.
3. `BookingCreateSerializer` validates weight and resolves route details.
4. Booking is created in `pending_payment`.
5. Farmer initiates `/api/payments/stk-push/`.
6. Daraja callback updates payment and booking state.
7. Booking becomes visible to matching drivers once paid and confirmed.

### Driver Dispatch Flow

1. Driver updates profile and vehicles through `/api/transporters/me/`.
2. Driver shares location through `/api/transporters/me/location/`.
3. Driver loads `/api/bookings/driver/open/`.
4. Backend filters by available vehicle types and progressive geographic matches.
5. Driver accepts via `/api/bookings/driver/decision/`.
6. Backend assigns transporter and vehicle, marks booking `accepted`, and locks the vehicle.

### Delivery Update Flow

1. Driver submits pickup or delivery action.
2. Backend checks current status transition rules.
3. Backend checks driver location proximity.
4. Booking status and status history are updated.
5. Payment release logic runs when delivery completion qualifies.

## 8. Matching And Pricing Logic

### Vehicle Resolution

The required vehicle type is not user-entered. It is derived from booking weight through configured pricing bands in `TransportPricing` or the seeded defaults.

### Pricing

Quoted booking price is computed as:

`price_per_km * route_distance_km`

The admin dashboard can modify:

- `vehicle_type`
- `price_per_km`
- `min_weight_kg`
- `max_weight_kg`

### Driver Matching

Matching is progressive:

- open jobs must already be `confirmed`
- driver must have an available vehicle with a compatible type
- if driver location exists, the matching service progressively expands the search radius

## 9. Security Model

### Authentication

- Django session authentication is the default auth mechanism.
- DRF uses `SessionAuthentication`.
- Write requests remain CSRF protected.

### Authorization

- DRF permission classes enforce `farmer` and `driver` role restrictions.
- Staff-only page access uses Django mixins.
- Object-level visibility is implemented in querysets and per-view checks.

### Deployment Security Controls

Security-related settings are environment-driven in `core/settings.py`, including:

- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`
- secure cookies
- SSL redirect
- HSTS
- proxy SSL header support
- clickjacking and MIME sniffing protections

## 10. Persistence Strategy

Database selection:

- PostgreSQL is used when all required PostgreSQL env vars are present.
- Otherwise the app falls back to SQLite.

This gives:

- simpler local startup
- easier Dockerized PostgreSQL deployment
- minimal branching in application logic

## 11. Deployment Model

### Local

- install dependencies from `requirements.txt`
- export `DJANGO_SECRET_KEY`
- run migrations
- start `runserver`

### Docker

The Docker image:

- installs Python and build dependencies
- installs Python requirements
- copies the project into `/app`
- starts `entrypoint.sh`

`entrypoint.sh`:

1. runs `python manage.py migrate --noinput`
2. starts `python manage.py runserver 0.0.0.0:8000`

The `docker-compose.yml` file defines:

- `web`
- `db`
- `adminer`

## 12. Observed Constraints And Gaps

- There is no configured OpenAPI or Swagger route even though `drf-spectacular` is installed.
- The default pricing weight bands contain a large gap between `pickup` and `truck`; bookings in that interval will require admin pricing changes to be accepted by vehicle resolution logic.
- The web UI is tightly coupled to same-origin session auth, which is fine for the current architecture but not yet ideal for third-party API clients.

## 13. Extension Paths

Likely next architectural improvements:

- add OpenAPI schema exposure
- move long-running payment or notification tasks to async workers
- add audit/event streams for operational analytics
- add push notifications or SMS delivery state alerts
- introduce a dedicated mobile tracking client for drivers
