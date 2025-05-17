#!/usr/bin/python3
"""
Batch processing of large data using generators.
"""
from seed import connect_to_prodev


def stream_users_in_batches(batch_size):
    """
    Fetches rows in batches from the user_data table.
    
    Args:
        batch_size (int): Number of records to fetch in each batch
        
    Yields:
        list: A batch of user records
    """
    connection = connect_to_prodev()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            offset = 0
            
            while True:
                cursor.execute(f"SELECT * FROM user_data LIMIT {batch_size} OFFSET {offset}")
                batch = cursor.fetchall()
                
                if not batch:
                    break
                    
                yield batch
                offset += batch_size
                
        except Exception as e:
            print(f"Error streaming users in batches: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()


def batch_processing(batch_size):
    """
    Processes each batch to filter users over the age of 25.
    
    Args:
        batch_size (int): Size of each batch to process
    """
    # Get batches of users
    for batch in stream_users_in_batches(batch_size):
        # Process each user in the batch
        for user in batch:
            # Filter users over age 25
            if user['age'] > 25:
                print(user)
                print()  # Empty line for better readability
