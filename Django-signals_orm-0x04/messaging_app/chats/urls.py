from django.urls import path
from . import views

urlpatterns = [
    # Main conversation views
    path('', views.conversation_list, name='conversation_list'),
    path('conversations/', views.conversation_list, name='conversation_list'),
    
    # Threaded conversation view (Task 3)
    path('thread/<int:message_id>/', views.threaded_conversation, name='threaded_conversation'),
    
    # Unread messages view (Task 4)
    path('unread/', views.unread_messages, name='unread_messages'),
    
    # Message actions
    path('send/', views.send_message, name='send_message'),
    path('mark-read/<int:message_id>/', views.mark_as_read, name='mark_as_read'),
    path('history/<int:message_id>/', views.message_history, name='message_history'),
    
    # User account management (Task 2)
    path('delete-account/', views.delete_user, name='delete_user'),
]