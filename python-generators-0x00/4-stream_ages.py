#!/usr/bin/python3
"""
Memory-efficient aggregation using generators to calculate average age.
"""
from seed import connect_to_prodev


def stream_user_ages():
    """
    A generator that yields user ages one by one.
    
    Yields:
        int: The age of a user
    """
    connection = connect_to_prodev()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT age FROM user_data")
            
            # Yield each age one by one
            for (age,) in cursor:
                yield age
                
        except Exception as e:
            print(f"Error streaming ages: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()


def calculate_average_age():
    """
    Calculate the average age of users without loading the entire dataset into memory.
    """
    total_age = 0
    count = 0
    
    # Process ages one by one
    for age in stream_user_ages():
        total_age += age
        count += 1
    
    # Calculate and print the average age
    if count > 0:
        average_age = total_age / count
        print(f"Average age of users: {average_age:.2f}")
    else:
        print("No users found")


if __name__ == "__main__":
    calculate_average_age()
