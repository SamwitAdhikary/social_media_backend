from rest_framework import generics, permissions, status
from django.utils import timezone
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Story, StoryView, StoryReaction
from .serializers import StorySerializer
from rest_framework.views import APIView
import io
import logging
from django.conf import settings
from django.core.files.base import ContentFile
from storages.backends.s3boto3 import S3Boto3Storage
from PIL import Image
from django.db.models import Q
from accounts.models import BlockedUser
from connections.models import Connection

logger = logging.getLogger(__name__)

# Create your views here.
class CreateStoryView(generics.CreateAPIView):
    serializer_class = StorySerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def perform_create(self, serializer):
        media_files = self.request.FILES.getlist("media_files")
        story = serializer.save(user=self.request.user)

        s3_storage = S3Boto3Storage(bucket_name=settings.AWS_STORAGE_BUCKET_NAME)

        for file in media_files:
            media_type = 'image' if file.name.lower().endswith(("jpg", "jpeg", "png", "gif")) else "video"

            try:
                file.seek(0)
                data = file.read()
                if not data:
                    logger.error(f"No data read from file: {file.name}")
                    print(f'No data read from file: {file.name}')
                    continue
                file_content = ContentFile(data)

                file_path = s3_storage.save(f"stories/{file.name}", file_content)
                s3_url = s3_storage.url(file_path)
                logger.info(f"Story file saved to S3: {s3_url}")

                story.media_files.name = file_path
                story.save()

                if media_type == 'image':
                    try:

                        image = Image.open(io.BytesIO(data))
                        image.verify()

                        image = Image.open(io.BytesIO(data))
                        image.thumbnail((200, 200))

                        thumb_io = io.BytesIO()
                        image_format = image.format if image.format else 'JPEG'
                        image.save(thumb_io, format=image_format)
                        thumb_file = ContentFile(thumb_io.getvalue(), name=f"thumb_{file.name}")

                        thumb_path = s3_storage.save(f"stories/thumbnails/{thumb_file.name}", thumb_file)
                        story.thumbnail_file.name = thumb_path
                        story.save()
                        logger.info(f"Thumbnail saved to S3: {s3_storage.url(thumb_path)}")
                    except Exception as e:
                        logger.error(f"Error generating thumbnail for {file.name}: {e}")

            except Exception as e:
                logger.error(f"Error uploading story file {file.name}: {e}")

class ListStoryView(generics.ListAPIView):
    serializer_class = StorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        now = timezone.now()
        
        all_stories = Story.objects.filter(expires_at__gt=now).order_by('-created_at')
        request_user = self.request.user

        blocked_by_user = BlockedUser.objects.filter(blocker=request_user).values_list("blocked", flat=True)
        blocked_by_others = BlockedUser.objects.filter(blocked=request_user).values_list("blocker", flat=True)
        blocked_ids = set(list(blocked_by_user) + list(blocked_by_others))

        allowed_ids = []
        for story in all_stories:
            if story.user.id in blocked_ids:
                continue

            if story.user == request_user:
                allowed_ids.append(story.pk)
                continue

            privacy = 'public'
            if story.user.profile.privacy_settings:
                privacy = story.user.profile.privacy_settings.get("profile_visibility", "public")

            if privacy == "public":
                allowed_ids.append(story.pk)

            elif privacy == "friends":
                is_friend = Connection.objects.filter(
                    Q(requester=request_user, target=story.user) |
                    Q(requester=story.user, target=request_user),
                    status='accepted',
                    connection_type='friend'
                ).exists()

                is_follower = Connection.objects.filter(
                    requester=request_user,
                    target=story.user,
                    status='accepted',
                    connection_type='follower'
                ).exists()
                if is_friend or is_follower:
                    allowed_ids.append(story.pk)
            elif privacy == 'private':
                continue

        return Story.objects.filter(pk__in=allowed_ids).order_by("-created_at")
    
class StoryDeleteView(generics.DestroyAPIView):
    """
    Allows an authenticated user to manually delete their own story only if it hasn't expired yet (i.e. within 24 hours of creation).
    """

    permission_classes = [permissions.IsAuthenticated]
    queryset = Story.objects.all()

    def get_object(self):
        # Ensure the story belongs to the authenticated user.
        obj = get_object_or_404(Story, pk=self.kwargs['pk'], user=self.request.user)
        return obj
    
    def delete(self, request, *args, **kwargs):
        story = self.get_object()
        if timezone.now() > story.expires_at:
            return Response({"error": "Story has already expired and cannot be manually deleted."}, status=status.HTTP_400_BAD_REQUEST)
        self.perform_destroy(story)
        return Response({"message": "Story deleted successfully."}, status=status.HTTP_200_OK)
    
class MarkStorySeenView(APIView):
    """
    Marks a story as seen by the authenticated user.
    Creates a storyview record if not already present.
    Returns the updated view count.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, story_id):
        story = get_object_or_404(Story, id=story_id)
        if not story.views.filter(user=request.user).exists():
            StoryView.objects.create(story=story, user=request.user)
        seen_count = story.views.count()
        return Response({"message": "Story marked as seen", "seen_count": seen_count}, status=status.HTTP_200_OK)

class StoryReactionView(generics.GenericAPIView):
    """
    Handles reacting to a story (e.g., "love" reaction).
    - If a reaction alreay exists and is the same, it removes it (unlike).
    - If a reaction exists but different (for stories, only 'love' is supported),
    - Otherwise, it creates a new reaction.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, story_id):
        story = get_object_or_404(Story, id=story_id)
        reaction_type = request.data.get('type')
        if reaction_type != "love":
            return Response({"error": "Only 'love' reaction is supported."}, status=status.HTTP_400_BAD_REQUEST)

        existing_reaction = story.reactions.filter(user=request.user).first()
        if existing_reaction:
            if existing_reaction.type == reaction_type:
                existing_reaction.delete()
                return Response({"message": "Reaction removed"}, status=status.HTTP_200_OK)
            else:
                existing_reaction.type = reaction_type
                existing_reaction.save()
                serializer = StorySerializer(existing_reaction, context={"request": request})
                return Response({"message": "Reaction updated.", "reaction": serializer.data}, status=status.HTTP_200_OK)
        else:
            serializer = StorySerializer(data={'story': story_id, 'type': reaction_type}, context={'request': request})
            serializer.is_valid(raise_exception=True)
            reaction = serializer.save(user=request.user)
            return Response({"message": "Reaction recorded", "reaction": serializer.data}, status=status.HTTP_200_OK)