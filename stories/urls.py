from django.urls import path
from .views import CreateStoryView, ListStoryView, StoryDeleteView

urlpatterns = [
    path('create/', CreateStoryView.as_view(), name='story-create'),
    path('list/', ListStoryView.as_view(), name='story-list'),
    path('<int:pk>/delete/', StoryDeleteView.as_view(), name='story-delete'),
]