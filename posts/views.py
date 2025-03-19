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
from accounts.serializers import UserSerializer
from .serializers import CommentReactionSerializer, PostSerializer, ReactionSerializer, CommentSerializer, HashtagSerializer, SavedPostSerializer, SharedPostCommentReactionSerializer, SharedPostCommentSerializer, SharedPostReactionSerializer, SharedPostSerializer
from .models import CommentReaction, Post, Hashtag, PostMedia, Reaction, SavedPost, SharedPost, SharedPostComment, SharedPostCommentReaction, SharedPostReaction
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
    """
    Handles post creation with media uploads:
    - Processes multiple media files
    - Generates thumbnails for images
    - Stores files in S3-compatible storage
    """

    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def perform_create(self, serializer):
        """Processes and uploads media files to cloud storage"""

        media_files = self.request.FILES.getlist('media_files')
        post = serializer.save(user=self.request.user)

        s3_storage = S3Boto3Storage(bucket_name=settings.AWS_STORAGE_BUCKET_NAME)

        for file in media_files:
            # Media processing logic
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

class FeedView(APIView):
    """
    Personalized post feed:
    - Combines privacy settings and social connections
    - Multiple sorting algorithms
    - Blocked content filtering
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user

        # Retrieve friend IDs for filtering posts.
        friends_requester = Connection.objects.filter(
            requester=user, status='accepted', connection_type='friend'
        ).values_list('target', flat=True)

        friends_target = Connection.objects.filter(
            target=user, status='accepted', connection_type="friend"
        ).values_list('requester', flat=True)

        friends_ids = list(set(list(friends_requester) + list(friends_target)))

        # Retrieve blocked user IDs.
        blocked_users = list(BlockedUser.objects.filter(blocker=user).values_list('blocked', flat=True))

        users_who_blocked_me = list(BlockedUser.objects.filter(blocked=user).values_list('blocker', flat=True))

        # Retrieve regular post with filtering
        posts_qs = Post.objects.prefetch_related(
            'comments', 'reactions', 'comments__user', 'reactions__user'
        ).filter(
            Q(visibility='public') |
            Q(user=user) |
            Q(user__in=friends_ids, visibility='friends')
        ).exclude(
            Q(user__in=blocked_users) | Q(user__in=users_who_blocked_me)
        )

        # Apply sorting if requested
        sort_param = request.query_params.get('sort', 'chronological')
        if sort_param == 'relevant':
            posts_qs = posts_qs.annotate(
                comment_count = Count('comments'),
                reaction_counts = Count('reactions'),
                friend_bonus = Case(
                    When(user__in=friends_ids, then=Value(50)),
                    default=Value(0),
                    output_field=IntegerField()
                )
            ).annotate(
                ranking=F('friend_bonus') + F('comment_count') * 2 + F("reaction_count")
            ).order_by('-ranking', '-created_at')
        else:
            posts_qs = posts_qs.order_by('-created_at')

        posts_data = PostSerializer(posts_qs, many=True, context={'request': request}).data
        for post in posts_data:
            post['item_type'] = 'post'

        # Retrieve shared posts.
        shared_qs = SharedPost.objects.select_related('user', 'original_post').all().order_by('-created_at')

        # Exclude shared posts if the sharer or the original post's user is blocked
        shared_qs = shared_qs.exclude(
            Q(user__in=blocked_users) | Q(user__in=users_who_blocked_me) | Q(original_post__user__in=blocked_users) | Q(original_post__user__in=users_who_blocked_me)
        )
        shared_data = SharedPostSerializer(shared_qs, many=True, context={'request': request}).data

        for shared in shared_data:
            shared['item_type'] = 'shared'

        # Merge posts and shared posts, then sort by created_at descending
        combined = posts_data + shared_data
        combined_sorted = sorted(combined, key=lambda x: x['created_at'], reverse=True)

        return Response(combined_sorted, status=status.HTTP_200_OK)
    
class ReactionView(APIView):
    """
    Handles post reactions and notifications

    Behaviour:
    - If the user has not reacted, a new reaction is created.
    - If the user has already reacted with the same type, the reaction is removed (unlike).
    - If the user has already reacted with a different type, the reaction is updated.
    - Real-time notifications are sent to the post owner if the reacting user is different. 
    """
    
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, post_id):
        post = get_object_or_404(Post, id=post_id)

        """Creates reaction and sends real-time notification"""
        reaction_type = request.data.get('type')
        if not reaction_type:
            return Response({"error": "Reaction type is required."}, status=status.HTTP_400_BAD_REQUEST)

        existing_reaction = Reaction.objects.filter(post=post, user=request.user).first()
        if existing_reaction:
            # If existing_reaction is same, remove it (Unlike)
            if existing_reaction.type == reaction_type:
                existing_reaction.delete()
                return Response({"message": "Reaction removed."}, status=status.HTTP_200_OK)
            else:
                existing_reaction.type = reaction_type
                existing_reaction.save()
                serializer = ReactionSerializer(existing_reaction, context={'request': request})

                if post.user != request.user:
                    notification = Notification.objects.create(
                        user = post.user,
                        type = 'reaction',
                        reference_id=post.id,
                        message=f"{request.user.username} updated their reaction on your post."
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
                return Response({"message": "Reaction updated.", "reaction": serializer.data}, status=status.HTTP_200_OK)
        else:
            serializer = ReactionSerializer(data={'post': post_id, **request.data}, context={'request': request})
            serializer.is_valid(raise_exception=True)
            reaction = serializer.save(user=request.user)
            if reaction.post.user != request.user:
                notification = Notification.objects.create(
                        user = post.user,
                        type = 'reaction',
                        reference_id=post.id,
                        message=f"{request.user.username} updated their reaction on your post."
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
    """
    Manages post comments and nested replies
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, post_id):
        """Creates comment and notifies relevant users"""
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
        """Retrieves comments with privacy checks"""
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
    """
    Search hashtags with pagination
    """
    serializer_class = HashtagSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = HashtagPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']

    def get_queryset(self):
        query = self.request.query_params.get('search', '')
        return Hashtag.objects.filter(name__icontains=query).distinct()
    
