"""MongoDB connection and indexes."""
from pymongo import MongoClient, ASCENDING, DESCENDING, GEOSPHERE, ReturnDocument
from config import MONGO_URI, DB_NAME

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
db = client[DB_NAME]
incidents = db["incidents"]
counters = db["counters"]


def init_indexes():
    incidents.create_index([("location", GEOSPHERE)])
    incidents.create_index([("detected_at", DESCENDING)])
    incidents.create_index([("status", ASCENDING), ("severity", ASCENDING)])
    incidents.create_index([("zone", ASCENDING)])
    incidents.create_index("incident_code", unique=True)


def next_incident_code() -> str:
    """KOP-000001, KOP-000002, ... (atomic counter)."""
    doc = counters.find_one_and_update(
        {"_id": "incident"}, {"$inc": {"seq": 1}}, upsert=True,
        return_document=ReturnDocument.AFTER)
    return f"KOP-{doc['seq']:06d}"
