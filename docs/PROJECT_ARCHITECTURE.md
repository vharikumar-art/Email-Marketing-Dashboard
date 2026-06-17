# Email Dashboard API - Complete Project Architecture & Documentation

## Table of Contents
1. [Project Overview](#project-overview)
2. [Technology Stack](#technology-stack)
3. [System Architecture](#system-architecture)
4. [Directory Structure](#directory-structure)
5. [Database Design](#database-design)
6. [Authentication & Authorization Flow](#authentication--authorization-flow)
7. [ID Range Management](#id-range-management)
8. [API Endpoints](#api-endpoints)
9. [Key Features](#key-features)
10. [Security Implementation](#security-implementation)
11. [Deployment & Configuration](#deployment--configuration)
12. [Workflow Examples](#workflow-examples)

---

## Project Overview

### What is this project?

The **Email Dashboard API** is a comprehensive backend system designed to manage email communications, client relationships, manuscripts, orders, and payments. It features a **Role-Based Access Control (RBAC)** system that permits different user roles (Admin, Manager, Employee) to perform operations within their bounds.

### Purpose

The system serves as a centralized platform for:
- Managing client information and communications
- Tracking manuscript submissions (optional, ~30% of clients)
- Processing and managing orders for academic/editorial services
- Handling multi-phase payment tracking and transaction history
- Currency conversion between INR and USD using live exchange rates
- Auto-generating client and order IDs within non-overlapping ranges assigned to employees
- Providing secure 2FA/OTP login for privileged users (Admin and Manager)

### Target Users

- **Super Admins / Admins**: Organization administrators with full control over user creation, manager creation, global settings, and viewing/updating all system data.
- **Managers**: Team leaders who can manage employees, create new employees/managers, view all clients, and oversee dashboard data.
- **Employees**: Front-line team members who manage assigned clients, create/update orders, and process payments. Employees are restricted to viewing and managing only their assigned clients.

---

## Technology Stack

### Backend Framework
- **FastAPI**: Modern, fast ASGI web framework for building REST APIs
- **Python (3.11+)**: Core programming language
- **Uvicorn**: ASGI server for running the FastAPI application

### Database & Caching
- **MongoDB**: NoSQL database for flexible, document-based data storage
- **PyMongo**: Python MongoDB driver for database connectivity
- **Redis & cachetools**: Caching infrastructure supporting both Redis (production) and local memory (fallback) via `CacheManager`

### Authentication & Security
- **Python-Jose**: JWT token creation, signature verification, and session decoding
- **Cryptography (Fernet)**: Two-way symmetric encryption. Unlike traditional hashing (e.g. Bcrypt), password credentials are encrypted and decrypted bidirectionally using a secure 256-bit `ENCRYPTION_KEY` to allow Admins and Managers to view decrypted employee passwords on display endpoints.

### Utilities & Integrations
- **Pydantic**: Data validation and serialization using Pydantic V2 schemas
- **python-dotenv**: Environment variable management
- **requests**: External HTTP client used to fetch live exchange rates from the exchange rate API
- **aiosmtplib**: Asynchronous SMTP client used to send OTP emails securely over TLS/STARTTLS

---

## System Architecture

### High-Level Architecture Diagram

```
┌─────────────────────┐
│   Frontend (React)  │ (Deployed on Vercel)
└──────────┬──────────┘
           │ HTTPS/CORS
           ▼
┌─────────────────────┐
│   FastAPI Server    │ (Main API Layer)
├─────────────────────┤
│ - Performance MW    │
│ - Authentication    │
│ - Authorization     │
│ - Cache Manager     │
│ - Business Logic    │
│ - StaticFiles Mount │ ← /static/uploads/
└──────────┬──────────┘
           ├──────────────────────────┬──────────────────────┐
           │ TCP Connection           │ Cache Lookups        │ Local Disk
           ▼                          ▼                       ▼
┌─────────────────────┐    ┌─────────────────────┐  ┌─────────────────────┐
│     MongoDB         │    │     Redis / Memory  │  │  static/uploads/    │
├─────────────────────┤    ├─────────────────────┤  ├─────────────────────┤
│ - users             │    │ - Dashboard cache   │  │ - users/  (photos)  │
│ - clients           │    │ - User cache        │  │ - clients/(photos)  │
│ - orders            │    └─────────────────────┘  │ - receipts/(imgs)   │
│ - payments          │                              └─────────────────────┘
│ - manuscripts       │
│ - payment_history   │
│ - tokens            │
│ - otps              │
└─────────────────────┘
```

### Architectural Layers

#### 1. **Presentation Layer (Frontend)**
- React-based dashboard, communicating with the FastAPI backend via REST APIs. Handles UI views, forms, and client-side routing.

#### 2. **API Layer (FastAPI)**
- Handles HTTP requests, parses schemas, triggers validation, executes business logic, and formats responses consistently.
- Integrates a `PerformanceMiddleware` to log slow requests (>1.0 second) and medium requests (>0.5 second).

#### 3. **Authentication Layer (JWT + OTP)**
- Issues JWT bearer tokens for session management.
- Privileged users (Admin/Manager) must complete a two-step authentication process requiring email OTP verification.
- Tokens are automatically blacklisted/invalidated in the database upon logout.

#### 4. **Business Logic Layer**
- Implements currency conversion, unified client-order-payment creation, database synchronization (rippling client modifications), and non-overlapping ID range checks.

#### 5. **Persistence Layer (MongoDB)**
- Stores structured documents in MongoDB. Uses single-field, compound, and TTL indexes for search and performance optimization.

---

## Directory Structure

```
Email Dashboard/
│
├── app/                             # Core Application Code
│   ├── main.py                      # Application entry point & API endpoints
│   ├── auth.py                      # JWT verification & Fernet encryption logic
│   ├── schemas.py                   # Pydantic data models & validators
│   ├── database.py                  # MongoDB connection & index initialization
│   ├── config.py                    # Environment configuration
│   ├── cache.py                     # Caching layer (Redis / TTLCache)
│   └── currency_converter.py        # INR ↔ USD live exchange rate converter
│
├── static/                          # Static Assets & Uploaded Files
│   ├── default_user.png             # Fallback user profile photo
│   ├── default_client.png           # Fallback client photo
│   └── uploads/                     # ← Runtime image uploads (auto-created)
│       ├── users/                   # User profile photos (UUID-named files)
│       ├── clients/                 # Client photos (UUID-named files)
│       └── receipts/                # Payment receipt screenshots (UUID-named files)
│
├── docs/                            # Project Documentation
│   ├── PROJECT_ARCHITECTURE.md      # This file
│   ├── DATABASE_DOCUMENTATION.md    # Database schemas
│   ├── API_DOCUMENTATION.md         # API reference
│   └── ...
│
├── scripts/                         # Utility & Administrative Scripts
│   ├── seed_data.py                 # Initial DB seed data
│   ├── mock_data_generator.py       # Detailed mock data generator
│   ├── clear_db.py                  # Database reset script
│   ├── check_admins.py              # Administrative check for existing admins
│   ├── consolidate_payment_history.py # Syncs historical payments to history
│   └── migration_add_new_fields.py  # Migrates database schema to support new fields
│
├── migrate_images.py                # One-time migration: MongoDB blobs → filesystem
├── .env                             # Environment variables configuration
├── requirements.txt                 # Project dependencies
├── pyproject.toml                   # Project metadata & requirements
├── vercel.json                      # Vercel deployment config
└── render.yaml                      # Render deployment config
```

---

## Database Design

### Collections Overview

The database contains **8 collections** optimized with indexes for query speeds and aggregation.

```
┌──────────┐
│  users   │  (System Users & Authentication)
└────┬─────┘
     │
     ├─── handles ──→ clients (1-to-Many)
     ├─── owns ──────→ tokens (1-to-Many)
     └─── receives ──→ otps (1-to-Many)

┌──────────┐
│ clients  │  (Client Information)
└────┬─────┘
     │
     ├─── submits ──→ manuscripts (1-to-Many, Optional)
     └─── places ───→ orders (1-to-Many)
                          │
                          ├─→ payments (1-to-1 Phase Document)
                          └─→ payment_history (1-to-Many logs)
```

### Collection Schemas & Fields

#### 1. **users**
Stores account data. Passwords are encrypted using two-way Fernet encryption, allowing administrative retrieval. Profile photos are stored on the server filesystem; only the relative path is stored in MongoDB.
```javascript
{
  "_id": ObjectId("..."),
  "email": "employee@company.com",          // Unique login identifier
  "full_name": "Jane Doe",
  "password": "gAAAAABm...",                // Fernet encrypted string
  "role": "employee",                       // admin | manager | employee
  "phone_number": "+1234567890",             // Work phone number
  "personal_email": "jane.personal@gmail.com", // Personal contact email
  "personal_number": "+1987654321",          // Personal phone number
  "branch": "East Coast",
  "profile_names": ["Profile_A", "Profile_B"], // Multiple profiles managed by employee
  "permissions": {
    "dashboard": []                         // Column permissions (Legacy)
  },
  "id_range_start": 100,                    // Auto-generated ID range start
  "id_range_end": 200,                      // Auto-generated ID range end
  "has_photo": true,
  "photo_path": "static/uploads/users/a1b2c3d4e5f6.jpg",  // Relative path on disk
  "photo_mime": "image/png"                 // MIME type for Content-Type header
}
```
**Indexes**: `email` (unique), `full_name`, `role`

#### 2. **clients**
Stores client credentials, affiliations, and handler associations. Client photos are stored on the server filesystem; only the relative path is stored in MongoDB.
```javascript
{
  "_id": ObjectId("..."),
  "client_id": "CL-2026-0100",             // Generated within handler range
  "name": "Global Research Ltd",
  "country": "USA",
  "email": "contact@research.com",
  "whatsapp_no": "+1987654321",
  "client_ref_no": "REF-2026-001",
  "client_link": "https://www.example.com",
  "bank_account": "ACC-9988-XX",
  "affiliation": "MIT Research",
  "total_orders": 5,                       // Denormalized order count
  "client_handler": "employee@company.com", // Employee email reference
  "client_drive_link": "https://drive...",  // Google Drive link
  "payment_drive_link": "https://drive...", // Proof of payment link
  "created_at": ISODate("2026-05-20T11:00:00Z"),
  "has_photo": false,
  "photo_path": "static/uploads/clients/b1c2d3e4f5a6.jpg",  // Relative path on disk
  "photo_mime": "image/jpeg"               // MIME type for Content-Type header
}
```
**Indexes**: `client_id` (unique), `client_handler`

#### 3. **orders**
Represents assignments. It contains detailed pricing components, timeline markers, and tracking fields.
```javascript
{
  "_id": ObjectId("..."),
  "order_id": "ORD-2026-005",              // Globally sequential order ID
  "reference_id": "REF-2026-0100",          // Generated within handler range
  "profile_name": "Profile_A",             // Profile used for assignment
  "client_ref_no": "REF-2026-001",
  "s_no": 5,
  "order_date": ISODate("2026-05-20T11:00:00Z"),
  "client_id": "CL-2026-0100",             // FK → clients
  "manuscript_id": "MS-CL-2026-0100-REF-2026-0100", // FK → manuscripts (Optional)
  "journal_name": "IEEE Access",
  "title": "A Review of Neural Nets",
  "order_type": "WO",                      // WO | PO | Thesis writing | etc.
  "index": "SCI",                          // SCI | Scopus | ESCI | etc.
  "rank": "Q1",                            // Q1 | Q2 | Q3 | Q4
  "currency": "USD",                       // USD | INR
  "total_amount": 1200.00,
  "writing_amount": 800.00,
  "modification_amount": 300.00,
  "po_amount": 100.00,
  "writing_start_date": ISODate("2026-05-21T00:00:00Z"),
  "writing_end_date": ISODate("2026-06-21T00:00:00Z"),
  "modification_start_date": null,
  "modification_end_date": null,
  "po_start_date": null,
  "po_end_date": null,
  "payment_status": "Pending",             // Pending | Partial Paid | Paid
  "order_status": "Active",                // Active | Inactive
  "payment_drive_link": "https://drive...",
  "client_drive_link": "https://drive...",
  "clients_details": "Important manuscript details",
  "is_new_order": "yes",
  "remarks": null,
  "created_at": ISODate("2026-05-20T11:00:00Z"),
  "updated_at": ISODate("2026-05-20T11:00:00Z"),
  // Receipt screenshot files (stored on disk; relative paths saved here)
  "receipt_phase_1_path": "static/uploads/receipts/c1d2e3.jpg",
  "receipt_phase_1_mime": "image/jpeg",
  "receipt_phase_2_path": null,
  "receipt_phase_2_mime": null,
  "receipt_phase_3_path": null,
  "receipt_phase_3_mime": null
}
```
**Indexes**: `order_id` (unique), `client_id`, `reference_id`, `s_no`, `order_date`, compound index on `(client_id, order_id)`

#### 4. **payments**
Aggregated billing information tracking payment phases on an order.
```javascript
{
  "_id": ObjectId("..."),
  "client_id": "CL-2026-0100",
  "order_id": "ORD-2026-005",
  "reference_id": "REF-2026-0100",
  "client_ref_number": "REF-2026-001",
  "phase": 1,
  "amount": 400.00,
  "payment_received_account": "Bank-A",
  "payment_date": ISODate("2026-05-20T11:00:00Z"),
  "phase_1_payment": 400.00,
  "phase_1_payment_date": ISODate("2026-05-20T11:00:00Z"),
  "phase_1_payment_details": "First installment paid",
  "phase_2_payment": 0.0,
  "phase_2_payment_date": null,
  "phase_2_payment_details": null,
  "phase_3_payment": 0.0,
  "phase_3_payment_date": null,
  "phase_3_payment_details": null,
  "status": "paid",
  "paid_amount": 400.00,
  "created_at": ISODate("2026-05-20T11:00:00Z")
}
```
**Indexes**: `client_id`, `order_id`, `phase`, compound index on `(order_id, phase)`

#### 5. **payment_history**
Flat log of payment actions, allowing append-only audit tracking.
```javascript
{
  "_id": ObjectId("..."),
  "client_name": "Global Research Ltd",
  "client_id": "CL-2026-0100",
  "order_id": "ORD-2026-005",
  "reference_id": "REF-2026-0100",
  "order_title": "A Review of Neural Nets",
  "amount": 1200.00,
  "paid_amount": 400.00,
  "payment_date": ISODate("2026-05-20T11:00:00Z"),
  "payment_received_account": "Bank-A",
  "phase_1_payment": 400.00,
  "phase_1_payment_date": ISODate("2026-05-20T11:00:00Z"),
  "phase_1_payment_details": "First installment paid",
  "phase_2_payment": 0.0,
  "phase_2_payment_date": null,
  "phase_2_payment_details": null,
  "phase_3_payment": 0.0,
  "phase_3_payment_date": null,
  "phase_3_payment_details": null,
  "created_at": ISODate("2026-05-20T11:00:00Z"),
  "updated_at": ISODate("2026-05-20T11:00:00Z")
}
```
**Indexes**: `client_id`, `order_id`, `payment_date`

#### 6. **manuscripts**
Stores target journal details and service types for associated files.
```javascript
{
  "_id": ObjectId("..."),
  "manuscript_id": "MS-CL-2026-0100-REF-2026-0100",
  "title": "A Review of Neural Nets",
  "journal_name": "IEEE Access",
  "order_type": "WO",
  "client_id": "CL-2026-0100",
  "created_at": ISODate("2026-05-20T11:00:00Z")
}
```
**Indexes**: `manuscript_id` (unique), `client_id`

#### 7. **tokens**
Session tracking database mapping JWTs to users.
```javascript
{
  "_id": ObjectId("..."),
  "user_email": "employee@company.com",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI...",
  "created_at": ISODate("2026-05-20T11:00:00Z") // Expires automatically after 10 hours
}
```
**Indexes**: `token` (unique), `created_at` (TTL index expiring in 10 hours)

#### 8. **otps**
Stores login OTP records.
```javascript
{
  "_id": ObjectId("..."),
  "email": "admin@company.com",
  "otp": "654321",
  "created_at": ISODate("2026-05-20T11:55:00Z")
}
```
**Indexes**: `email`

---

## Authentication & Authorization Flow

### 1. Two-Step Login Flow (Admins & Managers)

```
Client (Admin/Manager)                 FastAPI Backend                SMTP Server / DB
      │                                     │                                │
      ├─ POST /login (email, password) ───→ │                                │
      │                                     ├─ Decrypt & Verify Password     │
      │                                     ├─ Generate 6-digit OTP          │
      │                                     ├─ Store OTP in `otps` ─────────→│
      │                                     ├─ Send OTP Email via SMTP ─────→│
      │ ← Response: {otp_required: true} ───┤                                │
      │                                     │                                │
      │                                     │                                │
      ├─ POST /verify-otp (email, otp) ───→ │                                │
      │                                     ├─ Fetch & Validate OTP          │
      │                                     ├─ Issue JWT Access Token        │
      │                                     ├─ Store in `tokens` collection  │
      │                                     ├─ Delete OTP from DB            │
      │ ← Response: {access_token: "JWT"} ──┤                                │
```

- **Direct Login**: Employees skip OTP verification and receive a JWT access token immediately upon submitting correct email and password credentials.
- **OTP Expiration**: OTPs are valid for exactly **5 minutes** from generation.

### 2. Session Invalidation (Logout)
Calling `POST /logout` drops the active JWT record from the `tokens` collection, rendering it invalid for subsequent requests.

### 3. Role Hierarchy & Restrictions

- **Admin**: Full access. Bootstrapped using `/init-super-admin` (permitted up to 5 Admins total). Can create other Admins and Managers.
- **Manager**: Can create Managers and Employees. Can assign clients. Has global read access to dashboard columns.
- **Employee**: Restricted to records where `client_handler` equals the employee's login email. Employee actions are confined to this dataset.

*Note: Column-level editing permissions (previously stored in `users.permissions.dashboard`) are legacy. All authenticated users are authorized to update fields inside their scoped clients/orders.*

---

## ID Range Management

To prevent collision of custom identifiers across distributed entries, the application enforces non-overlapping **ID Ranges** for employees.

- Admins/Managers configure numeric boundaries (e.g., employee A has start `100` to end `200`) when creating or updating employees.
- When an employee initiates a Client or Order record creation without manual IDs, the system generates IDs matching the format:
  - **Client ID**: `CL-{YYYY}-{Sequential Number}` (e.g. `CL-2026-0101`)
  - **Reference ID**: `REF-{YYYY}-{Sequential Number}` (e.g. `REF-2026-0101`)
- The system fetches the highest existing sequential identifier in the current year within the employee's range and increments it by 1.
- Range overlap validations are executed during user configuration (`POST /users` and `PUT /users/permissions`), raising a `400 Bad Request` if bounds intersect with an existing employee range.

---

## API Endpoints

### Authentication & Bootstrapping

#### `POST /init-super-admin`
- **Purpose**: Seed the initial super admin account (disabled once 5 admins exist).
- **Body**: `UserCreate` schema.

#### `POST /login`
- **Purpose**: Authenticate user and initiate verification.
- **Body**: `LoginRequest` (email, password).
- **Response**: `{ "otp_required": true }` for Admin/Manager; `{ "access_token": "..." }` for Employee.

#### `POST /verify-otp`
- **Purpose**: Verify the 6-digit OTP code for Admin/Manager login.
- **Body**: `OTPVerifyRequest` (email, otp).
- **Response**: JWT access token.

#### `POST /logout`
- **Purpose**: Invalidate JWT token.
- **Headers**: Authorization Bearer Token.

#### `GET /otp-status`
- **Purpose**: Retrieve the current status (enabled/disabled) of the global OTP requirement.
- **Auth Required**: Admin or Manager

#### `POST /toggle-otp`
- **Purpose**: Enable or disable the OTP requirement globally for Admins and Managers.
- **Auth Required**: Admin only

---

### User & Permission Management

#### `POST /users`
- **Purpose**: Create a new account (Admin, Manager, or Employee). Manager+ permissions required.

#### `POST /managers`
- **Purpose**: Specialized endpoint to create a Manager. Manager+ permissions required.

#### `GET /users`
- **Purpose**: Return all registered Employees. Password fields are decrypted on response. Manager+ permissions required.

#### `GET /admins`
- **Purpose**: Return all Managers and Admins. Passwords decrypted on response. Admin permissions required.

#### `PUT /users/permissions`
- **Purpose**: Update an Employee's auto-generation ranges (`id_range_start` and `id_range_end`). Manager+ permissions required.

#### `PUT /users/me/password`
- **Purpose**: Update current authenticated user password.

#### `PUT /users/password`
- **Purpose**: Reset another user's password. Managers can only update Employees; Admins can update any user (except other Admins).

#### `GET /users/me/details`
- **Purpose**: Retrieve full details of the currently authenticated user, including nested statistics (dashboard stats, country split, order status details) and photo URL.

#### `GET /users/{email}/details`
- **Purpose**: Retrieve full details of a specific user. Manager+ permissions required. Includes `photo_url` field pointing to the user's photo on disk.

---

### Profile Customization & Photo Uploads

#### `PUT /users/profile` / `PUT /users/{email}/profile`
- **Purpose**: Update contact details (personal email, personal phone, branch) and upload a profile photo (max 500KB). Photo is saved to `static/uploads/users/` on disk.
- **Request Type**: `multipart/form-data`.
- **Response**: Includes `photo_url` with the relative path to the saved file.

#### `GET /users/{email}/photo`
- **Purpose**: Serve the user's avatar image directly from disk, falling back to `static/default_user.png`.

#### `POST /users/{email}/photo`
- **Purpose**: Upload or replace a user's profile photo. Saves to `static/uploads/users/`. Returns `photo_url`.
- **Response**: Includes `photo_url` field.

#### `POST /clients/{client_id}/photo`
- **Purpose**: Upload a client avatar image. Saves to `static/uploads/clients/`. Manager+ permissions required.
- **Note**: Clients can also be created with a photo by passing `photo_base64` + `photo_mime` in `POST /clients` or `client_photo_base64` in `POST /unified/create`. The server decodes the base64 string and saves it to disk.

#### `GET /clients/{client_id}/photo`
- **Purpose**: Serve client photo from disk, falling back to `static/default_client.png`.

---

### Currency Converter

#### `GET /currency/exchange-rate`
- **Purpose**: Fetch live exchange rate from INR to USD, using caching to throttle external hits.

#### `POST /currency/inr-to-usd`
- **Purpose**: Convert INR amount to USD using current rates.
- **Body**: `{ "amount_inr": float }`

#### `POST /currency/usd-to-inr`
- **Purpose**: Convert USD amount to INR using current rates.
- **Body**: `{ "amount_usd": float }`

#### `POST /currency/convert`
- **Purpose**: Perform a generic currency conversion between any supported currencies (USD, INR, CNY, AED, SAR).
- **Body**: `CurrencyConvertRequest` containing amount, from_currency, and to_currency.

---

### Client Management

#### `POST /clients`
- **Purpose**: Create a new client record.

#### `GET /clients`
- **Purpose**: List clients. For Employees, only assigned clients are returned. Response includes options/metadata for dashboard dropdowns.

#### `GET /clients/{client_id}`
- **Purpose**: Fetch detailed info for a single client. Manager+ permissions required.

#### `POST /clients/assign`
- **Purpose**: Assign an Employee as handler to a client. Manager+ permissions required.

---

### Order, Manuscript & Payment Operations

#### `POST /orders`
- **Purpose**: Create a standalone order. Manager+ permissions required.

#### `GET /orders`
- **Purpose**: List orders. Employees are restricted to orders of assigned clients.

#### `POST /manuscripts`
- **Purpose**: Record a manuscript submission. Manager+ permissions required.

#### `GET /manuscripts`
- **Purpose**: Fetch manuscripts. Scoped to employee assignments if not Admin/Manager.

#### `POST /payments`
- **Purpose**: Record a billing phase transaction. Manager+ permissions required.

#### `GET /payments`
- **Purpose**: List billing phase details.

#### `GET /payments/history`
- **Purpose**: Fetch audit history entries from `payment_history_collection`.

#### `GET /payments/pending-summary`
- **Purpose**: Retrieve summary details and rankings of pending balances. Manager+ permissions required.

#### `POST /orders/{order_db_id}/receipt/{phase}`
- **Purpose**: Upload a payment receipt screenshot for a specific payment phase (1, 2, or 3). File is saved to `static/uploads/receipts/` on disk; the relative path is stored in the `orders` collection.
- **Request Type**: `multipart/form-data`.
- **Response**: Includes `receipt_url` with the relative path to the saved file.

#### `GET /orders/{order_db_id}/receipt/{phase}`
- **Purpose**: Serve the receipt image file directly from disk for the specified phase.

#### `DELETE /orders/{order_db_id}/receipt/{phase}`
- **Purpose**: Delete a previously uploaded payment receipt screenshot. Removes the file from disk and unsets the path field in MongoDB.

---

### Bank Account Management

#### `GET /bank-accounts`
- **Purpose**: Fetch all registered bank accounts (often used for frontend dropdowns).

#### `POST /bank-accounts`
- **Purpose**: Create a new bank account entry. Manager+ permissions required.

#### `PUT /bank-accounts/{account_id}`
- **Purpose**: Update an existing bank account. Manager+ permissions required.

#### `DELETE /bank-accounts/{account_id}`
- **Purpose**: Delete a bank account. Manager+ permissions required.

---

### Dashboard & Unified API

#### `GET /dashboard/orders`
- **Purpose**: Unified main dashboard endpoint. Executes an aggregation query linking client details, orders, and payment records into flat rows. Supported by caching layers. **Injects `client_photo_url` and `receipt_phase_N_url` relative path strings** (previously base64 blobs) into each row for efficient frontend rendering.

#### `PATCH /dashboard/orders/{order_db_id}`
- **Purpose**: Batch update details (Client fields, Order fields, Payment phases) in a single request.
- **Database Synchronization**: Updates to shared client fields ripple across related documents. Changing `client_id` propagates the new key across Orders, Payments, and Manuscripts collections. Automatically logs mutations in the `payment_history` collection.

#### `POST /unified/create`
- **Purpose**: Create Client, Order, Manuscript, and Payment documents in a single transaction-like request.
- **Flow**:
  1. Checks if client exists by `client_id` or name; creates new client if missing.
  2. If `client_photo_base64` is provided, decodes the base64 string, saves the file to `static/uploads/clients/`, and stores the path in MongoDB.
  3. Automatically links or creates a manuscript if specified.
  4. Sequentially auto-generates order serial number (`s_no`) and unique system-wide `order_id`.
  5. Automatically flows links (e.g., `payment_drive_link`) from client record to order if not overridden.
  6. Optionally records initial payment details and updates client order count (`total_orders`).

---

## Key Features

### 1. Symmetric Password Encryption
Storing passwords with Fernet symmetric encryption instead of hashing allows managers and admins to recover passwords to provide support or audits for employee workspace accounts.

### 2. Auto-generated Padded IDs
IDs are formatted with a year prefix and serial index (e.g., `CL-2026-0001`). This ensures clean record tracking. Ranges are validated against other employee ranges to prevent overlap collisions.

### 3. Unified Aggregated APIs
Endpoints `/dashboard/orders` and `/unified/create` reduce roundtrips. Instead of querying individual resources, the dashboard joins collections using MongoDB aggregation lookups.

### 4. Append-Only Payment Logs
The `payment_history` collection captures snapshots of order totals, amounts paid, received accounts, and phase completions, building a clean transaction timeline.

### 5. Filesystem Image Storage
All binary image assets (user/client profile photos and payment receipt screenshots) are stored on the **server filesystem** under `static/uploads/`. MongoDB stores only the relative file path (e.g., `static/uploads/receipts/abc123.jpg`) rather than the binary blob. This approach:
- **Eliminates** BSON 16 MB document size risk from large binary blobs
- **Eliminates** expensive in-memory base64 encoding/decoding on every dashboard request
- **Enables** browser-native HTTP caching of static image files
- **Enables** direct CDN fronting of the `/static/` route in production
- Photos are served via FastAPI's `StaticFiles` mount at `/static/uploads/{subfolder}/{filename}`
- A **one-time migration script** (`migrate_images.py`) is included to move existing MongoDB binary blobs to disk

---

## Security Implementation

### 1. Secure Transport & CORS
CORS middleware checks requests against a configured whitelist of allowed origins (e.g., Vercel domains, localhost) and strips trailing slashes to prevent matching mismatches.

### 2. Session Integrity
JWT verification validates signature, expiration, and checks the token's presence in the database `tokens` collection, ensuring that logged-out/revoked sessions cannot hit endpoints.

### 3. Input Sanitization & Validation
Pydantic V2 models parse input variables, verifying constraints like email formats (`EmailStr`), non-empty strings, and converting empty strings to `None` for database compatibility.

### 4. Masked Error Disclosures
A global exception handler catches unhandled internal errors, returning a generic `Internal Server Error` message to clients to prevent database details or server traces from leaking.

---

## Deployment & Configuration

### Environment Configuration (.env example)
```bash
# Database Configuration
MONGO_URI=mongodb+srv://...
DB_NAME=email_dashboard

# JWT Configuration
SECRET_KEY=yoursecretkeyhere
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=600

# Two-Way Encryption
ENCRYPTION_KEY=yourfernetencryptionkey32bytes=

# SMTP Config
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=sender@gmail.com
SMTP_PASSWORD=app-password
EMAIL_FROM=noreply@dashboard.com

# CORS Configuration (Comma Separated)
ALLOWED_ORIGINS=http://localhost:5173,https://my-dashboard.vercel.app
```

---

## Workflow Examples

### Example 1: Creating an Employee & Allocating ID Range
1. Admin logs in with OTP validation.
2. Admin opens user creation form, providing email and name. Admin sets `id_range_start: 500` and `id_range_end: 600`.
3. Server executes range check. If no other employee occupies bounds in `[500, 600]`, the user is inserted.
4. Admin can view the encrypted employee password securely decrypted on their panel.

### Example 2: Unified Submission Flow (Employee)
1. Employee fills out the Unified Creation form with client, paper, and payment details.
2. Employee submits the form, hitting `/unified/create`.
3. Server generates Client ID `CL-2026-0501` (from range start 500) and Order ID `ORD-2026-009`.
4. Manuscript document is registered, linking client and order.
5. First payment phase is recorded. Client's total order count increments to `1`.
6. Client and orders are immediately available on the employee's dashboard.

---

*This document serves as the absolute architecture outline for the Email Dashboard API.*

**Last Updated**: May 28, 2026  
**API Version**: 1.1.0-Phase1 (Image Storage Migration)  
**Target Environment**: Vercel (Frontend) & Render/Docker (Backend)

> **v1.1.0 Change Summary**: Migrated image storage from MongoDB binary blobs (`photo_data`, `receipt_phase_N_data`) to server filesystem (`static/uploads/`). All API responses now return URL path strings (`photo_url`, `receipt_phase_N_url`, `client_photo_url`) instead of base64-encoded data payloads. A `StaticFiles` mount at `/static` serves files publicly. Run `migrate_images.py` once to migrate existing data.
