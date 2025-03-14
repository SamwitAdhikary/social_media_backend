from rest_framework import serializers
from .models import Story

class StorySerializer(serializers.ModelSerializer):
    media_url = serializers.SerializerMethodField()

    class Meta:
        model = Story
        fields = ['id', 'user', 'media_files', 'thumbnail_file', 'media_url', 'content', 'created_at', 'expires_at']
        read_only_fields = ['user', 'created_at', 'expires_at']

    def get_media_url(self, obj):
        if obj.media_files and hasattr(obj.media_files, 'url'):
            request = self.context.get('request')
            return request.build_absolute_uri(obj.media_files.url) if request else obj.media_files.url
        return None