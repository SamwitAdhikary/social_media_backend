from django.urls import path
from .views import PostCreateView, FeedView, ReactionView, CommentView, HashtagSearchView, ToggleCommentVisibilityView, SavePostView, UnsavePostView, SavedPostListView

urlpatterns = [
    path('', PostCreateView.as_view(), name='post-create'),
    path('feed/', FeedView.as_view(), name='feed'),
    path('<int:post_id>/react/', ReactionView.as_view(), name='post-react'),
    path('<int:post_id>/comment/', CommentView.as_view(), name='post-comment'),
    path('hashtag/search/', HashtagSearchView.as_view(), name='hashtag-search'),
    path('comments/<int:comment_id>/toggle-visibility/', ToggleCommentVisibilityView.as_view(), name='toggle-comment-visibility'),
    path('<int:post_id>/save/', SavePostView.as_view(), name='save_post'),
    path('<int:post_id>/unsave/', UnsavePostView.as_view(), name='unsave_post'),
    path('saved-posts/', SavedPostListView.as_view(), name='get_saved_posts'),
]