from django.urls import path
from .views import RegisterView, LoginView, ProfileDetailView, VerifyEmailOTPView, ResendOTPView, ProfileUpdateView, UserSearchView, BlockedUserView, UnblockUserView, BlockedUserListView, PasswordResetConfirmView, PasswordResetRequestView, ChangePasswordView, Enable2FAView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('profile/<str:username>/',
         ProfileDetailView.as_view(), name='profile-details'),
    path('profile/<str:username>/update/',
         ProfileUpdateView.as_view(), name='profile-update'),
    path('verify-email-otp/', VerifyEmailOTPView.as_view(), name='verify-email-otp'),
    path('resend-otp/', ResendOTPView.as_view(), name='resend-otp'),
    path('search/', UserSearchView.as_view(), name='user-search'),
    path("block-user/", BlockedUserView.as_view(), name='block-user'),
    path('unblock-user/', UnblockUserView.as_view(), name='unblock-user'),
    path('blocked-users/', BlockedUserListView.as_view(), name='blocked-users'),
    path('password-reset/', PasswordResetRequestView.as_view(),
         name='password-reset-request'),
    path('password-reset-confirm/', PasswordResetConfirmView.as_view(),
         name='password-reset-confirm'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('enable-2fa/', Enable2FAView.as_view(), name="enable-2fa"),
]
