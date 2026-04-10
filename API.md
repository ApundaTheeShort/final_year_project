# API Reference

Backend API reference for the produce transport platform.

Base URL examples assume local development:

`http://127.0.0.1:8000`

Most API routes are under:

`/api/`

## Authentication

The project uses Django session authentication.

- Web login: `/accounts/login/`
- API auth: session-based after login
- Public signup: `/accounts/signup/`
- Email verification notice: `/accounts/verification-sent/`
- Email verification confirm: `/accounts/verify-email/<uidb64>/<token>/`
- Resend verification: `/accounts/resend-verification/`

Notes:

- Non-staff users must verify their email before they can sign in.
- Changing the account email triggers a new verification email.
- `BasicAuthentication` and token auth are not used by default.
- Most API endpoints require an authenticated user and are throttled by DRF.

## Roles

- `farmer`
  Can create, list, view, track, and delete pending bookings.
- `driver`
  Can configure vehicle details, update live location, accept bookings, mark pickup/delivery, and send tracking updates.
- `admin`
  Uses app dashboards and Django admin, not special API-only endpoints.

## Common Response Notes

- Validation errors usually return `400 Bad Request`
- Unauthorized access returns `401` or `403`
- Missing resources return `404`
- Successful delete returns `204 No Content`

## Booking Rules Enforced by API

- Farmers do not provide a search radius.
- The system automatically searches outward for matching drivers.
- Farmers can delete only `pending` bookings.
- Drivers can accept only matching bookings for their available vehicle.
- Drivers can mark `picked_up` only after arriving at pickup.
- Drivers can mark `delivered` only after arriving at dropoff.
- `in_transit` is set automatically after the driver leaves pickup with the goods.
- Farmers and drivers see technical tracking data hidden in the UI even though tracking endpoints still return operational data.

## Booking Status Values

- `pending`
- `accepted`
- `declined`
- `picked_up`
- `in_transit`
- `delivered`
- `cancelled`

## Bookings

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

Response includes:

- generated booking id
- resolved pickup/dropoff fields
- route distance and duration
- route geometry
- vehicle type required
- quoted price
- system-selected search radius
- matched transporters

Example response:

```json
{
  "id": 12,
  "produce_name": "Tomatoes",
  "produce_description": "Fresh tomatoes for market",
  "weight_kg": "800.00",
  "pickup_place_id": "11",
  "pickup_place_source": "nominatim",
  "pickup_address": "Farm Gate, Kiambu",
  "pickup_latitude": "-1.292100",
  "pickup_longitude": "36.821900",
  "dropoff_place_id": "22",
  "dropoff_place_source": "nominatim",
  "dropoff_address": "City Market, Nairobi",
  "dropoff_latitude": "-1.300000",
  "dropoff_longitude": "36.800000",
  "search_radius_km": "50.00",
  "estimated_distance_km": "12.40",
  "estimated_duration_minutes": "21.00",
  "route_geometry": {
    "type": "LineString",
    "coordinates": [[36.8219, -1.2921], [36.8, -1.3]]
  },
  "vehicle_type_required": "pickup",
  "quoted_price": "2480.00",
  "status": "pending",
  "matched_transporters": [
    {
      "transporter_id": 7,
      "transporter_name": "Driver Two",
      "company_name": "Village Hauliers",
      "distance_km": "0.00",
      "estimated_price": "2480.00",
      "vehicle": {
        "id": 4,
        "registration_number": "KDB321B",
        "vehicle_type": "pickup",
        "capacity_kg": "2000.00",
        "is_available": true
      }
    }
  ]
}
```

### Get Booking Detail

`GET /api/bookings/<id>/`

Roles:

- `farmer` for own booking
- `driver` for assigned booking

Example response:

```json
{
  "id": 12,
  "produce_name": "Tomatoes",
  "produce_description": "Fresh tomatoes for market",
  "weight_kg": "800.00",
  "pickup_place": {
    "place_id": "11",
    "source": "nominatim",
    "address": "Farm Gate, Kiambu",
    "latitude": "-1.292100",
    "longitude": "36.821900"
  },
  "dropoff_place": {
    "place_id": "22",
    "source": "nominatim",
    "address": "City Market, Nairobi",
    "latitude": "-1.300000",
    "longitude": "36.800000"
  },
  "search_radius_km": "50.00",
  "estimated_distance_km": "12.40",
  "estimated_duration_minutes": "21.00",
  "vehicle_type_required": "pickup",
  "quoted_price": "2480.00",
  "status": "accepted",
  "accepted_at": "2026-03-22T08:14:00Z",
  "delivered_at": null,
  "created_at": "2026-03-22T08:00:00Z",
  "updated_at": "2026-03-22T08:14:00Z",
  "vehicle": {
    "id": 4,
    "registration_number": "KDB321B",
    "vehicle_type": "pickup",
    "capacity_kg": "2000.00",
    "is_available": false
  },
  "transporter_profile": {
    "id": 3,
    "company_name": "Village Hauliers",
    "current_latitude": "-1.292100",
    "current_longitude": "36.821900",
    "last_location_update": "2026-03-22T08:14:00Z"
  }
}
```

