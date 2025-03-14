import json
from channels.generic.websocket import AsyncWebsocketConsumer

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")

        if user is None or user.is_anonymous:
            await self.close()
        else:
            self.group_name = f"notifications_{user.id}"

            if self.channel_layer is None:
                print("Channel layer is not configured properly")

            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
            print(f"{user.username} connected to {self.group_name}")

    async def disconnect(self, close_code):
        user = self.scope.get("user")
        if user and not user.is_anonymous:
            print(f"{user.username} disconnected from {self.group_name}")
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        pass

    async def send_notification(self, event):
        notification = event.get("notification", {})
        user = self.scope['user']
        print(f"Sending notification to {user.username}: {notification}")
        await self.send(text_data=json.dumps(notification))