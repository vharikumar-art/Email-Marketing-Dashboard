from pymongo import MongoClient
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "EM_DashBoard")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

def test_payment_history():
    print("\n--- Testing Payment History Pipeline ---")
    pipeline = [
        {"$match": {}},
        {
            "$lookup": {
                "from": "clients",
                "localField": "client_id",
                "foreignField": "client_id",
                "as": "client_info"
            }
        },
        {
            "$lookup": {
                "from": "orders",
                "localField": "order_id",
                "foreignField": "order_id",
                "as": "order_info"
            }
        },
        {"$unwind": {"path": "$client_info", "preserveNullAndEmptyArrays": True}},
        {"$unwind": {"path": "$order_info", "preserveNullAndEmptyArrays": True}},
        {
            "$project": {
                "_id": 0,
                "client_name": "$client_info.name",
                "client_id": {"$ifNull": ["$client_id", "$order_info.client_id"]},
                "order_id": 1,
                "reference_id": {"$ifNull": ["$reference_id", "$order_info.reference_id"]},
                "amount": {"$ifNull": ["$amount", "$order_info.total_amount"]},
                "paid_amount": {"$ifNull": ["$paid_amount", 0.0]},
                "payment_date": 1,
                "order_title": "$order_info.title",
                "phase_1_payment": {"$ifNull": ["$phase_1_payment", 0.0]},
                "phase_1_payment_date": 1,
                "phase_1_payment_details": 1,
                "phase_2_payment": {"$ifNull": ["$phase_2_payment", 0.0]},
                "phase_2_payment_date": 1,
                "phase_2_payment_details": 1,
                "phase_3_payment": {"$ifNull": ["$phase_3_payment", 0.0]},
                "phase_3_payment_date": 1,
                "phase_3_payment_details": 1
            }
        },
        {"$sort": {"payment_date": -1}},
        {"$limit": 5}
    ]
    results = list(db.payments.aggregate(pipeline))
    for res in results:
        print(res)

def test_pending_summary():
    print("\n--- Testing Pending Summary Pipeline ---")
    rate = 0.012  # Hardcoded for test
    pipeline = [
        {"$match": {"order_status": {"$ne": "Inactive"}}},
        {
            "$addFields": {
                "total_usd": {
                    "$cond": [
                        {"$eq": ["$currency", "INR"]},
                        {"$multiply": ["$total_amount", rate]},
                        "$total_amount"
                    ]
                },
                "paid_usd": {
                    "$cond": [
                        {"$eq": ["$currency", "INR"]},
                        {"$multiply": [{"$ifNull": ["$paid_amount", 0.0]}, rate]},
                        {"$ifNull": ["$paid_amount", 0.0]}
                    ]
                }
            }
        },
        {
            "$addFields": {
                "remaining_usd": {"$subtract": ["$total_usd", "$paid_usd"]}
            }
        },
        {"$match": {"remaining_usd": {"$gt": 0}}},
        {
            "$group": {
                "_id": "$client_id",
                "pending_orders": {"$sum": 1},
                "total_pending_amount": {"$sum": "$remaining_usd"}
            }
        },
        {
            "$lookup": {
                "from": "clients",
                "localField": "_id",
                "foreignField": "client_id",
                "as": "client_info"
            }
        },
        {"$unwind": "$client_info"},
        {
            "$project": {
                "_id": 0,
                "client_id": "$_id",
                "client_name": "$client_info.name",
                "total_orders": "$client_info.total_orders",
                "pending_orders": 1,
                "total_pending_amount": 1
            }
        },
        {"$sort": {"total_pending_amount": -1}}
    ]
    results = list(db.orders.aggregate(pipeline))
    print(f"Total Pending Clients: {len(results)}")
    for res in results[:5]:
        print(res)

if __name__ == "__main__":
    test_payment_history()
    test_pending_summary()