### Delete Pending Booking

`DELETE /api/bookings/<id>/`

Role:

- `farmer`

Allowed only when booking status is `pending`.

Successful response:

- `204 No Content`

### Get Booking Tracking Detail

`GET /api/bookings/<booking_id>/tracking/`

Roles:

- `farmer` for own booking
- assigned `driver`

Returns booking detail plus route and tracking data used by the dashboards.

Notes:

- Farmers use this for live tracking after booking acceptance.
- Drivers use this for assigned-trip route and progress display.

### Update Booking Status

`POST /api/bookings/<booking_id>/status/`

Role:

- assigned `driver`

Request body for pickup:

```json
{
  "status": "picked_up"
}
```

Request body for delivery:

```json
{
  "status": "delivered"
}
```

Notes:

- `in_transit` is not manually posted by the driver.
- Pickup and delivery are location-gated by backend validation.

Successful response example:

```json
{
  "id": 12,
  "status": "picked_up",
  "accepted_at": "2026-03-22T08:14:00Z",
  "delivered_at": null
}
```

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
  "notes": "Automatic live location update"
}
```

Notes:

- Also updates the driver's current location.
- Can automatically switch `picked_up` to `in_transit` once the driver leaves pickup.

Successful response example:

```json
{
  "id": 55,
  "latitude": "-1.295500",
  "longitude": "36.815000",
  "speed_kph": "45.00",
  "notes": "Automatic live location update",
  "created_at": "2026-03-22T08:20:00Z"
}
```

## Driver Booking Queue

### List Open Bookings For Driver

`GET /api/bookings/driver/open/`

Role:

- `driver`

Returns pending bookings that match:

- vehicle type
- vehicle capacity
- available vehicle
- location-based discovery

If the driver has not granted location yet, matching may be limited until live location is available.

### List Assigned Bookings For Driver

`GET /api/bookings/driver/assigned/`

Role:

- `driver`

Returns bookings currently assigned to the authenticated driver.

### Accept Booking

`POST /api/bookings/driver/decision/`

Role:

- `driver`

Request body:

```json
{
  "booking_id": 12,
  "vehicle_id": 4,
  "action": "accept"
}
```

Notes:

- The selected vehicle must belong to the driver.
- The selected vehicle must be available.
- The selected vehicle must match required type and capacity.

Successful response example:

```json
{
  "id": 12,
  "status": "accepted",
  "quoted_price": "2480.00",
  "accepted_at": "2026-03-22T08:14:00Z"
}
```

## Maps

### Search Places

`GET /api/maps/places/search/?q=<query>`

Authenticated endpoint.

Example:

`GET /api/maps/places/search/?q=City%20Market`

Successful response example:

```json
{
  "results": [
    {
      "place_id": "123",
      "source": "nominatim",
      "osm_type": "W",
      "osm_id": "456",
      "name": "City Market",
      "address": "City Market, Nairobi",
      "latitude": "-1.286389",
      "longitude": "36.817223"
    }
  ]
}
```

### Lookup Place

`GET /api/maps/places/lookup/?osm_type=<type>&osm_id=<id>`

Authenticated endpoint.

### Reverse Geocode

`GET /api/maps/places/reverse/?latitude=<lat>&longitude=<lng>`

Authenticated endpoint.

### Preview Route

`POST /api/maps/routes/preview/`

Authenticated endpoint.

Request body:

```json
{
  "pickup_place": {
    "address": "Farm Gate, Kiambu",
    "name": "Farm Gate",
    "latitude": "-1.292100",
    "longitude": "36.821900",
    "place_id": "11",
    "source": "nominatim",
    "osm_type": "W",
    "osm_id": "11"
  },
  "dropoff_place": {
    "address": "City Market, Nairobi",
    "name": "City Market",
    "latitude": "-1.300000",
    "longitude": "36.800000",
    "place_id": "22",
    "source": "nominatim",
    "osm_type": "W",
    "osm_id": "22"
  }
}
```

Response includes:

- pickup and dropoff payloads
- `distance_km`
- `duration_minutes`
- route `geometry`

## Transporters

### Get Driver Profile And Vehicles

`GET /api/transporters/me/`

Role:

- `driver`

Returns:

- transporter profile
- driver vehicles

Example response:

```json
{
  "profile": {
    "id": 3,
    "company_name": "Village Hauliers",
    "current_latitude": "-1.292100",
    "current_longitude": "36.821900",
    "last_location_update": "2026-03-22T08:14:00Z"
  },
  "vehicles": [
    {
      "id": 4,
      "registration_number": "KDB321B",
      "vehicle_type": "pickup",
      "capacity_kg": "2000.00",
      "is_available": true
    }
  ]
}
```

### Create Or Update Driver Profile And Vehicles

`POST /api/transporters/me/`

Role:

- `driver`

Request body:

```json
{
  "profile": {
    "company_name": "Fast Wheels",
    "current_latitude": "-1.292100",
    "current_longitude": "36.821900"
  },
  "vehicles": [
    {
      "registration_number": "KDA123A",
      "vehicle_type": "pickup",
      "capacity_kg": "1500.00",
      "is_available": true
    }
  ]
}
```

Notes:

- Transport pricing is not driver-controlled.
- Pricing is set by admin by vehicle type.
- The dashboard uses this endpoint for the vehicle profile modal.

### Update Driver Live Location

`PATCH /api/transporters/me/location/`

Role:

- `driver`

Request body:

```json
{
  "current_latitude": "-1.292100",
  "current_longitude": "36.821900"
}
```

## Admin Functions

The admin dashboard is page-based, not API-based.

- App dashboard: `/accounts/admin-dashboard/`
- Django admin: `/admin/`

Pricing is managed through:

- in-app admin dashboard
- Django admin `TransportPricing`

## Email Verification And Password Reset

### Signup

`POST /accounts/signup/`

Creates a `farmer` or `driver` account and sends an email verification link.

### Verify Email

`GET /accounts/verify-email/<uidb64>/<token>/`

Marks the account email as verified when the token is valid.

### Resend Verification

`GET /accounts/resend-verification/`
`POST /accounts/resend-verification/`

Accepts an email address and sends a fresh verification link if the account exists and is not yet verified.

### Password Reset

Password reset uses Django’s standard account routes:

- `/accounts/password_reset/`
- `/accounts/password_reset/done/`
- `/accounts/reset/<uidb64>/<token>/`
- `/accounts/reset/done/`

Real delivery depends on SMTP configuration, typically Brevo in this project.

## Troubleshooting

### Driver Cannot See Open Bookings

Check:

- driver is logged in
- vehicle exists
- vehicle is available
- vehicle type matches booking
- vehicle capacity is sufficient
- browser location permission is granted

### Driver Cannot Mark Pickup

The driver must first arrive at pickup and allow live location updates.

### Driver Cannot Mark Delivered

The driver must first arrive at the dropoff point and allow live location updates.

### Farmer Cannot See Live Tracking

Check:

- booking has been accepted
- pickup has started
- driver browser location sharing is active

### Verification Email Does Not Arrive

Check:

- SMTP env vars are present
- `DEFAULT_FROM_EMAIL` is a verified Brevo sender/domain
- Brevo transactional logs show delivery activity
- you are opening the app from `localhost` or a real HTTPS origin rather than `0.0.0.0`

## Error Response Examples

### Generic Validation Error

```json
{
  "non_field_errors": [
    "Request failed."
  ]
}
```

### Driver Tries Pickup Too Early

```json
{
  "non_field_errors": [
    "Arrive at the pickup location before marking this booking as picked up."
  ]
}
```

### Driver Tries Delivery Too Early

```json
{
  "non_field_errors": [
    "Arrive at the delivery location before marking this booking as delivered."
  ]
}
```

### Vehicle Capacity Mismatch

```json
{
  "non_field_errors": [
    "Vehicle capacity is too small for this booking."
  ]
}
```

### Missing Vehicle On Accept

```json
{
  "vehicle_id": [
    "This field is required when accepting a booking."
  ]
}
```

## Error Matrix

| Endpoint | Condition | Status |
|---|---|---:|
| `POST /api/bookings/` | Invalid place or payload | `400` |
| `DELETE /api/bookings/<id>/` | Booking not pending | `400` |
| `DELETE /api/bookings/<id>/` | Not owner | `404` |
| `POST /api/bookings/driver/decision/` | Booking not found | `400` |
| `POST /api/bookings/driver/decision/` | Vehicle missing/unavailable | `400` |
| `POST /api/bookings/<id>/status/` | Not at pickup/dropoff yet | `400` |
| `POST /api/bookings/<id>/status/` | Invalid status transition | `400` |
| `POST /api/bookings/<id>/tracking-updates/` | Not assigned driver | `404` |
| Any protected route | Not logged in | `401/403` |

## Integration Sequence

### Farmer Booking To Delivery

1. `POST /api/bookings/`
2. Driver sees booking with `GET /api/bookings/driver/open/`
3. Driver accepts with `POST /api/bookings/driver/decision/`
4. Driver arrives and posts `picked_up`
5. Driver sends tracking updates
6. System changes booking to `in_transit` after departure from pickup
7. Driver arrives and posts `delivered`
8. Farmer polls `GET /api/bookings/` and `GET /api/bookings/<id>/tracking/`

## Curl Examples

These examples assume:

- app is running locally at `http://127.0.0.1:8000`
- you already have a valid Django session cookie
- `csrftoken` and `sessionid` are available

Example cookie usage:

```bash
export BASE_URL=http://127.0.0.1:8000
export CSRF_TOKEN=your-csrf-token
export SESSION_ID=your-session-id
```

### Create Booking

```bash
curl -X POST "$BASE_URL/api/bookings/" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $CSRF_TOKEN" \
  -H "Cookie: csrftoken=$CSRF_TOKEN; sessionid=$SESSION_ID" \
  -d '{
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
  }'
```

### List Farmer Bookings

```bash
curl "$BASE_URL/api/bookings/" \
  -H "Cookie: csrftoken=$CSRF_TOKEN; sessionid=$SESSION_ID"
```

### Accept Booking As Driver

```bash
curl -X POST "$BASE_URL/api/bookings/driver/decision/" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $CSRF_TOKEN" \
  -H "Cookie: csrftoken=$CSRF_TOKEN; sessionid=$SESSION_ID" \
  -d '{
    "booking_id": 12,
    "vehicle_id": 4,
    "action": "accept"
  }'
```

### Mark Picked Up

```bash
curl -X POST "$BASE_URL/api/bookings/12/status/" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $CSRF_TOKEN" \
  -H "Cookie: csrftoken=$CSRF_TOKEN; sessionid=$SESSION_ID" \
  -d '{
    "status": "picked_up"
  }'
```

