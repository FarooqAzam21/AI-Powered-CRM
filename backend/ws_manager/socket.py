"""
WebSocket Connection Manager - Phase 8
Handles real-time connections, subscriptions, and broadcasting
"""
import logging
import json
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class DashboardSubscription:
    """Represents a user's dashboard subscriptions"""
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.channels: Set[str] = set()  # deals, territories, analytics, forecast
        self.subscribed_deals: Set[int] = set()  # Specific deal IDs
        self.subscribed_territories: Set[str] = set()  # Territory names
        self.connected_at = datetime.utcnow()

class ConnectionManager:
    """Advanced WebSocket connection manager with subscriptions"""
    
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}  # user_id -> websocket
        self.subscriptions: Dict[int, DashboardSubscription] = {}  # user_id -> subscription
        self.channel_subscribers: Dict[str, Set[int]] = {  # channel -> user_ids
            "deals": set(),
            "territories": set(),
            "analytics": set(),
            "forecast": set(),
            "activities": set()
        }
        logger.info("✅ WebSocket Connection Manager initialized")

    async def connect(self, user_id: int, websocket: WebSocket):
        """Accept and register new WebSocket connection"""
        try:
            await websocket.accept()
            self.active_connections[user_id] = websocket
            self.subscriptions[user_id] = DashboardSubscription(user_id)
            logger.info(f"🔗 User {user_id} connected")
        except Exception as e:
            logger.error(f"❌ Connection error: {e}")

    def disconnect(self, user_id: int):
        """Remove disconnected user"""
        try:
            self.active_connections.pop(user_id, None)
            
            # Remove from all channels
            subscription = self.subscriptions.pop(user_id, None)
            if subscription:
                for channel in subscription.channels:
                    self.channel_subscribers.get(channel, set()).discard(user_id)
            
            logger.info(f"🔓 User {user_id} disconnected")
        except Exception as e:
            logger.error(f"❌ Disconnection error: {e}")

    async def subscribe(self, user_id: int, channel: str, 
                       deal_ids: List[int] = None, territories: List[str] = None):
        """Subscribe user to a channel"""
        try:
            if user_id not in self.subscriptions:
                return False
            
            subscription = self.subscriptions[user_id]
            subscription.channels.add(channel)
            
            if channel in self.channel_subscribers:
                self.channel_subscribers[channel].add(user_id)
            
            # Track specific subscriptions
            if deal_ids:
                subscription.subscribed_deals.update(deal_ids)
            if territories:
                subscription.subscribed_territories.update(territories)
            
            logger.info(f"✅ User {user_id} subscribed to {channel}")
            return True
        except Exception as e:
            logger.error(f"❌ Subscription error: {e}")
            return False

    async def unsubscribe(self, user_id: int, channel: str):
        """Unsubscribe user from channel"""
        try:
            if user_id not in self.subscriptions:
                return False
            
            subscription = self.subscriptions[user_id]
            subscription.channels.discard(channel)
            
            if channel in self.channel_subscribers:
                self.channel_subscribers[channel].discard(user_id)
            
            logger.info(f"✅ User {user_id} unsubscribed from {channel}")
            return True
        except Exception as e:
            logger.error(f"❌ Unsubscribe error: {e}")
            return False

    async def send_personal_message(self, user_id: int, data: Dict[str, Any]):
        """Send JSON message to specific user"""
        try:
            websocket = self.active_connections.get(user_id)
            if websocket:
                await websocket.send_json(data)
                logger.debug(f"📤 Message sent to user {user_id}")
            else:
                logger.warning(f"⚠️  User {user_id} not connected")
        except Exception as e:
            logger.error(f"❌ Send error: {e}")
            self.disconnect(user_id)

    async def broadcast_to_channel(self, channel: str, data: Dict[str, Any]):
        """Broadcast message to all subscribers of a channel"""
        try:
            subscriber_ids = self.channel_subscribers.get(channel, set())
            logger.debug(f"📢 Broadcasting to {channel}: {len(subscriber_ids)} subscribers")
            
            for user_id in subscriber_ids:
                try:
                    await self.send_personal_message(user_id, data)
                except Exception as e:
                    logger.error(f"❌ Broadcast error for user {user_id}: {e}")
                    self.disconnect(user_id)
        except Exception as e:
            logger.error(f"❌ Broadcast error: {e}")

    async def broadcast_to_specific_users(self, user_ids: List[int], data: Dict[str, Any]):
        """Broadcast to specific users"""
        try:
            logger.debug(f"📢 Broadcasting to {len(user_ids)} users")
            for user_id in user_ids:
                try:
                    await self.send_personal_message(user_id, data)
                except Exception as e:
                    logger.error(f"❌ Send error: {e}")
                    self.disconnect(user_id)
        except Exception as e:
            logger.error(f"❌ Broadcast error: {e}")

    async def broadcast_deal_update(self, deal_id: int, update_data: Dict[str, Any]):
        """Broadcast deal update to interested subscribers"""
        try:
            # Find users subscribed to this deal
            interested_users = []
            for user_id, subscription in self.subscriptions.items():
                if deal_id in subscription.subscribed_deals or "deals" in subscription.channels:
                    interested_users.append(user_id)
            
            message = {
                "type": "deal_update",
                "deal_id": deal_id,
                "timestamp": datetime.utcnow().isoformat(),
                "data": update_data
            }
            
            await self.broadcast_to_specific_users(interested_users, message)
        except Exception as e:
            logger.error(f"❌ Deal broadcast error: {e}")

    async def broadcast_territory_update(self, territory_name: str, update_data: Dict[str, Any]):
        """Broadcast territory update to interested subscribers"""
        try:
            # Find users subscribed to this territory
            interested_users = []
            for user_id, subscription in self.subscriptions.items():
                if territory_name in subscription.subscribed_territories or "territories" in subscription.channels:
                    interested_users.append(user_id)
            
            message = {
                "type": "territory_update",
                "territory": territory_name,
                "timestamp": datetime.utcnow().isoformat(),
                "data": update_data
            }
            
            await self.broadcast_to_specific_users(interested_users, message)
        except Exception as e:
            logger.error(f"❌ Territory broadcast error: {e}")

    async def broadcast_metric_update(self, metric_type: str, user_id: int, 
                                     update_data: Dict[str, Any]):
        """Broadcast analytics metric update"""
        try:
            message = {
                "type": f"{metric_type}_update",
                "metric_type": metric_type,
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat(),
                "data": update_data
            }
            
            # Broadcast to users monitoring analytics
            interested_users = [
                uid for uid, sub in self.subscriptions.items()
                if "analytics" in sub.channels
            ]
            
            await self.broadcast_to_specific_users(interested_users, message)
        except Exception as e:
            logger.error(f"❌ Metric broadcast error: {e}")

    def get_active_connections_count(self) -> int:
        """Get number of active connections"""
        return len(self.active_connections)

    def get_channel_subscriber_count(self, channel: str) -> int:
        """Get number of subscribers to a channel"""
        return len(self.channel_subscribers.get(channel, set()))

    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return {
            "active_connections": self.get_active_connections_count(),
            "channels": {
                channel: self.get_channel_subscriber_count(channel)
                for channel in self.channel_subscribers
            },
            "timestamp": datetime.utcnow().isoformat()
        }

# Global manager instance
manager = ConnectionManager()