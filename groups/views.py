from rest_framework import generics, permissions, status, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied
from accounts.models import User
from accounts.serializers import UserSerializer
from posts.models import Comment, Post, Reaction
from posts.serializers import PostSerializer
from .serializers import GroupDetailSerializer, GroupMembershipSerializer
from .models import Group, GroupMembership
from django.db.models import Q
from rest_framework.pagination import PageNumberPagination


# Create your views here.
class GroupListCreateView(generics.CreateAPIView):
    """
    Handles group creation:
    - Requires authentication
    - Automatically sets creator
    - Validates group data
    """
    
    serializer_class = GroupDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Group.objects.all()

    def perform_create(self, serializer):
        """Associates group with creating user"""

        serializer.save(created_by=self.request.user)


class GroupDetailView(generics.RetrieveAPIView):
    """
    Provides group detail view:
    - Includes members, posts, and metadata
    - Respects group privacy settings
    """

    queryset = Group.objects.all()
    serializer_class = GroupDetailSerializer
    permission_classes = [permissions.IsAuthenticated]


class JoinGroupView(APIView):
    """
    Handles group joining logic:
    - Public groups: Auto-approve
    - Private/Secret: Require approval
    - Prevents duplicate memberships
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, group_id):
        user = request.user
        group = get_object_or_404(Group, id=group_id)

        if GroupMembership.objects.filter(group=group, user=user).exists():
            return Response({"detail": "You are already a member of this group."}, status=status.HTTP_400_BAD_REQUEST)

        # Public group handling
        if group.privacy == 'public':
            membership = GroupMembership.objects.create(
                group=group, user=user, status='approved', role='member'
            )
            serializer = GroupMembershipSerializer(membership)
            return Response({"detail": "Joined group successfully.", "membership": serializer.data}, status=status.HTTP_201_CREATED)

        # Private/Secret group handling
        elif group.privacy in ['private', 'secret']:
            membership = GroupMembership.objects.create(
                group=group, user=user, status='pending', role='member'
            )
            serializer = GroupMembershipSerializer(membership)
            return Response({"detail": "Join request sent. Awaiting admin approval.", "membership": serializer.data}, status=status.HTTP_202_ACCEPTED)

        return Response({"detail": "Invalid group privacy type."}, status=status.HTTP_400_BAD_REQUEST)


class ApproveJoinRequestView(APIView):
    """
    Admin-only endpoint for:
    - Approving pending join requests
    - Validates admin privileges
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, membership_id):
        membership = get_object_or_404(GroupMembership, id=membership_id)

        # Authorization check
        if request.user != membership.group.created_by:
            return Response({"detail": "You are not authorized to approve requests."}, status=status.HTTP_403_FORBIDDEN)

        membership.status = "approved"
        membership.save()
        return Response({'detail': 'Join request approved.'}, status=status.HTTP_200_OK)


class GroupMembersView(generics.ListAPIView):
    """
    Lists approved group members:
    - Paginated results
    - Includes member roles
    """

    serializer_class = GroupMembershipSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        group_id = self.kwargs['group_id']
        return GroupMembership.objects.filter(group_id=group_id, status="approved")


class GroupPagination(PageNumberPagination):
    """
    Custom pagination settings for group listings
    """

    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50

class GroupSearchView(generics.ListAPIView):
    """
    Group search functionality:
    - Search by name/description
    - Respects privacy settings
    - Paginated results
    """

    serializer_class = GroupDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = GroupPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'description']

    def get_queryset(self):
        """Filters groups based on search query and privacy"""

        query = self.request.query_params.get('search', '')
        return Group.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        ).distinct()
    
class MostActiveMemberView(APIView):
    """
    Calculates the most active member in a group based on:
    - Number of posts in the group
    - Number of comments made on posts in the group
    - Number of reactions on posts in the group

    Only approved group members are considered.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, group_id):
        # Get the group or 404
        group = get_object_or_404(Group, id=group_id)

        # Ensure the requesting user is an approved member of the group.
        if not group.memberships.filter(user=request.user, status='approved').exists():
            return Response({"error": "You are not a member of this group."}, status=status.HTTP_403_FORBIDDEN)

        memberships = group.memberships.filter(status='approved')
        if not memberships.exists():
            return Response({"message": "No members in this group."}, status=status.HTTP_404_NOT_FOUND)

        activity = {}

        for membership in memberships:
            member_id = membership.user_id
            posts_count = Post.objects.filter(group=group, user_id=member_id).count()
            comments_count = Comment.objects.filter(post__group=group, user_id=member_id).count()
            reactions_count = Reaction.objects.filter(post__group=group, user_id=member_id).count()
            total_activity = posts_count + comments_count + reactions_count
            activity[member_id] = total_activity

        if not activity:
            return Response({"message": "No activity data found for this group."}, status=status.HTTP_404_NOT_FOUND)

        most_active_member_id = max(activity, key=activity.get)
        score = activity[most_active_member_id]

        most_active_member = get_object_or_404(User, id=most_active_member_id)
        serializer = UserSerializer(most_active_member, context={'request': request})
        data = serializer.data
        data['activity_score'] = score

        return Response({"group_id": group_id, "most_active_member": data}, status=status.HTTP_200_OK)
    
class GroupPostView(generics.ListAPIView):
    """
    Lists posts for a specific group.
    - If the group's privacy is 'public' returns all posts.
    - If the group's privacy is 'private' or 'secret', only returns posts if the required user is an approved member.
    """

    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        group_id = self.kwargs.get("group_id")
        group = get_object_or_404(Group, id=group_id)

        if group.privacy in ['private', 'secret']:
            if not group.memberships.filter(user=self.request.user, status='approved').exists():
                raise PermissionDenied("You are not a member of this group.")
        
        return Post.objects.filter(group=group).order_by("-created_at")