from django.contrib import admin
from .models import Message, Notification, MessageHistory


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender', 'receiver', 'timestamp', 'edited', 'read')
    list_filter = ('timestamp', 'edited', 'read')
    search_fields = ('sender__username', 'receiver__username', 'content')
    readonly_fields = ('timestamp',)
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('sender', 'receiver', 'parent_message')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'content', 'timestamp', 'read')
    list_filter = ('timestamp', 'read')
    search_fields = ('user__username', 'content')
    readonly_fields = ('timestamp',)
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('user', 'message')


@admin.register(MessageHistory)
class MessageHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'message', 'edited_by', 'edited_at')
    list_filter = ('edited_at',)
    search_fields = ('message__content', 'edited_by__username', 'old_content')
    readonly_fields = ('edited_at',)
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('message', 'edited_by')