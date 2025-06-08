# messaging_app/urls.py

from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView,
)
from chats.views import UserViewSet, ConversationViewSet, MessageViewSet
from chats.auth import (
    CustomTokenObtainPairView,
    UserRegistrationView,
    UserProfileView,
    LogoutView,
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'conversations', ConversationViewSet)
router.register(r'messages', MessageViewSet)

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # Authentication endpoints
    path('api/auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('api/auth/register/', UserRegistrationView.as_view(), name='user_register'),
    path('api/auth/profile/', UserProfileView.as_view(), name='user_profile'),
    path('api/auth/logout/', LogoutView.as_view(), name='user_logout'),
    
    # API endpoints
    path('api/', include(router.urls)),
    
    # Nested routing for messages within conversations
    path('api/conversations/<uuid:conversation_pk>/messages/', 
         MessageViewSet.as_view({'get': 'list', 'post': 'create'}), 
         name='conversation-messages'),
    
    # Django REST Framework browsable API (for development)
    path('api-auth/', include('rest_framework.urls')),
]