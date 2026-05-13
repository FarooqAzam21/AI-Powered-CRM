from auth.jwt import get_password_hash
import json

with open("data/users.json", "r") as f:
    users = json.load(f)

for u in users:
    if not u["password"].startswith("$2b$"):
        u["password"] = get_password_hash(u["password"])

with open("data/users.json", "w") as f:
    json.dump(users, f, indent=2)

print("✅ All passwords hashed")
