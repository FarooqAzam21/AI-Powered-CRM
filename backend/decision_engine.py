def decide_action(category, confidence):
    """
    Decides the next step based on Category and Confidence.
    Returns: (Action, Reason)
    Actions: REPLY_IMMEDIATELY, DRAFT_RESPONSE, ARCHIVE, ESCALATE
    """
    
    # 1. SPAM FILTER
    if category == "Sales/Spam":
        if confidence > 0.60:
            return "ARCHIVE", "Classified as Spam."
        else:
            return "ESCALATE", "Potential Spam, needs human review."

    # 2. HIGH CONFIDENCE -> AUTO REPLY
    if confidence > 0.85:
        if category in ["General Inquiry", "Meeting Request"]:
            return "REPLY_IMMEDIATELY", f"High confidence ({confidence}) for standard request."

    # 3. CRITICAL/SENSITIVE -> DRAFT ONLY
    if category in ["Urgent Support", "Job Application"]:
        return "DRAFT_RESPONSE", f"Sensitive category ({category}) requires human approval."

    # 4. LOW CONFIDENCE -> ESCALATE
    if confidence < 0.50:
        return "ESCALATE", f"Low confidence ({confidence}). Unsure of intent."

    # Default fallback
    return "DRAFT_RESPONSE", f"Standard procedure for {category}."
