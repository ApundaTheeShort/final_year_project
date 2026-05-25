# API Reference

This document describes the backend API exposed by FreshHaul.

Base local URL:

`http://127.0.0.1:8000`

API namespaces:

- `/api/bookings/`
- `/api/maps/`
- `/api/payments/`
- `/api/transporters/`

## Authentication

The API uses Django session authentication.

- Login page: `/accounts/login/`
- Signup page: `/accounts/signup/`
- Authenticated API requests use the browser session cookie.
- CSRF protection applies to session-authenticated write requests.

Important auth rules:

- Non-staff users must verify email before login.
- Public signup only supports `farmer` and `driver`.
- Most API endpoints require authentication.
- DRF throttling is enabled for both anonymous and authenticated traffic.

## Roles

- `farmer`
  Booking creation, booking listing, booking deletion while unpaid, payment initiation, booking tracking.
- `driver`
  Vehicle/profile setup, live location updates, open jobs, assigned jobs, accept/decline decisions, pickup/delivery updates.
- `admin`
  Accesses dashboards and Django admin. No admin-only REST namespace is currently exposed.

## Common Error Behavior

- `400 Bad Request`
  Validation or business-rule failure.
- `401 Unauthorized`
  Not logged in.
- `403 Forbidden`
  Logged in without required role.
- `404 Not Found`
  Resource not visible to the current user.
- `204 No Content`
  Successful delete.

## Core Domain Rules

- Only farmers can create bookings.
- Bookings start in `pending_payment`.
- Drivers only see open jobs in `confirmed`.
- Drivers can only accept jobs that are already paid and that match their dispatch profile.
- Farmers can only delete bookings in `pending_payment`.
- Pickup and delivery actions are location-gated against the driver profile coordinates.
- Vehicle type is derived from booking weight, not chosen manually by the farmer.

## Status Reference

### Booking Status

- `pending_payment`
- `confirmed`
- `accepted`
- `declined`
- `picked_up`
- `in_transit`
- `delivered`
- `completed`
- `cancelled`

### Booking Payment Status

- `unpaid`
- `pending`
- `paid`

### Payment Status

- `pending`
- `stk_push_sent`
- `paid_held`
- `failed`
- `cancelled`
- `released`

### Payout Status

- `pending_release`
- `released`
- `failed`

## Accounts Web Endpoints

These are not under `/api/`, but they are part of the authentication and account flow:

- `GET /`
- `GET|POST /accounts/signup/`
- `GET|POST /accounts/login/`
- `GET|POST /accounts/profile/`
- `GET /accounts/verification-sent/`
- `GET|POST /accounts/verify-email/`
- `GET /accounts/verify-email/<uidb64>/<token>/`
- `GET|POST /accounts/resend-verification/`

## Booking Endpoints

### List Farmer Bookings

`GET /api/bookings/`

Role:

- `farmer`

Returns the authenticated farmer's bookings.

### Create Booking

`POST /api/bookings/`

Role:

- `farmer`

Request body:

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

Response includes derived booking fields such as:

- `search_radius_km`
- `estimated_distance_km`
- `estimated_duration_minutes`
- `route_geometry`
- `vehicle_type_required`
- `quoted_price`
- `status`
- `payment_status`
- `matched_transporters`

Typical created status values:

- `status = "pending_payment"`
- `payment_status = "unpaid"`

### Get Booking Detail

`GET /api/bookings/<id>/`

Roles:

- `farmer` for own booking
- `driver` for assigned booking

Returns:

- booking core fields
- pickup and dropoff place objects
- route data
- assigned vehicle
- transporter profile when assigned
- status history
- tracking updates

### Delete Booking

`DELETE /api/bookings/<id>/`

Role:

- `farmer`

Rule:

- Only allowed when the booking status is `pending_payment`.

Success:

- `204 No Content`

### Get Nearby Transporter Matches

`GET /api/bookings/<booking_id>/nearby-transporters/`

Role:

- `farmer`

Returns the progressive matching result used to identify compatible transporters for the booking.

### Get Booking Tracking Detail

`GET /api/bookings/<booking_id>/tracking/`

Roles:

- `farmer` for own booking
- assigned `driver`

Returns booking detail with status history and tracking updates.

### Get Booking Payment Snapshot

`GET /api/bookings/<booking_id>/payment-status/`

Roles:

- `farmer`
- assigned `driver`
- `admin`

Returns:

- booking `status`
- booking `payment_status`
- `quoted_price`
- nested payment detail if present

### Update Booking Status

`POST /api/bookings/<booking_id>/status/`

Role:

- assigned `driver`

Allowed request bodies:

```json
{
  "status": "picked_up"
}
```

```json
{
  "status": "delivered"
}
```

Optional field:

```json
{
  "status": "picked_up",
  "notes": "Loaded and leaving the farm."
}
```

Rules:

- `picked_up` is only valid from `accepted`
- `delivered` is only valid from `in_transit`
- driver location must be available
- driver must be near the required endpoint

### Mark Delivered Shortcut

