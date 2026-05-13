import uuid
import datetime

def generate_ticket():
    ticket_id = f"CS-{uuid.uuid4().hex[:6].upper()}"
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return ticket_id, timestamp
