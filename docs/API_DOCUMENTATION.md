# API Documentation - Email Dashboard

## Base URL
- **Production**: `https://marketing-dashboard-api.render.com` (Example)
- **Local**: `http://localhost:8000`

## Authentication
Most endpoints require a Bearer Token in the `Authorization` header.
`Authorization: Bearer <your_jwt_token>`

---

## 1. Authentication Endpoints

### Login
- **URL**: `/login`
- **Method**: `POST`
- **Body**:
  ```json
  {
    "email": "user@example.com",
    "password": "yourpassword"
  }
  ```
- **Description**: Authenticates user. Admins and Managers will receive `otp_required: true`. Employees receive `access_token` directly.

### Verify OTP
- **URL**: `/verify-otp`
- **Method**: `POST`
- **Body**:
  ```json
  {
    "email": "admin@example.com",
    "otp": "123456"
  }
  ```
- **Description**: Verifies OTP for privileged roles and returns a JWT.

---

## 2. Shared / Unified Operations

### Unified Creation
- **URL**: `/unified/create`
- **Method**: `POST`
- **Description**: Creates a Client, Order, optional Manuscript, and optional Payment in a single transaction.
- **Roles**: Admin, Manager.

---

## 3. User Management

### Get Current User Details
- **URL**: `/users/me/details`
- **Method**: `GET`
- **Description**: Returns full profile, dashboard stats, and handled clients.
- **Roles**: All.

### Create User
- **URL**: `/users`
- **Method**: `POST`
- **Roles**: Admin, Manager (Manager can only create Employees).

---

## 4. Operational Endpoints

### Clients
| Entity | ID Type | Example |
| :--- | :--- | :--- |
| Order | MongoDB `_id` (Hex) | `65f...456` (Unique, passed as `order_db_id`) |
| Client | `CLT` + 3 digits | `CLT001` |
| Order | `ORD` + 3 digits | `ORD001` |
| Manuscript | `MS-` + ClientID + Seq | `MS-CLT001-1` |
| Reference | `EM-` + Year + Seq | `EM-2024-001` |

- `GET /clients`: Fetch all clients (Admin/Manager) or assigned clients (Employee).
- `POST /clients`: Create a new client.
- `POST /clients/assign`: Assign a client to an employee.

### Orders
- `GET /orders`: Fetch all orders (Admin/Manager) or assigned (Employee).
- `POST /orders`: Create a new order.

### Payments
- `GET /payments`: Fetch payment records.

---

## 5. Dashboard Data

### Update Dashboard Order
- **URL**: `/dashboard/orders/{order_db_id}`
- **Method**: `PATCH`
- **Description**: Updates client, order, or payment data in a unified way. 
- **Relational Integrity**: If `client_id` is updated, the change is automatically rippled to all related orders, manuscripts, and payments.
- **Shared Fields**: Fields like `Country` and `Email` are client-level; updating them for one row updates them for all rows of that client.
- **Roles**: All. All users can update all dashboard fields for clients they have access to.
