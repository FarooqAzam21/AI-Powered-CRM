def generate_title(history, current_message, category):
    if history:
        return f"Follow-up: {category}"
    else:
        return f"New Issue: {category}"
