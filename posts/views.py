import io
from django.forms import ValidationError
from rest_framework import generics, status, permissions, filters
from channels.layers import get_channel_layer
from django.shortcuts import get_object_or_404
from PIL import Image
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import NotFound
from rest_framework.pagination import PageNumberPagination
from accounts.models import BlockedUser, User
from .serializers import PostSerializer, ReactionSerializer, CommentSerializer, HashtagSerializer, SavedPostSerializer
from .models import Post, Hashtag, PostMedia, SavedPost
from django.utils import timezone
from django.db.models import Q, Count, Case, When, Value, F, IntegerField
from posts.models import Comment
from notifications.models import Notification
from connections.models import Connection
from django.core.files.storage import default_storage
from rest_framework.parsers import MultiPartParser, FormParser
from asgiref.sync import async_to_sync
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
import logging
from storages.backends.s3boto3 import S3Boto3Storage

logger = logging.getLogger(__name__)

# Create your views here.
class PostCreateView(generics.CreateAPIView):
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def perform_create(self, serializer):
        media_files = self.request.FILES.getlist('media_files')
        post = serializer.save(user=self.request.user)

        s3_storage = S3Boto3Storage(bucket_name=settings.AWS_STORAGE_BUCKET_NAME)

        for file in media_files:
            media_type = 'image' if file.name.lower().endswith(("jpg", "jpeg", 'png', "gif")) else "video"

            try:
                file_content = ContentFile(file.read())
                file_path = s3_storage.save(f"post_media/{file.name}", file_content)
                s3_url = s3_storage.url(file_path)
                logger.info(f"Manually saved file to S3: {s3_url}")

                media = PostMedia.objects.create(
                    post=post,
                    media_type=media_type
                )

                media.media_file.name = file_path
                media.save()

                if media_type == 'image':
                    file.seek(0)
                    try:
                        image = Image.open(file)
                        image.thumbnail((200, 200))
                        thumb_io = io.BytesIO()
                        image_format = image.format if image.format else 'JPEG'
                        image.save(thumb_io, format=image_format)
                        thumb_file = ContentFile(thumb_io.getvalue(), name=f"thumb_{file.name}")

                        thumb_path = s3_storage.save(f"post_media/thumbnails/{thumb_file.name}", thumb_file)
                        media.thumbnail_file.name = thumb_path
                        media.save()
                        logger.info(f"Thumbnail saved to S3: {s3_storage.url(thumb_path)}")
                    except Exception as e:
                        logger.error(f"Error generating thumbnail for {file.name}: {e}")

            except Exception as e:
                logger.error(f"Error uploading file {file.name}: {e}")

class FeedView(generics.ListAPIView):
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):

        user = self.request.user

        friends_requester = Connection.objects.filter(requester=user, status__in='accepted', connection_type='friend').values_list('target', flat=True)

        friends_target = Connection.objects.filter(target=user, status='accepted', connection_type='friend').values_list('requester', flat=True)

        friends_ids = list(set(list(friends_requester) + list(friends_target)))

        base_qs = Post.objects.prefetch_related(
            'comments', 'reactions', 'comments__user', 'reactions__user'
        ).filter(
            Q(visibility='public') |
            Q(user=user) |
            Q(user__in=friends_ids, visibility='friends')
        )

        blocked_users = BlockedUser.objects.filter(blocker=user).values_list('blocked', flat=True)

        users_who_blocked_me = BlockedUser.objects.filter(blocked=user).values_list('blocker', flat=True)

        base_qs = base_qs.exclude(user__in=blocked_users).exclude(user__in=users_who_blocked_me)

        sort_param = self.request.query_params.get('sort', 'chronological')

        if sort_param == 'relevant':
            qs = base_qs.annotate(
                comment_count=Count('comments'),
                reaction_count=Count('reactions'),
                friend_bonus=Case(
                    When(user__in=friends_ids, then=Value(50)),
                    default=Value(0),
                    output_field=IntegerField()
                )
            )

            qs = qs.annotate(
                ranking=F('friend_bonus') + F("comment_count") * 2 + F('reaction_count')
            ).order_by('-ranking', '-created_at')

            return qs
        else:
            return base_qs.order_by("-created_at")
    
class ReactionView(APIView):
    def post(self, request, post_id):
        serializer = ReactionSerializer(data={'post': post_id, **request.data})
        serializer.is_valid(raise_exception=True)
        reaction = serializer.save(user=request.user)

        if reaction.post.user != request.user:
            notification = Notification.objects.create(
                user = reaction.post.user,
                type = 'reaction',
                reference_id=reaction.post.id,
                message=f"{request.user.username} reacted on your post."
            )
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"notifications_{notification.user.id}",
                {
                    "type": "send_notification",
                    "notification": {
                        "id": notification.id,
                        "type": notification.type,
                        "message": notification.message,
                    }
                }
            )

        return Response({'message': 'Reaction recorder'}, status=status.HTTP_200_OK)

class CommentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, post_id):
        data = {'post': post_id, **request.data}
        serializer = CommentSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            comment = serializer.save(user=request.user)
            notification = None
            if comment.parent and comment.parent.user != request.user:
                notification = Notification.objects.create(
                    user=comment.parent.user,
                    type='reply',
                    reference_id=comment.parent.id,
                    message=f"{request.user.username} replied to your comment."
                )
            elif comment.post.user != request.user:
                notification = Notification.objects.create(
                    user=comment.post.user,
                    type='comment',
                    reference_id=comment.post.id,
                    message=f"{request.user.username} commented on your post."
                )
            
            if notification:
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f"notifications_{notification.user.id}",
                    {
                        "type": "send_notification",
                        "notification": {
                            "id": notification.id,
                            "type": notification.type,
                            "message": notification.message
                        }
                    }
                )

            return Response({"message": "Comment added.", "comment": CommentSerializer(comment).data}, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, post_id):
        post_owner = request.user
        comments = Comment.objects.filter(post_id=post_id, parent=None).order_by('-created_at')

        if not request.user.is_authenticated or post_owner != request.user:
            comments = comments.filter(is_hidden=False)
        
        serializer = CommentSerializer(comments, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class HashtagPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50

class HashtagSearchView(generics.ListAPIView):
    serializer_class = HashtagSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = HashtagPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']

    def get_queryset(self):
        query = self.request.query_params.get('search', '')
        return Hashtag.objects.filter(name__icontains=query).distinct()
    
class ToggleCommentVisibilityView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, comment_id):
        comment = get_object_or_404(Comment, id=comment_id)
        if comment.post.user != request.user:
            return Response({"error": "You do not have permission to hide/unhide this comment."}, status=status.HTTP_403_FORBIDDEN)

        comment.is_hidden = not comment.is_hidden
        comment.save()
        return Response({
            "message": f"Comment {'hidden' if comment.is_hidden else 'unhidden'} successfully.",
            "is_hidden": comment.is_hidden
        }, status=status.HTTP_200_OK)
    
class PostDeleteView(generics.DestroyAPIView):
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Post.objects.filter(user=self.request.user)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({
            "message": "Post deleted successfully."
        }, status=status.HTTP_200_OK)

class UserPostListView(generics.ListAPIView):
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        username = self.kwargs.get("username")
        try:
            viewed_user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise NotFound("User Not Found.")

        blocked_by_user = set(BlockedUser.objects.filter(blocker=self.request.user).values_list('blocked', flat=True))
        blocked_by_others = set(BlockedUser.objects.filter(blocked=self.request.user).values_list('blocker', flat=True))
        if viewed_user.id in blocked_by_user or viewed_user.id in blocked_by_others:
            raise NotFound("This profile is not available")
        
        privacy = 'public'

        if viewed_user.profile.privacy_settings:
            privacy = viewed_user.profile.privacy_settings.get("profile_visibility", "public")

        if privacy == "public":
            return Post.objects.filter(user=viewed_user, visibility='public').order_by('-created_at')

        is_friend = Connection.objects.filter(
            Q(requester=self.request.user, target=viewed_user) |
            Q(requester=viewed_user, target=self.request.user),
            status='accepted',
            connection_type='friend'
        ).exists()

        is_follower = Connection.objects.filter(
            requester=self.request.user,
            target=viewed_user,
            status='accepted',
            connection_type='follower'
        ).exists()

        if is_friend or is_follower:
            return Post.objects.filter(user=viewed_user).filter(
                Q(visibility='public') | Q(visibility='friends')
            ).order_by('-created_at')
        else:
            return Post.objects.filter(user=viewed_user, visibility='public').order_by('-created_at')
    
class SavePostView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, post_id):
        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            return Response({"error": "Post not found."}, status=status.HTTP_404_NOT_FOUND)
        
        blocked_users = BlockedUser.objects.filter(blocker=request.user).values_list('blocked', flat=True)
        users_who_blocked_me = BlockedUser.objects.filter(blocked=request.user).values_list('blocker', flat=True)

        if post.user.id in list(blocked_users) or post.user.id in list(users_who_blocked_me):
            return Response({"error": "You cannot save a post from a blocked user."}, status=status.HTTP_403_FORBIDDEN)

        if post.visibility == 'private' and post.user != request.user:
            return Response({"error": "You cannot save a private post."}, status=status.HTTP_403_FORBIDDEN)

        saved_post, created = SavedPost.objects.get_or_create(user=request.user, post=post)
        if created:
            return Response({"message": "Post saved successfully."}, status=status.HTTP_201_CREATED)
        else:
            return Response({"message": "Post already saved."}, status=status.HTTP_200_OK)

class UnsavePostView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, post_id):
        try:
            saved_post = SavedPost.objects.get(user=request.user, post_id=post_id)
            saved_post.delete()
            return Response({"message": "Post unsaved successfully"}, status=status.HTTP_200_OK)
        except SavedPost.DoesNotExist:
            return Response({"error": "Post is not saved."}, status=status.HTTP_404_NOT_FOUND)

class SavedPostListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SavedPostSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = SavedPost.objects.filter(user=user).select_related('post', 'post__user')
        blocked_by_user = BlockedUser.objects.filter(blocker=user).values_list('blocked', flat=True)
        blocked_by_others = BlockedUser.objects.filter(blocked=user).values_list('blocker', flat=True)
        queryset = queryset.exclude(post__user__in=list(blocked_by_user) + list(blocked_by_others))
        return queryset