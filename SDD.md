# Software Design Document (SDD)

## FreshHaul: Web-Based Produce Transport Coordination System

Version: 1.0  
Date: 2026-05-07  
Prepared for: Final Year Project Documentation

## 1. Introduction

### 1.1 Purpose

This Software Design Document describes how FreshHaul is designed and implemented to satisfy the requirements defined in the SRS. It translates system requirements into software structure, component responsibilities, data design, interface design, control flow, and deployment design.

This document is intended for:

- developers implementing or extending the system
- reviewers evaluating the design quality
- testers mapping design to expected behavior
- deployers and maintainers operating the platform

### 1.2 Scope

This SDD covers the current FreshHaul implementation, including:

- high-level architecture
- module decomposition
- backend design by Django app
- data model design
- interface design
- workflow and control design
- security and deployment design
- recommended diagram placement

### 1.3 References

- [SRS.md](/home/magwar/Documents/final_year_project/SRS.md)
- [README.md](/home/magwar/Documents/final_year_project/README.md)
- [API.md](/home/magwar/Documents/final_year_project/API.md)
- [backend/ARCHITECTURE.md](/home/magwar/Documents/final_year_project/backend/ARCHITECTURE.md)
- [project.mmd](/home/magwar/Documents/final_year_project/project.mmd)

### 1.4 Design Goals

The design goals of FreshHaul are:

- clear separation of concerns across modules
- maintainable server-side business rules
- a simple browser-based operational workflow
- strong alignment between role permissions and business processes
- easy local and Docker-based deployment
- support for external service integration without overcomplicating the core system

## 2. Design Overview

### 2.1 Architectural Style

FreshHaul uses a layered client-server architecture with a modular backend.

Main layers:

- presentation layer
- application layer
- data layer
- integration layer

The presentation and application layers are tightly integrated because the frontend uses Django templates and same-origin API calls to DRF endpoints.

### 2.2 Design Strategy

The design strategy is based on:

- Django apps as module boundaries
- DRF serializers for validation and business-rule enforcement near API boundaries
- Django models for core domain persistence
- view classes for request handling and access control
- external service adapters for mapping and payment integration

Recommended diagram placement:

- Insert the `Container / Runtime Architecture Diagram` from [project.mmd](/home/magwar/Documents/final_year_project/project.mmd) here.
- Insert the `Application Component Diagram` here.

### 2.3 Technology Decisions

The design uses:

- Python 3.12
- Django 6
- Django REST Framework
- SQLite for simple local fallback
- PostgreSQL for managed deployment
- Leaflet and OpenStreetMap tiles for maps
- Nominatim and OSRM for geospatial features
- Safaricom Daraja for payment initiation and callback

Rationale:

- Django provides integrated authentication, templating, ORM, and admin tooling.
- DRF supports structured API design with serializer-based validation.
- Leaflet supports lightweight browser mapping.
- SQLite simplifies local development, while PostgreSQL supports more robust deployment.

## 3. System Architecture Design

### 3.1 High-Level Architecture

The system is composed of:

- browser clients
- Django template-rendered pages
- DRF API endpoints
- domain modules by app
- relational database
- external integration services

Core request path:

1. User interacts with a browser page.
2. Request reaches Django view or DRF API endpoint.
3. View delegates validation and business rules to serializers, forms, models, or services.
4. Data is persisted through the ORM.
5. External services are called when mapping, payment, or email functionality is needed.

Recommended diagram placement:

- Insert the `System Context Diagram` here.
- Insert the `Container / Runtime Architecture Diagram` here.

### 3.2 Module Decomposition

The backend is partitioned into the following Django apps:

- `accounts`
- `booking`
- `transporters`
- `payments`
- `maps`
- `core`

Each app owns a distinct concern and communicates through shared models, imports, and service-level interactions.

### 3.3 Interaction Model

The interaction model combines:

- page rendering for dashboards and account screens
- AJAX or fetch-style calls from dashboards to backend APIs
- REST-style JSON APIs for business operations
- callback-driven payment reconciliation

## 4. Detailed Component Design

### 4.1 `core` Module Design

Responsibilities:

- global Django settings
- root URL routing
- environment-driven configuration

