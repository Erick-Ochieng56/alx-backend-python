# messaging_app/chats/auth.py

from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer # type: ignore
from rest_framework_simplejwt.views import TokenObtainPairView # type: ignore
from rest_framework_simplejwt.tokens import RefreshToken # type: ignore
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import User


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT token serializer that includes additional user information
    """
    username_field = 'email'  # Allow login with email instead of username
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Allow login with either username or email
        self.fields['username'] = serializers.CharField(
            help_text="Username or email address"
        )
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Add custom claims to the token
        token['user_id'] = str(user.user_id)
        token['username'] = user.username
        token['email'] = user.email
        token['first_name'] = user.first_name
        token['last_name'] = user.last_name
        
        return token
    
    def validate(self, attrs):
        # Allow authentication with either username or email
        username_or_email = attrs.get('username')
        password = attrs.get('password')
        
        if username_or_email and password:
            # Try to find user by email first, then by username
            user = None
            if '@' in username_or_email:
                try:
                    user = User.objects.get(email=username_or_email)
                except User.DoesNotExist:
                    pass
            
            if not user:
                try:
                    user = User.objects.get(username=username_or_email)
                except User.DoesNotExist:
                    pass
            
            if user and user.check_password(password):
                if not user.is_active:
                    raise serializers.ValidationError('User account is disabled.')
                
                # Update attrs with the actual username for parent validation
                attrs['username'] = user.username
                
                # Call parent validation
                data = super().validate(attrs)
                
                # Add user information to response
                data['user'] = {
                    'user_id': str(user.user_id),
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'full_name': f"{user.first_name} {user.last_name}".strip(),
                }
                
                return data
            else:
                raise serializers.ValidationError('Invalid email/username or password.')
        else:
            raise serializers.ValidationError('Must include username/email and password.')


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom token obtain view with enhanced response
    """
    serializer_class = CustomTokenObtainPairSerializer


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration
    """
    password = serializers.CharField(
        write_only=True, 
        min_length=8,
        help_text="Password must be at least 8 characters long"
    )
    password_confirm = serializers.CharField(
        write_only=True,
        help_text="Confirm your password"
    )
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'phone_number'
        ]
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }
    
    def validate_email(self, value):
        """
        Validate that email is unique
        """
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value
    
    def validate_username(self, value):
        """
        Validate that username is unique
        """
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value
    
    def validate(self, attrs):
        """
        Validate password confirmation and strength
        """
        password = attrs.get('password')
        password_confirm = attrs.get('password_confirm')
        
        if password != password_confirm:
            raise serializers.ValidationError("Passwords do not match.")
        
        # Validate password strength using Django's validators
        try:
            validate_password(password)
        except ValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})
        
        return attrs
    
    def create(self, validated_data):
        """
        Create a new user with encrypted password
        """
        # Remove password_confirm as it's not needed for user creation
        validated_data.pop('password_confirm', None)
        
        # Create user with encrypted password
        user = User.objects.create_user(**validated_data)
        
        return user


class UserRegistrationView(APIView):
    """
    API endpoint for user registration
    """
    permission_classes = [AllowAny]
    serializer_class = UserRegistrationSerializer
    
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        
        if serializer.is_valid():
            user = serializer.save()
            
            # Generate JWT tokens for the new user
            refresh = RefreshToken.for_user(user)
            access = refresh.access_token
            
            # Add custom claims to access token
            access['user_id'] = str(user.user_id)
            access['username'] = user.username
            access['email'] = user.email
            access['first_name'] = user.first_name
            access['last_name'] = user.last_name
            
            return Response({
                'message': 'User created successfully',
                'user': {
                    'user_id': str(user.user_id),
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'full_name': f"{user.first_name} {user.last_name}".strip(),
                },
                'tokens': {
                    'access': str(access),
                    'refresh': str(refresh),
                }
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(APIView):
    """
    API endpoint for retrieving and updating user profile
    """
    def get(self, request):
        """
        Get current user's profile
        """
        user = request.user
        return Response({
            'user_id': str(user.user_id),
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'phone_number': user.phone_number,
            'full_name': f"{user.first_name} {user.last_name}".strip(),
            'created_at': user.created_at,
            'is_active': user.is_active,
        })
    
    def put(self, request):
        """
        Update current user's profile
        """
        user = request.user
        serializer = UserRegistrationSerializer(
            user, 
            data=request.data, 
            partial=True
        )
        
        # Remove password fields from partial updates
        if 'password' not in request.data:
            serializer.fields.pop('password', None)
            serializer.fields.pop('password_confirm', None)
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Profile updated successfully',
                'user': {
                    'user_id': str(user.user_id),
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'phone_number': user.phone_number,
                    'full_name': f"{user.first_name} {user.last_name}".strip(),
                }
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    """
    API endpoint for user logout (blacklist refresh token)
    """
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
                return Response({'message': 'Successfully logged out'})
            else:
                return Response(
                    {'error': 'Refresh token is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            return Response(
                {'error': 'Invalid token'}, 
                status=status.HTTP_400_BAD_REQUEST
            )