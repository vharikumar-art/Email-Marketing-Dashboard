# API Documentation - Email Dashboard

## Base URL
- **Production**: `https://marketing-dashboard-api.render.com` (Example)
- **Local**: `http://localhost:8000`

## Authentication
Most endpoints require a Bearer Token in the `Authorization` header.
```
Authorization: Bearer <your_jwt_token>
```

---

## ID Reference Guide

| Entity | ID Type | Example | Notes |
| :--- | :--- | :--- | :--- |
| Order (MongoDB) | Hex String | `65f1a2b3c4d5e6f7a8b9c0d1` | Use as `order_db_id` in paths |
| Client | Custom | `CLT001` | Auto-generated, text format |
| Order | Custom | `ORD-2026-001` | Auto-generated with year |
| Reference | Custom | `REF-2026-001` | Unique per order |
| Manuscript | Custom | `MS-CLT001-1` | ClientID-based |

---

---

# 1. AUTHENTICATION ENDPOINTS

## 1.1 Login
**Endpoint:** `POST /login`

**Purpose:** Authenticate user and receive OTP prompt (if Admin/Manager) or JWT token (if Employee)

**Request:**
```json
{
  "email": "user@example.com",
  "password": "yourpassword"
}
```

**Curl Example:**
```bash
curl -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "Admin@123"
  }'
```

**Success Response (Employee):**
```json
{
  "status_code": 200,
  "status": "success",
  "message": "Login successful",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "user": {
      "email": "emp@example.com",
      "role": "employee",
      "full_name": "John Doe"
    }
  }
}
```

**Success Response (Admin/Manager - OTP Required):**
```json
{
  "status_code": 200,
  "status": "success",
  "message": "OTP sent to your email",
  "data": {
    "otp_required": true,
    "email": "admin@example.com"
  }
}
```

**Postman Steps:**
1. Method: `POST`
2. URL: `http://localhost:8000/login`
3. Body → raw → JSON → paste request above
4. Click Send

---

## 1.2 Verify OTP
**Endpoint:** `POST /verify-otp`

**Purpose:** Verify OTP for Admin/Manager login

**Request:**
```json
{
  "email": "admin@example.com",
  "otp": "123456"
}
```

**Curl Example:**
```bash
curl -X POST http://localhost:8000/verify-otp \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "otp": "123456"
  }'
```

**Response:**
```json
{
  "status_code": 200,
  "status": "success",
  "message": "OTP verified successfully",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer"
  }
}
```

---

# 2. USER MANAGEMENT

## 2.1 Create User (with Optional Photo)
**Endpoint:** `POST /users`

**Purpose:** Create new user (Admin, Manager, or Employee)

**Auth Required:** Manager or Admin

**Step 1: Create User (JSON)**
```bash
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "email": "newuser@example.com",
    "full_name": "Jane Smith",
    "password": "SecurePass123",
    "phone_number": "+1-555-0123",
    "personal_email": "jane.personal@email.com",
    "personal_number": "+1-555-9876",
    "role": "employee",
    "profile_names": ["Profile A", "Profile B"],
    "branch": "New York",
    "permissions": {
      "dashboard": ["view", "edit"]
    }
  }'
```

**Response:**
```json
{
  "status_code": 201,
  "status": "success",
  "message": "User created successfully",
  "data": {
    "_id": "65f1a2b3c4d5e6f7a8b9c0d1",
    "email": "newuser@example.com",
    "full_name": "Jane Smith",
    "role": "employee",
    "password": "SecurePass123"
  }
}
```

**Postman Steps (Create User):**
1. Method: `POST`
2. URL: `http://localhost:8000/users`
3. Headers:
   - `Authorization: Bearer YOUR_TOKEN`
   - `Content-Type: application/json`
4. Body → raw → JSON → paste request above
5. Click Send

---

## 2.2 Upload User Photo
**Endpoint:** `POST /users/{email}/photo`

**Purpose:** Upload or update user profile photo (500 KB max)

**Auth Required:** Current user (self) or Admin/Manager

**Step 2: Upload Photo (multipart/form-data)**

