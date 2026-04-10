import sys
import os
import random
from datetime import datetime, timedelta

# Add the current directory to sys.path to import local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import (
    users_collection, 
    clients_collection, 
    manuscripts_collection, 
    orders_collection, 
    payments_collection,
    otps_collection
)
from schemas import UserRole

def get_existing_handlers():
    """Fetch names of existing Admin and Manager users to act as client handlers."""
    users = list(users_collection.find({"role": {"$in": [UserRole.ADMIN, UserRole.MANAGER]}}))
    if not users:
        # Fallback if no admins found
        return ["Default Admin"]
    return [u["full_name"] for u in users]

def clear_operational_data():
    """Clear all collections except users and tokens."""
    print("Clearing operational collections...")
    clients_collection.delete_many({})
    manuscripts_collection.delete_many({})
    orders_collection.delete_many({})
    payments_collection.delete_many({})
    otps_collection.delete_many({})
    print("Cleanup complete.")

def seed_clients(handlers):
    print("Seeding clients...")
    clients = []
    locations = ["California, USA", "London, UK", "Berlin, Germany", "Tokyo, Japan", "Singapore", "New York, USA"]
    affiliations = ["University", "Research Center", "Corporate", "Freelance"]
    
    for i in range(1, 11):
        client_id = f"CL-{i:03d}"
        clients.append({
            "client_id": client_id,
            "name": f"Organization {i}",
            "location": random.choice(locations),
            "email": f"contact{i}@org{i}.com",
            "whatsapp_no": f"+12345678{i:02d}",
            "client_ref_no": f"REF-{2000 + i}",
            "client_link": f"https://org{i}.com",
            "bank_account": f"BANK-{5000 + i}",
            "affiliation": random.choice(affiliations),
            "total_orders": 0,
            "client_handler": random.choice(handlers),
            "created_at": datetime.utcnow() - timedelta(days=30)
        })
    clients_collection.insert_many(clients)
    print(f"Successfully seeded {len(clients)} clients.")
    return clients

def seed_manuscripts(clients):
    print("Seeding manuscripts...")
    ms_list = []
    titles = [
        "Impact of AI on Healthcare", "Renewable Energy Trends", "Genetic Mapping in Agriculture", 
        "Global Economic Shifts", "Marine Biodiversity Loss", "Blockchain in Logistics"
    ]
    
    for client in clients:
        # 2 Manuscripts per client
        for j in range(1, 3):
            ms_id = f"MS-{client['client_id']}-{j}"
            ms_list.append({
                "manuscript_id": ms_id,
                "title": f"{random.choice(titles)} Part {j}",
                "order_type": random.choice(["Original", "Modification", "Proofreading"]),
                "client_id": client["client_id"],
                "client_ref_no": client["client_ref_no"],
                "created_at": datetime.utcnow() - timedelta(days=25)
            })
    manuscripts_collection.insert_many(ms_list)
    print(f"Successfully seeded {len(ms_list)} manuscripts.")
    return ms_list

def seed_orders(clients, manuscripts):
    print("Seeding orders...")
    orders = []
    for i, ms in enumerate(manuscripts):
        client = next(c for c in clients if c["client_id"] == ms["client_id"])
        
        order_id = f"ORD-{ms['manuscript_id']}"
        total = float(random.randint(1000, 5000))
        
        orders.append({
            "order_id": order_id,
            "client_ref_no": client["client_ref_no"],
            "s_no": i + 1,
            "order_date": datetime.utcnow() - timedelta(days=20),
            "client_id": client["client_id"],
            "manuscript_id": ms["manuscript_id"],
            "order_type": ms["order_type"],
            "index": random.choice(["Q1", "Q2", "Q3"]),
            "rank": random.choice(["A", "B"]),
            "currency": "USD",
            "total_amount": total,
            "writing_amount": total * 0.6,
            "modification_amount": total * 0.2,
            "po_amount": total * 0.2,
            "payment_status": random.choice(["Pending", "Partial", "Paid"]),
            "assigned_to": client["client_handler"],
            "remarks": "Priority Seeding Data",
            "created_at": datetime.utcnow() - timedelta(days=20),
            "updated_at": datetime.utcnow()
        })
    orders_collection.insert_many(orders)
    
    # Update client total_orders count
    for client in clients:
        count = orders_collection.count_documents({"client_id": client["client_id"]})
        clients_collection.update_one({"client_id": client["client_id"]}, {"$set": {"total_orders": count}})
        
    print(f"Successfully seeded {len(orders)} orders.")
    return orders

def seed_payments(orders):
    print("Seeding payments...")
    payments = []
    for order in orders:
        if order["payment_status"] == "Pending":
            continue
            
        # Add at least phase 1 for Partial/Paid
        pay_date = order["order_date"] + timedelta(days=5)
        phase_1_amt = order["total_amount"] * 0.4
        
        payments.append({
            "client_ref_number": order["client_ref_no"],
            "client_id": order["client_id"],
            "order_id": order["order_id"],
            "phase": 1,
            "amount": phase_1_amt,
            "payment_received_account": "HDFC-PRIMARY",
            "payment_date": pay_date,
            "phase_1_payment": phase_1_amt,
            "phase_1_payment_date": pay_date,
            "status": "Verified",
            "created_at": pay_date
        })
        
        # If Paid, add other phases
        if order["payment_status"] == "Paid":
            for phase in [2, 3]:
                amt = order["total_amount"] * 0.3
                p_date = pay_date + timedelta(days=phase * 5)
                payments.append({
                    "client_ref_number": order["client_ref_no"],
                    "client_id": order["client_id"],
                    "order_id": order["order_id"],
                    "phase": phase,
                    "amount": amt,
                    "payment_received_account": "HDFC-PRIMARY",
                    "payment_date": p_date,
                    f"phase_{phase}_payment": amt,
                    f"phase_{phase}_payment_date": p_date,
                    "status": "Verified",
                    "created_at": p_date
                })
                
    if payments:
        payments_collection.insert_many(payments)
    print(f"Successfully seeded {len(payments)} payment phases.")

if __name__ == "__main__":
    try:
        handlers = get_existing_handlers()
        print(f"Found active handlers: {handlers}")
        
        clear_operational_data()
        
        clients = seed_clients(handlers)
        manuscripts = seed_manuscripts(clients)
        orders = seed_orders(clients, manuscripts)
        seed_payments(orders)
        
        print("\n" + "="*40)
        print("RELATIONAL MOCK DATA SEEDED SUCCESSFULLY")
        print("="*40)
        print("Note: Users and Tokens collections were preserved.")
        
    except Exception as e:
        print(f"Error seeding data: {e}")
        import traceback
        traceback.print_exc()
