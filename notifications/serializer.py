from rest_framework import serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    """
    Serializes notification data for API responses:
    - Exposes read status and timestamps
    - Formats message content
    """

    class Meta:
        model = Notification
        fields = ['id', 'user', 'type', 'reference_id', 'message', 'is_read', 'created_at']