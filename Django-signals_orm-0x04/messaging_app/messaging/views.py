from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import logout
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from django.urls import reverse
import json

from .models import Message, Notification, MessageHistory


@login_required
def inbox(request):
    """Display user's inbox with received messages."""
    messages_list = Message.objects.filter(
        receiver=request.user
    ).select_related('sender').order_by('-timestamp')
    
    paginator = Paginator(messages_list, 20)
    page_number = request.GET.get('page')
    messages_page = paginator.get_page(page_number)
    
    # Get unread count
    unread_count = Message.unread.unread_for_user(request.user).count()
    
    context = {
        'messages': messages_page,
        'unread_count': unread_count,
        'page_title': 'Inbox'
    }
    return render(request, 'messaging/inbox.html', context)


@login_required
def sent_messages(request):
    """Display user's sent messages."""
    messages_list = Message.objects.filter(
        sender=request.user
    ).select_related('receiver').order_by('-timestamp')
    
    paginator = Paginator(messages_list, 20)
    page_number = request.GET.get('page')
    messages_page = paginator.get_page(page_number)
    
    context = {
        'messages': messages_page,
        'page_title': 'Sent Messages'
    }
    return render(request, 'messaging/sent_messages.html', context)


@login_required
def compose_message(request, recipient_id=None):
    """Compose and send a new message."""
    recipient = None
    if recipient_id:
        recipient = get_object_or_404(User, id=recipient_id)
    
    if request.method == 'POST':
        recipient_username = request.POST.get('recipient')
        content = request.POST.get('content')
        parent_message_id = request.POST.get('parent_message_id')
        
        if not recipient_username or not content:
            messages.error(request, 'Recipient and content are required.')
            return render(request, 'messaging/compose.html', {'recipient': recipient})
        
        try:
            recipient_user = User.objects.get(username=recipient_username)
        except User.DoesNotExist:
            messages.error(request, 'Recipient not found.')
            return render(request, 'messaging/compose.html', {'recipient': recipient})
        
        # Create the message
        parent_message = None
        if parent_message_id:
            parent_message = get_object_or_404(Message, id=parent_message_id)
        
        message = Message.objects.create(
            sender=request.user,
            receiver=recipient_user,
            content=content,
            parent_message=parent_message
        )
        
        # Create notification for recipient
        notification_content = f"New message from {request.user.username}"
        if parent_message:
            notification_content = f"Reply from {request.user.username}"
            
        Notification.objects.create(
            user=recipient_user,
            message=message,
            content=notification_content
        )
        
        messages.success(request, 'Message sent successfully!')
        return redirect('messaging:inbox')
    
    context = {
        'recipient': recipient,
        'page_title': 'Compose Message'
    }
    return render(request, 'messaging/compose.html', context)


@login_required
def view_message(request, message_id):
    """View a specific message and its thread."""
    message = get_object_or_404(Message, id=message_id)
    
    # Check if user has permission to view this message
    if message.sender != request.user and message.receiver != request.user:
        return HttpResponseForbidden("You don't have permission to view this message.")
    
    # Mark as read if user is the receiver
    if message.receiver == request.user and not message.read:
        message.read = True
        message.save(update_fields=['read'])
    
    # Get the full thread
    thread = message.get_thread()
    
    context = {
        'message': message,
        'thread': thread,
        'page_title': f'Message from {message.sender.username}'
    }
    return render(request, 'messaging/view_message.html', context)


