# messaging_app/chats/pagination.py

from rest_framework.pagination import PageNumberPagination, LimitOffsetPagination
from rest_framework.response import Response
from collections import OrderedDict


class MessagePagination(PageNumberPagination):
    """
    Custom pagination class for messages with 20 items per page
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    page_query_param = 'page'
    
    def get_paginated_response(self, data):
        """
        Custom response format with additional metadata
        """
        return Response(OrderedDict([
            ('count', self.page.paginator.count),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('page_info', {
                'current_page': self.page.number,
                'total_pages': self.page.paginator.num_pages,
                'page_size': self.get_page_size(self.request),
                'has_next': self.page.has_next(),
                'has_previous': self.page.has_previous(),
            }),
            ('results', data)
        ]))


class ConversationPagination(PageNumberPagination):
    """
    Custom pagination class for conversations with 10 items per page
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50
    page_query_param = 'page'
    
    def get_paginated_response(self, data):
        """
        Custom response format for conversation listing
        """
        return Response(OrderedDict([
            ('count', self.page.paginator.count),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('page_info', {
                'current_page': self.page.number,
                'total_pages': self.page.paginator.num_pages,
                'page_size': self.get_page_size(self.request),
                'has_next': self.page.has_next(),
                'has_previous': self.page.has_previous(),
            }),
            ('conversations', data)
        ]))


class UserPagination(PageNumberPagination):
    """
    Custom pagination class for users with 15 items per page
    """
    page_size = 15
    page_size_query_param = 'page_size'
    max_page_size = 100
    page_query_param = 'page'
    
    def get_paginated_response(self, data):
        """
        Custom response format for user listing
        """
        return Response(OrderedDict([
            ('count', self.page.paginator.count),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('page_info', {
                'current_page': self.page.number,
                'total_pages': self.page.paginator.num_pages,
                'page_size': self.get_page_size(self.request),
                'has_next': self.page.has_next(),
                'has_previous': self.page.has_previous(),
            }),
            ('users', data)
        ]))


class LimitOffsetMessagePagination(LimitOffsetPagination):
    """
    Alternative pagination using limit/offset for messages
    Useful for infinite scrolling implementations
    """
    default_limit = 20
    limit_query_param = 'limit'
    offset_query_param = 'offset'
    max_limit = 100
    
    def get_paginated_response(self, data):
        """
        Custom response format with limit/offset metadata
        """
        return Response(OrderedDict([
            ('count', self.count),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('pagination_info', {
                'limit': self.limit,
                'offset': self.offset,
                'remaining': max(0, self.count - self.offset - self.limit) if self.count else 0,
                'has_more': self.get_next_link() is not None,
            }),
            ('results', data)
        ]))


class CustomPageNumberPagination(PageNumberPagination):
    """
    Base custom pagination class with enhanced features
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 200
    page_query_param = 'page'
    
    def get_paginated_response(self, data):
        """
        Enhanced response format with comprehensive metadata
        """
        page_size = self.get_page_size(self.request)
        
        return Response(OrderedDict([
            ('pagination', {
                'count': self.page.paginator.count,
                'current_page': self.page.number,
                'total_pages': self.page.paginator.num_pages,
                'page_size': page_size,
                'has_next': self.page.has_next(),
                'has_previous': self.page.has_previous(),
                'next_page': self.page.next_page_number() if self.page.has_next() else None,
                'previous_page': self.page.previous_page_number() if self.page.has_previous() else None,
                'start_index': self.page.start_index(),
                'end_index': self.page.end_index(),
            }),
            ('links', {
                'next': self.get_next_link(),
                'previous': self.get_previous_link(),
            }),
            ('results', data)
        ]))


class MessageInfiniteScrollPagination(LimitOffsetPagination):
    """
    Specialized pagination for infinite scroll message loading
    Loads messages in reverse chronological order
    """
    default_limit = 20
    limit_query_param = 'limit'
    offset_query_param = 'offset'
    max_limit = 50
    
    def get_paginated_response(self, data):
        """
        Response format optimized for infinite scroll
        """
        has_more = self.get_next_link() is not None
        
        return Response(OrderedDict([
            ('messages', data),
            ('has_more', has_more),
            ('next_offset', self.offset + self.limit if has_more else None),
            ('total_count', self.count),
            ('loaded_count', min(self.offset + self.limit, self.count)),
            ('metadata', {
                'limit': self.limit,
                'offset': self.offset,
                'remaining': max(0, self.count - self.offset - self.limit) if self.count else 0,
            })
        ]))


class SmallPagePagination(PageNumberPagination):
    """
    Small page size pagination for mobile or limited bandwidth scenarios
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 25
    
    def get_paginated_response(self, data):
        """
        Minimal response format for bandwidth efficiency
        """
        return Response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'page': self.page.number,
            'total_pages': self.page.paginator.num_pages,
            'results': data
        })


class LargePagePagination(PageNumberPagination):
    """
    Large page size pagination for desktop applications
    """
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200
    
    def get_paginated_response(self, data):
        """
        Detailed response format for desktop applications
        """
        return Response(OrderedDict([
            ('summary', {
                'total_items': self.page.paginator.count,
                'total_pages': self.page.paginator.num_pages,
                'current_page': self.page.number,
                'items_per_page': self.get_page_size(self.request),
                'showing_from': self.page.start_index(),
                'showing_to': self.page.end_index(),
            }),
            ('navigation', {
                'next_url': self.get_next_link(),
                'previous_url': self.get_previous_link(),
                'has_next': self.page.has_next(),
                'has_previous': self.page.has_previous(),
            }),
            ('data', data)
        ]))


class SearchResultsPagination(PageNumberPagination):
    """
    Specialized pagination for search results
    """
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100
    
    def get_paginated_response(self, data):
        """
        Search-optimized response format
        """
        return Response(OrderedDict([
            ('search_results', {
                'total_matches': self.page.paginator.count,
                'pages': self.page.paginator.num_pages,
                'current_page': self.page.number,
                'results_per_page': self.get_page_size(self.request),
            }),
            ('navigation', {
                'next': self.get_next_link(),
                'previous': self.get_previous_link(),
            }),
            ('matches', data)
        ]))