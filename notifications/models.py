from django.db import models
from django.utils import timezone
from accounts.models import User

# Create your models here.

class Notification(models.Model):
    """
    Stores user notifications with:
    - Type-specific handling (likes, comments, etc)
    - Read/unread status tracking
    - Reference to related objects
    """

    NOTIFICATION_TYPES = [
        ('friend_request', 'Friend Request'),
        ('like', 'Like'),
        ('comment', 'Comment'),
        ('reaction', 'Reaction'),
        ('tag', 'Tag'),
        ('group_invite', 'Group Invite'),
        ('group_update', 'Group Update'),
        ('follower_activity', 'Follower Activity'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    reference_id = models.IntegerField(null=True, blank=True)
    message = models.TextField(blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)