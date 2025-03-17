from rest_framework import serializers
from .models import Post, PostMedia, Reaction, Comment, Hashtag, SavedPost, SharedPost, SharedPostComment, SharedPostReaction
from accounts.serializers import UserSerializer

class PostMediaSerializer(serializers.ModelSerializer):
    """
    Serializes media files with URLs:
    - Generates absolute URLs for media files
    - Includes thumbnail versions for images
    """

    media_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = PostMedia
        fields = ['id', 'media_url', 'media_type', 'thumbnail_url', 'order_index', 'created_at']

    def get_media_url(self, obj):
        """Returns full URL for media file"""

        if obj.media_file:
            url = obj.media_file.url
            # print(f"MEdia URL: {url}")
            return url
        return None
    
    def get_thumbnail_url(self, obj):
        """Returns thumbnail URL for images"""

        if obj.thumbnail_file:
            thumbnailurl = obj.thumbnail_file.url
            # print(thumbnailurl)
            return thumbnailurl
        return None

class ReactionSerializer(serializers.ModelSerializer):
    """
    Serializes reactions with user details
    """

    user = UserSerializer(read_only=True)

    class Meta:
        model = Reaction
        fields = ['id', 'post', 'user', 'type', 'created_at']

class CommentSerializer(serializers.ModelSerializer):
    """
    Hierarchical comment serializer:
    - Nested replies implementation
    - Hidden comment filtering
    """

    user = serializers.ReadOnlyField(source='user.id')
    parent = serializers.PrimaryKeyRelatedField(queryset=Comment.objects.all(), required=False, allow_null=True)
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ['id', 'post', 'user', 'content', 'is_hidden', 'created_at', 'updated_at', 'parent', 'replies']

    def get_replies(self, obj):
        """Recursive serialization of nested replies"""

        replies = obj.replies.filter(is_hidden=False)
        serializer = CommentSerializer(replies, many=True, context=self.context)
        return serializer.data
    


class HashtagSerializer(serializers.ModelSerializer):
    """
    Serializes hashtags with usage statistics
    """

    posts_count = serializers.IntegerField(source='posts.count', read_only=True)
    posts = serializers.SerializerMethodField()

    class Meta:
        model = Hashtag
        fields = ['id', 'name', 'posts_count', 'posts']

    def get_posts(self, obj):
        posts_qs = obj.posts.all().order_by('-created_at')[:3]
        return PostWithoutHashtag(posts_qs, many=True, context=self.context).data

class PostSerializer(serializers.ModelSerializer):
    """
    Main post serializer with nested relationships:
    - Handles media uploads
    - Manages hashtag creation
    - Includes engagement metrics
    """

    medias = PostMediaSerializer(many=True, read_only=True, source="media")

    hashtags = serializers.ListField(
        child=serializers.CharField(max_length=100),
        write_only=True,
        required=False
    )
    hashtags_display = HashtagSerializer(source='hashtags', many=True, read_only=True)
    # media = serializers.SerializerMethodField()
    user = serializers.ReadOnlyField(source='user.id')
    comments = CommentSerializer(many=True, read_only=True)
    reactions = ReactionSerializer(many=True, read_only=True)

    # Engagement metrics
    comments_count = serializers.IntegerField(source='comments.count', read_only=True)
    reactions_count = serializers.IntegerField(source='reactions.count', read_only=True)

    class Meta:
        model = Post
        fields = ['id', 'user', 'content', 'group', 'visibility', 'medias', 'created_at', 'updated_at', 'comments', 'reactions', 'comments_count', 'reactions_count', 'hashtags', 'hashtags_display']

    def create(self, validated_data):
        """Handles hashtag creation during post creation"""

        hashtag_data = validated_data.pop('hashtags', [])
        post = Post.objects.create(**validated_data)
        for tag in hashtag_data:
            hashtag, created = Hashtag.objects.get_or_create(name=tag.lower())
            hashtag.posts.add(post)
        return post
    
class PostWithoutHashtag(PostSerializer):
    class Meta(PostSerializer.Meta):
        fields = [field for field in PostSerializer.Meta.fields if field not in ['hashtags', 'hashtags_display']]
    
class SharedPostReactionSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    shared_post = serializers.PrimaryKeyRelatedField(queryset=SharedPost.objects.all(), write_only=True)

    class Meta:
        model = SharedPostReaction
        fields = ['id', 'user', 'shared_post', 'type', 'created_at']

class SharedPostCommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    shared_post = serializers.PrimaryKeyRelatedField(queryset=SharedPost.objects.all(), write_only=True)

    class Meta:
        model = SharedPostComment
        fields = ['id', 'user', 'content', 'shared_post', 'created_at', 'updated_at']


class SharedPostSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    original_post = PostSerializer(read_only=True)
    reactions = SharedPostReactionSerializer(many=True, read_only=True)
    comments = SharedPostCommentSerializer(many=True, read_only=True)

    comments_count = serializers.IntegerField(source='comments.count', read_only=True)
    reactions_count = serializers.IntegerField(source='reactions.count', read_only=True)

    class Meta:
        model = SharedPost
        fields = ['id', 'user', 'original_post', 'share_text', 'reactions', 'comments', 'reactions_count', 'comments_count', 'created_at']

class SavedPostSerializer(serializers.ModelSerializer):
    """
    Serializes saved posts with full post details
    """

    post = PostSerializer(read_only=True)

    class Meta:
        model = SavedPost
        fields = ['id', 'post', 'saved_at']