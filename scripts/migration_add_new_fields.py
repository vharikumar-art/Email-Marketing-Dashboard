#!/usr/bin/env python3
"""
Database Migration Script: Add New Fields for Unified API

This script adds the following new fields to support the unified create API:
- users.profile_name: String, optional
- clients.clients_details: String, optional
- clients.client_drive_link: String, optional
- clients.payment_drive_link: String, optional (SOURCE field)
- orders.payment_drive_link: String, optional (DERIVED from client)

Run this script once to migrate your existing database.
"""

import sys
import os
from datetime import datetime

# Add the current directory to Python path to import config
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pymongo import MongoClient
from config import MONGO_URI, DB_NAME

def migrate_database():
    """Add new fields to existing collections"""

    print("🔄 Starting database migration...")

    # Connect to MongoDB
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]

    # Get collections
    users_collection = db["users"]
    clients_collection = db["clients"]
    orders_collection = db["orders"]

    print("📊 Connected to database successfully")

    # Migration counters
    migrated_users = 0
    migrated_clients = 0
    migrated_orders = 0

    # 1. Add profile_name to users collection
    print("👤 Adding profile_name field to users collection...")
    users_without_profile = users_collection.find({"profile_name": {"$exists": False}})
    for user in users_without_profile:
        # Set default profile_name based on full_name or email
        default_profile = user.get("full_name", user["email"].split("@")[0])
        users_collection.update_one(
            {"_id": user["_id"]},
            {"$set": {"profile_name": f"{default_profile}'s Profile"}}
        )
        migrated_users += 1

    print(f"✅ Added profile_name to {migrated_users} users")

    # 2. Add new fields to clients collection
    print("🏢 Adding new fields to clients collection...")
    clients_without_new_fields = clients_collection.find({
        "$or": [
            {"clients_details": {"$exists": False}},
            {"client_drive_link": {"$exists": False}},
            {"payment_drive_link": {"$exists": False}}
        ]
    })

    for client in clients_without_new_fields:
        update_data = {}

        if "clients_details" not in client:
            update_data["clients_details"] = None

        if "client_drive_link" not in client:
            update_data["client_drive_link"] = None

        if "payment_drive_link" not in client:
            update_data["payment_drive_link"] = None

        if update_data:
            clients_collection.update_one(
                {"_id": client["_id"]},
                {"$set": update_data}
            )
            migrated_clients += 1

    print(f"✅ Added new fields to {migrated_clients} clients")

    # 3. Add payment_drive_link to orders collection and populate from client
    print("📋 Adding payment_drive_link field to orders collection...")
    orders_without_payment_link = orders_collection.find({"payment_drive_link": {"$exists": False}})

    for order in orders_without_payment_link:
        # Get client's payment_drive_link
        client = clients_collection.find_one({"client_id": order["client_id"]})
        client_payment_link = client.get("payment_drive_link") if client else None

        orders_collection.update_one(
            {"_id": order["_id"]},
            {"$set": {"payment_drive_link": client_payment_link}}
        )
        migrated_orders += 1

    print(f"✅ Added payment_drive_link to {migrated_orders} orders")

    # 4. Update existing orders to use client's current payment_drive_link
    print("🔄 Updating existing orders with current client payment_drive_link...")
    all_orders = orders_collection.find({})
    updated_orders = 0

    for order in all_orders:
        client = clients_collection.find_one({"client_id": order["client_id"]})
        if client and client.get("payment_drive_link") != order.get("payment_drive_link"):
            orders_collection.update_one(
                {"_id": order["_id"]},
                {"$set": {"payment_drive_link": client.get("payment_drive_link")}}
            )
            updated_orders += 1

    print(f"✅ Updated payment_drive_link in {updated_orders} existing orders")

    # Verification
    print("\n🔍 Verification:")
    print(f"Total users: {users_collection.count_documents({})}")
    print(f"Users with profile_name: {users_collection.count_documents({'profile_name': {'$exists': True}})}")
    print(f"Total clients: {clients_collection.count_documents({})}")
    print(f"Clients with new fields: {clients_collection.count_documents({'clients_details': {'$exists': True}, 'client_drive_link': {'$exists': True}, 'payment_drive_link': {'$exists': True}})}")
    print(f"Total orders: {orders_collection.count_documents({})}")
    print(f"Orders with payment_drive_link: {orders_collection.count_documents({'payment_drive_link': {'$exists': True}})}")

    print("\n✅ Database migration completed successfully!")
    print(f"📈 Summary: {migrated_users} users, {migrated_clients} clients, {migrated_orders} orders migrated")

    client.close()

if __name__ == "__main__":
    print("🚀 Database Migration Script for Unified API")
    print("=" * 50)

    # Confirm before proceeding
    confirm = input("⚠️  This will modify your database. Are you sure? (yes/no): ").lower().strip()
    if confirm not in ['yes', 'y']:
        print("❌ Migration cancelled.")
        sys.exit(0)

    try:
        migrate_database()
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        sys.exit(1)