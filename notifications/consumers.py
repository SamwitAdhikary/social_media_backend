import json
from channels.generic.websocket import AsyncWebsocketConsumer

class NotificationConsumer(AsyncWebsocketConsumer):
    """
    Handles real-time notifications via WebSocket:
    - Creates user-specific channel groups
    - Authenticates via JWT
    - Broadcasts notifications to connected clients
    """

    async def connect(self):
        """Authenticates user and joins notification channel group"""

        user = self.scope.get("user")

        if user is None or user.is_anonymous:
            await self.close()
        else:
            self.group_name = f"notifications_{user.id}"

            if self.channel_layer is None:
                print("Channel layer is not configured properly")

            # Add connection to user's notification group
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
            print(f"{user.username} connected to {self.group_name}")

    async def disconnect(self, close_code):
        """Cleans up channel group on disconnect"""

        user = self.scope.get("user")
        if user and not user.is_anonymous:
            print(f"{user.username} disconnected from {self.group_name}")
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        pass

    async def send_notification(self, event):
        """Broadcasts notification to all group members"""

        notification = event.get("notification", {})
        user = self.scope['user']
        print(f"Sending notification to {user.username}: {notification}")
        await self.send(text_data=json.dumps(notification))