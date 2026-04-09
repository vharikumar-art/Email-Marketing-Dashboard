import sys
import os
import random
from datetime import datetime, timedelta
from bson import ObjectId

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

def clear_data():
    print("Clearing existing data...")
    users_collection.delete_many({})
    clients_collection.delete_many({})
    manuscripts_collection.delete_many({})
    orders_collection.delete_many({})
    payments_collection.delete_many({})
    print("Data cleared.")

def generate_users():
    print("Generating 5 users...")
    users = [
        {"name": "Robert Smith", "email": "robert.s@company.com", "role": UserRole.ADMIN},
        {"name": "Sarah Jenkins", "email": "sarah.j@company.com", "role": UserRole.MANAGER},
        {"name": "Michael Chen", "email": "michael.c@company.com", "role": UserRole.MANAGER},
        {"name": "Emily Davis", "email": "emily.d@company.com", "role": UserRole.EMPLOYEE},
        {"name": "David Wilson", "email": "david.w@company.com", "role": UserRole.EMPLOYEE},
    ]
    
    for u in users:
        u["password_hash"] = get_password_hash("password123")
        u["created_at"] = datetime.utcnow() - timedelta(days=random.randint(30, 60))
        # Keep original passwords as passwords for testing
        u["password"] = "password123" 
    
    result = users_collection.insert_many(users)
    print(f"Inserted {len(result.inserted_ids)} users.")
    return list(users_collection.find())

