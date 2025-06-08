# messaging_app/chats/filters.py

import django_filters
from django.db.models import Q
from django_filters import rest_framework as filters
from .models import User, Conversation, Message


class MessageFilter(filters.FilterSet):
    """
    Filter class for Message model with comprehensive filtering options
    """
    # Date range filtering
    sent_after = filters.DateTimeFilter(field_name='sent_at', lookup_expr='gte')
    sent_before = filters.DateTimeFilter(field_name='sent_at', lookup_expr='lte')
    sent_date = filters.DateFilter(field_name='sent_at__date')
    
    # Date range choices for common time periods
    date_range = filters.ChoiceFilter(
        choices=[
            ('today', 'Today'),
            ('yesterday', 'Yesterday'),
            ('last_week', 'Last Week'),
            ('last_month', 'Last Month'),
            ('last_year', 'Last Year'),
        ],
        method='filter_by_date_range',
        help_text="Filter messages by predefined date ranges"
    )
    
    # Sender filtering
    sender = filters.ModelChoiceFilter(
        queryset=User.objects.filter(is_active=True),
        field_name='sender',
        help_text="Filter messages by sender"
    )
    sender_username = filters.CharFilter(
        field_name='sender__username',
        lookup_expr='icontains',
        help_text="Filter messages by sender username (case-insensitive)"
    )
    
    # Conversation filtering
    conversation = filters.UUIDFilter(
        field_name='conversation__conversation_id',
        help_text="Filter messages by conversation ID"
    )
    
    # Content filtering
    content = filters.CharFilter(
        field_name='message_body',
        lookup_expr='icontains',
        help_text="Search within message content (case-insensitive)"
    )
    content_exact = filters.CharFilter(
        field_name='message_body',
        lookup_expr='iexact',
        help_text="Exact match for message content (case-insensitive)"
    )
    
    # Message type filtering (if you have message types)
    # message_type = filters.ChoiceFilter(
    #     choices=[
    #         ('text', 'Text'),
    #         ('image', 'Image'),
    #         ('file', 'File'),
    #     ],
    #     field_name='message_type',
    #     help_text="Filter by message type"
    # )
    
    # Advanced filtering
    has_attachments = filters.BooleanFilter(
        method='filter_has_attachments',
        help_text="Filter messages that have attachments"
    )
    
    # Multiple participants filtering
    participants = filters.ModelMultipleChoiceFilter(
        queryset=User.objects.filter(is_active=True),
        field_name='conversation__participants',
        help_text="Filter messages from conversations with specific participants"
    )
    
    class Meta:
        model = Message
        fields = [
            'sent_after', 'sent_before', 'sent_date', 'date_range',
            'sender', 'sender_username', 'conversation',
            'content', 'content_exact', 'has_attachments', 'participants'
        ]
    
    def filter_by_date_range(self, queryset, name, value):
        """
        Custom method to filter by predefined date ranges
        """
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        
        if value == 'today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            return queryset.filter(sent_at__gte=start_date)
        elif value == 'yesterday':
            yesterday = now - timedelta(days=1)
            start_date = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=1)
            return queryset.filter(sent_at__gte=start_date, sent_at__lt=end_date)
        elif value == 'last_week':
            start_date = now - timedelta(days=7)
            return queryset.filter(sent_at__gte=start_date)
        elif value == 'last_month':
            start_date = now - timedelta(days=30)
            return queryset.filter(sent_at__gte=start_date)
        elif value == 'last_year':
            start_date = now - timedelta(days=365)
            return queryset.filter(sent_at__gte=start_date)
        
        return queryset
    
    def filter_has_attachments(self, queryset, name, value):
        """
        Custom method to filter messages with attachments
        Note: This assumes you have an attachments field or related model
        """
        # If you have attachments, uncomment and modify this:
        # if value:
        #     return queryset.filter(attachments__isnull=False).distinct()
        # else:
        #     return queryset.filter(attachments__isnull=True)
        
        # Placeholder implementation
        return queryset


class ConversationFilter(filters.FilterSet):
    """
    Filter class for Conversation model
    """
    # Participant filtering
    participant = filters.ModelChoiceFilter(
        queryset=User.objects.filter(is_active=True),
        field_name='participants',
        help_text="Filter conversations by participant"
    )
    participant_username = filters.CharFilter(
        field_name='participants__username',
        lookup_expr='icontains',
        help_text="Filter conversations by participant username"
    )
    
    # Date filtering
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    updated_after = filters.DateTimeFilter(field_name='updated_at', lookup_expr='gte')
    updated_before = filters.DateTimeFilter(field_name='updated_at', lookup_expr='lte')
    
    # Group conversation filtering
    is_group = filters.BooleanFilter(
        method='filter_is_group',
        help_text="Filter group conversations (more than 2 participants)"
    )
    
    # Activity filtering
    has_recent_activity = filters.BooleanFilter(
        method='filter_recent_activity',
        help_text="Filter conversations with recent activity (last 7 days)"
    )
    
    # Message count filtering
    min_messages = filters.NumberFilter(
        method='filter_min_messages',
        help_text="Filter conversations with minimum number of messages"
    )
    max_messages = filters.NumberFilter(
        method='filter_max_messages',
        help_text="Filter conversations with maximum number of messages"
    )
    
    class Meta:
        model = Conversation
        fields = [
            'participant', 'participant_username', 'created_after', 'created_before',
            'updated_after', 'updated_before', 'is_group', 'has_recent_activity',
            'min_messages', 'max_messages'
        ]
    
    def filter_is_group(self, queryset, name, value):
        """
        Filter group conversations (more than 2 participants)
        """
        if value:
            return queryset.annotate(
                participant_count=django_filters.Count('participants')
            ).filter(participant_count__gt=2)
        else:
            return queryset.annotate(
                participant_count=django_filters.Count('participants')
            ).filter(participant_count__lte=2)
    
    def filter_recent_activity(self, queryset, name, value):
        """
        Filter conversations with recent activity
        """
        from django.utils import timezone
        from datetime import timedelta
        
        if value:
            recent_date = timezone.now() - timedelta(days=7)
            return queryset.filter(updated_at__gte=recent_date)
        return queryset
    
    def filter_min_messages(self, queryset, name, value):
        """
        Filter conversations with minimum number of messages
        """
        return queryset.annotate(
            message_count=django_filters.Count('messages')
        ).filter(message_count__gte=value)
    
    def filter_max_messages(self, queryset, name, value):
        """
        Filter conversations with maximum number of messages
        """
        return queryset.annotate(
            message_count=django_filters.Count('messages')
        ).filter(message_count__lte=value)


