from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class UnreadMessagesManager(models.Manager):
    """Custom manager for filtering unread messages for a specific user."""
    
    def unread_for_user(self, user):
        """Return unread messages for a specific user."""
        return self.filter(receiver=user, read=False).only(
            'id', 'sender__username', 'content', 'timestamp', 'read'
        )


class Message(models.Model):
    """Model for storing messages between users."""
    sender = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='chats_sent_messages'
    )
    receiver = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='chats_received_messages'
    )
    content = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    edited = models.BooleanField(default=False)
    read = models.BooleanField(default=False)
    parent_message = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='replies'
    )
    
    # Custom managers
    objects = models.Manager()  # Default manager
    unread = UnreadMessagesManager()  # Custom manager for unread messages
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"Message from {self.sender.username} to {self.receiver.username}"
    
    def get_thread(self):
        """Get all messages in this thread (recursive)."""
        def get_replies(message):
            replies = []
            for reply in message.replies.all():
                replies.append(reply)
                replies.extend(get_replies(reply))
            return replies
        
        # If this is a reply, get the root message
        root_message = self
        while root_message.parent_message:
            root_message = root_message.parent_message
        
        # Get all replies recursively
        thread = [root_message]
        thread.extend(get_replies(root_message))
        return thread


class Notification(models.Model):
    """Model for storing notifications."""
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='chats_notifications'
    )
    message = models.ForeignKey(
        Message, 
        on_delete=models.CASCADE, 
        related_name='chats_notifications'
    )
    content = models.CharField(max_length=255)
    timestamp = models.DateTimeField(default=timezone.now)
    read = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"Notification for {self.user.username}: {self.content}"


class MessageHistory(models.Model):
    """Model for storing message edit history."""
    message = models.ForeignKey(
        Message, 
        on_delete=models.CASCADE, 
        related_name='edit_history'
    )
    old_content = models.TextField()
    edited_at = models.DateTimeField(default=timezone.now)
    edited_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='message_edits'
    )
    
    class Meta:
        ordering = ['-edited_at']
    
    def __str__(self):
        return f"Edit history for message {self.message.id}"