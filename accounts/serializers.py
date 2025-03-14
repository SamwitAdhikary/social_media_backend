from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, Profile, BlockedUser
from connections.models import Connection
from django.db.models import Q
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import PasswordResetTokenGenerator

class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User(**validated_data)
        user.set_password(validated_data['password'])
        user.save()
        Profile.objects.create(user=user, username=user.username)
        return user
    
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get("email")
        password = data.get("password")
        user = authenticate(email=email, password=password)
        if not user:
            raise serializers.ValidationError("Invalid Credentials.")
        data['user'] = user
        return data
    
class ProfileSerializer(serializers.ModelSerializer):
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
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

    def to_representation(self, instance):
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
    class Meta:
        model = BlockedUser
        fields = '__all__'

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email__iexact=value, is_active=True).exists():
            raise serializers.ValidationError("No active user with this email was found.")
        return value
    
class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8, write_only=True)

    def validate(self, data):
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
        user = self.validated_data['user']
        new_password = self.validated_data['new_password']
        user.set_password(new_password)
        user.save()
        return user
    
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=8)
    confirm_new_password = serializers.CharField(required=True, write_only=True, min_length=8)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("old password is not correct.")
        return value
    
    def validate(self, data):
        if data['new_password'] != data['confirm_new_password']:
            raise serializers.ValidationError("New password fields didn't match.")
        return data
    
    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user