class UserFilter(filters.FilterSet):
    """
    Filter class for User model
    """
    # Name filtering
    name = filters.CharFilter(
        method='filter_by_name',
        help_text="Search by first name, last name, or username"
    )
    
    # Registration date filtering
    joined_after = filters.DateTimeFilter(field_name='date_joined', lookup_expr='gte')
    joined_before = filters.DateTimeFilter(field_name='date_joined', lookup_expr='lte')
    
    # Activity status
    is_active = filters.BooleanFilter(field_name='is_active')
    
    # Email domain filtering
    email_domain = filters.CharFilter(
        method='filter_email_domain',
        help_text="Filter users by email domain"
    )
    
    class Meta:
        model = User
        fields = [
            'name', 'username', 'email', 'first_name', 'last_name',
            'joined_after', 'joined_before', 'is_active', 'email_domain'
        ]
    
    def filter_by_name(self, queryset, name, value):
        """
        Search across multiple name fields
        """
        return queryset.filter(
            Q(first_name__icontains=value) |
            Q(last_name__icontains=value) |
            Q(username__icontains=value)
        )
    
    def filter_email_domain(self, queryset, name, value):
        """
        Filter users by email domain
        """
        return queryset.filter(email__iendswith=f'@{value}')


# Additional specialized filters

class MessageTimeRangeFilter(filters.FilterSet):
    """
    Specialized filter for time-based message filtering
    """
    # Time of day filtering
    sent_hour = filters.NumberFilter(
        field_name='sent_at__hour',
        help_text="Filter messages sent at specific hour (0-23)"
    )
    sent_hour_range = filters.RangeFilter(
        field_name='sent_at__hour',
        help_text="Filter messages sent within hour range"
    )
    
    # Day of week filtering (0=Monday, 6=Sunday)
    sent_weekday = filters.NumberFilter(
        field_name='sent_at__week_day',
        help_text="Filter messages by day of week (1=Sunday, 7=Saturday)"
    )
    
    # Month filtering
    sent_month = filters.NumberFilter(
        field_name='sent_at__month',
        help_text="Filter messages by month (1-12)"
    )
    
    # Year filtering
    sent_year = filters.NumberFilter(
        field_name='sent_at__year',
        help_text="Filter messages by year"
    )
    
    class Meta:
        model = Message
        fields = ['sent_hour', 'sent_hour_range', 'sent_weekday', 'sent_month', 'sent_year']


class ConversationParticipantFilter(filters.FilterSet):
    """
    Specialized filter for conversation participants
    """
    # Filter conversations between specific users
    between_users = filters.CharFilter(
        method='filter_between_users',
        help_text="Filter conversations between specific users (comma-separated usernames)"
    )
    
    # Filter conversations including all specified users
    includes_all_users = filters.CharFilter(
        method='filter_includes_all_users',
        help_text="Filter conversations that include ALL specified users (comma-separated usernames)"
    )
    
    # Filter conversations including any of the specified users
    includes_any_user = filters.CharFilter(
        method='filter_includes_any_user',
        help_text="Filter conversations that include ANY of the specified users (comma-separated usernames)"
    )
    
    class Meta:
        model = Conversation
        fields = ['between_users', 'includes_all_users', 'includes_any_user']
    
    def filter_between_users(self, queryset, name, value):
        """
        Filter conversations between specific users only
        """
        usernames = [username.strip() for username in value.split(',')]
        users = User.objects.filter(username__in=usernames, is_active=True)
        
        if users.count() != len(usernames):
            return queryset.none()
        
        # Get conversations that have exactly these participants
        conversations = queryset.filter(participants__in=users).annotate(
            participant_count=django_filters.Count('participants')
        ).filter(participant_count=len(usernames))
        
        # Ensure all specified users are participants
        for user in users:
            conversations = conversations.filter(participants=user)
        
        return conversations.distinct()
    
    def filter_includes_all_users(self, queryset, name, value):
        """
        Filter conversations that include all specified users
        """
        usernames = [username.strip() for username in value.split(',')]
        users = User.objects.filter(username__in=usernames, is_active=True)
        
        conversations = queryset
        for user in users:
            conversations = conversations.filter(participants=user)
        
        return conversations.distinct()
    
    def filter_includes_any_user(self, queryset, name, value):
        """
        Filter conversations that include any of the specified users
        """
        usernames = [username.strip() for username in value.split(',')]
        users = User.objects.filter(username__in=usernames, is_active=True)
        
        return queryset.filter(participants__in=users).distinct()