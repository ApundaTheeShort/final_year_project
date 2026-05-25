# Software Requirements Specification (SRS)

## FreshHaul: Web-Based Produce Transport Coordination System

Version: 1.0  
Date: 2026-05-07  
Prepared for: Final Year Project Documentation

## 1. Introduction

### 1.1 Purpose

This Software Requirements Specification defines the functional and non-functional requirements for FreshHaul, a web-based produce transport coordination system. The system connects farmers who need transport for produce with drivers who can fulfill those deliveries, while allowing staff users to manage pricing and monitor operations.

This SRS is intended for:

- project supervisors and examiners
- developers maintaining or extending the system
- testers validating expected system behavior
- deployers and administrators configuring the environment

### 1.2 Scope

FreshHaul provides a browser-based workflow for produce transport booking, pricing, payment initiation, driver assignment, trip tracking, and operational administration.

The system supports:

- farmer account registration and login
- driver account registration and login
- email verification and password reset flows
- map-based pickup and dropoff selection
- route-based quotation using integrated map services
- M-Pesa STK Push payment initiation
- driver vehicle and profile management
- progressive matching of transporters to bookings
- delivery lifecycle tracking from pickup to completion
- staff pricing management and reporting dashboards

The current implementation is a Django web application with REST API endpoints used by the same-origin frontend.

### 1.3 Definitions, Acronyms, and Abbreviations

- `SRS`: Software Requirements Specification
- `API`: Application Programming Interface
- `DRF`: Django REST Framework
- `STK Push`: Safaricom M-Pesa payment prompt sent to a mobile device
- `OSRM`: Open Source Routing Machine
- `SMTP`: Simple Mail Transfer Protocol
- `Admin`: staff user with management access
- `Farmer`: user who creates produce transport bookings
- `Driver`: transporter user who accepts and fulfills bookings

### 1.4 References

- [README.md](/home/magwar/Documents/final_year_project/README.md)
- [API.md](/home/magwar/Documents/final_year_project/API.md)
- [backend/ARCHITECTURE.md](/home/magwar/Documents/final_year_project/backend/ARCHITECTURE.md)
- [project.mmd](/home/magwar/Documents/final_year_project/project.mmd)

### 1.5 Document Overview

This document covers:

- overall product description
- user classes and operating environment
- system features and functional requirements
- external interface requirements
- non-functional requirements
- data requirements
- constraints, assumptions, and future considerations

## 2. Overall Description

### 2.1 Product Perspective

FreshHaul is a standalone web application built around a layered architecture:

- presentation layer using Django templates and browser JavaScript
- application layer using Django and DRF
- data layer using Django ORM with SQLite or PostgreSQL
- integration layer using map, payment, and email services

The system is not a plugin to another application. It is a complete end-user platform.

Recommended diagram placement:

- Insert the `System Context Diagram` from [project.mmd](/home/magwar/Documents/final_year_project/project.mmd) here.
- Insert the `Container / Runtime Architecture Diagram` here.

### 2.2 Product Functions

At a high level, the system:

- allows farmers to create bookings with pickup and dropoff locations
- calculates transport quotes from route distance and pricing rules
- initiates M-Pesa STK Push payment for a booking
- makes paid bookings available to matching drivers
- allows drivers to manage vehicle details and live location
- allows drivers to accept bookings and update delivery progress
- allows farmers to track trip progress
- allows staff users to manage pricing and review operational data

### 2.3 User Classes and Characteristics

#### Farmer

Characteristics:

- creates bookings
- pays for transport
- tracks delivery progress
- can delete only unpaid bookings

Technical expectations:

- basic browser and smartphone literacy
- ability to use map-based selection and M-Pesa payment flow

#### Driver

Characteristics:

- maintains transporter profile and vehicles
- updates live location
- accepts jobs matching available vehicles
- performs pickup and delivery status updates

Technical expectations:

- browser access with location permission enabled
- ability to manage vehicle records and trip status flow

#### Admin

Characteristics:

- staff user with access to management dashboards
- manages pricing bands and reports
- reviews bookings and system metrics

Technical expectations:

- administrative familiarity with operations and pricing rules

