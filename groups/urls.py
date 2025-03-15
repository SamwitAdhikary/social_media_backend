from django.urls import path
from .views import GroupListCreateView, JoinGroupView, ApproveJoinRequestView, GroupMembersView, GroupDetailView, GroupSearchView

# Group Application URL Configuration
# Handles group creation, mamberships, and content management
urlpatterns = [
    # ==================== Group CRUD Operations ====================
    path('', GroupListCreateView.as_view(), name='group-list-create'),
    # GET: List public/private groups (excluding secret groups)
    # POST: Creates new group (requires authentication)

    path('<int:pk>/', GroupDetailView.as_view(), name='group-detail'),
    # GET: Retrieves group details with members and posts

    # ==================== Men=mbership Management ====================
    path('<int:group_id>/join/', JoinGroupView.as_view(), name='join-group'),
    # POST: Request to join group (auto-approve for public groups)

    path('membership/<int:membership_id>/approve/', ApproveJoinRequestView.as_view(), name='approve-join-request'),
    # POST: Approve pending join request (group admin only)

    # ==================== Group Content ====================
    path('<int:group_id>/members/', GroupMembersView.as_view(), name='group-members'),
    # GET: List approved members with roles (paginated)

    # ==================== Discovery ====================
    path('search/', GroupSearchView.as_view(), name='group-search'),
    # GET: Search groups by name/description (excludes secret groups)
]

# URL Pattern Notes:
# 1. All endpoints require authentication except public group listings
# 2. Secret groups don't appear in search/list results
# 3. Membership approval requires admin privileges
# 4. Pagination applied to members list and search results
# 5. POST endpoints return detailed membership status
# 6. Group privacy affects join process:
#    - Public: Instant join
#    - Private: Requires approval
#    - Secret: Invite-only