from django.test import TestCase
from django.contrib.auth.models import User
from django.db import connection
from django.test.utils import override_settings
from .models import Message, Notification, MessageHistory
from .signals import disconnect_signals, reconnect_signals


class SignalTestCase(TestCase):
    """Test case for Django signals functionality."""
    
    def setUp(self):
        """Set up test users."""
        self.user1 = User.objects.create_user(
            username='testuser1',
            email='test1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123'
        )
    
    def tearDown(self):
        """Clean up after tests."""
        # Ensure signals are reconnected after each test
        reconnect_signals()
    
    def test_message_notification_signal(self):
        """Test that notifications are created when messages are sent."""
        # Create a message
        message = Message.objects.create(
            sender=self.user1,
            receiver=self.user2,
            content="Hello, this is a test message!"
        )
        
        # Check that a notification was created
        notifications = Notification.objects.filter(user=self.user2, message=message)
        self.assertEqual(notifications.count(), 1)
        
        notification = notifications.first()
        self.assertEqual(notification.user, self.user2)
        self.assertEqual(notification.message, message)
        self.assertIn(self.user1.username, notification.content)
    
    def test_message_edit_logging_signal(self):
        """Test that message edits are logged."""
        # Create a message
        message = Message.objects.create(
            sender=self.user1,
            receiver=self.user2,
            content="Original content"
        )
        
        # Edit the message
        message.content = "Edited content"
        message.save()
        
        # Check that edit history was created
        history = MessageHistory.objects.filter(message=message)
        self.assertEqual(history.count(), 1)
        
        history_entry = history.first()
        self.assertEqual(history_entry.old_content, "Original content")
        self.assertEqual(history_entry.edited_by, self.user1)
        self.assertTrue(message.edited)
    
    def test_user_deletion_cleanup(self):
        """Test that user deletion cleans up related data."""
        # Create messages and notifications
        message = Message.objects.create(
            sender=self.user1,
            receiver=self.user2,
            content="Test message"
        )
        
        # Verify notification was created
        self.assertEqual(Notification.objects.filter(user=self.user2).count(), 1)
        
        # Delete the user
        user2_id = self.user2.id
        self.user2.delete()
        
        # Check that messages and notifications are deleted (CASCADE)
        self.assertEqual(Message.objects.filter(receiver_id=user2_id).count(), 0)
        self.assertEqual(Notification.objects.filter(user_id=user2_id).count(), 0)
    
    def test_signals_can_be_disconnected(self):
        """Test that signals can be disconnected for testing."""
        # Disconnect signals
        disconnect_signals()
        
        # Create a message
        message = Message.objects.create(
            sender=self.user1,
            receiver=self.user2,
            content="Test message without signals"
        )
        
        # Check that no notification was created
        notifications = Notification.objects.filter(user=self.user2, message=message)
        self.assertEqual(notifications.count(), 0)


class MessageModelTestCase(TestCase):
    """Test case for Message model functionality."""
    
    def setUp(self):
        """Set up test users."""
        self.user1 = User.objects.create_user(
            username='testuser1',
            email='test1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123'
        )
    
    def test_threaded_conversations(self):
        """Test threaded conversation functionality."""
        # Create a root message
        root_message = Message.objects.create(
            sender=self.user1,
            receiver=self.user2,
            content="Root message"
        )
        
        # Create replies
        reply1 = Message.objects.create(
            sender=self.user2,
            receiver=self.user1,
            content="Reply 1",
            parent_message=root_message
        )
        
        reply2 = Message.objects.create(
            sender=self.user1,
            receiver=self.user2,
            content="Reply 2",
            parent_message=reply1
        )
        
        # Test thread retrieval
        thread = root_message.get_thread()
        self.assertEqual(len(thread), 3)
        self.assertIn(root_message, thread)
        self.assertIn(reply1, thread)
        self.assertIn(reply2, thread)
    
    def test_unread_messages_manager(self):
        """Test the custom UnreadMessagesManager."""
        # Create messages
        Message.objects.create(
            sender=self.user1,
            receiver=self.user2,
            content="Unread message 1",
            read=False
        )
        
        Message.objects.create(
            sender=self.user1,
            receiver=self.user2,
            content="Read message",
            read=True
        )
        
        Message.objects.create(
            sender=self.user1,
            receiver=self.user2,
            content="Unread message 2",
            read=False
        )
        
        # Test unread messages for user2
        unread_messages = Message.unread.unread_for_user(self.user2)
        self.assertEqual(unread_messages.count(), 2)
        
        # Test that only specific fields are selected
        with self.assertNumQueries(1):
            list(unread_messages)  # Force evaluation


class PerformanceTestCase(TestCase):
    """Test case for performance optimizations."""
    
    def setUp(self):
        """Set up test data."""
        self.users = []
        for i in range(5):
            user = User.objects.create_user(
                username=f'testuser{i}',
                email=f'test{i}@example.com',
                password='testpass123'
            )
            self.users.append(user)
        
        # Create messages with replies
        self.root_message = Message.objects.create(
            sender=self.users[0],
            receiver=self.users[1],
            content="Root message"
        )
        
        for i in range(3):
            Message.objects.create(
                sender=self.users[i % len(self.users)],
                receiver=self.users[(i + 1) % len(self.users)],
                content=f"Reply {i}",
                parent_message=self.root_message
            )
    
    def test_select_related_optimization(self):
        """Test that select_related reduces queries."""
        # Without select_related
        with self.assertNumQueries(4):  # 1 for messages + 3 for related users
            messages = Message.objects.all()
            for message in messages:
                _ = message.sender.username
                _ = message.receiver.username
        
        # With select_related
        with self.assertNumQueries(1):  # Only 1 query with JOINs
            messages = Message.objects.select_related('sender', 'receiver').all()
            for message in messages:
                _ = message.sender.username
                _ = message.receiver.username
    
    def test_prefetch_related_optimization(self):
        """Test that prefetch_related optimizes reverse relationships."""
        # Without prefetch_related
        with self.assertNumQueries(2):  # 1 for users + 1 for each user's messages
            users = User.objects.all()
            for user in users:
                list(user.sent_messages.all())
        
        # With prefetch_related
        with self.assertNumQueries(2):  # 1 for users + 1 for all messages
            users = User.objects.prefetch_related('sent_messages').all()
            for user in users:
                list(user.sent_messages.all())