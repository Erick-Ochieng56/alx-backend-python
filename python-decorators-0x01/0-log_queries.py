import sqlite3
import functools
from datetime import datetime

def log_queries(func):
    """Decorator to log SQL queries before executing them"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Extract the query from the function arguments
        # Assuming the query is passed as a keyword argument or first positional argument
        query = None
        if 'query' in kwargs:
            query = kwargs['query']
        elif args:
            # Check if first argument looks like a SQL query
            if isinstance(args[0], str) and any(keyword in args[0].upper() for keyword in ['SELECT', 'INSERT', 'UPDATE', 'DELETE']):
                query = args[0]
        
        if query:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] Executing SQL Query: {query}")
        
        return func(*args, **kwargs)
    return wrapper

@log_queries
def fetch_all_users(query):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute(query)
    results = cursor.fetchall()
    conn.close()
    return results

# Fetch users while logging the query
users = fetch_all_users(query="SELECT * FROM users")
