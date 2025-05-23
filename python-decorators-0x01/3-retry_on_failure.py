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

def retry_on_failure(retries=3, delay=2):
    """Decorator that retries database operations on failure"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(retries + 1):  # +1 to include the initial attempt
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < retries:  # Don't sleep after the last attempt
                        print(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay} seconds...")
                        time.sleep(delay)
                    else:
                        print(f"All {retries + 1} attempts failed.")
            
            # If all retries failed, raise the last exception
            raise last_exception
        return wrapper
    return decorator

@with_db_connection
@retry_on_failure(retries=3, delay=1)
def fetch_users_with_retry(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    return cursor.fetchall()

# Attempt to fetch users with automatic retry on failure
users = fetch_users_with_retry()
print(users)