Design notes:

- `core/settings.py` centralizes security, DB, REST, email, maps, and M-Pesa settings.
- `core/urls.py` composes routes from the feature apps.
- storage backend is chosen dynamically based on PostgreSQL env vars.

### 4.2 `accounts` Module Design

Responsibilities:

- custom user model
- signup and login
- email verification
- profile management
- role-based dashboard entry
- admin dashboard and CSV export logic

Key design elements:

- `CustomUser` uses `phone_number` as the username field.
- form classes enforce registration and account-update constraints.
- `HomeView` acts as a role router.
- `AdminDashboardView` aggregates reporting and pricing-management context.

Important design decisions:

- staff users are treated as admins through Django’s staff mechanisms.
- public role creation is constrained at form level.
- email verification is enforced during login, not just during signup.

### 4.3 `booking` Module Design

Responsibilities:

- booking entity management
- route-derived quote lifecycle
- transporter matching
- driver acceptance
- status transitions
- tracking updates
- booking-related APIs

Key design elements:

- `Booking` stores core business data for a transport request.
- `BookingStatusHistory` preserves audit history.
- `TrackingUpdate` captures in-transit movement history.
- serializers implement most API validation and transition rules.

Important design decisions:

- booking creation is validation-heavy and computes route-derived fields at creation time.
- booking deletion is constrained by state, not just ownership.
- state transitions are controlled explicitly rather than generically.

### 4.4 `transporters` Module Design

Responsibilities:

- transporter profile management
- vehicle management
- transport pricing rules
- location updates

Key design elements:

- `TransporterProfile` separates driver operational data from base user data.
- `Vehicle` supports one-to-many driver-to-vehicle ownership.
- `TransportPricing` controls both pricing and booking weight band classification.

Important design decisions:

- vehicle type validation depends on configured transport rules.
- pricing bands are a business-admin-controlled design input for booking classification.
- current driver location is stored at the transporter profile level.

### 4.5 `payments` Module Design

Responsibilities:

- STK Push initiation
- callback handling
- payment state persistence
- payout release tracking
- payment detail APIs

Key design elements:

- `Payment` stores the main payment record.
- `PaymentStatusHistory` stores payment event history.
- `TransporterPayout` stores the payout release state tied to booking completion.
- serializers and services coordinate Daraja interaction and state changes.

Important design decisions:

- payment and payout are modeled separately.
- successful payment does not immediately imply released payout.
- callback handling is exposed publicly but isolated to a narrow endpoint.

### 4.6 `maps` Module Design

Responsibilities:

- place search
- place lookup
- reverse geocoding
- route preview

Key design elements:

- map endpoints are kept separate from booking logic.
- booking logic consumes route details from map services rather than implementing mapping logic directly.

Important design decisions:

- geospatial service access is abstracted through app-level services.
- route geometry and route metrics are persisted with the booking.

Recommended diagram placement:

- Insert the `Application Component Diagram` here.

## 5. Data Design

### 5.1 Data Architecture

FreshHaul uses a relational data model implemented through Django ORM models.

Design characteristics:

- normalized entities for users, bookings, vehicles, payments, and histories
- one-to-one links where ownership is exclusive
- one-to-many links for histories and collections
- optional foreign keys where assignment happens later in the workflow

### 5.2 Core Entities

#### User

Purpose:

- stores identity, role, and authentication-related fields

Important fields:

- `phone_number`
- `email`
- `role`
- `is_email_verified`
- `is_staff`

#### TransporterProfile

Purpose:

- stores driver operational identity and current location state

Important fields:

- `company_name`
- `current_latitude`
- `current_longitude`
- `last_location_update`

#### Vehicle

Purpose:

- stores vehicle details used in matching and assignment

Important fields:

- `registration_number`
- `vehicle_type`
- `capacity_kg`
- `is_available`

#### Booking

Purpose:

- represents a produce transport request and its lifecycle

Important fields:

- `farmer`
- `transporter`
- `vehicle`
- `produce_name`
- `weight_kg`
- pickup and dropoff coordinates
- `estimated_distance_km`
- `estimated_duration_minutes`
- `route_geometry`
- `vehicle_type_required`
- `quoted_price`
- `status`
- `payment_status`

