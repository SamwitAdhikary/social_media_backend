from django.contrib import admin
from django.urls import path, include
from social_network.custom_admin import custom_admin_site
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', custom_admin_site.urls),
    path('admin/dashboard/', custom_admin_site.admin_view(custom_admin_site.dashboard_view), name='admin_dashboard'),
    path('api/accounts/', include('accounts.urls')),
    path('api/posts/', include('posts.urls')),
    path('api/connections/', include('connections.urls')),
    path('api/groups/', include('groups.urls')),
    path('api/notifications/', include('notifications.urls')),
    path('api/stories/', include('stories.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)