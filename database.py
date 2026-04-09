from pymongo import MongoClient
from config import MONGO_URI, DB_NAME

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

users_collection = db["users"]
tokens_collection = db["tokens"]
clients_collection = db["clients"]
orders_collection = db["orders"]
manuscripts_collection = db["manuscripts"]
payments_collection = db["payments"]
otps_collection = db["otps"]