#### Payment

Purpose:

- records M-Pesa payment initiation, callback outcome, and held/released state

Important fields:

- `booking`
- `amount_kes`
- `phone_number`
- `merchant_request_id`
- `checkout_request_id`
- `mpesa_receipt_number`
- `status`

#### TransporterPayout

Purpose:

- records the payout state for the driver tied to a payment

### 5.3 Data Relationships

Key relationships:

- one user can create many bookings
- one user can be assigned many bookings as driver
- one driver profile belongs to one user
- one driver profile can own many vehicles
- one booking can have many tracking updates
- one booking can have many status history entries
- one booking can have one payment
- one payment can have one payout

Recommended diagram placement:

- Insert the `Entity Relationship Diagram` from [project.mmd](/home/magwar/Documents/final_year_project/project.mmd) here.

### 5.4 Persistence Decisions

Design choices:

- SQLite is used automatically when PostgreSQL configuration is absent.
- PostgreSQL is preferred in Docker or hosted setups.
- histories are persisted rather than derived to preserve audit traceability.

## 6. Interface Design

### 6.1 User Interface Design

FreshHaul uses server-rendered templates with dashboard-specific interaction logic.

Main UI segments:

- public landing and authentication pages
- farmer dashboard
- driver dashboard
- admin dashboard

UI design patterns:

- role-based page routing
- sidebar navigation for authenticated roles
- map-based interaction for booking and tracking
- modal and tab-driven operational flows

### 6.2 API Interface Design

The API design follows REST-like patterns under these namespaces:

- `/api/bookings/`
- `/api/maps/`
- `/api/payments/`
- `/api/transporters/`

API design characteristics:

- session-authenticated
- JSON request and response bodies
- serializer-driven validation
- role-scoped access control

### 6.3 External Service Interface Design

#### Map Services

Used for:

- search
- lookup
- reverse geocoding
- route preview

Design notes:

- map operations are invoked through service-level abstractions
- route metrics are stored with bookings to avoid repeated recalculation for core operations

#### Daraja

Used for:

- STK Push initiation
- payment callback handling

Design notes:

- callback processing is separated from user-initiated request flow
- payment metadata is persisted for audit and troubleshooting

#### SMTP

Used for:

- verification email delivery
- password reset email delivery

Recommended diagram placement:

- Insert the `System Context Diagram` here if interface-focused presentation is preferred.

## 7. Control and Workflow Design

### 7.1 Booking Creation Workflow

Design flow:

1. Farmer enters booking details.
2. Frontend requests map-based route information.
3. Booking serializer validates payload and computes derived values.
4. Booking record is created in `pending_payment`.
5. Matched transporters are computed and returned.

### 7.2 Payment Workflow

Design flow:

1. Farmer initiates STK Push for a booking.
2. Payment serializer validates ownership and payment eligibility.
3. Daraja initiation is performed through service logic.
4. Payment record is stored.
5. Callback endpoint reconciles final payment result.
6. Booking and payout-related state is updated.

### 7.3 Driver Dispatch Workflow

Design flow:

1. Driver configures vehicles and location.
2. Driver loads open jobs.
3. Matching filters jobs by vehicle and geographic logic.
4. Driver accepts using a selected vehicle.
5. Booking and vehicle states are updated.

### 7.4 Delivery Tracking Workflow

Design flow:

1. Driver updates live location.
2. Driver posts pickup or delivery state transition.
3. Backend validates location and current status.
4. Tracking updates and status history are stored.
5. Farmer views the current trip state and route progress.

Recommended diagram placement:

- Insert the `Booking And Payment Sequence Diagram` here.
- Insert the `Delivery Execution Sequence Diagram` here.

### 7.5 State Transition Design

Booking state design:

- `pending_payment`
- `confirmed`
- `accepted`
- `declined`
- `picked_up`
- `in_transit`
- `delivered`
- `completed`
- `cancelled`

Payment state design:

- `pending`
- `stk_push_sent`
- `paid_held`
- `failed`
- `cancelled`
- `released`

Design principle:

- transitions are explicitly validated in serializers and supporting logic
- invalid transitions are rejected at the API layer

