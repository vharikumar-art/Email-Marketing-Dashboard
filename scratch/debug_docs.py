from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "EM_DashBoard")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

print("ORDER:")
print(db.orders.find_one())
print("\nPAYMENT:")
print(db.payments.find_one())
