#!/usr/bin/env python3
"""
Custom class-based context manager for Database connection
"""

import sqlite3


class DatabaseConnection:
    """
    A custom context manager for handling database connections.
    Automatically manages opening and closing database connections.
    """
    
    def __init__(self, database_name):
        """
        Initialize the DatabaseConnection with a database name.
        
        Args:
            database_name (str): The name/path of the database file
        """
        self.database_name = database_name
        self.connection = None
        self.cursor = None
    
    def __enter__(self):
        """
        Enter the context manager - establish database connection.
        
        Returns:
            sqlite3.Cursor: The database cursor for executing queries
        """
        try:
            self.connection = sqlite3.connect(self.database_name)
            self.cursor = self.connection.cursor()
            return self.cursor
        except sqlite3.Error as e:
            print(f"Error connecting to database: {e}")
            raise
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the context manager - close database connection.
        
        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred
        """
        if self.cursor:
            self.cursor.close()
        if self.connection:
            if exc_type is None:
                # No exception occurred, commit any pending transactions
                self.connection.commit()
            else:
                # Exception occurred, rollback any pending transactions
                self.connection.rollback()
            self.connection.close()
        
        # Return False to propagate any exceptions
        return False


def main():
    """
    Demonstration of using the DatabaseConnection context manager.
    """
    # Create a sample database and table for testing
    try:
        # First, create the database and users table
        conn = sqlite3.connect('example.db')
        cursor = conn.cursor()
        
        # Create users table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                email TEXT
            )
        ''')
        
        # Insert some sample data
        sample_users = [
            (1, 'Alice', 25, 'alice@email.com'),
            (2, 'Bob', 30, 'bob@email.com'),
            (3, 'Charlie', 35, 'charlie@email.com'),
            (4, 'Diana', 45, 'diana@email.com')
        ]
        
        cursor.executemany('''
            INSERT OR REPLACE INTO users (id, name, age, email) 
            VALUES (?, ?, ?, ?)
        ''', sample_users)
        
        conn.commit()
        conn.close()
        
        # Now use our custom context manager
        print("Using DatabaseConnection context manager:")
        print("-" * 40)
        
        with DatabaseConnection('example.db') as cursor:
            cursor.execute("SELECT * FROM users")
            results = cursor.fetchall()
            
            print("Query: SELECT * FROM users")
            print("Results:")
            for row in results:
                print(f"ID: {row[0]}, Name: {row[1]}, Age: {row[2]}, Email: {row[3]}")
    
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
