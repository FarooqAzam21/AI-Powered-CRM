from fastapi import APIRouter

message_router = APIRouter(prefix="/messages", tags=["Messages"])

@message_router.get("/agent/{agent_name}")
def get_agent_messages(agent_name: str):
    # read messages.csv
    return {"messages": []}

@message_router.post("/reply")
def agent_reply(ticket_id: str, message: str):
    # save to messages.csv
    return {"status": "sent"}
