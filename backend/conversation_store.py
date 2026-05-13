import json
import os
import datetime

BASE_DIR = "conversations"
os.makedirs(BASE_DIR, exist_ok=True)

def _get_file_path(user_id):
    safe_id = user_id.replace("@", "_").replace(".", "_")
    return os.path.join(BASE_DIR, f"{safe_id}.json")

def load_conversation(user_id):
    path = _get_file_path(user_id)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_message(user_id, role, message, meta=None):
    path = _get_file_path(user_id)
    history = load_conversation(user_id)

    history.append({
        "role": role,
        "message": message,
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "meta": meta or {}
    })

    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)
