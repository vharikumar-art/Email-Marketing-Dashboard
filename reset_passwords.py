"""
Seed Script: Clear ALL data and insert clean demo data.
Users:   1 Admin, 1 Manager, 1 Employee
Clients: 5 clients (Client 1 has 3 orders, Client 2 has 2 orders, rest have 1 order each)
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
import sys
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app.database import (
    users_collection,
    tokens_collection,
    clients_collection,
    orders_collection,
    manuscripts_collection,
    payments_collection,
    otps_collection
)
from app.auth import encrypt_password

# ─────────────────────────────────────────────────────
# STEP 1: DELETE ALL EXISTING DATA
# ─────────────────────────────────────────────────────
print("🗑️  Deleting all existing data...")
users_collection.delete_many({})
tokens_collection.delete_many({})
clients_collection.delete_many({})
orders_collection.delete_many({})
manuscripts_collection.delete_many({})
payments_collection.delete_many({})
otps_collection.delete_many({})
print("✅  All collections cleared.\n")

# ─────────────────────────────────────────────────────
# STEP 2: INSERT USERS (Admin, Manager, Employee)
# ─────────────────────────────────────────────────────
print("👤 Creating users...")

users = [
    {
        "email": "admin@dashboard.com",
        "full_name": "Admin User",
        "profile_names": ["AdminProfile"],
        "role": "admin",
        "phone_number": "+91 9000000001",
        "permissions": {"dashboard": ["view", "edit", "delete"]},
        "branch": "HQ",
        "password": encrypt_password("Admin@123"),
    },
    {
        "email": "manager@dashboard.com",
        "full_name": "Manager User",
        "profile_names": ["ManagerProfile"],
        "role": "manager",
        "phone_number": "+91 9000000002",
        "permissions": {"dashboard": ["view", "edit"]},
        "branch": "Branch A",
        "password": encrypt_password("Manager@123"),
    },
    {
        "email": "employee@dashboard.com",
        "full_name": "John Employee",
        "profile_names": ["JohnProfile", "JohnAlt"],
        "role": "employee",
        "phone_number": "+91 9000000003",
        "permissions": {"dashboard": ["view"]},
        "branch": "Branch A",
        "password": encrypt_password("Employee@123"),
    },
]

users_collection.insert_many(users)
print(f"  ✅  {len(users)} users inserted.")
print("     admin@dashboard.com       → Admin@123")
print("     manager@dashboard.com     → Manager@123")
print("     employee@dashboard.com    → Employee@123\n")

# ─────────────────────────────────────────────────────
# STEP 3: INSERT 5 CLIENTS
# ─────────────────────────────────────────────────────
print("🏢 Creating clients...")

now = datetime.utcnow()

clients = [
    {
        "client_id": "CLT001",
        "name": "Dr. Ahmed Al-Farsi",
        "country": "UAE",
        "email": "ahmed.alfarsi@email.com",
        "whatsapp_no": "+971501234567",
        "client_ref_no": "REF-001",
        "client_link": "https://scholar.google.com/ahmed",
        "bank_account": "AE123456789012345678",
        "affiliation": "University of UAE",
        "clients_details": "Senior researcher focused on AI and ML topics.",
        "client_drive_link": "https://drive.google.com/clt001",
        "payment_drive_link": "https://drive.google.com/pay001",
        "total_orders": 3,
        "client_handler": "employee@dashboard.com",
        "created_at": now - timedelta(days=90),
    },
    {
        "client_id": "CLT002",
        "name": "Prof. Li Wei",
        "country": "China",
        "email": "li.wei@chinauniv.edu",
        "whatsapp_no": "+8613800138000",
        "client_ref_no": "REF-002",
        "client_link": "https://scholar.google.com/liwei",
        "bank_account": "CN987654321012345678",
        "affiliation": "Beijing Institute of Technology",
        "clients_details": "Specializes in material science and nanotechnology.",
        "client_drive_link": "https://drive.google.com/clt002",
        "payment_drive_link": "https://drive.google.com/pay002",
        "total_orders": 2,
        "client_handler": "employee@dashboard.com",
        "created_at": now - timedelta(days=60),
    },
    {
        "client_id": "CLT003",
        "name": "Dr. Priya Sharma",
        "country": "India",
        "email": "priya.sharma@iit.ac.in",
        "whatsapp_no": "+919876543210",
        "client_ref_no": "REF-003",
        "client_link": "https://scholar.google.com/priya",
        "bank_account": "IN456789012345678901",
        "affiliation": "IIT Bombay",
        "clients_details": "Biomedical engineering researcher.",
        "client_drive_link": "https://drive.google.com/clt003",
        "payment_drive_link": "https://drive.google.com/pay003",
        "total_orders": 1,
        "client_handler": "employee@dashboard.com",
        "created_at": now - timedelta(days=45),
    },
    {
        "client_id": "CLT004",
        "name": "Dr. Carlos Mendez",
        "country": "Mexico",
        "email": "carlos.mendez@unam.mx",
        "whatsapp_no": "+525512345678",
        "client_ref_no": "REF-004",
        "client_link": "https://scholar.google.com/carlos",
        "bank_account": "MX112233445566778899",
        "affiliation": "UNAM Mexico",
        "clients_details": "Environmental science and climate change studies.",
        "client_drive_link": "https://drive.google.com/clt004",
        "payment_drive_link": "https://drive.google.com/pay004",
        "total_orders": 1,
        "client_handler": "employee@dashboard.com",
        "created_at": now - timedelta(days=30),
    },
    {
        "client_id": "CLT005",
        "name": "Dr. Sarah Johnson",
        "country": "USA",
        "email": "sarah.johnson@mit.edu",
        "whatsapp_no": "+16175551234",
        "client_ref_no": "REF-005",
        "client_link": "https://scholar.google.com/sarah",
        "bank_account": "US998877665544332211",
        "affiliation": "MIT",
        "clients_details": "Quantum computing and cryptography research.",
        "client_drive_link": "https://drive.google.com/clt005",
        "payment_drive_link": "https://drive.google.com/pay005",
        "total_orders": 1,
        "client_handler": "employee@dashboard.com",
        "created_at": now - timedelta(days=15),
    },
]

clients_collection.insert_many(clients)
print(f"  ✅  {len(clients)} clients inserted.\n")

# ─────────────────────────────────────────────────────
# STEP 4: INSERT ORDERS
# CLT001 → 3 orders, CLT002 → 2 orders, rest → 1 each
# ─────────────────────────────────────────────────────
print("📦 Creating orders...")

orders = [
    # ── CLT001 (3 orders) ───────────────────────────
    {
        "order_id": "ORD001",
        "reference_id": "EM-2024-001",
        "profile_name": "JohnProfile",
        "client_ref_no": "REF-001",
        "s_no": 1,
        "order_date": now - timedelta(days=85),
        "client_id": "CLT001",
        "manuscript_id": None,
        "journal_name": "Nature Machine Intelligence",
        "title": "Deep Learning Approaches for Autonomous Vehicle Systems",
        "order_type": "writing",
        "index": "SCI",
        "rank": "Q1",
        "currency": "USD",
        "total_amount": 1500.00,
        "writing_amount": 1200.00,
        "modification_amount": 200.00,
        "po_amount": 100.00,
        "writing_start_date": now - timedelta(days=85),
        "writing_end_date": now - timedelta(days=65),
        "payment_status": "Paid",
        "remarks": "Completed successfully.",
        "created_at": now - timedelta(days=85),
        "updated_at": now - timedelta(days=65),
    },
    {
        "order_id": "ORD002",
        "reference_id": "EM-2024-002",
        "profile_name": "JohnProfile",
        "client_ref_no": "REF-001",
        "s_no": 2,
        "order_date": now - timedelta(days=70),
        "client_id": "CLT001",
        "manuscript_id": None,
        "journal_name": "IEEE Transactions on Neural Networks",
        "title": "Federated Learning with Differential Privacy",
        "order_type": "modification",
        "index": "SCI",
        "rank": "Q1",
        "currency": "USD",
        "total_amount": 800.00,
        "writing_amount": 0.00,
        "modification_amount": 700.00,
        "po_amount": 100.00,
        "modification_start_date": now - timedelta(days=70),
        "modification_end_date": now - timedelta(days=55),
        "payment_status": "Partial",
        "remarks": "Phase 2 payment pending.",
        "created_at": now - timedelta(days=70),
        "updated_at": now - timedelta(days=55),
    },
    {
        "order_id": "ORD003",
        "reference_id": "EM-2024-003",
        "profile_name": "JohnAlt",
        "client_ref_no": "REF-001",
        "s_no": 3,
        "order_date": now - timedelta(days=40),
        "client_id": "CLT001",
        "manuscript_id": None,
        "journal_name": "Artificial Intelligence Review",
        "title": "Reinforcement Learning for Robotic Process Automation",
        "order_type": "writing",
        "index": "Scopus",
        "rank": "Q2",
        "currency": "USD",
        "total_amount": 1100.00,
        "writing_amount": 950.00,
        "modification_amount": 100.00,
        "po_amount": 50.00,
        "writing_start_date": now - timedelta(days=40),
        "payment_status": "Pending",
        "remarks": "In progress.",
        "created_at": now - timedelta(days=40),
        "updated_at": now - timedelta(days=10),
    },
    # ── CLT002 (2 orders) ───────────────────────────
    {
        "order_id": "ORD004",
        "reference_id": "EM-2024-004",
        "profile_name": "JohnProfile",
        "client_ref_no": "REF-002",
        "s_no": 1,
        "order_date": now - timedelta(days=58),
        "client_id": "CLT002",
        "manuscript_id": None,
        "journal_name": "Advanced Materials",
        "title": "Graphene-Based Nanocomposites for Energy Storage",
        "order_type": "writing",
        "index": "SCI",
        "rank": "Q1",
        "currency": "USD",
        "total_amount": 2000.00,
        "writing_amount": 1800.00,
        "modification_amount": 200.00,
        "po_amount": 0.00,
        "writing_start_date": now - timedelta(days=58),
        "writing_end_date": now - timedelta(days=30),
        "payment_status": "Paid",
        "remarks": "Published successfully.",
        "created_at": now - timedelta(days=58),
        "updated_at": now - timedelta(days=30),
    },
    {
        "order_id": "ORD005",
        "reference_id": "EM-2024-005",
        "profile_name": "JohnProfile",
        "client_ref_no": "REF-002",
        "s_no": 2,
        "order_date": now - timedelta(days=25),
        "client_id": "CLT002",
        "manuscript_id": None,
        "journal_name": "Journal of Materials Science",
        "title": "Thermal Conductivity Enhancement in Polymer Nanocomposites",
        "order_type": "modification",
        "index": "Scopus",
        "rank": "Q2",
        "currency": "USD",
        "total_amount": 600.00,
        "writing_amount": 0.00,
        "modification_amount": 600.00,
        "po_amount": 0.00,
        "modification_start_date": now - timedelta(days=25),
        "payment_status": "Pending",
        "remarks": "Revision requested by journal.",
        "created_at": now - timedelta(days=25),
        "updated_at": now - timedelta(days=5),
    },
    # ── CLT003 (1 order) ────────────────────────────
    {
        "order_id": "ORD006",
        "reference_id": "EM-2024-006",
        "profile_name": "JohnProfile",
        "client_ref_no": "REF-003",
        "s_no": 1,
        "order_date": now - timedelta(days=42),
        "client_id": "CLT003",
        "manuscript_id": None,
        "journal_name": "Biomaterials",
        "title": "Scaffolds for Tissue Engineering: A Review",
        "order_type": "writing",
        "index": "SCI",
        "rank": "Q1",
        "currency": "USD",
        "total_amount": 1800.00,
        "writing_amount": 1600.00,
        "modification_amount": 150.00,
        "po_amount": 50.00,
        "writing_start_date": now - timedelta(days=42),
        "writing_end_date": now - timedelta(days=20),
        "payment_status": "Paid",
        "remarks": "Delivered and approved.",
        "created_at": now - timedelta(days=42),
        "updated_at": now - timedelta(days=20),
    },
    # ── CLT004 (1 order) ────────────────────────────
    {
        "order_id": "ORD007",
        "reference_id": "EM-2024-007",
        "profile_name": "JohnProfile",
        "client_ref_no": "REF-004",
        "s_no": 1,
        "order_date": now - timedelta(days=28),
        "client_id": "CLT004",
        "manuscript_id": None,
        "journal_name": "Environmental Science & Technology",
        "title": "Carbon Sequestration via Biochar Application in Tropical Soils",
        "order_type": "writing",
        "index": "SCI",
        "rank": "Q1",
        "currency": "USD",
        "total_amount": 1300.00,
        "writing_amount": 1100.00,
        "modification_amount": 150.00,
        "po_amount": 50.00,
        "writing_start_date": now - timedelta(days=28),
        "payment_status": "Partial",
        "remarks": "Phase 1 payment received.",
        "created_at": now - timedelta(days=28),
        "updated_at": now - timedelta(days=7),
    },
    # ── CLT005 (1 order) ────────────────────────────
    {
        "order_id": "ORD008",
        "reference_id": "EM-2024-008",
        "profile_name": "JohnAlt",
        "client_ref_no": "REF-005",
        "s_no": 1,
        "order_date": now - timedelta(days=12),
        "client_id": "CLT005",
        "manuscript_id": None,
        "journal_name": "Physical Review Letters",
        "title": "Quantum Error Correction Using Topological Codes",
        "order_type": "writing",
        "index": "SCI",
        "rank": "Q1",
        "currency": "USD",
        "total_amount": 2500.00,
        "writing_amount": 2200.00,
        "modification_amount": 200.00,
        "po_amount": 100.00,
        "writing_start_date": now - timedelta(days=12),
        "payment_status": "Pending",
        "remarks": "New order, writing in progress.",
        "created_at": now - timedelta(days=12),
        "updated_at": now - timedelta(days=2),
    },
]

orders_collection.insert_many(orders)
print(f"  ✅  {len(orders)} orders inserted.")
print("     CLT001 (Dr. Ahmed Al-Farsi)  → 3 orders")
print("     CLT002 (Prof. Li Wei)         → 2 orders")
print("     CLT003 (Dr. Priya Sharma)     → 1 order")
print("     CLT004 (Dr. Carlos Mendez)    → 1 order")
print("     CLT005 (Dr. Sarah Johnson)    → 1 order\n")

# ─────────────────────────────────────────────────────
# STEP 5: INSERT PAYMENTS
# ─────────────────────────────────────────────────────
print("💳 Creating payments...")

payments = [
    # CLT001 ORD001 - Fully Paid
    {
        "client_ref_number": "REF-001",
        "reference_id": "EM-2024-001",
        "client_id": "CLT001",
        "phase": 2,
        "amount": 1500.00,
        "payment_received_account": "PayPal-Admin",
        "phase_1_payment": 800.00,
        "phase_1_payment_date": now - timedelta(days=80),
        "phase_2_payment": 700.00,
        "phase_2_payment_date": now - timedelta(days=65),
        "status": "Paid",
        "created_at": now - timedelta(days=80),
    },
    # CLT001 ORD002 - Partial
    {
        "client_ref_number": "REF-001",
        "reference_id": "EM-2024-002",
        "client_id": "CLT001",
        "phase": 1,
        "amount": 400.00,
        "payment_received_account": "Bank Transfer",
        "phase_1_payment": 400.00,
        "phase_1_payment_date": now - timedelta(days=60),
        "phase_2_payment": 0.00,
        "status": "Partial",
        "created_at": now - timedelta(days=60),
    },
    # CLT002 ORD004 - Fully Paid
    {
        "client_ref_number": "REF-002",
        "reference_id": "EM-2024-004",
        "client_id": "CLT002",
        "phase": 2,
        "amount": 2000.00,
        "payment_received_account": "Wire Transfer",
        "phase_1_payment": 1000.00,
        "phase_1_payment_date": now - timedelta(days=55),
        "phase_2_payment": 1000.00,
        "phase_2_payment_date": now - timedelta(days=35),
        "status": "Paid",
        "created_at": now - timedelta(days=55),
    },
    # CLT003 ORD006 - Fully Paid
    {
        "client_ref_number": "REF-003",
        "reference_id": "EM-2024-006",
        "client_id": "CLT003",
        "phase": 2,
        "amount": 1800.00,
        "payment_received_account": "PayPal-Admin",
        "phase_1_payment": 900.00,
        "phase_1_payment_date": now - timedelta(days=38),
        "phase_2_payment": 900.00,
        "phase_2_payment_date": now - timedelta(days=22),
        "status": "Paid",
        "created_at": now - timedelta(days=38),
    },
    # CLT004 ORD007 - Partial
    {
        "client_ref_number": "REF-004",
        "reference_id": "EM-2024-007",
        "client_id": "CLT004",
        "phase": 1,
        "amount": 600.00,
        "payment_received_account": "Bank Transfer",
        "phase_1_payment": 600.00,
        "phase_1_payment_date": now - timedelta(days=20),
        "phase_2_payment": 0.00,
        "status": "Partial",
        "created_at": now - timedelta(days=20),
    },
]

payments_collection.insert_many(payments)
print(f"  ✅  {len(payments)} payments inserted.\n")

print("=" * 50)
print("🎉  Database seeded successfully!")
print("=" * 50)
print("\n📋  SUMMARY:")
print("   Users:    3  (1 Admin, 1 Manager, 1 Employee)")
print("   Clients:  5")
print("   Orders:   8  (CLT001 has 3, CLT002 has 2)")
print("   Payments: 5")
print("\n🔑  LOGIN CREDENTIALS:")
print("   admin@dashboard.com     → Admin@123")
print("   manager@dashboard.com   → Manager@123")
print("   employee@dashboard.com  → Employee@123")
