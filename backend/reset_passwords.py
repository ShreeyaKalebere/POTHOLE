"""Gives every staff account a new random password and writes them to demo_accounts.local.txt (never committed).

Run (from the backend folder):  python reset_passwords.py
Old logins stop working straight away, because sessions are tied to the password.
"""
import secrets
from pathlib import Path

from accounts import hash_password, users

OUT = Path(__file__).with_name("demo_accounts.local.txt")


def main():
    lines = ["MargDrishti demo accounts (laptop only). Do not share or commit this file.", ""]
    for user in users.find({}).sort([("role", 1), ("username", 1)]):
        password = secrets.token_urlsafe(9)
        users.update_one({"_id": user["_id"]}, {"$set": {"password_hash": hash_password(password), "active": True}})
        lines.append(f"{user['role']:13} {user['username']:22} {password}")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"new passwords set for {len(lines) - 2} accounts, saved in {OUT}")


if __name__ == "__main__":
    main()
