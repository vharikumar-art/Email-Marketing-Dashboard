# 📋 Email Dashboard — Feature Roadmap

Track upcoming features here. Check off each one as it gets implemented.

---

## 🔴 Production Must-Haves

- [ ] **Pagination** — Add `limit` & `offset` to `/clients`, `/orders`, `/dashboard/orders`
- [ ] **Rate Limiting** — Protect `/login` against brute-force attacks (`slowapi`)
- [ ] **Logout + Token Invalidation** — Blacklist tokens on logout
- [ ] **MongoDB Indexes** — Add indexes on `client_id`, `order_id`, `email`, `reference_id`
- [ ] **Structured Logging** — Replace all `print()` with Python `logging` module
- [ ] **Health Check Endpoint** — `/health` endpoint for monitoring tools
- [ ] **Security Response Headers** — Protect against XSS, clickjacking
- [ ] **Env Validation at Startup** — Fail fast if `SECRET_KEY`, `MONGO_URI` etc. are missing

---

## 📊 Analytics & Reporting

- [ ] **Revenue Reports** — Monthly/quarterly breakdown by employee, country, order type
- [ ] **Order Completion Rate** — Track Active → Completed conversion per period
- [ ] **Employee Performance Dashboard** — Most clients, highest revenue, fastest turnaround
- [ ] **Export to Excel/PDF** — Export filtered dashboard data for stakeholders

---

## 🔔 Notifications & Automation

- [ ] **Payment Due Reminders** — Auto-email when a balance is overdue
- [ ] **Order Deadline Alerts** — Notify when `writing_end_date` / `po_end_date` is approaching
- [ ] **New Order Notifications** — Notify employee when a client/order is assigned to them
- [ ] **Weekly Summary Emails** — Auto-digest of pending orders & payments sent to admins

---

## 👥 Client & Order Management

- [ ] **Client Activity Timeline** — Full history of all actions on a client account
- [ ] **Order Status Workflow** — Enforce stage progression: Draft → In Review → Active → Completed
- [ ] **Document Uploads** — Attach files (manuscripts, contracts) to orders
- [ ] **Client Notes / Comments** — Internal notes visible only to team members
- [ ] **Duplicate Client Detection** — Warn before creating a client with a similar name/email

---

## 💰 Payment Enhancements

- [ ] **Invoice Generator** — Auto-generate a PDF invoice per order based on phase data
- [ ] **Multi-Currency Summary** — Show total revenue in both INR and USD simultaneously
- [ ] **Partial Payment Progress Bar** — Visual indicator of how much of an order is paid
- [ ] **Refund Tracking** — Record refunds as negative payment entries

---

## 🔐 Security & Access Control

- [ ] **Audit Logs** — Record every create/update action with who did it and when
- [ ] **Field-Level Permissions** — Hide specific columns per employee (e.g., payment amounts)
- [ ] **Session Management** — View active sessions, force-logout from admin panel
- [ ] **IP Whitelisting** — Restrict login to specific office IP addresses

---

## 🤖 Smart / AI Features

- [ ] **Smart Client Search** — Full-text fuzzy search across name, email, country, order type
- [ ] **Revenue Forecasting** — Predict next month's revenue from pending orders & history
- [ ] **Anomaly Detection** — Flag unusual payment amounts or sudden drops in order activity

---

## ✅ Completed Features

- [x] Dynamic Order Type from orders table (aggregation pipeline)
- [x] 4-digit padded Client ID and Reference ID auto-generation (`CL-2024-0001`)
- [x] ID Range management per employee with overlap validation
- [x] Payment History collection (`payment_history`)
- [x] Pending Payment Summary endpoint
- [x] Currency conversion (INR ↔ USD) with live exchange rate
- [x] OTP-based login for Admin and Manager roles
- [x] Role-based access control (Admin / Manager / Employee)
- [x] Unified Create API (client + order + manuscript + payment in one request)
- [x] Personal email and personal phone number fields on User accounts
