from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Message, Notification, MessageHistory


@receiver(post_save, sender=Message)
def create_message_notification(sender, instance, created, **kwargs):
    """
    Signal to create a notification when a new message is created.
    Task 0: Automatically notify users when they receive a new message.
    """
    if created:
        # Create notification for the receiver
        notification_content = f"You have a new message from {instance.sender.username}"
        Notification.objects.create(
            user=instance.receiver,
            message=instance,
            content=notification_content
        )


@receiver(pre_save, sender=Message)
def log_message_edit(sender, instance, **kwargs):
    """
    Signal to log message edits before saving.
    Task 1: Log when a user edits a message and save the old content.
    """
    if instance.pk:  # Only for existing messages (updates)
        try:
            # Get the old message content
            old_message = Message.objects.get(pk=instance.pk)
            
            # Check if content has changed
            if old_message.content != instance.content:
                # Log the old content in MessageHistory
                MessageHistory.objects.create(
                    message=old_message,
                    old_content=old_message.content,
                    edited_by=instance.sender  # Assuming sender is the editor
                )
                
                # Mark the message as edited
                instance.edited = True
                
        except Message.DoesNotExist:
            # Handle case where message doesn't exist yet
            pass


@receiver(post_delete, sender=User)
def cleanup_user_data(sender, instance, **kwargs):
    """
    Signal to clean up user-related data when a user is deleted.
    Task 2: Automatically clean up related data when a user deletes their account.
    """
    # Clean up messages sent by the deleted user
    sent_messages = Message.objects.filter(sender=instance)
    sent_messages.delete()
    
    # Clean up messages received by the deleted user
    received_messages = Message.objects.filter(receiver=instance)
    received_messages.delete()
    
    # Clean up notifications for the deleted user
    user_notifications = Notification.objects.filter(user=instance)
    user_notifications.delete()


@receiver(post_save, sender=Message)
def cleanup_old_notifications(sender, instance, created, **kwargs):
    """
    Signal to clean up old notifications to prevent notification overflow.
    """
    if created:
        # Keep only the latest 50 notifications per user
        user_notifications = Notification.objects.filter(user=instance.receiver).order_by('-created_at')
        if user_notifications.count() > 50:
            old_notifications = user_notifications[50:]
            notification_ids = [notif.id for notif in old_notifications]
            Notification.objects.filter(id__in=notification_ids).delete()


# Additional utility functions for signal management
def disconnect_signals():
    """Utility function to disconnect signals during testing."""
    post_save.disconnect(create_message_notification, sender=Message)
    pre_save.disconnect(log_message_edit, sender=Message)
    post_delete.disconnect(cleanup_user_data, sender=User)
    post_save.disconnect(cleanup_old_notifications, sender=Message)


def reconnect_signals():
    """Utility function to reconnect signals after testing."""
    post_save.connect(create_message_notification, sender=Message)
    pre_save.connect(log_message_edit, sender=Message)
    post_delete.connect(cleanup_user_data, sender=User)
    post_save.connect(cleanup_old_notifications, sender=Message)