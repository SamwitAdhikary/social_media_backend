from rest_framework import serializers
from .models import Post, PostMedia, Reaction, Comment, Hashtag, SavedPost
from accounts.serializers import UserSerializer

class PostMediaSerializer(serializers.ModelSerializer):
    media_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = PostMedia
        fields = ['id', 'media_url', 'media_type', 'thumbnail_url', 'order_index', 'created_at']

    def get_media_url(self, obj):
        if obj.media_file:
            url = obj.media_file.url
            # print(f"MEdia URL: {url}")
            return url
        return None
    
    def get_thumbnail_url(self, obj):
        if obj.thumbnail_file:
            thumbnailurl = obj.thumbnail_file.url
            print(thumbnailurl)
            return thumbnailurl
        return None

class ReactionSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Reaction
        fields = ['id', 'post', 'user', 'type', 'created_at']

class CommentSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.id')
    parent = serializers.PrimaryKeyRelatedField(queryset=Comment.objects.all(), required=False, allow_null=True)
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ['id', 'post', 'user', 'content', 'is_hidden', 'created_at', 'updated_at', 'parent', 'replies']

    def get_replies(self, obj):
        replies = obj.replies.filter(is_hidden=False)
        serializer = CommentSerializer(replies, many=True, context=self.context)
        return serializer.data

class HashtagSerializer(serializers.ModelSerializer):
    posts_count = serializers.IntegerField(source='posts.count', read_only=True)

    class Meta:
        model = Hashtag
        fields = ['id', 'name', 'posts_count']

class PostSerializer(serializers.ModelSerializer):
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
    comments_count = serializers.IntegerField(source='comments.count', read_only=True)
    reactions_count = serializers.IntegerField(source='reactions.count', read_only=True)

    class Meta:
        model = Post
        fields = ['id', 'user', 'content', 'visibility', 'medias', 'created_at', 'updated_at', 'comments', 'reactions', 'comments_count', 'reactions_count', 'hashtags', 'hashtags_display']

    def create(self, validated_data):
        hashtag_data = validated_data.pop('hashtags', [])
        post = Post.objects.create(**validated_data)
        for tag in hashtag_data:
            hashtag, created = Hashtag.objects.get_or_create(name=tag.lower())
            hashtag.posts.add(post)
        return post
    
class SavedPostSerializer(serializers.ModelSerializer):
    post = PostSerializer(read_only=True)

    class Meta:
        model = SavedPost
        fields = ['id', 'post', 'saved_at']