### 2.4 Operating Environment

The system operates in:

- modern desktop or mobile web browsers
- a Django backend runtime on Python 3.12
- SQLite for simple local use or PostgreSQL for managed deployment
- network-connected environments capable of reaching map, email, and Daraja services

Deployment options:

- local development environment
- Docker Compose environment with PostgreSQL and Adminer

### 2.5 Design and Implementation Constraints

- public signup is restricted to `farmer` and `driver`
- authentication is session-based
- non-staff users must verify email before login
- payment integration depends on Safaricom Daraja configuration
- route and place services depend on external map endpoints
- pickup and delivery transitions depend on driver location availability
- the current implementation is browser-based and same-origin

### 2.6 User Documentation

Relevant project documentation includes:

- project overview in `README.md`
- API reference in `API.md`
- architecture notes in `backend/ARCHITECTURE.md`
- diagrams in `project.mmd`

### 2.7 Assumptions and Dependencies

- users have internet connectivity
- drivers allow browser location access
- email delivery is configured when verification and reset emails are required
- Daraja sandbox or production credentials are correctly configured
- external mapping services are reachable

## 3. System Features and Functional Requirements

### 3.1 User Registration and Authentication

Description:

The system shall allow public registration for farmer and driver accounts and shall authenticate users using phone number and password.

Functional requirements:

- `FR-001` The system shall allow a new user to register as a `farmer` or `driver`.
- `FR-002` The system shall require `phone_number`, `email`, `first_name`, `last_name`, `role`, and password during registration.
- `FR-003` The system shall reject public registration for the `admin` role.
- `FR-004` The system shall use `phone_number` as the login identifier.
- `FR-005` The system shall allow authenticated users to log in through the web login page.
- `FR-006` The system shall prevent non-staff users from logging in until email verification is completed.
- `FR-007` The system shall support password reset through email.
- `FR-008` The system shall support resending verification codes or verification emails.
- `FR-009` The system shall allow authenticated users to update basic profile details.

### 3.2 Role-Based Home and Dashboard Routing

Description:

The system shall serve different dashboard experiences based on user role.

Functional requirements:

- `FR-010` The system shall display a public landing page to anonymous users visiting `/`.
- `FR-011` The system shall display the farmer dashboard to authenticated users with role `farmer`.
- `FR-012` The system shall display the driver dashboard to authenticated users with role `driver`.
- `FR-013` The system shall display the admin dashboard to staff users.

### 3.3 Booking Creation

Description:

The farmer creates a produce transport request by providing produce details and selecting pickup and dropoff locations.

Functional requirements:

- `FR-014` The system shall allow only farmers to create bookings.
- `FR-015` The system shall accept produce name, produce description, weight, pickup place, and dropoff place for a booking.
- `FR-016` The system shall resolve and store pickup and dropoff coordinates and addresses.
- `FR-017` The system shall calculate route distance, route duration, and route geometry during booking creation.
- `FR-018` The system shall determine the required vehicle type from booking weight.
- `FR-019` The system shall calculate the quoted price from route distance and the configured pricing rule for the required vehicle type.
- `FR-020` The system shall create new bookings in the `pending_payment` status.
- `FR-021` The system shall create new bookings with booking payment status `unpaid`.
- `FR-022` The system shall compute and store the effective matching search radius used for the booking.
- `FR-023` The system shall return matching transporters for a newly created booking.

Recommended diagram placement:

- Insert the `Booking And Payment Sequence Diagram` from [project.mmd](/home/magwar/Documents/final_year_project/project.mmd) here.

### 3.4 Booking Deletion

Description:

Farmers may delete only unpaid bookings.

Functional requirements:

- `FR-024` The system shall allow only the booking owner to delete a booking.
- `FR-025` The system shall allow deletion only when the booking status is `pending_payment`.
- `FR-026` The system shall reject deletion of paid, confirmed, accepted, in-transit, delivered, completed, or cancelled bookings.

### 3.5 Pricing and Vehicle Rule Management

Description:

Pricing is managed centrally by staff users through transport pricing bands.

Functional requirements:

