"""Creates demo staff accounts for the laptop and writes them to demo_accounts.local.txt (never committed).

Run (from the backend folder):  python seed_users.py
Existing accounts are left unchanged. Do not use these accounts on the online app.
"""
import secrets
from pathlib import Path

from accounts import create_user, init_accounts, users

ACCOUNTS = [
    ("admin", "Administrator", "admin", None, None),
    ("officer_shahupuri", "Shahupuri Ward Officer", "ward_officer", "Shahupuri", None),
    ("officer_rajarampuri", "Rajarampuri Ward Officer", "ward_officer", "Rajarampuri", None),
    ("repair_unit1", "Road Repair Unit 1", "repair_team", None, "Road Repair Unit 1"),
    ("repair_unit2", "Road Repair Unit 2", "repair_team", None, "Road Repair Unit 2"),
]
OUT = Path(__file__).with_name("demo_accounts.local.txt")


def main():
    init_accounts()
    existing = OUT.read_text(encoding="utf-8").splitlines() if OUT.exists() else []
    lines = existing or ["MargDrishti demo accounts (laptop only). Do not share or commit this file.", ""]
    for username, name, role, ward, team in ACCOUNTS:
        if users.find_one({"username": username}):
            print("already exists:", username)
            continue
        password = secrets.token_urlsafe(9)
        create_user(username, password, role, name, ward, team)
        lines.append(f"{role:13} {username:22} {password}")
        print("created:", username)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("accounts file:", OUT)


if __name__ == "__main__":
    main()
