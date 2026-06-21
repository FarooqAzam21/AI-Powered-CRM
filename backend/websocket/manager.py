from collections import defaultdict


class WebSocketManager:
    def __init__(self):
        self.connections = defaultdict(set)

    async def connect(self, user_id, websocket):
        await websocket.accept()
        self.connections[str(user_id)].add(websocket)

    def disconnect(self, user_id, websocket):
        self.connections[str(user_id)].discard(websocket)

    async def send(self, user_id, event: dict):
        dead = []
        for websocket in self.connections.get(str(user_id), set()):
            try:
                await websocket.send_json(event)
            except Exception:
                dead.append(websocket)
        for websocket in dead:
            self.disconnect(user_id, websocket)


manager = WebSocketManager()
