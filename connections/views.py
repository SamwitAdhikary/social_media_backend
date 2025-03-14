from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from accounts.serializers import UserSerializer
from .serializers import ConnectionSerializer
from .models import Connection
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions
from django.db import models
from accounts.models import BlockedUser, User
from rest_framework.pagination import PageNumberPagination

# Create your views here.
class ConnectionRequestView(APIView):
    def post(self, request):
        serializer = ConnectionSerializer(
            data={'requester': request.user.id, **request.data})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'message': 'Request sent'}, status=status.HTTP_200_OK)


class ConnectionResponseView(APIView):
    def post(self, request):
        connection_id = request.data.get('connection_id')
        status_val = request.data.get('status')
        connection = get_object_or_404(Connection, id=connection_id)
        connection.status = status_val
        connection.save()
        return Response({'message': 'Connection updated.'}, status=status.HTTP_200_OK)


class ReceivedRequestsView(generics.ListAPIView):
    serializer_class = ConnectionSerializer

    def get_queryset(self):
        return Connection.objects.filter(target=self.request.user, status='pending')


class SentRequestsView(generics.ListAPIView):
    serializer_class = ConnectionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        status_filter = self.request.query_params.get('status', None)
        queryset = Connection.objects.filter(requester=self.request.user)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset


class FriendListView(generics.ListAPIView):
    serializer_class = ConnectionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        return Connection.objects.filter(connection_type='friend', status='accepted').filter(models.Q(requester=user) | models.Q(target=user))


class FollowUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        target_id = request.data.get('target_id')
        if not target_id:
            return Response({"error": "Target user id is required."}, status=status.HTTP_400_BAD_REQUEST)

        target = get_object_or_404(User, id=target_id)

        if request.user == target:
            return Response({"error": "You cannot follow yourself."}, status=status.HTTP_400_BAD_REQUEST)

        if BlockedUser.objects.filter(blocker=request.user, blocked=target).exists():
            return Response({"error": "You cannot follow this user because you have blocked them."}, status=status.HTTP_403_FORBIDDEN)
        
        if BlockedUser.objects.filter(blocker=target, blocked=request.user).exists():
            return Response({"error": "You cannot follow this user because they have blocked you."}, status=status.HTTP_403_FORBIDDEN)

        if Connection.objects.filter(
            models.Q(requester=request.user, target=target, connection_type='friend', status='accepted') |
            models.Q(requester=target, target=request.user, connection_type='friend', status='accepted')
        ).exists():
            return Response({"error": "You are already friends with this user. Following is not required"}, status=status.HTTP_400_BAD_REQUEST)

        if Connection.objects.filter(
            requester=request.user,
            target=target,
            connection_type='follower'
        ).exists():
            return Response({"error": "You already follow this user."}, status=status.HTTP_400_BAD_REQUEST)

        Connection.objects.create(
            requester=request.user,
            target=target,
            connection_type='follower',
            status='accepted'
        )

        return Response({"message": "You are now following this user."}, status=status.HTTP_201_CREATED)


class UnfollowUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        target_id = request.data.get("target_id")
        if not target_id:
            return Response({"error": "Target user id is required."}, status=status.HTTP_400_BAD_REQUEST)

        target = get_object_or_404(User, id=target_id)

        if request.user == target:
            return Response({"error": "You cannot unfollow yourself"}, status=status.HTTP_403_FORBIDDEN)
        
        if Connection.objects.filter(
            models.Q(requester=request.user, target=target, connection_type='friend', status='accepted') |
            models.Q(requester=target, target=request.user, connection_type='friend', status='accepted')
        ).exists():
            return Response({"error": "You are friends with this user. Unfollowing is not required."}, status=status.HTTP_403_FORBIDDEN)

        if BlockedUser.objects.filter(blocker=request.user, blocked=target).exists():
            return Response({"error": "You cannot unfollow this user because you have blocked them."}, status=status.HTTP_403_FORBIDDEN)

        if BlockedUser.objects.filter(blocker=target, blocked=request.user).exists():
            return Response({"error": "You cannot unfollow this user because they have blocked you."}, status=status.HTTP_403_FORBIDDEN)

        follow_relation = Connection.objects.filter(
            requester=request.user,
            target=target,
            connection_type='follower'
        )

        if not follow_relation.exists():
            return Response({"error": "You are not following this user"}, status=status.HTTP_404_NOT_FOUND)

        follow_relation.delete()
        return Response({"message": "You have unfollowed the user successfully."}, status=status.HTTP_200_OK)


class UserPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50


class FollowersListView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = UserPagination

    def get_queryset(self):
        user = self.request.user
        follower_ids = Connection.objects.filter(
            target=user,
            connection_type='follower',
            status='accepted'
        ).values_list('requester', flat=True)
        return User.objects.filter(id__in=follower_ids)


class FollowingListView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = UserPagination

    def get_queryset(self):
        user = self.request.user

        following_ids = Connection.objects.filter(
            requester=user,
            connection_type='follower',
            status='accepted'
        ).values_list('target', flat=True)
        return User.objects.filter(id__in=following_ids)
