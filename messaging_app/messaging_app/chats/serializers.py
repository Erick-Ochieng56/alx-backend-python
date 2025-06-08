# messaging_app/chats/serializers.py

from rest_framework import serializers
from .models import User, Conversation, Message


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model with essential fields
    """
    # Add CharField for computed full name
    full_name = serializers.CharField(read_only=True)
    
    class Meta:
        model = User
        fields = [
            'user_id', 'username', 'email', 'first_name', 
            'last_name', 'phone_number', 'full_name', 'created_at'
        ]
        read_only_fields = ['user_id', 'created_at']
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Compute full_name using CharField
        data['full_name'] = f"{instance.first_name} {instance.last_name}".strip()
        return data


class MessageSerializer(serializers.ModelSerializer):
    """
    Serializer for Message model with sender details
    """
    # Nested relationship: Include full sender details
    sender = UserSerializer(read_only=True)
    sender_id = serializers.UUIDField(write_only=True, source='sender.user_id')
    
    # CharField for message preview (truncated version)
    message_preview = serializers.CharField(read_only=True)
    
    class Meta:
        model = Message
        fields = [
            'message_id', 'sender', 'sender_id', 'conversation', 
            'message_body', 'message_preview', 'sent_at'
        ]
        read_only_fields = ['message_id', 'sent_at']
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Create message preview using CharField
        body = instance.message_body
        data['message_preview'] = body[:50] + '...' if len(body) > 50 else body
        return data
    
    def create(self, validated_data):
        """
        Create a new message and ensure sender is part of the conversation
        """
        sender_data = validated_data.pop('sender', {})
        sender_id = sender_data.get('user_id')
        
        if sender_id:
            try:
                sender = User.objects.get(user_id=sender_id)
                validated_data['sender'] = sender
            except User.DoesNotExist:
                raise serializers.ValidationError("Invalid sender ID")
        
        # Verify sender is participant in the conversation
        conversation = validated_data['conversation']
        if not conversation.participants.filter(user_id=sender.user_id).exists():
            raise serializers.ValidationError(
                "Sender must be a participant in the conversation"
            )
        
        return super().create(validated_data)


class ConversationSerializer(serializers.ModelSerializer):
    """
    Serializer for Conversation model with participants and messages
    Enhanced with proper nested relationships and CharField usage
    """
    # Nested relationships: Include full participant and message details
    participants = UserSerializer(many=True, read_only=True)
    participant_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False
    )
    messages = MessageSerializer(many=True, read_only=True)
    latest_message = serializers.SerializerMethodField()
    message_count = serializers.SerializerMethodField()
    
    # CharField additions for enhanced functionality
    conversation_title = serializers.CharField(
        max_length=100, 
        required=False, 
        allow_blank=True,
        help_text="Custom title for the conversation"
    )
    participant_summary = serializers.CharField(read_only=True)
    
    class Meta:
        model = Conversation
        fields = [
            'conversation_id', 'participants', 'participant_ids',
            'messages', 'latest_message', 'message_count',
            'conversation_title', 'participant_summary',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['conversation_id', 'created_at', 'updated_at']
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Create participant summary using CharField
        participant_names = [p.username for p in instance.participants.all()]
        data['participant_summary'] = ', '.join(participant_names) if participant_names else 'No participants'
        return data
    
    def get_latest_message(self, obj):
        """Get the latest message in the conversation with nested sender info"""
        latest = obj.latest_message
        if latest:
            return {
                'message_id': latest.message_id,
                'sender': {
                    'user_id': latest.sender.user_id,
                    'username': latest.sender.username,
                    'full_name': f"{latest.sender.first_name} {latest.sender.last_name}".strip()
                },
                'message_body': latest.message_body,
                'sent_at': latest.sent_at
            }
        return None
    
    def get_message_count(self, obj):
        """Get total number of messages in the conversation"""
        return obj.messages.count()
    
    def create(self, validated_data):
        """
        Create a new conversation with specified participants
        Properly handles nested relationships
        """
        participant_ids = validated_data.pop('participant_ids', [])
        conversation_title = validated_data.pop('conversation_title', '')
        
        conversation = Conversation.objects.create()
        
        # Handle nested relationship: Add participants to the conversation
        if participant_ids:
            participants = User.objects.filter(user_id__in=participant_ids)
            if participants.count() != len(participant_ids):
                conversation.delete()
                raise serializers.ValidationError(
                    "One or more participant IDs are invalid"
                )
            conversation.participants.set(participants)
        
        # If you have a title field in your model, uncomment this:
        # if conversation_title:
        #     conversation.title = conversation_title
        #     conversation.save()
        
        return conversation


class ConversationListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for listing conversations without full message details
    Optimized nested relationships for list views
    """
    # Nested relationship: Include participant info but not full message details
    participants = UserSerializer(many=True, read_only=True)
    latest_message = serializers.SerializerMethodField()
    message_count = serializers.SerializerMethodField()
    
    # CharField for display purposes
    display_name = serializers.CharField(read_only=True)
    last_activity = serializers.CharField(read_only=True)
    
    class Meta:
        model = Conversation
        fields = [
            'conversation_id', 'participants', 'latest_message',
            'message_count', 'display_name', 'last_activity',
            'created_at', 'updated_at'
        ]
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        
        # Create display name using CharField
        participant_names = [p.username for p in instance.participants.all()[:3]]
        if len(instance.participants.all()) > 3:
            data['display_name'] = f"{', '.join(participant_names)} and {len(instance.participants.all()) - 3} others"
        else:
            data['display_name'] = ', '.join(participant_names) if participant_names else 'Empty conversation'
        
        # Format last activity using CharField
        if hasattr(instance, 'updated_at') and instance.updated_at:
            data['last_activity'] = instance.updated_at.strftime("%Y-%m-%d %H:%M")
        else:
            data['last_activity'] = "No recent activity"
        
        return data
    
    def get_latest_message(self, obj):
        """Get the latest message summary with nested sender info"""
        latest = obj.latest_message
        if latest:
            return {
                'sender': {
                    'username': latest.sender.username,
                    'full_name': f"{latest.sender.first_name} {latest.sender.last_name}".strip()
                },
                'message_body': latest.message_body[:100] + '...' if len(latest.message_body) > 100 else latest.message_body,
                'sent_at': latest.sent_at
            }
        return None
    
    def get_message_count(self, obj):
        """Get total number of messages in the conversation"""
        return obj.messages.count()


# Additional serializer demonstrating CharField usage for search/filtering
class ConversationSearchSerializer(serializers.Serializer):
    """
    Serializer for conversation search parameters using CharField
    """
    search_term = serializers.CharField(
        max_length=200,
        required=False,
        help_text="Search in conversation messages"
    )
    
    participant_username = serializers.CharField(
        max_length=150,
        required=False,
        help_text="Filter by participant username"
    )
    
    date_range = serializers.CharField(
        required=False,
        help_text="Date range filter (e.g., 'last_week', 'last_month')"
    )