#!/usr/bin/python3
"""
Lazy loading paginated data from database using generators.
"""
from seed import connect_to_prodev


def paginate_users(page_size, offset):
    """
    Fetches paginated data from the user_data table.
    
    Args:
        page_size (int): Number of records per page
        offset (int): Starting position for fetching records
        
    Returns:
        list: A list of user records for the requested page
    """
    connection = connect_to_prodev()
    cursor = connection.cursor(dictionary=True)
    cursor.execute(f"SELECT * FROM user_data LIMIT {page_size} OFFSET {offset}")
    rows = cursor.fetchall()
    connection.close()
    return rows


def lazy_pagination(page_size):
    """
    Implements lazy loading of paginated data using a generator.
    Only fetches the next page when needed.
    
    Args:
        page_size (int): Number of records per page
        
    Yields:
        list: A page of user records
    """
    offset = 0
    
    while True:
        # Fetch the current page of data
        page = paginate_users(page_size, offset)
        
        # If page is empty, we've reached the end of the data
        if not page:
            break
            
        # Yield the current page
        yield page
        
        # Move to the next page
        offset += page_size
