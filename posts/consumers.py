import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser

class PostConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        print(f"User connecting: {self.scope['user']}")
        self.user = self.scope['user']
        if self.user.is_anonymous:
            print("Rejected anonymous user")
            await self.close()
        else:
            self.group_name = f'posts_{self.user.id}'
            print(f"Adding to group: {self.group_name}")
            await self.channel_layer.group_add(self.group_name, self.channel_name)

            await self.channel_layer.group_add("public_posts", self.channel_name)
            await self.accept()

    async def disconnet(self, close_code):
        if not self.user.is_anonymous:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        await self.close()

    async def new_post(self, event):
        await self.send(text_data=json.dumps({'type': 'new_post', 'post': event['post']}))