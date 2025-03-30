import base64
from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils import timezone
import pyotp
from django.core.validators import FileExtensionValidator

# Create your models here.
class User(AbstractUser):
    """
    Custom User Model with extended features:
    - Email verification via OTP
    - Two-Factor Authentication (2FA) support
    - OTP secret key storage
    """

    email = models.EmailField(unique=True)
    is_verified = models.BooleanField(default=False)
    email_otp = models.CharField(max_length=6, blank=True, null=True)
    otp_created_at = models.DateTimeField(blank=True, null=True)

    is_2fa_enabled = models.BooleanField(default=False)
    otp_secret_key = models.CharField(max_length=100, blank=True, null=True)

    groups = models.ManyToManyField(
        Group,
        related_name='custom_user_set',
        blank=True,
        help_text='The groups this user belongs to.',
        related_query_name='custom_user',
    )

    user_permissions = models.ManyToManyField(
        Permission,
        related_name='custom_user_set',
        blank=True,
        help_text="Specific permissions for this user.",
        related_query_name="custom_user",
    )

    def generate_otp_secret(self):
        """Generates base32 secret for TOTP if not exists"""

        if not self.otp_secret_key:
            self.otp_secret_key = pyotp.random_base32()
            self.save()
        return self.otp_secret_key
    
    def get_otp_auth_url(self):
        """Generates provisioning URI for authenticator apps"""

        secret = self.generate_otp_secret()
        account_name = self.username.replace(":", "")
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=account_name, issuer_name="InstaClone")

class Profile(models.Model):
    """
    User Profile Model storing:
    - Personal information
    - Privacy settings
    - Media URLs
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    full_name = models.CharField(max_length=255)
    username = models.CharField(max_length=150, unique=True)
    bio = models.TextField(blank=True)

    # profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])])
    # cover_picture = models.ImageField(upload_to='cover_pictures/', blank=True, validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])])

    profile_picture_url = models.URLField(blank=True)
    cover_picture_url = models.URLField(blank=True)

    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, blank=True)
    location = models.CharField(max_length=255, blank=True)
    relationship_status = models.CharField(max_length=100, blank=True)
    education = models.CharField(max_length=255, blank=True)
    work = models.CharField(max_length=255, blank=True)
    privacy_settings = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.username
    
class BlockedUser(models.Model):
    """
    Tracks user blocking relationships
    - blocker: User who initiated block
    - blocked: User who was blocked
    """

    blocker = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocking')
    blocked = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocked')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('blocker', 'blocked')

    def __str__(self):
        return f"{self.blocker} blocked {self.blocked}"