- `FR-027` The system shall maintain pricing rules by vehicle type.
- `FR-028` The system shall store a price-per-kilometer value for each vehicle type.
- `FR-029` The system shall store minimum and maximum supported weight bounds for each vehicle type.
- `FR-030` The system shall prevent overlapping pricing weight bands.
- `FR-031` The system shall allow staff users to create new pricing rules.
- `FR-032` The system shall allow staff users to update existing pricing rules.

### 3.6 Payment Initiation and Callback Handling

Description:

Payment is initiated after booking creation using Safaricom Daraja STK Push.

Functional requirements:

- `FR-033` The system shall allow only the booking farmer to initiate payment for the booking.
- `FR-034` The system shall initiate payment using the booking’s quoted amount rather than user-entered price data.
- `FR-035` The system shall normalize the supplied phone number to the required Kenyan format before initiating payment.
- `FR-036` The system shall reject payment initiation for cancelled bookings.
- `FR-037` The system shall reject duplicate payment attempts for already paid bookings.
- `FR-038` The system shall store payment initiation metadata from Daraja.
- `FR-039` The system shall accept callback notifications from Daraja.
- `FR-040` The system shall update payment status and booking payment status after processing a callback.
- `FR-041` The system shall move a successfully paid booking into a driver-visible state.

Recommended diagram placement:

- Insert the `Payment State Diagram` here.
- The first half of the `Booking And Payment Sequence Diagram` also fits here.

### 3.7 Driver Profile and Vehicle Management

Description:

Drivers manage their transporter profile and associated vehicles.

Functional requirements:

- `FR-042` The system shall allow only drivers to manage transporter profile data.
- `FR-043` The system shall allow drivers to store company name and live coordinates.
- `FR-044` The system shall allow drivers to create, update, and remove vehicles tied to their profile.
- `FR-045` The system shall require each vehicle registration number to be unique.
- `FR-046` The system shall require each vehicle type to match a configured transport pricing type.
- `FR-047` The system shall store vehicle capacity and availability status.

### 3.8 Driver Matching and Open Jobs

Description:

Paid bookings shall be exposed to appropriate drivers using matching rules.

Functional requirements:

- `FR-048` The system shall list open bookings only for authenticated drivers.
- `FR-049` The system shall expose only bookings in `confirmed` status as open jobs.
- `FR-050` The system shall require the driver to have an available vehicle of the required vehicle type.
- `FR-051` The system shall filter open jobs by progressive geographic matching when driver location exists.
- `FR-052` The system shall allow farmers to view nearby transporter matches for their own bookings.

### 3.9 Booking Acceptance and Assignment

Description:

Drivers accept bookings using one of their available vehicles.

Functional requirements:

- `FR-053` The system shall allow only drivers to accept or decline an open job.
- `FR-054` The system shall require a vehicle selection when accepting a booking.
- `FR-055` The system shall reject acceptance when the vehicle does not belong to the current driver.
- `FR-056` The system shall reject acceptance when the vehicle is unavailable.
- `FR-057` The system shall reject acceptance when the vehicle type does not match the booking requirement.
- `FR-058` The system shall reject acceptance when the vehicle capacity is insufficient.
- `FR-059` The system shall assign the transporter and selected vehicle to the accepted booking.
- `FR-060` The system shall set an accepted booking to status `accepted`.
- `FR-061` The system shall mark the selected vehicle unavailable after booking acceptance.

### 3.10 Delivery Progress and Tracking

Description:

The driver updates the trip from pickup to delivery, while the farmer can monitor progress.

Functional requirements:

- `FR-062` The system shall allow drivers to update live location.
- `FR-063` The system shall store booking tracking updates with timestamp, latitude, longitude, and optional speed and notes.
- `FR-064` The system shall allow only the assigned driver to post tracking updates for a booking.
- `FR-065` The system shall allow only the assigned driver to mark `picked_up`.
- `FR-066` The system shall allow only the assigned driver to mark `delivered`.
- `FR-067` The system shall validate driver proximity to the pickup point before accepting `picked_up`.
- `FR-068` The system shall validate driver proximity to the dropoff point before accepting `delivered`.
- `FR-069` The system shall prevent invalid booking status transitions.
- `FR-070` The system shall provide tracking details to the booking farmer and assigned driver.

