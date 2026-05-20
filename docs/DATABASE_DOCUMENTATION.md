# Database Documentation - Email Dashboard

This document provides a detailed overview of the MongoDB collections and the relational structure of the Email Dashboard API.

---

## 1. Collections Overview

### users
Stores user accounts, roles, and access permissions.
- **Fields**: 
    - `email`: Unique identifier (EmailStr).
    - `full_name`: User's full name.
    - `password`: Two-way encrypted password (Fernet).
    - `role`: `admin`, `manager`, or `employee`.
    - `phone_number`: Optional contact number.
    - `permissions`: Legacy field (Previously used for column-level dashboard permissions; now all roles have full dashboard access).
    - `profile_names`: List of profiles managed by the user (Employees).

### clients
Stores client information.
- **Fields**: 
    - `client_id`: Custom primary key (e.g., `CLT001`).
    - `name`: Client's name.
    - `country`: Client's location.
    - `email`: Contact email.
    - `whatsapp_no`: WhatsApp contact.
    - `client_ref_no`: Reference provided by the client.
    - `client_link`: Link to client profile/site.
    - `bank_account`: Payment bank details.
    - `affiliation`: University/Company affiliation.
    - `clients_details`: Detailed notes about the client.
    - `client_drive_link`: Link to client's files (Google Drive).
    - `payment_drive_link`: Link to payment proofs.
    - `total_orders`: Total number of orders placed (denormalized).
    - `client_handler`: Unique email of the assigned Employee.

### manuscripts
Stores records for manuscripts submitted by clients (~30% submission rate).
- **Fields**: 
    - `manuscript_id`: Custom identifier (e.g., `MS-CLT001-1`).
    - `title`: Paper title.
    - `journal_name`: Target journal.
    - `order_type`: `writing`, `modification`, or `proofreading`.
    - `client_id`: FK to `clients`.

### orders
Each order represents a specific service for a paper.
- **Fields**: 
    - `order_id`: System-generated ID (e.g., `ORD001`).
    - `reference_id`: **Globally Unique** identifier created by the team.
    - `profile_name`: The specific profile used for this order.
    - `client_id`: FK to `clients`.
    - `manuscript_id`: FK to `manuscripts` (Nullable).
    - `title`: Paper title.
    - `total_amount`: Total cost in specified currency.
    - `writing_amount`, `modification_amount`, `po_amount`: Component costs.
    - `payment_status`: `Pending`, `Partial`, or `Paid`.
    - `writing_start_date`, `modification_start_date`, etc.

### payments
Tracks payment phases for orders.
- **Fields**: 
    - `client_id`: FK to `clients`.
    - `reference_id`: Copied from order for easy lookup.
    - `phase`: 1, 2, or 3.
    - `amount`: Amount in this phase.
    - `payment_date`: Date received.
    - `status`: `Pending` or `Paid`.

### tokens & otps
- `tokens`: Active session JWTs.
- `otps`: Temporary 2FA codes for Admin/Manager logins.

---

## 2. Relationships

The system uses logical IDs for relationships to ensure portability across services.

- **User → Client**: Linked via `client_handler` (User Email).
- **Client → Order**: Linked via `client_id`.
- **Order → Payment**: Linked via `reference_id` (Globally Unique).
- **Order → Manuscript**: Linked via `manuscript_id` (Optional).

---

## 3. ID Conventions

| Entity | ID Format | Example |
|---|---|---|
| Client | `CLT` + 3 digits | `CLT001` |
| Order | `ORD` + 3 digits | `ORD001` |
| Database ID | MongoDB `_id` (Hex) | `65f...456` (Used as `order_db_id` for updates) |
| Manuscript | `MS-` + ClientID + Seq | `MS-CLT001-1` |
| Reference | `EM-` + Year + Seq | `EM-2024-001` |