`POST /api/bookings/<booking_id>/mark-delivered/`

Role:

- assigned `driver`

This endpoint internally submits the same delivery transition as `/status/` with `status = delivered`.

### Create Tracking Update

`POST /api/bookings/<booking_id>/tracking-updates/`

Role:

- assigned `driver`

Request body:

```json
{
  "latitude": "-1.295500",
  "longitude": "36.815000",
  "speed_kph": "45.00",
  "notes": "Heading to city market"
}
```

Success:

- `201 Created`

### List Open Driver Bookings

`GET /api/bookings/driver/open/`

Role:

- `driver`

Returns paid and confirmed bookings whose required vehicle class matches one of the driver's available vehicles. If the driver profile has location coordinates, progressive geographic matching is also applied.

### List Assigned Driver Bookings

`GET /api/bookings/driver/assigned/`

Role:

- `driver`

Returns bookings assigned to the authenticated driver.

### Driver Accept Or Decline Decision

`POST /api/bookings/driver/decision/`

Role:

- `driver`

Request body to accept:

```json
{
  "booking_id": 12,
  "vehicle_id": 4,
  "action": "accept"
}
```

Request body to decline:

```json
{
  "booking_id": 12,
  "action": "decline"
}
```

Acceptance rules:

- booking must be `confirmed`
- booking payment must already be `paid`
- chosen vehicle must belong to the current driver
- vehicle must be available
- vehicle type must match the booking requirement
- vehicle capacity must be sufficient

## Map Endpoints

### Search Places

`GET /api/maps/places/search/`

Used for forward search against the configured search provider.

### Lookup Places

`GET /api/maps/places/lookup/`

Used to resolve place details from a known place reference.

### Reverse Geocode

`GET /api/maps/places/reverse/`

Used to resolve a human-readable location from coordinates.

### Preview Route

`POST /api/maps/routes/preview/`

Used to get route distance, duration, and geometry between two coordinates.

## Transporter Endpoints

### Get Driver Profile And Vehicles

`GET /api/transporters/me/`

Role:

- `driver`

Returns:

- transporter profile
- current vehicles list

### Create Or Update Driver Profile And Vehicles

`POST /api/transporters/me/`

Role:

- `driver`

Request body shape:

```json
{
  "profile": {
    "company_name": "Village Hauliers",
    "current_latitude": "-1.292100",
    "current_longitude": "36.821900"
  },
  "vehicles": [
    {
      "registration_number": "KDB321B",
      "vehicle_type": "pickup",
      "capacity_kg": "2000.00",
      "is_available": true
    }
  ]
}
```

Notes:

- existing vehicle records can be updated by including `id`
- omitted existing vehicles are deleted during sync
- registration numbers must be unique
- vehicle type must exist in configured transport pricing

### Update Driver Live Location

`PATCH /api/transporters/me/location/`

Role:

- `driver`

Used by the dashboard to keep the driver's current coordinates fresh for matching and location-gated delivery actions.

## Payment Endpoints

### Initiate STK Push

`POST /api/payments/stk-push/`

Role:

- `farmer`

Request body:

```json
{
  "booking_id": 12,
  "phone_number": "0712345678"
}
```

Rules:

- booking must belong to the authenticated farmer
- cancelled bookings cannot be paid
- already paid bookings cannot be paid again
- phone number is normalized to Kenyan format

Success response includes:

- nested payment detail
- raw Daraja initiation response
- `callback_url_hint`

### M-Pesa Callback

`POST /api/payments/mpesa/callback/`

Auth:

- public

Notes:

- CSRF exempt
- used by Daraja to update payment state

Success response:

```json
{
  "ResultCode": 0,
  "ResultDesc": "Accepted",
  "payment_id": 15
}
```

### Get Payment Detail

`GET /api/payments/<id>/`

Roles:

- related `farmer`
- related `driver`
- `admin`

Returns:

- payment identifiers
- amount
- phone number
- receipt and callback metadata
- payment status history
- payout record when available

### Get Payment Status By Booking

`GET /api/payments/bookings/<booking_id>/status/`

Roles:

- related `farmer`
- related `driver`
- `admin`

Returns booking-level payment snapshot with nested payment detail.

## Route Summary

```text
/api/bookings/
/api/bookings/<id>/
/api/bookings/<booking_id>/nearby-transporters/
/api/bookings/<booking_id>/status/
/api/bookings/<booking_id>/mark-delivered/
/api/bookings/<booking_id>/tracking/
/api/bookings/<booking_id>/payment-status/
/api/bookings/<booking_id>/tracking-updates/
/api/bookings/driver/open/
/api/bookings/driver/assigned/
/api/bookings/driver/decision/

/api/maps/places/search/
/api/maps/places/lookup/
/api/maps/places/reverse/
/api/maps/routes/preview/

/api/payments/stk-push/
/api/payments/mpesa/callback/
/api/payments/<id>/
/api/payments/bookings/<booking_id>/status/

/api/transporters/me/
/api/transporters/me/location/
```
