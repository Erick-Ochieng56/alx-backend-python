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
from .permissions import (
    ConversationPermission, MessagePermission, UserPermission,
    IsParticipantInConversation, IsMessageSender
)


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing users with proper authentication
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, UserPermission]
    lookup_field = 'user_id'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['username', 'first_name', 'last_name', 'email']
    filterset_fields = ['is_active', 'date_joined']
    
    def get_queryset(self):
        """
        Filter users and allow search functionality
        """
        queryset = User.objects.filter(is_active=True)  # Only show active users
        search = self.request.query_params.get('search', None)
        if search is not None:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search)
            )
        return queryset
    
    def update(self, request, *args, **kwargs):
        """
        Only allow users to update their own profile
        """
        user = self.get_object()
        if user != request.user:
            return Response(
                {'error': 'You can only update your own profile'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """
        Only allow users to deactivate their own account
        """
        user = self.get_object()
        if user != request.user:
            return Response(
                {'error': 'You can only deactivate your own account'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Instead of deleting, deactivate the user
        user.is_active = False
        user.save()
        return Response(
            {'message': 'Account deactivated successfully'},
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """
        Get current user's profile
        """
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['patch'])
    def update_profile(self, request):
        """
        Update current user's profile
        """
        serializer = self.get_serializer(
            request.user, 
            data=request.data, 
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ConversationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing conversations with authentication and permissions
    """
    permission_classes = [IsAuthenticated, ConversationPermission]
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
        Create a new conversation with authenticated user as participant
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Ensure current user is included in participants
        participant_ids = request.data.get('participant_ids', [])
        if request.user.user_id not in participant_ids:
            participant_ids.append(request.user.user_id)
        
        # Validate all participant IDs exist
        valid_participants = User.objects.filter(
            user_id__in=participant_ids,
            is_active=True
        )
        if valid_participants.count() != len(participant_ids):
            return Response(
                {'error': 'One or more participants not found or inactive'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
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
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsParticipantInConversation])
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
            user = User.objects.get(user_id=user_id, is_active=True)
            
            # Check if user is already a participant
            if conversation.participants.filter(user_id=user_id).exists():
                return Response(
                    {'error': 'User is already a participant in this conversation'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            conversation.participants.add(user)
            return Response(
                {'message': f'User {user.username} added to conversation'},
                status=status.HTTP_200_OK
            )
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found or inactive'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsParticipantInConversation])
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
        
        # Prevent removing self from conversation
        if user_id == request.user.user_id:
            return Response(
                {'error': 'Use leave_conversation action to leave a conversation'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(user_id=user_id)
            
            # Check if user is actually a participant
            if not conversation.participants.filter(user_id=user_id).exists():
                return Response(
                    {'error': 'User is not a participant in this conversation'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
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
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsParticipantInConversation])
    def leave_conversation(self, request, conversation_id=None):
        """
        Allow current user to leave a conversation
        """
        conversation = self.get_object()
        
        # Check if this is the only participant
        if conversation.participants.count() == 1:
            return Response(
                {'error': 'Cannot leave conversation - you are the only participant'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        conversation.participants.remove(request.user)
        return Response(
            {'message': 'Successfully left the conversation'},
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated, IsParticipantInConversation])
    def participants(self, request, conversation_id=None):
        """
        Get list of participants in a conversation
        """
        conversation = self.get_object()
        participants = conversation.participants.filter(is_active=True)
        serializer = UserSerializer(participants, many=True)
        return Response(serializer.data)


class MessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing messages with authentication and permissions
    """
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated, MessagePermission]
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
        Create a new message with authentication checks
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
        
        # Check if message is within edit time limit (optional)
        # from django.utils import timezone
        # from datetime import timedelta
        # if timezone.now() - message.timestamp > timedelta(minutes=15):
        #     return Response(
        #         {'error': 'Message can only be edited within 15 minutes of sending'},
        #         status=status.HTTP_403_FORBIDDEN
        #     )
        
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
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsMessageSender])
    def mark_as_read(self, request, message_id=None):
        """
        Mark a message as read by the current user
        """
        message = self.get_object()
        
        # This would require a MessageRead model to track read status
        # For now, we'll return a simple success response
        return Response(
            {'message': 'Message marked as read'},
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """
        Get count of unread messages for the current user
        """
        # This would require implementing read status tracking
        # For now, return a placeholder
        return Response(
            {'unread_count': 0},
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['post'])
    def mark_conversation_as_read(self, request):
        """
        Mark all messages in a conversation as read
        """
        conversation_id = request.data.get('conversation_id')
        if not conversation_id:
            return Response(
                {'error': 'conversation_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            conversation = Conversation.objects.get(
                conversation_id=conversation_id,
                participants=request.user
            )
            
            # Implementation would mark all messages as read
            # For now, return success
            return Response(
                {'message': 'All messages in conversation marked as read'},
                status=status.HTTP_200_OK
            )
        except Conversation.DoesNotExist:
            return Response(
                {'error': 'Conversation not found or you are not a participant'},
                status=status.HTTP_404_NOT_FOUND
            )