from django.urls import re_path
from notifications.consumers import NotificationConsumer

# WebSocket routing configuration
websocket_urlpatterns = [
    re_path(r'^ws/notifications/$', NotificationConsumer.as_asgi()),
]