**Curl Example:**
```bash
curl -X POST http://localhost:8000/users/newuser@example.com/photo \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@/path/to/user_photo.jpg"
```

**Response:**
```json
{
  "status": "success",
  "message": "Photo updated for newuser@example.com",
  "photo_url": "static/uploads/users/a1b2c3d4e5f6.jpg"
}
```

**Postman Steps (Upload Photo):**
1. Create new request
2. Method: `POST`
3. URL: `http://localhost:8000/users/newuser@example.com/photo`
4. Headers:
   - `Authorization: Bearer YOUR_TOKEN`
   - ⚠️ DO NOT set Content-Type (Postman auto-sets multipart/form-data)
5. Body → form-data:
   - Key: `file` (type: File)
   - Value: Select your image file
6. Click Send

---

## 2.3 Get User Photo
**Endpoint:** `GET /users/{email}/photo`

**Purpose:** Retrieve user profile photo

**Auth Required:** No

**Curl Example:**
```bash
curl http://localhost:8000/users/newuser@example.com/photo -o user_photo.jpg
```

---

## 2.4 Get Current User Details
**Endpoint:** `GET /users/me/details`

**Purpose:** Get full profile, dashboard stats, country breakdown, and order status details

**Auth Required:** Yes

**Curl Example:**
```bash
curl -X GET http://localhost:8000/users/me/details \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "status_code": 200,
  "status": "success",
  "message": "User details fetched successfully",
  "data": {
    "email": "emp@example.com",
    "full_name": "John Doe",
    "role": "employee",
    "has_photo": true,
    "photo_url": "static/uploads/users/a1b2c3d4e5f6.jpg",
    "photo_mime": "image/jpeg",
    "dashboard_stats": {
      "total_amount": 15000.50,
      "paid_amount": 10000.00,
      "remaining_amount": 5000.50,
      "total_clients": 25,
      "pending_count": 8
    },
    "country_based_details": [
      {
        "country_name": "USA",
        "client_count": 10,
        "paid_amount": 8000.00
      }
    ]
  }
}
```

> **Displaying the photo:**
> ```html
> <img src="http://localhost:8000/{photo_url}" alt="User Photo" />
> ```

---

## 2.5 Get All Users
**Endpoint:** `GET /users`

**Purpose:** List all users

**Auth Required:** Admin or Manager

**Curl Example:**
```bash
curl -X GET http://localhost:8000/users \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

# 3. CLIENT MANAGEMENT

## 3.1 Create Client (with Optional Photo)
**Endpoint:** `POST /clients`

**Purpose:** Create new client

**Auth Required:** Yes

**Step 1: Create Client (JSON)**
```bash
curl -X POST http://localhost:8000/clients \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "name": "Acme Corporation",
    "country": "USA",
    "email": "contact@acme.com",
    "whatsapp_no": "+1-555-0123",
    "client_ref_no": "CLIENT123",
    "client_link": "https://acme.com",
    "bank_account": "1234567890",
    "affiliation": "Academic",
    "payment_drive_link": "https://drive.google.com/...",
    "client_drive_link": "https://drive.google.com/...",
    "photo_base64": "data:image/jpeg;base64,/9j/4AAQSkZ...",
    "photo_mime": "image/jpeg"
  }'
```

> **Note:** `photo_base64` in the create body is still accepted as a **base64-encoded string**. The server decodes it and saves it to disk, storing the resulting `photo_path` in MongoDB. The response does not echo the base64 back; instead use `GET /clients/{client_id}` to get the `photo_url`.
```

**Response:**
```json
{
  "status_code": 201,
  "status": "success",
  "message": "Client created successfully",
  "data": {
    "_id": "65f1a2b3c4d5e6f7a8b9c0d2",
    "client_id": "CLT001",
    "name": "Acme Corporation",
    "country": "USA",
    "email": "contact@acme.com"
  }
}
```

---

## 3.2 Upload Client Photo
**Endpoint:** `POST /clients/{client_id}/photo`

**Purpose:** Upload client logo/profile photo (500 KB max)

**Auth Required:** Admin or Manager

**Curl Example:**
```bash
curl -X POST http://localhost:8000/clients/CLT001/photo \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@/path/to/client_logo.jpg"
```

