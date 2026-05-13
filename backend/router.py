from fastapi import APIRouter
from auto_assign import assign_agent
from priority_checker import predict_priority
from responder import bot_reply

ticket_router = APIRouter(prefix="/tickets", tags=["Tickets"])

@ticket_router.post("/create")
def create_ticket(message: str, user_id: str):
    priority = predict_priority(message)
    agent = assign_agent(priority)
    reply, confidence = bot_reply(message)

    return {
        "ticket_id": "TKT-001",
        "agent": agent,
        "bot_reply": reply,
        "confidence": confidence
    }