@login_required
def reply_to_message(request, message_id):
    """Reply to a specific message."""
    parent_message = get_object_or_404(Message, id=message_id)
    
    # Check if user has permission to reply
    if parent_message.sender != request.user and parent_message.receiver != request.user:
        return HttpResponseForbidden("You don't have permission to reply to this message.")
    
    # Determine the recipient (the other person in the conversation)
    recipient = parent_message.sender if parent_message.receiver == request.user else parent_message.receiver
    
    if request.method == 'POST':
        content = request.POST.get('content')
        
        if not content:
            messages.error(request, 'Reply content is required.')
            return redirect('messaging:view_message', message_id=message_id)
        
        # Create the reply
        reply = Message.objects.create(
            sender=request.user,
            receiver=recipient,
            content=content,
            parent_message=parent_message
        )
        
        # Create notification
        Notification.objects.create(
            user=recipient,
            message=reply,
            content=f"Reply from {request.user.username}"
        )
        
        messages.success(request, 'Reply sent successfully!')
        return redirect('messaging:view_message', message_id=message_id)
    
    context = {
        'parent_message': parent_message,
        'recipient': recipient,
        'page_title': 'Reply to Message'
    }
    return render(request, 'messaging/reply.html', context)


@login_required
@require_POST
def edit_message(request, message_id):
    """Edit a message (only sender can edit)."""
    message = get_object_or_404(Message, id=message_id, sender=request.user)
    
    new_content = request.POST.get('content')
    if not new_content:
        return JsonResponse({'success': False, 'error': 'Content is required.'})
    
    # Save edit history
    MessageHistory.objects.create(
        message=message,
        old_content=message.content,
        edited_by=request.user
    )
    
    # Update message
    message.content = new_content
    message.edited = True
    message.save(update_fields=['content', 'edited'])
    
    return JsonResponse({
        'success': True,
        'new_content': new_content,
        'edited': True
    })


@login_required
@require_POST
def delete_message(request, message_id):
    """Delete a message (only sender can delete)."""
    message = get_object_or_404(Message, id=message_id, sender=request.user)
    message.delete()
    
    messages.success(request, 'Message deleted successfully!')
    return redirect('messaging:sent_messages')


@login_required
def notifications(request):
    """Display user's notifications."""
    notifications_list = Notification.objects.filter(
        user=request.user
    ).select_related('message', 'message__sender').order_by('-timestamp')
    
    paginator = Paginator(notifications_list, 20)
    page_number = request.GET.get('page')
    notifications_page = paginator.get_page(page_number)
    
    # Mark notifications as read
    unread_notifications = notifications_list.filter(read=False)
    unread_notifications.update(read=True)
    
    context = {
        'notifications': notifications_page,
        'page_title': 'Notifications'
    }
    return render(request, 'messaging/notifications.html', context)


@login_required
def search_messages(request):
    """Search through user's messages."""
    query = request.GET.get('q', '')
    messages_list = []
    
    if query:
        # Search in both sent and received messages
        messages_list = Message.objects.filter(
            Q(sender=request.user) | Q(receiver=request.user)
        ).filter(
            content__icontains=query
        ).select_related('sender', 'receiver').order_by('-timestamp')
    
    paginator = Paginator(messages_list, 20)
    page_number = request.GET.get('page')
    messages_page = paginator.get_page(page_number)
    
    context = {
        'messages': messages_page,
        'query': query,
        'page_title': 'Search Messages'
    }
    return render(request, 'messaging/search.html', context)


@login_required
def conversation_view(request, user_id):
    """View conversation between current user and another user."""
    other_user = get_object_or_404(User, id=user_id)
    
    # Get all messages between these two users
    messages_list = Message.objects.filter(
        Q(sender=request.user, receiver=other_user) |
        Q(sender=other_user, receiver=request.user)
    ).select_related('sender', 'receiver').order_by('timestamp')
    
    # Mark received messages as read
    unread_messages = messages_list.filter(receiver=request.user, read=False)
    unread_messages.update(read=True)
    
    paginator = Paginator(messages_list, 50)
    page_number = request.GET.get('page')
    messages_page = paginator.get_page(page_number)
    
    context = {
        'messages': messages_page,
        'other_user': other_user,
        'page_title': f'Conversation with {other_user.username}'
    }
    return render(request, 'messaging/conversation.html', context)


