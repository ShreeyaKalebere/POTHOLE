"""Copies the laptop's staff accounts to the online database, so the same usernames and passwords work there.

Run (from the backend folder):  python sync_accounts_to_cloud.py
It asks for your MongoDB Atlas link (hidden while you paste) and the online database name.
Only password hashes are copied, never the passwords. An online account with the same username
is overwritten, including an admin created from APP_PASSWORD. Nothing else online is changed.
"""
import getpass

from pymongo import ASCENDING, MongoClient
from pymongo.errors import InvalidURI

from accounts import users as laptop_users

FIELDS = ("username", "name", "role", "ward", "team", "password_hash", "active", "created_at")


def main():
    accounts = list(laptop_users.find({}, {f: 1 for f in FIELDS}))
    if not accounts:
        raise SystemExit("No accounts found on this laptop. Run seed_users.py first.")
    print("Accounts to copy:", ", ".join(a["username"] for a in accounts))

    uri = getpass.getpass("Paste your MongoDB Atlas link (it will not show): ").strip().strip("\"'")
    if not uri.startswith("mongodb"):
        raise SystemExit("That does not look like a MongoDB link.")
    db_name = input("Online database name [pothole_detection]: ").strip() or "pothole_detection"

    try:
        online = MongoClient(uri, serverSelectionTimeoutMS=10000)[db_name]["users"]
    except InvalidURI:
        raise SystemExit("The link was not pasted fully. Copy it again from Atlas (Connect > Drivers) and run this again.")
    online.find_one()   # fails here with a clear error if the link or password is wrong
    online.create_index([("username", ASCENDING)], unique=True)
    for a in accounts:
        doc = {f: a.get(f) for f in FIELDS if f != "username"}
        result = online.update_one({"username": a["username"]}, {"$set": doc}, upsert=True)
        print(f"  {a['username']:22} {'updated' if result.matched_count else 'created'}")
    print(f"Done. These accounts now use the same passwords on the website (database '{db_name}').")


if __name__ == "__main__":
    main()
