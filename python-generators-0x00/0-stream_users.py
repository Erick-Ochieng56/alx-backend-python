#!/usr/bin/python3
"""
Generator that streams rows from an SQL database one by one.
"""
from seed import connect_to_prodev


def stream_users():
    """
    Fetches rows one by one from the user_data table using a generator.
    
    Yields:
        dict: A dictionary containing user data (user_id, name, email, age)
    """
    connection = connect_to_prodev()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM user_data")
            
            # Yield each row one by one
            for row in cursor:
                yield row
                
        except Exception as e:
            print(f"Error streaming users: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
