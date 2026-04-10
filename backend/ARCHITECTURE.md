# Architecture Document
## Web-Based Farm Produce Transport Linking System

## 1. Overview

This document defines the software architecture for the **Web-Based Farm Produce Transport Linking System**, a final year project designed to connect farmers with transporters for efficient movement of farm produce.

The implemented system enables farmers to create map-based delivery requests, track delivery progress, and manage pending bookings. Transporters maintain vehicle details, accept matching jobs, share live location from the browser, and update delivery progress. Staff users manage transport pricing and booking oversight from an in-app dashboard.

The architecture is designed to be:
- modular
- scalable
- secure
- maintainable
- mobile-friendly
- suitable for future extensions such as payments, GPS tracking, and analytics

---

## 2. Architecture Goals

The main goals of the architecture are:

- Provide a reliable platform for linking farmers and transporters
- Support clear separation of concerns between frontend, backend, and database
- Allow secure user authentication and role-based access
- Support location-aware search and booking workflows
- Support email verification and password reset through SMTP delivery
- Make the system easy to maintain and extend
- Ensure the system performs well on mobile and low-resource devices

---

## 3. High-Level Architecture Style

The system follows a **client-server architecture** with a **layered design**.

### Main layers:
1. **Presentation Layer** – frontend user interface
2. **Application Layer** – backend business logic and APIs
3. **Data Layer** – relational database and persistent storage
4. **Integration Layer** – external services like maps and email delivery

This approach makes the system easier to test, maintain, and expand.

---

## 4. System Context

### Primary Users
- **Farmer**
- **Transporter**
- **Administrator**

### External Services
- Mapping service stack: OpenStreetMap tiles, Nominatim, OSRM
- SMTP email delivery provider such as Brevo
- Hosting/deployment infrastructure

### Core Business Interaction
- Farmers create transport requests
- System calculates route, quote, and matching transporters
- Transporters accept matching requests
- Deliveries move through controlled status stages
- Farmers track accepted deliveries live from the dashboard

---

## 5. High-Level Component Architecture

```text
+------------------------+
|   Web Frontend Client  |
|   Django Templates     |
|   HTML / JS / Leaflet  |
+-----------+------------+
            |
            | HTTPS / REST API
            v
+------------------------+
|   Backend Application  |
| Django + DRF          |
+-----------+------------+
            |
            | ORM / SQL
            v
+------------------------+
|     PostgreSQL DB      |
+------------------------+

Active Integrations:
- OpenStreetMap tile service
- Nominatim geocoding
- OSRM route service
- SMTP transactional email provider

Optional Future Integrations:
- Native mobile tracking client
- Redis/Celery for async jobs