class ToggleCommentVisibilityView(APIView):
    """
    Moderation endpoint for comment visibility
    """
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, comment_id):
        """Toggles comment's hidden status"""
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
    """
    Post deletion endpoint for owners
    """

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
    """
    Retrieves user's posts with privacy checks
    """

    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Applies privacy rules and blocking filters"""
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
    """
    Bookmarking system for posts
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, post_id):
        """Saves post with validity checks"""
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
    """
    Removes saved post bookmarks
    """

    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, post_id):
        try:
            saved_post = SavedPost.objects.get(user=request.user, post_id=post_id)
            saved_post.delete()
            return Response({"message": "Post unsaved successfully"}, status=status.HTTP_200_OK)
        except SavedPost.DoesNotExist:
            return Response({"error": "Post is not saved."}, status=status.HTTP_404_NOT_FOUND)

class SavedPostListView(generics.ListAPIView):
    """
    Lists user's saved posts with filters
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SavedPostSerializer

    def get_queryset(self):
        """Applies blocking filters to saved posts"""
        user = self.request.user
        queryset = SavedPost.objects.filter(user=user).select_related('post', 'post__user')
        blocked_by_user = BlockedUser.objects.filter(blocker=user).values_list('blocked', flat=True)
        blocked_by_others = BlockedUser.objects.filter(blocked=user).values_list('blocker', flat=True)
        queryset = queryset.exclude(post__user__in=list(blocked_by_user) + list(blocked_by_others))
        return queryset
    
class TopFanView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, post_id):
        post = get_object_or_404(Post, id=post_id)

        reaction_counts = Reaction.objects.filter(post=post).values('user').annotate(reaction_count=Count('id'))

        comment_counts = Comment.objects.filter(post=post).values('user').annotate(comment_count=Count("id"))

        interaction_dict = {}
        for rc in reaction_counts:
            uid = rc['user']
            interaction_dict[uid] = interaction_dict.get(uid, 0) + rc['reaction_count']

        for cc in comment_counts:
            uid = cc['user']
            interaction_dict[uid] = interaction_dict.get(uid, 0) + cc['comment_count']

        if not interaction_dict:
            return Response({"message": "No interactions for this post."}, status=status.HTTP_200_OK)

        top_fan_id = max(interaction_dict, key=interaction_dict.get)
        top_fan_count = interaction_dict[top_fan_id]
        top_fan = get_object_or_404(User, id=top_fan_id)
        serializer = UserSerializer(top_fan, context={'request': request})
        data = serializer.data
        data['interaction_count'] = top_fan_count

        return Response({"top_fan": data}, status=status.HTTP_200_OK)

class SharePostView(generics.CreateAPIView):
    """
    Allows an authenticated user to share (repost) a post.
    The original post is referenced, and an optional share text can be provided.
    If a shared post is attempted to be shared, it unwraps to share the original post.
    """

    serializer_class = SharedPostSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, post_id, *args, **kwargs):
        is_shared = request.query_params.get('is_shared', 'false').lower() == "true"

        if is_shared:
            shared_instance = get_object_or_404(SharedPost, id=post_id)
            post = shared_instance.original_post
            parent_share = shared_instance
        else:
            post = get_object_or_404(Post, id=post_id)
            parent_share = None

        share_text = request.data.get("share_text", "")
        shared_post = SharedPost.objects.create(
            user=request.user,
            original_post=post,
            share_text=share_text,
            parent_share=parent_share
        )
        serializer = self.get_serializer(shared_post, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class UserSharedPostsView(generics.ListAPIView):
    """
    Retrieves all shared posts by a specific user.
    """

    serializer_class = SharedPostSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user_id = self.kwargs.get("user_id")
        return SharedPost.objects.filter(user__id=user_id).order_by('-created_at')

class SharedPostReactionView(APIView):
    """
    Handles reactions for shared posts.
    POST: Creates a reaction for a given shared post.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, shared_post_id):
        # Ensure the shared post exists.
        shared_post = get_object_or_404(SharedPost, id=shared_post_id)

        reaction_type = request.data.get('type')
        if not reaction_type:
            return Response({"error": "Reaction type is required."}, status=status.HTTP_400_BAD_REQUEST)

        existing_reaction = SharedPostReaction.objects.filter(shared_post=shared_post, user=request.user).first()

        if existing_reaction:
            if existing_reaction.type == reaction_type:
                existing_reaction.delete()
                return Response({"message": "Reaction removed."}, status=status.HTTP_200_OK)
            else:
                existing_reaction.type = reaction_type
                existing_reaction.save()

                serializer = SharedPostReactionSerializer(existing_reaction, context={'request': request})
                return Response({"message": "Reaction updated.", "reaction": serializer.data}, status=status.HTTP_200_OK)
        else:

        # Prepare the data by including the shared_post ID.
            data = request.data.copy()
            data['shared_post'] = shared_post_id

            serializer = SharedPostReactionSerializer(data=data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            serializer.save(user=request.user)

            response = {
                "message": "Reaction recorded",
                "reaction": serializer.data,
            }

            return Response(response, status=status.HTTP_201_CREATED)
    
class SharedPostCommentView(APIView):
    """
    Handles comments on shared posts.
    POST: Create a new comment for a shared post.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, shared_post_id):
        # Ensure the shared post exists.
        shared_post = get_object_or_404(SharedPost, id=shared_post_id)
        # Prepare data: add the shared_post ID to the data.
        data = request.data.copy()
        data['shared_post'] = shared_post_id
        serializer = SharedPostCommentSerializer(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
class CommentReactionView(APIView):
    """
    Allows an authenticated user to react to a post comment.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, comment_id):
        comment = get_object_or_404(Comment, id=comment_id)
        reaction_type = request.data.get('type')

        if not reaction_type:
            return Response({"error": "Reaction type is required."}, status=status.HTTP_400_BAD_REQUEST)

        existing_reaction = CommentReaction.objects.filter(comment=comment, user=request.user).first()

        if existing_reaction:
            if existing_reaction.type == reaction_type:
                existing_reaction.delete()
                return Response({"message": "Reaction removed"}, status=status.HTTP_200_OK)
            else:
                existing_reaction.type = reaction_type
                existing_reaction.save()
                serializer = CommentReactionSerializer(existing_reaction, context={"request": request})
                comment_serializer = CommentSerializer(comment, context={'request': request})
                return Response({
                    "message": "Reaction Updated.",
                    "reaction": serializer.data,
                    "comment": comment_serializer.data,
                }, status=status.HTTP_200_OK)
        else:
            data = request.data.copy()
            data['comment'] = comment_id
            serializer = CommentReactionSerializer(data=data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            serializer.save(user=request.user)

            comment_serializer = CommentSerializer(comment, context={'request': request})

            response_data = {
                "message": "Reaction recorded",
                'reaction': serializer.data,
                'comment': comment_serializer.data
            }

            return Response(response_data, status=status.HTTP_201_CREATED)

class SharedPostCommentReactionView(APIView):
    """
    Allow an authenticated user to react to a shared post comment.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, shared_comment_id):
        shared_comment = get_object_or_404(SharedPostComment, id=shared_comment_id)

        reaction_type = request.data.get('type')
        if not reaction_type:
            return Response({"error": "Reaction type is required."}, status=status.HTTP_400_BAD_REQUEST)

        existing_reaction = SharedPostCommentReaction.objects.filter(shared_post_comment=shared_comment, user=request.user).first()

        if existing_reaction:
            if existing_reaction.type == reaction_type:
                existing_reaction.delete()
                return Response({"message": "Reaction removed."}, status=status.HTTP_200_OK)
            else:
                existing_reaction.type = reaction_type
                existing_reaction.save()
                serializer = SharedPostCommentReactionSerializer(existing_reaction, context={'request': request})
                shared_comment_serializer = SharedPostCommentSerializer(shared_comment, context={'request': request})
                return Response({
                    "message": "Reaction updated.",
                    "reaction": serializer.data,
                    "shared_comment": shared_comment_serializer.data,
                }, status=status.HTTP_200_OK)
        else:
            data = request.data.copy()
            data['shared_post_comment'] = shared_comment_id
            serializer = SharedPostCommentReactionSerializer(data=data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            serializer.save(user=request.user)

            shared_comment_serializer = SharedPostCommentSerializer(shared_comment, context={'request': request})

            return Response({
                "message": "Reaction recorded",
                "reaction": serializer.data,
                "shared_comment": shared_comment_serializer.data
            }, status=status.HTTP_201_CREATED)
        

class PostDetailView(APIView):
    """
    Retrieves a post's details and increments the view count.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        # Automatically increment view_count
        post.view_count = F('view_count') + 1
        post.save(update_fields=['view_count'])
        post.refresh_from_db()  # get updated value
        serializer = PostSerializer(post, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

class PostClickView(APIView):
    """
    Increments the click count when a user clicks a post link.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        post.click_count = F('click_count') + 1
        post.save(update_fields=['click_count'])
        post.refresh_from_db()
        return Response({
            "message": "Click recorded",
            "click_count": post.click_count,
        }, status=status.HTTP_200_OK)
    
class PostEngagementView(APIView):
    """
    Calculates and returns engagement metrics for a post.
    Engagement is computed as the sum of:
    - Number of reactions
    - Number of comments
    - Number of shares
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request, post_id):
        post = get_object_or_404(Post, id=post_id)
        reaction_count = post.reactions.count()
        comment_count = post.comments.count()
        share_count = SharedPost.objects.filter(original_post=post).count()
        view_count = post.view_count
        click_count = post.click_count

        engagement = reaction_count + comment_count + share_count + view_count + click_count

        return Response({
            "post_id": post.id,
            "reaction_count": reaction_count,
            "comment_count": comment_count,
            "share_count": share_count,
            "view_count": view_count,
            "click_count": click_count,
            "engagement": engagement,
        }, status=status.HTTP_200_OK)