**Postman Steps:**
1. Method: `POST`
2. URL: `http://localhost:8000/clients/CLT001/photo`
3. Headers: `Authorization: Bearer YOUR_TOKEN`
4. Body → form-data:
   - Key: `file` (type: File)
   - Value: Select client logo/photo
5. Click Send

---

## 3.3 Get Client Photo
**Endpoint:** `GET /clients/{client_id}/photo`

**Purpose:** Retrieve client profile photo

**Auth Required:** No

**Curl Example:**
```bash
curl http://localhost:8000/clients/CLT001/photo -o client_logo.jpg
```

---

## 3.4 Get All Clients
**Endpoint:** `GET /clients`

**Purpose:** List clients (Admin/Manager see all, Employee sees assigned clients)

**Auth Required:** Yes

**Curl Example:**
```bash
curl -X GET http://localhost:8000/clients \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 3.5 Get Client Details with Orders
**Endpoint:** `GET /clients/{client_id}`

**Purpose:** Get full client profile including all orders with receipts

**Auth Required:** Admin or Manager

**Curl Example:**
```bash
curl -X GET http://localhost:8000/clients/CLT001 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "status_code": 200,
  "status": "success",
  "message": "Client fetched successfully",
  "data": {
    "client_id": "CLT001",
    "name": "Acme Corporation",
    "country": "USA",
    "email": "contact@acme.com",
    "has_photo": true,
    "photo_url": "static/uploads/clients/b1c2d3e4f5a6.jpg",
    "photo_mime": "image/jpeg",
    "orders": [
      {
        "order_id": "ORD-2026-001",
        "reference_id": "REF-2026-001",
        "title": "Research Paper",
        "total_amount": 5000.00,
        "paid_amount": 2500.00,
        "phase_1_payment": 2500.00,
        "phase_1_payment_date": "2026-01-15T10:30:00",
        "phase_1_payment_details": "Phase 1 complete",
        "receipt_phase_1_url": "static/uploads/receipts/c1d2e3f4a5b6.jpg",
        "receipt_phase_1_mime": "image/jpeg",
        "receipt_phase_2_url": null,
        "receipt_phase_2_mime": null,
        "receipt_phase_3_url": null,
        "receipt_phase_3_mime": null
      }
    ]
  }
}
```

> **Displaying photos and receipts:**
> ```html
> <!-- Client photo -->
> <img src="http://localhost:8000/{photo_url}" alt="Client" />
>
> <!-- Receipt screenshot -->
> <img src="http://localhost:8000/{receipt_phase_1_url}" alt="Receipt Phase 1" />
> ```

---

## 3.6 Assign Client to Employee
**Endpoint:** `POST /clients/assign`

**Purpose:** Assign a client to an employee

**Auth Required:** Admin or Manager

**Request:**
```json
{
  "client_id": "CLT001",
  "employee_email": "emp@example.com"
}
```

**Curl Example:**
```bash
curl -X POST http://localhost:8000/clients/assign \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "client_id": "CLT001",
    "employee_email": "emp@example.com"
  }'
```

---

# 4. ORDER MANAGEMENT

## 4.1 Create Order
**Endpoint:** `POST /orders`

**Purpose:** Create new order for a client

**Auth Required:** Admin or Manager

**Request:**
```json
{
  "order_id": "ORD-2026-001",
  "reference_id": "REF-2026-001",
  "client_id": "CLT001",
  "title": "Research Paper on AI",
  "journal_name": "IEEE Transactions",
  "order_type": "WO / PO",
  "currency": "USD",
  "total_amount": 5000.00,
  "writing_amount": 3000.00,
  "modification_amount": 1500.00,
  "implementation_amount": 500.00,
  "writing_start_date": "2026-01-01",
  "writing_end_date": "2026-02-01",
  "payment_status": "Pending",
  "is_new_order": "yes"
}
```

**Curl Example:**
```bash
curl -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "order_id": "ORD-2026-001",
    "reference_id": "REF-2026-001",
    "client_id": "CLT001",
    "title": "Research Paper on AI",
    "journal_name": "IEEE Transactions",
    "currency": "USD",
    "total_amount": 5000.00,
    "payment_status": "Pending"
  }'
```

---

## 4.2 Get All Orders
**Endpoint:** `GET /orders`

**Purpose:** List orders (filtered by role)

**Auth Required:** Yes

**Curl Example:**
```bash
curl -X GET http://localhost:8000/orders \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

# 5. RECEIPT SCREENSHOT MANAGEMENT ✨

## 5.1 Upload Receipt Screenshot
**Endpoint:** `POST /orders/{order_db_id}/receipt/{phase}`

**Purpose:** Upload payment receipt screenshot for order phase (1, 2, or 3)

**Auth Required:** Admin or Manager

**Parameters:**
- `order_db_id`: MongoDB object ID (hex string from `order_db_id` in dashboard)
- `phase`: `1`, `2`, or `3` (payment phase)
- Max file size: **2 MB**
- Accepted formats: **JPEG, PNG, GIF, WebP**

**Curl Example:**
```bash
curl -X POST http://localhost:8000/orders/65f1a2b3c4d5e6f7a8b9c0d1/receipt/1 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@/path/to/receipt_phase1.jpg"
```

**Response:**
```json
{
  "status": "success",
  "message": "Receipt screenshot for phase 1 uploaded successfully",
  "receipt_url": "static/uploads/receipts/c1d2e3f4a5b6.jpg"
}
```

**Postman Steps:**
1. Method: `POST`
2. URL: `http://localhost:8000/orders/{order_db_id}/receipt/1`
   - Replace `{order_db_id}` with actual MongoDB ID from dashboard
   - Replace `1` with `2` or `3` for other phases
3. Headers:
   - `Authorization: Bearer YOUR_TOKEN`
   - ⚠️ DO NOT set Content-Type manually
4. Body → form-data:
   - Key: `file` (type: File)
   - Value: Select receipt image (JPEG/PNG, max 2MB)
5. Click Send

**How to get order_db_id:**
1. Call `GET /dashboard/orders`
2. Find the order row you want
3. Copy the `order_db_id` value (hex string like `65f1a2b3c4d5e6f7a8b9c0d1`)

---

## 5.2 View Receipt Screenshot
**Endpoint:** `GET /orders/{order_db_id}/receipt/{phase}`

**Purpose:** Download/view receipt screenshot for specific phase

**Auth Required:** No (Public)

**Parameters:**
- `order_db_id`: MongoDB object ID
- `phase`: `1`, `2`, or `3`

**Curl Example:**
```bash
# Download receipt as file
curl http://localhost:8000/orders/65f1a2b3c4d5e6f7a8b9c0d1/receipt/1 \
  -o receipt_phase1.jpg
```

**Postman Steps:**
1. Method: `GET`
2. URL: `http://localhost:8000/orders/{order_db_id}/receipt/1`
3. No headers required
4. Click Send
5. Response will show image preview (or binary download)

---

## 5.3 Delete Receipt Screenshot
**Endpoint:** `DELETE /orders/{order_db_id}/receipt/{phase}`

**Purpose:** Delete receipt screenshot from specific phase

**Auth Required:** Admin or Manager

**Curl Example:**
```bash
curl -X DELETE http://localhost:8000/orders/65f1a2b3c4d5e6f7a8b9c0d1/receipt/1 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "status": "success",
  "message": "Receipt screenshot for phase 1 deleted successfully"
}
```

**Postman Steps:**
1. Method: `DELETE`
2. URL: `http://localhost:8000/orders/{order_db_id}/receipt/1`
3. Headers:
   - `Authorization: Bearer YOUR_TOKEN`
4. Click Send

---

## 5.4 View Receipts in Dashboard
**Endpoint:** `GET /dashboard/orders`

**Purpose:** Get all orders with receipt URLs automatically injected for each phase

**Auth Required:** Yes

