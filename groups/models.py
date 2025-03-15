from django.db import models
from django.utils import timezone
from accounts.models import User

# Create your models here.
class Group(models.Model):
    """
    Represents user-created groups with configuratble privacy settings

    Attributes:
    - PRIVACY_CHOICES: Visibility levels for group content
    - created_by: Group owner/creator
    - name: Group display name
    - privacy: Controls who can find/join the group
    - memberships: Relationship to GroupMembership model
    """

    PRIVACY_CHOICES = [
        ('public', 'Public'),   # Visible to all, open joining
        ('private', 'Private'), # Visible but requires approval
        ('secret', 'Secret'),   # Hidden from searches
    ]

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_groups')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    cover_photo_url = models.URLField(blank=True)
    privacy = models.CharField(max_length=20, choices=PRIVACY_CHOICES, default='public')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

class GroupMembership(models.Model):
    """
    Tracks user participation in groups with:
    - Membership status (pending/approved/rejected)
    - User roles (member/admin/moderator)
    - Join timestamps
    """

    ROLE_CHOICES = [
        ('member', 'Member'),           # Awaiting Approval
        ('admin', 'Admin'),             # Active member
        ('moderator', 'Moderator'),     # Denied membership
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    joined_at = models.DateTimeField(default=timezone.now)