from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializer import NotificationSerializer
from .models import Notification
from django.shortcuts import get_object_or_404

# Create your views here.


class NotificationListView(generics.ListAPIView):
    """
    Lists authenticated user's notifications:
    - Ordered by creation date (newest first)
    - Includes pagination
    - Filters out read notifications
    """

    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')


class MarkNotificationReadView(APIView):
    """
    Updates notification read status:
    - Requires notification ownership
    - Marks single notification as read
    """

    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, notification_id):
        notification = get_object_or_404(
            Notification, id=notification_id, user=request.user)
        notification.is_read = True
        notification.save()
        return Response({"message": "Notification marked as read."}, status=status.HTTP_200_OK)


class MarkAllNotificationsReadView(APIView):
    """
    Mark all notification for the authentication user as read
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        notifications = Notification.objects.filter(
            user=request.user, is_read=False)
        count = notifications.update(is_read=True)
        return Response({"message": f"Marked {count} notifications as read."},status=status.HTTP_200_OK)

class MarkAllNotificationsUnreadView(APIView):
    """
    Mark all notifications for the authenticated user as unread
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        notifications = Notification.objects.filter(user=request.user, is_read=True)
        count = notifications.update(is_read=False)
        return Response({"message": f"Marked {count} notifications as unread."}, status=status.HTTP_200_OK)