Recommended diagram placement:

- Insert the `Booking State Diagram` here.
- Insert the `Payment State Diagram` here.

## 8. Security Design

### 8.1 Authentication Design

The system uses Django session authentication.

Design choices:

- browser session is the primary auth mechanism
- `phone_number` is the username field
- login restriction for unverified non-staff accounts

### 8.2 Authorization Design

Authorization is implemented through:

- DRF permission classes
- queryset scoping
- role checks in views and forms
- staff-only mixins for admin pages

### 8.3 Data Protection Design

Protection measures include:

- secure cookie support through configuration
- CSRF protection for same-origin writes
- object-level visibility restrictions for bookings and payments
- environment-driven SSL and HSTS options

### 8.4 Auditability Design

Audit support is provided through:

- booking status history
- payment status history
- persistent payment metadata
- persistent tracking updates

## 9. Deployment Design

### 9.1 Local Deployment Design

Local design assumptions:

- Python environment with project dependencies installed
- `DJANGO_SECRET_KEY` configured
- SQLite used unless PostgreSQL env vars are provided

### 9.2 Docker Deployment Design

Docker deployment contains:

- `web` container for Django
- `db` container for PostgreSQL
- `adminer` container for DB administration

Startup design:

- `entrypoint.sh` runs migrations automatically
- then starts Django development server

### 9.3 Configuration Design

Major configuration groups:

- security settings
- DB settings
- REST framework throttling
- map service endpoints
- email delivery settings
- Daraja payment settings
- site branding and support settings

Recommended diagram placement:

- Insert the `Deployment Diagram` from [project.mmd](/home/magwar/Documents/final_year_project/project.mmd) here.

## 10. Error Handling Design

### 10.1 Validation Error Design

Validation errors are primarily handled by:

- Django forms for web form flows
- DRF serializers for API operations
- model-level validation for invariant rules

### 10.2 Access Error Design

Access errors are handled through:

- authentication checks
- permission classes
- object ownership restrictions
- staff-only view protection

### 10.3 External Service Failure Design

Failure modes considered:

- payment initiation failure
- payment callback inconsistency
- map service latency or failure
- email delivery unavailability

Design approach:

- isolate external service logic in dedicated modules
- propagate structured validation or service errors back to calling layers
- persist enough payment metadata for diagnosis

## 11. Design Constraints and Tradeoffs

### 11.1 Current Constraints

- the system is optimized for same-origin browser use
- location tracking depends on browser permission and activity
- public mapping services may limit high-volume usage
- current payment flow is oriented toward Daraja integration

### 11.2 Tradeoffs

- server-rendered dashboards reduce frontend complexity but tighten UI/backend coupling
- session auth simplifies same-origin security but is less convenient for third-party clients
- storing route geometry improves trip reuse but increases booking payload size
- SQLite fallback improves portability but is not the preferred production backend

## 12. Recommended Diagram Placement Summary

Use the diagrams from [project.mmd](/home/magwar/Documents/final_year_project/project.mmd) in the following SDD sections:

- `System Context Diagram`: Section 3 System Architecture Design or Section 6 Interface Design
- `Container / Runtime Architecture Diagram`: Section 2 Design Overview or Section 3 System Architecture Design
- `Application Component Diagram`: Section 4 Detailed Component Design
- `Booking And Payment Sequence Diagram`: Section 7.1 Booking Creation Workflow or Section 7.2 Payment Workflow
- `Delivery Execution Sequence Diagram`: Section 7.4 Delivery Tracking Workflow
- `Booking State Diagram`: Section 7.5 State Transition Design
- `Payment State Diagram`: Section 7.5 State Transition Design
- `Entity Relationship Diagram`: Section 5 Data Design
- `Role Access Matrix Diagram`: Section 4 Detailed Component Design or Section 8 Security Design
- `Deployment Diagram`: Section 9 Deployment Design

## 13. Future Design Improvements

Potential design improvements include:

- publish OpenAPI schema routes
- add async processing for notifications or external callbacks
- improve driver tracking resilience beyond browser lifecycle
- introduce richer observability and audit reporting
- support alternative client channels such as mobile apps
