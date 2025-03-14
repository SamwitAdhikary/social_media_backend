from django.urls import path
from .views import ConnectionRequestView, ConnectionResponseView, ReceivedRequestsView, SentRequestsView, FriendListView, FollowUserView, UnfollowUserView, FollowingListView, FollowersListView

urlpatterns = [
    path('request/', ConnectionRequestView.as_view(), name='connection-request'),
    path('respond/', ConnectionResponseView.as_view(), name='connection-response'),
    path('received/', ReceivedRequestsView.as_view(), name='received-requests'),
    path('sent/', SentRequestsView.as_view(), name='sent-requests'),
    path('friends/', FriendListView.as_view(), name='friends-list'),
    path('follow/', FollowUserView.as_view(), name='follow-user'),
    path('unfollow/', UnfollowUserView.as_view(), name='unfollow-user'),
    path('followers/', FollowersListView.as_view(), name='followers-list'),
    path('following/', FollowingListView.as_view(), name="following-list")
]
