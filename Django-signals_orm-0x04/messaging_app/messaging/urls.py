from django.urls import path
from . import views


urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Core messaging views
    path('inbox/', views.inbox, name='inbox'),
    path('sent/', views.sent_messages, name='sent_messages'),
    path('compose/', views.compose_message, name='compose_message'),
    path('compose/<int:recipient_id>/', views.compose_message, name='compose_message_to'),
    
    # Message specific views
    path('message/<int:message_id>/', views.view_message, name='view_message'),
    path('message/<int:message_id>/reply/', views.reply_to_message, name='reply_to_message'),
    path('message/<int:message_id>/edit/', views.edit_message, name='edit_message'),
    path('message/<int:message_id>/delete/', views.delete_message, name='delete_message'),
    path('message/<int:message_id>/history/', views.message_history, name='message_history'),
    
    # Conversation and search
    path('conversation/<int:user_id>/', views.conversation_view, name='conversation_view'),
    path('search/', views.search_messages, name='search_messages'),
    
    # Notifications
    path('notifications/', views.notifications, name='notifications'),
    
    # User management
    path('users/', views.user_list, name='user_list'),
    path('profile/', views.user_profile, name='user_profile'),
    path('profile/<int:user_id>/', views.user_profile, name='user_profile_view'),
    path('settings/', views.account_settings, name='account_settings'),
    path('delete-account/', views.delete_user, name='delete_user'),
    
    # AJAX endpoints
    path('ajax/unread-count/', views.get_unread_count, name='get_unread_count'),
    path('ajax/mark-read/<int:message_id>/', views.mark_as_read, name='mark_as_read'),
    path('ajax/mark-all-read/', views.mark_all_as_read, name='mark_all_as_read'),
]