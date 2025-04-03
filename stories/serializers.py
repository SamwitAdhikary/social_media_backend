from rest_framework import serializers
from .models import Story, StoryReaction

class StoryReactionSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = StoryReaction
        fields = ['id', 'story', 'user', 'type', 'created_at']

class StorySerializer(serializers.ModelSerializer):
    media_url = serializers.SerializerMethodField()
    seen_count = serializers.SerializerMethodField()
    reaction_count = serializers.SerializerMethodField()

    class Meta:
        model = Story
        fields = ['id', 'user', 'media_files', 'thumbnail_file',
                  'media_url', 'content', 'created_at', 'expires_at', 'seen_count', 'reaction_count',]
        read_only_fields = ['user', 'created_at', 'expires_at', 'seen_count', 'reaction_count']

    def get_media_url(self, obj):
        if obj.media_files and hasattr(obj.media_files, 'url'):
            request = self.context.get('request')
            return request.build_absolute_uri(obj.media_files.url) if request else obj.media_files.url
        return None

    def get_seen_count(self, obj):
        return obj.views.count()
    
    def get_reaction_count(self, obj):
        return obj.reactions.count()