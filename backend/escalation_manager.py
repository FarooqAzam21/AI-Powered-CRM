def escalate_ticket(priority, sla_breached):
    if sla_breached or priority == "High":
        return {
            "escalated": True,
            "new_priority": "Critical",
            "escalation_level": "Manager"
        }

    return {
        "escalated": False,
        "new_priority": priority,
        "escalation_level": None
    }
