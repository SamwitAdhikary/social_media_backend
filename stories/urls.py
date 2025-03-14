from django.urls import path
from .views import CreateStoryView, ListStoryView

urlpatterns = [
    path('create/', CreateStoryView.as_view(), name='story-create'),
    path('list/', ListStoryView.as_view(), name='story-list'),
]