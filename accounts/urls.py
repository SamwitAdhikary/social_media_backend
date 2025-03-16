from django.urls import path
from .views import RegisterView, LoginView, ProfileDetailView, VerifyEmailOTPView, ResendOTPView, ProfileUpdateView, UserSearchView, BlockedUserView, UnblockUserView, BlockedUserListView, PasswordResetConfirmView, PasswordResetRequestView, ChangePasswordView, Enable2FAView, AccountDeletionView, DownloadUserDataView

# Accounts Application URL Configuration
# Defines endpoints for user management and authentication features

urlpatterns = [
     # ============ Authentication Endpoints ================
    path('register/', RegisterView.as_view(), name='register'),
     #  POST: Creates new user account with email verification

    path('login/', LoginView.as_view(), name='login'),
     # POST: Authenticates user and returns JWT tokens

     # ============ Email Verification Flow ================
     path('verify-email-otp/', VerifyEmailOTPView.as_view(), name='verify-email-otp'),
     # POST: Validates email verification OTP

     path('resend-otp/', ResendOTPView.as_view(), name='resend-otp'),
     # POST: Resends email verication OTP

     # ============ Profile Management ================
    path('profile/<str:username>/',ProfileDetailView.as_view(), name='profile-details'),
     # GET: Retrieves profile details (privacy-aware)
     
    path('profile/<str:username>/update/',ProfileUpdateView.as_view(), name='profile-update'),
     # PUT: Updates profile information (owner only)

     # ============ User Search & Relations ================
    path('search/', UserSearchView.as_view(), name='user-search'),
     # GET: Searchs user by username or full name

    path("block-user/", BlockedUserView.as_view(), name='block-user'),
     # POST: Blocks specific user

    path('unblock-user/', UnblockUserView.as_view(), name='unblock-user'),
     # POST: Removes block from specific user

    path('blocked-users/', BlockedUserListView.as_view(), name='blocked-users'),
     # GET: List all blocked users

     # ============ Password Management ================
    path('password-reset/', PasswordResetRequestView.as_view(),name='password-reset-request'),
     # POST: Initiates password reset process
     
    path('password-reset-confirm/', PasswordResetConfirmView.as_view(),name='password-reset-confirm'),
     # POST: Confirms password reset with token

    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
     # PUT: Changes password for authenticated user

     # ============ Security Features ================
    path('enable-2fa/', Enable2FAView.as_view(), name="enable-2fa"),
     # POST: Enables Two-Factor Authentication (generates QR code)

     path('delete-account/', AccountDeletionView.as_view(), name="delete-account"),

     path('download-data/', DownloadUserDataView.as_view(), name='download-user-data'),
]

# URL Pattern Notes:
# 1. All endpoints require authentication unless specified otherwise
# 2. Dynamic username parameter used in profile-related endpoints
# 3. Password reset flow uses token-based security
# 4. Blocking system prevents unwanted interactions
# 5. 2FA endpoint returns QR code for authenticator app setup