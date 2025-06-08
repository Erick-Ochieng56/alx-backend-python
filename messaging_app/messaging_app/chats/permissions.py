# messaging_app/chats/permissions.py

from rest_framework import permissions
from .models import Conversation, Message


class IsParticipantInConversation(permissions.BasePermission):
    """
    Permission to check if user is a participant in the conversation
    """
    message = "You must be a participant in this conversation to access it."
    
    def has_permission(self, request, view):
        """
        Check if user is authenticated
        """
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        """
        Check if user is a participant in the conversation
        """
        if isinstance(obj, Conversation):
            return obj.participants.filter(user_id=request.user.user_id).exists()
        elif isinstance(obj, Message):
            return obj.conversation.participants.filter(user_id=request.user.user_id).exists()
        return False


class IsMessageSender(permissions.BasePermission):
    """
    Permission to check if user is the sender of the message
    """
    message = "You can only modify your own messages."
    
    def has_permission(self, request, view):
        """
        Check if user is authenticated
        """
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        """
        Check if user is the sender of the message
        """
        if isinstance(obj, Message):
            return obj.sender == request.user
        return False


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Permission to allow owners of an object to edit it.
    Assumes the model instance has an `owner` attribute.
    """
    message = "You can only modify your own content."
    
    def has_object_permission(self, request, view, obj):
        # Read permissions for any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions only to the owner
        return getattr(obj, 'owner', None) == request.user


class CanCreateConversation(permissions.BasePermission):
    """
    Permission to check if user can create a conversation
    """
    message = "You need to be authenticated to create conversations."
    
    def has_permission(self, request, view):
        """
        Only authenticated users can create conversations
        """
        if request.method == 'POST':
            return request.user and request.user.is_authenticated
        return True


class CanSendMessage(permissions.BasePermission):
    """
    Permission to check if user can send a message to a conversation
    """
    message = "You must be a participant in the conversation to send messages."
    
    def has_permission(self, request, view):
        """
        Check if user is authenticated and participant in conversation
        """
        if not (request.user and request.user.is_authenticated):
            return False
        
        if request.method == 'POST':
            # Check conversation_id from URL or data
            conversation_id = None
            
            # Check URL kwargs (nested routing)
            if hasattr(view, 'kwargs') and 'conversation_pk' in view.kwargs:
                conversation_id = view.kwargs['conversation_pk']
            
            # Check request data
            if not conversation_id and 'conversation' in request.data:
                conversation_id = request.data['conversation']
            
            if conversation_id:
                try:
                    conversation = Conversation.objects.get(conversation_id=conversation_id)
                    return conversation.participants.filter(user_id=request.user.user_id).exists()
                except Conversation.DoesNotExist:
                    return False
        
        return True


class ConversationPermission(permissions.BasePermission):
    """
    Combined permission class for conversation operations
    """
    def has_permission(self, request, view):
        """
        Check general permissions
        """
        if not (request.user and request.user.is_authenticated):
            return False
        
        # Allow creation for authenticated users
        if request.method == 'POST':
            return True
        
        return True
    
    def has_object_permission(self, request, view, obj):
        """
        Check object-level permissions
        """
        if isinstance(obj, Conversation):
            # User must be a participant to access the conversation
            is_participant = obj.participants.filter(user_id=request.user.user_id).exists()
            
            if request.method in permissions.SAFE_METHODS:
                # Read access for participants
                return is_participant
            else:
                # Write access for participants (can add/remove other participants)
                return is_participant
        
        return False


class MessagePermission(permissions.BasePermission):
    """
    Combined permission class for message operations
    """
    def has_permission(self, request, view):
        """
        Check general permissions
        """
        if not (request.user and request.user.is_authenticated):
            return False
        
        if request.method == 'POST':
            # Check if user can send message to the conversation
            conversation_id = None
            
            # Check URL kwargs (nested routing)
            if hasattr(view, 'kwargs') and 'conversation_pk' in view.kwargs:
                conversation_id = view.kwargs['conversation_pk']
            
            # Check request data
            if not conversation_id and 'conversation' in request.data:
                conversation_id = request.data['conversation']
            
            if conversation_id:
                try:
                    conversation = Conversation.objects.get(conversation_id=conversation_id)
                    return conversation.participants.filter(user_id=request.user.user_id).exists()
                except Conversation.DoesNotExist:
                    return False
        
        return True
    
    def has_object_permission(self, request, view, obj):
        """
        Check object-level permissions
        """
        if isinstance(obj, Message):
            # User must be participant in conversation to read
            is_participant = obj.conversation.participants.filter(user_id=request.user.user_id).exists()
            
            if request.method in permissions.SAFE_METHODS:
                # Read access for conversation participants
                return is_participant
            else:
                # Write access only for message sender
                return obj.sender == request.user and is_participant
        
        return False


class UserPermission(permissions.BasePermission):
    """
    Permission class for user operations
    """
    def has_permission(self, request, view):
        """
        Check general permissions
        """
        if not (request.user and request.user.is_authenticated):
            return False
        
        # Allow list and retrieve for authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Only allow users to update their own profile
        return True
    
    def has_object_permission(self, request, view, obj):
        """
        Check object-level permissions
        """
        if request.method in permissions.SAFE_METHODS:
            # Read access for authenticated users
            return True
        else:
            # Write access only for the user themselves
            return obj == request.user


class AdminOrReadOnly(permissions.BasePermission):
    """
    Permission that allows read-only access to any user,
    but write access only to admin users.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff