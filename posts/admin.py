from django.contrib import admin
from posts.models import Post, PostMedia, Comment, Reaction, Hashtag

# Register your models here.

class PostMediaInline(admin.TabularInline):
    model = PostMedia
    extra = 1
    readonly_fields = ('media_preview',)

    def media_preview(self, obj):
        if obj.media_file:
            return f'<a href="{obj.media_file.url}" target="_blank">View Media</a>'
        return "No media"

    media_preview.allow_tags = True
    media_preview.short_description = "Preview"

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'content', 'visibility', 'created_at')
    list_filter = ('visibility', 'created_at')
    search_fields = ('user__username', 'content')
    ordering = ('-created_at',)
    inlines = [PostMediaInline]

    def has_add_permission(self, request):
        return request.user.is_staff
    
    def has_change_permission(self, request, obj=None):
        return request.user.is_staff
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

@admin.register(PostMedia)
class PostMediaAdmin(admin.ModelAdmin):
    list_display = ('id', 'post', 'media_type', 'media_preview', 'created_at')
    search_fields = ('post__content',)
    list_filter = ('media_type', 'created_at')

    def media_preview(self, obj):
        if obj.media_file:
            return f'<a href="{obj.media_file.url}" target="_blank">View Media</a>'
        return "No media"

    media_preview.allow_tags = True
    media_preview.short_description = "Preview"

    def has_add_permission(self, request):
        return request.user.is_staff
    
    def has_change_permission(self, request, obj=None):
        return request.user.is_staff
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'post', 'user', 'content', 'created_at')
    search_fields = ('user__username', 'post__content', 'content')
    list_filter = ('created_at',)

    def has_add_permission(self, request):
        return request.user.is_staff
    
    def has_change_permission(self, request, obj=None):
        return request.user.is_staff
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'post', 'user', 'type', 'created_at')
    search_fields = ('user__username',)
    list_filter = ('type', 'created_at')

    def has_add_permission(self, request):
        return request.user.is_staff
    
    def has_change_permission(self, request, obj=None):
        return request.user.is_staff
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

@admin.register(Hashtag)
class HashtagAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'posts_count')
    search_fields = ('name',)

    def posts_count(self, obj):
        return obj.posts.count()
    posts_count.short_description = "Number of Posts"

    def has_add_permission(self, request):
        return request.user.is_staff
    
    def has_change_permission(self, request, obj=None):
        return request.user.is_staff
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser