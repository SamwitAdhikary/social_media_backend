from rest_framework import serializers

from posts.serializers import PostSerializer
from .models import Group, GroupMembership
from accounts.serializers import UserSerializer


class GroupDetailSerializer(serializers.ModelSerializer):
    """
    Serializes group details with:
    - Member count
    - Full member list
    - Recent posts
    - Creator information
    """

    members_count = serializers.SerializerMethodField()
    created_by = UserSerializer(read_only=True)
    members = serializers.SerializerMethodField()
    posts= serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = ['id', 'created_by', 'name', 'description', 'cover_photo_url',
                  'privacy', 'created_at', 'updated_at', 'members_count', 'members', 'posts']

    def get_members_count(self, obj):
        """Returns count of approved members"""

        return GroupMembership.objects.filter(group=obj, status='approved').count()

    def get_members(self, obj):
        """Serializes approved members with their roles"""

        memberships = GroupMembership.objects.filter(group=obj, status='approved').select_related('user')
        return GroupMembershipSerializer(memberships, many=True).data
    
    def get_posts(self, obj):
        """List group posts in chronological order"""

        from posts.models import Post
        posts = Post.objects.filter(group=obj).order_by('-created_at')
        return PostSerializer(posts, many=True).data


class GroupMembershipSerializer(serializers.ModelSerializer):
    """
    Serializes membership details:
    - User information
    - Role/status in group
    - Join timestamp
    """

    user = UserSerializer(read_only=True)

    class Meta:
        model = GroupMembership
        fields = ['id', 'group', 'user', 'role', 'status', 'joined_at']
