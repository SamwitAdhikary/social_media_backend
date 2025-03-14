from django.contrib.admin import AdminSite
from django.contrib import admin
from django.db.models import Count
from django.utils.translation import gettext_lazy as _
from django.urls import path
from django.shortcuts import render
from django.contrib.auth import get_user_model
from posts.models import Post, Comment, Reaction, PostMedia, Hashtag
from notifications.models import Notification
from accounts.models import User, Profile
from datetime import timedelta
from django.utils.timezone import now
from groups.models import Group, GroupMembership

class CustomAdminSite(AdminSite):
    site_header = "Social Network Admin"
    site_title = "Social Network Admin Portal"
    index_title = "Welcome to Social Network Admin"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('dashboard/', self.admin_view(self.dashboard_view), name="admin-dashboard"),
        ]
        return custom_urls + urls
    
    def dashboard_view(self, request):
        last_7_days = now() - timedelta(days=7)

        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        new_user_last_week = User.objects.filter(date_joined__gte=last_7_days).count()

        total_posts = Post.objects.count()
        top_posts = Post.objects.annotate(like_count=Count('reactions')).order_by('-like_count')[:5]

        total_comments = Comment.objects.count()
        most_commented_posts = Post.objects.annotate(comment_count=Count('comments')).order_by('-comment_count')[:5]

        total_groups = Group.objects.count()
        new_group_last_week = Group.objects.filter(created_at__gte=last_7_days).count()
        pending_requests = GroupMembership.objects.filter(status="pending").count()

        context = {
            "total_users": total_users,
            "active_users": active_users,
            "new_users_last_week": new_user_last_week,
            "total_posts": total_posts,
            "top_posts": top_posts,
            "total_comments": total_comments,
            "most_commented_posts": most_commented_posts,
            "total_groups": total_groups,
            "new_groups_last_week": new_group_last_week,
            "pending_requests": pending_requests,
        }

        return render(request, "admin/custom_dashboard.html", context)
    
custom_admin_site = CustomAdminSite(name="custom_admin")

custom_admin_site.register(User)
custom_admin_site.register(Profile)
custom_admin_site.register(Post)
custom_admin_site.register(PostMedia)
custom_admin_site.register(Comment)
custom_admin_site.register(Reaction)
custom_admin_site.register(Hashtag)
custom_admin_site.register(Group)
custom_admin_site.register(GroupMembership)
custom_admin_site.register(Notification)