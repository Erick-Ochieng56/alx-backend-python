from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import models  # Add this 
from django.http import JsonResponse
from django.views.decorators.cache import cache_page
from django.core.paginator import Paginator
from messaging.models import Message, Notification, MessageHistory
 

@login_required
def delete_user(request):
    """
    Task 2: View to allow a user to delete their account.
    This will trigger the post_delete signal for cleanup.
    """
    if request.method == 'POST':
        user = request.user
        
        # Log the user out and delete the account
        # The post_delete signal will handle cleanup automatically
        user.delete()
        
        messages.success(request, "Your account has been successfully deleted.")
        return redirect('login')  # Redirect to login page
    
    return render(request, 'chats/delete_account.html')


@cache_page(60)  # Cache for 60 seconds (Task 5)
@login_required
def conversation_list(request):
    """
    Task 5: Cached view that displays a list of messages in conversations.
    Uses view-level caching with @cache_page decorator.
    """
    # Get messages for the current user (both sent and received)
    # Using select_related to optimize database queries
    messages_sent = Message.objects.filter(sender=request.user).select_related(
        'receiver', 'parent_message'
    )
    messages_received = Message.objects.filter(receiver=request.user).select_related(
        'sender', 'parent_message'
    )
    
    # Combine and order by timestamp
    all_messages = messages_sent.union(messages_received).order_by('-timestamp')
    
    # Pagination
    paginator = Paginator(all_messages, 20)  # Show 20 messages per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'messages': page_obj,
        'unread_count': Message.unread.unread_for_user(request.user).count(),
    }
    
    return render(request, 'chats/conversation_list.html', context)


@login_required
def threaded_conversation(request, message_id):
    """
    Task 3: View to display threaded conversations using advanced ORM techniques.
    Uses prefetch_related and select_related for optimization.
    """
    # Get the root message
    root_message = get_object_or_404(Message, id=message_id)
    
    # Get the complete thread using optimized queries
    thread_messages = Message.objects.filter(
        models.Q(id=root_message.id) | 
        models.Q(parent_message=root_message) |
        models.Q(parent_message__parent_message=root_message)  # Support nested replies
    ).select_related(
        'sender', 'receiver', 'parent_message'
    ).prefetch_related(
        'replies', 'edit_history'
    ).order_by('timestamp')
    
    # Alternative: Use the model method for recursive retrieval
    # thread_messages = root_message.get_thread()
    
    context = {
        'root_message': root_message,
        'thread_messages': thread_messages,
        'can_reply': request.user in [root_message.sender, root_message.receiver]
    }
    
    return render(request, 'chats/threaded_conversation.html', context)


@login_required
def unread_messages(request):
    """
    Task 4: View to display unread messages using custom manager.
    Uses the UnreadMessagesManager with .only() optimization.
    """
    # Use the custom manager to get unread messages
    unread_messages = Message.unread.unread_for_user(request.user)
    
    # Pagination
    paginator = Paginator(unread_messages, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'unread_messages': page_obj,
        'total_unread': unread_messages.count(),
    }
    
    return render(request, 'chats/unread_messages.html', context)


@login_required
def mark_as_read(request, message_id):
    """
    Utility view to mark a message as read.
    """
    if request.method == 'POST':
        message = get_object_or_404(Message, id=message_id, receiver=request.user)
        message.read = True
        message.save()
        
        return JsonResponse({'status': 'success'})
    
    return JsonResponse({'status': 'error'})


@login_required
def message_history(request, message_id):
    """
    View to display edit history of a message.
    """
    message = get_object_or_404(Message, id=message_id)
    
    # Check if user has permission to view history
    if request.user not in [message.sender, message.receiver]:
        messages.error(request, "You don't have permission to view this message history.")
        return redirect('conversation_list')
    
    # Get edit history
    edit_history = MessageHistory.objects.filter(message=message).select_related(
        'edited_by'
    ).order_by('-edited_at')
    
    context = {
        'message': message,
        'edit_history': edit_history,
    }
    
    return render(request, 'chats/message_history.html', context)


@login_required
def send_message(request):
    """
    View to send a new message or reply to an existing message.
    """
    if request.method == 'POST':
        receiver_id = request.POST.get('receiver_id')
        content = request.POST.get('content')
        parent_message_id = request.POST.get('parent_message_id')
        
        if not receiver_id or not content:
            messages.error(request, "Receiver and content are required.")
            return redirect('conversation_list')
        
        try:
            receiver = User.objects.get(id=receiver_id)
            
            # Create the message
            message_data = {
                'sender': request.user,
                'receiver': receiver,
                'content': content.strip(),
            }
            
            # Add parent message if this is a reply
            if parent_message_id:
                parent_message = Message.objects.get(id=parent_message_id)
                message_data['parent_message'] = parent_message
            
            message = Message.objects.create(**message_data)
            
            messages.success(request, "Message sent successfully!")
            
            # Redirect to threaded view if this was a reply
            if parent_message_id:
                return redirect('threaded_conversation', message_id=parent_message_id)
            else:
                return redirect('conversation_list')
                
        except User.DoesNotExist:
            messages.error(request, "Receiver not found.")
        except Message.DoesNotExist:
            messages.error(request, "Parent message not found.")
        except Exception as e:
            messages.error(request, f"Error sending message: {str(e)}")
    
    return redirect('conversation_list')


