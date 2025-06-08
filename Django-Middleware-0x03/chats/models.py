# messaging_app/chats/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
import uuid


class User(AbstractUser):
    """
    Extended User model with additional fields for messaging functionality
    """
    user_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)  # Added password field
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.username} ({self.first_name} {self.last_name})"


class Conversation(models.Model):
    """
    Model to represent a conversation between multiple users
    """
    conversation_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    participants = models.ManyToManyField(User, related_name='conversations')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        participant_names = ", ".join([user.username for user in self.participants.all()[:3]])
        if self.participants.count() > 3:
            participant_names += f" and {self.participants.count() - 3} others"
        return f"Conversation: {participant_names}"
    
    @property
    def latest_message(self):
        """Get the most recent message in this conversation"""
        return self.messages.order_by('-sent_at').first()


class Message(models.Model):
    """
    Model to represent individual messages within conversations
    """
    message_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='sent_messages'
    )
    conversation = models.ForeignKey(
        Conversation, 
        on_delete=models.CASCADE, 
        related_name='messages'
    )
    message_body = models.TextField()
    sent_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-sent_at']
    
    def __str__(self):
        return f"{self.sender.username}: {self.message_body[:50]}..."
    
    def save(self, *args, **kwargs):
        """Override save to update conversation's updated_at timestamp"""
        super().save(*args, **kwargs)
        # Update the conversation's updated_at field when a new message is added
        self.conversation.updated_at = self.sent_at
        self.conversation.save(update_fields=['updated_at'])