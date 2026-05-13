def check_priority(message):
    urgent_keywords = [
        "urgent", "immediately", "asap", "not working",
        "system down", "failed", "error", "complaint"
    ]

    message_lower = message.lower()

    for word in urgent_keywords:
        if word in message_lower:
            return "High 🔴"

    return "Normal 🟡"