Recommended diagram placement:

- Insert the `Delivery Execution Sequence Diagram` here.
- Insert the `Booking State Diagram` here.

### 3.11 Booking and Payment History

Description:

The system maintains operational history for key business objects.

Functional requirements:

- `FR-071` The system shall record booking status history entries.
- `FR-072` The system shall record payment status history entries.
- `FR-073` The system shall expose booking status history as part of booking detail responses.
- `FR-074` The system shall expose payment status history as part of payment detail responses.

### 3.12 Payout and Completion Handling

Description:

A payment record remains held until delivery completion logic allows release.

Functional requirements:

- `FR-075` The system shall create or maintain payout records linked to booking payments.
- `FR-076` The system shall hold successful payments before delivery completion.
- `FR-077` The system shall update payout state after eligible delivery completion.
- `FR-078` The system shall support payment status `released`.
- `FR-079` The system shall support payout status `pending_release`, `released`, and `failed`.

### 3.13 Reporting and Administration

Description:

Staff users manage operational data from an in-app dashboard and exports.

Functional requirements:

- `FR-080` The system shall provide a staff-only admin dashboard.
- `FR-081` The system shall show booking summary metrics in the admin dashboard.
- `FR-082` The system shall show revenue summaries in the admin dashboard.
- `FR-083` The system shall display bookings grouped by vehicle type.
- `FR-084` The system shall allow staff users to review active and recent bookings.
- `FR-085` The system shall provide CSV report exports for farmer bookings, transporter jobs, admin bookings, and admin rates.

Recommended diagram placement:

- Insert the `Role Access Matrix Diagram` here.

## 4. External Interface Requirements

### 4.1 User Interfaces

The system shall provide:

- public landing page
- signup and login pages
- verification and reset pages
- farmer dashboard
- driver dashboard
- admin dashboard

UI characteristics:

- responsive web layout
- map-assisted interaction using Leaflet
- role-specific navigation and actions
- sidebar-based dashboards for authenticated roles

### 4.2 Hardware Interfaces

No specialized hardware interface is required, but the following may be used:

- smartphone for M-Pesa confirmation
- device GPS/location services for driver live tracking

### 4.3 Software Interfaces

The system interfaces with:

- Nominatim for place search, lookup, and reverse geocoding
- OSRM for route preview and route distance estimation
- OpenStreetMap tile services for map display
- Safaricom Daraja for STK Push and callbacks
- SMTP provider for email delivery
- SQLite or PostgreSQL for persistence

### 4.4 Communications Interfaces

- HTTP/HTTPS between browser and server
- HTTP/HTTPS to external map services
- HTTP/HTTPS to Daraja APIs
- SMTP or provider-backed email transport for outgoing mail

## 5. Data Requirements

### 5.1 Core Data Entities

Main persisted entities:

- user
- transporter profile
- vehicle
- booking
- booking status history
- tracking update
- payment
- payment status history
- transporter payout
- transport pricing

Recommended diagram placement:

- Insert the `Entity Relationship Diagram` from [project.mmd](/home/magwar/Documents/final_year_project/project.mmd) here.

### 5.2 Data Retention Expectations

- booking records shall persist for operational and reporting use
- payment and payout records shall persist for audit and reconciliation
- status histories shall persist to support traceability
- tracking updates shall persist for trip history review

### 5.3 Data Validation Rules

- phone number shall be unique per user
- email shall be unique per user
- vehicle registration number shall be unique
- vehicle type shall be one of the configured transport types
- weight-based pricing bands shall not overlap
- a booking vehicle shall be capable of carrying the booking load

## 6. Non-Functional Requirements

### 6.1 Security Requirements

- `NFR-001` The system shall use authenticated sessions for protected actions.
- `NFR-002` The system shall enforce role-based authorization on protected resources.
- `NFR-003` The system shall enforce CSRF protection for authenticated write operations using session authentication.
- `NFR-004` The system shall support secure cookie configuration for deployed environments.
- `NFR-005` The system shall support HTTPS-related security settings including SSL redirect and HSTS through environment variables.
- `NFR-006` The system shall restrict non-owner access to booking and payment data.

