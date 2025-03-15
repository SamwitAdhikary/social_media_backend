from django.db import models
from django.utils import timezone
from accounts.models import User

# Create your models here.
class Connection(models.Model):
    """
    Represents relationships between users (friendships/followers)

    Attributes:
        - STATUS_CHOICES: Possible states of a connection request
        - TYPE_CHOICES: Types of connections (friends/followers)
        - requester: User initiating the connection
        - target: User receiving the request
        - status: Current state of the connection
        - connection_type: Type of relationship
        - created_at: Timestamp of creation
        - updated_at: Last update timestamp
    """

    STATUS_CHOICES = [
        ('pending', 'Pending'),     # Request waiting for response
        ('accepted', 'Accepted'),   # Request approved
        ('declined', 'Declined'),   # Request rejected
    ]

    TYPE_CHOICES = [
        ('friend', 'Friend'),       # Mutual relationship
        ('follower', 'Follower'),   # One-way following
    ]

    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_requests')
    target = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_requests')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    connection_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)