**Curl Example:**
```bash
curl -X GET http://localhost:8000/dashboard/orders \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response (excerpt showing receipt fields):**
```json
{
  "status_code": 200,
  "status": "success",
  "message": "Dashboard data fetched successfully",
  "data": [
    {
      "order_db_id": "65f1a2b3c4d5e6f7a8b9c0d1",
      "order_id": "ORD-2026-001",
      "title": "Research Paper",
      "total_amount": 5000.00,
      "paid_amount": 2500.00,
      "phase_1_payment": 2500.00,
      "phase_1_payment_date": "2026-01-15T10:30:00",
      "receipt_phase_1_url": "static/uploads/receipts/c1d2e3f4a5b6.jpg",
      "receipt_phase_1_mime": "image/jpeg",
      "receipt_phase_2_url": null,
      "receipt_phase_2_mime": null,
      "receipt_phase_3_url": null,
      "receipt_phase_3_mime": null,
      "client_photo_url": "static/uploads/clients/b1c2d3e4f5a6.jpg",
      "client_photo_mime": "image/jpeg"
    }
  ]
}
```

**Front-End Usage:**
All image fields are now **relative URL paths**. Prepend the API base URL:
```html
<!-- Client photo -->
<img src="http://localhost:8000/{client_photo_url}" alt="Client" />

<!-- Receipt screenshot -->
<img src="http://localhost:8000/{receipt_phase_1_url}" alt="Receipt Phase 1" />
```

> **Alternative:** Use the static file endpoint directly:
> ```
> GET http://localhost:8000/static/uploads/receipts/c1d2e3f4a5b6.jpg
> ```

---

# 6. PAYMENT MANAGEMENT

## 6.1 Create Payment
**Endpoint:** `POST /payments`

**Purpose:** Create payment record for order

**Auth Required:** Admin or Manager

**Request:**
```json
{
  "client_id": "CLT001",
  "order_id": "ORD-2026-001",
  "payment_date": "2026-01-15",
  "paid_amount": 2500.00,
  "phase_1_payment": 2500.00,
  "phase_1_payment_date": "2026-01-15",
  "phase_1_payment_details": "Payment received via bank transfer"
}
```

**Curl Example:**
```bash
curl -X POST http://localhost:8000/payments \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "client_id": "CLT001",
    "order_id": "ORD-2026-001",
    "paid_amount": 2500.00,
    "phase_1_payment": 2500.00,
    "phase_1_payment_date": "2026-01-15",
    "phase_1_payment_details": "Bank transfer received"
  }'
```

---

## 6.2 Get All Payments
**Endpoint:** `GET /payments`

**Purpose:** List payment records

**Auth Required:** Yes

**Curl Example:**
```bash
curl -X GET http://localhost:8000/payments \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 6.3 Get Payment History
**Endpoint:** `GET /payments/history`

**Purpose:** Detailed payment history with filters

**Auth Required:** Yes

**Query Parameters:**
- `client_id` (optional): Filter by client
- `order_id` (optional): Filter by order

**Curl Example:**
```bash
curl -X GET "http://localhost:8000/payments/history?client_id=CLT001" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

# 7. DASHBOARD & UNIFIED UPDATES

## 7.1 Get Dashboard Orders
**Endpoint:** `GET /dashboard/orders`

**Purpose:** Unified view of all orders with clients, payments, and receipts

**Auth Required:** Yes

**Curl Example:**
```bash
curl -X GET http://localhost:8000/dashboard/orders \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 7.2 Update Dashboard Order
**Endpoint:** `PATCH /dashboard/orders/{order_db_id}`

**Purpose:** Update client, order, or payment data in unified way

**Auth Required:** Yes

**Request (example updating order details):**
```json
{
  "title": "Updated Paper Title",
  "journal_name": "Nature",
  "total_amount": 6000.00,
  "writing_amount": 3500.00,
  "payment_status": "Partial Paid",
  "order_status": "In Progress"
}
```

**Curl Example:**
```bash
curl -X PATCH http://localhost:8000/dashboard/orders/65f1a2b3c4d5e6f7a8b9c0d1 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "title": "Updated Paper Title",
    "total_amount": 6000.00,
    "payment_status": "Partial Paid"
  }'
```

**Response:**
```json
{
  "status_code": 200,
  "status": "success",
  "message": "Dashboard order updated successfully",
  "data": null
}
```

---

## 7.3 Unified Create (Client + Order + Manuscript + Payment)
**Endpoint:** `POST /unified/create`

