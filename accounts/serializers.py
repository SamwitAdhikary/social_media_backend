from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, Profile, BlockedUser
from connections.models import Connection
from django.db.models import Q
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import PasswordResetTokenGenerator

class RegisterSerializer(serializers.ModelSerializer):
    """
    Handles user registration with:
    - Email validation
    - Password hashing
    - Automatic profile creation
    """

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        """Creates user with hashed password and initial profile"""

        user = User(**validated_data)
        user.set_password(validated_data['password'])
        user.save()
        Profile.objects.create(user=user, username=user.username)
        return user
    
class LoginSerializer(serializers.Serializer):
    """
    Handles user authentication:
    - Validates email/password combination
    - Integrates with Django's authentication system
    - Returns user instance if credentials are valid
    """

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        """Performs authentication and returns validated data with user instance"""

        email = data.get("email")
        password = data.get("password")
        user = authenticate(email=email, password=password)
        if not user:
            raise serializers.ValidationError("Invalid Credentials.")
        data['user'] = user
        return data
    
class ProfileSerializer(serializers.ModelSerializer):
    """
    Serializes profile data with privacy-aware field exposure:
    - Controls data visibility based on privacy settings
    - Shows basic info to public/full info to friends
    - Always shows complete data to profile owner
    """

    class Meta:
        model = Profile
        fields = [
            'user',
            'full_name',
            'username',
            'bio',
            'profile_picture_url',
            'cover_picture_url',
            'date_of_birth',
            'gender',
            'location',
            'relationship_status',
            'education',
            'work',
            'privacy_settings'
        ]

        read_only_fields = ['user', 'username']

    def to_representation(self, instance):
        """
        Custom representation based on viewer's relationship and privacy settings:
        1. Profile owner sees all fields
        2. Friends see extended info (if privacy allows)
        3. Public sees everything
        """

        representation = super().to_representation(instance)
        request = self.context.get('request')

        # Default: show basic fields
        basic_fields = {
            'username': representation.get('username'),
            'profile_picture_url': representation.get('profile_picture_url'),
        }

        profile_owner = instance.user

        # Determine profile visibility: default to public if not set.
        privacy = instance.privacy_settings.get("profile_visibility", "public")

        # If the logged-in user is viewing their own profile, show everything.
        if request and profile_owner == request.user:
            return representation
        
        # Checking if the viewer is a friend
        is_friend = False
        if request and request.user.is_authenticated:
            is_friend = Connection.objects.filter(
                (Q(requester=request.user, target=profile_owner) |
                 Q(requester=profile_owner, target=request.user)),
                 status='accepted',
                 connection_type = 'friend'
            ).exists()
        
        # if profile is public, show everything
        if privacy == 'public':
            return representation
        
        # if profile is set to 'friends', you may want to check if the viewer is a friend.
        if privacy == 'friends' and is_friend:
            return representation
        return {
            **basic_fields,
            "bio": representation.get('bio')
        }
    
class UserSerializer(serializers.ModelSerializer):
    """
    Serializes user data with privacy considerations:
    - Shows minimal info (ID, username, avatar) to non-friends
    - Shows full profile data to friends/self
    - Adds profile-related fields to user representation
    """

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

    def to_representation(self, instance):
        """Enhances user data with profile information and privacy checks"""

        request = self.context.get("request")

        privacy = instance.profile.privacy_settings.get("profile_visibility", 'public')

        if privacy == 'friends' and (not request or request.user != instance):
            return {
                "id": instance.id,
                "username": instance.username,
                "profile_picture_url": instance.profile.profile_picture_url,
            }
        
        ret = super().to_representation(instance)
        ret['full_name'] = instance.profile.full_name
        ret['profile_picture_url'] = instance.profile.profile_picture_url
        ret['bio'] = instance.profile.bio
        return ret
    
class BlockedUserSerializer(serializers.ModelSerializer):
    """
    Serializes blocked user relationships:
    - Shows blocker/blocked user IDs
    - Tracks creation time of block
    - Used for listing/displaying block relationships
    """

    class Meta:
        model = BlockedUser
        fields = '__all__'

class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Handles password reset initiation:
    - Validates email exists in active users
    - Triggers password reset email flow
    """

    email = serializers.EmailField()

    def validate_email(self, value):
        """Ensures email belongs to an active user account"""

        if not User.objects.filter(email__iexact=value, is_active=True).exists():
            raise serializers.ValidationError("No active user with this email was found.")
        return value
    
class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Handles password reset confirmation:
    - Validates UID/token combination
    - Sets new password if validation succeeds
    - Uses Django's password reset token generator
    """

    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8, write_only=True)

    def validate(self, data):
        """Verifies reset token validity and user existence"""
        try:
            uid = urlsafe_base64_decode(data['uid']).decode()
            user = User.objects.get(pk=uid)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            raise serializers.ValidationError({"uid": "Invalid UID."})

        token_generator = PasswordResetTokenGenerator()
        if not token_generator.check_token(user, data['token']):
            raise serializers.ValidationError({"token": "Invalid or expired token."})
        data['user'] = user
        return data
    
    def save(self):
        """Updates user password after successful validation"""
        user = self.validated_data['user']
        new_password = self.validated_data['new_password']
        user.set_password(new_password)
        user.save()
        return user
    
class ChangePasswordSerializer(serializers.Serializer):
    """Handles password change for authenticated users:
    - Validates old password correctness
    - Ensures new password confirmation matches
    - Updates password in database
    """

    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=8)
    confirm_new_password = serializers.CharField(required=True, write_only=True, min_length=8)

    def validate_old_password(self, value):
        """Verifies current password matches user's actual password"""

        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("old password is not correct.")
        return value
    
    def validate(self, data):
        """Ensures new password fields match"""

        if data['new_password'] != data['confirm_new_password']:
            raise serializers.ValidationError("New password fields didn't match.")
        return data
    
    def save(self, **kwargs):
        """Updates user's password after validation"""

        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user