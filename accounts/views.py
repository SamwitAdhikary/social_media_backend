import io
from django.http import HttpResponse
from django.utils import timezone
import pyotp
import qrcode
import qrcode.constants
from rest_framework import generics, status, permissions, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import ChangePasswordSerializer, RegisterSerializer, LoginSerializer, ProfileSerializer, UserSerializer, BlockedUserSerializer, PasswordResetRequestSerializer, PasswordResetConfirmSerializer
from .models import User, Profile, BlockedUser
from rest_framework_simplejwt.tokens import RefreshToken
import random
from storages.backends.s3boto3 import S3Boto3Storage
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

# Create your views here.


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


def generate_otp():
    return str(random.randint(100000, 999999))


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        otp = generate_otp()
        user.email_otp = otp
        user.otp_create_at = timezone.now()
        user.is_verified = False
        user.save()

        send_mail(
            subject="Your OTP for Email Verification",
            message=f"Your OTP is: {otp}. It is valid for 10 minutes.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        jwt_token = get_tokens_for_user(user)
        return Response({
            "message": "Registration successful. An OTP has been sent to your email for verification.",
            "user_id": user.id,
            "token": jwt_token
        }, status=status.HTTP_201_CREATED)


class VerifyEmailOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get("email")
        otp = request.data.get("otp")
        if not email or not otp:
            return Response({"error": "Email and OTP are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_400_BAD_REQUEST)

        if user.otp_created_at:
            elapsed = (timezone.now() - user.otp_created_at).total_seconds()
            if elapsed > 600:
                return Response({'error': "OTP expired. Please request a new one."}, status=status.HTTP_400_BAD_REQUEST)

        if user.email_otp != otp:
            return Response({'error': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)

        user.is_verified = True
        user.email_otp = ''
        user.otp_created_at = None
        user.save()

        return Response({"message": "Email verified successfully"}, status=status.HTTP_200_OK)


class ResendOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        if not email:
            return Response({'error': 'Email is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "User with this email does not exist."}, status=status.HTTP_400_BAD_REQUEST)

        if user.is_verified:
            return Response({"message": "User is already verified."}, status=status.HTTP_400_BAD_REQUEST)

        otp = generate_otp()
        user.email_otp = otp
        user.otp_created_at = timezone.now()
        user.save()

        send_mail(
            subject="Your OTP for Email Verification",
            message=f"Your new OTP is: {otp}. It is valid for 10 minutes.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        return Response({"message": "A new OTP has been sent to your email."}, status=status.HTTP_200_OK)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        if user.is_2fa_enabled:
            otp = request.data.get("otp")
            if not otp:
                return Response({"error": "OTP is required for two-factor authentication."}, status=status.HTTP_400_BAD_REQUEST)

            totp = pyotp.TOTP(user.otp_secret_key)
            current_valid_otp = totp.now()
            print(f"[DEBUG] Current valid OTP for user {user.username}: {current_valid_otp}")
            if not totp.verify(otp, valid_window=1):
                return Response({"error": "Invalid OTP. Please try again."}, status=status.HTTP_400_BAD_REQUEST)

        token = get_tokens_for_user(user)
        return Response({
            "token": token,
            "user": {"id": user.id, 'username': user.username}
        })


class ProfileDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    lookup_field = 'username'

    def get_queryset(self):
        user = self.request.user

        blocked_users = BlockedUser.objects.filter(
            blocker=user).values_list('blocked', flat=True)

        users_who_blocked_me = BlockedUser.objects.filter(
            blocked=user).values_list('blocker', flat=True)

        return Profile.objects.exclude(user__in=blocked_users).exclude(user__in=users_who_blocked_me)

    def get_object(self):
        obj = super().get_object()
        if obj.user in BlockedUser.objects.filter(blocker=self.request.user).values_list('blocked', flat=True) or obj.user in BlockedUser.objects.filter(blocked=self.request.user).values_list('blocker', flat=True):
            raise NotFound("This profile is not available.")
        return obj


class ProfileUpdateView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    lookup_field = 'username'

    def get_object(self):
        obj = super().get_object()
        if self.request.user != obj.user:
            raise PermissionDenied("You can only update your own profile.")
        return obj

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class UserPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50


class UserSearchView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = UserPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['username', 'profile__full_name']

    def get_queryset(self):
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
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
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
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
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
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        blocked_users = BlockedUser.objects.filter(blocker=request.user)
        serializer = BlockedUserSerializer(blocked_users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PasswordResetRequestView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetRequestSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        user = User.objects.get(email__iexact=email, is_active=True)
        token_generator = PasswordResetTokenGenerator()
        token = token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        reset_link = f"{request.scheme}://{request.get_host()}/accounts/password-reset-confirm/?uid={uid}&token={token}"

        subject = "Password Reset Request"
        message = f"Hi {user.username},\n\nPlease click the link below to reset your password:\n{reset_link}\n\nIf you did not request a password reset, please ignore this email."
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [email]
        send_mail(subject=subject, message=message, from_email=from_email,
                  recipient_list=recipient_list, fail_silently=False)

        return Response({"message": "Password reset link sent to your email."}, status=status.HTTP_200_OK)


class PasswordResetConfirmView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetConfirmSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Password has been reset successfully."}, status=status.HTTP_200_OK)


class ChangePasswordView(generics.UpdateAPIView):
    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, queryset=None):
        return self.request.user

    def update(self, request, *arg, **kwargs):
        user = self.get_object()
        serializer = self.get_serializer(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Password updated successfully."}, status=status.HTTP_200_OK)


class Enable2FAView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        otp_auth_url = user.get_otp_auth_url()

        qr = qrcode.QRCode(
            # version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=15,
            border=4
        )
        qr.add_data(otp_auth_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        s3_storage = S3Boto3Storage(
            bucket_name=settings.AWS_STORAGE_BUCKET_NAME)
        file_name = f"2fa_qrcodes/{user.id}_{int(timezone.now().timestamp())}.png"
        content_file = ContentFile(buffer.getvalue(), name=file_name)
        

        try:
            saved_path = s3_storage.save(file_name, content_file)
            qr_code_url = s3_storage.url(saved_path)
        except Exception as e:
            return Response({"error": f"Error uploading QR code {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        user.is_2fa_enabled = True
        user.save()

        return Response({
            "message": "Scan the QR code with your authenticator app",
            "otp_auth_url": otp_auth_url,
            "qr_code_link": qr_code_url
        }, status=status.HTTP_200_OK)
