# messaging_app/chats/serializers.py

from rest_framework import serializers
from .models import User, Conversation, Message


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model with essential fields
    """
    class Meta:
        model = User
        fields = [
            'user_id', 'username', 'email', 'first_name', 
            'last_name', 'phone_number', 'created_at'
        ]
        read_only_fields = ['user_id', 'created_at']


class MessageSerializer(serializers.ModelSerializer):
    """
    Serializer for Message model with sender details
    """
    sender = UserSerializer(read_only=True)
    sender_id = serializers.UUIDField(write_only=True, source='sender.user_id')
    
    class Meta:
        model = Message
        fields = [
            'message_id', 'sender', 'sender_id', 'conversation', 
            'message_body', 'sent_at'
        ]
        read_only_fields = ['message_id', 'sent_at']
    
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
    """
    participants = UserSerializer(many=True, read_only=True)
    participant_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False
    )
    messages = MessageSerializer(many=True, read_only=True)
    latest_message = serializers.SerializerMethodField()
    message_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'conversation_id', 'participants', 'participant_ids',
            'messages', 'latest_message', 'message_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['conversation_id', 'created_at', 'updated_at']
    
    def get_latest_message(self, obj):
        """Get the latest message in the conversation"""
        latest = obj.latest_message
        if latest:
            return {
                'message_id': latest.message_id,
                'sender': latest.sender.username,
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
        """
        participant_ids = validated_data.pop('participant_ids', [])
        conversation = Conversation.objects.create()
        
        # Add participants to the conversation
        if participant_ids:
            participants = User.objects.filter(user_id__in=participant_ids)
            if participants.count() != len(participant_ids):
                conversation.delete()
                raise serializers.ValidationError(
                    "One or more participant IDs are invalid"
                )
            conversation.participants.set(participants)
        
        return conversation


class ConversationListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for listing conversations without full message details
    """
    participants = UserSerializer(many=True, read_only=True)
    latest_message = serializers.SerializerMethodField()
    message_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'conversation_id', 'participants', 'latest_message',
            'message_count', 'created_at', 'updated_at'
        ]
    
    def get_latest_message(self, obj):
        """Get the latest message summary"""
        latest = obj.latest_message
        if latest:
            return {
                'sender': latest.sender.username,
                'message_body': latest.message_body[:100] + '...' if len(latest.message_body) > 100 else latest.message_body,
                'sent_at': latest.sent_at
            }
        return None
    
    def get_message_count(self, obj):
        """Get total number of messages in the conversation"""
        return obj.messages.count()