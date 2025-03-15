from django.urls import path
from .views import NotificationListView, MarkNotificationReadView

# Notifications Application URL Configuration
# Handles notification retrieval and status updates
urlpatterns = [
    # ============== Notification Retrieval ================
    path('', NotificationListView.as_view(), name='notifications'),
    # GET: Lists user's notifications (paginated)

    # ============== Notification Updates ==================
    path('<int:notification_id>/read/', MarkNotificationReadView.as_view(), name='mark-notification-read'),
    # PUT: Marks specific notification as read
]

# URL Pattern Notes:
# 1. WebSocket endpoint requires JWT authentication
# 2. Notifications are user-specific and isolated by account
# 3. Read status can only be modified by notification owner
# 4. Real-time updates via WebSocket connections
# 5. Notification history persists until manually cleared
# 6. Reference ID links to related content (posts, comments, etc)