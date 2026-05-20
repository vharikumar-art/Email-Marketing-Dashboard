# Email Dashboard API - Complete Project Architecture & Documentation

## Table of Contents
1. [Project Overview](#project-overview)
2. [Technology Stack](#technology-stack)
3. [System Architecture](#system-architecture)
4. [Directory Structure](#directory-structure)
5. [Database Design](#database-design)
6. [Authentication & Authorization Flow](#authentication--authorization-flow)
7. [API Endpoints](#api-endpoints)
8. [Key Features](#key-features)
9. [Security Implementation](#security-implementation)
10. [Deployment & Configuration](#deployment--configuration)
11. [Workflow Examples](#workflow-examples)

---

## Project Overview

### What is this project?

The **Email Dashboard API** is a comprehensive backend system designed to manage email communications, client relationships, manuscripts, orders, and payments. It's built with a **multi-tier Role-Based Access Control (RBAC)** system that allows different user roles to have varying levels of access and permissions.

### Purpose

The system serves as a centralized platform for:
- Managing client information and communications
- Tracking manuscript submissions (optional, ~30% of clients)
- Processing and managing orders for academic/editorial services
- Handling multi-phase payment tracking
- Providing column-level permissions for dashboard field access
- Implementing secure 2FA/OTP authentication for privileged users

### Target Users

- **Super Admins**: System administrators with full organizational control
- **Admins**: Senior management with broad access and user management capabilities
- **Managers**: Team leaders who can manage employees and access dashboard data
- **Employees**: Front-line staff with restricted access to assigned clients only

---

## Technology Stack

### Backend Framework
- **FastAPI**: Modern, fast ASGI web framework for building REST APIs
- **Python** (3.11+): Core programming language
- **Uvicorn**: ASGI server for running FastAPI applications

### Database
- **MongoDB**: NoSQL database for flexible, document-based data storage
- **PyMongo**: Python MongoDB driver for database connectivity

### Authentication & Security
- **Python-Jose**: JWT token creation and verification
- **Cryptography (Fernet)**: Two-way symmetric encryption for passwords and sensitive data
- **Bcrypt**: Legacy support for password hashing (transitioning to Fernet)

### Utilities
- **Pydantic**: Data validation and serialization
- **python-dotenv**: Environment variable management
- **python-docx**: (Newly added) For documentation generation

### Server Configuration
- **Uvicorn**: ASGI HTTP server
- **CORSMiddleware**: Cross-Origin Resource Sharing support
- **GZipMiddleware**: HTTP compression for optimized response sizes

---

## System Architecture

### High-Level Architecture Diagram

```
┌─────────────────────┐
│   Frontend (React)  │ (Deployed on Vercel)
├─────────────────────┤
         │ HTTPS/CORS
         │
         ▼
┌─────────────────────┐
│   FastAPI Server    │ (Main API Layer)
├─────────────────────┤
│ - Authentication    │
│ - Authorization     │
│ - Business Logic    │
│ - Error Handling    │
└──────────┬──────────┘
           │ TCP Connection
           ▼
┌─────────────────────┐
│     MongoDB         │ (Data Layer)
├─────────────────────┤
│ - users             │
│ - clients           │
│ - orders            │
│ - payments          │
│ - manuscripts       │
│ - tokens            │
│ - otps              │
└─────────────────────┘
```

### Architectural Layers

#### 1. **Presentation Layer (Frontend)**
- React-based dashboard
- Communicates via REST API
- Handles UI/UX and user interactions
- Deployed on Vercel

#### 2. **API Layer (FastAPI)**
- Receives HTTP requests from frontend
- Validates input using Pydantic schemas
- Enforces RBAC policies
- Executes business logic
- Returns structured JSON responses

#### 3. **Authentication Layer (JWT + OTP)**
- OAuth2 password bearer token scheme
- JWT-based session management
- OTP validation for 2FA (Admin/Manager only)
- Email-based OTP delivery via SMTP

#### 4. **Business Logic Layer**
- User management (creation, password updates)
- Client management (CRUD operations)
- Order processing and tracking
- Payment phase management
- Permission assignment and validation

#### 5. **Persistence Layer (MongoDB)**
- NoSQL document storage
- Collections for each entity
- Denormalized data for performance
- Reference-based relationships

---

## Directory Structure

```
Email Dashboard/
│
├── app/                             # Core Application Code
│   ├── main.py                      # Application entry point & endpoints
│   ├── auth.py                      # JWT & Encryption logic (Fernet)
│   ├── schemas.py                   # Pydantic data models
│   ├── database.py                  # MongoDB connection
│   └── config.py                    # App configuration
│
├── docs/                            # Project Documentation
│   ├── PROJECT_ARCHITECTURE.md      # This file
│   ├── DATABASE_DOCUMENTATION.md    # Database schemas
│   ├── API_DOCUMENTATION.md         # API reference
│   └── ...                          # Other guides
│
├── scripts/                         # Utility Scripts
│   ├── reset_passwords.py           # Database seeding script
│   ├── generate_docs.py             # Documentation generator
│   └── ...
│
├── tests/                           # Testing Suite
│
├── .env                             # Environment variables
├── requirements.txt                 # Dependencies
├── vercel.json                      # Vercel deployment config
└── render.yaml                      # Render deployment config
```

### File Purposes

| File | Purpose | Type |
|------|---------|------|
| `main.py` | Core API endpoints & app initialization | Source Code |
| `auth.py` | Password & JWT logic | Source Code |
| `schemas.py` | Request/response validation | Source Code |
| `database.py` | MongoDB connectivity | Source Code |
| `config.py` | Configuration & secrets | Source Code |
| `mock_data_generator.py` | Test data creation | Utility |
| `clear_db.py` | Database reset | Utility |
| `check_admins.py` | Admin verification | Utility |
| `README.md` | Installation guide | Documentation |
| `PROJECT_ARCHITECTURE.md` | This file | Documentation |

---

## Database Design

### Collections Relationship Diagram

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
                          └──→ payments (1-to-Many)
```

### Collection Schemas

#### 1. **users**
```javascript
{
  _id: ObjectId,
  email: "admin@company.com",              // Unique identifier
  full_name: "John Doe",
  password: "encrypted_string...",          // Two-way encrypted (Fernet)
  role: "admin",                           // admin | manager | employee
  phone_number: "+1234567890",             // Optional
  permissions: {
    dashboard: ["column1", "column2"]      // Column-level permissions
  },
  created_at: "2024-01-15T10:30:00Z"
}
```

**Indexes**: email (unique), role

#### 2. **clients**
```javascript
{
  _id: ObjectId,
  client_id: "CL-001",                     // Custom primary key
  name: "Global Research Ltd",
  country: "USA",
  email: "contact@research.com",           // Optional
  whatsapp_no: "+1987654321",              // Optional
  client_ref_no: "REF-2024-001",           // From client (optional)
  client_link: "https://www.example.com",  // Optional
  bank_account: "ACCOUNT-123",             // Optional
  affiliation: "Research Institute",       // Optional
  total_orders: 5,                         // Denormalized count
  client_handler: "John Doe",              // Ref to user full_name
  created_at: "2024-01-16T14:20:00Z"
}
```

**Indexes**: client_id (unique), client_handler (for filtering by manager)

#### 3. **orders**
```javascript
{
  _id: ObjectId,
  order_id: "ORD-2024-001",                // Auto-generated primary key
  reference_id: "REF-USER-001",            // User-created, globally unique
  client_ref_no: "CLIENT-REF",             // Optional, from client
  s_no: 1,                                 // Serial number
  order_date: "2024-01-17T09:00:00Z",
  client_id: "CL-001",                     // FK → clients
  manuscript_id: "MS-CL-001-1",            // FK → manuscripts (NULLABLE)
  journal_name: "Nature",
  title: "Advanced AI Systems",
  order_type: "writing",                   // writing | modification | proofreading
  index: "SCI",                            // SCI | Scopus | ESCI
  rank: "Q1",                              // Q1 | Q2 | Q3 | Q4
  currency: "USD",                         // USD | INR
  total_amount: 5000.00,
  writing_amount: 3000.00,
  modification_amount: 1500.00,
  po_amount: 500.00,
  writing_start_date: "2024-01-17",
  writing_end_date: "2024-02-17",
  modification_start_date: "2024-02-18",
  modification_end_date: "2024-02-25",
  po_start_date: "2024-02-26",
  po_end_date: "2024-02-28",
  payment_status: "pending",               // pending | partial | paid
  remarks: "Rush order",                   // Optional notes
  created_at: "2024-01-17T09:00:00Z",
  updated_at: "2024-01-20T15:30:00Z"
}
```

**Indexes**: order_id (unique), reference_id (unique), client_id, manuscript_id

#### 4. **payments**
```javascript
{
  _id: ObjectId,
  client_ref_number: "CLIENT-REF",        // Optional
  reference_id: "REF-USER-001",           // Copied from order (for lookup)
  client_id: "CL-001",                    // FK → clients
  order_id: "ORD-2024-001",               // FK → orders
  phase: 1,                               // 1 | 2 | 3 (payment phase)
  amount: 1500.00,
  payment_received_account: "Bank-A",
  payment_date: "2024-02-01",
  phase_1_payment: 1500.00,
  phase_1_payment_date: "2024-02-01",
  phase_2_payment: 1500.00,
  phase_2_payment_date: "2024-02-15",
  phase_3_payment: 2000.00,
  phase_3_payment_date: "2024-02-28",
  status: "paid",                         // pending | paid
  created_at: "2024-02-01T10:00:00Z"
}
```

**Indexes**: reference_id (for quick lookup), order_id, client_id, phase

#### 5. **manuscripts**
```javascript
{
  _id: ObjectId,
  manuscript_id: "MS-CL-001-1",           // Composite key format
  title: "Novel Algorithm Framework",
  journal_name: "IEEE Transactions",       // Target journal
  order_type: "writing",                  // writing | modification | proofreading
  client_id: "CL-001",                    // FK → clients
  created_at: "2024-01-18T11:00:00Z"
}
```

**Indexes**: manuscript_id (unique), client_id

#### 6. **tokens**
```javascript
{
  _id: ObjectId,
  user_email: "admin@company.com",        // FK → users
  token: "eyJhbGciOiJIUzI1NiIsInR5cCI...", // JWT token
  created_at: "2024-01-17T10:30:00Z"
}
```

**Indexes**: user_email, token

#### 7. **otps**
```javascript
{
  _id: ObjectId,
  email: "admin@company.com",             // FK → users
  otp: "123456",                          // 6-digit code
  created_at: "2024-01-17T10:30:00Z"      // For expiry calculation (15 minutes)
}
```

**Indexes**: email (for quick lookup)

---

## Authentication & Authorization Flow

### 1. Login Flow (Step-by-Step)

```
Client                          FastAPI Server              MongoDB
  │                                 │                           │
  ├─ POST /login ─────────────────→ │                           │
  │  (email, password)              │                           │
  │                                 ├── Find User ────────────→ │
  │                                 │                           │
  │                                 │ ← User Document ←─────── │
  │                                 │                           │
  │                                 ├─ Verify Password         │
  │                                 │  (bcrypt compare)        │
  │                                 │                           │
  │                         [IF Admin/Manager]                  │
  │                         Generate OTP (6 digits)             │
  │                         │                                   │
  │                         ├─ Store OTP ──────────────────────→│
  │                         │  (otps collection)               │
  │                         │                                   │
  │                         ├─ Send Email ─────→ [SMTP Server]  │
  │                         │  (with OTP code)                 │
  │                         │                                   │
  │ ← Login Response ────── │                                   │
  │  {                      │                                   │
  │   otp_required: true,   │                                   │
  │   email: "..."          │                                   │
  │  }                      │                                   │
  │                         │                                   │
```

### 2. OTP Verification Flow

```
Client                          FastAPI Server              MongoDB
  │                                 │                           │
  ├─ POST /verify-otp ────────────→ │                           │
  │  (email, otp)                   │                           │
  │                                 ├─ Find OTP ───────────────→│
  │                                 │  (in otps collection)    │
  │                                 │                           │
  │                                 │ ← OTP Document ←─────── │
  │                                 │                           │
  │                                 ├─ Check Expiry            │
  │                                 │  (< 15 minutes)          │
  │                                 │                           │
  │                                 ├─ Verify OTP Match       │
  │                                 │  (compare values)        │
  │                                 │                           │
  │                                 ├─ Generate JWT            │
  │                                 ├─ Store Token ────────────→│
  │                                 │  (tokens collection)     │
  │                                 │                           │
  │ ← Login Success ────── ────────│                           │
  │  {                              │                           │
  │   access_token: "JWT...",       │                           │
  │   token_type: "bearer"          │                           │
  │  }                              │                           │
  │                                 │                           │
```

### 3. Authenticated Request Flow

```
Client                          FastAPI Server              MongoDB
  │                                 │                           │
  ├─ GET /protected ──────────────→ │                           │
  │  Headers: Authorization         │                           │
  │  Bearer JWT_TOKEN               │                           │
  │                                 ├─ Extract JWT             │
  │                                 ├─ Verify Signature        │
  │                                 ├─ Check Expiry            │
  │                                 ├─ Decode Payload          │
  │                                 │  (extract email)         │
  │                                 │                           │
  │                                 ├─ Find User ──────────────→│
  │                                 │  (verify exists)         │
  │                                 │                           │
  │                                 │ ← User Document ←─────── │
  │                                 │                           │
  │                                 ├─ Check Role/Permissions  │
  │                                 │                           │
  │ ← Protected Data ────── ────────│                           │
  │  (if authorized)                │                           │
  │                                 │                           │
```

### Authorization Rules

#### By Role

| Action | Admin | Manager | Employee |
|--------|-------|---------|----------|
| Create User | ✅ | ✅ Employees only | ❌ |
| Create Manager | ✅ | ❌ | ❌ |
| Create Admin | ✅ Only (max 5) | ❌ | ❌ |
| View All Clients | ✅ | ✅ | ❌ See own assigned |
| Edit Dashboard | ✅ All fields | ✅ All fields | ✅ All fields (assigned clients) |
| 2FA Required | ✅ Yes | ✅ Yes | ❌ No |
| Update Own Password | ✅ | ✅ | ✅ |
| Update Others' Password | ✅ | ✅ Employees only | ❌ |

#### Editable Dashboard
- All users (Admin, Manager, Employee) can update any column on the dashboard.
- Update operations are performed using the Order's database ID (**`order_db_id`**).
- **Client Identification**: Updating a `client_id` for an order will automatically synchronize the change across all related collections (Orders, Payments, Manuscripts).
- **Data Normalization**: Fields like `Country` and `Email` belong to the Client document. Updating them for one order updates them for all orders belonging to that client.
- Employees are logically restricted to editing only their **assigned clients** and their related orders/payments.

---

## API Endpoints

### Authentication Endpoints

#### 1. Initialize Super Admin
```
POST /init-super-admin
Purpose: Bootstrap first admin (one-time operation)
Body: {
  "email": "admin@company.com",
  "full_name": "System Admin",
  "password": "securepass123"
}
Response: 201 Created
{
  "status_code": 201,
  "status": "success",
  "message": "Super Admin created successfully",
  "data": { user_object }
}
```

#### 2. Login
```
POST /login
Purpose: Authenticate user and initiate login
Body: {
  "email": "user@company.com",
  "password": "password123"
}
Response: 200 OK
{
  "otp_required": true/false,
  "email": "user@company.com",
  "access_token": "JWT..." (if employee),
  "token_type": "bearer"
}
```

#### 3. Verify OTP
```
POST /verify-otp
Purpose: Complete 2FA verification for Admin/Manager
Body: {
  "email": "admin@company.com",
  "otp": "123456"
}
Response: 200 OK
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

### User Management Endpoints

#### 1. Create User (Generic)
```
POST /users
Purpose: Create admin/manager/employee
Auth: Requires Manager+ privileges
Body: {
  "email": "john@company.com",
  "full_name": "John Smith",
  "role": "employee",
  "password": "password123",
  "phone_number": "+1234567890"
}
Response: 201 Created
```

#### 2. Create Manager
```
POST /managers
Purpose: Create manager specifically
Auth: Requires Admin privileges
Body: {
  "email": "manager@company.com",
  "full_name": "Manager Name",
  "password": "password123"
}
Response: 201 Created
```

#### 3. Get All Users
```
GET /users
Purpose: Retrieve all users
Auth: Requires Manager+ privileges
Response: 200 OK
{
  "status_code": 200,
  "data": [{ user objects }]
}
```

#### 4. Update Dashboard Row
```
PATCH /dashboard/orders/{order_db_id}
Purpose: Update client, order, or payment info
Auth: Authenticated users
Body: { DashboardUpdate fields }
```

#### 5. Update Own Password
```
PUT /users/me/password
Purpose: Change current user's password
Auth: All roles
Body: {
  "new_password": "newpass456"
}
Response: 200 OK
```

#### 6. Update Others' Password
```
PUT /users/password
Purpose: Admin/Manager updates employee password
Auth: Requires Manager+ privileges
Body: {
  "email": "employee@company.com",
  "new_password": "newpass456"
}
Response: 200 OK
```

#### 7. Update Permissions
```
PUT /users/permissions
Purpose: Assign column-level dashboard permissions
Auth: Requires Manager+ privileges
Body: {
  "email": "employee@company.com",
  "permissions": {
    "dashboard": ["status", "remarks", "amount"]
  }
}
Response: 200 OK
```

### Client Management Endpoints

#### 1. Create Client
```
POST /clients
Purpose: Add new client
Auth: Requires Manager+ privileges
Body: {
  "client_id": "CL-001",
  "name": "Research Labs Inc",
  "country": "USA",
  "email": "contact@labs.com",
  "whatsapp_no": "+1234567890"
}
Response: 201 Created
```

#### 2. Get All Clients
```
GET /clients
Purpose: Retrieve all clients (or assigned for employees)
Auth: Authenticated users
Response: 200 OK
{
  "data": [{ client objects }]
}
```

#### 3. Get Client by ID
```
GET /clients/{client_id}
Purpose: Get specific client details
Auth: Requires Manager+ privileges
Response: 200 OK
```

#### 4. Assign Client
```
POST /clients/assign
Purpose: Assign client to employee/manager
Auth: Requires Manager+ privileges
Body: {
  "client_id": "CL-001",
  "handler_email": "employee@company.com"
}
Response: 200 OK
```

### Order Management Endpoints

#### 1. Create Order
```
POST /orders
Purpose: Create new order
Auth: Requires Manager+ privileges
Body: {
  "order_id": "ORD-2024-001",
  "reference_id": "REF-USER-001",
  "client_id": "CL-001",
  "journal_name": "Nature",
  "title": "Advanced AI",
  "order_type": "writing",
  "total_amount": 5000
}
Response: 201 Created
```

#### 2. Get Orders
```
GET /orders
Purpose: Retrieve orders
Auth: Authenticated users
Response: 200 OK
```

#### 3. Update Order
```
PUT /orders/{order_id}
Purpose: Update order details
Auth: Requires Manager+ privileges
Response: 200 OK
```

### Payment Management Endpoints

#### 1. Create Payment
```
POST /payments
Purpose: Record payment transaction
Auth: Requires Manager+ privileges
Body: {
  "order_id": "ORD-2024-001",
  "reference_id": "REF-USER-001",
  "phase": 1,
  "amount": 1500,
  "payment_date": "2024-02-01",
  "status": "paid"
}
Response: 201 Created
```

#### 2. Get Payments
```
GET /payments
Purpose: Retrieve payment records
Auth: Authenticated users
Response: 200 OK
```

### Dashboard Endpoints

#### 1. Get Dashboard Data
```
GET /dashboard
Purpose: Retrieve dashboard statistics
Auth: Authenticated users
Response: 200 OK
{
  "data": {
    "overall_amount": 150000,
    "total_clients": 25,
    "pending_orders": 5,
    "recent_payments": [...]
  }
}
```

#### 2. Update Dashboard
```
PUT /dashboard/{order_id}
Purpose: Update dashboard-specific fields
Auth: Requires column permission
Body: {
  "status": "updated",
  "remarks": "Processing..."
}
Response: 200 OK
```

---

## Key Features

### 1. Multi-tier RBAC System

**Three Role Levels:**

- **Admin**: 
  - Full system access
  - Maximum 5 Admins allowed
  - Can create other Admins
  - 2FA required for login

- **Manager**: 
  - Can manage employees
  - Full dashboard access
  - Can assign permissions
  - 2FA required for login

- **Employee**: 
  - Limited to assigned clients
  - Can only view/update permitted dashboard columns
  - No 2FA required
  - Restricted action set

### 2. Two-Factor Authentication (2FA)

- **OTP Method**: Email-based 6-digit code
- **Who Uses**: Admin and Manager roles only
- **Duration**: 15-minute expiry
- **Delivery**: SMTP email service
- **Implementation**: Stored in `otps` collection

**Flow**:
1. User enters email + password
2. System sends OTP to email
3. User verifies OTP within 15 minutes
4. System generates JWT token

### 3. Column-Level Permissions

Employees can only update specific dashboard fields as granted by Admin/Manager.

**Permission Structure**:
```javascript
permissions: {
  dashboard: ["status", "remarks", "amount"]  // Granted columns
}
```

**Validation**: 
- Each update request checks if user has permission for modified fields
- Returns 403 Forbidden if unauthorized

### 4. JWT Token Management

- **Type**: HS256 (HMAC with SHA-256)
- **Payload**: Email (sub), Expiration (exp)
- **Storage**: Database tokens collection (for audit trail)
- **Validation**: Every protected endpoint validates token

### 5. Comprehensive Audit Trail

- `created_at`: Records creation timestamp
- `updated_at`: Tracks last modification
- `tokens` collection: Maintains session history
- `otps` collection: Logs authentication attempts

### 6. Denormalized Data for Performance

- `clients.total_orders`: Count stored directly
- `orders.payment_status`: Cached state from payments
- Reduces need for expensive aggregations
- Trade-off: Consistency responsibility on updates

---

## Security Implementation

### 1. Password Security

```python
# Using bcrypt with random salt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Hashing: Automatic salt generation, random rounds
hashed = pwd_context.hash(plain_password)

# Verification: Constant-time comparison
is_valid = pwd_context.verify(plain_password, hashed)
```

**Security Features**:
- Bcrypt with automatic salt (2^rounds iterations)
- Never stores plaintext passwords
- Constant-time comparison prevents timing attacks

### 2. JWT Token Security

```python
# Algorithm: HS256 (HMAC-SHA256)
# Secret: Strong 256+ bit key
# Expiry: Configurable (default 120 minutes)

token = jwt.encode(
  {"sub": email, "exp": expire_time},
  SECRET_KEY,
  algorithm="HS256"
)
```

**Security Features**:
- Cryptographically signed tokens
- Expiration enforced on every request
- Token revocation possible (check tokens table)

### 3. OTP Security

```python
# Generated as: 6 random digits
# Delivered: Via secure SMTP over TLS
# Storage: In database with timestamp
# Expiry: 15-minute window
```

**Security Features**:
- Random generation using secure RNG
- Limited 15-minute window
- Auto-expires in database
- Only 6-digit space (brute-force resistant with rate limiting)

### 4. CORS Security

```python
# Whitelist specific origins
ALLOWED_ORIGINS = [
  "https://marketing-dashboard.vercel.app",
  "http://localhost:5173"
]

# Only specified origins can make requests
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS)
```

**Security Features**:
- Prevents unauthorized cross-origin requests
- Configurable per environment
- Credentials allowed only for trusted origins

### 5. Input Validation

```python
# Pydantic models validate all inputs
class UserCreate(BaseModel):
  email: EmailStr            # Email format validation
  full_name: str
  password: str              # Length/complexity validated
  role: UserRole             # Enum restriction

# Automatic validation + sanitization
```

**Security Features**:
- Type validation (prevents injection)
- Format validation (EmailStr)
- Enum validation (restricted values)
- Length constraints (prevents buffer overflow)

### 6. Error Handling & Information Disclosure

```python
# Generic error responses (no leak of internal details)
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
  return JSONResponse(
    status_code=500,
    content={
      "status": "error",
      "message": "Internal server error",  # Generic message
      "data": None
    }
  )
```

**Security Features**:
- No stack traces in responses
- Generic error messages
- Prevents information leakage

### 7. HTTPS & Transport Security

- **Production**: All HTTPS connections required
- **CORS**: Credentials allowed only on HTTPS
- **Headers**: Secure cookie flags (if using cookies)
- **HSTS**: Should be configured on reverse proxy

### 8. Rate Limiting Recommendations

*Currently not implemented, but recommended for production*:

```python
# Example using slowapi
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/login")
@limiter.limit("5/minute")  # 5 attempts per minute
def login(request: Request, email: str, password: str):
  ...
```

---

## Deployment & Configuration

### Environment Variables (.env)

```bash
# MongoDB
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net
DB_NAME=email_dashboard

# JWT Configuration
SECRET_KEY=your-256-bit-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=120

# SMTP (for OTP emails)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=noreply@company.com

# CORS
ALLOWED_ORIGINS=https://frontend.vercel.app,http://localhost:5173

# Server
HOST=0.0.0.0
PORT=8000
```

### Docker Deployment (Recommended)

```dockerfile
FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Running Locally

```bash
# Clone and setup
git clone <repo>
cd "Email Dashboard"

# Create virtual environment
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
uv sync

# Create .env file
cp .env.example .env
# Edit .env with your settings

# Run server
uv run uvicorn main:app --reload

# Access API
# Swagger UI: http://localhost:8000/docs
# ReDoc: http://localhost:8000/redoc
```

### Deployment Platforms

#### Vercel (Frontend-ready)
```yaml
# vercel.json
{
  "buildCommand": "echo 'Frontend deployment'",
  "outputDirectory": "dist"
}
```

#### Render.com (Backend-ready)
```yaml
# render.yaml
services:
  - type: web
    name: email-dashboard-api
    env: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0
```

---

## Workflow Examples

### Example 1: Employee Login & View Assigned Clients

```
1. Employee navigates to login page
2. Submits email + password to POST /login
3. Server verifies credentials
4. Server checks role (employee) → No OTP required
5. Server generates JWT token
6. Returns access_token to frontend
7. Frontend stores token in localStorage
8. Employee navigates to "My Clients"
9. Frontend sends GET /clients with Authorization header
10. Server validates JWT
11. Server queries clients where client_handler = current user
12. Returns only assigned clients
```

### Example 2: Manager Creating Employee & Assigning Client

```
1. Manager logs in (Admin/Manager) → OTP verification
2. Navigates to "Create Employee"
3. Fills form: email, name, password → POST /users
4. Server verifies manager role
5. Server hashes password, creates user
6. Employee account created in users collection
7. Manager navigates to "Assign Client"
8. Selects employee + client → POST /clients/assign
9. Server updates clients.client_handler
10. Assignment complete
11. Employee can now see client on next login
```

### Example 3: Order Creation & Payment Tracking

```
1. Manager creates order: POST /orders
   - Sets total_amount: 5000
   - Sets payment_status: "pending"
2. Payment Phase 1 arrives: POST /payments
   - Phase: 1, Amount: 1500
   - Creates payment record
3. Order payment_status updates to: "partial"
4. Payment Phase 2 arrives: POST /payments
   - Phase: 2, Amount: 1500
5. Payment Phase 3 arrives: POST /payments
   - Phase: 3, Amount: 2000
6. Total payments now = 5000
7. Order payment_status updates to: "paid"
8. Order marked complete on dashboard
```

### Example 4: Column Permission Assignment

```
1. Admin wants to restrict employee dashboard access
2. Admin navigates to "Manage Permissions"
3. Selects employee + specific columns
4. Sends PUT /users/permissions with:
   {
     "email": "employee@company.com",
     "permissions": {
       "dashboard": ["status", "remarks"]  // Only these columns editable
     }
   }
5. Server updates users.permissions
6. Employee can still VIEW all columns
7. But can only EDIT "status" and "remarks"
8. Attempts to edit other columns return 403 Forbidden
```

---

## API Response Format

All endpoints follow a consistent response structure:

### Success Response (2xx)
```json
{
  "status_code": 200,
  "status": "success",
  "message": "Operation completed successfully",
  "data": { /* actual data */ }
}
```

### Error Response (4xx, 5xx)
```json
{
  "status_code": 400,
  "status": "error",
  "message": "Email already registered",
  "data": null
}
```

---

## Performance Optimization Strategies

### 1. Database Indexing
- Single-field indexes on frequently queried fields (`email`, `client_id`, `order_id`)
- Composite indexes for multi-field queries
- Regular index analysis and maintenance

### 2. Query Optimization
```python
# ❌ Inefficient: N+1 query problem
for client in clients:
  orders = orders_collection.find({"client_id": client["client_id"]})

# ✅ Efficient: Bulk query with filtering
all_orders = orders_collection.find({"client_id": {"$in": client_ids}})
```

### 3. Caching Strategy
- Cache user permissions at login (JWT claims)
- Cache frequently accessed clients (Redis recommended)
- Invalidate cache on updates

### 4. Pagination
```python
# For large result sets
GET /orders?page=1&limit=50
```

### 5. Response Compression
```python
# GZipMiddleware automatically compresses responses > 1KB
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

---

## Monitoring & Maintenance

### Health Check Endpoint (Recommended Addition)
```python
@app.get("/health")
def health_check():
  """Check API and database connectivity"""
  return {
    "status": "healthy",
    "database": "connected",
    "timestamp": datetime.utcnow()
  }
```

### Logging (Recommended Addition)
```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info(f"User {email} logged in successfully")
logger.warning(f"Failed login attempt for {email}")
logger.error(f"Database connection failed: {error}")
```

### Metrics to Monitor
- Request response times
- Database query duration
- Error rates by endpoint
- JWT token generation rate
- OTP delivery success rate

---

## Troubleshooting

### Issue: Login fails with "Could not validate credentials"
**Cause**: JWT token expired or invalid secret key
**Solution**: 
- Check `ACCESS_TOKEN_EXPIRE_MINUTES` setting
- Verify `SECRET_KEY` consistency
- Clear browser cache/localStorage

### Issue: OTP email not received
**Cause**: SMTP configuration incorrect or email service issue
**Solution**:
- Verify SMTP credentials in .env
- Check email spam folder
- Test SMTP connection separately
- Verify EMAIL_FROM is correct

### Issue: MongoDB connection timeout
**Cause**: Invalid MONGO_URI or network issues
**Solution**:
- Verify MONGO_URI format
- Check MongoDB Atlas IP whitelist
- Ensure network connectivity
- Test connectivity manually with `mongosh`

### Issue: CORS error when accessing from frontend
**Cause**: Frontend origin not in ALLOWED_ORIGINS
**Solution**:
- Add frontend URL to ALLOWED_ORIGINS in .env
- Verify exact protocol (http/https)
- Check for trailing slashes

---

## Summary

The **Email Dashboard API** is a production-ready backend system with:

✅ **Secure Authentication**: JWT + OTP 2FA for privileged users
✅ **Granular Authorization**: 3-tier RBAC with column-level permissions
✅ **Comprehensive Data Model**: 7 MongoDB collections with referential integrity
✅ **RESTful API**: 20+ endpoints with consistent response format
✅ **Error Handling**: Global exception handlers with generic error messages
✅ **Performance**: Indexed queries, compressed responses, denormalized data
✅ **Scalability**: Stateless design, database-backed sessions, cloud-ready
✅ **Documentation**: Complete API docs, database schema, RBAC rules

**Next Steps for Enhancement**:
1. Add rate limiting on login/OTP endpoints
2. Implement request logging and audit trail
3. Add health check and metrics endpoints
4. Set up automated backups for MongoDB
5. Implement API versioning for future changes
6. Add comprehensive integration tests
7. Set up CI/CD pipeline for automated deployments

---

*This document was generated as a comprehensive guide to the Email Dashboard API architecture and implementation.*

**Last Updated**: April 15, 2026
**Version**: 1.0.0
**Author**: Architecture Documentation Team
