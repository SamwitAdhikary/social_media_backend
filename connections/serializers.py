from rest_framework import serializers
from .models import Connection

class ConnectionSerializer(serializers.ModelSerializer):
    """
    Serializes Connection model data for API responses
    Handles conversion between model instance and JSON
    """

    class Meta:
        model = Connection
        fields = ['id', 'requester', 'target', 'status', 'connection_type', 'created_at', 'updated_at']