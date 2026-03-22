# Architecture Document
## Web-Based Farm Produce Transport Linking System

## 1. Overview

This document defines the software architecture for the **Web-Based Farm Produce Transport Linking System**, a final year project designed to connect farmers with transporters for efficient movement of farm produce.

The system enables farmers to create delivery requests, search for nearby transport providers, make bookings, track delivery progress, and review services after completion. Transporters can manage their availability, accept or decline bookings, update delivery status, and build trust through performance and ratings.

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
- Make the system easy to maintain and extend
- Ensure the system performs well on mobile and low-resource devices

---

## 3. High-Level Architecture Style

The system follows a **client-server architecture** with a **layered design**.

### Main layers:
1. **Presentation Layer** – frontend user interface
2. **Application Layer** – backend business logic and APIs
3. **Data Layer** – relational database and persistent storage
4. **Integration Layer** – external services like maps, SMS, and notifications

This approach makes the system easier to test, maintain, and expand.

---

## 4. System Context

### Primary Users
- **Farmer**
- **Transporter**
- **Administrator**

### External Services
- Mapping service (OpenStreetMap, Mapbox, or Google Maps)
- Optional SMS/OTP notification service
- Optional email service
- Optional hosting/deployment infrastructure

### Core Business Interaction
- Farmers create transport requests
- System matches or helps farmers find suitable transporters
- Transporters accept or reject requests
- Deliveries move through controlled status stages
- Farmers rate transporters after successful delivery

---

## 5. High-Level Component Architecture

```text
+------------------------+
|   Web Frontend Client  |
| (React / HTML / JS)    |
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

Optional Integrations:
- Maps API
- SMS/OTP Service
- Email Notification Service
- Redis/Celery for async jobs