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