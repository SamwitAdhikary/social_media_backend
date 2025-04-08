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
    is_seen = serializers.SerializerMethodField()
    react = serializers.SerializerMethodField()

    viewers_list = serializers.SerializerMethodField()
    reactors_list = serializers.SerializerMethodField()

    class Meta:
        model = Story
        fields = ['id', 'user', 'media_files', 'thumbnail_file',
                  'media_url', 'content', 'created_at', 'expires_at', 'seen_count', 'reaction_count', 'is_seen', 'react', 'viewers_list', 'reactors_list']
        
        read_only_fields = ['user', 'created_at', 'expires_at', 'seen_count', 'reaction_count', 'is_seen', 'react', 'viewers_list', 'reactors_list']

    def get_media_url(self, obj):
        if obj.media_files and hasattr(obj.media_files, 'url'):
            request = self.context.get('request')
            return request.build_absolute_uri(obj.media_files.url) if request else obj.media_files.url
        return None

    def get_seen_count(self, obj):
        return obj.views.count()
    
    def get_reaction_count(self, obj):
        return obj.reactions.count()
    
    def get_is_seen(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.views.filter(user=request.user).exists()
        return False
    
    def get_react(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            reaction = obj.reactions.filter(user=request.user).first()
            return reaction.type if reaction else None
        return None
    
    def get_viewers_list(self, obj):
        """
        Returns a list of viewers (id and username) only if the request user is owner.
        """

        request = self.context.get("request")
        if request and request.user == obj.user:
            viewers = obj.views.all().select_related('user')
            return [{'id': view.user.id, 'username': view.user.username} for view in viewers]
        return None

    def get_reactors_list(self, obj):
        """
        Returns a list of reactors (id, username, reaction type) only if the request user is the owner.
        """

        request = self.context.get('request')
        if request and request.user == obj.user:
            reactions = obj.reactions.all().select_related('user')
            return [{'id': react.user.id, 'username': react.user.username, 'reaction': react.type} for react in reactions]
        return None