import io
from django.http import HttpResponse
from django.utils import timezone
import pyotp
import qrcode
import qrcode.constants
from rest_framework import generics, status, permissions, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from connections.serializers import ConnectionSerializer
from notifications.models import Notification
from notifications.serializer import NotificationSerializer
from posts.models import Post, SavedPost
from posts.serializers import PostSerializer, SavedPostSerializer
from utils.aws import upload_file_to_s3
from .serializers import ChangePasswordSerializer, ProfileMediaUpdateSerializer, RegisterSerializer, LoginSerializer, ProfileSerializer, UserSerializer, BlockedUserSerializer, PasswordResetRequestSerializer, PasswordResetConfirmSerializer
from .models import User, Profile, BlockedUser
from rest_framework_simplejwt.tokens import RefreshToken
import random
from storages.backends.s3boto3 import S3Boto3Storage
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.exceptions import PermissionDenied, NotFound
from connections.models import Connection
from django.db import transaction
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

# Create your views here.


def get_tokens_for_user(user):
    """Generate JWT access and refresh tokens for user authentication"""

    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


def generate_otp():
    """Generates a 6-digit random numeric OTP for email verification"""
    return str(random.randint(100000, 999999))


class RegisterView(generics.CreateAPIView):
    """
    Handles user registration with:
    - Account creation
    - OTP generation
    - Email verification setup
    - JWT token return
    """

    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        """Processes user registration an initiates email verification"""

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generates and store verification OTP
        otp = generate_otp()
        user.email_otp = otp
        user.otp_create_at = timezone.now()
        user.is_verified = False
        user.save()

        # Send verification email
        send_mail(
            subject="Your OTP for Email Verification",
            message=f"Your OTP is: {otp}. It is valid for 10 minutes.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        # Return authentication tokens
        jwt_token = get_tokens_for_user(user)
        return Response({
            "message": "Registration successful. An OTP has been sent to your email for verification.",
            "user_id": user.id,
            "token": jwt_token
        }, status=status.HTTP_201_CREATED)


class VerifyEmailOTPView(APIView):
    """
    Handles email verification process:
    - Validates OTP against user record
    - Marks email as verified
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        """Verifies OTP and activates user account"""

        email = request.data.get("email")
        otp = request.data.get("otp")
        if not email or not otp:
            return Response({"error": "Email and OTP are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_400_BAD_REQUEST)

        # Check OTP expiraton (10 minutes)
        if user.otp_created_at:
            elapsed = (timezone.now() - user.otp_created_at).total_seconds()
            if elapsed > 600:
                return Response({'error': "OTP expired. Please request a new one."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate OTP match
        if user.email_otp != otp:
            return Response({'error': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)

        # Activate user account
        user.is_verified = True
        user.email_otp = ''
        user.otp_created_at = None
        user.save()

        return Response({"message": "Email verified successfully"}, status=status.HTTP_200_OK)


class ResendOTPView(APIView):
    """
    Handles OTP resend request for email verification
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        """Generates and sends new OTP to user's email"""

        email = request.data.get('email')
        if not email:
            return Response({'error': 'Email is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "User with this email does not exist."}, status=status.HTTP_400_BAD_REQUEST)

        if user.is_verified:
            return Response({"message": "User is already verified."}, status=status.HTTP_400_BAD_REQUEST)

        # Generate and store new OTP
        otp = generate_otp()
        user.email_otp = otp
        user.otp_created_at = timezone.now()
        user.save()

        # Resend verification email
        send_mail(
            subject="Your OTP for Email Verification",
            message=f"Your new OTP is: {otp}. It is valid for 10 minutes.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        return Response({"message": "A new OTP has been sent to your email."}, status=status.HTTP_200_OK)


class LoginView(APIView):
    """
    Handles user authentication:
    - Email/password verification
    - 2FA validation (if enabled)
    - JWT token generation
    """

    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        """Authenticates user and returns JWT tokens"""

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        # Handle 2FA if enabled
        if user.is_2fa_enabled:
            otp = request.data.get("otp")
            if not otp:
                return Response({"error": "OTP is required for two-factor authentication."}, status=status.HTTP_400_BAD_REQUEST)

            # TOTP validation
            totp = pyotp.TOTP(user.otp_secret_key)
            current_valid_otp = totp.now()
            if not totp.verify(otp, valid_window=1):
                return Response({"error": "Invalid OTP. Please try again."}, status=status.HTTP_400_BAD_REQUEST)

        # Generate authentication tokens
        token = get_tokens_for_user(user)
        return Response({
            "token": token,
            "user": {"id": user.id, 'username': user.username}
        })


class ProfileDetailView(generics.RetrieveAPIView):
    """
    Provides profile details view with:
    - Privacy-aware data exposure
    - Blocked user filtering
    """

    permission_classes = [permissions.IsAuthenticated]
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    lookup_field = 'username'

    def get_queryset(self):
        """Filters out profiles form blocked/blocking users"""

        user = self.request.user

        blocked_users = BlockedUser.objects.filter(
            blocker=user).values_list('blocked', flat=True)

        users_who_blocked_me = BlockedUser.objects.filter(
            blocked=user).values_list('blocker', flat=True)

        return Profile.objects.exclude(user__in=blocked_users).exclude(user__in=users_who_blocked_me)

    def get_object(self):
        """Checks for blocking relationships before returning profile"""

        obj = super().get_object()
        if obj.user in BlockedUser.objects.filter(blocker=self.request.user).values_list('blocked', flat=True) or obj.user in BlockedUser.objects.filter(blocked=self.request.user).values_list('blocker', flat=True):
            raise NotFound("This profile is not available.")
        return obj


class ProfileUpdateView(generics.RetrieveUpdateAPIView):
    """
    Handles profile updates:
    - Only allows profile owner to make changes
    - Maintains data consistency
    """

    permission_classes = [permissions.IsAuthenticated]
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    lookup_field = 'username'

    def get_object(self):
        """Ensures only profile owner can update"""

        obj = super().get_object()
        if self.request.user != obj.user:
            raise PermissionDenied("You can only update your own profile.")
        return obj

    def get_serializer_context(self):
        """Adds request context to serializer"""

        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
class ProfileMediaUpdateView(APIView):
    """
    Allows an authenticated user to update their profile picture and cover picture.
    Expects multipart/form-data with:
    - profile_picture: image file (optional)
    - cover_picture: image file (optional)
    """

    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        return self.handle_media_update(request)

    def put(self, request, *args, **kwargs):
        return self.handle_media_update(request)

    def patch(self, request):
        profile = get_object_or_404(Profile, user=request.user)
        updated_fields = {}

        if 'profile_picture' in request.FILES:
            file = request.FILES['profile_picture']
            try:
                saved_path, s3_url = upload_file_to_s3(file, folder='profile_pictures')
                profile.profile_picture_url = s3_url
                updated_fields['profile_picture'] = s3_url
            except Exception as e:
                return Response({"error": f"Error uploading profile picture: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if 'cover_picture' in request.FILES:
            file = request.FILES['cover_picture']
            try:
                saved_path, s3_url = upload_file_to_s3(file, folder='cover_pictures')
                profile.cover_picture_url = s3_url
                updated_fields['cover_picture'] = s3_url
            except Exception as e:
                return Response({"error": f"Error uploading cover picture: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        profile.save()
        return Response({"message": "Profile media updated successfully", "data": updated_fields}, status=status.HTTP_200_OK)

class UserPagination(PageNumberPagination):
    """Custom pagination settings for user listings"""

    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50


class UserSearchView(generics.ListAPIView):
    """
    Provides user search functionality:
    - Filters blocked users
    - Search by username or full name
    """

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = UserPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['username', 'profile__full_name']

    def get_queryset(self):
        """Filters search results based on blocking relationships"""

        user = self.request.user
        query = self.request.query_params.get('search', '')

        blocked_users = BlockedUser.objects.filter(
            blocker=user).values_list('blocked', flat=True)
        users_who_blocked_me = BlockedUser.objects.filter(
            blocked=user).values_list('blocker', flat=True)

        return User.objects.exclude(id__in=blocked_users).exclude(id__in=users_who_blocked_me).filter(
            Q(username__icontains=query) |
            Q(profile__full_name__icontains=query)
        ).distinct()


class BlockedUserView(APIView):
    """
    Handles user blocking functionality
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Creates a blocking relationship between users"""

        blocked_user_id = request.data.get('blocked_user_id')

        if not blocked_user_id:
            return Response({"error": "User ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            blocked_user = User.objects.get(id=blocked_user_id)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        if BlockedUser.objects.filter(blocker=request.user, blocked=blocked_user).exists():
            return Response({"error": "User is already blocked"}, status=status.HTTP_400_BAD_REQUEST)

        BlockedUser.objects.create(blocker=request.user, blocked=blocked_user)
        return Response({"message": "User blocked successfully"}, status=status.HTTP_201_CREATED)


class UnblockUserView(APIView):
    """
    Handles removal of blocking relationships
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Removes existing block between users"""

        blocked_user_id = request.data.get("blocked_user_id")

        if not blocked_user_id:
            return Response({"error": "User ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            blocked_user = User.objects.get(id=blocked_user_id)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        block_entry = BlockedUser.objects.filter(
            blocker=request.user, blocked=blocked_user)
        if not block_entry.exists():
            return Response({"error": "User is not blocked"}, status=status.HTTP_400_BAD_REQUEST)

        block_entry.delete()
        return Response({"message": "User unblocked successfully"}, status=status.HTTP_200_OK)


class BlockedUserListView(APIView):
    """
    Provides listing of blocked users
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Returns paginated list of blocked users"""

        blocked_users = BlockedUser.objects.filter(blocker=request.user)
        serializer = BlockedUserSerializer(blocked_users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PasswordResetRequestView(generics.GenericAPIView):
    """
    Handles password reset initiation
    """

    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetRequestSerializer

    def post(self, request, *args, **kwargs):
        """Generates and sends password reset link"""

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        user = User.objects.get(email__iexact=email, is_active=True)
        token_generator = PasswordResetTokenGenerator()
        token = token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        reset_link = f"{request.scheme}://{request.get_host()}/accounts/password-reset-confirm/?uid={uid}&token={token}"

        # Send password reset email
        subject = "Password Reset Request"
        message = f"Hi {user.username},\n\nPlease click the link below to reset your password:\n{reset_link}\n\nIf you did not request a password reset, please ignore this email."
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [email]
        send_mail(subject=subject, message=message, from_email=from_email,
                  recipient_list=recipient_list, fail_silently=False)

        return Response({"message": "Password reset link sent to your email."}, status=status.HTTP_200_OK)


class PasswordResetConfirmView(generics.GenericAPIView):
    """
    Handles password reset confirmation
    """

    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetConfirmSerializer

    def post(self, request, *args, **kwargs):
        """Validates reset token and updates password"""

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Password has been reset successfully."}, status=status.HTTP_200_OK)


class ChangePasswordView(generics.UpdateAPIView):
    """
    Handles password changes for authenticated users
    """

    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, queryset=None):
        """Returns the requesting user instance"""

        return self.request.user

    def update(self, request, *arg, **kwargs):
        """Validates and updates user password"""

        user = self.get_object()
        serializer = self.get_serializer(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Password updated successfully."}, status=status.HTTP_200_OK)


class Enable2FAView(APIView):
    """
    Handles Two-Factor Authentication setup
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Generates and store 2FA secret, returns QR code"""

        user = request.user
        otp_auth_url = user.get_otp_auth_url()

        # Generate QR code
        qr = qrcode.QRCode(
            # version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=15,
            border=4
        )
        qr.add_data(otp_auth_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black",
                            back_color="white").convert("RGB")

        # Save QR to buffer
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        # Upload to S3 Storage
        s3_storage = S3Boto3Storage(
            bucket_name=settings.AWS_STORAGE_BUCKET_NAME)
        file_name = f"2fa_qrcodes/{user.id}_{int(timezone.now().timestamp())}.png"
        content_file = ContentFile(buffer.getvalue(), name=file_name)

        try:
            saved_path = s3_storage.save(file_name, content_file)
            qr_code_url = s3_storage.url(saved_path)
        except Exception as e:
            return Response({"error": f"Error uploading QR code {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Enable 2FA for user
        user.is_2fa_enabled = True
        user.save()

        return Response({
            "message": "Scan the QR code with your authenticator app",
            "otp_auth_url": otp_auth_url,
            "qr_code_link": qr_code_url
        }, status=status.HTTP_200_OK)

class AccountDeletionView(generics.DestroyAPIView):
    """
    Deletes the authenticated user's account along with all related data:
    - Profile, Posts, Saved Posts, Connections (sent and received)
    - Notifications, etc.
    """

    permission_classes = [permissions.IsAuthenticated]
    queryset = User.objects.all()

    def get_object(self):
        # Ensure only the authenticated user can delete their account.
        return self.request.user
    
    @transaction.atomic
    def delete(self, request, *args, **kwargs):
        user = self.get_object()

        # Delete related data explicitly if not already cascading:
        if hasattr(user, 'profile'):
            user.profile.delete()

        # Delete all posts (and cascade will handle media, reactions, comments, etc.)
        user.posts.all().delete()

        # Delete saved posts (if not cascading)
        if hasattr(user, 'saved_posts'):
            user.saved_posts.all().delete()

        # Delete connections (both sent and received)
        user.sent_requests.all().delete()
        user.received_requests.all().delete()

        # Delete notifications (assuming Notifications has on_delete=models.CASCADE for user, but do it explicitly)
        user.notifications.all().delete()

        # Finally, delete the user account
        self.perform_destroy(user)
        return Response({"message": "Your account and all related data have been deleted."}, status=status.HTTP_200_OK)
    
class DownloadUserDataView(APIView):
    """
    Collects and returns all data for the authenticated user:
    - Profile details
    - Posts created by the user
    - Connections (both sent and received)
    - Notifications
    - Saved Posts
    The data is returned as a downloadable JSON file.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        # Profile Data (Assumes ProfileSerializer is used to serialize the user's profile)
        profile_data = ProfileSerializer(user.profile, context={'request': request}).data

        # Posts created by the user
        posts = Post.objects.filter(user=user).order_by('-created_at')
        posts_data = PostSerializer(posts, many=True, context={'request': request}).data

        # Connections: both sent and received friend/follow requests.
        connections = Connection.objects.filter(Q(requester=user) | Q(target=user))
        connections_data = ConnectionSerializer(connections, many=True, context={'request': request}).data

        # Notification for the user
        notifications = Notification.objects.filter(user=user).order_by('-created_at')
        notifications_data = NotificationSerializer(notifications, many=True, context={'request': request}).data

        # Saved posts
        saved_posts = SavedPost.objects.filter(user=user)
        saved_posts_data = SavedPostSerializer(saved_posts, many=True, context={"request":request}).data

        # Aggredate all data
        data = {
            "profile": profile_data,
            "posts": posts_data, 
            "connections": connections_data,
            "notifications": notifications_data,
            "saved_posts": saved_posts_data,
        }

        # Return as a downloadable JSON file with proper headers
        response = Response(data, status=status.HTTP_200_OK)
        response['Content-Disposition'] = 'attachment; filename="user_data.json"'
        return response
    
class UserProfileView(APIView):
    """
    Returns authenticated user details
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)