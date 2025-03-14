from rest_framework import serializers

from posts.serializers import PostSerializer
from .models import Group, GroupMembership
from accounts.serializers import UserSerializer


class GroupDetailSerializer(serializers.ModelSerializer):
    members_count = serializers.SerializerMethodField()
    created_by = UserSerializer(read_only=True)
    members = serializers.SerializerMethodField()
    posts= serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = ['id', 'created_by', 'name', 'description', 'cover_photo_url',
                  'privacy', 'created_at', 'updated_at', 'members_count', 'members', 'posts']

    def get_members_count(self, obj):
        return GroupMembership.objects.filter(group=obj, status='approved').count()

    def get_members(self, obj):
        memberships = GroupMembership.objects.filter(group=obj, status='approved').select_related('user')
        return GroupMembershipSerializer(memberships, many=True).data
    
    def get_posts(self, obj):
        from posts.models import Post
        posts = Post.objects.filter(group=obj).order_by('-created_at')
        return PostSerializer(posts, many=True).data


class GroupMembershipSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = GroupMembership
        fields = ['id', 'group', 'user', 'role', 'status', 'joined_at']
