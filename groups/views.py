from rest_framework import generics, permissions, status, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .serializers import GroupDetailSerializer, GroupMembershipSerializer
from .models import Group, GroupMembership
from django.db.models import Q
from rest_framework.pagination import PageNumberPagination


# Create your views here.


class GroupListCreateView(generics.CreateAPIView):
    serializer_class = GroupDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Group.objects.all()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class GroupDetailView(generics.RetrieveAPIView):
    queryset = Group.objects.all()
    serializer_class = GroupDetailSerializer
    permission_classes = [permissions.IsAuthenticated]


class JoinGroupView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, group_id):
        user = request.user
        group = get_object_or_404(Group, id=group_id)

        if GroupMembership.objects.filter(group=group, user=user).exists():
            return Response({"detail": "You are already a member of this group."}, status=status.HTTP_400_BAD_REQUEST)

        if group.privacy == 'public':
            membership = GroupMembership.objects.create(
                group=group, user=user, status='approved', role='member'
            )
            serializer = GroupMembershipSerializer(membership)
            return Response({"detail": "Joined group successfully.", "membership": serializer.data}, status=status.HTTP_201_CREATED)

        elif group.privacy in ['private', 'secret']:
            membership = GroupMembership.objects.create(
                group=group, user=user, status='pending', role='member'
            )
            serializer = GroupMembershipSerializer(membership)
            return Response({"detail": "Join request sent. Awaiting admin approval.", "membership": serializer.data}, status=status.HTTP_202_ACCEPTED)

        return Response({"detail": "Invalid group privacy type."}, status=status.HTTP_400_BAD_REQUEST)


class ApproveJoinRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, membership_id):
        membership = get_object_or_404(GroupMembership, id=membership_id)

        if request.user != membership.group.created_by:
            return Response({"detail": "You are not authorized to approve requests."}, status=status.HTTP_403_FORBIDDEN)

        membership.status = "approved"
        membership.save()
        return Response({'detail': 'Join request approved.'}, status=status.HTTP_200_OK)


class GroupMembersView(generics.ListAPIView):
    serializer_class = GroupMembershipSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        group_id = self.kwargs['group_id']
        return GroupMembership.objects.filter(group_id=group_id, status="approved")


class GroupPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50

class GroupSearchView(generics.ListAPIView):
    serializer_class = GroupDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = GroupPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'description']

    def get_queryset(self):
        query = self.request.query_params.get('search', '')
        return Group.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        ).distinct()