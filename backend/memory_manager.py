import csv
import os
import datetime

FILE_NAME = "conversation_memory.csv"

def save_message(user_id, message, category, confidence, priority):
    file_exists = os.path.isfile(FILE_NAME)

    with open(FILE_NAME, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow([
                "User ID", "Time", "Message",
                "Category", "Confidence", "Priority"
            ])

        writer.writerow([
            user_id,
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            message,
            category,
            confidence,
            priority
        ])


def get_user_history(user_id):
    if not os.path.isfile(FILE_NAME):
        return []

    history = []
    with open(FILE_NAME, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["User ID"] == user_id:
                history.append(row)

    return history
