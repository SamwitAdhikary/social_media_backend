from django.urls import path
from .views import ConnectionRequestView, ConnectionResponseView, ReceivedRequestsView, SentRequestsView, FriendListView, FollowUserView, UnfollowUserView, FollowingListView, FollowersListView

# Connections Application URL Configuration
# Handles social relationships and networking features
urlpatterns = [
    # ================ Connection Requests ====================
    path('request/', ConnectionRequestView.as_view(), name='connection-request'),
    # POST: Sends friend/follow request to another user

    path('respond/', ConnectionResponseView.as_view(), name='connection-response'),
    # POST: Accepts/declines incoming connection requests

    # ================ Request Management =====================
    path('received/', ReceivedRequestsView.as_view(), name='received-requests'),
    # GET: List pending requests received by current user

    path('sent/', SentRequestsView.as_view(), name='sent-requests'),
    # GET: List requests sent by current user (filterable by status)

    # ================ Friendship System ======================
    path('friends/', FriendListView.as_view(), name='friends-list'),
    # GET: List all accepted mutual friendships

    # ================ Following System =======================
    path('follow/', FollowUserView.as_view(), name='follow-user'),
    # POST: Establishes one-way following relationship

    path('unfollow/', UnfollowUserView.as_view(), name='unfollow-user'),
    # POST: Removes existing following relationship

    # ================ Relationship Listings ==================
    path('followers/', FollowersListView.as_view(), name='followers-list'),
    # GET: Paginated list of users following current user

    path('following/', FollowingListView.as_view(), name="following-list")
    # GET: Paginated list of users current user is following
]

# URL Pattern Notes:
# 1. All endpoints require authentication
# 2. Relationship operations check for blocking status
# 3. Follow system is separate from friendship system
# 4. Pagination applied to large result sets
# 5. Friend relationships require mutual acceptance
# 6. Following relationships are one-directional