### Send Tracking Update

```bash
curl -X POST "$BASE_URL/api/bookings/12/tracking-updates/" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $CSRF_TOKEN" \
  -H "Cookie: csrftoken=$CSRF_TOKEN; sessionid=$SESSION_ID" \
  -d '{
    "latitude": "-1.295500",
    "longitude": "36.815000",
    "speed_kph": "45.00",
    "notes": "Automatic live location update"
  }'
```

### Mark Delivered

```bash
curl -X POST "$BASE_URL/api/bookings/12/status/" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $CSRF_TOKEN" \
  -H "Cookie: csrftoken=$CSRF_TOKEN; sessionid=$SESSION_ID" \
  -d '{
    "status": "delivered"
  }'
```

### Update Driver Location

```bash
curl -X PATCH "$BASE_URL/api/transporters/me/location/" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $CSRF_TOKEN" \
  -H "Cookie: csrftoken=$CSRF_TOKEN; sessionid=$SESSION_ID" \
  -d '{
    "current_latitude": "-1.292100",
    "current_longitude": "36.821900"
  }'
```

### Search Map Places

```bash
curl "$BASE_URL/api/maps/places/search/?q=City%20Market" \
  -H "Cookie: csrftoken=$CSRF_TOKEN; sessionid=$SESSION_ID"
```

## Frontend Integration Notes

### Authentication

- Browser-based frontend should rely on session authentication.
- Send requests with credentials included.
- Include CSRF token for `POST`, `PATCH`, and `DELETE`.

### Recommended UI Polling

- Farmer booking list: every `10s`
- Farmer active tracking view: every `10s`
- Driver open/assigned bookings: every `10-15s`
- Driver live location updates: continuous browser geolocation watch

### Key UI Behaviors

- After farmer booking creation, clear all form and map-selection state.
- Show human-friendly messages instead of raw API validation JSON.
- Hide raw technical tracking/status history from farmers and drivers.
- Show farmer live tracking only after pickup starts.
- For driver pickup/delivery failures, use a modal/popup rather than inline JSON output.

### Important Frontend Rules

- Do not expose transport pricing controls to drivers.
- Do not allow farmers to edit bookings.
- Do not let drivers manually set `in_transit`.
- Do not show driver location to farmers before pickup starts.

## Suggested Future API Improvements

- Token-based API auth for mobile clients
- WebSocket or Server-Sent Events for live tracking instead of polling
- Public API schema export using OpenAPI/Swagger
- Dedicated admin analytics endpoints
- Paginated booking lists

## Test Command

```bash
cd backend
DJANGO_SECRET_KEY=test-secret-key ../.venv/bin/python manage.py test
```