**Purpose:** Create all related records in one request

**Auth Required:** Admin or Manager

**Request:**
```json
{
  "client_id": "CLT002",
  "client_name": "Beta Research Inc",
  "client_country": "Canada",
  "client_email": "contact@betaresearch.com",
  "client_whatsapp_no": "+1-555-9876",
  "reference_id": "REF-2026-002",
  "title": "Machine Learning Study",
  "journal_name": "ACM Computing Surveys",
  "order_type": "WO / PO",
  "currency": "USD",
  "total_amount": 8000.00,
  "writing_amount": 5000.00,
  "modification_amount": 2000.00,
  "payment_status": "Pending",
  "receive_bank_account": "1234567890",
  "create_manuscript": true,
  "manuscript_title": "ML Research Dataset",
  "create_payment": true,
  "payment_amount": 4000.00,
  "phase_1_payment": 4000.00,
  "phase_1_payment_date": "2026-01-20",
  "phase_1_payment_details": "Initial payment received"
}
```

**Curl Example:**
```bash
curl -X POST http://localhost:8000/unified/create \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "client_name": "Beta Research Inc",
    "client_country": "Canada",
    "client_email": "contact@betaresearch.com",
    "client_photo_base64": "data:image/jpeg;base64,/9j/4AAQSkZ...",
    "client_photo_mime": "image/jpeg",
```

> **Note:** `client_photo_base64` is still accepted as a base64 string in the request body. The server decodes it, saves the file to disk, and stores the path in MongoDB. To display the photo after creation, use the returned `photo_url` from `GET /clients/{client_id}` or `GET /dashboard/orders`.
    "reference_id": "REF-2026-002",
    "title": "Machine Learning Study",
    "total_amount": 8000.00,
    "currency": "USD"
  }'
