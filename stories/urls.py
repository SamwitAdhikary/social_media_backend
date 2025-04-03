from django.urls import path
from .views import CreateStoryView, ListStoryView, StoryDeleteView, MarkStorySeenView, StoryReactionView

urlpatterns = [
    path('create/', CreateStoryView.as_view(), name='story-create'),
    path('list/', ListStoryView.as_view(), name='story-list'),
    path('<int:pk>/delete/', StoryDeleteView.as_view(), name='story-delete'),
    path('<int:story_id>/seen/', MarkStorySeenView.as_view(), name='story-mark-seen'),
    path('<int:story_id>/react/', StoryReactionView.as_view(), name='story-react'),
]