def generate_clients(admin_ids):
    print("Generating 10 clients...")
    university_names = ["Stanford University", "Oxford University", "MIT", "Harvard Medical School", "Tokyo University"]
    company_names = ["BioTech Solutions", "EcoSystems Inc", "Quantum Labs", "PharmaCare", "Innovate Tech"]
    
    clients = []
    for i in range(1, 11):
        ref_no = f"REF-{2000 + i}"
        is_uni = i % 2 == 0
        clients.append({
            "client_id": f"CL-{i:03d}",
            "name": university_names[i//2 % 5] if is_uni else company_names[i//2 % 5],
            "location": random.choice(["California, USA", "London, UK", "Berlin, Germany", "Tokyo, Japan", "Singapore"]),
            "email": f"info@{ref_no.lower()}.org",
            "whatsapp_no": f"+1{''.join([str(random.randint(0,9)) for _ in range(9)])}",
            "client_ref_no": ref_no,
            "client_link": f"https://{ref_no.lower()}.org",
            "bank_account": f"IBAN-{''.join([str(random.randint(0,9)) for _ in range(12)])}",
            "affiliation": "University" if is_uni else "Corporate",
            "total_orders": 0, # Will be updated after orders
            "client_handlers": str(random.choice(admin_ids)),
            "created_at": datetime.utcnow() - timedelta(days=random.randint(20, 40))
        })
    
    clients_collection.insert_many(clients)
    print("Inserted 10 clients.")
    return list(clients_collection.find())

def generate_manuscripts(clients):
    print("Generating 20 manuscripts...")
    titles = [
        "Impact of Climate Change on Marine Biodiversity",
        "Advancements in CRISPR-Cas9 Gene Editing",
        "Neural Networks for Pattern Recognition in Medical Imaging",
        "Sustainable Agriculture in Sub-Saharan Africa",
        "The Role of Blockchain in Supply Chain Management",
        "Renewable Energy Trends in 2024",
        "Microplastic Contamination in Urban Waterways",
        "Machine Learning Models for Financial Forecasting",
        "Quantum Computing: A New Frontier in Cybersecurity",
        "Ethical Implications of Artificial Intelligence in Healthcare"
    ]
    
    ms_list = []
    for i in range(20):
        client = clients[i % 10]
        ms_list.append({
            "manuscript_id": f"MS-{client['client_id']}-{i+1}",
            "title": random.choice(titles) + f" (Part {i//10 + 1})",
            "order_type": random.choice(["writing", "modification", "proofreading"]),
            "client_id": client["client_id"],
            "client_ref_no": client["client_ref_no"],
            "created_at": datetime.utcnow() - timedelta(days=random.randint(15, 25))
        })
    
    manuscripts_collection.insert_many(ms_list)
    print("Inserted 20 manuscripts.")
    return list(manuscripts_collection.find())

def generate_orders(clients, manuscripts, user_ids):
    print("Generating 30 orders...")
    orders = []
    for i in range(1, 31):
        ms = manuscripts[i % 20]
        client = next(c for c in clients if c["client_id"] == ms["client_id"])
        
        # Logical dates
        start_date = ms["created_at"] + timedelta(days=random.randint(1, 3))
        end_date = start_date + timedelta(days=random.randint(5, 15))
        
        total = random.randint(800, 5000)
        writing = total * 0.6
        mod = total * 0.2
        po = total * 0.2
        
        status = random.choice(["pending", "partial", "paid"])
        
        orders.append({
            "order_id": f"ORD-{2024}-{i:03d}",
            "client_ref_no": client["client_ref_no"],
            "s_no": i,
            "order_date": start_date,
            "client_id": client["client_id"],
            "manuscript_id": ms["manuscript_id"],
            "order_type": ms["order_type"],
            "index": random.choice(["SCI", "Scopus", "ESCI"]),
            "rank": random.choice(["Q1", "Q2", "Q3", "Q4"]),
            "currency": random.choice(["USD", "INR"]),
            "total_amount": total,
            "writing_amount": writing,
            "modification_amount": mod,
            "po_amount": po,
            "writing_start_date": start_date,
            "writing_end_date": end_date,
            "modification_start_date": end_date + timedelta(days=1),
            "modification_end_date": end_date + timedelta(days=5),
            "payment_status": status,
            "assigned_to": str(random.choice(user_ids)),
            "remarks": "Priority order" if i % 5 == 0 else "Routine check",
            "created_at": start_date,
            "updated_at": datetime.utcnow()
        })
    
    orders_collection.insert_many(orders)
    
    # Update client total_orders count
    for client in clients:
        count = orders_collection.count_documents({"client_id": client["client_id"]})
        clients_collection.update_one({"_id": client["_id"]}, {"$set": {"total_orders": count}})
        
    print("Inserted 30 orders.")
    return list(orders_collection.find())

def generate_payments(clients, orders):
    print("Generating 40 payments...")
    payments = []
    for i in range(40):
        # Pick an order that is either partial or paid
        order = random.choice([o for o in orders if o["payment_status"] in ["partial", "paid"]])
        client = next(c for c in clients if c["client_id"] == order["client_id"])
        
        # Determin phase based on existing payments for this order
        existing_phases = [p["phase"] for p in payments if p.get("order_id") == order["order_id"]]
        phase = 1 if not existing_phases else max(existing_phases) + 1
        if phase > 3: phase = 3 # Cap at 3 for logic
        
        # Amount logic
        pay_amount = order["total_amount"] / 3
        if phase == 3: # Remaining
             total_paid = sum(p["amount"] for p in payments if p.get("order_id") == order["order_id"])
             pay_amount = max(0, order["total_amount"] - total_paid)
        
        if pay_amount <= 0: continue

        pay_date = order["order_date"] + timedelta(days=random.randint(5, 30))
        
        payments.append({
            "client_ref_number": client["client_ref_no"],
            "client_id": client["client_id"],
            "order_id": order["order_id"], # Extra internal ref for logic
            "phase": phase,
            "amount": round(pay_amount, 2),
            "payment_received_account": random.choice(["HDFC-SAVINGS-4521", "BOI-BUSINESS-8890", "PAYPAL-MERCHANT"]),
            "payment_date": pay_date,
            "phase_1_payment": round(pay_amount, 2) if phase == 1 else 0.0,
            "phase_1_payment_date": pay_date if phase == 1 else None,
            "phase_2_payment": round(pay_amount, 2) if phase == 2 else 0.0,
            "phase_2_payment_date": pay_date if phase == 2 else None,
            "phase_3_payment": round(pay_amount, 2) if phase == 3 else 0.0,
            "phase_3_payment_date": pay_date if phase == 3 else None,
            "status": "paid",
            "created_at": pay_date
        })
    
    if payments:
        payments_collection.insert_many(payments)
    print(f"Inserted {len(payments)} payments.")

if __name__ == "__main__":
    try:
        clear_data()
        
        users = generate_users()
        admin_and_manager_ids = [u["_id"] for u in users if u["role"] in [UserRole.ADMIN, UserRole.MANAGER]]
        employee_ids = [u["_id"] for u in users if u["role"] == UserRole.EMPLOYEE]
        all_user_ids = [u["_id"] for u in users]
        
        clients = generate_clients(admin_and_manager_ids)
        manuscripts = generate_manuscripts(clients)
        orders = generate_orders(clients, manuscripts, all_user_ids)
        generate_payments(clients, orders)
        
        print("\n" + "="*40)
        print("REALISTIC MOCK DATA GENERATED SUCCESSFULLY")
        print("="*40)
        print(f"Users: 5  |  Clients: 10  |  Manuscripts: 20")
        print(f"Orders: 30 |  Payments: {payments_collection.count_documents({})} ")
        print("="*40)
        print(f"Sample Login: robert.s@company.com / password123 (ADMIN)")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
