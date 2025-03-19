from django.urls import path
from .views import CommentReactionView, PostClickView, PostCreateView, FeedView, PostDetailView, PostEngagementView, ReactionView, CommentView, HashtagSearchView, SharePostView, SharedPostCommentReactionView, SharedPostCommentView, SharedPostReactionView, ToggleCommentVisibilityView, SavePostView, UnsavePostView, SavedPostListView, PostDeleteView, UserPostListView, TopFanView, UserSharedPostsView

# Posts Application URL Configuration
# Handles content creation, interaction, and discovery
urlpatterns = [
    # ============== Post Management ================
    path('', PostCreateView.as_view(), name='post-create'),
    # POST: Create new post

    path('<int:pk>/delete/', PostDeleteView.as_view(), name='post_delete'),
    # DELETE: Remove post

    # ============== Content Feed ===================
    path('feed/', FeedView.as_view(), name='feed'),
    # GET: Personalized post feed

    path('<int:post_id>/react/', ReactionView.as_view(), name='post-react'),
    # POST: Add reaction

    path('<int:post_id>/comment/', CommentView.as_view(), name='post-comment'),
    # POST: Add comment

    path('comments/<int:comment_id>/toggle-visibility/', ToggleCommentVisibilityView.as_view(), name='toggle-comment-visibility'),
    # PATCH: Moderate comment

    # ============== Saved Posts ====================
    path('<int:post_id>/save/', SavePostView.as_view(), name='save_post'),
    # POST: Bookmark post

    path('<int:post_id>/unsave/', UnsavePostView.as_view(), name='unsave_post'),
    # DELETE: Remove bookmark

    path('saved-posts/', SavedPostListView.as_view(), name='get_saved_posts'),
    # GET: List saved posts

    # ============== Discovery ======================
    path('hashtag/search/', HashtagSearchView.as_view(), name='hashtag-search'),
    # GET: Search hashtags

    path('user/<str:username>/posts/', UserPostListView.as_view(), name='user-post'),
    # GET: User's posts

    path('<int:post_id>/top-fan/', TopFanView.as_view(), name='top-fan'),

    path('<int:post_id>/share/', SharePostView.as_view(), name='share-post'),

    path('user/<int:user_id>/shared/', UserSharedPostsView.as_view(), name='user-shared-posts'),

    path('shared/<int:shared_post_id>/comment/', SharedPostCommentView.as_view(), name='shared-post-comment'),

    path('shared/<int:shared_post_id>/react/', SharedPostReactionView.as_view(), name='shared-post-react'),

    path('comment/<int:comment_id>/react/', CommentReactionView.as_view(), name='comment-react'),

    path('shared-comment/<int:shared_comment_id>/react/', SharedPostCommentReactionView.as_view(), name='shared-comment-react'),

    path('<int:pk>/', PostDetailView.as_view(), name='post-detail-view'),

    path('<int:pk>/click/', PostClickView.as_view(), name='post-click'),

    path('<int:post_id>/engagement/', PostEngagementView.as_view(), name='post-engagement'),
]

# URL Pattern Notes:
# 1. Authentication required for all endpoints
# 2. Content visibility enforced at query level
# 3. Media uploads use S3-compatible storage
# 4. Real-time notifications for interactions
# 5. Hierarchical comment system with moderation
# 6. Saved posts respect original content privacy