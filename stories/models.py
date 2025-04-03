from django.db import models
from django.utils import timezone
from django.conf import settings
from accounts.models import User

# Create your models here.
class Story(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="stories")
    media_files = models.FileField(upload_to='stories/', null=True, blank=True)
    thumbnail_file = models.FileField(upload_to='stories/thumbnails/', null=True, blank=True)
    content = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(hours=24)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Story by {self.user.username} at {self.created_at}"
    
class StoryView(models.Model):
    """
    Tracks which users have viewed a story.
    Each user can only count once per story.
    """

    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='views')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    seen_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('story', 'user')

    def __str__(self):
        return f"{self.user.username} viewed story {self.story.id}"

class StoryReaction(models.Model):
    """
    Stores reactions for a story.
    For now, we allow only 'love' reaction.
    """

    REACTION_CHOICES = [
        ('love', 'Love'),
    ]

    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    type = models.CharField(max_length=20, choices=REACTION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('story', 'user')

    def __str__(self):
        return f"{self.user.username} reacted {self.type} on Story {self.story.id}"