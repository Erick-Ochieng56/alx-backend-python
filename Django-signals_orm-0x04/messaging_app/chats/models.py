from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Q


class UnreadMessagesManager(models.Manager):
    """
    Custom manager for handling unread messages.
    Task 4: Custom manager to efficiently query unread messages.
    """
    
    def get_queryset(self):
        """Return only unread messages with optimized query."""
        return super().get_queryset().filter(read=False).only(
            'id', 'sender', 'receiver', 'content', 'timestamp', 'read'
        ).select_related('sender', 'receiver')
    
    def unread_for_user(self, user):
        """Get all unread messages for a specific user."""
        return self.get_queryset().filter(receiver=user)
    
    def unread_count_for_user(self, user):
        """Get count of unread messages for a specific user."""
        return self.unread_for_user(user).count()
    
    def mark_all_read_for_user(self, user):
        """Mark all messages as read for a specific user."""
        return self.unread_for_user(user).update(read=True)


class Message(models.Model):
    """
    Main Message model with support for threading and tracking edits.
    Supports all the functionality needed for the views and signals.
    """
    sender = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='messaging_sent_messages'  # Changed from 'sent_messages'
    )
    receiver = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='messaging_received_messages'  # Changed from 'received_messages'
    )
    content = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    read = models.BooleanField(default=False)
    
    # Threading support
    parent_message = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='replies'
    )
    
    # Edit tracking (Task 1)
    edited = models.BooleanField(default=False)
    last_edited = models.DateTimeField(null=True, blank=True)
    
    # Managers
    objects = models.Manager()  # Default manager
    unread = UnreadMessagesManager()  # Custom manager for unread messages
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['receiver', 'read']),
            models.Index(fields=['sender', 'timestamp']),
            models.Index(fields=['parent_message']),
        ]
    
    def __str__(self):
        return f"From {self.sender.username} to {self.receiver.username}: {self.content[:50]}..."
    
    def save(self, *args, **kwargs):
        """Override save to update last_edited timestamp."""
        if self.pk and self.edited:  # Existing message being edited
            self.last_edited = timezone.now()
        super().save(*args, **kwargs)
    
    def get_thread(self):
        """
        Get all messages in this thread (recursive method).
        Task 3: Support for threaded conversations.
        """
        if self.parent_message:
            # If this is a reply, get the root message's thread
            return self.parent_message.get_thread()
        else:
            # This is the root message, get all replies recursively
            return Message.objects.filter(
                Q(id=self.id) |
                Q(parent_message=self) |
                Q(parent_message__parent_message=self) |
                Q(parent_message__parent_message__parent_message=self)  # Support deeper nesting
            ).select_related('sender', 'receiver', 'parent_message').order_by('timestamp')
    
    def get_replies(self):
        """Get direct replies to this message."""
        return self.replies.all().select_related('sender', 'receiver')
    
    def is_thread_root(self):
        """Check if this message is the root of a thread."""
        return self.parent_message is None
    
    def get_thread_participants(self):
        """Get all users who have participated in this thread."""
        thread_messages = self.get_thread()
        participants = set()
        for message in thread_messages:
            participants.add(message.sender)
            participants.add(message.receiver)
        return list(participants)
    
    @property
    def has_replies(self):
        """Check if this message has any replies."""
        return self.replies.exists()
    
    @property
    def reply_count(self):
        """Get the number of direct replies to this message."""
        return self.replies.count()


class MessageHistory(models.Model):
    """
    Model to store message edit history.
    Task 1: Log message edits and store old content.
    """
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
        related_name='messaging_message_edits'  # Changed from 'message_edits'
    )
    
    class Meta:
        ordering = ['-edited_at']
        verbose_name_plural = "Message histories"
    
    def __str__(self):
        return f"Edit history for message {self.message.id} at {self.edited_at}"


class Notification(models.Model):
    """
    Model for user notifications.
    Task 0: Notify users when they receive new messages.
    """
    NOTIFICATION_TYPES = [
        ('message', 'New Message'),
        ('reply', 'Message Reply'),
        ('mention', 'User Mention'),
        ('system', 'System Notification'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='messaging_notifications'  # Changed from 'notifications'
    )
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='notifications',
        null=True,
        blank=True
    )
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        default='message'
    )
    content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    read = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'read']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Notification for {self.user.username}: {self.content[:50]}..."
    
    def mark_as_read(self):
        """Mark this notification as read."""
        self.read = True
        self.save()
    
    @classmethod
    def unread_count_for_user(cls, user):
        """Get count of unread notifications for a user."""
        return cls.objects.filter(user=user, read=False).count()
    
    @classmethod
    def mark_all_read_for_user(cls, user):
        """Mark all notifications as read for a user."""
        return cls.objects.filter(user=user, read=False).update(read=True)


class UserProfile(models.Model):
    """
    Extended user profile for additional messaging features.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='messaging_profile'  # Changed from 'profile' to avoid conflicts
    )
    last_seen = models.DateTimeField(null=True, blank=True)
    email_notifications = models.BooleanField(default=True)
    message_privacy = models.CharField(
        max_length=20,
        choices=[
            ('public', 'Anyone can message me'),
            ('friends', 'Only friends can message me'),
            ('private', 'No one can message me'),
        ],
        default='public'
    )
    
    def __str__(self):
        return f"Profile for {self.user.username}"
    
    def update_last_seen(self):
        """Update the last seen timestamp."""
        self.last_seen = timezone.now()
        self.save()
    
    @property
    def is_online(self):
        """Check if user was active in the last 5 minutes."""
        if not self.last_seen:
            return False
        return (timezone.now() - self.last_seen).seconds < 300


class MessageAttachment(models.Model):
    """
    Model for message attachments (optional enhancement).
    """
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    file = models.FileField(upload_to='message_attachments/')
    filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()
    uploaded_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"Attachment: {self.filename} for message {self.message.id}"


class Conversation(models.Model):
    """
    Model to group related messages into conversations (optional enhancement).
    """
    participants = models.ManyToManyField(User, related_name='messaging_conversations')  # Changed from 'conversations'
    title = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    last_message = models.ForeignKey(
        Message,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='last_message_in_conversation'
    )
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        if self.title:
            return self.title
        return f"Conversation {self.id}"
    
    def get_messages(self):
        """Get all messages in this conversation."""
        return Message.objects.filter(
            Q(sender__in=self.participants.all()) &
            Q(receiver__in=self.participants.all())
        ).order_by('timestamp')
    
    def add_participant(self, user):
        """Add a user to this conversation."""
        self.participants.add(user)
    
    def remove_participant(self, user):
        """Remove a user from this conversation."""
        self.participants.remove(user)
    
    @property
    def participant_count(self):
        """Get the number of participants in this conversation."""
        return self.participants.count()