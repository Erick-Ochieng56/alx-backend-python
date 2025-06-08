# messaging_app/chats/views.py
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Prefetch
from django.utils import timezone
from datetime import timedelta

from .models import User, Conversation, Message
from .serializers import (
    UserSerializer, ConversationSerializer, ConversationListSerializer,
    MessageSerializer
)
from .permissions import (
    ConversationPermission, MessagePermission, UserPermission,
    IsParticipantInConversation, IsMessageSender
)
from .filters import (
    UserFilter, ConversationFilter, MessageFilter,
    MessageTimeRangeFilter, ConversationParticipantFilter
)
from .pagination import (
    UserPagination, ConversationPagination, MessagePagination,
    MessageInfiniteScrollPagination, SearchResultsPagination,
    LimitOffsetMessagePagination
)


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing users with proper authentication, pagination and filtering
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, UserPermission]
    lookup_field = 'user_id'
    
    # Pagination
    pagination_class = UserPagination
    
    # Filtering and search backends
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = UserFilter
    search_fields = ['username', 'first_name', 'last_name', 'email']
    ordering_fields = ['username', 'first_name', 'last_name', 'date_joined', 'is_active']
    ordering = ['username']
    
    def get_queryset(self):
        """
        Filter users and allow search functionality
        """
        queryset = User.objects.filter(is_active=True)
        
        # Additional custom filtering
        search = self.request.query_params.get('search', None)
        if search is not None:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search)
            )
        
        # Filter by recent activity (users who sent messages in last 30 days)
        if self.request.query_params.get('recently_active') == 'true':
            recent_date = timezone.now() - timedelta(days=30)
            queryset = queryset.filter(
                sent_messages__sent_at__gte=recent_date
            ).distinct()
        
        return queryset.distinct()
    
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
    
    @action(detail=False, methods=['get'], pagination_class=SearchResultsPagination)
    def search(self, request):
        """
        Advanced user search with custom pagination
        """
        query = request.query_params.get('q', '')
        if not query:
            return Response(
                {'error': 'Search query parameter "q" is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset().filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query)
        )
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class ConversationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing conversations with authentication, permissions, pagination and filtering
    """
    permission_classes = [IsAuthenticated, ConversationPermission]
    lookup_field = 'conversation_id'
    
    # Pagination
    pagination_class = ConversationPagination
    
    # Filtering and search backends
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ConversationFilter
    search_fields = ['title', 'participants__username', 'participants__first_name', 'participants__last_name']
    ordering_fields = ['created_at', 'updated_at', 'title']
    ordering = ['-updated_at']
    
    def get_queryset(self):
        """
        Return conversations where the current user is a participant with optimized queries
        """
        return Conversation.objects.filter(
            participants=self.request.user
        ).select_related().prefetch_related(
            'participants',
            Prefetch(
                'messages',
                queryset=Message.objects.select_related('sender').order_by('-sent_at')[:5],
                to_attr='recent_messages'
            )
        ).annotate(
            participant_count=Count('participants'),
            message_count=Count('messages')
        )
    
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
    
    @action(detail=False, methods=['get'], filterset_class=ConversationParticipantFilter)
    def with_participants(self, request):
        """
        Filter conversations with specific participants using specialized filter
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class MessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing messages with authentication, permissions, pagination and filtering
    """
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated, MessagePermission]
    lookup_field = 'message_id'
    
    # Default pagination
    pagination_class = MessagePagination
    
    # Filtering and search backends
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = MessageFilter
    search_fields = ['message_body', 'sender__username', 'sender__first_name', 'sender__last_name']
    ordering_fields = ['sent_at', 'sender__username']
    ordering = ['-sent_at']  # Most recent first by default
    
    def get_queryset(self):
        """
        Return messages from conversations where the current user is a participant
        """
        user_conversations = Conversation.objects.filter(
            participants=self.request.user
        )
        
        queryset = Message.objects.filter(
            conversation__in=user_conversations
        ).select_related('sender', 'conversation').prefetch_related(
            'conversation__participants'
        )
        
        # Handle nested routing - filter by conversation if it's in the URL path
        if 'conversation_pk' in self.kwargs:
            conversation_id = self.kwargs['conversation_pk']
            queryset = queryset.filter(conversation__conversation_id=conversation_id)
        
        # Also handle query parameter for backward compatibility
        conversation_id = self.request.query_params.get('conversation_id', None)
        if conversation_id:
            queryset = queryset.filter(conversation__conversation_id=conversation_id)
        
        return queryset
    
    def get_pagination_class(self):
        """
        Use different pagination classes based on query parameters
        """
        if self.request.query_params.get('infinite_scroll') == 'true':
            return MessageInfiniteScrollPagination
        elif self.request.query_params.get('use_offset') == 'true':
            return LimitOffsetMessagePagination
        return MessagePagination
    
    @property
    def paginator(self):
        """
        Override paginator property to use dynamic pagination class
        """
        if not hasattr(self, '_paginator'):
            if self.pagination_class is None:
                self._paginator = None
            else:
                pagination_class = self.get_pagination_class()
                self._paginator = pagination_class()
        return self._paginator
    
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
        if self.request.query_params.get('enforce_edit_limit') == 'true':
            if timezone.now() - message.sent_at > timedelta(minutes=15):
                return Response(
                    {'error': 'Message can only be edited within 15 minutes of sending'},
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
    
    @action(detail=False, methods=['get'], filterset_class=MessageTimeRangeFilter, 
            pagination_class=SearchResultsPagination)
    def time_range_search(self, request):
        """
        Advanced time-based message filtering with specialized pagination
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], pagination_class=SearchResultsPagination)
    def full_text_search(self, request):
        """
        Advanced full-text search across message content
        """
        query = request.query_params.get('q', '')
        if not query:
            return Response(
                {'error': 'Search query parameter "q" is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset().filter(
            Q(message_body__icontains=query) |
            Q(sender__username__icontains=query) |
            Q(sender__first_name__icontains=query) |
            Q(sender__last_name__icontains=query)
        )
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def recent_messages(self, request):
        """
        Get recent messages across all conversations for the user
        """
        # Get messages from last 24 hours by default
        hours = int(request.query_params.get('hours', 24))
        recent_date = timezone.now() - timedelta(hours=hours)
        
        queryset = self.get_queryset().filter(
            sent_at__gte=recent_date
        ).order_by('-sent_at')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Get message statistics for the current user
        """
        queryset = self.get_queryset()
        
        stats = {
            'total_messages': queryset.count(),
            'messages_sent': queryset.filter(sender=request.user).count(),
            'messages_received': queryset.exclude(sender=request.user).count(),
            'conversations_count': queryset.values('conversation').distinct().count(),
            'messages_today': queryset.filter(
                sent_at__date=timezone.now().date()
            ).count(),
            'messages_this_week': queryset.filter(
                sent_at__gte=timezone.now() - timedelta(days=7)
            ).count(),
        }
        
        return Response(stats)