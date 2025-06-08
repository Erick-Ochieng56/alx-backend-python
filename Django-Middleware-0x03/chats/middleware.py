import logging
import os
from datetime import datetime, timedelta
from django.http import HttpResponseForbidden, JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from collections import defaultdict
import re


class RequestLoggingMiddleware:
    """
    Middleware that logs each user's requests to a file, including timestamp, user, and request path.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Set up logging configuration
        log_file_path = os.path.join(settings.BASE_DIR, 'requests.log')
        
        # Create logger
        self.logger = logging.getLogger('request_logger')
        self.logger.setLevel(logging.INFO)
        
        # Create file handler
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(message)s')
        file_handler.setFormatter(formatter)
        
        # Add handler to logger (avoid duplicate handlers)
        if not self.logger.handlers:
            self.logger.addHandler(file_handler)
    
    def __call__(self, request):
        # Get user information
        user = request.user if hasattr(request, 'user') and request.user.is_authenticated else 'Anonymous'
        
        # Log the request
        log_message = f"{datetime.now()} - User: {user} - Path: {request.path}"
        self.logger.info(log_message)
        
        response = self.get_response(request)
        return response


class RestrictAccessByTimeMiddleware:
    """
    Middleware that restricts access to the messaging app during certain hours of the day.
    Access is denied outside 6 AM to 9 PM.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Get current hour (24-hour format)
        current_hour = datetime.now().hour
        
        # Check if current time is outside allowed hours (6 AM to 9 PM)
        if current_hour < 6 or current_hour >= 21:  # 21 = 9 PM in 24-hour format
            return HttpResponseForbidden(
                "Access to the messaging app is restricted outside of 6 AM to 9 PM."
            )
        
        response = self.get_response(request)
        return response


class OffensiveLanguageMiddleware:
    """
    Middleware that limits the number of chat messages a user can send within a certain time window,
    based on their IP address. Limits to 5 messages per minute.
    """
    
    # Class-level storage for IP tracking (in production, use Redis or database)
    ip_message_counts = defaultdict(list)
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.max_messages = 5  # Maximum messages per time window
        self.time_window = 60  # Time window in seconds (1 minute)
    
    def __call__(self, request):
        # Only apply rate limiting to POST requests (message sending)
        if request.method == 'POST':
            # Get client IP address
            ip_address = self.get_client_ip(request)
            current_time = datetime.now()
            
            # Clean old entries for this IP
            self.clean_old_entries(ip_address, current_time)
            
            # Check if IP has exceeded the limit
            message_count = len(self.ip_message_counts[ip_address])
            
            if message_count >= self.max_messages:
                return JsonResponse(
                    {
                        'error': 'Rate limit exceeded. You can only send 5 messages per minute.',
                        'retry_after': self.time_window
                    },
                    status=429  # Too Many Requests
                )
            
            # Add current request timestamp
            self.ip_message_counts[ip_address].append(current_time)
        
        response = self.get_response(request)
        return response
    
    def get_client_ip(self, request):
        """Extract the client's IP address from the request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def clean_old_entries(self, ip_address, current_time):
        """Remove entries older than the time window."""
        cutoff_time = current_time - timedelta(seconds=self.time_window)
        self.ip_message_counts[ip_address] = [
            timestamp for timestamp in self.ip_message_counts[ip_address]
            if timestamp > cutoff_time
        ]


class RolepermissionMiddleware:  # Changed from RolePermissionMiddleware
    """
    Middleware that checks the user's role before allowing access to specific actions.
    Only allows access for admin or moderator users.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Define paths that require admin/moderator access
        self.restricted_paths = [
            '/api/users/',
            '/api/conversations/',
            '/api/messages/',
            '/admin/',
        ]
    
    def __call__(self, request):
        # Check if the request path requires role-based access
        if self.requires_role_check(request.path):
            # Check if user is authenticated
            if not hasattr(request, 'user') or not request.user.is_authenticated:
                return HttpResponseForbidden("Authentication required.")
            
            # Check user role
            user = request.user
            
            # Check if user is admin or moderator
            # This assumes you have role fields or groups set up in your User model
            is_admin = getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False)
            is_moderator = self.check_moderator_role(user)
            
            if not (is_admin or is_moderator):
                return HttpResponseForbidden(
                    "Access denied. This action requires admin or moderator privileges."
                )
        
        response = self.get_response(request)
        return response
    
    def requires_role_check(self, path):
        """Check if the given path requires role-based access control."""
        for restricted_path in self.restricted_paths:
            if path.startswith(restricted_path):
                return True
        return False
    
    def check_moderator_role(self, user):
        """
        Check if user has moderator role.
        This implementation checks for a 'moderator' group or a role field.
        Adjust based on your actual user model implementation.
        """
        # Option 1: Check if user belongs to a 'moderator' group
        if hasattr(user, 'groups'):
            return user.groups.filter(name='moderator').exists()
        
        # Option 2: Check for a role field (if you have one in your User model)
        if hasattr(user, 'role'):
            return user.role in ['moderator', 'admin']
        
        # Option 3: Check for custom field
        if hasattr(user, 'is_moderator'):
            return user.is_moderator
        
        return False

# Additional middleware for actual offensive language detection (bonus)
class OffensiveLanguageDetectionMiddleware:
    """
    Bonus middleware that actually detects offensive language in message content.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Basic list of offensive words (in production, use a more comprehensive solution)
        self.offensive_words = [
            'spam', 'hate', 'offensive', 'inappropriate', 'banned'
            # Add more words as needed, or integrate with a proper content filtering service
        ]
    
    def __call__(self, request):
        # Check POST requests for message content
        if request.method == 'POST' and 'message_body' in request.POST:
            message_content = request.POST.get('message_body', '').lower()
            
            # Check for offensive language
            if self.contains_offensive_language(message_content):
                return JsonResponse(
                    {
                        'error': 'Message contains inappropriate content and cannot be sent.',
                        'code': 'OFFENSIVE_CONTENT'
                    },
                    status=400
                )
        
        response = self.get_response(request)
        return response
    
    def contains_offensive_language(self, text):
        """Check if text contains offensive language."""
        text_words = re.findall(r'\b\w+\b', text.lower())
        return any(word in self.offensive_words for word in text_words)