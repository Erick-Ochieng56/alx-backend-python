
# messaging_app/chats/urls.py

from django.urls import path, include
from rest_framework import routers
from .views import UserViewSet, ConversationViewSet, MessageViewSet

# Create a router and register our viewsets with it
router = routers.DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'conversations', ConversationViewSet, basename='conversation')
router.register(r'messages', MessageViewSet, basename='message')

# The API URLs are now determined automatically by the router
urlpatterns = [
    path('api/', include(router.urls)),
]
