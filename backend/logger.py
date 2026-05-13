import csv
import os

FILE = "tickets.csv"

HEADERS = [
    "TicketID",
    "Timestamp",
    "Title",
    "Message",
    "Category",
    "Confidence",
    "Priority",
    "Agent",
    "ResponseTime",
    "SLA_Breached",
    "Escalated"
]

def log_ticket(row):
    file_exists = os.path.isfile(FILE)

    with open(FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow(HEADERS)

        writer.writerow(row)
