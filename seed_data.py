import sys
import os
from datetime import datetime

# Add the current directory to sys.path to import local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import (
    users_collection, 
    clients_collection, 
    manuscripts_collection, 
    orders_collection, 
    payments_collection
)
from auth import get_password_hash
from schemas import UserRole

def seed_users():
    print("Seeding users...")
    users_collection.delete_many({})
    users = []
    # 2 Super Admins
    for i in range(1, 3):
        users.append({
            "email": f"superadmin{i}@example.com",
            "password": get_password_hash("superadmin123"),
            "full_name": f"Super Admin {i}",
            "role": UserRole.ADMIN,
            "created_at": datetime.utcnow()
        })
    # 4 Admins
    for i in range(1, 5):
        users.append({
            "email": f"admin{i}@example.com",
            "password": get_password_hash("admin123"),
            "full_name": f"Admin {i}",
            "role": UserRole.ADMIN,
            "created_at": datetime.utcnow()
        })
    # 6 Users
    for i in range(1, 7):
        users.append({
            "email": f"user{i}@example.com",
            "password": get_password_hash("user123"),
            "full_name": f"User {i}",
            "role": UserRole.EMPLOYEE,
            "created_at": datetime.utcnow()
        })
    users_collection.insert_many(users)
    print(f"Successfully seeded {len(users)} users.")
    return [u["email"] for u in users if u["role"] == UserRole.ADMIN]

def seed_clients(admin_emails):
    print("Seeding clients...")
    clients_collection.delete_many({})
    clients = []
    for i in range(1, 41):
        ref_no = f"REF-{1000 + i}"
        clients.append({
            "client_id": f"CL-{i:03d}",
            "name": f"Client Organization {i}",
            "location": f"City {i}",
            "email": f"contact{i}@clientorg.com",
            "whatsapp_no": f"+12345678{i:02d}",
            "client_ref_no": ref_no,
            "client_link": f"https://client{i}.com",
            "bank_account": f"ACC-{5000 + i}",
            "affiliation": "Research Partner",
            "total_orders": 0,
            "client_handlers": admin_emails[i % len(admin_emails)], # Linked to an Admin
            "created_at": datetime.utcnow()
        })
    result = clients_collection.insert_one(clients[0]) # Dummy to show structure if needed, but we use insert_many
    clients_collection.delete_many({}) # Clean up
    result = clients_collection.insert_many(clients)
    print(f"Successfully seeded {len(clients)} clients.")
    return clients # Return full docs for ref access

def seed_manuscripts(clients):
    print("Seeding manuscripts...")
    manuscripts_collection.delete_many({})
    ms_list = []
    for i, client in enumerate(clients):
        # 2 Manuscripts per client
        for j in range(1, 3):
            ms_list.append({
                "manuscript_id": f"MS-{client['client_id']}-{j}",
                "title": f"Scientific Paper {i+1}.{j}",
                "order_type": "Original",
                "client_id": client["client_id"], # Proper Relation
                "client_ref_no": client["client_ref_no"], # Matching Ref
                "created_at": datetime.utcnow()
            })
    result = manuscripts_collection.insert_many(ms_list)
    print(f"Successfully seeded {len(ms_list)} manuscripts.")
    return ms_list

def seed_orders(clients, manuscripts):
    print("Seeding orders...")
    orders_collection.delete_many({})
    orders = []
    for i, client in enumerate(clients):
        # Link to the first manuscript of this client
        ms = next(m for m in manuscripts if m["client_id"] == client["client_id"])
        
        orders.append({
            "order_id": f"ORD-{client['client_id']}",
            "client_ref_no": client["client_ref_no"], # Matching Ref
            "s_no": i + 1,
            "order_date": datetime.utcnow(),
            "client_id": client["client_id"], # Proper Relation
            "manuscript_id": ms["manuscript_id"], # Proper Relation
            "order_type": ms["order_type"],
            "index": "Q1",
            "rank": "A",
            "currency": "USD",
            "total_amount": 1000.0,
            "writing_amount": 600.0,
            "modification_amount": 200.0,
            "po_amount": 200.0,
            "payment_status": "Partial" if i % 2 == 0 else "Pending",
            "assigned_to": client["client_handlers"], # Linked to the same handler
            "remarks": "Urgent" if i % 10 == 0 else "Regular",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })
    orders_collection.insert_many(orders)
    print(f"Successfully seeded {len(orders)} orders.")
    return orders

def seed_payments(clients, orders):
    print("Seeding payments...")
    payments_collection.delete_many({})
    payments = []
    for i, client in enumerate(clients[:20]): # Payments for first 20 clients
        order = next(o for o in orders if o["client_id"] == client["client_id"])
        
        payments.append({
            "client_ref_number": client["client_ref_no"], # Matching Ref
            "client_id": client["client_id"], # Proper Relation
            "phase": 1,
            "amount": order["total_amount"] / 2, # Logical amount
            "payment_received_account": "HDFC-001",
            "payment_date": datetime.utcnow(),
            "phase_1_payment": order["total_amount"] / 2,
            "phase_1_payment_date": datetime.utcnow(),
            "status": "Verified",
            "created_at": datetime.utcnow()
        })
    payments_collection.insert_many(payments)
    print(f"Successfully seeded {len(payments)} payments.")

if __name__ == "__main__":
    try:
        admin_emails = seed_users()
        clients = seed_clients(admin_emails)
        manuscripts = seed_manuscripts(clients)
        orders = seed_orders(clients, manuscripts)
        seed_payments(clients, orders)
        print("\nAll mock data seeded with STRICT RELATIONS successfully!")
    except Exception as e:
        print(f"Error seeding data: {e}")
        import traceback
        traceback.print_exc()