### 6.2 Performance Requirements

- `NFR-007` The system should return standard dashboard and API responses within acceptable web interaction time under normal academic-project scale usage.
- `NFR-008` Route preview and place lookup responses should be bounded primarily by external service latency.
- `NFR-009` The system should support throttling of anonymous and authenticated API traffic.

### 6.3 Reliability and Availability Requirements

- `NFR-010` The system shall preserve booking, payment, and history records in persistent storage.
- `NFR-011` The system should continue to operate with SQLite in local environments when PostgreSQL variables are not configured.
- `NFR-012` The system should recover service state after restart when persistent database storage is available.

### 6.4 Usability Requirements

- `NFR-013` The system shall provide a browser-based workflow usable without command-line knowledge.
- `NFR-014` The system shall present role-specific screens relevant to the current user.
- `NFR-015` The system should support desktop and mobile form factors.

### 6.5 Maintainability Requirements

- `NFR-016` The system shall separate concerns by Django app boundary.
- `NFR-017` The system shall provide dedicated project documentation for overview, API, architecture, diagrams, and SRS.
- `NFR-018` The system should support extension through additional integrations, async processing, or new clients.

### 6.6 Portability Requirements

- `NFR-019` The system shall run in a Python-based local environment.
- `NFR-020` The system shall run in a Docker-based environment.
- `NFR-021` The system shall support SQLite and PostgreSQL storage backends through configuration.

## 7. Business Rules

- `BR-001` Only farmers can create bookings.
- `BR-002` Public users cannot sign up as admins.
- `BR-003` Drivers can only accept paid and confirmed bookings.
- `BR-004` Farmers can only delete unpaid bookings.
- `BR-005` Pickup requires driver proximity to the pickup point.
- `BR-006` Delivery requires driver proximity to the dropoff point.
- `BR-007` Vehicle type is derived from weight bands, not directly chosen by the farmer.
- `BR-008` A driver vehicle must match both booking type and booking capacity requirements.

## 8. System Constraints

- the solution is currently browser-centered, not native mobile
- driver live tracking depends on browser location access
- map service quality depends on third-party provider availability
- Daraja testing depends on valid callback routing and credentials
- the current codebase includes `drf-spectacular` but does not publish an OpenAPI route yet

## 9. Acceptance Criteria Summary

The system shall be considered to satisfy this SRS if:

- users can register and authenticate according to role rules
- farmers can create, pay for, view, and track bookings
- drivers can configure vehicles, receive matched jobs, accept bookings, and complete delivery transitions
- admins can manage pricing and reports
- payment and payout records reflect booking lifecycle events
- the system enforces location, role, and state-transition constraints

## 10. Recommended Diagram Placement Summary

Use the diagrams from [project.mmd](/home/magwar/Documents/final_year_project/project.mmd) in the following SRS sections:

- `System Context Diagram`: Section 2.1 Product Perspective
- `Container / Runtime Architecture Diagram`: Section 2.1 Product Perspective or Section 4 External Interfaces
- `Application Component Diagram`: Section 2.1 Product Perspective or Section 6 Maintainability
- `Booking And Payment Sequence Diagram`: Section 3.3 Booking Creation or Section 3.6 Payment Initiation
- `Delivery Execution Sequence Diagram`: Section 3.10 Delivery Progress and Tracking
- `Booking State Diagram`: Section 3.10 Delivery Progress and Tracking
- `Payment State Diagram`: Section 3.6 Payment Initiation and Callback Handling
- `Entity Relationship Diagram`: Section 5 Data Requirements
- `Role Access Matrix Diagram`: Section 2.3 User Classes or Section 3.13 Reporting and Administration
- `Deployment Diagram`: Section 2.4 Operating Environment or Section 6 Portability

## 11. Future Enhancements

Potential future requirements not yet fully realized in the current implementation:

- OpenAPI schema publication
- asynchronous job processing for external integrations
- notification channels beyond email
- stronger audit reporting
- mobile-first driver tracking client