```

---

# 8. BANK ACCOUNTS

## 8.1 Get All Bank Accounts
**Endpoint:** `GET /bank-accounts`

**Purpose:** Fetch all bank accounts for the frontend dropdown options.

**Auth Required:** Yes (Any role)

## 8.2 Create Bank Account
**Endpoint:** `POST /bank-accounts`

**Purpose:** Create a new bank account number.

**Auth Required:** Admin or Manager

**Request:**
```json
{
  "account_number": "1234567890"
}
```

## 8.3 Update Bank Account
**Endpoint:** `PUT /bank-accounts/{account_id}`

**Purpose:** Update an existing bank account number.

**Auth Required:** Admin or Manager

**Request:**
```json
{
  "account_number": "0987654321"
}
```

## 8.4 Delete Bank Account
**Endpoint:** `DELETE /bank-accounts/{account_id}`

**Purpose:** Delete a bank account number.

**Auth Required:** Admin or Manager

---

# 9. POSTMAN COLLECTION QUICK START

## Import Postman Environment Variables

**Set these variables in Postman:**
```
{{base_url}} = http://localhost:8000
{{auth_token}} = YOUR_JWT_TOKEN_FROM_LOGIN
{{order_db_id}} = 65f1a2b3c4d5e6f7a8b9c0d1
{{client_id}} = CLT001
```

## Basic Workflow in Postman

1. **Login** → `POST {{base_url}}/login`
   - Copy `access_token` from response
   - Set `{{auth_token}}` to this value

2. **Create Client** → `POST {{base_url}}/clients`
   - Headers: `Authorization: Bearer {{auth_token}}`
   - Body: Client JSON
   - Copy `client_id` from response

3. **Upload Client Photo** → `POST {{base_url}}/clients/{{client_id}}/photo`
   - Headers: `Authorization: Bearer {{auth_token}}`
   - Body: form-data with `file`

4. **Create Order** → `POST {{base_url}}/orders`
   - Headers: `Authorization: Bearer {{auth_token}}`
   - Body: Order JSON
   - Copy `_id` as `{{order_db_id}}`

5. **Upload Receipt** → `POST {{base_url}}/orders/{{order_db_id}}/receipt/1`
   - Headers: `Authorization: Bearer {{auth_token}}`
   - Body: form-data with `file`

6. **View Dashboard** → `GET {{base_url}}/dashboard/orders`
   - Headers: `Authorization: Bearer {{auth_token}}`
   - Receipt and photo URLs are included as relative path strings
   - Display with: `<img src="{{base_url}}/{receipt_phase_1_url}" />`

7. **Access Static Image Directly** → `GET {{base_url}}/static/uploads/receipts/{filename}`
   - No auth required
   - Returns the raw image file

---

# 10. COMMON ERRORS & SOLUTIONS

| Error | Cause | Solution |
| :--- | :--- | :--- |
| `401 Unauthorized` | Invalid/missing token | Login again, copy token to Authorization header |
| `403 Forbidden` | Insufficient permissions | Use Admin/Manager account for restricted endpoints |
| `404 Not Found` | Invalid ID or endpoint | Verify correct ID format and endpoint path |
| `404 Not Found` on image URL | File deleted from server disk | Re-upload the image via the photo/receipt endpoint |
| `400 Bad Request - Image size` | File > 500KB (user/client) or 2MB (receipt) | Compress image or use smaller file |
| `400 Bad Request - File must be image` | Wrong file type (not JPEG/PNG) | Upload valid image format |
| `413 Payload Too Large` | Request body too large | Split large requests into smaller ones |

---

# 11. RATE LIMITS & BEST PRACTICES

- **No strict rate limiting** but avoid >100 requests/sec
- **Batch operations** when possible (use `/dashboard/orders` instead of individual queries)
- **Cache image URLs** client-side (photos, receipts don't change frequently; URLs are stable)
- **Use `<img src>` with URL**, not inline base64 — browsers cache static files efficiently
- **Use pagination** for large result sets (future enhancement)
- **Always validate file size** before uploading

---

# 12. STATIC FILE SERVING

Images are stored on the server filesystem and served via FastAPI's `StaticFiles` mount.

**Base static URL:** `GET /static/uploads/{subfolder}/{filename}`

| Subfolder | Content | Example URL |
| :--- | :--- | :--- |
| `users/` | User profile photos | `/static/uploads/users/a1b2c3.jpg` |
| `clients/` | Client photos | `/static/uploads/clients/b2c3d4.jpg` |
| `receipts/` | Payment receipt screenshots | `/static/uploads/receipts/c3d4e5.jpg` |

**Auth Required:** No (publicly accessible)

**Example:**
```bash
curl http://localhost:8000/static/uploads/clients/b2c3d4.jpg -o client.jpg
```

> **Important for deployment:** The `static/uploads/` directory must exist on a **persistent volume**. If you deploy to a stateless platform (Heroku, Vercel serverless), uploaded files will be lost on restart. Use a persistent disk (Render Disk, Docker volume, or AWS S3) for production.

---

# 13. MIGRATION NOTE

If upgrading from a version that stored photos as MongoDB binary blobs, run the one-time migration script:

```bash
# From the project root
python migrate_images.py
```

This script:
- Extracts all `photo_data` binary blobs from `users` and `clients` collections
- Extracts all `receipt_phase_N_data` blobs from `orders` collection
- Saves them as files to `static/uploads/{users|clients|receipts}/`
- Updates MongoDB documents with the new `photo_path` / `receipt_phase_N_path` fields
- Removes the old binary fields

After migration, restart the server. All existing images will be available at their new URLs.

---

# 14. TESTING CHECKLIST

- [ ] Login and get auth token
- [ ] Create a test user, then upload photo → verify `photo_url` in response
- [ ] Create a test client with `photo_base64` in body → verify photo is saved to disk
- [ ] Upload client photo via `POST /clients/{id}/photo` → verify `photo_url` in response
- [ ] Create a test order
- [ ] Upload receipt screenshot for phase 1 → verify `receipt_url` in response
- [ ] View receipt via `GET /orders/{id}/receipt/1` → verify image is served
- [ ] Access static file directly: `GET /static/uploads/receipts/{filename}`
- [ ] View dashboard → check `receipt_phase_1_url` and `client_photo_url` fields
- [ ] View client details → check `photo_url` and `receipt_phase_N_url` in orders
- [ ] Delete receipt screenshot → verify file removed from disk
- [ ] Update order via PATCH endpoint