@login_required
def message_history(request, message_id):
    """View edit history of a message."""
    message = get_object_or_404(Message, id=message_id)
    
    # Check if user has permission to view this message
    if message.sender != request.user and message.receiver != request.user:
        return HttpResponseForbidden("You don't have permission to view this message history.")
    
    history = MessageHistory.objects.filter(
        message=message
    ).select_related('edited_by').order_by('-edited_at')
    
    context = {
        'message': message,
        'history': history,
        'page_title': 'Message History'
    }
    return render(request, 'messaging/message_history.html', context)


@login_required
def user_list(request):
    """Display list of users for messaging."""
    users_list = User.objects.exclude(
        id=request.user.id
    ).annotate(
        message_count=Count('chats_received_messages')
    ).order_by('username')
    
    paginator = Paginator(users_list, 30)
    page_number = request.GET.get('page')
    users_page = paginator.get_page(page_number)
    
    context = {
        'users': users_page,
        'page_title': 'Users'
    }
    return render(request, 'messaging/user_list.html', context)


# AJAX Views
@login_required
def get_unread_count(request):
    """Get unread message count for current user."""
    count = Message.unread.unread_for_user(request.user).count()
    return JsonResponse({'unread_count': count})


@login_required
@require_POST
def mark_as_read(request, message_id):
    """Mark a specific message as read."""
    message = get_object_or_404(Message, id=message_id, receiver=request.user)
    message.read = True
    message.save(update_fields=['read'])
    
    return JsonResponse({'success': True})


@login_required
@require_POST
def mark_all_as_read(request):
    """Mark all messages as read for current user."""
    Message.objects.filter(receiver=request.user, read=False).update(read=True)
    return JsonResponse({'success': True})


# User Management Views
@login_required
def delete_user(request):
    """Delete the current user account."""
    if request.method == 'POST':
        password = request.POST.get('password')
        
        # Verify password before deletion
        if not request.user.check_password(password):
            messages.error(request, 'Incorrect password. Account not deleted.')
            return render(request, 'messaging/delete_user.html')
        
        # Get the user before deletion
        user = request.user
        
        # Log out the user first
        logout(request)
        
        # Delete the user (this will cascade delete all related messages, notifications, etc.)
        user.delete()
        
        messages.success(request, 'Your account has been successfully deleted.')
        return redirect('home')  # Redirect to home page or login page
    
    context = {
        'page_title': 'Delete Account'
    }
    return render(request, 'messaging/delete_user.html', context)


@login_required
def user_profile(request, user_id=None):
    """Display user profile and account management options."""
    if user_id:
        profile_user = get_object_or_404(User, id=user_id)
    else:
        profile_user = request.user
    
    # Get message statistics
    sent_count = Message.objects.filter(sender=profile_user).count()
    received_count = Message.objects.filter(receiver=profile_user).count()
    
    context = {
        'profile_user': profile_user,
        'sent_count': sent_count,
        'received_count': received_count,
        'is_own_profile': profile_user == request.user,
        'page_title': f'{profile_user.username} Profile'
    }
    return render(request, 'messaging/user_profile.html', context)


@login_required
def account_settings(request):
    """Display account settings and management options."""
    context = {
        'page_title': 'Account Settings'
    }
    return render(request, 'messaging/account_settings.html', context)


# Dashboard/Stats Views
@login_required
def dashboard(request):
    """Display messaging dashboard with statistics."""
    # Get various counts and statistics
    unread_count = Message.unread.unread_for_user(request.user).count()
    total_received = Message.objects.filter(receiver=request.user).count()
    total_sent = Message.objects.filter(sender=request.user).count()
    recent_messages = Message.objects.filter(
        receiver=request.user
    ).select_related('sender').order_by('-timestamp')[:5]
    recent_notifications = Notification.objects.filter(
        user=request.user
    ).select_related('message', 'message__sender').order_by('-timestamp')[:5]
    
    context = {
        'unread_count': unread_count,
        'total_received': total_received,
        'total_sent': total_sent,
        'recent_messages': recent_messages,
        'recent_notifications': recent_notifications,
        'page_title': 'Dashboard'
    }
    return render(request, 'messaging/dashboard.html', context)