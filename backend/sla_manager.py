def check_sla(priority, response_minutes):
    sla_limits = {
        "Low": 30,
        "Medium": 15,
        "High": 5,
        "Critical": 2
    }

    return response_minutes > sla_limits.get(priority, 30)
