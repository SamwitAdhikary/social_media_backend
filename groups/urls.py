from django.urls import path
from .views import GroupListCreateView, JoinGroupView, ApproveJoinRequestView, GroupMembersView, GroupDetailView, GroupSearchView

urlpatterns = [
    path('', GroupListCreateView.as_view(), name='group-list-create'),
    path('<int:pk>/', GroupDetailView.as_view(), name='group-detail'),
    path('<int:group_id>/join/', JoinGroupView.as_view(), name='join-group'),
    path('membership/<int:membership_id>/approve/', ApproveJoinRequestView.as_view(), name='approve-join-request'),
    path('<int:group_id>/members/', GroupMembersView.as_view(), name='group-members'),
    path('search/', GroupSearchView.as_view(), name='group-search'),
]