import time
import sqlite3 
import functools

def with_db_connection(func):
    """Decorator that automatically handles database connection opening and closing"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Open database connection
        conn = sqlite3.connect('users.db')
        try:
            # Call the original function with connection as first argument
            result = func(conn, *args, **kwargs)
            return result
        finally:
            # Always close the connection
            conn.close()
    return wrapper

query_cache = {}

def cache_query(func):
    """Decorator that caches query results based on the SQL query string"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Extract the query string to use as cache key
        cache_key = None
        
        # Look for 'query' in kwargs
        if 'query' in kwargs:
            cache_key = kwargs['query']
        else:
            # Look for query in args (assuming it's the second argument after conn)
            for arg in args[1:]:  # Skip the connection argument
                if isinstance(arg, str) and any(keyword in arg.upper() for keyword in ['SELECT', 'INSERT', 'UPDATE', 'DELETE']):
                    cache_key = arg
                    break
        
        # If we found a query and it's in cache, return cached result
        if cache_key and cache_key in query_cache:
            print(f"Cache hit for query: {cache_key}")
            return query_cache[cache_key]
        
        # Execute the function and cache the result
        result = func(*args, **kwargs)
        
        # Cache the result if we have a cache key
        if cache_key:
            print(f"Caching result for query: {cache_key}")
            query_cache[cache_key] = result
        
        return result
    return wrapper

@with_db_connection
@cache_query
def fetch_users_with_cache(conn, query):
    cursor = conn.cursor()
    cursor.execute(query)
    return cursor.fetchall()

# First call will cache the result
users = fetch_users_with_cache(query="SELECT * FROM users")

# Second call will use the cached result
users_again = fetch_users_with_cache(query="SELECT * FROM users")
