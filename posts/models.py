from django.db import models
from django.utils import timezone
from accounts.models import User
from groups.models import Group

# Create your models here.
class Post(models.Model):
    """
    Core content model for user-generated posts:
    - Supports text content with media attachments
    - Configurable visibility settings
    - Group association for community posts
    """

    VISIBILITY_CHOICES = [
        ('public', 'Public'),               # Visibile to all users
        ('friends', 'Friends/Followers'),   # Visible to connections
        ('private', 'Only Me'),             # Visible only to post owner
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    content = models.TextField()  # Main post text
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='posts', null=True, blank=True)  # Associated group
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='public')  # Privacy settings
    created_at = models.DateTimeField(default=timezone.now)  # Creation timestamp
    updated_at = models.DateTimeField(auto_now=True)  # Last edit time

    # Metrics fields
    view_count = models.PositiveIntegerField(default=0)
    click_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-created_at']  # Default chronological order

class PostMedia(models.Model):
    """
    Stores media files associated with posts:
    - Supports images and videos
    - Maintains display order and thumbnails
    """

    MEDIA_TYPE_CHOICES = [
        ('image', 'Image'),     # Support image formats
        ('video', 'Video'),     # Support video formats
    ]

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='media')
    media_file = models.FileField(upload_to='post_media/', null=True, blank=True)
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES)
    thumbnail_file = models.FileField(upload_to='post_media/thumbnails/',blank=True)
    order_index = models.IntegerField(default=0)  # Display order in post
    created_at = models.DateTimeField(default=timezone.now)

class Reaction(models.Model):
    """
    Tracks user reactions to posts:
    - Predefined reaction types
    - Prevents duplicate reactions
    """

    REACTION_CHOICES = [
        ('like', 'Like'),
        ('love', 'Love'),
        ('haha', 'Haha'),
        ('sad', 'Sad'),
    ]

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    type = models.CharField(max_length=20, choices=REACTION_CHOICES)
    created_at = models.DateTimeField(default=timezone.now)

class Comment(models.Model):
    """
    Hierarchical comment system:
    - Supports nested replies
    - Moderation capabilities
    - Edit history tracking
    """

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    parent = models.ForeignKey('self', null=True, blank=True, related_name='replies', on_delete=models.CASCADE)
    is_hidden = models.BooleanField(default=False)
    content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

class Hashtag(models.Model):
    """
    Categorization system for posts:
    - Auto-generated from post content
    - Case-insensitive unique names
    """

    name = models.CharField(max_length=100, unique=True)
    posts = models.ManyToManyField(Post, related_name='hashtags', blank=True)

    def __str__(self):
        return self.name
    

class SavedPost(models.Model):
    """
    Bookmarking system for users:
    - Unique user-post combinations
    - Access control based on post visibility
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_post')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='saved_by_users')
    saved_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('user', 'post')

    def __str__(self):
        return f"{self.user.username} saved Post #{self.post.id}"
    
class SharedPost(models.Model):
    """
    Represents a shared (reposted) post.
    - user: The user who is sharing the post.
    - original_post: The post being shared.
    - share_text: Optional text/comment added by the sharing user.
    - created_at: Timestamp when the share was created
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shared_posts')
    original_post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='shared_by')
    parent_share = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='child_shares')
    share_text = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} shared Post #{self.original_post.id}"

class SharedPostReaction(models.Model):
    """
    Represents a reaction (like, love, etc.) on a shared post.
    """

    REACTION_CHOICES = [
        ('like', 'Like'),
        ('love', 'Love'),
        ('haha', 'Haha'),
        ('sad', 'Sad'),
    ]

    shared_post = models.ForeignKey(SharedPost, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    type = models.CharField(max_length=20, choices=REACTION_CHOICES)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.username} reacted {self.type} on shared post {self.shared_post.id}"

class SharedPostComment(models.Model):
    """
    Represents a comment on a shared post
    """

    shared_post = models.ForeignKey(SharedPost, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Comment by {self.user.username} on shared post {self.shared_post.id}"
    
class CommentReaction(models.Model):
    REACTION_CHOICES = [
        ('like', 'Like'),
        ('love', 'Love'),
        ('haha', 'Haha'),
        ('sad', 'Sad'),
    ]

    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    type = models.CharField(max_length=20, choices=REACTION_CHOICES)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.username} reacted {self.type} on Comment #{self.comment.id}"

class SharedPostCommentReaction(models.Model):
    REACTION_CHOICES = [
        ('like', 'Like'),
        ('love', 'Love'),
        ('haha', 'Haha'),
        ('sad', 'Sad'),
    ]

    shared_post_comment = models.ForeignKey(SharedPostComment, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    type = models.CharField(max_length=20, choices=REACTION_CHOICES)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.username} reacted {self.type} on SharedPostComment #{self.shared_post_comment.id}"