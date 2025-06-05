# messaging_app/chats/views.py

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from .models import User, Conversation, Message
from .serializers import (
    UserSerializer, ConversationSerializer, ConversationListSerializer,
    MessageSerializer
)


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing users
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'user_id'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['username', 'first_name', 'last_name', 'email']
    filterset_fields = ['is_active', 'date_joined']
    
    def get_queryset(self):
        """
        Optionally filter users by search query
        """
        queryset = User.objects.all()
        search = self.request.query_params.get('search', None)
        if search is not None:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search)
            )
        return queryset


class ConversationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing conversations
    """
    permission_classes = [IsAuthenticated]
    lookup_field = 'conversation_id'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title']
    filterset_fields = ['is_group', 'created_at']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-updated_at']
    
    def get_queryset(self):
        """
        Return conversations where the current user is a participant
        """
        return Conversation.objects.filter(
            participants=self.request.user
        ).prefetch_related('participants', 'messages__sender')
    
    def get_serializer_class(self):
        """
        Use different serializers for list and detail views
        """
        if self.action == 'list':
            return ConversationListSerializer
        return ConversationSerializer
    
    def create(self, request, *args, **kwargs):
        """
        Create a new conversation
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Ensure current user is included in participants
        participant_ids = request.data.get('participant_ids', [])
        if request.user.user_id not in participant_ids:
            participant_ids.append(request.user.user_id)
        
        # Update the serializer data
        mutable_data = request.data.copy()
        mutable_data['participant_ids'] = participant_ids
        serializer = self.get_serializer(data=mutable_data)
        serializer.is_valid(raise_exception=True)
        
        conversation = serializer.save()
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, 
            status=status.HTTP_201_CREATED, 
            headers=headers
        )
    
    @action(detail=True, methods=['post'])
    def add_participant(self, request, conversation_id=None):
        """
        Add a participant to an existing conversation
        """
        conversation = self.get_object()
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(user_id=user_id)
            conversation.participants.add(user)
            return Response(
                {'message': f'User {user.username} added to conversation'},
                status=status.HTTP_200_OK
            )
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def remove_participant(self, request, conversation_id=None):
        """
        Remove a participant from a conversation
        """
        conversation = self.get_object()
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(user_id=user_id)
            conversation.participants.remove(user)
            return Response(
                {'message': f'User {user.username} removed from conversation'},
                status=status.HTTP_200_OK
            )
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class MessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing messages
    """
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'message_id'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['content']
    filterset_fields = ['conversation', 'sender', 'timestamp', 'message_type']
    ordering_fields = ['timestamp']
    ordering = ['timestamp']
    
    def get_queryset(self):
        """
        Return messages from conversations where the current user is a participant
        """
        user_conversations = Conversation.objects.filter(
            participants=self.request.user
        )
        
        queryset = Message.objects.filter(
            conversation__in=user_conversations
        ).select_related('sender', 'conversation')
        
        # Handle nested routing - filter by conversation if it's in the URL path
        if 'conversation_pk' in self.kwargs:
            conversation_id = self.kwargs['conversation_pk']
            queryset = queryset.filter(conversation__conversation_id=conversation_id)
        
        # Also handle query parameter for backward compatibility
        conversation_id = self.request.query_params.get('conversation_id', None)
        if conversation_id:
            queryset = queryset.filter(conversation__conversation_id=conversation_id)
        
        return queryset
    
    def create(self, request, *args, **kwargs):
        """
        Create a new message
        """
        # Automatically set the sender to the current user
        mutable_data = request.data.copy()
        mutable_data['sender_id'] = request.user.user_id
        
        # Handle nested routing - get conversation from URL path
        if 'conversation_pk' in self.kwargs:
            mutable_data['conversation'] = self.kwargs['conversation_pk']
        
        serializer = self.get_serializer(data=mutable_data)
        serializer.is_valid(raise_exception=True)
        
        # Verify user is participant in the conversation
        conversation_id = mutable_data.get('conversation')
        try:
            conversation = Conversation.objects.get(conversation_id=conversation_id)
            if not conversation.participants.filter(user_id=request.user.user_id).exists():
                return Response(
                    {'error': 'You are not a participant in this conversation'},
                    status=status.HTTP_403_FORBIDDEN
                )
        except Conversation.DoesNotExist:
            return Response(
                {'error': 'Conversation not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        message = serializer.save()
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )
    
    def update(self, request, *args, **kwargs):
        """
        Update a message (only if user is the sender)
        """
        message = self.get_object()
        if message.sender != request.user:
            return Response(
                {'error': 'You can only edit your own messages'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete a message (only if user is the sender)
        """
        message = self.get_object()
        if message.sender != request.user:
            return Response(
                {'error': 'You can only delete your own messages'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)