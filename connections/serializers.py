from rest_framework import serializers
from django.utils import timezone
from accounts.serializers import UserSerializer
from .models import Connection


class ConnectionSerializer(serializers.ModelSerializer):
    """
    Serializes Connection model data for API responses
    Handles conversion between model instance and JSON
    """

    requester_details = serializers.SerializerMethodField()

    class Meta:
        model = Connection
        fields = ['id', 'requester_details', 'requester', 'target',
                  'status', 'connection_type', 'created_at', 'updated_at']

    def get_requester_details(self, obj):
        """
        Returns the sender's details for a friend request:
        - If the request is accepted, show full details.
        - If pending and sender's profile is private:
            * If less than 7 days old, return full details.
            * Otherwise, return limited details (username and profile picture).
        - Otherwise, return full details.
        """
        context = self.context.copy()
        context['force_full'] = True
        full_details = UserSerializer(obj.requester, context=context).data
        
        if obj.status == "pending":
            days_elapsed = (timezone.now() - obj.created_at).days
            days_remaining = max(7 - days_elapsed, 0)
        else:
            days_remaining = None

        # Get the sender's privacy settings from their profile (default to 'public')
        privacy = obj.requester.profile.privacy_settings.get(
            "profile_visibility", "public")

        # If the friend request has been accepted, always return full details.
        if obj.status == "accepted":
            full_details["details_visible_for"] = None
            return full_details

        # For pending requests from private accounts, check the time elapsed.
        if obj.status == "pending":
            if privacy == "private":
                if days_elapsed < 7:
                    full_details["details_visible_for"] = days_remaining
                    return full_details
                else:
                    return {
                        "id": obj.requester.id,
                        "username": obj.requester.username,
                        "profile_picture_url": obj.requester.profile.profile_picture_url,
                        "details_visible_for": days_remaining
                    }
            else:
                full_details["details_visible_for"] = days_remaining
        
        return full_details
