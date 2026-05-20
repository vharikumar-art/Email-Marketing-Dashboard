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
    countries = ["USA", "UK", "Germany", "Japan", "Singapore", "Canada", "Australia", "France", "China", "India", "Netherlands", "Norway"]
    affiliations = ["University", "Research Center", "Corporate", "Freelance"]
    
    org_names = [
        "Global Research Inst", "Health & Biotech", "Tech Synergy", "Green Energy Corp", 
        "Astra Solutions", "Horizon Labs", "BioMed Frontier", "Infinite Tech", "Apex Research", "Nova Systems"
    ]

    for i in range(1, 11):
        client_id = f"CL-{i:03d}"
        org_name = random.choice(org_names)
        # Clean org name for email (remove spaces and special characters like &)
        clean_org = "".join(e for e in org_name if e.isalnum())
        clients.append({
            "client_id": client_id,
            "name": f"{org_name} {i}",
            "country": random.choice(countries),
            "email": f"contact@{clean_org.lower()}.com",
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
    print("Seeding manuscripts (~30% of clients)...")
    ms_list = []
    titles = [
        "Impact of AI on Healthcare", "Renewable Energy Trends", "Genetic Mapping in Agriculture", 
        "Global Economic Shifts", "Marine Biodiversity Loss", "Blockchain in Logistics",
        "Deep Learning for Vision", "Quantum Computing Basics", "Edge Computing in IoT",
        "NLP Advances in 2025", "Cybersecurity in FinTech", "Zero Trust Architecture"
    ]
    journal_names = [
        "Nature", "Science", "The Lancet", "Cell", "BMJ",
        "IEEE Transactions", "PNAS", "JAMA", "Elsevier Reviews",
        "Springer Nature", "Frontiers in AI", "PLoS ONE"
    ]
    
    # Only ~30% of clients get manuscripts
    ms_clients = random.sample(clients, max(1, len(clients) * 3 // 10))
    
    for client in ms_clients:
        # 1-2 Manuscripts per selected client
        for j in range(1, random.randint(2, 3)):
            ms_id = f"MS-{client['client_id']}-{j}"
            ms_list.append({
                "manuscript_id": ms_id,
                "title": f"{random.choice(titles)} Part {j}",
                "journal_name": random.choice(journal_names),
                "order_type": random.choice(["Original", "Modification", "Proofreading"]),
                "client_id": client["client_id"],
                "created_at": datetime.utcnow() - timedelta(days=25)
            })
    if ms_list:
        manuscripts_collection.insert_many(ms_list)
    print(f"Successfully seeded {len(ms_list)} manuscripts for {len(ms_clients)} clients.")
    return ms_list

def seed_orders(clients, manuscripts):
    print("Seeding orders...")
    
    paper_titles = [
        "CRISPR Gene Therapy Review", "Stem Cell Research 2024",
        "Marine Ecosystem Monitoring", "AI-Driven Drug Discovery",
        "Renewable Energy Grid Analysis", "Blockchain Supply Chain Audit",
        "Quantum Cryptography Protocols", "NLP for Clinical Data",
        "Smart City Traffic Optimization", "Deep Learning in Radiology"
    ]
    journal_names = [
        "Nature", "Science", "The Lancet", "Cell", "BMJ",
        "IEEE Transactions", "PNAS", "JAMA", "Elsevier Reviews",
        "Springer Nature", "Frontiers in AI", "PLoS ONE"
    ]
    
    # Build a map of client_id -> list of manuscripts
    ms_by_client = {}
    for ms in manuscripts:
        ms_by_client.setdefault(ms["client_id"], []).append(ms)
    
    orders = []
    for i in range(1, 21):  # 20 orders
        client = clients[(i - 1) % len(clients)]
        
        # ~30% of orders get linked to a manuscript (if the client has any)
        linked_ms = None
        if client["client_id"] in ms_by_client and random.random() < 0.3:
            linked_ms = random.choice(ms_by_client[client["client_id"]])
        
        total = float(random.randint(1000, 5000))
        
        orders.append({
            "order_id": f"ORD-SEED-{i:03d}",
            "reference_id": f"REF-S{i:04d}",  # Unique per order, created by users
            "client_ref_no": client.get("client_ref_no"),  # Optional, from client
            "s_no": i,
            "order_date": datetime.utcnow() - timedelta(days=20),
            "client_id": client["client_id"],
            "manuscript_id": linked_ms["manuscript_id"] if linked_ms else None,
            "journal_name": linked_ms.get("journal_name") if linked_ms else random.choice(journal_names),
            "title": linked_ms["title"] if linked_ms else random.choice(paper_titles),
            "order_type": linked_ms["order_type"] if linked_ms else random.choice(["Original", "Modification", "Proofreading"]),
            "index": random.choice(["Q1", "Q2", "Q3"]),
            "rank": random.choice(["A", "B"]),
            "currency": "USD",
            "total_amount": total,
            "writing_amount": total * 0.6,
            "modification_amount": total * 0.2,
            "po_amount": total * 0.2,
            "payment_status": random.choice(["Pending", "Partial", "Paid"]),
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
            "client_ref_number": order.get("client_ref_no"),
            "reference_id": order.get("reference_id"),  # Copied from order
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
                    "client_ref_number": order.get("client_ref_no"),
                    "reference_id": order.get("reference_id"),  # Copied from order
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
